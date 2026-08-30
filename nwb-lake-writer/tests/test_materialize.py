"""Materializing analysis.spike_events onto the reference clock."""

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from nwb_lake_writer.materialize import NotAligned, spike_events

AP, HARP = 30000, 31250
REF = "harp"
PROBE = "probe.samples"


class Handle:
    def __init__(self, path):
        self.path = path


class Fake:
    """The smallest thing `spike_events` reads: two tables and a file handle."""

    def __init__(self, tmp_path, *, ticks, clocks, anchors=True, reference=REF, unit_of=None):
        self.tmp_path = tmp_path
        self.root = tmp_path / "packet"
        self.root.mkdir(exist_ok=True)
        self._clocks = pa.table({"clock_id": [REF, PROBE], "tick_rate_hz": [float(HARP), float(AP)]})
        unit_of = unit_of or (lambda i: f"u{i % 2:02d}")
        self._sessions = pa.table({"session_id": ["s1"], "reference_clock_id": [reference]})
        n = 8
        at = np.arange(n, dtype=np.int64) * AP + 1000
        ap = np.arange(n, dtype=np.int64) * HARP + 500_000_000
        self._anchors = pa.table(
            {
                "clock_id": [PROBE] * n if anchors else [],
                "anchor_index": list(range(n)) if anchors else [],
                "t_tick": at.tolist() if anchors else [],
                "parent_tick": ap.tolist() if anchors else [],
            }
        )
        path = tmp_path / "spike_events.parquet"
        pq.write_table(
            pa.table(
                {
                    "session_id": ["s1"] * len(ticks),
                    "unit_id": [unit_of(i) for i in range(len(ticks))],
                    "sorting_run_id": ["run"] * len(ticks),
                    "curation_id": ["cur"] * len(ticks),
                    "t_tick": pa.array(ticks, type=pa.int64()),
                    "clock_id": clocks,
                }
            ),
            path,
        )
        self._path = path

    def table(self, rid):
        return {
            "core.sessions": self._sessions,
            "core.clock_anchors": self._anchors,
            "core.clocks": self._clocks,
        }[rid]

    def table_resource(self, rid):
        return Handle(self._path)


def rows(packet, **kwargs):
    batches = list(spike_events(packet, **kwargs))
    return pa.Table.from_batches(batches).to_pydict() if batches else {}


def test_ticks_land_on_the_reference_clock(tmp_path):
    """An anchor maps to its own parent, so a spike at one maps there too."""
    out = rows(Fake(tmp_path, ticks=[1000, 1000 + AP], clocks=[PROBE] * 2))
    assert out["t_tick"] == [500_000_000, 500_000_000 + HARP]
    assert out["clock_id"] == [REF, REF]


def test_a_spike_already_on_the_reference_passes_through(tmp_path):
    """Behaviour is HARP-native; converting it again would be wrong, not merely wasteful."""
    out = rows(Fake(tmp_path, ticks=[777], clocks=[REF]))
    assert out["t_tick"] == [777]


def test_an_unmappable_spike_is_dropped(tmp_path):
    """R27 §5.3 leaves it undefined, and a derived table is the wrong place to say so."""
    far = 1000 + 20 * AP
    out = rows(Fake(tmp_path, ticks=[1000, far], clocks=[PROBE] * 2))
    assert out["t_tick"] == [500_000_000]


def test_the_reference_comes_from_the_session(tmp_path):
    """R27 §2: the session declares what its times are reported on."""
    out = rows(Fake(tmp_path, ticks=[1000], clocks=[PROBE]))
    assert out["clock_id"] == [REF]


def test_an_explicit_reference_overrides_it(tmp_path):
    out = rows(Fake(tmp_path, ticks=[1000], clocks=[PROBE], reference="other"), reference=REF)
    assert out["clock_id"] == [REF]


def test_a_session_declaring_no_reference_is_refused(tmp_path):
    with pytest.raises(NotAligned, match="no reference_clock_id"):
        rows(Fake(tmp_path, ticks=[1000], clocks=[PROBE], reference=None))


def test_a_clock_with_no_anchors_is_refused(tmp_path):
    """Silently dropping every spike on it would look like an empty session."""
    with pytest.raises(NotAligned, match="no anchors"):
        rows(Fake(tmp_path, ticks=[1000], clocks=[PROBE], anchors=False))


def test_one_bucket_keeps_the_input_order(tmp_path):
    """core.spike_events is already in the registry's order and the map is monotone, so
    within a single bucket nothing needs reordering."""
    ticks = list(range(1000, 1000 + 5 * AP, AP // 4))
    out = rows(Fake(tmp_path, ticks=ticks, clocks=[PROBE] * len(ticks)), bucket_seconds=3600)
    assert len(set(out["time_bucket_tick"])) == 1
    assert out["t_tick"] == sorted(out["t_tick"])


def test_every_row_carries_the_start_of_its_bucket(tmp_path):
    ticks = list(range(1000, 1000 + 5 * AP, AP // 4))
    out = rows(Fake(tmp_path, ticks=ticks, clocks=[PROBE] * len(ticks)), bucket_seconds=1)
    width = HARP
    assert out["time_bucket_tick"] == [(t // width) * width for t in out["t_tick"]]
    assert len(set(out["time_bucket_tick"])) > 1  # the fixture really does span buckets


def test_buckets_come_out_in_time_order(tmp_path):
    """The whole point of the layout: a row group's tick range is one bucket wide."""
    ticks = list(range(1000, 1000 + 5 * AP, AP // 4))
    out = rows(Fake(tmp_path, ticks=ticks, clocks=[PROBE] * len(ticks)), bucket_seconds=1)
    assert out["time_bucket_tick"] == sorted(out["time_bucket_tick"])


def test_a_batch_never_spans_two_buckets(tmp_path):
    """R30 §3.2: each batch becomes one row group, and a straddling group would span twice
    the intended time range."""
    ticks = list(range(1000, 1000 + 5 * AP, AP // 4))
    packet = Fake(tmp_path, ticks=ticks, clocks=[PROBE] * len(ticks))
    for batch in spike_events(packet, bucket_seconds=1):
        assert len(set(batch.column("time_bucket_tick").to_pylist())) == 1


def test_units_stay_grouped_inside_a_bucket(tmp_path):
    """Core is unit-major, so appending in its order must leave each bucket unit-major."""
    ticks = list(range(1000, 1000 + 5 * AP, AP // 8))
    half = len(ticks) // 2
    # One unit's spikes, then the next unit's -- which is what core.spike_events looks like.
    ordered = sorted(ticks[:half]) + sorted(ticks[half:])
    packet = Fake(
        tmp_path,
        ticks=ordered,
        clocks=[PROBE] * len(ordered),
        unit_of=lambda i: "u00" if i < half else "u01",
    )
    out = rows(packet, bucket_seconds=1)
    seen = list(zip(out["time_bucket_tick"], out["unit_id"], out["t_tick"], strict=True))
    assert seen == sorted(seen)


def test_identity_columns_survive(tmp_path):
    out = rows(Fake(tmp_path, ticks=[1000, 1000 + AP], clocks=[PROBE] * 2))
    assert out["unit_id"] == ["u00", "u01"]
    assert out["sorting_run_id"] == ["run", "run"]
    assert out["curation_id"] == ["cur", "cur"]


def test_a_batch_where_nothing_maps_yields_nothing(tmp_path):
    far = 1000 + 50 * AP
    assert list(spike_events(Fake(tmp_path, ticks=[far], clocks=[PROBE]))) == []


# -- provenance (R31) -------------------------------------------------------------------


class Recorder:
    """The three calls `into` makes on a writer."""

    def __init__(self):
        self.batches, self.tables, self.derived, self.runs = {}, {}, {}, {}

    def add_batches(self, rid, batches):
        self.batches[rid] = list(batches)

    def add(self, rid, records):
        self.tables.setdefault(rid, []).extend(records)

    def derives(self, rid, sources):
        self.derived[rid] = list(sources)

    def produced_by(self, rid, run_id):
        self.runs[rid] = run_id


def test_into_records_the_run_that_produced_the_table(tmp_path):
    from nwb_lake_writer.materialize import RUN_ID, into

    writer = Recorder()
    assert into(Fake(tmp_path, ticks=[1000], clocks=[PROBE]), writer) == "analysis.spike_events"
    assert writer.runs["analysis.spike_events"] == RUN_ID
    assert writer.derived["analysis.spike_events"] == [
        "core.spike_events",
        "core.clock_anchors",
        "core.clocks",
    ]
    run = writer.tables["core.processing_runs"][0]
    assert run["processing_run_id"] == RUN_ID
    assert run["activity_type"] == "materialization"
    assert run["software_name"] and run["software_version"]


def test_the_bucket_width_is_recorded_because_it_cannot_be_recovered(tmp_path):
    """R31 §3: a table whose buckets are all non-empty looks the same at 300 s as at 299 s."""
    from nwb_lake_writer.materialize import into

    writer = Recorder()
    into(Fake(tmp_path, ticks=[1000], clocks=[PROBE]), writer, bucket_seconds=17)
    assert writer.tables["core.processing_runs"][0]["parameters"]["bucket_seconds"] == 17

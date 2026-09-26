"""Materializing analysis.spike_events onto the reference clock."""

from types import SimpleNamespace

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_writer.materialize import Collided, NotAligned, spike_events

from .conftest import REGISTRY

AP, HARP = 30000, 31250
#: Identifiers are `int32` since R53, and so is what a materialised row carries. The strings
#: these were let the materializer's dictionary path pass a test after the format had stopped
#: producing anything it could encode.
REF, PROBE = 0, 1
SESSION, RUN, CURATION = 0, 0, 0


class Handle:
    def __init__(self, path):
        self.path = path


class Fake:
    """The smallest thing `spike_events` reads: two tables and a file handle."""

    def __init__(self, tmp_path, *, ticks, clocks, anchors=True, reference=REF, unit_of=None, absent=()):
        self.tmp_path = tmp_path
        self.absent = set(absent)
        self.root = tmp_path / "packet"
        self.root.mkdir(exist_ok=True)
        self._clocks = pa.table(
            {
                "clock_id": pa.array([REF, PROBE], type=pa.int32()),
                "clock_name": ["harp", "probe.samples"],
                "tick_rate_hz": [float(HARP), float(AP)],
            }
        )
        unit_of = unit_of or (lambda i: i % 2)
        self._sessions = pa.table(
            {
                "session_id": pa.array([SESSION], type=pa.int32()),
                "reference_clock_id": pa.array([reference], type=pa.int32()),
            }
        )
        self.sessions = (SESSION,)
        n = 8
        at = np.arange(n, dtype=np.int64) * AP + 1000
        ap = np.arange(n, dtype=np.int64) * HARP + 500_000_000
        self._anchors = pa.table(
            {
                "clock_id": pa.array([PROBE] * n if anchors else [], type=pa.int32()),
                "anchor_index": list(range(n)) if anchors else [],
                "t_tick": at.tolist() if anchors else [],
                "parent_tick": ap.tolist() if anchors else [],
            }
        )
        # R96 §3.4 struck `core.spike_events.clock_id` and §3.3 resolves a tick's clock through
        # the unit, so the clock is declared once per unit and the spike carries none.
        identifiers = [unit_of(i) for i in range(len(ticks))]
        by_unit: dict[int, int] = {}
        for unit, clock in zip(identifiers, clocks, strict=True):
            if by_unit.setdefault(unit, clock) != clock:
                raise AssertionError(f"unit {unit} on two clocks, which R96 §3.3 leaves unsayable")
        ordered = sorted(by_unit)
        self._units = pa.table(
            {
                "unit_id": pa.array(ordered, type=pa.int32()),
                "clock_id": pa.array([by_unit[u] for u in ordered], type=pa.int32()),
            }
        )
        path = tmp_path / "spike_events.parquet"
        pq.write_table(
            pa.table(
                {
                    "session_id": pa.array([SESSION] * len(ticks), type=pa.int32()),
                    "unit_id": pa.array(identifiers, type=pa.int32()),
                    "t_tick": pa.array(ticks, type=pa.int64()),
                }
            ),
            path,
        )
        self._path = path

    @property
    def registry(self):
        """The reference registry, which is where the derived table's types come from."""
        return REGISTRY

    def table(self, rid):
        return {
            "core.sessions": self._sessions,
            "core.clock_anchors": self._anchors,
            "core.clocks": self._clocks,
            "core.units": self._units,
        }[rid]

    def resources(self):
        carried = ["core.sessions", "core.clock_anchors", "core.clocks", "core.units", "core.spike_events"]
        return tuple(SimpleNamespace(resource_id=rid) for rid in carried if rid not in self.absent)

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
    """Part 01 §3.9 leaves it undefined, and a derived table is the wrong place to say so."""
    far = 1000 + 20 * AP
    out = rows(Fake(tmp_path, ticks=[1000, far], clocks=[PROBE] * 2))
    assert out["t_tick"] == [500_000_000]


def test_two_spikes_of_one_unit_on_one_reference_tick_refuse_the_table(tmp_path):
    """Part 06 §4. The table is keyed on the converted tick, so a collision is unbuildable.

    A conversion preserves distinctness only where it expands; here the two spikes are already
    on the reference clock and pass through, which is the same arrival the writer must refuse.
    """
    packet = Fake(tmp_path, ticks=[777, 777], clocks=[REF, REF], unit_of=lambda i: 0)
    with pytest.raises(Collided, match="unit 0 has two spikes on reference tick 777"):
        rows(packet)


def test_two_spikes_of_different_units_on_one_tick_are_fine(tmp_path):
    """The key is `(session_id, unit_id, t_tick)`, so one tick may carry many units' spikes."""
    out = rows(Fake(tmp_path, ticks=[777, 777], clocks=[REF, REF], unit_of=lambda i: i))
    assert out["t_tick"] == [777, 777]
    assert out["unit_id"] == [0, 1]


def test_a_dropped_spike_is_counted(tmp_path):
    """Part 06 §4: a derived table one row short looks exactly like a derived table."""
    counted: list[int] = [0]
    rows(Fake(tmp_path, ticks=[1000, 1000 + 20 * AP], clocks=[PROBE] * 2), dropped=counted)
    assert counted == [1]


def test_dropping_nothing_is_counted_too(tmp_path):
    """A recorded zero is the evidence the bound was sufficient, not an assumption."""
    counted: list[int] = [0]
    rows(Fake(tmp_path, ticks=[1000, 1000 + AP], clocks=[PROBE] * 2), dropped=counted)
    assert counted == [0]


def test_the_reference_comes_from_the_session(tmp_path):
    """R27 §2: the session declares what its times are reported on."""
    out = rows(Fake(tmp_path, ticks=[1000], clocks=[PROBE]))
    assert out["clock_id"] == [REF]


def test_an_explicit_reference_overrides_it(tmp_path):
    out = rows(Fake(tmp_path, ticks=[1000], clocks=[PROBE], reference=99), reference="harp")
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
    """Part 03 §5.4: each batch becomes one row group, and a straddling group would span twice
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
        unit_of=lambda i: 0 if i < half else 1,
    )
    out = rows(packet, bucket_seconds=1)
    seen = list(zip(out["time_bucket_tick"], out["unit_id"], out["t_tick"], strict=True))
    assert seen == sorted(seen)


def test_identity_columns_survive(tmp_path):
    out = rows(Fake(tmp_path, ticks=[1000, 1000 + AP], clocks=[PROBE] * 2))
    assert out["unit_id"] == [0, 1]
    # R81 §2.3: the spike row identifies its unit by one column, and the run and curation
    # are attributes of `core.units` a join away.
    assert out["unit_id"] == out["unit_id"]


def test_a_batch_where_nothing_maps_yields_nothing(tmp_path):
    far = 1000 + 50 * AP
    assert list(spike_events(Fake(tmp_path, ticks=[far], clocks=[PROBE]))) == []


# -- provenance (R31) -------------------------------------------------------------------


class Recorder:
    """The three calls `into` makes on a writer."""

    def __init__(self):
        self.batches, self.tables, self.derived = {}, {}, {}

    def add_batches(self, rid, batches):
        self.batches[rid] = list(batches)

    def add(self, rid, records):
        self.tables.setdefault(rid, []).extend(records)

    def derives(self, rid, sources):
        self.derived[rid] = list(sources)


def test_into_records_lineage_and_a_run_row(tmp_path):
    """Part 04 §7 requires the lineage; Part 06 §5 permits the run, which no manifest member names."""
    from escapewheel_writer.materialize import RUN_ID, into

    writer = Recorder()
    assert into(Fake(tmp_path, ticks=[1000], clocks=[PROBE]), writer) == "analysis.spike_events"
    assert writer.derived["analysis.spike_events"] == [
        "core.spike_events",
        "core.clock_anchors",
        "core.clocks",
    ]
    run = writer.tables["core.processing_runs"][0]
    assert run["processing_run_id"] == RUN_ID
    assert run["activity_type"] == "materialization"
    assert run["software_name"] and run["software_version"]


def test_lineage_names_only_a_source_the_packet_carries(tmp_path):
    """`core.clock_anchors` is optional, and a packet without it cannot be a lineage source."""
    from escapewheel_writer.materialize import into

    writer = Recorder()
    into(Fake(tmp_path, ticks=[1000], clocks=[REF], absent={"core.clock_anchors"}), writer)
    assert writer.derived["analysis.spike_events"] == ["core.spike_events", "core.clocks"]


def test_the_dropped_count_is_the_one_the_stream_reached(tmp_path):
    """A writer consumes the stream at commit, after `into` has returned the run row."""
    from escapewheel_writer.materialize import into

    class Deferred(Recorder):
        def add_batches(self, rid, batches):
            self.batches[rid] = batches

    writer = Deferred()
    into(Fake(tmp_path, ticks=[1000, 1000 + 20 * AP], clocks=[PROBE] * 2), writer)
    list(writer.batches["analysis.spike_events"])
    assert writer.tables["core.processing_runs"][0]["parameters"]["spikes_without_a_defined_mapping"] == 1


def test_the_bucket_width_is_recorded_because_it_cannot_be_recovered(tmp_path):
    """Part 06 §5: an unrecoverable transform parameter is recorded."""
    from escapewheel_writer.materialize import into

    writer = Recorder()
    into(Fake(tmp_path, ticks=[1000], clocks=[PROBE]), writer, bucket_seconds=17)
    assert writer.tables["core.processing_runs"][0]["parameters"]["bucket_seconds"] == 17


def test_a_budget_keeps_the_partition_in_memory(tmp_path):
    """Given room the partition never reaches disk, and the rows are the same either way."""
    scratch = tmp_path / "spill"
    scratch.mkdir()
    spilled = rows(Fake(tmp_path, ticks=[1000, 1000 + AP], clocks=[PROBE] * 2), scratch=scratch)

    held_dir = tmp_path / "held"
    held_dir.mkdir()
    held = rows(
        Fake(tmp_path, ticks=[1000, 1000 + AP], clocks=[PROBE] * 2),
        scratch=held_dir,
        memory_budget="1GB",
    )
    assert not list(held_dir.glob("*.parquet")), "a budget this large spills nothing"
    assert held == spilled


def test_a_byte_budget_reads_the_units_it_is_written_in():
    from escapewheel_writer.materialize import _bytes

    assert _bytes("10GB") == 10 * (1 << 30)
    assert _bytes("512MB") == 512 * (1 << 20)
    assert _bytes("2G") == 2 * (1 << 30)
    assert _bytes(0) == 0

"""Spikes against events (R43 §4).

The fixture is sized so every expected count can be read off by hand. Two events at ticks 100
and 200; five spikes at 90, 100, 145, 190 and 210.

    half=30   windows [70,130] [170,230]   disjoint, spike 145 falls in neither
    half=60   windows [40,160] [140,260]   overlapping, spike 145 falls in both
"""

import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_reader import open_packet
from escapewheel_reader.alignment import (
    ClockMismatch,
    aligned_spikes,
    assigned_spikes,
    windows_disjoint,
)

from .conftest import CLOCK_BEHAVIOUR, CLOCK_PROBE, CURATION, SESSION, SORTING_RUN, UNITS, _resource

CUES = [100, 200]
SPIKES = [90, 100, 145, 190, 210]


@pytest.fixture
def aligned_packet(tmp_path, packet_root):
    """The fixture packet plus mapped spikes and cue events, all on one clock."""
    root = tmp_path / "aligned"
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())

    def write(layer, name, table):
        path = root / "tables" / layer
        path.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path / f"{name}.parquet", compression="zstd")
        return f"tables/{layer}/{name}.parquet"

    spikes = pa.table(
        {
            "session_id": pa.array([SESSION] * len(SPIKES)),
            "unit_id": pa.array([UNITS[0]] * len(SPIKES)),
            "sorting_run_id": pa.array([SORTING_RUN] * len(SPIKES)),
            "curation_id": pa.array([CURATION] * len(SPIKES)),
            "t_tick": pa.array(SPIKES, type=pa.int64()),
            "clock_id": pa.array([CLOCK_BEHAVIOUR] * len(SPIKES)),
            "time_bucket_tick": pa.array([0] * len(SPIKES), type=pa.int64()),
        }
    )
    # R91 §3.1: the kind and the clock are the stream's, and an event is a tick on one.
    events = pa.table(
        {
            "session_id": pa.array([SESSION] * len(CUES)),
            "stream_id": pa.array(["cue_stream"] * len(CUES)),
            "t_tick": pa.array(CUES, type=pa.int64()),
        }
    )
    streams = pa.table(
        {
            "event_stream_id": pa.array(["cue_stream"]),
            "session_id": pa.array([SESSION]),
            "name": pa.array(["cue"]),
            "event_type": pa.array(["cue"]),
            "clock_id": pa.array([CLOCK_BEHAVIOUR]),
        }
    )
    manifest["resources"] = [r for r in manifest["resources"]
                             if r["resource_id"] not in {"core.events", "core.event_streams"}]
    manifest["resources"].append(_resource("core.events", write("core", "events", events)))
    manifest["resources"].append(
        _resource("core.event_streams", write("core", "event_streams", streams)))
    entry = _resource("analysis.spike_events", write("analysis", "spike_events", spikes))
    entry["layer"] = "analysis"
    manifest["resources"].append(entry)
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


def test_disjoint_windows_are_recognised(aligned_packet):
    """The gap is 100 ticks, so windows of 60 fit between the cues and windows of 120 do not."""
    assert windows_disjoint(aligned_packet, "cue", 30)
    assert not windows_disjoint(aligned_packet, "cue", 60)


def test_a_spike_in_two_windows_is_returned_twice(aligned_packet):
    """The duplicating semantics R43 §4 needs: each event contributes its own window."""
    rows = aligned_spikes(aligned_packet, "cue", 60).fetchall()
    assert len(rows) == 6, "five spikes, one of them in both windows"

    by_tick: dict[int, list[int]] = {}
    for row in rows:
        by_tick.setdefault(row[5], []).append(row[4])
    assert sorted(by_tick[145]) == sorted(CUES), "the shared spike names both events"
    assert all(len(v) == 1 for t, v in by_tick.items() if t != 145)


def test_disjoint_windows_return_each_spike_once(aligned_packet):
    """Spike 145 falls outside both narrow windows, so four rows and no duplicates."""
    rows = aligned_spikes(aligned_packet, "cue", 30).fetchall()
    assert len(rows) == 4
    assert sorted(r[5] for r in rows) == [90, 100, 190, 210]


def test_the_asof_shortcut_returns_the_same_rows(aligned_packet):
    """The optimisation is invisible: the disjoint path must agree with the range join."""
    con = aligned_packet.duckdb(
        tables=("analysis.spike_events", "core.events", "core.event_streams"))
    half = 30
    reference = con.sql(
        "SELECT s.t_tick, e.t_tick FROM analysis_spike_events s "
        "JOIN (SELECT e.t_tick FROM core_events e JOIN core_event_streams m "
        "ON e.stream_id = m.event_stream_id WHERE m.event_type = 'cue') e "
        f"ON s.t_tick BETWEEN e.t_tick - {half} AND e.t_tick + {half}"
    ).fetchall()
    assert windows_disjoint(aligned_packet, "cue", half)
    got = [(r[5], r[4]) for r in aligned_spikes(aligned_packet, "cue", half).fetchall()]
    assert sorted(got) == sorted(reference)


def test_relative_ticks_are_signed(aligned_packet):
    """A spike before its event has a negative offset, which is what a PSTH bins on."""
    rows = {r[5]: r[6] for r in aligned_spikes(aligned_packet, "cue", 30).fetchall()}
    assert rows[90] == -10
    assert rows[100] == 0
    assert rows[210] == 10


def test_assignment_gives_each_spike_at_most_one_event(aligned_packet):
    """Where alignment duplicates, assignment chooses -- which is the whole difference."""
    rows = assigned_spikes(aligned_packet, "cue", to="nearest", half_window=60).fetchall()
    assert len(rows) == 5
    assert len({r[4] for r in rows}) == len(rows), "one row per spike"


def test_preceding_and_nearest_disagree(aligned_packet):
    """Two rules, two answers.

    Spike 190 has the second cue as its nearest and the first as its preceding, and the first is
    further away than the window, so preceding drops it while nearest keeps it. R91 §3.2 names an
    event by its tick, there being no identifier to name it by.
    """
    nearest = {r[4]: r[5] for r in assigned_spikes(aligned_packet, "cue", to="nearest", half_window=60).fetchall()}
    preceding = {r[4]: r[5] for r in assigned_spikes(aligned_packet, "cue", to="preceding", half_window=60).fetchall()}
    assert nearest[190] == CUES[1]
    assert 190 not in preceding
    assert len(nearest) == 5
    assert len(preceding) == 3


def test_nearest_without_a_window_is_refused(aligned_packet):
    """Unbounded, it would compare every spike against every event."""
    with pytest.raises(ValueError, match="needs half_window"):
        assigned_spikes(aligned_packet, "cue", to="nearest")


def test_an_unknown_assignment_is_refused(aligned_packet):
    """The choice is a name, not a free string."""
    with pytest.raises(ValueError, match="must be one of"):
        assigned_spikes(aligned_packet, "cue", to="closest")


def test_an_absent_event_type_is_a_lookup_failure(aligned_packet):
    """Nothing to align to is a missing key, not an empty result."""
    with pytest.raises(KeyError, match="no 'lick' stream"):
        aligned_spikes(aligned_packet, "lick", 30)


def test_events_on_another_clock_are_refused(aligned_packet):
    """A tick means nothing beside a tick on another clock (R27 §2), so this must not join."""
    root = aligned_packet.root
    # The clock is the stream's since R91 §3.1, so moving the events means moving their stream.
    path = root / "tables" / "core" / "event_streams.parquet"
    streams = pq.read_table(path)
    moved = streams.set_column(
        streams.schema.get_field_index("clock_id"),
        "clock_id",
        pa.array([CLOCK_PROBE] * streams.num_rows),
    )
    pq.write_table(moved, path, compression="zstd")
    with pytest.raises(ClockMismatch, match="map one onto the other"):
        aligned_spikes(open_packet(root), "cue", 30)

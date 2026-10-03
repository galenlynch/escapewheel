import json
import shutil

import numpy as np
import pyarrow as pa
import pytest
from packet_fixture import (
    CLOCK_BEHAVIOUR,
    CLOCK_PROBE,
    CURATION,
    SESSION,
    SESSION_NAME,
    SORTING_RUN,
    STREAMS,
    SUBJECT,
    TS,
    UNITS,
    resource_entry,
    write_packet,
    write_table,
)

#: What the fixture packet declares of core: each table's key and the columns a test reads.
COLUMNS = {
    "core.sessions": ("session_id", "session_name", "subject_id", "session_start_time"),
    "core.clocks": ("session_id", "clock_id"),
    "core.processing_runs": ("session_id", "processing_run_id"),
    "core.intervals": (
        "session_id",
        "interval_id",
        "interval_name",
        "interval_kind",
        "local_interval_label",
        "start_tick",
        "stop_tick",
        "clock_id",
    ),
    "core.units": ("session_id", "unit_id", "unit_name", "sorting_run_id", "curation_id", "quality_label", "clock_id"),
    "core.event_streams": ("event_stream_id", "session_id", "event_stream_name", "event_type", "clock_id"),
    "core.events": ("session_id", "stream_id", "t_tick"),
    "core.spike_events": ("session_id", "unit_id", "t_tick"),
    "analysis.spike_events": ("session_id", "unit_id", "t_tick"),
}


@pytest.fixture
def packet_root(tmp_path):
    """The shared packet with `core.clocks` declared and absent, so a test supplies the clocks it needs."""
    return write_packet(tmp_path / "session_001", COLUMNS, unwritten=("core.clocks",))


@pytest.fixture
def two_clock_packet(tmp_path, packet_root):
    """A packet whose spikes are on a probe clock and whose session reports on another.

    The realistic shape: anchors relate the two, and only a mapped tick is comparable with a
    behavioural event. Anchor pairs are exact multiples so the expected ticks are exact.
    """
    root = tmp_path / "two_clock"
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())
    by_id = {r["resource_id"]: r for r in manifest["resources"]}

    i32 = pa.int32()
    sessions = pa.table(
        {
            "session_id": pa.array([SESSION], type=i32),
            "session_name": pa.array([SESSION_NAME]),
            "subject_id": pa.array([SUBJECT], type=i32),
            "session_start_time": pa.array([1_756_000_000_000_000], type=TS),
            "reference_clock_id": pa.array([CLOCK_BEHAVIOUR], type=i32),
            # Probe tick 0, which is where the probe clock's observation window begins and so
            # what Part 01 §2.2 makes the origin. It lands on a whole harp second by construction,
            # so a derived second is exact and a test can say what it should be.
            "t_zero_tick": pa.array([1_000_000], type=pa.int64()),
        }
    )
    clocks = pa.table(
        {
            "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], type=i32),
            "session_id": pa.array([SESSION] * 2, type=i32),
            "tick_rate_num": pa.array([31_250, 30_000], type=pa.int64()),
            "tick_rate_den": pa.array([1, 1], type=pa.int64()),
            "parent_clock_id": pa.array([None, CLOCK_BEHAVIOUR], type=i32),
        }
    )
    units = pa.table(
        {
            "session_id": pa.array([SESSION] * 3, type=i32),
            "unit_id": pa.array(list(UNITS), type=i32),
            "unit_name": pa.array([str(unit) for unit in UNITS]),
            "sorting_run_id": pa.array([SORTING_RUN] * 3, type=i32),
            "curation_id": pa.array([CURATION] * 3, type=i32),
            "quality_label": pa.array(["sua", "mua", "noise"]),
            "clock_id": pa.array([CLOCK_PROBE, CLOCK_PROBE, CLOCK_BEHAVIOUR], type=i32),
        }
    )
    # Probe tick 0 is harp tick 1,000,000, and the probe runs at 30 kHz against harp's 31,250.
    n = 8
    anchors = pa.table(
        {
            "clock_id": pa.array([CLOCK_PROBE] * n, type=i32),
            "anchor_index": pa.array(list(range(n)), type=pa.int64()),
            "t_tick": pa.array([i * 30_000 for i in range(n)], type=pa.int64()),
            "parent_tick": pa.array([1_000_000 + i * 31_250 for i in range(n)], type=pa.int64()),
        }
    )
    spikes = pa.table(
        {
            "session_id": pa.array([SESSION] * 3, type=i32),
            "unit_id": pa.array([UNITS[0], UNITS[0], UNITS[2]], type=i32),
            "t_tick": pa.array([30_000, 60_000, 90_000], type=pa.int64()),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array([SESSION], type=i32),
            "stream_id": pa.array([STREAMS[0]], type=i32),
            "t_tick": pa.array([1_200_000], type=pa.int64()),
        }
    )
    # The kind lives on the stream, so the fixture declares the one it emits.
    event_streams = pa.table(
        {
            "event_stream_id": pa.array([STREAMS[0]], type=i32),
            "session_id": pa.array([SESSION], type=i32),
            "event_stream_name": pa.array(["go_cue"]),
            "event_type": pa.array(["go_cue"]),
            "clock_id": pa.array([CLOCK_BEHAVIOUR], type=i32),
        }
    )
    for resource_id, name, table in (
        ("core.sessions", "sessions", sessions),
        ("core.units", "units", units),
        ("core.spike_events", "spike_events", spikes),
        ("core.event_streams", "event_streams", event_streams),
        ("core.events", "events", events),
    ):
        by_id[resource_id]["uri"] = write_table(root, name, table)
    manifest["resources"].append(resource_entry("core.clock_anchors", write_table(root, "clock_anchors", anchors)))
    manifest["resources"].append(resource_entry("core.clocks", write_table(root, "clocks", clocks)))
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return root


@pytest.fixture
def dense_root(two_clock_packet):
    """`two_clock_packet` with spikes and events on every 7th tick across and past the probe's anchors.

    The first two units and the second stream are on the probe, the third unit and the first stream
    on the reference clock, and intervals sit on both, so a range selects differently on each clock.
    """
    i32 = pa.int32()
    ticks = np.arange(-60_000, 300_000, 7, dtype=np.int64)
    spikes = pa.table(
        {
            "session_id": pa.array([SESSION] * (3 * ticks.size), i32),
            "unit_id": pa.array(np.repeat(np.array(UNITS, np.int32), ticks.size)),
            "t_tick": pa.array(np.tile(ticks, 3) + np.repeat([0, 1_000_000, 1_000_000], ticks.size)),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array([SESSION] * (2 * ticks.size), i32),
            "stream_id": pa.array(np.repeat(np.array(STREAMS, np.int32), ticks.size)),
            "t_tick": pa.array(np.concatenate([ticks + 1_000_000, ticks])),
        }
    )
    event_streams = pa.table(
        {
            "event_stream_id": pa.array(list(STREAMS), i32),
            "session_id": pa.array([SESSION] * 2, i32),
            "event_stream_name": pa.array(["go_cue", "lick"]),
            "event_type": pa.array(["go_cue", "lick"]),
            "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], i32),
        }
    )
    intervals = pa.table(
        {
            "session_id": pa.array([SESSION] * 4, i32),
            "interval_id": pa.array([1, 2, 3, 4], i32),
            "interval_name": pa.array(["a", "b", "c", "d"]),
            "interval_kind": pa.array(["trial"] * 4),
            "local_interval_label": pa.array(["a", "b", "c", "d"]),
            "start_tick": pa.array([0, 90_000, 1_010_000, 1_100_000], pa.int64()),
            "stop_tick": pa.array([30_000, 400_000, 1_040_000, 1_200_000], pa.int64()),
            "clock_id": pa.array([CLOCK_PROBE, CLOCK_PROBE, CLOCK_BEHAVIOUR, CLOCK_BEHAVIOUR], i32),
        }
    )
    manifest = json.loads((two_clock_packet / "packet.json").read_text())
    by_id = {r["resource_id"]: r for r in manifest["resources"]}
    for resource_id, name, table in (
        ("core.spike_events", "spike_events", spikes),
        ("core.events", "events", events),
        ("core.event_streams", "event_streams", event_streams),
        ("core.intervals", "intervals", intervals),
    ):
        by_id[resource_id]["uri"] = write_table(two_clock_packet, name, table)
    (two_clock_packet / "packet.json").write_text(json.dumps(manifest, indent=2))
    return two_clock_packet

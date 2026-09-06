import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

TS = pa.timestamp("us", tz="UTC")

#: R53 §2.1 makes an identifier an integer. The values are distinct across kinds so a test that
#: confuses two of them fails rather than passing by coincidence, and a carried one (R53 §2.3)
#: is the number its source would really have supplied.
SESSION = 1
SUBJECT = 7
CLOCK_BEHAVIOUR = 3
CLOCK_PROBE = 4
TRIALS = (0, 1)  # carried: an NWB trials table numbers its rows from 0
UNITS = (11, 12, 13)  # carried: the sorter's own labels
SORTING_RUN = 5
CURATION = 6
EVENTS = (20, 21, 22)

#: The session's name, which is what the manifest lists and what a stable cross-packet
#: reference uses (R53 §2.3.1).
SESSION_NAME = "s001"


def _write(root, name, table):
    path = root / "tables" / "core"
    path.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path / f"{name}.parquet", compression="zstd")
    return f"tables/core/{name}.parquet"


def _resource(resource_id, uri, **extra):
    entry = {
        "resource_id": resource_id,
        "layer": "core",
        "kind": "table",
        "schema_id": f"{resource_id}.v0.1",
        "physical_profile": "parquet",
        "uri": uri,
        "canonical": True,
        "validation_state": "passed",
    }
    entry.update(extra)
    return entry


#: R53 §2.3, mirroring the registry's own map: an identifier is the source's own number or one
#: this format chose, and only the second obliges its owner to carry a `*_name`.
_CARRIED = {"interval_id", "unit_id"}


def _col(name, type_, presence, **extra):
    # R48 §2.1: every column declares a role. Inferred here from the same two conventions the
    # registry's own map rests on, because a test fixture's columns are all ordinary shapes.
    role = (
        "coordinate" if name.endswith("_tick") else "identifier" if name.endswith("_id") else extra.pop("role", "data")
    )
    column = {"name": name, "type": type_, "presence": presence, "role": role, "description": name, **extra}
    if role == "identifier":
        column["identity"] = "carried" if name in _CARRIED else "assigned"
    return column


def _registry():
    """A registry describing exactly the tables the fixture writes."""
    return {
        "registry_version": "0.1.0",
        "semantic_standard_version": "escapewheel-semantic-v0.1",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "tables": {
            "core.sessions": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("session_name", "string", "nullable"),
                    _col("subject_id", "int32", "required"),
                    _col("session_start_time", "timestamp", "required"),
                ],
                "primary_key": ["session_id"],
                "references": [],
                "sort": ["session_id"],
                "rules": [
                    {
                        "id": "core.sessions.manifest_sessions_match",
                        "level": "error",
                        "message": "the manifest sessions list disagrees with core.sessions",
                        "sql": (
                            "SELECT session_name FROM core_sessions WHERE session_name NOT IN "
                            "(SELECT session_id FROM manifest_sessions)"
                        ),
                    }
                ],
            },
            "core.intervals": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    dict(_col("interval_kind", "string", "required"), role="discriminator", resolves="required"),
                    _col("interval_id", "int32", "required"),
                    _col("start_tick", "int64", "required"),
                    _col("stop_tick", "int64", "required"),
                    _col("clock_id", "int32", "required"),
                ],
                "primary_key": ["session_id", "interval_kind", "interval_id"],
                "references": [
                    {
                        "columns": ["session_id"],
                        "resource": "core.sessions",
                        "resource_columns": ["session_id"],
                    }
                ],
                "sort": ["session_id", "interval_kind", "interval_id"],
                "rules": [
                    {
                        "id": "core.intervals.interval_valid",
                        "level": "error",
                        "message": "stop_tick precedes start_tick",
                        "sql": "SELECT session_id, interval_id FROM core_intervals WHERE stop_tick < start_tick",
                    }
                ],
            },
            "core.units": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("unit_id", "int32", "required"),
                    _col("sorting_run_id", "int32", "required"),
                    _col("curation_id", "int32", "required"),
                    _col("quality_label", "string", "nullable", enum=["sua", "mua", "noise"]),
                ],
                "primary_key": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                "references": [
                    {
                        "columns": ["session_id"],
                        "resource": "core.sessions",
                        "resource_columns": ["session_id"],
                    }
                ],
                "sort": ["session_id", "unit_id"],
                "rules": [],
            },
            "core.events": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("event_id", "int32", "required"),
                    _col("event_type", "string", "required", vocabulary="open"),
                    _col("t_tick", "int64", "required"),
                    _col("clock_id", "int32", "required"),
                ],
                "primary_key": ["session_id", "event_id"],
                "references": [
                    {
                        "columns": ["session_id"],
                        "resource": "core.sessions",
                        "resource_columns": ["session_id"],
                    }
                ],
                "sort": ["session_id", "event_id"],
                "rules": [],
            },
            "core.spike_events": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("unit_id", "int32", "required"),
                    _col("sorting_run_id", "int32", "required"),
                    _col("curation_id", "int32", "required"),
                    _col("t_tick", "int64", "required"),
                    _col("clock_id", "int32", "required"),
                ],
                "primary_key": ["session_id", "unit_id", "sorting_run_id", "curation_id", "t_tick"],
                "references": [
                    {
                        "columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                        "resource": "core.units",
                        "resource_columns": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                    }
                ],
                "sort": ["session_id", "unit_id", "t_tick"],
                "rules": [],
            },
        },
    }


@pytest.fixture
def packet_root(tmp_path):
    """A minimal two-table packet: one session, two trials referencing it."""
    root = tmp_path / "session_001"
    root.mkdir()

    i32 = pa.int32()
    sessions = pa.table(
        {
            "session_id": pa.array([SESSION], type=i32),
            "session_name": pa.array([SESSION_NAME]),
            "subject_id": pa.array([SUBJECT], type=i32),
            "session_start_time": pa.array([1_756_000_000_000_000], type=TS),
        }
    )
    trials = pa.table(
        {
            "session_id": pa.array([SESSION] * 2, type=i32),
            "interval_kind": pa.array(["task.trials"] * 2),
            "interval_id": pa.array(list(TRIALS), type=i32),
            "start_tick": pa.array([1000, 6000], type=pa.int64()),
            "stop_tick": pa.array([5000, 10000], type=pa.int64()),
            "clock_id": pa.array([CLOCK_BEHAVIOUR] * 2, type=i32),
        }
    )
    units = pa.table(
        {
            "session_id": pa.array([SESSION] * 2, type=i32),
            "unit_id": pa.array(list(UNITS[:2]), type=i32),
            "sorting_run_id": pa.array([SORTING_RUN] * 2, type=i32),
            "curation_id": pa.array([CURATION] * 2, type=i32),
            "quality_label": pa.array(["sua", "mua"]),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array([SESSION] * 3, type=i32),
            "event_id": pa.array(list(EVENTS), type=i32),
            "event_type": pa.array(["stimulus_onset", "reward", "stimulus_onset"]),
            "t_tick": pa.array([1200, 4200, 6200], type=pa.int64()),
            "clock_id": pa.array([CLOCK_BEHAVIOUR] * 3, type=i32),
        }
    )
    spike_events = pa.table(
        {
            "session_id": pa.array([SESSION] * 5, type=i32),
            "unit_id": pa.array([UNITS[0]] * 3 + [UNITS[1]] * 2, type=i32),
            "sorting_run_id": pa.array([SORTING_RUN] * 5, type=i32),
            "curation_id": pa.array([CURATION] * 5, type=i32),
            "t_tick": pa.array([30000, 39000, 48000, 45000, 66000], type=pa.int64()),
            "clock_id": pa.array([CLOCK_PROBE] * 5, type=i32),
        }
    )
    resources = [
        _resource("core.sessions", _write(root, "sessions", sessions)),
        _resource("core.intervals", _write(root, "intervals", trials)),
        _resource("core.units", _write(root, "units", units)),
        _resource("core.events", _write(root, "events", events)),
        _resource("core.spike_events", _write(root, "spike_events", spike_events)),
    ]

    (root / "schemas").mkdir()
    (root / "schemas" / "logical_schemas.json").write_text(json.dumps(_registry(), indent=2))

    (root / "packet.json").write_text(
        json.dumps(
            {
                "packet_id": "session_001",
                "packet_version": "0.1.0",
                "profile_id": "escapewheel-portable-v0.1",
                "semantic_standard_version": "escapewheel-semantic-v0.1",
                "logical_standard_version": "escapewheel-logical-v0.1",
                "registry_version": "0.1.0",
                "created_at": "2026-08-26T00:00:00Z",
                "sessions": [SESSION_NAME],
                "required_codecs": [],
                "resources": resources,
                "validation": {
                    "status": "passed",
                    "validated_at": "2026-08-26T00:00:00Z",
                    "validator_name": "escapewheel_validate",
                    "validator_version": "0.1.0",
                },
            },
            indent=2,
        )
    )
    return root


@pytest.fixture
def two_clock_packet(tmp_path, packet_root):
    """A packet whose spikes are on a probe clock and whose session reports on another.

    The realistic shape: anchors relate the two, and only a mapped tick is comparable with a
    behavioural event. Anchor pairs are exact multiples so the expected ticks are exact.
    """
    import shutil

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
            "session_start_time": pa.array([1_756_000_000_000_000], type=pa.timestamp("us", tz="UTC")),
            "reference_clock_id": pa.array([CLOCK_BEHAVIOUR], type=i32),
            # Probe tick 0, which is where the probe clock's observation window begins and so
            # what R39 §2.1 makes the origin. It lands on a whole harp second by construction,
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
            "sorting_run_id": pa.array([SORTING_RUN] * 3, type=i32),
            "curation_id": pa.array([CURATION] * 3, type=i32),
            "t_tick": pa.array([30_000, 60_000, 90_000], type=pa.int64()),
            "clock_id": pa.array([CLOCK_PROBE, CLOCK_PROBE, CLOCK_BEHAVIOUR], type=i32),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array([SESSION], type=i32),
            "event_id": pa.array([EVENTS[0]], type=i32),
            "event_type": pa.array(["go_cue"]),
            "t_tick": pa.array([1_200_000], type=pa.int64()),
            "clock_id": pa.array([CLOCK_BEHAVIOUR], type=i32),
        }
    )
    for resource_id, name, table in (
        ("core.sessions", "sessions", sessions),
        ("core.spike_events", "spike_events", spikes),
        ("core.events", "events", events),
    ):
        by_id[resource_id]["uri"] = _write(root, name, table)
    manifest["resources"].append(_resource("core.clock_anchors", _write(root, "clock_anchors", anchors)))
    manifest["resources"].append(_resource("core.clocks", _write(root, "clocks", clocks)))
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return root

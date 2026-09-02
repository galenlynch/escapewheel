import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

TS = pa.timestamp("us", tz="UTC")


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


def _col(name, type_, presence, **extra):
    # R48 §2.1: every column declares a role. Inferred here from the same two conventions the
    # registry's own map rests on, because a test fixture's columns are all ordinary shapes.
    role = ("coordinate" if name.endswith("_tick")
            else "identifier" if name.endswith("_id")
            else extra.pop("role", "data"))
    return {"name": name, "type": type_, "presence": presence, "role": role,
            "description": name, **extra}


def _registry():
    """A registry describing exactly the tables the fixture writes."""
    return {
        "registry_version": "0.1.0",
        "semantic_standard_version": "nwb-lake-semantic-v0.1",
        "logical_standard_version": "nwb-lake-logical-v0.1",
        "tables": {
            "core.sessions": {
                "columns": [
                    _col("session_id", "string", "required"),
                    _col("subject_id", "string", "required"),
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
                            "SELECT session_id FROM core_sessions WHERE session_id NOT IN "
                            "(SELECT session_id FROM manifest_sessions)"
                        ),
                    }
                ],
            },
            "core.trials": {
                "columns": [
                    _col("session_id", "string", "required"),
                    _col("trial_id", "string", "required"),
                    _col("start_tick", "int64", "required"),
                    _col("stop_tick", "int64", "required"),
                    _col("clock_id", "string", "required"),
                ],
                "primary_key": ["session_id", "trial_id"],
                "references": [
                    {
                        "columns": ["session_id"],
                        "resource": "core.sessions",
                        "resource_columns": ["session_id"],
                    }
                ],
                "sort": ["session_id", "trial_id"],
                "rules": [
                    {
                        "id": "core.trials.interval_valid",
                        "level": "error",
                        "message": "stop_tick precedes start_tick",
                        "sql": "SELECT session_id, trial_id FROM core_trials WHERE stop_tick < start_tick",
                    }
                ],
            },
            "core.units": {
                "columns": [
                    _col("session_id", "string", "required"),
                    _col("unit_id", "string", "required"),
                    _col("sorting_run_id", "string", "required"),
                    _col("curation_id", "string", "required"),
                    _col("quality_label", "string", "nullable", enum=["sua", "mua", "noise"]),
                ],
                "primary_key": ["session_id", "unit_id", "sorting_run_id", "curation_id"],
                "references": [],
                "sort": ["session_id", "unit_id"],
                "rules": [],
            },
            "core.events": {
                "columns": [
                    _col("session_id", "string", "required"),
                    _col("event_id", "string", "required"),
                    _col("event_type", "string", "required", vocabulary="open"),
                    _col("t_tick", "int64", "required"),
                    _col("clock_id", "string", "required"),
                ],
                "primary_key": ["session_id", "event_id"],
                "references": [],
                "sort": ["session_id", "event_id"],
                "rules": [],
            },
            "core.spike_events": {
                "columns": [
                    _col("session_id", "string", "required"),
                    _col("unit_id", "string", "required"),
                    _col("sorting_run_id", "string", "required"),
                    _col("curation_id", "string", "required"),
                    _col("t_tick", "int64", "required"),
                    _col("clock_id", "string", "required"),
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

    sessions = pa.table(
        {
            "session_id": pa.array(["s001"]),
            "subject_id": pa.array(["m001"]),
            "session_start_time": pa.array([1_756_000_000_000_000], type=TS),
        }
    )
    trials = pa.table(
        {
            "session_id": pa.array(["s001", "s001"]),
            "trial_id": pa.array(["trial_0001", "trial_0002"]),
            "start_tick": pa.array([1000, 6000], type=pa.int64()),
            "stop_tick": pa.array([5000, 10000], type=pa.int64()),
            "clock_id": pa.array(["behavior_s001"] * 2),
        }
    )
    units = pa.table(
        {
            "session_id": pa.array(["s001", "s001"]),
            "unit_id": pa.array(["unit_001", "unit_002"]),
            "sorting_run_id": pa.array(["sort_001"] * 2),
            "curation_id": pa.array(["cur_001"] * 2),
            "quality_label": pa.array(["sua", "mua"]),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array(["s001"] * 3),
            "event_id": pa.array(["ev_1", "ev_2", "ev_3"]),
            "event_type": pa.array(["stimulus_onset", "reward", "stimulus_onset"]),
            "t_tick": pa.array([1200, 4200, 6200], type=pa.int64()),
            "clock_id": pa.array(["behavior_s001"] * 3),
        }
    )
    spike_events = pa.table(
        {
            "session_id": pa.array(["s001"] * 5),
            "unit_id": pa.array(["unit_001"] * 3 + ["unit_002"] * 2),
            "sorting_run_id": pa.array(["sort_001"] * 5),
            "curation_id": pa.array(["cur_001"] * 5),
            "t_tick": pa.array([30000, 39000, 48000, 45000, 66000], type=pa.int64()),
            "clock_id": pa.array(["imec_ap_s001"] * 5),
        }
    )
    resources = [
        _resource("core.sessions", _write(root, "sessions", sessions)),
        _resource("core.trials", _write(root, "trials", trials)),
        _resource("core.units", _write(root, "units", units)),
        _resource("core.events", _write(root, "events", events)),
        _resource("core.spike_events", _write(root, "spike_events", spike_events)),
    ]

    (root / "schemas").mkdir()
    (root / "schemas" / "logical_schemas.json").write_text(json.dumps(_registry(), indent=2))

    (root / "nwb.packet.json").write_text(
        json.dumps(
            {
                "packet_id": "session_001",
                "packet_version": "0.1.0",
                "profile_id": "nwb-lake-portable-v0.1",
                "semantic_standard_version": "nwb-lake-semantic-v0.1",
                "logical_standard_version": "nwb-lake-logical-v0.1",
                "registry_version": "0.1.0",
                "created_at": "2026-08-26T00:00:00Z",
                "sessions": ["s001"],
                "required_codecs": [],
                "resources": resources,
                "validation": {
                    "status": "passed",
                    "validated_at": "2026-08-26T00:00:00Z",
                    "validator_name": "nwb_lake_validate",
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
    manifest = json.loads((root / "nwb.packet.json").read_text())
    by_id = {r["resource_id"]: r for r in manifest["resources"]}

    sessions = pa.table(
        {
            "session_id": pa.array(["s001"]),
            "subject_id": pa.array(["m001"]),
            "session_start_time": pa.array([1_756_000_000_000_000], type=pa.timestamp("us", tz="UTC")),
            "reference_clock_id": pa.array(["harp"]),
            # Probe tick 0, which is where the probe clock's observation window begins and so
            # what R39 §2.1 makes the origin. It lands on a whole harp second by construction,
            # so a derived second is exact and a test can say what it should be.
            "t_zero_tick": pa.array([1_000_000], type=pa.int64()),
        }
    )
    clocks = pa.table(
        {
            "clock_id": pa.array(["harp", "probe"]),
            "session_id": pa.array(["s001"] * 2),
            "tick_rate_num": pa.array([31_250, 30_000], type=pa.int64()),
            "tick_rate_den": pa.array([1, 1], type=pa.int64()),
            "parent_clock_id": pa.array([None, "harp"]),
        }
    )
    # Probe tick 0 is harp tick 1,000,000, and the probe runs at 30 kHz against harp's 31,250.
    n = 8
    anchors = pa.table(
        {
            "clock_id": pa.array(["probe"] * n),
            "anchor_index": pa.array(list(range(n)), type=pa.int64()),
            "t_tick": pa.array([i * 30_000 for i in range(n)], type=pa.int64()),
            "parent_tick": pa.array([1_000_000 + i * 31_250 for i in range(n)], type=pa.int64()),
        }
    )
    spikes = pa.table(
        {
            "session_id": pa.array(["s001"] * 3),
            "unit_id": pa.array(["unit_001", "unit_001", "unit_003"]),
            "sorting_run_id": pa.array(["sort_001"] * 3),
            "curation_id": pa.array(["cur_001"] * 3),
            "t_tick": pa.array([30_000, 60_000, 90_000], type=pa.int64()),
            "clock_id": pa.array(["probe", "probe", "harp"]),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array(["s001"]),
            "event_id": pa.array(["ev_1"]),
            "event_type": pa.array(["go_cue"]),
            "t_tick": pa.array([1_200_000], type=pa.int64()),
            "clock_id": pa.array(["harp"]),
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
    (root / "nwb.packet.json").write_text(json.dumps(manifest, indent=2))
    return root

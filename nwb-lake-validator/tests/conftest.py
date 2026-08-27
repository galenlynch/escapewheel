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
    return {"name": name, "type": type_, "presence": presence, "description": name, **extra}


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

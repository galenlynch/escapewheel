import gzip
import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_validator.stores import digest

TS = pa.timestamp("us", tz="UTC")
METADATA_DESCRIPTION = (
    "What the source stated about this row that the standard does not model, carried "
    "in the source's own vocabulary and read by no rule."
)


def _metadata():
    return _col("metadata", "json_string", "optional", description=METADATA_DESCRIPTION)


def install_registry(root, document, *, role=None, path=None, name=None, body=None):
    """Store a registry as the portable profile does and bind it in the packet's manifest.

    The descriptor is rewritten to match, so a test that edits a registry exercises the edit
    rather than a digest mismatch. `name` binds it under another registry ID, and `body` stores
    those bytes in place of the serialized document.
    """
    registry_id = name or document["registry_id"]
    body = json.dumps(document, indent=2).encode() if body is None else body
    relative = path or f"registries/{registry_id}/{document['registry_version']}.json.gz"
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_bytes(gzip.compress(body, mtime=0))
    descriptor = {
        "role": role or ("core" if registry_id == "core" else "extension"),
        "version": document["registry_version"],
        "path": relative,
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    manifest_path = root / "packet.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        manifest.setdefault("registries", {})[registry_id] = descriptor
        manifest_path.write_text(json.dumps(manifest, indent=2))
    return descriptor


def read_registry(root, registry_id="core"):
    """The registry a packet binds under `registry_id`, decoded."""
    manifest = json.loads((root / "packet.json").read_text())
    return json.loads(gzip.decompress((root / manifest["registries"][registry_id]["path"]).read_bytes()))


def _write(root, name, table):
    path = root / "tables" / "core"
    path.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path / f"{name}.parquet", compression="zstd")
    return f"tables/core/{name}.parquet"


def owned_digest(root, uri, algorithm="sha256"):
    """The `digest` a writer records for a packet-owned resource under `root` (Part 04 §4.3)."""
    return {"algorithm": algorithm, "value": digest(str(root / uri), algorithm)}


#: A well-formed digest for an entry whose bytes a test never reads.
UNREAD_DIGEST = {"algorithm": "sha256", "value": "0" * 64}


def _resource(resource_id, uri, **extra):
    entry = {
        "resource_id": resource_id,
        "declaration_id": resource_id,
        "uri": uri,
        "validation_state": "passed",
    }
    entry.update(extra)
    return entry


def _col(name, type_, presence, **extra):
    # R48 §2.1: every column declares a role. Inferred here from the same two conventions the
    # registry's own map rests on, because a test fixture's columns are all ordinary shapes.
    role = (
        "coordinate" if name.endswith("_tick") else "identifier" if name.endswith("_id") else extra.pop("role", "data")
    )
    entry = {"name": name, "type": type_, "presence": presence, "role": role, "description": name, **extra}
    if role == "identifier":
        # R53 §2.3: required exactly where the role is identifier. `assigned` unless the fixture
        # says otherwise, since a fixture invents its own ids rather than carrying anyone's.
        entry.setdefault("identity", "assigned")
    if type_ == "string" and role != "discriminator":
        # Part 02 §9.3: required of every string column but a discriminator. `closed` where the
        # fixture declares an `enum`, and otherwise `free` -- a fixture's strings are names and
        # labels, and one meaning to be a vocabulary says so.
        entry.setdefault("vocabulary", "closed" if "enum" in entry else "free")
    if type_ in {"float32", "float64"}:
        entry.setdefault("finite", True)
    return entry


def _registry():
    """A registry describing exactly the tables the fixture writes."""
    document = {
        "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
        "registry_id": "core",
        "registry_version": "0.1.0",
        "semantic_standard_version": "escapewheel-semantic-v0.1",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.2",
        "tables": {
            "core.sessions": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("session_name", "string", "required"),
                    _col("subject_id", "int32", "required"),
                    _col("session_start_time", "timestamp", "required"),
                    _metadata(),
                ],
                "primary_key": ["session_id"],
                "amendment_groups": [["session_id"]],
                "references": [],
                "rules": [],
            },
            "core.intervals": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("interval_id", "int32", "required"),
                    _col("interval_name", "string", "optional"),
                    _col("start_tick", "int64", "required", clock_from="clock_id"),
                    _col("stop_tick", "int64", "required", clock_from="clock_id"),
                    _col("clock_id", "int32", "required"),
                    _metadata(),
                ],
                "primary_key": ["session_id", "interval_id"],
                "amendment_groups": [["session_id", "interval_id"]],
                "references": [
                    {
                        "columns": ["session_id"],
                        "resource": "core.sessions",
                        "resource_columns": ["session_id"],
                    },
                    {"columns": ["clock_id"], "resource": "core.clocks", "resource_columns": ["clock_id"]},
                ],
                "rules": [
                    {
                        "id": "core.intervals.interval_valid",
                        "level": "error",
                        "message": "stop_tick precedes start_tick",
                        "sql": "SELECT session_id, interval_id FROM core.intervals WHERE stop_tick < start_tick",
                    }
                ],
            },
            "core.units": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("unit_id", "int32", "required"),
                    _col("unit_name", "string", "optional"),
                    _col("sorting_run_id", "int32", "required"),
                    _col("curation_id", "int32", "required"),
                    _col("quality_label", "string", "nullable", enum=["sua", "mua", "noise"]),
                    _col("clock_id", "int32", "required"),
                    _metadata(),
                ],
                "primary_key": ["unit_id"],
                "amendment_groups": [["unit_id"]],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {"columns": ["clock_id"], "resource": "core.clocks", "resource_columns": ["clock_id"]},
                ],
                "rules": [],
            },
            "core.events": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("event_id", "int32", "required"),
                    _col("event_name", "string", "optional"),
                    _col("event_type", "string", "required", vocabulary="open"),
                    _col("t_tick", "int64", "required", clock_from="clock_id"),
                    _col("clock_id", "int32", "required"),
                    _metadata(),
                ],
                "primary_key": ["session_id", "event_id"],
                "amendment_groups": [["session_id", "event_id"]],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
                    {"columns": ["clock_id"], "resource": "core.clocks", "resource_columns": ["clock_id"]},
                ],
                "rules": [],
            },
            "core.spike_events": {
                "columns": [
                    _col("session_id", "int32", "required"),
                    _col("unit_id", "int32", "required"),
                    _col("t_tick", "int64", "required", clock_from="core.units.clock_id"),
                ],
                "primary_key": ["session_id", "unit_id", "t_tick"],
                "amendment_groups": [["session_id", "unit_id", "t_tick"]],
                "references": [
                    {
                        "columns": ["session_id"],
                        "resource": "core.sessions",
                        "resource_columns": ["session_id"],
                    },
                    {
                        "columns": ["unit_id"],
                        "resource": "core.units",
                        "resource_columns": ["unit_id"],
                    },
                ],
                "rules": [],
            },
            "core.clocks": {
                "columns": [
                    _col("clock_id", "int32", "required"),
                    _col("clock_name", "string", "required"),
                    _metadata(),
                ],
                "primary_key": ["clock_id"],
                "amendment_groups": [["clock_id"]],
                "references": [],
                "rules": [],
            },
        },
    }
    tables = document.pop("tables")
    document["resources"] = {
        name: {
            "content_class": "core",
            "kind": "table",
            "instances": {
                "mode": "singleton",
                "presence": "required" if name == "core.sessions" else "optional",
            },
            "requires": [],
            "lineage": "optional",
            "table": table,
        }
        for name, table in tables.items()
    }
    return document


@pytest.fixture
def packet_root(tmp_path):
    """A minimal two-table packet: one session, two intervals referencing it."""
    root = tmp_path / "session_001"
    root.mkdir()

    sessions = pa.table(
        {
            "session_id": pa.array([1], type=pa.int32()),
            "session_name": pa.array(["s001"]),
            "subject_id": pa.array([1], type=pa.int32()),
            "session_start_time": pa.array([1_756_000_000_000_000], type=TS),
        }
    )
    intervals = pa.table(
        {
            "session_id": pa.array([1, 1], type=pa.int32()),
            "interval_id": pa.array([1, 2], type=pa.int32()),
            "start_tick": pa.array([1000, 6000], type=pa.int64()),
            "stop_tick": pa.array([5000, 10000], type=pa.int64()),
            "clock_id": pa.array([1, 1], type=pa.int32()),
        }
    )
    units = pa.table(
        {
            "session_id": pa.array([1, 1], type=pa.int32()),
            "unit_id": pa.array([1, 2], type=pa.int32()),
            "sorting_run_id": pa.array([1, 1], type=pa.int32()),
            "curation_id": pa.array([1, 1], type=pa.int32()),
            "quality_label": pa.array(["sua", "mua"]),
            "clock_id": pa.array([2, 2], type=pa.int32()),
        }
    )
    events = pa.table(
        {
            "session_id": pa.array([1, 1, 1], type=pa.int32()),
            "event_id": pa.array([1, 2, 3], type=pa.int32()),
            "event_type": pa.array(["stimulus_onset", "reward", "stimulus_onset"]),
            "t_tick": pa.array([1200, 4200, 6200], type=pa.int64()),
            "clock_id": pa.array([1, 1, 1], type=pa.int32()),
        }
    )
    spike_events = pa.table(
        {
            "session_id": pa.array([1, 1, 1, 1, 1], type=pa.int32()),
            "unit_id": pa.array([1, 1, 1, 2, 2], type=pa.int32()),
            "t_tick": pa.array([30000, 39000, 48000, 45000, 66000], type=pa.int64()),
        }
    )
    clocks = pa.table(
        {
            "clock_id": pa.array([1, 2], type=pa.int32()),
            "clock_name": pa.array(["behavior", "probe"]),
            "metadata": pa.array([None, None], type=pa.string()),
        }
    )
    resources = [
        _resource("core.sessions", uri := _write(root, "sessions", sessions), digest=owned_digest(root, uri)),
        _resource("core.intervals", uri := _write(root, "intervals", intervals), digest=owned_digest(root, uri)),
        _resource("core.units", uri := _write(root, "units", units), digest=owned_digest(root, uri)),
        _resource("core.events", uri := _write(root, "events", events), digest=owned_digest(root, uri)),
        _resource(
            "core.spike_events", uri := _write(root, "spike_events", spike_events), digest=owned_digest(root, uri)
        ),
        _resource("core.clocks", uri := _write(root, "clocks", clocks), digest=owned_digest(root, uri)),
    ]

    core = install_registry(root, _registry())
    (root / "packet.json").write_text(
        json.dumps(
            {
                "packet_id": "session_001",
                "packet_version": "0.1.0",
                "profile_id": "escapewheel-portable-v0.1",
                "semantic_standard_version": "escapewheel-semantic-v0.1",
                "logical_standard_version": "escapewheel-logical-v0.1",
                "registries": {"core": core},
                "created_at": "2026-08-26T00:00:00Z",
                "sessions": ["s001"],
                "resources": resources,
                "validation": {
                    "status": "passed",
                    "validated_at": "2026-08-26T00:00:00Z",
                    "validator_name": "escapewheel_validator",
                    "validator_version": "0.1.0",
                },
            },
            indent=2,
        )
    )
    return root

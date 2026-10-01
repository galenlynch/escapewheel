"""The small packet the reader's and the validator's suites build, and the registry it binds.

The registry is the core registry cut down to the columns a suite names, each declared as core
declares it, so a suite's fixture cannot drift from the standard. Each suite puts this directory
on its import path (`pythonpath` in its pytest configuration).
"""

import copy
import gzip
import hashlib
import json
from functools import cache
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

CORE_REGISTRY = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"

#: The fixture registry's own version: a cut-down document is not the release it was cut from.
REGISTRY_VERSION = "0.1.0"

TS = pa.timestamp("us", tz="UTC")

#: An identifier is an integer (Part 02 §5.3). The values are distinct across kinds so a test
#: that confuses two of them fails rather than passing by coincidence.
SESSION = 1
SUBJECT = 7
CLOCK_BEHAVIOUR = 3
CLOCK_PROBE = 4
TRIALS = (0, 1)  # a packet numbers its intervals from 0 (Part 02 §12.9)
UNITS = (11, 12, 13)  # not dense from 0 as core numbers them: no suite keeps that rule
SORTING_RUN = 5
CURATION = 6
STREAMS = (0, 1)

#: The session's name, which is what the manifest lists and what a stable cross-packet
#: reference uses (Part 01 §2.1).
SESSION_NAME = "s001"

#: A well-formed digest for an entry whose bytes a test never reads.
UNREAD_DIGEST = {"algorithm": "sha256", "value": "0" * 64}

#: Column properties naming another column, as `column` or `resource.column`.
_COLUMN_LINKS = ("clock_from", "unit_from", "discriminates", "discriminates_via")


@cache
def _core():
    return json.loads(CORE_REGISTRY.read_text())


def core_table(resource_id, columns, *, rules=(), resources=None):
    """Core's declaration of a table, cut down to `columns` and to the rules named in `rules`.

    A reference survives where its columns do and its target is in `resources`, a mapping of
    resource ID to kept columns that defaults to this table alone. An amendment group survives
    where all its columns do. A kept column naming a dropped one is an error, as is a dropped
    key column.
    """
    resources = {resource_id: columns} if resources is None else resources
    declaration = copy.deepcopy(_core()["resources"][resource_id])
    table = declaration["table"]
    kept = set(columns)
    declared = {column["name"] for column in table["columns"]}
    if kept - declared:
        raise KeyError(f"{resource_id} declares no {sorted(kept - declared)}")
    if not set(table["primary_key"]) <= kept:
        raise KeyError(f"{resource_id}: the key {table['primary_key']} is not among the kept columns")
    table["columns"] = [column for column in table["columns"] if column["name"] in kept]
    for column in table["columns"]:
        links = [column[key] for key in _COLUMN_LINKS if key in column] + column.get("determined_by", [])
        for link in links:
            owner, _, name = link.rpartition(".")
            if name not in resources.get(owner or resource_id, ()):
                raise KeyError(f"{resource_id}.{column['name']} names {link}, which is not kept")
    table["references"] = [
        reference
        for reference in table["references"]
        if set(reference["columns"]) <= kept
        and set(reference["resource_columns"]) <= set(resources.get(reference["resource"], ()))
    ]
    table["amendment_groups"] = [group for group in table["amendment_groups"] if set(group) <= kept]
    table["rules"] = [rule for rule in table["rules"] if rule["id"] in rules]
    return declaration


def core_registry(columns, *, rules=()):
    """The core registry cut down to the resources and columns of `columns`.

    `columns` maps a resource ID to the names of the columns to keep, and `rules` names the
    rules to keep; see `core_table` for what else survives.
    """
    document = {key: value for key, value in _core().items() if key != "resources"}
    document["registry_version"] = REGISTRY_VERSION
    document["resources"] = {
        resource_id: core_table(resource_id, names, rules=rules, resources=columns)
        for resource_id, names in columns.items()
    }
    found = {rule["id"] for declaration in document["resources"].values() for rule in declaration["table"]["rules"]}
    if set(rules) - found:
        raise KeyError(f"core declares no rule {sorted(set(rules) - found)} on the kept tables")
    return document


def column(name, type_, presence, **extra):
    """A column declaration for a table a test declares itself, with the properties Part 02 §8 requires."""
    role = (
        "coordinate" if name.endswith("_tick") else "identifier" if name.endswith("_id") else extra.pop("role", "data")
    )
    entry = {"name": name, "type": type_, "presence": presence, "role": role, "description": name, **extra}
    if role == "identifier":
        entry.setdefault("identity", "assigned")
    if type_ == "string" and role != "discriminator":
        entry.setdefault("vocabulary", "closed" if "enum" in entry else "free")
    if type_ in {"float32", "float64"}:
        entry.setdefault("finite", True)
    return entry


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


def write_table(root, name, table, namespace="core"):
    """Write `table` as the resource `namespace.name` and return its URI."""
    path = root / "tables" / namespace
    path.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path / f"{name}.parquet", compression="zstd")
    return f"tables/{namespace}/{name}.parquet"


def resource_entry(resource_id, uri, **extra):
    """A manifest entry for a resource whose declaration has its own ID."""
    return {
        "resource_id": resource_id,
        "declaration_id": resource_id,
        "uri": uri,
        "validation_state": "passed",
        **extra,
    }


def tables():
    """The packet's rows by resource ID: one session, two clocks, two trials, two units."""
    i32, i64 = pa.int32(), pa.int64()
    return {
        "core.sessions": pa.table(
            {
                "session_id": pa.array([SESSION], type=i32),
                "session_name": pa.array([SESSION_NAME]),
                "subject_id": pa.array([SUBJECT], type=i32),
                "session_start_time": pa.array([1_756_000_000_000_000], type=TS),
            }
        ),
        "core.intervals": pa.table(
            {
                "session_id": pa.array([SESSION] * 2, type=i32),
                "interval_id": pa.array(list(TRIALS), type=i32),
                "interval_name": pa.array([f"{SESSION_NAME}/task.trials/{t + 1}" for t in TRIALS]),
                "interval_kind": pa.array(["task.trials"] * 2),
                "local_interval_label": pa.array([str(t + 1) for t in TRIALS]),
                "start_tick": pa.array([1000, 6000], type=i64),
                "stop_tick": pa.array([5000, 10000], type=i64),
                "clock_id": pa.array([CLOCK_BEHAVIOUR] * 2, type=i32),
            }
        ),
        "core.units": pa.table(
            {
                "session_id": pa.array([SESSION] * 2, type=i32),
                "unit_id": pa.array(list(UNITS[:2]), type=i32),
                "unit_name": pa.array([str(unit) for unit in UNITS[:2]]),
                "sorting_run_id": pa.array([SORTING_RUN] * 2, type=i32),
                "curation_id": pa.array([CURATION] * 2, type=i32),
                "quality_label": pa.array(["sua", "mua"]),
                "clock_id": pa.array([CLOCK_PROBE] * 2, type=i32),
            }
        ),
        # An event is a tick on a stream; the kind and the clock are the stream's (Part 01 §3.11).
        "core.event_streams": pa.table(
            {
                "event_stream_id": pa.array(list(STREAMS), type=i32),
                "session_id": pa.array([SESSION] * 2, type=i32),
                "event_stream_name": pa.array(["stimulus", "reward"]),
                "event_type": pa.array(["stimulus_onset", "reward"]),
                "clock_id": pa.array([CLOCK_BEHAVIOUR] * 2, type=i32),
            }
        ),
        "core.events": pa.table(
            {
                "session_id": pa.array([SESSION] * 3, type=i32),
                "stream_id": pa.array([STREAMS[0], STREAMS[0], STREAMS[1]], type=i32),
                "t_tick": pa.array([1200, 6200, 4200], type=i64),
            }
        ),
        "core.spike_events": pa.table(
            {
                "session_id": pa.array([SESSION] * 5, type=i32),
                "unit_id": pa.array([UNITS[0]] * 3 + [UNITS[1]] * 2, type=i32),
                "t_tick": pa.array([30000, 39000, 48000, 45000, 66000], type=i64),
            }
        ),
        "core.clocks": pa.table(
            {
                "session_id": pa.array([SESSION] * 2, type=i32),
                "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], type=i32),
                "clock_name": pa.array(["behaviour", "probe"]),
                "metadata": pa.array([None, None], type=pa.string()),
            }
        ),
    }


def write_packet(root, columns, *, rules=(), unwritten=(), digest=None):
    """Write the packet under `root`, binding `core_registry(columns, rules=rules)`.

    A table is written with the columns `columns` keeps for it, unless its resource is in
    `unwritten`, which leaves it declared and absent. `digest(root, uri)` supplies each entry's
    `digest` member; without it the entries carry none.
    """
    root.mkdir()
    resources = []
    for resource_id, table in tables().items():
        if resource_id not in columns or resource_id in unwritten:
            continue
        kept = table.select([name for name in table.column_names if name in columns[resource_id]])
        uri = write_table(root, resource_id.partition(".")[2], kept)
        resources.append(resource_entry(resource_id, uri, **({"digest": digest(root, uri)} if digest else {})))
    manifest = {
        "packet_id": "session_001",
        "packet_version": "0.1.0",
        "profile_id": "escapewheel-portable-v0.1",
        "semantic_standard_version": "escapewheel-semantic-v0.1",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "registries": {"core": install_registry(root, core_registry(columns, rules=rules))},
        "created_at": "2026-08-26T00:00:00Z",
        "sessions": [SESSION_NAME],
        "resources": resources,
        "validation": {
            "status": "passed",
            "validated_at": "2026-08-26T00:00:00Z",
            "validator_name": "escapewheel_validator",
            "validator_version": "0.1.0",
        },
    }
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return root

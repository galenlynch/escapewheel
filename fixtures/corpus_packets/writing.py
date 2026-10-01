"""Writing a packet in the portable layout, with the digests and listings its manifest records."""

import gzip
import hashlib
import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq

from .numbering import Numbering
from .registry import EXTENSION, REGISTRY


def crc(polynomial: int, bits: int, data: bytes) -> int:
    """A reflected CRC with all-ones initial value and final XOR, bit by bit (Part 04 §4.3).

    Written from the polynomial rather than taken from the implementation under test, so the
    corpus pins the form a validator must reproduce.
    """
    mask = (1 << bits) - 1
    register = mask
    for byte in data:
        register ^= byte
        for _ in range(8):
            register = (register >> 1) ^ polynomial if register & 1 else register >> 1
    return register ^ mask


def digest(algorithm: str, data: bytes) -> str:
    """One object's Part 04 §4.3 value: lowercase hexadecimal of the algorithm's width."""
    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    if algorithm == "crc64nvme":
        return f"{crc(0x9A6C9329AC4BC9B5, 64, data):016x}"
    if algorithm == "crc32c":
        return f"{crc(0x82F63B78, 32, data):08x}"
    if algorithm == "crc32":
        return f"{crc(0xEDB88320, 32, data):08x}"
    raise ValueError(algorithm)


def write_packet(
    out: Path,
    tables: dict[str, list[dict]],
    *,
    recast: dict | None = None,
    unsorted: frozenset = frozenset(),
    algorithm: str = "sha256",
    extensions: tuple = (),
    numbers: dict[str, dict[str, int]] | None = None,
) -> Numbering:
    """Write a packet in 03's portable layout, and return the numbering of its names.

    `recast` maps a resource to a function from its Arrow table to the one written, for
    variants that must violate the registry's own schema; `unsorted` names resources
    written in insertion order, for variants that must violate Part 03 §5.3. Every resource
    records its `digest` under `algorithm`. `extensions` are registry documents bound beside
    core and `dynamic_foraging`. `numbers` replaces the numbering of each identifier it names,
    for variants that must number one otherwise."""
    if out.exists():
        shutil.rmtree(out)
    documents = (REGISTRY, EXTENSION, *extensions)
    numbering = Numbering(*documents)
    numbering.preassign(tables)
    numbering.keys.update({kind: dict(names) for kind, names in (numbers or {}).items()})
    (out / "tables" / "core").mkdir(parents=True)

    resources = []
    for resource, rows in tables.items():
        t = numbering.table(resource, rows, numbering.paired_readers(tables, resource))
        if resource not in unsorted:
            t = numbering.sort_table(resource, t)
        if resource in (recast or {}):
            t = recast[resource](t)
        namespace, name = resource.split(".", 1)
        rel = f"tables/{namespace}/{name}.parquet"
        (out / "tables" / namespace).mkdir(exist_ok=True)
        pq.write_table(t, out / rel, compression="zstd")
        resources.append(
            {
                "resource_id": resource,
                "declaration_id": resource,
                "uri": rel,
                "validation_state": "not_run",
                "digest": {
                    "algorithm": algorithm,
                    "value": digest(algorithm, (out / rel).read_bytes()),
                },
            }
        )

    registries = {document["registry_id"]: bind(out, document) for document in documents}

    sessions = sorted({r["session_id"] for r in tables["core.sessions"]})
    (out / "packet.json").write_text(
        json.dumps(
            {
                "packet_id": out.name,
                "packet_version": "0.1.0",
                "profile_id": "escapewheel-portable-v0.1",
                "semantic_standard_version": REGISTRY["semantic_standard_version"],
                "logical_standard_version": REGISTRY["logical_standard_version"],
                "registries": registries,
                "created_at": "2026-08-26T00:00:00Z",
                "description": "Phase 0 synthetic fixture, single session (R1 §6).",
                "sessions": sessions,
                "resources": resources,
                "validation": {
                    "status": "not_run",
                    "validated_at": "2026-08-26T00:00:00Z",
                    "validator_name": "escapewheel_validator",
                    "validator_version": "0.1.0",
                },
            },
            indent=2,
        )
        + "\n"
    )
    return numbering


def bind(out, document):
    """Store a registry as Part 03 §3.3 requires and return its manifest descriptor."""
    body = (json.dumps(document, indent=2) + "\n").encode()
    relative = f"registries/{document['registry_id']}/{document['registry_version']}.json.gz"
    (out / relative).parent.mkdir(parents=True, exist_ok=True)
    (out / relative).write_bytes(gzip.compress(body, mtime=0))
    return {
        "role": "extension" if "extension_id" in document else "core",
        "version": document["registry_version"],
        "path": relative,
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def edit_manifest(out: Path, change) -> None:
    manifest = json.loads((out / "packet.json").read_text())
    change(manifest)
    (out / "packet.json").write_text(json.dumps(manifest, indent=2) + "\n")


def listing(rows) -> bytes:
    """Part 04 §4.3's listing of `(key, size_bytes, digest)` rows: sorted by the key's UTF-8, and
    RFC 8785's JSON, which `ensure_ascii=False` matches and whose keys are therefore raw UTF-8."""
    ordered = sorted((list(row) for row in rows), key=lambda row: row[0].encode())
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

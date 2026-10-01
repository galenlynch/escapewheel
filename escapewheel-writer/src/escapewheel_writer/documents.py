"""The documents a commit writes beside a packet's resources, and the values they state (Part 04).

- :func:`manifest` -- a new packet's manifest.
- :func:`with_lineage` -- each derived resource's `derived_from` on its manifest entry.
- :func:`sources_document` -- the default resolution document for the sources referenced.
- :func:`store_registries` -- the bound registries, stored, with their descriptors.
- :func:`retain` -- the retained copy of each manifest an amendment supersedes or publishes.
- :func:`first_version`, :func:`bump`, :func:`writer_version`, :func:`sha256_of` -- a packet's
  first and next version, this writer's version, and a resource's digest.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from escapewheel_reader import check_sources
from escapewheel_reader.location import SOURCES_VERSION
from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME
from escapewheel_reader.profile import PROFILE_ID
from escapewheel_reader.registries import gunzip_member as gzip_member
from escapewheel_validator import Report

from .bindings import ExternalArray, ExternalMedia
from .errors import UsageError, UsageFault
from .layout import REGISTRIES, retained


def writer_version() -> str:
    """Read this package's version without importing it at module scope."""
    from . import __version__

    return __version__


#: What a manifest's `validation.status` and a resource's `validation_state` may say (Part 04 §4.1, §9).
VALIDATION_PASSED = "passed"
VALIDATION_FAILED = "failed"
VALIDATION_NOT_RUN = "not_run"


def first_version(packet_id: str, replaces: Sequence[Mapping[str, str]]) -> str:
    """Return a new packet's version: a major version above every packet it replaces of its id (Part 05 §9.3)."""
    majors = [int(item["packet_version"].split(".", 1)[0]) for item in replaces if item["packet_id"] == packet_id]
    return f"{max(majors) + 1}.0.0" if majors else "0.1.0"


def bump(version: str) -> str:
    """Return the next packet version.

    Patch level, so a packet under development stays inside one minor series while the
    structure moves. Part 05 §15.1 requires only that the new version keep the major version and
    sort strictly after the superseded one, so nothing here rests on the choice.
    """
    major, minor, patch, *_ = (*version.split("."), "0", "0", "0")
    return f"{int(major)}.{int(minor)}.{int(patch) + 1}"


def sha256_of(path: Path) -> dict[str, str]:
    """Part 04 §4.3: what the packet says its own bytes are, under SHA-256.

    Required of every packet-owned resource, because the promise it makes checkable is not optional
    either: Part 03 §8.1 declares these bytes immutable and Part 05 §15.4 spends that, bounding
    revalidation after an amendment to what the amendment wrote. Costs 0.5% of a build -- the bytes
    were just written, so they are in page cache and hash at ~2 GB/s.

    A prefix goes through that section's listing, a single file is its own bytes; `digest` already
    distinguishes them.
    """
    from escapewheel_validator.stores import digest

    return {"algorithm": "sha256", "value": digest(str(path))}


def manifest(
    entries: Sequence[Mapping[str, Any]],
    registries: Mapping[str, Mapping[str, str]],
    report: Report | None,
    *,
    packet_id: str,
    core: Mapping[str, Any],
    sessions: Sequence[Mapping[str, Any]],
    retention: Mapping[str, Any],
    description: str | None,
    replaces: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Build a new packet's manifest for these resources, binding the registries `store_registries` wrote.

    `sessions` is the packet's `core.sessions` records and `core` its core registry.
    """
    session_ids = sorted({r["session_id"] for r in sessions if "session_id" in r})
    now = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    validation = {
        "status": VALIDATION_NOT_RUN if report is None else (VALIDATION_PASSED if report.passed else VALIDATION_FAILED),
        "validated_at": now,
        "validator_name": "escapewheel_validator",
        "validator_version": writer_version(),
    }
    document: dict[str, Any] = {
        "packet_id": packet_id,
        "packet_version": first_version(packet_id, replaces),
        "profile_id": PROFILE_ID,
        "semantic_standard_version": core["semantic_standard_version"],
        "logical_standard_version": core["logical_standard_version"],
        "registries": {name: dict(descriptor) for name, descriptor in registries.items()},
        "created_at": now,
        "sessions": session_ids,
        "resources": [dict(e) for e in entries],
        # Part 05 §15.5: declared rather than left to a default, because `prune` reads it and a
        # packet that says nothing makes the operator's policy invisible to the operation.
        "retention": dict(retention),
        "validation": validation,
    }
    if description is not None:
        document["description"] = description
    if replaces:
        document["replaces"] = [dict(item) for item in replaces]
    return document


def with_lineage(entries: list[dict[str, Any]], derived: Mapping[str, Sequence[str]]) -> list[dict[str, Any]]:
    """Put each derived resource's `derived_from` on its manifest entry."""
    if missing := sorted(set(derived) - {e["resource_id"] for e in entries}):
        raise UsageError(
            f"lineage was recorded for {missing}, which this packet does not carry",
            code=UsageFault.LINEAGE_UNSTAGED,
            where=", ".join(missing),
        )
    for entry in entries:
        if lineage := derived.get(entry["resource_id"]):
            entry["derived_from"] = list(lineage)
    return entries


def sources_document(
    packet_id: str, sources: Mapping[str, str], referenced: Iterable[ExternalArray | ExternalMedia]
) -> dict[str, Any] | None:
    """Return Part 04 §5.5's default resolution document, or None where no resource names a source.

    None rather than an empty document, since a document locating nothing is worse than
    none -- it would answer a lookup the caller meant to answer itself. Written before the
    manifest, because Part 05 §6 makes publishing the manifest what makes a commit visible.

    Raises
    ------
    UsageError
        If the document would not satisfy its schema, which a writer MUST NOT write (Part 04
        §5.5). Raised before anything is promoted.
    """
    located = {
        entry.source: {"uri": sources[entry.source]}
        for entry in referenced
        if entry.source is not None and entry.source in sources
    }
    if not located:
        return None
    document = {
        "$schema": "https://escapewheel.org/schemas/sources/0.1.0",
        "sources_standard_version": SOURCES_VERSION,
        "description": f"Where {packet_id} read its referenced data. Editable: not a packet resource.",
        "sources": dict(sorted(located.items())),
    }
    if problems := check_sources(document):
        raise UsageError(
            f"the source resolution document would not satisfy its schema: {'; '.join(problems)}",
            code=UsageFault.SOURCES_DOCUMENT,
        )
    return document


def retain(root: Path, superseded: Mapping[str, Any], amended: Mapping[str, Any], amended_body: bytes) -> None:
    """Keep the exact bytes of every manifest a packet has had (Part 05 §15.3).

    A superseded file is only interpretable if the manifest that named it still exists;
    without these, an orphan and a stray are indistinguishable and a recorded `digest` points
    at a state nothing can reconstruct. Exact, because a replacement names a version by the
    SHA-256 of its manifest (Part 04 §3).
    """
    versions = root / MANIFESTS_DIRNAME
    versions.mkdir(exist_ok=True)
    for manifest, body in ((superseded, (root / MANIFEST_FILENAME).read_bytes()), (amended, amended_body)):
        path = versions / retained(manifest)
        # An existing copy is the one an earlier amendment retained, and retained bytes are
        # not rewritten.
        if not path.exists():
            path.write_bytes(body)


def store_registries(
    documents: Iterable[Mapping[str, Any]], root: Path, *, staging: Path | None = None
) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Store core and every extension as Part 03 §3.3 requires, returning their descriptors.

    The digest covers the exact serialized bytes (Part 04 §10). A registry ID and version that
    the packet's current or a retained manifest already binds is reused where the digest
    matches and refused where it differs (Part 05 §15.3), so every manifest keeps naming bytes
    that exist.

    Parameters
    ----------
    documents : iterable of Mapping
        Core and every extension the packet binds.
    root : Path
        Where the registries are bound: the staged packet for a commit, the packet for an
        amendment.
    staging : Path, optional
        For an amendment, where a registry the packet does not yet store is written instead,
        its descriptor pointing there until promotion moves it (Part 05 §6).

    Returns
    -------
    dict
        A descriptor per registry ID, for the manifest's `registries`.
    list of str
        The root-relative final path of each registry written under `staging`.
    """
    recorded: dict[tuple[str, str], Mapping[str, str]] = {}
    for manifest_path in [root / MANIFEST_FILENAME, *sorted((root / MANIFESTS_DIRNAME).glob("*.json"))]:
        if manifest_path.is_file():
            for name, bound in json.loads(manifest_path.read_text()).get("registries", {}).items():
                recorded.setdefault((name, bound["version"]), bound)
    descriptors: dict[str, dict[str, str]] = {}
    added: list[str] = []
    for document in documents:
        registry_id = str(document["registry_id"])
        body = (json.dumps(document, indent=2) + "\n").encode()
        version = str(document["registry_version"])
        digest = hashlib.sha256(body).hexdigest()
        earlier = recorded.get((registry_id, version))
        relative = earlier["path"] if earlier else f"{REGISTRIES}/{registry_id}/{version}.json.gz"
        path = root / relative
        stored = hashlib.sha256(gzip_member(path.read_bytes())).hexdigest() if path.is_file() else None
        bound = relative
        if (earlier is not None and earlier["sha256"] != digest) or stored not in {None, digest}:
            raise UsageError(
                f"this packet already binds a different {registry_id} {version} at {relative}; two digests "
                "under one registry ID and version cannot both be retained (Part 05 §15.3). Bump registry_version.",
                code=UsageFault.REGISTRY_DIGEST_DIFFERS,
                where=relative,
            )
        if stored is None:
            if staging is not None:
                path = staging / relative
                bound = f"{staging.relative_to(root).as_posix()}/{relative}"
                added.append(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(body, mtime=0))
        descriptors[registry_id] = {
            "role": "extension" if "extension_id" in document else "core",
            "version": version,
            "path": bound,
            "sha256": digest,
        }
    return descriptors, added


__all__ = [
    "VALIDATION_NOT_RUN",
    "VALIDATION_PASSED",
    "bump",
    "manifest",
    "retain",
    "sha256_of",
    "sources_document",
    "store_registries",
    "with_lineage",
    "writer_version",
]

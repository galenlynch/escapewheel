"""Verify a committed packet where its bytes now live, and record what was found (Part 04 §5.2).

- :func:`verify` -- record what is true of a packet's external resources, as a new version.
- :data:`LEVELS` -- how much may be established: `size`, `members` or `sha256`.
- :data:`VERIFY_UNREACHABLE`, :data:`VERIFY_RECORDED` -- the checks a finding of :func:`verify` is reported under.

Verifying writes no file and adds no resource: it changes only what the manifest says about the
resources the packet does not own.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from escapewheel_reader import Manifest, Packet
from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME
from escapewheel_validator import CheckEntry, Level, Report, Scope, validate
from escapewheel_validator.errors import StoreUnreachable
from escapewheel_validator.stores import digest, digest_resource, listing

from .errors import NotCommitted, UsageError, UsageFault
from .writer import VALIDATION_PASSED, _bump, _version, retained, semver

#: What to establish, each level including the one before it. `size` lists, `members` also
#: records a prefix's Part 04 §5.4 per-member listing with the entity tag the store handed over,
#: and `sha256` also digests every byte, recording a SHA-256 `digest` and each member's beside it.
#: `members` is the default because it is the strongest thing available for the price of the listing.
LEVELS = ("size", "members", "sha256")

#: A resource's store could not be read, so what the manifest says of it is unchanged.
VERIFY_UNREACHABLE = CheckEntry("verify.unreachable", Level.WARNING, Scope.RESOURCE, named=False)
#: How many external resources were verified, and at what level.
VERIFY_RECORDED = CheckEntry("verify.recorded", Level.INFO, Scope.PACKET, named=False)


def _member_entry(member: Any, digest: str | None) -> dict[str, Any]:
    entry: dict[str, Any] = {"key": member.key, "size_bytes": member.size_bytes}
    if digest is not None:
        entry["digest"] = digest
    if member.store_digest is not None:
        entry["store_digest"] = {"algorithm": member.store_digest.algorithm, "value": member.store_digest.value}
    return entry


def _measure(entry: dict[str, Any], level: str, notes: list[str]) -> bool:
    """Record what the store holds for one external resource. False where it could not be read.

    Below `sha256` a recorded digest is kept, and its member values are carried by key; where the
    listing gained an object no recorded value covers, the digest no longer describes it and goes.
    """
    uri = str(entry.get("uri", ""))
    try:
        digested = digest_resource(uri) if level == "sha256" else None
        found = listing(uri) if digested is None else digested.found
    except StoreUnreachable as exc:
        notes.append(f"{entry['resource_id']}: unchanged, {exc}")
        return False
    entry["size_bytes"] = found.size_bytes
    entry["verified_at"] = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    if digested is not None:
        entry["digest"] = {"algorithm": digested.algorithm, "value": digested.value}
        values: tuple[str | None, ...] = digested.members
    else:
        recorded = {str(m.get("key")): m.get("digest") for m in entry.get("members") or ()}
        values = tuple(recorded.get(m.key) for m in found.members)
        if "digest" in entry and not found.is_single_object and None in values:
            del entry["digest"]
        if "digest" not in entry:
            values = (None,) * len(found.members)
    if level in {"members", "sha256"} and not found.is_single_object:
        entry["members"] = [_member_entry(m, value) for m, value in zip(found.members, values, strict=True)]
    return True


def verify(
    root: str | Path,
    *,
    level: str = "members",
    packet_version: str | None = None,
) -> tuple[Report, dict[str, Any]]:
    """Record what is true about a committed packet's external resources, as a new version.

    Parameters
    ----------
    root : str or Path
        A packet root holding a committed manifest.
    level : {"size", "members", "sha256"}, default "members"
        How much to establish. `sha256` reads every byte, which is the cost Part 04 §5.2 puts
        here rather than in a build, and records each prefix member's digest beside the
        resource's (Part 04 §5.4).
    packet_version : str, optional
        The new version. Defaults to bumping the patch component, as an amendment does.

    Returns
    -------
    tuple
        The validation report for what was recorded, and the new manifest.

    Raises
    ------
    NotCommitted
        If `root` holds no committed manifest.
    UsageError
        If `level` is not one of :data:`LEVELS`, or `packet_version` does not sort after the
        packet's or has another major version (Part 05 §15.1).
    """
    if level not in LEVELS:
        raise UsageError(f"level must be one of {', '.join(LEVELS)}, not {level!r}", code=UsageFault.UNKNOWN_LEVEL)
    root = Path(root)
    if not (root / MANIFEST_FILENAME).is_file():
        raise NotCommitted(f"{root} holds no committed {MANIFEST_FILENAME}; there is nothing to verify")
    superseded_body = (root / MANIFEST_FILENAME).read_bytes()
    superseded = json.loads(superseded_body)
    version = packet_version or _bump(superseded["packet_version"])
    before = semver(superseded["packet_version"])
    if semver(version) <= before or semver(version)[0] != before[0]:
        raise UsageError(
            f"packet_version {version} does not sort after {superseded['packet_version']} within its major "
            "version (Part 05 §15.1)",
            code=UsageFault.VERSION_NOT_AFTER if semver(version) <= before else UsageFault.VERSION_MAJOR_CHANGED,
        )

    notes: list[str] = []
    candidate = json.loads(json.dumps(superseded))
    reached = 0
    for entry in candidate["resources"]:
        if entry.get("external"):
            reached += _measure(entry, level, notes)
        elif "digest" not in entry:
            # Part 04 §4.3 requires one. Filling it in is the same act as the rest of this
            # command -- write down what is true now -- and costs 0.5% of a build.
            try:
                entry["digest"] = {"algorithm": "sha256", "value": digest(str(root / str(entry.get("uri", ""))))}
            except StoreUnreachable as exc:
                notes.append(f"{entry['resource_id']}: no digest recorded, {exc}")

    candidate["packet_version"] = version

    # Level 3 against what was just recorded, and nothing else. This writes no file and adds no
    # resource, so every packet-owned verdict is determined by immutability exactly as Part 05 §15.4
    # says -- `scan` and `recheck` are empty for the same reason an amendment narrows them to
    # what it wrote, and here that is nothing. What is worth checking is what just changed.
    report = validate(
        Packet(root, Manifest.from_dict(candidate)),
        external=True,
        checksums=level == "sha256",
        store_digests=level in {"members", "sha256"},
        scan=(),
        recheck=(),
    )
    for note in notes:
        report.add(VERIFY_UNREACHABLE, note)
    if not report.passed:
        return report, superseded

    candidate["validation"] = {
        "status": VALIDATION_PASSED,
        "validated_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "validator_name": "escapewheel_validator",
        "validator_version": _version(),
    }
    versions = root / MANIFESTS_DIRNAME
    versions.mkdir(exist_ok=True)
    body = (json.dumps(candidate, indent=2) + "\n").encode()
    for manifest, exact in ((superseded, superseded_body), (candidate, body)):
        # Retained bytes are exact and never rewritten (Part 05 §15.3).
        if not (path := versions / retained(manifest)).exists():
            path.write_bytes(exact)
    written = root / f"{MANIFEST_FILENAME}.candidate"
    written.write_bytes(body)
    os.replace(written, root / MANIFEST_FILENAME)
    report.add(VERIFY_RECORDED, f"{reached} external resource(s) verified at {level}")
    return report, candidate


__all__ = ["LEVELS", "VERIFY_RECORDED", "VERIFY_UNREACHABLE", "verify"]

"""Verify a committed packet where its bytes now live, and record what was found (`04` §5.2).

`05`'s commit records only what the build could reach, and a packet built where its data will
not live records nothing about that data -- correctly, since `04` §5.2 requires a writer that
cannot reach a URI to record nothing rather than guess. This is the step that closes it: once
the bytes have landed, reach them, and write down what was true.

It is the smallest thing R32 calls a new version. No file is written, no resource is added, and
no recorded fact about a packet-owned file changes except one that was missing. What changes is
what the manifest says about resources the packet does **not** own, which is exactly the class
`03` §8 dates rather than promises.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from escapewheel_reader import Manifest, Packet
from escapewheel_validator import Report, validate
from escapewheel_validator.stores import StoreUnreachable, digest, listing

from .writer import MANIFEST, MANIFESTS, NotCommitted, _bump, _version

#: What to establish, each level including the one before it. `size` lists, `members` also
#: records `04` §5.4's per-member listing with whatever content hash the store handed over, and
#: `sha256` also digests every byte. `members` is the default because it is the strongest thing
#: available for the price of the listing.
LEVELS = ("size", "members", "sha256")


def _member_entry(member: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {"key": member.key, "size_bytes": member.size_bytes}
    if member.store_digest is not None:
        entry["store_digest"] = {"algorithm": member.store_digest.algorithm, "value": member.store_digest.value}
    return entry


def _measure(entry: dict[str, Any], level: str, notes: list[str]) -> bool:
    """Record what the store holds for one external resource. False where it could not be read."""
    uri = str(entry.get("uri", ""))
    try:
        found = listing(uri)
        checksum = digest(uri) if level == "sha256" else None
    except StoreUnreachable as exc:
        notes.append(f"{entry['resource_id']}: unchanged, {exc}")
        return False
    entry["size_bytes"] = found.size_bytes
    entry["verified_at"] = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    if level in {"members", "sha256"}:
        entry["members"] = [_member_entry(m) for m in found.members]
    if checksum is not None:
        entry["sha256"] = checksum
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
        How much to establish. `sha256` reads every byte -- 88 s for a session's LFP against
        S3 -- which is the cost `04` §5.2 puts here rather than in a build.
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
    ValueError
        If `level` is not one of :data:`LEVELS`.
    """
    if level not in LEVELS:
        raise ValueError(f"level must be one of {', '.join(LEVELS)}, not {level!r}")
    root = Path(root)
    if not (root / MANIFEST).is_file():
        raise NotCommitted(f"{root} holds no committed {MANIFEST}; there is nothing to verify")
    superseded = json.loads((root / MANIFEST).read_text())

    notes: list[str] = []
    candidate = json.loads(json.dumps(superseded))
    reached = 0
    for entry in candidate["resources"]:
        if entry.get("external"):
            reached += _measure(entry, level, notes)
        elif entry.get("sha256") is None:
            # A packet committed before R52 records none. Filling it in is the same act as the
            # rest of this command -- write down what is true now -- and costs 0.5% of a build.
            try:
                entry["sha256"] = digest(str(root / str(entry.get("uri", ""))))
            except StoreUnreachable as exc:
                notes.append(f"{entry['resource_id']}: no digest recorded, {exc}")

    candidate["packet_version"] = packet_version or _bump(superseded["packet_version"])
    candidate["supersedes"] = superseded["packet_version"]

    # Level 3 against what was just recorded, and nothing else. This writes no file and adds no
    # resource, so every packet-owned verdict is determined by immutability exactly as `03` §9.4
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
        report.add("warning", "verify.unreachable", note)
    if not report.passed:
        return report, superseded

    candidate["validation"] = {
        "status": "passed",
        "validated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "validator_name": "escapewheel_validator",
        "validator_version": _version(),
    }
    versions = root / MANIFESTS
    versions.mkdir(exist_ok=True)
    for manifest in (superseded, candidate):
        (versions / f"nwb.packet.{manifest['packet_version']}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    written = root / f"{MANIFEST}.candidate"
    written.write_text(json.dumps(candidate, indent=2) + "\n")
    os.replace(written, root / MANIFEST)
    report.add("info", "verify.recorded", f"{reached} external resource(s) verified at {level}")
    return report, candidate


__all__ = ["LEVELS", "verify"]

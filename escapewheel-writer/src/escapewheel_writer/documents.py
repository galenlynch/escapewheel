"""The values a manifest states: versions, validation status and digests (Part 04 §4)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path


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

    A prefix goes through Part 04 §4.3's listing, a single file is its own bytes; `digest` already
    distinguishes them.
    """
    from escapewheel_validator.stores import digest

    return {"algorithm": "sha256", "value": digest(str(path))}


__all__ = [
    "VALIDATION_FAILED",
    "VALIDATION_NOT_RUN",
    "VALIDATION_PASSED",
    "bump",
    "first_version",
    "sha256_of",
    "writer_version",
]

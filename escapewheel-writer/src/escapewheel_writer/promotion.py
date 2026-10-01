"""The promotion record, and what a writer may create or must undo at a packet root (Part 05 §6)."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterable
from pathlib import Path

from escapewheel_reader.manifest import MANIFEST_FILENAME
from escapewheel_validator.amendment import semver

from .errors import (
    PacketOccupied,
    PromotionRecordUnreadable,
)
from .layout import PROMOTED, PROMOTION, STAGING


def record_promotion(staging: Path, packet_version: str, paths: Iterable[str]) -> None:
    """Write the promotion record durably, before anything is written outside `staging` (Part 05 §6)."""
    body = json.dumps({"packet_version": packet_version, "paths": sorted(set(paths))}, indent=2) + "\n"
    pending = staging / f"{PROMOTION}.pending"
    with pending.open("w") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(pending, staging / PROMOTION)
    directory = os.open(staging, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def read_promotion(root: Path) -> tuple[str, list[str]] | None:
    """Return the version and paths of the promotion record at `root`, or None where there is none.

    Raises
    ------
    PromotionRecordUnreadable
        If the record cannot be parsed, or lists a path outside the packet root.
    """
    path = root / STAGING / PROMOTION
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text())
        version = str(record["packet_version"])
        paths = [str(p) for p in record["paths"]]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise PromotionRecordUnreadable(f"{path}: cannot read the promotion record ({error})", path=path) from None
    if escaping := [p for p in paths if Path(p).is_absolute() or ".." in Path(p).parts or not p]:
        raise PromotionRecordUnreadable(f"{path}: lists {escaping[0]!r}, which is not under the packet root", path=path)
    return version, paths


def act_on_promotion(root: Path) -> None:
    """Undo what an unpublished promotion created, before anything else happens at `root` (Part 05 §6).

    Where the record's version is already published the record is stale and the listed paths are
    the packet's, so nothing is removed; the staging area is emptied afterwards either way.
    """
    record = read_promotion(root)
    if record is None:
        return
    version, paths = record
    manifest = root / MANIFEST_FILENAME
    if manifest.is_file() and semver(json.loads(manifest.read_text())["packet_version"]) >= semver(version):
        return
    for relative in paths:
        target = root / relative
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()


def claim(root: Path, paths: Iterable[str]) -> None:
    """Refuse to promote onto a path that already exists, naming it (Part 05 §6)."""
    if taken := sorted(p for p in paths if (root / p).exists()):
        raise PacketOccupied(
            f"{root / taken[0]} already exists, so promotion would overwrite it", root=root, occupied=taken
        )


def created(root: Path, relative: str) -> str:
    """Return the outermost path writing `relative` under `root` would create."""
    parts = Path(relative).parts
    for depth in range(1, len(parts) + 1):
        if not (root / Path(*parts[:depth])).exists():
            return Path(*parts[:depth]).as_posix()
    return relative


def refuse_occupied(root: Path) -> None:
    """Refuse a root holding a committed manifest or a directory commit would promote into.

    Called after `act_on_promotion`, so what remains is a promoted directory no promotion record
    claims: a stray a writer may not remove (Part 05 §15.5), and moving another into it would nest
    the new one inside.
    """
    if (root / MANIFEST_FILENAME).exists():
        raise PacketOccupied(
            f"{root} already holds a committed {MANIFEST_FILENAME}", root=root, occupied=[MANIFEST_FILENAME]
        )
    if occupied := [name for name in PROMOTED if (root / name).exists()]:
        raise PacketOccupied(
            f"{root} holds {', '.join(occupied)} but no committed {MANIFEST_FILENAME}, as an interrupted promotion "
            "leaves it; remove them or commit elsewhere",
            root=root,
            occupied=occupied,
        )


__all__ = ["act_on_promotion", "claim", "created", "read_promotion", "record_promotion", "refuse_occupied"]

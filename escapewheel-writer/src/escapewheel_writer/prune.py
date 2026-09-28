"""Cleanup over a committed packet (Part 05 §15.5).

Two removals, in one order. **Orphans first**: a manifest identifies the orphans of its own
version, so expiring it before they are removed makes an orphan and a stray indistinguishable and
does so permanently. Superseded manifests go second, and only as far as the retention policy
allows.

A stray -- a file no manifest has ever named, outside the staging area and every path an
unpublished promotion record claims -- is reported and never removed. A packet may carry files this
specification does not govern, and cleanup that deletes the ungoverned is a data-loss operation
wearing a maintenance name. Files a build or amendment owns are reported apart, and left to it.

Nothing is removed unless a caller asks. Part 05 §15.5 makes reporting the default because the
alternative is a delete whose blast radius is a listing the caller has not read.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from escapewheel_reader.uri import decode, is_absolute

from .writer import MANIFEST, MANIFESTS, STAGING, NotCommitted, PromotionRecordUnreadable, read_promotion, semver

#: Part 05 §15.5. One superseded manifest, and no age limit: a packet is an archival artifact where a
#: table is an operational one, so age alone never expires one.
KEEP_VERSIONS = 1
KEEP_DAYS: float | None = None


@dataclass(frozen=True)
class Plan:
    """What cleanup would remove, or did.

    Attributes
    ----------
    orphans : tuple of Path
        Files a retained manifest names and the current one does not.
    expired : tuple of Path
        Superseded manifests the retention policy no longer keeps.
    strays : tuple of Path
        Files no manifest has ever named, outside every build's own paths (Part 03 §9).
        Reported, never removed.
    staged : tuple of Path
        Files in the staging area (Part 03 §3.4), which the next build or amendment owns.
    promoting : tuple of Path
        Files under a path an unpublished promotion record lists (Part 05 §6), which the next
        build or amendment removes.
    retained : tuple of Path
        Superseded manifests the policy keeps.
    applied : bool
        Whether the removals were carried out.
    """

    orphans: tuple[Path, ...] = ()
    expired: tuple[Path, ...] = ()
    strays: tuple[Path, ...] = ()
    retained: tuple[Path, ...] = ()
    applied: bool = False
    notes: tuple[str, ...] = field(default=())
    staged: tuple[Path, ...] = ()
    promoting: tuple[Path, ...] = ()

    def __len__(self) -> int:
        """How many files the plan removes. A stray is not counted, because it is never one."""
        return len(self.orphans) + len(self.expired)


def _read(path: Path) -> Mapping[str, Any]:
    parsed: Mapping[str, Any] = json.loads(path.read_text())
    return parsed


def _stamp(manifest: Mapping[str, Any]) -> datetime | None:
    """When a manifest was last written, which is what its age is measured from."""
    raw = (manifest.get("validation") or {}).get("validated_at") or manifest.get("created_at")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _names(manifest: Mapping[str, Any]) -> set[str]:
    """Packet-relative paths one manifest names, a prefix's as its directory.

    An external resource is not named: Part 04 §5.1 puts its bytes outside the packet, so cleanup has
    no standing over them. A relative `uri` is decoded to the names it appends (Part 03 §4). Each
    bound registry is named, because a retained manifest is uninterpretable without the registries
    its descriptors bind (Part 05 §15.3).
    """
    named = set()
    for resource in manifest.get("resources", []):
        uri = str(resource.get("uri", ""))
        if resource.get("external") or is_absolute(uri):
            continue
        try:
            named.add("/".join(decode(uri)))
        except ValueError:
            named.add(uri)
    named.update(descriptor["path"] for descriptor in (manifest.get("registries") or {}).values())
    return named


def _covered(name: str, named: set[str]) -> bool:
    """Whether a file is named, itself or as a member of a prefix a name covers."""
    parts = name.split("/")
    return any("/".join(parts[:depth]) in named for depth in range(1, len(parts) + 1))


def _files(root: Path) -> Iterator[Path]:
    """Every file in the packet except the manifests, which the second pass governs."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts[0] == MANIFESTS or relative.as_posix() == MANIFEST:
            continue
        yield path


def prune(
    root: Path,
    *,
    keep_versions: int | None = None,
    keep_days: float | None = None,
    apply: bool = False,
    now: datetime | None = None,
) -> Plan:
    """Plan cleanup over a committed packet, and carry it out where asked (Part 05 §15.5).

    Parameters
    ----------
    root : Path
        A committed packet.
    keep_versions, keep_days : optional
        Override the packet's declared retention. Both are floors: a manifest is expired only
        where both permit it (Part 05 §15.5).
    apply : bool, default False
        Remove. The default reports.

    Returns
    -------
    Plan
        What would be removed, or was.
    """
    root = Path(root)
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        raise NotCommitted(f"{root} carries no {MANIFEST}, so there is no committed state to clean up")
    current = _read(manifest_path)

    declared = current.get("retention") or {}
    versions = keep_versions if keep_versions is not None else declared.get("keep_versions", KEEP_VERSIONS)
    days = keep_days if keep_days is not None else declared.get("keep_days", KEEP_DAYS)

    superseded = sorted(
        ((path, _read(path)) for path in (root / MANIFESTS).glob("nwb.packet.*.json")),
        key=lambda pair: semver(pair[1].get("packet_version", "")),
    )
    # The current version's own retained copy is not superseded, whatever the policy says.
    superseded = [pair for pair in superseded if pair[1].get("packet_version") != current.get("packet_version")]

    # Retention is decided first, because an orphan is judged against the manifests that
    # *survive*: a file named only by a manifest being kept is still needed, and deleting it
    # would leave that manifest uninterpretable -- which is the property Part 05 §15.3 retains for.
    moment = now or datetime.now(tz=timezone.utc)
    keep, expire, notes = [], [], []
    for index, (path, manifest) in enumerate(reversed(superseded)):  # newest first
        if index < max(0, int(versions)):
            keep.append((path, manifest))
            continue
        if days is not None:
            stamp = _stamp(manifest)
            if stamp is None:
                notes.append(f"{path.name} carries no timestamp, so age cannot expire it")
                keep.append((path, manifest))
                continue
            if (moment - stamp).total_seconds() < float(days) * 86_400:
                keep.append((path, manifest))
                continue
        expire.append((path, manifest))

    surviving = _names(current)
    for _, manifest in keep:
        surviving |= _names(manifest)
    named_ever = set(surviving)
    for _, manifest in expire:
        named_ever |= _names(manifest)

    present = {path.relative_to(root).as_posix(): path for path in _files(root)}
    staged = {name for name in present if name.split("/", 1)[0] == STAGING}
    claimed: set[str] = set()
    try:
        record = read_promotion(root)
    except PromotionRecordUnreadable as error:
        record = None
        notes.append(f"{error}; the paths it lists cannot be told from strays")
    if record is not None and semver(record[0]) > semver(current.get("packet_version", "")):
        listed = record[1]
        claimed = {n for n in present if any(n == p or n.startswith(f"{p}/") for p in listed)}
    orphans = tuple(
        sorted(path for name, path in present.items() if _covered(name, named_ever) and not _covered(name, surviving))
    )
    strays = tuple(
        sorted(
            path
            for name, path in present.items()
            if not _covered(name, named_ever) and name not in staged and name not in claimed
        )
    )

    plan = Plan(
        orphans,
        tuple(sorted(path for path, _ in expire)),
        strays,
        tuple(sorted(path for path, _ in keep)),
        apply,
        tuple(notes),
        tuple(sorted(present[name] for name in staged)),
        tuple(sorted(present[name] for name in claimed - staged)),
    )
    if not apply:
        return plan
    for path in plan.orphans:  # Part 05 §15.5: orphans before the manifests that identify them
        path.unlink(missing_ok=True)
    for path in plan.expired:
        path.unlink(missing_ok=True)
    return plan


__all__ = ["KEEP_DAYS", "KEEP_VERSIONS", "Plan", "prune"]

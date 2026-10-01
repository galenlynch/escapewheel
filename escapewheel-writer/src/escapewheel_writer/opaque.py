"""A packet-owned opaque resource: a payload in a directory named by its resource ID (Part 12 §5).

- :func:`read` -- every payload one source placed in its `opaque_location`.
- :func:`write` -- payloads handed over as bytes, written as a protocol adapter would place them.
- :func:`size` -- the bytes a payload holds.
- :func:`shown` -- a path rendered for a report.
- :class:`Payload` -- a payload an in-process adapter hands the build as bytes.
- :class:`StagedPayload` -- one payload a source delivered, not yet bound.
- :data:`DELIVERIES`, :data:`ROOT` -- where payloads lie under the staging area, and under the
  packet root.

This module binds a payload to nothing but its resource directory's name. Binding it to a catalog
row or a singleton declaration needs every source's rows, so the writer does that at commit.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from escapewheel_reader.uri import representable

from .errors import PayloadFault, PayloadProblem, PayloadRefused

#: Where under the staging area each source's `opaque_location` lies, one directory per source kind.
#: Apart from `array_location`'s, which an adapter writes into directly.
DELIVERIES = "opaque-deliveries"

#: The packet-root directory publishing each payload at `opaque/<resource_id>/<name>` (Part 03 §3.1).
ROOT = "opaque"


@dataclass(frozen=True)
class Payload:
    """A payload an in-process adapter hands the build as bytes (Part 12 §5).

    Exactly one of `data`, for a file, and `files`, for a directory keyed by each file's `/`-separated
    path relative to it.
    """

    resource_id: str
    name: str
    data: bytes | None = None
    files: Mapping[str, bytes] | None = None


@dataclass(frozen=True)
class StagedPayload:
    """One payload a source delivered, found where it lies and not yet bound.

    `owned` is what the recipe leaves the delivering source owning, which a payload for a singleton
    declaration must be among (Part 05 §3.4); None where no recipe settled ownership.
    """

    source: str
    resource_id: str
    path: Path
    owned: frozenset[str] | None = None


def shown(path: Path) -> str:
    """Render a path for a report, escaping bytes that are not UTF-8 rather than losing them."""
    return os.fsencode(path).decode("utf-8", "backslashreplace")


def write(payloads: Iterable[Payload], location: str | Path | None, source: str) -> int:
    """Write handed-over payloads into `opaque_location` as an adapter reached by a protocol would.

    A name is checked before it becomes a path, since `/` or `..` in one would place bytes somewhere
    no scan of the location could see; everything else is refused by :func:`read` afterwards.

    Raises
    ------
    PayloadRefused
        If no location was supplied, a name is not representable, a payload is neither a file nor a
        directory, or a resource directory would hold a second payload.
    """
    handed = list(payloads)
    if not handed:
        return 0
    if not location:
        raise _refused(
            source,
            PayloadFault.NO_LOCATION,
            "hands over a packet-owned opaque resource and declares no opaque_location; a payload "
            "crosses into a location the build supplies (Part 12 §5)",
        )
    root = Path(location)
    for payload in handed:
        directory = root / payload.resource_id
        if not representable(payload.resource_id):
            raise _refused(
                source,
                PayloadFault.RESOURCE_ID_UNREPRESENTABLE,
                f"{payload.resource_id!r} cannot name a resource directory",
            )
        target = directory / payload.name
        if not representable(payload.name):
            raise _refused(
                source,
                PayloadFault.NAME_UNREPRESENTABLE,
                f"{shown(directory)}: payload name {payload.name!r} is not representable",
            )
        if (payload.data is None) == (payload.files is None):
            raise _refused(
                source,
                PayloadFault.NOT_ONE_FORM,
                f"{shown(target)}: a payload is one file's bytes or a directory's files",
            )
        if directory.exists() and any(directory.iterdir()):
            raise _refused(
                source,
                PayloadFault.NOT_ONE_PAYLOAD,
                f"{shown(directory)}: a resource directory holds one payload",
            )
        directory.mkdir(parents=True, exist_ok=True)
        if payload.data is not None:
            target.write_bytes(payload.data)
            continue
        target.mkdir()
        assert payload.files is not None
        for relative, data in payload.files.items():
            names = relative.split("/")
            if bad := [name for name in names if not representable(name)]:
                raise _refused(
                    source,
                    PayloadFault.NAME_UNREPRESENTABLE,
                    f"{shown(target)}: {relative!r} holds {bad[0]!r}, which is not representable",
                )
            path = target.joinpath(*names)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return len(handed)


def read(source: str, location: str | Path | None, owned: Collection[str] | None = None) -> list[StagedPayload]:
    """Return every payload one source placed in its `opaque_location`, refusing what a packet cannot own.

    Raises
    ------
    PayloadRefused
        Naming the source and each path: an entry that is not a directory, a resource directory
        holding no payload or several, a member that is neither a regular file nor a directory, an
        empty directory (Part 12 §5), or a name that is not representable (Part 03 §11).
    """
    if not location or not Path(location).is_dir():
        return []
    held = frozenset(owned) if owned is not None else None
    found: list[StagedPayload] = []
    problems: list[PayloadProblem] = []
    for directory in sorted(Path(location).iterdir()):
        if directory.is_symlink() or not directory.is_dir():
            problems.append(
                PayloadProblem(
                    PayloadFault.NOT_A_RESOURCE_DIRECTORY,
                    f"{shown(directory)} is not a resource directory; opaque_location holds only directories",
                )
            )
            continue
        members = sorted(directory.iterdir())
        if len(members) != 1:
            problems.append(
                PayloadProblem(
                    PayloadFault.NOT_ONE_PAYLOAD,
                    f"{shown(directory)} holds {len(members)} payloads; a resource directory holds one",
                )
            )
            continue
        refused = list(_refusals(members[0]))
        problems += refused
        if not refused:
            found.append(StagedPayload(source, directory.name, members[0], held))
    if problems:
        raise PayloadRefused(
            f"{source}: " + "; ".join(p.message for p in problems) + " (Part 12 §5)", problems=problems, source=source
        )
    return found


def _refused(source: str, code: PayloadFault, message: str) -> PayloadRefused:
    """Return the refusal of one thing `source` handed over."""
    return PayloadRefused(f"{source}: {message}", problems=[PayloadProblem(code, message)], source=source)


def _refusals(path: Path) -> Iterator[PayloadProblem]:
    """Yield what a payload holds that a packet cannot own: a non-regular file, an empty directory, a bad name."""
    if not representable(path.name):
        yield PayloadProblem(PayloadFault.NAME_UNREPRESENTABLE, f"{shown(path)}: the name is not representable")
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return
    if stat.S_ISDIR(mode):
        children = sorted(path.iterdir())
        if not children:
            yield PayloadProblem(
                PayloadFault.EMPTY_DIRECTORY,
                f"{shown(path)} is an empty directory, which a prefix of objects cannot hold",
            )
        for child in children:
            yield from _refusals(child)
        return
    what = "a symbolic link" if stat.S_ISLNK(mode) else "neither a regular file nor a directory"
    yield PayloadProblem(
        PayloadFault.NOT_REGULAR, f"{shown(path)} is {what}; a payload holds only regular files and directories"
    )


def size(path: Path) -> int:
    """Return the bytes a payload holds, which its `size_bytes` covers (Part 03 §10)."""
    if path.is_file():
        return path.stat().st_size
    return sum(member.stat().st_size for member in path.rglob("*") if member.is_file())


__all__ = ["DELIVERIES", "ROOT", "Payload", "StagedPayload", "read", "shown", "size", "write"]

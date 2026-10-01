"""Names in a packet-owned opaque payload that would not survive every copy (Part 05 §5.3).

- :func:`findings` -- one `(directory, names, reason)` for each set of colliding names and each
  name Windows cannot hold.
- :func:`describe` -- one of those as a finding's message.
- :func:`colliding`, :func:`caseless` -- the sets of distinct names that are a canonical caseless
  match, and the key they match under.
- :func:`unportable_to_windows` -- whether Windows cannot hold a name.
- :func:`payload_directories` -- a mapping from each directory in or above a payload to the names
  it holds.

A payload keeps its names byte for byte (Part 03 §11), so a packet conforms whatever its names
are. These functions report the names that Windows, or a filesystem that folds case or
normalization, cannot hold.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence

#: U+0001 through U+001F and the eight characters Windows refuses in a name.
_WINDOWS_FORBIDDEN = frozenset('"*:<>?\\|') | {chr(code) for code in range(0x01, 0x20)}

#: Windows' device names, alone or before a full stop. `re.ASCII` keeps the case-insensitivity to ASCII,
#: as Part 05 §5.3 requires; Unicode matching would also equate the Kelvin sign with `K`, say.
_WINDOWS_DEVICE = re.compile(r"(?:CON|PRN|AUX|NUL|(?:COM|LPT)[1-9¹²³])(?:\..*)?", re.IGNORECASE | re.ASCII | re.DOTALL)


def caseless(name: str) -> str:
    """Return the key under which names are a canonical caseless match (Unicode D145)."""
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", name).casefold())


def unportable_to_windows(name: str) -> bool:
    """Whether Windows cannot hold a file or directory under this name."""
    return (
        any(character in _WINDOWS_FORBIDDEN for character in name)
        or name.endswith((".", " "))
        or _WINDOWS_DEVICE.fullmatch(name) is not None
    )


def colliding(names: Iterable[str]) -> list[tuple[str, ...]]:
    """Return each set of distinct names that are a canonical caseless match, names in UTF-8 byte order."""
    groups: dict[str, set[str]] = defaultdict(set)
    for name in names:
        groups[caseless(name)].add(name)
    found = [tuple(sorted(group, key=str.encode)) for group in groups.values() if len(group) > 1]
    return sorted(found, key=lambda group: group[0].encode())


def payload_directories(segments: Sequence[str], keys: Iterable[str]) -> dict[str, set[str]]:
    """Map each directory to the names it holds, as paths under the packet root, the root being `.`.

    `segments` is the payload `uri` decoded; each of them is a name in the directory before it, so
    the payload's own name is one in the directory holding it. `keys` are the payload's files,
    relative to it, and empty for a payload that is one file. A directory holding no file is not
    listed, as a prefix in an object store has no such thing.
    """
    directories: dict[str, set[str]] = defaultdict(set)
    for depth, name in enumerate(segments):
        directories["/".join(segments[:depth]) or "."].add(name)
    for key in keys:
        parts = key.split("/")
        for depth, name in enumerate(parts):
            directories["/".join((*segments, *parts[:depth]))].add(name)
    return dict(directories)


def findings(segments: Sequence[str], keys: Iterable[str]) -> list[tuple[str, tuple[str, ...], str]]:
    """Return one `(directory, names, reason)` per colliding set and per name unportable to Windows.

    Collisions are sought within the payload and the directory holding it; Windows portability also
    in every decoded segment of the `uri` above them (Part 05 §5.3). `reason` is `collide` or `windows`.
    """
    payload = "/".join(segments)
    within = {"/".join(segments[:-1]) or ".", payload}
    reported: list[tuple[str, tuple[str, ...], str]] = []
    directories = payload_directories(segments, keys)
    for directory in sorted(directories, key=str.encode):
        names = directories[directory]
        if directory in within or directory.startswith(f"{payload}/"):
            reported.extend((directory, group, "collide") for group in colliding(names))
        reported.extend(
            (directory, (name,), "windows") for name in sorted(names, key=str.encode) if unportable_to_windows(name)
        )
    return reported


def describe(resource_id: str, directory: str, names: Sequence[str], reason: str) -> str:
    """Return a finding's message, naming the resource, the directory, and the names."""
    if reason == "collide":
        # Escaped, since names differing only in normalization print identically.
        listed = ", ".join(ascii(name) for name in names)
        return (
            f"{resource_id}: in {directory!r}, {listed} are one name to a filesystem folding case or "
            "normalization (Unicode D145)"
        )
    return f"{resource_id}: in {directory!r}, {names[0]!r} is a name Windows cannot hold"


__all__ = [
    "caseless",
    "colliding",
    "describe",
    "findings",
    "payload_directories",
    "unportable_to_windows",
]

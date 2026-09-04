"""One source root, read once and shared by every adapter that reads it.

Three adapters in a real recipe open the same `.nwb` directory -- `NWBSource` for the tables
it is the authority for, `WaveformSource` for the templates, `LFPSource` for the series -- and
two of them independently read `general/extracellular_ephys/electrodes`. `WaveformSource` reads
its six `units/` arrays twice within itself. None of that is expensive enough to matter on its
own; what matters is that two readers of the same bytes can disagree, and a cache shared by
both makes that impossible rather than unlikely.

A memo retains what it reads, for the whole build. That is free for the columns an adapter
keeps anyway and expensive for one it samples: reading an array whole to look at its head
costs its full size held, so :meth:`SourceStore.head` decodes only the chunks it needs.

Only reads that are *pure* live here. `NWBSource._table` stays where it is because it produces
notes, and a note about a skipped column belongs to the adapter that asked, not to whichever
one happened to ask first.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from numpy.typing import NDArray

from .zarr_compat import attrs, members, read_array


class SourceStore:
    """A source directory, with every parsed read memoized.

    Parameters
    ----------
    root : str or Path
        The source directory. Resolved, so two recipes naming the same tree by different paths
        share one store.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self._arrays: dict[str, NDArray[Any]] = {}
        self._attrs: dict[str, dict[str, Any]] = {}
        self._heads: dict[tuple[str, int], NDArray[Any]] = {}
        self._members: dict[str, list[str]] = {}
        self._json: dict[str, dict[str, Any] | None] = {}

    def __repr__(self) -> str:
        """Name the root, since that is a store's whole identity."""
        return f"SourceStore({self.root})"

    def _key(self, path: str | Path) -> str:
        """Normalise a path to a key relative to the root."""
        target = Path(path)
        return str(target.relative_to(self.root) if target.is_absolute() else target)

    def path(self, path: str | Path) -> Path:
        """Resolve a relative path against the root."""
        target = Path(path)
        return target if target.is_absolute() else self.root / target

    def array(self, path: str | Path) -> NDArray[Any]:
        """Read a one-dimensional array, memoized.

        Raises whatever `read_array` raises -- an `UnsupportedEncoding` is a fact about the
        array and the caller decides what to do about it. Failures are not cached, so a caller
        that handles one and a caller that does not both see it.
        """
        key = self._key(path)
        if key not in self._arrays:
            self._arrays[key] = read_array(self.path(path))
        return self._arrays[key]

    def head(self, path: str | Path, count: int) -> NDArray[Any]:
        """Read the first `count` values of an array, memoized.

        Decodes only the chunks holding them, and keeps only those: an LFP series stores
        7,983,750 timestamps and `_decimation` wants two, so reading it whole and slicing
        costs 64 MB retained per series for 16 bytes used.
        """
        key = self._key(path)
        if key in self._arrays:
            return self._arrays[key][:count]
        if (key, count) not in self._heads:
            self._heads[key, count] = read_array(self.path(path), limit=count)
        return self._heads[key, count]

    def attrs(self, path: str | Path = "") -> dict[str, Any]:
        """Read a node's attributes, memoized."""
        key = self._key(path)
        if key not in self._attrs:
            self._attrs[key] = attrs(self.path(path))
        return self._attrs[key]

    def members(self, path: str | Path) -> list[str]:
        """List a group's children, memoized."""
        key = self._key(path)
        if key not in self._members:
            self._members[key] = members(self.path(path))
        return self._members[key]

    def zarray(self, path: str | Path) -> dict[str, Any] | None:
        """Read an array's `.zarray` document, or None where the path is not a v2 array."""
        key = self._key(path)
        if key not in self._json:
            document = self.path(path) / ".zarray"
            self._json[key] = json.loads(document.read_text()) if document.is_file() else None
        return self._json[key]

    def is_array(self, path: str | Path) -> bool:
        """Whether a path holds a Zarr v2 array."""
        return self.zarray(path) is not None


def store_for(root: str | Path, shared: dict[Path, SourceStore] | None = None) -> SourceStore:
    """Return the store for a root, from `shared` where a caller is keeping one.

    An adapter constructed on its own gets a private store, so nothing about sharing leaks
    into how an adapter is written or tested.
    """
    if shared is None:
        return SourceStore(root)
    resolved = Path(root).resolve()
    if resolved not in shared:
        shared[resolved] = SourceStore(resolved)
    return shared[resolved]


__all__ = ["SourceStore", "store_for"]

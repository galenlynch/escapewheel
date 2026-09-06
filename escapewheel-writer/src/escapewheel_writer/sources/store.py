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
from pathlib import Path, PurePath
from typing import Any

from numpy.typing import NDArray
from upath import UPath

from .zarr_compat import attrs, members, read_array


class SourceStore:
    """A source directory, with every parsed read memoized.

    Parameters
    ----------
    root : str or path
        The source directory, local or a store URI. Resolved, so two recipes naming the same
        tree by different paths share one store.

        A `UPath` because an AIND session's assets are prefixes on `aind-open-data`, and a
        build reads about 12% of a sorted asset -- the spikes, the analyzer's `recording_info`
        and its spike amplitudes, and none of the templates, PCA or provenance pickles. Which
        12% is a fact about what the adapters read, so fetching it first means writing that
        list down somewhere the adapters cannot check it. Reading in place has no list: it
        costs 6.6 s against 0.07 s for a stream's 344 MB `spikes.npy`, roughly 66 s on a
        121 s build, and saves the 3.8 GB copy.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = source_root(root)
        self._arrays: dict[str, NDArray[Any]] = {}
        self._attrs: dict[str, dict[str, Any]] = {}
        self._heads: dict[tuple[str, int], NDArray[Any]] = {}
        self._members: dict[str, list[str]] = {}
        self._json: dict[str, dict[str, Any] | None] = {}

    def __repr__(self) -> str:
        """Name the root, since that is a store's whole identity."""
        return f"SourceStore({self.root})"

    def _key(self, path: str | Path) -> str:
        """Normalise a path to a key relative to the root.

        The root's own flavour is preserved: re-wrapping a `UPath` with `Path` would collapse
        `s3://bucket/x` to `s3:/bucket/x` and silently look for it on local disk.
        """
        target = path if isinstance(path, PurePath) else UPath(path)
        return str(target.relative_to(self.root) if _rooted(target) else target)

    def path(self, path: str | Path) -> Any:
        """Resolve a relative path against the root, in the root's own flavour."""
        target = path if isinstance(path, PurePath) else UPath(path)
        return target if _rooted(target) else self.root / target

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


def _rooted(target: Any) -> bool:
    """Whether a path already names a location, rather than a fragment under a root."""
    return bool(getattr(target, "protocol", "")) or target.is_absolute()


#: Protocols whose clients accept `anon`, which a public bucket needs and a stale credential
#: chain otherwise defeats. Anything else is left to fsspec's own defaults.
ANONYMOUS = frozenset({"s3", "gs", "gcs", "az", "abfs", "adl"})


def source_root(root: str | PurePath, **storage: Any) -> Any:
    """Return a root as a path: a local one resolved, a store one opened.

    `resolve()` on a store URI is a no-op that still costs a round trip on some backends, and
    a URI has no `..` to collapse: what makes two spellings of one local tree share a store is
    exactly what a URI does not need.

    **A store is read anonymously unless the caller says otherwise.** These packets are built
    from public buckets, and signing is what fails: a stale profile makes the client refresh an
    SSO token and give up before considering that the object needs no signing at all. Passing
    `storage` replaces that default rather than adding to it, so `anon=False` asks for the
    ambient credential chain back.
    """
    path = root if isinstance(root, PurePath) and not storage else UPath(str(root), **storage)
    protocol = getattr(path, "protocol", "")
    if protocol in ("", "file"):
        return path.resolve()
    if storage or protocol not in ANONYMOUS:
        return path
    return UPath(str(root), anon=True)


def store_for(root: str | PurePath, shared: dict[Any, SourceStore] | None = None) -> SourceStore:
    """Return the store for a root, from `shared` where a caller is keeping one.

    An adapter constructed on its own gets a private store, so nothing about sharing leaks
    into how an adapter is written or tested.
    """
    if shared is None:
        return SourceStore(root)
    resolved = source_root(root)
    if resolved not in shared:
        shared[resolved] = SourceStore(resolved)
    return shared[resolved]


__all__ = ["SourceStore", "source_root", "store_for"]

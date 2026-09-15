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
import os
import tempfile
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
        target = path if _pathlike(path) else UPath(path)
        return str(target.relative_to(self.root) if _rooted(target) else target)

    def path(self, path: str | Path) -> Any:
        """Resolve a relative path against the root, in the root's own flavour."""
        target = path if _pathlike(path) else UPath(path)
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


def _pathlike(value: Any) -> bool:
    """Whether a value is already a path, local or store, rather than a string to parse."""
    return isinstance(value, PurePath) or hasattr(value, "protocol")


def _rooted(target: Any) -> bool:
    """Whether a path already names a location, rather than a fragment under a root."""
    return bool(getattr(target, "protocol", "")) or target.is_absolute()


#: Protocols whose clients accept `anon`, which a public bucket needs and a stale credential
#: chain otherwise defeats. Anything else is left to fsspec's own defaults.
ANONYMOUS = frozenset({"s3", "gs", "gcs", "az", "abfs", "adl"})


#: The environment variable naming the cache directory. Not a supplied term (Part 03 §11.2): an
#: adapter that never reads it caches somewhere else and is conforming, so this says where the
#: bytes should land rather than anything a delivery depends on.
CACHE_VARIABLE = "ESCAPEWHEEL_SOURCE_CACHE"


def cache_directory() -> Path:
    """Where a store's fetched objects are kept: `ESCAPEWHEEL_SOURCE_CACHE`, else under `TMPDIR`.

    The variable is the channel because an adapter may run in another process, where a value
    set in this one does not reach it; the environment is what a delivering command inherits.
    """
    named = os.environ.get(CACHE_VARIABLE)
    if named:
        return Path(named)
    return Path(os.environ.get("TMPDIR", tempfile.gettempdir())) / "escapewheel-source-cache"


#: What the last `cache_beside` put in the environment, so a second packet moves the cache and an
#: operator's own setting is left alone. Two recipes in one process is the case: the variable is
#: how the location reaches a child, and a value this process wrote is not a declaration.
_PLACED: str | None = None


def cache_beside(packet: str | PurePath) -> Path:
    """Put the cache in the packet's parent directory, and return where that is.

    A default under `TMPDIR` is RAM wherever `/tmp` is a tmpfs, so a cgroup cap does not bound
    what a build fetches and the kill arrives as system memory pressure. Beside the packet puts
    it on the filesystem that is about to hold the packet, which is the same choice the
    materializer and the validator make for their scratch.

    The parent rather than the packet, so a rebuild into a new directory reads what the last
    one fetched: `simplecache` keys on the URI, so two packets sharing a directory share
    whatever objects they share and collide over none.

    Call it before the first root resolves. A store root is opened through a chained path
    carrying the cache location, so where the bytes land is fixed when the path is built and
    moving the cache afterwards moves nothing.

    An operator who has set `ESCAPEWHEEL_SOURCE_CACHE` keeps it.
    """
    global _PLACED
    declared = os.environ.get(CACHE_VARIABLE)
    if declared and declared != _PLACED:
        return Path(declared)
    where = Path(packet).parent / ".escapewheel-source-cache"
    os.environ[CACHE_VARIABLE] = _PLACED = str(where)
    return where


def source_root(root: str | PurePath, *, cache: str | PurePath | None = None, **storage: Any) -> Any:
    """Return a root as a path: a local one resolved, a store one opened through a cache.

    `resolve()` on a store URI is a no-op that still costs a round trip on some backends, and
    a URI has no `..` to collapse: what makes two spellings of one local tree share a store is
    exactly what a URI does not need.

    **A store is read anonymously unless the caller says otherwise.** These packets are built
    from public buckets, and signing is what fails: a stale profile makes the client refresh an
    SSO token and give up before considering that the object needs no signing at all. Passing
    `storage` replaces that default rather than adding to it, so `anon=False` asks for the
    ambient credential chain back.

    **A store is also read through a local cache**, because an adapter reads some objects more
    than once: `spikes.npy` is read for a stream's unit summary and again to stream its spikes,
    and over a network that second read costs another 344 MB. Bandwidth is not the lever --
    parallel ranges within one object win 1.1x and concurrency across objects 1.2x against a
    link that saturates near 99 MB/s -- so what pays is not fetching twice, which the cache
    turns from 4.0 s into 0.1 s. What lands in it is exactly what the adapters read, which is
    the list a hand-written prefetch would have to keep in step with them. Pass `cache=False`
    to read straight through.
    """
    if not storage and not isinstance(root, str):
        # Idempotent: a root reaches an adapter already resolved by the recipe, and `str()` on
        # a store path drops the options it was opened with -- anonymity among them. Tested on
        # the type rather than on `PurePath`, because a chained `UPath` is not one: a
        # `simplecache::s3://` path subclasses `UPath` alone, so an isinstance check against
        # `PurePath` silently sends it down the re-parse path and it comes back signed.
        if getattr(root, "protocol", "") not in ("", "file"):
            return root
        return Path(root).resolve()
    text = str(root)
    protocol = getattr(UPath(text), "protocol", "")
    if protocol in ("", "file"):
        return Path(text).resolve()
    options = dict(storage) or ({"anon": True} if protocol in ANONYMOUS else {})
    if cache is False or protocol == "simplecache":
        return UPath(text, **options)
    where = cache_directory() if cache is None else Path(cache)
    where.mkdir(parents=True, exist_ok=True)
    # `cache_storage` at the top level, the target's options under its protocol. Nesting it under
    # `simplecache`, as the chained-URL form suggests, parses and is then dropped: the filesystem
    # comes back with `storage` at a `mkdtemp()` under `TMPDIR`, which is where every fetched
    # object went while the directory named here stayed empty.
    return UPath(f"simplecache::{text}", **{protocol: options, "cache_storage": str(where)})


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

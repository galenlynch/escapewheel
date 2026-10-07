"""One source root, read once and shared by every adapter that reads it.

- :class:`SourceStore` -- a source directory or store prefix, with every parsed read memoized.
- :func:`store_for` -- the store for a root, reused where the caller keeps shared stores.
- :func:`source_root` -- a root as a path: a local root resolved, a store root opened.
- :func:`store_uri` -- where a path lives, as a packet names it, whatever cache it is read through.
- :class:`KeptObjects` -- whole objects kept across builds, each confirmed by its store before
  use (Part 12 §10).
- :func:`prune_kept` -- the kept files unused for a number of days, removed where asked.
- :data:`STORAGE_FORMAT` -- the subdirectory in which this writer keeps data, under a
  source-cache location.

Only pure reads are memoized: a read that produces notes stays with the adapter that asked, since
a note belongs to its asker and not to whichever adapter asked first.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
import weakref
from pathlib import Path, PurePath
from typing import Any

from escapewheel_reader.resources import ZARR_METADATA_FILENAMES
from fsspec.implementations.cached import SimpleCacheFileSystem
from numpy.typing import NDArray
from upath import UPath

from .zarr_compat import attrs, members, read_array

#: This writer's storage format, the subdirectory of a source-cache location it keeps data under
#: and the only one it changes (Part 12 §10). Named for the package, which is what controls it.
STORAGE_FORMAT = "escapewheel-writer"

#: What a store's `info` reports that changes when an object's bytes do -- an entity tag, a
#: version, or a full-object checksum -- under each fsspec backend's key, in preference order.
#: A modification time is not one (Part 12 §10).
CONFIRMING = (
    "ETag",
    "etag",
    "VersionId",
    "version_id",
    "generation",
    "ChecksumSHA256",
    "ChecksumCRC64NVME",
    "crc32c",
    "md5Hash",
)

#: A URI naming one version of an object, whose content cannot change, so a copy of it needs no
#: confirmation (Part 12 §10).
PINNED = re.compile(r"[?&]versionId=[^&]+")


class KeptObjects(SimpleCacheFileSystem):  # type: ignore[misc]
    """Whole objects kept across builds, each used only once the store has confirmed it this run.

    Every read route upstream -- `open`, `cat`, `cat_file`, `cat_ranges` and their async forms --
    asks `_check_file` for a local copy before fetching one itself, so answering it with a
    confirmed, complete copy every time governs them all. Helpers are module functions because
    `CachingFileSystem.__getattribute__` hands any method it does not list to the target store.

    Layout under the storage root: `objects/` holds entries keyed by URI and confirming value,
    `partial/` fetches in flight, and `runs/<run>/` objects the store reports no confirming value
    for, which this run reuses and no later one does.

    Parameters
    ----------
    run : str
        Distinguishes this run's instance from every other: fsspec caches instances by their
        arguments, and a confirmation holds only within the run that made it.
    """

    def __init__(self, run: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.run = run
        self._confirmed: dict[str, str] = {}
        weakref.finalize(self, shutil.rmtree, os.path.join(self.storage[-1], "runs", run), ignore_errors=True)

    def _check_file(self, path: str) -> str:
        path = self._strip_protocol(path)
        kept = self._confirmed.get(path)
        if kept is None or not os.path.exists(kept):
            kept = self._confirmed[path] = _confirmed_copy(self, path)
        return kept


def _confirmed_copy(fs: KeptObjects, path: str) -> str:
    """Return a complete local copy of `path` that the store has just confirmed, fetching it if needed."""
    root = fs.storage[-1]
    uri = fs.fs.unstrip_protocol(path)
    if PINNED.search(uri):
        entry = os.path.join(root, "objects", _digest(uri))
        if not os.path.exists(entry):
            _fetch(fs, path, entry)
        return entry
    tag, size = _confirming(fs, path)
    this_run = os.path.join(root, "runs", fs.run, _digest(uri))
    if tag is None:
        if not os.path.exists(this_run):
            _fetch(fs, path, this_run)
        return this_run
    entry = os.path.join(root, "objects", _digest(f"{uri}\n{tag}"))
    if os.path.exists(entry) and os.path.getsize(entry) != size:
        os.remove(entry)
    if os.path.exists(entry):
        # Touched on use, so `prune_kept`'s age is time since a build last read it.
        os.utime(entry)
        return entry
    _fetch(fs, path, this_run)
    # Filed under the tag only if the store still reports it, since the object may have changed
    # between asking and fetching; otherwise it is only what this run read.
    if _confirming(fs, path)[0] != tag:
        return this_run
    os.makedirs(os.path.dirname(entry), exist_ok=True)
    os.replace(this_run, entry)
    return entry


def _confirming(fs: KeptObjects, path: str) -> tuple[str | None, int | None]:
    """Ask the store, bypassing any listing it cached, for the object's confirming value and size."""
    fs.fs.invalidate_cache(path)
    info = fs.fs.info(path)
    tag = next((f"{key}={info[key]}" for key in CONFIRMING if info.get(key) not in (None, "", "null")), None)
    return tag, info.get("size")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _fetch(fs: KeptObjects, path: str, entry: str) -> None:
    """Fetch into a name no reader looks up, and publish it under `entry` only once it is whole."""
    partial = os.path.join(fs.storage[-1], "partial")
    os.makedirs(partial, exist_ok=True)
    os.makedirs(os.path.dirname(entry), exist_ok=True)
    handle, fetching = tempfile.mkstemp(dir=partial)
    os.close(handle)
    try:
        fs.fs.get_file(path, fetching)
        os.replace(fetching, entry)
    finally:
        if os.path.exists(fetching):
            os.remove(fetching)


class SourceStore:
    """A source directory, with every parsed read memoized.

    Parameters
    ----------
    root : str or path
        The source directory, local or a store URI. Resolved, so two recipes naming the same
        tree by different paths share one store.

        A `UPath` because a source may be a prefix on an object store, and a build reads a
        small part of a sorted asset -- the spikes, the analyzer's `recording_info` and its
        spike amplitudes, and none of the templates, PCA or provenance pickles. Which part is
        a fact about what the adapters read, so fetching it first means writing that list down
        somewhere the adapters cannot check it. Reading in place has no list, at the cost of
        reading each object over the network, and saves copying the asset.
    """

    def __init__(self, root: str | Path, *, cache: str | PurePath | None = None) -> None:
        self.root = source_root(root, cache=cache)
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

        Decodes only the chunks holding them, and keeps only those: an LFP series stores a
        timestamp per sample and `_decimation` wants two, so reading it whole and slicing
        would retain the whole array for 16 bytes used.
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
            document = self.path(path) / ZARR_METADATA_FILENAMES[2]
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


def source_root(root: str | PurePath, *, cache: str | PurePath | None = None, **storage: Any) -> Any:
    """Return a root as a path: a local one resolved, a store one opened, through `cache` if given.

    `resolve()` on a store URI is a no-op that still costs a round trip on some backends, and
    a URI has no `..` to collapse: what makes two spellings of one local tree share a store is
    exactly what a URI does not need.

    **A store is read anonymously unless the caller says otherwise.** These packets are built
    from public buckets, and signing is what fails: a stale profile makes the client refresh an
    SSO token and give up before considering that the object needs no signing at all. Passing
    `storage` replaces that default rather than adding to it, so `anon=False` asks for the
    ambient credential chain back.

    **`cache` is the `source_cache` a build supplied** (Part 12 §10), and a store root is then
    read through :class:`KeptObjects` under it, because an adapter reads some objects more than
    once and some builds more than once: `spikes.npy` is read for a stream's unit summary and
    again to stream its spikes, and over a network that second read fetches the whole object
    again. Parallel ranges and concurrent objects gain little against a saturated link, so what
    pays is not fetching twice. What lands in the cache is exactly what the adapters read, which
    is the list a hand-written prefetch would have to keep in step with them. Each call opens a
    new run, so the store confirms each object again.
    """
    if not storage and not isinstance(root, str):
        # Idempotent: a root reaches an adapter already resolved by the recipe, and `str()` on
        # a store path drops the options it was opened with -- anonymity among them. Tested on
        # the type rather than on `PurePath`, because a chained `UPath` is not one.
        if getattr(root, "protocol", "") in ("", "file"):
            return Path(root).resolve()
        return root if cache is None or isinstance(root.fs, KeptObjects) else _kept(root, cache)
    text = str(root)
    protocol = getattr(UPath(text), "protocol", "")
    if protocol in ("", "file"):
        return Path(text).resolve()
    opened = UPath(text, **(dict(storage) or ({"anon": True} if protocol in ANONYMOUS else {})))
    return opened if cache is None else _kept(opened, cache)


def store_uri(path: Any) -> str:
    """Return where `path` lives, as a packet names it: a `file:` URI, or the store's own URI.

    A path read through the source cache stringifies as the chain `simplecache::s3://…`, which
    names this build's cache and no location a reader can open (Part 03 §4).
    """
    if getattr(path, "protocol", "") in ("", "file"):
        return Path(path).resolve().as_uri()
    return str(path).rsplit("::", 1)[-1]


def _kept(root: Any, cache: str | PurePath) -> Any:
    """Open a store root through the objects kept under `cache`, as a new run.

    A `simplecache::` path, so upath chains and joins it as the cache it is, with the filesystem
    assigned rather than registered: every path derived from it shares the instance, and fsspec's
    own `simplecache` stays what other code in the process expects.
    """
    kept = UPath(f"simplecache::{root}", **{root.protocol: dict(root.storage_options)})
    kept._fs_cached = KeptObjects(
        run=uuid.uuid4().hex,
        target_protocol=root.protocol,
        target_options=dict(root.storage_options),
        cache_storage=str(Path(cache) / STORAGE_FORMAT),
    )
    return kept


def prune_kept(
    location: str | PurePath, *, older_than: float | None = None, apply: bool = False
) -> list[tuple[Path, int]]:
    """Return each file this writer keeps under `location` unused for `older_than` days, with its size.

    Removes them where `apply` is set.
    Only under :data:`STORAGE_FORMAT`, since everything else in a location is another format's
    (Part 12 §10). Run between builds: a build reading what this removes fetches it again, and one
    fetching into `partial/` fails.
    """
    root = Path(location) / STORAGE_FORMAT
    if not root.is_dir():
        return []
    cutoff = None if older_than is None else time.time() - older_than * 86400
    found = []
    for path in sorted(root.rglob("*")):
        stat = path.stat()
        if path.is_file() and (cutoff is None or stat.st_mtime < cutoff):
            found.append((path, stat.st_size))
    if apply:
        for path, _ in found:
            path.unlink(missing_ok=True)
        runs = root / "runs"
        for run in runs.iterdir() if runs.is_dir() else ():
            if run.is_dir() and not any(run.iterdir()):
                run.rmdir()
    return found


def store_for(
    root: str | PurePath, shared: dict[Any, SourceStore] | None = None, *, cache: str | PurePath | None = None
) -> SourceStore:
    """Return the store for a root, from `shared` where a caller is keeping one.

    An adapter constructed on its own gets a private store, so nothing about sharing leaks
    into how an adapter is written or tested. Keyed by the cache too, since an adapter supplied
    no `source_cache` must not read through one (Part 12 §4).
    """
    if shared is None:
        return SourceStore(root, cache=cache)
    key = (source_root(root), None if cache is None else str(cache))
    if key not in shared:
        shared[key] = SourceStore(key[0], cache=cache)
    return shared[key]


__all__ = ["STORAGE_FORMAT", "KeptObjects", "SourceStore", "prune_kept", "source_root", "store_for", "store_uri"]

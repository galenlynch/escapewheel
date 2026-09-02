"""Reach an external resource's bytes, wherever they are.

R14 §2.3 makes referencing the expected form for a large resource, and in production that means
an object store. What a packet may then say about those bytes is bounded by two things.

**Nothing here runs by default.** R14 §2.3.2 keeps structural validation off the network:
reachability, credentials and whether the caller is offline are properties of a situation, not
of a packet. Every function in this module is reached only from an explicitly requested mode.

**What is verified is a point in time.** R14 §2.3.1: immutability covers packet-owned bytes,
and an external resource may change or vanish without the packet changing at all. So these
return what was true when they looked, which is what `verified_at` records beside them.

This lives with the validator rather than the reader because **no read path uses it**. A table
resolves to a local path or is handed to DuckDB as a URI; a Zarr array is handed its URI and its
own library opens it. What needs a store client is R36's verification -- list a prefix, and hash
its members -- and both users of it are on that side: this package checks what a manifest claims,
and `nwb-lake-writer` establishes it in the first place through its `verify` setting. The writer
depends on this package already, because `05`'s commit is validate-then-rename.

A local path needs no library. Any other scheme goes through fsspec, which is not a dependency
of this package -- the `remote` extra brings it, and a backend for the scheme is separate again
(`s3fs` for `s3://`, `gcsfs` for `gs://`).
"""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

#: Bytes per read when digesting. Large enough that a remote store is not asked a thousand
#: times for a chunk it would have streamed, small enough to bound memory on a 6.8 GB array.
BLOCK = 1 << 22


class StoreUnreachable(Exception):
    """A store could not be reached, which says nothing about whether the packet is valid."""


def is_local(uri: str) -> bool:
    """Whether a URI names a filesystem path this can open without a backend.

    A single-letter scheme is a Windows drive rather than a URI scheme.
    """
    scheme = urlparse(uri).scheme
    return not scheme or scheme == "file" or len(scheme) == 1


def local_path(uri: str) -> Path:
    """Return the path a local URI names."""
    return Path(unquote(urlparse(uri).path)) if urlparse(uri).scheme == "file" else Path(uri)


#: How many of a prefix's members to read at once when digesting (R36 §2.2). Object stores are
#: latency-bound per object, so this is the difference between a minute and eight over a
#: session's LFP; the value is modest because a store also rate-limits, and the gain is mostly
#: had by the eighth worker.
WORKERS = 8


def _filesystem(uri: str) -> tuple[Any, str]:
    """Return an fsspec filesystem and the path within it, for a non-local URI."""
    try:
        import fsspec  # type: ignore[import-untyped]  # optional; the 'remote' extra
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        scheme = urlparse(uri).scheme
        raise StoreUnreachable(
            f"reaching a {scheme}: store needs fsspec (the 'remote' extra) and a backend for "
            f"that scheme (s3fs for s3://, gcsfs for gs://)"
        ) from exc
    try:
        filesystem, path = fsspec.core.url_to_fs(uri)
    except (ImportError, ValueError) as exc:
        raise StoreUnreachable(f"{uri}: {exc}") from exc
    return filesystem, path


@dataclass(frozen=True)
class Listing:
    """What a store holds under one URI.

    Attributes
    ----------
    members : tuple
        ``(key, size)`` for every object, keyed relative to the URI and sorted. A single-object
        resource has one member whose key is the empty string.
    size_bytes : int
        Total across the members.
    """

    members: tuple[tuple[str, int], ...]
    size_bytes: int

    @property
    def is_single_object(self) -> bool:
        """Whether the URI names one object rather than a prefix of many."""
        return len(self.members) == 1 and self.members[0][0] == ""


def listing(uri: str) -> Listing:
    """List what a URI holds, without reading any of it.

    A dense array asset is a *prefix*, not an object: one LFP series is 208 chunk objects plus
    its metadata document. Sizing it is therefore a list operation, and the total is what
    `size_bytes` means for such a resource.

    Raises
    ------
    StoreUnreachable
        If the store cannot be reached or the URI holds nothing.
    """
    if is_local(uri):
        root = local_path(uri)
        if root.is_file():
            return Listing(((("", root.stat().st_size)),), root.stat().st_size)
        if not root.is_dir():
            raise StoreUnreachable(f"{uri} does not exist")
        found = sorted((str(f.relative_to(root)), f.stat().st_size) for f in root.rglob("*") if f.is_file())
    else:
        filesystem, path = _filesystem(uri)
        try:
            if filesystem.isfile(path):
                size = int(filesystem.info(path)["size"])
                return Listing(((("", size)),), size)
            entries = filesystem.find(path, detail=True)
        except FileNotFoundError as exc:
            raise StoreUnreachable(f"{uri} does not exist") from exc
        except Exception as exc:
            raise StoreUnreachable(f"{uri}: {exc}") from exc
        found = sorted(
            (key[len(path) :].lstrip("/"), int(info.get("size") or 0))
            for key, info in entries.items()
            if info.get("type") == "file"
        )
    if not found:
        raise StoreUnreachable(f"{uri} holds nothing")
    return Listing(tuple(found), sum(size for _, size in found))


def digest(uri: str, *, workers: int = WORKERS) -> str:
    """Return the sha256 a packet may record for what this URI holds.

    A single object is its own bytes, which is what every other format means by a checksum.

    A **prefix is not one object**, so a digest over it has to be defined rather than assumed:
    this is sha256 over a canonical JSON listing of ``[key, size, sha256]`` per member, sorted
    by key. Reproducible without knowing how the store enumerates, independent of chunk
    ordering, and each member stays independently checkable. See R36.

    Reading every byte is the cost -- 6.8 GB for a session's LFP -- which is why nothing calls
    this unless asked.

    Members are digested concurrently. An object store rewards that far more than any choice of
    client does: one LFP array of 208 objects reads at 15.7 MB/s one at a time and 94 MB/s across
    eight, where swapping the client for another changes it by a quarter. A local store is not
    hurt by it.

    Parameters
    ----------
    uri : str
        What to digest.
    workers : int, optional
        How many members to read at once. One reads sequentially.

    Raises
    ------
    StoreUnreachable
        If the store cannot be reached.
    """
    found = listing(uri)
    if found.is_single_object:
        return _member_digest(uri, "")
    keys = [key for key, _ in found.members]
    if workers > 1 and len(keys) > 1:
        # `map` preserves order, which the canonical listing depends on.
        with ThreadPoolExecutor(min(workers, len(keys))) as pool:
            digested = list(pool.map(lambda key: _member_digest(uri, key), keys))
    else:
        digested = [_member_digest(uri, key) for key in keys]
    rows = [[key, size, sha] for (key, size), sha in zip(found.members, digested, strict=True)]
    canonical = json.dumps(rows, separators=(",", ":"), sort_keys=False, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def read_member(uri: str, key: str) -> bytes:
    """Read one member of a store whole -- a metadata document, not a chunk.

    Raises
    ------
    StoreUnreachable
        If the store or the member cannot be reached.
    """
    try:
        if is_local(uri):
            return (local_path(uri) / key if key else local_path(uri)).read_bytes()
        filesystem, path = _filesystem(uri)
        with filesystem.open(f"{path}/{key}" if key else path, "rb") as handle:
            data: bytes = handle.read()
        return data
    except StoreUnreachable:
        raise
    except Exception as exc:
        raise StoreUnreachable(f"{uri}/{key}: {exc}") from exc


def _member_digest(uri: str, key: str) -> str:
    """sha256 of one member, streamed so a large chunk is never held whole."""
    digested = hashlib.sha256()
    if is_local(uri):
        target = local_path(uri) / key if key else local_path(uri)
        with target.open("rb") as handle:
            while block := handle.read(BLOCK):
                digested.update(block)
        return digested.hexdigest()
    filesystem, path = _filesystem(uri)
    with filesystem.open(f"{path}/{key}" if key else path, "rb") as handle:
        while block := handle.read(BLOCK):
            digested.update(block)
    return digested.hexdigest()


__all__ = [
    "BLOCK",
    "WORKERS",
    "Listing",
    "StoreUnreachable",
    "digest",
    "is_local",
    "listing",
    "local_path",
    "read_member",
]

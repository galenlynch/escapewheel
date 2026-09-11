"""Reach an external resource's bytes, wherever they are.

`04` §5.1 makes referencing the expected form for a large resource, and in production that means
an object store. What a packet may then say about those bytes is bounded by two things.

**Nothing here runs by default.** `04` §5.3 keeps structural validation off the network:
reachability, credentials and whether the caller is offline are properties of a situation, not
of a packet. Every function in this module is reached only from an explicitly requested mode.

**What is verified is a point in time.** `03` §8: immutability covers packet-owned bytes,
and an external resource may change or vanish without the packet changing at all. So these
return what was true when they looked, which is what `verified_at` records beside them.

This lives with the validator rather than the reader because **no read path uses it**. A table
resolves to a local path or is handed to DuckDB as a URI; a Zarr array is handed its URI and its
own library opens it. What needs a store client is R36's verification -- list a prefix, and hash
its members -- and both users of it are on that side: this package checks what a manifest claims,
and `escapewheel-writer` establishes it in the first place through its `verify` setting. The writer
depends on this package already, because `05`'s commit is validate-then-rename.

A local path needs no library. Any other scheme goes through fsspec, which is not a dependency
of this package -- the `remote` extra brings it, and a backend for the scheme is separate again
(`s3fs` for `s3://`, `gcsfs` for `gs://`).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
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


#: How many of a prefix's members to read at once when digesting (`04` §5.4). Object stores are
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
class StoreDigest:
    """A content hash the store computed itself, in the store's own algorithm (`04` §5.4).

    Never a substitute for sha256: it answers whether anything changed in place, not whether
    these are the bytes a manifest describes.
    """

    algorithm: str
    value: str


@dataclass(frozen=True)
class Member:
    """One object under a prefix.

    Attributes
    ----------
    key : str
        Relative to the URI, with `/` separators. Empty for a single-object resource.
    size_bytes : int
        What the store reports.
    store_digest : StoreDigest or None
        Present only where the store hands one over with the listing and it is a content hash
        of the whole object. A local filesystem offers none.
    """

    key: str
    size_bytes: int
    store_digest: StoreDigest | None = None


@dataclass(frozen=True)
class Listing:
    """What a store holds under one URI.

    Attributes
    ----------
    members : tuple of Member
        Every object, keyed relative to the URI and sorted by key. A single-object resource has
        one member whose key is the empty string.
    size_bytes : int
        Total across the members.
    """

    members: tuple[Member, ...]
    size_bytes: int

    @property
    def is_single_object(self) -> bool:
        """Whether the URI names one object rather than a prefix of many."""
        return len(self.members) == 1 and self.members[0].key == ""

    @property
    def digested_by_store(self) -> int:
        """How many members the store offered a usable content hash for."""
        return sum(1 for member in self.members if member.store_digest is not None)


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
            return Listing((Member("", root.stat().st_size),), root.stat().st_size)
        if not root.is_dir():
            raise StoreUnreachable(f"{uri} does not exist")
        found = [Member(str(f.relative_to(root)), f.stat().st_size) for f in root.rglob("*") if f.is_file()]
    else:
        filesystem, path = _filesystem(uri)
        try:
            if filesystem.isfile(path):
                info = filesystem.info(path)
                return Listing((Member("", int(info["size"]), store_digest(info)),), int(info["size"]))
            entries = filesystem.find(path, detail=True)
        except FileNotFoundError as exc:
            raise StoreUnreachable(f"{uri} does not exist") from exc
        except Exception as exc:
            raise StoreUnreachable(f"{uri}: {exc}") from exc
        found = [
            Member(key[len(path) :].lstrip("/"), int(info.get("size") or 0), store_digest(info))
            for key, info in entries.items()
            if info.get("type") == "file"
        ]
    if not found:
        raise StoreUnreachable(f"{uri} holds nothing")
    found.sort(key=lambda member: member.key)
    return Listing(tuple(found), sum(member.size_bytes for member in found))


def store_digest(info: Mapping[str, Any]) -> StoreDigest | None:
    """Return what a listing entry says about its own content, or None where it says nothing.

    S3 hands an ETag back with the listing at no extra request, and for a **single-part** object
    that ETag is the MD5 of its content. Three things disqualify one (R51 §1.1):

    - A multipart ETag is a hash of part hashes with the part count appended, so the same bytes
      uploaded with a different part size give a different value. It says nothing portable and
      MUST NOT be recorded.
    - Anything that is not 32 hex digits is not an MD5, whatever the store called it.
    - A store that offers no ETag at all -- every local filesystem -- offers nothing to record.
    """
    raw = info.get("ETag") or info.get("etag")
    if not isinstance(raw, str):
        return None
    value = raw.strip('"')
    if len(value) != 32 or any(character not in "0123456789abcdef" for character in value.lower()):
        return None
    return StoreDigest("md5", value.lower())


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
    keys = [member.key for member in found.members]
    if workers > 1 and len(keys) > 1:
        # `map` preserves order, which the canonical listing depends on.
        with ThreadPoolExecutor(min(workers, len(keys))) as pool:
            digested = list(pool.map(lambda key: _member_digest(uri, key), keys))
    else:
        digested = [_member_digest(uri, key) for key in keys]
    rows = [[m.key, m.size_bytes, sha] for m, sha in zip(found.members, digested, strict=True)]
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
    "Member",
    "StoreDigest",
    "StoreUnreachable",
    "digest",
    "is_local",
    "listing",
    "local_path",
    "read_member",
    "store_digest",
]

"""Reach an external resource's bytes, wherever they are (Part 04 §5.3).

Listing:

- :func:`listing` -- what a URI holds, as a :class:`Listing` of each :class:`Member`, without
  reading any of it.
- :class:`StoreDigest`, :func:`store_digest` -- a store's entity tag for an object, and the one a
  listing entry carries.
- :func:`read_member` -- one member read whole.
- :func:`is_local`, :func:`local_path` -- whether a URI names a filesystem path, and that path.

Digests (Part 04 §4.3):

- :func:`digest_resource` -- what a URI holds as a :class:`Digested`: its value, its members'
  values, and the route that established them.
- :func:`digest` -- that value alone, reading every byte.
- :func:`listing_digest` -- a prefix's value from its members' keys, sizes and values.
- :func:`hasher` -- a streaming hasher for one of :data:`ALGORITHMS`.
- :func:`store_checksums`, :func:`reported_checksum` -- the full-object checksums a store response
  reports, and the one a store reports for an object.
- :data:`ALGORITHMS`, :data:`ROUTES` -- the admitted digest functions, and the ways a digest is
  established.
- :data:`crc64nvme_python`, :data:`crc32c_python` -- the CRCs used where no native library is
  installed.

Failures:

- :exc:`.StoreUnreachable`, :exc:`.ResourceMissing` -- the store could not be reached, or was
  reached and holds nothing under the URI.

No function here runs unless the caller asks for a mode, and each result states what was true when
the function looked. A local path needs no library. Any other scheme needs fsspec, which the
`remote` extra installs, and a backend for that scheme.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import zlib
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .errors import ResourceMissing, StoreUnreachable

#: Bytes per read when digesting. Large enough that a remote store is not asked a thousand
#: times for a chunk it would have streamed, small enough to bound memory whatever an array's size.
BLOCK = 1 << 22


def is_local(uri: str) -> bool:
    """Whether a URI names a filesystem path this can open without a backend.

    A single-letter scheme is a Windows drive rather than a URI scheme.
    """
    scheme = urlparse(uri).scheme
    return not scheme or scheme == "file" or len(scheme) == 1


def local_path(uri: str) -> Path:
    """Return the path a local URI names."""
    return Path(unquote(urlparse(uri).path)) if urlparse(uri).scheme == "file" else Path(uri)


#: How many of a prefix's members to read at once when digesting (Part 04 §5.4). Object stores are
#: latency-bound per object, so reading several at once is several times faster; the value is
#: modest because a store also rate-limits, and the gain is mostly had by the eighth worker.
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


#: Each admitted digest function and the hexadecimal width of a single object's value (Part 04 §4.3).
#: A prefix's value is a SHA-256 under every algorithm, so it is always 64 digits.
ALGORITHMS: Mapping[str, int] = {"sha256": 64, "crc64nvme": 16, "crc32c": 8, "crc32": 8}

#: How a route establishes a digest (Part 04 §5.3): read every byte, take the store's full-object
#: checksums, or both across a prefix's objects.
ROUTES = ("computed", "store", "combined")


def _reflected_table(polynomial: int) -> tuple[int, ...]:
    table = []
    for byte in range(256):
        value = byte
        for _ in range(8):
            value = (value >> 1) ^ polynomial if value & 1 else value >> 1
        table.append(value)
    return tuple(table)


def _reflected_crc(polynomial: int, bits: int) -> Callable[[int, bytes], int]:
    """Build a reflected CRC with all-ones initial value and final XOR, continued from a previous value."""
    table, mask = _reflected_table(polynomial), (1 << bits) - 1

    def extend(previous: int, block: bytes) -> int:
        register = previous ^ mask
        for byte in block:
            register = table[(register ^ byte) & 0xFF] ^ (register >> 8)
        return register ^ mask

    return extend


#: Pure-Python fallbacks, used only where the native library is not installed; they run at a few
#: MB/s, where `awscrt` and `google-crc32c` run at the speed of memory.
crc64nvme_python = _reflected_crc(0x9A6C9329AC4BC9B5, 64)
crc32c_python = _reflected_crc(0x82F63B78, 32)


def _crc64nvme() -> Callable[[int, bytes], int]:
    try:
        from awscrt.checksums import crc64nvme  # type: ignore[import-not-found]  # optional
    except ImportError:
        return crc64nvme_python
    return lambda previous, block: int(crc64nvme(block, previous))


def _crc32c() -> Callable[[int, bytes], int]:
    try:
        import google_crc32c  # type: ignore[import-not-found]  # optional; zarr brings it
    except ImportError:
        return crc32c_python
    return lambda previous, block: int(google_crc32c.extend(previous, block))


class _Crc:
    def __init__(self, extend: Callable[[int, bytes], int], digits: int) -> None:
        self._extend, self._digits, self._value = extend, digits, 0

    def update(self, block: bytes) -> None:
        self._value = self._extend(self._value, block)

    def hexdigest(self) -> str:
        return f"{self._value:0{self._digits}x}"


def hasher(algorithm: str) -> Any:
    """Return a streaming hasher for one admitted algorithm, with `update` and `hexdigest`.

    Raises
    ------
    ValueError
        If the algorithm is not one Part 04 §4.3 admits.
    """
    if algorithm == "sha256":
        return hashlib.sha256()
    if algorithm == "crc64nvme":
        return _Crc(_crc64nvme(), 16)
    if algorithm == "crc32c":
        return _Crc(_crc32c(), 8)
    if algorithm == "crc32":
        return _Crc(lambda previous, block: zlib.crc32(block, previous), 8)
    raise ValueError(f"{algorithm!r} is not an admitted digest algorithm; expected one of {', '.join(ALGORITHMS)}")


def listing_digest(rows: Iterable[tuple[str, int, str]]) -> str:
    r"""Part 04 §4.3's prefix value: SHA-256 of the compact JSON listing, sorted by key bytes.

    Each key is the object's path relative to the resource, never percent-encoded. Python's encoder
    without ASCII escaping writes a string exactly as RFC 8785, Section 3.2.2.2 does: `\"`, `\\`,
    the five short escapes, `\u00xx` in lowercase for the rest of U+0000 to U+001F, and every other
    code point as its UTF-8.
    """
    ordered = sorted(((str(key), int(size), str(value)) for key, size, value in rows), key=lambda row: row[0].encode())
    canonical = json.dumps([list(row) for row in ordered], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StoreDigest:
    """What a store says about an object, recorded as evidence of change in place (Part 04 §5.4).

    Never a digest of the object's bytes: an entity tag is recorded verbatim under `etag`, and it
    answers whether anything changed in place, not whether these are the bytes a manifest describes.
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
        The store's entity tag where the listing carries one. A local filesystem offers none.
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
        """How many members the store offered an entity tag for."""
        return sum(1 for member in self.members if member.store_digest is not None)


def listing(uri: str) -> Listing:
    """List what a URI holds, without reading any of it.

    A dense array asset is a *prefix*, not an object: its chunk objects plus its metadata
    document. Sizing it is therefore a list operation, and the total is what `size_bytes` means
    for such a resource.

    Raises
    ------
    ResourceMissing
        If the URI names nothing, or a prefix holding no object, which Part 04 §4.3 reads as the
        same thing.
    StoreUnreachable
        If the store cannot be reached.
    """
    if is_local(uri):
        root = local_path(uri)
        if root.is_file():
            return Listing((Member("", root.stat().st_size),), root.stat().st_size)
        if not root.is_dir():
            raise ResourceMissing(f"{uri} does not exist")
        found = [Member(f.relative_to(root).as_posix(), f.stat().st_size) for f in root.rglob("*") if f.is_file()]
    else:
        filesystem, path = _filesystem(uri)
        try:
            if filesystem.isfile(path):
                info = filesystem.info(path)
                return Listing((Member("", int(info["size"]), store_digest(info)),), int(info["size"]))
            entries = filesystem.find(path, detail=True)
        except FileNotFoundError as exc:
            raise ResourceMissing(f"{uri} does not exist") from exc
        except Exception as exc:
            raise StoreUnreachable(f"{uri}: {exc}") from exc
        found = [
            Member(key[len(path) :].lstrip("/"), int(info.get("size") or 0), store_digest(info))
            for key, info in entries.items()
            if info.get("type") == "file"
        ]
    if not found:
        raise ResourceMissing(f"{uri} holds no object, so it does not exist (Part 04 §4.3)")
    found.sort(key=lambda member: member.key.encode())
    return Listing(tuple(found), sum(member.size_bytes for member in found))


def store_digest(info: Mapping[str, Any]) -> StoreDigest | None:
    """Return a listing entry's entity tag, verbatim under `etag`, or None where it has none.

    Part 04 §5.4 records an entity tag whatever produced it -- a multipart upload, an encrypted
    object -- because it is compared only with itself, never read as the bytes' digest.
    """
    raw = info.get("ETag") or info.get("etag")
    return StoreDigest("etag", raw) if isinstance(raw, str) and raw else None


#: S3's checksum members, by the algorithm each carries.
_S3_CHECKSUMS = {
    "ChecksumSHA256": "sha256",
    "ChecksumCRC64NVME": "crc64nvme",
    "ChecksumCRC32C": "crc32c",
    "ChecksumCRC32": "crc32",
}


def store_checksums(info: Mapping[str, Any]) -> dict[str, str]:
    """Return the full-object checksums a store response reports, in Part 04 §4.3's form.

    S3 reports a value as full-object only under `ChecksumType: FULL_OBJECT`; a composite value,
    derived from the parts, is never returned. Google Cloud Storage's `crc32c` always covers the
    whole object. Each value is base64 of the checksum's big-endian bytes, and one that does not
    decode to its algorithm's width is dropped rather than guessed at.
    """
    reported: dict[str, str] = {}
    if info.get("ChecksumType") == "FULL_OBJECT":
        for member, algorithm in _S3_CHECKSUMS.items():
            if isinstance(value := info.get(member), str):
                reported[algorithm] = value
    if isinstance(value := info.get("crc32c"), str):
        reported.setdefault("crc32c", value)
    converted = {}
    for algorithm, value in reported.items():
        try:
            raw = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            continue
        if len(raw) * 2 == ALGORITHMS[algorithm]:
            converted[algorithm] = raw.hex()
    return converted


def reported_checksum(uri: str, key: str, algorithm: str) -> str | None:
    """Return the store's full-object value for one object under `algorithm`, or None.

    One request per object: S3's listing names a checksum's algorithm but not its value, so this
    asks `HeadObject` with checksums enabled where the backend is s3fs, and otherwise takes what
    the backend's `info` reports. A local filesystem keeps no checksum.
    """
    if is_local(uri):
        return None
    filesystem, path = _filesystem(uri)
    target = f"{path}/{key}" if key else path
    info: Mapping[str, Any] | None = None
    try:
        if hasattr(filesystem, "call_s3") and hasattr(filesystem, "split_path"):
            bucket, name, version = filesystem.split_path(target)
            info = filesystem.call_s3(
                "head_object",
                Bucket=bucket,
                Key=name,
                ChecksumMode="ENABLED",
                **({"VersionId": version} if version else {}),
            )
        else:
            info = filesystem.info(target)
    except Exception:  # noqa: BLE001 - a store that will not say is read instead
        return None
    return store_checksums(info or {}).get(algorithm)


@dataclass(frozen=True)
class Digested:
    """A resource's digest, and how it was established.

    Attributes
    ----------
    algorithm : str
        The function, one of :data:`ALGORITHMS`.
    value : str
        The resource's value: the object's own for a single object, the listing's for a prefix.
    members : tuple of str
        Each object's single-object value, in `found.members` order.
    found : Listing
        The listing the value covers.
    route : str
        One of :data:`ROUTES`.
    """

    algorithm: str
    value: str
    members: tuple[str, ...]
    found: Listing
    route: str


def digest_resource(
    uri: str, algorithm: str = "sha256", *, workers: int = WORKERS, store_checksums: bool = False
) -> Digested:
    """Establish the Part 04 §4.3 digest of what a URI holds.

    Reading every byte is the cost, which is why nothing calls this unless asked. With
    `store_checksums`, an object whose store reports a full-object value in `algorithm` is not
    read (Part 04 §5.3); one whose store reports none still is.

    Objects are digested concurrently. An object store rewards that far more than any choice of
    client does, and a local store is not hurt by it.

    Parameters
    ----------
    uri : str
        What to digest.
    algorithm : str, default "sha256"
        One of :data:`ALGORITHMS`.
    workers : int, optional
        How many objects to handle at once. One is sequential.
    store_checksums : bool, default False
        Take the store's full-object checksums where it reports them.

    Raises
    ------
    ResourceMissing
        If the URI names nothing, or an empty prefix.
    StoreUnreachable
        If the store cannot be reached.
    ValueError
        If `algorithm` is not admitted.
    """
    hasher(algorithm)
    found = listing(uri)
    keys = [member.key for member in found.members]

    def one(key: str) -> tuple[str, bool]:
        if store_checksums and (reported := reported_checksum(uri, key, algorithm)) is not None:
            return reported, True
        return _member_digest(uri, key, algorithm), False

    if workers > 1 and len(keys) > 1:
        # `map` preserves order, which pairs each value with its member.
        with ThreadPoolExecutor(min(workers, len(keys))) as pool:
            results = list(pool.map(one, keys))
    else:
        results = [one(key) for key in keys]
    values = tuple(value for value, _ in results)
    from_store = sum(1 for _, stored in results if stored)
    route = "store" if from_store == len(results) else "computed" if from_store == 0 else "combined"
    if found.is_single_object:
        return Digested(algorithm, values[0], (), found, route)
    rows = [(member.key, member.size_bytes, value) for member, value in zip(found.members, values, strict=True)]
    return Digested(algorithm, listing_digest(rows), values, found, route)


def digest(uri: str, algorithm: str = "sha256", *, workers: int = WORKERS) -> str:
    """Return the Part 04 §4.3 value a packet may record for what this URI holds, reading every byte.

    Raises
    ------
    ResourceMissing
        If the URI names nothing, or an empty prefix.
    StoreUnreachable
        If the store cannot be reached.
    """
    return digest_resource(uri, algorithm, workers=workers).value


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


def _member_digest(uri: str, key: str, algorithm: str = "sha256") -> str:
    """One object's single-object value, streamed so a large chunk is never held whole."""
    digested = hasher(algorithm)
    if is_local(uri):
        target = local_path(uri) / key if key else local_path(uri)
        with target.open("rb") as handle:
            while block := handle.read(BLOCK):
                digested.update(block)
        return str(digested.hexdigest())
    filesystem, path = _filesystem(uri)
    with filesystem.open(f"{path}/{key}" if key else path, "rb") as handle:
        while block := handle.read(BLOCK):
            digested.update(block)
    return str(digested.hexdigest())


__all__ = [
    "ALGORITHMS",
    "BLOCK",
    "ROUTES",
    "WORKERS",
    "Digested",
    "Listing",
    "Member",
    "StoreDigest",
    "digest",
    "digest_resource",
    "hasher",
    "is_local",
    "listing",
    "listing_digest",
    "local_path",
    "read_member",
    "reported_checksum",
    "store_checksums",
    "store_digest",
]

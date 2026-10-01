"""Acquire the registry documents a packet binds (Part 04 §8, Part 03 §3.3).

- :func:`acquire` -- one bound registry's bytes, verified against its descriptor's digest.
- :func:`parse` -- verified bytes decoded for declaration lookup.
- :func:`gunzip_member` -- exactly one gzip member, decompressed.

A registry is read only from its descriptor's path and only after its digest matches; no other copy
stands in for it.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from typing import Any

from .errors import RegistryFault, RegistryUnavailable
from .location import Location
from .manifest import RegistryBinding


def gunzip_member(data: bytes) -> bytes:
    """Decompress exactly one gzip member, ignoring its header fields (Part 03 §3.3).

    Parameters
    ----------
    data : bytes
        The stored bytes.

    Returns
    -------
    bytes
        The decompressed member.

    Raises
    ------
    ValueError
        If the bytes are not one complete gzip member with nothing after it. `gzip.decompress`
        would silently concatenate a second member.
    """
    inflater = zlib.decompressobj(wbits=zlib.MAX_WBITS | 16)
    try:
        decoded = inflater.decompress(data) + inflater.flush()
    except zlib.error as exc:
        raise ValueError(f"not a gzip member: {exc}") from exc
    if not inflater.eof:
        raise ValueError("the gzip member is truncated")
    if inflater.unused_data:
        raise ValueError("bytes follow the first gzip member")
    return decoded


def _contained(path: str) -> bool:
    """Whether a descriptor path stays under the packet root, so reading it cannot escape."""
    segments = path.split("/")
    return (
        bool(path)
        and "\\" not in path
        and ":" not in segments[0]
        and not path.startswith("/")
        and all(segment not in {"", ".", ".."} for segment in segments)
    )


def acquire(root: Location, binding: RegistryBinding) -> bytes:
    """Read one bound registry's exact document bytes and verify them against its descriptor.

    Parameters
    ----------
    root : Location
        The packet root.
    binding : RegistryBinding
        The descriptor naming the registry.

    Returns
    -------
    bytes
        The decompressed document, whose SHA-256 equals the descriptor's.

    Raises
    ------
    RegistryUnavailable
        With reason `MISSING`, `UNREADABLE`, or `DIGEST`.
    """
    if not _contained(binding.path):
        raise RegistryUnavailable(
            binding.registry_id, RegistryFault.UNREADABLE, f"{binding.path!r} is not under the packet root"
        )
    location = root.join(binding.path)
    try:
        stored = location.read_bytes()
    except FileNotFoundError:
        raise RegistryUnavailable(binding.registry_id, RegistryFault.MISSING, f"nothing at {location}") from None
    except Exception as exc:
        raise RegistryUnavailable(
            binding.registry_id, RegistryFault.UNREADABLE, f"cannot read {location}: {exc}"
        ) from exc
    try:
        document = gunzip_member(stored)
    except ValueError as exc:
        raise RegistryUnavailable(binding.registry_id, RegistryFault.UNREADABLE, f"{location}: {exc}") from exc
    if hashlib.sha256(document).hexdigest() != binding.sha256:
        raise RegistryUnavailable(
            binding.registry_id, RegistryFault.DIGEST, f"{location} does not match its recorded sha256"
        )
    return document


def parse(binding: RegistryBinding, document: bytes) -> dict[str, Any]:
    """Decode verified registry bytes for declaration lookup, without checking the registry.

    Parameters
    ----------
    binding : RegistryBinding
        The descriptor the bytes were acquired through.
    document : bytes
        What :func:`acquire` returned.

    Returns
    -------
    dict
        The registry document.

    Raises
    ------
    RegistryUnavailable
        With reason `INVALID` where the bytes are not a JSON object.
    """
    try:
        parsed = json.loads(document)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryUnavailable(binding.registry_id, RegistryFault.INVALID, f"not JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RegistryUnavailable(binding.registry_id, RegistryFault.INVALID, "not a JSON object")
    return parsed


__all__ = ["acquire", "gunzip_member", "parse"]

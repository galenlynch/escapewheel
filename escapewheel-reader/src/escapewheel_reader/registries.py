"""Acquire the registry documents a packet binds (Part 04 §8).

- :func:`acquire` -- one bound registry's bytes, verified against its descriptor's digest.
- :func:`parse` -- verified bytes decoded for declaration lookup.
- :func:`gunzip_member` -- exactly one gzip member, decompressed.
- :func:`declared_tables` -- the tables a registry document declares.

A registry is read only from its descriptor's path and only after its digest matches; no other copy
stands in for it.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from collections.abc import Mapping
from typing import Any

from .errors import RegistryFault, RegistryUnavailable
from .location import Location
from .manifest import RegistryBinding


def gunzip_member(data: bytes) -> bytes:
    """Decompress exactly one gzip member, ignoring its header fields (Part 03 §3.2).

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


def declared_tables(document: Mapping[str, Any] | None, *, strict: bool = False) -> dict[str, Any]:
    """Return each table a registry document declares, by its resource ID.

    A resource of another kind declares no table and is left out.

    Parameters
    ----------
    document : Mapping or None
        A parsed registry document, or None where the caller holds none.
    strict : bool, default False
        Whether the document is taken to be valid. Where it is not, no document, a document without
        `resources`, a resource without a `kind` and a table resource without a `table` each declare
        nothing, which is what reading a document nobody has checked needs.

    Returns
    -------
    dict
        Each table declaration, in the document's order.

    Raises
    ------
    KeyError
        Under `strict`, where the document lacks `resources`, a resource lacks `kind`, or a table
        resource lacks `table`.
    TypeError
        Under `strict`, where there is no document.
    """
    if strict:
        if document is None:
            raise TypeError("a strict reading needs a registry document")
        return {
            str(name): declaration["table"]
            for name, declaration in document["resources"].items()
            if declaration["kind"] == "table"
        }
    return {
        str(name): declaration["table"]
        for name, declaration in (document or {}).get("resources", {}).items()
        if declaration.get("kind") == "table" and "table" in declaration
    }


__all__ = ["acquire", "declared_tables", "gunzip_member"]

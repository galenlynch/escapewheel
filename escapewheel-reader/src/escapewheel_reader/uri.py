"""A manifest `uri`'s two forms, and the one spelling of a relative reference (Part 03 §4).

- :func:`decode`, :func:`encode` -- a relative reference as the names it appends, and back.
- :func:`canonical`, :func:`in_one_form` -- rewrite a reference in the one form, or check it is.
- :func:`is_absolute` -- whether a `uri` has a scheme.
- :func:`representable` -- whether a packet can hold a file under a name.

A relative reference appends its decoded names to a root, never by RFC 3986's merge, and names are
kept byte-exact.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import quote, unquote_to_bytes

#: RFC 3986, Section 3.1's scheme, followed by ``://``, which is what the manifest schemas treat as absolute.
ABSOLUTE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")

#: One RFC 3986, Section 3.3 segment of at least one pchar, in any spelling RFC 3986 admits.
_SEGMENT = re.compile(r"(?:[A-Za-z0-9._~!$&'()*+,;=:@-]|%[0-9A-Fa-f]{2})+")


def is_absolute(uri: str) -> bool:
    """Whether a manifest `uri` is absolute: a scheme followed by `://`."""
    return ABSOLUTE.match(uri) is not None


def representable(name: str) -> bool:
    """Whether a packet can hold a file or directory under this name (Part 03 §11).

    Nonempty, valid UTF-8, holding neither NUL nor `/`, and neither `.` nor `..`. A `str` holding a
    lone surrogate, as `os.fsdecode` makes of bytes that are not UTF-8, is not valid UTF-8.
    """
    if not name or name in (".", "..") or "\0" in name or "/" in name:
        return False
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def encode(names: Iterable[str]) -> str:
    """Spell a sequence of names as a relative reference in the one form.

    Every unreserved character as itself and every other octet of the UTF-8 encoding as `%XX` with
    uppercase hexadecimal digits, which is what `quote` writes with nothing marked safe.

    Raises
    ------
    ValueError
        If there are no names, or one is not representable.
    """
    listed = list(names)
    if not listed:
        raise ValueError("a relative reference has at least one segment")
    for name in listed:
        if not representable(name):
            raise ValueError(f"{name!r} is not a representable name")
    return "/".join(quote(name, safe="", encoding="utf-8", errors="strict") for name in listed)


def decode(reference: str) -> tuple[str, ...]:
    """Read a relative reference, in any spelling RFC 3986 admits, as the names it appends.

    Raises
    ------
    ValueError
        If it is absolute, empty, begins with `/`, has an empty segment or one outside RFC 3986's
        segment grammar, has a `:` in its first segment (which RFC 3986 would read as a scheme),
        or has a segment that does not decode to a representable name.
    """
    if is_absolute(reference):
        raise ValueError(f"{reference!r} is absolute, not a relative reference")
    if not reference:
        raise ValueError("an empty uri is not a relative reference")
    if reference.startswith("/"):
        raise ValueError(f"{reference!r} begins with '/'")
    segments = reference.split("/")
    names = []
    for position, segment in enumerate(segments, start=1):
        if not segment:
            raise ValueError(f"{reference!r} has an empty segment")
        if _SEGMENT.fullmatch(segment) is None:
            raise ValueError(f"{reference!r}: segment {segment!r} is not an RFC 3986 segment")
        if position == 1 and ":" in segment:
            raise ValueError(f"{reference!r}: a ':' in the first segment would be read as a scheme")
        try:
            name = unquote_to_bytes(segment).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{reference!r}: segment {segment!r} does not decode to UTF-8") from exc
        if not representable(name):
            raise ValueError(f"{reference!r}: segment {segment!r} decodes to {name!r}, which is not representable")
        names.append(name)
    return tuple(names)


def canonical(reference: str) -> str:
    """Rewrite a relative reference in the one form, as a build records a resource document's.

    Raises
    ------
    ValueError
        As :func:`decode` does.
    """
    return encode(decode(reference))


def in_one_form(uri: str) -> bool:
    """Whether a manifest `uri` passes `packet.resource.uri_form`: absolute, or a relative reference in the one form."""
    if is_absolute(uri):
        return True
    try:
        return canonical(uri) == uri
    except ValueError:
        return False


__all__ = ["canonical", "decode", "encode", "in_one_form", "is_absolute", "representable"]

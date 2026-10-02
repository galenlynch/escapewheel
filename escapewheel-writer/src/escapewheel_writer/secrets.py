"""What this build recognizes as a credential in a recipe, and how it withholds one (Part 05 §3.2, §7).

- :func:`carries_a_secret` -- whether a member is a credential, by its name.
- :func:`userinfo` -- the userinfo a URI states.
- :func:`without_userinfo` -- a URI less its userinfo.
- :func:`stated_userinfo` -- the userinfo of every URI a recipe states.
- :func:`as_returned` -- a URI an adapter returned, less userinfo the recipe also states.
- :func:`redacted` -- a recipe document, or a value of one, as a build records it.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from typing import Any

#: Members that carry a credential itself rather than a reference to one. The names are fsspec's
#: and its backends': s3fs, gcsfs and adlfs each spell the pair their own way, and
#: `connection_string` carries both halves at once.
SECRETS = frozenset(
    {
        "account_key",
        "api_key",
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "client_secret",
        "connection_string",
        "credential",
        "credentials",
        "key",
        "passwd",
        "password",
        "private_key",
        "sas_token",
        "secret",
        "secret_key",
        "session_token",
        "token",
    }
)

#: What a `token` may say without being one. gcsfs takes a mode here as well as a credential, and
#: `token = "anon"` is how its own documentation reads a public bucket -- so the name alone does
#: not decide, and these are the values that name a way to authenticate rather than a secret.
TOKEN_MODES = frozenset({"anon", "browser", "cache", "cloud", "google_default"})

#: What a recorded recipe holds in place of a member this build withheld (Part 05 §3.2).
REDACTED = "[redacted]"

#: A URI's scheme and authority (RFC 3986 §3.2). The userinfo runs to the authority's last `@`,
#: so a password holding one unencoded is withheld whole.
_OPENING = re.compile(r"(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*://)(?:(?P<userinfo>[^/?#]*)@)?")


def carries_a_secret(name: str, value: Any) -> bool:
    """Whether one member of a recipe is a credential rather than a reference to one."""
    if name not in SECRETS:
        return False
    return not (name == "token" and isinstance(value, str) and value in TOKEN_MODES)


def userinfo(uri: str) -> str | None:
    """Return the userinfo a URI states, or None for a string stating none, a local path among them.

    Recognized whole, a name alone included, since a store takes a token in that place.
    """
    opening = _OPENING.match(uri)
    return opening["userinfo"] if opening else None


def without_userinfo(uri: str) -> str:
    """Return a URI less its userinfo, and any other string as it is (Part 05 §7).

    Nothing stands where the userinfo was: a marker there would make a string no URI parser reads.
    """
    opening = _OPENING.match(uri)
    return uri if not opening or opening["userinfo"] is None else opening["scheme"] + uri[opening.end() :]


def stated_userinfo(document: Any) -> frozenset[str]:
    """Return the userinfo of every URI a recipe document states, at any depth."""
    if isinstance(document, Mapping):
        document = list(document.values())
    if isinstance(document, list):
        return frozenset(found for item in document for found in stated_userinfo(item))
    found = userinfo(document) if isinstance(document, str) else None
    return frozenset() if found is None else frozenset({found})


def as_returned(uri: str, stated: Collection[str]) -> str:
    """Return a URI an adapter returned, less userinfo that a URI of the recipe states too (Part 05 §7).

    Any other userinfo is no value of the recipe, so the URI is written as the adapter returned it.
    """
    return without_userinfo(uri) if userinfo(uri) in stated else uri


def redacted(document: Any) -> Any:
    """Return a recipe document, or a value one states, as a build records it (Part 05 §3.2).

    A member named as a credential holds the marker, and a string that opens as a URI is written
    less its userinfo. Applied where a value is written down rather than at parse time, so a build
    still opens what the author declared, and to the whole document, since a recipe states a
    credential outside a source entry too.
    """
    if isinstance(document, Mapping):
        return {
            name: REDACTED if carries_a_secret(str(name), value) else redacted(value)
            for name, value in document.items()
        }
    if isinstance(document, list):
        return [redacted(item) for item in document]
    return without_userinfo(document) if isinstance(document, str) else document


__all__ = [
    "REDACTED",
    "SECRETS",
    "TOKEN_MODES",
    "as_returned",
    "carries_a_secret",
    "redacted",
    "stated_userinfo",
    "userinfo",
    "without_userinfo",
]

"""The storage options that carry a credential, and their redaction where a recipe is recorded (Part 05 §3.1)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: Storage options that carry a credential itself rather than a reference to one. Refused,
#: because a recipe is recorded inside the packet it builds -- `core.processing_runs.parameters`
#: carries the document verbatim -- so a key written here travels wherever the packet does, and
#: an environment that can be asked for one instead is available on every machine that has one.
#: The names are fsspec's and its backends': s3fs, gcsfs and adlfs each spell the pair their own
#: way, and `connection_string` carries both halves at once.
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

#: What a refused option is replaced by wherever a recipe is recorded.
REDACTED = "[redacted]"


def carries_a_secret(name: str, value: Any) -> bool:
    """Whether one storage option is a credential rather than a reference to one."""
    if name not in SECRETS:
        return False
    return not (name == "token" and isinstance(value, str) and value in TOKEN_MODES)


def redacted(document: Any) -> Any:
    """Return a recipe document with every credential replaced, for recording it.

    Applied wherever the recipe is written down rather than at parse time, so a build still opens
    what the author declared -- and applied to the whole document rather than to `storage_options`
    alone, because the next place a key gets written will not be the one this was built for.
    """
    if isinstance(document, Mapping):
        return {
            name: REDACTED if carries_a_secret(str(name), value) else redacted(value)
            for name, value in document.items()
        }
    if isinstance(document, list):
        return [redacted(item) for item in document]
    return document


__all__ = ["REDACTED", "SECRETS", "TOKEN_MODES", "carries_a_secret", "redacted"]

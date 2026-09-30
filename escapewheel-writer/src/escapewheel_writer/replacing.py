"""The packets a build replaces, read from its recipe's `[packet].replaces` (Part 05 §§3.5 and 9.3).

An entry is a packet root, whose `packet.json` is the manifest it published, or a manifest file,
such as one a packet retains under `manifests/`. Relative entries resolve against the recipe, as an
extension path does. Every refusal happens here, before any source opens.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
from escapewheel_validator.manifest import manifest_schema

from .writer import MANIFEST


class ReplacementRefused(Exception):
    """A recipe's `[packet].replaces` names what a build cannot replace (Part 05 §3.5)."""


@dataclass(frozen=True)
class Replaced:
    """One packet a build replaces, as the manifest read at its entry says."""

    entry: str
    packet_id: str
    packet_version: str
    #: The SHA-256 of the exact bytes read, which is what names the version (Part 04 §3).
    sha256: str
    resources: frozenset[str]

    def item(self) -> dict[str, str]:
        """Return the `replaces` item a manifest records for this packet."""
        return {"packet_id": self.packet_id, "packet_version": self.packet_version, "sha256": self.sha256}


def _identity_schema() -> dict[str, Any]:
    """Return the manifest schema's `packet_id` and `packet_version`, which an entry's manifest satisfies."""
    schema = manifest_schema()
    return {
        "type": "object",
        "required": ["packet_id", "packet_version"],
        "properties": {name: schema["properties"][name] for name in ("packet_id", "packet_version")},
    }


def read_replaced(entries: Iterable[str], base: Path) -> tuple[Replaced, ...]:
    """Read the manifest at each entry, refusing an unreadable one and two reading the same bytes.

    Raises
    ------
    ReplacementRefused
        Naming every entry refused.
    """
    identity = jsonschema.Draft202012Validator(_identity_schema())
    problems: list[str] = []
    read: list[Replaced] = []
    for entry in entries:
        path = base / entry
        path = path / MANIFEST if path.is_dir() else path
        try:
            body = path.read_bytes()
            manifest = json.loads(body)
        except (OSError, ValueError) as exc:
            problems.append(f"{entry}: no published manifest can be read ({type(exc).__name__})")
            continue
        errors = [] if not isinstance(manifest, dict) else [e.message for e in identity.iter_errors(manifest)]
        if not isinstance(manifest, dict) or errors:
            problems.append(f"{entry}: the manifest's packet_id or packet_version fails the manifest schema")
            continue
        entries_read = [r for r in manifest.get("resources", ()) if isinstance(r, Mapping) and "resource_id" in r]
        resources = frozenset(str(r["resource_id"]) for r in entries_read)
        read.append(
            Replaced(
                entry, manifest["packet_id"], manifest["packet_version"], hashlib.sha256(body).hexdigest(), resources
            )
        )
    by_digest: dict[str, list[str]] = {}
    for replaced in read:
        by_digest.setdefault(replaced.sha256, []).append(replaced.entry)
    problems += [f"{' and '.join(named)} read one manifest" for named in by_digest.values() if len(named) > 1]
    if problems:
        raise ReplacementRefused("; ".join(problems))
    return tuple(read)

"""Where the portable profile keeps a packet's parts under its root (Part 03 §3)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import opaque

#: Where the portable profile stores each bound registry, as `<registry_id>/<version>.json.gz`
#: (Part 03 §3.3).
REGISTRIES = "registries"

#: The directories under the packet root a commit promotes from its staging area, which a root holding
#: any of them without a committed manifest cannot take another commit into.
PROMOTED = ("tables", "arrays", opaque.ROOT, REGISTRIES)

#: The portable profile's staging area, directly under the packet root (Part 03 §3.4).
STAGING = "staging"

#: The promotion record inside the staging area (Part 05 §6). Its format is this writer's.
PROMOTION = "promotion.json"


def retained(manifest: Mapping[str, Any]) -> str:
    """Name a manifest's retained copy under `MANIFESTS_DIRNAME` by its version (Part 03 §3.1)."""
    return f"{manifest['packet_version']}.json"


__all__ = ["PROMOTED", "PROMOTION", "REGISTRIES", "STAGING", "retained"]

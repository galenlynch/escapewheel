"""The resources a build no longer carries, measured against a packet it replaces.

- :func:`lost` -- resource IDs the replaced packet carries and this build does not, sorted.
- :func:`resources` -- resource IDs a committed packet declares.

A loss is a warning and never an error: narrowing a packet is legitimate, and only the recipe's
author knows whether this narrowing was meant.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

#: A committed packet's manifest, which is the only file that lists every resource it holds.
MANIFEST = "packet.json"


def resources(packet: str | Path) -> set[str]:
    """Resource IDs a committed packet declares.

    Parameters
    ----------
    packet : str or Path
        A packet root, or the manifest itself.

    Returns
    -------
    set of str
        Every `resource_id` in the manifest, or an empty set where there is no manifest to
        read -- a first build has nothing to be compared against, which is not a failure.
    """
    path = Path(packet)
    manifest = path if path.is_file() else path / MANIFEST
    if not manifest.is_file():
        return set()
    try:
        parsed = json.loads(manifest.read_text())
    except json.JSONDecodeError:
        return set()
    return {r["resource_id"] for r in parsed.get("resources", []) if "resource_id" in r}


def lost(reference: Iterable[str], built: Iterable[str]) -> list[str]:
    """Resource IDs the reference carries and this build does not, sorted.

    Sorted rather than in manifest order so two runs of the same comparison report identically,
    which is what lets the line be diffed rather than only read.
    """
    return sorted(set(reference) - set(built))

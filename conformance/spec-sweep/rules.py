#!/usr/bin/env python3
"""Every rule an accepted revision specifies exists as a check a validator emits.

R18 §3 specified `core.spike_events.within_observation` and it was never implemented. The
gap survived acceptance, `registry/check.py`, and the conformance corpus, because all three
verify what the registry *contains* rather than what the revisions *asked for*.

Run with the validator installed:

    uv run --with ../../escapewheel-validator python rules.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# Ids a revision used before implementation settled on another name. Each entry records a
# rename, not a missing check -- verify before adding one.
ALIASES = {
    "manifest.sessions_match_core": "core.sessions.manifest_sessions_match",  # R1
    "core.spike_events.clock_resolves": "core.spike_events.clock_id_resolves",  # R5, generated
    "core.spike_events.unit_resolves": (  # R5, generated
        "core.spike_events.session_id_unit_id_sorting_run_id_curation_id_resolves"
    ),
    "core.spike_events.ticks_sorted_within_unit": "core.spike_events.physical_order",  # R5, moved to the shim by R12
}


def emitted() -> set[str]:
    """Every check id a validator can produce: generated, carried, and shim."""
    from escapewheel_validator import generate

    registry = json.loads((ROOT / "registry" / "logical_schemas.json").read_text())
    ids = {c.id for c in generate(registry, advisory=True)}
    shim = (
        ROOT
        / "escapewheel-validator"
        / "src"
        / "escapewheel_validator"
        / "validator.py"
    ).read_text()
    ids |= set(re.findall(r'report\.add\(\s*"[a-z]+",\s*"([a-z0-9_.]+)"', shim))
    ids |= set(re.findall(r'"([a-z0-9_.]+\.physical_order)"', shim))
    ids |= {
        f"{r}.physical_order" for r in registry["tables"]
    }  # built per resource at runtime
    return ids


def specified() -> list[tuple[str, str]]:
    """(revision, rule id) for every id named in an accepted revision's SQL block."""
    found = []
    for path in sorted((ROOT / "revisions").glob("*.md")):
        for block in re.findall(r"```sql\n(.*?)```", path.read_text(), re.S):
            for rule_id in re.findall(
                r"^--\s*((?:core|analysis|manifest)\.[a-z0-9_.]+)", block, re.M
            ):
                found.append((path.name, rule_id))
    return found


ids = emitted()
missing = [(rev, r) for rev, r in specified() if ALIASES.get(r, r) not in ids]

print(f"{len(ids)} check ids a validator can emit")
print(
    f"{len(specified())} rule ids named in revision SQL blocks, {len(ALIASES)} of them renamed since\n"
)
for revision, rule_id in missing:
    print(f"  MISSING  {rule_id:<50} {revision}")
print("  (none)" if not missing else f"\n{len(missing)} specified but not implemented")
sys.exit(1 if missing else 0)

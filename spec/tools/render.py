"""Render the registry as Markdown, so a table can be read without reading JSON.

This is generated from `logical_schemas.json` at build time, so it states the current registry
content and cannot drift from it.

It is not a standalone specification. The repository authority model identifies the sources that
bind; this rendering exposes the generated registry content for inspection.

    python render.py            # write the listing and the source guide's regions
    python render.py --check    # write nothing, and fail where either is stale
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from checkers.registry_conventions import name_columns
from specdoc import GenerationError, fill_regions, named_regions, region_names, registry_tables

HERE = Path(__file__).resolve().parent
REGISTRY = HERE.parent / "artifacts/logical_schemas.json"
OUT = HERE.parent / "informative/tables.md"

#: Part 02 §6's three presence states, rendered so the required ones stand out in a scan.
PRESENCE = {"required": "**required**", "nullable": "nullable", "optional": "optional"}


def _code(names: Any) -> str:
    """Render one name or a list of them as inline code."""
    if not names:
        return "—"
    if isinstance(names, str):
        return f"`{names}`"
    return ", ".join(f"`{n}`" for n in names)


def _declares(column: dict[str, Any]) -> str:
    """Render every declaration a column carries about its values (Part 02 §§5.4 and 9.3).

    The descriptions used to say these, because this table showed none of them and it is what a
    person reads. Generated from the field, so the two cannot disagree.
    """
    said = []
    if values := column.get("enum"):
        said.append("closed: " + ", ".join(f"`{v}`" for v in values))
    elif vocabulary := column.get("vocabulary"):
        said.append(vocabulary)
    if reserved := column.get("reserved_values"):
        said.append("reserving " + ", ".join(f"`{v}`" for v in reserved))
    if resolves := column.get("resolves"):
        said.append(f"resolves {resolves}")
    if authority := column.get("authority"):
        said.append(", ".join(f"[{a['name']}]({a['uri']})" for a in authority))
    if "finite" in column:
        said.append("finite" if column["finite"] else "admits non-finite")
    return "; ".join(said) or "—"


def _table(name: str, spec: dict[str, Any]) -> list[str]:
    """Render one table: its columns, then everything that constrains them."""
    out = [f"### `{name}`", ""]
    out += [
        "| Column | Type | Presence | Declares | Description |",
        "|---|---|:---:|---|---|",
    ]
    for column in spec["columns"]:
        description = (column.get("description") or "").replace("|", "\\|")
        out.append(
            f"| `{column['name']}` | {column['type']} | "
            f"{PRESENCE.get(column['presence'], column['presence'])} | "
            f"{_declares(column)} | "
            f"{description} |"
        )
    out.append("")

    key = spec.get("primary_key")
    out.append(f"**Primary key** — {_code(key) if key else 'none declared'}  ")
    out.append("")

    if references := spec.get("references"):
        out.append("**References**")
        out.append("")
        for ref in references:
            target = ", ".join(f"`{c}`" for c in ref["resource_columns"])
            specialising = f", specialising `{ref['specialises']}`" if "specialises" in ref else ""
            out.append(f"- {_code(ref['columns'])} → `{ref['resource']}` ({target}){specialising}")
        out.append("")

    groups = spec.get("amendment_groups")
    listed = " · ".join(f"({_code(group)})" for group in groups) if groups else "none"
    out.append(f"**Amendment groups** — {listed}  ")
    out.append("")

    if rules := spec.get("rules"):
        out.append(f"**Tier 2 rules** — {len(rules)}")
        out.append("")
        for rule in rules:
            level = rule.get("level", "error")
            advisory = " *(advisory)*" if rule.get("advisory") else ""
            out.append(f"- `{rule['id']}` — {level}{advisory}: {rule.get('message', '')}")
        out.append("")

    return out


def render(registry: dict[str, Any]) -> str:
    """Build the whole document."""
    resources = registry["resources"]
    tables = registry_tables(registry)
    columns = sum(len(t["columns"]) for t in tables.values())
    references = sum(len(t.get("references") or []) for t in tables.values())
    rules = sum(len(t.get("rules") or []) for t in tables.values())
    out = [
        "# Logical schemas, as the registry stands",
        "",
        "**Generated** by `tools/render.py` from `artifacts/logical_schemas.json`. Do not edit;",
        "run `python tools/build.py` to regenerate.",
        "",
        "This generated rendering is not a standalone specification. See",
        "[Part 00 §2](../parts/00_architecture.md#ew-specification-authority) for the sources that bind.",
        "",
        "```text",
        (
            f"{len(resources)} resources, {len(tables)} tables, {columns} columns, "
            f"{references} references, {rules} Tier 2 rules"
        ),
        (f"registry {registry.get('registry_version')}   logical standard {registry.get('logical_standard_version')}"),
        "```",
        "",
    ]

    namespaces: dict[str, list[str]] = {}
    for name in tables:
        namespaces.setdefault(name.split(".", 1)[0], []).append(name)

    out += ["## Contents", ""]
    for namespace, names in namespaces.items():
        listed = " · ".join(f"[`{n}`](#{n.replace('.', '')})" for n in names)
        out += [f"**{namespace}** ({len(names)}) — {listed}", ""]

    for namespace, names in namespaces.items():
        out += [f"## `{namespace}`", ""]
        for name in names:
            out += _table(name, tables[name])

    return "\n".join(out).rstrip() + "\n"


README = HERE.parent / "source/README.md"

#: Where the README's generated regions begin and end. A count stated in prose is a count that
#: goes stale: the README once disagreed with the generated registry's table and rule counts.
REGION = named_regions("generated")


def regions(registry: dict[str, Any]) -> dict[str, str]:
    """Return the README's generated regions, keyed by name.

    Only what the registry *declares*. How many Tier 1 checks that becomes is deliberately not
    here: it turns on which tables the shim's ordering scan settles uniqueness for, which is the
    validator's judgement, and a second implementation of it would drift.
    """
    resources = registry["resources"]
    tables = registry_tables(registry)
    columns = [c for t in tables.values() for c in t["columns"]]
    rules = [r for t in tables.values() for r in t["rules"]]
    levels = Counter(r["level"] for r in rules)
    declared = [
        (
            sum(1 for c in columns if c["presence"] == "required"),
            "required column, not null",
        ),
        (sum(len(t["references"]) for t in tables.values()), "reference, resolves"),
        (sum(1 for t in tables.values() if t["primary_key"]), "primary key, unique"),
        (sum(1 for c in columns if c.get("enum")), "closed vocabulary, member of"),
        (sum(1 for c in columns if c.get("finite") is True), "finite column, no NaN or infinity"),
        (sum(name_columns(tables).values()), "owned identifier's name, unique"),
        (
            sum(1 for c in columns if c.get("role") == "discriminator"),
            "discriminator, resolvable",
        ),
    ]
    by_table = sorted(
        ((n, t) for n, t in tables.items() if t["rules"]),
        key=lambda kv: (-len(kv[1]["rules"]), kv[0]),
    )
    return {
        "counts": (
            f"```\n{len(resources)} resources, {len(tables)} tables, {len(columns)} columns, "
            f"{sum(len(t['references']) for t in tables.values())} references, "
            f"{len(rules)} Tier 2 rules\n```"
        ),
        "structure": "```\n" + "\n".join(f"{n:<4}{label}" for n, label in declared) + "\n```",
        "rules": (
            f"{len(rules)} rules over {len(by_table)} tables: {levels['error']} error, "
            f"{levels['warning']} warning, {levels['info']} info — the "
            f"{sum(1 for r in rules if r.get('advisory'))} at `info` being the advisory ones "
            f"(Part 02 §10.2), off unless asked for.\n\n"
            "| Table | Rules |\n|---|---:|\n" + "\n".join(f"| `{n}` | {len(t['rules'])} |" for n, t in by_table)
        ),
    }


def fill(text: str, filled: dict[str, str]) -> str:
    """Replace each generated region's body, leaving the prose around it untouched."""
    named = region_names(REGION, text)
    if named != set(filled):
        raise GenerationError(f"README regions {sorted(named)} do not match what render.py fills {sorted(filled)}")
    return fill_regions(REGION, text, lambda name: filled[name] + "\n")


def outputs(registry: dict[str, Any]) -> dict[Path, str]:
    """Return each file rendered from `registry` and the text it holds when current."""
    return {OUT: render(registry), README: fill(README.read_text(), regions(registry))}


def main() -> tuple[Path, Path]:
    """Write `tables.md` and refill the README's generated regions, beside the registry."""
    for path, text in outputs(json.loads(REGISTRY.read_text())).items():
        path.write_text(text)
    return OUT, README


def _run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing, and fail where a rendering is stale")
    try:
        if parser.parse_args(argv).check:
            rendered = outputs(json.loads(REGISTRY.read_text()))
            stale = [path for path, text in rendered.items() if not path.is_file() or path.read_text() != text]
            for path in stale:
                print(f"{path.name} is stale; run `python build.py`")
            if not stale:
                print(f"{', '.join(path.name for path in rendered)} current")
            return 1 if stale else 0
        for path in main():
            print(f"wrote {path.name}: {len(path.read_text().splitlines())} lines")
    except GenerationError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())

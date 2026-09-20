"""Render the registry as Markdown, so a table can be read without reading JSON.

This is generated from `logical_schemas.json` at build time, so it states the current registry
content and cannot drift from it.

It is not a standalone specification. The repository authority model identifies the sources that
bind; this rendering exposes the generated registry content for inspection.
"""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "logical_schemas.json"
OUT = HERE / "tables.md"

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
    """Render every declaration a column carries about its values (Part 02 §9.3).

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
            out.append(f"- {_code(ref['columns'])} → `{ref['resource']}` ({target})")
        out.append("")

    if rules := spec.get("rules"):
        out.append(f"**Tier 2 rules** — {len(rules)}")
        out.append("")
        for rule in rules:
            level = rule.get("level", "error")
            advisory = " *(advisory)*" if rule.get("advisory") else ""
            out.append(
                f"- `{rule['id']}` — {level}{advisory}: {rule.get('message', '')}"
            )
        out.append("")

    return out


def render(registry: dict[str, Any]) -> str:
    """Build the whole document."""
    tables = registry["tables"]
    columns = sum(len(t["columns"]) for t in tables.values())
    references = sum(len(t.get("references") or []) for t in tables.values())
    rules = sum(len(t.get("rules") or []) for t in tables.values())
    out = [
        "# Logical schemas, as the registry stands",
        "",
        "**Generated** by `render.py` from `logical_schemas.json`. Do not edit; run",
        "`python registry/build.py` to regenerate.",
        "",
        "This generated rendering is not a standalone specification. See the repository",
        "[authority model](../README.md#authority) for the sources that bind.",
        "",
        "```text",
        f"{len(tables)} tables, {columns} columns, {references} references, {rules} Tier 2 rules",
        (
            f"registry {registry.get('registry_version')}   "
            f"logical standard {registry.get('logical_standard_version')}"
        ),
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


README = HERE / "README.md"

#: Where the README's generated regions begin and end. A count stated in prose is a count that
#: goes stale: the README once disagreed with the generated registry's table and rule counts.
REGION = re.compile(
    r"(<!-- BEGIN generated: (\w+) -->\n).*?(<!-- END generated: \2 -->)", re.DOTALL
)


def regions(registry: dict[str, Any]) -> dict[str, str]:
    """Return the README's generated regions, keyed by name.

    Only what the registry *declares*. How many Tier 1 checks that becomes is deliberately not
    here: it turns on which tables the shim's ordering scan settles uniqueness for, which is the
    validator's judgement, and a second implementation of it would drift.
    """
    tables = registry["tables"]
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
            f"```\n{len(tables)} tables, {len(columns)} columns, "
            f"{sum(len(t['references']) for t in tables.values())} references, "
            f"{len(rules)} Tier 2 rules\n```"
        ),
        "structure": "```\n"
        + "\n".join(f"{n:<4}{label}" for n, label in declared)
        + "\n```",
        "rules": (
            f"{len(rules)} rules over {len(by_table)} tables: {levels['error']} error, "
            f"{levels['warning']} warning, {levels['info']} info — the "
            f"{sum(1 for r in rules if r.get('advisory'))} at `info` being the advisory ones "
            f"(Part 02 §10.2), off unless asked for.\n\n"
            "| Table | Rules |\n|---|---:|\n"
            + "\n".join(f"| `{n}` | {len(t['rules'])} |" for n, t in by_table)
        ),
    }


def fill(text: str, filled: dict[str, str]) -> str:
    """Replace each generated region's body, leaving the prose around it untouched."""
    named = {name for _, name, _ in REGION.findall(text)}
    if named != set(filled):
        raise SystemExit(
            f"README regions {sorted(named)} do not match what render.py fills "
            f"{sorted(filled)}"
        )
    return REGION.sub(lambda m: f"{m.group(1)}{filled[m.group(2)]}\n{m.group(3)}", text)


def main() -> tuple[Path, Path]:
    """Write `tables.md` and refill the README's generated regions, beside the registry."""
    registry = json.loads(REGISTRY.read_text())
    OUT.write_text(render(registry))
    README.write_text(fill(README.read_text(), regions(registry)))
    return OUT, README


if __name__ == "__main__":
    for path in main():
        print(f"wrote {path.name}: {len(path.read_text().splitlines())} lines")

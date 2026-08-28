"""Render the registry as markdown, so a table can be read without reading JSON.

What a table looks like *now* is currently answerable only by reading `02` and then the
revisions that amended it, or by reading generated JSON. Neither is a document. This is
generated from `logical_schemas.json` at build time, so it states the registry's content and
cannot drift from it.

It is not a specification. `nwb_lake_poc_docs/` is frozen and the revisions bind where they
disagree with it; this says what the two together produced.
"""

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "logical_schemas.json"
OUT = HERE / "tables.md"

#: R2 §5's three presence states, rendered so the required ones stand out in a scan.
PRESENCE = {"required": "**required**", "nullable": "nullable", "optional": "optional"}


def _code(names: Any) -> str:
    """Render one name or a list of them as inline code."""
    if not names:
        return "—"
    if isinstance(names, str):
        return f"`{names}`"
    return ", ".join(f"`{n}`" for n in names)


def _table(name: str, spec: dict[str, Any]) -> list[str]:
    """Render one table: its columns, then everything that constrains them."""
    out = [f"### `{name}`", ""]
    if introduced := spec.get("since"):
        note = f"*Introduced by {introduced} (R29 §2). A column with no revision came from `02` unamended.*"
        out += [note, ""]

    out += ["| Column | Type | Presence | Since | Description |", "|---|---|:---:|---|---|"]
    for column in spec["columns"]:
        description = (column.get("description") or "").replace("|", "\\|")
        out.append(
            f"| `{column['name']}` | {column['type']} | "
            f"{PRESENCE.get(column['presence'], column['presence'])} | "
            f"{column.get('since', '')} | {description} |"
        )
    out.append("")

    key = spec.get("primary_key")
    out.append(f"**Primary key** — {_code(key) if key else 'none declared (R7)'}  ")
    sort = spec.get("sort")
    out.append(f"**Sort** — {_code(sort) if sort else 'the primary key (R10 §2)'}")
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
            advisory = " *(advisory, R26)*" if rule.get("advisory") else ""
            out.append(f"- `{rule['id']}` — {level}{advisory}: {rule.get('message', '')}")
        out.append("")

    return out


def render(registry: dict[str, Any]) -> str:
    """Build the whole document."""
    tables = registry["tables"]
    columns = sum(len(t["columns"]) for t in tables.values())
    references = sum(len(t.get("references") or []) for t in tables.values())
    rules = sum(len(t.get("rules") or []) for t in tables.values())
    derived = registry.get("derived_from", {})

    out = [
        "# Logical schemas, as the registry stands",
        "",
        "**Generated** by `render.py` from `logical_schemas.json`. Do not edit; run",
        "`python registry/build.py` to regenerate.",
        "",
        "This is not a specification. `nwb_lake_poc_docs/` is frozen and the revisions bind",
        "where they disagree with it — this states what the two together produced, which is",
        "otherwise answerable only by reading a frozen document and then every amendment to it.",
        "",
        "```text",
        f"{len(tables)} tables, {columns} columns, {references} references, {rules} Tier 2 rules",
        (
            f"registry {registry.get('registry_version')}   "
            f"logical standard {registry.get('logical_standard_version')}"
        ),
        f"derived from {derived.get('specification', '02')}, "
        + f"revisions {', '.join(derived.get('revisions', []) or ['none'])}",
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


def main() -> Path:
    """Write `tables.md` beside the registry."""
    OUT.write_text(render(json.loads(REGISTRY.read_text())))
    return OUT


if __name__ == "__main__":
    path = main()
    print(f"wrote {path.name}: {len(path.read_text().splitlines())} lines")

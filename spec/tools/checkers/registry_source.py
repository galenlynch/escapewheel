"""Assemble a registry document from its TOML source, in the one form a registry is committed in.

A registry's source is a directory: `registry.toml` holds the document's own fields and each
`<resource_id>.toml` declares one resource. A file uses the published format's keys (Part 02
§9) and differs from the document it produces in spelling only:

- a table's `primary_key`, `columns`, `references`, `rules` and `amendment_groups` sit at the top of its file, where
  the document nests them under `table`;
- a single-column reference is written on its column, as `references = "<resource>"` where the
  target column has the same name and `references = { resource = "...", column = "..." }`
  where it does not, with any `specialises` in that table, so a `[[references]]` entry is always
  a multi-column one;
- a rule may invoke the `interval` template (Part 02 §10.2), which is expanded into plain SQL,
  so the document a packet binds carries no vocabulary a validator would have to learn.

A packet binds a registry by its bytes, so two spellings of one declaration would be two
registries. The canonical form fixes what JSON leaves free: each object's keys follow the order
`registry.schema.json` declares them in, and a table lists its single-column references in the
order of their columns before its multi-column ones, which keep the order they were written in.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from .artifacts import ARTIFACTS

#: The file holding a source directory's own fields, and so marking a directory as a source.
HEADER = "registry.toml"
#: A table's keys, which its source file writes at the top level.
TABLE = ("primary_key", "columns", "references", "rules", "amendment_groups")

_SCHEMA = json.loads((ARTIFACTS / "registry.schema.json").read_text())


class RegistrySourceError(ValueError):
    """A source that assembles to no registry document; the message names where and why."""


def _order(pointer: str) -> list[str]:
    """Return the property order the meta-schema declares at one location."""
    node: dict[str, Any] = _SCHEMA
    for part in pointer.split("/"):
        node = node[part] if part else node
    return list(node["properties"])


ORDER = {
    "registry": _order(""),
    "resource": _order("$defs/resource"),
    "table": _order("$defs/table"),
    "column": _order("$defs/column"),
    "reference": _order("$defs/reference"),
    "rule": _order("$defs/rule"),
}


def _ordered(value: dict[str, Any], kind: str, where: str) -> dict[str, Any]:
    """Return `value` with its keys in the meta-schema's order for `kind`."""
    order = ORDER[kind]
    if unknown := sorted(set(value) - set(order)):
        raise RegistrySourceError(f"{where}: {kind} keys the meta-schema does not declare: {unknown}")
    return {key: value[key] for key in order if key in value}


def _references(table: dict[str, Any]) -> list[dict[str, Any]]:
    """Order single-column references by their column, then the multi-column ones as written."""
    position = {column["name"]: i for i, column in enumerate(table["columns"])}
    references = table.get("references", [])
    single = sorted(
        (r for r in references if len(r["columns"]) == 1),
        key=lambda r: position[r["columns"][0]],
    )
    return single + [r for r in references if len(r["columns"]) > 1]


def canonical(document: dict[str, Any]) -> dict[str, Any]:
    """Return `document` in the committed form, without changing what it declares."""
    resources = {}
    for resource_id, resource in sorted(document["resources"].items()):
        resource = _ordered(resource, "resource", resource_id)
        if table := resource.get("table"):
            table = dict(table)
            table["columns"] = [
                _ordered(column, "column", f"{resource_id}.{column['name']}") for column in table["columns"]
            ]
            if "references" in table:
                table["references"] = [_ordered(r, "reference", resource_id) for r in _references(table)]
            if "rules" in table:
                table["rules"] = [_ordered(r, "rule", r["id"]) for r in table["rules"]]
            resource["table"] = _ordered(table, "table", resource_id)
        resources[resource_id] = resource
    return _ordered({**document, "resources": resources}, "registry", "registry")


def dumps(document: dict[str, Any]) -> str:
    """Serialize a registry document as committed."""
    return json.dumps(canonical(document), indent=2) + "\n"


def extension_sources(directory: Path) -> dict[Path, Path]:
    """Return each source directory under `directory` and the document beside it that it builds."""
    return {
        source: directory / f"{source.name}.json"
        for source in sorted(directory.iterdir())
        if (source / HEADER).is_file()
    }


def expand(template: str, resource: str, call: dict[str, Any], key: list[str]) -> list[dict[str, str]]:
    """Expand one template invocation into the rules it stands for (Part 02 §10.2).

    Parameters
    ----------
    template : str
        Template name; only ``interval`` exists.
    resource : str
        The table being expanded for.
    call : dict
        The invocation, carrying the template's parameters.
    key : list of str
        The table's primary key, used to identify offending rows.

    Returns
    -------
    list of dict
        Rules in the same shape a written one has.
    """
    if template != "interval":
        raise RegistrySourceError(f"{resource}: unknown rule template {template!r}")

    start, stop = call["start"], call["stop"]
    report = ", ".join(dict.fromkeys([*key, start, stop]))
    rules = [
        {
            "id": f"{resource}.interval_valid",
            "level": "error",
            "message": f"{stop} precedes {start}",
            "sql": f"SELECT {report}\nFROM {resource}\nWHERE {stop} < {start}",
        }
    ]

    subject = call.get("partition_of")
    if subject is None:
        return rules

    # Without an `index` the rule orders by `start`, which is what it compares against, so the
    # check is an overlap test and nothing else.
    index, op = call.get("index"), call["overlap_op"]
    by = ", ".join(subject)
    if index is not None:
        rules.append(
            {
                "id": f"{resource}.index_contiguous",
                "level": "error",
                "message": f"{index} is not contiguous from 0",
                "sql": (
                    f"SELECT {by}, COUNT(*) AS n\nFROM {resource}\nGROUP BY {by}\n"
                    f"HAVING MAX({index}) <> COUNT(*) - 1\n  OR MIN({index}) <> 0"
                ),
            }
        )
    rules.append(
        {
            "id": f"{resource}.non_overlapping",
            "level": "error",
            "message": call["overlap_message"],
            "sql": (
                f"SELECT {report}\nFROM (\n"
                f"  SELECT *, LAG({stop}) OVER (PARTITION BY {by} ORDER BY {index or start})"
                f" AS prev_stop\n  FROM {resource}\n) AS checked_interval\n"
                f"WHERE prev_stop IS NOT NULL\n  AND {start} {op} prev_stop"
            ),
        }
    )
    return rules


def _column(resource: str, column: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Split a column's `references` from its declaration."""
    column = dict(column)
    name = column["name"]
    target = column.pop("references", None)
    if target is None:
        return column, None
    if isinstance(target, str):
        return column, {
            "columns": [name],
            "resource": target,
            "resource_columns": [name],
        }
    if not {"resource", "column"} <= set(target) <= {"resource", "column", "specialises"}:
        raise RegistrySourceError(
            f"{resource}.{name}: a column's references is a resource ID, or a table of "
            f"`resource`, `column` and optionally `specialises`, not {sorted(target)}"
        )
    reference = {
        "columns": [name],
        "resource": target["resource"],
        "resource_columns": [target["column"]],
    }
    if "specialises" in target:
        reference["specialises"] = target["specialises"]
    return column, reference


def _table(resource: str, source: dict[str, Any]) -> dict[str, Any]:
    """Build one table declaration from the top of its file."""
    columns, references = [], []
    for written in source["columns"]:
        column, reference = _column(resource, written)
        columns.append(column)
        if reference:
            references.append(reference)
    for reference in source.get("references", []):
        if len(reference["columns"]) < 2:
            raise RegistrySourceError(
                f"{resource}: a single-column reference is written on its column, "
                f"not as a [[references]] entry ({reference['columns']})"
            )
        references.append(reference)
    rules = []
    for rule in source.get("rules", []):
        if template := rule.get("use"):
            rules += expand(template, resource, rule, source["primary_key"])
        else:
            rules.append(rule)
    return {
        "columns": columns,
        "primary_key": source["primary_key"],
        "references": references,
        "rules": rules,
        "amendment_groups": source["amendment_groups"],
    }


def _resource(path: Path) -> dict[str, Any]:
    """Build one resource declaration from its file."""
    source = tomllib.loads(path.read_text())
    resource = {k: v for k, v in source.items() if k not in TABLE}
    if source.get("kind") == "table":
        resource["table"] = _table(path.stem, source)
    elif written := sorted(set(source) & set(TABLE)):
        raise RegistrySourceError(f"{path.name}: a {source.get('kind')} resource declares {written}")
    return resource


def assemble(directory: Path) -> dict[str, Any]:
    """Return the registry document one source directory declares, in canonical form."""
    document = tomllib.loads((directory / HEADER).read_text())
    document["resources"] = {
        path.stem: _resource(path) for path in sorted(directory.glob("*.toml")) if path.name != HEADER
    }
    return canonical(document)


__all__ = [
    "HEADER",
    "RegistrySourceError",
    "assemble",
    "canonical",
    "dumps",
    "expand",
    "extension_sources",
]

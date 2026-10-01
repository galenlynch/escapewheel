"""Put a registry document in the one form this repository commits.

A packet binds a registry by its bytes, so two spellings of one declaration would be two
registries. The form fixes what JSON leaves free: each object's keys follow the order
`registry.schema.json` declares them in, and a table lists its single-column references in the
order of their columns before its multi-column ones, which keep the order they were written in.
"""

import json
from pathlib import Path
from typing import Any

from specdoc import GenerationError

HERE = Path(__file__).resolve().parent
_SCHEMA = json.loads((HERE.parent / "artifacts/registry.schema.json").read_text())


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
        raise GenerationError(f"{where}: {kind} keys the meta-schema does not declare: {unknown}")
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

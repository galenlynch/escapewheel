"""The columns a source adapter hands a build, and which of them no registry declares.

A column resolves against core or the extension registry owning its resource's namespace, read
from the tree. The writer's and aind's suites each run their own adapters through this.
"""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE = json.loads((ROOT / "spec" / "artifacts" / "logical_schemas.json").read_text())
EXTENSIONS = {
    document["extension_id"]: document
    for document in (
        json.loads(path.read_text())
        for directory in ("extensions", "escapewheel-aind/extensions")
        for path in sorted((ROOT / directory).glob("*.json"))
    )
}


def declared(resource_id: str) -> set[str] | None:
    """Columns core or the resource's own extension declares for a table, or None if neither does."""
    namespace = resource_id.split(".", 1)[0]
    document = CORE if resource_id in CORE["resources"] else EXTENSIONS.get(namespace)
    declaration = (document or {}).get("resources", {}).get(resource_id)
    if declaration is None or declaration.get("kind") != "table":
        return None
    return {column["name"] for column in declaration["table"]["columns"]}


def emitted(source: Any) -> dict[str, set[str]]:
    """Every column a source hands a build, by resource, over each path the build stages from."""
    found: dict[str, set[str]] = {}
    for resource_id, rows in source.records().items():
        found.setdefault(resource_id, set()).update(key for row in rows for key in row)
    for resource_id, batches in getattr(source, "batches", dict)().items():
        for batch in batches:
            found.setdefault(resource_id, set()).update(batch.schema.names)
    if hasattr(source, "spike_batches"):
        for batch in source.spike_batches(batch_rows=4):
            found.setdefault("core.spike_events", set()).update(batch.schema.names)
    return found


def undeclared(source: Any) -> dict[str, list[str]]:
    """What of `emitted` no registry declares: a whole resource as `['*']`, else its stray columns."""
    wrong = {}
    for resource_id, columns in emitted(source).items():
        known = declared(resource_id)
        if known is None:
            wrong[resource_id] = ["*"]
        elif extra := sorted(columns - known):
            wrong[resource_id] = extra
    return wrong

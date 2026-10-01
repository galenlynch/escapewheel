"""What a registry document's declarations mean to the layers that read them.

- :func:`registry_meta_schema` -- the meta-schema a registry document is checked against.
- :data:`ARROW_TYPES` -- each registry column type's Arrow type, for the schema comparison.
- :data:`DDL` -- each registry column type's DuckDB type, for a typed empty relation.
- :func:`table_contracts` -- the table contracts a registry document declares, by resource ID.
- :func:`visible_declarations` -- core's declarations with those of the extensions beside it.

No module of the package is imported here, so every layer may read it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from importlib import resources as importlib_resources
from typing import Any

#: Registry column type -> the Arrow type a conforming writer must emit (Part 03 §5.5).
ARROW_TYPES = {
    "string": "string",
    "int32": "int32",
    "int64": "int64",
    "float32": "float",
    "float64": "double",
    "bool": "bool",
    "date": "date32[day]",
    "timestamp": "timestamp[us, tz=UTC]",
    "json_string": "string",
}


def table_contracts(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Project the table contracts from registry resource declarations."""
    return {
        str(name): declaration["table"]
        for name, declaration in registry.get("resources", {}).items()
        if declaration.get("kind") == "table" and "table" in declaration
    }


def visible_declarations(
    core: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Mapping[str, Any]]:
    """Combine the visible declarations without creating another serialized authority."""
    visible = dict(core.get("resources", {}))
    for document in extensions:
        visible.update(document.get("resources", {}))
    return visible


def registry_meta_schema() -> dict[str, Any]:
    """Part 02 §9.2's published meta-schema, as this distribution copies it.

    Public because Part 02 §9.2 makes its `$id` something a writer has to state: a document declares
    which meta-schema governs it, and the writer that emits the declaration must not keep its own
    copy of the URI.
    """
    text = importlib_resources.files("escapewheel_validator").joinpath("schemas/registry.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


#: Registry column type -> the DuckDB type used for the empty stand-in tables below.
DDL = {
    "string": "VARCHAR",
    "int32": "INTEGER",
    "int64": "BIGINT",
    "float32": "FLOAT",
    "float64": "DOUBLE",
    "bool": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMPTZ",
    "json_string": "VARCHAR",
}


__all__ = ["registry_meta_schema"]

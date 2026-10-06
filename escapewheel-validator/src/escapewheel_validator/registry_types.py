"""What a registry document's declarations mean to the layers that read them.

- :func:`registry_meta_schema` -- the meta-schema a registry document is checked against.
- :data:`PARQUET_TYPES`, :func:`in_family` -- each registry column type's Parquet types, for the schema
  comparison.
- :data:`DDL` -- each registry column type's DuckDB type, for a typed empty relation.
- :func:`visible_declarations` -- core's declarations with those of the extensions beside it.

No module of the package is imported here, so every layer may read it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from importlib import resources as importlib_resources
from typing import Any

#: A Parquet column's type: its physical type, and its logical type as a tuple whose first member
#: names it and whose others are the parameters Part 03 §5.1 distinguishes.
ParquetType = tuple[str, tuple[Any, ...]]

#: Registry column type -> the Parquet types a packet-owned table's column takes (Part 03 §5.1).
PARQUET_TYPES: dict[str, frozenset[ParquetType]] = {
    "int32": frozenset({("INT32", ("NONE",)), ("INT32", ("INT", 32, True))}),
    "int64": frozenset({("INT64", ("NONE",)), ("INT64", ("INT", 64, True))}),
    "float32": frozenset({("FLOAT", ("NONE",))}),
    "float64": frozenset({("DOUBLE", ("NONE",))}),
    "bool": frozenset({("BOOLEAN", ("NONE",))}),
    "string": frozenset({("BYTE_ARRAY", ("STRING",))}),
    "json_string": frozenset({("BYTE_ARRAY", ("STRING",))}),
    "timestamp": frozenset({("INT64", ("TIMESTAMP", True, "MICROS"))}),
    "date": frozenset({("INT32", ("DATE",))}),
}


def in_family(declared: str, observed: ParquetType) -> bool:
    """Whether an external table's column is at a Parquet type of its declared type's family (Part 03 §5.1)."""
    physical, logical = observed
    match declared:
        case "int32" | "int64":
            return physical in {"INT32", "INT64"} and logical[0] in {"NONE", "INT"}
        case "float32" | "float64":
            return physical in {"FLOAT", "DOUBLE"} and logical == ("NONE",)
        case "bool":
            return physical == "BOOLEAN"
        case "string" | "json_string":
            return physical == "BYTE_ARRAY" and logical[0] in {"STRING", "ENUM", "JSON"}
        case "timestamp":
            return physical == "INT64" and logical[:2] == ("TIMESTAMP", True)
        case "date":
            return physical == "INT32" and logical == ("DATE",)
    return False


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

    Public because its `$id` is something a writer has to state: a document declares
    which meta-schema governs it, and the writer that emits the declaration must not keep its own
    copy of the URI.
    """
    text = importlib_resources.files("escapewheel_validator").joinpath("schemas/registry.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def core_registry_bytes() -> bytes:
    """The core registry this distribution was released with, as its exact bytes.

    What an extension is checked under where its author names no other core; a build still names
    the registry it writes against (Part 04 §8).
    """
    return importlib_resources.files("escapewheel_validator").joinpath("schemas/logical_schemas.json").read_bytes()


#: Registry column type -> the DuckDB type of the empty table standing in for an absent one.
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


__all__ = ["core_registry_bytes", "registry_meta_schema"]

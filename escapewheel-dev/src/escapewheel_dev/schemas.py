"""The document JSON Schemas under `spec/artifacts/`."""

import json
from collections.abc import Mapping
from functools import cache
from typing import Any

import jsonschema

from ._root import ROOT

ARTIFACTS = ROOT / "spec" / "artifacts"


@cache
def schemas() -> Mapping[str, Mapping[str, Any]]:
    """Return every document schema by name: ``manifest`` for `manifest.schema.json`."""
    return {
        path.name.removesuffix(".schema.json"): json.loads(path.read_text())
        for path in sorted(ARTIFACTS.glob("*.schema.json"))
    }


def schema(name: str) -> Mapping[str, Any]:
    """Return one document schema by name."""
    return schemas()[name]


def schema_errors(name: str, document: Any) -> list[str]:
    """Return each way `document` fails schema `name`, formats included, as ``/pointer: message``."""
    validator = jsonschema.Draft202012Validator(schema(name), format_checker=jsonschema.FormatChecker())
    return [
        f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda error: list(map(str, error.absolute_path)))
    ]


__all__ = ["ARTIFACTS", "schema", "schema_errors", "schemas"]

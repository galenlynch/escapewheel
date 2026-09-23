"""Checked access to the incorporated physical-profile descriptor."""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping
from functools import cache
from importlib import resources as importlib_resources
from typing import Any

import jsonschema


class PhysicalProfileError(ValueError):
    """The physical-profile descriptor is malformed or internally inconsistent."""


def check_physical_profile(
    descriptor: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    logical_kinds: Collection[str] | None = None,
    logical_standard: str | None = None,
    part_text: str | None = None,
) -> tuple[str, ...]:
    """Return generic shape, cross-member, cross-artifact, and anchor errors."""
    errors = [
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in sorted(
            jsonschema.Draft202012Validator(schema).iter_errors(descriptor),
            key=lambda error: list(error.path),
        )
    ]
    if descriptor.get("$schema") != schema.get("$id"):
        errors.append("$schema does not name the supplied physical-profile schema")
    mappings = descriptor.get("kind_interfaces", {})
    interfaces = descriptor.get("interfaces", {})
    if isinstance(mappings, Mapping) and isinstance(interfaces, Mapping):
        mapped = {value for value in mappings.values() if isinstance(value, str)}
        declared = set(interfaces)
        for name in sorted(mapped - declared):
            errors.append(f"kind_interfaces refers to undeclared interface {name!r}")
        for name in sorted(declared - mapped):
            errors.append(f"interface {name!r} is not referenced by any logical kind")
        if logical_kinds is not None and set(mappings) != set(logical_kinds):
            errors.append("kind_interfaces keys do not equal the logical kind vocabulary")
    if logical_standard is not None and descriptor.get("logical_standard") != logical_standard:
        errors.append("logical_standard does not identify the checked logical standard")
    if part_text is not None and isinstance(interfaces, Mapping):
        for interface, entry in interfaces.items():
            candidates = [(str(interface), entry)]
            if isinstance(entry, Mapping):
                candidates.extend(
                    (f"{interface}.{variant}", value) for variant, value in entry.get("variants", {}).items()
                )
            for label, value in candidates:
                if not isinstance(value, Mapping):
                    continue
                for anchor in value.get("anchors", []):
                    count = len(
                        re.findall(
                            rf'<a id="{re.escape(str(anchor))}"(?: [^>]*)?></a>',
                            part_text,
                        )
                    )
                    if count != 1:
                        errors.append(f"{label} anchor {anchor!r} resolves {count} times in Part 03")
    return tuple(errors)


def _bundled_json(relative: str) -> dict[str, Any]:
    text = importlib_resources.files(__package__).joinpath(relative).read_text()
    value: dict[str, Any] = json.loads(text)
    return value


@cache
def physical_profile_schema() -> dict[str, Any]:
    """Return the bundled reusable descriptor schema."""
    return _bundled_json("schemas/physical_profile.schema.json")


@cache
def physical_profile() -> dict[str, Any]:
    """Return the bundled profile after one cached conformance check."""
    descriptor = _bundled_json("schemas/physical_profiles/escapewheel-portable-v0.1.json")
    errors = check_physical_profile(descriptor, physical_profile_schema())
    if errors:
        raise PhysicalProfileError("; ".join(errors))
    return descriptor


def interface_for(kind: str) -> str | None:
    """Derive the generic physical interface for one checked logical kind."""
    value = physical_profile()["kind_interfaces"].get(kind)
    return str(value) if value is not None else None


def variant_for_zarr_format(format_version: int) -> Mapping[str, Any] | None:
    """Return the descriptor variant selected by format-owned Zarr metadata."""
    variants = physical_profile()["interfaces"]["zarr"]["variants"]
    return next((entry for entry in variants.values() if entry["format_version"] == format_version), None)


def parquet_floor() -> Mapping[str, Any]:
    """Return the incorporated Parquet reader and packet-writer floor."""
    return physical_profile()["interfaces"]["parquet"]["reader_floor"]

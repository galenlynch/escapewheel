"""Check a physical-profile descriptor (Part 03 §1) and the overriding orders it declares (Part 03 §5.4)."""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from typing import Any

import jsonschema


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
        errors.extend(_misplaced_orders(mappings, interfaces))
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


def _misplaced_orders(mappings: Mapping[str, Any], interfaces: Mapping[str, Any]) -> list[str]:
    """Only the interface storing tables has a row order to override (Part 03 §1)."""
    return [
        f"interface {name!r} declares overriding_orders but does not store tables"
        for name, entry in interfaces.items()
        if isinstance(entry, Mapping) and "overriding_orders" in entry and mappings.get("table") != name
    ]


def override_errors(order: Sequence[str], table: Mapping[str, Any] | None) -> list[str]:
    """Where an overriding order is inconsistent with the table a core registry declares.

    The conditions of Part 03 §5.4 that let an override settle its key by adjacency without a
    packet (Part 03 §5.3). `table` is None where the registry declares no such table.
    """
    if table is None:
        return ["the core registry declares no such table"]
    columns = {column["name"]: column for column in table.get("columns", ())}
    key = list(table.get("primary_key") or ())
    errors = [f"{name!r} is not a column of the table" for name in order if name not in columns]
    errors += [f"key column {name!r} is absent" for name in key if name not in order]
    if errors:
        return errors
    last = max(order.index(name) for name in key)
    for name in order[:last]:
        determined = columns[name].get("determined_by")
        if name not in key and not (determined and set(determined) <= set(key)):
            errors.append(f"{name!r} precedes a key column and is not determined by the key")
    if list(order) == key:
        errors.append("the order is the table's primary key's order")
    return errors


__all__ = ["check_physical_profile", "override_errors"]

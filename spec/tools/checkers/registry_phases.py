"""The rule and unit phases of the registry contract: each rule's static check and each unit's UCUM parse."""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from typing import Any
from xml.etree import ElementTree

from .registry_invariants import declared_tables, one_column
from .registry_result import Outcome, invalid, json_pointer
from .rule_language import PROFILE_ID, RuleProfileError, check_rule


def rule_outcomes(document: Mapping[str, Any], core: Mapping[str, Any] | None) -> list[Outcome]:
    """Check each rule statically against the selected rule language, core being visible where given."""
    outcomes: list[Outcome] = []
    visible = dict(declared_tables(document))
    if core is not None:
        visible = dict(declared_tables(core)) | visible
    for resource, table in declared_tables(document).items():
        for index, rule in enumerate(table["rules"]):
            pointer = json_pointer(("tables", resource, "rules", index))
            rule_id = str(rule["id"])
            if document["rule_language"] != PROFILE_ID:
                outcomes.append(
                    Outcome(
                        "unsupported",
                        str(document["rule_language"]),
                        pointer,
                        rule_id,
                        detail="the exact selected rule language is unavailable",
                    )
                )
                continue
            try:
                checked = check_rule(str(rule["sql"]), document, core_resources=core)
            except RuleProfileError as exc:
                outcomes.append(invalid(PROFILE_ID, pointer, rule_id, str(exc)))
                continue
            optional = sorted(
                f"{input_resource}.{column}"
                for input_resource, column in checked.inputs
                if (spec := visible.get(input_resource)) is not None
                and (declared := one_column(spec, column)) is not None
                and declared["presence"] == "optional"
            )
            if optional:
                outcomes.append(
                    invalid(
                        "registry.rule.required_inputs",
                        pointer,
                        rule_id,
                        f"rule binds optional inputs: {', '.join(optional)}",
                    )
                )
    return outcomes


@cache
def _ucum_parser() -> Any | None:
    try:
        from ucumvert import get_ucum_parser  # type: ignore[import-untyped]

        essence = files("ucumvert").joinpath("vendor/ucum-essence.xml").read_text()
        root = ElementTree.fromstring(essence)
        if root.attrib.get("version") != "2.2" or root.attrib.get("revision-date") != "2024-06-17":
            return None
        return get_ucum_parser()
    except (ImportError, FileNotFoundError, ElementTree.ParseError):
        return None


def external_domains() -> tuple[str, ...]:
    """Name the exact external semantic domains available to this evaluation."""
    return ("ucum-2.2-2024-06-17",) if _ucum_parser() is not None else ()


def ucum_error(expression: str) -> str | None:
    """Why `expression` is not a case-sensitive UCUM 2.2 code, or None where it is one (Part 02 §8.4).

    Raises where the exact edition is unavailable; a valid context proves it present.
    """
    parser = _ucum_parser()
    if parser is None:
        raise RuntimeError("the exact UCUM 2.2 domain dated 2024-06-17 is unavailable")
    from ucumvert import InvalidUcumError, parse_ucum  # type: ignore[import-untyped]

    try:
        parse_ucum(expression, parser=parser)
    except InvalidUcumError as exc:
        return str(exc).splitlines()[0]
    return None


def unit_outcomes(document: Mapping[str, Any]) -> list[Outcome]:
    """Check each literal unit against the exact UCUM edition."""
    if _ucum_parser() is None:
        return [
            Outcome(
                "unsupported",
                "registry.unit.ucum_2_2_cs",
                reason="registry.phase.prerequisite_unsupported",
                detail="the exact UCUM 2.2 domain dated 2024-06-17 is unavailable",
            )
        ]
    outcomes: list[Outcome] = []
    for resource, table in declared_tables(document).items():
        for index, column in enumerate(table["columns"]):
            if "unit" not in column:
                continue
            error = ucum_error(str(column["unit"]))
            if error is not None:
                outcomes.append(
                    invalid(
                        "registry.unit.ucum_2_2_cs",
                        json_pointer(("tables", resource, "columns", index, "unit")),
                        resource,
                        error,
                    )
                )
    return outcomes


__all__ = [
    "external_domains",
    "rule_outcomes",
    "ucum_error",
    "unit_outcomes",
]

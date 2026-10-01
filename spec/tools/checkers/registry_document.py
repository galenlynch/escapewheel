"""Validate registry documents against the incorporated Part 02 contract."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from copy import deepcopy
from functools import cache
from importlib.resources import files
from typing import Any
from xml.etree import ElementTree

import jsonschema

from .artifacts import ARTIFACTS
from .registry_invariants import (
    METADATA_DESCRIPTION,
    UCUM_URI,
    Universe,
    declared_tables,
    one_column,
    semantic_outcomes,
)
from .registry_result import (
    PHASES,
    RESULT_SCHEMA_ID,
    CheckedRegistryContext,
    Outcome,
    PhaseRecord,
    RegistryRejected,
    RegistryResult,
    freeze,
    invalid,
    json_pointer,
)
from .rule_language import PROFILE_ID, RuleProfileError, check_rule

SCHEMA = ARTIFACTS / "registry.schema.json"
CONTRACT_SCHEMA = ARTIFACTS / "registry_contract.schema.json"
CONTRACT = ARTIFACTS / "registry_contracts" / "escapewheel-registry-contract-v0.9.json"
RESULT_SCHEMA = ARTIFACTS / "registry_result.schema.json"
_PRECEDENCE = {"passed": 0, "skipped": 0, "incomplete": 1, "unsupported": 2, "invalid": 3}


class _Object(dict[str, Any]):
    """Decoded object retaining duplicate member names for the JSON phase."""

    duplicates: tuple[str, ...]

    def __init__(self, pairs: list[tuple[str, Any]]) -> None:
        super().__init__(pairs)
        counts = Counter(name for name, _ in pairs)
        self.duplicates = tuple(sorted(name for name, count in counts.items() if count > 1))


def _owner(pointer: str) -> str | None:
    parts = pointer.split("/")
    if len(parts) >= 3 and parts[1] == "resources":
        return parts[2].replace("~1", "/").replace("~0", "~")
    return None


def _ordered(outcomes: Iterable[Outcome]) -> tuple[Outcome, ...]:
    return tuple(sorted(outcomes, key=lambda item: (item.instance, item.id, item.owner or "")))


def _phase(name: str, outcomes: Iterable[Outcome] = ()) -> PhaseRecord:
    ordered = _ordered(outcomes)
    state = max((item.state for item in ordered), key=lambda value: _PRECEDENCE[value], default="passed")
    return PhaseRecord(name, state, ordered)


def _skipped(name: str, reason: str) -> PhaseRecord:
    return PhaseRecord(name, "skipped", (), reason)


def _complete(phases: list[PhaseRecord], descriptor_id: str | None) -> RegistryResult:
    material = [phase.state for phase in phases if phase.state != "skipped"]
    state = max(material, key=lambda value: _PRECEDENCE[value], default="incomplete")
    return RegistryResult(descriptor_id, "valid" if state == "passed" else state, tuple(phases))


def _duplicates(value: Any, path: tuple[Any, ...] = ()) -> list[Outcome]:
    outcomes: list[Outcome] = []
    if isinstance(value, _Object):
        outcomes.extend(
            Outcome(
                "invalid",
                "registry.json.duplicate_member",
                json_pointer(path),
                detail=f"duplicate member {name!r}",
            )
            for name in value.duplicates
        )
        for name, child in value.items():
            outcomes.extend(_duplicates(child, (*path, name)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            outcomes.extend(_duplicates(child, (*path, index)))
    return outcomes


def check_registry_bytes(
    data: bytes,
    core: Mapping[str, Any] | None = None,
    *,
    descriptors: Iterable[Mapping[str, Any]] | None = None,
) -> RegistryResult:
    """Validate UTF-8 JSON bytes, including duplicate object members."""
    core_context = check_registry_context(core, descriptors=descriptors) if core is not None else None
    return check_registry_context_bytes(data, core=core_context, descriptors=descriptors).result


def check_registry_context_bytes(
    data: bytes,
    core: CheckedRegistryContext | None = None,
    *,
    descriptors: Iterable[Mapping[str, Any]] | None = None,
) -> CheckedRegistryContext:
    """Check exact registry bytes and bind the complete result to them."""
    descriptor_values = _load_contracts(descriptors)
    descriptor_identity = tuple(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in descriptor_values)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        outcome = Outcome("invalid", "registry.json.invalid_utf8", detail=str(exc))
        result = _complete(
            [
                _phase("json", [outcome]),
                *[_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[1:]],
            ],
            None,
        )
        return CheckedRegistryContext("bytes", bytes(data), None, result, descriptor_identity, external_domains(), core)
    try:
        document = json.loads(text, object_pairs_hook=_Object)
    except json.JSONDecodeError as exc:
        outcome = Outcome("invalid", "registry.json.invalid_syntax", detail=str(exc))
        result = _complete(
            [
                _phase("json", [outcome]),
                *[_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[1:]],
            ],
            None,
        )
        return CheckedRegistryContext("bytes", bytes(data), None, result, descriptor_identity, external_domains(), core)
    duplicate_outcomes = _duplicates(document)
    if duplicate_outcomes:
        result = _complete(
            [
                _phase("json", duplicate_outcomes),
                *[_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[1:]],
            ],
            None,
        )
        return CheckedRegistryContext(
            "bytes", bytes(data), freeze(document), result, descriptor_identity, external_domains(), core
        )
    result = _check_mapping(
        document,
        core.document if core is not None else None,
        PhaseRecord("json", "passed"),
        descriptor_values,
        core.result if core is not None else None,
    )
    domains = external_domains()
    return CheckedRegistryContext("bytes", bytes(data), freeze(document), result, descriptor_identity, domains, core)


def check_registry(
    document: Mapping[str, Any],
    core: Mapping[str, Any] | None = None,
    *,
    descriptors: Iterable[Mapping[str, Any]] | None = None,
) -> RegistryResult:
    """Validate an already-decoded mapping, beginning after byte-level JSON checks."""
    core_context = check_registry_context(core, descriptors=descriptors) if core is not None else None
    return check_registry_context(document, core=core_context, descriptors=descriptors).result


def check_registry_context(
    document: Mapping[str, Any],
    core: CheckedRegistryContext | None = None,
    *,
    descriptors: Iterable[Mapping[str, Any]] | None = None,
) -> CheckedRegistryContext:
    """Copy and check a decoded mapping, binding its result before caller mutation."""
    copied = deepcopy(document)
    descriptor_values = _load_contracts(descriptors)
    result = _check_mapping(
        copied,
        core.document if core is not None else None,
        _skipped("json", "registry.phase.mapping_input"),
        descriptor_values,
        core.result if core is not None else None,
    )
    descriptor_identity = tuple(json.dumps(item, sort_keys=True, separators=(",", ":")) for item in descriptor_values)
    domains = external_domains()
    frozen = freeze(copied)
    return CheckedRegistryContext("mapping", frozen, frozen, result, descriptor_identity, domains, core)


def _load_contracts(descriptors: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    schema = json.loads(CONTRACT_SCHEMA.read_text())
    loaded = (
        [dict(descriptor) for descriptor in descriptors]
        if descriptors is not None
        else [json.loads(path.read_text()) for path in sorted(CONTRACT.parent.glob("*.json"))]
    )
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for descriptor in loaded:
        validator.validate(descriptor)
    return loaded


def _check_mapping(
    document: Any,
    core: Mapping[str, Any] | None,
    json_phase: PhaseRecord,
    descriptors: Iterable[Mapping[str, Any]] | None,
    checked_core_result: RegistryResult | None = None,
) -> RegistryResult:
    phases = [json_phase]
    if not isinstance(document, Mapping):
        outcome = Outcome("invalid", "registry.schema.selector_missing")
        phases.append(_phase("schema_selection", [outcome]))
        phases.extend(_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[2:])
        return _complete(phases, None)
    selector = document.get("$schema")
    if selector is None:
        outcome = Outcome("invalid", "registry.schema.selector_missing")
        phases.append(_phase("schema_selection", [outcome]))
        phases.extend(_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[2:])
        return _complete(phases, None)
    if not isinstance(selector, str):
        outcome = Outcome("invalid", "registry.schema.selector_type", "/$schema")
        phases.append(_phase("schema_selection", [outcome]))
        phases.extend(_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[2:])
        return _complete(phases, None)

    schema = json.loads(SCHEMA.read_text())
    if selector != schema["$id"]:
        outcome = Outcome("unsupported", "registry.schema.selector_unsupported", "/$schema")
        phases.append(_phase("schema_selection", [outcome]))
        phases.extend(_skipped(name, "registry.phase.prerequisite_unsupported") for name in PHASES[2:])
        return _complete(phases, None)
    phases.append(_phase("schema_selection"))

    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    shape = [
        Outcome(
            "invalid",
            str(schema["$id"]),
            json_pointer(error.absolute_path),
            _owner(json_pointer(error.absolute_path)),
            schema_location=json_pointer(error.absolute_schema_path),
            detail=error.message,
        )
        for error in validator.iter_errors(document)
    ]
    phases.append(_phase("shape", shape))
    if shape:
        phases.extend(_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[3:])
        return _complete(phases, None)

    contracts = _load_contracts(descriptors)
    class_name = "extension" if "extension_id" in document else "core"
    core_result: RegistryResult | None = None
    core_usable = class_name == "core"
    core_semantic: Any = document.get("semantic_standard_version")
    if class_name == "extension" and core is not None:
        core_result = checked_core_result or check_registry(core, descriptors=contracts)
        core_usable = (
            core_result.state == "valid"
            and "extension_id" not in core
            and core.get("logical_standard_version") == document["logical_standard_version"]
        )
        if core_usable:
            core_semantic = core.get("semantic_standard_version")

    candidates = [
        descriptor
        for descriptor in contracts
        if selector == descriptor["registry_schema"]
        and document["logical_standard_version"] == descriptor["logical_standard"]
        and document["rule_language"] in descriptor["rule_languages"]
        and (class_name == "extension" and not core_usable or core_semantic == descriptor["semantic_standard"])
    ]
    contract_outcomes: list[Outcome] = []
    descriptor_id: str | None = None
    descriptor: Mapping[str, Any] | None = None
    if not candidates:
        contract_outcomes.append(Outcome("unsupported", "registry.contract.selector_unsupported"))
    elif len(candidates) > 1:
        contract_outcomes.append(Outcome("unsupported", "registry.contract.selector_ambiguous"))
    else:
        descriptor = candidates[0]
        descriptor_id = str(descriptor["id"])
        if class_name == "extension" and not core_usable:
            contract_outcomes.append(
                Outcome(
                    "incomplete",
                    "registry.contract.core_context_unusable",
                    reason="registry.phase.prerequisite_incomplete",
                )
            )
    phases.append(_phase("contract_selection", contract_outcomes))
    if descriptor_id is None:
        phases.extend(_skipped(name, "registry.phase.prerequisite_unsupported") for name in PHASES[4:])
        return _complete(phases, None)

    tables = dict(declared_tables(document))
    declarations = dict(document["resources"])
    if class_name == "extension" and core_usable and core is not None:
        tables = dict(declared_tables(core)) | tables
        declarations = dict(core["resources"]) | declarations
    assert descriptor is not None
    semantic = semantic_outcomes(
        document,
        class_name,
        core_usable,
        descriptor,
        {Universe.TABLES: tables, Universe.DECLARATIONS: declarations},
    )
    phases.append(_phase("semantic", semantic))
    rules = rule_outcomes(document, core if core_usable and class_name == "extension" else None)
    phases.append(_phase("rule_static", rules))
    phases.append(_phase("external_domain", unit_outcomes(document)))
    return _complete(phases, descriptor_id)


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
    "CONTRACT",
    "CONTRACT_SCHEMA",
    "METADATA_DESCRIPTION",
    "PHASES",
    "RESULT_SCHEMA",
    "RESULT_SCHEMA_ID",
    "SCHEMA",
    "UCUM_URI",
    "CheckedRegistryContext",
    "Outcome",
    "PhaseRecord",
    "RegistryRejected",
    "RegistryResult",
    "check_registry",
    "check_registry_bytes",
    "check_registry_context",
    "check_registry_context_bytes",
    "ucum_error",
]

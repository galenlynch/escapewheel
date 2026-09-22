"""Validate registry documents against the incorporated Part 02 contract."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

import jsonschema

from escapewheel_validator.rule_language import PROFILE_ID, RuleProfileError, check_rule

SCHEMAS = Path(__file__).resolve().parent / "schemas"
SCHEMA = SCHEMAS / "registry.schema.json"
CONTRACT_SCHEMA = SCHEMAS / "registry_contract.schema.json"
CONTRACT = SCHEMAS / "registry_contracts" / "escapewheel-registry-contract-v0.1.json"
METADATA_DESCRIPTION = (
    "What the source stated about this row that the standard does not model, carried "
    "in the source's own vocabulary and read by no rule."
)
PHASES = (
    "json",
    "schema_selection",
    "shape",
    "contract_selection",
    "semantic",
    "rule_static",
    "external_domain",
)
_PRECEDENCE = {"passed": 0, "skipped": 0, "incomplete": 1, "unsupported": 2, "invalid": 3}


@dataclass(frozen=True)
class Outcome:
    """One non-passing check in the abstract registry result."""

    state: str
    id: str
    instance: str = ""
    owner: str | None = None
    reason: str | None = None
    schema_location: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class PhaseRecord:
    """The state and ordered non-passing outcomes of one contract phase."""

    phase: str
    state: str
    outcomes: tuple[Outcome, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class RegistryResult:
    """The complete language-neutral result for one registry document."""

    descriptor_id: str | None
    state: str
    phases: tuple[PhaseRecord, ...]

    @property
    def findings(self) -> tuple[Outcome, ...]:
        """Return exactly the invalid outcomes."""
        return tuple(outcome for phase in self.phases for outcome in phase.outcomes if outcome.state == "invalid")


@dataclass(frozen=True)
class Finding:
    """Compatibility view used by the extension-author command."""

    label: str
    offenders: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """Whether the represented invariant passed."""
        return not self.offenders

    def __str__(self) -> str:
        """Render a concise human-oriented finding."""
        if self.passed:
            return self.label
        shown = ", ".join(self.offenders[:4])
        more = f", +{len(self.offenders) - 4} more" if len(self.offenders) > 4 else ""
        return f"{self.label} ({len(self.offenders)}): {shown}{more}"


class _Object(dict[str, Any]):
    """Decoded object retaining duplicate member names for the JSON phase."""

    duplicates: tuple[str, ...]

    def __init__(self, pairs: list[tuple[str, Any]]) -> None:
        super().__init__(pairs)
        counts = Counter(name for name, _ in pairs)
        self.duplicates = tuple(sorted(name for name, count in counts.items() if count > 1))


def _pointer(parts: Iterable[Any]) -> str:
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in parts)


def _owner(pointer: str) -> str | None:
    parts = pointer.split("/")
    if len(parts) >= 3 and parts[1] == "tables":
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
                _pointer(path),
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
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        outcome = Outcome("invalid", "registry.json.invalid_utf8", detail=str(exc))
        return _complete(
            [
                _phase("json", [outcome]),
                *[_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[1:]],
            ],
            None,
        )
    try:
        document = json.loads(text, object_pairs_hook=_Object)
    except json.JSONDecodeError as exc:
        outcome = Outcome("invalid", "registry.json.invalid_syntax", detail=str(exc))
        return _complete(
            [
                _phase("json", [outcome]),
                *[_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[1:]],
            ],
            None,
        )
    duplicate_outcomes = _duplicates(document)
    if duplicate_outcomes:
        return _complete(
            [
                _phase("json", duplicate_outcomes),
                *[_skipped(name, "registry.phase.prerequisite_invalid") for name in PHASES[1:]],
            ],
            None,
        )
    return _check_mapping(document, core, PhaseRecord("json", "passed"), descriptors)


def check_registry(
    document: Mapping[str, Any],
    core: Mapping[str, Any] | None = None,
    *,
    descriptors: Iterable[Mapping[str, Any]] | None = None,
) -> RegistryResult:
    """Validate an already-decoded mapping, beginning after byte-level JSON checks."""
    return _check_mapping(document, core, _skipped("json", "registry.phase.mapping_input"), descriptors)


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
            _pointer(error.absolute_path),
            _owner(_pointer(error.absolute_path)),
            schema_location=_pointer(error.absolute_schema_path),
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
        core_result = check_registry(core, descriptors=contracts)
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

    universe = dict(document["tables"])
    if class_name == "extension" and core_usable and core is not None:
        universe = dict(core["tables"]) | universe
    assert descriptor is not None
    semantic = _semantic_outcomes(document, universe, class_name, core_usable, descriptor)
    phases.append(_phase("semantic", semantic))
    rules = _rule_outcomes(document, core if core_usable and class_name == "extension" else None)
    phases.append(_phase("rule_static", rules))
    phases.append(_phase("external_domain", _unit_outcomes(document)))
    return _complete(phases, descriptor_id)


def _invalid(invariant: str, pointer: str, owner: str | None, detail: str) -> Outcome:
    return Outcome("invalid", invariant, pointer, owner, detail=detail)


def _columns(table: Mapping[str, Any]) -> dict[str, list[tuple[int, Mapping[str, Any]]]]:
    result: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    for index, column in enumerate(table["columns"]):
        result.setdefault(str(column["name"]), []).append((index, column))
    return result


def _one_column(table: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    found = _columns(table).get(name, [])
    return found[0][1] if len(found) == 1 else None


def _required_column(table: Mapping[str, Any], name: str) -> bool:
    column = _one_column(table, name)
    return column is not None and column["presence"] == "required"


def _semantic_outcomes(
    document: Mapping[str, Any],
    universe: Mapping[str, Any],
    class_name: str,
    core_usable: bool,
    descriptor: Mapping[str, Any] | None = None,
) -> list[Outcome]:
    checks = _semantic_checks()
    if descriptor is None:
        descriptor = json.loads(CONTRACT.read_text())
    outcomes: list[Outcome] = []
    core_dependent = {
        "registry.reference.resolves",
        "registry.reference.target_key",
        "registry.reference.compatible",
        "registry.session_scope.path",
        "registry.context_source.resolves",
    }
    for entry in descriptor["invariants"]:
        invariant = str(entry["id"])
        if entry["phase"] != "semantic" or class_name not in entry["classes"]:
            continue
        check = checks[invariant]
        outcomes.extend(check(document, universe, class_name, core_usable))
        if class_name == "extension" and not core_usable and invariant in core_dependent:
            outcomes.append(
                Outcome(
                    "incomplete",
                    invariant,
                    reason="registry.phase.prerequisite_incomplete",
                    detail="usable core context is required for cross-registry resolution",
                )
            )
    return outcomes


def _semantic_checks() -> dict[str, Any]:
    """Map every descriptor semantic ID to its sole implementation."""
    return {
        "registry.namespace.owned": _namespace_owned,
        "registry.namespace.reference_direction": _reference_direction,
        "registry.column.name_unique": _column_names,
        "registry.primary_key.resolves": _primary_keys,
        "registry.reference.resolves": _references_resolve,
        "registry.reference.target_key": _reference_targets_key,
        "registry.reference.compatible": _references_compatible,
        "registry.session_scope.path": _session_scope,
        "registry.identity.name": _identity_names,
        "registry.metadata.eligibility": _metadata,
        "registry.determined_by.resolves": _determined_by,
        "registry.discriminator.declaration": _discriminator_declarations,
        "registry.discriminator.path": _discriminator_paths,
        "registry.context_source.resolves": _context_sources,
        "registry.authority.uri": _authority_uris,
        "registry.rule.id_unique": _rule_ids_unique,
        "registry.rule.id_owner": _rule_ids_owned,
        "registry.core.device_detail": _core_device_detail,
    }


def _namespace_owned(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, core_usable
    allowed = {"core", "analysis"} if class_name == "core" else {str(document["extension_id"])}
    return [
        _invalid(
            "registry.namespace.owned",
            _pointer(("tables", resource)),
            resource,
            f"namespace {resource.split('.', 1)[0]!r} is not owned by this {class_name} registry",
        )
        for resource in document["tables"]
        if resource.split(".", 1)[0] not in allowed
    ]


def _reference_direction(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, core_usable
    own = set(document["tables"])
    extension_id = document.get("extension_id")
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        for index, reference in enumerate(table["references"]):
            target = str(reference["resource"])
            namespace = target.split(".", 1)[0]
            permitted = target in own if class_name == "core" else namespace in {"core", "analysis", extension_id}
            if not permitted:
                outcomes.append(
                    _invalid(
                        "registry.namespace.reference_direction",
                        _pointer(("tables", resource, "references", index, "resource")),
                        resource,
                        f"reference target {target!r} is outside the permitted direction",
                    )
                )
    return outcomes


def _column_names(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        seen: set[str] = set()
        for index, column in enumerate(table["columns"]):
            name = str(column["name"])
            if name in seen:
                outcomes.append(
                    _invalid(
                        "registry.column.name_unique",
                        _pointer(("tables", resource, "columns", index, "name")),
                        resource,
                        f"column name {name!r} occurs more than once",
                    )
                )
            seen.add(name)
    return outcomes


def _primary_keys(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        columns = _columns(table)
        for index, name in enumerate(table["primary_key"] or []):
            resolved = columns.get(name, [])
            if len(resolved) != 1:
                outcomes.append(
                    _invalid(
                        "registry.primary_key.resolves",
                        _pointer(("tables", resource, "primary_key", index)),
                        resource,
                        f"primary-key member {name!r} resolves {len(resolved)} times",
                    )
                )
            elif resolved[0][1]["presence"] != "required":
                outcomes.append(
                    _invalid(
                        "registry.primary_key.resolves",
                        _pointer(("tables", resource, "primary_key", index)),
                        resource,
                        f"primary-key member {name!r} is not required",
                    )
                )
    return outcomes


def _references_resolve(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        source_columns = _columns(table)
        for r_index, reference in enumerate(table["references"]):
            base = ("tables", resource, "references", r_index)
            target_name = str(reference["resource"])
            target = universe.get(target_name)
            if target is None:
                if not (
                    class_name == "extension"
                    and not core_usable
                    and target_name.split(".", 1)[0] in {"core", "analysis"}
                ):
                    outcomes.append(
                        _invalid(
                            "registry.reference.resolves",
                            _pointer((*base, "resource")),
                            resource,
                            f"target resource {target_name!r} does not resolve",
                        )
                    )
                continue
            target_columns = _columns(target)
            if len(reference["columns"]) != len(reference["resource_columns"]):
                outcomes.append(
                    _invalid(
                        "registry.reference.resolves",
                        _pointer(base),
                        resource,
                        "reference source and target arity differ",
                    )
                )
            for side, names, available in (
                ("columns", reference["columns"], source_columns),
                ("resource_columns", reference["resource_columns"], target_columns),
            ):
                for c_index, name in enumerate(names):
                    if len(available.get(name, [])) != 1:
                        outcomes.append(
                            _invalid(
                                "registry.reference.resolves",
                                _pointer((*base, side, c_index)),
                                resource,
                                f"reference member {name!r} resolves {len(available.get(name, []))} times",
                            )
                        )
    return outcomes


def _reference_targets_key(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        for index, reference in enumerate(table["references"]):
            target = universe.get(reference["resource"])
            if target is not None and (
                target["primary_key"] is None or reference["resource_columns"] != target["primary_key"]
            ):
                outcomes.append(
                    _invalid(
                        "registry.reference.target_key",
                        _pointer(("tables", resource, "references", index, "resource_columns")),
                        resource,
                        f"target side is not the complete ordered key of {reference['resource']}",
                    )
                )
    return outcomes


def _references_compatible(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        sources = _columns(table)
        for r_index, reference in enumerate(table["references"]):
            target = universe.get(reference["resource"])
            if target is None:
                continue
            targets = _columns(target)
            for c_index, (source_name, target_name) in enumerate(
                zip(reference["columns"], reference["resource_columns"], strict=False)
            ):
                source_matches = sources.get(source_name, [])
                target_matches = targets.get(target_name, [])
                if len(source_matches) != 1 or len(target_matches) != 1:
                    continue
                source_column, target_column = source_matches[0][1], target_matches[0][1]
                role_pair = (source_column["role"], target_column["role"])
                compatible = source_column["type"] == target_column["type"] and (
                    source_column["role"] == target_column["role"] or role_pair == ("data", "discriminator")
                )
                if source_column["role"] == "identifier":
                    compatible = compatible and source_column.get("identity") == target_column.get("identity")
                if not compatible:
                    outcomes.append(
                        _invalid(
                            "registry.reference.compatible",
                            _pointer(("tables", resource, "references", r_index, "columns", c_index)),
                            resource,
                            f"{source_name!r} is incompatible with {reference['resource']}.{target_name}",
                        )
                    )
    return outcomes


def _session_scope(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    if class_name == "extension" and not core_usable:
        return []
    edges: dict[str, set[str]] = {resource: set() for resource in universe}
    for resource, table in universe.items():
        sources = _columns(table)
        for reference in table["references"]:
            target = universe.get(reference["resource"])
            if target is None or target["primary_key"] is None:
                continue
            try:
                position = reference["columns"].index("session_id")
            except ValueError:
                continue
            pairs = list(zip(reference["columns"], reference["resource_columns"], strict=False))
            if (
                position >= len(reference["resource_columns"])
                or reference["resource_columns"][position] != "session_id"
                or reference["resource_columns"] != target["primary_key"]
                or any(not _required_column(table, name) for name in reference["columns"])
                or len(pairs) != len(reference["columns"])
            ):
                continue
            target_columns = _columns(target)
            if all(
                len(sources.get(left, [])) == 1
                and len(target_columns.get(right, [])) == 1
                and sources[left][0][1]["type"] == target_columns[right][0][1]["type"]
                and (
                    sources[left][0][1]["role"] == target_columns[right][0][1]["role"]
                    or (sources[left][0][1]["role"], target_columns[right][0][1]["role"]) == ("data", "discriminator")
                )
                and sources[left][0][1].get("identity") == target_columns[right][0][1].get("identity")
                for left, right in pairs
            ):
                edges[resource].add(str(reference["resource"]))
    scoped = {"core.sessions"} if "core.sessions" in universe else set()
    changed = True
    while changed:
        changed = False
        for resource, targets in edges.items():
            if resource not in scoped and targets & scoped:
                scoped.add(resource)
                changed = True
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        matches = _columns(table).get("session_id", [])
        correct = (
            len(matches) == 1
            and matches[0][1]["type"] == "int32"
            and matches[0][1]["presence"] == "required"
            and matches[0][1]["role"] == "identifier"
            and matches[0][1].get("identity") == "assigned"
        )
        if (resource in scoped) != correct:
            outcomes.append(
                _invalid(
                    "registry.session_scope.path",
                    _pointer(("tables", resource, "columns")),
                    resource,
                    "session-preserving path and required assigned int32 session_id disagree",
                )
            )
    return outcomes


def _identity_names(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        columns = _columns(table)
        referenced = {name for reference in table["references"] for name in reference["columns"]}
        owned = {
            name
            for name in (table["primary_key"] or [])
            if name not in referenced
            and (column := _one_column(table, name)) is not None
            and column["role"] == "identifier"
            and column.get("identity") == "assigned"
        }
        assigned = {
            name
            for name, matches in columns.items()
            if len(matches) == 1
            and matches[0][1]["role"] == "identifier"
            and matches[0][1].get("identity") == "assigned"
        }
        for name in assigned:
            expected = f"{name[:-3]}_name"
            matches = columns.get(expected, [])
            if name in owned:
                correct = (
                    len(matches) == 1
                    and matches[0][1]["type"] == "string"
                    and matches[0][1]["role"] == "data"
                    and "identity" not in matches[0][1]
                )
                if not correct:
                    outcomes.append(
                        _invalid(
                            "registry.identity.name",
                            _pointer(("tables", resource, "columns")),
                            resource,
                            f"owned assigned identifier {name!r} needs exactly one string data column {expected!r}",
                        )
                    )
            elif matches:
                outcomes.append(
                    _invalid(
                        "registry.identity.name",
                        _pointer(("tables", resource, "columns", matches[0][0])),
                        resource,
                        f"carried or referenced identifier {name!r} must not have {expected!r}",
                    )
                )
    return outcomes


def _metadata(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        columns = _columns(table)
        metadata = columns.get("metadata", [])
        for index, column in metadata:
            if (
                column["type"] != "json_string"
                or column["presence"] != "optional"
                or column["role"] != "data"
                or column.get("description") != METADATA_DESCRIPTION
            ):
                outcomes.append(
                    _invalid(
                        "registry.metadata.eligibility",
                        _pointer(("tables", resource, "columns", index)),
                        resource,
                        "metadata does not have the exact standard declaration",
                    )
                )
        key = table["primary_key"] or []
        referenced = {name for reference in table["references"] for name in reference["columns"]}
        own = []
        for name in key:
            key_column = _one_column(table, name)
            if name not in referenced and key_column is not None and key_column["role"] == "identifier":
                own.append(name)
        required = bool(own)
        forbidden = bool(key) and not own and all(name in referenced for name in key)
        if required and len(metadata) != 1:
            outcomes.append(
                _invalid(
                    "registry.metadata.eligibility",
                    _pointer(("tables", resource, "columns")),
                    resource,
                    f"table owning key identifiers {own!r} needs metadata",
                )
            )
        if forbidden and metadata:
            outcomes.append(
                _invalid(
                    "registry.metadata.eligibility",
                    _pointer(("tables", resource, "columns", metadata[0][0])),
                    resource,
                    "a relationship table keyed only by reference sources must not declare metadata",
                )
            )
    return outcomes


def _determined_by(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        columns = _columns(table)
        for c_index, column in enumerate(table["columns"]):
            for d_index, name in enumerate(column.get("determined_by", [])):
                if len(columns.get(name, [])) != 1:
                    outcomes.append(
                        _invalid(
                            "registry.determined_by.resolves",
                            _pointer(("tables", resource, "columns", c_index, "determined_by", d_index)),
                            resource,
                            f"determinant {name!r} does not resolve once in the table",
                        )
                    )
    return outcomes


def _discriminator_declarations(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        columns = _columns(table)
        for index, column in enumerate(table["columns"]):
            if column["role"] != "discriminator":
                continue
            paired = "discriminates" in column
            positioned = "positions_in" in column
            if paired and positioned:
                outcomes.append(
                    _invalid(
                        "registry.discriminator.declaration",
                        _pointer(("tables", resource, "columns", index)),
                        resource,
                        "a discriminator selects both paired-value and by-position shapes",
                    )
                )
                continue
            companion_name = column.get("discriminates") or column.get("positions_in")
            if companion_name is None:
                continue
            matches = columns.get(companion_name, [])
            correct = (
                len(matches) == 1
                and matches[0][1]["type"] == "string"
                and matches[0][1]["role"] == "data"
                and matches[0][1]["presence"] == column["presence"]
                and column["presence"] in {"required", "nullable"}
            )
            if not correct:
                outcomes.append(
                    _invalid(
                        "registry.discriminator.declaration",
                        _pointer(("tables", resource, "columns", index)),
                        resource,
                        f"companion {companion_name!r} is not one matching string data column",
                    )
                )
    return outcomes


def _discriminator_paths(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    tables = document["tables"]
    for target_resource, target in tables.items():
        for c_index, column in enumerate(target["columns"]):
            via = column.get("discriminates_via")
            if via is None:
                continue
            source_resource, source_column = str(via).rsplit(".", 1)
            source = tables.get(source_resource)
            matches = [] if source is None else _columns(source).get(source_column, [])
            references = (
                []
                if source is None
                else [
                    reference
                    for reference in source["references"]
                    if source_column in reference["columns"] and reference["resource"] == target_resource
                ]
            )
            if len(matches) != 1 or len(references) != 1:
                outcomes.append(
                    _invalid(
                        "registry.discriminator.path",
                        _pointer(("tables", target_resource, "columns", c_index, "discriminates_via")),
                        target_resource,
                        f"{via!r} does not identify one reverse one-hop reference to {target_resource}",
                    )
                )
    return outcomes


def _resolve_context(
    resource: str,
    table: Mapping[str, Any],
    value: str,
    universe: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, str | None]:
    if value.count(".") == 0:
        return _one_column(table, value), None
    target_resource, target_column = value.rsplit(".", 1)
    target = universe.get(target_resource)
    references = [reference for reference in table["references"] if reference["resource"] == target_resource]
    if target is None or len(references) != 1:
        return None, target_resource
    return _one_column(target, target_column), target_resource


def _context_sources(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        for index, column in enumerate(table["columns"]):
            for field in ("unit_from", "clock_from"):
                if field not in column:
                    continue
                target, target_resource = _resolve_context(resource, table, str(column[field]), universe)
                unavailable_core = (
                    class_name == "extension"
                    and not core_usable
                    and target_resource is not None
                    and target_resource.split(".", 1)[0] in {"core", "analysis"}
                )
                if target is None and not unavailable_core:
                    outcomes.append(
                        _invalid(
                            "registry.context_source.resolves",
                            _pointer(("tables", resource, "columns", index, field)),
                            resource,
                            f"{field} source {column[field]!r} does not resolve through exactly one path",
                        )
                    )
                if field == "unit_from" and target is not None:
                    authorities = {entry["uri"] for entry in target.get("authority", [])}
                    if target["type"] != "string" or "https://ucum.org/ucum" not in authorities:
                        outcomes.append(
                            _invalid(
                                "registry.context_source.resolves",
                                _pointer(("tables", resource, "columns", index, field)),
                                resource,
                                "unit_from target is not a UCUM-authorized string column",
                            )
                        )
            if column["role"] != "coordinate":
                continue
            source_name = str(column.get("clock_from", "clock_id"))
            source, source_resource = _resolve_context(resource, table, source_name, universe)
            if source is None:
                if not (class_name == "extension" and not core_usable and "." in source_name):
                    outcomes.append(
                        _invalid(
                            "registry.context_source.resolves",
                            _pointer(("tables", resource, "columns", index)),
                            resource,
                            f"coordinate clock source {source_name!r} does not resolve",
                        )
                    )
                continue
            declaring_table = table if source_resource is None else universe[source_resource]
            participates = any(
                reference["resource"] == "core.clocks"
                and any(
                    left == source["name"] and right == "clock_id"
                    for left, right in zip(reference["columns"], reference["resource_columns"], strict=False)
                )
                for reference in declaring_table["references"]
            )
            if source["role"] != "identifier" or not participates:
                outcomes.append(
                    _invalid(
                        "registry.context_source.resolves",
                        _pointer(("tables", resource, "columns", index)),
                        resource,
                        f"clock source {source_name!r} is not an identifier referenced to core.clocks.clock_id",
                    )
                )
    return outcomes


def _absolute_uri(value: str) -> bool:
    if any(character.isspace() for character in value):
        return False
    parsed = urlsplit(value)
    return bool(parsed.scheme) and (bool(parsed.netloc) or parsed.scheme not in {"http", "https"})


def _authority_uris(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        for c_index, column in enumerate(table["columns"]):
            authorities = column.get("authority", [])
            if authorities and not (
                column["type"] == "string"
                and column["role"] == "data"
                and column.get("vocabulary") in {"open", "closed"}
            ):
                outcomes.append(
                    _invalid(
                        "registry.authority.uri",
                        _pointer(("tables", resource, "columns", c_index, "authority")),
                        resource,
                        "authority is permitted only on string data with an open or closed vocabulary",
                    )
                )
            seen: set[str] = set()
            for a_index, authority in enumerate(authorities):
                uri = str(authority["uri"])
                name = str(authority["name"])
                valid = _absolute_uri(uri) and uri not in seen
                valid = valid and ((name == "UCUM") == (uri == "https://ucum.org/ucum"))
                if not valid:
                    outcomes.append(
                        _invalid(
                            "registry.authority.uri",
                            _pointer(("tables", resource, "columns", c_index, "authority", a_index)),
                            resource,
                            f"authority {name!r}, {uri!r} has invalid or duplicate identity",
                        )
                    )
                seen.add(uri)
    return outcomes


def _rule_ids_unique(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    seen: set[str] = set()
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        for index, rule in enumerate(table["rules"]):
            rule_id = str(rule["id"])
            if rule_id in seen:
                outcomes.append(
                    _invalid(
                        "registry.rule.id_unique",
                        _pointer(("tables", resource, "rules", index, "id")),
                        rule_id,
                        f"rule ID {rule_id!r} occurs more than once",
                    )
                )
            seen.add(rule_id)
    return outcomes


def _rule_ids_owned(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, class_name, core_usable
    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        for index, rule in enumerate(table["rules"]):
            rule_id = str(rule["id"])
            suffix = rule_id.removeprefix(f"{resource}.")
            valid = rule_id.startswith(f"{resource}.") and suffix.count(".") == 0
            valid = valid and bool(re.fullmatch(r"[a-z][a-z0-9_]*", suffix))
            if not valid:
                outcomes.append(
                    _invalid(
                        "registry.rule.id_owner",
                        _pointer(("tables", resource, "rules", index, "id")),
                        rule_id,
                        f"rule ID is not exactly {resource}.local_rule_id",
                    )
                )
    return outcomes


def _core_device_detail(
    document: Mapping[str, Any], universe: Mapping[str, Any], class_name: str, core_usable: bool
) -> list[Outcome]:
    del universe, core_usable
    if class_name != "core":
        return []
    return [
        _invalid(
            "registry.core.device_detail",
            _pointer(("tables", resource, "primary_key", 0)),
            resource,
            "a core table other than core.devices is shaped as a device-detail table",
        )
        for resource, table in document["tables"].items()
        if resource != "core.devices" and table["primary_key"] and table["primary_key"][0] == "device_id"
    ]


def _rule_outcomes(document: Mapping[str, Any], core: Mapping[str, Any] | None) -> list[Outcome]:
    outcomes: list[Outcome] = []
    visible = dict(document["tables"])
    if core is not None:
        visible = dict(core["tables"]) | visible
    for resource, table in document["tables"].items():
        for index, rule in enumerate(table["rules"]):
            pointer = _pointer(("tables", resource, "rules", index))
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
                outcomes.append(_invalid(PROFILE_ID, pointer, rule_id, str(exc)))
                continue
            optional = sorted(
                f"{input_resource}.{column}"
                for input_resource, column in checked.inputs
                if (spec := visible.get(input_resource)) is not None
                and (declared := _one_column(spec, column)) is not None
                and declared["presence"] == "optional"
            )
            if optional:
                outcomes.append(
                    _invalid(
                        "registry.rule.required_inputs",
                        pointer,
                        rule_id,
                        f"rule binds optional inputs: {', '.join(optional)}",
                    )
                )
    return outcomes


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


def _unit_outcomes(document: Mapping[str, Any]) -> list[Outcome]:
    parser = _ucum_parser()
    if parser is None:
        return [
            Outcome(
                "unsupported",
                "registry.unit.ucum_2_2_cs",
                reason="registry.phase.prerequisite_unsupported",
                detail="the exact UCUM 2.2 domain dated 2024-06-17 is unavailable",
            )
        ]
    from ucumvert import InvalidUcumError, parse_ucum  # type: ignore[import-untyped]

    outcomes: list[Outcome] = []
    for resource, table in document["tables"].items():
        for index, column in enumerate(table["columns"]):
            if "unit" not in column:
                continue
            try:
                parse_ucum(str(column["unit"]), parser=parser)
            except InvalidUcumError as exc:
                outcomes.append(
                    _invalid(
                        "registry.unit.ucum_2_2_cs",
                        _pointer(("tables", resource, "columns", index, "unit")),
                        resource,
                        str(exc).splitlines()[0],
                    )
                )
    return outcomes


def against_schema(document: Any) -> list[Finding]:
    """Return the shape phase as the legacy finding view."""
    if not isinstance(document, Mapping):
        return [Finding("shape", ("document is not a mapping",))]
    result = check_registry(document)
    shape = next(phase for phase in result.phases if phase.phase == "shape")
    return [Finding("shape", tuple(item.detail or item.id for item in shape.outcomes))]


def structural(tables: Mapping[str, Any], universe: Mapping[str, Any], *, is_core: bool = False) -> list[Finding]:
    """Return semantic invariants for callers that already selected and shaped a document."""
    document: dict[str, Any] = {"tables": tables}
    if not is_core:
        namespace = next(iter(tables)).split(".", 1)[0] if tables else "extension"
        document["extension_id"] = namespace
    outcomes = _semantic_outcomes(document, universe, "core" if is_core else "extension", True)
    labels = [entry["id"] for entry in json.loads(CONTRACT.read_text())["invariants"] if entry["phase"] == "semantic"]
    return [
        Finding(
            label,
            tuple(item.detail or item.instance for item in outcomes if item.id == label and item.state == "invalid"),
        )
        for label in labels
        if is_core or label != "registry.core.device_detail"
    ]


def declarations(document: Any, name: str | None = None) -> list[Finding]:
    """Return document-class and namespace findings through the compatibility interface."""
    del name
    if not isinstance(document, Mapping) or "tables" not in document:
        return [Finding("registry document shape", ("document has no tables mapping",))]
    universe = document["tables"]
    outcomes = _namespace_owned(document, universe, "extension", True) + _reference_direction(
        document, universe, "extension", True
    )
    return [
        Finding(label, tuple(item.detail or item.instance for item in outcomes if item.id == label))
        for label in ("registry.namespace.owned", "registry.namespace.reference_direction")
    ]


def check_extension(document: Any, core: Any, *, name: str | None = None) -> list[Finding]:
    """Validate one extension and return a concise legacy finding list."""
    del name
    if not isinstance(document, Mapping) or not isinstance(core, Mapping):
        return [Finding("registry document", ("document and core must be mappings",))]
    result = check_registry(document, core)
    grouped: dict[str, list[str]] = {}
    for outcome in result.findings:
        grouped.setdefault(outcome.id, []).append(outcome.detail or outcome.instance)
    return [Finding(label, tuple(offenders)) for label, offenders in grouped.items()]


__all__ = [
    "CONTRACT",
    "CONTRACT_SCHEMA",
    "SCHEMA",
    "Finding",
    "Outcome",
    "PhaseRecord",
    "RegistryResult",
    "against_schema",
    "check_extension",
    "check_registry",
    "check_registry_bytes",
    "declarations",
    "structural",
]

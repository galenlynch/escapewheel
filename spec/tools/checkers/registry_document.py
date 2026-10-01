"""Validate registry documents against the incorporated Part 02 contract."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import Enum
from functools import cache
from importlib.resources import files
from typing import Any, NamedTuple
from urllib.parse import urlsplit
from xml.etree import ElementTree

import jsonschema

from .artifacts import ARTIFACTS
from .rule_language import PROFILE_ID, RuleProfileError, check_rule

SCHEMA = ARTIFACTS / "registry.schema.json"
CONTRACT_SCHEMA = ARTIFACTS / "registry_contract.schema.json"
CONTRACT = ARTIFACTS / "registry_contracts" / "escapewheel-registry-contract-v0.9.json"
RESULT_SCHEMA = ARTIFACTS / "registry_result.schema.json"
UCUM_URI = "https://ucum.org/ucum"
RESULT_SCHEMA_ID = "https://escapewheel.org/schemas/registry-result/0.1.0"
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
    detail: str | None = dataclass_field(default=None, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """Return this outcome's portable Part 02 representation."""
        result: dict[str, Any] = {"state": self.state, "id": self.id, "instance": self.instance}
        for name in ("owner", "reason", "schema_location", "detail"):
            if (value := getattr(self, name)) is not None:
                result[name] = value
        return result


@dataclass(frozen=True)
class PhaseRecord:
    """The state and ordered non-passing outcomes of one contract phase."""

    phase: str
    state: str
    outcomes: tuple[Outcome, ...] = ()
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return this phase's portable Part 02 representation."""
        result: dict[str, Any] = {
            "phase": self.phase,
            "state": self.state,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


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

    def to_dict(self) -> dict[str, Any]:
        """Return the portable representation incorporated by Part 02 §9.5."""
        return {
            "$schema": RESULT_SCHEMA_ID,
            "descriptor_id": self.descriptor_id,
            "state": self.state,
            "phases": [phase.to_dict() for phase in self.phases],
        }


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        from types import MappingProxyType

        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


@dataclass(frozen=True)
class CheckedRegistryContext(Mapping[str, Any]):
    """One registry result bound to immutable input and evaluation context."""

    input_kind: str
    exact_input: Any
    decoded: Any
    result: RegistryResult
    descriptors: tuple[str, ...]
    external_domains: tuple[str, ...]
    core: CheckedRegistryContext | None = None

    @property
    def document(self) -> Any:
        """Return an isolated ordinary-Python copy of the checked decoded value."""
        return _thaw(self.decoded)

    def __getitem__(self, key: str) -> Any:
        """Read one member from an isolated copy of the checked document."""
        document = self.document
        if not isinstance(document, Mapping):
            raise KeyError(key)
        return document[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate the checked document's root member names."""
        document = self.document
        return iter(document if isinstance(document, Mapping) else {})

    def __len__(self) -> int:
        """Return the checked document's number of root members."""
        document = self.document
        return len(document) if isinstance(document, Mapping) else 0

    def __deepcopy__(self, memo: dict[int, Any]) -> Any:
        """Materialize a mutable copy without copying locks or mapping proxies."""
        del memo
        return self.document


class RegistryRejected(ValueError):
    """A production boundary received a non-valid registry context."""

    def __init__(self, subject: str, context: CheckedRegistryContext) -> None:
        self.subject = subject
        self.context = context
        self.result = context.result
        super().__init__(f"{subject} registry is {context.result.state}")


class _Object(dict[str, Any]):
    """Decoded object retaining duplicate member names for the JSON phase."""

    duplicates: tuple[str, ...]

    def __init__(self, pairs: list[tuple[str, Any]]) -> None:
        super().__init__(pairs)
        counts = Counter(name for name, _ in pairs)
        self.duplicates = tuple(sorted(name for name, count in counts.items() if count > 1))


def _pointer(parts: Iterable[Any]) -> str:
    parts = tuple(parts)
    if len(parts) >= 2 and parts[0] == "tables":
        parts = ("resources", parts[1], "table", *parts[2:])
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in parts)


def _owner(pointer: str) -> str | None:
    parts = pointer.split("/")
    if len(parts) >= 3 and parts[1] == "resources":
        return parts[2].replace("~1", "/").replace("~0", "~")
    return None


def _tables(document: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Project table-kind payloads from the sole serialized resource authority."""
    return {
        str(resource_id): declaration["table"]
        for resource_id, declaration in document.get("resources", {}).items()
        if declaration.get("kind") == "table" and "table" in declaration
    }


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
        return CheckedRegistryContext(
            "bytes", bytes(data), None, result, descriptor_identity, _external_domains(), core
        )
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
        return CheckedRegistryContext(
            "bytes", bytes(data), None, result, descriptor_identity, _external_domains(), core
        )
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
            "bytes", bytes(data), _freeze(document), result, descriptor_identity, _external_domains(), core
        )
    result = _check_mapping(
        document,
        core.document if core is not None else None,
        PhaseRecord("json", "passed"),
        descriptor_values,
        core.result if core is not None else None,
    )
    domains = _external_domains()
    return CheckedRegistryContext("bytes", bytes(data), _freeze(document), result, descriptor_identity, domains, core)


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
    domains = _external_domains()
    frozen = _freeze(copied)
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

    tables = dict(_tables(document))
    declarations = dict(document["resources"])
    if class_name == "extension" and core_usable and core is not None:
        tables = dict(_tables(core)) | tables
        declarations = dict(core["resources"]) | declarations
    assert descriptor is not None
    semantic = _semantic_outcomes(
        document,
        class_name,
        core_usable,
        descriptor,
        {Universe.TABLES: tables, Universe.DECLARATIONS: declarations},
    )
    phases.append(_phase("semantic", semantic))
    rules = _rule_outcomes(document, core if core_usable and class_name == "extension" else None)
    phases.append(_phase("rule_static", rules))
    phases.append(_phase("external_domain", _unit_outcomes(document)))
    return _complete(phases, descriptor_id)


def _invalid(invariant: str, pointer: str, owner: str | None, detail: str) -> Outcome:
    return Outcome("invalid", invariant, pointer, owner, detail=detail)


class Defect(NamedTuple):
    """One place a document breaks an invariant, reported under the ID the invariant is registered with."""

    instance: str
    owner: str | None
    detail: str


@dataclass(frozen=True)
class Scope:
    """What an invariant reads: the document, its class, and the universe its names resolve in."""

    document: Mapping[str, Any]
    class_name: str
    core_usable: bool
    universe: Mapping[str, Any]

    @property
    def core_missing(self) -> bool:
        """Whether the document is an extension checked without a usable core."""
        return self.class_name == "extension" and not self.core_usable

    def withheld(self, resource: str) -> bool:
        """Whether `resource` lies in a core namespace that a missing core leaves unresolvable."""
        return self.core_missing and resource.split(".", 1)[0] in {"core", "analysis"}


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
    class_name: str,
    core_usable: bool,
    descriptor: Mapping[str, Any],
    universes: Mapping[Universe, Mapping[str, Any]],
) -> list[Outcome]:
    """Run each semantic invariant the descriptor applies to this class of document."""
    invariants = {invariant.id: invariant for invariant in INVARIANTS}
    scopes = {kind: Scope(document, class_name, core_usable, universe) for kind, universe in universes.items()}
    outcomes: list[Outcome] = []
    for entry in descriptor["invariants"]:
        if entry["phase"] != "semantic" or class_name not in entry["classes"]:
            continue
        invariant = invariants[str(entry["id"])]
        outcomes.extend(_invalid(invariant.id, *defect) for defect in invariant.check(scopes[invariant.universe]))
        if class_name == "extension" and not core_usable and invariant.needs_core:
            outcomes.append(
                Outcome(
                    "incomplete",
                    invariant.id,
                    reason="registry.phase.prerequisite_incomplete",
                    detail="usable core context is required for cross-registry resolution",
                )
            )
    return outcomes


def _resource_classification(scope: Scope) -> list[Defect]:
    permitted = (
        {"core", "analysis", "compatibility_projection", "documentation"}
        if scope.class_name == "core"
        else {"extension", "analysis", "compatibility_projection", "documentation"}
    )
    defects: list[Defect] = []
    for resource, declaration in scope.document["resources"].items():
        content_class = str(declaration["content_class"])
        if content_class not in permitted:
            defects.append(
                Defect(
                    _pointer(("resources", resource, "content_class")),
                    resource,
                    f"content class {content_class!r} is not permitted in a {scope.class_name} registry",
                )
            )
    return defects


def _resource_instance(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, declaration in scope.document["resources"].items():
        instances = declaration["instances"]
        if (
            declaration["content_class"] in {"analysis", "compatibility_projection", "documentation"}
            and instances["mode"] == "singleton"
            and instances["presence"] != "optional"
        ):
            defects.append(
                Defect(
                    _pointer(("resources", resource, "instances", "presence")),
                    resource,
                    f"{declaration['content_class']} declarations must be optional",
                )
            )
        if (
            declaration["content_class"] in {"analysis", "compatibility_projection"}
            and declaration["lineage"] != "required"
        ):
            defects.append(
                Defect(
                    _pointer(("resources", resource, "lineage")),
                    resource,
                    f"{declaration['content_class']} declarations require lineage",
                )
            )
        if declaration["content_class"] == "documentation" and declaration["lineage"] != "forbidden":
            defects.append(
                Defect(
                    _pointer(("resources", resource, "lineage")),
                    resource,
                    "documentation declarations forbid lineage",
                )
            )
    return defects


def _resource_direction(target: str, document: Mapping[str, Any], class_name: str) -> bool:
    if class_name == "core":
        return target in document["resources"]
    return target.split(".", 1)[0] in {
        "core",
        "analysis",
        str(document["extension_id"]),
    }


def _resource_catalog(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    pairs: dict[tuple[str, str], str] = {}
    for resource, declaration in scope.document["resources"].items():
        instances = declaration["instances"]
        if instances["mode"] != "catalog":
            continue
        target_name = str(instances["catalog_resource"])
        column_name = str(instances["resource_id_column"])
        target = scope.universe.get(target_name)
        unavailable_core = scope.withheld(target_name)
        eligible = target is not None and target["kind"] == "table"
        eligible = eligible and target["instances"]["mode"] == "singleton" if target else False
        column = None if not eligible else _one_column(target["table"], column_name)
        eligible = eligible and column is not None
        if column is not None:
            eligible = eligible and all(
                (
                    column["type"] == "string",
                    column["presence"] == "required",
                    column["role"] == "identifier",
                    column.get("identity") == "carried",
                    column.get("vocabulary") == "free",
                )
            )
        eligible = eligible and _resource_direction(target_name, scope.document, scope.class_name)
        if not eligible and not unavailable_core:
            defects.append(
                Defect(
                    _pointer(("resources", resource, "instances")),
                    resource,
                    f"catalog binding {target_name}.{column_name} is not one eligible visible singleton table column",
                )
            )
        pair = (target_name, column_name)
        if pair in pairs:
            defects.append(
                Defect(
                    _pointer(("resources", resource, "instances")),
                    resource,
                    f"catalog pair {target_name}.{column_name} is already owned by {pairs[pair]}",
                )
            )
        else:
            pairs[pair] = resource
    return defects


def _resource_array_axes(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, declaration in scope.document["resources"].items():
        if declaration["kind"] != "dense_array":
            continue
        axes_name = str(declaration["array"]["axes_resource"])
        catalog_name = str(declaration["instances"]["catalog_resource"])
        axes = scope.universe.get(axes_name)
        unavailable_core = scope.withheld(axes_name)
        eligible = axes is not None and axes["kind"] == "table"
        eligible = eligible and axes["instances"]["mode"] == "singleton" if axes else False
        bindings: list[Mapping[str, Any]] = []
        if eligible and axes is not None:
            table = axes["table"]
            catalog = scope.universe.get(catalog_name)
            catalog_key = None if catalog is None or catalog["kind"] != "table" else catalog["table"]["primary_key"]
            bindings = [
                reference
                for reference in table["references"]
                if reference["resource"] == catalog_name
                and catalog_key is not None
                and reference["resource_columns"] == catalog_key
                and table["primary_key"] is not None
                and table["primary_key"][: len(reference["columns"])] == reference["columns"]
                and len(table["primary_key"]) == len(reference["columns"]) + 1
                and (index_column := _one_column(table, table["primary_key"][-1])) is not None
                and index_column["presence"] == "required"
                and index_column["role"] == "structural_index"
            ]
            eligible = len(bindings) == 1
        eligible = eligible and _resource_direction(axes_name, scope.document, scope.class_name)
        if not eligible and not unavailable_core:
            defects.append(
                Defect(
                    _pointer(("resources", resource, "array", "axes_resource")),
                    resource,
                    f"axes resource {axes_name!r} does not provide exactly one eligible catalog binding",
                )
            )
    return defects


def _resource_dependency(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, declaration in scope.document["resources"].items():
        for index, target_name in enumerate(declaration["requires"]):
            target = scope.universe.get(target_name)
            unavailable_core = scope.withheld(target_name)
            eligible = target is not None and target["instances"]["mode"] == "singleton"
            eligible = eligible and _resource_direction(target_name, scope.document, scope.class_name)
            if not eligible and not unavailable_core:
                defects.append(
                    Defect(
                        _pointer(("resources", resource, "requires", index)),
                        resource,
                        f"dependency {target_name!r} is not one visible singleton declaration",
                    )
                )
    return defects


CANONICAL_CLASSES = frozenset({"core", "extension"})


def _resource_canonical_targets(scope: Scope) -> list[Defect]:
    """Part 02 §2.2: a canonical declaration depends only on canonical ones.

    An unresolved target is left to the invariant that resolves it, so one defect is not reported
    twice; a discriminator names without depending and is not a reference here.
    """
    defects: list[Defect] = []
    for resource, declaration in scope.document["resources"].items():
        if declaration["content_class"] not in CANONICAL_CLASSES:
            continue
        targets: list[tuple[str, tuple[Any, ...]]] = []
        if declaration.get("kind") == "table" and "table" in declaration:
            targets += [
                (str(reference["resource"]), ("tables", resource, "references", index, "resource"))
                for index, reference in enumerate(declaration["table"]["references"])
            ]
        targets += [
            (str(name), ("resources", resource, "requires", index))
            for index, name in enumerate(declaration["requires"])
        ]
        if declaration["instances"]["mode"] == "catalog":
            targets.append(
                (
                    str(declaration["instances"]["catalog_resource"]),
                    ("resources", resource, "instances", "catalog_resource"),
                )
            )
        for target_name, parts in targets:
            target = scope.universe.get(target_name)
            if target is None or target["content_class"] in CANONICAL_CLASSES:
                continue
            defects.append(
                Defect(
                    _pointer(parts),
                    resource,
                    f"canonical declaration depends on {target['content_class']} declaration {target_name!r}",
                )
            )
    return defects


def _amendment_groups(scope: Scope) -> list[Defect]:
    """Part 02 §2.8: a group list names present columns once, and only a canonical table has one."""
    defects: list[Defect] = []
    for resource, declaration in scope.document["resources"].items():
        table = _tables(scope.document).get(resource)
        if table is None:
            continue
        groups = table["amendment_groups"]
        if groups and declaration["content_class"] not in CANONICAL_CLASSES:
            defects.append(
                Defect(
                    _pointer(("tables", resource, "amendment_groups")),
                    resource,
                    f"a {declaration['content_class']} table declares amendment groups",
                )
            )
            continue
        columns = _columns(table)
        seen: set[frozenset[str]] = set()
        for index, group in enumerate(groups):
            for position, name in enumerate(group):
                found = columns.get(str(name), [])
                if len(found) != 1 or found[0][1]["presence"] == "optional":
                    defects.append(
                        Defect(
                            _pointer(("tables", resource, "amendment_groups", index, position)),
                            resource,
                            f"group-list member {name!r} names "
                            + ("an optional column" if found else "no column of the table"),
                        )
                    )
            members = frozenset(map(str, group))
            if members in seen:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "amendment_groups", index)),
                        resource,
                        "another group list names the same columns",
                    )
                )
            seen.add(members)
    return defects


def _specialisations(scope: Scope) -> list[Defect]:
    """Part 02 §8.3: a specialising reference names a shared-key discriminator of the table it targets."""
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        declared = [(index, r) for index, r in enumerate(table["references"]) if "specialises" in r]
        for position, (r_index, reference) in enumerate(declared):
            pointer = _pointer(("tables", resource, "references", r_index, "specialises"))
            if position > 0:
                defects.append(Defect(pointer, resource, "the table declares specialises on another reference"))
                continue
            holder_name, column_name = str(reference["specialises"]).rsplit(".", 1)
            holder = scope.universe.get(holder_name)
            if holder is None and scope.withheld(holder_name):
                continue  # reported incomplete as core-dependent
            column = None if holder is None else _one_column(holder, column_name)
            if column is None or column["role"] != "discriminator" or "discriminates" in column:
                problem = (
                    "names no visible column"
                    if column is None
                    else "names a column that is not a discriminator"
                    if column["role"] != "discriminator"
                    else "names a paired-value discriminator"
                )
                defects.append(Defect(pointer, resource, f"specialises {problem}"))
                continue
            via = column.get("discriminates_via")
            specialised = holder_name if via is None else str(via).rsplit(".", 1)[0]
            if reference["resource"] != specialised:
                target = reference["resource"]
                defects.append(Defect(pointer, resource, f"the reference targets {target}, not {specialised}"))
            columns = list(reference["columns"])
            if list(table.get("primary_key") or [])[: len(columns)] != columns:
                message = "the primary key does not begin with the reference's columns"
                defects.append(Defect(pointer, resource, message))
    return defects


def _namespace_owned(scope: Scope) -> list[Defect]:
    allowed = {"core", "analysis"} if scope.class_name == "core" else {str(scope.document["extension_id"])}
    return [
        Defect(
            _pointer(("tables", resource)),
            resource,
            f"namespace {resource.split('.', 1)[0]!r} is not owned by this {scope.class_name} registry",
        )
        for resource in scope.document["resources"]
        if resource.split(".", 1)[0] not in allowed
    ]


def _reference_direction(scope: Scope) -> list[Defect]:
    own = set(_tables(scope.document))
    extension_id = scope.document.get("extension_id")
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        for index, reference in enumerate(table["references"]):
            target = str(reference["resource"])
            namespace = target.split(".", 1)[0]
            permitted = target in own if scope.class_name == "core" else namespace in {"core", "analysis", extension_id}
            if not permitted:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "references", index, "resource")),
                        resource,
                        f"reference target {target!r} is outside the permitted direction",
                    )
                )
    return defects


def _column_names(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        seen: set[str] = set()
        for index, column in enumerate(table["columns"]):
            name = str(column["name"])
            if name in seen:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "columns", index, "name")),
                        resource,
                        f"column name {name!r} occurs more than once",
                    )
                )
            seen.add(name)
    return defects


def _primary_keys(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        columns = _columns(table)
        for index, name in enumerate(table["primary_key"] or []):
            resolved = columns.get(name, [])
            if len(resolved) != 1:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "primary_key", index)),
                        resource,
                        f"primary-key member {name!r} resolves {len(resolved)} times",
                    )
                )
            elif resolved[0][1]["presence"] != "required":
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "primary_key", index)),
                        resource,
                        f"primary-key member {name!r} is not required",
                    )
                )
    return defects


def _references_resolve(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        source_columns = _columns(table)
        for r_index, reference in enumerate(table["references"]):
            base = ("tables", resource, "references", r_index)
            target_name = str(reference["resource"])
            target = scope.universe.get(target_name)
            if target is None:
                if not scope.withheld(target_name):
                    defects.append(
                        Defect(
                            _pointer((*base, "resource")),
                            resource,
                            f"target resource {target_name!r} does not resolve",
                        )
                    )
                continue
            target_columns = _columns(target)
            if len(reference["columns"]) != len(reference["resource_columns"]):
                defects.append(
                    Defect(
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
                        defects.append(
                            Defect(
                                _pointer((*base, side, c_index)),
                                resource,
                                f"reference member {name!r} resolves {len(available.get(name, []))} times",
                            )
                        )
    return defects


def _reference_targets_key(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        for index, reference in enumerate(table["references"]):
            target = scope.universe.get(reference["resource"])
            if target is not None and (
                target["primary_key"] is None or reference["resource_columns"] != target["primary_key"]
            ):
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "references", index, "resource_columns")),
                        resource,
                        f"target side is not the complete ordered key of {reference['resource']}",
                    )
                )
    return defects


def _references_compatible(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        sources = _columns(table)
        for r_index, reference in enumerate(table["references"]):
            target = scope.universe.get(reference["resource"])
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
                    defects.append(
                        Defect(
                            _pointer(("tables", resource, "references", r_index, "columns", c_index)),
                            resource,
                            f"{source_name!r} is incompatible with {reference['resource']}.{target_name}",
                        )
                    )
    return defects


def _session_scope(scope: Scope) -> list[Defect]:
    if scope.core_missing:
        return []
    edges: dict[str, set[str]] = {resource: set() for resource in scope.universe}
    for resource, table in scope.universe.items():
        sources = _columns(table)
        for reference in table["references"]:
            target = scope.universe.get(reference["resource"])
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
    scoped = {"core.sessions"} if "core.sessions" in scope.universe else set()
    changed = True
    while changed:
        changed = False
        for resource, targets in edges.items():
            if resource not in scoped and targets & scoped:
                scoped.add(resource)
                changed = True
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        matches = _columns(table).get("session_id", [])
        correct = (
            len(matches) == 1
            and matches[0][1]["type"] == "int32"
            and matches[0][1]["presence"] == "required"
            and matches[0][1]["role"] == "identifier"
            and matches[0][1].get("identity") == "assigned"
        )
        if (resource in scoped) != correct:
            defects.append(
                Defect(
                    _pointer(("tables", resource, "columns")),
                    resource,
                    "session-preserving path and required assigned int32 session_id disagree",
                )
            )
    return defects


def _registry_id(scope: Scope) -> list[Defect]:
    """Part 02 §9.1: an extension binds under its own namespace, so the two names are one."""
    registry_id, extension_id = scope.document["registry_id"], scope.document["extension_id"]
    if registry_id == extension_id:
        return []
    return [Defect("/registry_id", None, f"registry_id {registry_id!r} differs from extension_id {extension_id!r}")]


def _identity_names(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
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
                    defects.append(
                        Defect(
                            _pointer(("tables", resource, "columns")),
                            resource,
                            f"owned assigned identifier {name!r} needs exactly one string data column {expected!r}",
                        )
                    )
            elif matches:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "columns", matches[0][0])),
                        resource,
                        f"carried or referenced identifier {name!r} must not have {expected!r}",
                    )
                )
    return defects


def _metadata(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        columns = _columns(table)
        metadata = columns.get("metadata", [])
        for index, column in metadata:
            if (
                column["type"] != "json_string"
                or column["presence"] != "optional"
                or column["role"] != "data"
                or column.get("description") != METADATA_DESCRIPTION
            ):
                defects.append(
                    Defect(
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
            defects.append(
                Defect(
                    _pointer(("tables", resource, "columns")),
                    resource,
                    f"table owning key identifiers {own!r} needs metadata",
                )
            )
        if forbidden and metadata:
            defects.append(
                Defect(
                    _pointer(("tables", resource, "columns", metadata[0][0])),
                    resource,
                    "a relationship table keyed only by reference sources must not declare metadata",
                )
            )
    return defects


def _determined_by(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        columns = _columns(table)
        for c_index, column in enumerate(table["columns"]):
            for d_index, name in enumerate(column.get("determined_by", [])):
                if len(columns.get(name, [])) != 1:
                    defects.append(
                        Defect(
                            _pointer(("tables", resource, "columns", c_index, "determined_by", d_index)),
                            resource,
                            f"determinant {name!r} does not resolve once in the table",
                        )
                    )
    return defects


def _discriminator_declarations(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    tables = _tables(scope.document)
    for resource, table in tables.items():
        for index, column in enumerate(table["columns"]):
            if column["role"] != "discriminator" or (companion_name := column.get("discriminates")) is None:
                continue
            # Part 02 §8.3: the paired value sits on the specialised table where `discriminates_via`
            # names one, and there a null value names no row of the row's kind rather than leaving
            # the kind undeterminable, so it may be nullable whatever the discriminator's presence.
            via = column.get("discriminates_via")
            if via is None:
                holder, allowed = table, {column["presence"]} & {"required", "nullable"}
            else:
                holder = tables.get(str(via).rsplit(".", 1)[0])
                if holder is None:
                    continue  # `registry.discriminator.path` reports a target that does not resolve
                allowed = {"required", "nullable"}
            matches = _columns(holder).get(companion_name, [])
            companion = matches[0][1] if len(matches) == 1 else None
            correct = (
                companion is not None
                and (
                    (companion["type"] == "string" and companion["role"] == "data") or companion["role"] == "identifier"
                )
                and companion["presence"] in allowed
            )
            if not correct:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "columns", index)),
                        resource,
                        f"companion {companion_name!r} is not one string data or identifier column "
                        "with the presence Part 02 §8.3 requires",
                    )
                )
    return defects


def _discriminator_paths(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    tables = _tables(scope.document)
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
                defects.append(
                    Defect(
                        _pointer(("tables", target_resource, "columns", c_index, "discriminates_via")),
                        target_resource,
                        f"{via!r} does not identify one reverse one-hop reference to {target_resource}",
                    )
                )
    return defects


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


def _context_sources(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        for index, column in enumerate(table["columns"]):
            for field in ("unit_from", "clock_from"):
                if field not in column:
                    continue
                target, target_resource = _resolve_context(resource, table, str(column[field]), scope.universe)
                unavailable_core = target_resource is not None and scope.withheld(target_resource)
                if target is None and not unavailable_core:
                    defects.append(
                        Defect(
                            _pointer(("tables", resource, "columns", index, field)),
                            resource,
                            f"{field} source {column[field]!r} does not resolve through exactly one path",
                        )
                    )
                if field == "unit_from" and target is not None:
                    authorities = {entry["uri"] for entry in target.get("authority", [])}
                    if target["type"] != "string" or UCUM_URI not in authorities:
                        defects.append(
                            Defect(
                                _pointer(("tables", resource, "columns", index, field)),
                                resource,
                                "unit_from target is not a UCUM-authorized string column",
                            )
                        )
            if column["role"] != "coordinate":
                continue
            source_name = str(column.get("clock_from", "clock_id"))
            source, source_resource = _resolve_context(resource, table, source_name, scope.universe)
            if source is None:
                if not (scope.core_missing and "." in source_name):
                    defects.append(
                        Defect(
                            _pointer(("tables", resource, "columns", index)),
                            resource,
                            f"coordinate clock source {source_name!r} does not resolve",
                        )
                    )
                continue
            declaring_table = table if source_resource is None else scope.universe[source_resource]
            participates = any(
                reference["resource"] == "core.clocks"
                and any(
                    left == source["name"] and right == "clock_id"
                    for left, right in zip(reference["columns"], reference["resource_columns"], strict=False)
                )
                for reference in declaring_table["references"]
            )
            if source["role"] != "identifier" or not participates:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "columns", index)),
                        resource,
                        f"clock source {source_name!r} is not an identifier referenced to core.clocks.clock_id",
                    )
                )
    return defects


def _absolute_uri(value: str) -> bool:
    if any(character.isspace() for character in value):
        return False
    parsed = urlsplit(value)
    return bool(parsed.scheme) and (bool(parsed.netloc) or parsed.scheme not in {"http", "https"})


def _authority_uris(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        for c_index, column in enumerate(table["columns"]):
            authorities = column.get("authority", [])
            if authorities and not (
                column["type"] == "string"
                and column["role"] == "data"
                and column.get("vocabulary") in {"open", "closed"}
            ):
                defects.append(
                    Defect(
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
                valid = valid and ((name == "UCUM") == (uri == UCUM_URI))
                if not valid:
                    defects.append(
                        Defect(
                            _pointer(("tables", resource, "columns", c_index, "authority", a_index)),
                            resource,
                            f"authority {name!r}, {uri!r} has invalid or duplicate identity",
                        )
                    )
                seen.add(uri)
    return defects


def _rule_ids_unique(scope: Scope) -> list[Defect]:
    seen: set[str] = set()
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        for index, rule in enumerate(table["rules"]):
            rule_id = str(rule["id"])
            if rule_id in seen:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "rules", index, "id")),
                        rule_id,
                        f"rule ID {rule_id!r} occurs more than once",
                    )
                )
            seen.add(rule_id)
    return defects


def _rule_ids_owned(scope: Scope) -> list[Defect]:
    defects: list[Defect] = []
    for resource, table in _tables(scope.document).items():
        for index, rule in enumerate(table["rules"]):
            rule_id = str(rule["id"])
            suffix = rule_id.removeprefix(f"{resource}.")
            valid = rule_id.startswith(f"{resource}.") and suffix.count(".") == 0
            valid = valid and bool(re.fullmatch(r"[a-z][a-z0-9_]*", suffix))
            if not valid:
                defects.append(
                    Defect(
                        _pointer(("tables", resource, "rules", index, "id")),
                        rule_id,
                        f"rule ID is not exactly {resource}.local_rule_id",
                    )
                )
    return defects


def _core_device_detail(scope: Scope) -> list[Defect]:
    if scope.class_name != "core":
        return []
    return [
        Defect(
            _pointer(("tables", resource, "primary_key", 0)),
            resource,
            "a core table other than core.devices is shaped as a device-detail table",
        )
        for resource, table in _tables(scope.document).items()
        if resource != "core.devices" and table["primary_key"] and table["primary_key"][0] == "device_id"
    ]


class Universe(Enum):
    """The declarations an invariant resolves a name against: the document's, over usable core's."""

    TABLES = "tables"
    """Each table-kind resource's table payload, by resource ID."""
    DECLARATIONS = "declarations"
    """Each resource's whole declaration, by resource ID."""


@dataclass(frozen=True)
class Invariant:
    """One semantic invariant of the registry contract, and what its check reads."""

    id: str
    check: Callable[[Scope], list[Defect]]
    universe: Universe = Universe.TABLES
    needs_core: bool = False
    """Whether an extension checked without a usable core leaves the invariant incomplete."""


#: Every semantic invariant a contract descriptor may name, each with its sole implementation.
INVARIANTS = (
    Invariant("registry.namespace.owned", _namespace_owned),
    Invariant("registry.namespace.reference_direction", _reference_direction),
    Invariant("registry.column.name_unique", _column_names),
    Invariant("registry.primary_key.resolves", _primary_keys),
    Invariant("registry.reference.resolves", _references_resolve, needs_core=True),
    Invariant("registry.reference.target_key", _reference_targets_key, needs_core=True),
    Invariant("registry.reference.compatible", _references_compatible, needs_core=True),
    Invariant("registry.session_scope.path", _session_scope, needs_core=True),
    Invariant("registry.identity.name", _identity_names),
    Invariant("registry.identity.registry_id", _registry_id),
    Invariant("registry.metadata.eligibility", _metadata),
    Invariant("registry.determined_by.resolves", _determined_by),
    Invariant("registry.discriminator.declaration", _discriminator_declarations),
    Invariant("registry.discriminator.path", _discriminator_paths),
    Invariant("registry.context_source.resolves", _context_sources, needs_core=True),
    Invariant("registry.authority.uri", _authority_uris),
    Invariant("registry.rule.id_unique", _rule_ids_unique),
    Invariant("registry.rule.id_owner", _rule_ids_owned),
    Invariant("registry.core.device_detail", _core_device_detail),
    Invariant("registry.resource.classification", _resource_classification, Universe.DECLARATIONS),
    Invariant("registry.resource.instance", _resource_instance, Universe.DECLARATIONS),
    Invariant("registry.resource.catalog", _resource_catalog, Universe.DECLARATIONS, needs_core=True),
    Invariant("registry.resource.array_axes", _resource_array_axes, Universe.DECLARATIONS, needs_core=True),
    Invariant("registry.resource.dependency", _resource_dependency, Universe.DECLARATIONS, needs_core=True),
    Invariant(
        "registry.resource.canonical_targets", _resource_canonical_targets, Universe.DECLARATIONS, needs_core=True
    ),
    Invariant("registry.amendment_groups.resolves", _amendment_groups),
    Invariant("registry.discriminator.specialisation", _specialisations, needs_core=True),
)


def _rule_outcomes(document: Mapping[str, Any], core: Mapping[str, Any] | None) -> list[Outcome]:
    outcomes: list[Outcome] = []
    visible = dict(_tables(document))
    if core is not None:
        visible = dict(_tables(core)) | visible
    for resource, table in _tables(document).items():
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


def _external_domains() -> tuple[str, ...]:
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


def _unit_outcomes(document: Mapping[str, Any]) -> list[Outcome]:
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
    for resource, table in _tables(document).items():
        for index, column in enumerate(table["columns"]):
            if "unit" not in column:
                continue
            error = ucum_error(str(column["unit"]))
            if error is not None:
                outcomes.append(
                    _invalid(
                        "registry.unit.ucum_2_2_cs",
                        _pointer(("tables", resource, "columns", index, "unit")),
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

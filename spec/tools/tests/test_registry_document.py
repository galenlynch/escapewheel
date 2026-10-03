"""The complete Part 02 §9.4 registry-document conformance contract."""

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from checkers import registry_document, registry_invariants, registry_phases
from checkers.artifacts import ARTIFACTS
from checkers.registry_document import (
    CONTRACT,
    METADATA_DESCRIPTION,
    PHASES,
    RESULT_SCHEMA,
    SCHEMA,
    check_registry,
    check_registry_bytes,
    check_registry_context,
    check_registry_context_bytes,
)

CORE = json.loads((ARTIFACTS / "logical_schemas.json").read_text())


def _column(name, **overrides):
    column = {
        "name": name,
        "type": "int32",
        "presence": "required",
        "role": "identifier",
        "identity": "assigned",
        "description": "A demonstration column.",
    }
    column.update(overrides)
    if column["role"] != "identifier":
        column.pop("identity", None)
    if column["type"] in {"float32", "float64"}:
        column.setdefault("finite", True)
    return column


def _document():
    return {
        "$schema": json.loads(SCHEMA.read_text())["$id"],
        "registry_id": "demo",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.2",
        "extension_id": "demo",
        "resources": {
            "demo.rows": {
                "content_class": "extension",
                "kind": "table",
                "instances": {"mode": "singleton", "presence": "optional"},
                "requires": [],
                "lineage": "optional",
                "table": {
                    "primary_key": ["session_id", "demo_id"],
                    "amendment_groups": [["session_id", "demo_id"]],
                    "columns": [
                        _column("session_id"),
                        _column("demo_id", identity="carried"),
                        _column(
                            "metadata",
                            type="json_string",
                            presence="optional",
                            role="data",
                            description=METADATA_DESCRIPTION,
                        ),
                    ],
                    "references": [
                        {
                            "columns": ["session_id"],
                            "resource": "core.sessions",
                            "resource_columns": ["session_id"],
                        }
                    ],
                    "rules": [],
                },
            }
        },
    }


def _table(document, name="demo.rows"):
    return document["resources"][name]["table"]


def _ids(result):
    return {outcome.id for phase in result.phases for outcome in phase.outcomes}


def test_reference_registry_has_one_complete_valid_result():
    result = check_registry(CORE)
    assert result.state == "valid"
    assert result.descriptor_id == "escapewheel-registry-contract-v0.10"
    assert tuple(phase.phase for phase in result.phases) == PHASES
    assert result.phases[0].state == "skipped"
    assert result.phases[0].reason == "registry.phase.mapping_input"
    assert result.findings == ()


def test_portable_result_validates_against_the_incorporated_schema():
    context = check_registry_context_bytes((ARTIFACTS / "logical_schemas.json").read_bytes())
    Draft202012Validator(json.loads(RESULT_SCHEMA.read_text())).validate(context.result.to_dict())


def test_diagnostic_detail_does_not_affect_result_comparison():
    first = registry_document.Outcome("invalid", "example", detail="first wording")
    second = registry_document.Outcome("invalid", "example", detail="different wording")
    assert first == second


def test_mapping_context_isolated_from_later_caller_mutation():
    supplied = copy.deepcopy(CORE)
    context = check_registry_context(supplied)
    supplied["resources"].clear()
    assert context.result.state == "valid"
    assert context.document["resources"]
    assert context.result.phases[0].reason == "registry.phase.mapping_input"


def test_extension_context_retains_the_exact_checked_core_context():
    core = check_registry_context(CORE)
    extension = check_registry_context(_document(), core=core)
    assert extension.result.state == "valid"
    assert extension.core is core


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(extra=True),
        lambda value: value["phases"].reverse(),
        lambda value: value["phases"][0].pop("reason"),
        lambda value: value["phases"][1]["outcomes"][0].update(instance="not-a-pointer"),
    ],
)
def test_result_schema_rejects_inconsistent_serializations(mutate):
    document = check_registry({}).to_dict()
    mutate(document)
    assert list(Draft202012Validator(json.loads(RESULT_SCHEMA.read_text())).iter_errors(document))


def test_descriptor_and_semantic_implementation_have_no_hidden_checks():
    descriptor = json.loads(CONTRACT.read_text())
    described = {entry["id"] for entry in descriptor["invariants"] if entry["phase"] == "semantic"}
    assert {invariant.id for invariant in registry_invariants.INVARIANTS} == described
    assert len(registry_invariants.INVARIANTS) == len(described)


def test_byte_entry_rejects_a_nested_duplicate_at_its_containing_object():
    result = check_registry_bytes(
        b'{"$schema":"https://escapewheel.org/schemas/registry/0.12.0","resources":{"demo.rows":{"table":{"rules":[],"rules":[]}}}}'
    )
    outcome = result.findings[0]
    assert result.state == "invalid"
    assert outcome.id == "registry.json.duplicate_member"
    assert outcome.instance == "/resources/demo.rows/table"
    assert all(phase.state == "skipped" for phase in result.phases[1:])


@pytest.mark.parametrize("data", [b"[]", b"null", b"42", b'"registry"'])
def test_byte_entry_reports_a_non_object_json_root(data):
    result = check_registry_bytes(data)
    assert result.state == "invalid"
    assert result.phases[0].state == "passed"
    assert result.phases[1].state == "invalid"
    assert _ids(result) == {"registry.schema.selector_missing"}
    assert all(phase.state == "skipped" for phase in result.phases[2:])


def test_schema_selection_distinguishes_invalid_and_unsupported():
    missing = check_registry({})
    assert missing.state == "invalid"
    assert "registry.schema.selector_missing" in _ids(missing)

    unknown = check_registry({"$schema": "https://example.org/unknown"})
    assert unknown.state == "unsupported"
    assert "registry.schema.selector_unsupported" in _ids(unknown)

    wrong_type = check_registry({"$schema": 4})
    assert wrong_type.state == "invalid"
    assert "registry.schema.selector_type" in _ids(wrong_type)


@pytest.mark.parametrize("version", ["0.6.0", "0.11.0"])
def test_a_registry_naming_the_superseded_meta_schema_is_unsupported(version):
    document = _document()
    document["$schema"] = f"https://escapewheel.org/schemas/registry/{version}"
    result = check_registry(document, CORE)
    assert result.state == "unsupported"
    assert "registry.schema.selector_unsupported" in _ids(result)


def test_shape_failure_uses_schema_identity_and_location():
    document = _document()
    _table(document)["columns"][1]["type"] = "uint8"
    result = check_registry(document, CORE)
    outcome = result.findings[0]
    assert result.state == "invalid"
    assert outcome.id == "https://escapewheel.org/schemas/registry/0.12.0"
    assert outcome.instance == "/resources/demo.rows/table/columns/1/type"
    assert outcome.schema_location


@pytest.mark.parametrize(
    "case",
    [
        "identifier_identity",
        "missing_role",
        "coordinate_type",
        "discriminator_shape",
        "string_vocabulary",
        "nonstring_vocabulary",
        "closed_enum",
        "reserved_open",
        "open_description",
        "unit_exclusive",
        "clock_role",
        "json_presence",
        "metadata_shape",
        "identifier_name",
        "id_declaration",
        "coordinate_name",
        "tick_declaration",
        "index_declaration",
        "name_type",
        "uri_type",
        "float_finite",
        "string_finite",
    ],
)
def test_meta_schema_owns_each_local_conditional(case):  # noqa: C901
    document = _document()
    table = _table(document)
    if case == "identifier_identity":
        table["columns"][1].pop("identity")
    elif case == "missing_role":
        table["columns"][1].pop("role")
    elif case == "coordinate_type":
        table["columns"].append(_column("time_tick", type="float64", role="coordinate"))
    elif case == "discriminator_shape":
        table["columns"].append(
            _column("row_kind", type="string", presence="optional", role="discriminator", vocabulary="free")
        )
    elif case == "string_vocabulary":
        table["columns"].append(_column("label", type="string", role="data"))
    elif case == "nonstring_vocabulary":
        table["columns"].append(_column("value", type="float64", role="data", vocabulary="free"))
    elif case == "closed_enum":
        table["columns"].append(_column("label", type="string", role="data", vocabulary="closed"))
    elif case == "reserved_open":
        table["columns"].append(
            _column("label", type="string", role="data", vocabulary="free", reserved_values=["unknown"])
        )
    elif case == "open_description":
        table["columns"].append(
            {"name": "label", "type": "string", "presence": "nullable", "role": "data", "vocabulary": "open"}
        )
    elif case == "unit_exclusive":
        table["columns"].append(_column("value", type="float64", role="data", unit="s", unit_from="unit_name"))
    elif case == "clock_role":
        table["columns"].append(_column("value", type="float64", role="data", clock_from="clock_id"))
    elif case == "json_presence":
        table["columns"].append(_column("payload", type="json_string", presence="required", role="data"))
    elif case == "metadata_shape":
        table["columns"][2]["presence"] = "nullable"
    elif case == "identifier_name":
        table["columns"].append(_column("number"))
    elif case == "id_declaration":
        table["columns"].append(_column("bad_id", type="string", role="data", vocabulary="free"))
    elif case == "coordinate_name":
        table["columns"].append(_column("time", type="int64", role="coordinate"))
    elif case == "tick_declaration":
        table["columns"].append(_column("time_tick", type="int64", role="data"))
    elif case == "index_declaration":
        table["columns"].append(_column("sample_index", type="int64", role="data"))
    elif case == "name_type":
        table["columns"].append(_column("row_name", type="int32", role="data"))
    elif case == "uri_type":
        table["columns"].append(_column("source_uri", type="int32", role="data"))
    elif case == "float_finite":
        column = _column("value", type="float64", presence="nullable", role="data")
        column.pop("finite")
        table["columns"].append(column)
    elif case == "string_finite":
        table["columns"].append(_column("label", type="string", role="data", vocabulary="free", finite=True))
    result = check_registry(document, CORE)
    shape = next(phase for phase in result.phases if phase.phase == "shape")
    assert shape.state == "invalid"
    assert {outcome.id for outcome in shape.outcomes} == {"https://escapewheel.org/schemas/registry/0.12.0"}


def test_unknown_contract_tuple_is_unsupported():
    document = _document()
    document["logical_standard_version"] = "escapewheel-logical-v9"
    result = check_registry(document, CORE)
    assert result.state == "unsupported"
    assert "registry.contract.selector_unsupported" in _ids(result)


def test_null_primary_key_is_a_valid_duplicate_row_declaration():
    document = _document()
    document["resources"]["demo.rows"]["table"] = {
        "columns": [_column("value", type="float64", presence="nullable", role="data")],
        "primary_key": None,
        "amendment_groups": [],
        "references": [],
        "rules": [],
    }
    assert check_registry(document, CORE).state == "valid"


def test_two_local_contracts_for_one_tuple_are_ambiguous():
    first = json.loads(CONTRACT.read_text())
    second = copy.deepcopy(first)
    second["id"] = "escapewheel-registry-contract-v0.9"
    result = check_registry(CORE, descriptors=[first, second])
    assert result.state == "unsupported"
    assert "registry.contract.selector_ambiguous" in _ids(result)


def test_extension_without_core_runs_local_checks_and_is_incomplete():
    result = check_registry(_document())
    assert result.state == "incomplete"
    assert result.descriptor_id == "escapewheel-registry-contract-v0.10"
    assert "registry.contract.core_context_unusable" in _ids(result)

    broken = _document()
    broken["resources"]["other.rows"] = copy.deepcopy(broken["resources"].pop("demo.rows"))
    result = check_registry(broken)
    assert result.state == "invalid"
    assert "registry.namespace.owned" in _ids(result)


@pytest.mark.parametrize(
    ("invariant", "mutate"),
    [
        (
            "registry.resource.classification",
            lambda document: document["resources"]["demo.rows"].update(content_class="core"),
        ),
        (
            "registry.resource.instance",
            lambda document: document["resources"]["demo.rows"].update(content_class="analysis"),
        ),
        (
            "registry.resource.catalog",
            lambda document: document["resources"].update(
                {
                    "demo.items": {
                        "content_class": "extension",
                        "kind": "opaque",
                        "instances": {
                            "mode": "catalog",
                            "catalog_resource": "demo.rows",
                            "resource_id_column": "demo_id",
                        },
                        "requires": [],
                        "lineage": "optional",
                    }
                }
            ),
        ),
        (
            "registry.resource.array_axes",
            lambda document: document["resources"].update(
                {
                    "demo.arrays": {
                        "content_class": "extension",
                        "kind": "dense_array",
                        "instances": {
                            "mode": "catalog",
                            "catalog_resource": "core.array_assets",
                            "resource_id_column": "resource_id",
                        },
                        "requires": [],
                        "lineage": "optional",
                        "array": {"axes_resource": "core.sessions"},
                    }
                }
            ),
        ),
        (
            "registry.resource.dependency",
            lambda document: document["resources"]["demo.rows"].update(requires=["demo.missing"]),
        ),
    ],
)
def test_resource_invariants_reject_ineligible_declarations(invariant, mutate):
    document = _document()
    mutate(document)
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    assert invariant in _ids(result)


def _canonical_target_pointers(result):
    return {outcome.instance for outcome in result.findings if outcome.id == "registry.resource.canonical_targets"}


REFERENCE_SITE = "/resources/core.array_channels/table/references/0/resource"
REQUIRES_SITE = "/resources/core.sessions/requires/0"


@pytest.mark.parametrize(
    ("target", "content_class", "site"),
    [
        ("analysis.array_assets", None, REFERENCE_SITE),
        ("analysis.array_assets", None, REQUIRES_SITE),
        ("core.legacy_rows", "compatibility_projection", REFERENCE_SITE),
        ("core.notes", "documentation", REQUIRES_SITE),
        ("core.sidecars", None, REFERENCE_SITE),
        ("core.sidecars", None, REQUIRES_SITE),
    ],
    ids=[
        "reference_to_analysis",
        "requires_analysis",
        "reference_to_projection",
        "requires_documentation",
        "reference_to_sidecars",
        "requires_sidecars",
    ],
)
def test_a_core_declaration_depends_only_on_canonical_ones(target, content_class, site):
    document = copy.deepcopy(CORE)
    if content_class is not None:
        declaration = copy.deepcopy(document["resources"]["analysis.array_assets"])
        declaration["content_class"] = content_class
        document["resources"][target] = declaration
    if site == REQUIRES_SITE:
        document["resources"]["core.sessions"]["requires"] = [target]
    else:
        document["resources"]["core.array_channels"]["table"]["references"][0]["resource"] = target
    result = check_registry(document)
    assert result.state == "invalid"
    assert site in _canonical_target_pointers(result)


def _with_extension_analysis(document):
    derived = copy.deepcopy(document["resources"]["demo.rows"])
    derived.update(content_class="analysis", lineage="required")
    derived["table"]["columns"].pop()
    derived["table"]["amendment_groups"] = []
    document["resources"]["demo.derived"] = derived
    return document


def test_an_extension_declaration_depends_only_on_canonical_ones():
    document = _with_extension_analysis(_document())
    _table(document)["references"].append(
        {
            "columns": ["session_id", "demo_id"],
            "resource": "demo.derived",
            "resource_columns": ["session_id", "demo_id"],
        }
    )
    document["resources"]["demo.items"] = {
        "content_class": "extension",
        "kind": "opaque",
        "instances": {
            "mode": "catalog",
            "catalog_resource": "demo.derived",
            "resource_id_column": "demo_id",
        },
        "requires": [],
        "lineage": "optional",
    }
    for core in (CORE, None):
        result = check_registry(document, core)
        assert result.state == "invalid"
        assert _canonical_target_pointers(result) >= {
            "/resources/demo.rows/table/references/1/resource",
            "/resources/demo.items/instances/catalog_resource",
        }


def _without_metadata(declaration):
    declaration["table"]["columns"] = [c for c in declaration["table"]["columns"] if c["name"] != "metadata"]


def _grouped(declaration):
    declaration["table"]["amendment_groups"] = [declaration["table"]["primary_key"]]


@pytest.mark.parametrize(
    ("resource", "mutate", "invariant"),
    [
        ("core.sidecars", _without_metadata, "registry.metadata.eligibility"),
        ("core.sidecars", _grouped, "registry.amendment_groups.resolves"),
        ("core.sidecar_scopes", _grouped, "registry.amendment_groups.resolves"),
        ("core.sidecars", lambda declaration: declaration.update(lineage="optional"), "registry.resource.instance"),
    ],
    ids=["sidecars_without_metadata", "sidecars_grouped", "scopes_grouped", "sidecars_with_lineage"],
)
def test_the_sidecar_tables_are_held_to_the_documentation_rules(resource, mutate, invariant):
    document = copy.deepcopy(CORE)
    mutate(document["resources"][resource])
    result = check_registry(document)
    assert result.state == "invalid"
    assert invariant in _ids(result)


def test_the_sidecar_scopes_may_declare_metadata_or_not():
    document = copy.deepcopy(CORE)
    assert check_registry(document).state == "valid"
    document["resources"]["core.sidecar_scopes"]["table"]["columns"].append(
        _column("metadata", type="json_string", presence="optional", role="data", description=METADATA_DESCRIPTION)
    )
    assert check_registry(document).state == "valid"


def test_a_core_non_canonical_target_needs_the_core_context():
    document = _document()
    _table(document)["references"][0]["resource"] = "analysis.array_assets"
    assert check_registry(document).state == "incomplete"
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    assert "/resources/demo.rows/table/references/0/resource" in _canonical_target_pointers(result)


def test_a_non_canonical_declaration_may_depend_on_a_canonical_one():
    document = _with_extension_analysis(_document())
    document["resources"]["demo.derived"]["table"]["references"].append(
        {
            "columns": ["session_id", "demo_id"],
            "resource": "demo.rows",
            "resource_columns": ["session_id", "demo_id"],
        }
    )
    result = check_registry(document, CORE)
    assert result.state == "valid"


def test_an_extension_registry_id_names_its_extension():
    document = _document()
    document["registry_id"] = "other"
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    outcome = next(outcome for outcome in result.findings if outcome.id == "registry.identity.registry_id")
    assert outcome.instance == "/registry_id"


def test_core_registry_id_is_fixed_by_the_meta_schema():
    document = copy.deepcopy(CORE)
    document["registry_id"] = "base"
    result = check_registry(document)
    assert result.state == "invalid"
    assert next(phase for phase in result.phases if phase.phase == "shape").state == "invalid"


def test_a_declaration_naming_a_producing_run_policy_is_rejected():
    """Part 02 §2.7 has only a lineage policy; the meta-schema is closed."""
    document = _document()
    document["resources"]["demo.rows"]["producing_run"] = "optional"
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    assert next(phase for phase in result.phases if phase.phase == "shape").state == "invalid"


def test_cross_declaration_invariants_have_stable_ids_and_pointers():
    document = _document()
    _table(document)["columns"].append(copy.deepcopy(_table(document)["columns"][1]))
    result = check_registry(document, CORE)
    duplicate = next(outcome for outcome in result.findings if outcome.id == "registry.column.name_unique")
    assert duplicate.instance == "/resources/demo.rows/table/columns/3/name"
    assert duplicate.owner == "demo.rows"


def test_reference_must_target_the_complete_ordered_key():
    document = _document()
    reference = _table(document)["references"][0]
    reference["resource"] = "core.intervals"
    result = check_registry(document, CORE)
    assert "registry.reference.target_key" in _ids(result)


def test_session_scope_requires_a_session_preserving_path():
    document = _document()
    _table(document)["references"] = []
    result = check_registry(document, CORE)
    assert "registry.session_scope.path" in _ids(result)


def test_metadata_uses_the_exact_standard_declaration():
    document = _document()
    _table(document)["columns"][2]["description"] = "Other metadata."
    result = check_registry(document, CORE)
    assert "registry.metadata.eligibility" in _ids(result)


def test_rule_static_validation_rejects_an_optional_input():
    document = _document()
    table = _table(document)
    table["columns"].append(
        _column("optional_value", type="string", presence="optional", role="data", vocabulary="free")
    )
    table["rules"].append(
        {
            "id": "demo.rows.optional_value_present",
            "level": "warning",
            "message": "An optional value was present.",
            "sql": "SELECT optional_value FROM demo.rows WHERE optional_value IS NOT NULL",
        }
    )
    result = check_registry(document, CORE)
    assert "registry.rule.required_inputs" in _ids(result)


def test_invalid_rule_language_outcome_is_attached_to_the_rule():
    document = _document()
    _table(document)["rules"] = [{**_rule(), "sql": "DELETE FROM demo.rows"}]
    result = check_registry(document, CORE)
    outcome = next(outcome for outcome in result.findings if outcome.id == "escapewheel-rule-sql-v0.2")
    assert outcome.owner == "demo.rows.negative_demo_id"


def test_unavailable_selected_rule_language_is_unsupported_and_attached():
    descriptor = json.loads(CONTRACT.read_text())
    descriptor["id"] = "demo-registry-contract-v0.1"
    descriptor["rule_languages"] = ["demo-rule-v0.1"]
    core = copy.deepcopy(CORE)
    core["rule_language"] = "demo-rule-v0.1"
    result = check_registry(core, descriptors=[descriptor])
    rule_phase = next(phase for phase in result.phases if phase.phase == "rule_static")
    assert result.state == "unsupported"
    assert rule_phase.state == "unsupported"
    assert all(outcome.owner for outcome in rule_phase.outcomes)


def test_the_superseded_rule_language_selects_no_contract():
    core = copy.deepcopy(CORE)
    core["rule_language"] = "escapewheel-rule-sql-v0.1"
    result = check_registry(core)
    assert result.state == "unsupported"
    assert "registry.contract.selector_unsupported" in _ids(result)


def test_external_domain_uses_exact_ucum_syntax():
    document = _document()
    _table(document)["columns"].append(
        _column("value", type="float64", presence="nullable", role="data", unit="not a unit")
    )
    result = check_registry(document, CORE)
    assert "registry.unit.ucum_2_2_cs" in _ids(result)
    assert next(phase for phase in result.phases if phase.phase == "external_domain").state == "invalid"


def test_missing_exact_ucum_domain_is_unsupported(monkeypatch):
    monkeypatch.setattr(registry_phases, "_ucum_parser", lambda: None)
    result = check_registry(_document(), CORE)
    assert result.state == "unsupported"
    assert next(phase for phase in result.phases if phase.phase == "external_domain").state == "unsupported"


def test_invalid_outcome_dominates_an_independent_unsupported_phase(monkeypatch):
    monkeypatch.setattr(registry_phases, "_ucum_parser", lambda: None)
    document = _document()
    _table(document)["columns"].append(copy.deepcopy(_table(document)["columns"][1]))
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    assert next(phase for phase in result.phases if phase.phase == "external_domain").state == "unsupported"


def test_reference_direction_is_independent_of_target_resolution():
    document = _document()
    _table(document)["references"][0]["resource"] = "other.rows"
    result = check_registry(document, CORE)
    assert "registry.namespace.reference_direction" in _ids(result)


def test_primary_key_members_must_resolve_to_required_columns():
    document = _document()
    _table(document)["primary_key"] = ["missing_id"]
    assert "registry.primary_key.resolves" in _ids(check_registry(document, CORE))


def test_reference_members_must_resolve():
    document = _document()
    _table(document)["references"][0]["columns"] = ["missing_id"]
    assert "registry.reference.resolves" in _ids(check_registry(document, CORE))


def test_reference_pairs_must_be_compatible():
    document = _document()
    _table(document)["columns"][0]["type"] = "int64"
    assert "registry.reference.compatible" in _ids(check_registry(document, CORE))


def test_owned_assigned_identifier_requires_its_name():
    document = _document()
    _table(document)["columns"][1]["identity"] = "assigned"
    assert "registry.identity.name" in _ids(check_registry(document, CORE))


def _owning_document(presence):
    document = _document()
    table = _table(document)
    table["columns"][1]["identity"] = "assigned"
    table["columns"].insert(2, _column("demo_name", type="string", presence=presence, role="data", vocabulary="free"))
    return document


def test_an_owned_assigned_identifiers_required_name_is_valid():
    assert check_registry(_owning_document("required"), CORE).state == "valid"


@pytest.mark.parametrize("presence", ["nullable", "optional"])
def test_an_owned_assigned_identifiers_name_must_be_required(presence):
    """Part 02 §8.2: `registry.identity.name` reads the name's presence, in either class."""
    assert "registry.identity.name" in _ids(check_registry(_owning_document(presence), CORE))
    core = copy.deepcopy(CORE)
    unit_name = next(c for c in core["resources"]["core.units"]["table"]["columns"] if c["name"] == "unit_name")
    unit_name["presence"] = presence
    result = check_registry(core)
    assert result.state == "invalid"
    assert "registry.identity.name" in _ids(result)


def test_core_declares_every_owned_identifiers_name_required():
    for resource, declaration in CORE["resources"].items():
        table = declaration.get("table") or {}
        for column in table.get("columns", []):
            if column["name"].endswith("_name") and any(
                c["name"] == f"{column['name'][:-5]}_id" and c.get("identity") == "assigned"
                for c in table["columns"]
            ):
                assert column["presence"] == "required", (resource, column["name"])


@pytest.mark.parametrize(
    ("resource", "name", "description", "references"),
    [
        (
            "core.devices",
            "parent_device_id",
            "The device this one was attached to -- a probe's headstage, a headstage's connect board.",
            "core.devices",
        ),
        ("core.sessions", "source_session_id", "Source-system session ID.", None),
        ("core.processing_runs", "supersedes_run_id", "The run this one replaces.", "core.processing_runs"),
    ],
)
def test_a_naming_columns_description_gives_a_null_no_reading_of_its_own(resource, name, description, references):
    """Part 02 §6.2 owns what a null in a naming column says, so these descriptions say nothing of one."""
    table = CORE["resources"][resource]["table"]
    (column,) = [c for c in table["columns"] if c["name"] == name]
    assert column == {
        "name": name,
        "type": "int32",
        "presence": "nullable",
        "role": "identifier",
        "identity": "assigned",
        "description": description,
    }
    named = [r["resource"] for r in table["references"] if r["columns"] == [name]]
    assert named == ([references] if references else [])


def test_determinants_resolve_locally():
    document = _document()
    _table(document)["columns"][2]["determined_by"] = ["missing_id"]
    assert "registry.determined_by.resolves" in _ids(check_registry(document, CORE))


def test_discriminator_companion_has_matching_declaration():
    document = _document()
    table = _table(document)
    table["columns"].extend(
        [
            _column(
                "row_kind",
                type="string",
                role="discriminator",
                resolves="required",
                discriminates="row_name",
            ),
            _column("row_name", type="string", presence="nullable", role="data", vocabulary="free"),
        ]
    )
    assert "registry.discriminator.declaration" in _ids(check_registry(document, CORE))


def test_discriminator_reverse_path_must_resolve_once():
    document = _document()
    _table(document)["columns"].append(
        _column(
            "row_kind",
            type="string",
            role="discriminator",
            resolves="required",
            discriminates_via="demo.missing.demo_id",
        )
    )
    assert "registry.discriminator.path" in _ids(check_registry(document, CORE))


def test_a_by_position_discriminator_is_not_a_shape():
    """Part 02 §8.3 has two shapes, and the meta-schema does not admit `positions_in`."""
    document = _document()
    _table(document)["columns"].extend(
        [
            _column("row_kind", type="string", role="discriminator", resolves="required", positions_in="row_column"),
            _column("row_column", type="string", role="data", vocabulary="free"),
        ]
    )
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    assert json.loads(SCHEMA.read_text())["$id"] in _ids(result)


def test_a_paired_value_is_a_string_or_an_identifier():
    """A float column can hold neither a key's name nor its value (Part 02 §8.3)."""
    document = _document()
    _table(document)["columns"].extend(
        [
            _column("row_kind", type="string", role="discriminator", resolves="required", discriminates="row_value"),
            _column("row_value", type="float64", role="data"),
        ]
    )
    assert "registry.discriminator.declaration" in _ids(check_registry(document, CORE))


def test_an_identifier_paired_value_may_sit_on_the_specialised_table():
    """With `discriminates_via`, the value is on the table the path names, and null names no row."""
    document = _document()
    _table(document)["columns"].append(
        _column(
            "row_kind",
            type="string",
            role="discriminator",
            resolves="required",
            discriminates_via="demo.details.demo_id",
            discriminates="label_id",
        )
    )
    document["resources"]["demo.details"] = copy.deepcopy(document["resources"]["demo.rows"])
    details = _table(document, "demo.details")
    details["columns"] = [
        _column("session_id"),
        _column("demo_id", identity="carried"),
        _column("label_id", presence="nullable"),
    ]
    details["references"] = [
        {"columns": ["session_id", "demo_id"], "resource": "demo.rows", "resource_columns": ["session_id", "demo_id"]}
    ]
    details["rules"] = []
    ids = _ids(check_registry(document, CORE))
    assert not {i for i in ids if i.startswith("registry.discriminator.")}, ids


def test_coordinate_context_source_must_resolve():
    document = _document()
    _table(document)["columns"].append(
        _column("time_tick", type="int64", presence="nullable", role="coordinate", clock_from="missing_id")
    )
    assert "registry.context_source.resolves" in _ids(check_registry(document, CORE))


def test_ucum_authority_name_and_identity_are_paired():
    document = _document()
    _table(document)["columns"].append(
        _column(
            "unit_name",
            type="string",
            presence="nullable",
            role="data",
            vocabulary="open",
            authority=[{"name": "UCUM", "uri": "https://example.org/units"}],
        )
    )
    assert "registry.authority.uri" in _ids(check_registry(document, CORE))


def _rule(rule_id="demo.rows.negative_demo_id"):
    return {
        "id": rule_id,
        "level": "error",
        "message": "A demonstration ID is negative.",
        "sql": "SELECT demo_id FROM demo.rows WHERE demo_id < 0",
    }


def test_rule_ids_are_document_unique():
    document = _document()
    _table(document)["rules"] = [_rule(), _rule()]
    assert "registry.rule.id_unique" in _ids(check_registry(document, CORE))


def test_rule_id_has_exact_resource_owner():
    document = _document()
    _table(document)["rules"] = [_rule("demo.other.negative_demo_id")]
    assert "registry.rule.id_owner" in _ids(check_registry(document, CORE))


def test_core_device_detail_shape_is_reserved_for_extensions():
    core = copy.deepcopy(CORE)
    core["resources"]["core.device_detail"] = {
        "content_class": "core",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": [
                _column("device_id"),
                _column("device_name", type="string", role="data", vocabulary="free"),
                _column(
                    "metadata",
                    type="json_string",
                    presence="optional",
                    role="data",
                    description=METADATA_DESCRIPTION,
                ),
            ],
            "primary_key": ["device_id"],
            "amendment_groups": [["device_id"]],
            "references": [],
            "rules": [],
        },
    }
    assert "registry.core.device_detail" in _ids(check_registry(core))


def _group_pointers(result):
    return {outcome.instance for outcome in result.findings if outcome.id == "registry.amendment_groups.resolves"}


@pytest.mark.parametrize(
    ("groups", "site"),
    [
        ([["session_id", "absent_id"]], "/resources/demo.rows/table/amendment_groups/0/1"),
        ([["metadata"]], "/resources/demo.rows/table/amendment_groups/0/0"),
        ([["session_id", "demo_id"], ["demo_id", "session_id"]], "/resources/demo.rows/table/amendment_groups/1"),
    ],
    ids=["absent_column", "optional_column", "one_set_twice"],
)
def test_a_group_list_names_present_columns_once(groups, site):
    """Part 02 §2.8: a member names one required column, and no two lists of a table name one set."""
    document = _document()
    _table(document)["amendment_groups"] = groups
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    assert _group_pointers(result) == {site}


def test_an_analysis_table_declares_no_group_list():
    document = _with_extension_analysis(_document())
    _table(document, "demo.derived")["amendment_groups"] = [["session_id"]]
    result = check_registry(document, CORE)
    assert result.state == "invalid"
    assert _group_pointers(result) == {"/resources/demo.derived/table/amendment_groups"}


def test_a_table_without_group_lists_fails_its_shape():
    document = _document()
    del _table(document)["amendment_groups"]
    result = check_registry(document, CORE)
    shape = next(phase for phase in result.phases if phase.phase == "shape")
    assert shape.state == "invalid"


def _with_detail(document, reference=None, key=None):
    """Declare `demo.tones`, a detail table of `core.intervals.interval_kind` unless told otherwise."""
    detail = copy.deepcopy(document["resources"]["demo.rows"])
    table = detail["table"]
    table["columns"] = [_column("session_id"), _column("tone_id")]
    table["primary_key"] = key or ["tone_id"]
    table["amendment_groups"] = [["tone_id"]]
    table["references"] = [
        {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]},
        {
            "columns": ["tone_id"],
            "resource": "core.intervals",
            "resource_columns": ["interval_id"],
            "specialises": "core.intervals.interval_kind",
            **(reference or {}),
        },
    ]
    document["resources"]["demo.tones"] = detail
    return document


def _specialisation_pointers(result):
    return {outcome.instance for outcome in result.findings if outcome.id == "registry.discriminator.specialisation"}


def test_a_detail_table_of_an_interval_is_valid():
    assert check_registry(_with_detail(_document()), CORE).state == "valid"


@pytest.mark.parametrize(
    ("reference", "key"),
    [
        ({"specialises": "core.intervals.no_such_column"}, None),
        ({"specialises": "core.intervals.clock_id"}, None),
        ({"specialises": "core.processing_runs.scope_kind"}, None),
        ({"specialises": "core.devices.device_kind"}, None),
        ({}, ["session_id", "tone_id"]),
    ],
    ids=["absent_column", "not_a_discriminator", "paired_value", "another_target", "key_elsewhere"],
)
def test_a_specialising_reference_names_a_shared_key_discriminator_of_its_target(reference, key):
    """Part 02 §8.3: the discriminator is shared-key, specialises the target, and leads the detail key."""
    result = check_registry(_with_detail(_document(), reference, key), CORE)
    assert result.state == "invalid"
    assert _specialisation_pointers(result) == {"/resources/demo.tones/table/references/1/specialises"}


def test_a_specialisation_through_discriminates_via_targets_the_specialised_table():
    """`core.event_streams.detail_kind` specialises events, so a reference to the stream is refused."""
    document = _document()
    table = _table(document)
    table["columns"] = [_column("session_id"), _column("stream_id")]
    table["primary_key"] = ["session_id", "stream_id"]
    table["amendment_groups"] = [["session_id", "stream_id"]]
    table["references"] = [
        {
            "columns": ["session_id", "stream_id"],
            "resource": "core.event_streams",
            "resource_columns": ["session_id", "stream_id"],
            "specialises": "core.event_streams.detail_kind",
        }
    ]
    result = check_registry(document, CORE)
    assert _specialisation_pointers(result) == {"/resources/demo.rows/table/references/0/specialises"}


def test_a_table_specialises_through_one_reference():
    """The later of two declarations is reported, though each alone would be valid."""
    document = _with_detail(_document())
    table = _table(document, "demo.tones")
    table["columns"].append(_column("cue_id"))
    table["references"].append({**table["references"][1], "columns": ["cue_id"]})
    result = check_registry(document, CORE)
    assert _specialisation_pointers(result) == {"/resources/demo.tones/table/references/2/specialises"}


def test_a_specialises_value_that_is_not_a_column_path_fails_its_shape():
    result = check_registry(_with_detail(_document(), {"specialises": "core.intervals"}), CORE)
    shape = next(phase for phase in result.phases if phase.phase == "shape")
    assert shape.state == "invalid"

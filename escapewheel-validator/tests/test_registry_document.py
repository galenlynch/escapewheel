"""The complete Part 02 §9.4 registry-document conformance contract."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from escapewheel_validator import RegistryRejected, generate, registry_document
from escapewheel_validator.registry_document import (
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

ROOT = Path(__file__).resolve().parents[2]
CORE = json.loads((ROOT / "registry/logical_schemas.json").read_text())
EXTENSIONS = sorted((ROOT / "registry/extensions").glob("*.json"))


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
    return column


def _document():
    return {
        "$schema": json.loads(SCHEMA.read_text())["$id"],
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.1",
        "extension_id": "demo",
        "resources": {
            "demo.rows": {
                "content_class": "extension",
                "kind": "table",
                "instances": {"mode": "singleton", "presence": "optional"},
                "requires": [],
                "lineage": "optional",
                "producing_run": "optional",
                "table": {
                    "primary_key": ["session_id", "demo_id"],
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
    assert result.descriptor_id == "escapewheel-registry-contract-v0.2"
    assert tuple(phase.phase for phase in result.phases) == PHASES
    assert result.phases[0].state == "skipped"
    assert result.phases[0].reason == "registry.phase.mapping_input"
    assert result.findings == ()


def test_portable_result_validates_against_the_incorporated_schema():
    context = check_registry_context_bytes((ROOT / "registry/logical_schemas.json").read_bytes())
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
    extension = check_registry_context(json.loads(EXTENSIONS[0].read_text()), core=core)
    assert extension.result.state == "valid"
    assert extension.core is core


def test_generator_rejects_a_nonvalid_checked_context():
    context = check_registry_context({"$schema": "https://example.org/unknown"})
    with pytest.raises(RegistryRejected) as caught:
        generate(context)
    assert caught.value.result is context.result


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
    assert set(registry_document._semantic_checks()) == described


@pytest.mark.parametrize("path", EXTENSIONS, ids=lambda path: path.stem)
def test_every_repository_extension_satisfies_the_same_contract(path):
    result = check_registry(json.loads(path.read_text()), CORE)
    assert result.state == "valid", [outcome for phase in result.phases for outcome in phase.outcomes]


def test_byte_entry_rejects_a_nested_duplicate_at_its_containing_object():
    result = check_registry_bytes(
        b'{"$schema":"https://escapewheel.org/schemas/registry/0.5.0","resources":{"demo.rows":{"table":{"rules":[],"rules":[]}}}}'
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


def test_shape_failure_uses_schema_identity_and_location():
    document = _document()
    _table(document)["columns"][1]["type"] = "uint8"
    result = check_registry(document, CORE)
    outcome = result.findings[0]
    assert result.state == "invalid"
    assert outcome.id == "https://escapewheel.org/schemas/registry/0.5.0"
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
    result = check_registry(document, CORE)
    shape = next(phase for phase in result.phases if phase.phase == "shape")
    assert shape.state == "invalid"
    assert {outcome.id for outcome in shape.outcomes} == {"https://escapewheel.org/schemas/registry/0.5.0"}


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
        "references": [],
        "rules": [],
    }
    assert check_registry(document, CORE).state == "valid"


def test_two_local_contracts_for_one_tuple_are_ambiguous():
    first = json.loads(CONTRACT.read_text())
    second = copy.deepcopy(first)
    second["id"] = "escapewheel-registry-contract-v0.2"
    result = check_registry(CORE, descriptors=[first, second])
    assert result.state == "unsupported"
    assert "registry.contract.selector_ambiguous" in _ids(result)


def test_extension_without_core_runs_local_checks_and_is_incomplete():
    result = check_registry(_document())
    assert result.state == "incomplete"
    assert result.descriptor_id == "escapewheel-registry-contract-v0.2"
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
                        "producing_run": "optional",
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
                        "producing_run": "optional",
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
    outcome = next(outcome for outcome in result.findings if outcome.id == "escapewheel-rule-sql-v0.1")
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


def test_external_domain_uses_exact_ucum_syntax():
    document = _document()
    _table(document)["columns"].append(
        _column("value", type="float64", presence="nullable", role="data", unit="not a unit")
    )
    result = check_registry(document, CORE)
    assert "registry.unit.ucum_2_2_cs" in _ids(result)
    assert next(phase for phase in result.phases if phase.phase == "external_domain").state == "invalid"


def test_missing_exact_ucum_domain_is_unsupported(monkeypatch):
    monkeypatch.setattr(registry_document, "_ucum_parser", lambda: None)
    result = check_registry(_document(), CORE)
    assert result.state == "unsupported"
    assert next(phase for phase in result.phases if phase.phase == "external_domain").state == "unsupported"


def test_invalid_outcome_dominates_an_independent_unsupported_phase(monkeypatch):
    monkeypatch.setattr(registry_document, "_ucum_parser", lambda: None)
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
        "producing_run": "optional",
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
            "references": [],
            "rules": [],
        },
    }
    assert "registry.core.device_detail" in _ids(check_registry(core))

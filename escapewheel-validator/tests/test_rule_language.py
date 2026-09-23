import copy
import json
from importlib import resources as importlib_resources
from pathlib import Path

import jsonschema
import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import validate
from escapewheel_validator.rule_language import PROFILE_ID, RuleProfileError, check_rule

ROOT = Path(__file__).resolve().parents[2]


def _rule(registry, sql, *, rule_id="core.trials.profile_test"):
    changed = copy.deepcopy(registry)
    changed["resources"]["core.trials"]["table"]["rules"].append(
        {"id": rule_id, "level": "error", "message": "profile test", "sql": sql}
    )
    return changed


def test_maintained_profile_validates_and_vendored_copies_are_exact():
    schema_path = ROOT / "registry/rule_language.schema.json"
    profile_path = ROOT / "registry/rule_languages/escapewheel-rule-sql-v0.1.json"
    schema = json.loads(schema_path.read_text())
    profile = json.loads(profile_path.read_text())
    jsonschema.Draft202012Validator(schema).validate(profile)
    assert profile["id"] == PROFILE_ID
    package = importlib_resources.files("escapewheel_validator").joinpath("schemas")
    assert package.joinpath("rule_language.schema.json").read_text() == schema_path.read_text()
    assert package.joinpath("escapewheel-rule-sql-v0.1.json").read_text() == profile_path.read_text()


def test_every_shipped_rule_passes_static_profile_check():
    core = json.loads((ROOT / "registry/logical_schemas.json").read_text())
    documents = [
        core,
        *[json.loads(path.read_text()) for path in sorted((ROOT / "registry/extensions").glob("*.json"))],
    ]
    checked = [
        check_rule(rule["sql"], document, core_resources=core)
        for document in documents
        for declaration in document["resources"].values()
        if declaration["kind"] == "table"
        for table in [declaration["table"]]
        for rule in table["rules"]
    ]
    assert len(checked) == 121


def test_invalid_rule_is_not_executed_or_reported_as_a_packet_finding(packet_root):
    packet = open_packet(packet_root)
    registry = _rule(packet.registry, "DELETE FROM core.trials")
    report = validate(packet, registry=registry)
    assert not report.passed
    supplied = next(item for item in report.registries if item.subject == "core:supplied")
    assert supplied.result.state == "invalid"
    assert not any(f.check == "core.trials.profile_test" for f in report.findings)


def test_unsupported_language_is_distinct_from_a_finding(packet_root):
    packet = open_packet(packet_root)
    registry = copy.deepcopy(packet.registry)
    registry["rule_language"] = "another-rule-language-v1.0"
    report = validate(packet, registry=registry)
    assert not report.passed
    supplied = next(item for item in report.registries if item.subject == "core:supplied")
    assert supplied.result.state == "unsupported"
    assert not any(f.check == "rule_language.unsupported" for f in report.findings)


def test_engine_failure_is_incomplete_not_a_packet_finding(packet_root):
    packet = open_packet(packet_root)
    sql = (
        "SELECT CAST(start_tick AS DECIMAL(38,0)) * 99999999999999999999999999999999999999 AS exploded FROM core.trials"
    )
    registry = _rule(packet.registry, sql)
    report = validate(packet, registry=registry)
    assert not report.passed
    assert any(e.status == "incomplete" and e.rule == "core.trials.profile_test" for e in report.evaluations)
    assert not any(f.check == "core.trials.profile_test" for f in report.findings)


def test_cross_extension_relation_is_rejected_before_execution():
    document = {
        "extension_id": "task_a",
        "rule_language": PROFILE_ID,
        "resources": {
            "task_a.rows": {
                "kind": "table",
                "table": {
                    "primary_key": ["row_id"],
                    "columns": [{"name": "row_id", "type": "int64"}],
                    "references": [],
                    "rules": [],
                },
            }
        },
    }
    try:
        check_rule("SELECT row_id FROM task_b.rows", document, core_resources={"core.sessions"})
    except RuleProfileError as exc:
        assert "not visible" in str(exc)
    else:
        raise AssertionError("cross-extension relation was accepted")


def test_undeclared_column_is_rejected_during_static_binding():
    document = {
        "rule_language": PROFILE_ID,
        "resources": {
            "core.rows": {
                "kind": "table",
                "table": {
                    "primary_key": ["row_id"],
                    "columns": [{"name": "row_id", "type": "int64"}],
                    "references": [],
                    "rules": [],
                },
            }
        },
    }
    with pytest.raises(RuleProfileError, match="does not bind"):
        check_rule("SELECT missing FROM core.rows", document)

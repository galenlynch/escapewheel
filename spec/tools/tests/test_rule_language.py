"""The static boundary of the portable Tier 2 language profile (Part 11)."""

import json

import jsonschema
import pytest

from checkers.artifacts import ARTIFACTS
from checkers.rule_language import PROFILE_ID, RuleProfileError, check_rule

CORE = json.loads((ARTIFACTS / "logical_schemas.json").read_text())


def test_the_incorporated_profile_validates_and_is_the_checked_one():
    schema = json.loads((ARTIFACTS / "rule_language.schema.json").read_text())
    profile = json.loads((ARTIFACTS / "rule_languages/escapewheel-rule-sql-v0.2.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(profile)
    assert profile["id"] == PROFILE_ID


def test_every_core_rule_passes_static_profile_check():
    checked = [
        check_rule(rule["sql"], CORE)
        for declaration in CORE["resources"].values()
        if declaration["kind"] == "table"
        for rule in declaration["table"]["rules"]
    ]
    assert len(checked) == 91


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


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("SELECT CHAR_LENGTH(local_unit_label) AS n FROM core.units", "outside the profile"),
        ("SELECT LENGTH(local_unit_label) AS n FROM core.units", "outside the profile"),
        ("SELECT LEN(local_unit_label) AS n FROM core.units", "outside the profile"),
        ("SELECT CHARACTER_LENGTH(local_unit_label USING OCTETS) AS n FROM core.units", ""),
        ("SELECT CHARACTER_LENGTH(unit_id) AS n FROM core.units", "CHARACTER VARYING"),
    ],
    ids=["char-length", "length", "len", "using-octets", "integer-argument"],
)
def test_character_length_is_admitted_in_one_spelling_over_a_string(sql, message):
    check_rule("SELECT CHARACTER_LENGTH(local_unit_label) AS n FROM core.units", CORE)
    with pytest.raises(RuleProfileError, match=message):
        check_rule(sql, CORE)

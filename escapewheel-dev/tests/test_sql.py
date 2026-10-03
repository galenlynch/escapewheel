import re

from sqlglot import exp

import escapewheel_dev as ew


def test_node_counts_agree_with_the_keyword_in_the_text():
    rules = ew.rules()
    counts = ew.node_counts(rules, exp.Between)
    assert counts[exp.Between] == sum(len(re.findall(r"\bBETWEEN\b", rule.sql, re.IGNORECASE)) for rule in rules)


def test_every_shipped_rule_passes_the_static_check():
    for rule in ew.rules():
        assert ew.checked(rule).resources, rule.id


def test_rules_reading_a_column_read_it():
    readers = ew.rules_reading("core.units", "unit_id", ew.rules())
    assert readers
    assert all(("core.units", "unit_id") in ew.checked(rule).inputs for rule in readers)


def test_checks_carry_each_shipped_rule_once_advisory_included():
    core_rules = ew.rules("core")
    shipped = [check for check in ew.checks(advisory=True) if check.tier == 2]
    assert sorted(check.id for check in shipped) == sorted(rule.id for rule in core_rules)
    default = [check for check in ew.checks() if check.tier == 2]
    assert len(default) == sum(1 for rule in core_rules if not rule.advisory)


def test_an_extension_generates_checks_against_core():
    extension = next(registry_id for registry_id in ew.registries() if registry_id != "core")
    assert ew.checks(extension)

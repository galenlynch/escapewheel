import json

import pytest

import escapewheel_dev as ew
from escapewheel_dev.registry import CORE


def test_core_comes_first_and_every_extension_follows():
    ids = list(ew.registries())
    assert ids[0] == "core"
    assert len(ids) > 1
    assert all(ew.registry(registry_id).is_extension for registry_id in ids[1:])


def test_column_filters_agree_with_the_raw_document():
    document = json.loads(CORE.read_text())
    expected = [
        (resource_id, column["name"])
        for resource_id, declaration in document["resources"].items()
        if declaration["kind"] == "table"
        for column in declaration["table"]["columns"]
        if column["presence"] == "nullable" and column.get("role") in ("identifier", "discriminator")
    ]
    found = ew.columns("core", presence="nullable", roles=("identifier", "discriminator"))
    assert [(column.table, column.name) for column in found] == expected


def test_rules_are_every_table_rule_of_every_registry():
    total = sum(
        len(declaration["table"].get("rules", ()))
        for document in ew.registries().values()
        for declaration in document.document["resources"].values()
        if declaration["kind"] == "table"
    )
    assert len(ew.rules()) == total


def test_references_to_a_table_name_it():
    references = ew.references_to("core.sessions")
    assert references
    assert {reference.resource for reference in references} == {"core.sessions"}
    assert any(reference.registry != "core" for reference in references)


def test_table_lookup_crosses_registries():
    assert ew.table("core.units").column("unit_id").presence == "required"
    with pytest.raises(KeyError):
        ew.table("core.units").column("no_such_column")
    with pytest.raises(KeyError):
        ew.table("no.such_table")

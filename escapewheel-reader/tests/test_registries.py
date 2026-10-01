"""The tables a registry document declares."""

import pytest

from escapewheel_reader import open_packet
from escapewheel_reader.registries import declared_tables

UNITS = {"columns": [{"name": "unit_id"}], "primary_key": ["unit_id"]}
DOCUMENT = {
    "resources": {
        "core.units": {"kind": "table", "table": UNITS},
        "core.array_asset_instances": {"kind": "array", "array": {}},
    }
}

#: Each way a document nobody has checked can fail to declare a table.
MALFORMED = [
    {},
    {"resources": {"core.units": {"table": UNITS}}},
    {"resources": {"core.units": {"kind": "table"}}},
]


def test_a_table_resource_is_returned_by_its_id_and_another_kind_is_not():
    assert declared_tables(DOCUMENT) == {"core.units": UNITS}
    assert declared_tables(DOCUMENT, strict=True) == {"core.units": UNITS}


def test_the_declaration_is_the_documents_own():
    """A caller reads the registry through it, so a copy would hide a later binding's changes."""
    assert declared_tables(DOCUMENT)["core.units"] is UNITS


def test_no_document_declares_nothing():
    assert declared_tables(None) == {}


@pytest.mark.parametrize("document", MALFORMED)
def test_an_unchecked_document_declares_only_what_it_states(document):
    assert declared_tables(document) == {}


@pytest.mark.parametrize("document", MALFORMED)
def test_a_strict_reading_refuses_a_malformed_document(document):
    with pytest.raises(KeyError):
        declared_tables(document, strict=True)


def test_a_strict_reading_needs_a_document():
    with pytest.raises(TypeError):
        declared_tables(None, strict=True)


def test_both_readings_agree_on_a_bound_registry(packet_root):
    registry = open_packet(packet_root).registry
    assert declared_tables(registry) == declared_tables(registry, strict=True)
    assert "core.sessions" in declared_tables(registry)

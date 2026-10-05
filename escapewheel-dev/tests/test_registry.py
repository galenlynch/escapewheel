import json
import sys

import pytest

import escapewheel_dev as ew
from escapewheel_dev.registry import CORE, EXTENSIONS_VARIABLE


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


@pytest.fixture
def outside(tmp_path, monkeypatch):
    """A directory outside the checkout holding one extension, `outside`, and no extension added yet."""
    document = json.loads((ew.ROOT / "extensions" / "vr_foraging.json").read_text())
    document["extension_id"] = document["registry_id"] = "outside"
    document["resources"] = {
        f"outside.{resource_id.partition('.')[2]}": declaration
        for resource_id, declaration in document["resources"].items()
    }
    directory = tmp_path / "authored"
    directory.mkdir()
    (directory / "outside.json").write_text(json.dumps(document))
    monkeypatch.setattr(sys.modules["escapewheel_dev.registry"], "_ADDED", [])
    ew.registries.cache_clear()
    yield directory
    ew.registries.cache_clear()


def test_an_extension_outside_the_checkout_is_read_from_the_variable(outside, monkeypatch):
    monkeypatch.setenv(EXTENSIONS_VARIABLE, str(outside))
    ew.registries.cache_clear()
    assert ew.registry("outside").path == outside / "outside.json"
    assert ew.table("outside.sites").registry == "outside"


def test_an_added_extension_is_read(outside):
    ew.add_extensions(outside / "outside.json")
    assert ew.registry("outside").path == outside / "outside.json"


def test_the_command_reads_an_extension_named_before_the_subcommand(outside, capsys):
    from escapewheel_dev.cli import main

    assert main(["--extension", str(outside), "tables", "outside"]) == 0
    assert "outside.sites" in capsys.readouterr().out
    assert main([f"--extension={outside / 'absent.json'}", "tables", "outside"]) == 2
    assert "absent.json does not exist" in capsys.readouterr().err


def test_a_missing_path_in_the_variable_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv(EXTENSIONS_VARIABLE, str(tmp_path / "absent.json"))
    with pytest.raises(FileNotFoundError, match="absent.json"):
        ew.extension_paths()

import json

import pytest

import escapewheel_dev as ew
from escapewheel_dev.cli import COMMANDS, main


def run(capsys, *args):
    status = main(list(args))
    out, err = capsys.readouterr()
    return status, out, err


def test_help_lists_every_subcommand_in_one_line_each(capsys):
    with pytest.raises(SystemExit) as exit:
        main(["--help"])
    assert exit.value.code == 0
    out = capsys.readouterr().out
    assert all(name in out for name in COMMANDS)
    # Only each docstring's summary line, not what follows it.
    assert "Prints one" not in out


@pytest.mark.parametrize("name", list(COMMANDS))
def test_each_subcommand_help_shows_its_whole_docstring(capsys, name):
    with pytest.raises(SystemExit) as exit:
        main([name, "--help"])
    assert exit.value.code == 0
    out = " ".join(capsys.readouterr().out.split())
    assert " ".join(COMMANDS[name].__doc__.split("\n")[0].split()) in out


def test_text_output_names_the_record_and_its_fields(capsys):
    status, out, _ = run(capsys, "requirements", "2", "--keyword", "MUST")
    assert status == 0
    header, first, *_ = out.splitlines()
    assert header == "# Requirement: section.part\tsection.number\tkeywords\tsentence"
    assert first.startswith("02\t")


def test_json_holds_every_field_the_library_returns(capsys):
    status, out, _ = run(capsys, "columns", "core", "--presence", "nullable", "--role", "identifier", "--json")
    assert status == 0
    found = json.loads(out)
    expected = ew.columns("core", presence="nullable", roles=("identifier",))
    assert [(column["table"], column["name"]) for column in found] == [(c.table, c.name) for c in expected]
    assert "raw" not in found[0]
    assert {"registry", "type", "presence", "role", "identity", "unit", "description"} <= set(found[0])


def test_a_missing_name_is_an_error_naming_it(capsys):
    status, out, err = run(capsys, "table", "no.such_table")
    assert (status, out) == (2, "")
    assert "no.such_table" in err


def test_fields_name_what_a_record_has(capsys):
    status, out, _ = run(capsys, "fields", "Requirement")
    assert status == 0
    assert [line.split("\t")[1] for line in out.splitlines()[1:]] == ["section", "keywords", "sentence"]
    with pytest.raises(AttributeError, match="sentence"):
        _ = ew.requirements(2)[0].text  # type: ignore[attr-defined]


def test_rule_shows_what_its_query_reads(capsys):
    rule = ew.rules_reading("core.units", "unit_id", ew.rules())[0]
    status, out, _ = run(capsys, "rule", rule.id, "--json")
    assert status == 0
    shown = json.loads(out)
    assert shown["sql"] == rule.sql
    assert ["core.units", "unit_id"] in shown["checked"]["inputs"]


def test_packet_subcommands(capsys, valid):
    status, out, _ = run(capsys, "validate", str(valid), "--json")
    assert status == 0
    assert json.loads(out)["status"] == "passed"
    status, out, _ = run(capsys, "sql", str(valid), "SELECT count(*) AS n FROM core_units", "--json")
    assert json.loads(out)[0]["n"] > 0
    status, out, _ = run(capsys, "stored-columns", str(valid), "core.units")
    assert "unit_id" in out.splitlines()
    status, out, _ = run(capsys, "undeclared-columns", str(valid))
    assert out.splitlines() == ["# resource_id\tcolumns"]

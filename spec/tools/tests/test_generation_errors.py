"""A generator raises `GenerationError` for a source it cannot use, and its `main` reports it."""

import pytest

import assemble
import build
import canonical
import columns
import render
from specdoc import GenerationError


def test_an_unknown_rule_template_is_a_generation_error():
    with pytest.raises(GenerationError, match="core.a: unknown rule template 'span'"):
        assemble.expand("span", "core.a", {}, ["a_id"])


def test_a_malformed_column_reference_is_a_generation_error():
    with pytest.raises(GenerationError, match="core.a.b_id: a column's references"):
        assemble._column("core.a", {"name": "b_id", "references": {"resource": "core.b"}})


def test_a_single_column_reference_entry_is_a_generation_error():
    source = {"columns": [], "references": [{"columns": ["b_id"]}]}
    with pytest.raises(GenerationError, match="core.a: a single-column reference is written on its column"):
        assemble._table("core.a", source)


def test_a_non_table_resource_declaring_columns_is_a_generation_error(tmp_path):
    path = tmp_path / "core.a.toml"
    path.write_text('kind = "opaque"\ncolumns = []\n')
    with pytest.raises(GenerationError, match=r"core.a.toml: a opaque resource declares \['columns'\]"):
        assemble._resource(path)


def test_an_undeclared_key_is_a_generation_error():
    with pytest.raises(GenerationError, match="core.a: rule keys the meta-schema does not declare"):
        canonical._ordered({"undeclared": 1}, "rule", "core.a")


def test_a_column_table_of_an_undeclared_resource_is_a_generation_error():
    with pytest.raises(GenerationError, match="core.a is not a resource of the registry"):
        columns.table("core.a", {})


def test_unmatched_guide_regions_are_a_generation_error():
    with pytest.raises(GenerationError, match="README regions"):
        render.fill("<!-- BEGIN generated: other -->\n<!-- END generated: other -->", {"counts": ""})


def test_main_reports_a_generation_error_and_fails(monkeypatch, capsys):
    def refuse():
        raise GenerationError("core.a: unusable")

    monkeypatch.setattr(build, "stale", refuse)

    assert build.main(["--check"]) == 1
    assert capsys.readouterr().err == "core.a: unusable\n"

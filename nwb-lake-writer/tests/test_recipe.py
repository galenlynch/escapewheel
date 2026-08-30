"""The session recipe: parsing, and the checks the registry makes possible before any I/O."""

from __future__ import annotations

import pytest

from nwb_lake_writer.recipe import Recipe
from nwb_lake_writer.session import CONSUMES, RecipeError, order

BASE = """
[packet]
id = "s001"
registry = "reg.json"

[session]
session_id = "s001"
reference_clock_id = "harp"

[subject]
subject_id = "m001"

[[clock]]
clock_id = "harp"
name = "HARP"
tick_rate_num = 31250
origin = "HARP epoch"
"""


def write(tmp_path, body, name="session.toml"):
    """Write a recipe and return its path."""
    path = tmp_path / name
    path.write_text(BASE + body)
    return path


def levels(problems):
    """The messages, keyed by level, for asserting on one kind at a time."""
    return {p.level: [q.message for q in problems if q.level == p.level] for p in problems}


def test_a_recipe_parses_its_declarations(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "sorted"\nowns = ["core.units"]\n'))
    assert recipe.packet_id == "s001"
    assert recipe.session["session_id"] == "s001"
    assert [c.clock_id for c in recipe.clocks] == ["harp"]
    assert recipe.sources[0].kind == "sorter"
    assert recipe.sources[0].owns == ("core.units",)


def test_paths_resolve_against_the_recipe_not_the_caller(tmp_path):
    """A recipe travels with the tree it describes, so relative paths are relative to it."""
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "sorted"\nowns = []\n'))
    assert recipe.sources[0].root == tmp_path / "sorted"
    assert recipe.registry == tmp_path / "reg.json"


def test_the_digest_identifies_the_parameters(tmp_path):
    """`core.processing_runs` names the run; the digest is what makes the name answerable."""
    one = Recipe.load(write(tmp_path, "\n", "a.toml"))
    same = Recipe.load(write(tmp_path, "\n", "b.toml"))
    other = Recipe.load(write(tmp_path, "\n# a comment changes it\n", "c.toml"))
    assert one.digest == same.digest
    assert one.digest != other.digest


def test_a_sound_recipe_reports_nothing(tmp_path, registry):
    path = tmp_path / "sound.toml"
    path.write_text(
        BASE.replace('[subject]\nsubject_id = "m001"\n', "")
        + '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.subjects"]\n'
    )
    assert [str(p) for p in Recipe.load(path).check(registry) if p.level == "error"] == []


def test_an_unknown_resource_is_caught(tmp_path, registry):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.nonsense"]\n'))
    assert any("core.nonsense" in p.message for p in recipe.check(registry))


def test_two_owners_of_one_resource_is_an_error(tmp_path, registry):
    """The failure this exists to prevent: last writer wins, silently."""
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.probes"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = ["core.probes"]\n'
    )
    problems = recipe_problems(tmp_path, body, registry)
    assert any("owned by 2 sources" in m for m in problems["error"])


def test_two_contributors_to_one_resource_is_allowed(tmp_path, registry):
    """`core.clocks` is the real case: per-stream clocks and the rig clock they anchor to."""
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\ncontributes = ["core.clocks"]\n'
        '\n[[source]]\nkind = "sync"\nroot = "."\nowns = []\ncontributes = ["core.clocks"]\n'
    )
    problems = recipe_problems(tmp_path, body, registry)
    assert not any("core.clocks" in m for m in problems.get("error", []))


def test_owning_what_another_source_also_supplies_is_an_error(tmp_path, registry):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.clocks"]\n'
        '\n[[source]]\nkind = "sync"\nroot = "."\nowns = []\ncontributes = ["core.clocks"]\n'
    )
    problems = recipe_problems(tmp_path, body, registry)
    assert any("also supplied by" in m for m in problems["error"])


def test_a_reference_clock_that_is_not_declared_is_caught(tmp_path, registry):
    path = tmp_path / "s.toml"
    path.write_text(BASE.replace('reference_clock_id = "harp"', 'reference_clock_id = "nope"'))
    assert any("reference_clock_id" in p.message for p in Recipe.load(path).check(registry))


def test_a_parent_clock_that_is_not_declared_is_caught(tmp_path, registry):
    body = (
        '\n[[clock]]\nclock_id = "probe"\nname = "p"\ntick_rate_num = 30000\norigin = "x"\nparent_clock_id = "gone"\n'
    )
    assert any("gone" in p.message for p in Recipe.load(write(tmp_path, body)).check(registry))


def recipe_problems(tmp_path, body, registry):
    """Check a recipe body and return its messages grouped by level."""
    return levels(Recipe.load(write(tmp_path, body)).check(registry))


def test_sources_order_after_what_they_consume(tmp_path, registry):
    body = (
        '\n[[source]]\nkind = "waveforms"\nroot = "."\nowns = []\n'
        '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n'
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'
    )
    ordered = [s.kind for s in order(Recipe.load(write(tmp_path, body)))]
    assert ordered.index("sorter") < ordered.index("nwb") < ordered.index("waveforms")


def test_a_source_consuming_an_undeclared_kind_is_refused(tmp_path):
    """`NWBSource` needs the sorter's units to attach a unit to an electrode."""
    body = '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n'
    with pytest.raises(RecipeError, match="consumes sorter"):
        order(Recipe.load(write(tmp_path, body)))


def test_a_dependency_cycle_is_refused(tmp_path, monkeypatch):
    monkeypatch.setitem(CONSUMES, "sorter", ("nwb",))
    body = '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'
    with pytest.raises(RecipeError, match="depend on each other"):
        order(Recipe.load(write(tmp_path, body)))

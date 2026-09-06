"""The session recipe: parsing, and the checks the registry makes possible before any I/O."""

from __future__ import annotations

import pytest

from escapewheel_writer.recipe import RECIPE_SUPPLIES, Recipe
from escapewheel_writer.session import CONSUMES, RecipeError, _note_unclaimed, order

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


def test_a_required_option_is_reported_not_crashed_on(tmp_path):
    """`_build_source` pops `zone` for the nwb kind, so a recipe without one used to die there
    with a KeyError after --check had called the recipe sound."""
    from escapewheel_writer.recipe import REQUIRED_OPTIONS, Recipe

    path = tmp_path / "recipe.toml"
    path.write_text(
        '[packet]\nid = "s"\n\n[session]\nsession_id = "s"\n\n'
        '[[source]]\nkind = "nwb"\nroot = "."\nowns = ["core.trials"]\n'
    )
    problems = Recipe.load(path).check({"tables": {"core.trials": {"columns": [], "references": []}}})
    assert "zone" in REQUIRED_OPTIONS["nwb"]
    assert any("requires 'zone'" in str(p) for p in problems)


def test_an_option_that_is_set_is_not_reported(tmp_path):
    from escapewheel_writer.recipe import Recipe

    path = tmp_path / "recipe.toml"
    path.write_text(
        '[packet]\nid = "s"\n\n[session]\nsession_id = "s"\n\n'
        '[[source]]\nkind = "nwb"\nroot = "."\nzone = "UTC"\nowns = ["core.trials"]\n'
    )
    problems = Recipe.load(path).check({"tables": {"core.trials": {"columns": [], "references": []}}})
    assert not [p for p in problems if "zone" in str(p)]


class Noted:
    """The one thing `_note_unclaimed` needs of a source: somewhere to put a note."""

    def __init__(self) -> None:
        self.notes: list[str] = []


def test_a_produced_resource_no_source_claims_is_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    _note_unclaimed(recipe, recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 19_061})
    assert len(source.notes) == 1
    assert "core.unit_quality_labels (19,061 rows)" in source.notes[0]
    assert "discarded" in source.notes[0]


def test_a_resource_another_source_claims_is_not_noted(tmp_path):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\n'
    )
    recipe = Recipe.load(write(tmp_path, body))
    source = Noted()
    # The sorter offers core.probes too; cli.PREFERRED gives it to the NWB, so losing it here
    # is the design rather than an omission.
    _note_unclaimed(recipe, recipe.sources[0], source, {"core.units": 4, "core.probes": 10})
    assert source.notes == []


def test_an_empty_unclaimed_resource_is_not_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    _note_unclaimed(recipe, recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 0})
    assert source.notes == []


def test_what_the_recipe_itself_supplies_is_not_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    # RECIPE_SUPPLIES: the recipe writes these, so a source producing them loses to it by design.
    _note_unclaimed(recipe, recipe.sources[0], source, {"core.processing_runs": 2, "core.subjects": 1})
    assert source.notes == []


# -- R63: a recipe declares what it narrows ------------------------------------------------


def test_a_source_that_declares_no_owns_takes_what_it_produces(tmp_path, registry):
    """Silence means the whole of PRODUCES, not nothing (R63 §2.2)."""
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n'))
    owns = set(recipe.sources[0].owns)
    assert "core.units" in owns and "core.unit_quality_labels" in owns and "core.spike_events" in owns
    # RECIPE_SUPPLIES is not an adapter's to claim (R63 §3).
    assert not owns & set(RECIPE_SUPPLIES)


def test_an_explicit_owns_still_narrows(tmp_path, registry):
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
    assert Recipe.load(write(tmp_path, body)).sources[0].owns == ("core.units",)


def test_an_empty_owns_narrows_to_nothing(tmp_path, registry):
    """An explicit empty list is a decision; silence is not, so the two cannot be conflated."""
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = []\n'
    assert Recipe.load(write(tmp_path, body)).sources[0].owns == ()


def test_a_defaulted_source_does_not_take_what_another_explicitly_owns(tmp_path, registry):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\nzone = "UTC"\n'
    )
    recipe = Recipe.load(write(tmp_path, body))
    sorter = next(s for s in recipe.sources if s.kind == "sorter")
    assert "core.probes" not in sorter.owns


def test_a_preference_settles_a_resource_two_adapters_produce(tmp_path, registry):
    """Both produce core.probes; PREFERRED gives it to the NWB, so neither owns it twice."""
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\n\n[[source]]\nkind = "nwb"\nroot = "n"\nzone = "UTC"\n'
    recipe = Recipe.load(write(tmp_path, body))
    owners = {s.kind: set(s.owns) for s in recipe.sources}
    assert "core.probes" in owners["nwb"] and "core.probes" not in owners["sorter"]
    assert not [p for p in recipe.check(registry) if p.level == "error"]


def test_a_shared_resource_is_contributed_not_owned(tmp_path, registry):
    """core.clocks has two legitimate suppliers, so a default contributes rather than owns."""
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n'))
    spec = recipe.sources[0]
    assert "core.clocks" in spec.contributes and "core.clocks" not in spec.owns


def test_a_resource_no_source_claims_is_a_warning(tmp_path, registry):
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
    said = levels(Recipe.load(write(tmp_path, body)).check(registry))
    assert any("core.unit_quality_labels" in m for m in said.get("warning", []))
    # Narrowing this far also dangles required foreign keys, which is a separate finding and
    # the reason the unclaimed report is a warning rather than one more error.
    assert any("core.curation_versions" in m for m in said.get("error", []))


def test_what_a_source_produces_is_what_it_can_emit():
    """R63 §4: a PRODUCES that drifts from the code reintroduces the defect one level up."""
    from escapewheel_writer.sources import ADAPTERS

    for kind, adapter in ADAPTERS.items():
        declared = set(getattr(adapter, "PRODUCES", ()))
        assert declared or kind == "tables", f"{kind} declares no PRODUCES (R63 §2.1)"
        assert all(r.count(".") == 1 for r in declared), f"{kind} declares a malformed resource ID"

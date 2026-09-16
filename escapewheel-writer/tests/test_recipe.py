"""The session recipe: parsing, and the checks the registry makes possible before any I/O."""

from __future__ import annotations

from typing import ClassVar

import pytest

from escapewheel_writer.recipe import RECIPE_SUPPLIES, SHARED, Recipe, arbitrated, preferences, produces
from escapewheel_writer.session import (
    Context,
    RecipeError,
    _encoding_exceptions,
    _note_unclaimed,
    _refuse_a_discarded_fact,
    order,
)
from escapewheel_writer.sources import ADAPTERS, SourceDefect, discovered

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


def test_a_recipe_may_run_some_sources_in_process_and_not_others(tmp_path):
    """Part 05 §3.9 is per source, and `[packet]` is the default because whether a set of adapters
    installs together is a fact about the set. An entry narrows or widens it."""
    both = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.units"]{}\n'
        '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = ["core.probes"]\n'
    )

    path = tmp_path / "packet-level.toml"
    path.write_text(BASE.replace('registry = "reg.json"', 'registry = "reg.json"\nin_process = true') + both.format(""))
    assert [s.in_process for s in Recipe.load(path).sources] == [True, True]

    out = write(tmp_path, both.format("\nin_process = true"), "one-in.toml")
    assert [s.in_process for s in Recipe.load(out).sources] == [True, False]


def test_a_shipped_adapter_needs_no_declaration_and_a_registered_one_does(tmp_path):
    """Part 03 §11.1's test is the release boundary. A built-in ships with this package and is
    upgraded with it, so in process is its only route and there is nothing to declare; a kind
    another distribution registers moves on its own schedule and must say how it can be reached."""
    registry = {"tables": {"core.units": {"columns": [], "rules": []}}}

    built_in = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'))
    assert not [p for p in built_in.check(registry) if "reach" in p.message]

    registered = write(tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\n', "reg.toml")
    problems = [p.message for p in Recipe.load(registered).check(registry) if "neither delivers" in p.message]
    assert problems and "vr_sites" in problems[0]

    opted = write(
        tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\nin_process = true\n', "opt.toml"
    )
    assert not [p for p in Recipe.load(opted).check(registry) if "neither delivers" in p.message]

    delivered = write(
        tmp_path,
        '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\n'
        '\n[source.delivery]\nprotocol = "stream-v0.1"\ncommand = ["vr-sites-adapter"]\n',
        "delivered.toml",
    )
    assert not [p for p in Recipe.load(delivered).check(registry) if "neither delivers" in p.message]


def test_an_in_process_source_does_not_carry_the_flag_into_the_adapter(tmp_path):
    """`in_process` is the build's business, so it must not reach the adapter as an option: every
    other key of a source entry is passed through as a keyword argument."""
    recipe = Recipe.load(
        write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\nin_process = true\n')
    )
    assert "in_process" not in recipe.sources[0].options


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
    # Both consume the sorter's units and neither consumes the other: the waveform source names a
    # contact from the electrode table it opens itself, and the writer resolves the name (Part 05
    # §8), so nothing makes it wait for the NWB.
    assert ordered.index("sorter") < ordered.index("nwb")
    assert ordered.index("sorter") < ordered.index("waveforms")


def test_a_source_consuming_an_undeclared_kind_is_refused(tmp_path):
    """`NWBSource` needs the sorter's units to attach a unit to an electrode."""
    body = '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n'
    with pytest.raises(RecipeError, match="consumes sorter"):
        order(Recipe.load(write(tmp_path, body)))


def test_a_dependency_cycle_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(ADAPTERS["sorter"], "CONSUMES", ("nwb",))
    body = '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'
    with pytest.raises(RecipeError, match="depend on each other"):
        order(Recipe.load(write(tmp_path, body)))


def test_a_required_option_is_reported_not_crashed_on(tmp_path):
    """`_build_source` pops `zone` for the nwb kind, so a recipe without one used to die there
    with a KeyError after --check had called the recipe sound.

    What makes it reportable is the adapter's own `NEEDS` (Part 05 §3.4): `zone` resolves to no
    term, so it falls through to the recipe's options and the entry has to carry it.
    """
    from escapewheel_writer.recipe import Recipe, needs

    path = tmp_path / "recipe.toml"
    path.write_text(
        '[packet]\nid = "s"\n\n[session]\nsession_id = "s"\n\n'
        '[[source]]\nkind = "nwb"\nroot = "."\nowns = ["core.trials"]\n'
    )
    problems = Recipe.load(path).check({"tables": {"core.trials": {"columns": [], "references": []}}})
    assert "zone" in needs("nwb")
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
    _note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 19_061})
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
    _note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.probes": 10})
    assert source.notes == []


def test_an_empty_unclaimed_resource_is_not_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    _note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 0})
    assert source.notes == []


def test_what_the_recipe_itself_supplies_is_not_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    # RECIPE_SUPPLIES: the recipe writes these, so a source producing them loses to it by design.
    _note_unclaimed(recipe.sources[0], source, {"core.processing_runs": 2, "core.sessions": 1})
    assert source.notes == []


def test_rows_another_source_owns_are_noted_without_a_preference(tmp_path):
    """Part 05 §3.4. Two sources holding disjoint parts of one resource; `owns` keeps one silently."""
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
                                        'owns = ["core.units"]\n'
                                        '\n[[source]]\nkind = "sync"\nroot = "y"\n'
                                        'owns = ["core.clock_observation_intervals"]\n'))
    source = Noted()
    _note_unclaimed(recipe.sources[0], source, {"core.clock_observation_intervals": 12})
    assert any("core.clock_observation_intervals" in n for n in source.notes)


def test_a_preference_is_what_makes_a_discard_silent(tmp_path):
    """The other side: `core.probes` names a winner, so the loser's copy is redundant by design.

    This was written against `core.clocks`, whose preference was never consulted -- SHARED is
    checked first and returns -- so the silence came from a dead entry rather than from a
    preference. `core.probes` is the preference that arbitrates.
    """
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
                                        'owns = ["core.units"]\n'
                                        '\n[[source]]\nkind = "nwb"\nroot = "y"\n'
                                        'owns = ["core.probes"]\n'))
    source = Noted()
    _note_unclaimed(recipe.sources[0], source, {"core.probes": 12})
    assert source.notes == []


def test_a_preferred_resource_draws_a_refusal_rather_than_a_note(tmp_path):
    """Part 05 §3.4 replaces the note for a preferred resource with something stronger.

    A preference exempts a resource from Part 05 §3.4's report. What makes that sound is not the
    silence but the refusal: `_refuse_a_discarded_fact` fails the build where the displaced source
    stated a value the preferred one did not, which a note only mentioned.

    Checked on `core.probes`, which this package both prefers and produces from two kinds. The
    other case, `core.subjects`, is declared by the distribution shipping the `session` kind and is
    checked there, since a preference is kept honest by whoever can see both producers.
    """
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    _note_unclaimed(recipe.sources[0], source, {"core.probes": 1})
    assert source.notes == []
    assert preferences()["core.probes"] == "nwb"


# -- R108: a preference discards no stated fact --------------------------------------------


class _Registry:
    """Enough of a writer to answer what a table declares."""

    def __init__(self, registry):
        self._registry = registry

    def spec(self, resource_id):
        return self._registry["tables"].get(resource_id)


def _contest(tmp_path):
    """A recipe where the NWB claims `core.probes` and the sorter also produces it."""
    return Recipe.load(write(tmp_path, '\n[[source]]\nkind = "nwb"\nroot = "n"\n'
                                       'owns = ["core.probes"]\n'
                                       '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
                                       'owns = ["core.units"]\n'))


def test_a_preference_names_a_resource_more_than_one_source_produces(tmp_path):
    """Part 05 §3.3: an uncontested entry arbitrates nothing and exempts a report never due.

    `core.unit_electrodes` sat here until the sorter stopped producing that table, and nothing
    noticed. This is Part 02 §4's discipline for a declared naming exception, one table over.
    """
    uncontested = {
        resource: [kind for kind in sorted({**ADAPTERS, **discovered()}) if resource in produces(kind)]
        for resource in sorted(preferences())
    }
    assert {r: k for r, k in uncontested.items() if len(k) < 2} == {}


def test_a_shared_resource_is_not_compared(tmp_path, registry):
    """R108 §4: where the rows are disjoint there is no passed-over row to weigh.

    `core.clocks` and both array tables sit in `PREFERRED` *and* `SHARED`, and
    `_resolve_ownership` checks `SHARED` first, so the preference arbitrates nothing there. A real
    build refused on exactly these: the sync source's reference clock read as a loss against the
    sorter's twelve probe clocks, which are different rows and not a displaced copy.
    """
    assert "core.probes" in arbitrated()
    assert not arbitrated() & SHARED


def test_a_preference_that_discards_a_stated_fact_is_refused(tmp_path, registry):
    """Part 05 §3.4: the premise a preference buys silence on is now checked."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {
        "nwb": [{"probe_id": "probeA", "probe_type": None}],
        "sorter": [{"probe_id": "probeA", "probe_type": "NP2000"}],
    }
    with pytest.raises(SourceDefect, match=r"core\.probes\.probe_type"):
        _refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))


def test_a_preferred_source_that_stages_nothing_is_refused(tmp_path, registry):
    """Part 05 §3.4's limiting case: every value discarded, not just one."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {"sorter": [{"probe_id": "probeA"}]}
    context.stated["core.probes"]["nwb"] = []
    with pytest.raises(SourceDefect, match="staged none"):
        _refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))


def test_two_sources_that_agree_are_not_refused(tmp_path, registry):
    """Agreement is the ordinary case, and `metadata` is never compared (Part 05 §3.4)."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {
        "nwb": [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"a": 1}'}],
        "sorter": [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"b": 2}'}],
    }
    _refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))


# -- R63: a recipe declares what it narrows ------------------------------------------------


def test_a_source_that_declares_no_owns_takes_what_it_produces(tmp_path, registry):
    """Silence means the whole of PRODUCES, not nothing (Part 05 §3.4)."""
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
        assert declared or kind == "tables", f"{kind} declares no PRODUCES (Part 05 §3.4)"
        assert all(r.count(".") == 1 for r in declared), f"{kind} declares a malformed resource ID"


# -- R87: authority for a declared fact ------------------------------------------------------

NWB = '\n[[source]]\nkind = "nwb"\nroot = "s"\nzone = "UTC"\nowns = ["core.probes"]\n'


def test_a_declared_fact_a_source_states_is_reported_before_any_io(tmp_path, registry):
    """Part 05 §3.5. The base recipe declares `[subject].subject_id` and the NWB states it."""
    problems = levels(Recipe.load(write(tmp_path, NWB)).check(registry))
    assert any("subject.subject_id is declared and nwb states it" in m for m in problems.get("warning", []))


def test_an_override_is_recorded_rather_than_warned(tmp_path, registry):
    """Part 05 §3.5: a field an override covers is information; the build will apply it."""
    body = '\n[overrides]\n"subject.subject_id" = "the file names the wrong animal"\n' + NWB
    problems = levels(Recipe.load(write(tmp_path, body)).check(registry))
    assert any("subject.subject_id is declared and overrides nwb" in m for m in problems.get("info", []))
    assert not any("subject.subject_id is declared and nwb" in m for m in problems.get("warning", []))


def test_an_override_with_no_reason_is_refused(tmp_path, registry):
    """Part 05 §3.6: a bare marker would silence a difference without saying why."""
    body = '\n[overrides]\n"subject.subject_id" = "   "\n' + NWB
    problems = levels(Recipe.load(write(tmp_path, body)).check(registry))
    assert any("carries no reason" in m for m in problems.get("error", []))


def test_an_override_of_a_fact_nothing_states_is_reported_not_refused(tmp_path, registry):
    """Part 05 §3.6: a stale override leaves the packet correct, so it costs a line of the log."""
    body = (
        '\n[overrides]\n"subject.subject_id" = "why"\n'
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
    )
    problems = levels(Recipe.load(write(tmp_path, body)).check(registry))
    assert any("overrides nothing" in m for m in problems.get("warning", []))
    assert not any("overrides nothing" in m for m in problems.get("error", []))


def test_a_source_that_cannot_say_what_it_states_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: an adapter declaring nothing must not read as one that states nothing."""
    from escapewheel_writer import sources

    class Mute:
        PRODUCES = frozenset({"core.units"})

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Mute)
    problems = levels(Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry))
    assert any("declares no STATES" in m for m in problems.get("error", []))


def test_a_stated_fact_with_no_accessor_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: the declaration is checked against the class, so it cannot drift unseen."""
    from escapewheel_writer import sources

    class Absent:
        PRODUCES = frozenset({"core.units"})
        STATES: ClassVar[dict[str, str]] = {"subject.subject_id": "nowhere"}

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Absent)
    problems = levels(Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry))
    assert any("which its adapter does not expose" in m for m in problems.get("error", []))


# -- an extension declares an encoding where the writer can read it without importing it ------


def test_an_encoding_declaration_needs_a_choice_and_a_reason(tmp_path):
    """An extension reaches the writer across a file, so it declares in the recipe, with a reason.

    The reason is what makes the entry re-judgeable: an encoding is a fact about one packet's
    values, so a bare choice cannot be checked against the next session's data.
    """
    recipe = Recipe.load(write(tmp_path, """
[encoding]
"aind_unit_qc.metrics.num_spikes_used" = { encoding = "delta", reason = "climbs with the spike count; 1.7x" }
"aind_unit_qc.metrics.presence_ratio" = { encoding = "sideways", reason = "no such thing" }
"aind_unit_qc.metrics.silhouette" = { encoding = "plain", reason = "" }
"""))
    tables = {"aind_unit_qc.metrics": {"columns": [{"name": "num_spikes_used"},
                                                   {"name": "presence_ratio"},
                                                   {"name": "silhouette"}]}}
    found = recipe.encoding_problems(tables)
    assert any("sideways" in e for e in found)
    assert any("silhouette" in e and "no reason" in e for e in found)
    assert not any("num_spikes_used" in e for e in found)


def test_an_encoding_declaration_reaches_the_writer(tmp_path):
    """`resource.column` splits at the last dot, a resource ID being dotted itself."""
    recipe = Recipe.load(write(tmp_path, """
[encoding]
"aind_unit_qc.metrics.num_spikes_used" = { encoding = "delta", reason = "1.7x" }
"""))
    assert _encoding_exceptions(recipe)["delta"] == {"aind_unit_qc.metrics": ("num_spikes_used",)}


# -- a source the build does not import (Part 03 §11) ---------------------------------------


def declaration_for(tmp_path, **fields):
    """Write an adapter's declaration document and return its path, relative to the recipe."""
    import json

    document = {
        "kind": "thermistor",
        "protocol": "stream-v0.1",
        "produces": ["core.devices"],
        "needs": ["root", "session_id", "sample_rate_hz"],
        "states": [],
        "consumes": [],
        **fields,
    }
    (tmp_path / "thermistor.json").write_text(json.dumps(document))
    return "thermistor.json"


DELIVERED = """
[[source]]
kind = "thermistor"
root = "."
sample_rate_hz = 1000

[source.delivery]
declaration = "{declaration}"
command = ["thermistor-adapter", "--verbose"]
report_path = "reports/thermistor.json"
"""


def test_a_delivered_source_carries_how_a_build_reaches_it(tmp_path):
    """The recipe carries every fact about the machine; the document carries the adapter's."""
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=declaration_for(tmp_path))))
    (spec,) = recipe.sources
    assert spec.delivery.command == ("thermistor-adapter", "--verbose")
    assert spec.delivery.protocol == "stream-v0.1"
    assert spec.delivery.report_path == tmp_path / "reports/thermistor.json"


def test_ownership_defaults_from_a_document_for_a_kind_that_cannot_be_imported(tmp_path, registry):
    """Which is the point of the document: a build settles ownership before it launches anything."""
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=declaration_for(tmp_path))))
    # `core.devices` is shared, so silence makes it a contribution rather than an exclusive claim.
    assert recipe.sources[0].claims == ("core.devices",)
    assert not [p for p in recipe.check(registry) if p.level == "error"]


def test_a_declaration_that_cannot_be_read_is_reported_rather_than_raised(tmp_path, registry):
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration="absent.json")))
    assert any("no adapter declaration to read" in p.message for p in recipe.check(registry))


def test_a_declaration_naming_a_resource_no_registry_declares_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, produces=["core.tirals"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any("no loaded registry declares" in p.message for p in recipe.check(registry))


def test_a_declaration_naming_a_protocol_outside_the_group_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, protocol="carrier-pigeon-v1.0")
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any("in no group" in p.message for p in recipe.check(registry))


def test_a_declaration_whose_shape_is_wrong_is_reported_where_it_is_wrong(tmp_path, registry):
    """The schema checks the shape; what the declaration says is checked against the registry."""
    named = declaration_for(tmp_path, protocol="carrier pigeon")
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any("protocol" in p.message and "thermistor.json" in p.message for p in recipe.check(registry))


def test_a_declaration_needing_what_the_recipe_does_not_set_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, needs=["root", "session_id", "calibration_uri"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any("neither a term nor an option" in p.message for p in recipe.check(registry))


def test_an_option_no_declaration_names_is_refused(tmp_path, registry):
    """An option nothing reads is a statement about the packet that never reaches the source."""
    named = declaration_for(tmp_path, accepts=["smoothing_window"])
    body = DELIVERED.format(declaration=named).replace(
        "sample_rate_hz = 1000", "sample_rate_hz = 1000\nsmoothing_windwo = 3"
    )
    recipe = Recipe.load(write(tmp_path, body))
    problems = [p.message for p in recipe.check(registry)]
    assert any("smoothing_windwo" in m and "neither as needed nor as accepted" in m for m in problems), problems


def test_an_accepted_option_the_recipe_leaves_unset_is_not_refused(tmp_path, registry):
    """What separates the two lists: a needed name a recipe omits is refused and an accepted one is not."""
    named = declaration_for(tmp_path, accepts=["smoothing_window"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert not [p for p in recipe.check(registry) if p.level == "error"]


def test_a_document_written_before_accepts_accepts_nothing(tmp_path, registry):
    """R119 §5's break, stated: such a document names no option, so a recipe setting one is refused."""
    import json

    named = declaration_for(tmp_path)
    assert "accepts" not in json.loads((tmp_path / named).read_text())
    body = DELIVERED.format(declaration=named).replace(
        "sample_rate_hz = 1000", "sample_rate_hz = 1000\nsmoothing_window = 3"
    )
    recipe = Recipe.load(write(tmp_path, body))
    assert any("neither as needed nor as accepted" in p.message for p in recipe.check(registry))


def test_a_delivery_with_no_command_is_refused(tmp_path, registry):
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        'command = ["thermistor-adapter", "--verbose"]\n', ""
    )
    recipe = Recipe.load(write(tmp_path, body))
    assert any("no command to run it with" in p.message for p in recipe.check(registry))


def test_a_source_is_reached_one_way_or_the_other(tmp_path, registry):
    """Part 05 §3.9: in process is the recipe's choice, and a delivery is the other choice."""
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        "sample_rate_hz = 1000", "sample_rate_hz = 1000\nin_process = true"
    )
    recipe = Recipe.load(write(tmp_path, body))
    assert any("one way or the other" in p.message for p in recipe.check(registry))


def test_a_built_in_adapter_may_be_delivered_without_a_document(tmp_path, registry):
    """A build may serve an adapter it ships over any protocol of the group (Part 03 §11.1)."""
    body = """
[[source]]
kind = "sorter"
root = "."
owns = ["core.units"]

[source.delivery]
protocol = "files-v0.1"
command = ["escapewheel", "deliver", "sorter"]
"""
    recipe = Recipe.load(write(tmp_path, body))
    assert recipe.sources[0].delivery.declaration is None
    # The recipe is one source short of validating, which is not what this is about: nothing the
    # build says about reaching the adapter is a problem.
    about = ("delivery", "declaration", "protocol", "declares")
    assert not [p for p in recipe.check(registry) if any(word in p.message for word in about)]


# -- a credential is not a recipe's to carry ------------------------------------------------


SIGNED = """
[[source]]
kind = "sorter"
root = "s3://private/ecephys"
owns = []
storage_options = {{ {options} }}
"""


def test_a_storage_option_carrying_a_credential_is_refused(tmp_path, registry):
    """The recipe is recorded in the packet it builds, so a key written here travels with it."""
    recipe = Recipe.load(write(tmp_path, SIGNED.format(options='key = "AKIA...", secret = "xyz"')))
    refused = [p.message for p in recipe.check(registry) if p.level == "error" and "credential" in p.message]
    assert len(refused) == 2
    assert "name a profile" in refused[0]


def test_a_reference_to_a_credential_is_not_one(tmp_path, registry):
    """A profile names where the secret is; the environment holds it and nothing crosses."""
    recipe = Recipe.load(write(tmp_path, SIGNED.format(options='profile = "aind", anon = false')))
    assert not [p for p in recipe.check(registry) if "credential" in p.message]


def test_a_token_that_names_a_mode_is_not_a_credential(tmp_path, registry):
    """gcsfs reads a public bucket with `token = "anon"`, so the name alone does not decide."""
    mode = Recipe.load(write(tmp_path, SIGNED.format(options='token = "anon"')))
    assert not [p for p in mode.check(registry) if "credential" in p.message]
    real = Recipe.load(write(tmp_path, SIGNED.format(options='token = "ya29.a0..."'), "signed.toml"))
    assert [p for p in real.check(registry) if "credential" in p.message]


def test_what_a_run_records_carries_no_credential(tmp_path):
    """Applied wherever a recipe is written down, since one written before the refusal exists."""
    from escapewheel_writer.recipe import REDACTED, redacted

    document = {
        "source": [
            {"kind": "sorter", "storage_options": {"key": "AKIA...", "anon": False}},
            {"kind": "nwb", "root": "/data/session.nwb"},
        ],
        "session": {"session_id": "s001"},
    }
    clean = redacted(document)
    assert clean["source"][0]["storage_options"] == {"key": REDACTED, "anon": False}
    assert clean["source"][1] == document["source"][1], "everything else is recorded as written"
    assert document["source"][0]["storage_options"]["key"] == "AKIA...", "the original is untouched"

"""The session recipe: parsing, and the checks the registry makes possible before any I/O."""

from __future__ import annotations

from typing import ClassVar

import pytest

from escapewheel_writer.recipe import RECIPE_SUPPLIES, Recipe
from escapewheel_writer.session import (
    Context,
    RecipeError,
    _encoding_exceptions,
    _note_unclaimed,
    _refuse_a_discarded_fact,
    order,
)
from escapewheel_writer.sources import ADAPTERS, SourceDefect

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


#: The NWB states a probe's type and manufacturer where the sorter knows only the stream, so a
#: recipe listing both prefers it.
PREFER_NWB = """
[preference."core.probes"]
source = "nwb"
reason = "the NWB states a probe's type and manufacturer; the sorter knows only the stream"
"""


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
    registry = {"resources": {"core.units": {"kind": "table", "table": {"columns": [], "rules": []}}}}

    built_in = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'))
    assert not [p for p in built_in.check(registry) if "reach" in p.message]

    registered = write(tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\n', "reg.toml")
    problems = [p.message for p in Recipe.load(registered).check(registry) if "neither delivers" in p.message]
    assert problems and "vr_sites" in problems[0]

    opted = write(tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\nin_process = true\n', "opt.toml")
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
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\nin_process = true\n'))
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
    problems = Recipe.load(path).check(
        {
            "resources": {
                "core.trials": {
                    "kind": "table",
                    "table": {"columns": [], "references": []},
                }
            }
        }
    )
    assert "zone" in needs("nwb")
    assert any("requires 'zone'" in str(p) for p in problems)


def test_an_option_that_is_set_is_not_reported(tmp_path):
    from escapewheel_writer.recipe import Recipe

    path = tmp_path / "recipe.toml"
    path.write_text(
        '[packet]\nid = "s"\n\n[session]\nsession_id = "s"\n\n'
        '[[source]]\nkind = "nwb"\nroot = "."\nzone = "UTC"\nowns = ["core.trials"]\n'
    )
    problems = Recipe.load(path).check(
        {
            "resources": {
                "core.trials": {
                    "kind": "table",
                    "table": {"columns": [], "references": []},
                }
            }
        }
    )
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


def test_a_resource_the_recipe_prefers_another_source_for_is_not_noted(tmp_path):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\n' + PREFER_NWB
    )
    recipe = Recipe.load(write(tmp_path, body))
    source = Noted()
    # The sorter offers core.probes too; the recipe gives it to the NWB, so losing it here is the
    # design rather than an omission.
    _note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.probes": 10}, frozenset(recipe.preferred))
    assert source.notes == []


def test_a_resource_another_source_owns_is_noted_where_the_recipe_prefers_none(tmp_path):
    """Part 05 §3.4: without a preference the two sources are producing different rows."""
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\n'
    )
    recipe = Recipe.load(write(tmp_path, body))
    source = Noted()
    _note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.probes": 10}, frozenset(recipe.preferred))
    assert any("core.probes (10 rows)" in n for n in source.notes)


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
    recipe = Recipe.load(
        write(
            tmp_path,
            '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
            'owns = ["core.units"]\n'
            '\n[[source]]\nkind = "sync"\nroot = "y"\n'
            'owns = ["core.clock_observation_intervals"]\n',
        )
    )
    source = Noted()
    _note_unclaimed(recipe.sources[0], source, {"core.clock_observation_intervals": 12})
    assert any("core.clock_observation_intervals" in n for n in source.notes)


def test_a_preferred_resource_draws_a_refusal_rather_than_a_note(tmp_path):
    """Part 05 §3.4 replaces the note for a preferred resource with something stronger.

    A preference exempts a resource from Part 05 §3.4's report. What makes that sound is not the
    silence but the refusal: `_refuse_a_discarded_fact` fails the build where the displaced source
    stated a value the preferred one did not, which a note only mentioned.
    """
    recipe = _contest(tmp_path)
    sorter = next(spec for spec in recipe.sources if spec.kind == "sorter")
    source = Noted()
    _note_unclaimed(sorter, source, {"core.probes": 1}, frozenset(recipe.preferred))
    assert source.notes == []


# -- R108: a preference discards no stated fact --------------------------------------------


class _Registry:
    """Enough of a writer to answer what a table declares."""

    def __init__(self, registry):
        self._registry = registry

    def spec(self, resource_id):
        declaration = self._registry["resources"].get(resource_id)
        return None if declaration is None or declaration["kind"] != "table" else declaration["table"]


def _contest(tmp_path):
    """A recipe preferring the NWB for `core.probes`, which the sorter also produces."""
    return Recipe.load(
        write(
            tmp_path,
            '\n[[source]]\nkind = "nwb"\nroot = "n"\n'
            'owns = ["core.probes"]\n'
            '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
            'owns = ["core.units"]\n' + PREFER_NWB,
        )
    )


def test_a_preference_names_a_resource_more_than_one_source_produces(tmp_path, registry):
    """Part 05 §3.3: an uncontested entry arbitrates nothing and exempts a report never due."""
    body = '\n[[source]]\nkind = "nwb"\nroot = "n"\nzone = "UTC"\n' + PREFER_NWB
    problems = [p.message for p in Recipe.load(write(tmp_path, body)).check(registry)]
    assert any("core.probes arbitrates nothing: only nwb" in m for m in problems), problems


def test_a_resource_the_recipe_prefers_nothing_for_is_not_compared(tmp_path, registry):
    """Where the rows are disjoint there is no passed-over row to weigh (Part 05 §3.4).

    A sync source's reference clock and a sorter's probe clocks are different rows of one table,
    so comparing them would report a loss that is not one.
    """
    context = Context(session_id="s001")
    context.stated["core.clocks"] = {
        "sync": [{"clock_id": "harp", "tick_rate_num": 31250}],
        "sorter": [{"clock_id": "probeA", "tick_rate_num": 30000}],
    }
    _refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))


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


TWO_DEFAULTED = '\n[[source]]\nkind = "sorter"\nroot = "s"\n\n[[source]]\nkind = "nwb"\nroot = "n"\nzone = "UTC"\n'


def test_a_preference_settles_a_resource_two_adapters_produce(tmp_path, registry):
    """Both produce core.probes; the recipe gives it to the NWB, so neither owns it twice."""
    recipe = Recipe.load(write(tmp_path, TWO_DEFAULTED + PREFER_NWB))
    owners = {s.kind: set(s.owns) for s in recipe.sources}
    assert "core.probes" in owners["nwb"] and "core.probes" not in owners["sorter"]
    assert not [p for p in recipe.check(registry) if p.level == "error"]


def test_a_resource_two_defaulted_sources_produce_is_refused_without_a_preference(tmp_path, registry):
    """Part 05 §3.4: a build holds no winner of its own, so the recipe must name one."""
    recipe = Recipe.load(write(tmp_path, TWO_DEFAULTED))
    errors = levels(recipe.check(registry)).get("error", [])
    assert any(m.startswith("core.probes is owned by 2 sources (nwb, sorter); declare a [preference]") for m in errors)


def test_a_preferred_source_owns_its_resource_whatever_its_entry_declares(tmp_path, registry):
    """Part 05 §3.3: a preference declares ownership, so a narrowed entry gains the resource."""
    body = TWO_DEFAULTED.replace('zone = "UTC"', 'zone = "UTC"\nowns = ["core.electrodes"]')
    recipe = Recipe.load(write(tmp_path, body + PREFER_NWB))
    nwb = next(s for s in recipe.sources if s.kind == "nwb")
    assert set(nwb.owns) == {"core.electrodes", "core.probes"}


@pytest.mark.parametrize(
    ("preference", "refusal"),
    [
        (
            '[preference."core.probes"]\nsource = "waveforms"\nreason = "r"\n',
            "waveforms, which this recipe does not list",
        ),
        (
            '[preference."core.units"]\nsource = "nwb"\nreason = "r"\n',
            "whose adapter does not declare it can supply it",
        ),
    ],
    ids=["unlisted", "cannot-supply"],
)
def test_a_preference_naming_a_source_that_cannot_own_it_is_refused(tmp_path, registry, preference, refusal):
    """Part 05 §3.3: an absent source, or one whose adapter cannot supply the resource, owns nothing."""
    recipe = Recipe.load(write(tmp_path, TWO_DEFAULTED + "\n" + preference))
    assert any(refusal in p.message for p in recipe.check(registry))


@pytest.mark.parametrize("declared", ["owns", "contributes"])
def test_a_preference_another_entry_contradicts_is_refused(tmp_path, registry, declared):
    """A preference says one source knows more; another entry's own claim says it supplies the resource."""
    body = TWO_DEFAULTED.replace('root = "s"', f'root = "s"\n{declared} = ["core.probes"]')
    recipe = Recipe.load(write(tmp_path, body + PREFER_NWB))
    assert any("source sorter declares it under owns or contributes" in p.message for p in recipe.check(registry))


def test_a_kind_listed_twice_is_refused(tmp_path, registry):
    """Part 05 §3.1: a source is named by its kind, so two entries of one kind are indistinguishable."""
    body = '\n[[source]]\nkind = "harp"\nroot = "a"\n\n[[source]]\nkind = "harp"\nroot = "b"\n'
    recipe = Recipe.load(write(tmp_path, body))
    assert any(p.message.startswith("source harp is listed 2 times") for p in recipe.check(registry))


@pytest.mark.parametrize(
    ("body", "where"),
    [
        ("\n[bogus]\nx = 1\n", "Additional properties are not allowed ('bogus'"),
        (
            '\n[[source]]\nkind = "sorter"\nroot = "s"\n[source.delivery]\ncommand = "run it"\n',
            "source/0/delivery/command",
        ),
        ('\n[preference."core.probes"]\nsource = "nwb"\n', "'reason' is a required property"),
        ('\n[preference."core.probes"]\nsource = "nwb"\nreason = " "\n', "preference/core.probes/reason"),
    ],
    ids=["unknown-block", "string-command", "no-reason", "blank-reason"],
)
def test_a_recipe_failing_the_schema_is_refused_on_load(tmp_path, body, where):
    """Part 05 §3.1: a misspelled block is refused rather than dropped, before any source opens."""
    with pytest.raises(ValueError, match="not a recipe") as refused:
        Recipe.load(write(tmp_path, body))
    assert where in str(refused.value)


def test_a_defaulted_entry_contributes_and_does_not_own_what_it_lists_under_contributes(tmp_path, registry):
    """Part 05 §3.4: an entry's own `contributes` is a contribution, whatever the default reads."""
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\ncontributes = ["core.units"]\n'
    spec = Recipe.load(write(tmp_path, body)).sources[0]
    assert "core.units" in spec.contributes and "core.units" not in spec.owns


def test_a_partly_supplied_resource_is_contributed_not_owned(tmp_path, registry):
    """The sorter declares core.clocks as supplied in part, so a default contributes rather than owns."""
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


def test_an_override_with_no_reason_is_refused(tmp_path):
    """Part 05 §3.6: a bare marker would silence a difference without saying why."""
    body = '\n[overrides]\n"subject.subject_id" = "   "\n' + NWB
    with pytest.raises(ValueError, match="overrides/subject.subject_id"):
        Recipe.load(write(tmp_path, body))


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


def test_an_adapter_contributing_what_it_does_not_produce_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: a partly supplied resource is one the adapter supplies at all."""
    from escapewheel_writer import sources

    class Overreaching:
        PRODUCES = frozenset({"core.units"})
        CONTRIBUTES = frozenset({"core.clocks"})
        STATES: ClassVar[dict[str, str]] = {}

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Overreaching)
    problems = levels(Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry))
    assert "sorter contributes core.clocks, which its produces does not name" in problems.get("error", [])


# -- an extension declares an encoding where the writer can read it without importing it ------


@pytest.mark.parametrize(
    "entry",
    ['{ encoding = "sideways", reason = "no such thing" }', '{ encoding = "plain", reason = "" }'],
    ids=["unknown-choice", "empty-reason"],
)
def test_an_encoding_declaration_needs_a_choice_and_a_reason(tmp_path, entry):
    """An extension reaches the writer across a file, so it declares in the recipe, with a reason.

    The reason is what makes the entry re-judgeable: an encoding is a fact about one packet's
    values, so a bare choice cannot be checked against the next session's data.
    """
    with pytest.raises(ValueError, match="encoding/aind_unit_qc.metrics.silhouette"):
        Recipe.load(write(tmp_path, f'\n[encoding]\n"aind_unit_qc.metrics.silhouette" = {entry}\n'))


def test_an_encoding_declaration_names_a_declared_column(tmp_path):
    """The registries are what know the columns, so this waits for them rather than for the schema."""
    recipe = Recipe.load(
        write(
            tmp_path,
            """
[encoding]
"aind_unit_qc.metrics.num_spikes_used" = { encoding = "delta", reason = "climbs with the spike count; 1.7x" }
"aind_unit_qc.metrics.presence" = { encoding = "plain", reason = "r" }
""",
        )
    )
    found = recipe.encoding_problems({"aind_unit_qc.metrics": {"columns": [{"name": "num_spikes_used"}]}})
    assert found == ["[encoding] aind_unit_qc.metrics.presence names no column of aind_unit_qc.metrics"]


def test_an_encoding_declaration_reaches_the_writer(tmp_path):
    """`resource.column` splits at the last dot, a resource ID being dotted itself."""
    recipe = Recipe.load(
        write(
            tmp_path,
            """
[encoding]
"aind_unit_qc.metrics.num_spikes_used" = { encoding = "delta", reason = "1.7x" }
""",
        )
    )
    assert _encoding_exceptions(recipe)["delta"] == {"aind_unit_qc.metrics": ("num_spikes_used",)}


# -- a source the build does not import (Part 03 §11) ---------------------------------------


def declaration_for(tmp_path, **fields):
    """Write an adapter's declaration document and return its path, relative to the recipe."""
    import json

    document = {
        "kind": "thermistor",
        "protocols": ["stream-v0.1"],
        "produces": ["core.devices"],
        "contributes": [],
        "states": [],
        "needs": ["root", "session_id", "sample_rate_hz"],
        "accepts": [],
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
    assert spec.delivery.report_path == tmp_path / "reports/thermistor.json"


def test_a_recipe_naming_no_protocol_reaches_the_adapter_by_one_it_declares(tmp_path):
    """Part 03 §11.1: the adapter's first declared, and only that protocol's terms are supplied."""
    from escapewheel_writer.delivery import _protocol_supplies
    from escapewheel_writer.recipe import reached_by

    named = declaration_for(tmp_path, protocols=["flight-v0.1", "files-v0.1"])
    (spec,) = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named))).sources
    assert spec.delivery.protocol == ""
    assert reached_by(spec) == "flight-v0.1"
    assert set(_protocol_supplies("flight-v0.1", tmp_path, tmp_path / "report.json")) == {"socket"}


def test_a_recipe_naming_a_protocol_its_adapter_does_not_declare_is_refused(tmp_path, registry):
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        "[source.delivery]", '[source.delivery]\nprotocol = "flight-v0.1"'
    )
    problems = [p.message for p in Recipe.load(write(tmp_path, body)).check(registry)]
    assert "thermistor names protocol 'flight-v0.1', which its adapter does not declare (stream-v0.1)" in problems


def test_a_source_run_in_process_is_reached_by_no_protocol(tmp_path):
    """In process there is no boundary, so no protocol and none of its terms (Part 03 §11.2)."""
    from escapewheel_writer.recipe import reached_by

    (spec,) = Recipe.load(write(tmp_path, '[[source]]\nkind = "sorter"\nroot = "."\n')).sources
    assert reached_by(spec) is None


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


def test_a_declaration_contributing_what_it_does_not_produce_is_refused(tmp_path, registry):
    """Part 03 §11.5: the document form of the sixth fact is checked as the class form is."""
    named = declaration_for(tmp_path, contributes=["core.clocks"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any("contributes core.clocks, which its produces does not name" in p.message for p in recipe.check(registry))


def test_a_declaration_naming_a_protocol_outside_the_group_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, protocols=["carrier-pigeon-v1.0"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any("in no group" in p.message for p in recipe.check(registry))


def test_a_declaration_whose_shape_is_wrong_is_reported_where_it_is_wrong(tmp_path, registry):
    """The schema checks the shape; what the declaration says is checked against the registry."""
    named = declaration_for(tmp_path, protocols=["carrier pigeon"])
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


@pytest.mark.parametrize(
    ("accepted", "refusal"),
    [
        ("root", "a term a build fills"),
        ("sample_rate_hz", "both optional and required"),
    ],
)
def test_an_accepted_name_a_build_cannot_honor_is_refused(tmp_path, registry, accepted, refusal):
    """Part 03 §11.5: an option cannot be a term, nor both accepted and needed."""
    named = declaration_for(tmp_path, accepts=[accepted])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any(refusal in p.message for p in recipe.check(registry))


@pytest.mark.parametrize(
    "member", ["kind", "protocols", "produces", "contributes", "states", "needs", "accepts", "consumes"]
)
def test_a_document_missing_a_member_is_refused(tmp_path, registry, member):
    """Part 03 §11.5: all eight are required, so an absent one has no reading to fall back on."""
    import json

    named = declaration_for(tmp_path)
    document = json.loads((tmp_path / named).read_text())
    del document[member]
    (tmp_path / named).write_text(json.dumps(document))
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any(f"'{member}' is a required property" in p.message for p in recipe.check(registry))


def test_a_document_carrying_a_single_protocol_is_refused(tmp_path, registry):
    import json

    named = declaration_for(tmp_path)
    document = json.loads((tmp_path / named).read_text())
    document["protocol"] = document.pop("protocols")[0]
    (tmp_path / named).write_text(json.dumps(document))
    messages = [p.message for p in Recipe.load(write(tmp_path, DELIVERED.format(declaration=named))).check(registry)]
    assert any("'protocols' is a required property" in m for m in messages), messages


@pytest.mark.parametrize("protocols", [[], ["stream-v0.1", "stream-v0.1"]], ids=["empty", "repeated"])
def test_a_document_declaring_no_protocol_or_one_twice_is_refused(tmp_path, registry, protocols):
    named = declaration_for(tmp_path, protocols=protocols)
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert any("thermistor.json: protocols" in p.message for p in recipe.check(registry))


def test_a_document_declaring_every_member_empty_is_sound(tmp_path, registry):
    """An empty array declares none, which is a declaration and not an omission."""
    named = declaration_for(tmp_path, produces=[], needs=[])
    body = DELIVERED.format(declaration=named).replace("sample_rate_hz = 1000\n", "")
    recipe = Recipe.load(write(tmp_path, body))
    assert not [p for p in recipe.check(registry) if p.level == "error" and "thermistor" in p.message]


class Registered:
    """An adapter another distribution registers, whose class a build checks as its document."""

    PROTOCOLS = ("stream-v0.1",)
    PRODUCES = frozenset({"core.devices"})
    CONTRIBUTES = frozenset({"core.devices"})
    STATES: ClassVar[dict[str, str]] = {}
    NEEDS = ("root", "session_id")
    ACCEPTS: tuple[str, ...] = ()
    CONSUMES: tuple[str, ...] = ()


def _registered(monkeypatch, tmp_path, registry, **attributes):
    from escapewheel_writer import sources

    adapter = type("Thermistor", (Registered,), attributes)
    monkeypatch.setattr(sources, "discovered", lambda: {"thermistor": adapter})
    body = '[[source]]\nkind = "thermistor"\nroot = "."\nin_process = true\n'
    return [p.message for p in Recipe.load(write(tmp_path, body)).check(registry) if p.level == "error"]


def test_a_sound_registered_class_is_refused_for_nothing(monkeypatch, tmp_path, registry):
    assert not [m for m in _registered(monkeypatch, tmp_path, registry) if m.startswith("thermistor")]


def test_a_registered_class_run_in_process_is_reached_by_no_protocol(monkeypatch, tmp_path, registry):
    """In process there is no boundary, whatever the adapter declares (Part 03 §11.1)."""
    from escapewheel_writer.recipe import reached_by

    _registered(monkeypatch, tmp_path, registry)
    (spec,) = Recipe.load(tmp_path / "session.toml").sources
    assert spec.in_process and reached_by(spec) is None


@pytest.mark.parametrize(
    ("attributes", "refusal"),
    [
        ({"PROTOCOLS": ()}, "thermistor declares no protocol; an adapter released independently"),
        ({"PRODUCES": frozenset({"core.devices", "core.tirals"})}, "no loaded registry declares"),
        ({"ACCEPTS": ("units",)}, "a term a build fills"),
        ({"NEEDS": ("root", "session_id", "Sample Rate")}, "thermistor declaration: needs/2"),
    ],
    ids=["no-protocol", "undeclared-resource", "term-accepted", "malformed-name"],
)
def test_a_registered_class_is_refused_as_its_document_would_be(monkeypatch, tmp_path, registry, attributes, refusal):
    """Part 03 §11.5: a class run in process is checked, and on the same terms as a document."""
    assert any(refusal in m for m in _registered(monkeypatch, tmp_path, registry, **attributes))


def test_a_shipped_class_may_declare_no_protocol(tmp_path, registry):
    body = '[[source]]\nkind = "sorter"\nroot = "."\n'
    problems = Recipe.load(write(tmp_path, body)).check(registry)
    assert not [p for p in problems if "protocol" in p.message or "declaration:" in p.message]


def test_a_shipped_adapter_served_over_a_protocol_outside_the_group_is_refused(tmp_path, registry):
    body = """
[[source]]
kind = "sorter"
root = "."

[source.delivery]
protocol = "carrier-pigeon-v1.0"
command = ["escapewheel", "deliver", "sorter"]
"""
    problems = [p.message for p in Recipe.load(write(tmp_path, body)).check(registry)]
    assert "sorter names protocol 'carrier-pigeon-v1.0', which is in no group this profile names" in problems


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

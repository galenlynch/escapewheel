"""The session recipe: parsing, and the checks the registry makes possible before any I/O."""

from __future__ import annotations

from typing import ClassVar

import pytest

from escapewheel_writer.errors import (
    RecipeFault,
    RecipeUnreadable,
    RecipeUnsound,
    SourceDefect,
    SourceFault,
    SourcesNotOrdered,
)
from escapewheel_writer.facts import refuse_a_discarded_fact
from escapewheel_writer.notes import NoteCode, codes
from escapewheel_writer.notes import coded as noted
from escapewheel_writer.recipe import RECIPE_SUPPLIES, Recipe
from escapewheel_writer.session import Context, grouped_encoding_exceptions, note_unclaimed
from escapewheel_writer.sources import ADAPTERS
from escapewheel_writer.sourcing import order

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


def coded(problems, code, level=None):
    """The problems carrying one code, at one level where given."""
    return [p for p in problems if p.code is code and level in (None, p.level)]


def messages(problems, level):
    """The messages reported at one level."""
    return [p.message for p in problems if p.level == level]


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
    """Part 12 §3's test is the release boundary. A built-in ships with this package and is
    upgraded with it, so in process is its only route and there is nothing to declare; a kind
    another distribution registers moves on its own schedule and must say how it can be reached."""
    registry = {"resources": {"core.units": {"kind": "table", "table": {"columns": [], "rules": []}}}}

    built_in = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'))
    assert not coded(built_in.check(registry), RecipeFault.NO_ROUTE)

    registered = write(tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\n', "reg.toml")
    (unreached,) = coded(Recipe.load(registered).check(registry), RecipeFault.NO_ROUTE)
    assert "vr_sites" in unreached.message

    opted = write(tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\nin_process = true\n', "opt.toml")
    assert not coded(Recipe.load(opted).check(registry), RecipeFault.NO_ROUTE)

    delivered = write(
        tmp_path,
        '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\n'
        '\n[source.delivery]\nprotocol = "stream-v0.1"\ncommand = ["vr-sites-adapter"]\n',
        "delivered.toml",
    )
    assert not coded(Recipe.load(delivered).check(registry), RecipeFault.NO_ROUTE)


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
    (undefined,) = coded(recipe.check(registry), RecipeFault.UNDEFINED_RESOURCE)
    assert "core.nonsense" in undefined.message


def test_two_owners_of_one_resource_is_an_error(tmp_path, registry):
    """The failure this exists to prevent: last writer wins, silently."""
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.probes"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = ["core.probes"]\n'
    )
    assert coded(recipe_problems(tmp_path, body, registry), RecipeFault.SEVERAL_OWNERS, "error")


def test_two_contributors_to_one_resource_is_allowed(tmp_path, registry):
    """`core.clocks` is the real case: per-stream clocks and the rig clock they anchor to."""
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\ncontributes = ["core.clocks"]\n'
        '\n[[source]]\nkind = "sync"\nroot = "."\nowns = []\ncontributes = ["core.clocks"]\n'
    )
    problems = recipe_problems(tmp_path, body, registry)
    assert not any("core.clocks" in m for m in messages(problems, "error"))


def test_owning_what_another_source_also_supplies_is_an_error(tmp_path, registry):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.clocks"]\n'
        '\n[[source]]\nkind = "sync"\nroot = "."\nowns = []\ncontributes = ["core.clocks"]\n'
    )
    assert coded(recipe_problems(tmp_path, body, registry), RecipeFault.OWNED_AND_SUPPLIED, "error")


def test_a_reference_clock_that_is_not_declared_is_caught(tmp_path, registry):
    path = tmp_path / "s.toml"
    path.write_text(BASE.replace('reference_clock_id = "harp"', 'reference_clock_id = "nope"'))
    assert coded(Recipe.load(path).check(registry), RecipeFault.REFERENCE_CLOCK_UNDECLARED)


def test_a_parent_clock_that_is_not_declared_is_caught(tmp_path, registry):
    body = (
        '\n[[clock]]\nclock_id = "probe"\nname = "p"\ntick_rate_num = 30000\norigin = "x"\nparent_clock_id = "gone"\n'
    )
    (orphaned,) = coded(Recipe.load(write(tmp_path, body)).check(registry), RecipeFault.PARENT_CLOCK_UNDECLARED)
    assert "'gone'" in orphaned.message


def test_a_materializer_parameter_it_does_not_take_is_refused(tmp_path, registry):
    """Materialization runs at commit, so an unknown parameter would otherwise fail the build last."""
    body = '\n[[materialize]]\nresource = "analysis.spike_events"\nreference = "harp"\nbucket_seconds = 300\n'
    (refused,) = (p for p in recipe_problems(tmp_path, body, registry) if p.level == "error")
    assert refused.code is RecipeFault.MATERIALIZE_PARAMETER
    assert "analysis.spike_events sets 'reference'" in refused.message


def test_a_resource_nothing_materializes_is_refused(tmp_path, registry):
    body = '\n[[materialize]]\nresource = "analysis.array_assets"\n'
    (refused,) = (p for p in recipe_problems(tmp_path, body, registry) if p.level == "error")
    assert refused.code is RecipeFault.NO_MATERIALIZER
    assert "analysis.array_assets" in refused.message


def test_a_materializer_parameter_it_takes_is_sound(tmp_path, registry):
    body = '\n[[materialize]]\nresource = "analysis.spike_events"\nbucket_seconds = 300\n'
    assert not messages(recipe_problems(tmp_path, body, registry), "error")


def recipe_problems(tmp_path, body, registry):
    """Check a recipe body and return its problems."""
    return Recipe.load(write(tmp_path, body)).check(registry)


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
    with pytest.raises(SourcesNotOrdered) as refused:
        order(Recipe.load(write(tmp_path, body)))
    assert (refused.value.kinds, refused.value.missing) == (("nwb",), ("sorter",))


def test_a_dependency_cycle_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(ADAPTERS["sorter"], "CONSUMES", ("nwb",))
    body = '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = []\n\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'
    with pytest.raises(SourcesNotOrdered) as refused:
        order(Recipe.load(write(tmp_path, body)))
    assert (refused.value.kinds, refused.value.missing) == (("nwb", "sorter"), ())


def test_a_required_option_is_reported_not_crashed_on(tmp_path):
    """`build_source` pops `zone` for the nwb kind, so a recipe without one used to die there
    with a KeyError after --check had called the recipe sound.

    What makes it reportable is the adapter's own `NEEDS` (Part 05 §3.4): `zone` resolves to no
    term, so it falls through to the recipe's options and the entry has to carry it.
    """
    from escapewheel_writer.kinds import needs
    from escapewheel_writer.recipe import Recipe

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
    (unset,) = coded(problems, RecipeFault.OPTION_UNSET)
    assert "'zone'" in unset.message


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
    assert not coded(problems, RecipeFault.OPTION_UNSET)


class Noted:
    """The one thing `note_unclaimed` needs of a source: somewhere to put a note."""

    def __init__(self) -> None:
        self.notes: list[str] = []


def test_a_produced_resource_no_source_claims_is_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 19_061})
    assert codes(source.notes) == [NoteCode.UNCLAIMED_DISCARDED]
    assert "core.unit_quality_labels (19,061 rows)" in source.notes[0]


def test_a_resource_the_recipe_prefers_another_source_for_is_not_noted(tmp_path):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\n' + PREFER_NWB
    )
    recipe = Recipe.load(write(tmp_path, body))
    source = Noted()
    # The sorter offers core.probes too; the recipe gives it to the NWB, so losing it here is the
    # design rather than an omission.
    note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.probes": 10}, frozenset(recipe.preferred))
    assert source.notes == []


def test_a_resource_another_source_owns_is_noted_where_the_recipe_prefers_none(tmp_path):
    """Part 05 §3.4: without a preference the two sources are producing different rows."""
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\n'
    )
    recipe = Recipe.load(write(tmp_path, body))
    source = Noted()
    note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.probes": 10}, frozenset(recipe.preferred))
    assert any("core.probes (10 rows)" in n for n in noted(source.notes, NoteCode.UNCLAIMED_DISCARDED))


def test_an_empty_unclaimed_resource_is_not_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 0})
    assert source.notes == []


def test_what_the_recipe_itself_supplies_is_not_noted(tmp_path):
    recipe = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    # RECIPE_SUPPLIES: the recipe writes these, so a source producing them loses to it by design.
    note_unclaimed(recipe.sources[0], source, {"core.processing_runs": 2, "core.sessions": 1})
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
    note_unclaimed(recipe.sources[0], source, {"core.clock_observation_intervals": 12})
    (discarded,) = noted(source.notes, NoteCode.UNCLAIMED_DISCARDED)
    assert "core.clock_observation_intervals" in discarded


def test_a_preferred_resource_draws_a_refusal_rather_than_a_note(tmp_path):
    """Part 05 §3.4 replaces the note for a preferred resource with something stronger.

    A preference exempts a resource from Part 05 §3.4's report. What makes that sound is not the
    silence but the refusal: `refuse_a_discarded_fact` fails the build where the displaced source
    stated a value the preferred one did not, which a note only mentioned.
    """
    recipe = _contest(tmp_path)
    sorter = next(spec for spec in recipe.sources if spec.kind == "sorter")
    source = Noted()
    note_unclaimed(sorter, source, {"core.probes": 1}, frozenset(recipe.preferred))
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
    (idle,) = coded(Recipe.load(write(tmp_path, body)).check(registry), RecipeFault.PREFERENCE_IDLE)
    assert "core.probes" in idle.message and "only nwb" in idle.message


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
    refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))


def test_a_preference_that_discards_a_stated_fact_is_refused(tmp_path, registry):
    """Part 05 §3.4: the premise a preference buys silence on is now checked."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {
        "nwb": [{"probe_id": "probeA", "probe_type": None}],
        "sorter": [{"probe_id": "probeA", "probe_type": "NP2000"}],
    }
    with pytest.raises(SourceDefect) as refused:
        refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))
    assert refused.value.code is SourceFault.FACT_DISCARDED
    assert "core.probes.probe_type" in str(refused.value)


def test_a_preferred_source_that_stages_nothing_is_refused(tmp_path, registry):
    """Part 05 §3.4's limiting case: every value discarded, not just one."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {"sorter": [{"probe_id": "probeA"}]}
    context.stated["core.probes"]["nwb"] = []
    with pytest.raises(SourceDefect) as refused:
        refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))
    assert refused.value.code is SourceFault.FACT_DISCARDED
    assert "staged none" in str(refused.value)


def test_two_sources_that_agree_are_not_refused(tmp_path, registry):
    """Agreement is the ordinary case, and `metadata` is never compared (Part 05 §3.4)."""
    context = Context(session_id="s001")
    context.stated["core.probes"] = {
        "nwb": [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"a": 1}'}],
        "sorter": [{"probe_id": "probeA", "probe_type": "NP2000", "metadata": '{"b": 2}'}],
    }
    refuse_a_discarded_fact(_Registry(registry), context, _contest(tmp_path))


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
    contested = coded(recipe.check(registry), RecipeFault.SEVERAL_OWNERS, "error")
    assert any(p.message.startswith("core.probes is owned by 2 sources (nwb, sorter)") for p in contested)


def test_a_preferred_source_owns_its_resource_whatever_its_entry_declares(tmp_path, registry):
    """Part 05 §3.3: a preference declares ownership, so a narrowed entry gains the resource."""
    body = TWO_DEFAULTED.replace('zone = "UTC"', 'zone = "UTC"\nowns = ["core.electrodes"]')
    recipe = Recipe.load(write(tmp_path, body + PREFER_NWB))
    nwb = next(s for s in recipe.sources if s.kind == "nwb")
    assert set(nwb.owns) == {"core.electrodes", "core.probes"}


@pytest.mark.parametrize(
    ("preference", "fault"),
    [
        ('[preference."core.probes"]\nsource = "waveforms"\nreason = "r"\n', RecipeFault.PREFERENCE_UNLISTED),
        ('[preference."core.units"]\nsource = "nwb"\nreason = "r"\n', RecipeFault.PREFERENCE_UNPRODUCED),
    ],
    ids=["unlisted", "cannot-supply"],
)
def test_a_preference_naming_a_source_that_cannot_own_it_is_refused(tmp_path, registry, preference, fault):
    """Part 05 §3.3: an absent source, or one whose adapter cannot supply the resource, owns nothing."""
    recipe = Recipe.load(write(tmp_path, TWO_DEFAULTED + "\n" + preference))
    assert coded(recipe.check(registry), fault, "error")


@pytest.mark.parametrize("declared", ["owns", "contributes"])
def test_a_preference_another_entry_contradicts_is_refused(tmp_path, registry, declared):
    """A preference says one source knows more; another entry's own claim says it supplies the resource."""
    body = TWO_DEFAULTED.replace('root = "s"', f'root = "s"\n{declared} = ["core.probes"]')
    recipe = Recipe.load(write(tmp_path, body + PREFER_NWB))
    (contradicted,) = coded(recipe.check(registry), RecipeFault.PREFERENCE_CONTRADICTED)
    assert "source sorter" in contradicted.message


def test_a_kind_listed_twice_is_refused(tmp_path, registry):
    """Part 05 §3.1: a source is named by its kind, so two entries of one kind are indistinguishable."""
    body = '\n[[source]]\nkind = "harp"\nroot = "a"\n\n[[source]]\nkind = "harp"\nroot = "b"\n'
    recipe = Recipe.load(write(tmp_path, body))
    (repeated,) = coded(recipe.check(registry), RecipeFault.REPEATED_KIND)
    assert repeated.message.startswith("source harp is listed 2 times")


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
    with pytest.raises(RecipeUnreadable) as refused:
        Recipe.load(write(tmp_path, body))
    assert {p.code for p in refused.value.problems} == {RecipeFault.RECIPE_SHAPE}
    assert any(where in p.message for p in refused.value.problems)


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
    said = Recipe.load(write(tmp_path, body)).check(registry)
    assert any("core.unit_quality_labels" in p.message for p in coded(said, RecipeFault.UNCLAIMED, "warning"))
    # Narrowing this far also dangles required foreign keys, which is a separate finding and
    # the reason the unclaimed report is a warning rather than one more error.
    dangling = coded(said, RecipeFault.DANGLING_REFERENCE, "error")
    assert any("core.curation_versions" in p.message for p in dangling)


def test_what_a_source_produces_is_what_it_can_emit():
    """R63 §4: a PRODUCES that drifts from the code reintroduces the defect one level up."""
    from escapewheel_writer.sources import ADAPTERS

    for kind, adapter in ADAPTERS.items():
        declared = set(getattr(adapter, "PRODUCES", ()))
        assert declared, f"{kind} declares no PRODUCES (Part 05 §3.4)"
        assert all(r.count(".") == 1 for r in declared), f"{kind} declares a malformed resource ID"


# -- R87: authority for a declared fact ------------------------------------------------------

NWB = '\n[[source]]\nkind = "nwb"\nroot = "s"\nzone = "UTC"\nowns = ["core.probes"]\n'


def test_a_declared_fact_a_source_states_is_reported_before_any_io(tmp_path, registry):
    """Part 05 §3.5. The base recipe declares `[subject].subject_id` and the NWB states it."""
    compared = coded(Recipe.load(write(tmp_path, NWB)).check(registry), RecipeFault.FACT_COMPARED, "warning")
    assert any(p.message.startswith("subject.subject_id is declared and nwb") for p in compared)


def test_an_override_is_recorded_rather_than_warned(tmp_path, registry):
    """Part 05 §3.5: a field an override covers is information; the build will apply it."""
    body = '\n[overrides]\n"subject.subject_id" = "the file names the wrong animal"\n' + NWB
    problems = Recipe.load(write(tmp_path, body)).check(registry)
    applied = coded(problems, RecipeFault.OVERRIDE_APPLIED, "info")
    assert any(p.message.startswith("subject.subject_id is declared and overrides nwb") for p in applied)
    assert not any(p.message.startswith("subject.subject_id") for p in coded(problems, RecipeFault.FACT_COMPARED))


def test_an_override_with_no_reason_is_refused(tmp_path):
    """Part 05 §3.6: a bare marker would silence a difference without saying why."""
    body = '\n[overrides]\n"subject.subject_id" = "   "\n' + NWB
    with pytest.raises(RecipeUnreadable) as refused:
        Recipe.load(write(tmp_path, body))
    (problem,) = refused.value.problems
    assert problem.code is RecipeFault.RECIPE_SHAPE
    assert problem.message.startswith("overrides/subject.subject_id")


def test_an_override_of_a_fact_nothing_states_is_reported_not_refused(tmp_path, registry):
    """Part 05 §3.6: a stale override leaves the packet correct, so it costs a line of the log."""
    body = (
        '\n[overrides]\n"subject.subject_id" = "why"\n'
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
    )
    problems = Recipe.load(write(tmp_path, body)).check(registry)
    assert [p.level for p in coded(problems, RecipeFault.OVERRIDE_IDLE)] == ["warning"]


def test_a_source_that_cannot_say_what_it_states_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: an adapter declaring nothing must not read as one that states nothing."""
    from escapewheel_writer import sources

    class Mute:
        PRODUCES = frozenset({"core.units"})

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Mute)
    problems = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry)
    assert coded(problems, RecipeFault.STATES_UNDECLARED, "error")


def test_a_stated_fact_with_no_accessor_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: the declaration is checked against the class, so it cannot drift unseen."""
    from escapewheel_writer import sources

    class Absent:
        PRODUCES = frozenset({"core.units"})
        STATES: ClassVar[dict[str, str]] = {"subject.subject_id": "nowhere"}

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Absent)
    problems = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry)
    (unexposed,) = coded(problems, RecipeFault.STATE_UNEXPOSED, "error")
    assert "'nowhere'" in unexposed.message


def test_an_adapter_contributing_what_it_does_not_produce_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: a partly supplied resource is one the adapter supplies at all."""
    from escapewheel_writer import sources

    class Overreaching:
        PRODUCES = frozenset({"core.units"})
        CONTRIBUTES = frozenset({"core.clocks"})
        STATES: ClassVar[dict[str, str]] = {}

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Overreaching)
    problems = Recipe.load(write(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry)
    (overreached,) = coded(problems, RecipeFault.CONTRIBUTES_UNPRODUCED, "error")
    assert overreached.message.startswith("sorter contributes core.clocks")


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
    with pytest.raises(RecipeUnreadable) as refused:
        Recipe.load(write(tmp_path, f'\n[encoding]\n"aind_unit_qc.metrics.silhouette" = {entry}\n'))
    assert {p.code for p in refused.value.problems} == {RecipeFault.RECIPE_SHAPE}
    assert all(p.message.startswith("encoding/aind_unit_qc.metrics.silhouette") for p in refused.value.problems)


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
    assert grouped_encoding_exceptions(recipe)["delta"] == {"aind_unit_qc.metrics": ("num_spikes_used",)}


# -- a source the build does not import (Part 12 §2) ---------------------------------------


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
    """Part 12 §3: the adapter's first declared, and only that protocol's terms are supplied."""
    from escapewheel_writer.reading import protocol_supplies
    from escapewheel_writer.recipe import reached_by

    named = declaration_for(tmp_path, protocols=["flight-v0.1", "files-v0.1"])
    (spec,) = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named))).sources
    assert spec.delivery.protocol == ""
    assert reached_by(spec) == "flight-v0.1"
    assert set(protocol_supplies("flight-v0.1", tmp_path, tmp_path, tmp_path / "report.json")) == {"socket"}


def test_a_recipe_naming_a_protocol_its_adapter_does_not_declare_is_refused(tmp_path, registry):
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        "[source.delivery]", '[source.delivery]\nprotocol = "flight-v0.1"'
    )
    (undeclared,) = coded(Recipe.load(write(tmp_path, body)).check(registry), RecipeFault.PROTOCOL_UNDECLARED)
    assert "thermistor names protocol 'flight-v0.1'" in undeclared.message


def test_a_source_run_in_process_is_reached_by_no_protocol(tmp_path):
    """In process there is no boundary, so no protocol and none of its terms (Part 12 §4)."""
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
    assert coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)


def test_a_declaration_naming_a_resource_no_registry_declares_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, produces=["core.tirals"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    (undeclared,) = coded(recipe.check(registry), RecipeFault.PRODUCES_UNDECLARED)
    assert "core.tirals" in undeclared.message


def test_a_declaration_contributing_what_it_does_not_produce_is_refused(tmp_path, registry):
    """Part 12 §7: the document form of the sixth fact is checked as the class form is."""
    named = declaration_for(tmp_path, contributes=["core.clocks"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    (overreached,) = coded(recipe.check(registry), RecipeFault.CONTRIBUTES_UNPRODUCED)
    assert "core.clocks" in overreached.message


def test_a_declaration_naming_a_protocol_outside_the_group_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, protocols=["carrier-pigeon-v1.0"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert coded(recipe.check(registry), RecipeFault.PROTOCOL_UNKNOWN)


def test_a_declaration_whose_shape_is_wrong_is_reported_where_it_is_wrong(tmp_path, registry):
    """The schema checks the shape; what the declaration says is checked against the registry."""
    named = declaration_for(tmp_path, protocols=["carrier pigeon"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    (unreadable,) = coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)
    assert "thermistor.json: protocols" in unreadable.message


def test_a_declaration_needing_what_the_recipe_does_not_set_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, needs=["root", "session_id", "calibration_uri"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    (unfilled,) = coded(recipe.check(registry), RecipeFault.NEEDS_UNFILLED)
    assert "calibration_uri" in unfilled.message


def test_an_option_no_declaration_names_is_refused(tmp_path, registry):
    """An option nothing reads is a statement about the packet that never reaches the source."""
    named = declaration_for(tmp_path, accepts=["smoothing_window"])
    body = DELIVERED.format(declaration=named).replace(
        "sample_rate_hz = 1000", "sample_rate_hz = 1000\nsmoothing_windwo = 3"
    )
    recipe = Recipe.load(write(tmp_path, body))
    (unread,) = coded(recipe.check(registry), RecipeFault.OPTION_UNREAD)
    assert "'smoothing_windwo'" in unread.message


def test_an_accepted_option_the_recipe_leaves_unset_is_not_refused(tmp_path, registry):
    """What separates the two lists: a needed name a recipe omits is refused and an accepted one is not."""
    named = declaration_for(tmp_path, accepts=["smoothing_window"])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert not [p for p in recipe.check(registry) if p.level == "error"]


@pytest.mark.parametrize(
    ("accepted", "fault"),
    [
        ("root", RecipeFault.ACCEPTS_TERM),
        ("sample_rate_hz", RecipeFault.ACCEPTS_NEEDED),
    ],
)
def test_an_accepted_name_a_build_cannot_honor_is_refused(tmp_path, registry, accepted, fault):
    """Part 12 §7: an option cannot be a term, nor both accepted and needed."""
    named = declaration_for(tmp_path, accepts=[accepted])
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    assert coded(recipe.check(registry), fault)


@pytest.mark.parametrize(
    "member", ["kind", "protocols", "produces", "contributes", "states", "needs", "accepts", "consumes"]
)
def test_a_document_missing_a_member_is_refused(tmp_path, registry, member):
    """Part 12 §7: all eight are required, so an absent one has no reading to fall back on."""
    import json

    named = declaration_for(tmp_path)
    document = json.loads((tmp_path / named).read_text())
    del document[member]
    (tmp_path / named).write_text(json.dumps(document))
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    unreadable = coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)
    assert any(f"'{member}' is a required property" in p.message for p in unreadable)


def test_a_document_carrying_a_single_protocol_is_refused(tmp_path, registry):
    import json

    named = declaration_for(tmp_path)
    document = json.loads((tmp_path / named).read_text())
    document["protocol"] = document.pop("protocols")[0]
    (tmp_path / named).write_text(json.dumps(document))
    problems = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named))).check(registry)
    (unreadable,) = coded(problems, RecipeFault.DECLARATION_UNREADABLE)
    assert "'protocols' is a required property" in unreadable.message


@pytest.mark.parametrize("protocols", [[], ["stream-v0.1", "stream-v0.1"]], ids=["empty", "repeated"])
def test_a_document_declaring_no_protocol_or_one_twice_is_refused(tmp_path, registry, protocols):
    named = declaration_for(tmp_path, protocols=protocols)
    recipe = Recipe.load(write(tmp_path, DELIVERED.format(declaration=named)))
    (unreadable,) = coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)
    assert "thermistor.json: protocols" in unreadable.message


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
    return [p for p in Recipe.load(write(tmp_path, body)).check(registry) if p.level == "error"]


def test_a_sound_registered_class_is_refused_for_nothing(monkeypatch, tmp_path, registry):
    assert not [p for p in _registered(monkeypatch, tmp_path, registry) if p.message.startswith("thermistor")]


def test_a_registered_class_run_in_process_is_reached_by_no_protocol(monkeypatch, tmp_path, registry):
    """In process there is no boundary, whatever the adapter declares (Part 12 §3)."""
    from escapewheel_writer.recipe import reached_by

    _registered(monkeypatch, tmp_path, registry)
    (spec,) = Recipe.load(tmp_path / "session.toml").sources
    assert spec.in_process and reached_by(spec) is None


@pytest.mark.parametrize(
    ("attributes", "fault", "named"),
    [
        ({"PROTOCOLS": ()}, RecipeFault.NO_PROTOCOL, "thermistor"),
        ({"PRODUCES": frozenset({"core.devices", "core.tirals"})}, RecipeFault.PRODUCES_UNDECLARED, "core.tirals"),
        ({"ACCEPTS": ("units",)}, RecipeFault.ACCEPTS_TERM, "units"),
        ({"NEEDS": ("root", "session_id", "Sample Rate")}, RecipeFault.DECLARATION_SHAPE, "needs/2"),
    ],
    ids=["no-protocol", "undeclared-resource", "term-accepted", "malformed-name"],
)
def test_a_registered_class_is_refused_as_its_document_would_be(
    monkeypatch, tmp_path, registry, attributes, fault, named
):
    """Part 12 §7: a class run in process is checked, and on the same terms as a document."""
    (refused,) = coded(_registered(monkeypatch, tmp_path, registry, **attributes), fault)
    assert named in refused.message


def test_a_shipped_class_may_declare_no_protocol(tmp_path, registry):
    body = '[[source]]\nkind = "sorter"\nroot = "."\n'
    problems = Recipe.load(write(tmp_path, body)).check(registry)
    about = {
        RecipeFault.NO_PROTOCOL,
        RecipeFault.PROTOCOL_UNKNOWN,
        RecipeFault.PROTOCOL_UNDECLARED,
        RecipeFault.DECLARATION_SHAPE,
    }
    assert not [p for p in problems if p.code in about]


def test_a_shipped_adapter_served_over_a_protocol_outside_the_group_is_refused(tmp_path, registry):
    body = """
[[source]]
kind = "sorter"
root = "."

[source.delivery]
protocol = "carrier-pigeon-v1.0"
command = ["escapewheel", "deliver", "sorter"]
"""
    (unknown,) = coded(Recipe.load(write(tmp_path, body)).check(registry), RecipeFault.PROTOCOL_UNKNOWN)
    assert "sorter names protocol 'carrier-pigeon-v1.0'" in unknown.message


def test_a_delivery_with_no_command_is_refused(tmp_path, registry):
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        'command = ["thermistor-adapter", "--verbose"]\n', ""
    )
    recipe = Recipe.load(write(tmp_path, body))
    assert coded(recipe.check(registry), RecipeFault.NO_COMMAND)


def test_a_source_is_reached_one_way_or_the_other(tmp_path, registry):
    """Part 05 §3.9: in process is the recipe's choice, and a delivery is the other choice."""
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        "sample_rate_hz = 1000", "sample_rate_hz = 1000\nin_process = true"
    )
    recipe = Recipe.load(write(tmp_path, body))
    assert coded(recipe.check(registry), RecipeFault.TWO_ROUTES)


def test_a_built_in_adapter_may_be_delivered_without_a_document(tmp_path, registry):
    """A build may serve an adapter it ships over any protocol of the group (Part 12 §3)."""
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
    refused = coded(recipe.check(registry), RecipeFault.CREDENTIAL, "error")
    assert ["storage_options.key" in p.message for p in refused] == [True, False]


def test_a_reference_to_a_credential_is_not_one(tmp_path, registry):
    """A profile names where the secret is; the environment holds it and nothing crosses."""
    recipe = Recipe.load(write(tmp_path, SIGNED.format(options='profile = "aind", anon = false')))
    assert not coded(recipe.check(registry), RecipeFault.CREDENTIAL)


def test_a_token_that_names_a_mode_is_not_a_credential(tmp_path, registry):
    """gcsfs reads a public bucket with `token = "anon"`, so the name alone does not decide."""
    mode = Recipe.load(write(tmp_path, SIGNED.format(options='token = "anon"')))
    assert not coded(mode.check(registry), RecipeFault.CREDENTIAL)
    real = Recipe.load(write(tmp_path, SIGNED.format(options='token = "ya29.a0..."'), "signed.toml"))
    assert coded(real.check(registry), RecipeFault.CREDENTIAL)


def test_what_a_run_records_carries_no_credential(tmp_path):
    """Applied wherever a recipe is written down, since one written before the refusal exists."""
    from escapewheel_writer.secrets import REDACTED, redacted

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


# -- prefix -----------------------------------------------------------------------------------


def prefixed(**by_kind):
    """Source entries of these kinds, each setting `prefix` to its value or leaving it unset for None."""
    return "".join(
        f'\n[[source]]\nkind = "{kind}"\nroot = "."\nowns = []\n' + ("" if value is None else f'prefix = "{value}"\n')
        for kind, value in by_kind.items()
    )


def prefix_refusals(tmp_path, registry, body):
    """The refusals naming a prefix disagreement."""
    return [p.message for p in coded(Recipe.load(write(tmp_path, body)).check(registry), RecipeFault.PREFIX_DISAGREES)]


def test_a_prefix_set_on_one_source_and_not_another_is_refused(tmp_path, registry):
    """`nwb` and `waveforms` name one contact through `contact_ids`; half-prefixed, it is two electrodes."""
    (refused,) = prefix_refusals(tmp_path, registry, prefixed(nwb="a.", waveforms=None))
    assert "(nwb 'a.', waveforms unset)" in refused


def test_two_different_prefixes_are_refused(tmp_path, registry):
    (refused,) = prefix_refusals(tmp_path, registry, prefixed(nwb="a.", lfp="b."))
    assert "(lfp 'b.', nwb 'a.')" in refused


def test_one_prefix_on_every_source_that_accepts_it_passes(tmp_path, registry):
    body = prefixed(sorter="a.", sync="a.", nwb="a.", lfp="a.", waveforms="a.", openephys="a.", harp="a.")
    assert prefix_refusals(tmp_path, registry, body) == []


def test_a_device_source_left_unprefixed_is_refused(tmp_path, registry):
    """An NWB probe links to an `openephys` headstage, so the two cannot disagree on the prefix."""
    (refused,) = prefix_refusals(tmp_path, registry, prefixed(nwb="a.", openephys=None, harp="a."))
    assert "(harp 'a.', nwb 'a.', openephys unset)" in refused


def test_a_source_that_takes_no_prefix_is_not_asked_for_one(tmp_path, registry):
    """A delivered source whose declaration accepts no `prefix` disagrees with nothing by leaving it unset."""
    body = prefixed(sorter="a.") + DELIVERED.format(declaration=declaration_for(tmp_path))
    assert prefix_refusals(tmp_path, registry, body) == []


def test_a_delivered_source_whose_declaration_accepts_prefix_must_agree(tmp_path, registry):
    """Whether a source takes a prefix comes from its declaration, not from a list of kinds."""
    body = prefixed(nwb="a.") + DELIVERED.format(declaration=declaration_for(tmp_path, accepts=["prefix"]))
    (refused,) = prefix_refusals(tmp_path, registry, body)
    assert "(nwb 'a.', thermistor unset)" in refused


@pytest.mark.parametrize("prefix", ["A_", "a b.", "é.", "a/"])
def test_a_prefix_a_resource_id_does_not_admit_is_refused(tmp_path, registry, prefix):
    """Part 04 §4.1: a prefix begins a minted resource ID's name, so it is refused before a build."""
    problems = Recipe.load(write(tmp_path, prefixed(sorter=prefix))).check(registry)
    (refused,) = coded(problems, RecipeFault.PREFIX_CHARACTERS)
    assert f"source 'sorter': prefix {prefix!r}" in refused.message


def test_a_build_refuses_disagreeing_prefixes_before_opening_a_source(tmp_path, registry):
    from escapewheel_writer.session import build

    recipe = Recipe.load(write(tmp_path, prefixed(sorter="a.", nwb=None).replace('root = "."', 'root = "absent"')))
    with pytest.raises(RecipeUnsound) as refused:
        build(recipe, registry)
    assert RecipeFault.PREFIX_DISAGREES in {p.code for p in refused.value.problems}
    assert not (recipe.out / "staging").exists(), "refused before anything was prepared"


PREFERRED = """
[[preferred_run]]
activity_type = "curation"
scope_kind = "core.sorting_runs"
scope = "probeA"
processing_run_name = "probeA.curation"
reason = "the manual curation"
"""


def test_two_preferred_runs_of_one_key_are_refused(tmp_path, registry):
    """Part 05 §3.5: a recipe prefers one run per activity and scope."""
    recipe = Recipe.load(write(tmp_path, PREFERRED + PREFERRED.replace("probeA.curation", "probeA.other")))
    assert recipe.preferred_runs[1]["processing_run_name"] == "probeA.other"
    assert coded(recipe.check(registry), RecipeFault.REPEATED_PREFERRED_RUN, "error")


@pytest.mark.parametrize("chosen", ["2026-09-01T00:00:00", "2026-09-01", "yesterday"])
def test_a_chosen_at_naming_no_instant_is_refused(tmp_path, registry, chosen):
    recipe = Recipe.load(
        write(tmp_path, PREFERRED + f"chosen_at = {chosen if chosen[0].isdigit() else repr(chosen)}\n")
    )
    assert coded(recipe.check(registry), RecipeFault.CHOSEN_AT_NO_INSTANT, "error")


def test_an_offset_chosen_at_is_normalized_to_utc(tmp_path, registry):
    from datetime import UTC, datetime

    from escapewheel_writer.recipe import normalized_chosen_at

    recipe = Recipe.load(write(tmp_path, PREFERRED + "chosen_at = 2026-09-01T02:00:00+02:00\n"))
    assert not coded(recipe.check(registry), RecipeFault.CHOSEN_AT_NO_INSTANT)
    assert normalized_chosen_at(recipe.preferred_runs[0]["chosen_at"]) == datetime(2026, 9, 1, tzinfo=UTC)


def test_an_amending_recipe_declares_only_its_session(tmp_path, registry):
    """Part 05 §3.5: the packet's session and subject rows prevail, so the recipe states neither."""
    body = BASE.replace('registry = "reg.json"', 'registry = "reg.json"\namends = "0.1.0"')
    path = tmp_path / "amend.toml"
    path.write_text(body + '\n[overrides]\n"subject.subject_id" = "because"\n')
    declared = coded(Recipe.load(path).check(registry), RecipeFault.AMENDING_DECLARES, "error")
    stated = " ".join(p.message for p in declared)
    for name in ("[session] reference_clock_id", "[subject] subject_id", "[overrides] subject.subject_id"):
        assert name in stated


def test_an_amended_packet_supplies_what_it_holds(tmp_path, registry):
    """Part 05 §3.5: a held table satisfies a required reference, and a held clock a parent."""
    body = '\n[[source]]\nkind = "sorter"\nroot = "sorted"\nparent_clock_id = "harp"\nowns = ["core.units"]\n'
    recipe = Recipe.load(write(tmp_path, body))
    assert coded(recipe.check(registry), RecipeFault.DANGLING_REFERENCE, "error")
    held = recipe.check(
        registry, held_tables=["core.sorting_runs", "core.curation_versions", "core.probes", "core.clocks"]
    )
    assert not coded(held, RecipeFault.DANGLING_REFERENCE, "error")

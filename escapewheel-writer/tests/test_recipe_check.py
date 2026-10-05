"""The checks of a recipe the registry makes possible before any I/O."""

from __future__ import annotations

from typing import ClassVar

import pytest

from escapewheel_writer.errors import (
    RecipeFault,
)
from escapewheel_writer.recipe import Recipe
from tests.builders import (
    DELIVERED,
    NWB_OWNING_PROBES,
    PREFER_NWB,
    RECIPE_BASE,
    TWO_DEFAULTED,
    contested_recipe,
    declaration_for,
    prefixed,
    problems_coded,
    write_recipe,
)


def messages(problems, level):
    """The messages reported at one level."""
    return [p.message for p in problems if p.level == level]


def test_a_sound_recipe_reports_nothing(tmp_path, registry):
    path = tmp_path / "sound.toml"
    path.write_text(
        RECIPE_BASE.replace('[subject]\nsubject_id = "m001"\n', "")
        + '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.subjects"]\n'
    )
    assert [str(p) for p in Recipe.load(path).check(registry) if p.level == "error"] == []


def test_an_unknown_resource_is_caught(tmp_path, registry):
    recipe = Recipe.load(
        write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.nonsense"]\n')
    )
    (undefined,) = problems_coded(recipe.check(registry), RecipeFault.UNDEFINED_RESOURCE)
    assert "core.nonsense" in undefined.message


def test_two_owners_of_one_resource_is_an_error(tmp_path, registry):
    """The failure this exists to prevent: last writer wins, silently."""
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = ["core.probes"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "."\nowns = ["core.probes"]\n'
    )
    assert problems_coded(recipe_problems(tmp_path, body, registry), RecipeFault.SEVERAL_OWNERS, "error")


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
    assert problems_coded(recipe_problems(tmp_path, body, registry), RecipeFault.OWNED_AND_SUPPLIED, "error")


def test_a_reference_clock_that_is_not_declared_is_caught(tmp_path, registry):
    path = tmp_path / "s.toml"
    path.write_text(RECIPE_BASE.replace('reference_clock_id = "harp"', 'reference_clock_id = "nope"'))
    assert problems_coded(Recipe.load(path).check(registry), RecipeFault.REFERENCE_CLOCK_UNDECLARED)


def test_a_parent_clock_that_is_not_declared_is_caught(tmp_path, registry):
    body = (
        '\n[[clock]]\nclock_id = "probe"\nname = "p"\ntick_rate_num = 30000\norigin = "x"\nparent_clock_id = "gone"\n'
    )
    (orphaned,) = problems_coded(
        Recipe.load(write_recipe(tmp_path, body)).check(registry), RecipeFault.PARENT_CLOCK_UNDECLARED
    )
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
    return Recipe.load(write_recipe(tmp_path, body)).check(registry)


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
    (unset,) = problems_coded(problems, RecipeFault.OPTION_UNSET)
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
    assert not problems_coded(problems, RecipeFault.OPTION_UNSET)


def test_a_preference_names_a_resource_more_than_one_source_produces(tmp_path, registry):
    """Part 05 §3.3: an uncontested entry arbitrates nothing and exempts a report never due."""
    body = '\n[[source]]\nkind = "nwb"\nroot = "n"\nzone = "UTC"\n' + PREFER_NWB
    (idle,) = problems_coded(Recipe.load(write_recipe(tmp_path, body)).check(registry), RecipeFault.PREFERENCE_IDLE)
    assert "core.probes" in idle.message and "only nwb" in idle.message


def test_a_preference_settles_a_resource_two_adapters_produce(tmp_path, registry):
    """Both produce core.probes; the recipe gives it to the NWB, so neither owns it twice."""
    recipe = Recipe.load(write_recipe(tmp_path, TWO_DEFAULTED + PREFER_NWB))
    owners = {s.kind: set(s.owns) for s in recipe.sources}
    assert "core.probes" in owners["nwb"] and "core.probes" not in owners["sorter"]
    assert not [p for p in recipe.check(registry) if p.level == "error"]


def test_a_resource_two_defaulted_sources_produce_is_refused_without_a_preference(tmp_path, registry):
    """Part 05 §3.4: a build holds no winner of its own, so the recipe must name one."""
    recipe = Recipe.load(write_recipe(tmp_path, TWO_DEFAULTED))
    contested = problems_coded(recipe.check(registry), RecipeFault.SEVERAL_OWNERS, "error")
    assert any(p.message.startswith("core.probes is owned by 2 sources (nwb, sorter)") for p in contested)


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
    recipe = Recipe.load(write_recipe(tmp_path, TWO_DEFAULTED + "\n" + preference))
    assert problems_coded(recipe.check(registry), fault, "error")


@pytest.mark.parametrize("declared", ["owns", "contributes"])
def test_a_preference_another_entry_contradicts_is_refused(tmp_path, registry, declared):
    """A preference says one source knows more; another entry's own claim says it supplies the resource."""
    body = TWO_DEFAULTED.replace('root = "s"', f'root = "s"\n{declared} = ["core.probes"]')
    recipe = Recipe.load(write_recipe(tmp_path, body + PREFER_NWB))
    (contradicted,) = problems_coded(recipe.check(registry), RecipeFault.PREFERENCE_CONTRADICTED)
    assert "source sorter" in contradicted.message


def test_a_kind_listed_twice_is_refused(tmp_path, registry):
    """Part 05 §3.1: a source is named by its kind, so two entries of one kind are indistinguishable."""
    body = '\n[[source]]\nkind = "harp"\nroot = "a"\n\n[[source]]\nkind = "harp"\nroot = "b"\n'
    recipe = Recipe.load(write_recipe(tmp_path, body))
    (repeated,) = problems_coded(recipe.check(registry), RecipeFault.REPEATED_KIND)
    assert repeated.message.startswith("source harp is listed 2 times")


def test_a_resource_no_source_claims_is_a_warning(tmp_path, registry):
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
    said = Recipe.load(write_recipe(tmp_path, body)).check(registry)
    assert any("core.unit_quality_labels" in p.message for p in problems_coded(said, RecipeFault.UNCLAIMED, "warning"))
    # Narrowing this far also dangles required foreign keys, which is a separate finding and
    # the reason the unclaimed report is a warning rather than one more error.
    dangling = problems_coded(said, RecipeFault.DANGLING_REFERENCE, "error")
    assert any("core.curation_versions" in p.message for p in dangling)


def test_a_declared_fact_a_source_states_is_reported_before_any_io(tmp_path, registry):
    """Part 05 §3.5. The base recipe declares `[subject].subject_id` and the NWB states it."""
    compared = problems_coded(
        Recipe.load(write_recipe(tmp_path, NWB_OWNING_PROBES)).check(registry), RecipeFault.FACT_COMPARED, "warning"
    )
    assert any(p.message.startswith("subject.subject_id is declared and nwb") for p in compared)


def test_an_override_is_recorded_rather_than_warned(tmp_path, registry):
    """Part 05 §3.5: a field an override covers is information; the build will apply it."""
    body = '\n[overrides]\n"subject.subject_id" = "the file names the wrong animal"\n' + NWB_OWNING_PROBES
    problems = Recipe.load(write_recipe(tmp_path, body)).check(registry)
    applied = problems_coded(problems, RecipeFault.OVERRIDE_APPLIED, "info")
    assert any(p.message.startswith("subject.subject_id is declared and overrides nwb") for p in applied)
    assert not any(
        p.message.startswith("subject.subject_id") for p in problems_coded(problems, RecipeFault.FACT_COMPARED)
    )


def test_an_override_of_a_fact_nothing_states_is_reported_not_refused(tmp_path, registry):
    """Part 05 §3.6: a stale override leaves the packet correct, so it costs a line of the log."""
    body = (
        '\n[overrides]\n"subject.subject_id" = "why"\n'
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
    )
    problems = Recipe.load(write_recipe(tmp_path, body)).check(registry)
    assert [p.level for p in problems_coded(problems, RecipeFault.OVERRIDE_IDLE)] == ["warning"]


def test_a_source_that_cannot_say_what_it_states_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: an adapter declaring nothing must not read as one that states nothing."""
    from escapewheel_writer import sources

    class Mute:
        PRODUCES = frozenset({"core.units"})

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Mute)
    problems = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry)
    assert problems_coded(problems, RecipeFault.STATES_UNDECLARED, "error")


def test_a_stated_fact_with_no_accessor_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: the declaration is checked against the class, so it cannot drift unseen."""
    from escapewheel_writer import sources

    class Absent:
        PRODUCES = frozenset({"core.units"})
        STATES: ClassVar[dict[str, str]] = {"subject.subject_id": "nowhere"}

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Absent)
    problems = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry)
    (unexposed,) = problems_coded(problems, RecipeFault.STATE_UNEXPOSED, "error")
    assert "'nowhere'" in unexposed.message


def test_an_adapter_contributing_what_it_does_not_produce_is_refused(tmp_path, registry, monkeypatch):
    """Part 05 §3.4: a partly supplied resource is one the adapter supplies at all."""
    from escapewheel_writer import sources

    class Overreaching:
        PRODUCES = frozenset({"core.units"})
        CONTRIBUTES = frozenset({"core.clocks"})
        STATES: ClassVar[dict[str, str]] = {}

    monkeypatch.setitem(sources.ADAPTERS, "sorter", Overreaching)
    problems = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n')).check(registry)
    (overreached,) = problems_coded(problems, RecipeFault.CONTRIBUTES_UNPRODUCED, "error")
    assert overreached.message.startswith("sorter contributes core.clocks")


def test_a_recipe_naming_a_protocol_its_adapter_does_not_declare_is_refused(tmp_path, registry):
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        "[source.delivery]", '[source.delivery]\nprotocol = "flight-v0.1"'
    )
    (undeclared,) = problems_coded(
        Recipe.load(write_recipe(tmp_path, body)).check(registry), RecipeFault.PROTOCOL_UNDECLARED
    )
    assert "thermistor names protocol 'flight-v0.1'" in undeclared.message


def test_ownership_defaults_from_a_document_for_a_kind_that_cannot_be_imported(tmp_path, registry):
    """Which is the point of the document: a build settles ownership before it launches anything."""
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=declaration_for(tmp_path))))
    # `core.devices` is shared, so silence makes it a contribution rather than an exclusive claim.
    assert recipe.sources[0].claims == ("core.devices",)
    assert not [p for p in recipe.check(registry) if p.level == "error"]


def test_a_declaration_that_cannot_be_read_is_reported_rather_than_raised(tmp_path, registry):
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration="absent.json")))
    assert problems_coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)


def test_a_declaration_naming_a_resource_no_registry_declares_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, produces=["core.tirals"])
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    (undeclared,) = problems_coded(recipe.check(registry), RecipeFault.PRODUCES_UNDECLARED)
    assert "core.tirals" in undeclared.message


def test_a_declaration_contributing_what_it_does_not_produce_is_refused(tmp_path, registry):
    """Part 12 §7: the document form of the sixth fact is checked as the class form is."""
    named = declaration_for(tmp_path, contributes=["core.clocks"])
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    (overreached,) = problems_coded(recipe.check(registry), RecipeFault.CONTRIBUTES_UNPRODUCED)
    assert "core.clocks" in overreached.message


def test_a_declaration_naming_a_protocol_outside_the_group_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, protocols=["carrier-pigeon-v1.0"])
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    assert problems_coded(recipe.check(registry), RecipeFault.PROTOCOL_UNKNOWN)


def test_a_declaration_whose_shape_is_wrong_is_reported_where_it_is_wrong(tmp_path, registry):
    """The schema checks the shape; what the declaration says is checked against the registry."""
    named = declaration_for(tmp_path, protocols=["carrier pigeon"])
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    (unreadable,) = problems_coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)
    assert "thermistor.json: protocols" in unreadable.message


def test_a_declaration_needing_what_the_recipe_does_not_set_is_refused(tmp_path, registry):
    named = declaration_for(tmp_path, needs=["root", "session_id", "calibration_uri"])
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    (unfilled,) = problems_coded(recipe.check(registry), RecipeFault.NEEDS_UNFILLED)
    assert "calibration_uri" in unfilled.message


def test_an_option_no_declaration_names_is_refused(tmp_path, registry):
    """An option nothing reads is a statement about the packet that never reaches the source."""
    named = declaration_for(tmp_path, accepts=["smoothing_window"])
    body = DELIVERED.format(declaration=named).replace(
        "sample_rate_hz = 1000", "sample_rate_hz = 1000\nsmoothing_windwo = 3"
    )
    recipe = Recipe.load(write_recipe(tmp_path, body))
    (unread,) = problems_coded(recipe.check(registry), RecipeFault.OPTION_UNREAD)
    assert "'smoothing_windwo'" in unread.message


def test_an_accepted_option_the_recipe_leaves_unset_is_not_refused(tmp_path, registry):
    """What separates the two lists: a needed name a recipe omits is refused and an accepted one is not."""
    named = declaration_for(tmp_path, accepts=["smoothing_window"])
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
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
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    assert problems_coded(recipe.check(registry), fault)


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
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    unreadable = problems_coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)
    assert any(f"'{member}' is a required property" in p.message for p in unreadable)


def test_a_document_carrying_a_single_protocol_is_refused(tmp_path, registry):
    import json

    named = declaration_for(tmp_path)
    document = json.loads((tmp_path / named).read_text())
    document["protocol"] = document.pop("protocols")[0]
    (tmp_path / named).write_text(json.dumps(document))
    problems = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named))).check(registry)
    (unreadable,) = problems_coded(problems, RecipeFault.DECLARATION_UNREADABLE)
    assert "'protocols' is a required property" in unreadable.message


@pytest.mark.parametrize("protocols", [[], ["stream-v0.1", "stream-v0.1"]], ids=["empty", "repeated"])
def test_a_document_declaring_no_protocol_or_one_twice_is_refused(tmp_path, registry, protocols):
    named = declaration_for(tmp_path, protocols=protocols)
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named)))
    (unreadable,) = problems_coded(recipe.check(registry), RecipeFault.DECLARATION_UNREADABLE)
    assert "thermistor.json: protocols" in unreadable.message


def test_a_document_declaring_every_member_empty_is_sound(tmp_path, registry):
    """An empty array declares none, which is a declaration and not an omission."""
    named = declaration_for(tmp_path, produces=[], needs=[])
    body = DELIVERED.format(declaration=named).replace("sample_rate_hz = 1000\n", "")
    recipe = Recipe.load(write_recipe(tmp_path, body))
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
    return [p for p in Recipe.load(write_recipe(tmp_path, body)).check(registry) if p.level == "error"]


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
    (refused,) = problems_coded(_registered(monkeypatch, tmp_path, registry, **attributes), fault)
    assert named in refused.message


def test_a_shipped_class_may_declare_no_protocol(tmp_path, registry):
    body = '[[source]]\nkind = "sorter"\nroot = "."\n'
    problems = Recipe.load(write_recipe(tmp_path, body)).check(registry)
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
    (unknown,) = problems_coded(Recipe.load(write_recipe(tmp_path, body)).check(registry), RecipeFault.PROTOCOL_UNKNOWN)
    assert "sorter names protocol 'carrier-pigeon-v1.0'" in unknown.message


def test_a_delivery_with_no_command_is_refused(tmp_path, registry):
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        'command = ["thermistor-adapter", "--verbose"]\n', ""
    )
    recipe = Recipe.load(write_recipe(tmp_path, body))
    assert problems_coded(recipe.check(registry), RecipeFault.NO_COMMAND)


def test_a_source_is_reached_one_way_or_the_other(tmp_path, registry):
    """Part 05 §3.10: an entry naming a delivery and in process states two routes, so it is refused."""
    body = DELIVERED.format(declaration=declaration_for(tmp_path)).replace(
        "sample_rate_hz = 1000", "sample_rate_hz = 1000\nin_process = true"
    )
    recipe = Recipe.load(write_recipe(tmp_path, body))
    assert problems_coded(recipe.check(registry), RecipeFault.TWO_ROUTES)


def test_a_delivery_opts_its_entry_out_of_the_packets_in_process(tmp_path, registry):
    """Part 05 §3.10: a `delivery` table is the entry saying otherwise to `[packet] in_process`."""
    from escapewheel_writer.recipe import reached_by

    path = write_recipe(tmp_path, DELIVERED.format(declaration=declaration_for(tmp_path)))
    path.write_text(
        path.read_text().replace('registry = "reg.json"\n', 'registry = "reg.json"\nin_process = true\n', 1)
    )
    recipe = Recipe.load(path)
    assert not problems_coded(recipe.check(registry), RecipeFault.TWO_ROUTES)
    (spec,) = recipe.sources
    assert not spec.in_process
    assert reached_by(spec) is not None


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
    recipe = Recipe.load(write_recipe(tmp_path, body))
    assert recipe.sources[0].delivery.declaration is None
    # The recipe is one source short of validating, which is not what this is about: nothing the
    # build says about reaching the adapter is a problem.
    about = ("delivery", "declaration", "protocol", "declares")
    assert not [p for p in recipe.check(registry) if any(word in p.message for word in about)]


def prefix_refusals(tmp_path, registry, body):
    """The refusals naming a prefix disagreement."""
    return [
        p.message
        for p in problems_coded(Recipe.load(write_recipe(tmp_path, body)).check(registry), RecipeFault.PREFIX_DISAGREES)
    ]


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
    problems = Recipe.load(write_recipe(tmp_path, prefixed(sorter=prefix))).check(registry)
    (refused,) = problems_coded(problems, RecipeFault.PREFIX_CHARACTERS)
    assert f"source 'sorter': prefix {prefix!r}" in refused.message


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
    recipe = Recipe.load(write_recipe(tmp_path, PREFERRED + PREFERRED.replace("probeA.curation", "probeA.other")))
    assert recipe.preferred_runs[1]["processing_run_name"] == "probeA.other"
    assert problems_coded(recipe.check(registry), RecipeFault.REPEATED_PREFERRED_RUN, "error")


@pytest.mark.parametrize("chosen", ["2026-09-01T00:00:00", "2026-09-01", "yesterday"])
def test_a_chosen_at_naming_no_instant_is_refused(tmp_path, registry, chosen):
    recipe = Recipe.load(
        write_recipe(tmp_path, PREFERRED + f"chosen_at = {chosen if chosen[0].isdigit() else repr(chosen)}\n")
    )
    assert problems_coded(recipe.check(registry), RecipeFault.CHOSEN_AT_NO_INSTANT, "error")


def test_an_offset_chosen_at_is_normalized_to_utc(tmp_path, registry):
    from datetime import UTC, datetime

    from escapewheel_writer.recipe import normalized_chosen_at

    recipe = Recipe.load(write_recipe(tmp_path, PREFERRED + "chosen_at = 2026-09-01T02:00:00+02:00\n"))
    assert not problems_coded(recipe.check(registry), RecipeFault.CHOSEN_AT_NO_INSTANT)
    assert normalized_chosen_at(recipe.preferred_runs[0]["chosen_at"]) == datetime(2026, 9, 1, tzinfo=UTC)


def test_an_amending_recipe_declares_only_its_session(tmp_path, registry):
    """Part 05 §3.5: the packet's session and subject rows prevail, so the recipe states neither."""
    body = RECIPE_BASE.replace('registry = "reg.json"', 'registry = "reg.json"\namends = "0.1.0"')
    path = tmp_path / "amend.toml"
    path.write_text(body + '\n[overrides]\n"subject.subject_id" = "because"\n')
    declared = problems_coded(Recipe.load(path).check(registry), RecipeFault.AMENDING_DECLARES, "error")
    stated = " ".join(p.message for p in declared)
    for name in ("[session] reference_clock_id", "[subject] subject_id", "[overrides] subject.subject_id"):
        assert name in stated


def test_an_amended_packet_supplies_what_it_holds(tmp_path, registry):
    """Part 05 §3.5: a held table satisfies a required reference, and a held clock a parent."""
    body = '\n[[source]]\nkind = "sorter"\nroot = "sorted"\nparent_clock_id = "harp"\nowns = ["core.units"]\n'
    recipe = Recipe.load(write_recipe(tmp_path, body))
    assert problems_coded(recipe.check(registry), RecipeFault.DANGLING_REFERENCE, "error")
    held = recipe.check(
        registry, held_tables=["core.sorting_runs", "core.curation_versions", "core.probes", "core.clocks"]
    )
    assert not problems_coded(held, RecipeFault.DANGLING_REFERENCE, "error")


@pytest.mark.parametrize(
    ("key", "said"),
    [
        ("core.units.unit_name", "no preference"),
        ("core.probes.nonexistent", "no column"),
        ("core.probes.metadata", "metadata"),
        ("core.probes.probe_id", "primary key"),
    ],
    ids=["no-preference", "undeclared-column", "metadata", "key-column"],
)
def test_a_column_override_that_can_release_nothing_is_refused(tmp_path, registry, key, said):
    """Part 05 §3.5: each is decided from the recipe and its registries, before any source opens."""
    recipe = contested_recipe(tmp_path, f'\n[overrides]\n"{key}" = "why"\n')
    (refused,) = problems_coded(recipe.check(registry), RecipeFault.COLUMN_OVERRIDE_UNSOUND, "error")
    assert key in refused.message and said in refused.message


def test_a_column_override_of_a_required_column_is_admitted(tmp_path, registry):
    """Part 05 §3.5: only the four refusals; the non-null check guards a required column (Part 05 §5.1)."""
    recipe = contested_recipe(tmp_path, '\n[overrides]\n"core.probes.session_id" = "why"\n')
    assert not problems_coded(recipe.check(registry), RecipeFault.COLUMN_OVERRIDE_UNSOUND)


def test_a_column_override_draws_no_report_of_a_declared_field(tmp_path, registry):
    """Part 05 §3.5: a column override covers no declared field, so it is neither idle nor applied there."""
    recipe = contested_recipe(tmp_path, '\n[overrides]\n"core.probes.probe_type" = "why"\n')
    assert not any("core.probes.probe_type" in p.message for p in recipe.check(registry))


def test_an_amending_recipe_admits_a_column_override_and_refuses_a_field_override(tmp_path, registry):
    """Part 05 §3.5: the packet's rows prevail over a declared field, and a preference still arbitrates."""
    body = RECIPE_BASE.replace('registry = "reg.json"', 'registry = "reg.json"\namends = "0.1.0"')
    path = tmp_path / "amend.toml"
    path.write_text(
        body
        + '\n[overrides]\n"subject.subject_id" = "because"\n"core.probes.probe_type" = "because"\n'
        + '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\n'
        + '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
        + PREFER_NWB
    )
    declared = problems_coded(Recipe.load(path).check(registry), RecipeFault.AMENDING_DECLARES, "error")
    stated = " ".join(p.message for p in declared)
    assert "[overrides] subject.subject_id" in stated
    assert "core.probes.probe_type" not in stated

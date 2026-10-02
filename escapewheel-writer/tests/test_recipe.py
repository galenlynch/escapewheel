"""The session recipe: parsing, and what its declarations resolve to."""

from __future__ import annotations

import pytest

from escapewheel_writer.errors import (
    RecipeFault,
    RecipeUnreadable,
)
from escapewheel_writer.recipe import RECIPE_SUPPLIES, Recipe
from escapewheel_writer.sources import ADAPTERS
from tests.builders import (
    DELIVERED,
    NWB_OWNING_PROBES,
    PREFER_NWB,
    RECIPE_BASE,
    TWO_DEFAULTED,
    declaration_for,
    problems_coded,
    write_recipe,
)


def test_a_recipe_parses_its_declarations(tmp_path):
    recipe = Recipe.load(
        write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "sorted"\nowns = ["core.units"]\n')
    )
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
    path.write_text(
        RECIPE_BASE.replace('registry = "reg.json"', 'registry = "reg.json"\nin_process = true') + both.format("")
    )
    assert [s.in_process for s in Recipe.load(path).sources] == [True, True]

    out = write_recipe(tmp_path, both.format("\nin_process = true"), "one-in.toml")
    assert [s.in_process for s in Recipe.load(out).sources] == [True, False]


def test_a_shipped_adapter_needs_no_declaration_and_a_registered_one_does(tmp_path):
    """Part 12 §3's test is the release boundary. A built-in ships with this package and is
    upgraded with it, so in process is its only route and there is nothing to declare; a kind
    another distribution registers moves on its own schedule and must say how it can be reached."""
    registry = {"resources": {"core.units": {"kind": "table", "table": {"columns": [], "rules": []}}}}

    built_in = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\n'))
    assert not problems_coded(built_in.check(registry), RecipeFault.NO_ROUTE)

    registered = write_recipe(tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\n', "reg.toml")
    (unreached,) = problems_coded(Recipe.load(registered).check(registry), RecipeFault.NO_ROUTE)
    assert "vr_sites" in unreached.message

    opted = write_recipe(
        tmp_path, '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\nin_process = true\n', "opt.toml"
    )
    assert not problems_coded(Recipe.load(opted).check(registry), RecipeFault.NO_ROUTE)

    delivered = write_recipe(
        tmp_path,
        '\n[[source]]\nkind = "vr_sites"\nroot = "."\nowns = []\n'
        '\n[source.delivery]\nprotocol = "stream-v0.1"\ncommand = ["vr-sites-adapter"]\n',
        "delivered.toml",
    )
    assert not problems_coded(Recipe.load(delivered).check(registry), RecipeFault.NO_ROUTE)


def test_an_in_process_source_does_not_carry_the_flag_into_the_adapter(tmp_path):
    """`in_process` is the build's business, so it must not reach the adapter as an option: every
    other key of a source entry is passed through as a keyword argument."""
    recipe = Recipe.load(
        write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "."\nowns = []\nin_process = true\n')
    )
    assert "in_process" not in recipe.sources[0].options


def test_paths_resolve_against_the_recipe_not_the_caller(tmp_path):
    """A recipe travels with the tree it describes, so relative paths are relative to it."""
    recipe = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "sorted"\nowns = []\n'))
    assert recipe.sources[0].root == tmp_path / "sorted"
    assert recipe.registry == tmp_path / "reg.json"


def test_the_digest_identifies_the_parameters(tmp_path):
    """`core.processing_runs` names the run; the digest is what makes the name answerable."""
    one = Recipe.load(write_recipe(tmp_path, "\n", "a.toml"))
    same = Recipe.load(write_recipe(tmp_path, "\n", "b.toml"))
    other = Recipe.load(write_recipe(tmp_path, "\n# a comment changes it\n", "c.toml"))
    assert one.digest == same.digest
    assert one.digest != other.digest


# -- a recipe declares what it narrows -----------------------------------------------------


def test_a_source_that_declares_no_owns_takes_what_it_produces(tmp_path, registry):
    """Silence means the whole of PRODUCES, not nothing (Part 05 §3.4)."""
    recipe = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n'))
    owns = set(recipe.sources[0].owns)
    assert "core.units" in owns and "core.unit_quality_labels" in owns and "core.spike_events" in owns
    # RECIPE_SUPPLIES is not an adapter's to claim.
    assert not owns & set(RECIPE_SUPPLIES)


def test_an_explicit_owns_still_narrows(tmp_path, registry):
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
    assert Recipe.load(write_recipe(tmp_path, body)).sources[0].owns == ("core.units",)


def test_an_empty_owns_narrows_to_nothing(tmp_path, registry):
    """An explicit empty list is a decision; silence is not, so the two cannot be conflated."""
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = []\n'
    assert Recipe.load(write_recipe(tmp_path, body)).sources[0].owns == ()


def test_a_defaulted_source_does_not_take_what_another_explicitly_owns(tmp_path, registry):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\nzone = "UTC"\n'
    )
    recipe = Recipe.load(write_recipe(tmp_path, body))
    sorter = next(s for s in recipe.sources if s.kind == "sorter")
    assert "core.probes" not in sorter.owns


def test_a_preferred_source_owns_its_resource_whatever_its_entry_declares(tmp_path, registry):
    """Part 05 §3.3: a preference declares ownership, so a narrowed entry gains the resource."""
    body = TWO_DEFAULTED.replace('zone = "UTC"', 'zone = "UTC"\nowns = ["core.electrodes"]')
    recipe = Recipe.load(write_recipe(tmp_path, body + PREFER_NWB))
    nwb = next(s for s in recipe.sources if s.kind == "nwb")
    assert set(nwb.owns) == {"core.electrodes", "core.probes"}


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
        Recipe.load(write_recipe(tmp_path, body))
    assert {p.code for p in refused.value.problems} == {RecipeFault.RECIPE_SHAPE}
    assert any(where in p.message for p in refused.value.problems)


def test_a_defaulted_entry_contributes_and_does_not_own_what_it_lists_under_contributes(tmp_path, registry):
    """Part 05 §3.4: an entry's own `contributes` is a contribution, whatever the default reads."""
    body = '\n[[source]]\nkind = "sorter"\nroot = "s"\ncontributes = ["core.units"]\n'
    spec = Recipe.load(write_recipe(tmp_path, body)).sources[0]
    assert "core.units" in spec.contributes and "core.units" not in spec.owns


def test_a_partly_supplied_resource_is_contributed_not_owned(tmp_path, registry):
    """The sorter declares core.clocks as supplied in part, so a default contributes rather than owns."""
    recipe = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\n'))
    spec = recipe.sources[0]
    assert "core.clocks" in spec.contributes and "core.clocks" not in spec.owns


def test_what_a_source_produces_is_what_it_can_emit():
    """Part 05 §3.4: a PRODUCES that drifts from the code declares what the adapter cannot emit."""

    for kind, adapter in ADAPTERS.items():
        declared = set(getattr(adapter, "PRODUCES", ()))
        assert declared, f"{kind} declares no PRODUCES (Part 05 §3.4)"
        assert all(r.count(".") == 1 for r in declared), f"{kind} declares a malformed resource ID"


def test_an_override_with_no_reason_is_refused(tmp_path):
    """Part 05 §3.6: a bare marker would silence a difference without saying why."""
    body = '\n[overrides]\n"subject.subject_id" = "   "\n' + NWB_OWNING_PROBES
    with pytest.raises(RecipeUnreadable) as refused:
        Recipe.load(write_recipe(tmp_path, body))
    (problem,) = refused.value.problems
    assert problem.code is RecipeFault.RECIPE_SHAPE
    assert problem.message.startswith("overrides/subject.subject_id")


@pytest.mark.parametrize(
    "key",
    ["subject.strain", "session.session_start_time", "core.probes.probe_type", "aind_unit_qc.metrics.num_spikes_used"],
)
def test_an_override_key_of_either_form_loads(tmp_path, key):
    """Part 05 §3.6: a field override's `block.field` and a column override's `resource.column`."""
    recipe = Recipe.load(write_recipe(tmp_path, f'\n[overrides]\n"{key}" = "why"\n' + NWB_OWNING_PROBES))
    assert key in {**recipe.field_overrides, **recipe.column_overrides}


@pytest.mark.parametrize(
    "key",
    ["core.probes", "probes.probe_type", "core.probes.probe_type.extra", "core..probe_type", "subject."],
    ids=["a-resource", "no-block", "four-segments", "empty-segment", "empty-field"],
)
def test_an_override_key_of_neither_form_is_refused_on_load(tmp_path, key):
    """Part 05 §3.1: a two-segment key names `session` or `subject`, and no other key shape is an override."""
    with pytest.raises(RecipeUnreadable) as refused:
        Recipe.load(write_recipe(tmp_path, f'\n[overrides]\n"{key}" = "why"\n' + NWB_OWNING_PROBES))
    assert {p.code for p in refused.value.problems} == {RecipeFault.RECIPE_SHAPE}


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
        Recipe.load(write_recipe(tmp_path, f'\n[encoding]\n"aind_unit_qc.metrics.silhouette" = {entry}\n'))
    assert {p.code for p in refused.value.problems} == {RecipeFault.RECIPE_SHAPE}
    assert all(p.message.startswith("encoding/aind_unit_qc.metrics.silhouette") for p in refused.value.problems)


def test_an_encoding_declaration_names_a_declared_column(tmp_path):
    """The registries are what know the columns, so this waits for them rather than for the schema."""
    recipe = Recipe.load(
        write_recipe(
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


def test_a_delivered_source_carries_how_a_build_reaches_it(tmp_path):
    """The recipe carries every fact about the machine; the document carries the adapter's."""
    recipe = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=declaration_for(tmp_path))))
    (spec,) = recipe.sources
    assert spec.delivery.command == ("thermistor-adapter", "--verbose")
    assert spec.delivery.report_path == tmp_path / "reports/thermistor.json"


def test_a_recipe_naming_no_protocol_reaches_the_adapter_by_one_it_declares(tmp_path):
    """Part 12 §3: the adapter's first declared, and only that protocol's terms are supplied."""
    from escapewheel_writer.reading import protocol_supplies
    from escapewheel_writer.recipe import reached_by

    named = declaration_for(tmp_path, protocols=["flight-v0.1", "files-v0.1"])
    (spec,) = Recipe.load(write_recipe(tmp_path, DELIVERED.format(declaration=named))).sources
    assert spec.delivery.protocol == ""
    assert reached_by(spec) == "flight-v0.1"
    assert set(protocol_supplies("flight-v0.1", tmp_path, tmp_path, tmp_path / "report.json")) == {"socket"}


def test_a_source_run_in_process_is_reached_by_no_protocol(tmp_path):
    """In process there is no boundary, so no protocol and none of its terms (Part 12 §4)."""
    from escapewheel_writer.recipe import reached_by

    (spec,) = Recipe.load(write_recipe(tmp_path, '[[source]]\nkind = "sorter"\nroot = "."\n')).sources
    assert reached_by(spec) is None

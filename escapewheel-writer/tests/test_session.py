"""What a build notes or refuses about its recipe before it writes."""

from __future__ import annotations

import pytest

from escapewheel_writer.errors import (
    RecipeFault,
    RecipeUnsound,
)
from escapewheel_writer.notes import NoteCode, codes
from escapewheel_writer.notes import coded as noted
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.session import grouped_encoding_exceptions, note_unclaimed
from tests.builders import PREFER_NWB, contested_recipe, prefixed, write_recipe


class Noted:
    """The one thing `note_unclaimed` needs of a source: somewhere to put a note."""

    def __init__(self) -> None:
        self.notes: list[str] = []


def test_a_produced_resource_no_source_claims_is_noted(tmp_path):
    recipe = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 19_061})
    assert codes(source.notes) == [NoteCode.UNCLAIMED_DISCARDED]
    assert "core.unit_quality_labels (19,061 rows)" in source.notes[0]


def test_a_resource_the_recipe_prefers_another_source_for_is_not_noted(tmp_path):
    body = (
        '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'
        '\n[[source]]\nkind = "nwb"\nroot = "n"\nowns = ["core.probes"]\n' + PREFER_NWB
    )
    recipe = Recipe.load(write_recipe(tmp_path, body))
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
    recipe = Recipe.load(write_recipe(tmp_path, body))
    source = Noted()
    note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.probes": 10}, frozenset(recipe.preferred))
    assert any("core.probes (10 rows)" in n for n in noted(source.notes, NoteCode.UNCLAIMED_DISCARDED))


def test_an_empty_unclaimed_resource_is_not_noted(tmp_path):
    recipe = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    note_unclaimed(recipe.sources[0], source, {"core.units": 4, "core.unit_quality_labels": 0})
    assert source.notes == []


def test_what_the_recipe_itself_supplies_is_not_noted(tmp_path):
    recipe = Recipe.load(write_recipe(tmp_path, '\n[[source]]\nkind = "sorter"\nroot = "s"\nowns = ["core.units"]\n'))
    source = Noted()
    # RECIPE_SUPPLIES: the recipe writes these, so a source producing them loses to it by design.
    note_unclaimed(recipe.sources[0], source, {"core.processing_runs": 2, "core.sessions": 1})
    assert source.notes == []


def test_rows_another_source_owns_are_noted_without_a_preference(tmp_path):
    """Part 05 §3.4. Two sources holding disjoint parts of one resource; `owns` keeps one silently."""
    recipe = Recipe.load(
        write_recipe(
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
    recipe = contested_recipe(tmp_path)
    sorter = next(spec for spec in recipe.sources if spec.kind == "sorter")
    source = Noted()
    note_unclaimed(sorter, source, {"core.probes": 1}, frozenset(recipe.preferred))
    assert source.notes == []


def test_an_encoding_declaration_reaches_the_writer(tmp_path):
    """`resource.column` splits at the last dot, a resource ID being dotted itself."""
    recipe = Recipe.load(
        write_recipe(
            tmp_path,
            """
[encoding]
"aind_unit_qc.metrics.num_spikes_used" = { encoding = "delta", reason = "1.7x" }
""",
        )
    )
    assert grouped_encoding_exceptions(recipe)["delta"] == {"aind_unit_qc.metrics": ("num_spikes_used",)}


def test_a_build_refuses_disagreeing_prefixes_before_opening_a_source(tmp_path, registry):
    from escapewheel_writer.session import build

    recipe = Recipe.load(
        write_recipe(tmp_path, prefixed(sorter="a.", nwb=None).replace('root = "."', 'root = "absent"'))
    )
    with pytest.raises(RecipeUnsound) as refused:
        build(recipe, registry)
    assert RecipeFault.PREFIX_DISAGREES in {p.code for p in refused.value.problems}
    assert not (recipe.out / "staging").exists(), "refused before anything was prepared"

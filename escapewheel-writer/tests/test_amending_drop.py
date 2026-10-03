"""An amending build and a held column its bound declaration does not declare (Part 05 §3.5)."""

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_validator import Level

from escapewheel_writer.errors import CommitRefused, RecipeFault, RecipeUnsound
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.session import build, commit_arguments, prepare
from tests.builders import amending_recipe, commit_tables, held_dropped_json, session_recipe, session_sources
from tests.conftest import REGISTRY, read_registry

COLUMN = "core.source_files.dropped_json"
SPIKE_EVENTS = "analysis.spike_events"
MATERIALIZE = f'\n[[materialize]]\nresource = "{SPIKE_EVENTS}"\n'


def _recipe(root: Path, extra: str = "") -> Recipe:
    """An amending recipe reading no source, so all it can do is decide over what the packet holds."""
    path = root.parent / "amend.toml"
    path.write_text(
        f'[packet]\nid = "{root.name}"\nout = "{root}"\namends = "0.1.0"\n\n[session]\nsession_id = "s001"\n{extra}'
    )
    return Recipe.load(path)


def _drop(*keys: str) -> str:
    return "\n[drop]\n" + "".join(f'"{key}" = "given up"\n' for key in keys)


def _problems(recipe: Recipe, registry=REGISTRY) -> list[tuple[Level, RecipeFault, str]]:
    codes = {
        RecipeFault.HELD_COLUMN_UNDECLARED,
        RecipeFault.DROP_UNSOUND,
        RecipeFault.DROP_IDLE,
        RecipeFault.COLUMN_DROPPED,
    }
    return [(p.level, p.code, p.message) for p in prepare(recipe, registry).problems if p.code in codes]


def _file(root: Path, resource_id: str) -> Path:
    entries = json.loads((root / "packet.json").read_text())["resources"]
    return root / next(e["uri"] for e in entries if e["resource_id"] == resource_id)


def _hold_column(root: Path, resource_id: str, column: str = "extra") -> None:
    """Give a held table's file a column no registry declares, as a writer outside this one might."""
    path = _file(root, resource_id)
    table = pq.read_table(path)
    pq.write_table(table.append_column(column, pa.array(["x"] * table.num_rows, pa.string())), path)


def test_a_held_undeclared_column_refuses_the_build_before_any_source(tmp_path, minimal):
    root = held_dropped_json(tmp_path, REGISTRY, minimal)
    missing = tmp_path / "nowhere"
    recipe = _recipe(root, f'\n[[source]]\nkind = "sorter"\nroot = "{missing}"\nowns = ["core.units"]\n')
    with pytest.raises(RecipeUnsound) as refused:
        build(recipe, REGISTRY)
    [problem] = [p for p in refused.value.problems if p.code is RecipeFault.HELD_COLUMN_UNDECLARED]
    assert "core.source_files holds dropped_json" in problem.message
    # The packet's own registry still declares the column, so binding it is the second remedy.
    assert f"[drop] as {COLUMN}" in problem.message
    assert "name no core registry" in problem.message


def test_a_drop_entry_builds_and_reports_the_drop(tmp_path, minimal):
    root = held_dropped_json(tmp_path, REGISTRY, minimal)
    superseded = _file(root, "core.source_files")
    recipe = _recipe(root, _drop(COLUMN))
    assert _problems(recipe) == [
        (
            Level.INFO,
            RecipeFault.COLUMN_DROPPED,
            f"[drop] {COLUMN}: the build writes core.source_files without dropped_json, because given up",
        )
    ]
    assert build(recipe, REGISTRY).amend(recipe.out).passed
    assert "dropped_json" not in pq.read_schema(_file(root, "core.source_files")).names
    assert "dropped_json" in pq.read_schema(superseded).names


def test_naming_no_core_registry_binds_the_packets_own(tmp_path, minimal):
    """What the command line does for an amending recipe naming none (Part 05 §15.1)."""
    root = held_dropped_json(tmp_path, REGISTRY, minimal)
    recipe = _recipe(root)
    assert _problems(recipe, read_registry(root)) == []
    assert build(recipe, read_registry(root)).amend(recipe.out).passed


def test_where_the_packets_own_registry_lacks_the_column_only_drop_is_named(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    _hold_column(root, "core.clocks")
    [(level, code, message)] = _problems(_recipe(root))
    assert (level, code) == (Level.ERROR, RecipeFault.HELD_COLUMN_UNDECLARED)
    assert '[drop] as core.clocks.extra = "' in message
    assert "registry" not in message.split(";", 1)[1]


def test_a_drop_entry_for_a_column_the_file_lacks_is_idle(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    recipe = _recipe(root, _drop("core.clocks.extra"))
    assert [(level, code) for level, code, _ in _problems(recipe)] == [(Level.WARNING, RecipeFault.DROP_IDLE)]


@pytest.mark.parametrize(
    "key, reason",
    [
        ("core.units.extra", "does not hold as a table"),
        ("core.clocks.origin", "the registry the build binds declares"),
    ],
)
def test_an_unsound_drop_entry_is_refused(tmp_path, registry, minimal, key, reason):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    [(level, code, message)] = _problems(_recipe(root, _drop(key)))
    assert (level, code) == (Level.ERROR, RecipeFault.DROP_UNSOUND)
    assert key in message and reason in message


# -- a derived table -------------------------------------------------------------------


def _derived(tmp_path: Path) -> tuple[Path, Path]:
    """Commit a build deriving spike events, and return the packet and its sorted asset."""
    sorted_root, raw = session_sources(tmp_path)
    path = session_recipe(tmp_path, sorted_root, raw)
    path.write_text(path.read_text() + MATERIALIZE)
    recipe = Recipe.load(path)
    assert build(recipe, REGISTRY).commit(recipe.out, **commit_arguments(recipe)).passed
    return recipe.out, sorted_root


def _rerunning(tmp_path: Path, sorted_root: Path, extra: str = "") -> Recipe:
    """An amending build that re-runs the held curation, so it adds no spike event (Part 05 §4.3)."""
    path = amending_recipe(tmp_path, sorted_root, extra=extra)
    path.write_text(path.read_text().replace('curation = "recurated"\n', ""))
    return Recipe.load(path)


def test_a_drop_naming_a_table_derived_again_is_refused(tmp_path):
    out, sorted_root = _derived(tmp_path)
    _hold_column(out, SPIKE_EVENTS)
    recipe = _rerunning(tmp_path, sorted_root, MATERIALIZE + _drop(f"{SPIKE_EVENTS}.extra"))
    with pytest.raises(RecipeUnsound) as refused:
        build(recipe, REGISTRY)
    [problem] = refused.value.problems
    assert problem.code is RecipeFault.DROP_UNSOUND
    assert "[[materialize]]" in problem.message


def test_a_held_analysis_table_is_refused_dropped_or_derived_again(tmp_path):
    out, sorted_root = _derived(tmp_path)
    _hold_column(out, SPIKE_EVENTS)
    with pytest.raises(RecipeUnsound) as refused:
        build(_rerunning(tmp_path, sorted_root), REGISTRY)
    assert [p.code for p in refused.value.problems] == [RecipeFault.HELD_COLUMN_UNDECLARED]

    dropping = _rerunning(tmp_path, sorted_root, _drop(f"{SPIKE_EVENTS}.extra"))
    assert build(dropping, REGISTRY).amend(dropping.out).passed
    assert "extra" not in pq.read_schema(_file(out, SPIKE_EVENTS)).names


def test_a_held_analysis_table_derived_again_carries_no_held_column(tmp_path):
    out, sorted_root = _derived(tmp_path)
    _hold_column(out, SPIKE_EVENTS)
    recipe = _rerunning(tmp_path, sorted_root, MATERIALIZE)
    assert build(recipe, REGISTRY).amend(recipe.out, **commit_arguments(recipe)).passed
    assert "extra" not in pq.read_schema(_file(out, SPIKE_EVENTS)).names


def test_a_drop_only_rewrite_of_a_derived_from_table_leaves_the_derived_one_stale(tmp_path, monkeypatch):
    """Part 05 §15.2: removing a column changes no row, but the table is written, so the duty holds."""
    from escapewheel_writer.amending import Held

    out, sorted_root = _derived(tmp_path)
    _hold_column(out, "core.spike_events")
    dropping = _drop("core.spike_events.extra")
    monkeypatch.setattr(Held, "without_stale", lambda self, resources, written: list(resources))
    with pytest.raises(CommitRefused) as refused:
        recipe = _rerunning(tmp_path, sorted_root, dropping)
        build(recipe, REGISTRY).amend(recipe.out)
    assert "amendment.derived_resource_stale" in {f.check for f in refused.value.report.findings}
    monkeypatch.undo()

    recipe = _rerunning(tmp_path, sorted_root, dropping)
    assert build(recipe, REGISTRY).amend(recipe.out).passed
    entries = json.loads((out / "packet.json").read_text())["resources"]
    assert SPIKE_EVENTS not in {e["resource_id"] for e in entries}

    (tmp_path / "again").mkdir()
    out, sorted_root = _derived(tmp_path / "again")
    _hold_column(out, "core.spike_events")
    recipe = _rerunning(tmp_path / "again", sorted_root, dropping + MATERIALIZE)
    assert build(recipe, REGISTRY).amend(recipe.out, **commit_arguments(recipe)).passed
    entries = json.loads((out / "packet.json").read_text())["resources"]
    assert SPIKE_EVENTS in {e["resource_id"] for e in entries}

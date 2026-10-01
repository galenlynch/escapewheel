"""An amending build: a recipe whose `[packet].amends` names the packet it adds to (Part 05 §15.1)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from escapewheel_reader import open_packet

from escapewheel_writer.errors import RecipeFault, RecipeUnsound, SourceDefect
from escapewheel_writer.recipe import Recipe, SourceSpec
from escapewheel_writer.session import _compare_held_facts, build
from tests.conftest import REGISTRY
from tests.test_build_end_to_end import CLOCK_NAME, _recipe, _sources


def _amending(root: Path, sorted_root: Path, *, amends: str = "0.1.0", extra: str = "") -> Path:
    """A recipe adding a second curation of the packet's sortings, and nothing it holds."""
    path = root / "amend.toml"
    path.write_text(f"""
[packet]
id = "s1"
out = "{root}/packet"
amends = "{amends}"

[session]
session_id = "s1"

[[source]]
kind = "sorter"
root = "{sorted_root}"
parent_clock_id = "{CLOCK_NAME}"
curation = "recurated"
contributes = ["core.processing_runs"]
owns = ["core.units", "core.spike_events", "core.curation_versions", "core.unit_quality_labels"]
{extra}""")
    return path


@pytest.fixture
def packet(tmp_path):
    """A committed packet and its sorted asset, fresh for each test since an amendment changes it."""
    sorted_root, raw = _sources(tmp_path)
    recipe = Recipe.load(_recipe(tmp_path, sorted_root, raw))
    assert build(recipe, REGISTRY).commit(recipe.out).passed
    return tmp_path, sorted_root


def _rows(root: Path, resource_id: str) -> list[dict]:
    return open_packet(root).table(resource_id).to_pylist()


def test_an_amending_build_adds_a_curation_and_prefers_it(packet):
    """Part 05 §12: the added curation shares its sorting's scope with the held one, so it is preferred."""
    root, sorted_root = packet
    out = root / "packet"
    held_units = _rows(out, "core.units")
    recipe = Recipe.load(_amending(root, sorted_root))
    report = build(recipe, REGISTRY).amend(recipe.out)
    assert report.passed, [f"{f.check}: {f.message}" for f in report.findings if f.level == "error"]
    manifest = json.loads((out / "packet.json").read_text())
    assert manifest["packet_version"] == "0.1.1"
    units = _rows(out, "core.units")
    assert units[: len(held_units)] == held_units
    assert len(units) == 2 * len(held_units)
    assert min(u["unit_id"] for u in units[len(held_units) :]) > max(u["unit_id"] for u in held_units)
    runs = {r["processing_run_id"]: r for r in _rows(out, "core.processing_runs")}
    preferred = [runs[p["processing_run_id"]]["processing_run_name"] for p in _rows(out, "core.preferred_runs")]
    assert sorted(preferred) == sorted(
        r["processing_run_name"] for r in runs.values() if r["processing_run_name"].endswith(".recurated.curation")
    )
    # The packet's session row prevails, and the import run is a second import, not an alternative.
    assert [s["session_name"] for s in _rows(out, "core.sessions")] == ["s1"]
    assert sum(r["activity_type"] == "import" for r in runs.values()) == 2


def test_an_amending_build_refuses_a_version_it_does_not_amend(packet):
    root, sorted_root = packet
    recipe = Recipe.load(_amending(root, sorted_root, amends="0.2.0"))
    with pytest.raises(RecipeUnsound) as refused:
        build(recipe, REGISTRY)
    assert [p.code for p in refused.value.problems] == [RecipeFault.AMENDS_OTHER_VERSION]


def test_an_amending_recipe_declares_no_session_fact(packet):
    """Part 05 §3.5: the packet's session and subject rows prevail, so a recipe stating one is refused."""
    root, sorted_root = packet
    path = _amending(root, sorted_root)
    path.write_text(path.read_text().replace('session_id = "s1"\n', 'session_id = "s1"\ntask_name = "x"\n', 1))
    with pytest.raises(RecipeUnsound) as refused:
        build(Recipe.load(path), REGISTRY)
    (problem,) = refused.value.problems
    assert problem.code is RecipeFault.AMENDING_DECLARES
    assert "[session] task_name" in problem.message


def test_an_amending_build_refuses_a_held_clock_declared_again(packet):
    root, sorted_root = packet
    clock = f'\n[[clock]]\nclock_id = "{CLOCK_NAME}"\nname = "HARP"\ntick_rate_num = 31250\norigin = "harp epoch"\n'
    with pytest.raises(RecipeUnsound) as refused:
        build(Recipe.load(_amending(root, sorted_root, extra=clock)), REGISTRY)
    assert [p.code for p in refused.value.problems] == [RecipeFault.CLOCK_HELD]


def test_rerunning_the_held_curation_adds_none_of_its_rows(packet):
    """Part 05 §4.3: the rows equal the packet's and are dropped, so only the import is recorded."""
    root, sorted_root = packet
    path = _amending(root, sorted_root)
    path.write_text(path.read_text().replace('curation = "recurated"\n', ""))
    before = _rows(root / "packet", "core.units")
    recipe = Recipe.load(path)
    assert build(recipe, REGISTRY).amend(recipe.out).passed
    assert _rows(root / "packet", "core.units") == before


def test_a_preferred_run_names_a_run_the_packet_holds(packet):
    root, sorted_root = packet
    held = {r["processing_run_name"] for r in _rows(root / "packet", "core.processing_runs")}
    curation = next(name for name in sorted(held) if name.endswith(".curation"))
    sorting = curation.removesuffix(".curation")
    entry = (
        f'\n[[preferred_run]]\nactivity_type = "curation"\nscope_kind = "core.sorting_runs"\n'
        f'scope = "{sorting}"\nprocessing_run_name = "{curation}"\nreason = "the first curation stands"\n'
        "chosen_at = 2026-09-01T00:00:00Z\n"
    )
    recipe = Recipe.load(_amending(root, sorted_root, extra=entry))
    assert build(recipe, REGISTRY).amend(recipe.out).passed
    runs = {r["processing_run_id"]: r["processing_run_name"] for r in _rows(root / "packet", "core.processing_runs")}
    chosen = {p["scope"]: runs[p["processing_run_id"]] for p in _rows(root / "packet", "core.preferred_runs")}
    assert chosen[sorting] == curation


def test_a_preferred_run_naming_no_run_is_refused(packet):
    root, sorted_root = packet
    entry = (
        '\n[[preferred_run]]\nactivity_type = "curation"\nscope_kind = "core.sorting_runs"\n'
        'scope = "x"\nprocessing_run_name = "nothing"\nreason = "r"\n'
    )
    with pytest.raises(RecipeUnsound) as refused:
        build(Recipe.load(_amending(root, sorted_root, extra=entry)), REGISTRY)
    assert [p.code for p in refused.value.problems] == [RecipeFault.PREFERRED_RUN_UNKNOWN]


def _stating(**facts):
    """A source stating each fact under an attribute of the same name."""
    return SimpleNamespace(STATES={fact: fact for fact in facts}, **facts)


def test_a_source_s_differing_session_fact_is_reported_and_the_packet_s_kept():
    """Part 05 §3.6: the packet's row prevails, so the difference is noted and nothing is written."""
    notes = []
    source = _stating(**{"session.task_name": "reversal", "session.institution": "AIND"})
    held = {"session.task_name": "foraging", "session.institution": "AIND"}
    _compare_held_facts(SourceSpec(kind="nwb", root=Path("."), owns=()), source, held, notes, {})
    assert notes == [
        "session.task_name is 'foraging' in the packet and nwb states 'reversal'; the packet's value is kept"
    ]


def test_a_source_naming_another_subject_refuses_the_amendment():
    source = _stating(**{"subject.subject_id": "786867"})
    with pytest.raises(SourceDefect, match="keeps the packet's value"):
        _compare_held_facts(
            SourceSpec(kind="nwb", root=Path("."), owns=()), source, {"subject.subject_id": "776259"}, [], {}
        )

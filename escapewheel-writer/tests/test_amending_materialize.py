"""An amendment that derives: a materializer run over the staged amended packet (Part 05 §8, §15)."""

import json
from pathlib import Path

from escapewheel_reader import open_packet

from escapewheel_writer import PacketWriter
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.session import build, commit_arguments
from tests.builders import amending_recipe, session_recipe, session_sources
from tests.conftest import REGISTRY, REGISTRY_CONTEXT

SCOPED = {"scope_kind": "core.sessions", "scope": "s001"}
SPIKE_EVENTS = "analysis.spike_events"
MATERIALIZE = f'\n[[materialize]]\nresource = "{SPIKE_EVENTS}"\n'


def _run(name, activity="import", **more):
    return {
        "processing_run_id": name,
        "session_id": "s001",
        "activity_type": activity,
        "status": "succeeded",
        "started_at": "2026-08-27T00:00:00Z",
        "software_name": "escapewheel_writer",
        "software_version": "0.0.0",
        **more,
    }


def _deriving(name):
    """A materializer recording a run named for what the packet it is handed holds."""

    def derive(packet, target):
        resources = len(packet.resources())
        runs = packet.table("core.processing_runs").num_rows
        target.add("core.processing_runs", [_run(f"{name}.{resources}.{runs}", "materialization", **SCOPED)])

    return derive


def _runs(root: Path) -> dict[int, dict]:
    return {r["processing_run_id"]: r for r in open_packet(root).table("core.processing_runs").to_pylist()}


def _preferred(root: Path) -> dict[str, str]:
    """Each preference's activity, and the name of the run it prefers."""
    runs = _runs(root)
    rows = open_packet(root).table("core.preferred_runs").to_pylist()
    return {p["activity_type"]: runs[p["processing_run_id"]]["processing_run_name"] for p in rows}


def _entries(root: Path) -> dict[str, dict]:
    return {e["resource_id"]: e for e in json.loads((root / "packet.json").read_text())["resources"]}


def test_amendments_with_and_without_materializers(tmp_path, minimal):
    """Part 05 §12: each run an amendment adds to a held run's scope is resolved by a preference."""
    root = tmp_path / "s001"
    writer = PacketWriter(REGISTRY_CONTEXT, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.add("core.processing_runs", [_run("run_import")])
    assert writer.commit(root, materialize=[_deriving("first")]).passed

    # Each materializer is handed the packet as staged before either derives.
    amending = PacketWriter(REGISTRY_CONTEXT, packet_id="s001")
    assert amending.amend(root, materialize=[_deriving("second"), _deriving("third")]).passed
    names = {r["processing_run_name"] for r in _runs(root).values()}
    assert names == {"run_import", "first.4.1", "second.4.2", "third.4.2"}
    # Two added runs share the held run's scope and one row resolves the key; which is not tested.
    assert _preferred(root)["materialization"] in {"second.4.2", "third.4.2"}
    chosen = _preferred(root)["materialization"]

    # A curation run in a scope holding no curation is no alternative.
    curating = PacketWriter(REGISTRY_CONTEXT, packet_id="s001")
    curating.add("core.processing_runs", [_run("scoped", "curation", **SCOPED)])
    assert curating.amend(root).passed
    assert _preferred(root) == {"materialization": chosen}

    def curating_again(packet, target):
        target.add("core.processing_runs", [_run("scoped_again", "curation", **SCOPED)])

    deriving = PacketWriter(REGISTRY_CONTEXT, packet_id="s001")
    assert deriving.amend(root, materialize=[curating_again]).passed
    assert _preferred(root) == {"materialization": chosen, "curation": "scoped_again"}
    assert json.loads((root / "packet.json").read_text())["packet_version"] == "0.1.3"


def _derived_then_amended(tmp_path: Path, *, materializing: bool) -> Path:
    """Commit a build deriving spike events, then add a curation by an amending build."""
    sorted_root, raw = session_sources(tmp_path)
    path = session_recipe(tmp_path, sorted_root, raw)
    path.write_text(path.read_text() + MATERIALIZE)
    recipe = Recipe.load(path)
    assert build(recipe, REGISTRY).commit(recipe.out, **commit_arguments(recipe)).passed
    assert SPIKE_EVENTS in _entries(recipe.out)

    path = amending_recipe(tmp_path, sorted_root)
    if materializing:
        path.write_text(path.read_text() + MATERIALIZE)
    recipe = Recipe.load(path)
    assert build(recipe, REGISTRY).amend(recipe.out, **commit_arguments(recipe)).passed
    return recipe.out


def test_an_amending_build_removes_what_it_does_not_derive_again(tmp_path):
    """Part 05 §15.2: the curation adds spike events, so spike events derived from the old ones go."""
    out = _derived_then_amended(tmp_path, materializing=False)
    assert SPIKE_EVENTS not in _entries(out)


def test_an_amending_build_derives_again_from_the_amended_packet(tmp_path):
    """Part 05 §8: the derived resource replaces the packet's, at a path of its own (Part 03 §9)."""
    out = _derived_then_amended(tmp_path, materializing=True)
    entry = _entries(out)[SPIKE_EVENTS]
    assert entry["uri"] == "tables/analysis/spike_events.0.1.1.parquet"
    packet = open_packet(out)
    assert packet.table(SPIKE_EVENTS).num_rows == packet.table("core.spike_events").num_rows
    rederived = "materialize.analysis.spike_events.2"
    assert rederived in {r["processing_run_name"] for r in _runs(out).values()}
    assert _preferred(out)["materialization"] == rederived

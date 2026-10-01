"""A replacing build: a recipe whose `[packet].replaces` names the packets it replaces (Part 05 §9.3)."""

import argparse
import hashlib
import json
from pathlib import Path

import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import check_table, validate

from escapewheel_writer.errors import RecipeFault, RecipeUnsound, ReplacementRefused, UsageError, UsageFault
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.replacing import read_replaced
from escapewheel_writer.scripts.cli import register
from escapewheel_writer.session import build
from tests.conftest import REGISTRY
from tests.test_amending_build import _amending, packet  # noqa: F401
from tests.test_build_end_to_end import _recipe

CORE = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"


def _replacing(root: Path, *entries: str, out: str = "replacement") -> Path:
    """The packet fixture's recipe, rebuilt into `out` and naming `entries` as the packets it replaces."""
    path = _recipe(root, root / "sorted", root / "raw")
    text = path.read_text().replace(f'out = "{root}/packet"', f'out = "{root}/{out}"\nreplaces = {json.dumps(entries)}')
    path.write_text(text)
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_a_replacement_of_its_own_packet_records_it_at_the_next_major_version(packet):  # noqa: F811
    root, _ = packet
    recipe = Recipe.load(_replacing(root, "packet"))
    assert build(recipe, REGISTRY).commit(recipe.out).passed
    manifest = json.loads((recipe.out / "packet.json").read_text())
    assert manifest["packet_version"] == "1.0.0"
    assert manifest["replaces"] == [
        {"packet_id": "s1", "packet_version": "0.1.0", "sha256": _sha(root / "packet" / "packet.json")}
    ]
    report = validate(open_packet(recipe.out), replaced=[root / "packet"])
    about_replacing = {check_table.PACKET_REPLACES_MAJOR_VERSION.id, check_table.PACKET_REPLACES_MISMATCH.id}
    assert report.passed and not [f for f in report.findings if f.check in about_replacing]


def test_a_recipe_naming_no_packet_records_no_replaces(packet):  # noqa: F811
    root, _ = packet
    assert "replaces" not in json.loads((root / "packet" / "packet.json").read_text())


@pytest.mark.parametrize(
    ("entries", "fault", "named"),
    [
        (("absent",), RecipeFault.REPLACED_UNREADABLE, "absent: "),
        (("packet", "packet/packet.json"), RecipeFault.REPLACED_TWICE, "packet and packet/packet.json "),
    ],
    ids=["unreadable", "one-manifest-twice"],
)
def test_a_build_refuses_what_it_cannot_replace_before_any_source_opens(packet, entries, fault, named):  # noqa: F811
    root, _ = packet
    recipe = Recipe.load(_replacing(root, *entries))
    with pytest.raises(RecipeUnsound) as unsound:
        build(recipe, REGISTRY)
    with pytest.raises(ReplacementRefused) as refused:
        read_replaced(entries, root)
    (problem,) = refused.value.problems
    assert problem.code is fault
    assert problem.message.startswith(named)
    assert unsound.value.problems == [problem]


def test_an_entry_whose_identity_fails_the_manifest_schema_is_refused(tmp_path):
    (tmp_path / "old.json").write_text(json.dumps({"packet_id": "s1"}))
    with pytest.raises(ReplacementRefused) as refused:
        read_replaced(["old.json"], tmp_path)
    assert [p.code for p in refused.value.problems] == [RecipeFault.REPLACED_NO_IDENTITY]


def test_a_recipe_both_replacing_and_amending_is_refused(packet):  # noqa: F811
    root, sorted_root = packet
    path = _amending(root, sorted_root)
    path.write_text(path.read_text().replace('amends = "0.1.0"', 'amends = "0.1.0"\nreplaces = ["packet"]'))
    with pytest.raises(RecipeUnsound) as refused:
        build(Recipe.load(path), REGISTRY)
    assert RecipeFault.REPLACES_AND_AMENDS in {p.code for p in refused.value.problems}


def test_an_amendment_keeps_the_major_version(packet):  # noqa: F811
    root, sorted_root = packet
    recipe = Recipe.load(_amending(root, sorted_root))
    with pytest.raises(UsageError) as refused:
        build(recipe, REGISTRY).amend(recipe.out, packet_version="1.0.0")
    assert refused.value.code is UsageFault.VERSION_MAJOR_CHANGED


def test_an_amendment_retains_the_exact_bytes_it_supersedes(packet):  # noqa: F811
    """A replacement names a version by its manifest's SHA-256, so a re-serialised copy would not match."""
    root, sorted_root = packet
    manifest = root / "packet" / "packet.json"
    manifest.write_text(json.dumps(json.loads(manifest.read_text())))
    published = manifest.read_bytes()
    recipe = Recipe.load(_amending(root, sorted_root))
    assert build(recipe, REGISTRY).amend(recipe.out).passed
    assert (root / "packet" / "manifests" / "0.1.0.json").read_bytes() == published
    assert (root / "packet" / "manifests" / "0.1.1.json").read_bytes() == manifest.read_bytes()


def test_import_warns_of_each_resource_a_named_packet_had_and_the_replacement_lacks(packet, capsys):  # noqa: F811
    root, _ = packet
    manifest_path = root / "packet" / "packet.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["resources"].append({**manifest["resources"][0], "resource_id": "core.gone"})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    parser = argparse.ArgumentParser()
    register(parser.add_subparsers())
    args = parser.parse_args(["import", str(_replacing(root, "packet")), "--registry", str(CORE)])
    assert args.func(args) == 0
    assert "warning: 1 resource(s) in packet are not in this build:\n  lost  core.gone" in capsys.readouterr().err

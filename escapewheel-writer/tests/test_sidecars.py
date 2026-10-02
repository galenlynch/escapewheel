"""Sidecars a recipe lists: catalog rows, scope rows and the payload or reference each row binds (Part 02 §12.10)."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import Level

from escapewheel_writer import reading, serving
from escapewheel_writer.bindings import ExternalResource
from escapewheel_writer.errors import (
    AmendmentFault,
    AmendmentRefused,
    CommitRefused,
    RecipeFault,
    RecipeUnsound,
    SourceDefect,
    SourceFault,
)
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.session import build
from escapewheel_writer.sources.sidecars import SidecarSource
from tests.conftest import REGISTRY

SIDECARS = ("core.sidecars", "core.sidecar_scopes", "core.sidecar_instances")

#: The core registry the version before sidecars: the same document without the three declarations.
EARLIER = copy.deepcopy(REGISTRY)
for _resource in SIDECARS:
    del EARLIER["resources"][_resource]
EARLIER["registry_version"] = "0.14.0"

RECIPE = """
[packet]
id = "s1"
out = "{out}"
{amends}
{session}
{source}"""

SOURCE = """
[[source]]
kind = "sidecars"
root = "{root}"
{owns}
{listed}
"""

SESSION = """
[session]
session_id = "s1"
subject_id = "m001"
session_start_time = "2026-08-27T00:00:00Z"

[subject]
subject_id = "m001"
species = "Mus musculus"
sex = "male"

[[clock]]
clock_id = "harp"
name = "HARP"
tick_rate_num = 31250
origin = "harp epoch"
"""

README = """
[[source.sidecars]]
resource_id = "core.readme"
path = "README.md"
media_type = "text/markdown"
"""

VIEWER = """
[[source.sidecars]]
resource_id = "core.viewer_state"
path = "viewer"
sidecar_type = "viewer_state"
description = "Saved state of a viewer"

[[source.sidecars.scopes]]
scope_kind = "core.subjects"
scope = "m001"
"""

PROTOCOL = """
[[source.sidecars]]
resource_id = "core.protocol"
uri = "https://example.org/protocols/surgery.pdf"

[[source.sidecars.scopes]]
scope_kind = "core.sessions"
scope = "s1"
"""


def _recipe(
    tmp_path: Path, listed: str | None, *, amends: str = "", owns: str = "", name: str = "recipe.toml"
) -> Recipe:
    """A recipe listing `listed` under a sidecar source, or naming no sidecar source where it is None."""
    root = tmp_path / "docs"
    root.mkdir(exist_ok=True)
    (root / "README.md").write_text("# s1\n")
    (root / "viewer").mkdir(exist_ok=True)
    (root / "viewer" / "state.json").write_text('{"zoom": 2}\n')
    path = tmp_path / name
    path.write_text(
        RECIPE.format(
            out=tmp_path / "packet",
            amends=f'amends = "{amends}"' if amends else "",
            session='[session]\nsession_id = "s1"\n' if amends else SESSION,
            source="" if listed is None else SOURCE.format(root=root, owns=owns, listed=listed),
        )
    )
    return Recipe.load(path)


def _passed(report) -> None:
    assert report.passed, [f"{f.check}: {f.message}" for f in report.findings if f.level == Level.ERROR]


def _commit(recipe: Recipe, registry=REGISTRY, *, amend: bool = False) -> None:
    """Build and commit or amend, failing with the findings rather than a staging path."""
    session = build(recipe, registry)
    try:
        _passed(session.amend(recipe.out) if amend else session.commit(recipe.out))
    except CommitRefused as refused:
        pytest.fail(str([f"{f.check}: {f.message}" for f in refused.report.findings if f.level == Level.ERROR]))


def _entries(out: Path) -> dict[str, dict]:
    manifest = json.loads((out / "packet.json").read_text())
    return {entry["resource_id"]: entry for entry in manifest["resources"]}


def test_a_file_a_directory_and_a_reference_are_each_bound_to_their_row(tmp_path):
    recipe = _recipe(tmp_path, README + VIEWER + PROTOCOL)
    _commit(recipe)
    packet = open_packet(recipe.out)
    listed = {row["resource_id"]: row for row in packet.table("core.sidecars").to_pylist()}
    assert sorted(listed) == ["core.protocol", "core.readme", "core.viewer_state"]
    assert listed["core.readme"]["media_type"] == "text/markdown"
    assert listed["core.protocol"]["sidecar_type"] is None and listed["core.protocol"]["media_type"] is None
    scopes = sorted(
        (r["resource_id"], r["scope_kind"], r["scope"]) for r in packet.table("core.sidecar_scopes").to_pylist()
    )
    assert scopes == [("core.protocol", "core.sessions", "s1"), ("core.viewer_state", "core.subjects", "m001")]
    entries = _entries(recipe.out)
    assert entries["core.readme"]["declaration_id"] == "core.sidecar_instances"
    assert entries["core.readme"]["uri"] == "opaque/core.readme/README.md"
    assert (recipe.out / "opaque" / "core.readme" / "README.md").read_text() == "# s1\n"
    assert entries["core.viewer_state"]["uri"] == "opaque/core.viewer_state/viewer"
    assert (recipe.out / "opaque" / "core.viewer_state" / "viewer" / "state.json").is_file()
    assert entries["core.protocol"] == {
        "resource_id": "core.protocol",
        "declaration_id": "core.sidecar_instances",
        "uri": "https://example.org/protocols/surgery.pdf",
        "validation_state": entries["core.protocol"]["validation_state"],
        "external": True,
    }


def test_a_copy_of_a_recorded_source_file_is_listed_and_its_row_kept(tmp_path):
    """Part 02 §2.2: listing a file the import read records no dependence, and removes no provenance."""
    recipe = _recipe(tmp_path, '\n[[source.sidecars]]\nresource_id = "core.inputs"\npath = "."\n')
    _commit(recipe)
    packet = open_packet(recipe.out)
    root = str(tmp_path / "docs")
    assert root in {row["uri"] for row in packet.table("core.source_files").to_pylist()}
    copied = recipe.out / "opaque" / "core.inputs" / "docs" / "README.md"
    assert copied.read_bytes() == (tmp_path / "docs" / "README.md").read_bytes()


CONTRIBUTES = 'contributes = ["core.sidecars", "core.sidecar_scopes"]'


def _two_sources(tmp_path, monkeypatch, contributes: str) -> Recipe:
    """A second source kind listing sidecars of its own, beside the built-in one."""
    from escapewheel_writer.sources import ADAPTERS

    class More(SidecarSource):
        pass

    monkeypatch.setitem(ADAPTERS, "more_sidecars", More)
    second = tmp_path / "second"
    second.mkdir()
    (second / "NOTES.txt").write_text("notes\n")
    extra = (
        f'\n[[source]]\nkind = "more_sidecars"\nroot = "{second}"\n{contributes}\n'
        '\n[[source.sidecars]]\nresource_id = "core.notes"\npath = "NOTES.txt"\n'
    )
    return _recipe(tmp_path, README + extra, owns=contributes)


def test_two_sources_each_contribute_sidecars(tmp_path, monkeypatch):
    """Part 05 §3.3: each entry names both tables under `contributes`, and both sources' rows are kept."""
    recipe = _two_sources(tmp_path, monkeypatch, CONTRIBUTES)
    _commit(recipe)
    listed = {row["resource_id"] for row in open_packet(recipe.out).table("core.sidecars").to_pylist()}
    assert listed == {"core.readme", "core.notes"}


def test_two_sources_left_owning_the_sidecars_are_refused(tmp_path, monkeypatch):
    """Part 05 §3.4: without `contributes`, two entries are each left owning both tables."""
    with pytest.raises(RecipeUnsound) as refused:
        build(_two_sources(tmp_path, monkeypatch, ""), REGISTRY)
    assert {p.code for p in refused.value.problems} == {RecipeFault.SEVERAL_OWNERS}


def test_an_amending_build_adds_sidecars_to_a_packet_bound_to_the_earlier_registry(tmp_path):
    """Part 05 §4.3: a documentation row whose key the packet does not hold is added, and again on the result."""
    first = _recipe(tmp_path, None, name="first.toml")
    _commit(first, EARLIER)
    assert json.loads((first.out / "packet.json").read_text())["registries"]["core"]["version"] == "0.14.0"

    amend = _recipe(tmp_path, README, amends="0.1.0", name="amend.toml")
    _commit(amend, amend=True)
    manifest = json.loads((amend.out / "packet.json").read_text())
    assert manifest["registries"]["core"]["version"] == "0.15.0"
    assert [r["resource_id"] for r in open_packet(amend.out).table("core.sidecars").to_pylist()] == ["core.readme"]

    again = _recipe(tmp_path, README + VIEWER, amends=manifest["packet_version"], name="again.toml")
    _commit(again, amend=True)
    packet = open_packet(again.out)
    assert sorted(r["resource_id"] for r in packet.table("core.sidecars").to_pylist()) == [
        "core.readme",
        "core.viewer_state",
    ]
    assert [r["resource_id"] for r in packet.table("core.sidecar_scopes").to_pylist()] == ["core.viewer_state"]
    held = hashlib.sha256((again.out / "opaque" / "core.readme" / "README.md").read_bytes()).hexdigest()
    assert _entries(again.out)["core.readme"]["digest"]["value"] == held


def test_an_amending_build_refuses_a_held_sidecar_described_otherwise(tmp_path):
    """Part 05 §4.3: a documentation row sharing a held key and differing from it is refused."""
    first = _recipe(tmp_path, README, name="first.toml")
    _commit(first)
    amend = _recipe(
        tmp_path, README.replace('media_type = "text/markdown"', 'description = "other"'), amends="0.1.0", name="a.toml"
    )
    with pytest.raises(AmendmentRefused) as refused:
        build(amend, REGISTRY).amend(amend.out)
    assert (refused.value.code, refused.value.resource_id) == (AmendmentFault.CHANGES_HELD, "core.sidecars")


@pytest.mark.parametrize(
    ("listed", "fault"),
    [
        ('\n[[source.sidecars]]\npath = "README.md"\n', SourceFault.SIDECAR_UNSTATED),
        ('\n[[source.sidecars]]\nresource_id = "core.x"\n', SourceFault.SIDECAR_UNSTATED),
        (
            '\n[[source.sidecars]]\nresource_id = "core.x"\npath = "README.md"\nuri = "https://example.org/x"\n',
            SourceFault.SIDECAR_UNSTATED,
        ),
        ('\n[[source.sidecars]]\nresource_id = "core.x"\npath = "absent.md"\n', SourceFault.SIDECAR_ABSENT),
    ],
)
def test_a_sidecar_no_row_can_be_made_from_is_refused(tmp_path, listed, fault):
    recipe = _recipe(tmp_path, listed)
    with pytest.raises(SourceDefect) as refused:
        build(recipe, REGISTRY).commit(recipe.out)
    assert refused.value.code is fault


def test_a_delivered_reference_binds_the_row_carrying_its_resource_id(tmp_path):
    """Part 12 §5: across a protocol, a referenced sidecar is an entry of the resource document."""
    uri = "https://example.org/protocols/surgery.pdf"
    listed = [
        {"resource_id": "core.protocol", "uri": uri},
        {"resource_id": "core.readme", "uri": "https://example.org/r"},
    ]
    source = SidecarSource(tmp_path, sidecars=listed)
    document = serving.referenced(source)
    assert document is not None
    rows = serving.as_table(source.records()["core.sidecars"][:1])
    got = reading.Delivered("sidecars", {"core.sidecars": rows}, referenced=document["resources"])
    assert got.external_resources() == {"core.protocol": ExternalResource("core.sidecar_instances", uri)}
    assert got.unresolved() == ["core.readme"]

"""A build writes no credential it recognizes in a recipe (Part 05 §3.2, §3.5, §7)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, ClassVar
from urllib.parse import urlsplit

import pytest
from escapewheel_reader import open_packet

from escapewheel_writer.bindings import ExternalMedia
from escapewheel_writer.errors import RecipeFault, RecipeUnsound
from escapewheel_writer.recipe import Recipe
from escapewheel_writer.secrets import REDACTED, as_returned, redacted, stated_userinfo, without_userinfo
from escapewheel_writer.session import build
from escapewheel_writer.writer import PacketWriter
from tests.builders import problems_coded, write_recipe

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
    recipe = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='key = "AKIA...", secret = "xyz"')))
    refused = problems_coded(recipe.check(registry), RecipeFault.CREDENTIAL, "error")
    assert ["storage_options.key" in p.message for p in refused] == [True, False]
    assert all("[[source]] sorter" in p.message for p in refused), "the refusal names the source"
    assert not any(value in p.message for p in refused for value in ("AKIA...", "xyz")), "and not the value"


def test_a_reference_to_a_credential_is_not_one(tmp_path, registry):
    """A profile names where the secret is; the environment holds it and nothing crosses."""
    recipe = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='profile = "aind", anon = false')))
    assert not problems_coded(recipe.check(registry), RecipeFault.CREDENTIAL)


def test_a_token_that_names_a_mode_is_not_a_credential(tmp_path, registry):
    """gcsfs reads a public bucket with `token = "anon"`, so the name alone does not decide."""
    mode = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='token = "anon"')))
    assert not problems_coded(mode.check(registry), RecipeFault.CREDENTIAL)
    real = Recipe.load(write_recipe(tmp_path, SIGNED.format(options='token = "ya29.a0..."'), "signed.toml"))
    assert problems_coded(real.check(registry), RecipeFault.CREDENTIAL)


def test_what_a_run_records_carries_no_credential():
    """Part 05 §3.2: a marker under a member's name, a URI less its userinfo, and no other difference."""
    document = {
        "source": [
            {"kind": "sorter", "storage_options": {"key": "AKIA...", "anon": False}},
            {"kind": "nwb", "root": "/data/session.nwb", "mirrors": ["s3://AKIA:xyz@bucket/a", "/data/b"]},
        ],
        "session": {"session_id": "s001", "key": "left-handed", "notes": "see https://alice:xyz@host/a"},
    }
    clean = redacted(document)
    assert clean["source"][0]["storage_options"] == {"key": REDACTED, "anon": False}
    assert clean["source"][1] == {**document["source"][1], "mirrors": ["s3://bucket/a", "/data/b"]}
    assert clean["session"] == {**document["session"], "key": REDACTED}, "a member is named anywhere in the recipe"
    assert document["source"][0]["storage_options"]["key"] == "AKIA...", "the original is untouched"


@pytest.mark.parametrize(
    ("stated", "written"),
    [
        ("s3://AKIA:xyz@bucket/prefix", "s3://bucket/prefix"),
        ("https://alice@host:8443/a?as=b@c", "https://host:8443/a?as=b@c"),
        ("s3://AKIA:x@yz@bucket/prefix", "s3://bucket/prefix"),
        ("s3://bucket/prefix@v2", "s3://bucket/prefix@v2"),
        ("/data/alice@host/session.nwb", "/data/alice@host/session.nwb"),
    ],
    ids=["a-pair", "a-name-alone", "an-unencoded-at", "an-at-in-the-path", "a-local-path"],
)
def test_a_uri_is_written_without_its_userinfo(stated, written):
    """Part 05 §7: the whole userinfo goes and nothing stands in its place, so the result still parses."""
    assert without_userinfo(stated) == written
    assert urlsplit(written).username is None
    assert urlsplit(written)[2:] == urlsplit(stated)[2:], "the path and the query are as stated"


def test_a_returned_uri_loses_only_userinfo_the_recipe_states():
    """Part 05 §7: the same component, whatever host the recipe stated it for."""
    stated = stated_userinfo({"source": [{"root": "s3://AKIA:xyz@bucket/a", "args": ["https://alice@host/b"]}]})
    assert stated == {"AKIA:xyz", "alice"}
    assert as_returned("s3://AKIA:xyz@mirror/a/cam.mp4", stated) == "s3://mirror/a/cam.mp4"
    assert as_returned("s3://bob:xyz@bucket/a/cam.mp4", stated) == "s3://bob:xyz@bucket/a/cam.mp4"
    assert as_returned("cam.mp4", stated) == "cam.mp4"


# -- a build writes no credential it recognizes ----------------------------------------------

#: A root stating userinfo, and the same root less it.
ROOT = "s3://AKIAEXAMPLE:hunter2@private/ecephys"
BARE = "s3://private/ecephys"

HEAD = """
[packet]
id = "s001"
out = "{out}"
{packet}
[session]
session_id = "s001"
"""

FACTS = """subject_id = "m001"
session_start_time = "2026-08-27T00:00:00Z"

[subject]
subject_id = "m001"
species = "Mus musculus"
sex = "male"

[[clock]]
clock_id = "harp"
name = "harp"
tick_rate_num = 31250
origin = "harp_epoch"
"""


class Cams:
    """An adapter referencing one video at a URI stating userinfo, and taking an `api_key`."""

    PROTOCOLS = ("files-v0.1",)
    PRODUCES = frozenset({"core.media_assets"})
    CONTRIBUTES: frozenset[str] = frozenset()
    STATES: ClassVar[dict[str, str]] = {}
    NEEDS = ("root", "session_id")
    ACCEPTS: tuple[str, ...] = ("api_key",)
    CONSUMES: tuple[str, ...] = ()

    #: The root each construction was given, so a test can tell that no source was opened.
    opened: ClassVar[list[str]] = []

    def __init__(self, root: Any, *, session_id: str, api_key: str | None = None) -> None:
        self.session_id = session_id
        self.notes: list[str] = []
        Cams.opened.append(str(root))

    def records(self) -> dict[str, list[dict[str, Any]]]:
        row = {"session_id": self.session_id, "media_asset_id": "cam", "resource_id": "core.cam"}
        return {"core.media_assets": [{**row, "media_asset_name": "cam"}]}

    def external_media(self) -> dict[str, ExternalMedia]:
        referenced = ExternalMedia(
            media_asset_id="cam", declaration_id="core.media_asset_instances", uri=f"{ROOT}/cam.mp4"
        )
        return {"core.cam": referenced}


class Rows(Cams):
    """The same adapter referencing nothing, for a source that only states a root."""

    PRODUCES: frozenset[str] = frozenset()

    def records(self) -> dict[str, list[dict[str, Any]]]:
        return {}

    def external_media(self) -> dict[str, ExternalMedia]:
        return {}


@pytest.fixture
def adapters(monkeypatch):
    """Register the two adapters under the kinds the recipes below name."""
    monkeypatch.setattr("escapewheel_writer.sources.discovered", lambda: {"cams": Cams, "rows": Rows})
    Cams.opened.clear()


def _source(kind: str, root: str, option: str = "") -> str:
    """A recipe's entry for one of the two kinds, run in this process."""
    return f'\n[[source]]\nkind = "{kind}"\nroot = "{root}"\nin_process = true\n{option}'


def _stated(kind: str, root: str, **options: Any) -> dict[str, Any]:
    """What `_source` states, as a recorded recipe holds it."""
    return {"kind": kind, "root": root, "in_process": True, **options}


def _recipe(tmp_path, sources: str, *, amends: str | None = None, packet: str = "", facts: str = FACTS) -> Recipe:
    packet = packet if amends is None else f'amends = "{amends}"\n'
    path = tmp_path / "session.toml"
    path.write_text(HEAD.format(out=tmp_path / "packet", packet=packet) + ("" if amends else facts) + sources)
    return Recipe.load(path)


def _rows(root, resource_id: str) -> list[dict[str, Any]]:
    return open_packet(root).table(resource_id).to_pylist()


def _import(root) -> dict[str, Any]:
    """The newest import run a packet records, its `parameters` decoded."""
    run = [row for row in _rows(root, "core.processing_runs") if row["activity_type"] == "import"][-1]
    return {**run, "parameters": json.loads(run["parameters"])}


def _written(root) -> str:
    """Every row of every table a packet holds and its manifest, as text to search for a value."""
    manifest = json.loads((root / "packet.json").read_text())
    tables = [entry["resource_id"] for entry in manifest["resources"] if entry["uri"].endswith(".parquet")]
    return json.dumps([manifest, *(_rows(root, table) for table in tables)], default=str)


def _digest(recipe: Recipe) -> str:
    """Part 05 §3.2: `code_uri` is the digest of the recipe as the build read it."""
    return f"sha256:{hashlib.sha256(recipe.path.read_bytes()).hexdigest()}"


def test_a_build_refuses_a_storage_credential_before_it_opens_a_source(tmp_path, registry, adapters):
    """Part 05 §3.5: refused naming the source and the member and not the value, no adapter constructed."""
    source = _source("cams", BARE, 'storage_options = { secret = "hunter2" }\n')
    with pytest.raises(RecipeUnsound) as refused:
        build(_recipe(tmp_path, source), registry)
    (problem,) = problems_coded(refused.value.problems, RecipeFault.CREDENTIAL, "error")
    assert "[[source]] cams sets storage_options.secret" in problem.message
    assert "hunter2" not in problem.message and "hunter2" not in str(refused.value)
    assert Cams.opened == []


def test_a_credential_in_another_option_is_recorded_as_the_marker(tmp_path, registry, adapters):
    """Part 05 §3.2: `[redacted]` under the option's name, the value nowhere in the record."""
    recipe = _recipe(tmp_path, _source("rows", "raw", 'api_key = "hunter2"\n'))
    assert build(recipe, registry).commit(recipe.out).passed
    run = _import(recipe.out)
    assert run["parameters"]["recipe"]["source"] == [_stated("rows", "raw", api_key=REDACTED)]
    written = _written(recipe.out)
    assert REDACTED in written and "hunter2" not in written
    assert run["code_uri"] == _digest(recipe)


def test_a_credential_outside_a_source_entry_is_recorded_as_the_marker(tmp_path, registry, adapters):
    """Part 05 §3.2: a member is recognized by its name wherever the recipe states it, an array's URI too."""
    limits = '\n[commit]\ntoken = "hunter2"\nmirrors = ["https://alice:hunter2@host/a", "plain"]\n'
    recipe = _recipe(tmp_path, _source("rows", "raw") + limits)
    assert build(recipe, registry).commit(recipe.out).passed
    run = _import(recipe.out)
    assert run["parameters"]["recipe"]["commit"] == {"token": REDACTED, "mirrors": ["https://host/a", "plain"]}
    assert "hunter2" not in _written(recipe.out)
    assert run["code_uri"] == _digest(recipe)


def test_a_row_the_build_composes_holds_a_stated_uri_without_userinfo(tmp_path, registry, adapters):
    """Part 05 §3.2, §7: the manifest and a recipe-supplied row are the build's own, as the record is."""
    recipe = _recipe(
        tmp_path,
        _source("rows", "raw"),
        packet='description = "https://alice:hunter2@host/about"\n',
        facts=FACTS.replace('sex = "male"', 'sex = "male"\nstrain = "https://alice:hunter2@host/strain"'),
    )
    assert build(recipe, registry).commit(recipe.out).passed
    assert json.loads((recipe.out / "packet.json").read_text())["description"] == "https://host/about"
    (subject,) = _rows(recipe.out, "core.subjects")
    assert subject["strain"] == "https://host/strain"
    run = _import(recipe.out)
    assert run["parameters"]["recipe"]["subject"]["strain"] == "https://host/strain"
    assert "hunter2" not in _written(recipe.out)
    assert run["code_uri"] == _digest(recipe)


def test_a_token_naming_a_mode_is_recorded_as_stated(tmp_path, registry, adapters):
    """`token = "anon"` names a way to authenticate, so the record holds it and no marker."""
    recipe = _recipe(tmp_path, _source("rows", BARE, 'storage_options = { token = "anon" }\n'))
    assert build(recipe, registry).commit(recipe.out).passed
    run = _import(recipe.out)
    assert run["parameters"]["recipe"]["source"] == [_stated("rows", BARE, storage_options={"token": "anon"})]
    assert run["code_uri"] == _digest(recipe)


def test_a_root_stating_userinfo_is_written_without_it(tmp_path, registry, adapters):
    """Part 05 §7: the source-file row, the manifest entry and the recorded recipe carry no userinfo.

    The adapter is handed the root as stated. No marker stands where the userinfo was, so the
    recorded root, read back, parses as a URI (Part 05 §3.2).
    """
    recipe = _recipe(tmp_path, _source("cams", ROOT))
    assert build(recipe, registry).commit(recipe.out).passed
    assert Cams.opened == [ROOT]
    (file,) = _rows(recipe.out, "core.source_files")
    assert (file["source_file_name"], file["uri"]) == (BARE, BARE)
    manifest = json.loads((recipe.out / "packet.json").read_text())
    (entry,) = [entry for entry in manifest["resources"] if entry["resource_id"] == "core.cam"]
    assert entry["uri"] == f"{BARE}/cam.mp4"
    run = _import(recipe.out)
    assert run["parameters"]["recipe"]["source"] == [_stated("cams", BARE)]
    recorded = urlsplit(run["parameters"]["recipe"]["source"][0]["root"])
    assert (recorded.scheme, recorded.username, recorded.hostname, recorded.path) == ("s3", None, "private", "/ecephys")
    written = _written(recipe.out)
    assert not any(withheld in written for withheld in ("hunter2", "AKIAEXAMPLE", REDACTED))
    assert run["code_uri"] == _digest(recipe)


@pytest.mark.parametrize(
    ("stated", "written"),
    [
        ("s3://AKIAEXAMPLE:hunter2@mirror/ecephys", f"{BARE}/cam.mp4"),
        (BARE, f"{ROOT}/cam.mp4"),
        ("s3://another:secret@private/ecephys", f"{ROOT}/cam.mp4"),
    ],
    ids=["the-same-userinfo", "no-userinfo", "another-userinfo"],
)
def test_a_returned_uri_is_written_without_userinfo_the_recipe_states(tmp_path, registry, adapters, stated, written):
    """Part 05 §7: a returned URI loses the component the recipe states, and no other userinfo.

    Userinfo no URI of the recipe states is no value of the recipe, so the build writes the URI as
    the adapter returned it.
    """
    recipe = _recipe(tmp_path, _source("cams", stated))
    assert build(recipe, registry).commit(recipe.out).passed
    manifest = json.loads((recipe.out / "packet.json").read_text())
    (entry,) = [entry for entry in manifest["resources"] if entry["resource_id"] == "core.cam"]
    assert entry["uri"] == written


def test_a_resolution_document_locates_a_source_without_userinfo(tmp_path, registry, minimal):
    """Part 04 §5.5's document is one more place a root is written (Part 05 §7)."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.add(
        "core.media_assets",
        [{"session_id": "s001", "media_asset_id": "cam", "resource_id": "core.cam", "media_asset_name": "cam"}],
    )
    writer.declare_source("cams", ROOT)
    writer.reference_media(
        "core.cam",
        ExternalMedia(media_asset_id="cam", declaration_id="core.media_asset_instances", uri="cam.mp4", source="cams"),
    )
    root = tmp_path / "s001"
    assert writer.commit(root).passed
    assert json.loads((root / "sources.json").read_text())["sources"] == {"cams": {"uri": BARE}}


def test_roots_differing_only_in_userinfo_are_one_source_file(tmp_path, registry, adapters):
    """Part 05 §7: equal once the userinfo is removed, so one row, which the import names once."""
    recipe = _recipe(tmp_path, _source("cams", ROOT) + _source("rows", BARE))
    assert build(recipe, registry).commit(recipe.out).passed
    assert [row["uri"] for row in _rows(recipe.out, "core.source_files")] == [BARE]
    assert len(_rows(recipe.out, "core.processing_run_inputs")) == 1
    assert _import(recipe.out)["code_uri"] == _digest(recipe)


@pytest.mark.parametrize(
    "stated",
    [ROOT, BARE, "s3://another:secret@private/ecephys"],
    ids=["the-held-userinfo", "no-userinfo", "another-userinfo"],
)
def test_an_amending_build_compares_a_root_after_removing_userinfo(tmp_path, registry, adapters, stated):
    """Part 05 §7: a held row recording userinfo is the row of the same root stated any other way.

    The packet holds one row, as a build that recognized no credential recorded it, so the amending
    build adds none, links its import to that row, and leaves the row's `uri` as recorded.
    """
    recipe = _recipe(tmp_path, _source("rows", "raw"))
    assert build(recipe, registry).commit(recipe.out).passed
    earlier = PacketWriter(registry, packet_id="s001")
    earlier.add("core.source_files", [{"source_file_id": "kept", "uri": ROOT}])
    assert earlier.amend(recipe.out).passed

    amending = _recipe(tmp_path, _source("rows", stated), amends="0.1.1")
    assert build(amending, registry).amend(amending.out).passed
    files = {row["source_file_id"]: row["uri"] for row in _rows(amending.out, "core.source_files")}
    assert sorted(files.values()) == ["raw", ROOT]
    run = _import(amending.out)
    linked = [
        files[row["source_file_id"]]
        for row in _rows(amending.out, "core.processing_run_inputs")
        if row["processing_run_id"] == run["processing_run_id"]
    ]
    assert linked == [ROOT]
    assert run["code_uri"] == _digest(amending)

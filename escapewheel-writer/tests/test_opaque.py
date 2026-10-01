"""A packet-owned opaque resource crosses as its bytes in a directory named by its resource ID (Part 12 §5)."""

import hashlib
import io
import json
import os
import sys
import unicodedata
from pathlib import Path

import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import Verdict, check_table
from escapewheel_validator.stores import listing_digest

from escapewheel_writer import declaration, delivery, opaque
from escapewheel_writer.bindings import ExternalMedia
from escapewheel_writer.errors import DeliveryFailed, PacketOccupied, PayloadFault, PayloadRefused, SourceFault
from escapewheel_writer.opaque import Payload
from escapewheel_writer.writer import PacketWriter
from tests import opaquefixture

PDF = b"%PDF-1.7\n" + bytes(range(256))
QC_NAME = "QC report é.pdf"
QC_URI = "opaque/core.report/QC%20report%20%C3%A9.pdf"

#: An extension declaring one opaque singleton, which binds a payload with no catalog row.
QC = {
    "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
    "registry_id": "qc",
    "registry_version": "0.1.0",
    "logical_standard_version": "escapewheel-logical-v0.1",
    "rule_language": "escapewheel-rule-sql-v0.2",
    "extension_id": "qc",
    "resources": {
        "qc.report": {
            "content_class": "extension",
            "kind": "opaque",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "optional",
        }
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lay(directory: Path, tree: dict) -> None:
    """Write `tree`, a name to bytes or to a nested tree, under `directory`."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, held in tree.items():
        if isinstance(held, dict):
            _lay(directory / name, held)
        else:
            (directory / name).write_bytes(held)


def _row(resource_id: str) -> dict:
    asset = resource_id.split(".", 1)[1]
    return {"session_id": "s001", "media_asset_id": asset, "resource_id": resource_id, "media_asset_name": asset}


def _writer(registry, minimal, rows=(), extensions=()):
    writer = PacketWriter(registry, packet_id="s001", extensions=list(extensions))
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    if rows:
        writer.add("core.media_assets", [_row(resource_id) for resource_id in rows])
    return writer


def _entry(root: Path, resource_id: str) -> dict:
    manifest = json.loads((root / "packet.json").read_text())
    return next(entry for entry in manifest["resources"] if entry["resource_id"] == resource_id)


def _commit_one(tmp_path, registry, minimal, resource_id, payload, *, rows=None, extensions=(), owned=None):
    """Deliver one payload, `payload` being a name to bytes or a tree, and commit it."""
    location = tmp_path / "delivered"
    _lay(location / resource_id, payload)
    writer = _writer(registry, minimal, [resource_id] if rows is None else rows, extensions)
    writer.add_payloads("clips", location, owned=owned)
    root = tmp_path / "s001"
    return root, writer.commit(root)


# -- publication and digest -----------------------------------------------------------------


def test_a_payload_file_is_published_under_its_resource_directory(tmp_path, registry, minimal):
    """Part 12 §5: bound by its directory to the row naming it, digested as a single object."""
    clip = b"\x00\x00\x00\x18ftypmp42" * 100
    root, report = _commit_one(tmp_path, registry, minimal, "core.clip", {"clip.mp4": clip})
    assert report.passed, [(f.check, f.message) for f in report.findings]
    assert _entry(root, "core.clip") == {
        "resource_id": "core.clip",
        "declaration_id": "core.media_asset_instances",
        "uri": "opaque/core.clip/clip.mp4",
        "validation_state": _entry(root, "core.clip")["validation_state"],
        "size_bytes": len(clip),
        "digest": {"algorithm": "sha256", "value": _sha256(clip)},
    }
    assert (root / "opaque" / "core.clip" / "clip.mp4").read_bytes() == clip
    assert sorted(p.name for p in (root / "opaque" / "core.clip").iterdir()) == ["clip.mp4"]


def test_a_payload_directory_is_a_prefix_listed_under_its_own_keys(tmp_path, registry, minimal):
    """Part 03 §10: a directory's digest is the listing value, keyed relative to the payload."""
    first, second = b"\x89PNG first", b"\x89PNG second frame"
    frames = {"0.png": first, "1.png": second}
    root, report = _commit_one(tmp_path, registry, minimal, "core.frames", {"frames": frames})
    assert report.passed, [(f.check, f.message) for f in report.findings]
    entry = _entry(root, "core.frames")
    assert entry["uri"] == "opaque/core.frames/frames"
    assert entry["size_bytes"] == len(first) + len(second)
    expected = listing_digest([("0.png", len(first), _sha256(first)), ("1.png", len(second), _sha256(second))])
    assert entry["digest"] == {"algorithm": "sha256", "value": expected}


def test_a_payload_records_no_format(tmp_path, registry, minimal):
    """Nothing about the payload's name, suffix, or contents is read, so a misleading suffix is kept."""
    root, report = _commit_one(tmp_path, registry, minimal, "core.clip", {"clip.txt": PDF})
    assert report.passed
    entry = _entry(root, "core.clip")
    assert entry["uri"] == "opaque/core.clip/clip.txt"
    assert not {"format", "media_type", "external"} & set(entry)


def test_a_payload_binds_an_extension_s_opaque_singleton(tmp_path, registry, minimal):
    """A directory named by an opaque singleton declaration binds it, with no catalog row."""
    root, report = _commit_one(
        tmp_path, registry, minimal, "qc.report", {"QC.pdf": PDF}, rows=(), extensions=[QC], owned={"qc.report"}
    )
    assert report.passed, [(f.check, f.message) for f in report.findings]
    entry = _entry(root, "qc.report")
    assert (entry["declaration_id"], entry["uri"]) == ("qc.report", "opaque/qc.report/QC.pdf")
    assert entry["digest"]["value"] == _sha256(PDF)


def test_a_name_needing_encoding_is_published_as_it_is_and_read_back(tmp_path, registry, minimal):
    """The name is kept; only the uri is percent-encoded, and the reader and validator decode it."""
    root, report = _commit_one(tmp_path, registry, minimal, "core.report", {QC_NAME: PDF})
    assert report.passed, [(f.check, f.message) for f in report.findings]
    assert _entry(root, "core.report")["uri"] == QC_URI
    published = root / "opaque" / "core.report" / QC_NAME
    assert published.read_bytes() == PDF
    assert Path(open_packet(root).path("core.report")) == published
    assert report.verdict() == Verdict.PASSED


def test_every_name_is_kept_and_a_fragile_one_warned_of(tmp_path, registry, minimal):
    """Part 05 §5.3: names that fold together or that Windows cannot hold are warned of, not changed."""
    nfd = unicodedata.normalize("NFD", "été.png")
    frames = {"a.png": b"a", "A.png": b"A", nfd: b"nfd", "12:00:00.png": b"noon"}
    root, report = _commit_one(tmp_path, registry, minimal, "core.frames", {"frames": frames})
    published = root / "opaque" / "core.frames" / "frames"
    assert sorted(os.listdir(published)) == sorted(frames)
    warned = [f for f in report.findings if f.check == check_table.PHYSICAL_OPAQUE_NAME_PORTABILITY.id]
    assert len(warned) == 2, [(f.check, f.message) for f in report.findings]
    assert report.passed


# -- structural refusals, naming the source and the path ------------------------------------


def _refused(tmp_path, arrange, fault) -> str:
    """Read what `arrange` lays down, requiring one refusal of `fault`, and return its message."""
    location = tmp_path / "delivered"
    location.mkdir()
    arrange(location)
    with pytest.raises(PayloadRefused) as refused:
        opaque.read("clips", location)
    assert refused.value.source == "clips"
    assert str(refused.value).startswith("clips: ") and "Part 12 §5" in str(refused.value)
    (problem,) = refused.value.problems
    assert problem.code is fault
    return problem.message


def test_a_file_directly_in_the_location_is_refused(tmp_path):
    message = _refused(
        tmp_path, lambda here: (here / "clip.mp4").write_bytes(b"x"), PayloadFault.NOT_A_RESOURCE_DIRECTORY
    )
    assert message.startswith(f"{tmp_path / 'delivered' / 'clip.mp4'} ")


def test_a_resource_directory_holding_two_payloads_is_refused(tmp_path):
    message = _refused(
        tmp_path, lambda here: _lay(here / "core.clip", {"a.mp4": b"a", "b.mp4": b"b"}), PayloadFault.NOT_ONE_PAYLOAD
    )
    assert message.startswith(f"{tmp_path / 'delivered' / 'core.clip'} holds 2 payloads")


def test_a_resource_directory_holding_none_is_refused(tmp_path):
    message = _refused(tmp_path, lambda here: (here / "core.clip").mkdir(), PayloadFault.NOT_ONE_PAYLOAD)
    assert message.startswith(f"{tmp_path / 'delivered' / 'core.clip'} holds 0 payloads")


def test_a_symbolic_link_is_refused(tmp_path):
    target = tmp_path / "elsewhere.png"
    target.write_bytes(b"x")

    def arrange(here):
        _lay(here / "core.frames" / "frames", {"0.png": b"0"})
        (here / "core.frames" / "frames" / "1.png").symlink_to(target)

    message = _refused(tmp_path, arrange, PayloadFault.NOT_REGULAR)
    assert message.startswith(f"{tmp_path / 'delivered' / 'core.frames' / 'frames' / '1.png'} is a symbolic link")


def test_an_empty_directory_within_a_payload_is_refused(tmp_path):
    def arrange(here):
        _lay(here / "core.frames" / "frames", {"0.png": b"0"})
        (here / "core.frames" / "frames" / "later").mkdir()

    message = _refused(tmp_path, arrange, PayloadFault.EMPTY_DIRECTORY)
    assert message.startswith(f"{tmp_path / 'delivered' / 'core.frames' / 'frames' / 'later'} ")


def test_a_name_that_is_not_utf8_is_refused(tmp_path):
    def arrange(here):
        _lay(here / "core.clip", {})
        with open(os.path.join(os.fsencode(here / "core.clip"), b"clip\xff.mp4"), "wb") as handle:
            handle.write(b"x")

    message = _refused(tmp_path, arrange, PayloadFault.NAME_UNREPRESENTABLE)
    assert "clip\\xff.mp4: " in message


# -- binding refusals, naming the directory and the resource ID -----------------------------


def _bind_refused(tmp_path, registry, minimal, deliveries, fault, *, rows=(), extensions=(), referenced=None) -> str:
    """Commit `deliveries`, a source to its (resource ID, tree, owned) triples, requiring a refusal.

    Returns the message of the one problem carrying `fault`.
    """
    writer = _writer(registry, minimal, rows, extensions)
    for source, payloads in deliveries.items():
        location = tmp_path / source
        owned = None
        for resource_id, tree, owned in payloads:
            _lay(location / resource_id, tree)
        writer.add_payloads(source, location, owned=owned)
    if referenced is not None:
        writer.reference_media(*referenced)
    root = tmp_path / "s001"
    with pytest.raises(PayloadRefused) as refused:
        writer.commit(root)
    assert not (root / "packet.json").exists() and not (root / "opaque").exists()
    assert "Part 12 §5" in str(refused.value)
    (problem,) = [p for p in refused.value.problems if p.code is fault]
    return problem.message


def test_a_directory_binding_nothing_is_refused(tmp_path, registry, minimal):
    deliveries = {"clips": [("core.nothing", {"a.mp4": b"a"}, None)]}
    message = _bind_refused(tmp_path, registry, minimal, deliveries, PayloadFault.BINDS_NOTHING)
    assert message.startswith(f"clips: {tmp_path / 'clips' / 'core.nothing'} names core.nothing")


def test_a_directory_named_by_a_dense_array_row_is_refused(tmp_path, registry, minimal):
    """Only an opaque family's catalog binds a payload; an array asset crosses as an array."""
    writer = _writer(registry, minimal)
    writer.add(
        "core.array_assets",
        [{"session_id": "s001", "array_asset_id": "lfp", "resource_id": "core.lfp", "array_asset_name": "lfp"}],
    )
    _lay(tmp_path / "clips" / "core.lfp", {"lfp.bin": b"x"})
    writer.add_payloads("clips", tmp_path / "clips")
    with pytest.raises(PayloadRefused) as refused:
        writer.commit(tmp_path / "s001")
    (problem,) = refused.value.problems
    assert problem.code is PayloadFault.BINDS_NOTHING
    assert "names core.lfp" in problem.message


def test_a_resource_id_delivered_by_two_sources_is_refused(tmp_path, registry, minimal):
    message = _bind_refused(
        tmp_path,
        registry,
        minimal,
        {"clips": [("core.clip", {"a.mp4": b"a"}, None)], "more": [("core.clip", {"b.mp4": b"b"}, None)]},
        PayloadFault.DELIVERED_TWICE,
        rows=["core.clip"],
    )
    assert message.startswith("core.clip is delivered as a payload 2 times")
    assert f"clips at {tmp_path / 'clips' / 'core.clip'}" in message
    assert f"more at {tmp_path / 'more' / 'core.clip'}" in message


def test_a_resource_id_delivered_as_a_payload_and_referenced_is_refused(tmp_path, registry, minimal):
    referenced = (
        "core.clip",
        ExternalMedia(media_asset_id="clip", declaration_id="core.media_asset_instances", uri="s3://bucket/clip.mp4"),
    )
    message = _bind_refused(
        tmp_path,
        registry,
        minimal,
        {"clips": [("core.clip", {"a.mp4": b"a"}, None)]},
        PayloadFault.DELIVERED_AND_REFERENCED,
        rows=["core.clip"],
        referenced=referenced,
    )
    assert message.startswith("core.clip ")


def test_an_opaque_catalog_row_nothing_binds_is_refused(tmp_path, registry, minimal):
    message = _bind_refused(
        tmp_path,
        registry,
        minimal,
        {"clips": [("core.clip", {"a.mp4": b"a"}, None)]},
        PayloadFault.ROW_UNBOUND,
        rows=["core.clip", "core.lost"],
    )
    assert message.startswith("core.media_assets row with resource_id core.lost ")


def test_a_directory_naming_a_row_and_a_singleton_is_refused(tmp_path, registry, minimal):
    message = _bind_refused(
        tmp_path,
        registry,
        minimal,
        {"clips": [("qc.report", {"QC.pdf": PDF}, frozenset({"qc.report"}))]},
        PayloadFault.ROW_AND_SINGLETON,
        rows=["qc.report"],
        extensions=[QC],
    )
    assert f"{tmp_path / 'clips' / 'qc.report'} names qc.report" in message


def test_a_singleton_another_source_owns_is_refused(tmp_path, registry, minimal):
    message = _bind_refused(
        tmp_path,
        registry,
        minimal,
        {"more": [("qc.report", {"QC.pdf": PDF}, frozenset({"core.media_assets"}))]},
        PayloadFault.SINGLETON_NOT_OWNED,
        extensions=[QC],
    )
    assert message.startswith("more: delivers a payload for opaque singleton qc.report")


# -- the in-process hand-over ---------------------------------------------------------------


def test_handed_over_bytes_land_as_a_protocol_adapter_would_write_them(tmp_path):
    location = tmp_path / "delivered"
    handed = [
        Payload("core.clip", "clip.mp4", data=b"clip"),
        Payload("core.frames", "frames", files={"0.png": b"0", "deeper/1.png": b"1"}),
    ]
    assert opaque.write(handed, location, "clips") == 2
    assert (location / "core.clip" / "clip.mp4").read_bytes() == b"clip"
    assert (location / "core.frames" / "frames" / "deeper" / "1.png").read_bytes() == b"1"
    found = opaque.read("clips", location)
    assert [(p.resource_id, p.path.name) for p in found] == [("core.clip", "clip.mp4"), ("core.frames", "frames")]


@pytest.mark.parametrize(
    ("handed", "location", "fault", "named"),
    [
        ([Payload("core.clip", "clip.mp4", data=b"x")], None, PayloadFault.NO_LOCATION, ""),
        ([Payload("core.clip", "../clip.mp4", data=b"x")], "here", PayloadFault.NAME_UNREPRESENTABLE, "'../clip.mp4'"),
        ([Payload("core.clip", "..", data=b"x")], "here", PayloadFault.NAME_UNREPRESENTABLE, "'..'"),
        (
            [Payload("core.frames", "frames", files={"a/../b.png": b"x"})],
            "here",
            PayloadFault.NAME_UNREPRESENTABLE,
            "'a/../b.png' holds '..'",
        ),
        ([Payload("core.clip", "clip.mp4")], "here", PayloadFault.NOT_ONE_FORM, "clip.mp4"),
        (
            [Payload("core.clip", "a.mp4", data=b"a"), Payload("core.clip", "b.mp4", data=b"b")],
            "here",
            PayloadFault.NOT_ONE_PAYLOAD,
            "core.clip",
        ),
    ],
    ids=["no-location", "slash", "dot-dot", "segment", "neither", "second-payload"],
)
def test_a_hand_over_a_location_could_not_hold_is_refused(tmp_path, handed, location, fault, named):
    with pytest.raises(PayloadRefused) as refused:
        opaque.write(handed, tmp_path / location if location else None, "clips")
    (problem,) = refused.value.problems
    assert problem.code is fault
    assert named in problem.message
    assert refused.value.source == "clips"


def test_a_hand_over_with_nowhere_to_go_is_refused_over_a_protocol(tmp_path):
    class Handing:
        def records(self):
            return {}

        def staged_payloads(self):
            return [Payload("core.clip", "clip.mp4", data=b"x")]

    with pytest.raises(PayloadRefused) as refused:
        delivery.serve(Handing(), {}, "stream-v0.1", out=io.BytesIO())
    assert refused.value.source == "Handing"
    assert [p.code for p in refused.value.problems] == [PayloadFault.NO_LOCATION]


# -- the build-supplied location and the routes ---------------------------------------------


def test_opaque_location_is_supplied_empty_under_staging_one_per_source(tmp_path):
    """Part 12 §4: supplied empty, since what is found there is bound; apart from `array_location`'s."""
    from escapewheel_writer.recipe import TERMS, SourceSpec
    from escapewheel_writer.session import Context
    from escapewheel_writer.sourcing import filled_terms

    assert "opaque_location" in TERMS
    context = Context(session_id="s001")
    context.staging = tmp_path / "packet" / "staging"
    stale = context.staging / opaque.DELIVERIES / "clips" / "core.clip"
    stale.mkdir(parents=True)
    locations = {
        kind: filled_terms(
            SourceSpec(kind=kind, root=tmp_path, owns=()), None, context, ["opaque_location", "array_location"]
        )
        for kind in ("clips", "more")
    }
    assert locations["clips"]["opaque_location"] == str(context.staging / opaque.DELIVERIES / "clips")
    assert locations["more"]["opaque_location"] == str(context.staging / opaque.DELIVERIES / "more")
    assert locations["clips"]["opaque_location"] != locations["clips"]["array_location"]
    assert not stale.exists() and not stale.parent.exists()
    assert context.opaque_locations == {kind: Path(terms["opaque_location"]) for kind, terms in locations.items()}


def test_opaque_location_is_supplied_only_where_declared(tmp_path):
    from escapewheel_writer.recipe import SourceSpec
    from escapewheel_writer.session import Context
    from escapewheel_writer.sourcing import filled_terms

    context = Context(session_id="s001")
    context.staging = tmp_path / "staging"
    assert "opaque_location" not in filled_terms(
        SourceSpec(kind="plain", root=tmp_path, owns=()), None, context, ["root"]
    )
    assert context.opaque_locations == {}


SESSION = """
[session]
session_id = "s001"
subject_id = "m001"
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

#: How a delivered `Clips` runs: its own process, handed what a build supplies on standard input.
SERVE = """import json, sys
sys.path.insert(0, {here!r})
from escapewheel_writer import delivery
from tests.opaquefixture import Clips
supplied = json.loads(sys.stdin.buffer.read())
source = Clips(supplied["root"], session_id=supplied["session_id"], opaque_location=supplied["opaque_location"])
delivery.serve(source, supplied, sys.argv[1])
"""


def _source(tmp_path, kind, tree, owns, route="in-process"):
    """A recipe's source entry for a `Clips` kind whose root holds `tree`, reached by `route`."""
    root = tmp_path / f"{kind}-root"
    _lay(root, tree)
    body = f'\n[[source]]\nkind = "{kind}"\nroot = "{root}"\nowns = {json.dumps(owns)}\n'
    if route == "in-process":
        return body + "in_process = true\n"
    script = tmp_path / "serve.py"
    script.write_text(SERVE.format(here=str(Path(__file__).resolve().parents[1])))
    document = declaration.document_of(opaquefixture.Clips, kind)
    (tmp_path / f"{kind}.json").write_text(json.dumps(document))
    command = json.dumps([sys.executable, str(script), route])
    return body + f'\n[source.delivery]\ndeclaration = "{kind}.json"\nprotocol = "{route}"\ncommand = {command}\n'


def _build(tmp_path, registry, monkeypatch, sources, *, extensions=None):
    from escapewheel_writer.recipe import Recipe
    from escapewheel_writer.session import build

    monkeypatch.setattr(
        "escapewheel_writer.sources.discovered",
        lambda: {
            "clips": opaquefixture.Clips,
            "more": opaquefixture.Clips,
            "reports": opaquefixture.Reports,
            "plain": opaquefixture.Plain,
            "undeclared": opaquefixture.Undeclared,
        },
    )
    head = f'[packet]\nid = "s001"\nout = "{tmp_path / "packet"}"\n'
    if extensions:
        for name, document in extensions.items():
            (tmp_path / name).write_text(json.dumps(document))
        head += f"extensions = {json.dumps(list(extensions))}\n"
    path = tmp_path / "session.toml"
    path.write_text(head + SESSION + "".join(sources))
    recipe = Recipe.load(path)
    return recipe, build(recipe, registry)


@pytest.mark.parametrize("route", ["in-process", "files-v0.1", "stream-v0.1", "flight-v0.1"])
def test_one_payload_yields_one_entry_whatever_the_route(tmp_path, registry, monkeypatch, route):
    """Part 12 §5: handed over in process or written by an adapter reached by any protocol."""
    if route == "flight-v0.1":
        pytest.importorskip("pyarrow.flight")
    source = _source(tmp_path, "clips", {"core.report": {QC_NAME: PDF}}, ["core.media_assets"], route)
    recipe, writer = _build(tmp_path, registry, monkeypatch, [source])
    report = writer.commit(recipe.out)
    assert report.passed, [(f.check, f.message) for f in report.findings]
    entry = _entry(recipe.out, "core.report")
    assert {k: entry[k] for k in ("declaration_id", "uri", "size_bytes", "digest")} == {
        "declaration_id": "core.media_asset_instances",
        "uri": QC_URI,
        "size_bytes": len(PDF),
        "digest": {"algorithm": "sha256", "value": _sha256(PDF)},
    }
    assert (recipe.out / "opaque" / "core.report" / QC_NAME).read_bytes() == PDF
    assert not (recipe.out / "staging").exists()


def test_a_build_binds_an_owned_singleton(tmp_path, registry, monkeypatch):
    source = _source(tmp_path, "reports", {"qc.report": {"QC.pdf": PDF}}, ["core.media_assets", "qc.report"])
    recipe, writer = _build(tmp_path, registry, monkeypatch, [source], extensions={"qc.json": QC})
    report = writer.commit(recipe.out)
    assert report.passed, [(f.check, f.message) for f in report.findings]
    assert _entry(recipe.out, "qc.report")["uri"] == "opaque/qc.report/QC.pdf"


def test_two_sources_delivering_one_resource_id_are_both_seen_and_refused(tmp_path, registry, monkeypatch):
    """Each source has its own location, so neither payload overwrites the other before binding."""
    sources = [
        _source(tmp_path, "clips", {"core.clip": {"a.mp4": b"a"}}, ["core.media_assets"]),
        _source(tmp_path, "more", {"core.clip": {"b.mp4": b"b"}}, []),
    ]
    recipe, writer = _build(tmp_path, registry, monkeypatch, sources)
    staging = recipe.out / "staging" / opaque.DELIVERIES
    with pytest.raises(PayloadRefused) as refused:
        writer.commit(recipe.out)
    (problem,) = refused.value.problems
    assert problem.code is PayloadFault.DELIVERED_TWICE
    assert problem.message.startswith("core.clip ")
    assert f"clips at {staging / 'clips' / 'core.clip'}" in problem.message
    assert f"more at {staging / 'more' / 'core.clip'}" in problem.message
    assert not (recipe.out / "packet.json").exists()


def test_a_build_refuses_a_singleton_the_recipe_leaves_another_source_owning(tmp_path, registry, monkeypatch):
    sources = [
        _source(tmp_path, "reports", {}, ["core.media_assets", "qc.report"]),
        _source(tmp_path, "more", {"qc.report": {"QC.pdf": PDF}}, []),
    ]
    monkeypatch.setattr(opaquefixture.Clips, "PRODUCES", opaquefixture.Reports.PRODUCES)
    recipe, writer = _build(tmp_path, registry, monkeypatch, sources, extensions={"qc.json": QC})
    with pytest.raises(PayloadRefused) as refused:
        writer.commit(recipe.out)
    (problem,) = refused.value.problems
    assert problem.code is PayloadFault.SINGLETON_NOT_OWNED
    assert problem.message.startswith("more: ")


def test_an_adapter_declaring_no_opaque_location_is_given_none(tmp_path, registry, monkeypatch):
    opaquefixture.Clips.constructed.clear()
    source = _source(tmp_path, "plain", {}, [])
    recipe, writer = _build(tmp_path, registry, monkeypatch, [source])
    assert opaquefixture.Clips.constructed == [set()]
    report = writer.commit(recipe.out)
    assert report.passed, [(f.check, f.message) for f in report.findings]
    assert not (recipe.out / "opaque").exists()
    assert not any(
        e["uri"].startswith("opaque/") for e in json.loads((recipe.out / "packet.json").read_text())["resources"]
    )


def test_an_adapter_handing_over_bytes_without_declaring_where_is_refused(tmp_path, registry, monkeypatch):
    source = _source(tmp_path, "undeclared", {"core.clip": {"a.mp4": b"a"}}, ["core.media_assets"])
    with pytest.raises(PayloadRefused) as refused:
        _build(tmp_path, registry, monkeypatch, [source])
    assert refused.value.source == "undeclared"
    assert [p.code for p in refused.value.problems] == [PayloadFault.NO_LOCATION]


def test_an_occupied_opaque_directory_refuses_a_commit(tmp_path, registry, minimal):
    """Part 05 §6: an interrupted promotion may leave `opaque/` without a manifest."""
    root = tmp_path / "s001"
    (root / "opaque" / "core.clip").mkdir(parents=True)
    with pytest.raises(PacketOccupied) as refused:
        _writer(registry, minimal).commit(root)
    assert refused.value.occupied == ["opaque"]


# -- resource-document URIs and the external rule -------------------------------------------


def _document_delivery(tmp_path, entries, rows=()):
    """Fetch a stream delivery carrying `entries` as its resource document and `rows` of media assets."""
    script = tmp_path / "document.py"
    script.write_text(
        "import json, sys\n"
        "import pyarrow as pa\n"
        "from escapewheel_writer import delivery\n"
        "json.loads(sys.stdin.buffer.read())\n"
        "out = sys.stdout.buffer\n"
        f"delivery._write(out, 'core.media_assets', delivery.as_table({list(rows)!r}))\n"
        f"doc = json.dumps({{'resources': {entries!r}}})\n"
        "delivery._write(out, delivery.RESOURCES, delivery.as_table([{'document': doc}]))\n"
        "delivery._write(out, delivery.SENTINEL, pa.table({}))\n"
        "out.flush()\n"
    )
    return delivery.fetch(
        "cams",
        [sys.executable, str(script)],
        {"root": str(tmp_path), "session_id": "s001"},
        protocol="stream-v0.1",
        wanted=["core.media_assets"],
        workspace=tmp_path / "work",
    )


def _cam(uri, **fields):
    return {"resource_id": "core.cam", "declaration_id": "core.media_asset_instances", "uri": uri, **fields}


@pytest.mark.parametrize("uri", ["videos/cam 1.mp4", "a%2Fb.mp4", "../b.mp4"])
def test_a_resource_document_uri_no_reader_could_resolve_is_refused(tmp_path, uri):
    """Part 03 §4: a uri without a scheme is a relative reference, or it is refused."""
    with pytest.raises(DeliveryFailed) as refused:
        _document_delivery(tmp_path, [_cam(uri, external=True, source="cams")])
    assert [failure.code for failure in refused.value.failures] == [SourceFault.ENTRY_URI]
    assert refused.value.failures[0].where == "core.cam"
    assert refused.value.where == "cams"


def test_a_resource_document_uri_is_recorded_in_one_form(tmp_path):
    got = _document_delivery(
        tmp_path, [_cam("videos/r%c3%a9sum%c3%a9.pdf", external=True, source="cams")], rows=[_row("core.cam")]
    )
    assert [entry["uri"] for entry in got.referenced] == ["videos/r%C3%A9sum%C3%A9.pdf"]


def test_a_source_relative_uri_is_resolved_by_the_reader(tmp_path, registry, minimal):
    """Part 04 §5.5: decoded, and its names appended to wherever the source resolves."""
    got = _document_delivery(
        tmp_path, [_cam("videos/cam%201.mp4", external=True, source="cams")], rows=[_row("core.cam")]
    )
    writer = _writer(registry, minimal)
    writer.add("core.media_assets", got.rows("core.media_assets"))
    cams = tmp_path / "cams"
    _lay(cams / "videos", {"cam 1.mp4": b"video"})
    writer.declare_source("cams", str(cams))
    for resource_id, media in got.external_media().items():
        writer.reference_media(resource_id, media)
    root = tmp_path / "s001"
    report = writer.commit(root)
    assert report.passed, [(f.check, f.message) for f in report.findings]
    assert _entry(root, "core.cam")["uri"] == "videos/cam%201.mp4"
    assert Path(open_packet(root).path("core.cam")) == cams / "videos" / "cam 1.mp4"


def test_a_resource_document_entry_declaring_itself_owned_is_refused(tmp_path):
    """Part 12 §5: a packet-owned opaque resource crosses only as a payload."""
    with pytest.raises(DeliveryFailed) as refused:
        _document_delivery(tmp_path, [_cam("videos/cam.mp4", external=False)])
    assert [failure.code for failure in refused.value.failures] == [SourceFault.ENTRY_NOT_EXTERNAL]
    assert refused.value.failures[0].where == "core.cam"
    assert refused.value.where == "cams"


def test_a_resource_document_entry_declaring_nothing_is_recorded_as_external(tmp_path, registry, minimal):
    got = _document_delivery(tmp_path, [_cam("beside/cam.mp4")], rows=[_row("core.cam")])
    assert [entry["external"] for entry in got.referenced] == [True]
    writer = _writer(registry, minimal)
    writer.add("core.media_assets", got.rows("core.media_assets"))
    for resource_id, media in got.external_media().items():
        writer.reference_media(resource_id, media)
    root = tmp_path / "s001"
    writer.commit(root)
    entry = _entry(root, "core.cam")
    assert (entry["external"], entry["uri"]) == (True, "beside/cam.mp4")


def test_the_writer_spells_its_own_relative_uris_in_one_form(tmp_path, registry, minimal):
    """Part 03 §4: every relative uri a writer records decodes and re-encodes to itself."""
    from escapewheel_reader.uri import canonical

    root, _ = _commit_one(tmp_path, registry, minimal, "core.report", {QC_NAME: PDF})
    manifest = json.loads((root / "packet.json").read_text())
    relative = [entry["uri"] for entry in manifest["resources"] if "://" not in entry["uri"]]
    assert relative and all(canonical(uri) == uri for uri in relative)


# -- cleanup --------------------------------------------------------------------------------


def test_cleanup_reads_a_payload_s_uri_decoded_and_a_prefix_as_its_files(tmp_path, registry, minimal):
    """Part 03 §9: a payload's files are named by its entry, so none is a stray."""
    from escapewheel_writer.prune import prune

    root, _ = _commit_one(tmp_path, registry, minimal, "core.report", {QC_NAME: PDF})
    plan = prune(root)
    assert not plan.strays and not plan.orphans

    frames = root / "opaque" / "core.frames" / "frames"
    _lay(frames, {"0.png": b"0"})
    assert prune(root).strays == (frames / "0.png",)


def test_cleanup_finds_an_orphaned_payload_prefix(tmp_path):
    from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME

    from escapewheel_writer.prune import prune

    root = tmp_path / "p"
    frames = root / "opaque" / "core.frames" / "frames"
    _lay(frames, {"0.png": b"0", "1.png": b"1"})

    def manifest(version, uris):
        return {
            "packet_id": "p",
            "packet_version": version,
            "registries": {},
            "created_at": "2026-01-01T00:00:00Z",
            "resources": [
                {"resource_id": uri, "declaration_id": "core.media_asset_instances", "uri": uri} for uri in uris
            ],
        }

    (root / MANIFEST_FILENAME).write_text(json.dumps(manifest("0.2.0", [])))
    (root / MANIFESTS_DIRNAME).mkdir()
    (root / MANIFESTS_DIRNAME / "0.1.0.json").write_text(json.dumps(manifest("0.1.0", ["opaque/core.frames/frames"])))
    (root / MANIFESTS_DIRNAME / "0.2.0.json").write_text(json.dumps(manifest("0.2.0", [])))
    plan = prune(root, keep_versions=0, keep_days=0)
    assert plan.orphans == (frames / "0.png", frames / "1.png")
    assert not plan.strays

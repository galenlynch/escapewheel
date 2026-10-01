"""`escapewheel verify` records what is true once the bytes have landed (Part 04 §5.2)."""

import json

import pytest

from escapewheel_writer import PacketWriter
from escapewheel_writer.errors import NotCommitted
from escapewheel_writer.verify import verify

from .conftest import read_registry, rebind_registry


def _commit(root, registry, tables):
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    return writer.commit(root)


def _external(root, uri):
    """Declare an external array the committed packet says nothing about, as a build that could
    not reach its store leaves it (Part 04 §5.2)."""
    registry = read_registry(root)
    registry["resources"]["core.test_payloads"] = {
        "content_class": "core",
        "kind": "opaque",
        "instances": {"mode": "family"},
        "requires": [],
        "lineage": "optional",
    }
    rebind_registry(root, registry)
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"].append(
        {
            "resource_id": "core.probe.lfp",
            "declaration_id": "core.test_payloads",
            "uri": uri,
            "validation_state": "passed",
            "external": True,
        }
    )
    path.write_text(json.dumps(manifest))
    return root


def _zarr(tmp_path):
    store = tmp_path / "lfp.zarr"
    store.mkdir()
    (store / ".zarray").write_text(
        json.dumps(
            {
                "shape": [4, 2],
                "chunks": [4, 2],
                "dtype": "<i2",
                "zarr_format": 2,
                "compressor": {"id": "blosc"},
                "filters": None,
                "order": "C",
                "fill_value": 0,
            }
        )
    )
    (store / "0.0").write_bytes(b"x" * 100)
    return store


def test_verify_records_what_the_store_holds(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    store = _zarr(tmp_path)
    _external(root, store.resolve().as_uri())

    report, manifest = verify(root)
    assert report.passed
    entry = next(r for r in manifest["resources"] if r.get("external"))
    assert entry["size_bytes"] == sum(f.stat().st_size for f in store.rglob("*") if f.is_file())
    assert entry["verified_at"] is not None
    assert {m["key"] for m in entry["members"]} == {".zarray", "0.0"}


def test_a_single_object_records_no_members(tmp_path, registry, minimal):
    """Part 04 §5.4 gives only a prefix members; a single object has no key to list it under."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    video = tmp_path / "camera.mp4"
    video.write_bytes(b"x" * 100)
    _external(root, video.resolve().as_uri())

    report, manifest = verify(root, level="sha256")
    assert report.passed, [f.message for f in report.findings if f.level == "error"]
    entry = next(r for r in manifest["resources"] if r.get("external"))
    assert entry["size_bytes"] == 100
    assert "members" not in entry


def test_verify_is_a_new_packet_version_that_retains_the_old(tmp_path, registry, minimal):
    """Part 05 §15.3: a superseded file is interpretable only while the manifest naming it survives."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, _zarr(tmp_path).resolve().as_uri())

    _, manifest = verify(root)
    assert manifest["packet_version"] == "0.1.1"
    assert sorted(p.name for p in (root / "manifests").iterdir()) == [
        "0.1.0.json",
        "0.1.1.json",
    ]


def test_sha256_is_asked_for_separately(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, _zarr(tmp_path).resolve().as_uri())

    _, cheap = verify(root)
    assert "digest" not in next(r for r in cheap["resources"] if r.get("external"))
    _, dear = verify(root, level="sha256")
    assert next(r for r in dear["resources"] if r.get("external"))["digest"]["algorithm"] == "sha256"


def test_a_digest_records_each_member_beside_the_resource(tmp_path, registry, minimal):
    """Part 04 §5.4: a member's own value lets a consumer check one chunk without the rest."""
    from escapewheel_validator.stores import digest, listing_digest

    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    store = _zarr(tmp_path)
    _external(root, store.resolve().as_uri())

    report, manifest = verify(root, level="sha256")
    assert report.passed, [f.message for f in report.findings if f.level == "error"]
    entry = next(r for r in manifest["resources"] if r.get("external"))
    assert {m["key"]: m["digest"] for m in entry["members"]} == {
        key: digest(str(store / key)) for key in (".zarray", "0.0")
    }
    rows = [(m["key"], m["size_bytes"], m["digest"]) for m in entry["members"]]
    assert entry["digest"] == {"algorithm": "sha256", "value": listing_digest(rows)}

    # A later listing-only pass keeps both, since the schema admits member digests only beside one.
    report, manifest = verify(root)
    assert report.passed, [f.message for f in report.findings if f.level == "error"]
    again = next(r for r in manifest["resources"] if r.get("external"))
    assert again["digest"] == entry["digest"] and again["members"] == entry["members"]


def test_a_listing_that_gained_an_object_drops_a_digest_it_no_longer_describes(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    store = _zarr(tmp_path)
    _external(root, store.resolve().as_uri())
    verify(root, level="sha256")
    (store / "1.0").write_bytes(b"y" * 10)

    report, manifest = verify(root)
    assert report.passed, [f.message for f in report.findings if f.level == "error"]
    entry = next(r for r in manifest["resources"] if r.get("external"))
    assert "digest" not in entry and all("digest" not in m for m in entry["members"])


def test_a_multipart_entity_tag_is_recorded_as_etag_and_compared(tmp_path, registry, minimal, monkeypatch):
    """Part 04 §5.4: an entity tag is recorded verbatim under `etag`, a multipart one included."""
    import importlib

    from escapewheel_validator import validator as validating
    from escapewheel_validator.stores import Listing, Member, listing, store_digest

    verifying = importlib.import_module("escapewheel_writer.verify")  # the package exports a function by that name

    def tagged(uri):
        found = listing(uri)
        members = (Member(m.key, m.size_bytes, store_digest({"ETag": f'"{m.key}-3"'})) for m in found.members)
        return Listing(tuple(members), found.size_bytes)

    monkeypatch.setattr(verifying, "listing", tagged)
    monkeypatch.setattr(validating, "listing", tagged)
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, _zarr(tmp_path).resolve().as_uri())

    report, manifest = verify(root)
    assert report.passed, [f.message for f in report.findings if f.level == "error"]
    entry = next(r for r in manifest["resources"] if r.get("external"))
    assert [m["store_digest"] for m in entry["members"]] == [
        {"algorithm": "etag", "value": '".zarray-3"'},
        {"algorithm": "etag", "value": '"0.0-3"'},
    ]
    assert "1 store_digest" in next(f for f in report.findings if f.check == "external.verified").message


def test_an_unreachable_store_leaves_the_claim_unmade(tmp_path, registry, minimal):
    """Part 04 §5.2: a writer that cannot reach a URI records nothing rather than guessing."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, "file:///nowhere/at/all.zarr")

    report, manifest = verify(root)
    entry = next(r for r in manifest["resources"] if r.get("external"))
    assert "size_bytes" not in entry and "members" not in entry
    assert "verify.unreachable" in {f.check for f in report.findings}


def test_a_missing_packet_owned_digest_is_filled_in(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    for entry in manifest["resources"]:
        entry.pop("digest", None)
    path.write_text(json.dumps(manifest))
    _external(root, _zarr(tmp_path).resolve().as_uri())

    _, recorded = verify(root)
    owned = [r for r in recorded["resources"] if not r.get("external")]
    assert owned and all(r["digest"]["algorithm"] == "sha256" for r in owned)


def test_an_uncommitted_root_is_refused(tmp_path):
    with pytest.raises(NotCommitted):
        verify(tmp_path)


def test_an_unknown_level_is_refused(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    with pytest.raises(ValueError, match="level must be"):
        verify(root, level="md5")


def test_verify_retains_the_exact_bytes_it_supersedes(tmp_path, registry, minimal):
    """`_external` writes the manifest compactly, so a copy re-serialised at retention would differ."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, _zarr(tmp_path).resolve().as_uri())
    published = (root / "packet.json").read_bytes()

    verify(root)
    assert (root / "manifests" / "0.1.0.json").read_bytes() == published
    assert (root / "manifests" / "0.1.1.json").read_bytes() == (root / "packet.json").read_bytes()


@pytest.mark.parametrize("version", ["0.1.0", "1.0.0"])
def test_verify_refuses_a_version_an_amendment_could_not_take(tmp_path, registry, minimal, version):
    """Part 05 §15.1: the new version sorts after the old one and keeps its major version."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    with pytest.raises(ValueError, match="within its major version"):
        verify(root, packet_version=version)

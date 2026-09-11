"""`escapewheel verify` records what is true once the bytes have landed (Part 04 §5.2)."""

import json

import pytest

from escapewheel_writer import PacketWriter
from escapewheel_writer.verify import verify
from escapewheel_writer.writer import NotCommitted


def _commit(root, registry, tables):
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    return writer.commit(root)


def _external(root, uri):
    """Declare an external array the committed packet says nothing about, as a build that could
    not reach its store leaves it (Part 04 §5.2)."""
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"].append(
        {
            "resource_id": "core.probe.lfp",
            "layer": "core",
            "kind": "dense_array_asset",
            "physical_profile": "zarr_v2",
            "uri": uri,
            "array_asset_id": "probe.lfp",
            "canonical": True,
            "validation_state": "passed",
            "external": True,
            "codecs": ["blosc"],
        }
    )
    manifest["required_codecs"] = sorted({c for r in manifest["resources"] for c in r.get("codecs", [])})
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


def test_verify_is_a_new_packet_version_that_retains_the_old(tmp_path, registry, minimal):
    """Part 03 §9.3: a superseded file is interpretable only while the manifest naming it survives."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, _zarr(tmp_path).resolve().as_uri())

    _, manifest = verify(root)
    assert manifest["packet_version"] == "0.1.1"
    assert manifest["supersedes"] == "0.1.0"
    assert sorted(p.name for p in (root / "manifests").iterdir()) == [
        "nwb.packet.0.1.0.json",
        "nwb.packet.0.1.1.json",
    ]


def test_sha256_is_asked_for_separately(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, _zarr(tmp_path).resolve().as_uri())

    _, cheap = verify(root)
    assert next(r for r in cheap["resources"] if r.get("external")).get("sha256") is None
    _, dear = verify(root, level="sha256")
    assert next(r for r in dear["resources"] if r.get("external"))["sha256"] is not None


def test_an_unreachable_store_leaves_the_claim_unmade(tmp_path, registry, minimal):
    """Part 04 §5.2: a writer that cannot reach a URI records nothing rather than guessing."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    _external(root, "file:///nowhere/at/all.zarr")

    report, manifest = verify(root)
    entry = next(r for r in manifest["resources"] if r.get("external"))
    assert "size_bytes" not in entry and "members" not in entry
    assert "verify.unreachable" in {f.check for f in report.findings}


def test_a_packet_owned_digest_missing_since_before_r52_is_filled_in(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    for entry in manifest["resources"]:
        entry.pop("sha256", None)
    path.write_text(json.dumps(manifest))
    _external(root, _zarr(tmp_path).resolve().as_uri())

    _, recorded = verify(root)
    owned = [r for r in recorded["resources"] if not r.get("external")]
    assert owned and all(r.get("sha256") for r in owned)


def test_an_uncommitted_root_is_refused(tmp_path):
    with pytest.raises(NotCommitted):
        verify(tmp_path)


def test_an_unknown_level_is_refused(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    with pytest.raises(ValueError, match="level must be"):
        verify(root, level="md5")

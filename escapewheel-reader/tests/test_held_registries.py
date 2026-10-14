"""A reader takes a bound registry from any document matching its digest (Part 04 §10), and reads
what it does not hold, and the resolution documents, only when they are needed."""

import gzip
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from packet_fixture import install_registry, read_registry

from escapewheel_reader import RegistryFault, RegistryUnavailable, open_packet, registries
from escapewheel_reader import location as location_module
from escapewheel_reader import packet as packet_module

INCORPORATED_CORE = Path(__file__).resolve().parents[2] / "spec" / "artifacts" / "logical_schemas.json"


def _stored(root, registry_id="core"):
    manifest = json.loads((root / "packet.json").read_text())
    return root / manifest["registries"][registry_id]["path"]


def test_a_held_document_answers_without_the_stored_copy(packet_root):
    stored = _stored(packet_root)
    registries.hold(gzip.decompress(stored.read_bytes()))
    stored.unlink()
    assert "core.sessions" in open_packet(packet_root).registry["resources"]


def test_a_document_of_the_same_version_with_another_digest_is_not_used(packet_root):
    stored = _stored(packet_root)
    document = json.loads(gzip.decompress(stored.read_bytes()))
    registries.hold(json.dumps({**document, "resources": {}}).encode())
    assert open_packet(packet_root).registry == document


def test_a_missing_stored_copy_fails_naming_the_registry_where_none_is_held(packet_root):
    _stored(packet_root).unlink()
    with pytest.raises(RegistryUnavailable) as refused:
        _ = open_packet(packet_root).registry
    assert (refused.value.registry_id, refused.value.reason) == ("core", RegistryFault.MISSING)


def test_a_verified_stored_copy_serves_the_next_packet_binding_it(packet_root, tmp_path):
    other = tmp_path / "other"
    shutil.copytree(packet_root, other)
    _stored(other).unlink()
    first = open_packet(packet_root).registry
    assert open_packet(other).registry == first


def test_a_stored_copy_failing_its_digest_is_not_held(packet_root, tmp_path):
    other = tmp_path / "other"
    shutil.copytree(packet_root, other)
    stored = _stored(packet_root)
    stored.write_bytes(gzip.compress(gzip.decompress(stored.read_bytes()) + b" "))
    with pytest.raises(RegistryUnavailable):
        _ = open_packet(packet_root).registry
    _stored(other).unlink()
    with pytest.raises(RegistryUnavailable) as refused:
        _ = open_packet(other).registry
    assert refused.value.reason is RegistryFault.MISSING


def test_the_shipped_core_registry_is_the_incorporated_one(monkeypatch):
    monkeypatch.setattr(registries, "_HELD", None)
    document = INCORPORATED_CORE.read_bytes()
    assert registries.held(hashlib.sha256(document).hexdigest()) == document


def test_acquire_reads_only_the_stored_copy(packet_root):
    """What a validator checks is the packet's copy, whatever this process holds (Part 03 §3.2)."""
    stored = _stored(packet_root)
    registries.hold(gzip.decompress(stored.read_bytes()))
    stored.unlink()
    packet = open_packet(packet_root)
    binding = packet.manifest.registries["core"]
    with pytest.raises(RegistryUnavailable) as refused:
        registries.acquire(packet.location, binding)
    assert refused.value.reason is RegistryFault.MISSING


def test_every_unheld_bound_registry_is_read_once(packet_root, monkeypatch):
    """The first declaration a packet needs reads every registry it binds, together."""
    install_registry(
        packet_root, {**read_registry(packet_root), "registry_id": "task", "resources": {}}, role="extension"
    )
    reads = []
    acquire = registries.acquire

    def counted(root, binding):
        reads.append(binding.registry_id)
        return acquire(root, binding)

    monkeypatch.setattr(packet_module, "acquire", counted)
    packet = open_packet(packet_root)
    _ = packet.registry
    _ = packet.extensions()
    assert sorted(reads) == ["core", "task"]


def test_an_unreadable_extension_fails_only_what_needs_it(packet_root):
    install_registry(
        packet_root, {**read_registry(packet_root), "registry_id": "task", "resources": {}}, role="extension"
    )
    _stored(packet_root, "task").unlink()
    packet = open_packet(packet_root)
    assert "core.sessions" in packet.registry["resources"]
    with pytest.raises(RegistryUnavailable) as refused:
        packet.extensions()
    assert (refused.value.registry_id, refused.value.reason) == ("task", RegistryFault.MISSING)


def test_opening_reads_no_resolution_document(packet_root, monkeypatch):
    """Only an external entry needs one (Part 04 §5.5), so a packet-owned read never looks."""
    looked = []
    read_document = location_module.read_document
    monkeypatch.setattr(location_module, "read_document", lambda where: looked.append(where) or read_document(where))
    packet = open_packet(packet_root)
    assert packet.table("core.intervals").num_rows == 2
    assert looked == []
    _ = packet.resolution.documents
    assert [str(where) for where in looked][-1] == str(packet_root / "sources.json")

import json

import pytest

from escapewheel_reader import Manifest, ManifestError, RegistryUnavailable, open_packet

from .conftest import SESSION_NAME, install_registry, read_registry


def test_load_parses_declared_fields(packet_root):
    manifest = Manifest.load(packet_root)
    assert manifest.packet_id == "session_001"
    assert manifest.profile_id == "escapewheel-portable-v0.1"
    assert manifest.core.registry_id == "core"
    assert manifest.core.version == "0.1.0"
    assert manifest.sessions == (SESSION_NAME,)
    assert {r.resource_id for r in manifest.resources} == {
        "core.sessions",
        "core.intervals",
        "core.units",
        "core.event_streams",
        "core.events",
        "core.spike_events",
    }


def test_missing_manifest_is_an_error(tmp_path):
    with pytest.raises(ManifestError, match="no packet.json"):
        Manifest.load(tmp_path)


def test_unparsable_manifest_is_an_error(tmp_path):
    (tmp_path / "packet.json").write_text("{not json")
    with pytest.raises(ManifestError, match="not valid UTF-8 JSON"):
        Manifest.load(tmp_path)


def _rewrite(packet_root, edit):
    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    edit(entry)
    path.write_text(json.dumps(entry))


def test_a_reader_does_not_apply_the_manifest_schema(packet_root):
    """Part 04 §10: closure and formats are the validator's, so reading proceeds."""

    def edit(entry):
        entry["created_at"] = "2026-09-04 04:22:45"
        entry["unknown_member"] = True
        entry["resources"][0]["physical_profile"] = "parquet"

    _rewrite(packet_root, edit)
    assert open_packet(packet_root).table("core.intervals").num_rows == 2


def test_a_repeated_member_is_rejected(packet_root):
    """`json.load` keeps the last of two members, which would hide which one the writer meant."""
    path = packet_root / "packet.json"
    text = path.read_text()
    path.write_text(
        text.replace(
            '"resource_id": "core.sessions",', '"resource_id": "core.sessions", "resource_id": "core.units",', 1
        )
    )
    with pytest.raises(ManifestError, match="repeats member 'resource_id'"):
        Manifest.load(packet_root)


def test_a_repeated_resource_id_is_rejected_before_any_lookup(packet_root):
    _rewrite(packet_root, lambda entry: entry["resources"].append(dict(entry["resources"][0])))
    with pytest.raises(ManifestError, match="'core.sessions' names more than one entry"):
        Manifest.load(packet_root)


def test_a_member_read_with_the_wrong_type_is_named(packet_root):
    def edit(entry):
        entry["resources"][1]["uri"] = 7

    _rewrite(packet_root, edit)
    with pytest.raises(ManifestError, match="'uri' has the wrong JSON type"):
        Manifest.load(packet_root)


def test_a_missing_required_member_is_named(packet_root):
    _rewrite(packet_root, lambda entry: entry.pop("registries"))
    with pytest.raises(ManifestError, match="lacks required member 'registries'"):
        Manifest.load(packet_root)


def test_listing_resources_acquires_no_registry(packet_root):
    """Opening a packet and listing resources need no declaration (Part 04 §10)."""
    (packet_root / read_registry_path(packet_root)).unlink()
    packet = open_packet(packet_root)
    assert len(packet.resources()) == 6
    with pytest.raises(RegistryUnavailable, match="'core'") as raised:
        _ = packet.resource("core.intervals").kind
    assert raised.value.reason == "missing"


def test_a_registry_failing_its_digest_fails_the_operation_that_needed_it(packet_root):
    def edit(entry):
        entry["registries"]["core"]["sha256"] = "0" * 64

    _rewrite(packet_root, edit)
    packet = open_packet(packet_root)
    with pytest.raises(RegistryUnavailable) as raised:
        _ = packet.registry
    assert (raised.value.registry_id, raised.value.reason) == ("core", "digest")


def test_a_second_gzip_member_makes_a_registry_unreadable(packet_root):
    path = packet_root / read_registry_path(packet_root)
    path.write_bytes(path.read_bytes() * 2)
    with pytest.raises(RegistryUnavailable) as raised:
        _ = open_packet(packet_root).registry
    assert raised.value.reason == "unreadable"


def test_gzip_header_fields_do_not_change_what_a_descriptor_matches(packet_root):
    import gzip

    path = packet_root / read_registry_path(packet_root)
    document = gzip.decompress(path.read_bytes())
    path.write_bytes(gzip.compress(document, compresslevel=1, mtime=123456789))
    assert open_packet(packet_root).registry["registry_id"] == "core"


def test_an_unbound_namespace_declares_nothing(packet_root):
    registry = read_registry(packet_root)
    registry["registry_id"] = "task"
    install_registry(packet_root, registry, role="extension")
    packet = open_packet(packet_root)
    assert packet.manifest.binding_for("elsewhere.table") is None
    assert packet.manifest.binding_for("task.trials").registry_id == "task"


def read_registry_path(packet_root):
    return json.loads((packet_root / "packet.json").read_text())["registries"]["core"]["path"]


def test_resource_interface_derives_from_logical_kind(packet_root):
    manifest = Manifest.load(packet_root)
    packet = open_packet(packet_root)
    assert packet.resource(manifest.resources[1].resource_id).interface == "parquet"

import json

import pytest

from escapewheel_reader import Manifest, ManifestError, open_packet

from .conftest import SESSION_NAME


def test_load_parses_declared_fields(packet_root):
    manifest = Manifest.load(packet_root)
    assert manifest.packet_id == "session_001"
    assert manifest.profile_id == "escapewheel-portable-v0.1"
    assert manifest.registry_version == "0.1.0"
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
    with pytest.raises(ManifestError, match="not valid JSON"):
        Manifest.load(tmp_path)


def test_retired_physical_field_is_an_error(packet_root):
    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    entry["resources"][0]["physical_profile"] = "parquet"
    path.write_text(json.dumps(entry))
    with pytest.raises(ManifestError, match="does not conform"):
        Manifest.load(packet_root)


def test_validation_can_be_skipped(packet_root):
    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    entry["resources"][0]["physical_profile"] = "parquet"
    path.write_text(json.dumps(entry))
    assert open_packet(packet_root, validate_manifest=False).manifest.resources


def test_resource_interface_derives_from_logical_kind(packet_root):
    manifest = Manifest.load(packet_root)
    packet = open_packet(packet_root)
    assert packet.resource(manifest.resources[1].resource_id).interface == "parquet"

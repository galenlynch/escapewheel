import json

import pytest

from nwb_lake_reader import Manifest, ManifestError, open_packet


def test_load_parses_declared_fields(packet_root):
    manifest = Manifest.load(packet_root)
    assert manifest.packet_id == "session_001"
    assert manifest.profile_id == "nwb-lake-portable-v0.1"
    assert manifest.registry_version == "0.1.0"
    assert manifest.sessions == ("s001",)
    assert manifest.required_codecs == ()
    assert {r.resource_id for r in manifest.resources} == {
        "core.sessions",
        "core.trials",
        "core.units",
        "core.events",
        "core.spike_events",
    }


def test_missing_manifest_is_an_error(tmp_path):
    with pytest.raises(ManifestError, match="no nwb.packet.json"):
        Manifest.load(tmp_path)


def test_unparsable_manifest_is_an_error(tmp_path):
    (tmp_path / "nwb.packet.json").write_text("{not json")
    with pytest.raises(ManifestError, match="not valid JSON"):
        Manifest.load(tmp_path)


def test_schema_violation_is_an_error(packet_root):
    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    del entry["required_codecs"]
    path.write_text(json.dumps(entry))
    with pytest.raises(ManifestError, match="does not conform"):
        Manifest.load(packet_root)


def test_validation_can_be_skipped(packet_root):
    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    del entry["required_codecs"]
    path.write_text(json.dumps(entry))
    assert open_packet(packet_root, validate_manifest=False).manifest.required_codecs == ()


def test_partitioned_resource_is_recognised(packet_root):
    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    entry["resources"][1]["physical_profile"] = "parquet_dataset"
    entry["resources"][1]["partitioning"] = ["session_id"]
    path.write_text(json.dumps(entry))
    manifest = Manifest.load(packet_root)
    assert manifest.resources[1].is_partitioned
    assert not manifest.resources[0].is_partitioned

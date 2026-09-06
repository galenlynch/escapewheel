"""Cleanup over a committed packet (R61 §2)."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from escapewheel_writer.prune import KEEP_VERSIONS, prune
from escapewheel_writer.writer import MANIFEST, MANIFESTS, NotCommitted


def _manifest(version, resources, registry="0.1.0", when="2026-01-01T00:00:00Z"):
    return {
        "packet_id": "p",
        "packet_version": version,
        "registry_version": registry,
        "created_at": when,
        "resources": [{"resource_id": name, "uri": uri, "kind": "table"} for name, uri in resources],
        "validation": {"status": "passed", "validated_at": when},
    }


@pytest.fixture
def packet(tmp_path):
    """A packet at 0.3.0 whose 0.1.0 named a table 0.2.0 dropped."""
    root = tmp_path / "p"
    (root / "tables" / "core").mkdir(parents=True)
    (root / "schemas").mkdir()
    for name in ("kept.parquet", "dropped.parquet"):
        (root / "tables" / "core" / name).write_text("x")
    (root / "schemas" / "logical_schemas.json").write_text("{}")
    (root / "schemas" / "logical_schemas.0.1.0.json").write_text("{}")

    kept = ("core.kept", "tables/core/kept.parquet")
    dropped = ("core.dropped", "tables/core/dropped.parquet")
    # The packet is on registry 0.2.0, so 0.1.0 survives as the versioned copy its own
    # manifest names, exactly as `_install_registry` retains it.
    (root / MANIFEST).write_text(json.dumps(_manifest("0.3.0", [kept], registry="0.2.0")))
    (root / MANIFESTS).mkdir()
    for version, resources, registry in (
        ("0.1.0", [kept, dropped], "0.1.0"),
        ("0.2.0", [kept], "0.2.0"),
        ("0.3.0", [kept], "0.2.0"),
    ):
        (root / MANIFESTS / f"nwb.packet.{version}.json").write_text(
            json.dumps(_manifest(version, resources, registry=registry))
        )
    return root


def test_an_orphan_is_a_file_no_surviving_manifest_names(packet):
    """Expiring 0.1.0 unreferences both what it named and the registry it was written against."""
    plan = prune(packet)
    assert [p.name for p in plan.orphans] == ["logical_schemas.0.1.0.json", "dropped.parquet"]
    assert not plan.strays
    assert (packet / "tables/core/dropped.parquet").exists(), "reporting must not remove"


def test_a_stray_is_reported_and_never_removed(packet):
    (packet / "tables" / "core" / "notes.txt").write_text("mine")
    plan = prune(packet, apply=True)
    assert [p.name for p in plan.strays] == ["notes.txt"]
    assert (packet / "tables" / "core" / "notes.txt").exists()


def test_orphans_go_before_the_manifests_that_identify_them(packet):
    """R61 §2.1. Expiring first would make the orphan indistinguishable from a stray, so a second
    run over an already-pruned packet must find nothing rather than a new stray."""
    first = prune(packet, apply=True)
    assert first.orphans and first.expired
    assert not (packet / "tables/core/dropped.parquet").exists()
    assert not prune(packet).strays, "the orphan was removed before the manifest naming it"


def test_the_default_keeps_one_superseded_manifest(packet):
    plan = prune(packet)
    assert KEEP_VERSIONS == 1
    assert [p.name for p in plan.retained] == ["nwb.packet.0.2.0.json"]
    assert [p.name for p in plan.expired] == ["nwb.packet.0.1.0.json"]


def test_the_current_versions_own_copy_is_never_expired(packet):
    plan = prune(packet, keep_versions=0)
    assert "nwb.packet.0.3.0.json" not in [p.name for p in plan.expired]


def test_a_packet_declares_its_retention(packet):
    manifest = json.loads((packet / MANIFEST).read_text())
    manifest["retention"] = {"keep_versions": 2}
    (packet / MANIFEST).write_text(json.dumps(manifest))
    assert not prune(packet).expired


def test_an_argument_overrides_what_the_packet_declares(packet):
    manifest = json.loads((packet / MANIFEST).read_text())
    manifest["retention"] = {"keep_versions": 2}
    (packet / MANIFEST).write_text(json.dumps(manifest))
    assert [p.name for p in prune(packet, keep_versions=0).expired] == [
        "nwb.packet.0.1.0.json",
        "nwb.packet.0.2.0.json",
    ]


def test_both_floors_must_permit_an_expiry(packet):
    """R61 §2.2: keep_versions and keep_days are floors, not alternatives."""
    assert prune(packet, keep_versions=0, keep_days=365, now=datetime(2026, 2, 1, tzinfo=timezone.utc)).expired == ()
    old = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=400)
    assert prune(packet, keep_versions=0, keep_days=365, now=old).expired


def test_a_manifest_with_no_timestamp_is_kept_and_said_so(packet):
    path = packet / MANIFESTS / "nwb.packet.0.1.0.json"
    manifest = json.loads(path.read_text())
    del manifest["created_at"], manifest["validation"]
    path.write_text(json.dumps(manifest))
    plan = prune(packet, keep_versions=0, keep_days=1)
    assert path in plan.retained
    assert any("no timestamp" in note for note in plan.notes)


def test_a_retained_registry_lives_as_long_as_the_manifest_naming_it_survives(packet):
    """R61 §2.3. Kept while its manifest is kept, and an orphan in the run that expires it."""
    kept = prune(packet, keep_versions=2)
    assert "logical_schemas.0.1.0.json" not in [p.name for p in kept.orphans]
    expiring = prune(packet, keep_versions=1)
    assert "logical_schemas.0.1.0.json" in [p.name for p in expiring.orphans]


def test_a_manifest_deleted_out_of_band_strands_its_registry(packet):
    """Which is why R61 §2.1 puts orphans first: nothing names the file any more, so it is a
    stray, and a stray is never removed."""
    (packet / MANIFESTS / "nwb.packet.0.1.0.json").unlink()
    plan = prune(packet)
    assert "logical_schemas.0.1.0.json" in [p.name for p in plan.strays]
    assert "logical_schemas.0.1.0.json" not in [p.name for p in plan.orphans]


def test_a_manifest_on_the_installed_registry_names_the_unversioned_copy(packet):
    """`_install_registry` puts the current registry at one path and every other at a versioned
    one, so a retained manifest written against the current registry names the same file the
    current manifest does -- not a versioned copy that was never written."""
    plan = prune(packet)
    assert not [p for p in plan.orphans if p.name == "logical_schemas.json"]
    assert not [p for p in plan.strays if p.name == "logical_schemas.json"]


def test_an_external_resource_is_never_touched(packet):
    manifest = json.loads((packet / MANIFEST).read_text())
    manifest["resources"].append(
        {"resource_id": "core.lfp", "uri": "s3://bucket/lfp.zarr", "external": True, "kind": "array"}
    )
    (packet / MANIFEST).write_text(json.dumps(manifest))
    assert not prune(packet).strays


def test_an_uncommitted_packet_is_refused(tmp_path):
    with pytest.raises(NotCommitted):
        prune(tmp_path)

"""Cleanup over a committed packet (Part 05 §15.5)."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME

from escapewheel_writer.errors import NotCommitted
from escapewheel_writer.layout import PROMOTION, STAGING
from escapewheel_writer.prune import KEEP_VERSIONS, prune


def _manifest(version, resources, registry="0.1.0", when="2026-01-01T00:00:00Z"):
    return {
        "packet_id": "p",
        "packet_version": version,
        "registries": {
            "core": {
                "role": "core",
                "version": registry,
                "path": f"registries/core/{registry}.json.gz",
                "sha256": "0" * 64,
            }
        },
        "created_at": when,
        "resources": [{"resource_id": name, "declaration_id": name, "uri": uri} for name, uri in resources],
        "validation": {"status": "passed", "validated_at": when},
    }


@pytest.fixture
def packet(tmp_path):
    """A packet at 0.3.0 whose 0.1.0 named a table 0.2.0 dropped."""
    root = tmp_path / "p"
    (root / "tables" / "core").mkdir(parents=True)
    (root / "registries" / "core").mkdir(parents=True)
    for name in ("kept.parquet", "dropped.parquet"):
        (root / "tables" / "core" / name).write_text("x")
    for version in ("0.1.0", "0.2.0"):
        (root / "registries" / "core" / f"{version}.json.gz").write_text("{}")

    kept = ("core.kept", "tables/core/kept.parquet")
    dropped = ("core.dropped", "tables/core/dropped.parquet")
    # The packet is on registry 0.2.0, and 0.1.0 stays at the path its own manifest names.
    (root / MANIFEST_FILENAME).write_text(json.dumps(_manifest("0.3.0", [kept], registry="0.2.0")))
    (root / MANIFESTS_DIRNAME).mkdir()
    for version, resources, registry in (
        ("0.1.0", [kept, dropped], "0.1.0"),
        ("0.2.0", [kept], "0.2.0"),
        ("0.3.0", [kept], "0.2.0"),
    ):
        (root / MANIFESTS_DIRNAME / f"{version}.json").write_text(
            json.dumps(_manifest(version, resources, registry=registry))
        )
    return root


def test_an_orphan_is_a_file_no_surviving_manifest_names(packet):
    """Expiring 0.1.0 unreferences both what it named and the registry it was written against."""
    plan = prune(packet)
    assert [p.name for p in plan.orphans] == ["0.1.0.json.gz", "dropped.parquet"]
    assert not plan.strays
    assert (packet / "tables/core/dropped.parquet").exists(), "reporting must not remove"


def test_a_stray_is_reported_and_never_removed(packet):
    (packet / "tables" / "core" / "notes.txt").write_text("mine")
    plan = prune(packet, apply=True)
    assert [p.name for p in plan.strays] == ["notes.txt"]
    assert (packet / "tables" / "core" / "notes.txt").exists()


def test_orphans_go_before_the_manifests_that_identify_them(packet):
    """Part 05 §15.5. Expiring first would make the orphan indistinguishable from a stray, so a second
    run over an already-pruned packet must find nothing rather than a new stray."""
    first = prune(packet, apply=True)
    assert first.orphans and first.expired
    assert not (packet / "tables/core/dropped.parquet").exists()
    assert not prune(packet).strays, "the orphan was removed before the manifest naming it"


def test_the_default_keeps_one_superseded_manifest(packet):
    plan = prune(packet)
    assert KEEP_VERSIONS == 1
    assert [p.name for p in plan.retained] == ["0.2.0.json"]
    assert [p.name for p in plan.expired] == ["0.1.0.json"]


def test_the_current_versions_own_copy_is_never_expired(packet):
    plan = prune(packet, keep_versions=0)
    assert "0.3.0.json" not in [p.name for p in plan.expired]


def test_a_packet_declares_its_retention(packet):
    manifest = json.loads((packet / MANIFEST_FILENAME).read_text())
    manifest["retention"] = {"keep_versions": 2}
    (packet / MANIFEST_FILENAME).write_text(json.dumps(manifest))
    assert not prune(packet).expired


def test_an_argument_overrides_what_the_packet_declares(packet):
    manifest = json.loads((packet / MANIFEST_FILENAME).read_text())
    manifest["retention"] = {"keep_versions": 2}
    (packet / MANIFEST_FILENAME).write_text(json.dumps(manifest))
    assert [p.name for p in prune(packet, keep_versions=0).expired] == [
        "0.1.0.json",
        "0.2.0.json",
    ]


def test_both_floors_must_permit_an_expiry(packet):
    """Part 05 §15.5: keep_versions and keep_days are floors, not alternatives."""
    assert prune(packet, keep_versions=0, keep_days=365, now=datetime(2026, 2, 1, tzinfo=UTC)).expired == ()
    old = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=400)
    assert prune(packet, keep_versions=0, keep_days=365, now=old).expired


def test_a_manifest_with_no_timestamp_is_kept_and_said_so(packet):
    path = packet / MANIFESTS_DIRNAME / "0.1.0.json"
    manifest = json.loads(path.read_text())
    del manifest["created_at"], manifest["validation"]
    path.write_text(json.dumps(manifest))
    plan = prune(packet, keep_versions=0, keep_days=1)
    assert path in plan.retained
    assert any("no timestamp" in note for note in plan.notes)


def test_a_retained_registry_lives_as_long_as_the_manifest_naming_it_survives(packet):
    """Kept while its manifest is kept, and an orphan in the run that expires it."""
    kept = prune(packet, keep_versions=2)
    assert "0.1.0.json.gz" not in [p.name for p in kept.orphans]
    expiring = prune(packet, keep_versions=1)
    assert "0.1.0.json.gz" in [p.name for p in expiring.orphans]


def test_a_manifest_deleted_out_of_band_strands_its_registry(packet):
    """Which is why Part 05 §15.5 puts orphans first: nothing names the file any more, so it is a
    stray, and a stray is never removed."""
    (packet / MANIFESTS_DIRNAME / "0.1.0.json").unlink()
    plan = prune(packet)
    assert "0.1.0.json.gz" in [p.name for p in plan.strays]
    assert "0.1.0.json.gz" not in [p.name for p in plan.orphans]


def test_a_registry_the_current_manifest_binds_is_never_an_orphan(packet):
    """A registry version is stored once, at the path every manifest binding it names."""
    plan = prune(packet, keep_versions=0)
    assert not [p for p in plan.orphans if p.name == "0.2.0.json.gz"]
    assert not [p for p in plan.strays if p.name == "0.2.0.json.gz"]


def test_an_external_resource_is_never_touched(packet):
    manifest = json.loads((packet / MANIFEST_FILENAME).read_text())
    manifest["resources"].append(
        {
            "resource_id": "core.lfp",
            "declaration_id": "core.array_asset_instances",
            "uri": "s3://bucket/lfp.zarr",
            "external": True,
        }
    )
    (packet / MANIFEST_FILENAME).write_text(json.dumps(manifest))
    assert not prune(packet).strays


def test_an_uncommitted_packet_is_refused(tmp_path):
    with pytest.raises(NotCommitted):
        prune(tmp_path)


def _record(root, version, paths):
    (root / STAGING).mkdir(exist_ok=True)
    (root / STAGING / PROMOTION).write_text(json.dumps({"packet_version": version, "paths": paths}))


def test_a_leftover_staging_area_holds_no_stray(packet):
    """Part 03 §9: the staging area is the next build's to empty, and apply leaves it."""
    (packet / STAGING / "tables" / "core").mkdir(parents=True)
    (packet / STAGING / "tables" / "core" / "partial.parquet").write_text("x")
    _record(packet, "0.4.0", ["tables/core/new.parquet"])
    plan = prune(packet, apply=True)
    assert not plan.strays
    assert [p.name for p in plan.staged] == [PROMOTION, "partial.parquet"]
    assert (packet / STAGING / "tables" / "core" / "partial.parquet").exists()


def test_a_path_an_unpublished_record_lists_is_no_stray(packet):
    (packet / "tables" / "core" / "new.parquet").write_text("x")
    _record(packet, "0.4.0", ["tables/core/new.parquet"])
    plan = prune(packet, apply=True)
    assert not plan.strays
    assert [p.name for p in plan.promoting] == ["new.parquet"]
    assert (packet / "tables" / "core" / "new.parquet").exists()


def test_a_stale_record_claims_nothing(packet):
    """Its version is published, so what it lists is either named by a manifest or a stray."""
    (packet / "tables" / "core" / "notes.txt").write_text("mine")
    _record(packet, "0.3.0", ["tables/core/notes.txt"])
    plan = prune(packet)
    assert [p.name for p in plan.strays] == ["notes.txt"]
    assert not plan.promoting


def test_an_unreadable_record_is_said_so(packet):
    (packet / STAGING).mkdir()
    (packet / STAGING / PROMOTION).write_text("{")
    plan = prune(packet)
    assert not plan.strays
    assert any(PROMOTION in note for note in plan.notes)

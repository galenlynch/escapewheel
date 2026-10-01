"""A build owns its staging area and the paths its promotion record lists (Part 05 §6)."""

import json
import shutil

import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import validate

import escapewheel_writer.writer as module
from escapewheel_writer import CommitRefused, PacketWriter
from escapewheel_writer.errors import PacketOccupied, PromotionRecordUnreadable
from escapewheel_writer.writer import MANIFEST, PROMOTION, STAGING, read_promotion
from tests.test_writer import _runs, _write


class Interrupted(Exception):
    """Stands in for a process stopped partway through promotion."""


def _stop_after_first_move(monkeypatch):
    real = shutil.move

    def move(source, destination):
        real(source, destination)
        raise Interrupted(destination)

    monkeypatch.setattr(module.shutil, "move", move)


def _outside_staging(root):
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.relative_to(root).parts[0] != STAGING}


def _record(root, version, paths):
    (root / STAGING).mkdir(exist_ok=True)
    (root / STAGING / PROMOTION).write_text(json.dumps({"packet_version": version, "paths": paths}))


def _newer(registry, runs):
    """A writer amending with a registry version the packet does not store yet."""
    writer = PacketWriter({**registry, "registry_version": "9.9.9"}, packet_id="s001")
    writer.add("core.processing_runs", runs)
    return writer


def test_the_record_lists_every_path_outside_staging_before_the_first_move(tmp_path, registry, minimal, monkeypatch):
    root = tmp_path / "s001"
    _stop_after_first_move(monkeypatch)
    with pytest.raises(Interrupted):
        _write(root, registry, minimal)
    assert read_promotion(root) == ("0.1.0", [f"{MANIFEST}.candidate", "registries", "tables"])
    assert (root / "tables").is_dir() and not (root / MANIFEST).exists()


def test_an_interrupted_commit_is_undone_and_published_on_retry(tmp_path, registry, minimal, monkeypatch):
    root = tmp_path / "s001"
    _stop_after_first_move(monkeypatch)
    with pytest.raises(Interrupted):
        _write(root, registry, minimal)
    monkeypatch.undo()
    assert _write(root, registry, minimal).passed
    assert validate(open_packet(root)).passed
    assert not (root / STAGING).exists()


def test_a_promoted_directory_with_no_record_is_refused_and_kept(tmp_path, registry, minimal):
    """No record means no build claims it, so it is a stray (Part 03 §9)."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    (root / MANIFEST).unlink()
    before = _outside_staging(root)
    with pytest.raises(PacketOccupied) as refused:
        _write(root, registry, minimal)
    assert "tables" in refused.value.occupied
    assert _outside_staging(root) == before


@pytest.mark.parametrize(
    "body",
    ["{", json.dumps({"paths": ["tables"]}), json.dumps({"packet_version": "0.1.0", "paths": ["../elsewhere"]})],
    ids=["not-json", "no-version", "escaping-path"],
)
def test_an_unreadable_record_is_refused_and_nothing_is_removed(tmp_path, registry, minimal, body):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    (root / MANIFEST).unlink()
    (root / STAGING).mkdir()
    (root / STAGING / PROMOTION).write_text(body)
    before = _outside_staging(root)
    with pytest.raises(PromotionRecordUnreadable, match=PROMOTION):
        _write(root, registry, minimal)
    assert _outside_staging(root) == before
    assert (root / STAGING / PROMOTION).read_text() == body


def test_an_unreadable_record_refuses_an_amendment(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    (root / STAGING).mkdir()
    (root / STAGING / PROMOTION).write_text("{")
    with pytest.raises(PromotionRecordUnreadable, match=PROMOTION):
        PacketWriter(registry, packet_id="s001").amend(root)
    assert json.loads((root / MANIFEST).read_text())["packet_version"] == "0.1.0"


def test_a_stale_record_leaves_the_published_paths_alone(tmp_path, registry, minimal):
    """The record's version is published, so the paths it lists are the packet's."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    _record(root, "0.1.0", [f"{MANIFEST}.candidate", "registries", "tables"])
    (root / STAGING / "leftover").write_text("x")
    before = _outside_staging(root)
    writer = PacketWriter(registry, packet_id="s001")
    writer.add("core.processing_runs", _runs())
    assert writer.amend(root).passed
    assert before <= _outside_staging(root)
    assert not (root / STAGING).exists()
    assert validate(open_packet(root)).passed


def test_an_interrupted_amendment_is_undone_and_published_on_retry(tmp_path, registry, minimal, monkeypatch):
    """Stopped after the superseded manifest is retained, so the record's retained path exists too."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    real = PacketWriter._retain

    def retain(self, *args):
        real(self, *args)
        raise Interrupted

    monkeypatch.setattr(PacketWriter, "_retain", retain)
    with pytest.raises(Interrupted):
        _newer(registry, _runs()).amend(root)
    version, paths = read_promotion(root)
    assert version == "0.1.1"
    assert "registries/core/9.9.9.json.gz" in paths
    retained = next(p for p in paths if "manifests/0.1.0.json".startswith(p))
    assert (root / retained).exists()

    monkeypatch.undo()
    assert _newer(registry, _runs()).amend(root).passed
    manifest = json.loads((root / MANIFEST).read_text())
    assert (manifest["packet_version"], manifest["registries"]["core"]["path"]) == (
        "0.1.1",
        "registries/core/9.9.9.json.gz",
    )
    assert validate(open_packet(root)).passed
    assert not (root / STAGING).exists()


def test_a_refused_amendment_writes_nothing_outside_staging(tmp_path, registry, minimal):
    """Its new registry is bound under staging/ until validation passes."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    before = _outside_staging(root)
    with pytest.raises(CommitRefused):
        _newer(registry, _runs(status="bogus")).amend(root)
    assert _outside_staging(root) == before
    assert (root / STAGING / "registries" / "core" / "9.9.9.json.gz").exists()

"""Comparing a build against the packet it replaces (R63 §2)."""

from __future__ import annotations

import json

from escapewheel_writer.compare import lost, resources


def manifest(tmp_path, *ids, name="packet"):
    """Write a minimal manifest declaring these resources and return its root."""
    root = tmp_path / name
    root.mkdir()
    (root / "packet.json").write_text(
        json.dumps({"packet_id": "p", "resources": [{"resource_id": r} for r in ids]})
    )
    return root


def test_a_packets_resources_are_read_from_its_manifest(tmp_path):
    assert resources(manifest(tmp_path, "core.units", "core.trials")) == {"core.units", "core.trials"}


def test_the_manifest_may_be_named_directly(tmp_path):
    root = manifest(tmp_path, "core.units")
    assert resources(root / "packet.json") == {"core.units"}


def test_a_first_build_has_nothing_to_compare_against(tmp_path):
    # Not a failure: the reference is absent, so every comparison against it is empty.
    assert resources(tmp_path / "absent") == set()
    assert lost(resources(tmp_path / "absent"), ["core.units"]) == []


def test_an_unreadable_manifest_reports_no_resources(tmp_path):
    root = tmp_path / "broken"
    root.mkdir()
    (root / "packet.json").write_text("{not json")
    assert resources(root) == set()


def test_a_resource_the_reference_had_is_reported(tmp_path):
    before = resources(manifest(tmp_path, "core.units", "core.unit_quality_labels"))
    assert lost(before, ["core.units"]) == ["core.unit_quality_labels"]


def test_a_resource_only_the_build_has_is_not_reported(tmp_path):
    before = resources(manifest(tmp_path, "core.units"))
    assert lost(before, ["core.units", "analysis.spike_events"]) == []


def test_what_is_lost_is_sorted_so_two_runs_report_identically(tmp_path):
    before = resources(manifest(tmp_path, "core.z", "core.a", "core.m"))
    assert lost(before, []) == ["core.a", "core.m", "core.z"]

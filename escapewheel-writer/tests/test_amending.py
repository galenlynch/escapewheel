"""An amendment adds to a committed packet under a new manifest, or leaves it as it was."""

import json

import pytest
from escapewheel_reader import open_packet

from escapewheel_writer import CommitRefused, PacketWriter
from escapewheel_writer.amending import Held
from escapewheel_writer.errors import (
    AmendmentFault,
    AmendmentRefused,
    UsageError,
    UsageFault,
)
from tests.builders import commit_tables, import_runs

# -- amending a committed packet --------------------------------------------------------


def _amend(root, registry, tables, **kwargs):
    writer = PacketWriter(registry, packet_id=root.name, **kwargs)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    return writer.amend(root)


def test_an_amendment_adds_a_resource(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    report = _amend(root, registry, {"core.processing_runs": import_runs()})
    assert report.passed
    packet = open_packet(root)
    assert "core.processing_runs" in [r.resource_id for r in packet.resources()]
    assert packet.table("core.processing_runs").num_rows == 1


def test_an_amendment_re_runs_only_the_rules_its_resources_implicate(tmp_path, registry, minimal):
    """Part 05 §15.4. What it writes is what it must re-check; everything else is immutable."""
    import escapewheel_writer.publication as module

    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    seen = {}
    real = module.validate

    def spy(packet, **kwargs):
        seen.update(kwargs)
        return real(packet, **kwargs)

    module.validate = spy
    try:
        assert _amend(root, registry, {"core.processing_runs": import_runs()}).passed
    finally:
        module.validate = real
    assert seen["recheck"] == {"core.processing_runs"}


def test_an_amendment_still_validates_what_it_writes(tmp_path, registry, minimal):
    """Narrowing must not narrow away the added resource: `status` is a closed vocabulary."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    with pytest.raises(CommitRefused):
        _amend(root, registry, {"core.processing_runs": import_runs(status="finished")})


def test_an_amendment_bumps_the_version(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    before = json.loads((root / "packet.json").read_text())
    _amend(root, registry, {"core.processing_runs": import_runs()})
    after = json.loads((root / "packet.json").read_text())
    assert after["packet_version"] == "0.1.1"
    assert after["registries"] == before["registries"]


def test_an_amendment_keeps_packet_level_fields(tmp_path, registry, minimal):
    """Part 05 §15.3: derived from the superseded manifest, not rebuilt. A writer handed only the
    added resource knows nothing about the sessions the packet already declared."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal, description="a packet")
    _amend(root, registry, {"core.processing_runs": import_runs()})
    after = json.loads((root / "packet.json").read_text())
    assert after["sessions"] == ["s001"]
    assert after["description"] == "a packet"
    assert after["created_at"] == json.loads((root / "manifests" / "0.1.0.json").read_text())["created_at"]


def test_every_manifest_is_retained(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    _amend(root, registry, {"core.processing_runs": import_runs()})
    kept = sorted(p.name for p in (root / "manifests").iterdir())
    assert kept == ["0.1.0.json", "0.1.1.json"]


def test_amending_an_uncommitted_root_is_refused(tmp_path, registry, minimal):
    from escapewheel_writer.errors import NotCommitted

    with pytest.raises(NotCommitted):
        _amend(tmp_path / "nothing", registry, {"core.processing_runs": import_runs()})


def test_an_amendment_may_not_change_a_held_row(tmp_path, registry, minimal):
    """Part 05 §15.2: a packet whose core data changes is a new packet, not a new version."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    changed = [dict(minimal["core.sessions"][0], session_start_time="2026-08-28T00:00:00Z")]
    with pytest.raises(AmendmentRefused) as refused:
        _amend(root, registry, {"core.sessions": changed})
    assert (refused.value.code, refused.value.resource_id) == (AmendmentFault.CHANGES_HELD, "core.sessions")
    retimed = [dict(minimal["core.clocks"][0], tick_rate_num=1000)]
    with pytest.raises(AmendmentRefused) as refused:
        _amend(root, registry, {"core.clocks": retimed})
    assert (refused.value.code, refused.value.resource_id) == (AmendmentFault.CHANGES_HELD, "core.clocks")


def test_an_amendment_binding_a_registry_without_a_held_column_rewrites_its_rows_without_it(
    tmp_path, registry, minimal
):
    """Part 05 §15.6 compares held rows over the columns the amended manifest's registry declares, so
    a value in a column that registry no longer declares survives only in the superseded file."""
    import copy

    import pyarrow.parquet as pq

    earlier = copy.deepcopy(dict(registry))
    earlier["registry_version"] = "0.0.1"
    columns = earlier["resources"]["core.source_files"]["table"]["columns"]
    columns.insert(
        next(i for i, c in enumerate(columns) if c["name"] == "metadata"),
        {"name": "dropped_json", "type": "json_string", "presence": "optional", "role": "data", "description": "x"},
    )
    held = {"source_file_id": "f1", "uri": "file:///x", "dropped_json": '{"slope":2.0,"offset":5.0}'}
    root = tmp_path / "s001"
    commit_tables(root, earlier, {**minimal, "core.source_files": [held]})

    def source_files():
        entries = json.loads((root / "packet.json").read_text())["resources"]
        return root / next(e["uri"] for e in entries if e["resource_id"] == "core.source_files")

    superseded = source_files()
    rows = [{"source_file_id": "f1", "uri": "file:///x"}, {"source_file_id": "f2", "uri": "file:///y"}]
    assert _amend(root, registry, {"core.source_files": rows}).passed
    rewritten = pq.read_table(source_files())
    assert "dropped_json" not in rewritten.column_names
    assert sorted(rewritten.column("uri").to_pylist()) == ["file:///x", "file:///y"]
    assert pq.read_table(superseded).column("dropped_json").to_pylist() == ['{"slope":2.0,"offset":5.0}']


def test_an_amendment_drops_a_row_the_packet_holds(tmp_path, registry, minimal):
    """Part 05 §4.3: a row equal to a held row is dropped, and a table gaining none is not written."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    before = {e["resource_id"]: e["uri"] for e in json.loads((root / "packet.json").read_text())["resources"]}
    assert _amend(root, registry, {**minimal, "core.processing_runs": import_runs()}).passed
    after = {e["resource_id"]: e["uri"] for e in json.loads((root / "packet.json").read_text())["resources"]}
    assert {r: u for r, u in after.items() if r in before} == before
    assert set(after) - set(before) == {"core.processing_runs"}


def test_an_amendment_numbers_after_every_held_identifier(tmp_path, registry, minimal):
    """Part 05 §4.3: a held name keeps its number and an added one follows the largest held."""
    root = tmp_path / "s001"
    scoped = {"scope_kind": "core.sessions", "scope": "s001"}
    commit_tables(root, registry, {**minimal, "core.processing_runs": import_runs(**scoped)})
    added = [*import_runs(processing_run_id="run0", **scoped), *import_runs(**scoped)]
    assert _amend(root, registry, {"core.processing_runs": added}).passed
    runs = open_packet(root).table("core.processing_runs").to_pylist()
    assert [(r["processing_run_id"], r["processing_run_name"]) for r in runs] == [(0, "run1"), (1, "run0")]
    entry = next(
        e
        for e in json.loads((root / "packet.json").read_text())["resources"]
        if e["resource_id"] == "core.processing_runs"
    )
    assert entry["uri"] == "tables/core/processing_runs.0.1.1.parquet"
    assert (root / "tables/core/processing_runs.parquet").is_file()


def test_an_added_run_of_a_held_scope_is_preferred(tmp_path, registry, minimal):
    """Part 05 §12: the added run is an alternative to the held one, and the amendment says which is current."""
    root = tmp_path / "s001"
    scoped = {"scope_kind": "core.sessions", "scope": "s001"}
    commit_tables(root, registry, {**minimal, "core.processing_runs": import_runs(**scoped)})
    writer = PacketWriter(registry, packet_id=root.name)
    writer.amending(Held.open(root))
    name = writer.name_apart("processing_run_id", "run1")
    assert name == "run1.2"
    writer.add("core.processing_runs", import_runs(processing_run_id=name, **scoped))
    assert writer.amend(root).passed
    packet = open_packet(root)
    runs = {r["processing_run_id"]: r["processing_run_name"] for r in packet.table("core.processing_runs").to_pylist()}
    [preference] = packet.table("core.preferred_runs").to_pylist()
    assert runs[preference["processing_run_id"]] == "run1.2"


def test_a_preference_replaces_the_held_row_of_its_key(tmp_path, registry, minimal):
    """Part 05 §15.2: the one row an amendment may replace, and the superseded version keeps it."""
    root = tmp_path / "s001"
    scoped = {"scope_kind": "core.sessions", "scope": "s001"}
    runs = [*import_runs(**scoped), *import_runs(processing_run_id="run2", **scoped)]
    preference = {"session_id": "s001", "activity_type": "materialization", **scoped, "reason": "first"}
    commit_tables(
        root,
        registry,
        {**minimal, "core.processing_runs": runs, "core.preferred_runs": [dict(preference, processing_run_id="run1")]},
    )
    assert _amend(
        root, registry, {"core.preferred_runs": [dict(preference, processing_run_id="run2", reason="second")]}
    ).passed
    [row] = open_packet(root).table("core.preferred_runs").to_pylist()
    assert (row["processing_run_id"], row["reason"]) == (1, "second")


def test_an_amendment_may_extend_a_provenance_table(tmp_path, registry, minimal):
    """Append-only by nature: a later run does not change what an earlier one did."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    assert _amend(root, registry, {"core.processing_runs": import_runs()}).passed


def test_a_failed_amendment_leaves_the_packet_at_its_old_version(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    with pytest.raises(CommitRefused):
        _amend(root, registry, {"core.processing_runs": import_runs(status="bogus")})
    manifest = json.loads((root / "packet.json").read_text())
    assert manifest["packet_version"] == "0.1.0"
    assert "core.processing_runs" not in [r["resource_id"] for r in manifest["resources"]]


def test_an_amendment_installs_a_newer_registry_and_retains_the_old(tmp_path, registry, minimal):
    """Part 05 §15.3: the bound registry must describe the added resource, and the superseded one
    stays where its manifest names it, so a packet at the old version stays interpretable."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    newer = {**registry, "registry_version": "9.9.9"}
    writer = PacketWriter(newer, packet_id=root.name)
    writer.add("core.processing_runs", import_runs())
    assert writer.amend(root).passed
    bound = json.loads((root / "packet.json").read_text())["registries"]["core"]
    assert (bound["version"], bound["path"]) == ("9.9.9", "registries/core/9.9.9.json.gz")
    retained = json.loads((root / "manifests" / "0.1.0.json").read_text())["registries"]["core"]
    assert (root / retained["path"]).is_file()
    assert retained["version"] == registry["registry_version"]


def test_a_failed_amendment_restores_the_registry(tmp_path, registry, minimal):
    """The registry goes in before validation, so a refusal has to put it back."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    newer = {**registry, "registry_version": "9.9.9"}
    writer = PacketWriter(newer, packet_id=root.name)
    writer.add("core.processing_runs", import_runs(status="bogus"))
    with pytest.raises(CommitRefused):
        writer.amend(root)
    assert (
        json.loads((root / "packet.json").read_text())["registries"]["core"]["version"] == registry["registry_version"]
    )
    assert not (root / "registries" / "core" / "9.9.9.json.gz").exists()


def test_a_registry_that_changed_without_its_version_is_refused(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    import copy

    altered = copy.deepcopy(registry)
    altered["resources"]["core.sessions"]["table"]["columns"][0]["description"] = "changed, same version"
    writer = PacketWriter(altered, packet_id=root.name)
    writer.add("core.processing_runs", import_runs())
    with pytest.raises(UsageError) as refused:
        writer.amend(root)
    assert refused.value.code is UsageFault.REGISTRY_DIGEST_DIFFERS


def test_a_registry_colliding_with_a_retained_copy_is_refused(tmp_path, registry, minimal):
    """Part 05 §15.3: two digests under one registry ID and version would make the packet's own
    retained manifests name bytes that no longer exist."""
    import copy

    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)

    # Move off the registry's version, retaining it, then come back to it with different content.
    newer = {**copy.deepcopy(registry), "registry_version": "9.9.9"}
    writer = PacketWriter(newer, packet_id=root.name)
    writer.add("core.processing_runs", import_runs())
    assert writer.amend(root).passed

    altered = copy.deepcopy(registry)
    altered["resources"]["core.sessions"]["table"]["columns"][0]["description"] = "changed, same version"
    back = PacketWriter(altered, packet_id=root.name)
    back.add("core.source_files", [{"source_file_id": "f1", "uri": "file:///x"}])
    with pytest.raises(UsageError) as refused:
        back.amend(root)
    assert refused.value.code is UsageFault.REGISTRY_DIGEST_DIFFERS


def test_a_retained_binding_elsewhere_still_fixes_its_digest(tmp_path, registry, minimal):
    """Part 05 §15.3 judges two digests across every manifest, not only the file at one path."""
    import copy

    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    manifest = json.loads((root / "packet.json").read_text())
    moved = "registries/elsewhere.json.gz"
    (root / manifest["registries"]["core"]["path"]).rename(root / moved)
    manifest["registries"]["core"]["path"] = moved
    (root / "packet.json").write_text(json.dumps(manifest))

    altered = copy.deepcopy(registry)
    altered["resources"]["core.sessions"]["table"]["columns"][0]["description"] = "changed, same version"
    writer = PacketWriter(altered, packet_id=root.name)
    writer.add("core.processing_runs", import_runs())
    with pytest.raises(UsageError) as refused:
        writer.amend(root)
    assert refused.value.code is UsageFault.REGISTRY_DIGEST_DIFFERS
    assert not (root / "registries" / "core" / f"{registry['registry_version']}.json.gz").exists()

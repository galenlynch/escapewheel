"""The writer produces packets the validator accepts, and refuses ones it does not."""

import json

import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import RegistryRejected, RegistryState, check_table, validate

from escapewheel_writer import CommitRefused, PacketWriter
from escapewheel_writer.errors import (
    PacketOccupied,
    UndeclaredResource,
    UsageError,
    UsageFault,
)
from tests.builders import commit_tables


def test_constructor_rejects_a_nonvalid_registry_with_the_complete_result():
    with pytest.raises(RegistryRejected) as caught:
        PacketWriter({"$schema": "https://example.org/unknown"}, packet_id="s001")
    assert caught.value.result.state == RegistryState.UNSUPPORTED
    assert caught.value.result.to_dict()["state"] == RegistryState.UNSUPPORTED


def test_stamp_sets_columns_on_rows_already_added(registry, minimal):
    """The fact arrives after the row it belongs on is staged."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    changed = writer.stamp(
        "core.clocks", "clock_id", {"harp_s001": {"withheld_first_anchor": True, "withheld_last_anchor": False}}
    )
    assert changed == 1
    (clock,) = writer.rows("core.clocks")
    assert clock["withheld_first_anchor"] is True and clock["withheld_last_anchor"] is False
    assert clock["origin"] == "harp_epoch"  # the row it was, not a row standing in for it


def test_stamp_reports_a_miss_rather_than_raising(registry, minimal):
    """A count is what lets a caller tell a clock it could not reach from one it stamped."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    assert writer.stamp("core.clocks", "clock_id", {"absent": {"withheld_last_anchor": True}}) == 0


def test_stamp_refuses_a_resource_the_registry_does_not_define(registry):
    with pytest.raises(UndeclaredResource) as refused:
        PacketWriter(registry, packet_id="s001").stamp("core.nope", "id", {})
    assert refused.value.resource_id == "core.nope"


def test_commits_a_valid_packet(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    report = commit_tables(root, registry, minimal)
    assert report.passed
    assert (root / "packet.json").exists()
    assert validate(open_packet(root)).passed


def test_the_packet_reads_back(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    packet = open_packet(root)
    assert list(packet.sessions) == ["s001"]
    assert packet.table("core.clocks").column("tick_rate_num").to_pylist() == [31250]


def test_staging_is_gone_after_a_successful_commit(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    assert not (root / "staging").exists()


def test_a_failing_packet_is_not_committed(tmp_path, registry, minimal):
    """An unresolved foreign key means no manifest appears at the root at all."""
    broken = {**minimal, "core.clocks": [{**minimal["core.clocks"][0], "session_id": "s999"}]}
    root = tmp_path / "s001"
    with pytest.raises(CommitRefused) as caught:
        commit_tables(root, registry, broken)
    assert not (root / "packet.json").exists()
    assert (root / "staging").exists()  # left for inspection
    unresolved = check_table.reference_resolves("core.clocks", ["session_id"]).id
    assert any(f.check == unresolved for f in caught.value.report.findings)


def test_lineage_for_a_resource_the_packet_does_not_carry_is_refused(tmp_path, registry, minimal):
    """`derives` accepts a resource staged later, so the check waits for commit."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.derives("analysis.unit_rates", ["core.sessions"])
    root = tmp_path / "s001"
    with pytest.raises(UsageError) as refused:
        writer.commit(root)
    assert refused.value.code is UsageFault.LINEAGE_UNSTAGED
    assert refused.value.where == "analysis.unit_rates"
    assert not (root / "packet.json").exists()


def _workspace(tmp_path):
    """A delivery workspace holding what a `files-v0.1` source hands over."""
    workspace = tmp_path / "s001.deliveries"
    (workspace / "tables" / "delivery").mkdir(parents=True)
    (workspace / "tables" / "delivery" / "core.probes.parquet").write_bytes(b"")
    return workspace


def test_the_delivery_workspace_is_gone_after_a_successful_commit(tmp_path, registry, minimal):
    """Nothing in a committed packet points into it, so leaving it behind only accumulates."""
    workspace = _workspace(tmp_path)
    commit_tables(tmp_path / "s001", registry, minimal, workspace=workspace)
    assert not workspace.exists()


def test_a_refused_commit_keeps_the_delivery_workspace(tmp_path, registry, minimal):
    """Kept with staging: what a source delivered is evidence of why the packet failed."""
    broken = {**minimal, "core.clocks": [{**minimal["core.clocks"][0], "session_id": "s999"}]}
    workspace = _workspace(tmp_path)
    with pytest.raises(CommitRefused):
        commit_tables(tmp_path / "s001", registry, broken, workspace=workspace)
    assert (workspace / "tables" / "delivery" / "core.probes.parquet").exists()


def test_tables_are_written_in_the_registry_order(tmp_path, registry, minimal):
    """Part 03 §5.3: sorted by the primary key, whatever order the adapter emitted."""
    out_of_order = [{"subject_id": s, "species": "Mus musculus", "sex": "male"} for s in ("m004", "m002", "m003")]
    root = tmp_path / "s001"
    commit_tables(root, registry, {**minimal, "core.subjects": out_of_order + minimal["core.subjects"]})
    written = open_packet(root).table("core.subjects")
    # The key is the number. Numbers are assigned in name order, so a packet does not
    # depend on the order an adapter emitted in, and the names come back in the order they name.
    assert written.column("subject_id").to_pylist() == [0, 1, 2, 3]
    assert written.column("subject_name").to_pylist() == ["m001", "m002", "m003", "m004"]


def test_a_packet_without_sessions_is_refused(tmp_path, registry):
    """Part 04 §3: the manifest's session inventory may not be empty."""
    writer = PacketWriter(registry, packet_id="p")
    writer.add("core.subjects", [{"subject_id": "m001", "species": "Mus musculus", "sex": "male"}])
    with pytest.raises(UsageError) as refused:
        writer.commit(tmp_path / "p")
    assert refused.value.code is UsageFault.NO_SESSION


def test_a_naive_timestamp_is_refused(tmp_path, registry, minimal):
    """Part 03 requires a UTC offset; assuming one would be a guess."""
    from escapewheel_writer.errors import NaiveTimestamp

    naive = {**minimal, "core.sessions": [{**minimal["core.sessions"][0], "session_start_time": "2026-08-27T00:00:00"}]}
    with pytest.raises(NaiveTimestamp):
        commit_tables(tmp_path / "s001", registry, naive)


def test_the_registry_travels_with_the_packet(tmp_path, registry, minimal):
    """Part 04 §10: the digest covers the serialized bytes, stored as one gzip member (Part 03 §3.3)."""
    import gzip
    import hashlib

    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    manifest = json.loads((root / "packet.json").read_text())
    assert "registry_version" not in manifest
    descriptor = manifest["registries"]["core"]
    assert descriptor["role"] == "core"
    assert descriptor["version"] == registry["registry_version"] == "0.16.0"
    assert descriptor["path"] == "registries/core/0.16.0.json.gz"
    body = gzip.decompress((root / descriptor["path"]).read_bytes())
    assert hashlib.sha256(body).hexdigest() == descriptor["sha256"]
    assert json.loads(body) == dict(registry)


def test_an_unknown_resource_is_refused(registry):
    with pytest.raises(UndeclaredResource) as refused:
        PacketWriter(registry, packet_id="p").add("core.nonesuch", [])
    assert refused.value.resource_id == "core.nonesuch"


def test_committing_over_a_packet_is_refused(tmp_path, registry, minimal):
    """Immutability covers packet-owned bytes (Part 03 §8.1)."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    with pytest.raises(PacketOccupied) as refused:
        commit_tables(root, registry, minimal)
    assert refused.value.occupied == ["packet.json"]


def test_committing_over_an_interrupted_promotion_is_refused(tmp_path, registry, minimal):
    """A promoted directory with no manifest is a stray a writer may not remove (Part 05 §15.5), and
    promoting into it would nest the new one inside."""
    root = tmp_path / "s001"
    commit_tables(root, registry, minimal)
    (root / "packet.json").unlink()
    with pytest.raises(PacketOccupied) as refused:
        commit_tables(root, registry, minimal)
    assert "tables" in refused.value.occupied
    assert not (root / "tables" / "tables").exists()

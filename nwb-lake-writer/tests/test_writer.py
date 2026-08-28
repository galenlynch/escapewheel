"""The writer produces packets the validator accepts, and refuses ones it does not."""

import json

import pytest
from nwb_lake_reader import open_packet
from nwb_lake_validator import validate

from nwb_lake_writer import CommitRefused, PacketWriter


def _write(root, registry, tables, **kwargs):
    writer = PacketWriter(registry, packet_id=root.name, **kwargs)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    return writer.commit(root)


def test_commits_a_valid_packet(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    report = _write(root, registry, minimal)
    assert report.passed
    assert (root / "nwb.packet.json").exists()
    assert validate(open_packet(root)).passed


def test_the_packet_reads_back(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    packet = open_packet(root)
    assert list(packet.sessions) == ["s001"]
    assert packet.table("core.clocks").column("tick_rate_num").to_pylist() == [31250]


def test_staging_is_gone_after_a_successful_commit(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    assert not (root / "staging").exists()


def test_a_failing_packet_is_not_committed(tmp_path, registry, minimal):
    """An unresolved foreign key means no manifest appears at the root at all."""
    broken = {**minimal, "core.clocks": [{**minimal["core.clocks"][0], "session_id": "s999"}]}
    root = tmp_path / "s001"
    with pytest.raises(CommitRefused) as caught:
        _write(root, registry, broken)
    assert not (root / "nwb.packet.json").exists()
    assert (root / "staging").exists()  # left for inspection
    assert any(f.check == "core.clocks.session_id_resolves" for f in caught.value.report.findings)


def test_tables_are_written_in_the_registry_order(tmp_path, registry, minimal):
    """R10 §2: sorted by the primary key, whatever order the adapter emitted."""
    out_of_order = [{"subject_id": s, "species": "Mus musculus", "sex": "M"} for s in ("m004", "m002", "m003")]
    root = tmp_path / "s001"
    _write(root, registry, {**minimal, "core.subjects": out_of_order + minimal["core.subjects"]})
    written = open_packet(root).table("core.subjects")
    assert written.column("subject_id").to_pylist() == ["m001", "m002", "m003", "m004"]


def test_a_packet_without_sessions_is_refused(tmp_path, registry):
    """R1 §6: the manifest's session inventory may not be empty."""
    writer = PacketWriter(registry, packet_id="p")
    writer.add("core.subjects", [{"subject_id": "m001", "species": "Mus musculus", "sex": "M"}])
    with pytest.raises(ValueError, match="at least one session"):
        writer.commit(tmp_path / "p")


def test_a_naive_timestamp_is_refused(tmp_path, registry, minimal):
    """`03` requires a UTC offset; assuming one would be a guess."""
    from nwb_lake_writer.arrow import NaiveTimestamp

    naive = {**minimal, "core.sessions": [{**minimal["core.sessions"][0], "session_start_time": "2026-08-27T00:00:00"}]}
    with pytest.raises(NaiveTimestamp, match="no UTC offset"):
        _write(tmp_path / "s001", registry, naive)


def test_the_registry_travels_with_the_packet(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    embedded = json.loads((root / "schemas" / "logical_schemas.json").read_text())
    assert embedded["registry_version"] == registry["registry_version"]
    assert len(embedded["tables"]) == len(registry["tables"])


def test_an_unknown_resource_is_refused(registry):
    with pytest.raises(KeyError, match="no table"):
        PacketWriter(registry, packet_id="p").add("core.nonesuch", [])


def test_committing_over_a_packet_is_refused(tmp_path, registry, minimal):
    """Immutability covers packet-owned bytes (R14 §2.3)."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    with pytest.raises(FileExistsError):
        _write(root, registry, minimal)

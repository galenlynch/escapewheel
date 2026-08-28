"""The writer produces packets the validator accepts, and refuses ones it does not."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
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


def test_localize_resolves_dst_per_date():
    """A rig's zone is an IANA zone; its offset depends on the date (`inventory/` §3.1)."""
    from zoneinfo import ZoneInfo

    from nwb_lake_writer.arrow import localize

    la = ZoneInfo("America/Los_Angeles")
    assert localize("2025-04-09T17:25:12", la).utcoffset().total_seconds() == -7 * 3600  # PDT
    assert localize("2024-11-26T16:51:12", la).utcoffset().total_seconds() == -8 * 3600  # PST


def test_localize_refuses_a_fixed_offset():
    """A fixed offset is wrong for half the year, silently."""
    from datetime import timedelta, timezone

    from nwb_lake_writer.arrow import localize

    with pytest.raises(TypeError, match="IANA zone"):
        localize("2025-04-09T17:25:12", timezone(timedelta(hours=-7)))


def test_localize_leaves_an_aware_value_alone():
    from zoneinfo import ZoneInfo

    from nwb_lake_writer.arrow import localize

    aware = localize("2025-04-09T17:25:12+00:00", ZoneInfo("America/Los_Angeles"))
    assert aware.utcoffset().total_seconds() == 0


def test_metadata_is_serialized_to_canonical_json(tmp_path, registry, minimal):
    """Adapters build metadata as dictionaries; JSON encoding belongs to the profile."""
    clock = {**minimal["core.clocks"][0], "metadata": {"source": "harp", "board": 1}}
    root = tmp_path / "s001"
    _write(root, registry, {**minimal, "core.clocks": [clock]})
    written = open_packet(root).table("core.clocks").column("metadata").to_pylist()[0]
    assert written == '{"board":1,"source":"harp"}'  # keys sorted, no spaces


def test_metadata_drops_non_finite_numbers_rather_than_emitting_invalid_json(tmp_path, registry, minimal):
    """JSON has no NaN, and source data is full of it -- 384 electrodes' worth in one file."""
    clock = {**minimal["core.clocks"][0], "metadata": {"drift_ppm": float("nan"), "rate": 31250.0}}
    root = tmp_path / "s001"
    _write(root, registry, {**minimal, "core.clocks": [clock]})
    written = open_packet(root).table("core.clocks").column("metadata").to_pylist()[0]
    assert json.loads(written) == {"drift_ppm": None, "rate": 31250.0}


def test_a_metadata_string_is_left_alone(tmp_path, registry, minimal):
    """A caller that serialized its own JSON keeps its bytes."""
    clock = {**minimal["core.clocks"][0], "metadata": '{"already": "json"}'}
    root = tmp_path / "s001"
    _write(root, registry, {**minimal, "core.clocks": [clock]})
    assert open_packet(root).table("core.clocks").column("metadata").to_pylist()[0] == '{"already": "json"}'


def test_metadata_carries_sequences_and_arrays(tmp_path, registry, minimal):
    import numpy as np

    clock = {**minimal["core.clocks"][0], "metadata": {"anchors": [1, 2], "gains": np.array([0.5, 1.5])}}
    root = tmp_path / "s001"
    _write(root, registry, {**minimal, "core.clocks": [clock]})
    written = json.loads(open_packet(root).table("core.clocks").column("metadata").to_pylist()[0])
    assert written == {"anchors": [1, 2], "gains": [0.5, 1.5]}


def test_a_date_written_as_a_string_becomes_a_date(tmp_path, registry, minimal):
    subject = {**minimal["core.subjects"][0], "date_of_birth": "2024-09-24"}
    root = tmp_path / "s001"
    _write(root, registry, {**minimal, "core.subjects": [subject]})
    written = open_packet(root).table("core.subjects").column("date_of_birth").to_pylist()[0]
    assert (written.year, written.month, written.day) == (2024, 9, 24)


# -- the columnar path ---------------------------------------------------------------


def _spike_batch(n, unit, first_tick):
    """One batch of core.spike_events, already in the registry's sort order."""
    return pa.record_batch(
        {
            "session_id": pa.array(["s001"] * n),
            "unit_id": pa.array([unit] * n),
            "sorting_run_id": pa.array(["sort_1"] * n),
            "curation_id": pa.array(["cur_1"] * n),
            "t_tick": pa.array(range(first_tick, first_tick + n), type=pa.int64()),
            "clock_id": pa.array(["harp_s001"] * n),
            "amplitude": pa.array([-50.0] * n, type=pa.float32()),
        }
    )


def _add_spike_context(writer):
    """The rows core.spike_events references, so a commit can validate."""
    writer.add(
        "core.sorting_runs", [{"sorting_run_id": "sort_1", "session_id": "s001", "amplitude_unit": "uV"}]
    )  # R11 2: spikes carry amplitudes
    writer.add("core.curation_versions", [{"curation_id": "cur_1", "sorting_run_id": "sort_1", "session_id": "s001"}])
    writer.add(
        "core.units", [{"session_id": "s001", "unit_id": "u1", "sorting_run_id": "sort_1", "curation_id": "cur_1"}]
    )


def test_batches_reach_the_packet(tmp_path, registry, minimal):
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    writer.add_batches("core.spike_events", (_spike_batch(500, "u1", t) for t in (0, 500, 1000)))
    writer.commit(tmp_path / "pkt")
    table = pq.read_table(tmp_path / "pkt" / "tables" / "core" / "spike_events.parquet")
    assert table.num_rows == 1500
    assert table.column("t_tick").to_pylist()[:3] == [0, 1, 2]


def test_a_generator_is_consumed_lazily(tmp_path, registry):
    """Peak memory is one batch, so the source must not be materialized before commit."""
    seen = []

    def batches():
        for t in (0, 100):
            seen.append(t)
            yield _spike_batch(100, "u1", t)

    writer = PacketWriter(registry, packet_id="s001")
    writer.add_batches("core.spike_events", batches())
    assert seen == []  # nothing pulled at add time


def test_one_table_takes_one_path(registry):
    writer = PacketWriter(registry, packet_id="s001")
    writer.add("core.spike_events", [{"session_id": "s001"}])
    with pytest.raises(ValueError, match="already has records"):
        writer.add_batches("core.spike_events", [])
    writer2 = PacketWriter(registry, packet_id="s001")
    writer2.add_batches("core.spike_events", [])
    with pytest.raises(ValueError, match="already has batches"):
        writer2.add_batches("core.spike_events", [])


def test_a_later_batch_may_omit_a_declared_column(tmp_path, registry, minimal):
    """It is written as nulls, the way a record that lacks the key is."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    wide = _spike_batch(10, "u1", 0)
    narrow = _spike_batch(10, "u1", 10).drop_columns(["amplitude"])
    writer.add_batches("core.spike_events", iter([wide, narrow]))
    writer.commit(tmp_path / "pkt")
    table = pq.read_table(tmp_path / "pkt" / "tables" / "core" / "spike_events.parquet")
    assert table.column("amplitude").to_pylist() == [-50.0] * 10 + [None] * 10


def test_a_later_batch_may_not_introduce_a_column(tmp_path, registry, minimal):
    """It is not in the schema the first batch fixed, so it would vanish silently."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    plain = _spike_batch(10, "u1", 0)
    extra = pa.record_batch(
        [*plain.columns, pa.array(['{"a":1}'] * 10)],
        names=[*plain.schema.names, "metadata"],
    )
    writer.add_batches("core.spike_events", iter([plain, extra]))
    with pytest.raises(ValueError, match="dropped silently"):
        writer.commit(tmp_path / "pkt")


def test_an_unknown_resource_is_refused_on_the_batch_path_too(registry):
    writer = PacketWriter(registry, packet_id="s001")
    with pytest.raises(KeyError, match="no table"):
        writer.add_batches("core.not_a_table", [])

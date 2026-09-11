"""The writer produces packets the validator accepts, and refuses ones it does not."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import open_packet
from escapewheel_validator import validate

from escapewheel_writer import CommitRefused, PacketWriter
from escapewheel_writer.encoding import (
    DELTA_COLUMNS,
    DICTIONARY_COLUMNS,
    NO_DICTIONARY,
    inefficient,
)


def _write(root, registry, tables, **kwargs):
    writer = PacketWriter(registry, packet_id=root.name, **kwargs)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    return writer.commit(root)


def test_stamp_sets_columns_on_rows_already_added(registry, minimal):
    """R99 §3.2: the fact arrives after the row it belongs on is staged."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    changed = writer.stamp("core.clocks", "clock_id",
                           {"harp_s001": {"withheld_first_anchor": True,
                                          "withheld_last_anchor": False}})
    assert changed == 1
    (clock,) = writer._tables["core.clocks"]
    assert clock["withheld_first_anchor"] is True and clock["withheld_last_anchor"] is False
    assert clock["clock_name"] == "harp"  # the row it was, not a row standing in for it


def test_stamp_reports_a_miss_rather_than_raising(registry, minimal):
    """A count is what lets a caller tell a clock it could not reach from one it stamped."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    assert writer.stamp("core.clocks", "clock_id", {"absent": {"withheld_last_anchor": True}}) == 0


def test_stamp_refuses_a_resource_the_registry_does_not_define(registry):
    with pytest.raises(KeyError):
        PacketWriter(registry, packet_id="s001").stamp("core.nope", "id", {})


def test_commits_a_valid_packet(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    report = _write(root, registry, minimal)
    assert report.passed
    assert (root / "packet.json").exists()
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
    assert not (root / "packet.json").exists()
    assert (root / "staging").exists()  # left for inspection
    assert any(f.check == "core.clocks.session_id_resolves" for f in caught.value.report.findings)


def test_tables_are_written_in_the_registry_order(tmp_path, registry, minimal):
    """`03` §5.3: sorted by the primary key, whatever order the adapter emitted."""
    out_of_order = [{"subject_id": s, "species": "Mus musculus", "sex": "male"} for s in ("m004", "m002", "m003")]
    root = tmp_path / "s001"
    _write(root, registry, {**minimal, "core.subjects": out_of_order + minimal["core.subjects"]})
    written = open_packet(root).table("core.subjects")
    # R53 §2.1: the key is the number. Numbers are assigned in name order, so a packet does not
    # depend on the order an adapter emitted in, and the names come back in the order they name.
    assert written.column("subject_id").to_pylist() == [0, 1, 2, 3]
    assert written.column("subject_name").to_pylist() == ["m001", "m002", "m003", "m004"]


def test_a_packet_without_sessions_is_refused(tmp_path, registry):
    """R1 §6: the manifest's session inventory may not be empty."""
    writer = PacketWriter(registry, packet_id="p")
    writer.add("core.subjects", [{"subject_id": "m001", "species": "Mus musculus", "sex": "male"}])
    with pytest.raises(ValueError, match="at least one session"):
        writer.commit(tmp_path / "p")


def test_a_naive_timestamp_is_refused(tmp_path, registry, minimal):
    """`03` requires a UTC offset; assuming one would be a guess."""
    from escapewheel_writer.arrow import NaiveTimestamp

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
    with pytest.raises(KeyError, match="no registry defines a table"):
        PacketWriter(registry, packet_id="p").add("core.nonesuch", [])


def test_committing_over_a_packet_is_refused(tmp_path, registry, minimal):
    """Immutability covers packet-owned bytes (`04` §5.1)."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    with pytest.raises(FileExistsError):
        _write(root, registry, minimal)


def test_localize_resolves_dst_per_date():
    """A rig's zone is an IANA zone; its offset depends on the date (`inventory/` §3.1)."""
    from zoneinfo import ZoneInfo

    from escapewheel_writer.arrow import localize

    la = ZoneInfo("America/Los_Angeles")
    assert localize("2025-04-09T17:25:12", la).utcoffset().total_seconds() == -7 * 3600  # PDT
    assert localize("2024-11-26T16:51:12", la).utcoffset().total_seconds() == -8 * 3600  # PST


def test_localize_refuses_a_fixed_offset():
    """A fixed offset is wrong for half the year, silently."""
    from datetime import timedelta, timezone

    from escapewheel_writer.arrow import localize

    with pytest.raises(TypeError, match="IANA zone"):
        localize("2025-04-09T17:25:12", timezone(timedelta(hours=-7)))


def test_localize_leaves_an_aware_value_alone():
    from zoneinfo import ZoneInfo

    from escapewheel_writer.arrow import localize

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
    """One batch of core.spike_events, already in the registry's sort order.

    `unit` is the number the writer assigned (R81 §2.1), not the sorter's label: a batch is
    written as given, so a caller streaming one supplies identifiers the packet already knows.
    """
    return pa.record_batch(
        {
            "session_id": pa.array(["s001"] * n),
            "unit_id": pa.array([unit] * n),
            "t_tick": pa.array(range(first_tick, first_tick + n), type=pa.int64()),
            "amplitude": pa.array([-50.0] * n, type=pa.float32()),
        }
    )


def _add_spike_context(writer):
    """The rows core.spike_events references, so a commit can validate."""
    writer.add("core.sorting_runs", [{"sorting_run_id": "sort_1", "session_id": "s001"}])
    writer.add("core.curation_versions", [{"curation_id": "cur_1", "sorting_run_id": "sort_1", "session_id": "s001"}])
    # R96 §3: the unit names the clock its ticks are counted on and the unit of measure its
    # amplitudes are in, and a spike reaches both in one hop.
    writer.add("core.units", [{"session_id": "s001", "unit_id": 1, "sorting_run_id": "sort_1",
                               "curation_id": "cur_1", "clock_id": "harp_s001", "amplitude_unit": "uV"}])


def test_batches_reach_the_packet(tmp_path, registry, minimal):
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    unit = writer.keys.of("unit", "1")
    writer.add_batches("core.spike_events", (_spike_batch(500, unit, t) for t in (0, 500, 1000)))
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
            yield _spike_batch(100, 1, t)

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
    unit = writer.keys.of("unit", "1")
    wide = _spike_batch(10, unit, 0)
    narrow = _spike_batch(10, unit, 10).drop_columns(["amplitude"])
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
    unit = writer.keys.of("unit", "1")
    plain = _spike_batch(10, unit, 0)
    later = _spike_batch(10, unit, 10)  # continues the order, so the schema is what fails
    extra = pa.record_batch(
        [*later.columns, pa.array(['{"a":1}'] * 10)],
        names=[*later.schema.names, "metadata"],
    )
    writer.add_batches("core.spike_events", iter([plain, extra]))
    with pytest.raises(ValueError, match="dropped silently"):
        writer.commit(tmp_path / "pkt")


def test_an_unknown_resource_is_refused_on_the_batch_path_too(registry):
    writer = PacketWriter(registry, packet_id="s001")
    with pytest.raises(KeyError, match="no registry defines a table"):
        writer.add_batches("core.not_a_table", [])


# -- amending a committed packet (R32) --------------------------------------------------


def _amend(root, registry, tables, **kwargs):
    writer = PacketWriter(registry, packet_id=root.name, **kwargs)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    return writer.amend(root)


def _runs(**overrides):
    """A materialization activity (`04` §3), which is what an amendment normally carries."""
    return [
        {
            "processing_run_id": "run1",
            # `02` §7.1: a run is session-scoped, and an amendment names the session it is for
            # rather than inheriting one -- the packet it amends may hold more than one.
            "session_id": "s001",
            "activity_type": "materialization",
            "software_name": "escapewheel_writer",
            "software_version": "0.0.0",
            "status": "succeeded",
            **overrides,
        }
    ]


def test_an_amendment_adds_a_resource(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    report = _amend(root, registry, {"core.processing_runs": _runs()})
    assert report.passed
    packet = open_packet(root)
    assert "core.processing_runs" in [r.resource_id for r in packet.resources()]
    assert packet.table("core.processing_runs").num_rows == 1


def test_an_amendment_re_runs_only_the_rules_its_resources_implicate(tmp_path, registry, minimal):
    """`03` §9.4. What it writes is what it must re-check; everything else is immutable."""
    import escapewheel_writer.writer as module

    root = tmp_path / "s001"
    _write(root, registry, minimal)
    seen = {}
    real = module.validate

    def spy(packet, **kwargs):
        seen.update(kwargs)
        return real(packet, **kwargs)

    module.validate = spy
    try:
        assert _amend(root, registry, {"core.processing_runs": _runs()}).passed
    finally:
        module.validate = real
    assert seen["recheck"] == {"core.processing_runs"}


def test_an_amendment_still_validates_what_it_writes(tmp_path, registry, minimal):
    """Narrowing must not narrow away the added resource: `status` is a closed vocabulary."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    with pytest.raises(CommitRefused):
        _amend(root, registry, {"core.processing_runs": _runs(status="finished")})


def test_an_amendment_bumps_the_version_and_says_what_it_supersedes(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    before = json.loads((root / "packet.json").read_text())
    _amend(root, registry, {"core.processing_runs": _runs()})
    after = json.loads((root / "packet.json").read_text())
    assert after["packet_version"] == "0.1.1"
    assert after["supersedes"] == before["packet_version"]


def test_an_amendment_keeps_packet_level_fields(tmp_path, registry, minimal):
    """`03` §9.3: derived from the superseded manifest, not rebuilt. A writer handed only the
    added resource knows nothing about the sessions the packet already declared."""
    root = tmp_path / "s001"
    _write(root, registry, minimal, description="a packet")
    _amend(root, registry, {"core.processing_runs": _runs()})
    after = json.loads((root / "packet.json").read_text())
    assert after["sessions"] == ["s001"]
    assert after["description"] == "a packet"
    assert after["created_at"] == json.loads((root / "manifests" / "nwb.packet.0.1.0.json").read_text())["created_at"]


def test_every_manifest_is_retained(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    _amend(root, registry, {"core.processing_runs": _runs()})
    kept = sorted(p.name for p in (root / "manifests").iterdir())
    assert kept == ["nwb.packet.0.1.0.json", "nwb.packet.0.1.1.json"]


def test_amending_an_uncommitted_root_is_refused(tmp_path, registry, minimal):
    from escapewheel_writer.writer import NotCommitted

    with pytest.raises(NotCommitted, match="no committed"):
        _amend(tmp_path / "nothing", registry, {"core.processing_runs": _runs()})


def test_an_amendment_may_not_replace_a_core_resource(tmp_path, registry, minimal):
    """`03` §9.2: a packet whose core data changes is a new packet, not a new version."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    with pytest.raises(ValueError, match="new packet"):
        _amend(root, registry, {"core.sessions": minimal["core.sessions"]})


def test_an_amendment_may_extend_a_provenance_table(tmp_path, registry, minimal):
    """Append-only by nature: a later run does not change what an earlier one did."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    assert _amend(root, registry, {"core.processing_runs": _runs()}).passed


def test_a_failed_amendment_leaves_the_packet_at_its_old_version(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    with pytest.raises(CommitRefused):
        _amend(root, registry, {"core.processing_runs": _runs(status="bogus")})
    manifest = json.loads((root / "packet.json").read_text())
    assert manifest["packet_version"] == "0.1.0"
    assert "core.processing_runs" not in [r["resource_id"] for r in manifest["resources"]]


def test_an_amendment_installs_a_newer_registry_and_retains_the_old(tmp_path, registry, minimal):
    """`03` §9.3: the embedded copy must describe the added resource, and the superseded one
    is kept so a packet at the old version stays interpretable."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    newer = {**registry, "registry_version": "9.9.9"}
    writer = PacketWriter(newer, packet_id=root.name)
    writer.add("core.processing_runs", _runs())
    assert writer.amend(root).passed
    installed = json.loads((root / "schemas" / "logical_schemas.json").read_text())
    assert installed["registry_version"] == "9.9.9"
    kept = json.loads((root / "schemas" / f"logical_schemas.{registry['registry_version']}.json").read_text())
    assert kept["registry_version"] == registry["registry_version"]
    assert json.loads((root / "packet.json").read_text())["registry_version"] == "9.9.9"


def test_a_failed_amendment_restores_the_registry(tmp_path, registry, minimal):
    """The registry goes in before validation, so a refusal has to put it back."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    newer = {**registry, "registry_version": "9.9.9"}
    writer = PacketWriter(newer, packet_id=root.name)
    writer.add("core.processing_runs", _runs(status="bogus"))
    with pytest.raises(CommitRefused):
        writer.amend(root)
    installed = json.loads((root / "schemas" / "logical_schemas.json").read_text())
    assert installed["registry_version"] == registry["registry_version"]
    assert not (root / "schemas" / f"logical_schemas.{registry['registry_version']}.json").exists()


def test_a_registry_that_changed_without_its_version_is_refused(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    import copy

    altered = copy.deepcopy(registry)
    altered["tables"]["core.sessions"]["columns"][0]["description"] = "changed, same version"
    writer = PacketWriter(altered, packet_id=root.name)
    writer.add("core.processing_runs", _runs())
    with pytest.raises(ValueError, match="cannot be told apart"):
        writer.amend(root)


def test_a_registry_colliding_with_a_retained_copy_is_refused(tmp_path, registry, minimal):
    """`03` §9.3: two different registries at one version inside one packet would make its own
    retained manifests name something that no longer identifies anything."""
    import copy

    root = tmp_path / "s001"
    _write(root, registry, minimal)

    # Move off 0.1.0, retaining it, then try to come back to 0.1.0 with different content.
    newer = {**copy.deepcopy(registry), "registry_version": "9.9.9"}
    writer = PacketWriter(newer, packet_id=root.name)
    writer.add("core.processing_runs", _runs())
    assert writer.amend(root).passed

    altered = copy.deepcopy(registry)
    altered["tables"]["core.sessions"]["columns"][0]["description"] = "changed, same version"
    back = PacketWriter(altered, packet_id=root.name)
    back.add("core.source_files", [{"source_file_id": "f1", "uri": "file:///x"}])
    with pytest.raises(ValueError, match="two different .* in one packet"):
        back.amend(root)


# -- dense arrays (Phase 5) ---------------------------------------------------------------


def _waveforms(units=8, channels=4, samples=10):
    """A small stand-in with the shape a waveform array has: units, channels, samples."""
    import numpy as np

    rng = np.random.default_rng(0)
    return (rng.normal(0, 100, (units, channels, samples))).astype("int16")


def _array_tables(uri: str = "arrays/core/waveform_means.zarr") -> dict[str, list[dict]]:
    """The rows an array must be accompanied by: `03` §6.2 requires every axis to be named."""
    return {
        "core.array_assets": [
            {
                "array_asset_id": "wf",
                "session_id": "s001",
                "semantic_type": "waveform_mean",
                "array_asset_name": "mean waveform per unit",
                "uri": uri,
                "format": "zarr_v3",
            }
        ],
        "core.array_dimensions": [
            {"array_asset_id": "wf", "axis_index": i, "dimension_name": n}
            for i, n in enumerate(("unit", "channel", "sample"))
        ],
    }


def test_an_array_is_written_as_zarr_v3(tmp_path, registry, minimal):
    from escapewheel_writer.writer import StagedArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in _array_tables().items():
        writer.add(resource_id, records)
    values = _waveforms()
    writer.add_array(
        "core.waveform_means",
        StagedArray(values=values, array_asset_id="wf", chunks=(1, 4, 10), shard=(4, 4, 10)),
    )
    report = writer.commit(root)
    assert report.passed
    entry = next(
        r
        for r in json.loads((root / "packet.json").read_text())["resources"]
        if r["resource_id"] == "core.waveform_means"
    )
    assert entry["kind"] == "dense_array_asset"
    assert entry["physical_profile"] == "zarr_v3"  # `03` §6.1: packet-owned must be v3
    # Sharding is a codec, and the manifest must say so: a reader without sharding support
    # would otherwise read `["blosc"]` and discover the shard only on opening the array.
    assert entry["codecs"] == ["sharding_indexed", "blosc"]
    assert (root / "arrays" / "core" / "waveform_means.zarr").is_dir()


def test_the_array_reads_back_identically(tmp_path, registry, minimal):
    import numpy as np
    import zarr

    from escapewheel_writer.writer import StagedArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    for resource_id, records in _array_tables().items():
        writer.add(resource_id, records)
    values = _waveforms()
    writer.add_array(
        "core.waveform_means", StagedArray(values=values, array_asset_id="wf", chunks=(1, 4, 10), shard=(4, 4, 10))
    )
    writer.commit(root)
    back = zarr.open_array(str(root / "arrays" / "core" / "waveform_means.zarr"), mode="r")
    assert np.array_equal(np.asarray(back[:]), values)


def test_a_shard_that_is_not_whole_chunks_is_refused(tmp_path, registry, minimal):
    """A partial shard is not a regular chunk grid, which `03` §6.1 requires."""
    from escapewheel_writer.writer import StagedArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.add_array(
        "core.waveform_means",
        StagedArray(values=_waveforms(), array_asset_id="wf", chunks=(3, 4, 10), shard=(4, 4, 10)),
    )
    with pytest.raises(ValueError, match="whole number of chunks"):
        writer.commit(root)


def test_a_codec_outside_the_floor_is_written_and_declared(tmp_path):
    """`03` §6.4: a writer MAY use any Zarr codec so long as the manifest names it.

    The floor is a reader obligation -- `Packet.unopenable` is where a reader finds out it
    cannot open an array -- so refusing here would enforce against a writer a rule written for
    readers, and would make R14's own LFP case unwritable.
    """
    from escapewheel_writer.arrays import declared_codecs
    from escapewheel_writer.writer import StagedArray

    spec = StagedArray(values=_waveforms(), array_asset_id="wf", chunks=(1, 4, 10), codecs=("numcodecs.delta", "zstd"))
    assert declared_codecs(spec) == ("numcodecs.delta", "zstd")

    from escapewheel_writer.arrays import write_zarr

    written = write_zarr(tmp_path / "wf.zarr", spec)
    assert written > 0
    import zarr

    assert (zarr.open(tmp_path / "wf.zarr", mode="r")[:] == spec.values).all()


def test_shard_size_follows_the_bandwidth_delay_product():
    """The rule is `S = share/(1-share) * latency * bandwidth`, not a constant.

    A store read from inside the same region has an order less latency and more bandwidth, so
    the object that spends the same fraction of a fetch on transfer is several times smaller.
    A number baked in would be wrong exactly where the data lives.
    """
    from escapewheel_writer.arrays import shard_for, target_object_bytes

    off = target_object_bytes()
    near = target_object_bytes(latency_s=0.005, bandwidth_bps=100e6)
    assert off > near * 2
    far = shard_for((6781, 26, 150), (1, 26, 150), 3850)
    close = shard_for((6781, 26, 150), (1, 26, 150), 3850, target_bytes=near)
    assert far is not None and close is not None
    assert far[0] > close[0]


def test_a_power_of_two_is_preferred_only_inside_the_band():
    from escapewheel_writer.arrays import BAND, shard_for, target_object_bytes

    target = target_object_bytes()
    chosen = shard_for((6781, 26, 150), (1, 26, 150), 3850)
    assert chosen is not None
    per = chosen[0]
    assert per & (per - 1) == 0, "a power of two was available inside the band"
    assert target / BAND <= per * 3850 <= target * BAND


def test_an_array_that_fits_one_object_is_not_sharded():
    """A shard would add an index and buy nothing."""
    from escapewheel_writer.arrays import shard_for

    assert shard_for((100, 26, 150), (1, 26, 150), 3850) is None


def test_one_batch_becomes_exactly_one_row_group(tmp_path, registry):
    """The streaming path's boundary guarantee, which `03` §5.4 and S3 sizing both rest on.

    pyarrow's own default is 2**20 rows per row group, so a larger batch is silently cut into
    several. That would put `analysis.spike_events` row groups across time-bucket boundaries and
    would quietly cap any row-group size a caller chose for the store the packet will live on.
    """
    import pyarrow as pa

    from escapewheel_writer.writer import _write_stream

    rows = (1 << 20) + 200_000  # deliberately over pyarrow's default cut
    spec = registry["tables"]["core.spike_events"]
    batch = pa.record_batch(
        {
            # int32 since R53 §2.1. `_write_stream` is below `add_batches`, which is where a
            # streamed batch's identifiers are numbered, so this builds them already numbered.
            "session_id": pa.repeat(pa.scalar(0, pa.int32()), rows),
            "unit_id": pa.repeat(pa.scalar(1, pa.int32()), rows),
            "t_tick": pa.array(range(rows), type=pa.int64()),
        }
    )
    tail = pa.record_batch(
        {
            **{name: batch.column(name) for name in batch.schema.names if name != "t_tick"},
            "t_tick": pa.array(range(rows, rows + batch.num_rows), type=pa.int64()),
        },
    ).slice(0, 1000)
    path = tmp_path / "spike_events.parquet"
    _write_stream(spec, [batch, tail], path, "core.spike_events")

    metadata = pq.ParquetFile(path).metadata
    assert metadata.num_row_groups == 2, "a batch was split into several row groups"
    assert [metadata.row_group(i).num_rows for i in range(2)] == [rows, 1000]


def test_an_out_of_order_stream_is_refused_while_staging(tmp_path, registry, minimal):
    """The order is established on the way in, so a bad stream fails before anything is written.

    Previously this reached the file and surfaced as a physical_order warning after 467 MB of
    re-reading; now it stops at the batch that breaks it.
    """
    from escapewheel_validator import OrderViolation

    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    writer.add_batches("core.spike_events", iter([_spike_batch(10, 1, 10), _spike_batch(10, 1, 0)]))
    with pytest.raises(OrderViolation, match="sorts before"):
        writer.commit(tmp_path / "pkt")


def test_a_record_carrying_an_undeclared_column_is_refused(registry):
    """Both entry points refuse it, which is the whole point.

    `add_batches` always has; `add` documented the key as ignored, so one adapter defect was a
    build failure through one door and a dropped column through the other. Three test fixtures
    were carrying `name` where the registry declares `array_asset_name` and `clock_name`, and
    nothing said so.
    """
    writer = PacketWriter(registry, packet_id="s001")
    with pytest.raises(ValueError, match="declared by no registry"):
        writer.add("core.clocks", [{"clock_id": "c", "session_id": "s001", "name": "master"}])


def test_a_batch_says_which_of_the_two_causes_it_hit(tmp_path, registry, minimal):
    """An undeclared column and a late optional one send an author to different files.

    The check fires on the first batch too, where only the first cause is possible, so a message
    naming only the second described the rarer case.
    """
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    batch = _spike_batch(4, 1, 0)
    stray = pa.record_batch(
        {**{n: batch.column(n) for n in batch.schema.names},
         "nonsense": pa.array([1, 2, 3, 4], type=pa.int64())}
    )
    writer.add_batches("core.spike_events", iter([stray]))
    with pytest.raises(ValueError, match=r"\['nonsense'\] is declared by no registry"):
        writer.commit(tmp_path / "pkt")


def test_an_optional_column_absent_from_the_first_batch_says_so(tmp_path, registry, minimal):
    """The other cause: `schema` omits an optional column no first batch carries (`02` §6).

    Nothing is undeclared here, so the fix is to the stream rather than to a registry, which is
    why the two read differently.
    """
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    rows = {"session_id": pa.array(["s001"]), "stream_id": pa.array(["s"]),
            "t_tick": pa.array([1], type=pa.int64())}
    writer.add_batches(
        "core.events",
        iter([pa.record_batch(rows),
              pa.record_batch({**rows, "t_tick": pa.array([2], type=pa.int64()),
                               "metadata": pa.array(['{"a": 1}'])})]),
    )
    with pytest.raises(ValueError, match=r"\['metadata'\] is optional and absent"):
        writer.commit(tmp_path / "pkt")


def test_a_duplicate_across_batches_is_refused_while_staging(tmp_path, registry, minimal):
    from escapewheel_validator import OrderViolation

    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    writer.add_batches("core.spike_events", iter([_spike_batch(10, 1, 0), _spike_batch(1, 1, 9)]))
    with pytest.raises(OrderViolation, match="repeats"):
        writer.commit(tmp_path / "pkt")


def test_a_materializer_may_add_rows_to_an_already_staged_table(tmp_path, registry, minimal):
    """The run record lands in `core.processing_runs`, which staging has already written.

    Restaging only what is new leaves that row in memory, and the derived resource then names a
    run the packet does not contain — which the validator reports rather than the writer.
    """
    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.add("core.processing_runs", [_run("run_import")])

    def derive(packet, target):
        # `04` §3: a materialization records what produced it, which its own rule checks.
        target.add(
            "core.processing_runs",
            [dict(_run("run_derived", "materialization"),
                  software_name="escapewheel_writer", software_version="0.0.0")],
        )

    writer.commit(root, materialize=[derive])

    runs = pq.read_table(root / "tables" / "core" / "processing_runs.parquet")
    # R53: the key is a number and the name is what it stands for. Both runs are present, and
    # the materializer's run is numbered by the same Keys the staged rows used.
    assert sorted(runs.column("processing_run_name").to_pylist()) == ["run_derived", "run_import"]
    assert sorted(runs.column("processing_run_id").to_pylist()) == [0, 1]
    entries = [e for e in json.loads((root / "packet.json").read_text())["resources"]]
    assert [e["resource_id"] for e in entries].count("core.processing_runs") == 1, "duplicated entry"


def _run(run_id, activity="import"):
    """One `core.processing_runs` row.

    The activity is a parameter because R82 §2.2 makes two runs of one activity declare their
    scopes, and a derived run is a materialization rather than a second import (`04` §3).
    """
    return {
        "processing_run_id": run_id,
        "session_id": "s001",
        "activity_type": activity,
        "status": "succeeded",
    }


def test_a_referenced_array_is_declared_external_and_copied_nowhere(tmp_path, registry, minimal):
    """`04` §5.1: the bytes stay where they are and the packet says where that is."""
    from escapewheel_writer.writer import ExternalArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.reference_array(
        "core.probe.lfp",
        ExternalArray(
            array_asset_id="probe.lfp",
            uri="s3://bucket/lfp",
            physical_profile="zarr_v2",
            codecs=("blosc",),
            size_bytes=17,
        ),
    )
    assert writer.commit(root).passed
    entry = next(
        r
        for r in json.loads((root / "packet.json").read_text())["resources"]
        if r["resource_id"] == "core.probe.lfp"
    )
    assert entry["external"] is True
    assert entry["physical_profile"] == "zarr_v2"
    assert entry["uri"] == "s3://bucket/lfp"
    assert entry["size_bytes"] == 17
    assert not (root / "arrays").exists(), "nothing was copied"


def test_a_relative_reference_is_refused(tmp_path, registry):
    """A relative URI resolves against a packet the bytes do not live in."""
    from escapewheel_writer.writer import ExternalArray

    writer = PacketWriter(registry, packet_id="s001")
    with pytest.raises(ValueError, match="not absolute"):
        writer.reference_array("core.probe.lfp", ExternalArray(array_asset_id="probe.lfp", uri="arrays/lfp"))


def test_a_referenced_codec_joins_required_codecs(tmp_path, registry, minimal):
    """`04` §3: the top-level list is the union, so a reader can answer the whole-packet question."""
    from escapewheel_writer.writer import ExternalArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id="s001")
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.reference_array(
        "core.probe.lfp",
        ExternalArray(array_asset_id="probe.lfp", uri="s3://bucket/lfp", physical_profile="zarr_v2", codecs=("blosc",)),
    )
    writer.commit(root)
    assert json.loads((root / "packet.json").read_text())["required_codecs"] == ["blosc"]


def test_no_catalog_names_a_resource_that_is_not_in_place(tmp_path, registry, minimal):
    """`05` §6: a reader sees the previous catalog or the new one, never a partial one.

    The invariant is about visibility, not about the mechanism: whatever primitive publishes the
    catalog, every resource it names must already be at its final location. Checked by reading
    the committed catalog and demanding every packet-owned URI resolve.
    """
    root = tmp_path / "packet"
    writer = PacketWriter(registry, packet_id="p")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    writer.commit(root)

    manifest = json.loads((root / "packet.json").read_text())
    absent = [r["uri"] for r in manifest["resources"] if not r.get("external") and not (root / r["uri"]).exists()]
    assert not absent, f"the catalog names {absent}, which are not in place"


def test_a_refused_commit_publishes_no_catalog(tmp_path, registry, minimal):
    """`05` §6 again, from the other side: a failed commit leaves the previous state visible.

    Here there is no previous state, so nothing at all may be published -- a catalog naming
    resources that failed validation is the thing the ordering exists to prevent.
    """
    root = tmp_path / "packet"
    writer = PacketWriter(registry, packet_id="p")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    # A clock that names a parent it does not have: refused by the generated foreign key.
    writer.add(
        "core.clocks",
        [{"clock_id": "orphan", "session_id": "s1", "clock_name": "x", "origin": "sample 0",
          "parent_clock_id": "nowhere"}],
    )
    with pytest.raises(CommitRefused):
        writer.commit(root)
    assert not (root / "packet.json").exists()


def test_a_referenced_source_reaches_the_default_document(tmp_path, registry, minimal):
    """`04` §5.5: written at the packet root, and not declared as a resource."""
    from escapewheel_writer.writer import ExternalArray

    root = tmp_path / "s001"
    writer = PacketWriter(registry, packet_id=root.name)
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.declare_source("raw_nwb", "file:///mnt/Data/ephys/session.nwb")
    writer.reference_array(
        "core.probe0.lfp",
        ExternalArray(
            array_asset_id="lfp0",
            uri="processing/ecephys/LFP/data",
            source="raw_nwb",
            physical_profile="zarr_v2",
        ),
    )
    writer.commit(root)

    document = json.loads((root / "sources.json").read_text())
    assert document["sources_standard_version"] == "escapewheel-sources-v0.1"
    assert document["sources"]["raw_nwb"]["uri"] == "file:///mnt/Data/ephys/session.nwb"

    manifest = json.loads((root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r["resource_id"] == "core.probe0.lfp")
    assert entry["source"] == "raw_nwb"
    assert entry["uri"] == "processing/ecephys/LFP/data"
    # Not a packet resource: nothing in the manifest names it, which is what keeps `04` §5.1's
    # immutability off it and lets a moved mirror be corrected in place.
    assert not any(r.get("uri") == "sources.json" for r in manifest["resources"])


def test_no_source_means_no_document(tmp_path, registry, minimal):
    """A document locating nothing is worse than none: it answers a lookup it should not."""
    root = tmp_path / "s001"
    _write(root, registry, minimal)
    assert not (root / "sources.json").exists()


def test_every_encoding_exception_names_a_column_that_exists(registry):
    """An exception no column answers to is a claim nothing tests.

    `_delta_columns` picks a Parquet encoding from two rules and two lists of exceptions, each
    declared with the measurement that justifies it. `check.py` applies the same discipline to
    `NAMING_EXCEPTIONS` — declared with a reason, and checked to still be needed — and the list
    that went stale unnoticed was `recipe.PREFERRED`'s `core.unit_electrodes`, which arbitrated
    nothing until R108 §3.4 struck it.

    Whether the encoding is the *better* one needs real values, which
    `conformance/parquet-probe/layout.py` measures against a built packet. That the column exists
    and is an integer is decidable here, with no packet in hand.
    """
    tables = dict(registry["tables"])
    named = [resource
             for entries in (DELTA_COLUMNS, NO_DICTIONARY, DICTIONARY_COLUMNS)
             for resource in entries]
    assert [r for r in named if not r.startswith(("core.", "analysis."))] == [], (
        "core names an extension's table; an extension supplies its own to PacketWriter"
    )
    stale = [
        f"{listed}: {resource}.{column}"
        for listed, entries in (("DELTA_COLUMNS", DELTA_COLUMNS),
                                ("NO_DICTIONARY", NO_DICTIONARY),
                                ("DICTIONARY_COLUMNS", DICTIONARY_COLUMNS))
        for resource, columns in entries.items()
        for column in columns
        if resource not in tables
        or not any(c["name"] == column and c["type"] in {"int32", "int64", "float32", "float64"}
                   for c in tables[resource]["columns"])
    ]
    assert stale == []


def test_an_inefficient_encoding_is_reported(tmp_path, registry, minimal):
    """`03` §5.5's rules are good guesses, and a column it guesses wrong about is said aloud.

    Collected and never read is how this mechanism failed first: the notes were appended in two
    places and emitted in none, so the report existed and reached nobody. Both halves are pinned
    here — that `inefficient` finds a column, and that `commit` says what it found.
    """
    said: list[str] = []
    writer = PacketWriter(registry, packet_id="p", session="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    writer._encoding_notes.append("core.pretend.column is plain where dict is 9.9x smaller")
    writer.commit(tmp_path / "packet", say=said.append)
    assert [line for line in said if "9.9x smaller" in line], "a collected note reached nobody"


def test_inefficient_finds_a_column_encoded_worse_than_it_could_be(registry):
    """An ascending integer is what delta exists for, so calling it anything else is reported.

    The check is over what a caller says it chose, not over what a rule would choose, so a writer
    that ignores `03` §5.5 entirely still learns what its choice cost.
    """
    ramp = pa.table({"t_tick": pa.array(range(1_000_000, 1_020_000), type=pa.int64())})
    assert inefficient("core.pretend", ramp, delta=[], plain=["t_tick"]), "delta is far smaller"
    assert inefficient("core.pretend", ramp, delta=["t_tick"], plain=[]) == [], "and delta is said to be right"

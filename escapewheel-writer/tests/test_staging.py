"""Tables are staged from records or from batches, and a stream is checked as it is written."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_writer import PacketWriter
from escapewheel_writer.errors import (
    UndeclaredResource,
    UsageError,
    UsageFault,
)
from escapewheel_writer.staging import parquet_options

# -- the columnar path ---------------------------------------------------------------


def _spike_batch(n, unit, first_tick):
    """One batch of core.spike_events, already in the registry's sort order.

    `unit` is the number the writer assigned (Part 02 §12.1), not the sorter's label: a batch is
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
    # The unit names the clock its ticks are counted on and the unit of measure its
    # amplitudes are in, and a spike reaches both in one hop.
    writer.add(
        "core.units",
        [
            {
                "session_id": "s001",
                "unit_id": 1,
                "sorting_run_id": "sort_1",
                "curation_id": "cur_1",
                "clock_id": "harp_s001",
                "amplitude_unit": "uV",
            }
        ],
    )


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


def test_a_stream_is_consumed_before_any_table_is_built(tmp_path, registry, minimal):
    """A row may record what a stream only knows once it has run, such as how many rows it dropped."""
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    run = dict(_run("run_import"), parameters={"batches": 0})
    writer.add("core.processing_runs", [run])
    unit = writer.keys.of("unit", "1")

    def batches():
        yield _spike_batch(10, unit, 0)
        run["parameters"]["batches"] = 1

    writer.add_batches("core.spike_events", batches())
    writer.commit(tmp_path / "pkt")
    runs = pq.read_table(tmp_path / "pkt" / "tables" / "core" / "processing_runs.parquet")
    assert [json.loads(p) for p in runs.column("parameters").to_pylist()] == [{"batches": 1}]


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
    with pytest.raises(UsageError) as refused:
        writer.add_batches("core.spike_events", [])
    assert refused.value.code is UsageFault.STAGED_TWICE
    assert refused.value.where == "core.spike_events"
    writer2 = PacketWriter(registry, packet_id="s001")
    writer2.add_batches("core.spike_events", [])
    with pytest.raises(UsageError) as refused:
        writer2.add_batches("core.spike_events", [])
    assert refused.value.code is UsageFault.STAGED_TWICE


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
    with pytest.raises(UsageError) as refused:
        writer.commit(tmp_path / "pkt")
    assert refused.value.code is UsageFault.UNDECLARED_COLUMN
    assert refused.value.where == "core.spike_events"


def test_an_unknown_resource_is_refused_on_the_batch_path_too(registry):
    writer = PacketWriter(registry, packet_id="s001")
    with pytest.raises(UndeclaredResource) as refused:
        writer.add_batches("core.not_a_table", [])
    assert refused.value.resource_id == "core.not_a_table"


def test_one_batch_becomes_exactly_one_row_group(tmp_path, registry):
    """The streaming path's boundary guarantee, which Part 03 §5.4 and S3 sizing both rest on.

    pyarrow's own default is 2**20 rows per row group, so a larger batch is silently cut into
    several. That would put `analysis.spike_events` row groups across time-bucket boundaries and
    would quietly cap any row-group size a caller chose for the store the packet will live on.
    """
    import pyarrow as pa

    from escapewheel_writer.staging import write_stream

    rows = (1 << 20) + 200_000  # deliberately over pyarrow's default cut
    spec = registry["resources"]["core.spike_events"]["table"]
    batch = pa.record_batch(
        {
            # int32 (Part 02 §5.3). `write_stream` is below `add_batches`, which is where a
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
    write_stream(spec, [batch, tail], path, "core.spike_events")

    metadata = pq.ParquetFile(path).metadata
    assert metadata.num_row_groups == 2, "a batch was split into several row groups"
    assert [metadata.row_group(i).num_rows for i in range(2)] == [rows, 1000]


def test_an_out_of_order_stream_is_refused_while_staging(tmp_path, registry, minimal):
    """The order is established on the way in, so a bad stream fails before anything is written.

    Previously this reached the file and surfaced as a physical_order warning after 467 MB of
    re-reading; now it stops at the batch that breaks it.
    """
    from escapewheel_validator import OrderFault, OrderViolation

    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    writer.add_batches("core.spike_events", iter([_spike_batch(10, 1, 10), _spike_batch(10, 1, 0)]))
    with pytest.raises(OrderViolation) as refused:
        writer.commit(tmp_path / "pkt")
    assert (refused.value.kind, refused.value.resource_id) == (OrderFault.DESCENT, "core.spike_events")
    assert refused.value.row == 10


def test_a_record_carrying_an_undeclared_column_is_refused(registry):
    """Both entry points refuse it, which is the whole point.

    `add_batches` always has; `add` documented the key as ignored, so one adapter defect was a
    build failure through one door and a dropped column through the other. Three test fixtures
    were carrying `name` where the registry declares `array_asset_name` and `clock_name`, and
    nothing said so.
    """
    writer = PacketWriter(registry, packet_id="s001")
    with pytest.raises(UsageError) as refused:
        writer.add("core.clocks", [{"clock_id": "c", "session_id": "s001", "name": "master"}])
    assert refused.value.code is UsageFault.UNDECLARED_COLUMN
    assert refused.value.where == "core.clocks"


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
        {**{n: batch.column(n) for n in batch.schema.names}, "nonsense": pa.array([1, 2, 3, 4], type=pa.int64())}
    )
    writer.add_batches("core.spike_events", iter([stray]))
    with pytest.raises(UsageError) as refused:
        writer.commit(tmp_path / "pkt")
    assert refused.value.code is UsageFault.UNDECLARED_COLUMN
    assert "nonsense" in str(refused.value)


def test_an_optional_column_absent_from_the_first_batch_says_so(tmp_path, registry, minimal):
    """The other cause: `schema` omits an optional column no first batch carries (Part 02 §6).

    Nothing is undeclared here, so the fix is to the stream rather than to a registry, which is
    why the two read differently.
    """
    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    rows = {"session_id": pa.array(["s001"]), "stream_id": pa.array(["s"]), "t_tick": pa.array([1], type=pa.int64())}
    writer.add_batches(
        "core.events",
        iter(
            [
                pa.record_batch(rows),
                pa.record_batch({**rows, "t_tick": pa.array([2], type=pa.int64()), "metadata": pa.array(['{"a": 1}'])}),
            ]
        ),
    )
    with pytest.raises(UsageError) as refused:
        writer.commit(tmp_path / "pkt")
    assert refused.value.code is UsageFault.COLUMN_AFTER_FIRST_BATCH
    assert "metadata" in str(refused.value)


def test_a_duplicate_across_batches_is_refused_while_staging(tmp_path, registry, minimal):
    from escapewheel_validator import OrderFault, OrderViolation

    writer = PacketWriter(registry, packet_id="s001")
    for resource, rows in minimal.items():
        writer.add(resource, rows)
    _add_spike_context(writer)
    writer.add_batches("core.spike_events", iter([_spike_batch(10, 1, 0), _spike_batch(1, 1, 9)]))
    with pytest.raises(OrderViolation) as refused:
        writer.commit(tmp_path / "pkt")
    assert (refused.value.kind, refused.value.resource_id) == (OrderFault.REPEAT, "core.spike_events")
    assert refused.value.row == 10


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
        # Part 06 §5: a materialization records the run that produced it.
        target.add(
            "core.processing_runs",
            [
                dict(
                    _run("run_derived", "materialization"), software_name="escapewheel_writer", software_version="0.0.0"
                )
            ],
        )

    writer.commit(root, materialize=[derive])

    runs = pq.read_table(root / "tables" / "core" / "processing_runs.parquet")
    # The key is a number and the name is what it stands for. Both runs are present, and
    # the materializer's run is numbered by the same Keys the staged rows used.
    assert sorted(runs.column("processing_run_name").to_pylist()) == ["run_derived", "run_import"]
    assert sorted(runs.column("processing_run_id").to_pylist()) == [0, 1]
    entries = [e for e in json.loads((root / "packet.json").read_text())["resources"]]
    assert [e["resource_id"] for e in entries].count("core.processing_runs") == 1, "duplicated entry"


def _run(run_id, activity="import"):
    """One `core.processing_runs` row.

    The activity is a parameter because two runs of one activity declare their
    scopes (Part 01 §2.6), and a derived run is a materialization rather than a second import (Part 06 §5).
    """
    return {
        "processing_run_id": run_id,
        "session_id": "s001",
        "activity_type": activity,
        "status": "succeeded",
    }


@pytest.mark.parametrize("held", ["strings", "codes"])
def test_a_string_chosen_plain_is_written_without_a_dictionary(tmp_path, registry, held):
    """A string may reach the writer as dictionary codes, and is still a string column in Parquet.

    Judged by its Arrow type alone it would be skipped, so the same column built from records and
    streamed as codes would be written two ways.
    """
    names = pa.array(["probe.CH0", "probe.CH1", "probe.CH10"])
    table = pa.table({"electrode_name": names if held == "strings" else names.dictionary_encode()})
    path = tmp_path / "electrodes.parquet"
    spec = registry["resources"]["core.electrodes"]["table"]
    pq.write_table(table, path, **parquet_options("core.electrodes", spec, table.schema, sample=table))
    encodings = {str(e) for e in pq.ParquetFile(path).metadata.row_group(0).column(0).encodings}
    assert not any("DICTIONARY" in e for e in encodings), encodings
    assert pq.read_table(path).column(0).to_pylist() == names.to_pylist()


def _stream_units(tmp_path, registry, extra=None, report=None, **columns):
    """Stream one batch of `core.units` through the writer and return each column's encodings."""
    from escapewheel_writer.staging import write_stream

    rows = 1_000
    batch = pa.record_batch(
        {
            "session_id": pa.array([0] * rows, type=pa.int32()),
            "unit_id": pa.array(range(rows), type=pa.int32()),
            **columns,
        }
    )
    path = tmp_path / "units.parquet"
    write_stream(registry["resources"]["core.units"]["table"], iter([batch]), path, "core.units", extra, report)
    metadata = pq.ParquetFile(path).metadata
    return {
        metadata.schema.column(i).name: {str(e) for e in metadata.row_group(0).column(i).encodings}
        for i in range(metadata.num_columns)
    }


def test_a_column_a_stream_omits_is_encoded_as_the_nulls_it_is_written_as(tmp_path, registry):
    """A nullable column absent from a delivery is written as nulls, and holds no value to index."""
    encodings = _stream_units(tmp_path, registry)
    assert not any("DICTIONARY" in e for e in encodings["firing_rate_hz"]), encodings["firing_rate_hz"]


def test_a_recipe_exception_reaches_a_streamed_table(tmp_path, registry):
    """The streaming loop once bound its unexpected columns to the name the exceptions arrive under."""
    extra = {"dictionary": {"core.units": ("firing_rate_hz",)}}
    encodings = _stream_units(tmp_path, registry, extra)
    assert any("DICTIONARY" in e for e in encodings["firing_rate_hz"]), encodings["firing_rate_hz"]


def test_a_streamed_column_is_reported_at_the_type_it_is_written_as(tmp_path, registry):
    """A source's `int64` cast to the registry's `int32` is measured as written, not as delivered."""
    report: list[str] = []
    sizes = pa.array([[2, 4, 8][i % 3] for i in range(1_000)], type=pa.int64())
    _stream_units(tmp_path, registry, {"plain": {"core.units": ("probe_id",)}}, report, probe_id=sizes)
    assert not [line for line in report if ".probe_id " in line], report

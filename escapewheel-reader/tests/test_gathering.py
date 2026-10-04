"""A table's runs as list columns, in each form a table comes in.

`core.spike_events` is stored by `(session_id, unit_id, t_tick)`, so its key is
`(session_id, unit_id)`; `analysis.spike_events` puts `clock_id` and `time_bucket_tick` first.
"""

import pyarrow as pa
import pytest

from escapewheel_reader import NotDeclared, Unordered, open_packet, ragged

SPIKES = pa.table(
    {
        "session_id": pa.array([1, 1, 1, 1, 1, 1], pa.int32()),
        "unit_id": pa.array([3, 3, 3, 5, 7, 7], pa.int32()),
        "t_tick": pa.array([10, 20, 30, 15, 5, 25], pa.int64()),
        "amplitude": pa.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
    }
)
EXPECTED = {
    "session_id": [1, 1, 1],
    "unit_id": [3, 5, 7],
    "t_tick": [[10, 20, 30], [15], [5, 25]],
    "amplitude": [[1.0, 2.0, 3.0], [4.0], [5.0, 6.0]],
}


@pytest.fixture
def packet(packet_root):
    return open_packet(packet_root)


def test_each_unit_becomes_one_row_with_its_values_as_lists(packet):
    out = ragged(packet, SPIKES, "core.spike_events")
    assert out.to_pydict() == EXPECTED
    assert out.schema.field("t_tick").type == pa.large_list(pa.int64())


@pytest.mark.parametrize("rows", [1, 2, 4])
def test_a_run_cut_by_a_chunk_is_joined_back(packet, rows):
    chunked = pa.Table.from_batches(SPIKES.to_batches(max_chunksize=rows))
    assert ragged(packet, chunked, "core.spike_events").to_pydict() == EXPECTED


@pytest.mark.parametrize("rows", [1, 2, 4])
def test_a_stream_is_gathered_batch_by_batch(packet, rows):
    reader = pa.RecordBatchReader.from_batches(SPIKES.schema, SPIKES.to_batches(max_chunksize=rows))
    out = ragged(packet, reader, "core.spike_events")
    assert isinstance(out, pa.RecordBatchReader)
    assert out.read_all().to_pydict() == EXPECTED


def test_a_record_batch_comes_back_as_one(packet):
    out = ragged(packet, SPIKES.to_batches()[0], "core.spike_events")
    assert isinstance(out, pa.RecordBatch)
    assert out.to_pydict() == EXPECTED


def test_no_rows_keep_the_gathered_schema(packet):
    out = ragged(packet, SPIKES.slice(0, 0), "core.spike_events")
    assert out.num_rows == 0
    assert out.schema.field("amplitude").type == pa.large_list(pa.float64())


def test_a_dictionary_key_gathers_across_chunks_with_different_dictionaries(packet):
    units = SPIKES.column("unit_id").combine_chunks()
    encoded = pa.chunked_array([units.slice(0, 2).dictionary_encode(), units.slice(2).dictionary_encode()])
    table = SPIKES.set_column(1, "unit_id", encoded)
    out = ragged(packet, table, "core.spike_events")
    assert out.column("unit_id").to_pylist() == [3, 5, 7]
    assert out.column("t_tick").to_pylist() == EXPECTED["t_tick"]


def test_a_key_column_left_out_gathers_by_the_rest(packet):
    out = ragged(packet, SPIKES.drop_columns("session_id"), "core.spike_events")
    assert out.column("unit_id").to_pylist() == [3, 5, 7]


@pytest.mark.parametrize("rows", [1, 6])
def test_a_key_that_returns_after_another_is_refused(packet, rows):
    shuffled = SPIKES.take([0, 3, 1, 2, 4, 5])
    with pytest.raises(Unordered):
        ragged(packet, pa.Table.from_batches(shuffled.to_batches(max_chunksize=rows)), "core.spike_events")


def test_descending_keys_are_refused(packet):
    with pytest.raises(Unordered):
        ragged(packet, SPIKES.take([4, 5, 3, 0, 1, 2]), "core.spike_events")


def test_a_key_column_left_out_is_refused_where_the_rest_repeat(packet):
    """Two sessions each have a unit 3, so unit 3 returns once `session_id` is dropped."""
    two_sessions = pa.table(
        {
            "session_id": pa.array([1, 1, 2], pa.int32()),
            "unit_id": pa.array([3, 5, 3], pa.int32()),
            "t_tick": pa.array([10, 20, 30], pa.int64()),
        }
    )
    assert ragged(packet, two_sessions, "core.spike_events").column("t_tick").to_pylist() == [[10], [20], [30]]
    with pytest.raises(Unordered):
        ragged(packet, two_sessions.drop_columns("session_id"), "core.spike_events")


def test_a_resource_with_no_order_is_not_declared(packet):
    with pytest.raises(NotDeclared):
        ragged(packet.with_declarations(_unordered(packet)), SPIKES, "core.spike_events")


def _unordered(packet):
    """A registry declaring `core.spike_events` with its primary key withdrawn."""
    resource = packet.resource("core.spike_events")
    declaration = dict(resource.declaration)
    declaration["table"] = {**declaration["table"], "primary_key": None}
    return {"resources": {resource.declaration_id: declaration}}


def test_a_packet_scanner_gathers_as_its_table_does(packet):
    columns = ["session_id", "unit_id", "t_tick"]
    eager = ragged(packet, packet.table("core.spike_events", columns=columns), "core.spike_events")
    streamed = ragged(packet, packet.scanner("core.spike_events", columns=columns), "core.spike_events")
    assert streamed.read_all().to_pydict() == eager.to_pydict()
    assert eager.num_rows == len(set(packet.table("core.spike_events", columns=["unit_id"])["unit_id"].to_pylist()))

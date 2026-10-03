"""The clock transforms over every Arrow form a read can take."""

import pyarrow as pa
import pyarrow.dataset as pads
import pytest
from packet_fixture import CLOCK_BEHAVIOUR

from escapewheel_reader import attach_clocks, clocks, on_clock, open_packet, seconds
from escapewheel_reader.clocks import seconds_expression

SPIKES = "core.spike_events"


def _forms(packet, resource_id):
    """The same rows as each form a transform accepts, with what it should come back as."""
    table = packet.table(resource_id)
    return [
        (table, pa.Table),
        (table.combine_chunks().to_batches()[0], pa.RecordBatch),
        (pa.RecordBatchReader.from_batches(table.schema, table.to_batches(max_chunksize=1)), pa.RecordBatchReader),
        (packet.scanner(resource_id), pa.RecordBatchReader),
        (packet.scan(resource_id), pa.RecordBatchReader),
    ]


def _table(out):
    if isinstance(out, pa.RecordBatchReader):
        return out.read_all()
    return pa.Table.from_batches([out]) if isinstance(out, pa.RecordBatch) else out


@pytest.fixture
def packet(two_clock_packet):
    return open_packet(two_clock_packet)


TRANSFORMS = {
    "attach_clocks": lambda packet, data: attach_clocks(packet, data, SPIKES),
    "on_clock": lambda packet, data: on_clock(packet, data, resource_id=SPIKES),
    "seconds": lambda packet, data: seconds(packet, on_clock(packet, data, resource_id=SPIKES)),
}


@pytest.mark.parametrize("name", TRANSFORMS)
def test_every_form_gives_the_rows_a_table_gives(packet, name):
    transform = TRANSFORMS[name]
    expected = transform(packet, packet.table(SPIKES))
    for data, kind in _forms(packet, SPIKES):
        out = transform(packet, data)
        assert isinstance(out, kind)
        assert _table(out).equals(expected), type(data)


def test_an_empty_stream_keeps_the_schema_a_table_would_have(packet):
    expected = on_clock(packet, packet.table(SPIKES), resource_id=SPIKES)
    empty = packet.scanner(SPIKES, unit_id=-1)
    assert on_clock(packet, empty, resource_id=SPIKES).read_all().schema == expected.schema


def test_a_stream_reads_the_table_its_clock_is_in_once(packet, monkeypatch):
    reads = []
    original = type(packet).table

    def counted(self, resource_id, **kwargs):
        reads.append(resource_id)
        return original(self, resource_id, **kwargs)

    monkeypatch.setattr(type(packet), "table", counted)
    reader = pa.RecordBatchReader.from_batches(
        packet.scan(SPIKES).schema, packet.scan(SPIKES).to_table().to_batches(max_chunksize=1)
    )
    on_clock(packet, reader, resource_id=SPIKES).read_all()
    assert reads.count("core.units") == 1


def test_seconds_projected_in_a_scan_equal_seconds_after_it(packet):
    events = on_clock(packet, packet.table("core.events"), resource_id="core.events")
    expected = seconds(packet, events).column("t_second")
    projected = pads.dataset(events).to_table(columns={"t_second": seconds_expression(packet)})
    assert events.column("clock_id").to_pylist() == [CLOCK_BEHAVIOUR]
    assert projected.column("t_second").equals(expected)


def test_a_stream_builds_each_clock_map_once(packet, monkeypatch):
    """A stream maps batch by batch; rebuilding every clock's map per batch cost more than mapping."""
    built = []
    original = clocks._Map.__init__

    def counted(self, *args, **kwargs):
        built.append(1)
        original(self, *args, **kwargs)

    monkeypatch.setattr(clocks._Map, "__init__", counted)
    table = packet.table(SPIKES)
    for _ in range(2):
        batches = pa.RecordBatchReader.from_batches(table.schema, table.to_batches(max_chunksize=1))
        on_clock(packet, batches, resource_id=SPIKES).read_all()
    assert 0 < len(built) <= len(clocks.clock_graph(packet).anchors)

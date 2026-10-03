"""Column constraints as Arrow expressions."""

import pyarrow as pa
import pyarrow.dataset as pads

from escapewheel_reader import open_packet, where

ROWS = pa.table({"stream_id": pa.array([1, 2, 3, 1]), "t_tick": pa.array([10, 20, 30, 40])})


def test_where_reads_as_the_table_keywords_do():
    found = pads.dataset(ROWS).to_table(filter=where(stream_id={1, 3}, t_tick=(15, 40), absent=None))
    assert found.column("t_tick").to_pylist() == [30, 40]


def test_where_with_nothing_keeps_every_row():
    assert pads.dataset(ROWS).to_table(filter=where()).num_rows == ROWS.num_rows


def test_a_scanner_ands_its_filter_with_its_constraints(packet_root):
    packet = open_packet(packet_root)
    events = packet.table("core.events")
    stream = events.column("stream_id")[0].as_py()
    first = events.column("t_tick")[0].as_py()
    found = packet.scanner("core.events", filter=where(t_tick=(first, first)), stream_id=stream).to_table()
    assert found.num_rows >= 1
    assert set(found.column("t_tick").to_pylist()) == {first}
    assert set(found.column("stream_id").to_pylist()) == {stream}

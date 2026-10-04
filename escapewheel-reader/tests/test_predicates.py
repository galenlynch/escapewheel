"""Column constraints as Arrow expressions."""

import pyarrow as pa
import pyarrow.dataset as pads
import pyarrow.parquet as pq

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


def test_a_long_membership_still_prunes_row_groups(tmp_path):
    """PyArrow tests a long `is_in` against no row group's statistics, so `where` guards it with ranges."""
    path = tmp_path / "units.parquet"
    pq.write_table(pa.table({"unit_id": pa.array(range(10_000), pa.int32())}), path, row_group_size=100)
    wanted = list(range(5_000, 5_200, 2)) + [9_999]
    fragment = next(pads.dataset(path).get_fragments())
    assert len(fragment.split_by_row_group(where(unit_id=wanted))) == 3
    assert pads.dataset(path).to_table(filter=where(unit_id=set(wanted)))["unit_id"].to_pylist() == wanted

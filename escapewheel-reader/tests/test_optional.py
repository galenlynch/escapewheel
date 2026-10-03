"""Reading a table the packet need not hold."""

from escapewheel_reader import open_packet
from escapewheel_reader.optional import held, read_optional


def test_an_absent_table_reads_as_no_rows_with_every_column(packet_root):
    packet = open_packet(packet_root)
    assert "core.preferred_runs" not in held(packet)
    table = read_optional(packet, "core.preferred_runs", ["session_id", "scope"])
    assert table.column_names == ["session_id", "scope"]
    assert table.num_rows == 0


def test_an_absent_column_reads_as_nulls_beside_the_present_ones(packet_root):
    packet = open_packet(packet_root)
    units = packet.table("core.units", columns=["unit_id"])
    table = read_optional(packet, "core.units", ["unit_id", "not_a_column"])
    assert table.column("unit_id").equals(units.column("unit_id"))
    assert table.column("not_a_column").null_count == units.num_rows

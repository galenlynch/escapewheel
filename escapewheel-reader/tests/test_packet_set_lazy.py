"""A packet set read lazily: one dataset over every packet, and the transforms dispatched by packet."""

import json
import shutil

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest
from packet_fixture import CLOCK_BEHAVIOUR, CLOCK_PROBE, SESSION, SESSION_NAME, UNITS

from escapewheel_reader import (
    Refused,
    attach_clocks,
    on_clock,
    open_packets,
    seconds,
    tick_bounds,
    tick_range,
    where,
)

SPIKES = "core.spike_events"
SECOND_NAME = "s002"
SPAN = (1_031_250, 1_100_000)


def _renamed(root, tmp_path, name):
    """A copy of `root` whose one session is `name`, reusing every identifier."""
    copy = tmp_path / name
    shutil.copytree(root, copy)
    sessions = pq.read_table(copy / "tables/core/sessions.parquet")
    index = sessions.schema.get_field_index("session_name")
    pq.write_table(sessions.set_column(index, "session_name", pa.array([name])), copy / "tables/core/sessions.parquet")
    manifest = json.loads((copy / "packet.json").read_text())
    manifest["packet_id"] = name
    manifest["sessions"] = [name]
    (copy / "packet.json").write_text(json.dumps(manifest, indent=2))
    return copy


@pytest.fixture
def pair(dense_root, tmp_path):
    return open_packets([dense_root, _renamed(dense_root, tmp_path, SECOND_NAME)])


def _per_packet(pair, read, *, identity=True):
    """Each packet's rows by `read`, stamped with its packet and session as the packet set numbers them."""
    parts = []
    for session in pair.sessions:
        part = read(pair.packets[session.packet_key])
        part = part.append_column("packet_key", pa.array([session.packet_key] * part.num_rows, pa.int32()))
        if identity:
            part = part.append_column("session_key", pa.array([session.session_key] * part.num_rows, pa.int32()))
            part = part.append_column("session_name", pa.array([session.session_name] * part.num_rows, pa.string()))
        parts.append(part)
    return pa.concat_tables(parts)


def _sorted(table, *columns):
    return table.sort_by([(name, "ascending") for name in columns or table.column_names])


def test_a_scan_holds_every_packets_rows_under_its_packet(pair):
    stored = _per_packet(pair, lambda packet: packet.table(SPIKES), identity=False)
    assert _sorted(pair.scan(SPIKES).to_table()).equals(_sorted(stored))
    expected = _per_packet(pair, lambda packet: packet.table(SPIKES))
    assert pair.table(SPIKES).equals(expected)
    assert _sorted(pair.scanner(SPIKES).to_table()).equals(_sorted(expected))


def test_a_filter_on_the_packet_skips_the_other_packets_files(pair):
    dataset = pair.scan(SPIKES)
    second = pc.field("packet_key") == pa.scalar(1, pa.int32())
    opened = sum(len(list(child.get_fragments(filter=second))) for child in dataset.children)
    assert opened == len(list(dataset.children[1].get_fragments()))
    named = pair.scanner(SPIKES, session_name=SECOND_NAME).to_table()
    assert set(named.column("packet_key").to_pylist()) == {1}


def test_the_session_table_joins_the_session_onto_a_scan(pair):
    sessions = pair.session_table()
    assert sessions.column_names == ["packet_key", "session_id", "session_key", "session_name"]
    assert sessions.column("session_name").to_pylist() == [SESSION_NAME, SECOND_NAME]
    joined = pair.scan(SPIKES).to_table().join(sessions, ["packet_key", "session_id"])
    assert _sorted(joined.select(pair.table(SPIKES).column_names)).equals(_sorted(pair.table(SPIKES)))


def test_the_scanner_takes_the_tables_constraints(pair):
    found = pair.scanner(SPIKES, columns=["unit_id", "t_tick", "session_key"], unit_id=UNITS[0], session_key=1)
    expected = pair.table(SPIKES, columns=["unit_id", "t_tick", "session_key"], unit_id=UNITS[0], session_key=1)
    assert found.to_table().equals(expected)
    assert set(expected.column("session_key").to_pylist()) == {1}


def test_the_table_maps_and_times_each_packet_as_the_packet_does(pair):
    def read(packet):
        return packet.table(SPIKES, on_clock=True, seconds=True, t_tick=SPAN)

    assert pair.table(SPIKES, on_clock=True, seconds=True, t_tick=SPAN).equals(_per_packet(pair, read))


@pytest.mark.parametrize("on_clock", [False, True])
def test_the_table_returns_exactly_the_columns_named(pair, on_clock):
    """An identity column costs a value per row, so it comes back only when named."""
    alone = pair.packets[0].table(SPIKES, columns=["unit_id", "t_tick"], on_clock=on_clock).column_names
    bare = pair.table(SPIKES, columns=["unit_id", "t_tick"], on_clock=on_clock)
    assert bare.column_names == alone
    keyed = pair.table(SPIKES, columns=["unit_id", "t_tick", "session_name"], on_clock=on_clock)
    assert keyed.column_names == [*alone, "session_name"]
    assert keyed.column("t_tick").equals(bare.column("t_tick"))


def test_a_range_over_the_set_selects_what_each_packets_range_does(pair):
    found = pair.scan(SPIKES).to_table(filter=tick_range(pair, SPIKES, SPAN))
    expected = _per_packet(
        pair, lambda packet: packet.scan(SPIKES).to_table(filter=tick_range(packet, SPIKES, SPAN)), identity=False
    )
    assert _sorted(found).equals(_sorted(expected))
    bounds = tick_bounds(pair, SPIKES, SPAN)
    assert bounds.column_names == ["packet_key", "clock_id", "lo", "hi"]
    one = tick_bounds(pair.packets[0], SPIKES, SPAN)
    assert bounds.filter(where(packet_key=1)).drop_columns("packet_key").equals(one)


@pytest.mark.parametrize("form", ["table", "stream"])
def test_transforms_dispatch_rows_to_the_packet_their_packet_key_names(pair, form):
    stored = pair.table(SPIKES)
    data = stored if form == "table" else pair.scanner(SPIKES)
    mapped = on_clock(pair, data, resource_id=SPIKES)
    timed = seconds(pair, mapped, resource_id=SPIKES)
    if form == "stream":
        timed = timed.read_all()
    expected = _per_packet(
        pair,
        lambda packet: seconds(packet, on_clock(packet, packet.table(SPIKES), resource_id=SPIKES), resource_id=SPIKES),
    )
    columns = ["packet_key", "unit_id", "t_tick"]
    assert _sorted(timed, *columns).equals(_sorted(expected.select(timed.column_names), *columns))
    attached = attach_clocks(pair, stored, SPIKES)
    assert attached.num_rows == stored.num_rows


def test_rows_without_a_packet_cannot_be_dispatched(pair):
    with pytest.raises(ValueError, match="packet_key"):
        on_clock(pair, pair.packets[0].table(SPIKES), resource_id=SPIKES)


@pytest.fixture
def two_sessions(dense_root, tmp_path):
    """One packet holding two sessions, its units all in the first."""
    root = tmp_path / "two_sessions"
    shutil.copytree(dense_root, root)
    sessions = pq.read_table(root / "tables/core/sessions.parquet")
    pq.write_table(
        pa.concat_tables(
            [
                sessions,
                sessions.set_column(0, "session_id", pa.array([SESSION + 1], pa.int32())).set_column(
                    sessions.schema.get_field_index("session_name"), "session_name", pa.array([SECOND_NAME])
                ),
            ]
        ),
        root / "tables/core/sessions.parquet",
    )
    manifest = json.loads((root / "packet.json").read_text())
    manifest["sessions"] = [SESSION_NAME, SECOND_NAME]
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packets([root])


def test_a_packet_of_several_sessions_is_scanned_through_its_session_ids(two_sessions):
    count = two_sessions.packets[0].table("core.units").num_rows
    assert two_sessions.scan("core.units").count_rows() == count
    assert two_sessions.scanner("core.units").to_table().equals(two_sessions.table("core.units"))
    assert set(two_sessions.table("core.units").column("session_key").to_pylist()) == {0}
    assert two_sessions.scanner("core.units", session_key=0).to_table().num_rows == count
    assert two_sessions.scanner("core.units", session_name=SECOND_NAME).to_table().num_rows == 0
    assert two_sessions.table("core.units", session_key=1).num_rows == 0
    timed = seconds(two_sessions, two_sessions.table(SPIKES, on_clock=True), resource_id=SPIKES)
    alone = seconds(two_sessions.packets[0], two_sessions.packets[0].table(SPIKES, on_clock=True), resource_id=SPIKES)
    assert timed.column("t_second").equals(alone.column("t_second"))


def test_a_clock_named_across_packets_must_be_the_reference(pair):
    """A clock ID is assigned within its packet, so only the reference names one clock in all of them."""
    stored = pair.table(SPIKES)
    assert on_clock(pair, stored, CLOCK_BEHAVIOUR, resource_id=SPIKES).equals(
        on_clock(pair, stored, resource_id=SPIKES)
    )
    with pytest.raises(Refused, match="different clock in each packet"):
        on_clock(pair, stored, CLOCK_PROBE, resource_id=SPIKES)
    with pytest.raises(Refused, match="different clock in each packet"):
        tick_range(pair, SPIKES, SPAN, clock=CLOCK_PROBE)
    with pytest.raises(Refused, match="different clock in each packet"):
        tick_bounds(pair, SPIKES, SPAN, clock=CLOCK_PROBE)
    with pytest.raises(Refused, match="different clock in each packet"):
        pair.table(SPIKES, on_clock=CLOCK_PROBE)
    assert pair.table(SPIKES, on_clock=CLOCK_BEHAVIOUR).equals(pair.table(SPIKES, on_clock=True))


def test_seconds_over_a_packet_set_takes_the_session_from_each_row(pair):
    mapped = on_clock(pair, pair.table(SPIKES), resource_id=SPIKES)
    with pytest.raises(ValueError, match="packet_key and session_id"):
        seconds(pair, mapped, resource_id=SPIKES, session_id=SESSION)

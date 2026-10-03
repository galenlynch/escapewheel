"""A packet set read lazily: one dataset over every packet, and the transforms dispatched by session."""

import json
import shutil

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest
from packet_fixture import SESSION, SESSION_NAME, UNITS

from escapewheel_reader import (
    MultiSessionUnresolved,
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


def _per_packet(pair, read):
    """Each packet's rows by `read`, stamped with its session as the packet set numbers it."""
    parts = []
    for session in pair.sessions:
        packet = next(p for p in pair.packets if p.manifest.packet_id == session.packet_id)
        part = read(packet)
        part = part.append_column("session_key", pa.array([session.session_key] * part.num_rows, pa.int32()))
        parts.append(part.append_column("session_name", pa.array([session.session_name] * part.num_rows, pa.string())))
    return pa.concat_tables(parts)


def _sorted(table, *columns):
    return table.sort_by([(name, "ascending") for name in columns or table.column_names])


def test_a_scan_holds_every_packets_rows_under_its_session(pair):
    expected = _per_packet(pair, lambda packet: packet.table(SPIKES))
    assert _sorted(pair.scan(SPIKES).to_table()).equals(_sorted(expected))
    assert pair.table(SPIKES).equals(expected)


def test_a_filter_on_the_session_skips_the_other_packets_files(pair):
    dataset = pair.scan(SPIKES)
    second = pc.field("session_key") == pa.scalar(1, pa.int32())
    opened = sum(len(list(child.get_fragments(filter=second))) for child in dataset.children)
    assert opened == len(list(dataset.children[1].get_fragments()))
    assert set(dataset.to_table(filter=second).column("session_name").to_pylist()) == {SECOND_NAME}


def test_the_scanner_takes_the_tables_constraints(pair):
    found = pair.scanner(SPIKES, columns=["unit_id", "t_tick", "session_key"], unit_id=UNITS[0], session_key=1)
    expected = pair.table(SPIKES, columns=["unit_id", "t_tick"], unit_id=UNITS[0], session_key=1)
    assert found.to_table().equals(expected.select(["unit_id", "t_tick", "session_key"]))
    assert set(expected.column("session_key").to_pylist()) == {1}


def test_the_table_maps_and_times_each_packet_as_the_packet_does(pair):
    def read(packet):
        return packet.table(SPIKES, on_clock=True, seconds=True, t_tick=SPAN)

    assert pair.table(SPIKES, on_clock=True, seconds=True, t_tick=SPAN).equals(_per_packet(pair, read))


def test_a_range_over_the_set_selects_what_each_packets_range_does(pair):
    found = pair.scan(SPIKES).to_table(filter=tick_range(pair, SPIKES, SPAN))
    expected = _per_packet(pair, lambda packet: packet.scan(SPIKES).to_table(filter=tick_range(packet, SPIKES, SPAN)))
    assert _sorted(found).equals(_sorted(expected))
    bounds = tick_bounds(pair, SPIKES, SPAN)
    assert bounds.column_names == ["session_key", "clock_id", "lo", "hi"]
    one = tick_bounds(pair.packets[0], SPIKES, SPAN)
    assert bounds.filter(where(session_key=1)).drop_columns("session_key").equals(one)


@pytest.mark.parametrize("form", ["table", "stream"])
def test_transforms_dispatch_rows_to_the_packet_their_session_names(pair, form):
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
    columns = ["session_key", "unit_id", "t_tick"]
    assert _sorted(timed, *columns).equals(_sorted(expected.select(timed.column_names), *columns))
    attached = attach_clocks(pair, stored, SPIKES)
    assert attached.num_rows == stored.num_rows


def test_rows_without_a_session_cannot_be_dispatched(pair):
    with pytest.raises(ValueError, match="session_key"):
        on_clock(pair, pair.packets[0].table(SPIKES), resource_id=SPIKES)


@pytest.fixture
def two_sessions(packet_root, tmp_path):
    """One packet holding two sessions, its units all in the first."""
    root = tmp_path / "two_sessions"
    shutil.copytree(packet_root, root)
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
    with pytest.raises(MultiSessionUnresolved, match="scanner"):
        two_sessions.scan("core.units")
    assert two_sessions.scanner("core.units").to_table().equals(two_sessions.table("core.units"))
    assert two_sessions.scanner("core.units", session_key=0).to_table().num_rows == 2
    assert two_sessions.scanner("core.units", session_name=SECOND_NAME).to_table().num_rows == 0
    assert two_sessions.table("core.units", session_key=1).num_rows == 0

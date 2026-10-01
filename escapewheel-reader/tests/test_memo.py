"""What the free functions keep in a packet's memo, and when."""

import pyarrow as pa
import pytest

from escapewheel_reader import open_packet, spike_times
from escapewheel_reader.clocks import anchors, declared_bound, origin, reference_clock
from escapewheel_reader.protocols import Memo
from escapewheel_reader.runs import ambiguities

SESSION = 1


class _Counting:
    """A stand-in over one sessions table that counts its reads and keeps a memo if given one."""

    def __init__(self, memo=None):
        self.reads = 0
        if memo is not None:
            self.memo = memo

    def table(self, resource_id, columns=None):
        del resource_id
        self.reads += 1
        table = pa.table({"alignment_bound": pa.array([2.0], pa.float64())})
        return table.select(columns) if columns else table


def _unreadable(packet):
    """Make every later table read fail, so an answer can only come from the memo."""

    def refuse(resource_id, **_):
        raise AssertionError(f"read {resource_id} again")

    packet.table = refuse


def test_a_packet_starts_with_nothing_kept(packet_root):
    assert open_packet(packet_root).memo == Memo()


def test_each_function_keeps_its_answer_in_the_memo(two_clock_packet):
    packet = open_packet(two_clock_packet)
    kept = {
        "anchors": anchors(packet),
        "reference_clock": reference_clock(packet),
        "ambiguities": ambiguities(packet),
    }
    whole = origin(packet)
    for name, answer in kept.items():
        assert getattr(packet.memo, name) is answer, name
    assert packet.memo.origins == {None: whole}

    _unreadable(packet)
    assert anchors(packet) is kept["anchors"]
    assert reference_clock(packet) == kept["reference_clock"]
    assert ambiguities(packet) is kept["ambiguities"]
    assert origin(packet) == whole


def test_an_empty_answer_is_kept(packet_root):
    """A packet with no anchors and no ambiguity is not read again to learn that twice."""
    packet = open_packet(packet_root)
    assert anchors(packet) == {}
    assert ambiguities(packet) == ()
    _unreadable(packet)
    assert anchors(packet) == {}
    assert ambiguities(packet) == ()


def test_an_origin_is_kept_per_session_asked_for(two_clock_packet):
    packet = open_packet(two_clock_packet)
    assert origin(packet, SESSION) == origin(packet)
    assert set(packet.memo.origins) == {SESSION, None}


def test_a_named_session_does_not_set_the_packet_reference_clock(two_clock_packet):
    """The kept clock answers for the packet, which one session's declaration does not."""
    packet = open_packet(two_clock_packet)
    reference_clock(packet, session_id=SESSION)
    assert packet.memo.reference_clock is None


def test_spike_times_resolves_unit_windows_once(two_clock_packet):
    packet = open_packet(two_clock_packet)
    assert packet.memo.unit_windows is None
    unit_ids = packet.table("core.units", columns=["unit_id"]).column("unit_id").to_pylist()
    spike_times(packet, unit_id=unit_ids[0])
    resolved = packet.memo.unit_windows
    assert resolved is not None
    spike_times(packet, unit_id=unit_ids[-1])
    assert packet.memo.unit_windows is resolved


def test_an_unreadable_bound_is_not_kept():
    """So the default it falls back to does not outlast the failure."""

    class _Broken:
        memo = Memo()

        def table(self, resource_id, columns=None):
            raise RuntimeError("no such resource")

    declared_bound(_Broken())
    assert _Broken.memo.bound is None


def test_a_rebound_packet_starts_from_what_was_kept_and_keeps_its_own(two_clock_packet):
    packet = open_packet(two_clock_packet)
    kept = anchors(packet)
    rebound = packet.with_declarations(packet.registry)
    assert rebound.memo is not packet.memo
    assert rebound.memo.anchors is kept
    ambiguities(rebound)
    assert packet.memo.ambiguities is None


def test_a_declared_bound_is_kept():
    packet = _Counting(Memo())
    assert declared_bound(packet) == declared_bound(packet) == 2.0
    assert packet.memo.bound == 2.0
    assert packet.reads == 1


def test_a_stand_in_keeping_no_memo_is_read_each_time():
    packet = _Counting()
    assert declared_bound(packet) == declared_bound(packet) == 2.0
    assert packet.reads == 2


@pytest.mark.parametrize("kept", [None, {}, "anchors"])
def test_only_a_memo_counts_as_one(kept):
    """A stand-in's unrelated `memo` attribute is not written to."""

    class _Other:
        memo = kept

    assert Memo.of(_Other()) == Memo()

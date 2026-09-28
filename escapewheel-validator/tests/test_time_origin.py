"""Part 05 §5.3's origin check: a declared `t_zero_tick` is the session's earliest mapped start.

The packet here is a stand-in exposing only the tables the check reads, so each case varies one
clock arrangement without building a registry around it.
"""

import pyarrow as pa
import pytest
from escapewheel_reader import ResourceNotFoundError

from escapewheel_validator.validator import Report, _check_time_origin

#: Probe anchors onto the reference: 30 parent ticks per tick, offset by 500.
ANCHORS = [(t, 30 * t + 500) for t in range(0, 11_000, 1000)]


class _Packet:
    def __init__(self, tables):
        self._tables = tables
        self._anchor_cache = None

    def table(self, resource_id, columns=None):
        if resource_id not in self._tables:
            raise ResourceNotFoundError(resource_id)
        table = self._tables[resource_id]
        return table.select(columns) if columns else table


def _packet(clocks, starts, *, origin, reference=1, anchors=(), sessions=None):
    """One session unless `sessions` is given as (session_id, origin, reference) rows."""
    sessions = sessions or [(1, origin, reference)]
    return _Packet(
        {
            "core.sessions": pa.table(
                {
                    "session_id": pa.array([s for s, _, _ in sessions], pa.int32()),
                    "t_zero_tick": pa.array([o for _, o, _ in sessions], pa.int64()),
                    "reference_clock_id": pa.array([r for _, _, r in sessions], pa.int32()),
                }
            ),
            "core.clocks": pa.table(
                {
                    "clock_id": pa.array([c for c, _, _, _ in clocks], pa.int32()),
                    "parent_clock_id": pa.array([p for _, p, _, _ in clocks], pa.int32()),
                    "transform_slope": pa.array([s for _, _, s, _ in clocks], pa.float64()),
                    "transform_offset": pa.array([o for _, _, _, o in clocks], pa.float64()),
                }
            ),
            "core.clock_observation_intervals": pa.table(
                {
                    "session_id": pa.array([s for s, _, _ in starts], pa.int32()),
                    "clock_id": pa.array([c for _, c, _ in starts], pa.int32()),
                    "start_tick": pa.array([t for _, _, t in starts], pa.int64()),
                }
            ),
            "core.clock_anchors": pa.table(
                {
                    "clock_id": pa.array([c for c, _, _ in anchors], pa.int32()),
                    "t_tick": pa.array([t for _, t, _ in anchors], pa.int64()),
                    "parent_tick": pa.array([p for _, _, p in anchors], pa.int64()),
                }
            ),
        }
    )


def _checks(packet):
    report = Report()
    _check_time_origin(packet, report)
    assert all(f.level == "error" and f.registry == "core" for f in report.findings)
    return [f.check for f in report.findings]


def _anchored(origin):
    # The probe's start at tick 10 maps to 800, before the reference's own start at 1000.
    return _packet(
        [(1, None, None, None), (2, 1, None, None)],
        [(1, 1, 1000), (1, 2, 10)],
        origin=origin,
        anchors=[(2, t, p) for t, p in ANCHORS],
    )


@pytest.mark.parametrize("origin", [799, 800, 801])
def test_an_origin_within_one_reference_tick_passes(origin):
    assert _checks(_anchored(origin)) == []


@pytest.mark.parametrize("origin", [798, 802, 1000])
def test_an_origin_two_ticks_from_the_earliest_start_is_not_earliest(origin):
    assert _checks(_anchored(origin)) == ["time.origin_not_earliest"]


def test_a_window_on_an_unanchored_clock_is_unmappable():
    packet = _packet([(1, None, None, None), (2, 1, None, None)], [(1, 1, 1000), (1, 2, 10)], origin=1000)
    assert _checks(packet) == ["time.origin_unmappable"]


def test_a_start_beyond_the_anchors_bound_is_unmappable():
    # 50,000 ticks past the last anchor is fifty median intervals out.
    packet = _packet(
        [(1, None, None, None), (2, 1, None, None)],
        [(1, 1, 1000), (1, 2, 60_000)],
        origin=1000,
        anchors=[(2, t, p) for t, p in ANCHORS],
    )
    assert _checks(packet) == ["time.origin_unmappable"]


def test_an_origin_but_no_reference_clock_is_unmappable():
    packet = _packet([(1, None, None, None)], [(1, 1, 1000)], origin=1000, reference=None)
    assert _checks(packet) == ["time.origin_unmappable"]


def test_a_linear_transform_maps_the_start():
    packet = _packet([(1, None, None, None), (2, 1, 30.0, 500.0)], [(1, 1, 1000), (1, 2, 10)], origin=800)
    assert _checks(packet) == []


def test_a_chain_of_parents_maps_through_every_clock():
    # Clock 3 halves onto clock 2, which is anchored onto the reference: 5 -> 10 -> 800. Reading
    # clock 2's tick as the reference's would put the minimum at 10.
    packet = _packet(
        [(1, None, None, None), (2, 1, None, None), (3, 2, 2.0, 0.0)],
        [(1, 1, 1000), (1, 3, 5)],
        origin=800,
        anchors=[(2, t, p) for t, p in ANCHORS],
    )
    assert _checks(packet) == []


def test_a_reference_below_the_root_is_reached_through_the_inverse():
    # The reference is the probe; the root's start at 800 is the probe's tick 10.
    packet = _packet(
        [(1, None, None, None), (2, 1, None, None)],
        [(1, 1, 800), (1, 2, 1000)],
        origin=10,
        reference=2,
        anchors=[(2, t, p) for t, p in ANCHORS],
    )
    assert _checks(packet) == []


def test_each_session_is_judged_on_its_own_reference_clock():
    packet = _packet(
        [(1, None, None, None), (2, None, None, None)],
        [(1, 1, 1000), (2, 2, 40)],
        origin=None,
        sessions=[(1, 1000, 1), (2, 40, 2)],
    )
    assert _checks(packet) == []


def test_a_session_that_observed_nothing_is_not_checked():
    packet = _packet(
        [(1, None, None, None)],
        [(1, 1, 1000)],
        origin=None,
        sessions=[(1, 1000, 1), (2, 5, 1)],
    )
    assert _checks(packet) == []

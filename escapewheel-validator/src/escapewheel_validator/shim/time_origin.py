"""A session's declared time origin against its earliest mapped observation start.

- :func:`check_time_origin` -- each declared `t_zero_tick` is its session's earliest observation
  start, carried onto the session's reference clock.

A tick is carried between clocks along the parent chain `core.clocks` declares, through the
reader's own alignment, so the check and a reader agree on where a tick lands.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pyarrow as pa
from escapewheel_reader import Packet, PacketError
from escapewheel_reader.resource_ids import (
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_SESSIONS,
)

from .. import check_table
from ..errors import _Unmappable
from ..report import Report


def _clock_graph(packet: Packet) -> dict[int, dict[str, Any]]:
    """Each clock's parent and the transform onto it, from `core.clocks`."""
    clocks = packet.table(CORE_CLOCKS)
    names = clocks.column_names
    columns = {c: clocks.column(c).to_pylist() for c in ("parent_clock_id", "transform_slope", "transform_offset")}
    graph: dict[int, dict[str, Any]] = {}
    for row, clock in enumerate(clocks.column("clock_id").to_pylist()):
        graph[clock] = {c: (columns[c][row] if c in names else None) for c in columns}
    return graph


def _ancestry(clock: int, graph: Mapping[int, Mapping[str, Any]]) -> list[int]:
    """Walk from `clock` through its parents to the root, stopping where a cycle repeats."""
    chain = [clock]
    while (parent := graph.get(chain[-1], {}).get("parent_clock_id")) is not None and parent not in chain:
        chain.append(parent)
    return chain


def _step(
    tick: int,
    child: int,
    graph: Mapping[int, Mapping[str, Any]],
    by_clock: Mapping[int, tuple[Any, Any]],
    bound: float,
    *,
    upward: bool,
) -> int:
    """Carry one tick across the edge from `child` to its parent, or back down it."""
    from escapewheel_reader.clocks import align
    from escapewheel_reader.errors import Unanchored

    edge = graph[child]
    if edge["transform_slope"] is not None and edge["transform_offset"] is not None:
        slope, offset = float(edge["transform_slope"]), float(edge["transform_offset"])
        return int(np.rint(offset + slope * tick if upward else (tick - offset) / slope))
    if child not in by_clock:
        raise _Unmappable(f"{child} declares neither a transform nor anchors onto its parent")
    anchor_t, anchor_p = by_clock[child]
    try:
        converted, defined = align(
            np.array([tick], dtype=np.int64),
            *((anchor_t, anchor_p) if upward else (anchor_p, anchor_t)),
            bound=bound,
        )
    except (Unanchored, ValueError) as refused:
        raise _Unmappable(f"{child}'s anchors do not map: {refused}") from refused
    if not defined[0]:
        raise _Unmappable(f"tick {tick} lies beyond the alignment bound of {child}'s anchors")
    return int(converted[0])


def _onto(
    tick: int,
    clock: int,
    reference: int,
    graph: Mapping[int, Mapping[str, Any]],
    by_clock: Mapping[int, tuple[Any, Any]],
    bound: float,
) -> int:
    """Carry a tick from `clock` to `reference` along the parent chain joining them.

    The path climbs from `clock` to the nearest clock it shares with the reference's ancestry, then
    descends to the reference through the inverse of each edge, so a reference that is itself a
    child clock is reached as well as one at the root.
    """
    up, down = _ancestry(clock, graph), _ancestry(reference, graph)
    shared = next((c for c in up if c in down), None)
    if shared is None:
        raise _Unmappable(f"{clock} and {reference} share no ancestor, so no path joins them")
    for child in up[: up.index(shared)]:
        tick = _step(tick, child, graph, by_clock, bound, upward=True)
    for child in reversed(down[: down.index(shared)]):
        tick = _step(tick, child, graph, by_clock, bound, upward=False)
    return tick


def check_time_origin(packet: Packet, report: Report) -> None:
    """Part 05 §5.3: each declared `t_zero_tick` is its session's earliest observation start.

    Not SQL: the minimum is taken across clocks, and carrying a start onto the reference walks the
    parent chain through each clock's anchors or transform, which no query expresses. Each session
    is judged on its own reference clock and alignment bound. A session declaring no origin is not
    checked; one declaring a wrong origin shifts every second a consumer derives.
    """
    from escapewheel_reader.clocks import BOUND, anchors

    try:
        sessions = packet.table(CORE_SESSIONS)
        intervals = packet.table(CORE_CLOCK_OBSERVATION_INTERVALS)
    except PacketError:
        return
    if "t_zero_tick" not in sessions.column_names or not intervals.num_rows:
        return

    def column(table: pa.Table, name: str) -> list[Any]:
        return table.column(name).to_pylist() if name in table.column_names else [None] * table.num_rows

    starts_by_session: dict[Any, list[tuple[int, int]]] = {}
    for session, clock, start in zip(
        column(intervals, "session_id"), column(intervals, "clock_id"), column(intervals, "start_tick"), strict=True
    ):
        if start is not None:
            starts_by_session.setdefault(session, []).append((clock, int(start)))

    try:
        graph, by_clock = _clock_graph(packet), anchors(packet)
    except (PacketError, ValueError):
        graph, by_clock = {}, {}

    for session, stated, reference, bound in zip(
        column(sessions, "session_id"),
        column(sessions, "t_zero_tick"),
        column(sessions, "reference_clock_id"),
        column(sessions, "alignment_bound"),
        strict=True,
    ):
        # Part 01 §2.2 forbids an origin where the session observed nothing; no checker verifies it.
        if stated is None or not (starts := starts_by_session.get(session)):
            continue
        if reference is None:
            report.add(
                check_table.TIME_ORIGIN_UNMAPPABLE,
                f"session {session} declares t_zero_tick but no reference clock to state it on",
                [(str(session),)],
                registry="core",
            )
            continue
        mapped = []
        for clock, start in starts:
            try:
                mapped.append(_onto(start, clock, reference, graph, by_clock, BOUND if bound is None else float(bound)))
            except _Unmappable as refused:
                report.add(
                    check_table.TIME_ORIGIN_UNMAPPABLE,
                    f"session {session}: {clock}'s observation start {start} does not map to {reference}, "
                    f"so no origin is defined ({refused})",
                    [(str(session), str(clock), str(start))],
                    registry="core",
                )
                break
        else:
            expected = min(mapped)
            # A writer's estimator may fit anchors it does not record, so one reference tick of
            # disagreement is rounding rather than a wrong origin.
            if abs(int(stated) - expected) > 1:
                report.add(
                    check_table.TIME_ORIGIN_NOT_EARLIEST,
                    f"session {session} declares t_zero_tick {stated} but its earliest observation start "
                    f"on {reference} is {expected}",
                    [(str(session), str(stated), str(expected))],
                    registry="core",
                )


__all__: list[str] = []

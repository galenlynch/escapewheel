"""The clock mappings of a build and what it records of them (Part 01 §3.9).

- :data:`TOLERANCE` -- the most error a clock mapping may carry, in seconds.
- :func:`anchors_by_clock`, :func:`bound_for` -- a build's anchors per clock, and the bound a
  clock is mapped at.
- :func:`time_origin`, :func:`declare_origin` -- the session's time origin and its record.
- :func:`declare_withheld` -- the terminal-anchor test's result on each clock.
- :func:`alignment_parameters` -- what the import run records of the alignment.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from math import ceil
from typing import TYPE_CHECKING, Any

import numpy as np
from escapewheel_reader.clocks import BOUND, align
from escapewheel_reader.resource_ids import CORE_CLOCKS
from numpy.typing import NDArray

from .delivery import Delivered
from .notes import Note, NoteCode
from .protocols import WithholdsAnchors

if TYPE_CHECKING:
    from .session import Context


#: The most error a mapping may carry before Part 01 §3.9 calls it undefined, in **seconds**.
#:
#: A duration rather than a tick count, because it is a claim about time and not about one
#: clock's granularity. Three milliseconds is R40's default: several times the estimator's own
#: error at any anchor distance, and far below anything that moves an analysis. One parent
#: tick would sit below the estimator's median error and gate on measurement noise.
TOLERANCE = 3e-3


def anchors_by_clock(context: Context) -> dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Return every anchor a source produced as arrays per clock, in the shape `align` wants."""
    collected: dict[str, tuple[list[int], list[int]]] = {}
    for row in context.anchors:
        at, parent = collected.setdefault(row["clock_id"], ([], []))
        at.append(row["t_tick"])
        parent.append(row["parent_tick"])
    return {
        clock: (np.array(at, dtype=np.int64), np.array(parent, dtype=np.int64))
        for clock, (at, parent) in collected.items()
    }


def bound_for(
    by_clock: Mapping[str, tuple[NDArray[np.int64], NDArray[np.int64]]],
    reach: Mapping[str, tuple[int, int]],
    tolerance: float,
    rate: float,
) -> tuple[float, dict[str, Any]]:
    """Choose the bound to map at, measuring it as Part 01 §3.9 requires.

    A packet whose earliest data sits inside one median anchor interval of its first anchor
    needs nothing; Part 01 §3.9's default covers it and this returns it unmeasured. Where it does
    not -- and withholding a displaced first anchor (Part 02 §12.6) is what usually makes it not --
    the writer may go further only by measuring the estimator at the distance it intends to
    use and finding its **95th percentile** within `tolerance` (Part 01 §3.9). The median is not a
    statement about what a consumer may rely on.

    Parameters
    ----------
    by_clock : Mapping
        Anchor pairs per clock.
    reach : Mapping
        Clock ID to the span that must map, which is the clock's own observation window. Both
        ends count: a session whose sync train stops well before its recording does needs the
        bound at the far end, and only the window says so.
    tolerance : float
        The most error the mapping may carry, in seconds (Part 01 §3.9).
    rate : float
        The parent clock's rate in hertz, which turns that duration into the parent ticks the
        measurement is in.

    Returns
    -------
    tuple
        The bound in median anchor intervals, and the measurement, for the run's parameters.
    """
    from escapewheel_reader.clocks import extrapolation_error

    needed = 0.0
    for clock, (at, _) in by_clock.items():
        if (window := reach.get(clock)) is None:
            continue
        interval = float(np.median(np.diff(at)))
        needed = max(needed, (at[0] - window[0]) / interval, (window[1] - at[-1]) / interval)
    if needed <= BOUND:
        return BOUND, {}

    distance = ceil(needed)
    allowed = tolerance * rate
    measured = {clock: extrapolation_error(at, parent, distance) for clock, (at, parent) in by_clock.items()}
    worst = max((m["p95"] for m in measured.values() if m), default=float("inf"))
    report: dict[str, Any] = {
        "distance": distance,
        "tolerance_seconds": tolerance,
        # Every statistic, so a reader may judge the packet by a stricter rule than the
        # writer applied (Part 01 §3.9).
        "p95_error_seconds": round(worst / rate, 9),
        "median_error_seconds": round(max((m["median"] for m in measured.values() if m), default=0.0) / rate, 9),
        "max_error_seconds": round(max((m["max"] for m in measured.values() if m), default=0.0) / rate, 9),
        "per_clock": {clock: {k: round(v, 2) for k, v in m.items()} for clock, m in measured.items() if m},
    }
    report["used"] = BOUND if worst > allowed else float(distance)
    return report["used"], report


def time_origin(
    context: Context,
    intervals: list[dict[str, Any]],
    by_clock: Mapping[str, tuple[NDArray[np.int64], NDArray[np.int64]]],
    bound: float,
) -> int | None:
    """Part 01 §2.2: the earliest observation start among the session's clocks, on the reference.

    Returns None where any clock's window start cannot be mapped, since a minimum taken over
    some of the clocks is not the minimum Part 01 §2.2 requires a writer to declare -- and R39
    §2.4 says an origin the writer cannot compute is one it must not state.
    """
    reference = context.reference.clock_id if context.reference else None
    starts: list[int] = []
    for row in intervals:
        clock, start = row["clock_id"], int(row["start_tick"])
        if clock == reference:
            starts.append(start)
            continue
        if clock not in by_clock:
            return None
        converted, defined = align(np.array([start], dtype=np.int64), *by_clock[clock], bound=bound)
        if not defined[0]:
            return None
        starts.append(int(converted[0]))
    return min(starts) if starts else None


def declare_withheld(context: Context, writer: Any, say: Callable[[str], None]) -> None:
    """Put Part 02 §12.6's terminal-anchor test on each clock it examined (R99 §3.2).

    The sync source computes this and emits only the reference clock's row; the probe clock rows
    are the sorter's, and the sorter's `CONSUMES` runs it first, so they are already staged. Three
    states are the point: a clock the test never reached keeps both columns null, where one it
    reached and kept records `false` (Part 02 §12.6).
    """
    tester = context.sources.get("sync")
    withheld = tester.withheld if isinstance(tester, WithholdsAnchors) else None
    if not withheld:
        if any(isinstance(source, Delivered) for source in context.sources.values()):
            # A delivered source states what it produced and nothing about another source's rows,
            # and this is a fact about the sorter's clock rows. No resource carries it, so it does
            # not cross -- and a packet missing it says nothing, which is why this says it here.
            context.notes.append(
                Note(
                    "the terminal-anchor test's result is not recorded: the source that runs it was "
                    "delivered, and no resource carries a fact about another source's rows (R99 §3.2)",
                    NoteCode.ANCHOR_TEST_UNRECORDED,
                )
            )
        return
    stamped = writer.stamp(
        CORE_CLOCKS,
        "clock_id",
        {
            clock: {
                "withheld_first_anchor": "first" in entry["anchors"],
                "withheld_last_anchor": "last" in entry["anchors"],
            }
            for clock, entry in withheld.items()
        },
    )
    dropped = sum(entry["n_withheld"] for entry in withheld.values())
    say(
        f"  terminal-anchor test recorded on {stamped} of {len(withheld)} clocks, "
        f"{dropped} anchor(s) withheld (R99 §3.2)"
    )
    if stamped != len(withheld):
        context.notes.append(
            Note(
                f"the terminal-anchor test examined {len(withheld)} clocks and {stamped} of them are "
                "staged, so the rest carry no record of it",
                NoteCode.ANCHOR_TEST_PARTIAL,
            )
        )


def declare_origin(context: Context, say: Callable[[str], None]) -> None:
    """Put R39's time origin on the session, or say why the packet gets none."""
    if not (context.observed and context.reference):
        return
    by_clock, bound = context.alignment()
    # R99 §3.1: a null column is a writer that stayed within Part 01 §3.9's default, so only a
    # measured widening is recorded. Set before the origin, which may decline to be stated.
    if bound != BOUND:
        context.session_extra["alignment_bound"] = bound
        say(f"  alignment_bound {bound:g} median anchor intervals (R99 §3.1)")
    origin = time_origin(context, context.observed, by_clock, bound)
    if origin is None:
        say("  no t_zero_tick: a clock's observation start does not map to the reference (Part 01 §2.2)")
        return
    context.session_extra["t_zero_tick"] = origin
    say(f"  t_zero_tick {origin:,} on {context.reference.clock_id} (Part 01 §2.2)")


def alignment_parameters(context: Context | None) -> dict[str, Any]:
    """Return the measurement behind the run's alignment decisions, or nothing.

    Part 02 §12.6 draws the line: the three facts a consumer needs to place a tick are columns, and
    what justified them stays here. So this holds the error distribution and the distance it was
    measured at, and not the bound, the withheld anchors or the phase steps.
    """
    if context is None or not context.measured_bound:
        return {}
    # `used` is `core.sessions.alignment_bound`; the rest is why the writer chose it.
    return {"alignment_bound": {k: v for k, v in context.measured_bound.items() if k != "used"}}


__all__ = [
    "TOLERANCE",
    "alignment_parameters",
    "anchors_by_clock",
    "bound_for",
    "declare_origin",
    "declare_withheld",
    "time_origin",
]

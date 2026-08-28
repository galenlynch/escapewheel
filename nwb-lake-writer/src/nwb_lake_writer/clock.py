"""A declared clock, and the only sanctioned way to turn seconds into ticks.

Time in a packet is integer ticks on a declared clock (`03`); float seconds are derived.
An importer therefore has to get from its source's seconds to ticks, and there are exactly
two ways to do that:

**Quantization** -- the source's values already lie on the clock's grid, so
``round(t * rate)`` is lossless and provable. :meth:`Clock.ticks` does this and *checks*,
refusing anything off-grid.

**Fitting** -- the source's values do not lie on any grid, so recovering ticks means
estimating a rate and an offset. That is a guess, and this module does not offer it.

The distinction is not academic. In `inventory/nwb-zarr-776259-2025-04-09.md` the same file
contains both cases: every behaviour and trial timestamp is exactly on a 31,250 Hz grid
(§3.3.1), while spike times have a per-probe alignment baked in and lie on no grid at all
(§3.3). One converts; the other cannot, and gets an :class:`OffGrid` rather than plausible
numbers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from numpy.typing import NDArray

#: int64's range. A tick outside it is not representable in `core.*.t_tick`.
TICK_MIN, TICK_MAX = -(2**63), 2**63 - 1


class OffGrid(ValueError):
    """Source seconds do not lie on this clock's tick grid, so no exact tick exists.

    Recovering ticks from such values means fitting a rate and an offset, which is an
    estimate this package will not silently produce. The message reports how many values
    missed and by how much, in ticks.

    Attributes
    ----------
    n_off : int
        How many values missed the grid.
    worst : float
        The largest miss, as a fraction of one tick.
    """

    def __init__(self, message: str, *, n_off: int, worst: float) -> None:
        super().__init__(message)
        self.n_off = n_off
        self.worst = worst


class NonFinite(ValueError):
    """A source timestamp was NaN or infinite.

    Placeholder streams do occur -- three of the six behaviour streams in
    `inventory/nwb-zarr-776259-2025-04-09.md` carry a single NaN -- so a caller that expects
    them filters first and says so, rather than letting a NaN become an arbitrary integer.
    """


@dataclass(frozen=True)
class Clock:
    """A clock a packet declares, and the tick grid it defines.

    The rate is a rational, not a float, because the grid check has to be exact: HARP's
    31,250 Hz is 31250/1, and a nominal 30 kHz sampling clock whose true rate is 30000/1.0001
    is not the same grid as 30000/1.

    Parameters
    ----------
    clock_id : str
        Stable ID, unique in the packet.
    session_id : str
        The session this clock belongs to.
    name : str
        Human-readable name.
    tick_rate_num, tick_rate_den : int
        The tick rate as an exact rational, in hertz.
    origin : str
        What tick 0 means. Free text; `core.clocks.origin` is required.
    tick_zero_utc : datetime, optional
        Wall-clock instant of tick 0 (R6). Offset-aware, or omitted. A free-running clock's
        tick 0 is a power-on instant that no source declares, so this is usually derived --
        see :meth:`~nwb_lake_writer.sources.aind.SessionSource.epoch`, which records the
        derivation as a note because the packet has nowhere to carry its ±1 s uncertainty.
        Derive it only where an independent check exists; omit it rather than guess.
    parent_clock_id : str, optional
        The clock this one aligns to (R13 §4). The alignment itself lives elsewhere -- in
        `transform_slope`/`transform_offset` or in `core.clock_anchors`, never both -- so a
        parent alone declares parentage without claiming the relation has been measured.
    metadata : dict, optional
        Free-form, serialized into `core.clocks.metadata`.

    Examples
    --------
    >>> harp = Clock("harp", session_id="s1", name="HARP", tick_rate_num=31250, origin="HARP epoch")
    >>> harp.ticks([1.0, 0.000032])
    array([31250,     1])
    """

    clock_id: str
    session_id: str
    name: str
    tick_rate_num: int
    origin: str
    tick_rate_den: int = 1
    tick_zero_utc: datetime | None = None
    parent_clock_id: str | None = None
    metadata: dict[str, Any] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Reject a rate that is not a positive rational."""
        if self.tick_rate_num <= 0 or self.tick_rate_den <= 0:
            raise ValueError(f"{self.clock_id}: tick rate {self.tick_rate_num}/{self.tick_rate_den} is not positive")

    @property
    def hz(self) -> float:
        """The tick rate in hertz, as a float. The rational is authoritative."""
        return self.tick_rate_num / self.tick_rate_den

    def ticks(self, seconds: Sequence[float] | NDArray[np.floating[Any]]) -> NDArray[np.int64]:
        """Convert seconds on this clock to exact integer ticks.

        Parameters
        ----------
        seconds : sequence of float
            Times in seconds since this clock's tick 0.

        Returns
        -------
        numpy.ndarray of int64
            The ticks.

        Raises
        ------
        NonFinite
            If any value is NaN or infinite.
        OffGrid
            If any value does not land on an integer tick.
        OverflowError
            If any tick falls outside int64.
        """
        values = np.asarray(seconds, dtype=np.float64)
        if values.size == 0:
            return np.empty(0, dtype=np.int64)
        if not np.isfinite(values).all():
            raise NonFinite(f"{self.clock_id}: {int((~np.isfinite(values)).sum())} of {values.size} values not finite")

        exact = values * self.tick_rate_num / self.tick_rate_den
        rounded = np.rint(exact)
        residual = np.abs(exact - rounded)
        if off := int((residual > 0).sum()):
            worst = float(residual.max())
            raise OffGrid(
                f"{self.clock_id}: {off} of {values.size} values miss the {self.hz:g} Hz grid "
                f"by up to {worst:.4g} tick; converting them would mean fitting a rate, not quantizing",
                n_off=off,
                worst=worst,
            )
        if rounded.min() < TICK_MIN or rounded.max() > TICK_MAX:
            raise OverflowError(f"{self.clock_id}: ticks {rounded.min():.0f}..{rounded.max():.0f} exceed int64")
        return rounded.astype(np.int64)

    def tick_at(self, instant: datetime) -> int:
        """Convert a wall-clock instant to the nearest tick on this clock.

        Distinct from :meth:`ticks`, and deliberately so. `ticks` converts values already on
        this clock and refuses any that miss the grid, because a source disagreeing with the
        declared rate is a defect. This converts an instant read off a *different* clock -- a
        wall clock -- where landing on the grid is coincidence, so it rounds. The residual is
        under half a tick, 16 µs at 31,250 Hz, which is far below the uncertainty in any
        `tick_zero_utc` derived rather than declared.

        Parameters
        ----------
        instant : datetime
            An offset-aware wall-clock time.

        Returns
        -------
        int
            The tick on this clock.

        Raises
        ------
        ValueError
            If this clock has no `tick_zero_utc`, or `instant` carries no offset -- in either
            case nothing locates the instant on this clock.
        OverflowError
            If the tick falls outside int64.
        """
        if self.tick_zero_utc is None:
            raise ValueError(f"{self.clock_id}: no tick_zero_utc, so a wall clock locates no tick on it")
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError(f"{instant!r} carries no offset, so it locates no tick")
        elapsed = (instant.astimezone(timezone.utc) - self.tick_zero_utc).total_seconds()
        tick = round(elapsed * self.tick_rate_num / self.tick_rate_den)
        if tick < TICK_MIN or tick > TICK_MAX:
            raise OverflowError(f"{self.clock_id}: tick {tick} exceeds int64")
        return tick

    def record(self) -> dict[str, Any]:
        """Render this clock as a `core.clocks` row.

        Returns
        -------
        dict
            The row. `tick_rate_hz` is written alongside the rational so a reader that wants
            a float does not have to divide; `core.clocks.tick_rate_declared` accepts either.
        """
        row: dict[str, Any] = {
            "clock_id": self.clock_id,
            "session_id": self.session_id,
            "name": self.name,
            "tick_rate_hz": self.hz,
            "tick_rate_num": self.tick_rate_num,
            "tick_rate_den": self.tick_rate_den,
            "origin": self.origin,
        }
        if self.tick_zero_utc is not None:
            row["tick_zero_utc"] = self.tick_zero_utc
        if self.parent_clock_id is not None:
            row["parent_clock_id"] = self.parent_clock_id
        if self.metadata:
            row["metadata"] = self.metadata
        return row


def epoch_from(instant: datetime, t_tick: int, tick_rate_num: int, tick_rate_den: int = 1) -> datetime:
    """Locate tick 0 in wall-clock terms, given one tick whose instant is known.

    The arithmetic is done in UTC, and that is the whole reason this function exists.
    Python's aware-datetime subtraction is **wall-clock** arithmetic: it subtracts from the
    naive local time and then re-resolves the offset, so stepping back across a DST boundary
    loses or gains an hour silently. A HARP epoch 134 days before a Pacific session in April
    lands in November, on the far side of the transition, and gets it wrong by an hour.

    Parameters
    ----------
    instant : datetime
        Wall-clock time of `t_tick`. Must carry an offset.
    t_tick : int
        The tick that occurred at `instant`.
    tick_rate_num, tick_rate_den : int
        The clock's tick rate, in hertz.

    Returns
    -------
    datetime
        The UTC instant of tick 0.

    Raises
    ------
    ValueError
        If `instant` carries no offset, since then it locates nothing.
    """
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError(f"{instant!r} carries no offset, so it does not locate tick 0")
    elapsed = timedelta(seconds=t_tick * tick_rate_den / tick_rate_num)
    return instant.astimezone(timezone.utc) - elapsed


#: HARP's native fractional resolution: 32 µs, measured exact for every behaviour and trial
#: timestamp in `inventory/nwb-zarr-776259-2025-04-09.md` §3.3.1.
HARP_TICK_RATE_HZ = 31250


__all__ = ["HARP_TICK_RATE_HZ", "TICK_MAX", "TICK_MIN", "Clock", "NonFinite", "OffGrid", "epoch_from"]

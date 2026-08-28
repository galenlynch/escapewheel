"""Map ticks from one clock onto its parent, through anchors.

This is R13 §3's piecewise-linear mapping with R27 §5.3's bound, and it is the only place
that arithmetic is written. A spike's tick is exact on its probe's clock and means nothing
beside another probe's; the anchors are what relate them, and this turns the relation into
numbers.

Three rules, and the third is the one that costs
------------------------------------------------

Let *m* be the median interval between a clock's anchors.

1. Between two anchors no more than 2*m* apart, linear interpolation on that pair.
2. Beyond the terminal anchors, out to *m*, the **globally fitted rate** -- never the terminal
   segment's slope. Measured on real sync pulses, a global fit predicts held-out anchors to
   6-18 µs at one second and stays under 1.4 samples at a minute, while the terminal segment
   degrades to ~0.9 ms. That difference is the whole reason R27 replaced R13's ban.
3. Anywhere further than *m* from every anchor -- past the ends, or inside a wider gap -- the
   mapping is undefined, and this returns a mask saying so rather than a plausible number.

The mask is not a formality. On a real session the first sync pulse arrives 18,000 to 28,000
samples after the recording starts, so the spikes in that window have no defined parent tick
and are exactly the ones a caller would otherwise silently misplace.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

#: How far from an anchor the mapping stays defined, as a multiple of the median anchor
#: interval (R27 §5.3). One, so that the same threshold covers a gap between anchors and the
#: unanchored ends -- the bound and the region it has to cover are the same quantity, because
#: a free-running sync pulse leaves less than one interval at each end by construction.
BOUND = 1.0


class Unanchored(ValueError):
    """A clock has too few anchors to define a mapping.

    Two anchors define a segment but no median interval worth trusting, so the bound would
    rest on a single observation.
    """


def rate(anchor_t: NDArray[np.int64], anchor_p: NDArray[np.int64]) -> tuple[float, float]:
    """Fit parent ticks against ticks over the whole anchor sequence.

    Returns slope and intercept. Centred before fitting: anchors run to 5.5e11 on a HARP
    clock, and a least-squares fit on raw values there loses precision that the residual
    cannot afford.
    """
    centre_t = float(anchor_t.mean())
    centre_p = float(anchor_p.mean())
    dt = anchor_t.astype(np.float64) - centre_t
    dp = anchor_p.astype(np.float64) - centre_p
    slope = float(dt @ dp / (dt @ dt))
    return slope, centre_p - slope * centre_t


def align(
    ticks: NDArray[np.int64],
    anchor_t: NDArray[np.int64],
    anchor_p: NDArray[np.int64],
    *,
    bound: float = BOUND,
) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
    """Map ticks onto the parent clock.

    Parameters
    ----------
    ticks : numpy.ndarray of int64
        Ticks on the child clock, in any order.
    anchor_t, anchor_p : numpy.ndarray of int64
        The anchor pairs, both strictly increasing (R13 §3).
    bound : float, default `BOUND`
        How far from an anchor the mapping stays defined, in median anchor intervals.

    Returns
    -------
    parent : numpy.ndarray of int64
        The parent tick for each input. Meaningless where `defined` is False.
    defined : numpy.ndarray of bool
        Whether the mapping is defined there. A caller writes null where it is not.

    Raises
    ------
    Unanchored
        If fewer than three anchors are given.
    ValueError
        If either sequence does not strictly increase, since interpolation between them
        would then be undefined (R13 §3).
    """
    anchor_t = np.asarray(anchor_t, dtype=np.int64)
    anchor_p = np.asarray(anchor_p, dtype=np.int64)
    if anchor_t.size < 3:
        raise Unanchored(f"{anchor_t.size} anchors define no median interval to bound by")
    if not ((np.diff(anchor_t) > 0).all() and (np.diff(anchor_p) > 0).all()):
        raise ValueError("anchors do not increase together, so interpolation between them is undefined")

    ticks = np.asarray(ticks, dtype=np.int64)
    span = float(np.median(np.diff(anchor_t))) * bound

    # Interior: np.interp is a single C pass doing the search and the lerp together, and is an
    # order of magnitude faster than gathering the bracketing pairs and computing them here.
    parent = np.rint(np.interp(ticks, anchor_t, anchor_p)).astype(np.int64)

    # Outside the anchor span np.interp clamps to the terminal value, which is a wrong answer
    # rather than a missing one, so both ends are recomputed at the fitted rate.
    slope, intercept = rate(anchor_t, anchor_p)
    outside = (ticks < anchor_t[0]) | (ticks > anchor_t[-1])
    if outside.any():
        parent[outside] = np.rint(slope * ticks[outside].astype(np.float64) + intercept).astype(np.int64)

    # Distance to the nearest anchor, which is what the bound is on -- the same threshold for
    # a gap between anchors and for the unanchored ends.
    left = np.searchsorted(anchor_t, ticks, side="right") - 1
    np.clip(left, 0, anchor_t.size - 1, out=left)
    right = np.minimum(left + 1, anchor_t.size - 1)
    nearest = np.minimum(np.abs(ticks - anchor_t[left]), np.abs(anchor_t[right] - ticks))
    return parent, nearest <= span


__all__ = ["BOUND", "Unanchored", "align", "rate"]

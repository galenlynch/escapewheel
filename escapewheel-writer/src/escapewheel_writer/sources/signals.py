"""Continuously sampled streams as arrays on their own dispatch clocks, whatever file they are read from.

- :class:`SignalArrays` -- each signal's array, asset row, clock, axis and anchors, from the
  ticks and values a reading adapter supplies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from escapewheel_reader.resource_ids import CORE_ARRAY_ASSET_INSTANCES
from numpy.typing import NDArray

from ..clock import TickGrid


class SignalArrays:
    """The tables a set of signals becomes, given each one's ticks on the reference clock and its values.

    A reading adapter sets `signals`, `prefix`, `session_id` and `clock` (the reference
    :class:`~escapewheel_writer.clock.TickGrid`), and supplies `_signal`; the remaining hooks
    have defaults.
    """

    signals: tuple[str, ...]
    prefix: str
    session_id: str
    clock: TickGrid

    if TYPE_CHECKING:

        def _signal(self, name: str) -> tuple[NDArray[np.int64], NDArray[Any]]:
            """Return one signal's reference-clock ticks and its values, one per sample."""

    def signal_device_id(self, name: str) -> str | None:
        """Return the instrument that made a signal, or None where the source does not say."""
        return None

    def signal_unit(self, name: str) -> str | None:
        """Return a signal's UCUM unit, or None where the source does not say."""
        return None

    def signal_array_id(self, name: str) -> str:
        """Return the array asset a signal becomes; its resource is `core.` followed by this."""
        return f"{self.prefix}{name}"

    def _measured_rate(self, name: str) -> float | None:
        ticks, _ = self._signal(name)
        span = int(ticks[-1] - ticks[0]) if len(ticks) > 1 else 0
        return round((len(ticks) - 1) * self.clock.tick_rate_num / span, 6) if span else None

    def staged_arrays(self) -> list[Any]:
        """Return each signal's values, for `add_array`.

        One array per signal. Its time axis is not an array: the samples are regular on the
        device's dispatch clock, so `array_dimensions` declares the axis in regular form.
        """
        from ..bindings import StagedArray

        staged = []
        for name in self.signals:
            _, values = self._signal(name)
            array_id = self.signal_array_id(name)
            # Delta, because a densely sampled signal is smooth and its differences compress far
            # better than its values. Part 03 §6.3 permits any codec, but delta is outside the v3
            # reader floor: Zarr.jl, TensorStore, and zarrs cannot read it (Part 10 §5), and a
            # validator reports the array at `info`.
            staged.append(
                StagedArray(
                    values=values,
                    resource_id=f"core.{array_id}",
                    declaration_id=CORE_ARRAY_ASSET_INSTANCES,
                    array_asset_id=array_id,
                    chunks=(min(len(values), 1 << 20),),
                    codecs=("numcodecs.delta", "blosc"),
                )
            )
        return staged

    def array_assets(self) -> list[dict[str, Any]]:
        """`core.array_assets`, one row per signal."""
        return [
            {
                "session_id": self.session_id,
                "array_asset_id": self.signal_array_id(name),
                # The packet identity `staged_arrays` gives the array, so a delivered one binds
                # to this row by name alone (Part 12 §5).
                "resource_id": f"core.{self.signal_array_id(name)}",
                # Part 01 §3.17: which instrument made this array.
                "device_id": self.signal_device_id(name),
                # No `array_asset_name`: Part 02 §8.2's rule for a clock holds for an asset
                # too -- the name is what the identifier stands for, and the numbering fills
                # it from exactly that where a row leaves it unset. A source's own label here
                # would leave the packet with no record of what the identifier was minted from,
                # and nothing to join a row to its manifest entry by.
                "clock_id": self._dispatch_clock_id(name),
                "sample_rate_hz": self._measured_rate(name),
                "unit": self.signal_unit(name),
            }
            for name in self.signals
        ]

    def _dispatch_clock_id(self, name: str) -> str:
        """Return the clock a signal is regular on: the device's own dispatch counter."""
        return f"{self.signal_array_id(name)}.dispatch"

    def array_dimensions(self) -> list[dict[str, Any]]:
        """`core.array_dimensions`, one axis per signal, in Part 02 §12.11's regular form.

        Tick `k` is sample `k`. That is not an approximation: a HARP device schedules its
        dispatch on its own microsecond timer, accumulating rather than re-basing, so the
        samples are evenly spaced on that counter. What is *not* even is the HARP timestamp
        each message carries, because the timer and the timestamp count different oscillators,
        parts per million apart, which over a session reaches hundreds of ticks. Exactly that
        difference belongs in `core.clock_anchors` rather than in the axis.
        """
        return [
            {
                "array_asset_id": self.signal_array_id(name),
                "axis_index": 0,
                "dimension_name": "time",
                "clock_id": self._dispatch_clock_id(name),
                "origin_tick": 0,
                "step_tick_num": 1,
            }
            for name in self.signals
        ]

    def signal_clocks(self) -> list[dict[str, Any]]:
        """`core.clocks`, one per signal: the dispatch counter its samples are regular on."""
        return [
            {
                "clock_id": self._dispatch_clock_id(name),
                "session_id": self.session_id,
                # The float alone (Part 02 §12.4). This rate is measured from the dispatch
                # spacing rather than declared, so a rational would be one the source never
                # stated, and a rate someone measured is recorded as measured.
                "tick_rate_hz": self._measured_rate(name),
                "origin": "the device's first dispatched sample; tick k is sample k",
                # `clock_name` is left for the numbering to fill from `clock_id` (Part 02 §8.2);
                # what this counter is travels as a label, having no column of its own.
                "metadata": {"label": f"{name} dispatch counter"},
                "parent_clock_id": self.clock.clock_id,
            }
            for name in self.signals
        ]

    def signal_anchors(self, every: int = 10_000) -> list[dict[str, Any]]:
        """`core.clock_anchors`, relating each dispatch counter to the reference clock.

        Every sample carries its own HARP timestamp, so every anchor here is measured and none
        is fitted. They are subsampled because they need only bound the interpolation error
        Part 01 §3.9 governs: at the parts per million separating the two oscillators, anchors
        tens of seconds apart leave far less than one tick between them, where the tolerance is
        3 ms.
        """
        rows: list[dict[str, Any]] = []
        for name in self.signals:
            ticks, _ = self._signal(name)
            if not len(ticks):
                continue
            positions = list(range(0, len(ticks), max(1, every)))
            if positions[-1] != len(ticks) - 1:
                positions.append(len(ticks) - 1)
            rows.extend(
                {
                    "clock_id": self._dispatch_clock_id(name),
                    "anchor_index": index,
                    "t_tick": position,
                    "parent_tick": int(ticks[position]),
                }
                for index, position in enumerate(positions)
            )
        return rows


__all__ = ["SignalArrays"]

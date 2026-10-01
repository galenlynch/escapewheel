"""An NWB file's continuously sampled acquisition streams, as arrays on their own dispatch clocks."""

from __future__ import annotations

from typing import Any

import numpy as np
from escapewheel_reader.resource_ids import (
    CORE_ARRAY_ASSET_INSTANCES,
)
from numpy.typing import NDArray

from ...errors import SourceDefect, SourceFault
from .file import NWBFile
from .names import ucum_code


class Signals(NWBFile):
    """The streams a recipe declares signals: each one's array, asset row, clock and anchors."""

    def signal_device_id(self, name: str) -> str | None:
        """Return the instrument that made a stream; None, since base NWB links it to no Device."""
        return None

    def _signal(self, name: str) -> tuple[NDArray[np.int64], NDArray[Any]]:
        """Return one signal's ticks and values, non-finite timestamps dropped as events are.

        Memoized: four callers need it -- the array, its asset row, its clock and its anchors --
        and each read decodes the whole series twice over, its timestamps and its values.
        """
        if name not in self._signals:
            # A recipe declares its signals, because whether a stream is one is a fact about
            # the instrument. Saying so about a stream the file lacks is a contradiction Part 05 §3.5
            # refuses in a recipe, so the refusal here names the declaration that asked for it
            # rather than surfacing as a Zarr encoding error naming a path.
            if not self.store.is_array(f"acquisition/{name}/timestamps"):
                held = ", ".join(self.store.members("acquisition")) or "nothing"
                raise SourceDefect(
                    f"the recipe declares signal {name!r} and this NWB has no "
                    f"acquisition/{name} with timestamps; acquisition holds {held}",
                    code=SourceFault.SIGNAL_ABSENT,
                    where=f"acquisition/{name}",
                )
            seconds = self.store.array(f"acquisition/{name}/timestamps")
            ticks, finite = self._ticks(seconds, f"acquisition/{name}")
            values = self._array(f"acquisition/{name}/data")
            self._signals[name] = (ticks, values[finite] if values.size == seconds.size else values)
        return self._signals[name]

    def staged_arrays(self) -> list[Any]:
        """Return each signal's values, for `add_array`.

        One array per signal. Its time axis is not an array: the samples are regular on the
        device's dispatch clock, so `array_dimensions` declares the axis in regular form.
        """
        from ...bindings import StagedArray

        staged = []
        for name in self.signals:
            ticks, values = self._signal(name)
            del ticks  # the axis is a clock and its anchors, not an array (R20 §2.1)
            # Delta, because a densely sampled signal is smooth and its differences compress far
            # better than its values. Part 03 §6.4 permits any codec, but delta is outside the v3
            # reader floor: Zarr.jl, TensorStore, and zarrs cannot read it (Part 10 §5), and a
            # validator reports the array at `info`.
            staged.append(
                StagedArray(
                    values=values,
                    resource_id=f"core.{self.prefix}{name}",
                    declaration_id=CORE_ARRAY_ASSET_INSTANCES,
                    array_asset_id=f"{self.prefix}{name}",
                    chunks=(min(len(values), 1 << 20),),
                    codecs=("numcodecs.delta", "blosc"),
                )
            )
        return staged

    def array_assets(self) -> list[dict[str, Any]]:
        """`core.array_assets`, one row per signal."""
        rows = []
        for name in self.signals:
            ticks, _ = self._signal(name)
            span = int(ticks[-1] - ticks[0]) if len(ticks) > 1 else 0
            rate = (len(ticks) - 1) * self.clock.tick_rate_num / span if span else None
            rows.append(
                {
                    "session_id": self.session_id,
                    "array_asset_id": f"{self.prefix}{name}",
                    # The packet identity `staged_arrays` gives the array, so a delivered one binds
                    # to this row by name alone (Part 12 §5).
                    "resource_id": f"core.{self.prefix}{name}",
                    # Part 01 §3.17: which instrument made this array. Read from the same description
                    # `_signal_devices` declares the device from, so the two cannot disagree.
                    "device_id": self.signal_device_id(name),
                    # No `array_asset_name`: Part 02 §8.2's rule for a clock holds for an asset
                    # too -- the name is what the identifier stands for, and the numbering fills
                    # it from exactly that where a row leaves it unset (R53 §2.5). A source's own
                    # label here would leave the packet with no record of what the identifier
                    # was minted from, and nothing to join a row to its manifest entry by.
                    # The description stays where it is read from, and is what the
                    # device row is built from.
                    "clock_id": self._dispatch_clock_id(name),
                    "sample_rate_hz": round(rate, 6) if rate else None,
                    "unit": ucum_code(str(self.attrs(f"acquisition/{name}/data").get("unit") or "") or None),
                }
            )
        return rows

    def _dispatch_clock_id(self, name: str) -> str:
        """Return the clock a signal is regular on: the device's own dispatch counter."""
        return f"{self.prefix}{name}.dispatch"

    def array_dimensions(self) -> list[dict[str, Any]]:
        """`core.array_dimensions`, one axis per signal, in R20 §2.1's regular form.

        Tick `k` is sample `k`. That is not an approximation: a HARP device schedules its
        dispatch on its own microsecond timer, accumulating rather than re-basing, so the
        samples are evenly spaced on that counter. What is *not* even is the HARP timestamp
        each message carries, because the timer and the timestamp count different oscillators,
        parts per million apart, which over a session reaches hundreds of ticks. R20 §2.1 puts
        exactly that difference in `core.clock_anchors` rather than in the axis.
        """
        return [
            {
                "array_asset_id": f"{self.prefix}{name}",
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
        rows = []
        for name in self.signals:
            ticks, _ = self._signal(name)
            span = int(ticks[-1] - ticks[0]) if len(ticks) > 1 else 0
            rate = (len(ticks) - 1) * self.clock.tick_rate_num / span if span else None
            rows.append(
                {
                    "clock_id": self._dispatch_clock_id(name),
                    "session_id": self.session_id,
                    # The float alone (Part 02 §12.4). This rate is measured from the dispatch
                    # spacing rather than declared, so a rational would be one the source never
                    # stated -- the rounding Part 02 §12.4 says this format does not do on a
                    # source's behalf. R95 §4 keeps the float expressible for exactly this: a
                    # rate someone measured is recorded as measured.
                    "tick_rate_hz": round(rate, 6) if rate else None,
                    "origin": "the device's first dispatched sample; tick k is sample k",
                    # `clock_name` is left for the numbering to fill from `clock_id` (Part 02 §8.2);
                    # what this counter is travels as a label, having no column of its own.
                    "metadata": {"label": f"{name} dispatch counter"},
                    "parent_clock_id": self.clock.clock_id,
                }
            )
        return rows

    def signal_anchors(self, every: int = 10_000) -> list[dict[str, Any]]:
        """`core.clock_anchors`, relating each dispatch counter to the reference clock.

        Every sample carries its own HARP timestamp, so every anchor here is measured and none
        is fitted. They are subsampled because they need only bound the interpolation error
        Part 01 §3.9 governs: at the parts per million separating the two oscillators, anchors
        tens of seconds apart leave far less than one tick between them, where the tolerance is
        3 ms.
        """
        rows = []
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


__all__ = ["Signals"]

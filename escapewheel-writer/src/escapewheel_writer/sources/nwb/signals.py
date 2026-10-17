"""An NWB file's continuously sampled acquisition streams, as arrays on their own dispatch clocks."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from ...errors import SourceDefect, SourceFault
from ..signals import SignalArrays
from .file import NWBFile
from .names import ucum_code


class Signals(NWBFile, SignalArrays):
    """The streams a recipe declares signals, each read from `acquisition/<name>`."""

    def signal_device_id(self, name: str) -> str | None:
        """Return the instrument that made a stream; None, since base NWB links it to no Device."""
        return None

    def signal_unit(self, name: str) -> str | None:
        """Return the UCUM unit of a stream's `data`."""
        return ucum_code(str(self.attrs(f"acquisition/{name}/data").get("unit") or "") or None)

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


__all__ = ["Signals"]

"""Harp devices and their register streams, read from the acquisition directories each device writes.

- :class:`HarpSource` -- `core.devices`, one row per Harp device found under a root, and each
  register the recipe declares a signal as an array on its dispatch clock.
- :data:`SCHEMA` -- the name of the schema file.
- :data:`FIELDS` -- the fields this adapter reads from a device schema.

Registers are decoded by `harp-python`, the Harp project's own reader.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from escapewheel_reader.resource_ids import (
    CORE_ARRAY_ASSETS,
    CORE_ARRAY_DIMENSIONS,
    CORE_CLOCK_ANCHORS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_DEVICES,
)
from numpy.typing import NDArray

from ..clock import HARP_TICK_RATE_HZ, TickGrid
from ..errors import SourceDefect, SourceFault, UsageError, UsageFault
from ..notes import Note, NoteCode
from .signals import SignalArrays
from .store import source_root


def _clean(value: Any) -> str | None:
    """Return a schema value as the string a column takes, or None where the schema omitted it."""
    return None if value is None else str(value)


def _snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


#: The schema file the Harp protocol puts beside a device's data.
SCHEMA = "device.yml"

#: What a device schema is asked for. `whoAmI` is the Harp device *type* -- 1401 is a sniff
#: detector, whatever this one is called -- so it belongs with the model rather than the serial.
FIELDS = ("device", "whoAmI", "firmwareVersion", "hardwareTargets", "registers")

#: Harp protocol payload types, as the schema spells them.
_DTYPES = {
    "U8": np.uint8,
    "S8": np.int8,
    "U16": np.uint16,
    "S16": np.int16,
    "U32": np.uint32,
    "S32": np.int32,
    "U64": np.uint64,
    "S64": np.int64,
    "Float": np.float32,
}


class HarpSource(SignalArrays):
    """`core.devices`, one row per Harp device found under `root`, and its declared signals.

    Parameters
    ----------
    root : str or Path
        A directory holding Harp acquisition directories, or one such directory itself. Each is
        recognised by the `device.yml` inside it.
    session_id : str
        The session these devices were used in.
    reference_clock : mapping, optional
        The `core.clocks` row Harp timestamps are converted onto; its grid must hold every
        Harp tick. Needed only for `signals`; a build always supplies it.
    prefix : str, optional
        Prepended to every device ID and name, and to every signal's array ID.
    signals : sequence of str, optional
        Registers to read as signals, by the name a device schema gives them. Each becomes the
        array `<device>_<register>` in snake case, on its own dispatch clock.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    """

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset(
        {
            CORE_DEVICES,
            CORE_CLOCKS,
            CORE_CLOCK_ANCHORS,
            CORE_CLOCK_OBSERVATION_INTERVALS,
            CORE_ARRAY_ASSETS,
            CORE_ARRAY_DIMENSIONS,
        }
    )

    #: Part 05 §3.4: what of `PRODUCES` this adapter supplies only part of, which a source entry
    #: without `owns` contributes rather than owns.
    CONTRIBUTES = PRODUCES

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply, resolved against Part 12 §4's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    #:
    #: An option the adapter can run without is left out: a declared name a recipe does not set
    #: resolves to nothing, so declaring one makes it mandatory.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "reference_clock")

    #: Part 05 §3.4: options this adapter reads and can run without (Part 12 §4).
    ACCEPTS: ClassVar[tuple[str, ...]] = ("prefix", "signals", "source_cache")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        reference_clock: Mapping[str, Any] | None = None,
        prefix: str = "",
        signals: Sequence[str] = (),
        source_cache: str | None = None,
    ) -> None:
        self.root = source_root(root, cache=source_cache)
        self.session_id = session_id
        if reference_clock is not None:
            if reference_clock.get("session_id") != session_id:
                raise UsageError(
                    f"clock {reference_clock.get('clock_id')!r} belongs to session "
                    f"{reference_clock.get('session_id')!r}, not {session_id!r}",
                    code=UsageFault.CLOCK_OTHER_SESSION,
                    where=str(reference_clock.get("clock_id")),
                )
            self.clock = TickGrid.from_row(reference_clock)
        elif signals:
            raise UsageError(
                f"signals {', '.join(signals)} were asked for with no reference clock to put their ticks on",
                code=UsageFault.SIGNALS_WITHOUT_CLOCK,
                where=str(root),
            )
        self.prefix = prefix
        self.signals = tuple(signals)
        self._signals: dict[str, tuple[NDArray[np.int64], NDArray[Any]]] = {}
        self._registers: dict[str, tuple[str, Any]] = {}
        self.notes: list[str] = []

    def schemas(self) -> list[Path]:
        """Every `device.yml` under `root`, sorted.

        A session restarted mid-recording writes one acquisition directory per run, each with an
        identical schema; :meth:`devices` counts the device once however many times it was started.
        """
        found = [self.root / SCHEMA] if (self.root / SCHEMA).is_file() else []
        found += sorted(p / SCHEMA for p in sorted(self.root.iterdir()) if (p / SCHEMA).is_file())
        return found

    def _read(self, path: Path) -> dict[str, Any]:
        """Parse one device schema, keeping only what this adapter reads."""
        import yaml

        parsed = yaml.safe_load(path.read_text()) or {}
        return {field: parsed.get(field) for field in FIELDS}

    def devices(self) -> list[dict[str, Any]]:
        """`core.devices`, one row per distinct device declared under `root`."""
        rows: dict[str, dict[str, Any]] = {}
        for path in self.schemas():
            declared = self._read(path)
            name = declared.get("device")
            if not name:
                self.notes.append(Note(f"{path}: declares no device name; skipped", NoteCode.DEVICE_UNNAMED))
                continue
            if name in rows:
                continue
            rows[name] = {
                "device_id": self.prefix + str(name),
                "session_id": self.session_id,
                "device_name": self.prefix + str(name),
                # Harp is the bus, not the maker: a schema names neither a manufacturer nor a
                # serial, and inventing either would assert what nothing states.
                "manufacturer": None,
                "model": f"Harp {declared['whoAmI']}" if declared.get("whoAmI") is not None else None,
                # Part 01 §3.5: verbatim, unparsed. `hardwareTargets` is this schema's name for the
                # hardware the firmware targets, which is the revision the device reports.
                "firmware_version": _clean(declared.get("firmwareVersion")),
                "hardware_version": _clean(declared.get("hardwareTargets")),
                "serial_number": None,
                # whoAmI is on `model`; what remains is nothing, so the column stays empty rather
                # than restating what two typed columns carry.
                "metadata": None,
            }
        return [rows[name] for name in sorted(rows)]

    # -- signals ----------------------------------------------------------------------

    def _register(self, name: str) -> tuple[str, Path, int, Any]:
        """Return the device declaring register `name`, the one file holding it, its address and its dtype.

        A directory whose device declares the register but holds no messages for it -- a run
        stopped before it started streaming -- is passed over; two that hold some are a
        restarted recording, and which run the packet carries is the recipe's to choose by root.
        """
        held = []
        for path in self.schemas():
            declared = self._read(path)
            register = (declared.get("registers") or {}).get(name)
            if not declared.get("device") or not isinstance(register, dict):
                continue
            address = int(register["address"])
            files = [f for f in path.parent.iterdir() if f.name.endswith(f"_{address}.bin") and f.stat().st_size]
            held += [(str(declared["device"]), f, address, _DTYPES.get(str(register.get("type")))) for f in files]
        if not held:
            raise SourceDefect(
                f"the recipe declares signal {name!r} and no device under {self.root} records that register",
                code=SourceFault.SIGNAL_ABSENT,
                where=str(self.root),
            )
        if len(held) > 1:
            raise SourceDefect(
                f"register {name!r} is recorded in {len(held)} files under {self.root}: "
                f"{', '.join(str(h[1]) for h in held)}; point `root` at the one acquisition to read",
                code=SourceFault.SIGNAL_SPLIT,
                where=str(self.root),
            )
        return held[0]

    def _signal(self, name: str) -> tuple[NDArray[np.int64], NDArray[Any]]:
        """Return one register's event ticks on the reference clock and its values.

        Only `Event` messages are samples: a register file also logs the reads and writes that
        configured it. Memoized, since four tables need each signal and a file is every sample.
        """
        if name not in self._signals:
            import harp

            device, path, address, dtype = self._register(name)
            self._registers[name] = (device, path)
            frame = harp.read(path.read_bytes(), address=address, dtype=dtype, keep_type=True)
            if frame.index.name != "Time":
                raise SourceDefect(
                    f"{path}: register {name!r} carries no timestamps",
                    code=SourceFault.SIGNAL_ABSENT,
                    where=str(path),
                )
            events = frame[frame[harp.MessageType.__name__] == harp.MessageType.EVENT.name]
            payload = events.drop(columns=harp.MessageType.__name__).to_numpy()
            if payload.shape[1] != 1:
                raise SourceDefect(
                    f"{path}: register {name!r} carries {payload.shape[1]} values per message, "
                    "and a signal here is one value per sample",
                    code=SourceFault.ARRAY_RANK,
                    where=str(path),
                )
            # The float `harp` returns is within an ulp of an exact counter tick, so rounding
            # recovers the tick, and the nearest float to that tick is what the grid checks.
            harp_ticks = np.rint(events.index.to_numpy(dtype=np.float64) * HARP_TICK_RATE_HZ)
            self._signals[name] = (self.clock.ticks(harp_ticks / HARP_TICK_RATE_HZ), payload[:, 0])
        return self._signals[name]

    def signal_device_id(self, name: str) -> str | None:
        """Return the device whose schema declares the register."""
        self._signal(name)
        return self.prefix + self._registers[name][0]

    def signal_array_id(self, name: str) -> str:
        """Return `<prefix><device>_<register>`, the two names in snake case as resource names are."""
        self._signal(name)
        return f"{self.prefix}{_snake(self._registers[name][0])}_{_snake(name)}"

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource this root holds."""
        return {resource: len(rows) for resource, rows in self.records().items()}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        built = {
            CORE_DEVICES: self.devices(),
            CORE_CLOCKS: self.signal_clocks(),
            CORE_CLOCK_ANCHORS: self.signal_anchors(),
            CORE_CLOCK_OBSERVATION_INTERVALS: self.signal_observation_intervals(),
            CORE_ARRAY_ASSETS: self.array_assets(),
            CORE_ARRAY_DIMENSIONS: self.array_dimensions(),
        }
        return {resource: rows for resource, rows in built.items() if rows}


__all__ = ["FIELDS", "SCHEMA", "HarpSource"]

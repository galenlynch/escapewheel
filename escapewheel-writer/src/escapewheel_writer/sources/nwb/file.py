"""An opened NWB-Zarr file: its arrays, attributes and tables, and its times as ticks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import NDArray

from ...clock import TickGrid, zone_of
from ...errors import SourceDefect, SourceFault, UnsupportedEncoding, UsageError, UsageFault
from ...notes import Note, NoteCode
from ..compensations import Compensates
from ..store import SourceStore, source_root
from ..values import utc_offset as _offset
from .names import one


def _resolve(root: Path) -> Path:
    """Accept either the ``.nwb`` directory or the asset directory holding one."""
    if (root / ".zgroup").is_file():
        return root
    candidates = sorted(child for child in root.iterdir() if child.suffix == ".nwb" and child.is_dir())
    if len(candidates) == 1:
        return candidates[0]
    raise SourceDefect(
        f"{root} is not an NWB-Zarr directory and holds {len(candidates)} of them",
        code=SourceFault.NO_ONE_NWB,
        where=str(root),
    )


class NWBFile(Compensates):
    """The file and the state every group of an `NWBSource`'s tables reads; `NWBSource` documents the parameters."""

    def __init__(
        self,
        root: str | Path,
        *,
        reference_clock: Mapping[str, Any],
        zone: str | ZoneInfo,
        session_id: str | None = None,
        prefix: str = "",
        trial_metadata: bool = True,
        units: Sequence[Mapping[str, Any]] = (),
        signals: Sequence[str] = (),
        interval_kind: str | None = None,
        emit_clock: bool = True,
        attachments: str | Path | None = None,
        store: Any = None,
        source_cache: str | None = None,
    ) -> None:
        zone = zone_of(zone)
        self.root = _resolve(source_root(root, cache=source_cache))
        # Part 01 §3.10: an interval declares the resource that says what it was, and this adapter
        # cannot know it -- an exported trials table is the task's, and which task it is is a
        # fact about the session rather than about the file, so the recipe names it.
        self.interval_kind = interval_kind
        self.store = store if store is not None else SourceStore(self.root)
        # The row is kept to emit as `core.clocks` where the recipe asks; the grid is what
        # converts, and is all the row can rebuild: a row carries no label, `clock_name` being
        # what `clock_id` stands for (Part 02 §8.2).
        self.clock_row = dict(reference_clock)
        self.clock = TickGrid.from_row(reference_clock)
        self.zone = zone
        self.prefix = prefix
        self.trial_metadata = trial_metadata
        #: Where the acquisition records which headstage each probe was in (Part 01 §3.5). The NWB
        #: does not say, and the file that does joins on `custom_probe_name`, which is the name
        #: the NWB gives its Device -- so this reads one extra file for one column rather than
        #: needing a source to write into another source's rows.
        self.attachments = Path(attachments) if attachments else None
        #: Acquisition streams that are signals rather than events, named by the recipe. A
        #: continuously sampled quantity is an array with a time axis, not one row per sample
        #: carrying its value in JSON, which Part 02 §6 confines to optional columns. Declared
        #: rather than inferred: whether a stream is a signal is a fact about the instrument, not
        #: about how many distinct values one session happened to record.
        self.signals = tuple(signals)
        self._signals: dict[str, tuple[NDArray[np.int64], NDArray[Any]]] = {}
        #: Whether to emit the reference clock. False where the sync source declares it,
        #: since both emitting it puts two rows under one clock_id.
        self.emit_clock = emit_clock
        #: Unmapped trial columns found constant across the session, filled in by `trials`.
        self._constants: dict[str, Any] = {}
        #: The build's unit identity, keyed by the pair this file joins on. A collection crosses
        #: as records (Part 12 §4), so the lookup is built here rather than handed over: a
        #: mapping keyed by a pair does not survive the crossing at all.
        self.units = {(str(row["device_name"]), str(row["local_unit_label"])): row["unit_id"] for row in units}
        Compensates.__init__(self)
        self.notes: list[str] = []
        self._cache: dict[str, Any] = {}
        self.session_id = session_id or one(self._array("general/session_id")) or self.root.stem
        if self.clock_row.get("session_id") != self.session_id:
            raise UsageError(
                f"clock {self.clock.clock_id!r} belongs to session "
                f"{self.clock_row.get('session_id')!r}, not {self.session_id!r}",
                code=UsageFault.CLOCK_OTHER_SESSION,
                where=self.clock.clock_id,
            )

    # -- source access ----------------------------------------------------------------

    def _array(self, path: str) -> NDArray[Any]:
        """Read one array, or an empty one if it is absent."""
        if not self.store.is_array(path):
            return np.empty(0)
        return self.store.array(path)

    def attrs(self, path: str = "") -> dict[str, Any]:
        """Read one node's attributes."""
        return self.store.attrs(path)

    def table(self, path: str) -> dict[str, NDArray[Any]]:
        """Read an hdmf table's row-aligned columns, skipping any this package will not decode.

        **A column an `<name>_index` declares ragged is not read.** Its rows are runs rather
        than values, so indexing it by a table row -- which is what every caller here does --
        is wrong for all but the first row; a caller that wants one reads it alongside its index.
        It is also where the bytes are: `units/spike_times` holds every spike of the session
        against the table's one row per unit, and decoding it would be most of what this
        adapter reads.

        Cached: a table is consulted by more than one builder, and re-reading it would
        repeat every note it produced.
        """
        if path in self._cache:
            cached: dict[str, NDArray[Any]] = self._cache[path]
            return cached
        node = self.root / path
        out: dict[str, NDArray[Any]] = {}
        if node.is_dir():
            names = self.store.members(path)
            ragged = {name.removesuffix("_index") for name in names if name.endswith("_index")}
            for name in names:
                if name in ragged or not self.store.is_array(f"{path}/{name}"):
                    continue
                try:
                    out[name] = self.store.array(f"{path}/{name}")
                except UnsupportedEncoding as refused:
                    self.notes.append(
                        Note(f"{path}/{name}: not read; {str(refused).rsplit('/', 1)[-1]}", NoteCode.COLUMN_NOT_READ)
                    )
        self._cache[path] = out
        return out

    # -- time -------------------------------------------------------------------------

    def _instant(self, raw: str | None, label: str) -> datetime | None:
        """Parse a stored wall-clock value, checking its offset against the declared zone.

        The check is worth making because both failure modes are real and silent: a source may
        stamp `+00:00` on a local wall clock, and one converting a date without a timezone
        database stamps a Local Mean Time offset such as `-07:53`. The stored value is kept
        either way -- overriding it would be a second guess on top of the first -- but it is
        reported.
        """
        if raw is None:
            return None
        value = datetime.fromisoformat(raw)
        expected = value.replace(tzinfo=self.zone).utcoffset()
        if value.tzinfo is None:
            self.notes.append(Note(f"{label}: no offset stored; read as {self.zone.key}", NoteCode.OFFSET_ASSUMED))
            return value.replace(tzinfo=self.zone)
        if value.utcoffset() != expected:
            self.compensate("nwb.stored_offset_kept")
            self.notes.append(
                Note(
                    f"{label}: stored offset {_offset(value.utcoffset())} disagrees with "
                    f"{self.zone.key}'s {_offset(expected)} for {value.replace(tzinfo=None).isoformat()}; "
                    "kept as stored",
                    NoteCode.OFFSET_KEPT,
                )
            )
        return value

    def _ticks(self, seconds: NDArray[Any], label: str) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
        """Quantize seconds to ticks, dropping non-finite values and saying how many.

        Cached by label, so `notes` is a property of the source rather than of how many times
        a caller happened to read it. Without this, calling `events()` twice reports every
        dropped placeholder twice.
        """
        key = f"ticks:{label}"
        if key in self._cache:
            cached: tuple[NDArray[np.int64], NDArray[np.bool_]] = self._cache[key]
            return cached
        finite = np.isfinite(seconds)
        if not finite.all():
            self.notes.append(
                Note(
                    f"{label}: {int((~finite).sum())} of {finite.size} timestamps not finite; dropped",
                    NoteCode.TIMESTAMPS_DROPPED,
                )
            )
        converted = (self.clock.ticks(seconds[finite]), finite)
        self._cache[key] = converted
        return converted


__all__ = ["NWBFile"]

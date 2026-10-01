"""`core.event_streams`, `core.events` and `core.intervals` from an NWB file's acquisition and trials."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, ClassVar

import numpy as np
from escapewheel_reader.resource_ids import (
    CORE_INTERVALS,
)
from numpy.typing import NDArray

from ...errors import SourceDefect, SourceFault
from .file import NWBFile
from .names import alike, clean


class Events(NWBFile):
    """The moments an NWB file records, on acquisition streams and in trial columns, and its trials."""

    #: Trial columns that are *events*, and the type each becomes. A task writes these into the
    #: trials table because they happen once a trial, but a moment on a clock is an event whatever
    #: table it arrives in. `TimeIntervals` declares `start_time`, `stop_time` and tags alone, so
    #: every such column is a task's own and a dialect names them.
    TRIAL_EVENTS: ClassVar[dict[str, str]] = {}

    #: Trial columns this adapter accounts for; the rest go to `core.intervals.metadata` verbatim.
    #: A dialect widens this with the task columns it maps, which is what keeps them out of the bag
    #: rather than swept in as unmapped.
    TRIAL_MAPPED: ClassVar[frozenset[str]] = frozenset({"start_time", "stop_time"})

    def _series(self) -> Iterator[tuple[str, NDArray[Any], NDArray[Any]]]:
        """Yield each acquisition TimeSeries as (name, timestamps, data)."""
        acquisition = self.root / "acquisition"
        if not acquisition.is_dir():
            return
        for name in self.store.members("acquisition"):
            if name in self.signals or not self.store.is_array(f"acquisition/{name}/timestamps"):
                continue
            yield (
                name,
                self.store.array(f"acquisition/{name}/timestamps"),
                self._array(f"acquisition/{name}/data"),
            )

    def event_streams(self) -> list[dict[str, Any]]:
        """`core.event_streams`, one row per acquisition TimeSeries.

        `processing_run_id` is null, which R23 §4 defines as *came off the device as
        recorded*: an acquisition TimeSeries is what the rig detected and logged online.

        `event_type` is the stream's, not the event's (R91 §3.1), and it is the source's field
        name normalised -- `left_lick_time` becomes `left_lick`. Nothing derives it at read time:
        this is the writer stating what kind of event the stream emits.
        """
        rows = []
        for name, _, _ in self._series():
            rows.append(
                {
                    "event_stream_id": self.prefix + name,
                    "session_id": self.session_id,
                    "event_stream_name": self.prefix + name,
                    "event_type": name.removesuffix("_time"),
                    "clock_id": self.clock.clock_id,
                    "metadata": {"description": self.attrs(f"acquisition/{name}").get("description")},
                }
            )
        for column, kind in self._trial_event_columns():
            rows.append(
                {
                    "event_stream_id": self.prefix + kind,
                    "session_id": self.session_id,
                    "event_stream_name": self.prefix + kind,
                    "event_type": kind,
                    "clock_id": self.clock.clock_id,
                    "metadata": {"description": f"intervals/trials/{column}, one per trial"},
                }
            )
        return rows

    def _trial_event_columns(self) -> list[tuple[str, str]]:
        """Trial columns that carry a moment, in the order `TRIAL_EVENTS` names them."""
        columns = self.table("intervals/trials")
        return [(name, kind) for name, kind in self.TRIAL_EVENTS.items() if name in columns]

    def events(self) -> list[dict[str, Any]]:
        """`core.events`, one row per timestamp on an acquisition TimeSeries.

        An event is a tick on a stream (R91 §3.2): no identifier, no name, and no type of its
        own, the type being the stream's. The row is traceable back to the NWB through its
        stream, which carries the source's field name.
        """
        rows = []
        for name, seconds, data in self._series():
            ticks, finite = self._ticks(seconds, f"acquisition/{name}")
            payloads = data[finite] if data.size == seconds.size else None
            # `data` is commonly a constant marker, and a copy of it per event would be noise,
            # so it travels only when it varies.
            varies = payloads is not None and payloads.size > 0 and len(np.unique(payloads)) > 1
            for position, tick in enumerate(ticks):
                row: dict[str, Any] = {
                    "session_id": self.session_id,
                    "stream_id": self.prefix + name,
                    "t_tick": int(tick),
                }
                if varies and payloads is not None:
                    row["payload"] = {"value": clean(payloads[position])}
                rows.append(row)
        rows.extend(self._trial_events())
        return rows

    def _trial_events(self) -> list[dict[str, Any]]:
        """`core.events` for the moments a task recorded as trial columns.

        A trial that did not reach one -- no go cue because the animal never engaged -- has NaN
        there, and no event happened, so no row is emitted. That is why these cannot simply be
        columns on `core.trials`: absence is a fact about the trial, not a null to carry.
        """
        columns = self.table("intervals/trials")
        if not columns:
            return []
        rows = []
        for column, kind in self._trial_event_columns():
            ticks, _ = self._ticks(columns[column], f"intervals/trials/{column}")
            for tick in ticks:
                rows.append(
                    {
                        "session_id": self.session_id,
                        "stream_id": self.prefix + kind,
                        "t_tick": int(tick),
                        # No payload naming the interval: as JSON the reference would be untyped,
                        # unjoinable, and invisible to every check. An event belongs to whatever
                        # intervals contain it, which may be none or several, and containment is
                        # a query against `core.intervals` rather than a column (R11 §5, R54 §3).
                    }
                )
        return rows

    def intervals(self) -> list[dict[str, Any]]:
        """`core.intervals`, one row per trial (Part 01 §3.10)."""
        if self.interval_kind is None:
            raise SourceDefect(
                "core.intervals needs an interval_kind naming the resource that specialises these "
                "intervals (Part 01 §3.10); set it on the nwb source",
                code=SourceFault.NO_INTERVAL_KIND,
                where=CORE_INTERVALS,
            )
        columns = self.table("intervals/trials")
        if not columns:
            return []
        for required in ("start_time", "stop_time"):
            if required not in columns:
                raise SourceDefect(
                    f"intervals/trials has no {required}",
                    code=SourceFault.TRIAL_COLUMN_ABSENT,
                    where=f"intervals/trials/{required}",
                )
        for edge in ("start_time", "stop_time"):
            if not np.isfinite(columns[edge]).all():
                missing = int((~np.isfinite(columns[edge])).sum())
                raise SourceDefect(
                    f"intervals/trials: {missing} trials have no {edge}, so they are not intervals",
                    code=SourceFault.TRIAL_EDGE_MISSING,
                    where=f"intervals/trials/{edge}",
                )
        start = self.clock.ticks(columns["start_time"])
        stop = self.clock.ticks(columns["stop_time"])
        identifiers = columns.get("id", np.arange(len(start)))
        unmapped = [name for name in columns if name not in self.TRIAL_MAPPED and name != "id"]
        varying = self._trial_parameters(columns, unmapped, len(start))
        rows = []
        for index in range(len(start)):
            label = str(int(identifiers[index]))
            row: dict[str, Any] = {
                "session_id": self.session_id,
                "interval_kind": self.interval_kind,
                # The NWB numbers only its trials, so its `id` is a label and the name carries the
                # session and kind that make it unique in the packet (Part 02 §8.2).
                "interval_id": f"{self.prefix}{self.session_id}/{self.interval_kind}/{label}",
                "local_interval_label": label,
                "start_tick": int(start[index]),
                "stop_tick": int(stop[index]),
                "clock_id": self.clock.clock_id,
            }
            # Part 02 §8.6: only what no column holds. A recipe turns this off where an extension
            # declares the varying keys as typed columns.
            if self.trial_metadata and varying:
                row["metadata"] = {name: columns[name][index] for name in varying}
            rows.append(row)
        return rows

    def _trial_parameters(self, columns: Mapping[str, NDArray[Any]], unmapped: list[str], n: int) -> list[str]:
        """Split unmapped trial columns into what varies per trial and what does not.

        A task parameter that never changes across a session is not trial data; recording it on
        every trial restates one fact `n` times, which Part 02 §5.2 forbids for the same reason a
        repeated value becomes a child table.

        The constant ones are held for `sessions` to carry, and the varying names returned. This
        is a split, not a judgement about which matter: a constant may be the most important
        thing about the session, and it is still recorded once.
        """
        constant: dict[str, Any] = {}
        varying: list[str] = []
        for name in unmapped:
            values = columns[name]
            first = values[0] if n else None
            # One trial is no evidence of constancy, so nothing moves: with nothing to
            # compare against, calling a value a session parameter claims more than is known.
            same = n > 1 and all(alike(values[i], first) for i in range(1, n))
            if same:
                constant[name] = first
            else:
                varying.append(name)
        self._constants = constant
        return varying


__all__ = ["Events"]

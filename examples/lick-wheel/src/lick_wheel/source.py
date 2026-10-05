"""One session of a lick-and-wheel task, as the core tables and one packet-owned array.

The rig records on a HARP clock. A lick sensor and a reward valve write events in HARP seconds to
`events.csv`; a wheel encoder samples at 250 Hz on its own counter and stamps each sample with the
HARP time it arrived at, in `wheel.csv`. `session.json` names the subject and the span the rig
recorded over.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from escapewheel_writer.adapter import FILES, STREAM, Clock, Note, SourceDefect, StagedArray, source_root

#: The wheel encoder's own sampling rate, which is its counter's: tick k is sample k.
WHEEL_HZ = 250

#: One anchor per this many wheel samples, plus the last. The encoder's oscillator and HARP's
#: differ by tens of parts per million, which a second between anchors keeps far under a tick.
ANCHOR_EVERY = WHEEL_HZ

#: Each event the source writes, and the stream it belongs to. A stream emits one kind of event.
STREAMS = {"lick": "lick_sensor", "reward": "reward_valve"}

#: The array this adapter stages, by its name in the packet.
WHEEL = "wheel_position"

CLOCKS, OBSERVED, ANCHORS = "core.clocks", "core.clock_observation_intervals", "core.clock_anchors"
DEVICES, EVENT_STREAMS, EVENTS = "core.devices", "core.event_streams", "core.events"
STREAM_OBSERVED = "core.event_stream_observation_intervals"
ASSETS, DIMENSIONS = "core.array_assets", "core.array_dimensions"


class LickWheelSource:
    """The licks, rewards and wheel of one session under `root`.

    Parameters
    ----------
    root : str or Path
        The session directory, local or a store URI, holding `session.json`, `events.csv` and,
        where the wheel was recorded, `wheel.csv`.
    session_id : str
        The session these were recorded in.
    reference_clock : Mapping
        The `core.clocks` row of the HARP clock every time in the source is in seconds of.
    array_location : str, optional
        Where the wheel array goes when this adapter is delivered out of process. Unread here:
        `escapewheel deliver` writes what `staged_arrays` returns there.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    """

    #: Both protocols a build can reach a released adapter by without a socket; `escapewheel
    #: deliver` serves either, and the first is what a recipe naming none gets (Part 12 §3).
    PROTOCOLS: ClassVar[tuple[str, ...]] = (STREAM, FILES)

    PRODUCES = frozenset(
        {CLOCKS, OBSERVED, ANCHORS, DEVICES, EVENT_STREAMS, EVENTS, STREAM_OBSERVED, ASSETS, DIMENSIONS}
    )

    #: Another source of the same session adds rows to every one of these: its own clocks, its
    #: devices, its streams. This adapter supplies its rows of each and owns none of them.
    CONTRIBUTES = PRODUCES

    #: The recipe field this source states, to the attribute holding the value. A build compares it
    #: with the recipe's `[subject]` and refuses a recipe naming another animal (Part 05 §3.6).
    STATES: ClassVar[dict[str, str]] = {"subject.subject_id": "subject_id"}

    #: `array_location` because the wheel crosses a process boundary as a Zarr array a build names
    #: the place for (Part 12 §5); in process the build supplies it too, and stages the values.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "reference_clock", "array_location")
    ACCEPTS: ClassVar[tuple[str, ...]] = ("source_cache",)

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        reference_clock: Mapping[str, Any],
        array_location: str | None = None,
        source_cache: str | None = None,
    ) -> None:
        # A local path or an opened store path; every read below goes through it, so the adapter
        # reads an object store as it reads a disk.
        self.root = source_root(root, cache=source_cache)
        self.session_id = session_id
        self.reference = dict(reference_clock)
        self.harp = Clock(
            clock_id=str(reference_clock["clock_id"]),
            session_id=session_id,
            name=str(reference_clock["clock_id"]),
            tick_rate_num=int(reference_clock["tick_rate_num"]),
            tick_rate_den=int(reference_clock.get("tick_rate_den") or 1),
            origin=str(reference_clock["origin"]),
        )
        self.wheel_clock = Clock(
            clock_id="wheel",
            session_id=session_id,
            name="wheel encoder sample counter",
            tick_rate_num=WHEEL_HZ,
            origin="the encoder's first sample of the session; tick k is sample k",
            parent_clock_id=self.harp.clock_id,
        )
        self.notes: list[str] = []
        if not (self.root / "wheel.csv").exists():
            self.notes.append(Note(f"{self.root} holds no wheel.csv: the wheel was not recorded"))

    def _read(self, name: str) -> str:
        path = self.root / name
        if not path.exists():
            raise SourceDefect(f"{self.root} holds no {name}", code="lick_wheel.file_absent", where=str(path))
        return str(path.read_text())

    @cached_property
    def stated(self) -> dict[str, Any]:
        """`session.json`, which names the subject and the recorded span in HARP seconds."""
        return dict(json.loads(self._read("session.json")))

    @property
    def subject_id(self) -> str | None:
        """The subject the source names, which `STATES` offers the build to check."""
        return self.stated.get("subject_id")

    @cached_property
    def events(self) -> list[dict[str, str]]:
        """Each row of `events.csv`, in the order the rig wrote them."""
        return list(csv.DictReader(io.StringIO(self._read("events.csv"))))

    @cached_property
    def wheel(self) -> tuple[np.ndarray, np.ndarray] | None:
        """Each wheel sample's HARP tick and position in degrees, or None where none was recorded."""
        if not (self.root / "wheel.csv").exists():
            return None
        rows = list(csv.DictReader(io.StringIO(self._read("wheel.csv"))))
        seconds = np.array([float(row["harp_seconds"]) for row in rows])
        position = np.array([float(row["position_deg"]) for row in rows], dtype=np.float32)
        # The HARP time a sample arrived at is on the HARP grid; converting refuses one that is not,
        # which is the loud failure a wrong reference clock deserves.
        return self.harp.ticks(seconds), position

    def recorded(self) -> tuple[int, int]:
        """The first and last HARP tick the rig recorded over."""
        start, stop = self.harp.ticks([self.stated["harp_start_seconds"], self.stated["harp_stop_seconds"]])
        return int(start), int(stop)

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Return every table this session has rows for, keyed by resource ID.

        Identifiers are the source's names; the build numbers them packet-wide (Part 12 §5).
        """
        if unknown := sorted({row["event"] for row in self.events} - STREAMS.keys()):
            raise SourceDefect(
                f"events.csv names events no stream emits: {', '.join(unknown)}", code="lick_wheel.event_unknown"
            )
        start, stop = self.recorded()
        session = {"session_id": self.session_id}
        ticks = self.harp.ticks([float(row["harp_seconds"]) for row in self.events])
        tables: dict[str, list[dict[str, Any]]] = {
            CLOCKS: [{**self.reference, **session}],
            # Every clock a row is timed on is observed over a window (Part 02 §12.5).
            OBSERVED: [{**session, "clock_id": self.harp.clock_id, "start_tick": start, "stop_tick": stop}],
            DEVICES: [{**session, "device_id": device} for device in STREAMS.values()],
            EVENT_STREAMS: [
                {
                    **session,
                    "event_stream_id": kind,
                    "event_type": kind,
                    "device_id": device,
                    "clock_id": self.harp.clock_id,
                }
                for kind, device in STREAMS.items()
            ],
            # A stream observed over the whole recording says that a stretch with no licks had none,
            # rather than that nobody was looking (Part 01 §2.3).
            STREAM_OBSERVED: [
                {**session, "event_stream_id": kind, "start_tick": start, "stop_tick": stop} for kind in STREAMS
            ],
            EVENTS: [
                {
                    **session,
                    "stream_id": row["event"],
                    "t_tick": int(tick),
                    # What one event carries beyond its moment is its payload, as JSON.
                    **({"payload": json.dumps({"volume_ul": float(row["volume_ul"])})} if row["volume_ul"] else {}),
                }
                for row, tick in zip(self.events, ticks, strict=True)
            ],
        }
        if self.wheel is not None:
            for name, rows in self._wheel_tables(*self.wheel).items():
                tables.setdefault(name, []).extend(rows)
        # A table with no rows is left out, and the build delivers it empty (Part 12 §5).
        return {name: rows for name, rows in tables.items() if rows}

    def _wheel_tables(self, arrived: np.ndarray, position: np.ndarray) -> dict[str, list[dict[str, Any]]]:
        """The wheel's catalog row, its time axis, and the anchors placing its clock on HARP's.

        The samples are evenly spaced on the encoder's counter and not on HARP, whose oscillator
        drifts against it, so the axis is regular on the wheel's own clock and the drift is what
        the anchors carry. A reader aligning the wheel to an event interpolates between them.
        """
        session = {"session_id": self.session_id}
        clock = self.wheel_clock.clock_id
        positions = list(range(0, len(arrived), ANCHOR_EVERY))
        if positions[-1] != len(arrived) - 1:
            positions.append(len(arrived) - 1)
        return {
            CLOCKS: [self.wheel_clock.record()],
            DEVICES: [{**session, "device_id": "wheel_encoder"}],
            ASSETS: [
                {
                    **session,
                    "array_asset_id": WHEEL,
                    # The packet resource the staged array becomes, which binds the two (Part 12 §5).
                    "resource_id": f"core.{WHEEL}",
                    "device_id": "wheel_encoder",
                    "clock_id": clock,
                    "sample_rate_hz": float(WHEEL_HZ),
                    "unit": "deg",
                }
            ],
            DIMENSIONS: [
                {
                    **session,
                    "array_asset_id": WHEEL,
                    "axis_index": 0,
                    "dimension_name": "time",
                    "clock_id": clock,
                    "origin_tick": 0,
                    "step_tick_num": 1,
                }
            ],
            OBSERVED: [{**session, "clock_id": clock, "start_tick": 0, "stop_tick": len(arrived) - 1}],
            ANCHORS: [
                {**session, "clock_id": clock, "anchor_index": index, "t_tick": at, "parent_tick": int(arrived[at])}
                for index, at in enumerate(positions)
            ],
        }

    def staged_arrays(self) -> list[StagedArray]:
        """The wheel's positions, which the packet owns as a Zarr array (Part 03 §6)."""
        if self.wheel is None:
            return []
        _, position = self.wheel
        return [
            StagedArray(
                values=position,
                resource_id=f"core.{WHEEL}",
                declaration_id="core.array_asset_instances",
                array_asset_id=WHEEL,
                # A chunk of a minute's samples is the unit a reader aligning to a trial fetches.
                chunks=(min(len(position), 60 * WHEEL_HZ),),
                codecs=("blosc",),
                # Stated here because a delivered array is written before any build reads the axes
                # rows that would otherwise name them (Part 03 §6.5).
                dimension_names=("time",),
            )
        ]

    def offers(self) -> dict[str, int]:
        """The rows of each table `records` supplies (Part 05 §4.1)."""
        return {name: len(rows) for name, rows in self.records().items()}

"""Read `aind-data-schema` metadata JSONs into records.

The JSONs carry two facts no data file in the asset records, and both are about time.

**When each acquisition ran.** `session.json` declares a window per data stream, in wall
clock. The NWB records when events happened, never when a sensor was watching, so this is
the only source for `core.event_stream_observation_intervals`. It matters because the
windows differ: on `inventory/nwb-zarr-776259-2025-04-09.md`'s session the ephys stream runs
6387 s and the behaviour stream 7849 s, and a reward rate computed against the wrong one is
wrong by 23%.

**Where tick zero sits.** A HARP clock free-runs from device power-on, so its tick 0 is a
power-on instant rather than a protocol constant -- 1.157e7 s before this session, 6.7e6 s
before one on another rig. Nothing in the NWB locates it: its `timestamps_reference_time`
claims to and is wrong, equalling `session_start_time` while the timestamps are HARP-epoch,
which places the first lick 134 days after the session. A stream's declared start, paired
with a tick observed at that start, locates it. See :meth:`SessionSource.epoch`.

The stored offsets are not trusted
----------------------------------

`session.json` stamps `+00:00` on Pacific wall-clock readings -- a seven-hour error on the
session this was built from, which `05` would import silently. The naive reading is right in
every stream checked, including the ones whose offset is right, so this adapter drops the
stored offset and localizes to the declared zone. Every disagreement is reported.

That is the opposite of what :class:`~nwb_lake_writer.sources.nwb.NWBSource` does with a bad
offset, and the difference is the defect. `+00:00` on a local reading is correctable, because
the reading survives. `-07:53` on a date of birth -- Pacific Local Mean Time -- is not: there
is nothing to re-localize a date to.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..clock import Clock, epoch_from
from .compensations import Compensates
from .nwb import SourceDefect, _offset

#: `session.json`'s own name for the file, used to accept either it or its directory.
SESSION_JSON = "session.json"


@dataclass(frozen=True)
class AcquisitionStream:
    """One `session.json` data stream, with its window resolved into the rig's zone.

    Attributes
    ----------
    index : int
        0-based offset into `data_streams`, carried so a note can identify the stream a
        finding came from. It is an offset, not a position; nothing displays it bare.
    start, stop : datetime
        The window, offset-aware, in the rig's zone.
    modalities : tuple of str
        Declared modality abbreviations. Empty on the ephys stream in real files, which is
        why :meth:`SessionSource.ephys` keys on `ephys_modules` instead.
    ephys : bool
        Whether the stream declares `ephys_modules`.
    """

    index: int
    start: datetime
    stop: datetime
    modalities: tuple[str, ...]
    ephys: bool

    @property
    def duration(self) -> timedelta:
        """How long the stream ran."""
        return self.stop - self.start


class SessionSource(Compensates):
    """An asset's `session.json`, read against a declared zone.

    Parameters
    ----------
    root : str or Path
        `session.json` itself, or a directory holding one.
    zone : zoneinfo.ZoneInfo
        The rig's wall-clock zone. An IANA zone, not a fixed offset: this session is PDT and
        the HARP epoch its ticks count from is PST, so a rig constant is wrong half the year.
    session_id : str, optional
        Overrides the ID derived from the asset directory name.

    Attributes
    ----------
    notes : list of str
        What was overridden or found inconsistent. A stored offset that disagrees with the
        zone appears here; so does an epoch derivation, since it is not a declared fact.

    Examples
    --------
    >>> source = SessionSource(asset, zone=ZoneInfo("America/Los_Angeles"))  # doctest: +SKIP
    >>> harp = source.clock(clock_id="harp", at_tick=first_spike_tick)  # doctest: +SKIP
    >>> source.observation_intervals(harp, ["left_lick_time"])  # doctest: +SKIP
    """

    def __init__(self, root: str | Path, *, zone: ZoneInfo, session_id: str | None = None) -> None:
        if not isinstance(zone, ZoneInfo):
            raise TypeError(f"{zone!r} is a fixed offset; pass an IANA zone so DST resolves per date")
        path = Path(root)
        self.path = path if path.is_file() else path / SESSION_JSON
        if not self.path.is_file():
            raise SourceDefect(f"{path} holds no {SESSION_JSON}")
        self.zone = zone
        Compensates.__init__(self)
        self.notes: list[str] = []
        self._streams: list[AcquisitionStream] | None = None
        self._document: dict[str, Any] = json.loads(self.path.read_text())
        self.session_id = session_id or self.path.parent.name

    # -- time -------------------------------------------------------------------------

    def _instant(self, raw: str, label: str) -> datetime:
        """Read a wall-clock value as local time in the declared zone, whatever it claims.

        The stored offset is discarded rather than checked, because on this schema it is
        wrong often enough to be useless as a signal and the naive reading is right. A
        disagreement is reported, not resolved in the file's favour.
        """
        value = datetime.fromisoformat(raw)
        self.compensate("aind.stored_offset_distrusted")
        localized = value.replace(tzinfo=self.zone)
        if value.tzinfo is not None and value.utcoffset() != localized.utcoffset():
            self.notes.append(
                f"{label}: stored offset {_offset(value.utcoffset())} replaced with "
                f"{self.zone.key}'s {_offset(localized.utcoffset())} for {value.replace(tzinfo=None).isoformat()}"
            )
        return localized

    # -- streams ----------------------------------------------------------------------

    def streams(self) -> list[AcquisitionStream]:
        """Every declared data stream, in file order.

        Cached, so `notes` is a property of the file rather than of how many times a caller
        read it: deriving a clock and then asking for a window would otherwise report each
        replaced offset twice.
        """
        if self._streams is not None:
            return self._streams
        out = []
        for index, stream in enumerate(self._document.get("data_streams", [])):
            for required in ("stream_start_time", "stream_end_time"):
                if not stream.get(required):
                    raise SourceDefect(f"{self.path}: data_streams[{index}] has no {required}")
            modalities = tuple(m["abbreviation"] for m in stream.get("stream_modalities") or [] if isinstance(m, dict))
            out.append(
                AcquisitionStream(
                    index=index,
                    start=self._instant(stream["stream_start_time"], f"data_streams[{index}].stream_start_time"),
                    stop=self._instant(stream["stream_end_time"], f"data_streams[{index}].stream_end_time"),
                    modalities=modalities,
                    ephys=bool(stream.get("ephys_modules")),
                )
            )
        self._streams = out
        return out

    def _only(self, *, ephys: bool) -> AcquisitionStream:
        """Return the single stream on one side of the ephys split, or raise."""
        matching = [stream for stream in self.streams() if stream.ephys is ephys]
        if len(matching) != 1:
            kind = "ephys" if ephys else "non-ephys"
            raise SourceDefect(f"{self.path}: {len(matching)} {kind} data streams, expected exactly 1")
        return matching[0]

    def ephys(self) -> AcquisitionStream:
        """Return the stream that declares `ephys_modules`."""
        return self._only(ephys=True)

    def behavior(self) -> AcquisitionStream:
        """Return the stream that does not.

        Its declared modality is `behavior-videos`, but its `software` is the task controller
        that also drives the lick sensors and reward valves, so it is the behaviour
        acquisition window rather than a camera's.
        """
        return self._only(ephys=False)

    # -- the clock --------------------------------------------------------------------

    def epoch(
        self,
        at_tick: int,
        *,
        stream: AcquisitionStream | None = None,
        tick_rate_num: int,
        tick_rate_den: int = 1,
    ) -> datetime:
        """Locate tick 0, given a tick observed at a stream's declared start.

        The caller supplies the tick because no JSON contains one: on the NWB it is the
        first spike, whose offset from acquisition start is sub-second when hundreds of units
        are firing. The resulting uncertainty is that offset plus the JSON's whole-second
        quantization, about ±1 s, and it is not recorded anywhere in the packet -- which is
        why this is reported as a note rather than passed off as a declared fact.

        Verify it rather than trusting it. Placing a *different* stream's declared window on
        the resulting clock and checking that it contains that stream's observed events is an
        independent test, and `core.events.within_observation` performs exactly that check
        once the packet is written.

        Parameters
        ----------
        at_tick : int
            The tick observed at `stream`'s declared start.
        stream : AcquisitionStream, optional
            Which stream `at_tick` was observed in. Defaults to the ephys stream.
        tick_rate_num, tick_rate_den : int
            The clock's tick rate, in hertz.

        Returns
        -------
        datetime
            The UTC instant of tick 0.
        """
        anchor = self.ephys() if stream is None else stream
        instant = epoch_from(anchor.start, at_tick, tick_rate_num, tick_rate_den)
        self.notes.append(
            f"tick_zero_utc {instant.isoformat()} derived from data_streams[{anchor.index}] "
            f"start and tick {at_tick}; not declared by any source, ~1 s uncertain"
        )
        return instant

    def clock(
        self,
        *,
        clock_id: str,
        at_tick: int,
        tick_rate_num: int,
        tick_rate_den: int = 1,
        name: str | None = None,
        origin: str | None = None,
        stream: AcquisitionStream | None = None,
        epoch: datetime | None = None,
    ) -> Clock:
        """Build a clock, preferring a supplied `tick_zero_utc` to one derived here.

        A caller that can locate tick 0 from an instrument's own record should: this source's
        :meth:`epoch` pairs a wall clock with the first spike, and the JSON it reads rounds to
        the second. Where the caller passes one, nothing here is consulted and no compensation
        is claimed.

        Returns
        -------
        Clock
            Ready to hand to another adapter, and to write via `Clock.record()`.
        """
        instant = epoch or self.epoch(at_tick, stream=stream, tick_rate_num=tick_rate_num, tick_rate_den=tick_rate_den)
        return Clock(
            clock_id=clock_id,
            session_id=self.session_id,
            name=name or clock_id,
            tick_rate_num=tick_rate_num,
            tick_rate_den=tick_rate_den,
            origin=origin or "free-running device counter; tick 0 is a power-on instant, not the session start",
            tick_zero_utc=instant,
        )

    # -- tables -----------------------------------------------------------------------

    def observation_intervals(
        self,
        clock: Clock,
        event_stream_ids: list[str],
        *,
        stream: AcquisitionStream | None = None,
    ) -> list[dict[str, Any]]:
        """`core.event_stream_observation_intervals` for streams sharing one acquisition window.

        One interval per ID, all with the same window, because these streams come from a
        single acquisition: a stream with 46 rewards was watched exactly as long as one with
        2641 licks, and giving each its own range would make a rare event look frequent.

        The window is the declared one, never the extent of the events. Deriving it from the
        events makes `core.events.within_observation` vacuous by construction and biases every
        rate upward by excluding the silent head and tail.

        Parameters
        ----------
        clock : Clock
            The clock to place the window on. Needs `tick_zero_utc`.
        event_stream_ids : list of str
            The `core.event_streams` observed in this window, already prefixed by whatever
            adapter emitted them.
        stream : AcquisitionStream, optional
            Which acquisition window. Defaults to the behaviour stream.

        Returns
        -------
        list of dict
            One record per ID, or empty if none were given.
        """
        if not event_stream_ids:
            return []
        window = self.behavior() if stream is None else stream
        start = clock.tick_at(window.start)
        stop = clock.tick_at(window.stop)
        if stop < start:
            raise SourceDefect(f"{self.path}: data_streams[{window.index}] ends before it starts")
        return [
            {"event_stream_id": event_stream_id, "start_tick": start, "stop_tick": stop}
            for event_stream_id in event_stream_ids
        ]

    def extent(self) -> tuple[datetime, datetime]:
        """When the session began and ended, across every declared stream.

        The union, not one stream's window: acquisition is staggered -- here ephys starts
        first and behaviour runs 24 minutes past it -- and a session that ended when its
        first stream did would exclude data the packet holds.

        Returns
        -------
        tuple of datetime
            Earliest start and latest stop, in UTC.
        """
        windows = self.streams()
        if not windows:
            raise SourceDefect(f"{self.path}: no data_streams, so the session has no extent")
        return (
            min(w.start for w in windows).astimezone(timezone.utc),
            max(w.stop for w in windows).astimezone(timezone.utc),
        )

    def records(
        self,
        *,
        at_tick: int,
        clock_id: str,
        tick_rate_num: int,
        tick_rate_den: int = 1,
        name: str | None = None,
        origin: str | None = None,
        event_stream_ids: list[str] | None = None,
        epoch: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return the tables this source owns: the reference clock, and when each stream was watched.

        Both need a tick the JSON does not contain, so `at_tick` is the caller's to supply --
        a tick observed at the ephys stream's declared start, which is what locates tick 0.

        Parameters
        ----------
        at_tick : int
            The tick observed at the ephys stream's declared start.
        clock_id, tick_rate_num, tick_rate_den, name, origin
            The clock to build, as for :meth:`clock`.
        event_stream_ids : list of str, optional
            The `core.event_streams` observed in the behaviour window.
        epoch : datetime, optional
            `tick_zero_utc`, where the caller located it from something better than this
            source's JSON. Supplying it makes `at_tick` unused for the clock.

        Returns
        -------
        dict
            `core.clocks` and `core.event_stream_observation_intervals`.
        """
        built = self.clock(
            clock_id=clock_id,
            at_tick=at_tick,
            tick_rate_num=tick_rate_num,
            tick_rate_den=tick_rate_den,
            name=name,
            origin=origin,
            epoch=epoch,
        )
        if epoch is None:
            self.compensate("aind.tick_zero_from_stream_start")
        return {
            "core.clocks": [built.record()],
            "core.event_stream_observation_intervals": self.observation_intervals(built, list(event_stream_ids or [])),
        }


__all__ = ["SESSION_JSON", "AcquisitionStream", "SessionSource"]

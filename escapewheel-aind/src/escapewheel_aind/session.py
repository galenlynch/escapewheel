"""Read `aind-data-schema` metadata JSONs into records.

- :class:`SessionSource` -- reads `session.json` with the `rig.json` and `subject.json` beside it,
  and yields the subject, the calibrations, the reference clock's row and that clock's observation
  window.
- :class:`AcquisitionStream` -- one declared data stream, its window resolved into the rig's zone.

The adapter drops a stored UTC offset and localizes the reading to the declared zone, because this
schema may stamp `+00:00` on a local wall clock. It reports each replaced offset in `notes`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

from escapewheel_reader.resource_ids import (
    CORE_CALIBRATION_DEVICES,
    CORE_CALIBRATION_POINTS,
    CORE_CALIBRATIONS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_EVENT_STREAM_OBSERVATION_INTERVALS,
    CORE_SUBJECTS,
)
from escapewheel_writer.clock import Clock, epoch_from, zone_of
from escapewheel_writer.declaration import FILES, FLIGHT, STREAM
from escapewheel_writer.errors import SourceDefect
from escapewheel_writer.notes import Note
from escapewheel_writer.sources.compensations import Compensates
from escapewheel_writer.sources.store import source_root
from escapewheel_writer.sources.values import sex as _sex
from escapewheel_writer.sources.values import utc_offset as _offset

from .errors import AindFault
from .notes import AindNote

#: `session.json`'s own name for the file, used to accept either it or its directory.
SESSION_JSON = "session.json"
RIG_JSON = "rig.json"
SUBJECT_JSON = "subject.json"


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
    zone : str or zoneinfo.ZoneInfo
        The rig's wall-clock zone, named or resolved. An IANA zone, not a fixed offset: a session
        may fall in daylight time and the HARP epoch its ticks count from in standard time, so a
        rig constant is wrong half the year.
    session_id : str, optional
        Overrides the ID derived from the asset directory name.
    prefix : str, optional
        Prepended to every calibration ID and name, and to the device a calibration covers, which
        is an NWB source's device ID and carries the prefix that source was built with. The
        reference clock and the subject are not this adapter's to name, so they are left as given.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).

    Attributes
    ----------
    notes : list of str
        What was overridden or found inconsistent. A stored offset that disagrees with the
        zone appears here; so does an epoch derivation, since it is not a declared fact.

    Examples
    --------
    >>> source = SessionSource(asset, zone=zone, reference_clock=harp_row)  # doctest: +SKIP
    >>> source.records()["core.calibrations"]  # doctest: +SKIP
    >>> source.behavior().start  # doctest: +SKIP
    """

    #: Part 12 §3: released apart from the writer, so it declares its protocols. `escapewheel
    #: deliver` serves every one; the first is what a build reaches it by when a recipe names none.
    PROTOCOLS: ClassVar[tuple[str, ...]] = (STREAM, FILES, FLIGHT)

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    #: Static, so a recipe check reads it with nothing open -- `offers` counts rows and
    #: therefore needs the data.
    PRODUCES = frozenset(
        {
            CORE_CALIBRATION_DEVICES,
            CORE_CALIBRATION_POINTS,
            CORE_CALIBRATIONS,
            CORE_CLOCKS,
            # The window this source watched the reference clock over, which is the fact the
            # rows below are composed from: the streams watched in it are the NWB's, so the
            # build pairs the two (Part 05 §3.4 leaves a row to one source).
            CORE_CLOCK_OBSERVATION_INTERVALS,
            # Declared here because this is the source whose presence makes the resource
            # available, which is what ownership is settled from.
            CORE_EVENT_STREAM_OBSERVATION_INTERVALS,
            CORE_SUBJECTS,
        }
    )

    #: Part 05 §3.4: what of `PRODUCES` this adapter supplies only part of, which a source entry
    #: without `owns` contributes rather than owns.
    CONTRIBUTES = frozenset(
        {
            CORE_CLOCK_OBSERVATION_INTERVALS,
            CORE_CLOCKS,
        }
    )

    #: Part 05 §3.4: `session.json` names the subject and `subject.json` describes it, and the recipe
    #: may declare either by hand. A build compares each against what the recipe says and refuses
    #: only on `subject.subject_id`, which is the one fact a reader resolves across packets.
    STATES: ClassVar[dict[str, str]] = {
        # Both ends of the session, which this JSON declares per data stream and the recipe may
        # also carry. A build compares them and keeps this source's (Part 05 §3.6): a hand-typed
        # start transcribes the source's own derivation rather than competing with it.
        "session.session_start_time": "stated_session_start_time",
        "session.session_end_time": "stated_session_end_time",
        "subject.subject_id": "subject_id",
        "subject.species": "stated_species",
        "subject.sex": "stated_sex",
        "subject.genotype": "stated_genotype",
        "subject.date_of_birth": "stated_date_of_birth",
        "subject.strain": "stated_strain",
    }

    #: Part 05 §3.4: what a build must supply, resolved against Part 12 §4's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    #:
    #: An option the adapter can run without is left out: a declared name a recipe does not set
    #: resolves to nothing, so declaring one makes it mandatory.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "zone", "reference_clock")

    #: Part 05 §3.4: options this adapter reads and can run without (Part 12 §4).
    ACCEPTS: ClassVar[tuple[str, ...]] = ("prefix", "source_cache")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    #: `aind_nwb` rather than `nwb`: a kind is matched by name, and `session.order` raises on one
    #: the recipe does not declare, so an adapter pairs with the NWB reader it ships beside.
    CONSUMES: ClassVar[tuple[str, ...]] = ("sorter", "sync", "aind_nwb")

    def __init__(
        self,
        root: str | Path,
        *,
        zone: str | ZoneInfo,
        reference_clock: Mapping[str, Any],
        session_id: str | None = None,
        prefix: str = "",
        source_cache: str | None = None,
    ) -> None:
        zone = zone_of(zone)
        #: The reference clock's own row, emitted as given. A build locates `tick_zero_utc`
        #: from the record nodes' stamps, which are better than anything here (Part 12 §4);
        #: :meth:`epoch` is what derives one where a caller has nothing better.
        self.clock_row = dict(reference_clock)
        path = source_root(root, cache=source_cache)
        self.path = path if path.is_file() else path / SESSION_JSON
        if not self.path.is_file():
            raise SourceDefect(f"{path} holds no {SESSION_JSON}", code=AindFault.NO_SESSION_JSON, where=str(path))
        self.zone = zone
        self.prefix = prefix
        Compensates.__init__(self)
        self.notes: list[str] = []
        self._streams: list[AcquisitionStream] | None = None
        self._document: dict[str, Any] = json.loads(self.path.read_text())
        self._rig_document: dict[str, Any] | None = None
        self._subject_document: dict[str, Any] | None = None
        self.session_id = session_id or self.path.parent.name

    @property
    def stated_session_start_time(self) -> datetime:
        """When the earliest declared acquisition began, which is when the session did."""
        return self.extent()[0]

    @property
    def stated_session_end_time(self) -> datetime:
        """When the last declared acquisition ended, since acquisition is staggered."""
        return self.extent()[1]

    @property
    def subject_id(self) -> str | None:
        """The subject `session.json` names, for the recipe's declaration to be checked against.

        `core.subjects` is one of the few tables the recipe supplies outright (Part 05 §3.1), so
        nothing else in the build has a second opinion about which animal this is -- and a
        subject is exactly the identifier that must not be session-scoped, so a wrong one
        unifies with another packet's rather than colliding with it.
        """
        value = self._document.get("subject_id")
        return str(value) if value is not None else None

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
                Note(
                    f"{label}: stored offset {_offset(value.utcoffset())} replaced with "
                    f"{self.zone.key}'s {_offset(localized.utcoffset())} for {value.replace(tzinfo=None).isoformat()}",
                    AindNote.OFFSET_REPLACED,
                )
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
                    raise SourceDefect(
                        f"{self.path}: data_streams[{index}] has no {required}",
                        code=AindFault.STREAM_FIELD_ABSENT,
                        where=f"data_streams[{index}]",
                    )
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
            raise SourceDefect(
                f"{self.path}: {len(matching)} {kind} data streams, expected exactly 1",
                code=AindFault.NO_ONE_STREAM,
                where=str(self.path),
            )
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
        self.compensate("aind.tick_zero_from_stream_start")
        self.notes.append(
            Note(
                f"tick_zero_utc {instant.isoformat()} derived from data_streams[{anchor.index}] "
                f"start and tick {at_tick}; not declared by any source, ~1 s uncertain",
                AindNote.TICK_ZERO_DERIVED,
            )
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

    def watched(self) -> list[dict[str, Any]]:
        """`core.clock_observation_intervals`: when the behaviour acquisition watched the clock.

        One row, on the reference clock the build supplied, because that is what this JSON can
        say about it: the window is the declared one, never the extent of the events. Deriving
        it from the events makes `core.events.within_observation` vacuous by construction and
        biases every rate upward by excluding the silent head and tail.

        Returns
        -------
        list of dict
            The one window, or none where nothing locates tick 0 on the supplied clock and a
            wall-clock window therefore names no tick.
        """
        clock = Clock(
            clock_id=str(self.clock_row["clock_id"]),
            session_id=self.session_id,
            name=str(self.clock_row["clock_id"]),
            tick_rate_num=int(self.clock_row["tick_rate_num"]),
            tick_rate_den=int(self.clock_row.get("tick_rate_den", 1)),
            origin=str(self.clock_row.get("origin", "")),
            tick_zero_utc=_instant(self.clock_row.get("tick_zero_utc")),
        )
        if clock.tick_zero_utc is None:
            self.notes.append(
                Note(
                    f"{self.clock_row['clock_id']}: no tick_zero_utc, so the declared acquisition window "
                    "locates no ticks and no observation interval is emitted",
                    AindNote.NO_OBSERVATION_INTERVAL,
                )
            )
            return []
        window = self.behavior()
        start, stop = clock.tick_at(window.start), clock.tick_at(window.stop)
        if stop < start:
            raise SourceDefect(
                f"{self.path}: data_streams[{window.index}] ends before it starts",
                code=AindFault.STREAM_REVERSED,
                where=f"data_streams[{window.index}]",
            )
        return [
            {
                "session_id": self.session_id,
                "clock_id": clock.clock_id,
                "start_tick": start,
                "stop_tick": stop,
            }
        ]

    def extent(self) -> tuple[datetime, datetime]:
        """When the session began and ended, across every declared stream.

        The union, not one stream's window: acquisition is staggered, and a session that ended
        when its first stream did would exclude data the packet holds.

        Returns
        -------
        tuple of datetime
            Earliest start and latest stop, in UTC.
        """
        windows = self.streams()
        if not windows:
            raise SourceDefect(
                f"{self.path}: no data_streams, so the session has no extent",
                code=AindFault.NO_STREAMS,
                where=str(self.path),
            )
        return (
            min(w.start for w in windows).astimezone(UTC),
            max(w.stop for w in windows).astimezone(UTC),
        )

    # -- calibrations (R89) -----------------------------------------------------------

    @property
    def _rig(self) -> dict[str, Any]:
        """The `rig.json` beside this `session.json`, or an empty document where there is none.

        Absent is not a defect: a packet holding no calibration is conforming (R89 §3), and the
        rig document is a separate file that an asset may not carry.
        """
        if self._rig_document is None:
            path = self.path.parent / RIG_JSON
            self._rig_document = json.loads(path.read_text()) if path.is_file() else {}
        return self._rig_document

    @property
    def _subject(self) -> dict[str, Any]:
        """The `subject.json` beside this `session.json`, or an empty document where there is none.

        Absent is not a defect: the document is a separate file an asset may not carry, as
        `rig.json` is. A partial copy of an asset may hold the session document without it, which
        is a fact about the copy and not about the source.
        """
        if self._subject_document is None:
            path = self.path.parent / SUBJECT_JSON
            self._subject_document = json.loads(path.read_text()) if path.is_file() else {}
        return self._subject_document

    @property
    def stated_species(self) -> str | None:
        """The scientific name, as NCBI Taxonomy spells it and this document already writes it."""
        return _clean((self._subject.get("species") or {}).get("name"))

    @property
    def stated_sex(self) -> str | None:
        """The sex, mapped onto its closed vocabulary: this document writes `Male`."""
        return _sex(_clean(self._subject.get("sex")))

    @property
    def stated_genotype(self) -> str | None:
        """The genotype as stated, in whatever nomenclature this document used."""
        return _clean(self._subject.get("genotype"))

    @property
    def stated_strain(self) -> str | None:
        """The background strain, or None where the document leaves it unset."""
        return _clean(self._subject.get("background_strain"))

    @property
    def stated_date_of_birth(self) -> date | None:
        """The date of birth this document writes, read as the calendar date it is."""
        born = _clean(self._subject.get("date_of_birth"))
        # A date of birth is a calendar date (R4 §3.3), and this document writes one, so there is
        # no instant to localize and nothing can move it by a day.
        return date.fromisoformat(born) if born else None

    def subjects(self) -> list[dict[str, Any]]:
        """`core.subjects` from `subject.json`, which states what the NWB does not.

        `general/subject` states a species too, so this is the record rather than the only
        source. What it adds is what the exporter's projection has no place for: a
        `background_strain` key the NWB lacks entirely, and a date of birth with no timezone, where
        the NWB writes a midnight with an offset, which a conversion can move to another day
        (R4 §3.3). Nothing translates either way: both already spell the name as NCBI Taxonomy
        does, and a writer that guessed one from a common name would be inventing a fact
        (R101 §3.4).

        Everything the standard does not model goes to `metadata` (Part 02 §8.6), the taxon identifier
        included -- `NCBI:txid10090` is what survives a renaming the name does not (R59 §1), and no
        column holds one. The name itself is not repeated there, which Part 02 §8.6 forbids.
        """
        document = self._subject
        if not document:
            return []
        row: dict[str, Any] = {
            "subject_id": _clean(document.get("subject_id")) or self.subject_id,
            "species": self.stated_species,
            "strain": self.stated_strain,
            "sex": self.stated_sex,
            "genotype": self.stated_genotype,
            "date_of_birth": self.stated_date_of_birth,
        }
        extra: dict[str, Any] = {}
        if identifier := _clean((document.get("species") or {}).get("registry_identifier")):
            extra["species_registry_identifier"] = identifier
        for key in ("rrid", "breeding_info", "housing", "restrictions", "notes", "source"):
            value = document.get(key)
            if value not in (None, {}, [], "") and _clean(value) is not None:
                extra[key] = value
        if extra:
            row["metadata"] = json.dumps(extra, sort_keys=True)
        return [row]

    def _modules(self) -> list[dict[str, Any]]:
        """Every `ephys_module` of every stream, in file order."""
        return [m for s in self._document.get("data_streams", []) or [] for m in s.get("ephys_modules", []) or []]

    def calibrations(self) -> list[dict[str, Any]]:
        """`core.calibrations`: what was measured about an instrument so its numbers can be read.

        Two shapes, because a source states a calibration more than one way (R89 §1.3). A
        `rig.json` entry is a curve, and its type is the quantity its own output label names --
        the vocabulary is open (Part 02 §9.3), so the source's word for what it measured is a value
        rather than something to map onto a closed set. An `ephys_module` states a manipulator
        transform, one calibration cited by every module sharing its file and timestamp (R89
        §1.4), whose content is an array this adapter does not read: the row records that the
        calibration was in force and that the packet holds nothing further (Part 02 §12.3).
        """
        rows: list[dict[str, Any]] = []
        for entry in self._rig.get("calibrations", []) or []:
            name = _clean(entry.get("device_name"))
            if name is None:
                continue
            output = _label(entry.get("output"))
            rows.append(
                {
                    "calibration_id": self.prefix + name,
                    "session_id": self.session_id,
                    "calibration_name": self.prefix + name,
                    "calibration_type": _quantity(output) or "unknown",
                    "calibrated_at": self._calibrated_at(entry.get("calibration_date"), name),
                    "description": _clean(entry.get("description")),
                    "input_unit": _unit(_label(entry.get("input"))),
                    "output_unit": _unit(output),
                    "array_asset_id": None,
                    "detail_kind": None,
                    # R89 §2.6: what the source said that no column above models. The note is not
                    # `description`, which carries the source's own description field.
                    "metadata": _bag(notes=_clean(entry.get("notes"))),
                }
            )
        for transform, when in self._transforms().items():
            rows.append(
                {
                    "calibration_id": self.prefix + transform,
                    "session_id": self.session_id,
                    "calibration_name": self.prefix + transform,
                    "calibration_type": "manipulator_transform",
                    "calibrated_at": self._calibrated_at(when, transform),
                    "description": None,
                    "input_unit": None,
                    "output_unit": None,
                    # R89 §2.4 wants the array asset; this adapter does not read the `.npy`, so the
                    # content is unrecorded (Part 02 §12.3). The path is `calibration_name`, which is the
                    # identifier the source used for it, so nothing repeats it in `metadata`.
                    "array_asset_id": None,
                    "detail_kind": None,
                    "metadata": None,
                }
            )
        return rows

    def calibration_points(self) -> list[dict[str, Any]]:
        """`core.calibration_points`: the paired series of each calibration that is a curve.

        `rig.json` holds two parallel JSON lists, which Part 02 §5.2 forbids as a column; a series of
        unequal lengths is a defect in the source rather than something to truncate.
        """
        rows: list[dict[str, Any]] = []
        for entry in self._rig.get("calibrations", []) or []:
            name = _clean(entry.get("device_name"))
            if name is None:
                continue
            inputs, outputs = _series(entry.get("input")), _series(entry.get("output"))
            if len(inputs) != len(outputs):
                raise SourceDefect(
                    f"calibration {name!r} states {len(inputs)} inputs against {len(outputs)} "
                    "outputs; a point needs both sides (R89 §2.3)",
                    code=AindFault.CALIBRATION_MISALIGNED,
                    where=name,
                )
            rows.extend(
                {
                    "session_id": self.session_id,
                    "calibration_id": self.prefix + name,
                    "point_index": index,
                    "input_value": float(x),
                    "output_value": float(y),
                }
                for index, (x, y) in enumerate(zip(inputs, outputs, strict=True))
            )
        return rows

    def calibration_devices(self) -> list[dict[str, Any]]:
        """`core.calibration_devices`: the devices each calibration covers.

        The assembly name is the device name the acquisition chain gives the same probe, and the
        writer numbers both from that name under one recipe prefix (Part 05 §4.3), so the reference
        resolves without this adapter seeing `core.devices`. A calibration covering a device the
        packet does not hold gets no row, which is a fact rather than a defect (R89 §2.2) -- which is
        why the lick spouts of a water calibration appear here only if some source built them.
        """
        rows = []
        for module in self._modules():
            transform = _clean(module.get("coordinate_transform"))
            device = _clean(module.get("assembly_name"))
            if transform is not None and device is not None:
                rows.append(
                    {
                        "session_id": self.session_id,
                        "calibration_id": self.prefix + transform,
                        "device_id": self.prefix + device,
                    }
                )
        return rows

    def _transforms(self) -> dict[str, str | None]:
        """Each distinct `coordinate_transform` the modules cite, to the date they state for it."""
        found: dict[str, str | None] = {}
        for module in self._modules():
            transform = _clean(module.get("coordinate_transform"))
            if transform is not None:
                found.setdefault(transform, _clean(module.get("calibration_date")))
        return found

    def _calibrated_at(self, raw: str | None, label: str) -> datetime | None:
        """When the calibration was measured, in UTC, or None where the source states none.

        Null rather than invented (Part 01 §3.23). A stated offset is kept here where `_instant`
        discards one: a calibration is dated to the day and its offset is the rig's own, where
        `session_start_time` carries an offset this schema gets wrong often enough to distrust.
        A value with no offset falls back to the declared zone.
        """
        if raw is None:
            return None
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = self._instant(raw, f"calibration {label}")
        return parsed.astimezone(UTC)

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource this root holds."""
        return {
            CORE_SUBJECTS: len(self.subjects()),
            CORE_CALIBRATIONS: len(self.calibrations()),
            CORE_CALIBRATION_POINTS: len(self.calibration_points()),
            CORE_CALIBRATION_DEVICES: len(self.calibration_devices()),
        }

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Return the tables this source owns.

        Returns
        -------
        dict
            `core.clocks`, plus `core.subjects` and the calibration tables where the documents
            behind them are present. The reference clock is the row a build supplied, emitted
            rather than rebuilt: everything a build supplies is data (Part 12 §4), and where
            a build located tick 0 from an instrument's own record it knows better than the
            whole-second stream start this JSON carries.
        """
        calibrations = {
            CORE_CALIBRATIONS: self.calibrations(),
            CORE_CALIBRATION_DEVICES: self.calibration_devices(),
            CORE_CALIBRATION_POINTS: self.calibration_points(),
        }
        return {
            CORE_CLOCKS: [self.clock_row],
            **({CORE_CLOCK_OBSERVATION_INTERVALS: watched} if (watched := self.watched()) else {}),
            # Omitted rather than staged empty where the document is absent, as a calibration is.
            **({CORE_SUBJECTS: subjects} if (subjects := self.subjects()) else {}),
            # An asset carrying no calibration is conforming (R89 §3), so the resources are
            # omitted rather than staged empty -- a manifest entry a packet cannot answer for.
            **{resource: rows for resource, rows in calibrations.items() if rows},
        }


def _instant(value: Any) -> datetime | None:
    """Read a wall clock the build supplied, which crosses a boundary as a string."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _clean(value: Any) -> str | None:
    """Return a stated string, or None where the source wrote nothing or its word for nothing.

    This schema writes the string `None` where a field is unset, so a truthiness test keeps it.
    """
    if value is None:
        return None
    text = str(value).strip()
    return None if text in {"", "None", "null"} else text


def _label(side: Any) -> str | None:
    """Return the single key naming one side of a calibration's series."""
    return next(iter(side), None) if isinstance(side, dict) and len(side) == 1 else None


def _series(side: Any) -> list[float]:
    """Return the values of one side of a calibration's series, in file order."""
    return list(next(iter(side.values()))) if isinstance(side, dict) and len(side) == 1 else []


def _unit(label: str | None) -> str | None:
    """Return the unit of measure a series label states in parentheses, as in `water volume (ul):`."""
    found = re.search(r"\(([^)]*)\)", label or "")
    return found.group(1).strip() or None if found else None


def _quantity(label: str | None) -> str | None:
    """Return a series label's quantity as a vocabulary value: `water volume (ul):` to `water_volume`.

    The vocabulary is open (Part 02 §9.3), so what the source called the quantity it measured is a value
    rather than something to map onto a closed set this specification does not have.
    """
    if label is None:
        return None
    bare = re.sub(r"\([^)]*\)", "", label).strip().strip(":").strip()
    return re.sub(r"[^a-z0-9]+", "_", bare.lower()).strip("_") or None


def _bag(**stated: str | None) -> str | None:
    """Return what the source stated that no column models, as JSON, or None where it stated none."""
    kept = {key: value for key, value in stated.items() if value is not None}
    return json.dumps(kept, sort_keys=True) if kept else None


__all__ = ["RIG_JSON", "SESSION_JSON", "SUBJECT_JSON", "AcquisitionStream", "SessionSource"]

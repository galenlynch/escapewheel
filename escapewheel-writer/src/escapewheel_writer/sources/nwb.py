"""Read an NWB-Zarr file into records, against a clock and a zone the caller declares.

- :class:`NWBSource` -- the file's subject, session, devices, probes, electrodes, events, trials
  and signals.
- :func:`electrode_name`, :func:`contact_ids`, :func:`contact_columns` -- the one rule naming a
  contact, shared by every adapter reading the file.
- :func:`ucum_code` -- the UCUM code for an NWB `unit` attribute.
- :data:`ABSENT` -- the spellings an NWB writes where a value is absent.
- :func:`clean` -- a source value as a typed column takes it, absence as null.

The adapter emits no units or spikes: an NWB stores spike times as float seconds and ticks are not
fitted from them, so units and spikes come from the sorter. Times on a clock other than the one
declared raise :exc:`~escapewheel_writer.errors.OffGrid` rather than convert to plausible ticks.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime
from functools import cached_property
from os.path import commonprefix
from pathlib import Path
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

import numpy as np
from escapewheel_reader.resource_ids import (
    CORE_ARRAY_ASSET_INSTANCES,
    CORE_ARRAY_ASSETS,
    CORE_ARRAY_DIMENSIONS,
    CORE_CLOCK_ANCHORS,
    CORE_CLOCKS,
    CORE_COORDINATE_FRAME_AXES,
    CORE_COORDINATE_FRAMES,
    CORE_DEVICES,
    CORE_ELECTRODE_COORDINATE_VALUES,
    CORE_ELECTRODE_COORDINATES,
    CORE_ELECTRODES,
    CORE_EVENT_STREAMS,
    CORE_EVENTS,
    CORE_INTERVALS,
    CORE_PROBES,
    CORE_SESSIONS,
    CORE_SUBJECTS,
    CORE_UNIT_COORDINATE_VALUES,
    CORE_UNIT_COORDINATES,
)
from numpy.typing import NDArray

from ..clock import TickGrid, zone_of
from ..errors import SourceDefect, SourceFault, UnsupportedEncoding, UsageError, UsageFault
from ..notes import Note, NoteCode
from .compensations import Compensates
from .store import SourceStore, source_root
from .values import sex as _sex
from .values import utc_offset as _offset

#: NWB writes the literal string ``None`` where a value is absent -- in `laser_location`,
#: `auto_train_stage`, `was_generated_by`. Treated as null when mapped into a typed core
#: column; left verbatim inside metadata, which is a faithful copy of the source.
ABSENT = {"", "None", "none", "nan", "NaN"}


def _one(values: NDArray[Any]) -> str | None:
    """Take the single value of a scalar NWB array, as text, or None if it is absent."""
    if values.size == 0:
        return None
    value = values[0]
    if isinstance(value, bytes):
        value = value.decode()
    text = str(value).strip()
    return None if text in ABSENT else text


def clean(value: Any) -> Any:
    """Map a source value into a typed core column, turning absence into null."""
    if isinstance(value, bytes):
        value = value.decode()
    if isinstance(value, str):
        return None if value.strip() in ABSENT else value
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if isinstance(value, np.generic):
        return clean(value.item())
    return value


def _alike(a: Any, b: Any) -> bool:
    """Whether two trial-column values are the same, with NaN equal to NaN.

    A float column of all-NaN is constant, not varying: `nan != nan` would otherwise make every
    absent parameter look like per-trial data and keep it on every row.
    """
    try:
        if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
            return True
    except TypeError:
        pass
    return bool(a == b)


def electrode_name(group: Any, channel: Any, prefix: str = "") -> str:
    """Compose a contact's packet-wide name, which no NWB column carries on its own.

    `electrode_name` repeats across the shanks of a quad-base probe and `channel_name` is
    per-probe, so the pair is what identifies a contact.

    Module-level because every adapter reading one NWB composes it: a writer numbers a name
    (Part 05 §4.3), so a second spelling of one contact mints a second electrode, and the packet then
    references a row that is not there.
    """
    return f"{prefix}{group}.{channel}"


#: Part 02 §8.4. NWB spells a unit as a word where a packet records its UCUM code. A spelling not
#: listed passes through unchanged, so validation rejects it rather than the writer guessing.
UCUM_CODES: Mapping[str, str] = {"volts": "V"}


def ucum_code(stated: str | None) -> str | None:
    """Return the UCUM code for an NWB `unit` attribute, or None where the file states none."""
    return UCUM_CODES.get(stated, stated) if stated else None


def contact_columns(store: Any, table: Path) -> dict[str, Any]:
    """Read the electrode columns a contact's name is composed from, whichever the file carries."""
    return {
        column: store.array(table / column)
        for column in ("group_name", "channel_name", "id")
        if (table / column).is_dir()
    }


def contact_ids(columns: Mapping[str, Any], prefix: str = "") -> tuple[list[str], Note | None]:
    """Name every contact in electrode-table row order, and say if the fallback was needed.

    Three adapters name the same contacts, and a writer numbers a name (Part 05 §4.3), so a second
    spelling of one contact mints a second electrode and the packet then references a row that is
    not there. The rule lives here once rather than in each of them.
    """
    if "group_name" not in columns:
        raise SourceDefect(
            "electrodes/group_name: absent, so no contact can be named",
            code=SourceFault.NO_ELECTRODE_GROUPS,
            where="electrodes/group_name",
        )
    group = columns["group_name"]
    if "channel_name" in columns:
        pairs = columns["channel_name"]
        note: Note | None = None
    else:
        # Every `DynamicTable` has an `id`, so a contact is always nameable; what the fallback
        # loses is the source's own spelling, which `local_channel_label` then cannot carry.
        pairs = columns["id"] if "id" in columns else np.arange(len(group))
        note = Note(
            "electrodes: no channel_name, so a contact is named by its group and row id", NoteCode.NO_CHANNEL_NAMES
        )
    return [electrode_name(one, other, prefix) for one, other in zip(group, pairs, strict=True)], note


def _subject_fact(key: str) -> property:
    """Return a `subject.*` fact this file states, from the row `subjects()` already builds.

    Part 05 §3.4 has a build ask an adapter what it states without opening it, so each fact needs an
    attribute of its own for the class-level check to see; the value still comes from one read.
    """
    return property(lambda self: self.subjects()[0].get(key))


class NWBSource(Compensates):
    """An NWB file, read as records against a declared clock and zone.

    Parameters
    ----------
    root : str or Path
        The ``.nwb`` directory, or a directory containing exactly one.
    reference_clock : Mapping
        The `core.clocks` row of the clock the file's `timestamps` are on (Part 12 §4). Every
        conversion is checked against its grid, so the wrong clock raises rather than producing
        plausible ticks. A row rather than a clock object because everything a build supplies is
        data, and the row is what an adapter out of process receives.
    zone : str or zoneinfo.ZoneInfo
        The rig's wall-clock zone. Used for values stored without an offset, and to
        cross-check the ones stored with one.
    session_id : str, optional
        Overrides the file's own `general/session_id`.
    prefix : str, optional
        Prepended to every generated ID. A single-session packet needs none; merging
        sessions into one packet needs the IDs disambiguated.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    trial_metadata : bool, default True
        Carry each unmapped trial column that varies across trials into `core.intervals.metadata`
        (Part 02 §8.6). A column `TRIAL_MAPPED` names is never carried. Turn it off where an
        extension holds the same columns, which `metadata` must not repeat.

    Attributes
    ----------
    notes : list of str
        What was dropped, coerced, or found inconsistent while reading. Empty is not the
        expected case: real files carry placeholder streams and bad offsets, and an importer
        that says nothing about them has hidden them.

    Examples
    --------
    >>> source = NWBSource(path, reference_clock=harp, zone=ZoneInfo("America/Los_Angeles"))  # doctest: +SKIP
    >>> tables = source.records()  # doctest: +SKIP
    """

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    #: Static, so a recipe check reads it with nothing open -- `offers` counts rows and
    #: therefore needs the data.
    PRODUCES = frozenset(
        {
            CORE_ARRAY_ASSETS,
            CORE_ARRAY_DIMENSIONS,
            CORE_CLOCK_ANCHORS,
            CORE_CLOCKS,
            CORE_DEVICES,
            CORE_COORDINATE_FRAME_AXES,
            CORE_COORDINATE_FRAMES,
            CORE_ELECTRODE_COORDINATE_VALUES,
            CORE_ELECTRODE_COORDINATES,
            CORE_ELECTRODES,
            CORE_EVENT_STREAMS,
            CORE_EVENTS,
            CORE_INTERVALS,
            CORE_PROBES,
            CORE_SESSIONS,
            CORE_SUBJECTS,
        }
    )
    # Not `core.unit_coordinates` or its values. Placing a unit needs the sorter's own label for
    # it, and no column base NWB defines carries one -- `units/id` is the DynamicTable row number,
    # which is not the sorter's label. A dialect that writes the label declares those two
    # resources and supplies `unit_identity`.

    #: Part 01 §3.24: the unit every coordinate this adapter writes is in. No NWB states one; what
    #: makes this the packet's answer is that this adapter passed the values through unconverted,
    #: and R19 §3 declared micrometres when it named the columns `x_um`, `y_um` and `z_um`.
    COORDINATE_UNIT: ClassVar[str] = "um"

    #: Part 02 §12.7: each frame's axes in index order, named for the field the values are read
    #: from. The name is carried verbatim (Part 01 §3.24) -- `rel_x` says the packet's axis 0 holds
    #: what this file called `rel_x`, which is a fact, where calling it `across_shank` would be a
    #: claim no source supports and calling it `x` would discard where the value came from.
    #:
    #: One frame here. `rel_x` and `rel_y` are columns core 2.9.0 declares on its electrodes table;
    #: an atlas frame is a producer's addition, and a dialect adds it by extending this.
    FRAME_AXES: ClassVar[dict[str, tuple[str, ...]]] = {"probe": ("rel_x", "rel_y")}

    #: The axes a *unit* carries a position on, which base NWB gives none of: `Units` declares
    #: `spike_times`, `electrodes` and the waveform columns, and no coordinate.
    UNIT_AXES: ClassVar[tuple[str, ...]] = ()

    #: The frame those axes are in, and what a position in it claims (R64 §1.3). Empty while
    #: `UNIT_AXES` is, since a frame with no axes names nothing; a dialect sets both together.
    UNIT_FRAME: ClassVar[str] = ""
    UNIT_BASIS: ClassVar[str] = "measured"

    #: Trial columns that are *events*, and the type each becomes. A task writes these into the
    #: trials table because they happen once a trial, but a moment on a clock is an event whatever
    #: table it arrives in. `TimeIntervals` declares `start_time`, `stop_time` and tags alone, so
    #: every such column is a task's own and a dialect names them.
    TRIAL_EVENTS: ClassVar[dict[str, str]] = {}

    #: Trial columns this adapter accounts for; the rest go to `core.intervals.metadata` verbatim.
    #: A dialect widens this with the task columns it maps, which is what keeps them out of the bag
    #: rather than swept in as unmapped.
    TRIAL_MAPPED: ClassVar[frozenset[str]] = frozenset({"start_time", "stop_time"})

    #: Electrode columns carried into `core.electrodes.metadata` verbatim (Part 02 §8.6). Empty
    #: here: every column core 2.9.0 declares is either mapped or unread, so nothing is left over.
    CARRIED_ELECTRODE: ClassVar[tuple[str, ...]] = ()

    #: Part 05 §3.4: what of `PRODUCES` this adapter supplies only part of, which a source entry
    #: without `owns` contributes rather than owns.
    CONTRIBUTES = frozenset(
        {
            CORE_ARRAY_ASSETS,
            CORE_ARRAY_DIMENSIONS,
            CORE_CLOCK_ANCHORS,
            CORE_CLOCKS,
            CORE_DEVICES,
        }
    )

    #: Part 05 §3.4: every column of `core.subjects` this file states.
    STATES: ClassVar[dict[str, str]] = {
        "subject.subject_id": "stated_subject_id",
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
    #: `units` is not here: the build fills it, and only a dialect that can read a unit's label
    #: joins on it. A subclass that does declares it (Part 12 §4).
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "reference_clock", "zone")

    #: Part 05 §3.4: options this adapter reads and can run without, which a recipe may leave
    #: unset (Part 12 §4). `interval_kind` defaults to no intervals, which is right for a session
    #: holding none.
    ACCEPTS: ClassVar[tuple[str, ...]] = (
        "prefix",
        "trial_metadata",
        "signals",
        "interval_kind",
        "emit_clock",
        "attachments",
        "source_cache",
    )

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ("sorter",)

    stated_subject_id = _subject_fact("subject_id")
    stated_species = _subject_fact("species")
    stated_sex = _subject_fact("sex")
    stated_genotype = _subject_fact("genotype")
    stated_date_of_birth = _subject_fact("date_of_birth")
    stated_strain = _subject_fact("strain")

    #: Not `core.unit_electrodes`, though the file has a column for it.
    #: `extremum_channel_index` indexes the channels the **sorting kept**, while
    #: `general/extracellular_ephys/electrodes` lists every contact of the probe and nothing
    #: records which were dropped, so the index cannot be resolved here -- read as a contact
    #: position it names the wrong electrode wherever the sorting dropped a channel below it. The
    #: adapter that owns the table reads the sorting analyzer, where the kept channels and the
    #: support are both stated.

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
        self.session_id = session_id or _one(self._array("general/session_id")) or self.root.stem
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

    # -- tables -----------------------------------------------------------------------

    def subjects(self) -> list[dict[str, Any]]:
        """`core.subjects`, one row."""
        if "subjects" in self._cache:
            cached: list[dict[str, Any]] = self._cache["subjects"]
            return cached
        columns = {name: _one(self._array(f"general/subject/{name}")) for name in self.store.members("general/subject")}
        born = self._instant(columns.get("date_of_birth"), "subject.date_of_birth")
        row: dict[str, Any] = {
            "subject_id": columns.get("subject_id") or self.session_id,
            "species": columns.get("species"),
            "sex": _sex(columns.get("sex")),
            "genotype": columns.get("genotype"),
            # A date of birth is a calendar date (R4 §3.3): the local date as written is the
            # fact, and converting it through UTC could move it by a day.
            "date_of_birth": born.date() if born is not None else None,
            "strain": columns.get("strain"),
        }
        if extra := {k: v for k, v in columns.items() if k not in row and v is not None}:
            row["metadata"] = extra
        self._cache["subjects"] = [row]
        return [row]

    def sessions(self) -> list[dict[str, Any]]:
        """`core.sessions`, one row."""
        start = self._instant(_one(self._array("session_start_time")), "session_start_time")
        if start is None:
            raise SourceDefect(
                f"{self.root}: no session_start_time", code=SourceFault.NO_SESSION_START, where=str(self.root)
            )
        reference = _one(self._array("timestamps_reference_time"))
        metadata = {
            "nwb_identifier": _one(self._array("identifier")),
            "nwb_version": self.attrs().get("nwb_version"),
            "lab": _one(self._array("general/lab")),
            "protocol": _one(self._array("general/protocol")),
            "timestamps_reference_time": reference,
            "file_create_date": _one(self._array("file_create_date")),
        }
        # A task parameter constant across every trial belongs here, once, rather than on each
        # of them. `intervals` computes the split, so ask for it before reading what it found.
        self.intervals()
        metadata.update({k: v for k, v in self._constants.items() if v is not None})
        return [
            {
                "session_id": self.session_id,
                "subject_id": self.subjects()[0]["subject_id"],
                "session_start_time": start,
                "session_description": _one(self._array("session_description")),
                "institution": _one(self._array("general/institution")),
                "metadata": {k: v for k, v in metadata.items() if v is not None},
            }
        ]

    def _attachment(self) -> dict[str, dict[str, str | None]]:
        """Which headstage each probe was in and on which dock, or nothing."""
        if self.attachments is None:
            return {}
        from .openephys import OpenEphysSource

        return OpenEphysSource(self.attachments, session_id=self.session_id, prefix=self.prefix).attachments()

    @cached_property
    def _devices(self) -> list[dict[str, Any]]:
        """`core.devices`, one row per physical instrument (Part 01 §3.5).

        One row per *object*, not per NWB Device: a quad-base probe presents four Devices with
        one serial number, and recording four rows asserts four probes where the session had
        one. Identity is the serial the file states; the four remain four `core.probes` rows.
        The surviving row takes the common prefix of the names it covers where there is one --
        naming only, since the serial is what decided identity.
        """
        found: dict[str, dict[str, Any]] = {}
        attached = self._attachment()
        for name in self.store.members("general/devices"):
            described = self.attrs(f"general/devices/{name}")
            identity = self.device_identity(described)
            serial = identity["serial_number"]
            attachment = attached.get(name) or {}
            row = {
                "device_id": self.prefix + name,
                "session_id": self.session_id,
                "device_name": self.prefix + name,
                "manufacturer": clean(described.get("manufacturer")),
                "model": identity["model"],
                "serial_number": serial,
                "parent_device_id": attachment.get("parent_device_id"),
                # R85 §2.1: the dock of that headstage. Null where no attachment is stated, and
                # null is what a consumer must read as unrecorded rather than parse out of a name.
                "parent_port": attachment.get("parent_port"),
                "metadata": identity["metadata"],
            }
            # A device with no serial is its own object: nothing says two of them are one.
            key = serial or f"\0{name}"
            if (kept := found.get(key)) is None:
                found[key] = row | {"covers": [name]}
            else:
                kept["covers"].append(name)
        rows = []
        for row in found.values():
            covers = row.pop("covers")
            if len(covers) > 1:
                shared = commonprefix(covers).rstrip("-_ .") or covers[0]
                row |= {"device_id": self.prefix + shared, "device_name": self.prefix + shared}
                self.notes.append(
                    Note(
                        f"devices: {', '.join(covers)} share serial {row['serial_number']}; "
                        f"recorded as one device named {shared} (Part 01 §3.5)",
                        NoteCode.DEVICES_MERGED,
                    )
                )
            rows.append(row)
        return rows

    def devices(self) -> list[dict[str, Any]]:
        """`core.devices`, computed once: it reads the store and the attachment file."""
        return self._devices

    def device_identity(self, described: Mapping[str, Any]) -> dict[str, Any]:
        """Return what a `Device` states about the object it names: model, serial, and the rest.

        Core 2.9.0 declares all three as attributes, so that is where they are read. A producer
        that leaves them unset and packs the same facts into `description` needs a dialect.
        """
        description = clean(described.get("description"))
        return {
            "model": clean(described.get("model_number")) or clean(described.get("model_name")),
            "serial_number": clean(described.get("serial_number")),
            "metadata": {"description": description} if description else None,
        }

    def _device_of(self) -> dict[str, dict[str, Any]]:
        """Every NWB Device name mapped to the `core.devices` row that covers it."""
        by_name = {}
        for name in self.store.members("general/devices"):
            described = self.attrs(f"general/devices/{name}")
            by_name[name] = self.device_identity(described)["serial_number"]
        rows = {row["serial_number"]: row for row in self.devices() if row["serial_number"]}
        named = {row["device_name"]: row for row in self.devices()}
        return {name: rows.get(serial) or named.get(self.prefix + name) for name, serial in by_name.items()}

    def probes(self) -> list[dict[str, Any]]:
        """`core.probes`, one row per NWB ElectrodeGroup.

        An ElectrodeGroup is what actually recorded, which is why it -- and not the Device --
        is the probe: each shank of a quad-base probe gets a group of its own, and a Device may
        have recorded nothing.
        """
        devices = self._device_of()
        rows = []
        for name in self.store.members("general/extracellular_ephys"):
            if name == "electrodes":
                continue
            described = self.attrs(f"general/extracellular_ephys/{name}")
            linked = [
                link["path"].rsplit("/", 1)[-1]
                for link in described.get("zarr_link", [])
                if link.get("name") == "device"
            ]
            device = devices.get(linked[0]) if linked else devices.get(name)
            rows.append(
                {
                    "probe_id": self.prefix + name,
                    "session_id": self.session_id,
                    "device_id": device["device_id"] if device else None,
                    "probe_name": self.prefix + name,
                    "probe_type": device["model"] if device else None,
                    "manufacturer": device["manufacturer"] if device else None,
                    "serial_number": device["serial_number"] if device else None,
                    "target_region": clean(described.get("location")),
                    "metadata": {"description": described["description"]} if described.get("description") else None,
                }
            )
        return rows

    def _electrode_ids(self, columns: Mapping[str, NDArray[Any]]) -> list[str]:
        """Compose electrode IDs, because no NWB column is unique on its own."""
        names, note = contact_ids(columns, self.prefix)
        if note is not None and note not in self.notes:
            self.notes.append(note)
        return names

    def electrodes(self) -> list[dict[str, Any]]:
        """`core.electrodes`, one row per recorded contact."""
        columns = self.table("general/extracellular_ephys/electrodes")
        if not columns:
            return []
        carried = self.CARRIED_ELECTRODE
        if "inter_sample_shift" in columns:
            self.notes.append(
                Note(
                    "electrodes/inter_sample_shift: not emitted; R19 puts it on core.array_channels "
                    "and this adapter emits no array assets",
                    NoteCode.SAMPLE_SHIFT_NOT_EMITTED,
                )
            )
        rows = []
        for index, electrode_id in enumerate(self._electrode_ids(columns)):
            metadata = {name: clean(columns[name][index]) for name in carried if name in columns}
            rows.append(
                {
                    "electrode_id": electrode_id,
                    "session_id": self.session_id,
                    "probe_id": self.prefix + str(columns["group_name"][index]),
                    "local_electrode_label": self.local_electrode_label(columns, index),
                    "local_channel_label": clean(columns["channel_name"][index]) if "channel_name" in columns else None,
                    "impedance_ohm": clean(columns["imp"][index]) if "imp" in columns else None,
                    "metadata": {k: v for k, v in metadata.items() if v is not None} or None,
                }
            )
        return rows

    def local_electrode_label(self, columns: Mapping[str, NDArray[Any]], index: int) -> str | None:
        """Return a contact's own label; None, because base NWB names only its group."""
        return None

    def signal_device_id(self, name: str) -> str | None:
        """Return the instrument that made a stream; None, since base NWB links it to no Device."""
        return None

    #: R64 §1.3: the basis travels with the columns a value comes from rather than with the
    #: frame's name. `rel_x` is the shank's own layout and so is true by construction, where a
    #: CCF triple is what a registration found. `planned` cannot be imported from either -- an
    #: exported file records where a probe was, never where it was aimed, and a targeting record
    #: does not reach NWB.
    FRAME_BASIS: ClassVar[dict[str, str]] = {"probe": "nominal"}

    def _electrode_positions(self) -> list[tuple[dict[str, Any], tuple[float | None, ...]]]:
        """Each electrode coordinate paired with its values, in its frame's axis order.

        One pass serves both `core.electrode_coordinates` and its values, which Part 01 §3.8 makes
        the same position split in two: the parent carries the annotation and the child one row
        per axis.
        """
        columns = self.table("general/extracellular_ephys/electrodes")
        if not columns:
            return []
        found = []
        for index, electrode_id in enumerate(self._electrode_ids(columns)):
            for frame, axes in self.FRAME_AXES.items():
                values = tuple(clean(columns[axis][index]) if axis in columns else None for axis in axes)
                if all(value is None for value in values):
                    continue
                found.append(
                    (
                        {
                            "electrode_id": electrode_id,
                            "coordinate_frame": frame,
                            "coordinate_basis": self.FRAME_BASIS[frame],
                            **self.annotation(columns, index, frame),
                        },
                        values,
                    )
                )
        return found

    def electrode_coordinates(self) -> list[dict[str, Any]]:
        """`core.electrode_coordinates`, one row per electrode per populated frame.

        Rows per frame rather than one NaN-padded triple (R19 §3): a file may leave `x`/`y`/`z`,
        the columns NWB specifies, NaN for every electrode while it populates other frames whose
        coverage differs.
        """
        return [row for row, _values in self._electrode_positions()]

    def electrode_coordinate_values(self) -> list[dict[str, Any]]:
        """`core.electrode_coordinate_values`, one row per axis of each coordinate (Part 01 §3.8).

        An axis this file leaves empty gets no row. That is a position the source did not state
        on that axis, which Part 01 §3.8 forbids a consumer reading as a zero.
        """
        return [
            {
                "session_id": self.session_id,
                "electrode_id": row["electrode_id"],
                "coordinate_frame": row["coordinate_frame"],
                "coordinate_basis": row["coordinate_basis"],
                "axis_index": index,
                "axis_value": value,
            }
            for row, values in self._electrode_positions()
            for index, value in enumerate(values)
            if value is not None
        ]

    def _populated_frames(self) -> list[str]:
        """Return the frames this file states a coordinate in, in `FRAME_AXES` order."""
        named = {
            *self.table("general/extracellular_ephys/electrodes"),
            *self.table("units"),
        }
        return [frame for frame, axes in self.FRAME_AXES.items() if any(axis in named for axis in axes)]

    def coordinate_frames(self) -> list[dict[str, Any]]:
        """`core.coordinate_frames`, one row per frame this file populates (Part 01 §3.24).

        `atlas` and `atlas_version` are null. Base NWB names neither, and Part 01 §3.24 forbids
        reading one out of the frame's name, `ccf` being a label rather than a version.
        """
        return [
            {
                "session_id": self.session_id,
                "coordinate_frame": frame,
                "atlas": None,
                "atlas_version": None,
                "description": None,
            }
            for frame in self._populated_frames()
        ]

    def coordinate_frame_axes(self) -> list[dict[str, Any]]:
        """`core.coordinate_frame_axes`, one row per axis of each populated frame (Part 02 §12.7).

        `axis_direction` is null throughout: which way `rel_x` or `ccf_ml` increases is an
        interpretation of the source rather than a report of it, and Part 01 §3.24 requires a writer
        to leave it null where its source does not state it.
        """
        return [
            {
                "session_id": self.session_id,
                "coordinate_frame": frame,
                "axis_index": index,
                "axis_name": axis,
                "axis_direction": None,
                "unit": self.COORDINATE_UNIT,
            }
            for frame in self._populated_frames()
            for index, axis in enumerate(self.FRAME_AXES[frame])
        ]

    def annotation(self, columns: Mapping[str, Any], index: int, frame: str) -> dict[str, Any]:
        """Return a coordinate's atlas annotation; empty, since base NWB declares no atlas frame."""
        return {}

    # -- units, which this file describes but does not date -----------------------------

    def unit_identity(self) -> list[tuple[int, dict[str, Any]]]:
        """Return NWB unit rows paired with the build's unit identity, in row order.

        Empty: no column base NWB declares carries the sorter's label, and `units/id` is the row
        number, which is not that label.
        """
        return []

    def _unit_positions(self) -> list[tuple[dict[str, Any], tuple[float | None, ...]]]:
        """Each unit coordinate paired with its CCF values, as `_electrode_positions` does."""
        paired = self.unit_identity()
        if not paired or not self.UNIT_AXES:
            return []
        columns = self.table("units")
        if not any(axis in columns for axis in self.UNIT_AXES):
            return []
        found = []
        for index, identity in paired:
            values = tuple(clean(columns[axis][index]) if axis in columns else None for axis in self.UNIT_AXES)
            if all(value is None for value in values):
                continue
            found.append(
                (
                    {
                        "session_id": self.session_id,
                        **identity,
                        "coordinate_frame": self.UNIT_FRAME,
                        "coordinate_basis": self.UNIT_BASIS,
                        **self.annotation(columns, index, self.UNIT_FRAME),
                    },
                    values,
                )
            )
        return found

    def unit_coordinates(self) -> list[dict[str, Any]]:
        """`core.unit_coordinates`, a unit's position per populated frame (R28).

        Empty without `unit_identity` and `UNIT_AXES`. Where a subclass supplies both, a unit
        whose coordinates are all absent still gets no row.
        """
        return [row for row, _values in self._unit_positions()]

    def unit_coordinate_values(self) -> list[dict[str, Any]]:
        """`core.unit_coordinate_values`, one row per axis of each unit coordinate (Part 01 §3.8)."""
        return [
            {
                "session_id": self.session_id,
                "unit_id": row["unit_id"],
                "coordinate_frame": row["coordinate_frame"],
                "coordinate_basis": row["coordinate_basis"],
                "axis_index": index,
                "axis_value": value,
            }
            for row, values in self._unit_positions()
            for index, value in enumerate(values)
            if value is not None
        ]

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
        from ..writer import StagedArray

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
            same = n > 1 and all(_alike(values[i], first) for i in range(1, n))
            if same:
                constant[name] = first
            else:
                varying.append(name)
        self._constants = constant
        return varying

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter produces, keyed by resource ID.

        Returns
        -------
        dict
            Resource ID to records. Empty tables are omitted.
        """
        built = {
            CORE_SUBJECTS: self.subjects(),
            CORE_SESSIONS: self.sessions(),
            CORE_CLOCKS: ([self.clock_row] if self.emit_clock else []) + self.signal_clocks(),
            CORE_DEVICES: self.devices(),
            CORE_PROBES: self.probes(),
            CORE_ELECTRODES: self.electrodes(),
            CORE_COORDINATE_FRAMES: self.coordinate_frames(),
            CORE_COORDINATE_FRAME_AXES: self.coordinate_frame_axes(),
            CORE_ELECTRODE_COORDINATES: self.electrode_coordinates(),
            CORE_ELECTRODE_COORDINATE_VALUES: self.electrode_coordinate_values(),
            CORE_UNIT_COORDINATES: self.unit_coordinates(),
            CORE_UNIT_COORDINATE_VALUES: self.unit_coordinate_values(),
            CORE_EVENT_STREAMS: self.event_streams(),
            CORE_EVENTS: self.events(),
            CORE_INTERVALS: self.intervals(),
            CORE_CLOCK_ANCHORS: self.signal_anchors(),
            CORE_ARRAY_ASSETS: self.array_assets(),
            CORE_ARRAY_DIMENSIONS: self.array_dimensions(),
        }
        return {resource: rows for resource, rows in built.items() if rows}

    def offers(self) -> dict[str, int]:
        """Which resources this source supplies from its root, and how many rows (Part 05 §4.1)."""
        return {resource: len(rows) for resource, rows in self.records().items()}


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


__all__ = ["ABSENT", "NWBSource", "clean", "contact_columns", "contact_ids", "electrode_name", "ucum_code"]

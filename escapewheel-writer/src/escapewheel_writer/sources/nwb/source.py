"""Read an NWB-Zarr file into records, against a clock and a zone the caller declares.

- :class:`NWBSource` -- the file's subject, session, devices, probes, electrodes, events, trials
  and signals, composed from the method groups of this subpackage.

The adapter emits no units or spikes: an NWB stores spike times as float seconds and ticks are not
fitted from them, so units and spikes come from the sorter. Times on a clock other than the one
declared raise :exc:`~escapewheel_writer.errors.OffGrid` rather than convert to plausible ticks.
"""

from __future__ import annotations

from typing import Any, ClassVar

from escapewheel_reader.resource_ids import (
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

from ...errors import SourceDefect, SourceFault
from ..values import sex as _sex
from .devices import Devices
from .electrodes import Electrodes
from .events import Events
from .names import one
from .signals import Signals


def _subject_fact(key: str) -> property:
    """Return a `subject.*` fact this file states, from the row `subjects()` already builds.

    Part 05 §3.4 has a build ask an adapter what it states without opening it, so each fact needs an
    attribute of its own for the class-level check to see; the value still comes from one read.
    """
    return property(lambda self: self.subjects()[0].get(key))


class NWBSource(Devices, Electrodes, Signals, Events):
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

    # -- tables -----------------------------------------------------------------------

    def subjects(self) -> list[dict[str, Any]]:
        """`core.subjects`, one row."""
        if "subjects" in self._cache:
            cached: list[dict[str, Any]] = self._cache["subjects"]
            return cached
        columns = {name: one(self._array(f"general/subject/{name}")) for name in self.store.members("general/subject")}
        born = self._instant(columns.get("date_of_birth"), "subject.date_of_birth")
        row: dict[str, Any] = {
            "subject_id": columns.get("subject_id") or self.session_id,
            "species": columns.get("species"),
            "sex": _sex(columns.get("sex")),
            "genotype": columns.get("genotype"),
            # A date of birth is a calendar date: the local date as written is the
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
        start = self._instant(one(self._array("session_start_time")), "session_start_time")
        if start is None:
            raise SourceDefect(
                f"{self.root}: no session_start_time", code=SourceFault.NO_SESSION_START, where=str(self.root)
            )
        reference = one(self._array("timestamps_reference_time"))
        metadata = {
            "nwb_identifier": one(self._array("identifier")),
            "nwb_version": self.attrs().get("nwb_version"),
            "lab": one(self._array("general/lab")),
            "protocol": one(self._array("general/protocol")),
            "timestamps_reference_time": reference,
            "file_create_date": one(self._array("file_create_date")),
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
                "session_description": one(self._array("session_description")),
                "institution": one(self._array("general/institution")),
                "metadata": {k: v for k, v in metadata.items() if v is not None},
            }
        ]

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


__all__ = ["NWBSource"]

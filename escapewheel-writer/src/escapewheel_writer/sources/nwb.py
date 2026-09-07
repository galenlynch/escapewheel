"""Read an NWB file into records, without writing anything.

An adapter returns records; the writer turns records into a packet. That split is forced by
the data rather than chosen for tidiness: no single source carries a whole session. In
`inventory/nwb-zarr-776259-2025-04-09.md` §6 the NWB is the only source for trials and
behaviour and the only one with CCF registration, while the integer tick that
`core.spike_events` needs survives only in the sorter's output. A first packet therefore
merges sources, and an adapter that wrote packets could not be merged.

What this adapter emits, and what it does not
---------------------------------------------

It emits what the NWB is the authority for: identity, devices and probes, electrodes and
their two coordinate frames, the behaviour event streams, and trials.

It does **not** emit `core.units` or `core.spike_events`. Not because the NWB lacks units --
it has 6781 of them with three quality-label sources -- but because §3.3 measured that spike
times in this file have a per-probe alignment baked into float seconds and lie on no tick
grid. Recovering ticks would mean fitting a rate and an offset, and :class:`~escapewheel_writer.clock.Clock`
refuses that by design. Units come from the sorter, which still has its sample indices.

The clock is a parameter, not a discovery
-----------------------------------------

Nothing in an NWB declares a time base: `timestamps` are seconds, and NWB's contract says
they are relative to `session_start_time`. In this file they are not -- they are on the HARP
epoch, 134 days earlier (§3.1). So the caller passes the :class:`~escapewheel_writer.clock.Clock`
these times are on, and every conversion is checked against its grid. A wrong clock does not
produce wrong ticks; it produces :class:`~escapewheel_writer.clock.OffGrid`.

The zone is a parameter for the same reason
-------------------------------------------

`America/Los_Angeles` cannot be read out of the file, and the offsets that are in the file
are not reliable: this one carries `-07:53` on the subject's date of birth, the Local Mean
Time of the Pacific coast and the signature of localizing a date without a real timezone
database. The adapter cross-checks every stored offset against the declared zone and reports
the ones that disagree instead of trusting either blindly.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping, Sequence
from datetime import datetime
from functools import cached_property
from os.path import commonprefix
from pathlib import Path
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import NDArray

from ..clock import Clock
from .compensations import Compensates
from .store import SourceStore, source_root
from .zarr_compat import UnsupportedEncoding

#: NWB writes the literal string ``None`` where a value is absent -- in `laser_location`,
#: `auto_train_stage`, `was_generated_by`. Treated as null when mapped into a typed core
#: column; left verbatim inside metadata, which is a faithful copy of the source.
ABSENT = {"", "None", "none", "nan", "NaN"}

#: ``Model: <model> - Serial number: <serial>``, which is how `aind-data-schema` renders a
#: probe into an NWB `Device` description. The model itself contains hyphens.
#: The NWB packs a device's model, serial and description into one string. The serial is bounded
#: explicitly rather than by end-of-line: a lazy `.+?` anchored to `$` still swallows the
#: description after it, which put "20403319544 - Description: duplicate of PRB2_1_2_0640_0" in a
#: serial number column on every probe of a real session.
DEVICE_DESCRIPTION = re.compile(
    r"^Model:\s*(?P<model>.*?)\s*-\s*Serial number:\s*(?P<serial>[^\s-]+)"
    r"(?:\s*-\s*Description:\s*(?P<description>.*?))?\s*$"
)

#: The instrument behind an acquired signal, named in the signal's description because
#: `general/devices` lists probes alone -- "imported from HARP SniffDetector__32.bin". A signal
#: acquired by a separate workflow has no rig metadata in this packet's sources at all, so this
#: sentence is the only statement of what made the array that reaches the importer.
SIGNAL_DEVICE = re.compile(r"\bfrom\s+(?P<bus>HARP)\s+(?P<device>[A-Za-z0-9]+?)__(?P<register>\d+)\b")

#: `animal_response` in AIND's dynamic-foraging trials, per the column's own description.

#: Trial columns that are *events*, and the type each becomes. A task writes these into the
#: trials table because they happen once a trial, but a moment on a clock is an event whatever
#: table it arrives in: they belong in `core.events` so a query can find them without knowing
#: which task shape put them where. `analysis.trials_wide` denormalises them back (`06`).
TRIAL_EVENTS = {
    "goCue_start_time": "go_cue",
    "reward_outcome_time": "reward_outcome",
    "delay_start_time": "delay_start",
}

#: Trial columns this adapter accounts for; the rest go to `core.intervals.metadata` verbatim.
#: `animal_response` and the reward histories stay named here although R54 §2.3 struck their core
#: columns: they belong to the task's extension, and naming them is what keeps them out of core
#: metadata rather than swept in as unmapped.
TRIAL_MAPPED = frozenset(
    {"start_time", "stop_time", "animal_response", "rewarded_historyL", "rewarded_historyR", *TRIAL_EVENTS}
)

#: R19 §3: CCF's `ml`, `ap`, `dv` occupy `x_um`, `y_um`, `z_um` in that order.
CCF_AXES = ("ccf_ml", "ccf_ap", "ccf_dv")


class SourceDefect(ValueError):
    """The NWB is missing something an importer cannot proceed without."""


def _one(values: NDArray[Any]) -> str | None:
    """Take the single value of a scalar NWB array, as text, or None if it is absent."""
    if values.size == 0:
        return None
    value = values[0]
    if isinstance(value, bytes):
        value = value.decode()
    text = str(value).strip()
    return None if text in ABSENT else text


def _clean(value: Any) -> Any:
    """Map a source value into a typed core column, turning absence into null."""
    if isinstance(value, bytes):
        value = value.decode()
    if isinstance(value, str):
        return None if value.strip() in ABSENT else value
    if isinstance(value, float):
        return None if math.isnan(value) else value
    if isinstance(value, np.generic):
        return _clean(value.item())
    return value


def _alike(a: Any, b: Any) -> bool:
    """Whether two trial-column values are the same, with NaN equal to NaN.

    A float column of all-NaN is constant, not varying: `nan != nan` would otherwise make every
    absent parameter look like per-trial data and keep it on all 708 rows.
    """
    try:
        if isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b):
            return True
    except TypeError:
        pass
    return bool(a == b)


def _subject_fact(key: str) -> property:
    """Return a `subject.*` fact this file states, from the row `subjects()` already builds.

    R87 §2.2 has a build ask an adapter what it states without opening it, so each fact needs an
    attribute of its own for the class-level check to see; the value still comes from one read.
    """
    return property(lambda self: self.subjects()[0].get(key))


class NWBSource(Compensates):
    """An NWB file, read as records against a declared clock and zone.

    Parameters
    ----------
    root : str or Path
        The ``.nwb`` directory, or a directory containing exactly one.
    clock : Clock
        The clock the file's `timestamps` are on. Every conversion is checked against its
        grid, so passing the wrong clock raises rather than producing plausible ticks.
    zone : zoneinfo.ZoneInfo
        The rig's wall-clock zone. Used for values stored without an offset, and to
        cross-check the ones stored with one.
    session_id : str, optional
        Overrides the file's own `general/session_id`.
    prefix : str, optional
        Prepended to every generated ID. A single-session packet needs none; merging
        sessions into one packet needs the IDs disambiguated.
    trial_metadata : bool, default False
        Carry every unmapped trial column into `core.intervals.metadata` as JSON. **Off**, per
        R54 §2.5: a writer SHOULD NOT fill that column routinely, because doing so puts a task's
        varying parameters back into a JSON string that no rule can see and every row must parse
        — which is what an R17 extension's typed columns exist to replace. Turn it on only for a
        session whose task has no extension, and then as a stopgap.

    Attributes
    ----------
    notes : list of str
        What was dropped, coerced, or found inconsistent while reading. Empty is not the
        expected case: real files carry placeholder streams and bad offsets, and an importer
        that says nothing about them has hidden them.

    Examples
    --------
    >>> source = NWBSource(path, clock=harp, zone=ZoneInfo("America/Los_Angeles"))  # doctest: +SKIP
    >>> source.into(writer)  # doctest: +SKIP
    """

    #: R63 §2.1: what this adapter can supply, whatever a given root happens to hold.
    #: Static, so a recipe check reads it with nothing open -- `offers` counts rows and
    #: therefore needs the data.
    PRODUCES = frozenset(
        {
            "core.array_assets",
            "core.array_dimensions",
            "core.clock_anchors",
            "core.clocks",
            "core.devices",
            "core.electrode_coordinates",
            "core.electrodes",
            "core.event_streams",
            "core.events",
            "core.intervals",
            "core.probes",
            "core.sessions",
            "core.subjects",
            "core.unit_coordinates",
        }
    )

    #: R87 §2.2: every column of `core.subjects` this file states. The recipe declares four of
    #: them by hand, and until R87 §2.8 the row built from these was discarded unread.
    STATES: ClassVar[dict[str, str]] = {
        "subject.subject_id": "stated_subject_id",
        "subject.species": "stated_species",
        "subject.sex": "stated_sex",
        "subject.genotype": "stated_genotype",
        "subject.date_of_birth": "stated_date_of_birth",
        "subject.strain": "stated_strain",
    }

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
    #: position it named the wrong electrode for 5,071 of 6,781 units on the measured session,
    #: eleven of twelve probes having dropped between 1 and 18 channels. `WaveformSource` takes
    #: the peak from `waveform_mean` itself, reproducing the source's index in 6,781 of 6,781.

    def __init__(
        self,
        root: str | Path,
        *,
        clock: Clock,
        zone: ZoneInfo,
        session_id: str | None = None,
        prefix: str = "",
        trial_metadata: bool = False,
        units: Mapping[tuple[str, str], Mapping[str, str]] | None = None,
        signals: Sequence[str] = (),
        interval_kind: str | None = None,
        emit_clock: bool = True,
        attachments: str | Path | None = None,
        store: Any = None,
    ) -> None:
        if not isinstance(zone, ZoneInfo):
            raise TypeError(f"{zone!r} is a fixed offset; pass an IANA zone so DST resolves per date")
        self.root = _resolve(source_root(root))
        # R54 §2.1: an interval declares the resource that says what it was, and this adapter
        # cannot know it -- an exported trials table is the task's, and which task it is is a
        # fact about the session rather than about the file. The recipe names it, which is the
        # precondition R54 §4 required before the revision could be implemented at all.
        self.interval_kind = interval_kind
        self.store = store if store is not None else SourceStore(self.root)
        self.clock = clock
        self.zone = zone
        self.prefix = prefix
        self.trial_metadata = trial_metadata
        #: Where the acquisition records which headstage each probe was in (R67 §2.1). The NWB
        #: does not say, and the file that does joins on `custom_probe_name`, which is the name
        #: the NWB gives its Device -- so this reads one extra file for one column rather than
        #: needing a source to write into another source's rows.
        self.attachments = Path(attachments) if attachments else None
        #: Acquisition streams that are signals rather than events, named by the recipe. A
        #: continuously sampled quantity is an array with a time axis, not one row per sample
        #: carrying its value in JSON -- which R3 §2.1 confines to optional columns and which
        #: costs 5.9 M rows for one 400 Hz thermistor. Declared rather than inferred: whether a
        #: stream is a signal is a fact about the instrument, not about how many distinct
        #: values one session happened to record.
        self.signals = tuple(signals)
        self._signals: dict[str, tuple[NDArray[np.int64], NDArray[Any]]] = {}
        #: Whether to emit the reference clock. False where the sync source declares it,
        #: since both emitting it puts two rows under one clock_id.
        self.emit_clock = emit_clock
        #: Unmapped trial columns found constant across the session, filled in by `trials`.
        self._constants: dict[str, Any] = {}
        self.units = dict(units or {})
        Compensates.__init__(self)
        self.notes: list[str] = []
        self._cache: dict[str, Any] = {}
        self.session_id = session_id or _one(self._array("general/session_id")) or self.root.stem
        if clock.session_id != self.session_id:
            raise ValueError(
                f"clock {clock.clock_id!r} belongs to session {clock.session_id!r}, not {self.session_id!r}"
            )

    # -- source access ----------------------------------------------------------------

    def _array(self, path: str) -> NDArray[Any]:
        """Read one array, or an empty one if it is absent."""
        if not self.store.is_array(path):
            return np.empty(0)
        return self.store.array(path)

    def _attrs(self, path: str = "") -> dict[str, Any]:
        """Read one node's attributes."""
        return self.store.attrs(path)

    def _table(self, path: str) -> dict[str, NDArray[Any]]:
        """Read an hdmf table's row-aligned columns, skipping any this package will not decode.

        **A column an `<name>_index` declares ragged is not read.** Its rows are runs rather
        than values, so indexing it by a table row -- which is what every caller here does --
        is wrong for all but the first row; a caller that wants one reads it alongside its index.
        It is also where the bytes are: `units/spike_times` is 287 M values against the
        table's 6,781 rows, and decoding it accounts for most of the time this adapter
        spends reading.

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
                    self.notes.append(f"{path}/{name}: not read; {str(refused).rsplit('/', 1)[-1]}")
        self._cache[path] = out
        return out

    # -- time -------------------------------------------------------------------------

    def _instant(self, raw: str | None, label: str) -> datetime | None:
        """Parse a stored wall-clock value, checking its offset against the declared zone.

        The check is worth making because both failure modes are real and silent. The
        `session.json` beside this file stamps `+00:00` on a Pacific wall clock, a seven-hour
        error; the NWB stamps `-07:53` on the date of birth, which is the Local Mean Time of
        the Pacific coast and the signature of a timezone conversion done without a database.
        The stored value is kept either way -- overriding it would be a second guess on top
        of the first -- but it is reported.
        """
        if raw is None:
            return None
        value = datetime.fromisoformat(raw)
        expected = value.replace(tzinfo=self.zone).utcoffset()
        if value.tzinfo is None:
            self.notes.append(f"{label}: no offset stored; read as {self.zone.key}")
            return value.replace(tzinfo=self.zone)
        if value.utcoffset() != expected:
            self.compensate("nwb.stored_offset_kept")
            self.notes.append(
                f"{label}: stored offset {_offset(value.utcoffset())} disagrees with "
                f"{self.zone.key}'s {_offset(expected)} for {value.replace(tzinfo=None).isoformat()}; kept as stored"
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
            self.notes.append(f"{label}: {int((~finite).sum())} of {finite.size} timestamps not finite; dropped")
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
            "sex": columns.get("sex"),
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
            raise SourceDefect(f"{self.root}: no session_start_time")
        reference = _one(self._array("timestamps_reference_time"))
        metadata = {
            "nwb_identifier": _one(self._array("identifier")),
            "nwb_version": self._attrs().get("nwb_version"),
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

        return OpenEphysSource(self.attachments, session_id=self.session_id).attachments()

    @cached_property
    def _devices(self) -> list[dict[str, Any]]:
        """`core.devices`, one row per physical instrument (R67 §2.2).

        One row per *object*, not per NWB Device: a quad-base probe presents four Devices with
        one serial number, and recording four rows asserts four probes where the session had
        one. Identity is the serial the file states; the four remain four `core.probes` rows,
        which is what a probe is (§2.2). The surviving row takes the common prefix of the names
        it covers where there is one -- naming only, since the serial is what decided identity.
        """
        found: dict[str, dict[str, Any]] = {}
        attached = self._attachment()
        for name in self.store.members("general/devices"):
            described = self._attrs(f"general/devices/{name}")
            description = str(described.get("description", ""))
            parsed = DEVICE_DESCRIPTION.match(description)
            serial = parsed["serial"] if parsed else None
            attachment = attached.get(name) or {}
            row = {
                "device_id": self.prefix + name,
                "session_id": self.session_id,
                "name": name,
                "manufacturer": _clean(described.get("manufacturer")),
                "model": (parsed["model"] or None) if parsed else None,
                "serial_number": serial,
                "parent_device_id": attachment.get("parent_device_id"),
                # R85 §2.1: the dock of that headstage. Null where no attachment is stated, and
                # null is what a consumer must read as unrecorded rather than parse out of a name.
                "parent_port": attachment.get("parent_port"),
                "metadata": _described(parsed, description),
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
                row |= {"device_id": self.prefix + shared, "name": shared}
                self.notes.append(
                    f"devices: {', '.join(covers)} share serial {row['serial_number']}; "
                    f"recorded as one device named {shared} (R67 §2.2)"
                )
            rows.append(row)
        return rows

    def devices(self) -> list[dict[str, Any]]:
        """`core.devices`, computed once: it reads the store and the attachment file."""
        return self._devices

    def _device_of(self) -> dict[str, dict[str, Any]]:
        """Every NWB Device name mapped to the `core.devices` row that covers it."""
        by_name = {}
        for name in self.store.members("general/devices"):
            described = self._attrs(f"general/devices/{name}")
            parsed = DEVICE_DESCRIPTION.match(str(described.get("description", "")))
            by_name[name] = parsed["serial"] if parsed else None
        rows = {row["serial_number"]: row for row in self.devices() if row["serial_number"]}
        named = {row["name"]: row for row in self.devices()}
        return {name: rows.get(serial) or named.get(name) for name, serial in by_name.items()}

    def probes(self) -> list[dict[str, Any]]:
        """`core.probes`, one row per NWB ElectrodeGroup.

        An ElectrodeGroup is what actually recorded, which is why it -- and not the Device --
        is the probe. This file has 15 Devices and 12 groups: four of the shanks of one
        quad-base probe each get a group, and three Devices recorded nothing.
        """
        devices = self._device_of()
        rows = []
        for name in self.store.members("general/extracellular_ephys"):
            if name == "electrodes":
                continue
            described = self._attrs(f"general/extracellular_ephys/{name}")
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
                    "name": name,
                    "probe_type": device["model"] if device else None,
                    "manufacturer": device["manufacturer"] if device else None,
                    "serial_number": device["serial_number"] if device else None,
                    "target_region": _clean(described.get("location")),
                    "metadata": {"description": described["description"]} if described.get("description") else None,
                }
            )
        return rows

    def _electrode_ids(self, columns: Mapping[str, NDArray[Any]]) -> list[str]:
        """Compose electrode IDs, because no NWB column is unique on its own.

        `electrode_name` repeats -- 1920 distinct values over 4608 rows, since the shanks of
        a quad-base probe reuse the numbering -- and `channel_name` is per-probe. The pair
        (group, channel) is unique, so that is the ID.
        """
        return [
            f"{self.prefix}{group}.{channel}"
            for group, channel in zip(columns["group_name"], columns["channel_name"], strict=True)
        ]

    def electrodes(self) -> list[dict[str, Any]]:
        """`core.electrodes`, one row per recorded contact."""
        columns = self._table("general/extracellular_ephys/electrodes")
        if not columns:
            return []
        carried = ("ccf_acronym", "ccf_name", "ccf_structure_id_path", "ccf_id")
        if "inter_sample_shift" in columns:
            self.notes.append(
                "electrodes/inter_sample_shift: not emitted; R19 puts it on core.array_channels "
                "and this adapter emits no array assets"
            )
        rows = []
        for index, electrode_id in enumerate(self._electrode_ids(columns)):
            metadata = {name: _clean(columns[name][index]) for name in carried if name in columns}
            rows.append(
                {
                    "electrode_id": electrode_id,
                    "session_id": self.session_id,
                    "probe_id": self.prefix + str(columns["group_name"][index]),
                    "local_electrode_label": _clean(columns["electrode_name"][index])
                    if "electrode_name" in columns
                    else None,
                    "local_channel_label": _clean(columns["channel_name"][index]),
                    "impedance_ohm": _clean(columns["imp"][index]) if "imp" in columns else None,
                    "metadata": {k: v for k, v in metadata.items() if v is not None} or None,
                }
            )
        return rows

    def _signal_device_id(self, name: str) -> str | None:
        """Return the device a signal's description names, or None where it names none.

        R65 §2.1 asks a writer to record which instrument produced an array. This file names it
        in prose and nowhere else -- `general/devices` lists probes alone -- so the sentence is
        parsed rather than ignored. The device *row* comes from the instrument's own schema
        (`sources.harp`), which is the only place its version is stated; this is the join.
        """
        self.compensate("nwb.signal_device_declared")
        matched = SIGNAL_DEVICE.search(str(self._attrs(f"acquisition/{name}").get("description", "")))
        return self.prefix + matched["device"] if matched else None

    def electrode_coordinates(self) -> list[dict[str, Any]]:
        """`core.electrode_coordinates`, one row per electrode per populated frame.

        R19 §3 replaced one NaN-padded coordinate triple with rows per frame, and this file
        is why: `x`/`y`/`z`, the columns NWB actually specifies, are NaN for all 4608
        electrodes, while probe-relative and CCF coordinates are both populated and differ in
        coverage.
        """
        columns = self._table("general/extracellular_ephys/electrodes")
        if not columns:
            return []
        # The basis travels with the columns a value comes from rather than with the frame's
        # name (R64 §1.3): `rel_x` is the shank's own layout and so is true by construction,
        # where a CCF triple is what a registration found. `planned` cannot be imported from
        # either -- an exported file records where a probe was, never where it was aimed, and
        # a targeting record does not reach NWB.
        frames = {
            "probe": (("rel_x", "rel_y", None), "nominal"),
            "ccf": (CCF_AXES, "measured"),
        }
        rows = []
        for index, electrode_id in enumerate(self._electrode_ids(columns)):
            for frame, (axes, basis) in frames.items():
                values = [_clean(columns[axis][index]) if axis and axis in columns else None for axis in axes]
                if all(value is None for value in values):
                    continue
                rows.append(
                    {
                        "electrode_id": electrode_id,
                        "coordinate_frame": frame,
                        "coordinate_basis": basis,
                        **self._annotation(columns, index, frame),
                        "x_um": values[0],
                        "y_um": values[1],
                        "z_um": values[2],
                    }
                )
        return rows

    #: Where an exporter puts the atlas structure id. The two spellings are the same fact from
    #: two versions of one pipeline (R59 §1).
    REGION_ID = ("brain_region_id", "ccf_id")
    #: Where it puts the label. `location` is core NWB's; `ccf_acronym` is the AIND addition.
    REGION_LABEL = ("ccf_acronym", "location")

    def _annotation(self, columns: Mapping[str, Any], index: int, frame: str) -> dict[str, Any]:
        """Return the atlas annotation for one coordinate row (R59 §2.1).

        Only an atlas frame carries one: `coordinate_frame` names the atlas the structure id is
        numbered by (R59 §2.2), and a probe-relative position is in no atlas.
        """
        if frame == "probe":
            return {}
        found: dict[str, Any] = {}
        for name in self.REGION_ID:
            if name in columns and (value := _clean(columns[name][index])) is not None:
                found["region_id"] = int(value)
                break
        for name in self.REGION_LABEL:
            if name in columns and (value := _clean(columns[name][index])) is not None:
                found["region_label"] = str(value)
                break
        return found

    # -- units, which this file describes but does not date -----------------------------

    def _unit_identity(self) -> list[tuple[int, Mapping[str, str]]]:
        """NWB unit rows paired with the identity a sorter gave them, in row order.

        The NWB is derived from the sorting, so it carries the sorter's own unit id as
        `ks_unit_id` (identical to `original_cluster_id`, measured) and the probe as
        `device_name`. Those two are the join back to `core.units`, which is why the caller
        supplies the mapping rather than this adapter inventing identifiers: unit identity is
        contextual -- `(session_id, unit_id, sorting_run_id, curation_id)` -- and only the
        sorter knows the run and curation.

        The key is the file's own `device_name`, unprefixed, because it names a probe as *this
        source* calls it. A quad-base probe is four device names here (`45883-1` through `-4`)
        and one `core.probes` row, so `probe_id` cannot serve as the key.

        A row whose pair is not in the mapping is skipped, which is what a unit the packet's
        sorting does not contain should do.
        """
        if not self.units:
            return []
        columns = self._table("units")
        if not columns or "ks_unit_id" not in columns or "device_name" not in columns:
            self.notes.append("units: no ks_unit_id/device_name, so no unit-electrode link is emitted")
            return []
        paired = []
        missed = 0
        for index in range(len(columns["ks_unit_id"])):
            device = str(_clean(columns["device_name"][index]))
            label = str(int(columns["ks_unit_id"][index]))
            identity = self.units.get((device, label))
            if identity is None:
                missed += 1
                continue
            paired.append((index, identity))
        if missed:
            self.notes.append(f"units: {missed} NWB row(s) match no unit in the packet's sorting; skipped")
        return paired

    def unit_coordinates(self) -> list[dict[str, Any]]:
        """`core.unit_coordinates`, a unit's position per populated frame (R28).

        CCF only: the registration is applied downstream of the sorting, so this file is the
        authority for it, while the probe-frame position belongs to the sorter's analyzer.
        A unit whose coordinates are all absent contributes no row -- 241 of 6,781 here, the
        electrode group the session's alignment does not cover.
        """
        paired = self._unit_identity()
        if not paired:
            return []
        columns = self._table("units")
        if not any(axis in columns for axis in CCF_AXES):
            return []
        rows = []
        for index, identity in paired:
            values = [_clean(columns[axis][index]) if axis in columns else None for axis in CCF_AXES]
            if all(value is None for value in values):
                continue
            rows.append(
                {
                    "session_id": self.session_id,
                    **identity,
                    "coordinate_frame": "ccf",
                    "coordinate_basis": "measured",
                    **self._annotation(columns, index, "ccf"),
                    "x_um": values[0],
                    "y_um": values[1],
                    "z_um": values[2],
                }
            )
        return rows

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
        and on a 400 Hz thermistor each read is 5.9 M elements twice over.
        """
        if name not in self._signals:
            # A recipe declares its signals, because whether a stream is one is a fact about
            # the instrument. Saying so about a stream the file lacks is a contradiction R63 §2
            # refuses in a recipe, and it surfaced here as a Zarr encoding error naming a path
            # rather than the declaration that asked for it.
            if not self.store.is_array(f"acquisition/{name}/timestamps"):
                held = ", ".join(self.store.members("acquisition")) or "nothing"
                raise SourceDefect(
                    f"the recipe declares signal {name!r} and this NWB has no "
                    f"acquisition/{name} with timestamps; acquisition holds {held}"
                )
            seconds = self.store.array(f"acquisition/{name}/timestamps")
            ticks, finite = self._ticks(seconds, f"acquisition/{name}")
            values = self._array(f"acquisition/{name}/data")
            self._signals[name] = (ticks, values[finite] if values.size == seconds.size else values)
        return self._signals[name]

    def staged_arrays(self) -> list[Any]:
        """Return the signal arrays and their coordinate arrays, for `add_array`.

        Two per signal. The values are the measurement; the ticks are its axis, which R20 §2.3
        requires as an array because the axis is not regular -- a HARP device dispatching at
        400 Hz on a 31,250 Hz counter lands on 78 or 79 ticks depending on the phase, so no
        step describes it and R33's rational form would cost 30 ms over a session.
        """
        from ..writer import StagedArray

        staged = []
        for name in self.signals:
            ticks, values = self._signal(name)
            del ticks  # the axis is a clock and its anchors, not an array (R20 §2.1)
            # Measured on this thermistor's 5,881,692 samples: delta takes the signal from
            # 11.8 MB to 3.47, because it is smooth at 400 Hz. R14 §2.2 permits any codec so
            # long as the manifest names it, which `declared_codecs` does, and Zarr.jl carries
            # delta -- R3 §1 targets Python and Julia.
            staged.append(
                StagedArray(
                    values=values,
                    array_asset_id=f"{self.prefix}{name}",
                    chunks=(min(len(values), 1 << 20),),
                    codecs=("numcodecs.delta", "blosc"),
                )
            )
        return staged

    def array_assets(self) -> list[dict[str, Any]]:
        """`core.array_assets`, two rows per signal: the values and their tick coordinates."""
        rows = []
        for name in self.signals:
            ticks, _ = self._signal(name)
            attrs = self._attrs(f"acquisition/{name}")
            span = int(ticks[-1] - ticks[0]) if len(ticks) > 1 else 0
            rate = (len(ticks) - 1) * self.clock.tick_rate_num / span if span else None
            rows.append(
                {
                    "session_id": self.session_id,
                    "array_asset_id": f"{self.prefix}{name}",
                    # R65 §2.1: which instrument made this array. Read from the same description
                    # `_signal_devices` declares the device from, so the two cannot disagree.
                    "device_id": self._signal_device_id(name),
                    "semantic_type": "signal",
                    "name": str(attrs.get("description") or name),
                    "kind": "dense_array_asset",
                    "uri": f"arrays/core/{name}.zarr",
                    "format": "zarr_v3",
                    "clock_id": self._dispatch_clock_id(name),
                    "sample_rate_hz": round(rate, 6) if rate else None,
                    "unit": str(self._attrs(f"acquisition/{name}/data").get("unit") or "") or None,
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
        each message carries, because the timer and the timestamp count different oscillators
        -- 2 ppm apart here, which over a session reaches 924 ticks. R20 §2.1 puts exactly
        that difference in `core.clock_anchors` rather than in the axis.
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
                    "name": f"{name} dispatch counter",
                    "tick_rate_hz": round(rate, 6) if rate else None,
                    "tick_rate_num": round(rate) if rate else None,
                    "tick_rate_den": 1 if rate else None,
                    "origin": "the device's first dispatched sample; tick k is sample k",
                    "parent_clock_id": self.clock.clock_id,
                }
            )
        return rows

    def signal_anchors(self, every: int = 10_000) -> list[dict[str, Any]]:
        """`core.clock_anchors`, relating each dispatch counter to the reference clock.

        Every sample carries its own HARP timestamp, so every anchor here is measured and none
        is fitted. They are subsampled because they need only bound the interpolation error
        R40 §2 governs: at the 2 ppm separating the two oscillators, anchors 25 s apart leave
        far less than one tick between them, where the tolerance is 3 ms.
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
        recorded*. That is the truth for these streams: lick detection is capacitance
        thresholding done online in the rig, and reward delivery is logged by the valve.
        """
        rows = []
        for name, _, _ in self._series():
            rows.append(
                {
                    "event_stream_id": self.prefix + name,
                    "session_id": self.session_id,
                    "name": name,
                    "clock_id": self.clock.clock_id,
                    "metadata": {"description": self._attrs(f"acquisition/{name}").get("description")},
                }
            )
        for column, kind in self._trial_event_columns():
            rows.append(
                {
                    "event_stream_id": self.prefix + kind,
                    "session_id": self.session_id,
                    "name": kind,
                    "clock_id": self.clock.clock_id,
                    "metadata": {"description": f"intervals/trials/{column}, one per trial"},
                }
            )
        return rows

    def _trial_event_columns(self) -> list[tuple[str, str]]:
        """Trial columns that carry a moment, in the order `TRIAL_EVENTS` names them."""
        columns = self._table("intervals/trials")
        return [(name, kind) for name, kind in TRIAL_EVENTS.items() if name in columns]

    def events(self) -> list[dict[str, Any]]:
        """`core.events`, one row per timestamp on an acquisition TimeSeries.

        `event_id` embeds the value's zero-based offset into its source array, which is an
        identifier and not a position -- it is what makes the row traceable back to the NWB.
        """
        rows = []
        for name, seconds, data in self._series():
            ticks, finite = self._ticks(seconds, f"acquisition/{name}")
            offsets = np.flatnonzero(finite)
            payloads = data[finite] if data.size == seconds.size else None
            # `data` is a constant marker on every stream here; carrying 3184 copies of 1.0
            # would be noise, so it travels only when it varies.
            varies = payloads is not None and payloads.size > 0 and len(np.unique(payloads)) > 1
            for tick, offset, position in zip(ticks, offsets, range(len(ticks)), strict=True):
                row: dict[str, Any] = {
                    "session_id": self.session_id,
                    "event_id": f"{name}:{int(offset)}",
                    "stream_id": self.prefix + name,
                    "event_type": name.removesuffix("_time"),
                    "t_tick": int(tick),
                    "clock_id": self.clock.clock_id,
                }
                if varies and payloads is not None:
                    row["payload"] = {"value": _clean(payloads[position])}
                rows.append(row)
        rows.extend(self._trial_events())
        return rows

    def _trial_events(self) -> list[dict[str, Any]]:
        """`core.events` for the moments a task recorded as trial columns.

        A trial that did not reach one -- no go cue because the animal never engaged -- has NaN
        there, and no event happened, so no row is emitted. That is why these cannot simply be
        columns on `core.trials`: absence is a fact about the trial, not a null to carry.
        """
        columns = self._table("intervals/trials")
        if not columns:
            return []
        identifiers = columns.get("id", np.arange(len(columns["start_time"])))
        rows = []
        for column, kind in self._trial_event_columns():
            ticks, finite = self._ticks(columns[column], f"intervals/trials/{column}")
            for tick, index in zip(ticks, np.flatnonzero(finite), strict=True):
                rows.append(
                    {
                        "session_id": self.session_id,
                        "event_id": f"{kind}:{int(identifiers[index])}",
                        "stream_id": self.prefix + kind,
                        "event_type": kind,
                        "t_tick": int(tick),
                        "clock_id": self.clock.clock_id,
                        # No payload naming the interval. R11 §5 struck `core.events.trial_id`,
                        # and carrying the same reference as JSON keeps the letter of that while
                        # defeating it: untyped, unjoinable, and invisible to every check. R54 §3
                        # settles what replaces it -- an event belongs to whatever intervals
                        # contain it, which may be none or several, and containment is a query
                        # against `core.intervals` rather than a column.
                    }
                )
        return rows

    def intervals(self) -> list[dict[str, Any]]:
        """`core.intervals`, one row per trial (R54 §2.1)."""
        if self.interval_kind is None:
            raise SourceDefect(
                "core.intervals needs an interval_kind naming the resource that specialises these "
                "intervals (R54 §2.1); set it on the nwb source"
            )
        columns = self._table("intervals/trials")
        if not columns:
            return []
        for required in ("start_time", "stop_time"):
            if required not in columns:
                raise SourceDefect(f"intervals/trials has no {required}")
        for edge in ("start_time", "stop_time"):
            if not np.isfinite(columns[edge]).all():
                missing = int((~np.isfinite(columns[edge])).sum())
                raise SourceDefect(f"intervals/trials: {missing} trials have no {edge}, so they are not intervals")
        start = self.clock.ticks(columns["start_time"])
        stop = self.clock.ticks(columns["stop_time"])
        identifiers = columns.get("id", np.arange(len(start)))
        unmapped = [name for name in columns if name not in TRIAL_MAPPED and name != "id"]
        varying = self._trial_parameters(columns, unmapped, len(start))
        rows = []
        for index in range(len(start)):
            row: dict[str, Any] = {
                "session_id": self.session_id,
                # Carried (R53 §2.3): intervals/trials/id is already int64 and already 0..n,
                # so the writer passes it through rather than composing a string from it.
                "interval_kind": self.interval_kind,
                "interval_id": int(identifiers[index]),
                "start_tick": int(start[index]),
                "stop_tick": int(stop[index]),
                "clock_id": self.clock.clock_id,
            }
            # R54 §2.5: off unless a recipe asks. The keys that vary are the ones an extension
            # declares as typed columns, so filling this duplicates them as unqueryable JSON.
            if self.trial_metadata and varying:
                row["metadata"] = {name: columns[name][index] for name in varying}
            rows.append(row)
        return rows

    def _trial_parameters(self, columns: Mapping[str, NDArray[Any]], unmapped: list[str], n: int) -> list[str]:
        """Split unmapped trial columns into what varies per trial and what does not.

        A task parameter that never changes across a session is not trial data; recording it on
        every trial restates one fact `n` times, which R3 §3.0 forbids for the same reason a
        repeated value becomes a child table. Measured on a real session: 49 of 59 keys are
        constant, so 34,692 of the 41,772 values stored were copies.

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
            "core.subjects": self.subjects(),
            "core.sessions": self.sessions(),
            "core.clocks": ([self.clock.record()] if self.emit_clock else []) + self.signal_clocks(),
            "core.devices": self.devices(),
            "core.probes": self.probes(),
            "core.electrodes": self.electrodes(),
            "core.electrode_coordinates": self.electrode_coordinates(),
            "core.unit_coordinates": self.unit_coordinates(),
            "core.event_streams": self.event_streams(),
            "core.events": self.events(),
            "core.intervals": self.intervals(),
            "core.clock_anchors": self.signal_anchors(),
            "core.array_assets": self.array_assets(),
            "core.array_dimensions": self.array_dimensions(),
        }
        return {resource: rows for resource, rows in built.items() if rows}

    def into(self, writer: Any) -> dict[str, int]:
        """Add every record to a :class:`~escapewheel_writer.writer.PacketWriter`.

        Parameters
        ----------
        writer : PacketWriter
            The writer to add to. Nothing is committed here.

        Returns
        -------
        dict
            Row counts per resource ID.
        """
        counted = {}
        for resource, rows in self.records().items():
            writer.add(resource, rows)
            counted[resource] = len(rows)
        return counted

    def offers(self) -> dict[str, int]:
        """Which resources this source supplies from its root, and how many rows (`05` §1)."""
        return {resource: len(rows) for resource, rows in self.records().items()}


def _described(parsed: Any, raw: str) -> dict[str, str] | None:
    """Return what a device's description says beyond its model and serial, or nothing.

    The raw string is kept only where it did not parse: carrying both a parsed description and
    the sentence it came from would store one fact twice (R3 §3.0).
    """
    if parsed is None:
        return {"description": raw} if raw else None
    return {"description": parsed["description"]} if parsed["description"] else None


def _offset(delta: Any) -> str:
    """Render a UTC offset the way a timestamp writes it, not the way a timedelta prints."""
    if delta is None:
        return "none"
    minutes = round(delta.total_seconds() / 60)
    return f"{'-' if minutes < 0 else '+'}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


def _resolve(root: Path) -> Path:
    """Accept either the ``.nwb`` directory or the asset directory holding one."""
    if (root / ".zgroup").is_file():
        return root
    candidates = sorted(child for child in root.iterdir() if child.suffix == ".nwb" and child.is_dir())
    if len(candidates) == 1:
        return candidates[0]
    raise SourceDefect(f"{root} is not an NWB-Zarr directory and holds {len(candidates)} of them")


__all__ = ["ABSENT", "NWBSource", "SourceDefect"]

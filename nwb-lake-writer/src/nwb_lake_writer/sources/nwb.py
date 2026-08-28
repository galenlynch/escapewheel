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
grid. Recovering ticks would mean fitting a rate and an offset, and :class:`~nwb_lake_writer.clock.Clock`
refuses that by design. Units come from the sorter, which still has its sample indices.

The clock is a parameter, not a discovery
-----------------------------------------

Nothing in an NWB declares a time base: `timestamps` are seconds, and NWB's contract says
they are relative to `session_start_time`. In this file they are not -- they are on the HARP
epoch, 134 days earlier (§3.1). So the caller passes the :class:`~nwb_lake_writer.clock.Clock`
these times are on, and every conversion is checked against its grid. A wrong clock does not
produce wrong ticks; it produces :class:`~nwb_lake_writer.clock.OffGrid`.

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
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import NDArray

from ..clock import Clock
from .zarr_compat import UnsupportedEncoding, attrs, members, read_array

#: NWB writes the literal string ``None`` where a value is absent -- in `laser_location`,
#: `auto_train_stage`, `was_generated_by`. Treated as null when mapped into a typed core
#: column; left verbatim inside metadata, which is a faithful copy of the source.
ABSENT = {"", "None", "none", "nan", "NaN"}

#: ``Model: <model> - Serial number: <serial>``, which is how `aind-data-schema` renders a
#: probe into an NWB `Device` description. The model itself contains hyphens.
DEVICE_DESCRIPTION = re.compile(r"^Model:\s*(?P<model>.+?)\s*-\s*Serial number:\s*(?P<serial>.+?)\s*$")

#: `animal_response` in AIND's dynamic-foraging trials, per the column's own description.
CHOICE = {0.0: "left", 1.0: "right", 2.0: "none"}

#: Trial columns this adapter maps into `core.trials`; the rest go to its metadata verbatim.
TRIAL_MAPPED = frozenset({"start_time", "stop_time", "animal_response", "rewarded_historyL", "rewarded_historyR"})

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


class NWBSource:
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
    trial_metadata : bool, default True
        Carry every unmapped trial column into `core.trials.metadata` as JSON. This file has
        67 trial columns and `02` defines 5 of them; the rest are dynamic-foraging task
        parameters with no core home until an extension registry (R17) gives them one.

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

    def __init__(
        self,
        root: str | Path,
        *,
        clock: Clock,
        zone: ZoneInfo,
        session_id: str | None = None,
        prefix: str = "",
        trial_metadata: bool = True,
    ) -> None:
        if not isinstance(zone, ZoneInfo):
            raise TypeError(f"{zone!r} is a fixed offset; pass an IANA zone so DST resolves per date")
        self.root = _resolve(Path(root))
        self.clock = clock
        self.zone = zone
        self.prefix = prefix
        self.trial_metadata = trial_metadata
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
        target = self.root / path
        if not (target / ".zarray").is_file():
            return np.empty(0)
        return read_array(target)

    def _attrs(self, path: str = "") -> dict[str, Any]:
        """Read one node's attributes."""
        return attrs(self.root / path)

    def _table(self, path: str) -> dict[str, NDArray[Any]]:
        """Read an hdmf table's columns, skipping any this package will not decode.

        Cached: a table is consulted by more than one builder, and re-reading it would
        repeat every note it produced.
        """
        if path in self._cache:
            cached: dict[str, NDArray[Any]] = self._cache[path]
            return cached
        node = self.root / path
        out: dict[str, NDArray[Any]] = {}
        if node.is_dir():
            for name in members(node):
                if not (node / name / ".zarray").is_file():
                    continue
                try:
                    out[name] = read_array(node / name)
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
        columns = {
            name: _one(self._array(f"general/subject/{name}")) for name in members(self.root / "general/subject")
        }
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

    def devices(self) -> list[dict[str, Any]]:
        """`core.devices`, one row per NWB Device."""
        rows = []
        for name in members(self.root / "general/devices"):
            described = self._attrs(f"general/devices/{name}")
            description = str(described.get("description", ""))
            parsed = DEVICE_DESCRIPTION.match(description)
            rows.append(
                {
                    "device_id": self.prefix + name,
                    "session_id": self.session_id,
                    "name": name,
                    "manufacturer": _clean(described.get("manufacturer")),
                    "model": parsed["model"] if parsed else None,
                    "serial_number": parsed["serial"] if parsed else None,
                    "metadata": {"description": description} if description else None,
                }
            )
        return rows

    def probes(self) -> list[dict[str, Any]]:
        """`core.probes`, one row per NWB ElectrodeGroup.

        An ElectrodeGroup is what actually recorded, which is why it -- and not the Device --
        is the probe. This file has 15 Devices and 12 groups: four of the shanks of one
        quad-base probe each get a group, and three Devices recorded nothing.
        """
        devices = {row["name"]: row for row in self.devices()}
        rows = []
        for name in members(self.root / "general/extracellular_ephys"):
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
                    "brain_region": _clean(columns["location"][index]) if "location" in columns else None,
                    "impedance_ohm": _clean(columns["imp"][index]) if "imp" in columns else None,
                    "metadata": {k: v for k, v in metadata.items() if v is not None} or None,
                }
            )
        return rows

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
        frames = {"probe": ("rel_x", "rel_y", None), "ccf": CCF_AXES}
        rows = []
        for index, electrode_id in enumerate(self._electrode_ids(columns)):
            for frame, axes in frames.items():
                values = [_clean(columns[axis][index]) if axis and axis in columns else None for axis in axes]
                if all(value is None for value in values):
                    continue
                rows.append(
                    {
                        "electrode_id": electrode_id,
                        "coordinate_frame": frame,
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
        for name in members(acquisition):
            if not (acquisition / name / "timestamps" / ".zarray").is_file():
                continue
            yield name, read_array(acquisition / name / "timestamps"), self._array(f"acquisition/{name}/data")

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
        return rows

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
        return rows

    def trials(self) -> list[dict[str, Any]]:
        """`core.trials`, one row per trial."""
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
        rewarded = [
            bool(columns.get("rewarded_historyL", np.zeros(len(start), bool))[i])
            or bool(columns.get("rewarded_historyR", np.zeros(len(start), bool))[i])
            for i in range(len(start))
        ]
        unmapped = [name for name in columns if name not in TRIAL_MAPPED and name != "id"]
        rows = []
        for index in range(len(start)):
            row: dict[str, Any] = {
                "session_id": self.session_id,
                "trial_id": f"{self.prefix}trial_{int(identifiers[index]):04d}",
                "start_tick": int(start[index]),
                "stop_tick": int(stop[index]),
                "clock_id": self.clock.clock_id,
                "rewarded": rewarded[index],
            }
            if "animal_response" in columns:
                row["choice"] = CHOICE.get(float(columns["animal_response"][index]))
            if self.trial_metadata and unmapped:
                row["metadata"] = {name: columns[name][index] for name in unmapped}
            rows.append(row)
        return rows

    # -- assembly ---------------------------------------------------------------------

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
            "core.clocks": [self.clock.record()],
            "core.devices": self.devices(),
            "core.probes": self.probes(),
            "core.electrodes": self.electrodes(),
            "core.electrode_coordinates": self.electrode_coordinates(),
            "core.event_streams": self.event_streams(),
            "core.events": self.events(),
            "core.trials": self.trials(),
        }
        return {resource: rows for resource, rows in built.items() if rows}

    def into(self, writer: Any) -> dict[str, int]:
        """Add every record to a :class:`~nwb_lake_writer.writer.PacketWriter`.

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


__all__ = ["ABSENT", "CHOICE", "NWBSource", "SourceDefect"]

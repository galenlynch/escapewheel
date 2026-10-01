"""Read an NWB written by an AIND pipeline, with the columns that pipeline adds.

- :class:`AindNWBSource` -- the base NWB adapter, extended to interpret the columns an AIND
  pipeline adds and the conventions it follows.

The added columns sit in the same rows as the standard ones, and one source supplies each row
(Part 05 §3.4), so this is a subclass of the base adapter and not a second adapter. A recipe names
this kind or the base kind.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, ClassVar

from escapewheel_reader.resource_ids import CORE_UNIT_COORDINATE_VALUES, CORE_UNIT_COORDINATES
from escapewheel_writer.adapter import FILES, FLIGHT, STREAM, Note, NWBSource, clean

from .notes import AindNote

#: ``Model: <model> - Serial number: <serial>``, which is how `aind-data-schema` renders a probe
#: into an NWB `Device` description. The model itself contains hyphens, so the serial is bounded
#: explicitly rather than by end-of-line: a lazy `.+?` anchored to `$` swallows the description
#: after it into the serial number.
DEVICE_DESCRIPTION = re.compile(
    r"^Model:\s*(?P<model>.*?)\s*-\s*Serial number:\s*(?P<serial>[^\s-]+)"
    r"(?:\s*-\s*Description:\s*(?P<description>.*?))?\s*$"
)

#: The instrument behind an acquired signal, named in the signal's description because
#: `general/devices` lists probes alone -- "imported from HARP SniffDetector__32.bin". A signal
#: acquired by a separate workflow has no rig metadata in this packet's sources at all, so this
#: sentence is the only statement of what made the array that reaches the importer.
SIGNAL_DEVICE = re.compile(r"\bfrom\s+(?P<bus>HARP)\s+(?P<device>[A-Za-z0-9]+?)__(?P<register>\d+)\b")

#: The CCF columns this pipeline writes, in the order they become a frame's axes.
CCF_AXES = ("ccf_ml", "ccf_ap", "ccf_dv")


class AindNWBSource(NWBSource):
    """An AIND-written NWB, read as base NWB plus the columns this pipeline adds.

    The base reader's behaviour is unchanged. Its hooks are filled here to interpret the seventeen
    columns an AIND pipeline adds and the three conventions it follows, which ``DESIGN.md`` lists.
    """

    #: Two frames rather than one. `rel_x` and `rel_y` are core 2.9.0's; the CCF triple is this
    #: pipeline's, and two of its exporters disagree about which names to use.
    FRAME_AXES: ClassVar[dict[str, tuple[str, ...]]] = {
        "probe": ("rel_x", "rel_y"),
        "ccf": CCF_AXES,
    }

    #: Part 01 §3.8: the basis travels with the columns a value comes from rather than with the frame's
    #: name. A shank position is true by construction; a CCF triple is what a registration found.
    FRAME_BASIS: ClassVar[dict[str, str]] = {"probe": "nominal", "ccf": "measured"}

    #: A unit's position is the same registration applied downstream of the sorting, so this file
    #: is its authority; the probe-frame position belongs to the sorter's analyzer.
    UNIT_AXES: ClassVar[tuple[str, ...]] = CCF_AXES
    UNIT_FRAME: ClassVar[str] = "ccf"

    #: Trial columns that are *events*, and the type each becomes. A task writes these into its
    #: trials table because they happen once a trial; a moment on a clock is an event whatever
    #: table it arrives in, so they belong in `core.events` where a query finds them without
    #: knowing which task shape put them there.
    TRIAL_EVENTS: ClassVar[dict[str, str]] = {
        "goCue_start_time": "go_cue",
        "reward_outcome_time": "reward_outcome",
        "delay_start_time": "delay_start",
    }

    #: `animal_response` and the reward histories are named although core declares no column for
    #: them: naming them is what keeps them out of `core.intervals.metadata` rather than
    #: swept in as unmapped, since they belong to the task's own extension.
    TRIAL_MAPPED: ClassVar[frozenset[str]] = frozenset(
        {
            "start_time",
            "stop_time",
            "animal_response",
            "rewarded_historyL",
            "rewarded_historyR",
            "goCue_start_time",
            "reward_outcome_time",
            "delay_start_time",
        }
    )

    #: Part 02 §8.6: `ccf_id` and `ccf_acronym` are columns of `core.electrode_coordinates` and
    #: these two are not modelled (R59 §2), so the bag is where they belong -- only what no column
    #: holds may travel in it.
    CARRIED_ELECTRODE: ClassVar[tuple[str, ...]] = ("ccf_name", "ccf_structure_id_path")

    #: Where an exporter puts the atlas structure id. The two spellings are one fact from two
    #: versions of one pipeline.
    REGION_ID: ClassVar[tuple[str, ...]] = ("brain_region_id", "ccf_id")
    #: Where it puts the label. `location` is core NWB's; `ccf_acronym` is this pipeline's.
    REGION_LABEL: ClassVar[tuple[str, ...]] = ("ccf_acronym", "location")

    #: Part 12 §3: released apart from the writer, so it declares its protocols. `escapewheel
    #: deliver` serves every one; the first is what a build reaches it by when a recipe names none.
    PROTOCOLS: ClassVar[tuple[str, ...]] = (STREAM, FILES, FLIGHT)

    PRODUCES = NWBSource.PRODUCES | {CORE_UNIT_COORDINATES, CORE_UNIT_COORDINATE_VALUES}

    #: `units` is what the base reader does not need: this adapter joins an NWB unit row to the
    #: identity the build assigned, so the build must supply it (Part 12 §4).
    NEEDS: ClassVar[tuple[str, ...]] = (*NWBSource.NEEDS, "units")

    def device_identity(self, described: Mapping[str, Any]) -> dict[str, Any]:
        """Return the model and serial this pipeline packs into a Device's description.

        It sets none of the three attributes core 2.9.0 declares for them, so the sentence is
        parsed rather than ignored. The raw string is kept only where it did not parse, since
        keeping both would store one fact twice (Part 02 §6).
        """
        raw = str(described.get("description", ""))
        parsed = DEVICE_DESCRIPTION.match(raw)
        if parsed is None:
            return {"model": None, "serial_number": None, "metadata": {"description": raw} if raw else None}
        return {
            "model": parsed["model"] or None,
            "serial_number": parsed["serial"],
            "metadata": {"description": parsed["description"]} if parsed["description"] else None,
        }

    def local_electrode_label(self, columns: Mapping[str, Any], index: int) -> str | None:
        """Return this pipeline's own name for a contact, which repeats and so cannot identify one.

        The shanks of a quad-base probe reuse the numbering, so it is a label and not an
        identifier.
        """
        if "electrode_name" not in columns:
            return None
        value = clean(columns["electrode_name"][index])
        return None if value is None else str(value)

    def signal_device_id(self, name: str) -> str | None:
        """Return the instrument a signal's description names, or None where it names none.

        Part 01 §3.17 asks a writer to record which instrument made an array, and this file says so
        in prose alone. The device *row* comes from the instrument's own schema, which is the only
        place its version is stated; this is the join.
        """
        self.compensate("nwb.signal_device_declared")
        matched = SIGNAL_DEVICE.search(str(self.attrs(f"acquisition/{name}").get("description", "")))
        return self.prefix + matched["device"] if matched else None

    def annotation(self, columns: Mapping[str, Any], index: int, frame: str) -> dict[str, Any]:
        """Return the atlas annotation for one coordinate row (Part 01 §3.8).

        Only an atlas frame carries one, the frame being the space the structure id is numbered in
        (Part 01 §3.24), so a probe-relative position gets nothing.
        """
        if frame != "ccf":
            return {}
        found: dict[str, Any] = {}
        for name in self.REGION_ID:
            if name in columns and (value := clean(columns[name][index])) is not None:
                found["region_id"] = int(value)
                break
        for name in self.REGION_LABEL:
            if name in columns and (value := clean(columns[name][index])) is not None:
                found["region_label"] = str(value)
                break
        return found

    def unit_identity(self) -> list[tuple[int, dict[str, Any]]]:
        """Return NWB unit rows paired with the identity the build assigned them, in row order.

        The join is `(device_name, ks_unit_id)`: the probe plus the sorter's own label, which this
        file carries because it was derived from the sorting. A run is one probe and runs
        reuse labels, so the probe is what makes the pair unique.

        The key uses the file's own `device_name`, unprefixed, because it names a probe as *this
        source* calls it -- a quad-base probe is four device names here and one `core.probes` row,
        so `probe_id` cannot serve. A row whose pair the build did not supply is skipped, which is
        what a unit the packet's sorting does not contain should do.
        """
        if not self.units:
            return []
        columns = self.table("units")
        if not columns or "ks_unit_id" not in columns or "device_name" not in columns:
            self.notes.append(
                Note("units: no ks_unit_id/device_name, so no unit coordinate is emitted", AindNote.NO_UNIT_NAMES)
            )
            return []
        paired: list[tuple[int, dict[str, Any]]] = []
        missed = 0
        for index in range(len(columns["ks_unit_id"])):
            device = str(clean(columns["device_name"][index]))
            label = str(int(columns["ks_unit_id"][index]))
            unit_id = self.units.get((device, label))
            if unit_id is None:
                missed += 1
                continue
            paired.append((index, {"unit_id": unit_id}))
        if missed:
            self.notes.append(
                Note(
                    f"units: {missed} NWB row(s) match no unit in the packet's sorting; skipped",
                    AindNote.UNIT_UNMATCHED,
                )
            )
        return paired


__all__ = ["CCF_AXES", "DEVICE_DESCRIPTION", "SIGNAL_DEVICE", "AindNWBSource"]

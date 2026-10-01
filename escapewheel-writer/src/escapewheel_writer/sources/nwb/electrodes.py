"""`core.electrodes` and the coordinates of electrodes and units from an NWB file."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from numpy.typing import NDArray

from ...notes import Note, NoteCode
from .file import NWBFile
from .names import clean, contact_ids


class Electrodes(NWBFile):
    """The contacts an NWB file lists, the frames it places them in, and a unit's position."""

    #: Part 01 §3.24: the unit every coordinate this adapter writes is in. No NWB states one; what
    #: makes this the packet's answer is that this adapter passed the values through unconverted,
    #: and micrometres is what the files it reads hold.
    COORDINATE_UNIT: ClassVar[str] = "um"

    #: Part 02 §12.7: each frame's axes in index order, named for the field the values are read
    #: from. The name is carried verbatim (Part 01 §3.24) -- `rel_x` says the packet's axis 0 holds
    #: what this file called `rel_x`, which is a fact, where calling it `across_shank` would be a
    #: claim no source supports and calling it `x` would discard where the value came from.
    #:
    #: One frame here. `rel_x` and `rel_y` are columns core 2.9.0 declares on its electrodes table;
    #: an atlas frame is a producer's addition, and a dialect adds it by extending this.
    FRAME_AXES: ClassVar[dict[str, tuple[str, ...]]] = {"probe": ("rel_x", "rel_y")}

    #: Part 01 §3.8: the basis travels with the columns a value comes from rather than with the
    #: frame's name. `rel_x` is the shank's own layout and so is true by construction, where a
    #: CCF triple is what a registration found. `planned` cannot be imported from either -- an
    #: exported file records where a probe was, never where it was aimed, and a targeting record
    #: does not reach NWB.
    FRAME_BASIS: ClassVar[dict[str, str]] = {"probe": "nominal"}

    #: The axes a *unit* carries a position on, which base NWB gives none of: `Units` declares
    #: `spike_times`, `electrodes` and the waveform columns, and no coordinate.
    UNIT_AXES: ClassVar[tuple[str, ...]] = ()

    #: The frame those axes are in, and what a position in it claims. Empty while
    #: `UNIT_AXES` is, since a frame with no axes names nothing; a dialect sets both together.
    UNIT_FRAME: ClassVar[str] = ""
    UNIT_BASIS: ClassVar[str] = "measured"

    #: Electrode columns carried into `core.electrodes.metadata` verbatim (Part 02 §8.6). Empty
    #: here: every column core 2.9.0 declares is either mapped or unread, so nothing is left over.
    CARRIED_ELECTRODE: ClassVar[tuple[str, ...]] = ()

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
                    "electrodes/inter_sample_shift: not emitted; it belongs on core.array_channels "
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

        Rows per frame rather than one NaN-padded triple: a file may leave `x`/`y`/`z`,
        the columns NWB specifies, NaN for every electrode while it populates other frames whose
        coverage differs.
        """
        return [row for row, _values in self._electrode_positions()]

    def electrode_coordinate_values(self) -> list[dict[str, Any]]:
        """`core.electrode_coordinate_values`, one row per axis of each coordinate (Part 01 §3.8).

        An axis this file leaves empty gets no row. That is a position the source did not state
        on that axis, which a consumer may not read as a zero (Part 02 §12.7).
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

        `atlas` and `atlas_version` are null. Base NWB names neither, and that section forbids
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
        """`core.unit_coordinates`, a unit's position per populated frame.

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


__all__ = ["Electrodes"]

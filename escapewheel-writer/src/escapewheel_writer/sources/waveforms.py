"""Read each unit's mean waveform from the analyzer that computed it.

- :class:`WaveformSource` -- an analyzer's templates as a sparse int16 array, and its tables.
- :data:`ANALYZERS` -- the directory SpikeInterface writes analyzers under.

The adapter reads the analyzer rather than the NWB exported from it: the analyzer states each
unit's contacts, its label and the unit of measure of its values, and the export loses all three.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from escapewheel_reader.resource_ids import (
    CORE_ARRAY_ASSET_INSTANCES,
    CORE_ARRAY_ASSETS,
    CORE_ARRAY_DIMENSIONS,
    CORE_ARRAY_LABELS,
    CORE_ELECTRODES,
    CORE_UNIT_ELECTRODES,
    CORE_UNITS,
)
from numpy.typing import NDArray

from ..errors import SourceDefect, SourceFault
from ..notes import Note, NoteCode
from .sorter import STREAM, SortedStream
from .store import SourceStore, source_root
from .zarr_compat import DenseV2, attrs, attrs_at

#: Where SpikeInterface writes the analyzer, beside the `curated` tree a sorting is read from.
ANALYZERS = "postprocessed"

#: The extension holding the templates, and the operator each quantity is stored under.
TEMPLATES = "extensions/templates"
MEAN, DEVIATION = "average", "std"


@dataclass
class _Template:
    """One unit's template cut to its own contacts, and the ordinal of its trough contact."""

    electrodes: list[str]
    primary: int
    slab: NDArray[np.float64]
    sd_slab: NDArray[np.float64] | None


@dataclass
class _Kept:
    """What the pass over every stream kept, keyed by unit, and the separate reasons it kept less.

    A unit matching nothing means the build's sorting and this analyzer disagree about which
    units exist; one sparse on no contact means the mask says the template was computed nowhere.
    One count covering both would hide the first behind the second.
    """

    templates: dict[Any, _Template] = field(default_factory=dict)
    peak: float = 0.0
    sd_peak: float = 0.0
    empty: set[Any] = field(default_factory=set)
    missed: int = 0
    blank: int = 0


def _dense(path: Any) -> DenseV2:
    """Open a multi-dimensional Zarr v2 array, wherever it is stored.

    `DenseV2` asks a path only whether it is a file and for its bytes, so a sorted asset on a
    store reads exactly as a local one does -- which is what lets a recipe name the same `s3://`
    prefix for this source and for the sorter, and have the unit ids line up by construction.
    """
    return DenseV2(path)


class WaveformSource:
    """A SpikeInterface analyzer's templates, as a sparse int16 array and the tables describing it.

    Parameters
    ----------
    root : str or Path
        The `postprocessed` directory, or an asset directory containing one.
    session_id : str
        The session these units belong to.
    units : sequence of Mapping
        One record per unit, as the build supplies it: `device_name` and `local_unit_label`, which
        are the stream's probe and the sorter's own label for the unit, and the `unit_id` assigned.
        A unit the packet's sorting does not contain is skipped rather than stored as padding, and
        every unit it does contain has a position, stored with no channels where it has no template.
    experiment : str, optional
        Restrict to one experiment, as `SorterSource` does. Each experiment restarts its sample
        index, so its streams are not comparable with another's.
    array_asset_id, sd_asset_id : str
        Identifiers for the mean and the deviation.
    sd : bool
        Also read the deviation and store it as a second array. Off by default: it doubles what
        the read holds, and a packet wanting only the template should not pay for it.
    compressed_per_chunk : float
        Expected compressed bytes per chunk, which is what `arrays.shard_for` sizes a shard
        against.
    prefix : str
        Prepended to identifiers this adapter mints, including the contact names it composes. It
        MUST match what the adapter owning `core.electrodes` uses, since a name is what the writer
        numbers.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    """

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset(
        {
            CORE_ARRAY_ASSETS,
            CORE_ARRAY_DIMENSIONS,
            CORE_ARRAY_LABELS,
            CORE_UNIT_ELECTRODES,
        }
    )

    #: Part 05 §3.4: what of `PRODUCES` this adapter supplies only part of, which a source entry
    #: without `owns` contributes rather than owns.
    CONTRIBUTES = frozenset(
        {
            CORE_ARRAY_ASSETS,
            CORE_ARRAY_DIMENSIONS,
            CORE_ARRAY_LABELS,
        }
    )

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply, resolved against Part 12 §4's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "units", "array_location")

    #: Part 05 §3.4: options this adapter reads and can run without, which a recipe may leave
    #: unset (Part 12 §4). `store` is absent because it is a handle, which a recipe cannot
    #: carry and a declaration may not name.
    ACCEPTS: ClassVar[tuple[str, ...]] = (
        "array_asset_id",
        "sd",
        "sd_asset_id",
        "compressed_per_chunk",
        "prefix",
        "experiment",
        "source_cache",
    )

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ("sorter",)

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        units: Sequence[Mapping[str, Any]],
        experiment: str | None = None,
        array_asset_id: str = "waveform_mean",
        sd: bool = False,
        sd_asset_id: str = "waveform_sd",
        compressed_per_chunk: float = 3850.0,
        prefix: str = "",
        array_location: str | None = None,
        store: Any = None,
        source_cache: str | None = None,
    ) -> None:
        path = source_root(root, cache=source_cache)
        self.root = path if path.name == ANALYZERS else path / ANALYZERS
        if not self.root.is_dir():
            raise SourceDefect(
                f"{path} holds no {ANALYZERS}/ directory", code=SourceFault.NO_ANALYZER_DIRECTORY, where=str(path)
            )
        self.store = store if store is not None else SourceStore(self.root)
        self.session_id = session_id
        self.experiment = experiment
        # Records in, lookup here: a mapping keyed by a pair does not cross a boundary
        # (Part 12 §4), so the build hands over rows and each adapter keys them itself.
        self.units = {(str(row["device_name"]), str(row["local_unit_label"])): row["unit_id"] for row in units}
        self.array_asset_id = f"{prefix}{array_asset_id}"
        self.sd = sd
        self.sd_asset_id = f"{prefix}{sd_asset_id}"
        self.compressed_per_chunk = compressed_per_chunk
        self.prefix = prefix
        #: Where an array goes when this source is delivered out of process (Part 12 §5). Held
        #: rather than used: the values are what `staged_arrays` hands over, and what writes them
        #: is whichever side of the boundary is staging.
        self.array_location = array_location
        self.notes: list[str] = []
        self._built: dict[str, Any] | None = None

    # -- the analyzer -------------------------------------------------------------------

    def streams(self) -> list[SortedStream]:
        """Every analyzer in the tree, named as the curated sorting names its streams."""
        found = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.suffix != ".zarr":
                continue
            if matched := STREAM.match(child.stem):
                found.append(SortedStream(path=child, **matched.groupdict()))
        if self.experiment is not None:
            found = [s for s in found if s.experiment == self.experiment]
        if not found:
            raise SourceDefect(
                f"{self.root} holds no analyzer for experiment {self.experiment!r}",
                code=SourceFault.NO_ANALYZER,
                where=str(self.root),
            )
        return found

    def _channels(self, stream: SortedStream) -> list[str]:
        """Return the contacts the sorting ran on, in the order its channel axis counts them (R83 §2.1).

        Named the way `SorterSource.sorting_run_channels` names them, so the two agree without
        either adapter having to run after the other.
        """
        recorded = attrs_at(stream.path, "recording_info").get("recording_attributes") or {}
        found = recorded.get("channel_ids")
        if not found:
            raise SourceDefect(
                f"{stream.key}: the analyzer states no channel list, so no contact can be named",
                code=SourceFault.NO_CHANNEL_LIST,
                where=stream.key,
            )
        return [f"{self.prefix}{stream.device}.{channel}" for channel in found]

    def _window(self, stream: SortedStream) -> tuple[int, float]:
        """How many samples precede the spike, and the rate they are sampled at.

        `ms_before` is what puts sample 0 of a template where the spike is, which the export
        does not record at all -- an importer reading it can only guess the window is centred.
        """
        params = attrs(stream.path / TEMPLATES).get("params") or {}
        recorded = attrs_at(stream.path, "recording_info").get("recording_attributes") or {}
        rate = recorded.get("sampling_frequency")
        if "ms_before" not in params or not rate:
            raise SourceDefect(
                f"{stream.key}: the analyzer states no ms_before or sampling rate for its templates",
                code=SourceFault.NO_TEMPLATE_WINDOW,
                where=stream.key,
            )
        return round(float(params["ms_before"]) * float(rate) / 1000.0), float(rate)

    def _unit(self, stream: SortedStream) -> str | None:
        """Return what the values are in, which the analyzer declares and the export does not."""
        settings = attrs(stream.path).get("settings") or {}
        if "return_in_uV" not in settings:
            self.notes.append(
                Note(
                    f"{stream.key}: the analyzer declares no return_in_uV; the unit is left unstated",
                    NoteCode.UNIT_UNSTATED,
                )
            )
            return None
        # `{adc}` is a UCUM annotation, a dimensionless count of converter steps (Part 02 §8.4).
        return "uV" if settings["return_in_uV"] else "{adc}"

    # -- reading ------------------------------------------------------------------------

    def _read(self) -> dict[str, Any]:
        """Cut every unit's template down to its own contacts, one chunk row at a time.

        The unit axis holds every unit of the session in the sorted order of the names
        `PacketWriter._preassign` numbers, and its labels name each position's unit. Analyzer
        order would not do: analyzers and sorting runs are named differently and sort differently.

        The block is the source's own chunk along the unit axis, so every chunk is read once and
        none twice. What survives is the slabs, far smaller than the block that produced them.
        They stay float64, because the arithmetic that follows is a division and a round, and in
        float32 some values land on the other side of a tie.
        """
        if self._built is not None:
            return self._built
        kept = _Kept()
        windows: set[tuple[int, float]] = set()
        samples: set[int] = set()
        units: set[str | None] = set()
        for stream in self.streams():
            windows.add(self._window(stream))
            units.add(self._unit(stream))
            samples.add(self._cut(stream, kept))

        if not kept.templates:
            raise SourceDefect(
                "no unit in the analyzer's templates matches the packet's sorting", code=SourceFault.NO_UNIT_MATCHES
            )
        if kept.missed:
            self.notes.append(
                Note(
                    f"units: {kept.missed} analyzer unit(s) match no unit in the packet's sorting; skipped",
                    NoteCode.UNIT_UNMATCHED,
                )
            )
        if kept.blank:
            self.notes.append(
                Note(
                    f"units: {kept.blank} analyzer unit(s) are sparse on no contact at all; stored with no channels",
                    NoteCode.UNIT_NO_CONTACT,
                )
            )
        order = sorted(set(self.units.values()), key=str)
        if absent := sum(unit not in kept.templates and unit not in kept.empty for unit in order):
            self.notes.append(
                Note(
                    f"units: {absent} unit(s) of the packet's sorting have no template; stored with no channels",
                    NoteCode.UNIT_NO_TEMPLATE,
                )
            )
        if len(samples) != 1 or len(windows) != 1:
            raise SourceDefect(
                f"the streams disagree about the template window: {sorted(samples)}, {sorted(windows)}",
                code=SourceFault.TEMPLATE_WINDOWS_DIFFER,
            )
        if len(units) != 1:
            raise SourceDefect(
                f"the streams disagree about what their values are in: {sorted(str(u) for u in units)}",
                code=SourceFault.TEMPLATE_UNITS_DIFFER,
            )
        if not kept.peak:
            raise SourceDefect(
                "every template is zero, so no unit has a channel support", code=SourceFault.TEMPLATES_ZERO
            )

        held = samples.pop()
        nbefore, rate = windows.pop()
        nothing = _Template([], -1, np.zeros((0, held)), None)
        templates = [kept.templates.get(unit, nothing) for unit in order]
        width = max(t.slab.shape[0] for t in templates)
        values, scale = _quantise([t.slab for t in templates], kept.peak, width, held)
        self._built = {
            "values": values,
            "scale": scale,
            "identity": [{"unit_id": unit} for unit in order],
            "electrodes": [t.electrodes for t in templates],
            "primary": [t.primary for t in templates],
            "samples": held,
            "nbefore": nbefore,
            "rate": rate,
            "unit": units.pop(),
        }
        if self.sd:
            if not kept.sd_peak:
                raise SourceDefect("every deviation is zero over the mean's support", code=SourceFault.DEVIATIONS_ZERO)
            sd_slabs = [t.sd_slab if t.sd_slab is not None else np.zeros((0, held)) for t in templates]
            sd_values, sd_scale = _quantise(sd_slabs, kept.sd_peak, width, held)
            self._built |= {"sd_values": sd_values, "sd_scale": sd_scale}
        return self._built

    def _cut(self, stream: SortedStream, kept: _Kept) -> int:
        """Append one stream's kept units to `kept`, and return its template window in samples."""
        labels = self.store.array(stream.path / "sorting/unit_ids")
        mask = np.asarray(_dense(stream.path / "sparsity_mask")[:], dtype=bool)
        array = _dense(stream.path / f"{TEMPLATES}/{MEAN}")
        spread = None
        if self.sd:
            if not (stream.path / f"{TEMPLATES}/{DEVIATION}").is_dir():
                raise SourceDefect(
                    f"{stream.key}: sd was asked for and the analyzer holds no {DEVIATION}",
                    code=SourceFault.NO_DEVIATION,
                    where=stream.key,
                )
            spread = _dense(stream.path / f"{TEMPLATES}/{DEVIATION}")
        channels = self._channels(stream)
        if len(labels) != array.shape[0] or mask.shape[0] != array.shape[0]:
            raise SourceDefect(
                f"{stream.key}: {len(labels)} unit ids and {mask.shape[0]} mask rows "
                f"against {array.shape[0]} templates",
                code=SourceFault.TEMPLATES_MISALIGNED,
                where=stream.key,
            )

        total = int(array.shape[0])
        block = int(array.chunks[0]) or total
        for start in range(0, total, block):
            dense = np.asarray(array[start : start + block])
            deviation = np.asarray(spread[start : start + block]) if spread is not None else None
            for offset in range(dense.shape[0]):
                row = start + offset
                found = self.units.get((stream.device, str(int(labels[row]))))
                if found is None:
                    kept.missed += 1
                    continue
                if found in kept.templates or found in kept.empty:
                    raise SourceDefect(
                        f"{stream.key}: unit {found} has a template in more than one analyzer row",
                        code=SourceFault.UNIT_REPEATED,
                        where=stream.key,
                    )
                live = np.flatnonzero(mask[row])
                if not live.size:
                    kept.blank += 1
                    kept.empty.add(found)
                    continue
                slab = dense[offset][:, live].T.copy()
                kept.peak = max(kept.peak, float(np.abs(slab).max()))
                sd_slab = None
                if deviation is not None:
                    sd_slab = deviation[offset][:, live].T.copy()
                    kept.sd_peak = max(kept.sd_peak, float(np.abs(sd_slab).max()))
                kept.templates[found] = _Template(
                    [channels[int(c)] for c in live], int(slab.min(axis=1).argmin()), slab, sd_slab
                )
            del dense, deviation
        return int(array.shape[1])

    # -- what the packet stores ----------------------------------------------------------

    @property
    def values(self) -> NDArray[np.int16]:
        """The array itself: `(unit, channel, sample)`, int16."""
        built = self._read()
        return built["values"]  # type: ignore[no-any-return]

    def _asset(self, asset_id: str, semantic_type: str, scale: float, clock_id: str | None) -> dict[str, Any]:
        """One `core.array_assets` row.

        No `dtype`, `shape`, location or format: the Zarr array declares the first two, and the
        build places the array by `resource_id` and records where in the manifest (Part 12 §5).
        `conversion` is the one thing the array cannot say.
        """
        built = self._read()
        return {
            "array_asset_id": asset_id,
            # The packet identity `staged_arrays` gives the array, so a delivered one binds to this
            # row by name alone (Part 12 §5).
            "resource_id": f"core.{asset_id}",
            "session_id": self.session_id,
            "semantic_type": semantic_type,
            # No `array_asset_name`: the numbering fills it from what `array_asset_id` stands for
            # (R53 §2.5), and a phrase this adapter invented is not that.
            "clock_id": clock_id,
            "sample_rate_hz": built["rate"],
            "unit": built["unit"],
            "conversion": scale,
            "offset": 0.0,
            "metadata": {"quantisation": "int16, scale = peak / 32767"},
        }

    def array_assets(self, clock_id: str | None = None) -> list[dict[str, Any]]:
        """`core.array_assets`, one row per array this source stores.

        The deviation gets its own `conversion`, because it is quantised against its own peak;
        sharing the mean's scale would spend resolution on a range it never reaches.
        """
        built = self._read()
        rows = [self._asset(self.array_asset_id, "waveform_mean", built["scale"], clock_id)]
        if self.sd:
            rows.append(self._asset(self.sd_asset_id, "waveform_sd", built["sd_scale"], clock_id))
        return rows

    def _axes(self, asset_id: str, clock_id: str | None, origin: int | None) -> list[dict[str, Any]]:
        """One array's three axes, in stored order (Part 03 §6.2)."""
        built = self._read()
        start = origin if origin is not None else -built["nbefore"]
        sample_axis: dict[str, Any] = {
            "array_asset_id": asset_id,
            "axis_index": 2,
            "dimension_name": "sample",
        }
        if clock_id is None:
            sample_axis |= {"origin_value": float(start), "step_value": 1.0, "coordinate_unit": "{sample}"}
        else:
            sample_axis |= {"clock_id": clock_id, "origin_tick": start, "step_tick_num": 1}
        return [
            {
                "array_asset_id": asset_id,
                "axis_index": 0,
                "dimension_name": "unit",
                "coordinate_resource": CORE_UNITS,
            },
            {
                "array_asset_id": asset_id,
                "axis_index": 1,
                "dimension_name": "channel",
                "coordinate_resource": CORE_ELECTRODES,
                "depends_on_axis_index": 0,
            },
            sample_axis,
        ]

    def array_dimensions(self, clock_id: str | None = None, origin: int | None = None) -> list[dict[str, Any]]:
        """`core.array_dimensions`, one row per axis of each array, in stored order (Part 03 §6.2).

        The unit axis is labelled with `core.units`. The channel axis is labelled with
        `core.electrodes` and depends on the unit axis, because which contact a position means is
        per unit and no coordinate array can say it.

        The sample axis takes the **numeric** form, in samples, and not the tick form. A waveform
        window is not positioned on any session clock: position *k* is *k - origin* samples from
        the spike, and each unit's spike sits on the clock of the probe that recorded it. Its
        origin is the analyzer's own `ms_before` rather than half the window, which is what an
        importer reading the export has to assume.
        """
        axes = self._axes(self.array_asset_id, clock_id, origin)
        if self.sd:
            axes += self._axes(self.sd_asset_id, clock_id, origin)
        return axes

    def _labels(self, asset_id: str) -> list[dict[str, Any]]:
        """One array's label rows: each unit position's unit, then each unit's contacts, padded with null."""
        built = self._read()
        width = int(built["values"].shape[1])
        common = {"session_id": self.session_id, "array_asset_id": asset_id}
        rows = [
            {
                **common,
                "axis_index": 0,
                "depends_on_position_index": 0,
                "position_index": k,
                "label_id": unit["unit_id"],
            }
            for k, unit in enumerate(built["identity"])
        ]
        for unit, contacts in enumerate(built["electrodes"]):
            rows.extend(
                {
                    **common,
                    "axis_index": 1,
                    "depends_on_position_index": unit,
                    "position_index": channel,
                    "label_id": contacts[channel] if channel < len(contacts) else None,
                }
                for channel in range(width)
            )
        return rows

    def array_labels(self) -> list[dict[str, Any]]:
        """`core.array_labels`, every position of both labelled axes of each array (Part 03 §6.3).

        A label is the name the writer numbers, so it resolves in the numbering of the resource the
        axis names. The deviation is cut on the mean's support and repeats its rows.
        """
        rows = self._labels(self.array_asset_id)
        if self.sd:
            rows += self._labels(self.sd_asset_id)
        return rows

    def unit_electrodes(self) -> list[dict[str, Any]]:
        """`core.unit_electrodes`, one row per unit per contact it has signal on (R28).

        These are the contacts the channel axis's labels name, and they are the analyzer's
        `sparsity_mask` rather than an inspection of the values: the export pads to every channel, so a reader of
        it can only recover the support by looking for zeros, which cannot tell a contact that was
        never computed from one whose template happens to be flat.

        `is_primary` is the template's own negative peak. Reading `extremum_channel_index` instead
        names the wrong electrode whenever the sorting dropped a channel below it.

        R28 `amplitude` is left null. The source measures one amplitude per unit, not per
        electrode, and no reduction of the template reproduces it.
        """
        built = self._read()
        rows = []
        for position, contacts in enumerate(built["electrodes"]):
            identity = built["identity"][position]
            for ordinal, electrode in enumerate(contacts):
                rows.append(
                    {
                        "session_id": self.session_id,
                        **identity,
                        "electrode_id": electrode,
                        "is_primary": ordinal == built["primary"][position],
                    }
                )
        return rows

    def staged_arrays(self) -> list[Any]:
        """Return the arrays themselves, sized for the store they will live in.

        The chunk is one unit, which is the unit of the question, and `shard_for` keeps that from
        becoming one object per chunk (`conformance/zarr-probe/waveforms.py`).
        """
        from ..arrays import shard_for
        from ..writer import StagedArray

        built = self._read()
        wanted = [(self.array_asset_id, built["values"])]
        if self.sd:
            wanted.append((self.sd_asset_id, built["sd_values"]))
        staged = []
        for asset_id, values in wanted:
            chunks = (1, *values.shape[1:])
            staged.append(
                StagedArray(
                    values=values,
                    resource_id=f"core.{asset_id}",
                    declaration_id=CORE_ARRAY_ASSET_INSTANCES,
                    array_asset_id=asset_id,
                    chunks=chunks,
                    shard=shard_for(values.shape, chunks, self.compressed_per_chunk),
                    dimension_names=("unit", "channel", "sample"),
                )
            )
        return staged

    def records(self, *, clock_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID.

        The arrays themselves are not among them: they are bytes, staged through
        `PacketWriter.add_array` from `staged_arrays`.
        """
        built = {
            CORE_ARRAY_ASSETS: self.array_assets(),
            CORE_ARRAY_DIMENSIONS: self.array_dimensions(clock_id=clock_id),
            CORE_ARRAY_LABELS: self.array_labels(),
            CORE_UNIT_ELECTRODES: self.unit_electrodes(),
        }
        return {resource: rows for resource, rows in built.items() if rows}

    def offers(self) -> dict[str, int]:
        """Which resources this source supplies from its root, and how many rows (Part 05 §4.1)."""
        return {resource: len(rows) for resource, rows in self.records().items()}


def _quantise(
    slabs: list[NDArray[np.float64]], peak: float, width: int, samples: int
) -> tuple[NDArray[np.int16], float]:
    """Scale float64 slabs onto int16, the peak landing on the last code.

    The quantisation this leaves, a step of peak/32767, is well under the standard error of the
    means themselves. The deviation is non-negative and still stored signed, spending a bit it
    never uses: unsigned would buy one bit of resolution on a quantity whose own sampling error
    is far larger, at the cost of a second convention for reading these arrays.
    """
    scale = peak / 32767.0
    values = np.zeros((len(slabs), width, samples), dtype=np.int16)
    for position, slab in enumerate(slabs):
        values[position, : slab.shape[0]] = np.rint(slab / scale).astype(np.int16)
    return values, scale


__all__ = ["ANALYZERS", "WaveformSource"]

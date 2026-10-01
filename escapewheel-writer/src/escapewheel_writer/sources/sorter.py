"""Read a SpikeInterface curated sorting into records, its spikes on the integer ticks it stores.

- :class:`SorterSource` -- a `curated/` tree as records, and its spikes as Arrow batches.
- :class:`SortedStream` -- one curated stream folder, with its name parsed.
- :data:`STREAM` -- the pattern a stream folder's name follows.
- :data:`PROJECTION` -- a mapping from a source's quality label to the closed set that
  `core.units.quality_label` takes, or to null where no member fits.
- :data:`LABEL_SOURCES` -- a mapping from each per-unit label file to the `source` of its labels.
- :data:`DESIGNATED` -- the label source that fills `core.units.quality_label`.
- :data:`STREAM_WORKERS` -- how many streams are read at once.

`unit_index` in `spikes.npy` is an offset into `unit_ids`, never an identifier: every unit is
resolved through `unit_ids[unit_index]`. The adapter names a unit by its run, its curation and
its zero-padded label, and the writer numbers those names in order (Part 02 §12.1).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pyarrow as pa
from escapewheel_reader.resource_ids import (
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_CURATION_VERSIONS,
    CORE_PROBES,
    CORE_PROCESSING_RUNS,
    CORE_SORTING_RUN_CHANNELS,
    CORE_SORTING_RUNS,
    CORE_SPIKE_EVENTS,
    CORE_UNIT_QUALITY_LABELS,
    CORE_UNITS,
)
from escapewheel_reader.resources import ZARR_METADATA_FILENAMES
from numpy.typing import NDArray

from ..clock import Clock
from ..errors import SourceDefect, SourceFault
from ..notes import Note, NoteCode
from .store import source_root
from .zarr_compat import attrs, attrs_at, read_array

#: ``experiment1_Record Node 109#Neuropix-PXI-100.50720-1_recording1``. The probe token holds
#: no underscore, which is what lets the recording suffix be split off unambiguously.
STREAM = re.compile(
    r"^(?P<experiment>experiment\d+)_Record Node (?P<node>\d+)#(?P<probe>[^_]+)_(?P<recording>recording\d+)$"
)

#: A quad-base probe is sorted as four shank streams that share one physical device.
SHANK = re.compile(r"^(?P<serial>.+?)-(?P<shank>\d+)$")

#: Part 02 §9.3: a source's own label is open, the projection onto the closed set is declared.
#: `non_soma` projects to null rather than being forced into `noise` -- bombcell means
#: "a real waveform recorded off-soma", which is not the same claim as "not a unit".
PROJECTION: dict[str, str | None] = {
    "good": "sua",
    "sua": "sua",
    "mua": "mua",
    "MUA": "mua",
    "noise": "noise",
    "non_soma": None,
}

#: `properties/<file>.npy` -> the `core.unit_quality_labels.source` it becomes.
LABEL_SOURCES = {
    "KSLabel": "kilosort",
    "bombcell_label": "bombcell",
    "decoder_label": "decoder",
    "unitrefine_label": "unitrefine",
}

#: `curation.json`'s label category that fills the same role the automated sources do. Any
#: other category becomes `manual:<category>`, since one source may emit one label per unit.
MANUAL_CATEGORY = "quality"

#: Sources that also report a probability, which becomes `confidence`.
CONFIDENCE = {"decoder": "decoder_probability", "unitrefine": "unitrefine_probability"}

#: Which source fills `core.units.quality_label`. The decoder emits `sua`/`mua`/`noise`
#: natively, which is the vocabulary R11 §3 closed the column to and the reason it chose
#: `sua` over the more common `good`.
DESIGNATED = "decoder"


#: Streams read at once when summarising spikes. Bounded, because the win and the cost pull
#: apart sharply: a spike file is a struct of three int64 fields, so reading one field pages the
#: whole 24 bytes per spike, and each concurrent stream is another file resident. Past four, a
#: further worker saves little time and holds another stream's spikes in memory.
STREAM_WORKERS = 4


@dataclass(frozen=True)
class SortedStream:
    """One curated sorting folder, with its name parsed.

    Attributes
    ----------
    path : Path
        The folder.
    experiment, node, probe, recording : str
        The four parts of the folder name. `probe` keeps any shank suffix.
    """

    path: Path
    experiment: str
    node: str
    probe: str
    recording: str

    @property
    def serial(self) -> str:
        """The physical probe's serial, with any shank suffix removed."""
        found = SHANK.match(self.probe)
        return found.group("serial") if found else self.probe

    @property
    def device(self) -> str:
        """The probe as the surrounding ecosystem names it, shank suffix and all.

        A quad-base probe reaches Open Ephys as four streams (`...-1` through `...-4`), and
        everything downstream keeps them apart: SpikeInterface sorts each separately, giving
        four unit-id spaces that each start at 0, and an NWB writes four electrode groups.
        Part 01 §3.5 admits exactly this: where a source presents several recording entities from
        one physical object, each is a Probe and all name the same Device. So `probe_id` names the
        recording entity and `serial_number` carries the object, which is where a grouping belongs
        rather than inside an identifier that would have to be parsed.
        """
        return self.probe.rsplit(".", 1)[-1]

    @property
    def key(self) -> str:
        """A stable id fragment for this stream, unique within an asset."""
        return f"{self.experiment}.{self.probe}"


def _parse(path: Path) -> SortedStream:
    """Parse a curated folder name, or refuse it."""
    found = STREAM.match(path.name)
    if not found:
        raise SourceDefect(
            f"{path.name} is not a curated stream folder name", code=SourceFault.STREAM_NAME, where=path.name
        )
    return SortedStream(path=path, **found.groupdict())


class SorterSource:
    """A SpikeInterface ``curated/`` tree, read as records.

    Parameters
    ----------
    root : str or Path
        The ``curated`` directory, or an asset directory containing one.
    session_id : str
        The session these sorted streams belong to.
    experiment : str, optional
        Restrict to one experiment, e.g. ``experiment1``. Each experiment restarts
        `sample_index` at zero, so its streams are on different clocks from another
        experiment's and the two are not comparable. Default reads every experiment, which is
        right only when the caller means them to share a packet.
    prefix : str, optional
        Prepended to every generated ID.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    parent_clock_id : str, optional
        The clock these sample clocks align to, where another source supplies the anchors.
        Left null a packet with more than one clock cannot satisfy R27 §2.
    emit_probes : bool, default True
        Emit `core.probes` from the stream names, which carry the serial. Set False when
        another adapter owns that table, since two adapters emitting it would collide on the
        primary key.

    Attributes
    ----------
    notes : list of str
        What was dropped, coerced, or found inconsistent.
    """

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    #: Static, so a recipe check reads it with nothing open -- `offers` counts rows and
    #: therefore needs the data.
    PRODUCES = frozenset(
        {
            CORE_CLOCK_OBSERVATION_INTERVALS,
            CORE_CLOCKS,
            CORE_CURATION_VERSIONS,
            CORE_PROBES,
            CORE_PROCESSING_RUNS,
            CORE_SORTING_RUN_CHANNELS,
            CORE_SORTING_RUNS,
            CORE_SPIKE_EVENTS,
            CORE_UNIT_QUALITY_LABELS,
            CORE_UNITS,
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

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply, resolved against Part 12 §4's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    #:
    #: An option the adapter can run without is left out: a declared name a recipe does not set
    #: resolves to nothing, so declaring one makes it mandatory.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id")

    #: Part 05 §3.4: options this adapter reads and can run without, which a recipe may leave
    #: unset (Part 12 §4). `sample` is among them because a build applies `--sample` by setting
    #: it, and a build may not supply what the adapter does not declare (Part 12 §4).
    ACCEPTS: ClassVar[tuple[str, ...]] = (
        "experiment",
        "prefix",
        "emit_probes",
        "parent_clock_id",
        "sample",
        "source_cache",
        "curation",
    )

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        experiment: str | None = None,
        prefix: str = "",
        emit_probes: bool = True,
        parent_clock_id: str | None = None,
        sample: int | None = None,
        source_cache: str | None = None,
        curation: str | None = None,
    ) -> None:
        path = source_root(root, cache=source_cache)
        self.root = path if path.name == "curated" else path / "curated"
        if not self.root.is_dir():
            raise SourceDefect(
                f"{path} holds no curated/ directory", code=SourceFault.NO_CURATED_DIRECTORY, where=str(path)
            )
        self.session_id = session_id
        self.experiment = experiment
        self.prefix = prefix
        self.emit_probes = emit_probes
        self.parent_clock_id = parent_clock_id
        self.sample = sample
        #: What names this curation apart from one a packet already holds, as an amendment adding a
        #: curation of a held sorting needs (Part 05 §12); None keeps the default names.
        self.curation = curation
        self.notes: list[str] = []
        self._cache: dict[str, Any] = {}
        self._noted_naive = False

    # -- source access ----------------------------------------------------------------

    def streams(self) -> list[SortedStream]:
        """Every curated stream, sorted by the id its rows will carry.

        The order is the one `core.spike_events` is stored in (Part 03 §5.3), so spike batches can
        be yielded stream by stream without a global sort.
        """
        found = [_parse(child) for child in self.root.iterdir() if child.is_dir()]
        if self.experiment is not None:
            found = [s for s in found if s.experiment == self.experiment]
        if not found:
            raise SourceDefect(
                f"{self.root} holds no streams for experiment {self.experiment!r}",
                code=SourceFault.NO_STREAM,
                where=str(self.root),
            )
        return sorted(found, key=lambda s: self._sorting_run_id(s))

    def _json(self, stream: SortedStream, name: str) -> dict[str, Any]:
        """Read one JSON file from a stream, cached."""
        key = f"{stream.key}/{name}"
        if key not in self._cache:
            path = stream.path / name
            if not path.is_file():
                raise SourceDefect(
                    f"{stream.path.name} has no {name}",
                    code=SourceFault.STREAM_FILE_ABSENT,
                    where=f"{stream.path.name}/{name}",
                )
            self._cache[key] = json.loads(path.read_text())
        loaded: dict[str, Any] = self._cache[key]
        return loaded

    @staticmethod
    def _npy(path: Any, *, mmap: bool = False) -> NDArray[Any]:
        """Read a `.npy`, from a local file or from a store.

        `mmap_mode` needs a real filesystem path, and it is what keeps `spikes.npy` off the
        heap when the sorting is on disk. A store has no such trick -- the object is fetched
        whole either way -- so it is opened as a file object and read.
        """
        if getattr(path, "protocol", ""):
            with path.open("rb") as handle:
                loaded: NDArray[Any] = np.load(handle, allow_pickle=False)
            return loaded
        return np.load(path, allow_pickle=False, **({"mmap_mode": "r"} if mmap else {}))

    @staticmethod
    def _npy_rows(path: Any) -> int:
        """Return a `.npy`'s row count from its header, without reading the array.

        Locally `mmap_mode` makes this free. Over a store it has to stay free too, or counting
        a quarter of a billion spikes would fetch every one of them: the header is a few
        hundred bytes at the front of the object, so it is one ranged read.
        """
        if not getattr(path, "protocol", ""):
            return int(np.load(path, mmap_mode="r").shape[0])
        readers = {(1, 0): np.lib.format.read_array_header_1_0, (2, 0): np.lib.format.read_array_header_2_0}
        with path.open("rb") as handle:
            version = np.lib.format.read_magic(handle)
            read_header = readers.get(version)
            if read_header is None:
                raise SourceDefect(
                    f"{path}: .npy format version {version}, which this reader does not know",
                    code=SourceFault.NPY_VERSION,
                    where=str(path),
                )
            shape, _, _ = read_header(handle)
        return int(shape[0])

    def _property(self, stream: SortedStream, name: str) -> NDArray[Any] | None:
        """Read one per-unit property array, or None if the sorting does not carry it."""
        path = stream.path / "properties" / f"{name}.npy"
        return self._npy(path) if path.is_file() else None

    def _unit_ids(self, stream: SortedStream) -> NDArray[np.int64]:
        """Return the stream's unit ids, in the order `unit_index` offsets into."""
        ids = np.asarray(self._json(stream, "numpysorting_info.json")["unit_ids"], dtype=np.int64)
        if ids.size and not np.all(np.diff(ids) > 0):
            raise SourceDefect(
                f"{stream.key}: unit_ids are not strictly increasing, so unit_index is ambiguous",
                code=SourceFault.UNIT_IDS_UNORDERED,
                where=stream.key,
            )
        return ids

    def _width(self, stream: SortedStream) -> int:
        """Digits needed so that string order over unit ids matches numeric order."""
        ids = self._unit_ids(stream)
        return max(len(str(int(ids.max()))), 1) if ids.size else 1

    # -- identity ---------------------------------------------------------------------

    # These compose a *name*. `arrow.build` maps it to the integer the column holds (R53 §2.1),
    # against one `Keys` shared by every adapter -- because the recipe exists precisely because
    # four sources can each produce `core.probes`, and two of them numbering the same probe
    # differently is a defect no foreign key could see: both values resolve, to different rows.

    def _clock_id(self, stream: SortedStream) -> str:
        return f"{self.prefix}{stream.key}.samples"

    def _sorting_run_id(self, stream: SortedStream) -> str:
        return f"{self.prefix}{stream.key}"

    def _curation_id(self, stream: SortedStream) -> str:
        return f"{self.prefix}{stream.key}.{self.curation or 'curated'}"

    def _probe_id(self, stream: SortedStream) -> str:
        return f"{self.prefix}{stream.device}"

    def _unit_id(self, stream: SortedStream, label: int, width: int) -> str:
        """Compose the name the writer numbers, ordered as Part 02 §12.1 requires.

        `unit_id` is assigned, so the sorter's label cannot be it: a sorter numbers from zero
        within each run and a run is one probe, so a label repeats across a session's units. The
        number must follow ascending
        `(sorting_run_id, curation_id, local_unit_label)` so a rebuild reproduces it (Part 05 §4.3),
        and `PacketWriter._preassign` assigns in sorted-name order -- so the name is those three,
        with the label zero-padded to `width` to make its text order its numeric one. Run and
        curation ids are themselves assigned in sorted-name order, which is what makes ordering
        by their names the same as ordering by their numbers.
        """
        return f"{self._sorting_run_id(stream)}|{self._curation_id(stream)}|{label:0{width}d}"

    # -- tables -----------------------------------------------------------------------

    def clocks(self) -> list[dict[str, Any]]:
        """`core.clocks`, one per stream.

        Each experiment restarts `sample_index` at zero, so a stream's clock belongs to one
        experiment; a tick on another experiment's clock is a different quantity that happens
        to be spelled the same way.

        No `tick_zero_utc` and no alignment columns: a curated sorting records neither when
        sample 0 happened nor how this stream relates to any other. Both are another source's
        to supply, and until one does R27 §4 refuses the packet rather than let the clocks
        look convertible.
        """
        rows = []
        for stream in self.streams():
            rate = self._json(stream, "numpysorting_info.json")["sampling_frequency"]
            if float(rate) != int(rate):
                raise SourceDefect(
                    f"{stream.key}: sampling_frequency {rate} is not a whole number of hertz",
                    code=SourceFault.RATE_NOT_WHOLE,
                    where=stream.key,
                )
            rows.append(
                Clock(
                    clock_id=self._clock_id(stream),
                    session_id=self.session_id,
                    name=f"{stream.probe} sample clock ({stream.experiment})",
                    tick_rate_num=int(rate),
                    origin=f"sample 0 of {stream.experiment} on {stream.probe}",
                    parent_clock_id=self.parent_clock_id,
                ).record()
            )
        return rows

    def probes(self) -> list[dict[str, Any]]:
        """`core.probes`, one per physical probe.

        A quad-base probe is sorted as four shank streams sharing a serial, so the four
        collapse to one row while keeping four sorting runs and four clocks.
        """
        if not self.emit_probes:
            return []
        seen: dict[str, dict[str, Any]] = {}
        for stream in self.streams():
            probe_id = self._probe_id(stream)
            seen.setdefault(
                probe_id,
                {
                    "probe_id": probe_id,
                    "session_id": self.session_id,
                    "serial_number": stream.serial.rsplit(".", 1)[-1],
                    "metadata": {"stream_prefix": stream.serial},
                },
            )
        return list(seen.values())

    def sorting_runs(self) -> list[dict[str, Any]]:
        """`core.sorting_runs`, one per stream.

        `started_at` stays null. The sorter stamps a naive datetime, and unlike a rig's wall
        clock there is no zone to localize it to -- it came off whatever machine ran the sort,
        which is not the rig and is not recorded. The raw string travels in `metadata` so
        nothing is lost, and Part 03's rule that a wall-clock column is UTC-adjusted stays true.
        """
        rows = []
        for stream in self.streams():
            info = self._json(stream, "si_folder.json")
            sorting = info.get("annotations", {}).get("__sorting_info__", {})
            log = sorting.get("log", {})
            params = sorting.get("params", {})
            if log.get("datetime") and not self._noted_naive:
                self._noted_naive = True
                self.notes.append(
                    Note(
                        "sorting_runs.started_at: the sorter stamps no UTC offset and its machine's "
                        "zone is not recorded; kept verbatim in metadata.sorted_at_naive",
                        NoteCode.SORT_TIME_NAIVE,
                    )
                )
            rows.append(
                {
                    "sorting_run_id": self._sorting_run_id(stream),
                    "session_id": self.session_id,
                    "probe_id": self._probe_id(stream),
                    # R41 §2.1: the sorting is reachable from the provenance graph, which is
                    # what lets a packet carrying two of them say which to read.
                    "processing_run_id": self._run_id(stream, "spike_sorting"),
                    "sorter_name": log.get("sorter_name") or params.get("sorter_name"),
                    "sorter_version": log.get("sorter_version"),
                    "parameters": params.get("sorter_params"),
                    "metadata": {
                        "spikeinterface_version": info.get("version"),
                        "stream": stream.path.name,
                        "run_time_s": log.get("run_time"),
                        "sorted_at_naive": log.get("datetime"),
                    },
                }
            )
        return rows

    def _run_id(self, stream: SortedStream, activity: str) -> str:
        """Return the `core.processing_runs` ID for one activity on one stream (R41 §2.1)."""
        if activity == "curation" and self.curation is not None:
            return f"{self._curation_id(stream)}.curation"
        return f"{self.prefix}{stream.key}.{activity}"

    def processing_runs(self) -> list[dict[str, Any]]:
        """`core.processing_runs`, one per stream per activity that made something here.

        R9 records what ran; R41 §2.1 makes the sorting and the curation *reachable* from it,
        which is the whole basis for saying later which of two sortings a consumer should read.
        The facts come from the sorted asset's own logs -- the same ones `sorting_runs` and
        `curation_versions` already report -- so this restates nothing the packet must derive.

        `supersedes` stays null. A first import supersedes nothing, and a writer that does not
        know what a run replaced does not guess. `scope` is set, because a run whose
        subject is unrecorded is undeterminable rather than unique (Part 01 §2.6).
        """
        rows = []
        for stream in self.streams():
            info = self._json(stream, "si_folder.json")
            log = info.get("annotations", {}).get("__sorting_info__", {}).get("log", {})
            curation = self._json(stream, "curation.json")
            rows.append(
                {
                    "processing_run_id": self._run_id(stream, "spike_sorting"),
                    "session_id": self.session_id,
                    "activity_type": "spike_sorting",
                    # R44 §2.1. The probe is what a sorting is *about*, so two sortings of one
                    # probe are alternatives and several probes sorted once each are not. R49 §2.2
                    # names the kind as a resource ID, so a consumer resolves it from the registry.
                    "scope_kind": CORE_PROBES,
                    "scope": self._probe_id(stream),
                    "software_name": log.get("sorter_name") or "unknown",
                    "software_version": log.get("sorter_version"),
                    "status": "failed" if log.get("error") else "succeeded",
                    "metadata": {"spikeinterface_version": info.get("version"), "stream": stream.path.name},
                }
            )
            rows.append(
                {
                    "processing_run_id": self._run_id(stream, "curation"),
                    "session_id": self.session_id,
                    "activity_type": "curation",
                    # The sorting rather than the probe: a curation is of one sorting, so
                    # choosing the sorting already narrows this, and scoping to the probe would
                    # restate that ambiguity instead of composing with it.
                    "scope_kind": CORE_SORTING_RUNS,
                    "scope": self._sorting_run_id(stream),
                    "software_name": "spikeinterface",
                    "software_version": curation.get("format_version"),
                    "status": "succeeded",
                    "metadata": {"stream": stream.path.name},
                }
            )
        return rows

    def curation_versions(self) -> list[dict[str, Any]]:
        """`core.curation_versions`, one per stream.

        Merges and splits are counted, not replayed. Part 02 has no table for a curation
        operation, and inventing one to hold a list is a schema decision an adapter is not
        entitled to make.
        """
        rows = []
        for stream in self.streams():
            curation = self._json(stream, "curation.json")
            rows.append(
                {
                    "curation_id": self._curation_id(stream),
                    "sorting_run_id": self._sorting_run_id(stream),
                    "session_id": self.session_id,
                    "processing_run_id": self._run_id(stream, "curation"),  # R41 §2.1
                    "curation_tool": "spikeinterface",
                    "metadata": {
                        "format_version": curation.get("format_version"),
                        "n_removed": len(curation.get("removed") or []),
                        "n_merges": len(curation.get("merges") or []),
                        "n_splits": len(curation.get("splits") or []),
                    },
                }
            )
        return rows

    # -- the analyzer, where amplitudes live -------------------------------------------

    def _analyzer(self, stream: SortedStream) -> Path | None:
        """Locate the SortingAnalyzer for a stream, if the asset carries one."""
        path = self.root.parent / "postprocessed" / f"{stream.path.name}.zarr"
        return path if path.is_dir() else None

    def _recording_length(self, stream: SortedStream) -> int | None:
        """How many samples the sorted recording holds, from the analyzer's `recording_info`.

        This is the one place the length of the raw acquisition survives into the sorted
        asset: SpikeInterface records the recording's attributes beside the sorting, so a
        packet built from a sorting alone can still say when the probe was running without
        reaching for the compressed AP data or for a JSON that rounds to whole seconds.
        """
        analyzer = self._analyzer(stream)
        if analyzer is None:
            return None
        recorded = attrs_at(analyzer, "recording_info").get("recording_attributes") or {}
        lengths = recorded.get("num_samples") or []
        if len(lengths) != 1:
            # Each segment restarts the counter, so a multi-segment recording is more than one
            # clock (Part 01 §3.9) and its length is not one interval on this one.
            self.notes.append(
                Note(
                    f"{stream.key}: {len(lengths)} recording segments; no observation window written",
                    NoteCode.SEVERAL_SEGMENTS,
                )
            )
            return None
        return int(lengths[0])

    def _channel_ids(self, stream: SortedStream) -> list[str] | None:
        """Return the channels the sorting ran on in its own order, or None where it states none."""
        analyzer = self._analyzer(stream)
        if analyzer is None:
            return None
        recorded = attrs_at(analyzer, "recording_info").get("recording_attributes") or {}
        return [str(c) for c in recorded["channel_ids"]] if recorded.get("channel_ids") else None

    def sorting_run_channels(self) -> list[dict[str, Any]]:
        """`core.sorting_run_channels`, the channels each run used in its own order (R83 §2.1).

        A sorting drops bad channels before it runs, so a channel index it emits afterwards
        counts what it kept, and `extremum_channel_index` read as a contact position names the
        wrong electrode. The analyzer holds that list and the NWB does not, which is why this
        adapter owns the table and the NWB one cannot.

        The electrode is named rather than numbered, so the writer resolves it against the same
        `Keys` the NWB source's `core.electrodes` numbered: `<group>.<channel>` is what
        `NWBSource._electrode_ids` composes, and a name is what makes the two agree without
        this adapter having to run after that one.

        Part 02 §12.2 forbids inferring the list, so a stream whose analyzer states none contributes
        no rows and says so.
        """
        rows = []
        for stream in self.streams():
            channels = self._channel_ids(stream)
            if channels is None:
                self.notes.append(
                    Note(f"{stream.key}: the analyzer states no channel list; none written", NoteCode.NO_CHANNEL_LIST)
                )
                continue
            rows += [
                {
                    "session_id": self.session_id,
                    "sorting_run_id": self._sorting_run_id(stream),
                    "channel_index": index,
                    "electrode_id": f"{self.prefix}{stream.device}.{channel}",
                }
                for index, channel in enumerate(channels)
            ]
        return rows

    def observation_intervals(self) -> list[dict[str, Any]]:
        """`core.clock_observation_intervals`, one window per stream's sample clock.

        Part 01 §2.3: a sample clock's window is the extent of the recording it counts, which for
        a clock whose origin is sample 0 is `[0, length - 1]`. It is deliberately not derived
        from the spikes -- a denominator taken from the numerator makes every rate identical --
        and it is the fact that makes the window independent of what the sorting found: a unit
        that fires nothing was still observed.
        """
        rows = []
        for stream in self.streams():
            length = self._recording_length(stream)
            if length is None:
                continue
            rows.append(
                {
                    "session_id": self.session_id,
                    "clock_id": self._clock_id(stream),
                    "start_tick": 0,
                    "stop_tick": length - 1,
                }
            )
        return rows

    def _amplitude_unit(self, stream: SortedStream) -> str | None:
        """`uV` or `{adc}`, from the analyzer's own setting (R11 §2).

        Null when no analyzer is present, which is also when no amplitudes are emitted --
        `amplitude_unit_declared` binds only where amplitudes exist.
        """
        analyzer = self._analyzer(stream)
        if analyzer is None:
            return None
        settings = attrs(analyzer).get("settings") or {}
        if "return_in_uV" not in settings:
            self.notes.append(
                Note(f"{stream.key}: analyzer declares no return_in_uV; amplitude unit unknown", NoteCode.UNIT_UNSTATED)
            )
            return None
        # `{adc}` is a UCUM annotation, a dimensionless count of converter steps (Part 02 §8.4).
        return "uV" if settings["return_in_uV"] else "{adc}"

    def _amplitudes(self, stream: SortedStream, n_spikes: int) -> NDArray[Any] | None:
        """Per-spike amplitudes, in the source's own row order, or None."""
        analyzer = self._analyzer(stream)
        if analyzer is None:
            return None
        path = analyzer / "extensions" / "spike_amplitudes" / "amplitudes"
        if not (path / ZARR_METADATA_FILENAMES[2]).is_file():
            self.notes.append(Note(f"{stream.key}: analyzer carries no spike_amplitudes", NoteCode.NO_AMPLITUDES))
            return None
        values = read_array(path)
        # A sample truncates the spikes, so it must truncate their amplitudes by the same rule:
        # these are index-aligned, and the check below is what guarantees it.
        if self.sample is not None:
            values = values[: self.sample]
        if values.size != n_spikes:
            raise SourceDefect(
                f"{stream.key}: {values.size} amplitudes for {n_spikes} spikes; they are index-aligned or nothing",
                code=SourceFault.AMPLITUDES_MISALIGNED,
                where=stream.key,
            )
        return values

    # -- units --------------------------------------------------------------------------

    def units(self) -> list[dict[str, Any]]:
        """`core.units`, one row per unit per stream.

        `n_spikes`, `first_spike_tick` and `last_spike_tick` are the validated denormalization
        the spec asks for, computed from the spikes rather than copied from anywhere. That
        means reading every spike in the session, which is why the result is kept: an importer
        asks for it twice, once to join units to another source and once to write the table.

        Streams are read in parallel, :data:`STREAM_WORKERS` at a time. The work is numpy over a
        memory-mapped array and so releases the GIL, but each concurrent stream is another file
        resident, so the bound is a memory decision rather than a scheduling one.
        """
        if "units" not in self._cache:
            streams = self.streams()
            with ThreadPoolExecutor(max_workers=min(len(streams), STREAM_WORKERS) or 1) as pool:
                per_stream = list(pool.map(self._unit_rows, streams))
            self._cache["units"] = [row for rows in per_stream for row in rows]
        rows: list[dict[str, Any]] = self._cache["units"]
        return rows

    def _unit_rows(self, stream: SortedStream) -> list[dict[str, Any]]:
        """`core.units` rows for one stream, with its spike summary computed from the spikes."""
        rows = []
        ids = self._unit_ids(stream)
        width = self._width(stream)
        index, tick = self._spikes(stream)
        counts = np.bincount(index, minlength=ids.size)
        first, last = self._extremes(index, tick, counts)
        labels = {source: self._property(stream, name) for name, source in LABEL_SOURCES.items()}
        designated = labels.get(DESIGNATED)
        for offset, label in enumerate(ids):
            raw = str(designated[offset]) if designated is not None else None
            rows.append(
                {
                    "session_id": self.session_id,
                    "unit_id": self._unit_id(stream, int(label), width),
                    "probe_id": self._probe_id(stream),
                    "sorting_run_id": self._sorting_run_id(stream),
                    "curation_id": self._curation_id(stream),
                    "local_unit_label": str(int(label)),
                    "quality_label": PROJECTION.get(raw) if raw is not None else None,
                    "quality_label_source": DESIGNATED if raw is not None else None,
                    # R96 §3: both belong to the sorting run and a spike cannot reach it, so the
                    # unit carries them and `core.spike_events` resolves each in one hop.
                    "amplitude_unit": self._amplitude_unit(stream),
                    "clock_id": self._clock_id(stream),
                    "n_spikes": int(counts[offset]),
                    "first_spike_tick": int(first[offset]) if counts[offset] else None,
                    "last_spike_tick": int(last[offset]) if counts[offset] else None,
                }
            )

        return rows

    def _spikes(self, stream: SortedStream) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """Read a stream's `(unit_index, sample_index)` from disk.

        `unit_index` is an offset into `unit_ids`, never an identifier: the two diverge at the
        first gap a merge leaves in `unit_ids`. It is resolved before anything is written.

        `sample` truncates every stream to its first spikes, and is applied *here* rather than
        at either caller because both of them read through this one method. A cap applied to
        the spike stream alone would leave `core.units.n_spikes` counting spikes the packet
        does not contain, which is precisely what the `stale_summary` rule exists to catch.
        Truncating in file order takes an opening time window; a unit with nothing in it keeps
        its row with a null first and last tick.
        """
        spikes = self._npy(stream.path / "spikes.npy", mmap=True)
        if self.sample is not None:
            spikes = spikes[: self.sample]
        return np.asarray(spikes["unit_index"]), np.asarray(spikes["sample_index"])

    @staticmethod
    def _extremes(
        index: NDArray[np.int64], tick: NDArray[np.int64], counts: NDArray[Any]
    ) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """Lowest and highest tick per unit, as `-1` where a unit has no spikes.

        Grouped with `reduceat` over a stable sort rather than `ufunc.at`, which is
        unbuffered and two orders of magnitude slower over a stream's spikes. The source
        is in time order, but nothing here relies on that.
        """
        order = np.argsort(index, kind="stable")
        grouped = tick[order]
        starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
        first = np.full(counts.size, -1, dtype=np.int64)
        last = np.full(counts.size, -1, dtype=np.int64)
        present = counts > 0
        if present.any():
            first[present] = np.minimum.reduceat(grouped, starts[present])
            last[present] = np.maximum.reduceat(grouped, starts[present])
        return first, last

    def unit_quality_labels(self) -> list[dict[str, Any]]:
        """`core.unit_quality_labels`, one row per (unit, source).

        R22 §1: real curation emits labels no closed vocabulary covers. Four automated
        sources disagree here -- bombcell alone emits `non_soma`, which projects to null
        rather than being forced into `noise`, because "recorded off-soma" is a different
        claim from "not a unit".
        """
        rows = []
        for stream in self.streams():
            ids = self._unit_ids(stream)
            width = self._width(stream)
            for name, source in LABEL_SOURCES.items():
                labels = self._property(stream, name)
                if labels is None:
                    continue
                if labels.size != ids.size:
                    raise SourceDefect(
                        f"{stream.key}: {name} has {labels.size} values for {ids.size} units",
                        code=SourceFault.PROPERTY_MISALIGNED,
                        where=stream.key,
                    )
                confidence = self._property(stream, CONFIDENCE[source]) if source in CONFIDENCE else None
                unknown = {str(v) for v in np.unique(labels)} - set(PROJECTION)
                if unknown:
                    self.notes.append(
                        Note(
                            f"{stream.key}/{name}: {sorted(unknown)} have no declared projection; "
                            "kept verbatim with a null normalized_label",
                            NoteCode.LABEL_UNPROJECTED,
                        )
                    )
                for offset, label in enumerate(ids):
                    raw = str(labels[offset])
                    rows.append(
                        {
                            "session_id": self.session_id,
                            "unit_id": self._unit_id(stream, int(label), width),
                            "source": source,
                            "label": raw,
                            "normalized_label": PROJECTION.get(raw),
                            "confidence": float(confidence[offset]) if confidence is not None else None,
                        }
                    )
            rows += self.manual_labels(stream)
        return rows

    def manual_labels(self, stream: SortedStream) -> list[dict[str, Any]]:
        """`core.unit_quality_labels` rows from a curation's own manual labels.

        The four automated sources live in `properties/`; these live in `curation.json` and
        are the only record of what a person decided. Without them a packet's removed units
        are indistinguishable from its kept ones.

        Removal is checked here rather than emitted. `curation.json` lists `removed` units
        separately, and where that list is exactly the manually labelled set the label makes
        removal queryable. That coincidence is a property of a pipeline and not a rule, so a
        stream where it breaks is reported: the packet would then be hiding a removal no label
        records, and Part 02 has no column to put one in.
        """
        curation = self._json(stream, "curation.json")
        ids = self._unit_ids(stream)
        width = self._width(stream)
        known = set(ids.tolist())
        removed = set(curation.get("removed") or [])
        labelled = {entry["unit_id"] for entry in curation.get("manual_labels") or []}
        if removed != labelled:
            self.notes.append(
                Note(
                    f"{stream.key}: {len(removed - labelled)} units are removed by the curation and carry "
                    f"no manual label, so the packet cannot say they were removed; 02 has no column for it",
                    NoteCode.REMOVAL_UNRECORDED,
                )
            )
        if stray := labelled - known:
            self.notes.append(
                Note(
                    f"{stream.key}: {len(stray)} manual labels name units the sorting does not have",
                    NoteCode.LABEL_NAMES_NO_UNIT,
                )
            )

        rows = []
        for entry in curation.get("manual_labels") or []:
            label = entry["unit_id"]
            if label not in known:
                continue
            for category, values in (entry.get("labels") or {}).items():
                chosen = list(values) if isinstance(values, list) else [values]
                if len(chosen) != 1:
                    self.notes.append(
                        Note(
                            f"{stream.key}/unit {label}: {len(chosen)} labels in category {category!r}; "
                            "kept verbatim and left unprojected, since the closed set holds one value",
                            NoteCode.SEVERAL_LABELS,
                        )
                    )
                raw = "|".join(str(v) for v in chosen)
                rows.append(
                    {
                        "session_id": self.session_id,
                        "unit_id": self._unit_id(stream, int(label), width),
                        "source": "manual" if category == MANUAL_CATEGORY else f"manual:{category}",
                        "label": raw,
                        "normalized_label": PROJECTION.get(raw) if len(chosen) == 1 else None,
                    }
                )
        return rows

    # -- spikes, which do not fit in memory as records ----------------------------------

    def spike_batches(self, *, batch_rows: int = 1_000_000) -> Iterator[pa.RecordBatch]:
        """`core.spike_events`, streamed in the registry's sort order.

        Yielded stream by stream in `sorting_run_id` order, and within a stream sorted by
        `(unit_id, t_tick)`. That is exactly Part 03's ordering for this table, so no global sort
        is ever needed -- each curated folder is one `(sorting_run, curation)` group, and the
        groups are disjoint.

        The sort key is `(unit_index, sample_index)` packed into one int64. It stands in for
        the string `unit_id` only because that id is zero-padded, which is what makes its
        lexicographic order agree with numeric order.

        Parameters
        ----------
        batch_rows : int, default 1_000_000
            Rows per batch, and therefore the writer's peak memory.

        Yields
        ------
        pyarrow.RecordBatch
        """
        for stream in self.streams():
            ids = self._unit_ids(stream)
            width = self._width(stream)
            index, tick = self._spikes(stream)
            amplitude = self._amplitudes(stream, index.size)
            if tick.size and int(tick.max()) >= 1 << 32:
                raise SourceDefect(
                    f"{stream.key}: sample index {int(tick.max())} does not fit the packed sort key",
                    code=SourceFault.SAMPLE_INDEX_OVERFLOW,
                    where=stream.key,
                )
            order = np.argsort((index.astype(np.int64) << 32) | tick, kind="stable")
            # Dictionary-encoded against names built once a stream, so no batch builds a Python
            # string per row and `number_batch` maps a few hundred names rather than a million
            # strings a batch: the indices are already what `index` holds.
            unit_names = pa.array([self._unit_id(stream, int(label), width) for label in ids], type=pa.string())
            for start in range(0, order.size, batch_rows):
                selected = order[start : start + batch_rows]
                rows = selected.size
                # `pa.repeat` for `session_id`, which is constant within a stream: a
                # million-element Python list would cost more than the spikes. No `clock_id`:
                # the tick reaches its clock through the unit (R96 §3.4).
                columns = {
                    "session_id": pa.repeat(pa.scalar(self.session_id, pa.string()), rows),
                    "unit_id": pa.DictionaryArray.from_arrays(pa.array(index[selected], type=pa.int32()), unit_names),
                    "t_tick": pa.array(tick[selected], type=pa.int64()),
                }
                if amplitude is not None:
                    columns["amplitude"] = pa.array(amplitude[selected], type=pa.float32())
                yield pa.record_batch(columns)

    # -- assembly -----------------------------------------------------------------------

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records; spikes are not among them."""
        built = {
            CORE_PROBES: self.probes(),
            CORE_CLOCKS: self.clocks(),
            CORE_SORTING_RUNS: self.sorting_runs(),
            CORE_SORTING_RUN_CHANNELS: self.sorting_run_channels(),
            CORE_CURATION_VERSIONS: self.curation_versions(),
            CORE_UNITS: self.units(),
            CORE_UNIT_QUALITY_LABELS: self.unit_quality_labels(),
            CORE_CLOCK_OBSERVATION_INTERVALS: self.observation_intervals(),
            CORE_PROCESSING_RUNS: self.processing_runs(),
        }
        return {resource: rows for resource, rows in built.items() if rows}

    def into(self, writer: Any, *, batch_rows: int = 1_000_000) -> dict[str, int]:
        """Add every record and the spike stream to a :class:`~escapewheel_writer.writer.PacketWriter`.

        Returns
        -------
        dict
            Row counts per resource. `core.spike_events` counts the source's spikes, since
            the batches themselves are not materialized here.
        """
        counted = {}
        for resource, rows in self.records().items():
            writer.add(resource, rows)
            counted[resource] = len(rows)
        writer.add_batches(CORE_SPIKE_EVENTS, self.spike_batches(batch_rows=batch_rows))
        counted[CORE_SPIKE_EVENTS] = self.spike_count
        return counted

    @property
    def spike_count(self) -> int:
        """How many spikes this source holds, from the arrays' headers rather than contents.

        A quarter of a billion spikes counts in milliseconds, so a caller that has streamed
        them into a writer can still report how many without holding any.
        """
        held = (self._npy_rows(s.path / "spikes.npy") for s in self.streams())
        return sum(n if self.sample is None else min(n, self.sample) for n in held)

    def offers(self) -> dict[str, int]:
        """Which resources this source supplies from its root, and how many rows (Part 05 §4.1)."""
        return {
            **{resource: len(rows) for resource, rows in self.records().items()},
            CORE_SPIKE_EVENTS: self.spike_count,
        }


__all__ = ["DESIGNATED", "LABEL_SOURCES", "PROJECTION", "STREAM_WORKERS", "SortedStream", "SorterSource"]

"""A SpikeInterface asset's streams by name, and what a curated sorting reads from its analyzer.

- :data:`STREAM_FOLDER` -- the pattern a stream folder's name follows.
- :class:`SortedStream` -- one stream folder, with its name parsed.
- :func:`parse_stream` -- a curated folder as a :class:`SortedStream`, or a refusal.
- :func:`locate` -- the SortingAnalyzer beside a curated stream, where the asset carries one.
- :func:`recording_length`, :func:`channel_ids` -- the sorted recording's length and channels.
- :func:`amplitude_unit`, :func:`amplitudes` -- per-spike amplitudes and the unit they are in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from escapewheel_reader.resources import ZARR_METADATA_FILENAMES
from numpy.typing import NDArray

from ..errors import SourceDefect, SourceFault
from ..notes import Note, NoteCode
from .zarr_compat import attrs, attrs_at, read_array

#: ``experiment1_Record Node 109#Neuropix-PXI-100.50720-1_recording1``. The probe token holds
#: no underscore, which is what lets the recording suffix be split off unambiguously.
STREAM_FOLDER = re.compile(
    r"^(?P<experiment>experiment\d+)_Record Node (?P<node>\d+)#(?P<probe>[^_]+)_(?P<recording>recording\d+)$"
)

#: A quad-base probe is sorted as four shank streams that share one physical device.
SHANK = re.compile(r"^(?P<serial>.+?)-(?P<shank>\d+)$")


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


def parse_stream(path: Path) -> SortedStream:
    """Parse a curated folder name, or refuse it."""
    found = STREAM_FOLDER.match(path.name)
    if not found:
        raise SourceDefect(
            f"{path.name} is not a curated stream folder name", code=SourceFault.STREAM_NAME, where=path.name
        )
    return SortedStream(path=path, **found.groupdict())


def locate(curated: Path, stream: SortedStream) -> Path | None:
    """Locate the SortingAnalyzer for a stream, if the asset carries one."""
    path = curated.parent / "postprocessed" / f"{stream.path.name}.zarr"
    return path if path.is_dir() else None


def recording_length(curated: Path, stream: SortedStream, notes: list[str]) -> int | None:
    """How many samples the sorted recording holds, from the analyzer's `recording_info`.

    This is the one place the length of the raw acquisition survives into the sorted
    asset: SpikeInterface records the recording's attributes beside the sorting, so a
    packet built from a sorting alone can still say when the probe was running without
    reaching for the compressed AP data or for a JSON that rounds to whole seconds.
    """
    analyzer = locate(curated, stream)
    if analyzer is None:
        return None
    recorded = attrs_at(analyzer, "recording_info").get("recording_attributes") or {}
    lengths = recorded.get("num_samples") or []
    if len(lengths) != 1:
        # Each segment restarts the counter, so a multi-segment recording is more than one
        # clock (Part 01 §3.9) and its length is not one interval on this one.
        notes.append(
            Note(
                f"{stream.key}: {len(lengths)} recording segments; no observation window written",
                NoteCode.SEVERAL_SEGMENTS,
            )
        )
        return None
    return int(lengths[0])


def channel_ids(curated: Path, stream: SortedStream) -> list[str] | None:
    """Return the channels the sorting ran on in its own order, or None where it states none."""
    analyzer = locate(curated, stream)
    if analyzer is None:
        return None
    recorded = attrs_at(analyzer, "recording_info").get("recording_attributes") or {}
    return [str(c) for c in recorded["channel_ids"]] if recorded.get("channel_ids") else None


def amplitude_unit(curated: Path, stream: SortedStream, notes: list[str]) -> str | None:
    """`uV` or `{adc}`, from the analyzer's own setting (R11 §2).

    Null when no analyzer is present, which is also when no amplitudes are emitted --
    `amplitude_unit_declared` binds only where amplitudes exist.
    """
    analyzer = locate(curated, stream)
    if analyzer is None:
        return None
    settings = attrs(analyzer).get("settings") or {}
    if "return_in_uV" not in settings:
        notes.append(
            Note(f"{stream.key}: analyzer declares no return_in_uV; amplitude unit unknown", NoteCode.UNIT_UNSTATED)
        )
        return None
    # `{adc}` is a UCUM annotation, a dimensionless count of converter steps (Part 02 §8.4).
    return "uV" if settings["return_in_uV"] else "{adc}"


def amplitudes(
    curated: Path, stream: SortedStream, n_spikes: int, *, sample: int | None, notes: list[str]
) -> NDArray[Any] | None:
    """Per-spike amplitudes, in the source's own row order, or None."""
    analyzer = locate(curated, stream)
    if analyzer is None:
        return None
    path = analyzer / "extensions" / "spike_amplitudes" / "amplitudes"
    if not (path / ZARR_METADATA_FILENAMES[2]).is_file():
        notes.append(Note(f"{stream.key}: analyzer carries no spike_amplitudes", NoteCode.NO_AMPLITUDES))
        return None
    values = read_array(path)
    # A sample truncates the spikes, so it must truncate their amplitudes by the same rule:
    # these are index-aligned, and the check below is what guarantees it.
    if sample is not None:
        values = values[:sample]
    if values.size != n_spikes:
        raise SourceDefect(
            f"{stream.key}: {values.size} amplitudes for {n_spikes} spikes; they are index-aligned or nothing",
            code=SourceFault.AMPLITUDES_MISALIGNED,
            where=stream.key,
        )
    return values


__all__ = [
    "STREAM_FOLDER",
    "SortedStream",
    "amplitude_unit",
    "amplitudes",
    "channel_ids",
    "locate",
    "parse_stream",
    "recording_length",
]

"""Behaviour videos as external resources, with one row per frame on the rig clock.

- :class:`VideoSource` -- `core.media_assets` and `core.media_frames` for the videos under a root,
  each referenced as an external resource.
- :func:`resource_name` -- a resource-ID name for a video, from its file stem.

The source pairs each frame with a time that falls behind by one trigger period for every frame the
host dropped. The adapter therefore reconstructs `t_tick` from the camera's own frame counter, and
declares the repair as `video.zip_pairing_repaired`. A trigger time out of order with both its
neighbours is replaced by their midpoint, declared as `video.trigger_time_out_of_line`.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator, Mapping
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import quote, urlsplit

import numpy as np
import pyarrow as pa
from escapewheel_reader.resource_ids import CORE_MEDIA_ASSET_INSTANCES, CORE_MEDIA_ASSETS, CORE_MEDIA_FRAMES
from escapewheel_writer.adapter import (
    FILES,
    FLIGHT,
    STREAM,
    Compensates,
    ExternalMedia,
    Note,
    SourceDefect,
    source_root,
    store_uri,
)

from .errors import AindFault
from .mp4 import presentation
from .notes import AindNote

#: Rows per emitted batch. A camera writes ~2.5 M frames a session and three cameras 7.5 M, which
#: is why the frame table streams rather than being held as records.
BATCH_ROWS = 500_000

#: The container this adapter references. A camera here writes both an AVI and an MP4 of one
#: capture; this adapter selects the MP4 for its specialized consumer. The portable profile treats
#: the payload as opaque and does not enumerate its container (Part 03 §2).
SUFFIX = ".mp4"

#: What the timing CSV's leading columns hold, in order. Written by `foraging.bonsai`'s CsvWriter as
#: `Seconds,Value.ChunkData.FrameID,Value.ChunkData.Timestamp`; an older workflow appends exposure
#: and gain, which are not read.
COLUMNS = ("rig_seconds", "frame_counter", "camera_nanoseconds")

#: Ticks per second of the clock the CSV's first column is quantised to.
HARP_TICKS = 31250

#: Runs of characters Part 04 §4.1 does not admit after a resource ID's dot.
_INADMISSIBLE = re.compile(r"[^a-z0-9_.-]+")


def resource_name(stem: str) -> str:
    """Return a resource-ID name for a video from its file stem, however spelled (Part 04 §4.1).

    Accents are dropped, case is folded, and every other run of inadmissible characters becomes one
    `_`, so `Side Camera (Left)` is `side_camera_left`. A stem with nothing left is named by its
    digest. `media_asset_name` keeps the stem as it came.
    """
    ascii_only = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    return _INADMISSIBLE.sub("_", ascii_only.lower()).strip("_") or _digest(stem)


def _digest(stem: str) -> str:
    """Return eight hex digits naming a stem, stable across runs and independent of its siblings."""
    return hashlib.sha256(stem.encode()).hexdigest()[:8]


class VideoSource(Compensates):
    """`core.media_assets` and `core.media_frames` for the videos under `root`.

    Parameters
    ----------
    root : str or Path
        A directory holding videos and, beside each, a CSV of the same stem giving its frame
        timing. A video with no CSV is referenced and contributes no frames. A store root is read
        in place: the CSVs through the source cache, and from each video only its MP4 index, by
        range reads.
    session_id : str
        The session these were recorded in.
    reference_clock : Mapping
        The `core.clocks` row of the clock the CSV's first column is in seconds of
        (Part 12 §4). Only its `clock_id` is read: the CSV states a frame's tick, so nothing
        here converts.
    uri_base : str, optional
        Absolute base the videos are addressed under. Without one they are addressed where `root`
        holds them, which for a local root is a `file://` URI that resolves only on the machine
        that built it.
    prefix : str, optional
        Prepended to every media asset ID and name, and to the name part of the resource ID each
        video is referenced under, which a build binds to the asset by that name (Part 12 §5).
        The reference clock is not this adapter's to name, so it is left as given.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).
    """

    #: Part 12 §3: released apart from the writer, so it declares its protocols. `escapewheel
    #: deliver` serves every one; the first is what a build reaches it by when a recipe names none.
    PROTOCOLS: ClassVar[tuple[str, ...]] = (STREAM, FILES, FLIGHT)

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({CORE_MEDIA_ASSETS, CORE_MEDIA_FRAMES})

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply, resolved against Part 12 §4's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    #:
    #: An option the adapter can run without is left out: a declared name a recipe does not set
    #: resolves to nothing, so declaring one makes it mandatory.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "reference_clock")

    #: Part 05 §3.4: options this adapter reads and can run without, which a recipe may leave
    #: unset (Part 12 §4).
    ACCEPTS: ClassVar[tuple[str, ...]] = ("uri_base", "batch_rows", "prefix", "source_cache")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        reference_clock: Mapping[str, Any],
        uri_base: str | None = None,
        batch_rows: int = BATCH_ROWS,
        prefix: str = "",
        source_cache: str | None = None,
    ) -> None:
        self.root = source_root(root, cache=source_cache)
        self.session_id = session_id
        self.clock_id = str(reference_clock["clock_id"])
        self.remote = getattr(self.root, "protocol", "") not in ("", "file")
        #: Whether the addressed videos are the ones read here, which is what makes a size a claim.
        self.addressed_here = not uri_base
        self.uri_base = uri_base.rstrip("/") if uri_base else (store_uri(self.root) if self.remote else None)
        self.batch_rows = batch_rows
        self.prefix = prefix
        super().__init__()
        self.notes: list[str] = []
        self._indexes: dict[Path, tuple[int, int, np.ndarray]] = {}
        self._triggers: dict[Path, tuple[np.ndarray, np.ndarray]] = {}

    def videos(self) -> list[Path]:
        """Every video under `root`, whatever the case of its suffix, sorted so two runs number them alike."""
        return sorted(p for p in self.root.iterdir() if p.suffix.lower() == SUFFIX and p.is_file())

    @cached_property
    def _names(self) -> dict[Path, str]:
        """Each video's asset key, which is also the name in its resource ID.

        Stems that fold to one name each take their own digest as a suffix rather than a position,
        so adding a camera never renames another.
        """
        folded = {video: resource_name(video.stem) for video in self.videos()}
        taken = Counter(folded.values())
        return {
            video: self.prefix + (name if taken[name] == 1 else f"{name}-{_digest(video.stem)}")
            for video, name in folded.items()
        }

    def _timing(self, video: Path) -> Path | None:
        """Return the CSV beside a video, whatever the case of its suffix, or None where it has none."""
        beside = [p for p in video.parent.iterdir() if p.stem == video.stem and p.suffix.lower() == ".csv"]
        return beside[0] if len(beside) == 1 and beside[0].is_file() else None

    def _uri(self, video: Path) -> str:
        """Where this video is addressed, absolutely and percent-encoded (Part 03 §4, Part 04 §5.1)."""
        if self.uri_base:
            return f"{self.uri_base}/{quote(video.name, safe='')}"
        return video.resolve().as_uri()

    def _readable(self, video: Path) -> str:
        """Return what ffprobe opens for a video: its path, or the HTTPS URL of a public object.

        A store root is opened anonymously (Part 12 §10), so the object is public and its URL needs
        no signature.
        """
        if not self.remote:
            return str(video)
        uri = urlsplit(store_uri(video))
        if uri.scheme in ("http", "https"):
            return uri.geturl()
        if uri.scheme == "s3":
            return f"https://{uri.netloc}.s3.amazonaws.com{quote(uri.path)}"
        raise SourceDefect(
            f"{video}: ffprobe reads no {uri.scheme}:// object", code=AindFault.VIDEO_UNREADABLE, where=str(video)
        )

    def external_media(self) -> dict[str, ExternalMedia]:
        """Each video as a resource the packet references and does not own."""
        found = {}
        for video in self.videos():
            name = self._names[video]
            found[f"core.{name}"] = ExternalMedia(
                media_asset_id=name,
                declaration_id=CORE_MEDIA_ASSET_INSTANCES,
                uri=self._uri(video),
                format=SUFFIX.lstrip("."),
                # Part 04 §5.2: a writer records only what it looked at. The video read here can be
                # sized; a base addressing another copy says nothing about what is actually there.
                size_bytes=video.stat().st_size if self.addressed_here else None,
            )
        return found

    def media_assets(self) -> list[dict[str, Any]]:
        """`core.media_assets`, one row per video.

        Declares the timing repair here rather than where it is applied: the frame table streams,
        and a generator's compensations are collected before it has run. Declaring it in a path
        the build actually walks is what keeps it in the packet's provenance.
        """
        rows = []
        for video in self.videos():
            timing = self._timing(video)
            if timing is None:
                self.notes.append(
                    Note(f"{video.name}: no timing CSV beside it; referenced without frames", AindNote.NO_TIMING)
                )
            else:
                self.compensate("video.zip_pairing_repaired")
                # Read here rather than in `_frames`, whose compensations are collected before it runs.
                self._timed(video)
            rows.append(
                {
                    "media_asset_id": self._names[video],
                    "session_id": self.session_id,
                    "semantic_type": "behavior_video",
                    "media_asset_name": self.prefix + video.stem,
                    "resource_id": f"core.{self._names[video]}",
                    **(self._pts_rate(video) if timing else {}),
                    "clock_id": self.clock_id if timing else None,
                }
            )
        return rows

    def _pts_rate(self, video: Path) -> dict[str, int]:
        """Return what a consumer needs to read this asset's `pts` column as time (Part 01 §3.18).

        A container states a *time base* -- seconds per timestamp -- and core carries the
        reciprocal, so `core.media_assets` agrees with `core.clocks` about what a rational rate
        looks like. The inversion happens here, once, which is the boundary that section puts it at.

        Rational rather than a float, because 1/90000 has no exact decimal and a
        rounded one accumulates over the millions of frames a session holds.
        """
        num, den, _ = self._index(video)
        return {"pts_rate_num": den, "pts_rate_den": num}

    def _presentation(self, video: Path) -> np.ndarray:
        """Presentation timestamps of the frames the video presents, in container units (Part 01 §3.18)."""
        return self._index(video)[2]

    def _index(self, video: Path) -> tuple[int, int, np.ndarray]:
        """Return a video's time base and sorted presentation timestamps, read once.

        Read from the MP4 index, a few MB however long the video, so a remote one is timed without
        a download. An MP4 that index cannot time is listed by ffprobe, which reads every packet.
        """
        if video in self._indexes:
            return self._indexes[video]
        opened = source_root(store_uri(video)) if self.remote else video
        try:
            with opened.open("rb") as handle:
                found = presentation(handle)
        except SourceDefect as why:
            if why.code != AindFault.VIDEO_UNINDEXED:
                raise
            self.notes.append(Note(f"{video.name}: {why}, so ffprobe lists its packets", AindNote.INDEX_UNREAD))
            found = self._probed(video)
        self._indexes[video] = found
        return found

    def _probed(self, video: Path) -> tuple[int, int, np.ndarray]:
        """Ffprobe's time base and packets for a video, less those it flags `D` as the edit list excludes."""
        num, _, den = _ffprobe(self._readable(video), "stream=time_base").strip().partition("/")
        out = _ffprobe(self._readable(video), "packet=pts,flags")
        presented = (line.split(",") for line in out.split())
        values = np.fromiter((int(pts) for pts, flags in presented if "D" not in flags), dtype=np.int64)
        # Packets arrive in decode order, which B-frames reorder; diffing that reports false gaps.
        values.sort()
        return int(num), int(den or 1), values

    def _timed(self, video: Path) -> tuple[np.ndarray, np.ndarray]:
        """Return a video's trigger ticks and frame counter from its CSV, repaired and read once."""
        if video in self._triggers:
            return self._triggers[video]
        from pyarrow import csv

        timing = self._timing(video)
        assert timing is not None
        with timing.open("rb") as handle:
            width = handle.readline().count(b",") + 1
            handle.seek(0)
            table = csv.read_csv(
                handle,
                read_options=csv.ReadOptions(column_names=[*COLUMNS, *(f"_{i}" for i in range(width - 3))]),
                convert_options=csv.ConvertOptions(
                    column_types=dict.fromkeys(COLUMNS, pa.float64()), include_columns=list(COLUMNS)
                ),
            )
        seconds = table.column(COLUMNS[0]).to_numpy(zero_copy_only=False)
        counter = table.column(COLUMNS[1]).to_numpy(zero_copy_only=False).astype(np.int64)
        triggers = np.rint(seconds * HARP_TICKS).astype(np.int64)
        if (repaired := in_line(triggers)).size:
            self.compensate("video.trigger_time_out_of_line")
            self.notes.append(
                Note(
                    f"{video.name}: {repaired.size} trigger time(s) outside the span of their neighbours; "
                    "replaced by its midpoint",
                    AindNote.TRIGGER_REPAIRED,
                )
            )
        self._triggers[video] = (triggers, counter)
        return triggers, counter

    def _frames(self, video: Path) -> Iterator[pa.RecordBatch]:
        """One batch at a time of a video's frames, timed by the reconstruction above."""
        if self._timing(video) is None:
            return
        triggers, counter = self._timed(video)
        # Held only until its frames are emitted: three cameras' CSVs are tens of MB each.
        self._triggers.pop(video)

        pts = self._presentation(video)
        complete = pts.size == counter.size
        if complete:
            # A complete video is read in order: timestamps can skip where a transcode was
            # stitched from chunks without any picture going missing.
            rows = np.arange(pts.size, dtype=np.int64)
        else:
            # A short video's surviving frames carry their original row in their timestamps: an
            # encoder that drops pictures keeps the timeline, which is what makes the loss
            # identifiable rather than a silent renumbering.
            step = int(np.median(np.diff(pts))) if pts.size > 1 else 1
            rows = (pts - pts[0]) // step
        inside = rows < counter.size
        if not inside.all():
            self.notes.append(
                Note(
                    f"{video.name}: {int((~inside).sum())} frame(s) index past the timing file; dropped",
                    AindNote.FRAME_PAST_TIMING,
                )
            )
            pts, rows = pts[inside], rows[inside]
        if (missing := counter.size - rows.size) > 0:
            self.notes.append(
                Note(f"{video.name}: {missing} timed frame(s) absent from the video (transcode)", AindNote.FRAME_ABSENT)
            )

        # Every value in the first column is a real trigger timestamp; only the frame each was
        # written beside is wrong. So the repair is a lookup rather than a fit: exposure k was
        # triggered at the k-th recorded time. Frames past the last recorded trigger extrapolate
        # at the period the file measures, which reproduces the recorded times to 0.5 ms where
        # both exist.
        period = (triggers[-1] - triggers[0]) / (triggers.size - 1)
        exposures = counter[rows] - counter[0]
        ticks = np.empty(exposures.size, dtype=np.int64)
        known = exposures < triggers.size
        ticks[known] = triggers[exposures[known]]
        if (beyond := ~known).any():
            last = triggers.size - 1
            ticks[beyond] = triggers[last] + np.rint((exposures[beyond] - last) * period).astype(np.int64)
            self.notes.append(
                Note(
                    f"{video.name}: {int(beyond.sum()):,} frame(s) past the last recorded trigger; "
                    f"extrapolated at {period:.5f} ticks",
                    AindNote.FRAME_EXTRAPOLATED,
                )
            )
        # True where anything is missing immediately before this frame, from either cause. An
        # incomplete video's first frame is assumed to be the first exposure, so whether any came
        # before it is unknown, which the flag records as null (Part 01 §3.18).
        gap = np.empty(ticks.size, dtype=bool)
        gap[0] = False
        np.greater(np.diff(exposures), 1, out=gap[1:])
        unknown = np.zeros(ticks.size, dtype=bool)
        unknown[0] = not complete

        for start in range(0, ticks.size, self.batch_rows):
            stop = min(start + self.batch_rows, ticks.size)
            yield pa.record_batch(
                {
                    "media_asset_id": pa.array([self._names[video]] * (stop - start)),
                    "frame_index": pa.array(np.arange(start, stop, dtype=np.int64)),
                    "t_tick": pa.array(ticks[start:stop]),
                    "clock_id": pa.array([self.clock_id] * (stop - start)),
                    "pts": pa.array(pts[start:stop]),
                    "dropped": pa.array(gap[start:stop], mask=unknown[start:stop]),
                }
            )

    def frame_count(self, video: Path) -> int:
        """How many frames a video's CSV declares, counted without holding them."""
        timing = self._timing(video)
        if timing is None:
            return 0
        with timing.open("rb") as handle:
            return sum(block.count(b"\n") for block in iter(lambda: handle.read(1 << 22), b""))

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource this root holds."""
        return {**{resource: len(rows) for resource, rows in self.records().items()}, **self.stream_rows()}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records. Frames stream, so they are not here."""
        built = {CORE_MEDIA_ASSETS: self.media_assets()}
        return {resource: rows for resource, rows in built.items() if rows}

    def batches(self) -> dict[str, Iterator[pa.RecordBatch]]:
        """`core.media_frames`, streamed one camera at a time."""

        def every() -> Iterator[pa.RecordBatch]:
            for video in self.videos():
                yield from self._frames(video)

        return {CORE_MEDIA_FRAMES: every()} if self.videos() else {}

    def stream_rows(self) -> dict[str, int]:
        """How many frames `batches` streams, counted from each camera's container."""
        frames = sum(self.frame_count(video) for video in self.videos())
        return {CORE_MEDIA_FRAMES: frames} if frames else {}


def in_line(triggers: np.ndarray) -> np.ndarray:
    """Replace, in place, each trigger time outside the span of its two neighbours, and return where.

    Only a value whose neighbours are themselves in order is replaced, by their midpoint as recorded:
    a trigger is periodic, so that is within a period of the true time. Two adjacent values out of
    order with each other each qualify, since neither can be singled out, and both are replaced. Any
    other disorder is left for validation to refuse rather than guessed at.
    """
    before, value, after = triggers[:-2], triggers[1:-1], triggers[2:]
    where = np.nonzero((before <= after) & ((value < before) | (value > after)))[0] + 1
    triggers[where] = (triggers[where - 1] + triggers[where + 1]) // 2
    return where


def _ffprobe(video: str, entries: str) -> str:
    """Ask ffprobe for one set of entries about a video's first video stream."""
    import subprocess

    # A dropped connection resumes from the byte it reached rather than ending the listing early.
    resume = ["-reconnect", "1", "-reconnect_on_network_error", "1"] if video.startswith("http") else []
    selected = ["-select_streams", "v:0", "-show_entries", entries, "-of", "csv=p=0"]
    return subprocess.run(
        ["ffprobe", "-v", "error", *resume, *selected, video],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


__all__ = ["BATCH_ROWS", "COLUMNS", "SUFFIX", "VideoSource", "in_line"]

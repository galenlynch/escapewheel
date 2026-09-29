"""Behaviour videos, referenced rather than copied, with the timing the packet does own.

**The timing in the source is wrong and is reconstructed here** (`video.zip_pairing_repaired`).
The acquiring workflow joins the camera stream to the rig's timestamp stream with `rx:Zip`
(`dynamic-foraging-task`, `src/workflows/foraging.bonsai:8112`), which pairs by position. The
host drops frames in bursts, so every drop shifts the pairing by one and the recorded time falls
behind real time by one trigger period per lost frame -- 93.4 s by the end of a measured session.

What survives intact is the camera's own chunk data: `FrameID` counts exposures and skips where
one was lost, and the hardware timestamp accounts for every gap. Since the cameras are triggered,
exposure *k* is trigger *k*, so the frame's time is recovered exactly:

    t_tick = t0 + (FrameID - FrameID_0) x trigger_period

`t0` is the one pairing that is still correct -- nothing has dropped before the first frame -- and
the trigger period is measured from the file itself. Checked against the camera's independent
hardware clock, the reconstruction agrees to 35-85 ms over 85 minutes, against the 93 s error it
replaces.

Three cameras of one session are 10 GB as MP4 and 80 GB as the AVI they were encoded from, so a
packet that copied them would be mostly video (Part 04 §5.1). What it owns instead is one row per
frame on a declared clock, which is the part no player can supply: an MP4 knows its own
presentation timestamps and nothing about the rig's clock. It could own a video instead by declaring
`opaque_location` and delivering the file as a payload (Part 12 §5).

Each camera writes a CSV beside its video, one line per frame and three columns:

```
14425755.839584,1379782224,14593876902543944
```

- the frame's time in **seconds on the rig clock**, which is what `t_tick` is derived from;
- a **frame counter** that skips where frames were lost, which is what `dropped` is derived from;
- the **camera's own clock** in nanoseconds, which is what the repair was checked against.

`pts` carries none of the three. It is the frame's presentation timestamp in the **container**,
an integer of the container's own time base (Part 01 §3.18), which is what locates a row in the file a
consumer opens. The asset declares the rate those timestamps count at (Part 01 §3.18), so
`pts * pts_rate_den / pts_rate_num` is seconds of video without opening it, where `t_tick` is the
same frame on the rig clock.

Frames are numbered in presentation order (Part 01 §3.18), which is why the container index is sorted
before it is read: packets arrive in decode order, and this stream displaces one by up to three
positions from where it is shown.
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
from urllib.parse import quote

import numpy as np
import pyarrow as pa
from escapewheel_writer.declaration import FILES, FLIGHT, STREAM
from escapewheel_writer.sources.compensations import Compensates
from escapewheel_writer.sources.store import source_root
from escapewheel_writer.writer import ExternalMedia

#: Rows per emitted batch. A camera writes ~2.5 M frames a session and three cameras 7.5 M, which
#: is why the frame table streams rather than being held as records.
BATCH_ROWS = 500_000

#: The container this adapter references. A camera here writes both an AVI and an MP4 of one
#: capture; this adapter selects the MP4 for its specialized consumer. The portable profile treats
#: the payload as opaque and does not enumerate its container (Part 03 §2).
SUFFIX = ".mp4"

#: What the timing CSV's columns hold, in order. Written by `foraging.bonsai`'s CsvWriter as
#: `Seconds,Value.ChunkData.FrameID,Value.ChunkData.Timestamp`.
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
        timing. A video with no CSV is referenced and contributes no frames.
    session_id : str
        The session these were recorded in.
    reference_clock : Mapping
        The `core.clocks` row of the clock the CSV's first column is in seconds of
        (Part 12 §4). Only its `clock_id` is read: the CSV states a frame's tick, so nothing
        here converts.
    uri_base : str, optional
        Absolute base the videos are addressed under. Without one the packet records a `file://`
        URI, which resolves only on the machine that built it.
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
    PRODUCES = frozenset({"core.media_assets", "core.media_frames"})

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
        self.uri_base = uri_base.rstrip("/") if uri_base else None
        self.batch_rows = batch_rows
        self.prefix = prefix
        super().__init__()
        self.notes: list[str] = []

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

    def external_media(self) -> dict[str, ExternalMedia]:
        """Each video as a resource the packet references and does not own."""
        found = {}
        for video in self.videos():
            name = self._names[video]
            local = self.uri_base is None
            found[f"core.{name}"] = ExternalMedia(
                media_asset_id=name,
                declaration_id="core.media_asset_instances",
                uri=self._uri(video),
                format=SUFFIX.lstrip("."),
                # Part 04 §5.2: a writer records only what it looked at. A local path can be sized;
                # a remote base says nothing about what is actually there.
                size_bytes=video.stat().st_size if local else None,
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
                self.notes.append(f"{video.name}: no timing CSV beside it; referenced without frames")
            else:
                self.compensate("video.zip_pairing_repaired")
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
        looks like. The inversion happens here, once, which is the boundary Part 01 §3.18 puts it at.

        Rational rather than a float, for the reason R33 gives: 1/90000 has no exact decimal and a
        rounded one accumulates over the millions of frames a session holds.
        """
        num, _, den = _ffprobe(video, "stream=time_base").strip().partition("/")
        return {"pts_rate_num": int(den or 1), "pts_rate_den": int(num)}

    def _presentation(self, video: Path) -> np.ndarray:
        """Presentation timestamps of the frames the video actually holds, in container units.

        Read from the container index rather than by decoding -- 13 s for 2.5 M frames. Sorted,
        because packets arrive in decode order and B-frames reorder them; diffing decode order
        reports gaps that are not there.
        """
        out = _ffprobe(video, "packet=pts")
        values = np.fromiter((int(x) for x in out.replace(",", " ").split()), dtype=np.int64)
        values.sort()
        return values

    def _frames(self, video: Path) -> Iterator[pa.RecordBatch]:
        """One batch at a time of a video's frames, timed by the reconstruction above."""
        from pyarrow import csv

        timing = self._timing(video)
        if timing is None:
            return
        table = csv.read_csv(
            timing,
            read_options=csv.ReadOptions(column_names=list(COLUMNS)),
            convert_options=csv.ConvertOptions(column_types=dict.fromkeys(COLUMNS, pa.float64())),
        )
        seconds = table.column(COLUMNS[0]).to_numpy(zero_copy_only=False)
        counter = table.column(COLUMNS[1]).to_numpy(zero_copy_only=False).astype(np.int64)

        pts = self._presentation(video)
        if pts.size == counter.size:
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
            self.notes.append(f"{video.name}: {int((~inside).sum())} frame(s) index past the timing file; dropped")
            pts, rows = pts[inside], rows[inside]
        if (missing := counter.size - rows.size) > 0:
            self.notes.append(f"{video.name}: {missing} timed frame(s) absent from the video (transcode)")

        # Every value in the first column is a real trigger timestamp; only the frame each was
        # written beside is wrong. So the repair is a lookup rather than a fit: exposure k was
        # triggered at the k-th recorded time. Frames past the last recorded trigger extrapolate
        # at the period the file measures, which reproduces the recorded times to 0.5 ms where
        # both exist.
        triggers = np.rint(seconds * HARP_TICKS).astype(np.int64)
        period = (triggers[-1] - triggers[0]) / (triggers.size - 1)
        exposures = counter[rows] - counter[0]
        ticks = np.empty(exposures.size, dtype=np.int64)
        known = exposures < triggers.size
        ticks[known] = triggers[exposures[known]]
        if (beyond := ~known).any():
            last = triggers.size - 1
            ticks[beyond] = triggers[last] + np.rint((exposures[beyond] - last) * period).astype(np.int64)
            self.notes.append(
                f"{video.name}: {int(beyond.sum()):,} frame(s) past the last recorded trigger; "
                f"extrapolated at {period:.5f} ticks"
            )
        # True where anything is missing immediately before this frame, from either cause.
        gap = np.empty(ticks.size, dtype=bool)
        gap[0] = False
        np.greater(np.diff(exposures), 1, out=gap[1:])

        for start in range(0, ticks.size, self.batch_rows):
            stop = min(start + self.batch_rows, ticks.size)
            yield pa.record_batch(
                {
                    "media_asset_id": pa.array([self._names[video]] * (stop - start)),
                    "frame_index": pa.array(np.arange(start, stop, dtype=np.int64)),
                    "t_tick": pa.array(ticks[start:stop]),
                    "clock_id": pa.array([self.clock_id] * (stop - start)),
                    "pts": pa.array(pts[start:stop]),
                    "dropped": pa.array(gap[start:stop]),
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
        videos = self.videos()
        return {
            "core.media_assets": len(videos),
            "core.media_frames": sum(self.frame_count(v) for v in videos),
        }

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records. Frames stream, so they are not here."""
        built = {"core.media_assets": self.media_assets()}
        return {resource: rows for resource, rows in built.items() if rows}

    def batches(self) -> dict[str, Iterator[pa.RecordBatch]]:
        """`core.media_frames`, streamed one camera at a time."""

        def every() -> Iterator[pa.RecordBatch]:
            for video in self.videos():
                yield from self._frames(video)

        return {"core.media_frames": every()}


def _ffprobe(video: Path, entries: str) -> str:
    """Ask ffprobe for one set of entries about a video's first video stream."""
    import subprocess

    return subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", entries, "-of", "csv=p=0", str(video)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


__all__ = ["BATCH_ROWS", "COLUMNS", "SUFFIX", "VideoSource"]

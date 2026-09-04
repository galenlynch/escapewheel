"""Behaviour videos, referenced rather than copied, with the timing the packet does own.

Three cameras of one session are 10 GB as MP4 and 80 GB as the AVI they were encoded from, so a
packet that copied them would be mostly video (R14 §2.3). What it owns instead is one row per
frame on a declared clock, which is the part no player can supply: an MP4 knows its own
presentation timestamps and nothing about the rig's clock.

Each camera writes a CSV beside its video, one line per frame and three columns:

```
14425755.839584,1379782224,14593876902543944
```

- the frame's time in **seconds on the rig clock**, which is what `t_tick` is derived from;
- a **frame counter** that skips where frames were lost, which is what `dropped` is derived from;
- the **camera's own clock** in nanoseconds, carried as `pts`.

The last two disagree by design and that is why both are kept: measured on this session the rig
clock advances 1.952 ms a frame where the camera's advances 1.999 ms, so a consumer aligning by
one gets a different answer than by the other, and only the rig clock relates a frame to a spike.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa

from ..writer import ExternalMedia

#: Rows per emitted batch. A camera writes ~2.5 M frames a session and three cameras 7.5 M, which
#: is why the frame table streams rather than being held as records.
BATCH_ROWS = 500_000

#: The container this adapter references. A camera here writes both an AVI and an MP4 of one
#: capture; the MP4 is what the portable profile names (`03` §2) and what a reader will open.
SUFFIX = ".mp4"

#: What the timing CSV's columns hold, in order.
COLUMNS = ("rig_seconds", "frame_counter", "camera_nanoseconds")


class VideoSource:
    """`core.media_assets` and `core.media_frames` for the videos under `root`.

    Parameters
    ----------
    root : str or Path
        A directory holding videos and, beside each, a CSV of the same stem giving its frame
        timing. A video with no CSV is referenced and contributes no frames.
    session_id : str
        The session these were recorded in.
    clock_id : str
        The clock the CSV's first column is in seconds of.
    tick_rate : int
        That clock's ticks per second, used to convert those seconds to ticks.
    uri_base : str, optional
        Absolute base the videos are addressed under. Without one the packet records a `file://`
        URI, which resolves only on the machine that built it.
    """

    #: R63 §2.1: what this adapter can supply, whatever a given root happens to hold.
    PRODUCES = frozenset({"core.media_assets", "core.media_frames"})

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        clock_id: str,
        tick_rate: int,
        uri_base: str | None = None,
        batch_rows: int = BATCH_ROWS,
    ) -> None:
        self.root = Path(root)
        self.session_id = session_id
        self.clock_id = clock_id
        self.tick_rate = int(tick_rate)
        self.uri_base = uri_base.rstrip("/") if uri_base else None
        self.batch_rows = batch_rows
        self.notes: list[str] = []

    def videos(self) -> list[Path]:
        """Every video under `root`, sorted so two runs number them alike."""
        return sorted(p for p in self.root.glob(f"*{SUFFIX}") if p.is_file())

    def _timing(self, video: Path) -> Path | None:
        """Return the CSV beside a video, or None where it has none."""
        beside = video.with_suffix(".csv")
        return beside if beside.is_file() else None

    def _uri(self, video: Path) -> str:
        """Where this video is addressed, absolutely (R14 §2.3)."""
        if self.uri_base:
            return f"{self.uri_base}/{video.name}"
        return video.resolve().as_uri()

    def external_media(self) -> dict[str, ExternalMedia]:
        """Each video as a resource the packet references and does not own."""
        found = {}
        for video in self.videos():
            name = video.stem
            local = self.uri_base is None
            found[f"core.{name}"] = ExternalMedia(
                media_asset_id=name,
                uri=self._uri(video),
                format=SUFFIX.lstrip("."),
                # R36 §2.4: a writer records only what it looked at. A local path can be sized;
                # a remote base says nothing about what is actually there.
                size_bytes=video.stat().st_size if local else None,
            )
        return found

    def media_assets(self) -> list[dict[str, Any]]:
        """`core.media_assets`, one row per video."""
        rows = []
        for video in self.videos():
            timing = self._timing(video)
            if timing is None:
                self.notes.append(f"{video.name}: no timing CSV beside it; referenced without frames")
            rows.append(
                {
                    "media_asset_id": video.stem,
                    "session_id": self.session_id,
                    "semantic_type": "behavior_video",
                    "name": video.stem,
                    "uri": self._uri(video),
                    "format": SUFFIX.lstrip("."),
                    "clock_id": self.clock_id if timing else None,
                    "metadata": {"pts_unit": "s", "pts_source": COLUMNS[2]} if timing else None,
                }
            )
        return rows

    def _frames(self, video: Path) -> Iterator[pa.RecordBatch]:
        """One batch at a time of a video's frame timing."""
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
        counter = table.column(COLUMNS[1]).to_numpy(zero_copy_only=False)
        camera = table.column(COLUMNS[2]).to_numpy(zero_copy_only=False)
        # A counter that advances by more than one means frames were lost before this one. The
        # first frame has nothing before it, so it is never marked.
        dropped = np.empty(counter.size, dtype=bool)
        dropped[0] = False
        np.greater(np.diff(counter), 1, out=dropped[1:])
        ticks = np.rint(seconds * self.tick_rate).astype(np.int64)

        for start in range(0, ticks.size, self.batch_rows):
            stop = min(start + self.batch_rows, ticks.size)
            yield pa.record_batch(
                {
                    "media_asset_id": pa.array([video.stem] * (stop - start)),
                    "frame_index": pa.array(np.arange(start, stop, dtype=np.int64)),
                    "t_tick": pa.array(ticks[start:stop]),
                    "clock_id": pa.array([self.clock_id] * (stop - start)),
                    "pts": pa.array(camera[start:stop] / 1e9),
                    "dropped": pa.array(dropped[start:stop]),
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
        """`05` Stage 1: how many rows of each resource this root holds."""
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


__all__ = ["BATCH_ROWS", "COLUMNS", "SUFFIX", "VideoSource"]

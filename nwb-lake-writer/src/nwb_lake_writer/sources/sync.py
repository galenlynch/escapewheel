"""Read an Open Ephys events tree into clock anchors.

The sorter gives every probe an exact tick and no way to compare two of them. This is the
other half: the shared sync pulse each stream records, paired with the HARP time
`aind-ephys-rig-qc` wrote onto it, which is what `core.clock_anchors` is.

Which streams have anchors
--------------------------

A record node's directory lists every stream it saw, but only the ones it *owns* were
aligned. The unowned entries are stubs carrying acquisition-local seconds with nothing
marking them as unaligned -- no `original_timestamps.npy` beside them, which is the archive
rig-qc writes when it replaces a timestamp array. On one real session each of two nodes owned
six streams and carried seven local-only stubs of the other's, and the owned set matched the
sorter's output exactly.

So ownership is detected, not assumed: a stream with the archive has HARP time, and one
without is skipped and reported. Taking a stub at face value would put a probe's sync pulses
17.7 million seconds from where they belong.

Which sample counter
--------------------

Three arrays in one TTL directory count time, and only one of them is the sorter's.

```text
sample_numbers.npy        raw hardware counter, absolute across the acquisition
local_timestamps.npy      recording-relative seconds, already drift-corrected
original_timestamps.npy   acquisition-relative seconds, before HARP alignment
timestamps.npy            HARP seconds, after it
```

`spikes.npy`'s `sample_index` indexes the preprocessed recording, which is built from raw
samples with no correction, so it corresponds to **`sample_numbers`** and to neither of the
seconds arrays. Measured: `sample_numbers - local_timestamps * rate` takes 895 distinct
values across one stream's pulses, because the drift correction is in the seconds and not in
the counter. Using a timestamp array here would bake that correction in twice.

What remains is the recording's first raw sample, which lives in
`continuous/<stream>/sample_numbers.npy` and is read from element 0 -- memory-mapped, so the
1.3 GB the file weighs is never touched.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..clock import HARP_TICK_RATE_HZ, Clock
from .nwb import SourceDefect

#: rig-qc archives the pre-alignment array under this name when it rewrites `timestamps.npy`.
#: Its presence is the only signal that a stream was aligned; its absence, that the stream is
#: a stub whose seconds are acquisition-local.
ARCHIVE = "original_timestamps.npy"

#: `Record Node 109` in the clipped tree's directory name.
NODE = re.compile(r"^Record Node (?P<node>\d+)$")


@dataclass(frozen=True)
class SyncStream:
    """One stream's TTL events, with the parts needed to anchor it.

    Attributes
    ----------
    path : Path
        The ``TTL`` directory.
    node, experiment, recording, stream : str
        Where it sits in the clipped tree.
    aligned : bool
        Whether rig-qc rewrote its timestamps, detected by the archive beside them.
    """

    path: Path
    node: str
    experiment: str
    recording: str
    stream: str
    aligned: bool

    @property
    def key(self) -> str:
        """The stream key a sorted folder uses for the same data."""
        return f"{self.experiment}.{self.stream}"


class SyncSource:
    """An Open Ephys ``ecephys_clipped`` tree, read as clock anchors.

    Parameters
    ----------
    root : str or Path
        The clipped tree, or a directory containing one.
    session_id : str
        The session these anchors belong to.
    experiment : str, optional
        Restrict to one experiment. Each restarts its sample counter, so anchors from two of
        them are not comparable.
    recording : str, default "recording1"
        Which recording within the experiment.
    sync_line : int, default 1
        The TTL line carrying the shared pulse. Line 5 on this rig is the HARP heartbeat
        UART, which only the NI-DAQ decodes and which is not a bare edge.
    first_samples : Mapping, optional
        Stream key -> the recording's first raw sample. Read from
        ``continuous/<stream>/sample_numbers.npy`` when absent here and present on disk.
    prefix : str, optional
        Prepended to every generated ID.

    Attributes
    ----------
    notes : list of str
        Streams skipped, and why.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        experiment: str = "experiment1",
        recording: str = "recording1",
        sync_line: int = 1,
        first_samples: Mapping[str, int] | None = None,
        prefix: str = "",
    ) -> None:
        self.root = _resolve(Path(root))
        self.session_id = session_id
        self.experiment = experiment
        self.recording = recording
        self.sync_line = sync_line
        self.first_samples = dict(first_samples or {})
        self.prefix = prefix
        self.notes: list[str] = []

    # -- discovery ----------------------------------------------------------------------

    def streams(self) -> list[SyncStream]:
        """Every TTL directory in the chosen experiment, aligned or not."""
        found = []
        for node in sorted(self.root.iterdir()):
            matched = NODE.match(node.name)
            if not matched or not node.is_dir():
                continue
            events = node / self.experiment / self.recording / "events"
            if not events.is_dir():
                continue
            for stream in sorted(events.iterdir()):
                ttl = stream / "TTL"
                if (ttl / "states.npy").is_file():
                    found.append(
                        SyncStream(
                            path=ttl,
                            node=matched.group("node"),
                            experiment=self.experiment,
                            recording=self.recording,
                            stream=stream.name,
                            aligned=(ttl / ARCHIVE).is_file(),
                        )
                    )
        if not found:
            raise SourceDefect(f"{self.root} holds no TTL events for {self.experiment}/{self.recording}")
        return found

    def aligned(self) -> list[SyncStream]:
        """Return the streams a node owns, which are the ones carrying HARP time."""
        every = self.streams()
        keep = [s for s in every if s.aligned]
        for skipped in (s for s in every if not s.aligned):
            self.notes.append(
                f"{skipped.node}/{skipped.stream}: no {ARCHIVE}, so its timestamps are "
                "acquisition-local rather than HARP; skipped"
            )
        if not keep:
            raise SourceDefect(f"{self.root}: no stream in {self.experiment} carries HARP-aligned timestamps")
        return keep

    def _first_sample(self, stream: SyncStream) -> int:
        """Find the recording's first raw sample, supplied or read from element 0 on disk."""
        if stream.key in self.first_samples:
            return self.first_samples[stream.key]
        continuous = stream.path.parent.parent.parent / "continuous" / stream.stream / "sample_numbers.npy"
        if not continuous.is_file():
            raise SourceDefect(
                f"{stream.key}: no first sample supplied and {continuous} is absent, so a raw "
                "counter cannot be made recording-relative"
            )
        return int(np.load(continuous, mmap_mode="r")[0])

    def _rises(self, stream: SyncStream) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
        """Rising edges of the sync line: raw sample numbers and their HARP seconds."""
        states = np.load(stream.path / "states.npy")
        rising = states == self.sync_line
        if not rising.any():
            raise SourceDefect(f"{stream.key}: no rising edge on line {self.sync_line}")
        return (
            np.load(stream.path / "sample_numbers.npy")[rising].astype(np.int64),
            np.load(stream.path / "timestamps.npy")[rising].astype(np.float64),
        )

    # -- tables -------------------------------------------------------------------------

    def clock(self, *, clock_id: str = "harp", name: str = "HARP rig clock") -> Clock:
        """Build the reference clock every stream's anchors point at.

        No `tick_zero_utc`: HARP free-runs from device power-on and nothing in an events tree
        records when that was. `SessionSource.epoch` derives it where a packet needs one.
        """
        return Clock(
            clock_id=f"{self.prefix}{clock_id}",
            session_id=self.session_id,
            name=name,
            tick_rate_num=HARP_TICK_RATE_HZ,
            origin="HARP device power-on; tick 0 is not the session start",
        )

    def anchors(self, *, clock_id_for: Any = None, parent_clock_id: str = "harp") -> list[dict[str, Any]]:
        """`core.clock_anchors`, one row per sync pulse per aligned stream.

        Parameters
        ----------
        clock_id_for : callable, optional
            Maps a :class:`SyncStream` to the clock id its ticks are on, or to None for a
            stream the packet declares no clock for -- the NI-DAQ records the sync pulse and
            carries no ticks of its own, so it is anchored to nothing. Defaults to the
            convention `SorterSource` writes, so the two adapters meet without either
            knowing about the other.
        parent_clock_id : str, default "harp"
            The clock `parent_tick` is on.

        Returns
        -------
        list of dict
            Sorted by `(clock_id, anchor_index)`, as R13 §3 requires.
        """
        name_of = clock_id_for or (lambda s: f"{self.prefix}{s.key}.samples")
        rows = []
        for stream in self.aligned():
            clock = name_of(stream)
            if clock is None:
                self.notes.append(f"{stream.key}: no clock declared for it; anchored to nothing")
                continue
            first = self._first_sample(stream)
            samples, seconds = self._rises(stream)
            ticks = samples - first
            parents = np.rint(seconds * HARP_TICK_RATE_HZ).astype(np.int64)
            if not ((np.diff(ticks) > 0).all() and (np.diff(parents) > 0).all()):
                raise SourceDefect(
                    f"{stream.key}: sync pulses do not increase on both clocks, so interpolation "
                    "between them is undefined (R13 §3). A counter that reset mid-recording is two "
                    "clocks, not one (R27 §6)"
                )
            rows += [
                {
                    "clock_id": clock,
                    "anchor_index": index,
                    "t_tick": int(tick),
                    "parent_tick": int(parent),
                }
                for index, (tick, parent) in enumerate(zip(ticks, parents, strict=True))
            ]
            self.notes.append(
                f"{stream.key}: {ticks.size} anchors, ticks {int(ticks[0])}..{int(ticks[-1])}, "
                f"parent {int(parents[0])}..{int(parents[-1])}"
            )
        del parent_clock_id  # named for the caller's benefit; the parent lives on core.clocks
        return rows

    def into(self, writer: Any, *, clock_id_for: Any = None) -> dict[str, int]:
        """Add the reference clock and every anchor to a `PacketWriter`."""
        rows = self.anchors(clock_id_for=clock_id_for)
        writer.add("core.clocks", [self.clock().record()])
        writer.add("core.clock_anchors", rows)
        return {"core.clocks": 1, "core.clock_anchors": len(rows)}


def _resolve(root: Path) -> Path:
    """Accept the clipped tree, an asset holding one, or a directory of record nodes."""
    for candidate in (root, root / "ecephys" / "ecephys_clipped", root / "ecephys_clipped", root / "events"):
        if candidate.is_dir() and any(NODE.match(child.name) for child in candidate.iterdir() if child.is_dir()):
            return candidate
    raise SourceDefect(f"{root} holds no Record Node directories")


__all__ = ["ARCHIVE", "SyncSource", "SyncStream"]

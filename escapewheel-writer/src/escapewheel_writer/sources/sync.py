"""Read an Open Ephys events tree into clock anchors.

- :class:`SyncSource` -- an `ecephys_clipped` tree as the reference clock and its anchors.
- :class:`SyncStream` -- one stream's TTL events, and whether its timestamps were aligned.
- :class:`RecordingStart`, :func:`read_sync_messages` -- when a record node began, and each
  stream's counter at that moment.
- :data:`ARCHIVE` -- the file whose presence marks a stream as aligned.

An anchor pairs a stream's raw `sample_numbers`, made recording-relative, with HARP time. Only a
stream carrying :data:`ARCHIVE` has HARP time, so the adapter skips and reports a stream without it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from escapewheel_reader.resource_ids import (
    CORE_CLOCK_ANCHORS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCK_PHASE_STEPS,
    CORE_CLOCKS,
)
from numpy.typing import NDArray

from ..clock import HARP_TICK_RATE_HZ, Clock
from ..errors import SourceDefect, SourceFault
from ..notes import Note, NoteCode
from .store import source_root
from .sync_checks import phase_discontinuities, suspect_terminals

#: rig-qc archives the pre-alignment array under this name when it rewrites `timestamps.npy`.
#: Its presence is the only signal that a stream was aligned; its absence, that the stream is
#: a stub whose seconds are acquisition-local.
ARCHIVE = "original_timestamps.npy"

#: `Record Node 109` in the clipped tree's directory name.
NODE = re.compile(r"^Record Node (?P<node>\d+)$")

#: What a record node writes beside its data: when it started, and where each stream's
#: counter stood at that moment.
SYNC_MESSAGES = "sync_messages.txt"

#: `Software Time (milliseconds since midnight Jan 1st 1970 UTC): 1744244712090`.
SOFTWARE_TIME = re.compile(r"Software Time \(milliseconds since midnight Jan 1st 1970 UTC\):\s*(\d+)")

#: `Start Time for Neuropix-PXI (100) - 46110 @ 30000 Hz: 103017730`.
START_TIME = re.compile(
    r"Start Time for (?P<processor>.+?) \((?P<id>\d+)\) - (?P<stream>\S+) @ \S+ Hz:\s*(?P<sample>\d+)"
)


@dataclass(frozen=True)
class RecordingStart:
    """What one record node says about when it began.

    `started` is a real UTC instant, to the millisecond, written by the node itself. Nothing
    else in an ecephys asset carries one: `settings.xml` stamps the same moment to the second
    in the machine's local zone, and the aind-data-schema documents round it further. That is
    what makes this the only non-circular way to locate a free-running counter's tick zero --
    every other route pairs a wall clock with a datum, and a datum is the thing being placed.

    `samples` is each stream's counter at that moment, which is the value a raw sample number
    must be made relative to. The node lists every stream it *saw*, not only the ones it owns.
    """

    node: str
    started: datetime
    samples: dict[str, int]


def read_sync_messages(path: Path, node: str) -> RecordingStart | None:
    """Parse a record node's `sync_messages.txt`, or None where it has none."""
    if not path.is_file():
        return None
    text = path.read_text()
    stamp = SOFTWARE_TIME.search(text)
    if not stamp:
        return None
    return RecordingStart(
        node=node,
        started=datetime.fromtimestamp(int(stamp.group(1)) / 1000, tz=UTC),
        samples={
            f"{m['processor'].replace(' ', '')}-{m['id']}.{m['stream']}": int(m["sample"])
            for m in START_TIME.finditer(text)
        },
    )


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
        """The stream key a sorted folder uses for the same data.

        Deliberately without the record node, because that is what a sorted folder name
        reduces to. Unambiguous for probes -- their names are unique across nodes -- and
        ambiguous for the NI-DAQ, of which a two-node rig has one per node. Use `uid` where
        the value is an identity rather than a correspondence.
        """
        return f"{self.experiment}.{self.stream}"

    @property
    def uid(self) -> str:
        """A stream id that stays unique when two nodes carry the same stream name."""
        return f"{self.experiment}.{self.node}.{self.stream}"


def _load(path: Path) -> NDArray[Any]:
    """Read one `.npy` file through its path, since `np.load` given a store path cannot open it."""
    with path.open("rb") as stored:
        array: NDArray[Any] = np.load(stored)
    return array


def _first_element(path: Path) -> int:
    """Read element 0 of a one-dimensional `.npy` file from its header and one item, not the whole array."""
    with path.open("rb") as stored:
        version = np.lib.format.read_magic(stored)
        header = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
        _, _, dtype = header(stored)
        return int(np.frombuffer(stored.read(dtype.itemsize), dtype=dtype)[0])


def _by_key(streams: list[SyncStream]) -> dict[str, list[SyncStream]]:
    """Group streams by the key a sorted folder would use, to spot an ambiguous one."""
    grouped: dict[str, list[SyncStream]] = {}
    for stream in streams:
        grouped.setdefault(stream.key, []).append(stream)
    return grouped


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
    clocks : sequence of Mapping, optional
        The `core.clocks` row of every clock declared before this source runs. A stream is
        anchored to the clock named `<key>.samples` and only where the packet declares one,
        since an anchor naming a clock the packet does not carry is a dangling reference: the
        NI-DAQ records the sync pulse and carries no ticks of its own. Supply none and every
        aligned stream is anchored, which is the convention `SorterSource` writes.
    first_samples : sequence of Mapping, optional
        One record per stream: `stream`, its key, and `first_sample`, the recording's first raw
        sample. Read from ``continuous/<stream>/sample_numbers.npy`` when absent here and
        present on disk.
    prefix : str, optional
        Prepended to every generated ID.
    source_cache : str, optional
        The build's source-cache location, which a store root is read through (Part 12 §10).

    Attributes
    ----------
    notes : list of str
        Streams skipped, and why.
    """

    #: Part 05 §3.4: what this adapter can supply, whatever a given root happens to hold.
    #: Static, so a recipe check reads it with nothing open -- `offers` counts rows and
    #: therefore needs the data.
    PRODUCES = frozenset(
        {
            CORE_CLOCK_ANCHORS,
            CORE_CLOCK_OBSERVATION_INTERVALS,
            CORE_CLOCK_PHASE_STEPS,
            CORE_CLOCKS,
        }
    )

    #: Part 05 §3.4: what of `PRODUCES` this adapter supplies only part of, which a source entry
    #: without `owns` contributes rather than owns.
    CONTRIBUTES = frozenset(
        {
            CORE_CLOCK_ANCHORS,
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
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id", "clocks")

    #: Part 05 §3.4: options this adapter reads and can run without, which a recipe may leave
    #: unset (Part 12 §4). `first_samples` is absent because it is a term a build fills, which
    #: a declaration may not name as an option.
    ACCEPTS: ClassVar[tuple[str, ...]] = ("experiment", "recording", "sync_line", "prefix", "source_cache")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ("sorter",)

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        experiment: str = "experiment1",
        recording: str = "recording1",
        sync_line: int = 1,
        clocks: Sequence[Mapping[str, Any]] = (),
        first_samples: Sequence[Mapping[str, Any]] = (),
        prefix: str = "",
        source_cache: str | None = None,
    ) -> None:
        self.root = _resolve(source_root(root, cache=source_cache))
        self.session_id = session_id
        self.experiment = experiment
        self.recording = recording
        self.sync_line = sync_line
        self.declared = {str(row["clock_id"]) for row in clocks}
        self.first_samples = {str(row["stream"]): int(row["first_sample"]) for row in first_samples}
        self.prefix = prefix
        self.notes: list[str] = []
        #: Where tick 0 of the reference clock falls in wall clock, memoized: every caller that
        #: asks must get the same instant, and the note about how far the nodes disagreed is
        #: said once.
        self._epoch: datetime | None = None
        #: Clock ID to what the terminal-anchor test withheld from it, for the run's parameters. Every
        #: clock the test ran on appears here, dropping nothing included; one with too few anchors to
        #: test is absent, which is what leaves its two columns null (Part 02 §12.6).
        self.withheld: dict[str, dict[str, Any]] = {}
        #: Clock ID to phase steps found in the parent's alignment, for the run's parameters.
        #: Reported, never corrected: whether a step also moved the devices timestamped on the
        #: parent is not knowable from the packet, and subtracting it would be wrong if it did.
        self.discontinuities: dict[str, list[dict[str, Any]]] = {}
        self._observed: list[tuple[int, int]] = []
        self._pulses: dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]] = {}
        self._aligned: list[SyncStream] | None = None
        self._starts: dict[str, RecordingStart | None] = {}
        self._unanchored: set[str] = set()

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
            raise SourceDefect(
                f"{self.root} holds no TTL events for {self.experiment}/{self.recording}",
                code=SourceFault.NO_TTL_EVENTS,
                where=str(self.root),
            )
        return found

    def aligned(self) -> list[SyncStream]:
        """Return the streams a node owns, which are the ones carrying HARP time.

        Memoized: a build asks for the anchors more than once, and a note repeated per ask
        reads as a repeated defect rather than as one seen twice.
        """
        if self._aligned is not None:
            return self._aligned
        every = self.streams()
        keep = [s for s in every if s.aligned]
        for skipped in (s for s in every if not s.aligned):
            self.notes.append(
                Note(
                    f"{skipped.node}/{skipped.stream}: no {ARCHIVE}, so its timestamps are "
                    "acquisition-local rather than HARP; skipped",
                    NoteCode.STREAM_NOT_ALIGNED,
                )
            )
        if not keep:
            raise SourceDefect(
                f"{self.root}: no stream in {self.experiment} carries HARP-aligned timestamps",
                code=SourceFault.NO_ALIGNED_STREAM,
                where=str(self.root),
            )

        self._aligned = self._deduplicate(keep)
        return self._aligned

    def _deduplicate(self, keep: list[SyncStream]) -> list[SyncStream]:
        """Drop a stream that is another one recorded twice.

        Two record nodes can subscribe to the same physical device. They are one clock, and
        emitting both would put two clocks on one device and leave a reader to pick.

        **Sameness is agreement on the samples both saw, not identical arrays.** Two nodes
        rarely start on the same event, so one records an edge the other began too late to see
        while every shared sample number agrees on state. Requiring equal arrays would call
        that two devices.

        The stream that saw the most is kept, so no anchor is discarded, with the lowest node
        breaking a tie. What differed is reported rather than dropped: it measures how well the
        alignment is determined, which nothing else in the packet says.

        Two streams disagreeing on a sample both recorded are a different matter and are
        refused, because then the name really is ambiguous.
        """

        def events(stream: SyncStream) -> tuple[Any, Any]:
            return _load(stream.path / "states.npy"), _load(stream.path / "sample_numbers.npy")

        out = []
        for name, group in sorted(_by_key(keep).items()):
            if len(group) == 1:
                out.append(group[0])
                continue
            ordered = sorted(group, key=lambda st: (-_load(st.path / "sample_numbers.npy").size, st.node))
            first, *rest = ordered
            base_states, base_samples = events(first)
            for other in rest:
                other_states, other_samples = events(other)
                shared = np.intersect1d(base_samples, other_samples)
                here, there = np.isin(base_samples, shared), np.isin(other_samples, shared)
                if not np.array_equal(base_states[here], other_states[there]):
                    raise SourceDefect(
                        f"{name} names two streams that disagree on samples both recorded -- "
                        f"{first.node}/{first.stream} and {other.node}/{other.stream}. The key omits "
                        "the record node, so one would silently take the other's anchors; give them "
                        "distinct names.",
                        code=SourceFault.STREAMS_DISAGREE,
                        where=name,
                    )
                drift = np.abs(
                    _load(first.path / "timestamps.npy")[here] - _load(other.path / "timestamps.npy")[there]
                ).max()
                missed = base_samples.size - shared.size, other_samples.size - shared.size
                unseen = (
                    f"; node {first.node} saw {missed[0]} the other did not and node {other.node} saw {missed[1]}"
                    if any(missed)
                    else ""
                )
                self.notes.append(
                    Note(
                        f"{name}: node {other.node} records the same {shared.size:,} events as node "
                        f"{first.node}; kept {first.node}. The two alignments disagree by up to "
                        f"{drift * 1e6:.1f} us{unseen}",
                        NoteCode.NODE_DUPLICATE,
                    )
                )
            out.append(first)
        return out

    def started(self, stream: SyncStream) -> RecordingStart | None:
        """Return what the record node behind a stream says about when it began, memoized."""
        if stream.node not in self._starts:
            recording = stream.path.parent.parent.parent
            self._starts[stream.node] = read_sync_messages(recording / SYNC_MESSAGES, stream.node)
            if self._starts[stream.node] is None:
                self.notes.append(
                    Note(
                        f"{stream.node}: no {SYNC_MESSAGES}; the node's start instant is unknown",
                        NoteCode.NO_START_INSTANT,
                    )
                )
        return self._starts[stream.node]

    def _first_sample(self, stream: SyncStream) -> int:
        """Find the recording's first raw sample.

        Three sources, in the order of how directly each says it. A supplied value wins because
        a caller that states one has a reason. Then the record node's own `sync_messages.txt`,
        which is where a supplied value comes from anyway. Only then the counter array
        beside the data, read at element 0 from its header and first item -- correct, but it requires the
        continuous data to be present, and a packet built from events and a sorting has no
        reason to hold it.
        """
        for candidate in (stream.uid, stream.key):
            if candidate in self.first_samples:
                return self.first_samples[candidate]
        if (start := self.started(stream)) is not None and stream.stream in start.samples:
            return start.samples[stream.stream]
        continuous = stream.path.parent.parent.parent / "continuous" / stream.stream / "sample_numbers.npy"
        if not continuous.is_file():
            raise SourceDefect(
                f"{stream.key}: no first sample supplied, no {SYNC_MESSAGES}, and {continuous} is "
                "absent, so a raw counter cannot be made recording-relative",
                code=SourceFault.NO_FIRST_SAMPLE,
                where=stream.key,
            )
        return _first_element(continuous)

    def _rises(self, stream: SyncStream) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
        """Rising edges of the sync line: raw sample numbers and their HARP seconds."""
        states = _load(stream.path / "states.npy")
        rising = states == self.sync_line
        if not rising.any():
            raise SourceDefect(
                f"{stream.key}: no rising edge on line {self.sync_line}",
                code=SourceFault.NO_RISING_EDGE,
                where=stream.key,
            )
        return (
            _load(stream.path / "sample_numbers.npy")[rising].astype(np.int64),
            _load(stream.path / "timestamps.npy")[rising].astype(np.float64),
        )

    # -- tables -------------------------------------------------------------------------

    def clock(self, *, clock_id: str = "harp", name: str = "HARP rig clock") -> Clock:
        """Build the reference clock every stream's anchors point at.

        `tick_zero_utc` where :meth:`epoch` could locate it, and absent otherwise: HARP
        free-runs from device power-on, so tick 0 is a power-on instant rather than a protocol
        constant, and only a record node's own stamp says when that was.
        """
        return Clock(
            clock_id=f"{self.prefix}{clock_id}",
            session_id=self.session_id,
            name=name,
            tick_rate_num=HARP_TICK_RATE_HZ,
            origin="HARP device power-on; tick 0 is not the session start",
            tick_zero_utc=self.epoch(),
        )

    def epoch(self) -> datetime | None:
        """Locate the reference clock's tick 0 in wall clock, from the record nodes' own stamps.

        Each node writes `sync_messages.txt` when it starts: a UTC instant to the millisecond,
        and the counter value of every stream at that moment. A stream's tick 0 *is* that counter
        value, so mapping tick 0 onto the reference gives a (reference tick, UTC) pair -- which
        is what `tick_zero_utc` is, and the only route to it that pairs a wall clock with an
        instrument event rather than with a datum. Every other route pairs it with the first
        spike, and the first spike is the thing being placed.

        A node's streams do not all reach their first sample at the same moment: the node opens
        the file and writes each stream's first available sample, so a stream is at or after the
        stamp, never before. The earliest is therefore the closest, and the spread over the rest
        bounds the error. Two nodes give two independent estimates; their disagreement is
        reported.

        Derived here rather than by a build because the stamps are this tree's, and at the
        default bound because tick 0 sits **inside** a median anchor interval of the terminal
        anchor, so no wider allowance changes the answer.

        Returns
        -------
        datetime or None
            The instant, or None where no stream carries both a stamp and anchors.
        """
        from escapewheel_reader.clocks import align

        if self._epoch is None:
            by_clock: dict[str, list[dict[str, Any]]] = {}
            for row in self.anchors():
                by_clock.setdefault(str(row["clock_id"]), []).append(row)
            per_node: dict[str, list[int]] = {}
            stamps: dict[str, datetime] = {}
            for stream in self.aligned():
                clock, started = self.clock_id_for(stream), self.started(stream)
                if clock is None or started is None or clock not in by_clock:
                    continue
                rows = by_clock[clock]
                at = np.array([r["t_tick"] for r in rows], dtype=np.int64)
                parent = np.array([r["parent_tick"] for r in rows], dtype=np.int64)
                converted, defined = align(np.array([0], dtype=np.int64), at, parent)
                if defined[0]:
                    per_node.setdefault(stream.node, []).append(int(converted[0]))
                    stamps[stream.node] = started.started
            estimates = [
                stamps[node] - timedelta(seconds=min(ticks) / HARP_TICK_RATE_HZ) for node, ticks in per_node.items()
            ]
            if not estimates:
                return None
            earliest, latest = min(estimates), max(estimates)
            if len(estimates) > 1:
                self.notes.append(
                    Note(
                        f"tick_zero_utc: {len(estimates)} record nodes agree to "
                        f"{(latest - earliest).total_seconds() * 1e3:.0f} ms",
                        NoteCode.TICK_ZERO_SPREAD,
                    )
                )
            # The mean of the nodes' estimates; each is independently derived and neither is better.
            self._epoch = earliest + (latest - earliest) / 2
        return self._epoch

    def clock_id_for(self, stream: SyncStream) -> str | None:
        """Return the clock a stream's ticks are on, or None where the packet declares none.

        The name follows the convention `SorterSource` writes, so the two adapters meet without
        either knowing about the other. A stream is anchored only where the supplied clocks
        carry that name, because an anchor naming a clock the packet does not hold is a
        dangling reference: the rig aligns more than it sorts, and the NI-DAQ records the sync
        pulse while carrying no ticks of its own. Supplied none, every aligned stream is
        anchored, which is what a caller reading one tree on its own wants.
        """
        name = f"{self.prefix}{stream.key}.samples"
        return name if not self.declared or name in self.declared else None

    def anchors(self, *, parent_clock_id: str = "harp") -> list[dict[str, Any]]:
        """`core.clock_anchors`, one row per sync pulse per aligned stream.

        Parameters
        ----------
        parent_clock_id : str, default "harp"
            The clock `parent_tick` is on.

        Returns
        -------
        list of dict
            Sorted by `(clock_id, anchor_index)`, the order `core.clock_anchors` declares.
        """
        rows = []
        for stream in self.aligned():
            clock = self.clock_id_for(stream)
            if clock is None:
                if stream.key not in self._unanchored:
                    self._unanchored.add(stream.key)
                    self.notes.append(
                        Note(f"{stream.key}: no clock declared for it; anchored to nothing", NoteCode.NO_CLOCK_DECLARED)
                    )
                continue
            ticks, parents = self.pulses(stream, clock)
            rows += [
                {
                    "clock_id": clock,
                    "anchor_index": index,
                    "t_tick": int(tick),
                    "parent_tick": int(parent),
                }
                for index, (tick, parent) in enumerate(zip(ticks, parents, strict=True))
            ]
        del parent_clock_id  # named for the caller's benefit; the parent lives on core.clocks
        return rows

    def pulses(self, stream: SyncStream, clock: str) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """One stream's usable sync pulses as `(ticks, parent ticks)`, memoized.

        Memoized because reading a stream's pulses is where the terminal-anchor test runs and where the
        observed span is recorded, and both must happen exactly once however many times a
        caller asks for the anchors. Keyed on the clock name, since that is what the caller
        varies -- a stream anchored to nothing never reaches here.
        """
        if clock in self._pulses:
            return self._pulses[clock]
        first = self._first_sample(stream)
        samples, seconds = self._rises(stream)
        ticks = samples - first
        parents = np.rint(seconds * HARP_TICK_RATE_HZ).astype(np.int64)
        if not ((np.diff(ticks) > 0).all() and (np.diff(parents) > 0).all()):
            raise SourceDefect(
                f"{stream.key}: sync pulses do not increase on both clocks, so interpolation "
                "between them is undefined. A counter that reset mid-recording is two "
                "clocks, not one (Part 01 §3.9)",
                code=SourceFault.PULSES_UNORDERED,
                where=stream.key,
            )
        # The window HARP was observed over is the whole pulse train, recorded before the test
        # below removes anchors: withholding one is a statement about how well its parent tick
        # is placed, not about whether the rig was running then.
        self._observed.append((int(parents[0]), int(parents[-1])))
        tested = suspect_terminals(ticks, parents)
        if tested is None:
            self.notes.append(
                Note(
                    f"{stream.key}: {ticks.size} anchors are too few for the terminal-anchor test, "
                    "so neither terminal was tested",
                    NoteCode.ANCHOR_TEST_SKIPPED,
                )
            )
        drop_first, drop_last, residuals = tested or (False, False, {})
        withheld = ["first"] * drop_first + ["last"] * drop_last
        if tested is not None:
            # Recorded for every clock the test ran on, including the ones that dropped nothing
            # (Part 02 §12.6): a count of zero is the evidence that the bound was sufficient, and
            # a packet that says nothing is indistinguishable from one that never looked.
            self.withheld[clock] = {"anchors": withheld, "n_withheld": len(withheld), **residuals}
        if drop_first or drop_last:
            kept = slice(1 if drop_first else None, -1 if drop_last else None)
            ticks, parents = ticks[kept], parents[kept]
            self.notes.append(
                Note(
                    f"{stream.key}: withheld the {' and '.join(withheld)} anchor; residual "
                    f"{residuals['first']:.0f}/{residuals['last']:.0f} parent ticks against a "
                    f"{residuals['threshold']:.0f}-tick interior threshold",
                    NoteCode.ANCHOR_WITHHELD,
                )
            )
        self.notes.append(
            Note(
                f"{stream.key}: {ticks.size} anchors, ticks {int(ticks[0])}..{int(ticks[-1])}, "
                f"parent {int(parents[0])}..{int(parents[-1])}",
                NoteCode.ANCHORS_WRITTEN,
            )
        )
        if stepped := phase_discontinuities(ticks, parents, HARP_TICK_RATE_HZ):
            self.discontinuities[clock] = stepped
            self.notes.append(
                Note(
                    f"{stream.key}: {len(stepped)} phase discontinuit"
                    f"{'y' if len(stepped) == 1 else 'ies'} in the reference alignment, "
                    + ", ".join(f"{e['seconds'] * 1e3:+.2f} ms at tick {e['t_tick']}" for e in stepped),
                    NoteCode.PHASE_DISCONTINUITY,
                )
            )
        self._pulses[clock] = (ticks, parents)
        return ticks, parents

    def observation_intervals(self) -> list[dict[str, Any]]:
        """`core.clock_observation_intervals` for the reference clock (Part 02 §12.5).

        The window is the span of the sync train, which is HARP-native and so needs no
        conversion: every pulse carries a HARP time, and their extent is the interval over
        which this session has HARP time at all. Outside it the reference clock is not
        unobserved so much as unwitnessed, and either way nothing in the packet is on it.

        :meth:`anchors` must have run, since the span is what it saw.
        """
        if not self._observed:
            return []
        return [
            {
                "session_id": self.session_id,
                "clock_id": self.clock().clock_id,
                "start_tick": min(start for start, _ in self._observed),
                "stop_tick": max(stop for _, stop in self._observed),
            }
        ]

    def phase_steps(self) -> list[dict[str, Any]]:
        """`core.clock_phase_steps`, one row per step in a clock's alignment (Part 02 §12.6).

        A step is reported and never corrected. `anchors` is what detects them, and is memoized
        on the pulses, so asking for it here costs nothing and removes the order dependence
        between this and the anchor rows.
        """
        self.anchors()
        return [
            {
                "clock_id": clock,
                "t_tick": event["t_tick"],
                "parent_tick": event["parent_tick"],
                "shift_seconds": event["seconds"],
                "anchor_interval_span": event["anchor_intervals"],
            }
            for clock, events in sorted(self.discontinuities.items())
            for event in events
        ]

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Every table this adapter builds as records, keyed by resource ID."""
        built = {
            CORE_CLOCKS: [self.clock().record()],
            CORE_CLOCK_ANCHORS: self.anchors(),
            CORE_CLOCK_OBSERVATION_INTERVALS: self.observation_intervals(),
            CORE_CLOCK_PHASE_STEPS: self.phase_steps(),
        }
        return {resource: rows for resource, rows in built.items() if rows}

    def offers(self) -> dict[str, int]:
        """Which resources this source supplies from its root, and how many rows (Part 05 §4.1)."""
        return {resource: len(rows) for resource, rows in self.records().items()}


def _resolve(root: Path) -> Path:
    """Accept the clipped tree, an asset holding one, or a directory of record nodes."""
    for candidate in (root, root / "ecephys" / "ecephys_clipped", root / "ecephys_clipped", root / "events"):
        if candidate.is_dir() and any(NODE.match(child.name) for child in candidate.iterdir() if child.is_dir()):
            return candidate
    raise SourceDefect(f"{root} holds no Record Node directories", code=SourceFault.NO_RECORD_NODE, where=str(root))


__all__ = [
    "ARCHIVE",
    "RecordingStart",
    "SyncSource",
    "SyncStream",
    "read_sync_messages",
]

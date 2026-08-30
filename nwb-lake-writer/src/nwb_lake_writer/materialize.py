"""Build analysis resources from a packet's core ones.

`06` splits transformations two ways: a view where the work is cheap, a materialized table
where it is expensive or frequently reused. Clock alignment alone sits on the cheap side --
29 M spikes a second, so a query touching a few units pays single-digit milliseconds. What
justifies materializing is not the arithmetic but the **layout**: a common clock is what makes
ordering by time meaningful at all, and core, whose ticks are on twelve different probe clocks,
cannot express such an order (R30 §6).

What the analysis layer costs
-----------------------------

An analysis resource MUST declare lineage to core (`06`), which is the manifest's
`derived_from`, and it is disposable: nothing here is canonical, and a packet without it is
complete.

What it deliberately loses
--------------------------

The exact probe tick. `core.spike_events` keeps that and this does not, which is the whole
point of the layering -- the derived value is convenient and the measured one is the record.
A spike this cannot place is dropped rather than guessed, so the analysis table is not
row-aligned with core and does not pretend to be.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from numpy.typing import NDArray

from .align import BOUND, align

#: Rows per batch, and therefore per row group and per unit of writer memory. Measured: 128 K
#: costs 0.6% in bytes over 1 M once `t_tick` is not dictionary-encoded, and is what makes the
#: unit filter prune within a bucket (R30 §6).
#: The resource these buckets become, so the spill can take the encoding its columns want.
RESOURCE = "analysis.spike_events"

BATCH_ROWS = 1 << 17

#: Bucket width in seconds of the reference clock. The dial trades scattered-unit access
#: against time-window access, through how many row groups fit in one bucket; 300 s was the
#: best of 10/60/300 on a 5,364 s session with 7,291 units. Not normative (R30 §3.3).
BUCKET_SECONDS = 300


class NotAligned(ValueError):
    """A clock the spikes are on has no anchors, so its ticks reach no reference."""


def _anchors(packet: Any) -> dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Read `core.clock_anchors` into arrays per clock."""
    table = packet.table("core.clock_anchors")
    clock = table.column("clock_id").to_pylist()
    tick = np.asarray(table.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    parent = np.asarray(table.column("parent_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    out: dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]] = {}
    for name in dict.fromkeys(clock):
        where = np.array([i for i, c in enumerate(clock) if c == name])
        order = np.argsort(tick[where], kind="stable")
        out[name] = (tick[where][order], parent[where][order])
    return out


def _reference(packet: Any) -> str:
    """Return the clock a session reports its times on (R27 §2)."""
    sessions = packet.table("core.sessions")
    declared = (
        sessions.column("reference_clock_id").to_pylist() if "reference_clock_id" in sessions.column_names else []
    )
    if named := [d for d in declared if d]:
        return str(named[0])
    raise NotAligned("the session declares no reference_clock_id (R27 §2), so there is nothing to map onto")


def _tick_rate(packet: Any, clock_id: str) -> int:
    """Return the reference clock's rate, turning a bucket in seconds into one in ticks.

    Prefers the exact rational `tick_rate_num/den` over the float `tick_rate_hz`, since a clock
    may declare either and the rational is the one that is not already rounded.
    """
    clocks = packet.table("core.clocks")
    column = {n: clocks.column(n).to_pylist() for n in clocks.column_names}
    for i, name in enumerate(column["clock_id"]):
        if name != clock_id:
            continue
        num, den = column.get("tick_rate_num", [])[i : i + 1], column.get("tick_rate_den", [])[i : i + 1]
        if num and den and num[0] and den[0]:
            return round(float(num[0]) / float(den[0]))
        if (rate := column.get("tick_rate_hz", [])[i : i + 1]) and rate[0]:
            return round(float(rate[0]))
    raise NotAligned(f"{clock_id} declares no tick rate, so a bucket has no width in ticks")


def _mapped(batch: pa.RecordBatch, reference: str, anchors: Any, bound: float) -> tuple[Any, Any]:
    """Map one batch's ticks onto the reference clock, returning the ticks and what to keep."""
    ticks = np.asarray(batch.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
    clocks = batch.column("clock_id")
    parent = np.empty(ticks.size, dtype=np.int64)
    keep = np.zeros(ticks.size, dtype=bool)
    # A batch spans at most two streams, since the table is sorted by sorting_run_id and each
    # stream is one run, so this loop runs once or twice. Its *body* must still stay in Arrow:
    # asking for the column as Python strings to group it costs a string object per spike, and
    # the comparison that follows is over a handful of distinct values either way.
    for name in [n for n in pc.unique(clocks).to_pylist() if n is not None]:
        where = np.flatnonzero(pc.equal(clocks, pa.scalar(name, pa.string())).to_numpy(zero_copy_only=False))
        if name == reference:
            parent[where], keep[where] = ticks[where], True
            continue
        if name not in anchors:
            raise NotAligned(f"{name} carries no anchors, so its ticks reach no reference clock")
        parent[where], keep[where] = align(ticks[where], *anchors[name], bound=bound)
    return parent, keep


def _bytes(budget: int | str) -> int:
    """Parse a byte budget written as a number or as `"10GB"`, `"512MB"`, `"2G"`."""
    if isinstance(budget, int):
        return budget
    text = budget.strip().upper().removesuffix("B")
    scale = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}
    if text and text[-1] in scale:
        return int(float(text[:-1]) * scale[text[-1]])
    return int(float(text))


def _packed(batch: pa.RecordBatch) -> pa.RecordBatch:
    """Hold a batch with its identifiers as dictionary codes rather than strings.

    36 bytes a row against 195, which is what decides whether a session's partition can be
    held at all: 10.4 GB against 56 GB over 287 M spikes. The codes are what Parquet would
    store anyway, so nothing is lost and the decode is deferred to the one place it was always
    going to happen.
    """
    columns = [
        column.dictionary_encode() if pa.types.is_string(field.type) else column
        for column, field in zip(batch.columns, batch.schema, strict=True)
    ]
    return pa.record_batch(columns, names=batch.schema.names)


def _unpacked(batch: pa.RecordBatch, out: pa.Schema) -> pa.RecordBatch:
    """Return a held batch to the schema the table declares."""
    columns = [column.cast(field.type) for column, field in zip(batch.columns, out, strict=True)]
    return pa.record_batch(columns, schema=out)


class _Buckets:
    """Per-bucket Parquet spill files, written in the order rows arrive.

    Parquet, although a spill is written once, read once and deleted, and its encoding
    therefore has no reader to benefit. The encoding is not for a reader here, it is for the
    disk: four of these seven columns are string identifiers, and dictionary-encoding them puts
    a million rows in 2.7 MB where Arrow IPC needs 195 MB. Writing a batch costs 0.100 s
    against IPC's 0.053 s, and over a full session that trade is worth taking on anything but
    the fastest storage -- uncompressed IPC spills 56 GB and takes 321.8 s where this takes
    76.6 s.

    Bucketing by time and sorting by unit inside each bucket needs no global sort, because
    `core.spike_events` is already ordered by `(sorting_run_id, curation_id, unit_id, t_tick)`
    (R10 §2, `03`). Visiting it in that order and appending each row to its bucket's file
    leaves every file in exactly the intra-bucket order R30 §3.2 declares. What remains is to
    concatenate the files in bucket order, which is a second pass and no comparisons.
    """

    def __init__(self, root: Path, out: pa.Schema, budget: int = 0) -> None:
        from .writer import _delta_columns

        self._root = root
        self._out = out
        # The spill gets the encoding the finished table gets. Its own bytes have no reader,
        # but a tick column left to pyarrow's default overflows the dictionary page and falls
        # back to PLAIN mid-column, paying for both: 1,195 MB and 77.4 s against 500 MB and
        # 60.9 s, at no cost in memory.
        delta = _delta_columns(RESOURCE, out)
        self._options: dict[str, Any] = {"compression": "zstd"}
        if delta:
            self._options["use_dictionary"] = [n for n in out.names if n not in delta]
            self._options["column_encoding"] = dict.fromkeys(delta, "DELTA_BINARY_PACKED")
        self._budget = budget
        # Packing is for holding, not for writing. A batch on its way to disk is about to be
        # dictionary-encoded by Parquet anyway, so encoding it here and decoding it back costs
        # 82 s over a session and buys nothing.
        self._pack = budget > 0
        self._bytes = 0
        self._writers: dict[int, pq.ParquetWriter] = {}
        self._held: dict[int, list[pa.RecordBatch]] = {}
        self._rows: dict[int, int] = {}

    def add(self, bucket: int, batch: pa.RecordBatch) -> None:
        packed = _packed(batch) if self._pack else batch
        self._held.setdefault(bucket, []).append(packed)
        self._rows[bucket] = self._rows.get(bucket, 0) + packed.num_rows
        self._bytes += packed.nbytes
        while self._bytes > self._budget:
            # Only buckets holding a whole batch are worth writing. The budget is a target
            # rather than a wall: with nothing full enough to spill, holding a little more
            # beats a stream of tiny row groups, and the excess is bounded by one batch per
            # bucket. Biggest first, so one write buys the most room.
            ready = [b for b in self._held if self._rows[b] >= BATCH_ROWS]
            if not ready:
                break
            self._flush(max(ready, key=lambda b: self._rows[b]))

    def _flush(self, bucket: int) -> None:
        held = self._held.pop(bucket, [])
        self._rows[bucket] = 0
        self._bytes -= sum(b.nbytes for b in held)
        if not held:
            return
        if bucket not in self._writers:
            path = self._root / f"bucket-{bucket:012d}.parquet"
            self._writers[bucket] = pq.ParquetWriter(path, self._out, **self._options)
        rows = [_unpacked(b, self._out) for b in held] if self._pack else held
        self._writers[bucket].write_table(pa.Table.from_batches(rows, schema=self._out))

    def drain(self) -> Iterator[pa.RecordBatch]:
        """Yield every bucket's rows in bucket order, in batches of at most `BATCH_ROWS`.

        A batch never spans two buckets, so each becomes a row group lying inside one bucket
        (R30 §3.2). Row groups cut at a fixed row count would straddle boundaries and span
        twice the intended time range.
        """
        # A bucket that never exceeded the budget has no writer and never reached disk; it is
        # yielded from memory. One that did keeps its remainder in `_held`, so it is flushed
        # first and read back whole.
        for bucket in sorted(self._writers):
            self._flush(bucket)
            self._writers[bucket].close()
        for bucket in sorted(set(self._writers) | set(self._held)):
            if bucket in self._writers:
                path = self._root / f"bucket-{bucket:012d}.parquet"
                yield from pq.ParquetFile(path).iter_batches(batch_size=BATCH_ROWS)
            else:
                for batch in self._held[bucket]:
                    yield _unpacked(batch, self._out) if self._pack else batch


def spike_events(
    packet: Any,
    *,
    reference: str | None = None,
    bound: float = BOUND,
    bucket_seconds: int = BUCKET_SECONDS,
    scratch: Path | None = None,
    memory_budget: int | str = 0,
) -> Iterator[pa.RecordBatch]:
    """`analysis.spike_events` -- core spikes on the reference clock, bucketed by time.

    A spike whose tick falls further than the bound from any anchor is **dropped**: R27 §5.3
    leaves it undefined, and a derived table is the wrong place to record that a value is
    missing.

    Parameters
    ----------
    packet : Packet
        An open packet carrying `core.spike_events`, `core.clock_anchors`, `core.clocks` and
        `core.sessions`.
    reference : str, optional
        The clock to map onto. Defaults to `core.sessions.reference_clock_id` (R27 §2).
    bound : float
        Passed to :func:`~nwb_lake_writer.align.align`.
    bucket_seconds : int
        Bucket width, in seconds of the reference clock. A transform parameter `06` requires
        the packet to declare, not something a reader can recover from the data.
    scratch : Path, optional
        Where the per-bucket spill files go. Defaults to a temporary directory beside the
        packet, so a large session does not land on a tmpfs `/tmp`.
    memory_budget : int or str, optional
        Bytes the partition may occupy before it spills, as a number or a string such as
        `"10GB"`. Bucketing is a transpose -- every unit spans every bucket, so no streaming
        pass can emit in order -- and the partition either fits in memory or goes to disk.
        Held with identifiers as dictionary codes it is 36 bytes a row, so a session of 287 M
        spikes wants 10.4 GB; the same rows spill to 0.5 GB of Parquet instead. Zero, the
        default, holds no more than one batch per bucket, because whether ten gigabytes is
        reasonable or ruinous is a property of the machine packaging the data rather than of
        the data. It buys about 8% on a session of this size, so spilling is the default for
        being the cheaper resource, not the faster path.

    Yields
    ------
    pyarrow.RecordBatch
        In R30 §3.2's order, at most `BATCH_ROWS` rows, never spanning two buckets.

    Raises
    ------
    NotAligned
        If the session declares no reference clock, if a clock the spikes are on carries no
        anchors, or if the reference clock declares no tick rate.
    """
    reference = reference or _reference(packet)
    width = bucket_seconds * _tick_rate(packet, reference)
    anchors = _anchors(packet)
    handle = packet.table_resource("core.spike_events")
    columns = ["session_id", "unit_id", "sorting_run_id", "curation_id", "t_tick", "clock_id"]
    out = pa.schema(
        [pa.field(n, pa.string()) for n in columns[:4]]
        + [pa.field("t_tick", pa.int64()), pa.field("clock_id", pa.string()), pa.field("time_bucket_tick", pa.int64())]
    )

    root = Path(scratch) if scratch else Path(tempfile.mkdtemp(prefix=".materialize-", dir=packet.root.parent))
    buckets = _Buckets(root, out, _bytes(memory_budget))
    try:
        for batch in pq.ParquetFile(handle.path).iter_batches(batch_size=BATCH_ROWS, columns=columns):
            parent, keep = _mapped(batch, reference, anchors, bound)
            if not keep.any():
                continue
            taken = np.flatnonzero(keep)
            ticks = parent[taken]
            # Floor division, so a negative tick lands in the bucket that starts before it
            # rather than the one that starts after.
            starts = (ticks // width) * width
            mapped = pa.record_batch(
                {
                    "session_id": batch.column("session_id").take(taken),
                    "unit_id": batch.column("unit_id").take(taken),
                    "sorting_run_id": batch.column("sorting_run_id").take(taken),
                    "curation_id": batch.column("curation_id").take(taken),
                    "t_tick": pa.array(ticks, type=pa.int64()),
                    "clock_id": pa.repeat(pa.scalar(reference, pa.string()), taken.size),
                    "time_bucket_tick": pa.array(starts, type=pa.int64()),
                },
                schema=out,
            )
            # A batch of core rows is one unit's spikes over the whole session, so it spans
            # many buckets; split it rather than assuming it belongs to one.
            edges = np.flatnonzero(np.diff(starts)) + 1
            for lo, hi in zip([0, *edges], [*edges, starts.size], strict=True):
                buckets.add(int(starts[lo]), mapped.slice(int(lo), int(hi - lo)))
        yield from buckets.drain()
    finally:
        if scratch is None:
            shutil.rmtree(root, ignore_errors=True)


#: `processing_run_id` for this materialization. Stable rather than random, so re-running it
#: produces the same identifier and an amendment that replaces the table replaces its run
#: rather than accumulating one per attempt.
RUN_ID = "materialize.analysis.spike_events"


def into(
    packet: Any,
    writer: Any,
    *,
    reference: str | None = None,
    bound: float = BOUND,
    bucket_seconds: int = BUCKET_SECONDS,
    run_id: str = RUN_ID,
    memory_budget: int | str = 0,
    scratch: Path | None = None,
) -> str:
    """Add `analysis.spike_events` to a writer, with the provenance `06` and R31 require.

    Three things are recorded, across the two places R9 left provenance in: the source
    resources as the manifest's `derived_from`, the run as a `core.processing_runs` row, and
    the link between them as the resource's `processing_run_id`.

    `bucket_seconds` goes in `parameters` because it cannot be recovered from the data -- a
    table whose buckets all happen to be non-empty looks the same at 300 s as at 299 s
    (R31 §3). `memory_budget` and `scratch` do not: they change how the rows are produced, not
    which rows they are, and recording them would make two identical packets claim different
    provenance.

    Returns
    -------
    str
        The resource ID added.
    """
    from . import __version__

    resource = "analysis.spike_events"
    started = datetime.now(tz=timezone.utc)
    writer.add_batches(
        resource,
        spike_events(
            packet,
            reference=reference,
            bound=bound,
            bucket_seconds=bucket_seconds,
            memory_budget=memory_budget,
            scratch=scratch,
        ),
    )
    writer.derives(resource, ["core.spike_events", "core.clock_anchors", "core.clocks"])
    writer.add(
        "core.processing_runs",
        [
            {
                "processing_run_id": run_id,
                "activity_type": "materialization",
                "software_name": "nwb_lake_writer",
                "software_version": __version__,
                "parameters": {
                    "bucket_seconds": bucket_seconds,
                    "bound": bound,
                    "reference_clock_id": reference,
                },
                "started_at": started,
                "ended_at": datetime.now(tz=timezone.utc),
                "status": "succeeded",
            }
        ],
    )
    writer.produced_by(resource, run_id)
    return resource


__all__ = ["BATCH_ROWS", "BUCKET_SECONDS", "RUN_ID", "NotAligned", "into", "spike_events"]

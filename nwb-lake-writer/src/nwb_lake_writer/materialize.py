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
import pyarrow.parquet as pq
from numpy.typing import NDArray

from .align import BOUND, align

#: Rows per batch, and therefore per row group and per unit of writer memory. Measured: 128 K
#: costs 0.6% in bytes over 1 M once `t_tick` is not dictionary-encoded, and is what makes the
#: unit filter prune within a bucket (R30 §6).
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
    clocks = batch.column("clock_id").to_pylist()
    parent = np.empty(ticks.size, dtype=np.int64)
    keep = np.zeros(ticks.size, dtype=bool)
    # A batch spans at most two streams, since the table is sorted by sorting_run_id and each
    # stream is one run -- so this loop runs once or twice, not per row.
    for name in dict.fromkeys(clocks):
        where = np.array([i for i, c in enumerate(clocks) if c == name])
        if name == reference:
            parent[where], keep[where] = ticks[where], True
            continue
        if name not in anchors:
            raise NotAligned(f"{name} carries no anchors, so its ticks reach no reference clock")
        parent[where], keep[where] = align(ticks[where], *anchors[name], bound=bound)
    return parent, keep


class _Buckets:
    """Per-bucket Parquet spill files, written in the order rows arrive.

    Bucketing by time and sorting by unit inside each bucket needs no global sort, because
    `core.spike_events` is already ordered by `(sorting_run_id, curation_id, unit_id, t_tick)`
    (R10 §2, `03`). Visiting it in that order and appending each row to its bucket's file
    leaves every file in exactly the intra-bucket order R30 §3.2 declares. What remains is to
    concatenate the files in bucket order, which is a second pass and no comparisons.
    """

    def __init__(self, root: Path, out: pa.Schema) -> None:
        self._root = root
        self._out = out
        self._writers: dict[int, pq.ParquetWriter] = {}
        self._held: dict[int, list[pa.RecordBatch]] = {}
        self._rows: dict[int, int] = {}

    def add(self, bucket: int, batch: pa.RecordBatch) -> None:
        self._held.setdefault(bucket, []).append(batch)
        self._rows[bucket] = self._rows.get(bucket, 0) + batch.num_rows
        if self._rows[bucket] >= BATCH_ROWS:
            self._flush(bucket)

    def _flush(self, bucket: int) -> None:
        held = self._held.pop(bucket, [])
        self._rows[bucket] = 0
        if not held:
            return
        if bucket not in self._writers:
            path = self._root / f"bucket-{bucket:012d}.parquet"
            self._writers[bucket] = pq.ParquetWriter(path, self._out, compression="zstd")
        self._writers[bucket].write_table(pa.Table.from_batches(held, schema=self._out))

    def drain(self) -> Iterator[pa.RecordBatch]:
        """Yield every bucket's rows in bucket order, in batches of at most `BATCH_ROWS`.

        A batch never spans two buckets, so each becomes a row group lying inside one bucket
        (R30 §3.2). Row groups cut at a fixed row count would straddle boundaries and span
        twice the intended time range.
        """
        # Over the union, not over `_writers`: a bucket holding fewer than one batch has no
        # writer yet, and iterating the writers alone would drop it without a word.
        for bucket in sorted(set(self._writers) | set(self._held)):
            self._flush(bucket)
            self._writers[bucket].close()
        for bucket in sorted(self._writers):
            path = self._root / f"bucket-{bucket:012d}.parquet"
            yield from pq.ParquetFile(path).iter_batches(batch_size=BATCH_ROWS)


def spike_events(
    packet: Any,
    *,
    reference: str | None = None,
    bound: float = BOUND,
    bucket_seconds: int = BUCKET_SECONDS,
    scratch: Path | None = None,
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
    buckets = _Buckets(root, out)
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
) -> str:
    """Add `analysis.spike_events` to a writer, with the provenance `06` and R31 require.

    Three things are recorded, across the two places R9 left provenance in: the source
    resources as the manifest's `derived_from`, the run as a `core.processing_runs` row, and
    the link between them as the resource's `processing_run_id`.

    `bucket_seconds` goes in `parameters` because it cannot be recovered from the data -- a
    table whose buckets all happen to be non-empty looks the same at 300 s as at 299 s
    (R31 §3).

    Returns
    -------
    str
        The resource ID added.
    """
    from . import __version__

    resource = "analysis.spike_events"
    started = datetime.now(tz=timezone.utc)
    writer.add_batches(resource, spike_events(packet, reference=reference, bound=bound, bucket_seconds=bucket_seconds))
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

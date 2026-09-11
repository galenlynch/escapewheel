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
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.clocks import NotAligned, anchors, declared_bound, mapped, reference_clock
from numpy.typing import NDArray

from .arrow import schema as arrow_schema

#: Rows per batch, and therefore per row group and per unit of writer memory. Measured: 128 K
#: costs 0.6% in bytes over 1 M once `t_tick` is not dictionary-encoded, and is what makes the
#: unit filter prune within a bucket (R30 §6).
#: The resource these buckets become, so the spill can take the encoding its columns want.
RESOURCE = "analysis.spike_events"


class Collided(NotAligned):
    """Two spikes of one unit convert to the same reference tick, so the table cannot be built.

    `06` §4. This table is keyed on the converted tick, and a conversion preserves distinctness
    only where it expands -- a reference clock slower than a probe's collapses spikes that were
    distinct on the probe. Refusing costs nothing usable: a histogram over collapsed spikes
    undercounts them, so a clock that coarse makes this table the wrong instrument rather than a
    broken one, and `06` §2 makes not building it an ordinary outcome.
    """


def _refuse_on_collision(units: Any, ticks: Any, carry: tuple[int, int] | None) -> None:
    """Raise where two consecutive spikes of one unit share a converted tick (`06` §4).

    Core sorts by `(session_id, unit_id, t_tick)` and the mapping is monotone, so a collision is
    always between neighbours; `carry` is the previous batch's last row, since a pair split
    across a boundary would otherwise pass unseen.
    """
    if units.size > 1:
        hit = np.flatnonzero((units[1:] == units[:-1]) & (np.diff(ticks) == 0))
        if hit.size:
            at = int(hit[0]) + 1
            raise Collided(f"unit {int(units[at])} has two spikes on reference tick {int(ticks[at])}")
    if carry is not None and units.size and units[0] == carry[0] and ticks[0] == carry[1]:
        raise Collided(f"unit {int(units[0])} has two spikes on reference tick {int(ticks[0])}")

BATCH_ROWS = 1 << 17

#: Bucket width in seconds of the reference clock. The dial trades scattered-unit access
#: against time-window access, through how many row groups fit in one bucket; 300 s was the
#: best of 10/60/300 on a 5,364 s session with 7,291 units. Not normative (R30 §3.3).
BUCKET_SECONDS = 300

#: How a string column is held in flight. A dictionary is an encoding, not a type -- Parquet writes
#: BYTE_ARRAY/String either way -- so this changes what the pipeline carries, not what it emits.


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


def _clock_id(packet: Any, reference: Any) -> Any:
    """Resolve a clock a recipe named to the identifier this packet assigned it (`05` §8).

    A recipe is written before any identifier exists, so it names a clock by name -- as its
    own `[[clock]]` blocks and every `parent_clock_id` do. `reference_clock` returns an id
    already, so only a recipe's spelling reaches here needing resolution, and an id passed
    straight through keeps a caller that has one from having to look up its name to pass it.
    """
    if not isinstance(reference, str):
        return reference
    clocks = packet.table("core.clocks")
    identifiers = clocks.column("clock_id").to_pylist()
    if reference in identifiers:
        # A packet whose identifiers are themselves names -- anything built before R53.
        return reference
    names = clocks.column("clock_name").to_pylist() if "clock_name" in clocks.column_names else []
    for identifier, name in zip(identifiers, names, strict=True):
        if name == reference:
            return identifier
    raise NotAligned(f"no clock is named {reference!r}, so there is nothing to map onto")


def _unit_clocks(packet: Any) -> NDArray[np.int64]:
    """Each unit's `clock_id`, indexed by `unit_id` (R96 §3.3).

    A spike's tick is on its unit's clock, and the hop is one column of a 6,781-row table against
    287 M rows that no longer carry a copy of it (R96 §3.4). An array rather than a mapping because
    R81 §2.1 numbers `unit_id` densely from zero, so the lookup is an index.
    """
    units = packet.table("core.units")
    identifiers = units.column("unit_id").to_numpy(zero_copy_only=False)
    clocks = units.column("clock_id").to_numpy(zero_copy_only=False)
    if identifiers.size == 0:
        return np.zeros(0, dtype=np.int64)
    found = np.full(int(identifiers.max()) + 1, -1, dtype=np.int64)
    found[identifiers] = clocks
    return found


def _bytes(budget: int | str) -> int:
    """Parse a byte budget written as a number or as `"10GB"`, `"512MB"`, `"2G"`."""
    if isinstance(budget, int):
        return budget
    text = budget.strip().upper().removesuffix("B")
    scale = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}
    if text and text[-1] in scale:
        return int(float(text[:-1]) * scale[text[-1]])
    return int(float(text))


def _coalesced(batches: Iterable[pa.RecordBatch], out: pa.Schema) -> Iterator[pa.RecordBatch]:
    """Merge small batches up to `BATCH_ROWS`, so held rows yield the row groups spilled ones do.

    A core batch spans many buckets, so splitting it leaves each bucket a handful of rows. Held
    and yielded as they arrive those become row groups of a couple of thousand rows: measured,
    140,315 groups against 2,197, and a table half again as large for the per-group overhead.
    """
    held: list[pa.RecordBatch] = []
    rows = 0
    for batch in batches:
        held.append(batch)
        rows += batch.num_rows
        if rows >= BATCH_ROWS:
            yield _merged(held, out)
            held, rows = [], 0
    if held:
        yield _merged(held, out)


def _merged(held: list[pa.RecordBatch], out: pa.Schema) -> pa.RecordBatch:
    """Concatenate held batches into one, unifying the dictionaries they were built with."""
    if len(held) == 1:
        return held[0]
    return pa.Table.from_batches(held, schema=out).combine_chunks().to_batches()[0]


class _Buckets:
    """Per-bucket Parquet spill files, written in the order rows arrive.

    Parquet, although a spill is written once, read once and deleted, and its encoding
    therefore has no reader to benefit. The encoding is not for a reader here, it is for the
    disk: dictionary-encoding a column that repeats a handful of values puts
    a million rows in 2.7 MB where Arrow IPC needs 195 MB. Writing a batch costs 0.100 s
    against IPC's 0.053 s, and over a full session that trade is worth taking on anything but
    the fastest storage -- uncompressed IPC spills 56 GB and takes 321.8 s where this takes
    76.6 s.

    Bucketing by time and sorting by unit inside each bucket needs no global sort, because
    `core.spike_events` is already ordered by `(session_id, unit_id, t_tick)` (R81 §2.4)
    (`03` §5.3, `03`). Visiting it in that order and appending each row to its bucket's file
    leaves every file in exactly the intra-bucket order `03` §5.4 declares. What remains is to
    concatenate the files in bucket order, which is a second pass and no comparisons.
    """

    def __init__(self, root: Path, out: pa.Schema, budget: int = 0,
                 spec: Mapping[str, Any] | None = None) -> None:
        from .encoding import encodings

        self._root = root
        self._out = out
        # The spill gets the encoding the finished table gets. Its own bytes have no reader,
        # but a tick column left to pyarrow's default overflows the dictionary page and falls
        # back to PLAIN mid-column, paying for both: 1,195 MB and 77.4 s against 500 MB and
        # 60.9 s, at no cost in memory.
        # No sample: the spill is opened before its first batch exists, so the naming convention
        # stands in. Its bytes have no reader, and the finished table is measured properly.
        delta, plain = encodings(RESOURCE, spec or {}, out)
        self._options: dict[str, Any] = {"compression": "zstd"}
        if delta or plain:
            self._options["use_dictionary"] = [n for n in out.names if n not in {*delta, *plain}]
            if delta:
                self._options["column_encoding"] = dict.fromkeys(delta, "DELTA_BINARY_PACKED")
        self._budget = budget
        # Read back as codes, the way they were written. A spill that decoded on the way out
        # would hand the table writer strings it is about to dictionary-encode again.
        self._coded = [f.name for f in out if pa.types.is_dictionary(f.type)]
        self._bytes = 0
        self._writers: dict[int, pq.ParquetWriter] = {}
        self._held: dict[int, list[pa.RecordBatch]] = {}
        self._rows: dict[int, int] = {}

    def add(self, bucket: int, batch: pa.RecordBatch) -> None:
        self._held.setdefault(bucket, []).append(batch)
        self._rows[bucket] = self._rows.get(bucket, 0) + batch.num_rows
        self._bytes += batch.nbytes
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
        self._writers[bucket].write_table(pa.Table.from_batches(held, schema=self._out))

    def drain(self) -> Iterator[pa.RecordBatch]:
        """Yield every bucket's rows in bucket order, in batches of at most `BATCH_ROWS`.

        A batch never spans two buckets, so each becomes a row group lying inside one bucket
        (`03` §5.4). Row groups cut at a fixed row count would straddle boundaries and span
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
                reader = pq.ParquetFile(path, read_dictionary=self._coded or None)
                # Coalesced on the way out as well as on the way in: reading a column as codes
                # cuts a batch wherever the dictionary changes, so `batch_size` is a ceiling
                # and not the size, and each short batch would become its own row group.
                batches = _coalesced(reader.iter_batches(batch_size=BATCH_ROWS), self._out)
            else:
                batches = _coalesced(self._held[bucket], self._out)
            yield from batches


def spike_events(
    packet: Any,
    *,
    reference: str | None = None,
    bound: float | None = None,
    bucket_seconds: int = BUCKET_SECONDS,
    scratch: Path | None = None,
    memory_budget: int | str = 0,
    dropped: list[int] | None = None,
) -> Iterator[pa.RecordBatch]:
    """`analysis.spike_events` -- core spikes on the reference clock, bucketed by time.

    A spike whose tick falls further than the bound from any anchor is **dropped**: `01` §3.9
    leaves it undefined, and a derived table is the wrong place to record that a value is
    missing.

    Parameters
    ----------
    packet : Packet
        An open packet carrying `core.spike_events`, `core.clock_anchors`, `core.clocks` and
        `core.sessions`.
    reference : str, optional
        The clock to map onto. Defaults to `core.sessions.reference_clock_id` (R27 §2).
    bound : float, optional
        Passed to :func:`~escapewheel_reader.clocks.align`. Defaults to what the packet's own
        import run measured (R37 §3.3), so a table derived here places the same spikes the
        packet's `t_zero_tick` was taken over.
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
    dropped : list of int, optional
        A one-element list the count of unmappable spikes is accumulated into, since a
        generator cannot return one. `06` §4 requires the producing run to record it.
        Held with identifiers as dictionary codes it is 36 bytes a row, so a session of 287 M
        spikes wants 10.4 GB; the same rows spill to 0.5 GB of Parquet instead. Zero, the
        default, holds no more than one batch per bucket, because whether ten gigabytes is
        reasonable or ruinous is a property of the machine packaging the data rather than of
        the data. It buys about 8% on a session of this size, so spilling is the default for
        being the cheaper resource, not the faster path.

    Yields
    ------
    pyarrow.RecordBatch
        In `03` §5.4's order, at most `BATCH_ROWS` rows, never spanning two buckets.

    Raises
    ------
    NotAligned
        If the session declares no reference clock, if a clock the spikes are on carries no
        anchors, or if the reference clock declares no tick rate.
    """
    reference = _clock_id(packet, reference or reference_clock(packet))
    bound = declared_bound(packet) if bound is None else bound
    width = bucket_seconds * _tick_rate(packet, reference)
    dropped = [0] if dropped is None else dropped
    by_clock = anchors(packet)
    handle = packet.table_resource("core.spike_events")
    columns = ["session_id", "unit_id", "t_tick"]
    # R96 §3.4 struck `core.spike_events.clock_id` and §3.3 gave `t_tick` a `clock_from` hop to
    # `core.units.clock_id`, so a spike's clock is resolved through its unit rather than carried
    # per row. Resolved once into an array indexed by `unit_id`, which R81 §2.1 numbers densely
    # from zero: a dict lookup per spike would materialise a Python object for each of 287 M rows,
    # which is the cost R53's note below says the int32 column exists to avoid.
    on_clock = _unit_clocks(packet)
    # Types come from the registry rather than being spelled here. They were dictionary-coded
    # strings until R53 made every identifier an `int32`, and the machinery that avoided
    # decoding them -- 9.13 GB of Arrow per 40 row groups -- has nothing left to avoid: four
    # bytes a row is what the code alone used to cost.
    registry = packet.registry
    if registry is None:
        raise NotAligned("the packet embeds no registry, so the derived table has no declared types")
    out = arrow_schema(registry["tables"]["analysis.spike_events"],
                       {*columns, "clock_id", "time_bucket_tick"})

    root = Path(scratch) if scratch else Path(tempfile.mkdtemp(prefix=".materialize-", dir=packet.root.parent))
    buckets = _Buckets(root, out, _bytes(memory_budget), registry["tables"][RESOURCE])
    try:
        reader = pq.ParquetFile(handle.path)
        carry: tuple[int, int] | None = None
        for batch in reader.iter_batches(batch_size=BATCH_ROWS, columns=columns):
            units = batch.column("unit_id").to_numpy(zero_copy_only=False)
            if units.size and int(units.max()) >= on_clock.size:
                raise NotAligned(
                    f"a spike names unit {int(units.max())}, which `core.units` does not declare, "
                    f"so its tick reaches no clock (R96 §3.3)"
                )
            timed = pa.record_batch(
                {"t_tick": batch.column("t_tick"), "clock_id": pa.array(on_clock[units])}
            )
            parent, keep = mapped(timed, reference, by_clock, bound)
            # `06` §4: counted whether or not any are dropped. A recorded zero is the
            # evidence the bound was sufficient; silence is what let a reader and this
            # writer disagree about which spikes exist without either noticing.
            dropped[0] += int(keep.size - keep.sum())
            if not keep.any():
                continue
            taken = np.flatnonzero(keep)
            ticks = parent[taken]
            units = batch.column("unit_id").take(taken).to_numpy(zero_copy_only=False)
            _refuse_on_collision(units, ticks, carry)
            carry = (int(units[-1]), int(ticks[-1])) if units.size else carry
            # Floor division, so a negative tick lands in the bucket that starts before it
            # rather than the one that starts after.
            starts = (ticks // width) * width
            converted = pa.record_batch(
                {
                    "session_id": batch.column("session_id").take(taken),
                    "unit_id": pa.array(units),
                    "t_tick": pa.array(ticks, type=pa.int64()),
                    # Every row is on the reference clock by construction, so this is one
                    # value repeated rather than a column read from the source.
                    "clock_id": pa.array(np.full(taken.size, reference, dtype=np.int32)),
                    "time_bucket_tick": pa.array(starts, type=pa.int64()),
                },
                schema=out,
            )
            # A batch of core rows is one unit's spikes over the whole session, so it spans
            # many buckets; split it rather than assuming it belongs to one.
            edges = np.flatnonzero(np.diff(starts)) + 1
            for lo, hi in zip([0, *edges], [*edges, starts.size], strict=True):
                buckets.add(int(starts[lo]), converted.slice(int(lo), int(hi - lo)))
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
    bound: float | None = None,
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
    (`04` §3). So does the count of spikes this could not place (`06` §4), which is otherwise
    invisible: a derived table one row short looks exactly like a derived table. `memory_budget`
    and `scratch` do not: they change how the rows are produced, not which rows they are, and
    recording them would make two identical packets claim different provenance.

    Returns
    -------
    str
        The resource ID added.
    """
    from . import __version__

    resource = "analysis.spike_events"
    session = packet.sessions[0] if len(packet.sessions) == 1 else None
    bound = declared_bound(packet) if bound is None else bound
    started = datetime.now(tz=timezone.utc)
    dropped: list[int] = [0]
    writer.add_batches(
        resource,
        spike_events(
            packet,
            reference=reference,
            bound=bound,
            bucket_seconds=bucket_seconds,
            memory_budget=memory_budget,
            scratch=scratch,
            dropped=dropped,
        ),
    )
    writer.derives(resource, ["core.spike_events", "core.clock_anchors", "core.clocks"])
    writer.add(
        "core.processing_runs",
        [
            {
                "processing_run_id": run_id,
                "session_id": session,
                "activity_type": "materialization",
                # R44 §2.1: session-wide, so the session is the scope. Both stay null on a
                # multi-session packet rather than naming one of several, because a writer that
                # cannot determine a fact records nothing (`04` §5.2). `02` §8.3: the pair is set
                # together or not at all.
                "scope_kind": "core.sessions" if session else None,
                "scope": session,
                "software_name": "escapewheel_writer",
                "software_version": __version__,
                "parameters": {
                    "bucket_seconds": bucket_seconds,
                    "bound": bound,
                    "reference_clock_id": reference,
                    # `06` §4. Recorded even when zero: that a bound was sufficient is a
                    # fact about this packet, not an assumption a reader should have to make.
                    "spikes_without_a_defined_mapping": dropped[0],
                },
                "started_at": started,
                "ended_at": datetime.now(tz=timezone.utc),
                "status": "succeeded",
            }
        ],
    )
    writer.produced_by(resource, run_id)
    return resource


__all__ = ["BATCH_ROWS", "BUCKET_SECONDS", "RUN_ID", "Collided", "NotAligned", "into", "spike_events"]

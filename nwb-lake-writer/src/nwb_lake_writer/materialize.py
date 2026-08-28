"""Build analysis resources from a packet's core ones.

`06` splits transformations two ways: a view where the work is cheap, a materialized table
where it is expensive or frequently reused. Clock alignment sits awkwardly between them and
the measurement decides it -- 29 M spikes a second, so a query touching a few units pays
single-digit milliseconds and a full-session scan pays seconds. This materializes the second
case and leaves the first to a view.

What the analysis layer costs
-----------------------------

An analysis resource MUST declare lineage to core (`06`), which is the manifest's
`derived_from`, and it is disposable: nothing here is canonical, and a packet without it is
complete. What it buys is that a query spanning two probes does no conversion, because the
ticks are already on one clock.

What it deliberately loses
--------------------------

The exact probe tick. `core.spike_events` keeps that and this does not, which is the whole
point of the layering -- the derived value is convenient and the measured one is the record.
A spike this cannot place is dropped rather than guessed, so the analysis table is not
row-aligned with core and does not pretend to be.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from numpy.typing import NDArray

from .align import BOUND, align

#: Rows per batch, and therefore the writer's peak memory.
BATCH_ROWS = 1 << 20


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


def spike_events(
    packet: Any,
    *,
    reference: str | None = None,
    bound: float = BOUND,
    batch_rows: int = BATCH_ROWS,
) -> Iterator[pa.RecordBatch]:
    """`analysis.spike_events` -- core spikes on the session's reference clock.

    Yielded in the registry's sort order, which `core.spike_events` is already in, so the
    mapping is applied batch by batch and nothing is sorted again. A spike whose tick falls
    further than the bound from any anchor is **dropped**: R27 §5.3 leaves it undefined, and
    a derived table is the wrong place to record that a value is missing.

    Parameters
    ----------
    packet : Packet
        An open packet carrying `core.spike_events`, `core.clock_anchors` and `core.clocks`.
    reference : str, optional
        The clock to map onto. Defaults to `core.sessions.reference_clock_id` (R27 §2), which
        is what the session declares its times are reported on.
    bound : float
        Passed to :func:`~nwb_lake_writer.align.align`.
    batch_rows : int
        Rows per batch.

    Yields
    ------
    pyarrow.RecordBatch

    Raises
    ------
    NotAligned
        If a clock the spikes are on carries no anchors reaching the reference.
    """
    if reference is None:
        sessions = packet.table("core.sessions")
        declared = (
            sessions.column("reference_clock_id").to_pylist() if "reference_clock_id" in sessions.column_names else []
        )
        named = [d for d in declared if d]
        if not named:
            raise NotAligned("the session declares no reference_clock_id (R27 §2), so there is nothing to map onto")
        reference = named[0]

    anchors = _anchors(packet)
    handle = packet.table_resource("core.spike_events")
    columns = ["session_id", "unit_id", "sorting_run_id", "curation_id", "t_tick", "clock_id"]

    for batch in pq.ParquetFile(handle.path).iter_batches(batch_size=batch_rows, columns=columns):
        ticks = np.asarray(batch.column("t_tick").to_numpy(zero_copy_only=False), dtype=np.int64)
        clocks = batch.column("clock_id").to_pylist()
        parent = np.empty(ticks.size, dtype=np.int64)
        keep = np.zeros(ticks.size, dtype=bool)

        # A batch spans at most two streams, since the table is sorted by sorting_run_id and
        # each stream is one run -- so this loop runs once or twice, not per row.
        for name in dict.fromkeys(clocks):
            where = np.array([i for i, c in enumerate(clocks) if c == name])
            if name == reference:
                parent[where], keep[where] = ticks[where], True
                continue
            if name not in anchors:
                raise NotAligned(f"{name} carries no anchors, so its ticks reach no reference clock")
            mapped, defined = align(ticks[where], *anchors[name], bound=bound)
            parent[where], keep[where] = mapped, defined

        if not keep.any():
            continue
        taken = np.flatnonzero(keep)
        yield pa.record_batch(
            {
                "session_id": batch.column("session_id").take(taken),
                "unit_id": batch.column("unit_id").take(taken),
                "sorting_run_id": batch.column("sorting_run_id").take(taken),
                "curation_id": batch.column("curation_id").take(taken),
                "t_tick": pa.array(parent[taken], type=pa.int64()),
                "clock_id": pa.repeat(pa.scalar(reference, pa.string()), taken.size),
            }
        )


def into(packet: Any, writer: Any, *, reference: str | None = None, bound: float = BOUND) -> str:
    """Add `analysis.spike_events` to a writer, with the lineage `06` requires.

    Returns
    -------
    str
        The resource ID added.
    """
    resource = "analysis.spike_events"
    writer.add_batches(resource, spike_events(packet, reference=reference, bound=bound))
    writer.derives(resource, ["core.spike_events", "core.clock_anchors", "core.clocks"])
    return resource


__all__ = ["BATCH_ROWS", "NotAligned", "into", "spike_events"]

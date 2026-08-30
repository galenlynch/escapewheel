# Performance

Measured on `ecephys_776259_2025-04-09`: 286,896,563 spikes, twelve probe streams, rotational
disk.

## Never leave Arrow inside a per-batch path

Every performance defect found in this package has been a column turned into Python objects
inside a loop that runs once per batch.

| What it was | Cost | In Arrow |
|---|---|---|
| `unit_id[index].tolist()` then `pa.array(...)` | 51.3 ms per 1 M rows | `values.take(idx)`, 2.9 ms — 18× |
| `to_pylist()` then `[i for i, c in enumerate(clocks) if c == name]` | 13.63 ms per batch | `pc.equal` + `np.flatnonzero`, 1.33 ms — 10× |
| `GROUP BY` over a four-column string key | 26 GB spilled | compare neighbours, over the existing sort order |

If a line converts a column to a Python `list` and its surrounding code runs once per batch, it
is wrong. `pc.unique`, `pc.equal`, `pc.is_in`, `Array.take`, `Array.dictionary_encode` and
`np.flatnonzero` cover nearly every case and release the GIL.

The enclosing loop can be short and the defect still per-row: the clock loop above runs twice,
and its comprehension ran 131,072 times.

Not every `to_pylist()` qualifies. `_tick_rate` calls one on `core.clocks`, thirteen rows, and
`arrow._plain` normalises single metadata values. The test is whether the call runs per batch.

## String identifiers are not the cause

Parquet dictionary-encodes them. `session_id` is 6 KB across 287 M rows; a million rows of
R5's four-column contextual unit key are 2.7 MB, against 195 MB as uncompressed Arrow IPC.
Decoding an identifier into Python costs; storing and comparing one does not.

This is why `materialize.py` spills to Parquet despite a spill having no reader to benefit from
the encoding. An Arrow IPC spill took 321.8 s against 76.6 s.

## Layout

**Tick columns take `DELTA_BINARY_PACKED`**, derived from the schema's `_tick` convention, plus
`anchor_index` and `n_spikes`. A tick has too many distinct values for a dictionary, so the
default overflows the dictionary page and falls back to `PLAIN` mid-column, paying for both.
`core.spike_events` 885 → 682 MB; `core.clock_anchors` 465 → 26 KB. `channel_ordinal` is the
exception: it cycles 0..25 per unit, where RLE over a 26-entry dictionary beats delta by 1.38×.

**Row groups are one million rows, not the 8–16 MB object-storage band.** No available reader
prunes below a row group, so a larger one multiplies what a predicate reads. A one-second
window, cold: 1 M rows 1.93 s, 4 M rows 4.42 s.

**No page index.** Neither DuckDB nor pyarrow reads one; `duckdb#2755` is closed as not
supported. Measured identically with and without.

**One batch is exactly one row group.** `ParquetWriter.write_batch` defaults to cutting at 2²⁰
rows, so R30 §3.2's guarantee must be asked for explicitly.

## Where an import spends 243.9 s

```text
sources                    9.5 s
stage core                59.9 s   core.spike_events is 99.9% of the rows
derive and stage analysis 97.8 s   spill write about half, clock arithmetic 7%
validate                  76.8 s   Tier 1 and Tier 2 over two 287 M-row tables
promote                    0.0 s
```

Physical order is established while staging, so validation does not re-read 467 MB of sort
columns. The comparison runs on the batches in its own pipeline stage, and `commit` passes the
resources it settled to `validate(scan=...)`.

## Checking a change

A profile locates cost; it does not identify the fix. `pq.write_table` is 46% of the
materialization and is not removable — that cost buys the 72× reduction in bytes above.

```bash
/usr/bin/time -f "PEAK %M KB  CPU %P" uv run nwb-lake import session.toml --out /tmp/pkt
nwb-lake import session.toml --sample 200000    # full validated packet, 8.7 s
```

Sort a profile by `tottime` rather than `cumtime` to find the hot call. `--sample` caps spikes
per stream at the single read the summary and the stream share, so `core.units` stays
consistent with what is written, and the cap reaches `core.processing_runs.parameters`.

Three changes have been made and reverted on measurement: an Arrow IPC spill, row groups in the
object-storage band, and a page index.

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

## Storing a low-cardinality string is cheap; converting one is not

Parquet dictionary-encodes it, so the column costs a hundredth of a bit a row: measured on
20 M rows over six values, a kind column is 0.013 bit/row against an int32 surrogate's 0.008,
and the two files differ by 0.05%. This is also why `materialize.py` spills to Parquet despite
a spill having no reader to benefit: an Arrow IPC spill took 321.8 s against 76.6 s.

What costs is converting between representations, and a path that does it four times — Parquet
decode, encode to spill, decode on read-back, encode to the table. Measured on 40 row groups of
five such columns:

| | time | Arrow held |
|---|---|---|
| decoded to strings | 1.05 s | 9.13 GB |
| held as codes | 0.15 s | 1.27 GB |

**Carry the codes end to end**, wherever a string column survives into a materialization.

## Dictionaries in pyarrow

A dictionary is an *encoding*, not a type. Parquet has no dictionary type — the column is
`BYTE_ARRAY`/`String` either way, and only the Arrow schema pyarrow stores as file metadata
records the choice. That single fact settles most of the rules below.

**Ask for codes on the way in.** `pq.ParquetFile(path, read_dictionary=[...])`, not
`read_table` followed by `dictionary_encode`.

**Do not advertise them.** Writing a dictionary column stores an Arrow schema saying so, and
the file then reads back as a dictionary by default — a type the registry does not declare.
`store_schema=False` withholds it; every other type survives, timestamps and their zone
included. `_as_held` and `_options` in `writer.py` are that pair.

**Never compare codes for order.** A dictionary is unordered, so code order is not value order.
Comparing `.indices` is valid only for equality, and only within one dictionary.

**Do not hand a dictionary to a comparison kernel either.** `pc.less` and `pc.equal` accept one
and are correct, but they decode both sides on every call. Compare the *rank* of the dictionary
values instead: rank the dictionary once — a few hundred entries beside a batch of a hundred
thousand rows — and compare int32. Per column of 131,072 rows:

| | |
|---|---|
| plain string | 0.682 ms |
| dictionary handed to `pc.less`/`pc.equal` | 2.369 ms |
| rank of the dictionary value, as int32 | 0.147 ms |

`_ranked` in `nwb_lake_validator.validator` is this, and it makes the ordering scan faster on
coded columns than on decoded ones.

**`batch_size` becomes a ceiling.** `iter_batches(read_dictionary=...)` cuts a batch wherever
the dictionary changes. Left alone that doubled `analysis.spike_events` to 4,242 row groups;
where one batch is one row group, coalesce before writing.

**A constant column is a one-entry dictionary.** `pa.repeat(pa.scalar(name), n)` builds n
strings; codes into a single-entry dictionary are 4 bytes a row.

**`take` gathers codes.** It keeps the dictionary and touches no characters.
`Table.from_batches` accepts chunks with differing dictionaries; `combine_chunks()` unifies
them, which costs — so merge once, not per batch.

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

## Where an import spends 105.1 s

A complete 23-resource packet, `--memory-budget 20GB`, one command:

```text
sources                    9.5 s
stage core                50.5 s   core.spike_events is 99.9% of the rows
derive and stage analysis 32.7 s
validate                  12.5 s   Tier 1 and Tier 2 over two 287 M-row tables
promote                    0.0 s
```

Physical order is established while staging, so validation does not re-read 467 MB of sort
columns. The comparison runs on the batches in its own pipeline stage, and `commit` passes the
resources it settled to `validate(scan=...)`.

Materializing `analysis.spike_events` alone, and validating a packet of unknown provenance,
where that shortcut does not apply:

| | spill | held (20 GB) | validate |
|---|---|---|---|
| decoded identifiers | 96.1 s | 191.9 s | 66.3 s |
| codes carried through | 58.5 s | 34.5 s | 37.1 s |

Spilling to tmpfs instead of disk is worth 4.6% (55.8 s against 58.5) and costs 479 MB of RAM
that a cgroup will not cap. `--scratch` reaches it; nothing special-cases it.

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

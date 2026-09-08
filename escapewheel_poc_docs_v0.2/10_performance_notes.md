# Part 10 — Performance Notes

Informative. Part version **0.1.0** (R93 §3.4).

## 1. Scope

This part carries what a packet's bytes make true under `escapewheel-portable-v0.1`: what an
encoding costs, what a row group spans, what an object store answers. A number here supports a
rule that lives elsewhere and states none of its own; where a measurement justifies a requirement,
the requirement stays in the part that binds and this part carries the reading (R93 §3.4).

It is not a substitute for `conformance/`, which holds the probes that produced these numbers.
This part says what they mean.

A number that would change if the reference implementation were replaced is Part 07 §7's, not this
part's: how a columnar library decodes a batch, how one query planner treats a projection against
a join. What survives that replacement is here (R93 §3.5).

**Every measurement below records the revision that took it and that revision's date, and none
records the library versions it was taken against except where noted.** Those were not kept, and
saying so is what R93 §3.4 asks: a number whose toolchain is unknown has unknown currency, where a
number silently missing the field says nothing at all.

## 2. Encoding and compression

### 2.1 A tick column is delta-encoded, not dictionary-encoded

`core.media_frames.pts` over 7,570,450 frames, the same rows in the same row groups (R68 §3,
2026-09-04; toolchain not kept):

| `pts` as | encoding | `pts` | whole table |
|---|---|---:|---:|
| `float64` | `RLE_DICTIONARY` | 11.371 MB | 11.73 MB |
| `float64` | `BYTE_STREAM_SPLIT` | 0.273 MB | 0.66 MB |
| `int64` | `DELTA_BINARY_PACKED` | 0.043 MB | 0.43 MB |

Dictionary encoding is what a column declaring nothing else receives, and a monotonic ramp of 7.5 M
distinct values is its worst case: `pts` is **96.9%** of the table as written. `DELTA_BINARY_PACKED`
is defined for `INT32` and `INT64` alone, which is what `03` §5.5's SHOULD turns on.

### 2.2 An integer identifier costs nothing to store and much to read

Over 287,896,563 spikes, the identifier columns are **8.1 MB, 1% of the table**, because a sorted
low-cardinality column compresses away; the integer form is **1.1% smaller** than the string one.
Storage is therefore not what decides the type — the read is, at **10.2x** on a join to
`core.units` (R53 §1, 2026-09-02; toolchain not kept).

### 2.3 A repeated key column is free under a clustered sort

Four-column unit identity against one numbered `unit_id`, over the same spike table: **819 MB
either way** (R81 §1, 2026-09-05; toolchain not kept). `core.media_frames` shows the same shape at
7,570,450 rows, where one distinct `session_id` costs **1.0005x**, 0.013 bits a row (R88 §4,
2026-09-07; toolchain not kept).

## 3. Row groups

A large table's row groups are sized for analytical scans (`03` §5.1). **100,000 to 1,000,000
rows** is a starting point to be adjusted by profiling; it is a number this format fixes rather
than a rule a packet can fail, which is why `03` §5.1 keeps the SHOULD and the number is here.

Where a table declares a time bucket, a row group SHOULD start at each bucket boundary (R30 §3.3):
a group cut at a fixed row count straddles boundaries and spans two buckets' worth of time.

## 4. The object store

### 4.1 An endpoint plateaus at about 120 requests a second

Whatever the concurrency (R86 §1.1, 2026-09-06; toolchain not kept). Twenty sessions of metadata
is therefore about a second, which is what makes a union across packets cheap enough that no
summary table is needed to avoid it.

### 4.2 One file beats a partitioned prefix on the engine that matters

The same rows staged to S3 four ways — a single file, a declared member list, the same members
reached by globbing, and hive layout — with the member arms at 682.2 MB against the single file's
681.6 MB (R42 §4.1, withdrawn 2026-09-02; toolchain not kept). DuckDB's single file wins every
query cold and warm. Where the member arms win, the gain reproduces at the same ratio on local
disk, so it is scan parallelism rather than skipped round trips.

The write side is the other way: a re-sorting rewrites the whole file where partitioning writes one
member. No session has yet had a second sorting.

## 5. The Zarr codec floor is version-specific

Measured in `conformance/zarr-probe/` against **zarr-python 3.3.0, Zarr.jl 0.10.2 and Julia
1.12.7** (R21 §2, 2026-08-27) — the one measurement here whose toolchain was kept, and the one that
shows why the others should be:

| configuration | zarr-python 3.3.0 | Zarr.jl 0.10.2 |
|---|---|---|
| v3 raw, gzip, zstd | reads | reads |
| v3 blosc-zstd-shuffle, `sharding_indexed` | reads | reads |
| v2 zstd, v2 blosc-zstd-shuffle | reads | reads |

A reading of this kind stops being true the moment a library moves, with nothing in the prose
changing to show it. That is what `03` §6.1's per-version codec floor exists to state as a rule,
and what this table exists to explain.

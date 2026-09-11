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

`core.media_frames.pts` over 7,570,450 frames, the same rows in the same row groups (R68 §1.3,
2026-09-04; toolchain not kept):

| `pts` as | encoding | `pts` | whole table |
|---|---|---:|---:|
| `float64` | `RLE_DICTIONARY` | 11.371 MB | 11.73 MB |
| `float64` | `BYTE_STREAM_SPLIT` | 0.273 MB | 0.66 MB |
| `int64` | `DELTA_BINARY_PACKED` | 0.043 MB | 0.43 MB |

Dictionary encoding is what a column declaring nothing else receives, and a monotonic ramp of 7.5 M
distinct values is its worst case: `pts` is **96.9%** of the table as written. `DELTA_BINARY_PACKED`
is defined for `INT32` and `INT64` alone, which is what Part 03 §5.5's SHOULD turns on.

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

### 2.4 An ascending identifier costs 30.95 bits a row under a dictionary

The first column of a table's sort order whose role is `identifier` ascends across the whole table,
and a dictionary over it stores the values once and an index into them again. Column-chunk bytes on
`ecephys_776259` (R110 §2.1, 2026-09-10; pyarrow 25.0.1, Python 3.13.15):

| column | dictionary | delta | |
|---|---:|---:|---:|
| `aind_unit_qc.synchrony.unit_id` | 48.6 kB | 0.6 kB | **79x** |
| `core.unit_coordinate_values.unit_id` | 46.8 kB | 0.6 kB | **75x** |
| `core.units.unit_id` | 26.3 kB | 0.5 kB | 57x |
| `core.unit_coordinates.unit_id` | 25.3 kB | 0.5 kB | 53x |
| `core.electrode_coordinates.electrode_id` | 24.3 kB | 0.5 kB | 48x |
| `core.electrodes.electrode_id` | 17.5 kB | 0.5 kB | 37x |

`core.unit_coordinates.unit_id` costs **30.95 bits a row** for an `int32`, which is almost the 32
bits the raw values take.

### 2.5 Four float columns in five do not repeat enough to index

Of the **32 float columns** reaching 2 kB under pyarrow's default across two packaged sessions,
**27 are smaller written plain**, by 1.15x to 1.76x. The five that repeat decide more than the
twenty-seven: `core.spike_events.amplitude` is quantised to the sorting run's amplitude step, so
286,896,563 rows hold few distinct values and the dictionary is **1.85x** better across **209 MB**
(R110 §2.2, 2026-09-10; toolchain as above).

### 2.6 A packet's small tables are what an open transfers

Two spike tables are **1,168 MB** of `ecephys_776259` and are read behind a filter; the other 38
tables come to **1.375 MB** and are read entire. Those 38 are **2.622 MB** under pyarrow's default,
so the encoding rules take **1.91x** off what a consumer transfers before a filter can prune
anything — 1.80x on `ecephys_786867` over its 37 comparable tables, and **23.94x** with
`core.media_frames` counted, where 7,570,450 rows go from 30.949 MB to 0.429 MB.

Decoding gives none of it back: over the same 38 tables, warm and interleaved, **15.6 ms against
15.8 ms**, and 28.8 ms against 57.7 ms where `core.media_frames` is among them (R110 §2.3,
2026-09-10; toolchain as above). Round trips are the one cost this leaves alone — a column chunk is
one ranged read at either size, so what an encoding changes is what each request carries (§4.1).

### 2.7 A rule read off the declaration picks worse on 82 columns of 116

What delta exploits is small successive differences and what a dictionary exploits is repetition,
and the registry declares neither. Deriving the choice from the sort key — delta for a key column,
a dictionary for everything else — was measured over the 116 column-and-packet pairs reaching 2 kB
under either choice and picked worse on **82**: `core.media_frames.pts` **188x worse** and
`core.clock_anchors.t_tick` 57x, both climbing steadily without being key columns, and
`core.unit_electrodes.electrode_id` 1.84x, a trailing key component that climbs within each unit
and resets (R110 §2.4, 2026-09-10; toolchain as above).

A declaration says what a value means. It does not say how the values are spread, and a storage
choice turns on the second.

## 3. Row groups

A large table's row groups are sized for analytical scans (Part 03 §5.1). **100,000 to 1,000,000
rows** is a starting point to be adjusted by profiling; it is a number this format fixes rather
than a rule a packet can fail, which is why Part 03 §5.1 keeps the SHOULD and the number is here.

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
changing to show it. That is what Part 03 §6.1's per-version codec floor exists to state as a rule,
and what this table exists to explain.

# Part 10 — Performance Notes

Informative. Part version **0.1.0**.

## 1. Scope

This part carries what a packet's bytes make true under `escapewheel-portable-v0.1`: what an
encoding costs, what a row group spans, what an object store answers. A number here supports a
rule that lives elsewhere and states none of its own; where a measurement justifies a requirement,
the requirement stays in the part that binds and this part carries the reading.

It is not a substitute for `conformance/`, which holds the probes that produced these numbers.
This part says what they mean.

**Every measurement below records its date, and none records the library versions it was taken
against except where noted.** Those were not kept. A number whose toolchain is unknown has unknown
currency; a number silently missing the field says nothing at all.

## 2. Encoding and compression

### 2.1 A tick column is delta-encoded, not dictionary-encoded

`core.media_frames.pts` over 7,570,450 frames, the same rows in the same row groups (2026-09-04; toolchain not kept):

| `pts` as | encoding | `pts` | whole table |
|---|---|---:|---:|
| `float64` | `RLE_DICTIONARY` | 11.371 MB | 11.73 MB |
| `float64` | `BYTE_STREAM_SPLIT` | 0.273 MB | 0.66 MB |
| `int64` | `DELTA_BINARY_PACKED` | 0.043 MB | 0.43 MB |

Dictionary encoding is what a column declaring nothing else receives, and a monotonic ramp of 7.5 M
distinct values is its worst case: `pts` is **96.9%** of the table as written. `DELTA_BINARY_PACKED`
is defined for `INT32` and `INT64` alone, which is what Part 03 §5.5's rule for an ordered integer
turns on.

### 2.2 An integer identifier costs nothing to store and much to read

Over 287,896,563 spikes, the identifier columns are **8.1 MB, 1% of the table**, because a sorted
low-cardinality column compresses away; the integer form is **1.1% smaller** than the string one.
Storage is therefore not what decides the type — the read is, at **10.2x** on a join to
`core.units` (2026-09-02; toolchain not kept).

### 2.3 A repeated key column is free under a clustered sort

Four-column unit identity against one numbered `unit_id`, over the same spike table: **819 MB
either way** (2026-09-05; toolchain not kept). `core.media_frames` shows the same shape at
7,570,450 rows, where one distinct `session_id` costs **1.0005x**, 0.013 bits a row (2026-09-07; toolchain not kept).

### 2.4 An ascending identifier costs 30.95 bits a row under a dictionary

The first column of a table's sort order whose role is `identifier` ascends across the whole table,
and a dictionary over it stores the values once and an index into them again. Column-chunk bytes on
`ecephys_776259` (2026-09-10; pyarrow 25.0.1, Python 3.13.15):

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
(2026-09-10; toolchain as above).

### 2.6 A packet's small tables are what an open transfers

Two spike tables are **1,168 MB** of `ecephys_776259` and are read behind a filter; the other 38
tables come to **1.375 MB** and are read entire. Those 38 are **2.622 MB** under pyarrow's default,
so the encoding rules take **1.91x** off what a consumer transfers before a filter can prune
anything — 1.80x on `ecephys_786867` over its 37 comparable tables, and **23.94x** with
`core.media_frames` counted, where 7,570,450 rows go from 30.949 MB to 0.429 MB.

Decoding gives none of it back: over the same 38 tables, warm and interleaved, **15.6 ms against
15.8 ms**, and 28.8 ms against 57.7 ms where `core.media_frames` is among them (2026-09-10; toolchain as above). Round trips are the one cost this leaves alone — a column chunk is
one ranged read at either size, so what an encoding changes is what each request carries (§4.1).

### 2.7 A rule read off the declaration picks worse on 82 columns of 116

What delta exploits is small successive differences and what a dictionary exploits is repetition,
and the registry declares neither. Deriving the choice from the sort key — delta for a key column,
a dictionary for everything else — was measured over the 116 column-and-packet pairs reaching 2 kB
under either choice and picked worse on **82**: `core.media_frames.pts` **188x worse** and
`core.clock_anchors.t_tick` 57x, both climbing steadily without being key columns, and
`core.unit_electrodes.electrode_id` 1.84x, a trailing key component that climbs within each unit
and resets (2026-09-10; toolchain as above).

A declaration says what a value means. It does not say how the values are spread, and a storage
choice turns on the second.

### 2.8 A dictionary page costs 27 bytes in every row group

A column holding one value gives a dictionary nothing to index that plain's compression does not
already remove. A constant `int32` under Zstandard (2026-09-15; pyarrow 25.0.1, Python
3.13.15):

| rows | dictionary | plain |
|---:|---:|---:|
| 12 | 92 B | 69 B |
| 6,781 | 95 B | 75 B |
| 171,280 | 666 B | 718 B |
| 1,000,000 | 3,577 B | 4,000 B |

The page is 27 bytes in each row group and outweighs the column below some tens of thousands of
rows; above them the dictionary is smaller by a steady 1.12x. The committed packets put the crossing
between `core.clock_anchors.session_id` at 41,275 rows, where the two are within 3 bytes, and at
76,646 rows, where the dictionary is smaller. Below 50,000 rows delta suits a single-valued integer
better than plain: it is never more than 6 bytes larger in either packet, and plain is up to 5.9x
larger, `core.array_channels.axis_index` being 546 bytes plain and 93 under delta.

### 2.9 Declarations mark the integers that climb within groups

A count over a whole column sees a climb only where the table is sorted by that column.
`core.spike_events.t_tick` climbs within each unit and `core.clock_anchors.anchor_index` within each
clock, so choosing by counts alone writes both plain: `anchor_index` 28x to 67x off its best,
`core.clock_anchors.t_tick` 30x to 32x, and the spike tables' `t_tick` 1.24x to 1.30x, 384 MB over
the best across both packets before any exception (2026-09-15; toolchain as above). The
`_tick` suffix, the `structural_index` and `sequence_position` roles and `assigned` identity mark
such columns. None states a distribution, so §2.7 stands, and a mark is wrong in places:
`core.unit_electrodes.channel_index` is a structural index cycling through 26 positions in every
unit.

### 2.10 A count sees repetition that a declaration cannot

Rules that each follow from a declaration leave 70 columns 1.15x or more off their best across the
two packets: a `free` string plain, an `open` or `closed` one a dictionary, a `data` integer plain,
and `session_id` plain. No declaration says how many rows share a value, and `session_id` wants
plain in a 12-row table and a dictionary in a million-row group. `core.spike_events.amplitude` and
`core.unit_quality_labels.confidence` are both floats: the first repeats and is 1.75x smaller under a
dictionary, and the second does not and is 1.47x larger (2026-09-15; toolchain as above).

### 2.11 The four rules leave 15 columns needing an exception

Columns 1.15x or more off their best in either packet (2026-09-15; toolchain as above):

| rules | columns | at 1.5x | at 2x |
|---|---:|---:|---:|
| sort-key heuristic, with its exceptions | 193 | 61 | 4 |
| declarations of type, role, identity and vocabulary | 70 | 20 | 4 |
| those, plus plain under 32 rows, or for one value under 50,000 rows | 34 | 12 | 4 |
| counts alone | 26 | 11 | 9 |
| Part 03 §5.5's, declared order then counts | 15 | 3 | 1 |

The count holds from 50 to 200 rows a run, from 32 to 50 rows a value, and at every one-value
threshold from 20,000 rows up, where bytes choose 50,000: at 500,000 the rules sit 913 kB over the
best against 304 kB. Thresholds fitted to either packet alone leave 13 on the other. Under the rules
and their exceptions every column of both packets lands within 1.15x of its best, 317 of 365 and 322
of 372 exactly at it, and 157 kB and 71 kB over the best in all. That 0.014% and 0.012% of each
packet is what the rules give up against writing each column three ways and keeping the smallest.

### 2.12 A sampled build encodes its spike tables for the rows it holds

`--sample 2000` keeps the first 2,000 spikes of each probe's stream, shrinking the two spike tables
and changing the values of `core.units`, and each packet then encodes 8 columns differently from its
full build (2026-09-15; toolchain as above). Seven take the encoding their sampled values
call for, within 1.04x of the best. `core.spike_events.amplitude` does not: each stream is one
2,000-row row group holding 97 and 128 distinct amplitudes, under 50 rows a value, so it is written
plain at 1.56x and 1.60x off its best. Every other column of both sampled packets lies within 1.15x
of its best, so a sampled packet is encoded for the rows it holds and does not preview the full
build's layout in the tables a sample shrinks.

## 3. Row groups

A large table's row groups are sized for analytical scans (Part 03 §5.1). **100,000 to 1,000,000
rows** is a starting point to be adjusted by profiling; it is a number this format fixes rather
than a rule a packet can fail, which is why Part 03 §5.1 keeps the SHOULD and the number is here.

Where a table declares a time bucket, a row group SHOULD start at each bucket boundary:
a group cut at a fixed row count straddles boundaries and spans two buckets' worth of time.

## 4. The object store

### 4.1 An endpoint plateaus at about 120 requests a second

Whatever the concurrency (2026-09-06; toolchain not kept). Twenty sessions of metadata
is therefore about a second, which is what makes a union across packets cheap enough that no
summary table is needed to avoid it.

### 4.2 One file beats a partitioned prefix on the engine that matters

The same rows staged to S3 four ways — a single file, a declared member list, the same members
reached by globbing, and hive layout — with the member arms at 682.2 MB against the single file's
681.6 MB (withdrawn 2026-09-02; toolchain not kept). DuckDB's single file wins every
query cold and warm. Where the member arms win, the gain reproduces at the same ratio on local
disk, so it is scan parallelism rather than skipped round trips.

The write side is the other way: a re-sorting rewrites the whole file where partitioning writes one
member. No session has yet had a second sorting.

<a id="ew-zarr-codec-floor-evidence" data-spec-anchor="canonical"></a>
## 5. The Zarr codec floor is version-specific

Measured in `conformance/zarr-probe/` against **zarr-python 3.4.0 with numcodecs 0.17.0, Zarr.jl
0.10.2 on Julia 1.12.7, TensorStore 0.1.85, zarrs-python 0.2.3 and zarrita 0.7.5 on Node 22.22.2**
(2026-09-24) — the one measurement here whose toolchain was kept, and the one that shows why the
others should be. Each reader checks the int64 element sum of arrays zarr-python and the reference
writer wrote; zarrs reads through a strict codec pipeline, so no read falls back to Python.

| stored v3 pipeline | zarr-python | Zarr.jl | TensorStore | zarrs | zarrita |
|---|---|---|---|---|---|
| `bytes`; `bytes`, `gzip`; `bytes`, `zstd` | reads | reads | reads | reads | reads |
| `bytes`, `blosc` (`zstd`), each of `noshuffle`, `shuffle`, `bitshuffle` | reads | reads | reads | reads | reads |
| `sharding_indexed` around each sequence of the first row and around `bytes`, `blosc` (`zstd`); index `bytes`, `crc32c`; at `end` | reads | reads | reads | reads | reads |
| `sharding_indexed` with index `bytes` alone, at `end` | reads | reads | reads | reads | reads |
| `sharding_indexed` with index at `start` | reads | reads | reads | reads | fails |
| `bytes`, `blosc` (`lz4`) | reads | reads | reads | reads | reads |
| the reference writer's `numcodecs.delta`, `bytes`, `blosc` (`zstd`) | reads | fails | fails | fails | reads |

All five also read Zarr v2 zstd and Blosc-Zstd. zarrita fails an index at `start` with
`RangeError [ERR_OUT_OF_RANGE]`; on the delta pipeline Zarr.jl reports that it does not support the
delta codec, TensorStore that `numcodecs.delta` is not registered, and zarrs that the metadata is
unsupported.

A reading of this kind stops being true the moment a library moves, with nothing in the prose
changing to show it. That is what Part 03 §6.4's per-version reader floor exists to state as a rule,
and what this table exists to explain.

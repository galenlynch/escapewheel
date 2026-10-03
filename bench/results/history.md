# Measurement history

Every reading quoted in the repository, newest first within each question. A row records the date
it was taken, what it was taken on, and the script that produced it. Where that script is gone,
the row says why. A reading against an older packet shape is kept for its date, not for its
currency. Before 2026-10-02 no toolchain was recorded. The 2026-10-02 JSON records a
dirty `786d6d7c`, or `517d9316` for the rerun: the scripts ran uncommitted, as `517d9316` commits
them. The core 0.18.0 runs record a dirty `c0f9214b`, for the same reason: the S3 arm and the
region operation were committed after they ran.

"Rotational" is a Toshiba MG09 SATA disk under ntfs-3g. There a cold read is approximate: eviction
does not reach the block device's buffer cache. "NVMe" is a WD SN850X under btrfs, where a cold
read is checked by `mincore`.

## A core 0.18.0 packet against its NWB, local and S3

Both sessions were rebuilt on 2026-10-02 at core 0.18.0 as `packet-r164` and read with the same
toolchain as the core 0.14.0 rows below. Each cell is the cold median of three in seconds. Other
work kept the host's load average between 3 and 10 on 24 threads throughout; each JSON records it.
The local cells are from the reruns, `*-r164-rerun.json`. The first 776259 run overlapped another
build on the same machine. The 786867 run agreed with its rerun to within 0.37 s in every cell.

On the NVMe:

| session | operation | packet, PyArrow | packet, DuckDB | pynwb | lazynwb |
|---|---|---|---|---|---|
| 776259 | open | 0.001 | 0.015 | 0.313 | 0.011 |
| 776259 | units, five columns | 0.003 | 0.016 | 0.345 | 0.032 |
| 776259 | units, all metadata | 0.018 | 0.032 | 0.427 | 0.123 |
| 776259 | trials | 0.006 | 0.027 | 0.395 | 0.103 |
| 776259 | every spike | 41.398 | 0.135 | 19.674 | 38.354 |
| 776259 | 10 s window | 0.063 | 0.063 | 22.226 | 22.049 |
| 776259 | one train | 0.197 | 0.031 | 0.348 | 0.199 |
| 776259 | units in MD with their trains | 0.231 | 0.092 | 1.137 | 2.127 |
| 786867 | open | 0.001 | 0.015 | 0.320 | 0.010 |
| 786867 | units, five columns | 0.003 | 0.016 | 0.329 | 0.032 |
| 786867 | units, all metadata | 0.008 | 0.030 | 0.373 | 0.112 |
| 786867 | trials | 0.005 | 0.025 | 0.372 | 0.101 |
| 786867 | every spike | 0.320 | 0.074 | 0.669 | 8.701 |
| 786867 | 10 s window | 0.041 | 0.040 | 0.772 | 9.051 |
| 786867 | one train | 0.080 | 0.024 | 0.330 | 0.093 |
| 786867 | units in MD with their trains | 0.119 | 0.055 | 0.610 | 0.412 |

From S3, with the megabytes the host received during the cell in parentheses. The packets and
NWB-Zarr copies are under `s3://aind-scratch-data/galen.lynch/nwb-lake-bench/r164/` in us-west-2,
read from an on-premises workstation over a 1 Gbit/s link, not from inside AWS. The lazynwb column
was measured an hour after the others, at a load average near 4, because its first run failed on
the NWB's name (see `README.md`).

| session | operation | packet, PyArrow | packet, DuckDB | pynwb | lazynwb |
|---|---|---|---|---|---|
| 776259 | open | 0.17 (0.0) | 0.54 (0.1) | 40.62 (4.1) | 0.40 (0.3) |
| 776259 | units, five columns | 0.28 (0.1) | 0.62 (0.1) | 39.91 (4.2) | 0.83 (0.7) |
| 776259 | units, all metadata | 0.46 (0.8) | 0.85 (0.8) | 44.16 (7.8) | 3.97 (3.6) |
| 776259 | trials | 0.41 (0.2) | 0.82 (0.2) | 46.63 (4.3) | 3.73 (0.8) |
| 776259 | every spike | 43.39 (484) | 4.87 (485) | 87.59 (1,177) | 246.20 (2,317) |
| 776259 | 10 s window | 0.71 (19.0) | 0.91 (17.7) | 99.24 (1,177) | 223.00 (2,322) |
| 776259 | one train | 1.57 (3.0) | 0.70 (3.3) | 38.11 (11.8) | 1.26 (7.6) |
| 776259 | units in MD with their trains | 4.04 (2.0) | 1.21 (0.9) | 122.18 (632) | 12.80 (194) |
| 786867 | open | 0.17 (0.0) | 0.57 (0.1) | 40.30 (3.9) | 0.40 (0.3) |
| 786867 | units, five columns | 0.28 (0.1) | 0.57 (0.1) | 38.65 (3.9) | 0.84 (0.7) |
| 786867 | units, all metadata | 0.50 (0.6) | 0.93 (0.6) | 43.77 (5.8) | 4.12 (2.5) |
| 786867 | trials | 0.61 (0.1) | 0.77 (0.2) | 47.04 (4.0) | 3.82 (0.7) |
| 786867 | every spike | 44.57 (239) | 2.69 (240) | 74.91 (560) | 118.81 (625) |
| 786867 | 10 s window | 0.62 (19.0) | 0.88 (18.6) | 44.17 (559) | 114.04 (607) |
| 786867 | one train | 1.27 (1.8) | 0.68 (1.7) | 36.31 (6.7) | 0.92 (3.5) |
| 786867 | units in MD with their trains | 2.35 (1.0) | 1.13 (0.5) | 61.25 (182) | 2.19 (26.9) |

The readers agreed on every count, with the two-spike window difference on 786867 described
below. On units in MD they differ by design: the packet counts a unit with any electrode in the
region, 466 and 164 units, while the NWBs give 409 and 140, through the units table's own
`location` for 776259 and through each unit's electrodes for 786867.

Over S3 the packet's DuckDB path answered every question in under 5 s. Its PyArrow path fetched
the same 485 MB for every spike as DuckDB and took 43 s instead of 4.9 s, the whole-column read
described below. pynwb took about 40 s to open either NWB from S3, against 0.3 s locally and 6.2 s
on 2026-09-05; why was not investigated.

Locally, the packet's PyArrow path read every spike of 786867 in 0.32 s and of 776259 in 41 s, so
the whole-column slowdown does not scale with the table's size alone. On the core 0.14.0 packet
of 786867, the same cell took 16.8 s and pynwb took 11.4 s, against 0.67 s now from the same NWB.
That difference is not explained either.

## A packet against its NWB

Each cell is in seconds, with the process's peak RSS in MiB where it was kept. "Cold" means one
process per cell after eviction. The 2026-10-02 cells are the median of three, taken against core
0.14.0 packets with the reader at 0.1.0, DuckDB 1.5.6, PyArrow 25.0.1, pynwb 4.2.0, hdmf-zarr
0.14.0 and lazynwb 1.0.0.dev5, on an i9-12900K. Their JSON is beside this file. Before 2026-10-02 a
cell's timing included importing the reader's modules.

| date | session, store | operation | packet, PyArrow | packet, DuckDB | pynwb | lazynwb | source |
|---|---|---|---|---|---|---|---|
| 2026-10-02 | 776259, NVMe, cold | open | 0.001 (167) | 0.015 (167) | 0.657 (193) | 0.010 (186) | `readers.py` |
| 2026-10-02 | 776259, NVMe, cold | units, five columns | 0.003 (167) | 0.016 (167) | 1.158 (196) | 0.038 (202) | `readers.py` |
| 2026-10-02 | 776259, NVMe, cold | units, all metadata | 0.008 (169) | 0.031 (170) | 1.060 (196) | 0.232 (208) | `readers.py` |
| 2026-10-02 | 776259, NVMe, cold | trials | 0.006 (167) | 0.040 (167) | 0.668 (195) | 0.117 (201) | `readers.py` |
| 2026-10-02 | 776259, NVMe, cold | every spike | 30.673 (3,041) | 0.133 (239) | 25.393 (2,416) | 23.808 (17,772) | `readers.py` |
| 2026-10-02 | 776259, NVMe, cold | 10 s window | 0.063 (291) | 0.061 (191) | 22.831 (3,240) | 21.180 (17,781) | `readers.py` |
| 2026-10-02 | 776259, NVMe, cold | one train | 0.199 (391) | 0.029 (195) | 0.481 (200) | 0.202 (463) | `readers.py` |
| 2026-10-02 | 786867, NVMe, cold | open | 0.001 (168) | 0.015 (168) | 0.315 (184) | 0.010 (186) | `readers.py` |
| 2026-10-02 | 786867, NVMe, cold | units, five columns | 0.004 (168) | 0.015 (168) | 0.353 (183) | 0.031 (200) | `readers.py` |
| 2026-10-02 | 786867, NVMe, cold | units, all metadata | 0.008 (174) | 0.031 (168) | 0.400 (182) | 0.114 (205) | `readers.py` |
| 2026-10-02 | 786867, NVMe, cold | trials | 0.005 (168) | 0.027 (168) | 0.365 (180) | 0.108 (201) | `readers.py` |
| 2026-10-02 | 786867, NVMe, cold | every spike | 16.754 (1,468) | 0.077 (203) | 11.406 (1,219) | 22.571 (8,400) | `readers.py` |
| 2026-10-02 | 786867, NVMe, cold | 10 s window | 0.042 (283) | 0.041 (183) | 16.541 (1,599) | 14.548 (7,973) | `readers.py` |
| 2026-10-02 | 786867, NVMe, cold | one train | 0.078 (233) | 0.023 (174) | 0.334 (183) | 0.091 (279) | `readers.py` |
| 2026-09-05 | 776259, S3, cold | open | | 0.46 (123) | 6.21 (196) | 12.21 (193) | `bench8.py`, removed |
| 2026-09-05 | 776259, S3, cold | units, five columns | | 4.00 (200) | 6.03 (196) | 23.27 (205) | `bench8.py`, removed |
| 2026-09-05 | 776259, S3, cold | every spike | | 8.43 (757) | 26.74 (3,468) | 73.96 (24,929) | `bench8.py`, removed |
| 2026-09-05 | 776259, S3, cold | 10 s window | | 4.34 (271) | 25.50 (4,221) | 79.57 (24,674) | `bench8.py`, removed |
| 2026-09-05 | 776259, S3, cold | one train | | 4.49 (210) | 6.21 (196) | 52.17 (3,516) | `bench8.py`, removed |
| 2026-09-05 | 786867, S3, cold | every spike | | 6.29 (506) | 15.43 (1,272) | 35.90 (8,393) | `bench8.py`, removed; the NWB held another sorting |
| 2026-09-05 | 776259 and 786867, S3, cold | units in MD with their trains | | 5.47 (559) | 99.60 (205) | failed | `bench11.py`, removed; 458 units against pynwb's 409 |
| 2026-09-03 | 786867, local | 10 s window, all units | 0.025, engine not kept | | 7.719, per unit | | not kept; quoted in Part 10 §6 |

The 776259 rows for all metadata and every spike through the packet come from a rerun on a quiet
machine, `2026-10-02-readers-776259-rerun.json`. The first run's cells for them overlapped another
process and read 1.536 s and 38.436 s.

The readers agreed on every count. The one exception is the 10 s window on 786867: 294,526 spikes
from the packet against 294,524 from the NWB, where the window's edges are rounded to the NWB's
float seconds. "Every spike" sums ticks in the packet and seconds in the NWB, so its values differ
by design.

**The packet's PyArrow path reads a whole column slower than the NWB readers.** `Packet.table`
calls `pyarrow.parquet.read_table` with `pre_buffer` at its default of true. On this file and disk
that took 19–38 s warm for `core.spike_events.t_tick` of 776259, against 0.4–1.9 s with
`pre_buffer=False`, 1.0 s reading the row groups one at a time, and 0.35 s fetching the column
through DuckDB. A narrow read prunes to a few row groups and is unaffected.

On every spike in the 2026-09-05 S3 run, the packet, pynwb and lazynwb fetched 486 MB, 1,174 MB
and 1,177 MB. Those S3 copies, in the packet shape of that date, are no longer under the prefix;
the core 0.18.0 S3 readings are in the section above.

Spelling matters as much as format. Warm on 776259, 2026-09-04, from `bench4.py` and `bench5.py`,
both removed:

- pynwb reading per unit took 3.01 s, against 0.72 s from the flat `spike_times` dataset.
- The reader scanning a column and filtering in memory took 0.42 s, against 0.09 s with the
  predicate pushed into DuckDB.

lazynwb's purpose-built calls were slower than the generic spelling over S3 on 2026-09-05
(`lazycheck.py`, removed):

| call | spelling | time (s) |
|---|---|---|
| unit metadata | `select` | 15.52 |
| unit metadata | `exclude_array_columns=True` | 25.80 |
| one train | `filter().select()` | 52.92 |
| one train | `merge_array_column` | 82.32 |

## The PyArrow and DuckDB paths over S3

776259, cold, 2026-09-05 (`bench10.py`, removed):

| operation | PyArrow (s) | DuckDB (s) |
|---|---|---|
| open | 1.11 | 1.27 |
| units, five columns | 0.81 | 0.81 |
| 10 s window | 1.21 | 1.33 |
| one train | 1.40 | 3.24 |

## Row-group size

`analysis.spike_events` of 776259. The 2026-10-02 rows are cold, from `row_groups.py`, the median
of three, with the toolchain of the section above. "As stored" is the writer's own cut: 131,072
rows a group and a new group at each time bucket, 2,197 groups in 494 MB. The other copies keep its
order, codec and encodings and cut only at the row count. The window is one second, 42,826 spikes;
the unit is the largest, 1,789,113 spikes. Each cell is in seconds.

| date | disk | rows per group | groups | window, PyArrow | window, DuckDB | one unit, PyArrow | one unit, DuckDB |
|---|---|---|---|---|---|---|---|
| 2026-10-02 | S3 | as stored | 2,197 | 0.615 | 0.589 | 0.619 | 0.349 |
| 2026-10-02 | S3 | 131,072 | 2,189 | 0.627 | 0.623 | 0.763 | 0.381 |
| 2026-10-02 | S3 | 1,048,576 | 274 | 0.756 | 0.501 | 1.307 | 0.286 |
| 2026-10-02 | S3 | 4,194,304 | 69 | 0.594 | 0.390 | 2.677 | 0.299 |
| 2026-10-02 | NVMe, core 0.18.0 | as stored | 2,197 | 0.059 | 0.041 | 0.054 | 0.039 |
| 2026-10-02 | NVMe, core 0.18.0 | 131,072 | 2,189 | 0.059 | 0.040 | 0.057 | 0.038 |
| 2026-10-02 | NVMe, core 0.18.0 | 1,048,576 | 274 | 0.035 | 0.081 | 0.121 | 0.051 |
| 2026-10-02 | NVMe, core 0.18.0 | 4,194,304 | 69 | 0.058 | 0.052 | 0.308 | 0.046 |
| 2026-10-02 | NVMe | as stored | 2,197 | 0.106 | 0.038 | 0.085 | 0.034 |
| 2026-10-02 | NVMe | 131,072 | 2,189 | 0.057 | 0.032 | 0.054 | 0.031 |
| 2026-10-02 | NVMe | 1,048,576 | 274 | 0.033 | 0.015 | 0.065 | 0.015 |
| 2026-10-02 | NVMe | 4,194,304 | 69 | 0.045 | 0.017 | 0.233 | 0.056 |
| 2026-08-29 | rotational | 1 M | | 1.93, engine not kept | | | |
| 2026-08-29 | rotational | 4 M | | 4.42, engine not kept | | | |

The S3 and core 0.18.0 rows read `packet-r164` of 776259, whose table has the same 2,197 groups;
from S3 the rewritten copies were uploaded beside it. From S3, DuckDB was fastest at four million
rows for the window, 0.390 s against 0.589 s as stored, and at a million rows for one unit, 0.286 s
against 0.349 s. PyArrow's one-unit read slowed as the groups grew, from 0.619 s as stored to
2.677 s at four million rows, and its window read was within 0.16 s at every size. No size was
fastest for every engine and query; the writer's cut was within 0.2 s of the fastest in every S3
cell. The 2026-08-29 rows are quoted in the writer's performance guide; their script was not kept.
On the NVMe every cell is under a quarter of a second. Through DuckDB a million rows was the fastest
of the four for both queries. Through PyArrow it was the fastest for the window, and 131,072 rows
was the fastest for one unit, by 0.011 s.

## Sort order of `core.spike_events`

776259, warm, 2026-09-05 (`sortbench.py`, removed). The table then carried `sorting_run_id` and
`curation_id` in its key, and the profile placed `unit_id` after them:

| order | MB | one unit | one probe's units | one unit across runs | count by run |
|---|---|---|---|---|---|
| profile order (session, run, curation, unit, tick) | 677 | 0.008 s | 0.004 s | 0.014 s | 0.220 s |
| key order (session, unit, run, curation, tick) | 879 | 0.007 s | 0.050 s | 0.004 s | 0.161 s |

## Containment of a trial in a block

Median of five, DuckDB at four threads. Each cell is in milliseconds.

| date | trials | blocks | range join | ASOF join | searchsorted | stored key | source |
|---|---|---|---|---|---|---|---|
| 2026-10-02, second run | 708 | 18 | 1.66 | 1.89 | 0.01 | 0.60 | `containment.py` |
| 2026-10-02, second run | 10,000 | 250 | 4.78 | 29.81 | 0.08 | 0.64 | `containment.py` |
| 2026-10-02, second run | 100,000 | 2,500 | 280.85 | 1,578.89 | 1.20 | 1.67 | `containment.py` |
| 2026-10-02, second run | 1,000,000 | 25,000 | 30,616.86 | 164,606.37 | 21.19 | 11.98 | `containment.py` |
| 2026-10-02 | 708 | 18 | 2.51 | 3.41 | 0.05 | 1.66 | `containment.py` |
| 2026-10-02 | 10,000 | 250 | 6.43 | 43.42 | 0.19 | 1.67 | `containment.py` |
| 2026-10-02 | 100,000 | 2,500 | 750.62 | 2,543.76 | 1.21 | 1.79 | `containment.py` |
| 2026-10-02 | 1,000,000 | 25,000 | 22,800.62 | 150,691.54 | 24.10 | 11.86 | `containment.py` |
| 2026-09-02 | 708 | 18 | 1.46 | 1.54 | 0.02 | 0.60 | `nesting/join.py`, now `containment.py` |
| 2026-09-02 | 10,000 | 250 | 5.58 | 32.70 | 0.07 | 1.00 | `nesting/join.py`, now `containment.py` |
| 2026-09-02 | 100,000 | 2,500 | 267.68 | 2,202.66 | 1.02 | 3.05 | `nesting/join.py`, now `containment.py` |
| 2026-09-02 | 1,000,000 | 25,000 | 21,708.92 | 219,594.04 | 15.95 | 32.21 | `nesting/join.py`, now `containment.py` |

The 2026-09-02 arms returned a row count and joined on string keys. The current script returns
one integer key per trial from every arm. Under both, the ASOF join is slower than the range join
at every scale, 6.6× at a million trials on 2026-10-02. A binary search over the blocks stays
within 13 ms of reading a stored key up to a million trials.

## Building and validating a packet

| date | session, disk | what | time | source |
|---|---|---|---|---|
| 2026-10-02 | 776259, rotational | `escapewheel import` of a 57-resource packet, core 0.18.0 | 806.8 s: sources 515.0, staging 227.7, derive 48.9, validate 15.2, promote 0.0 | the packet's build log |
| 2026-10-02 | 786867, rotational | `escapewheel import` of a 58-resource packet with video, core 0.18.0 | 587.8 s: sources 404.6, staging 145.0, derive 28.5, validate 9.7, promote 0.0 | the packet's build log |
| 2026-09-30 | 776259, rotational | `escapewheel import` of a 57-resource packet, core 0.14.0 | 630.1 s: sources 431.7, staging 146.6, derive 41.4, validate 9.5, promote 0.9 | the packet's build log |
| 2026-08-30 | 776259, rotational | `escapewheel import` of a 23-resource packet | 105.1 s: sources 9.5, core 50.5, analysis 32.7, validate 12.5 | not kept; quoted in the writer's performance guide |
| 2026-08-30 | 776259, rotational | `--sample 200000` import | 8.7 s | not kept; quoted in the writer's performance guide |

The 2026-09-30 sources include the waveforms (217.5 s) and the unit QC metrics (62.6 s). The
2026-08-30 import read neither, so the two totals are not comparable. The 2026-10-02 776259 build
spent 215.8 s in the sorter source, 217.2 s in the waveforms and 62.1 s in the unit QC metrics, at a
load average near 12 from unrelated work; the 2026-09-30 load was not recorded.

## Listing and downloading a stored session

Cold, 2026-10-02, from `stores.py`: one listing of each root by its own prefix, then a download
with `s5cmd` at 64 workers to the NVMe, over the same 1 Gbit/s link as above.

| root | list (s) | objects | GB | download (s) | MB/s |
|---|---|---|---|---|---|
| 776259 packet, core 0.18.0 | 0.19 | 55 | 1.220 | 11.72 | 104.0 |
| 776259 NWB-Zarr | 0.66 | 6,519 | 8.494 | 73.38 | 115.8 |
| 786867 packet, core 0.18.0 | 0.07 | 53 | 0.605 | 7.50 | 80.6 |
| 786867 NWB-Zarr | 0.56 | 4,809 | 4.736 | 42.25 | 112.1 |

Both downloads ran near the link's limit, so these say what a 1 Gbit/s host pays, not what S3
can serve inside its region.

The validator readings below were removed from its docstrings on 2026-10-01, and none has been
taken again. Each date is that of the commit that first quoted it:

| date | what | reading |
|---|---|---|
| 2026-08-28 | `core.spike_events.primary_key_unique` over 247,758,402 spikes, memory-bounded | 78 s at 4.0 GB peak |
| 2026-08-29 | the same uniqueness as a `GROUP BY` over 287 M spikes | spills 26 GB, 31× the packet |
| 2026-09-02 | establishing every digest of one session's 6.8 GB of LFP | 75 s local, 88 s S3 |
| 2026-09-02 | one LFP array of 208 objects from S3 | 15.7 MB/s sequential, 94 MB/s across eight |
| 2026-09-24 | digesting a packet's own 1,209 MB | 0.60 s |
| 2026-09-02 | store-digest comparison | 1.31 s, the cost of the listing |

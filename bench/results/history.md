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

## The lazy reader's final configuration, against the NWB readers

`readers.py`, `trials.py` and `lazy.py` on 2026-10-03, against the `packet-r164` packets of the
section on core 0.18.0, from the NVMe and from S3 read unsigned. Cold medians of three. The tables
are in [`../SUMMARY.md`](../SUMMARY.md), built from these files:

- `*-readers-<session>-r164[-s3]-final.json` and `*-trials-<session>-r164[-s3]-final.json`: the
  packet arms, at commits from `c69f7e68` to `c87fe92d`, all with the reader's read path of
  `c69f7e68`. The pynwb and lazynwb cells are the 2026-10-02 and earlier 2026-10-03 runs above.
- `*-readers-<session>-r164[-s3]-region.json` and `*-lazy-<session>-r164[-s3]-good.json`: the
  ten-second window through `spike_times`, the units in MD and `good region window`, rerun at
  `b3843f9d`, after `where` guarded a long membership test with value ranges. At `3bcc0c7f`, which
  split the test into `is_in` tests of 50 values instead, the window through `spike_times` took
  2.18 s locally and 3.18 s from S3 on 776259, against 0.089 s and 1.15 s before it; those runs
  were not kept.
- `*-lazy-<session>-r164[-s3].json`: the other lazy operations, at `42ae6f0a` locally and `c87fe92d`
  from S3. The local file also holds an earlier `region window` operation, superseded by
  `good region window`.
- `*-readers-<session>-r164[-s3]-list*.json`: listing, at `84915050` to `357151f7`; the 776259 local
  packet cells are from `-list-packet.json`, after the first run's eviction check failed.
- `*-before-lazy.json`: `spike_times` through the reader at `fa060640`, for the "before" column.
- `*-readers-*-lazy.json`, `*-trials-*-lazy.json` and `*-s3-polars-lazy.json`: the same packet arms
  at `38097644` to `84915050`, after the lazy reader and before the eager cache and the alignment
  changes; superseded by `-final.json`.

The load average was between 1 and 10 on 24 threads; each file records it. An `aligned_spikes` S3
cell of 801 MB taken earlier the same day overlapped other S3 traffic from the host and is not
used: alone, the cell received 522 MB against DuckDB's 520.

## What a reader function returns: the clock mapping as a relation

`lazy_spike.py` on 2026-10-03, 776259 `packet-r164` from the NVMe, at a dirty `3cd086d4` whose
uncommitted change is the script; load average 8 to 11 on 24 threads from other work. Each cell is
one run in its own process under a 60 GiB cap, cold after eviction; a warm rerun of every local
cell was within 0.2 s and is in the JSON (`2026-10-03-lazy-spike-776259-r164.json`, the Narwhals
DuckDB arm from `*-narwhals.json`). DuckDB 1.5.6, Polars 1.44.2, Narwhals 2.26.0, PyArrow 25.0.1.
Seconds, then peak RSS in MiB.

**The mapping is relational, exactly.** Every spike of `core.spike_events`, 286,896,563 on 12 probe
clocks with about 6,387 anchors each, was mapped onto the 31,250 Hz harp clock by an ASOF join of
spike to preceding anchor with the next anchor alongside, then `p0 + (p1 - p0) / (t1 - t0) *
(t - t0)` in doubles, as NumPy's `interp` evaluates it, rounded half to even. Beyond the ends it is
`p_end + rint(slope * (t - t_end))` with `clocks.rate`'s slope; a row is placed where its distance
to the nearer anchor is within the bound times the median interval. Each arm's output was dumped by
stored row and compared with `clocks.mapped` on every row:

| arm | seconds (MiB) | rows differing from the kernel |
|---|---|---|
| `clocks.mapped` over the whole column (reference) | 5.15 (17,292) | |
| `spike_times(units=every unit)` | 5.07 (13,605) | 0 |
| DuckDB ASOF join, rate and span from the reader | 12.25 (23,039) | 0 |
| DuckDB ASOF join, rate and span fitted in SQL | 12.17 (23,251) | 0 |
| DuckDB ASOF join with `round` in place of `round_even` | 11.65 (24,256) | 2,792,142, each by one tick |
| DuckDB, to a count and sum only | 8.34 (10,962) | sums equal |
| Polars `join_asof`, after sorting the spikes by tick | 14.23 (19,505) | 0 |
| Polars `search_sorted` on a (clock, tick) key, no sort | 16.41 (12,786) | 0 |
| Polars `search_sorted`, to a count and sum only | 13.20 (7,139) | sums equal |
| Narwhals over DuckDB | 13.57 (21,721) | 0 |
| Narwhals over Polars | 18.75 (24,413) | 0 |

The packet declares a bound of 2 and every spike is placed at it, so the mapping arms were rerun at
bound 0.5, where 36,139 spikes before the first anchors go unplaced, and at 0.1, where 229,484,782
inside the anchor span do (`*-bound-0.5.json`, `*-bound-0.1.json`). No arm differed from the kernel
on any row at either bound, in tick or in placement. Rounding is the one trap: 5,583,095 spikes
interpolate to exactly half a tick, and SQL's `round`, half away from zero, moves about half of
them. DuckDB's `round_even` and Polars' `round(mode="half_to_even")` match `np.rint`; Narwhals'
`round` takes no mode and rounds as its backend does, so its arms round by `floor` and a tie test.
A rate and span fitted in SQL from `core.clock_anchors` alone changed no row on this packet, though
SQL's summation order is not NumPy's, so equality there is measured, not guaranteed. Every clock
here is one hop from the reference; a chain is the same join once per edge, not measured.

Narwhals needed three workarounds: no rounding mode; its DuckDB `join_asof` queries through
DuckDB's default connection, so a relation from any other connection is refused; and it keeps the
right-hand join key on Polars but drops it on DuckDB. Its PyArrow backend has no `join_asof`.

**The go-cue analysis**, `trials.py`'s spikes within [-1, +2] s of each of 708 cues, from
`core.spike_events` mapped on the way. Every arm found 99,453,482 pairs over 6,774 units, a sum of
squared per-unit pairs of 9,120,651,850,060 and 1,514,726,240,589 summed ticks from cue, the
figures the section below found from `analysis.spike_events`. S3 is the packet under the prefix
named below, read unsigned over the same 1 Gbit/s link at load average 6 to 10
(`*-r164-s3.json`); every S3 cell received 483 to 528 MB.

| arm | NVMe | S3 |
|---|---|---|
| `spike_times` into a `pa.Table`, then the streaming Polars window plan | 15.72 (17,503) | 30.41 (17,061) |
| DuckDB: the lazy mapping, then the ASOF join to cues | 14.03 (30,876) | 19.33 (31,104) |
| Polars: the lazy mapping, then the same window plan | 23.21 (9,394) | 28.12 (9,391) |
| `Packet.scanner(...).to_reader()`, each batch through `clocks.mapped`, summed per unit | 16.26 (963) | 16.32 (926) |

The stream held 0.9 GiB where the eager table held 17 and DuckDB 30, in about the same time
locally and the least time from S3.

Correction: the DuckDB arm's 30 GiB measures one unsliced ASOF join, not a lazy relation. It mapped
stored ticks in SQL and then sorted every spike for the join, where `aligned_spikes` reads
`analysis.spike_events`, already mapped. The same join over `analysis.spike_events` took 6.06 s at
21 GiB (the section below), and over 16 time slices run one at a time 6.9 s at 2.0 GiB with the
same counts (the reader's README, "Joining spikes to events in SQL"). Neither engine pushed anything from the window into the
spike scan: DuckDB's plan projects `t_tick` and filters nothing, and Polars' scan carries no
selection. The window is on the mapped tick, which the file does not hold.

**A range on the reference clock**: 60 s from 1,800 s after the origin, 2,468,375 spikes in every
arm.

| arm | seconds (MiB) |
|---|---|
| `spike_times(units=..., t_tick=...)`, widened by `stored_span` and pushed | 4.09 (10,836) |
| DuckDB, the range after the lazy mapping | 8.41 (10,807) |
| DuckDB, the same with the widened stored range added to the scan by hand | 6.24 (9,110) |
| Polars, the range after the lazy mapping | 13.19 (7,437) |
| `analysis.spike_events` read by range | 0.07 (353) |

No engine pruned on its own: the range is on a computed column, and neither plan put a predicate
on the scan. Given the stored range by hand, DuckDB pushed it, but it could not prune either.
`stored_span` widens to the union over clocks, here probe ticks from 53,965,808 to the harp clock's
361,804,256,862, and `core.spike_events` is ordered by unit, so each of its 293 row groups spans
nearly the whole session; all 293 overlap the widened range. A time range on this table reads
everything whatever returns it. `analysis.spike_events`, stored on the reference clock by time
bucket, answered in 0.07 s.

**What each contract would cost the reader.** The operations that touch a tick are the mapping,
seconds, `attach_clocks`, the range filter with its widening, and each accessor's filters:

| contract | implementations of each | DuckDB required |
|---|---|---|
| eager `pa.Table` | one, NumPy and PyArrow; filters are accessor arguments | no |
| `RecordBatchReader` | the same one applied per batch; filters are accessor arguments | no |
| DuckDB relation | a SQL one, plus the PyArrow one that reading without DuckDB keeps, and a test that they agree; the widening stays the reader's | yes, for that path |
| Polars `LazyFrame` | as DuckDB, with Polars in place of SQL | Polars instead |
| Narwhals over both | one expression set for DuckDB and Polars, plus the PyArrow one, since its PyArrow backend has no ASOF join | one of the two |

`CONTRIBUTING.md` requires a complete PyArrow read path, so every lazy contract doubles the time
operations. The spike's SQL mapping is about 25 lines and the Polars one about 60, against about
120 for the kernel, `_Map` and `mapped`.

**Recommendation: keep the eager `pa.Table` and add a streaming form, not a lazy relation.** The
relational mapping matches the kernel on every row, so exactness does not decide it. What does:

- A lazy relation buys pushdown, and here there is none to buy. A filter on the mapped tick
  reaches no scan in either engine, so the reader would still own the widening and the pushdown,
  which is what accessor arguments are.
- Materialised, the relational mapping took 2.4 to 3.6 times the kernel's 5.15 s, at 0.7 to 1.4
  times its memory. Its one advantage is aggregating without materialising, and the stream has it
  too: 0.9 GiB for the go-cue analysis, against 31 GiB for DuckDB's unsliced join and 2.0 GiB
  sliced.
- It doubles every time operation and makes DuckDB or Polars part of reading.

A `RecordBatchReader` keeps one implementation, needs no engine, bounds memory, and was fastest
from S3. It is single pass and cannot be filtered after the fact, so it complements the table for
whole-session reads rather than replacing it. A caller who wants a relation over reference-clock
spikes already has one: `analysis.spike_events` through `Packet.duckdb` or `scan_polars`, mapped
at write time by the same kernel.

## Packet spike arms from `analysis.spike_events`

`trials.py` on 2026-10-03, go-cue spikes on 776259 from the NVMe, one cold run per cell, at a
dirty `d4b230ed` whose uncommitted change is these arms; load average 4 to 8 on 24 threads
(`2026-10-03-trials-776259-r164-analysis.json`). The packet's pandas arms now read
`analysis.spike_events`, already on the reference clock, in place of mapping `core.spike_events`
themselves, and its DuckDB arm states the ASOF join. Seconds, then peak RSS in MiB:

| arm | 776259, NVMe |
|---|---|
| packet pandas | 14.91 (25,479) |
| packet pandas, needed columns | 14.30 (18,899) |
| packet duckdb, ASOF join | 6.06 (21,376) |
| packet aligned_spikes | 7.94 (17,459) |
| pynwb pandas | 24.23 (20,403) |

Every packet arm found 99,453,482 pairs and pynwb 99,452,477, the edge-tick gap explained below.
DuckDB's range join, the arm's form in the section below, took 46.2 s in a separate run, nearly
all of it in a piecewise merge join; the ASOF join answers the same question in one sorted pass but
holds 21 GiB where the range join held 0.4. Of the pandas arms' time, 8.5 s is the shared analysis's
`window_sums` and 2.4 s its `np.unique` over unit IDs, which `analysis.spike_events` stores by
time bucket and then unit (Part 03 §5.4); NWB's spikes, flattened unit by unit, sort in 0.9 s.

## Trial analyses, local and S3

`trials.py` on 2026-10-03, against the core 0.18.0 packets and NWB-Zarr copies of the section
below, at `fa060640` with the script uncommitted. Two analyses: lick latency, the first lick after
each go cue and before the next; and go-cue spikes, every unit's spikes within [-1, +2] s of each
go cue. Each cell is seconds, then peak RSS in MiB, then for S3 the megabytes received. A cell is
the cold median of three, except the six S3 cells marked *, which are one run each
(`--once-above 300`). The needed-columns arm was added after the local runs, so its local cells
are a separate run, `*-r164-columns.json`. The local runs overlapped other work on the host, with
the load average between 1 and 14 on 24 threads; the S3 runs were at 1 to 3.

Lick latency:

| arm | 776259, NVMe | 776259, S3 | 786867, NVMe | 786867, S3 |
|---|---|---|---|---|
| packet pandas | 0.014 (173) | 1.26 (203; 0.2) | 0.014 (174) | 1.44 (203; 0.2) |
| packet pandas, needed columns | 0.013 (174) | 1.29 (203; 0.2) | 0.013 (173) | 1.24 (203; 0.2) |
| pynwb pandas | 0.609 (197) | 53.09 (225; 4.1) | 0.841 (184) | 47.80 (212; 3.9) |
| lazynwb pandas | 0.114 (205) | 4.45 (261; 0.8) | 0.225 (204) | 4.54 (261; 0.8) |
| packet polars | 0.009 (182) | 0.42 (210; 0.1) | 0.009 (183) | 0.42 (209; 0.1) |
| packet dataset | 0.006 (173) | 0.67 (203; 0.2) | 0.006 (174) | 0.64 (203; 0.2) |
| packet dataset, read_pool | 0.006 (173) | 0.63 (203; 0.2) | 0.005 (174) | 0.59 (203; 0.2) |
| lazynwb polars | 0.045 (211) | 0.61 (251; 0.3) | 0.047 (213) | 0.60 (251; 0.3) |
| packet duckdb | 0.024 (173) | 0.91 (210; 0.2) | 0.025 (174) | 1.04 (210; 0.2) |
| lazynwb sql | 0.123 (251) | 1.21 (292; 0.4) | 0.259 (264) | 1.39 (302; 0.4) |
| pynwb duckdb | 0.380 (228) | 50.74 (258; 4.2) | 0.544 (218) | 47.50 (247; 4.0) |

Go-cue spikes:

| arm | 776259, NVMe | 776259, S3 | 786867, NVMe | 786867, S3 |
|---|---|---|---|---|
| packet pandas | 64.37 (32,170) | 54.17 (33,163; 708) | 20.45 (18,904) | 26.56 (19,415; 359) |
| packet pandas, needed columns | 35.20 (24,883) | 50.21 (24,876; 485) | 15.74 (15,049) | 23.49 (15,058; 241) |
| packet pandas-derived | 16.28 (25,475) | 29.35 (25,489; 516) | 6.53 (14,234) | 13.23 (14,244; 256) |
| pynwb pandas | 24.73 (20,404) | 1,937.86* (20,402; 1,852) | 16.08 (9,599) | 1,326.58* (9,592; 951) |
| lazynwb pandas | 65.31 (63,228) | 293.15 (63,476; 2,568) | 32.50 (35,142) | 158.96 (35,450; 827) |
| packet polars | 10.27 (7,916) | 15.57 (7,961; 516) | 4.31 (3,741) | 7.89 (3,788; 257) |
| packet dataset | 10.46 (7,265) | 11.67 (6,487; 519) | 4.51 (4,134) | 6.79 (3,282; 258) |
| packet dataset, read_pool | 10.37 (6,055) | 13.99 (6,065; 515) | 4.49 (2,974) | 6.22 (2,937; 258) |
| lazynwb polars | 32.79 (17,791) | 224.85 (20,808; 2,349) | 13.50 (8,338) | 112.55 (8,909; 622) |
| packet duckdb | 51.81 (404) | 48.15 (853; 515) | 12.39 (326) | 15.07 (586; 257) |
| lazynwb sql | 1,287.96 (65,127) | 1,350.36* (76,428; 2,362) | 249.29 (30,479) | 406.59* (31,430; 624) |
| pynwb duckdb | 96.01 (13,563) | 1,977.85* (13,568; 1,851) | 29.94 (7,744) | 1,346.90* (7,737; 949) |
| packet aligned_spikes | 8.72 (17,449) | 27.43 (18,048; 527) | 3.37 (8,222) | 16.94 (8,370; 263) |
| lazynwb intervals | 62.14 (17,804) | 98.19 (17,887; 1,181) | 27.17 (8,566) | 58.55 (8,413; 562) |

`aligned_spikes` chose the ASOF join in every cell. Stated as a range join with `join_where`, the
Polars arms took 234 s and 29.8 GiB (packet) and 250 s and 30.8 GiB (lazynwb) in one cold run on
786867 while the script was written; the arms above search the sorted cues instead. Polars SQL
plans the same range join, which is why `lazynwb sql` is the slowest NWB arm on local disk.

Every arm agreed on lick latency: 496 of 708 trials on 776259 had a lick, median 243.0 ms, and 424
of 450 on 786867, median 154.3 ms. On go-cue spikes the arms fall into three groups:

| session | packet in ticks | packet in float seconds | NWB |
|---|---|---|---|
| 776259 | 99,453,482 pairs | the same | 99,452,477 pairs, 518.5 s less summed offset |
| 786867 | 45,723,853 pairs | 45,723,852 | 45,723,415 pairs, 134.3 s less summed offset |

"Packet in ticks" is every packet arm that compares integer ticks: Polars, the datasets, DuckDB and
`aligned_spikes`. "In float seconds" is the three pandas arms, which compare `seconds()` output.
The NWB group is all six NWB arms, including lazynwb's half-open window. All three groups find the
same units with spikes. A per-spike comparison of the two stores, run once and not kept as a
script, accounts for both gaps:

- **NWB against packet.** The two stores hold the same spikes per unit, 131,396,535 and 286,896,563,
  and the same go cues: the NWB's `goCue_start_time` is exactly the packet's tick over 31,250 Hz.
  The spike times differ. The packet maps each spike through its anchors to an integer tick on
  the 31,250 Hz harp reference clock; the NWB stores continuous seconds from its own alignment.
  The difference has a median under 0.1 µs, and 97.9% (786867) and 99.9% (776259) of spikes fall
  within one 32 µs tick. The largest is 0.41 ms and 0.60 ms. With 4,500 and 6,800 units,
  about one spike falls on each tick, so 899 and 2,029 spikes sit exactly on a window's edge tick.
  The packet's closed window holds all of them. The NWB places about half just outside. Of the
  packet-only pairs, 446 of 448 on 786867 and all 1,005 on 776259 are such edge spikes; on 786867,
  10 pairs are NWB-only. The edge pairs account for 141.0 s and 507.0 s of the summed-offset gap,
  since each adds -1 s or +2 s to it. Spikes inside the window but displaced add -6.7 s and
  +11.5 s.
- **Float seconds against ticks.** On 786867 one spike lies exactly 31,250 ticks before a cue.
  `seconds()` computes `(t_tick - t_zero_tick) / rate` for each, and their difference is
  -1.0000000000000568 s, so the float comparison drops a pair that the tick comparison keeps. The
  missing 1.0 s of summed offset is that pair. None of the 2,029 edge spikes on 776259 rounds out.

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

The PyArrow column was measured again on 2026-10-03 at `fa060640`, after `Packet.table` began
reading through `read_pool()`, the reader's jemalloc pool, in place of PyArrow's default mimalloc
pool (`*-r164-pyarrow.json` and `*-r164-s3-pyarrow.json`, cold medians of three). Every spike took
0.72 s locally and 10.77 s from S3 on 776259, against 41.40 s and 43.39 s above, and 0.34 s and
5.38 s on 786867, against 0.32 s and 44.57 s. Every other operation stayed within 0.8 s of
its time above, and every returned value was unchanged. The whole-column slowdown was the
allocator.

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
| 2026-10-02 | 776259, rotational scratch | `escapewheel import`, 57 resources, core 0.18.0, four workers then one | 478.8 and 506.4 s; sources 232.0 and 258.4, staging 184.1 and 178.4; peak RSS 3.78 and 3.76 GiB | `build.py` |
| 2026-10-02 | 776259, NVMe scratch | `escapewheel import`, 57 resources, core 0.18.0, one worker then four | 795.3 and 377.2 s; sources 396.7 and 190.4, staging 348.9 and 136.9; peak RSS 3.89 and 3.66 GiB | `build.py` |
| 2026-10-02 | 776259, rotational scratch | `escapewheel import`, 57 resources, core 0.18.0, one worker then four | 425.6 and 448.9 s; sources 239.0 and 236.7, staging 131.1 and 156.5; peak RSS 3.55 and 3.65 GiB | `build.py` |
| 2026-09-30 | 776259, rotational | `escapewheel import` of a 57-resource packet, core 0.14.0 | 630.1 s: sources 431.7, staging 146.6, derive 41.4, validate 9.5, promote 0.9 | the packet's build log |
| 2026-08-30 | 776259, rotational | `escapewheel import` of a 23-resource packet | 105.1 s: sources 9.5, core 50.5, analysis 32.7, validate 12.5 | not kept |
| 2026-08-30 | 776259, rotational | `--sample 200000` import | 8.7 s | not kept; quoted in the writer's performance guide |

The 2026-09-30 sources include the waveforms (217.5 s) and the unit QC metrics (62.6 s). The
2026-08-30 import read neither, so the two totals are not comparable. The 2026-10-02 776259 build
spent 215.8 s in the sorter source, 217.2 s in the waveforms and 62.1 s in the unit QC metrics, at a
load average near 12 from unrelated work; the 2026-09-30 load was not recorded.

The 2026-10-02 worker-count builds read their sources from the rotational disk and S3 through a
warm source cache, and put only the packet and its staging on the disk named. Their waveforms
source reads a slab's chunks concurrently and takes about 20 s, where the 2026-09-30 build's took
217.5 s; the spread between cells is not yet explained.

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

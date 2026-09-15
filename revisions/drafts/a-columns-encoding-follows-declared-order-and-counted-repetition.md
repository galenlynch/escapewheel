# A Column's Encoding Follows Its Declared Order and Its Counted Repetition

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 03 §5.5 (the tick, leading-identifier and float rules become four rules over declared order and counted repetition; the report measures a column's own chunks), Part 10 §2 (four readings appended) |
| **Supersedes** | R110 §3.1, R110 §3.2 |
| **Depends on** | R110 §2.5 (why choosing by writing each column three ways was refused), R110 §3.3 (an exception records its measurement), R110 §3.4 (an extension declares one in the recipe), R110 §3.5 (a writer reports a column 1.5x off its best), R68 §1.3 (delta is defined for integers alone), R48 §2.1 (every column declares a role), R53 §2.3 (an identifier is carried or assigned), R1 (single-session packets are primary, so `session_id` rarely orders a table) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

Part 03 §5.5 gives a writer three encoding rules, two of them from R110: a tick column and the
leading identifier of a table's sort take `DELTA_BINARY_PACKED`, a float takes no dictionary, and
every other column keeps the dictionary pyarrow applies by default. A declared exception overrides a
rule for one column (R110 §3.3), and a writer reports a column costing more than 1.5x its best
encoding (R110 §3.5).

Measured column by column, those rules leave half of each packet off its best encoding, mostly in
columns too short or too uniform for a dictionary to pay for itself. This replaces the three rules
with four. Declarations mark the integers likely to climb, and counts the writer takes of the column
it is about to write say whether its values repeat. Across both packaged sessions the four leave 15
columns needing an exception, where the packets as written leave 193.

Measured on **`ecephys_776259`** (twelve probes, 6,781 sorted units, recorded 2025-04-09) and
**`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25). The population is every
integer, float, string and wall-clock column of both committed packets: 381 columns, 737
column-and-packet pairs. Each figure is a column's own compressed chunks under Zstandard, for each
encoding Part 03 §5.5 permits it, which is a dictionary, plain, and delta for an integer; the two
spike tables are sampled over four row groups. Rewriting a column under the encoding it already has
reproduces its bytes at 1.000 on every column over 1 MB. A column counts against a set of rules
where it sits 1.15x or more off its best in either packet, the margin R110 §5 closed its residual
at. pyarrow 25.0.1, Python 3.13.15, 2026-09-15.

## 2. Background

Informative.

### 2.1 R110's rules leave half of each packet off its best encoding

As written, 173 of the 365 columns of `ecephys_776259` and 182 of the 372 of `ecephys_786867` sit
1.15x or more off their best encoding. Most are short or uniform: of the 173, 73 hold a single
value, such as `session_id` in every small table, and 36 hold none, where a dictionary costs 60 bytes
against plain's 36. No rule reaches either case, since each names a kind of column rather than what
a column holds.

The report R110 §3.5 requires found none of them. It compared one-column files, and a file's footer
runs to a few hundred bytes: `core.curation_versions.sorting_run_id` is 143 bytes against 72 as a
column chunk, 1.99x, and 560 against 476 as a file, 1.18x. Judged by the chunk, it reports 54
columns in `ecephys_776259` and 55 in `ecephys_786867`.

### 2.2 A dictionary page costs 27 bytes in every row group

A column holding one value gives a dictionary nothing to index that plain's compression does not
already remove. A constant `int32` under Zstandard:

| rows | dictionary | plain |
|---:|---:|---:|
| 12 | 92 B | 69 B |
| 6,781 | 95 B | 75 B |
| 171,280 | 666 B | 718 B |
| 1,000,000 | 3,577 B | 4,000 B |

The dictionary page is 27 bytes in each row group. Below some tens of thousands of rows it
outweighs the column, and above them the dictionary is smaller by a steady 1.12x. The packets put
the crossing between `core.clock_anchors.session_id` at 41,275 rows, where the two are within
3 bytes, and at 76,646 rows, where the dictionary is smaller. Whether `session_id` wants a
dictionary is therefore a fact about how many rows share it, which no declaration states.

Below 50,000 rows, delta suits a single-valued integer better than plain. It is never more than
6 bytes larger than plain in either packet, and plain is up to 5.9x larger than delta:
`core.array_channels.axis_index` is 546 bytes plain and 93 under delta.

### 2.3 Declarations mark the integers that climb within groups

Delta pays for a column that climbs, and a count over a whole column sees a climb only where the
table is sorted by that column. `core.spike_events.t_tick` climbs within each unit and resets at the
next, and `core.clock_anchors.anchor_index` climbs within each clock, so a test of whether values
never decrease finds neither. Choosing by counts alone leaves 26 exceptions and writes both plain:
`anchor_index` 28x to 67x off its best, `core.clock_anchors.t_tick` 30x to 32x, and the spike
tables' `t_tick` 1.24x to 1.30x, which on their size puts the set 384 MB over the best before any
exception.

Three declarations mark such columns: the `_tick` suffix Part 02 §4 gives a tick coordinate, the
`structural_index` and `sequence_position` roles (Part 02 §8.1), and `assigned` identity (Part 02
§8.2). None of them states how values are spread, so Part 10 §2.7's conclusion stands: a declaration
says what a value means and not how its values are distributed. What a mark gives is a good guess
about order within groups, where a count over the whole column sees nothing. It is a guess, and wrong
in places: `core.unit_electrodes.channel_index` is a structural index cycling through 26 positions in
every unit, and needs an exception.

### 2.4 A count sees repetition that a declaration cannot

Declarations alone fail the other way. Rules that each follow from one leave 70 exceptions: a `free`
string plain, an `open` or `closed` one a dictionary, a `data` integer plain, and `session_id`
plain. No declaration separates the cases they miss. `session_id` wants plain in a 12-row table and
a dictionary in a million-row group, and `core.probes.probe_type` holds one value in one packet and
three in the other. Writing plain wherever no declaration calls for a dictionary instead regresses
the columns a dictionary exists for, `core.electrode_coordinate_values.coordinate_frame` by 29x and
79x.

A count separates what a type cannot. `core.spike_events.amplitude` and
`core.unit_quality_labels.confidence` are both floats: the first repeats, quantised to the sorter's
amplitude step, and is 1.75x smaller under a dictionary, and the second does not and is 1.47x larger.

### 2.5 The four rules leave 15 exceptions

Declared or observed order decides delta, and counts decide the rest (§3). Columns 1.15x or more off
their best in either packet, each of which needs an exception:

| rules | columns | at 1.5x | at 2x |
|---|---:|---:|---:|
| as written, R110's with its exceptions | 193 | 61 | 4 |
| declarations of type, role, identity and vocabulary | 70 | 20 | 4 |
| those, plus plain under 32 rows, or for one value under 50,000 rows | 34 | 12 | 4 |
| counts alone | 26 | 11 | 9 |
| **declared order, then counts** | **15** | **3** | **1** |

The exceptions sit on a plateau. Holding the others, the run length leaves 15 from 50 to 200 rows a
run and the repetition 15 from 32 to 50 rows a value. The one-value threshold leaves 15 at every
setting from 20,000 rows up, and bytes choose 50,000 among them: at 500,000 the set sits 913 kB over
the best, against 304 kB. Thresholds fitted to either packet alone leave 13 exceptions on the other,
where the shared ones leave 13 and 12.

Written under the four rules and their exceptions, every column of both packets lands within 1.15x of
its best: 317 of 365 and 322 of 372 exactly at it, and 157 kB and 71 kB over the best in all, 0.014%
and 0.012% of each packet. The report finds none at 1.5x. Counting costs 0.12 s to 0.20 s a packet,
one pass over values the writer already holds.

Writing each column three ways and keeping the smallest would reach the best on every column, at
about 0.4 s a packet, and R110 §2.5 refused it for two reasons: a measured choice records no reason,
and a `--sample` build measures different values from a full one. The four rules answer the first. A
count and a threshold say why a column got its encoding, so an exception still marks a column the
rules got wrong and the 1.5x report still has something to find. They share the second (§6), and
give up about 0.013% of each packet to the measured choice.

### 2.6 Byte-stream split and delta string encodings stay out

Two encodings are smaller on some columns, and neither is among those Part 03 §5.5 permits.
`BYTE_STREAM_SPLIT` is 1.15x smaller than the better of a dictionary and plain on 4 float
column-and-packet pairs and 1.15x larger on 34, `core.spike_events.amplitude` by 2.8x to 3.1x.

`DELTA_BYTE_ARRAY` is 10x smaller than plain on `core.electrodes.electrode_name`, whose sorted names
share prefixes. Two readers refuse it while reading every other encoding a packet uses: hyparquet
1.30.1, the most downloaded JavaScript Parquet reader on npm with 748,618 downloads in the week to
2026-09-11 against 375,832 for @dsnp/parquetjs, and fastparquet 2026.5.0. It cannot be read as
dictionary codes by pyarrow 25.0.1, and Parquet2.jl 0.2.34 decodes neither encoding.
`DELTA_BINARY_PACKED` itself is defined for integers alone (R68 §1.3), so no rule gives a float
delta.

## 3. Decision

### 3.1 A writer counts the column it encodes

A writer **SHOULD** choose the encoding of each integer, float, string, timestamp and date column
from the column's declarations and from four counts over the rows it holds when it chooses: the
rows, nulls included; the distinct non-null values; the runs, a run being a maximal sequence of equal
values once nulls are set aside; and, for an integer, whether its non-null values never decrease.
Where a writer writes a table whole the rows are the table's. Where it streams a table, they are the
row group it is about to write, or the first row group where the writer keeps one encoding for the
whole file.

The first of §3.2 to §3.5 that applies decides.

### 3.2 An empty column is written plain

A writer **SHOULD** write plain a column in which every row is null.

### 3.3 A single-valued column takes a dictionary from 50,000 rows

A writer **SHOULD** dictionary-encode a column holding one distinct non-null value where it holds
50,000 rows or more. Below that it **SHOULD** encode such a column with `DELTA_BINARY_PACKED` where it
is an integer, and plain otherwise (§2.2).

### 3.4 An ordered integer takes delta unless its runs are long

An integer column is **ordered** where its name ends `_tick`; where it is the first column of its
table's sort order other than `session_id` and its role is `identifier`; where its role is
`structural_index` or `sequence_position` (Part 02 §8.1); where it is an `assigned` identifier
(Part 02 §8.2); or where its non-null values never decrease.

A writer **SHOULD** encode an ordered integer with `DELTA_BINARY_PACKED`, and **SHOULD** write it
plain where it holds at least 50 rows for each run.

### 3.5 Other columns take a dictionary where values repeat

A writer **SHOULD** dictionary-encode any other column where it holds at least 50 rows for each
distinct non-null value, and **SHOULD** write it plain otherwise. A float is judged the same way,
which replaces R110 §3.2 (§2.4).

### 3.6 The report measures a column by its own chunks

The report R110 §3.5 requires **SHOULD** measure a column by its own compressed chunks rather than by
a file carrying it, and **SHOULD** judge a string, timestamp or date column between a dictionary and
plain, the two encodings §3.2 to §3.5 choose among for it. R110 §3.3's override and R110 §3.4's
recipe declaration stand, and override §3.2 to §3.5 as they overrode the rules before.

## 4. What this does not change

- **No packet already written becomes invalid.** Part 03 §5.5 permits every encoding it names and
  requires readers to support them, so a packet encoded under R110's rules conforms as before.
- **No identifier is compared through a dictionary.** §3.3 gives `session_id`, `clock_id` and
  `media_asset_id` dictionary pages in the spike and media tables, which span up to 2,197 row groups,
  and Part 03 §5.1 forbids dictionary-encoding an identifier in a way that requires unification
  across row groups before it can be compared. A Parquet dictionary page is not that: pyarrow and
  DuckDB both return such a column as integers. The failure R53 §1.1 measures belongs to identifiers
  held as Arrow dictionary codes.

## 5. Consequence

Part 03 §5.5's tick rule and the rules of R110 §3.1 and §3.2 give way to §3.1 to §3.5, and its
override and report paragraphs gain §3.6. Part 10 §2 gains the readings of §2.2 to §2.5, appended
after its §2.7.

The reference writer carries 12 exceptions for core tables, and the two recipes carry 5 entries over
3 columns of `aind_unit_qc`, all of which §2.5's 15 counts. Eleven of the 15 core exceptions R110's
rules needed become rules, among them `core.spike_events.amplitude`'s dictionary under §3.5 and delta
for `core.media_frames.pts` and `core.clock_anchors.anchor_index` under §3.4; the four that remain
are `core.units.first_spike_tick` and `last_spike_tick`, `core.unit_electrodes.electrode_id` and
`core.electrode_coordinates.region_id`.

The reference writer keeps one encoding for a whole file, as pyarrow's writer does, so it counts a
stream's first row group (§3.1). It also opens a spill file for `analysis.spike_events` before any
row exists, and gives that file §3.4's declared order alone; a spill is no packet resource, so
nothing here binds it.

R110 §3.4 argued that an exception belongs in the recipe because it is a fact about one packet's
values, and R110 §5 illustrated it with `aind_unit_qc.metrics.presence_ratio`, wanting a dictionary
in one packet and plain in the other. Judged by its own chunks it wants a dictionary in both, by
1.87x and 1.39x, so the illustration does not reproduce. The argument stands on
`aind_unit_qc.synchrony.synchrony_size` instead, which wants plain by 1.38x in `ecephys_786867` and
sits within 1.15x under either encoding in `ecephys_776259`.

Both packets carry R110's encodings until they are rebuilt.

## 6. Open

- A `--sample` build counts fewer rows in the tables it samples, so a column near 50 rows a value,
  50 rows a run or 50,000 rows may encode differently from the full build. This is unmeasured.
- Multi-session packets are unmeasured. Every packet here holds one session, so `session_id` always
  meets §3.3 before §3.4, and nothing has tested what §3.4 and §3.5 do with a column holding several.
- Whether the thresholds hold beyond one pipeline is unmeasured. Both sessions come from one, and the
  1.5x report is what would show a third session disagreeing.

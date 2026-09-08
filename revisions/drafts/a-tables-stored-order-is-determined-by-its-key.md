# A Table's Stored Order Is Determined by Its Key

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `02` §12 (the override table), `03` §5.3 and §5.4, R10 §3 |
| **Depends on** | R10 (sort by primary key), R30 (`analysis.spike_events` layout), R81 (a table's sort following its key) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2 and §8, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

Two tables are stored in an order other than their primary key. One can be brought into line by
striking a surrogate nothing uses; the other cannot, because its order is what justified
materialising it.

This part settles what constrains a table's stored order, raises the level at which a departure is
reported, and leaves both primary keys as they are. Where that order is declared is `separation-of-the-logical-standard-from-the-physical-profile` §3.3's
question, which depends on the rule stated here.

Measurements are from the two packaged sessions: **`ecephys_776259`**, twelve probes and 6,781
sorted units, and **`ecephys_786867`**, ten probes and 4,505.

## 2. What the packets hold

Informative.

Every table in both packets is stored in primary-key order except the two the registry declares an
override for.

| packet | tables present | in primary-key order | registry declares no sort |
|---|---:|---:|---:|
| `ecephys_776259` | 26 | 24 | 9 |
| `ecephys_786867` | 28 | 26 | 10 |

The nine and ten tables the registry says nothing about are in primary-key order too. `build.py`
fills `sort` from the primary key in a single pass inside its R10 block, so a table a later block
adds carries `sort: null` unless that block sets one — thirteen of thirty-eight do, among them
`core.unit_electrodes`, `core.processing_runs` and `core.electrode_coordinates`. The validator
skips a table with no declared sort, so R10 §2 has never been checked on any of them; the writer
sorts them regardless.

Parquet records the order and has no notion of a key. `RowGroup.sorting_columns` is part of the
format, and this writer fills it: four columns for `core.events`, three for `core.spike_events`,
five for `analysis.spike_events`. What a key means here is therefore what `02` §2 and §7 say it
means — a uniqueness claim a validator checks after the fact, and the target a foreign key resolves
against — and not anything the storage layer enforces.

## 3. `core.events`

`core.events` is keyed `(session_id, event_id)` and stored in `(session_id, clock_id, t_tick,
event_type)` order, which R10 §3 records as an override for pruning by time. Key order and stored
order disagree on 5,483 of 5,485 rows in `ecephys_776259` and 6,255 of 6,256 in `ecephys_786867`,
so §5 cannot be satisfied while a surrogate is the key.

`an-event-is-an-occurrence-on-a-stream` strikes `event_id`, `event_name`, `event_type` and
`clock_id` — the first two unread, the last two the stream's — and keys the table on
`(session_id, stream_id, t_tick)`, measured unique in both packets. This part depends on that: with
it, `core.events` is stored in its key's order, every table in both packets satisfies §5, and both
override statements are struck.

They disagree, which is a second reason to strike them: `03` §5.4 gives the order as three columns
where `02` §12 and R10 §3 give four, and three is not unique —
`an-event-is-an-occurrence-on-a-stream` §2 measures 5,480 distinct triples against 5,485 rows. The
disagreement is moot once neither statement exists, and the order the key now gives — stream, then
tick — prunes the query the override was written for, since a stream is one kind of event.

## 4. `analysis.spike_events`

`analysis.spike_events` is keyed `(session_id, unit_id, t_tick)` and stored in `(session_id,
clock_id, time_bucket_tick, unit_id, t_tick)` order, which R30 §3.2 requires under a MUST.

The table carries two things: spikes converted to the session's reference clock, and that layout.
R30 §1 measured the conversion as insufficient on its own — at 29 M spikes a second a materialised
copy in core's order "buys a few milliseconds on the queries anyone would run" — and concluded that
what a common clock buys is the layout, which core cannot have because its spikes are on their
probes' own clocks. So the order is not decoration on a derived table; it is what R30 weighed the
table's existence on.

Renumbering cannot reconcile key and order as it does for `core.events`: `unit_id` is shared with
core, and `t_tick` here is a coordinate converted from a measurement, so neither may be reassigned
to suit a layout.

Widening the key to the stored order is the other obvious repair, and it is **rejected**. Measured
over all 286,876,859 rows of `ecephys_776259`, `clock_id` holds **one** distinct value and
`time_bucket_tick` is a strict function of `t_tick` — **0** ticks map to two buckets. Neither column
can separate any pair of rows, so a key containing them is a superkey rather than a candidate key,
and the redundancy is not a matter of taste. A foreign key resolves against a primary key (`02`
§7), so key width decides what may reference a table and how much a referencing row must carry:
R90 §3.6 already turns on this, admitting a paired discriminator only for a resource with a
single-column key. Widening this key from three columns to five would make every future reference
to it five columns wide, to gain no uniqueness.

The key states identity and the order states layout, and §5 is what makes the relationship between
them checkable rather than conventional.

## 5. Ordering under the portable profile

A table under `escapewheel-portable-v0.1` **MUST** be stored in an order that settles its primary
key by adjacency: every key column appears in the sort, and every sort column up to and including
the last key column is either a key column itself or one the registry declares `determined_by` a
subset of the key. A validator **MUST** report a departure as an **error**.

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a
column that is a function of the key takes the same value in both. So the scan that establishes
order settles uniqueness in the same pass, which is what `02` §10.3 waives the aggregate for.

A reader **MUST NOT** depend on stored order for correctness. Establishing the order is the
validator's work, and a reader that assumed it would be trusting a property of the profile rather
than of the logical standard.

The level is the substantive change. `03` §5.3 makes ordering a SHOULD reported at **warning**, on
the ground that a mis-sorted packet is readable and slower rather than wrong — but `02` §10.3
waives the uniqueness query for any table whose stored order settles its key, which is 23 of 38
today and all 38 under this part. A waiver may not rest on a property nothing requires, and that is
the whole argument: a MUST discharged by a SHOULD is the defect.

Cost does not decide it. Re-measured on `core.spike_events`'s 286,896,563 rows under a 4 GB memory
limit, the aggregate that waiver avoids runs in **9.8 s** and spills **2.70 GB**. The 26 GB the
validator's own scan still records for it was measured when the key was four string columns, which
R53 replaced with three integers, so what the waiver saves today is ten seconds on the largest
table either packet holds.

The fallback stays. Where the scan finds a departure, uniqueness **MUST** be settled by aggregate
rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of
neighbours. A packet reaching that path has already failed.

## 6. What this does not change

- **No packet's rows move.** `core.events` is already stored in the order §3.1 makes its key, so
  every table in both packets already satisfies §5; what changes for `core.events` is two columns,
  not a row's position.
- **`analysis.spike_events` keeps the three-column key it has**, and no table or reference is
  added anywhere.
- **An event stays addressable.** Should an extension ever record per-event detail, R90 §3.5's
  shared-key shape carries the four key columns rather than two. That is the cost of the strike,
  and it is paid only by a table that does not exist.
- **R30's layout and its MUST both stand.** Bucketing by time and sorting by unit within a bucket
  is why the table exists, and §5 accommodates it rather than requiring it be argued away.
- **`03` §5.2's partitioning rules are untouched.** A partitioned table's order across files is
  still undefined by the profile, and §5's MUST is a statement about a table's contents rather than
  about file boundaries.
- **The thirteen tables with `sort: null` gain a check, not an obligation.** They are already in
  primary-key order in both packets; what changes is that a departure would be seen.

## 7. Consequence

`registry/build.py` loses `core.events` from its `OVERRIDE` table and fills `sort` from the primary
key for every table declaring none, in a pass at the **end** of the build: the thirteen nulls of §2
are a table added after that pass ran, and a pass that runs last cannot be outrun by a later block.
`escapewheel_validator.generate.adjacency_settles_uniqueness` is unchanged, §5 being that function
stated as a rule rather than left as an optimisation the validator happens to make.

Tier 1 uniqueness goes from 14 generated `GROUP BY` checks to none on a conforming packet —
thirteen from the filled sorts, and the fourteenth because §3.1 makes `core.events` keyed on the
order it is stored in. Ordering scans go from 25 tables to all 38.

335 columns become **333**: `core.events` loses `event_id` and `event_name`. References stay at 97,
since neither column carried one, and the Tier 2 rules are unchanged.
`escapewheel_reader.alignment` selects the event's tick where it selected its identifier, and the
NWB adapter stops composing `f"{name}:{offset}"` for a column that no longer exists.

**Both packets must be rebuilt.** Striking a required column leaves a file the registry no longer
describes. R61 §3 makes a correction a rebuild, and this one re-reads no external resource; R87
§2.1 and R88 §2 already require it, so this adds no build of its own.

## 8. Open

- **Whether `determined_by` should be checked against rows.** §5 lets a declaration stand in for a
  key column, and nothing verifies it: `check.py` sees that `time_bucket_tick` declares itself a
  function of `t_tick`, not that it is one. It held on measurement — 0 of 286,876,859 rows map a
  tick to two buckets — but a wrong declaration would silently waive a uniqueness check rather than
  fail one, which is the shape R56 §2.4 exists to prevent for units and clocks. A Tier 2 rule per
  declaration would close it, at one aggregate over the declaring table.
- **Whether the remaining assigned identifiers are numbered usefully.** An assigned identifier may
  be numbered in any order a rebuild reproduces, and what that order is decides the layout of every
  table keyed on it. §3.1 removes one such choice by removing the identifier; of the **14** that
  remain, deciding the order of **33 of 38** tables, exactly one has been made deliberately —
  `unit_id` run-major (R81 §2.2). Most of the rest are too small for it to matter (12 probes, 12
  sorting runs, 26 processing runs), but `electrode_id` orders 4,608 electrodes, 8,832 coordinates,
  171,280 `core.unit_electrodes` rows and 29,568 quality labels, and no revision says what its
  numbering should cluster by.
- **Whether an amendment may append.** §5 requires a table to be in an order its key settles, and
  R32's amendment writes new resources rather than appending to existing ones, so no case exists
  yet. A profile that permitted appending would need to say whether a later batch may re-enter the
  key range of an earlier one.

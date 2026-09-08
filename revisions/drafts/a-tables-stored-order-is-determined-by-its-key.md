# A Table's Stored Order Is Determined by Its Key

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `02` §10.1 (the uniqueness obligation, losing its physical condition), `03` §5.3 (the ordering rule and the level a departure is reported at) |
| **Depends on** | R10 §2 (sort by primary key), R30 §3.2 (`analysis.spike_events`' layout), R81 §2.4 (that layout narrowed to five columns), R75 §2.1 (an assigned identifier is reproducible), R91 §3.2 (`core.events`' key) |
| **Profile** | `escapewheel-portable-v0.1` |

§5 is the only normative section.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`02` §10.1 lets a validator skip the primary-key uniqueness query "where a table's physical sort
begins with its primary key", since duplicates are then adjacent and the ordering scan settles
them. Uniqueness is a logical fact and stored order is a physical one, so the logical standard is
discharging its own MUST with a property only a profile can promise — and `03` §5.3 promises
nothing, making ordering a SHOULD reported at **warning** on the ground that a mis-sorted packet is
readable and slower rather than wrong.

Two defects follow. A correctness check is skipped on the strength of a recommendation. And the
clause that skips it sits in the part that must hold under every profile, though an Iceberg
compaction reorders rows and would make it false.

This part puts the obligation and the means on opposite sides of that line. `02` §10.1 keeps the
requirement that uniqueness be established and loses the condition; `03` §5.3 gains the ordering
rule as a **MUST** reported at **error**, stated so that it admits `analysis.spike_events`, whose
layout is what justified materialising it. The one declaration the rule leans on is verified rather
than believed. No column, reference or rule is added, and no packet's rows move.

Measurements are from the two packaged sessions: **`ecephys_776259`**, twelve probes and 6,781
sorted units, and **`ecephys_786867`**, ten probes and 4,505.

## 2. What the packets hold

Informative.

Both packets were built before R88 §2 and R91 §3.2 and must be rebuilt for them, so what they
measure is the writer's habit rather than the registry's present state: every table in both is
stored in primary-key order except the two the registry declared an override for when each was
written.

| packet | tables present | in primary-key order | registry declares no sort |
|---|---:|---:|---:|
| `ecephys_776259` | 26 | 24 | 9 |
| `ecephys_786867` | 28 | 26 | 10 |

The nine and ten tables the registry says nothing about are in primary-key order too. `build.py`
fills `sort` from the primary key in a single pass inside its R10 block, so a table a later block
adds carries `sort: null` unless that block sets one, and **13 of 38** tables carry one today. The
validator skips a table with no declared sort, so R10 §2 has never been checked on
`core.unit_electrodes`, `core.processing_runs`, `core.electrode_coordinates` or the ten others;
the writer sorts them regardless.

Parquet records the order and has no notion of a key. `RowGroup.sorting_columns` is part of the
format, and this writer fills it for every table declaring a sort: three columns for `core.events`
since R91 §3.2, three for `core.spike_events`, five for `analysis.spike_events`. What a key means
here is what `02` says it means — a declaration every table makes (§2), checked for uniqueness
after the fact (§10.1), and the target a reference resolves against (§7) — and not anything the
storage layer enforces.

## 3. `core.events` is already in line

`core.events` was keyed on a surrogate and stored in time order, so its key and its stored order
disagreed on all but a handful of rows in each packet. That is the departure this rule was written
against.

R91 §3.2 settled it: `event_id`, `event_name`, `event_type` and `clock_id` are struck and the key
is `(session_id, stream_id, t_tick)`, the order the table is already stored in. Accepting it
amended the documents as well — `02` §13.1 now records that no core table overrides the default, and
`03` §5.3 and §5.4 name only `analysis.spike_events` — so no statement of the old order survives
where a reader would look for one. R10 §3's override table still lists it, and a revision is the
record of a decision rather than a statement of current law.

One line of the implementation outlived the decision. `registry/build.py` still carries
`core.events` in the `OVERRIDE` table its R10 block reads, dead because the R91 block rewrites the
same field afterwards; two blocks stating different orders for one table is a contradiction a later
edit could resolve the wrong way, and §7 removes it.

Both committed packets still hold the old order, so `core.events` is **1,293** rows out of its
current key order in `ecephys_776259` and **1,001** in `ecephys_786867`. That is the one place
§5.2 fails today, and the rebuild R91 §5 already requires is what clears it.

## 4. `analysis.spike_events`

`analysis.spike_events` is keyed `(session_id, unit_id, t_tick)` and stored in `(session_id,
clock_id, time_bucket_tick, unit_id, t_tick)`. R30 §3.2 requires that layout under a MUST and
states it in seven columns; R81 §2.4 narrowed it to these five when `sorting_run_id` and
`curation_id` left spike identity, keeping R30's time bucket ahead of the unit.

The table carries two things: spikes converted to the session's reference clock, and that layout.
R30 §1 measured the conversion as insufficient on its own — at 29 M spikes a second a materialised
copy in core's order "buys a few milliseconds on the queries anyone would run" — and concluded that
what a common clock buys is the layout, which core cannot have because its spikes are on their
probes' own clocks. The order is not decoration on a derived table; it is what R30 weighed the
table's existence on.

Neither a strike nor a renumbering reconciles key and order here as R91 §3.2 did for `core.events`:
`unit_id` is shared with core and `t_tick` is a coordinate converted from a measurement, so neither
may be reassigned to suit a layout, and both are load-bearing in the sort.

Widening the key to the stored order is the other obvious repair, and it is **rejected**. Measured
over all 286,876,859 rows of `ecephys_776259`, `clock_id` holds **one** distinct value and
`time_bucket_tick` is a strict function of `t_tick` — **0** ticks map to two buckets. Neither
column can separate any pair of rows, so a key containing them is a superkey rather than a
candidate key. Key width also decides what may reference a table and how much a referencing row
must carry, which R90 §3.6 already turns on, admitting a paired discriminator only for a resource
with a single-column key. Widening this key from three columns to five would make every future
reference to it five columns wide, to gain no uniqueness.

The key states identity and the order states layout, and §5 is what makes the relationship between
them checkable rather than conventional.

## 5. Ordering under the portable profile

### 5.1 The obligation and the means

`02` §10.1's sentence waiving the uniqueness query is **struck**. What the logical standard requires
is the fact alone: a validator **MUST** establish that a table's primary key is unique, by query or
by any means a physical profile defines as establishing it. That clause holds under every profile,
which is what a clause of Part 02 has to do.

How it is established under `escapewheel-portable-v0.1` is §5.2, and Part 03 is where a rule
belongs that would change if the profile changed. An Iceberg compaction rewrites files and
preserves no order across them, so a table's stored order is exactly such a rule.

### 5.2 The order a table is stored in

A table under `escapewheel-portable-v0.1` **MUST** be stored in an order that settles its primary
key by adjacency: every key column appears in the sort, and every sort column up to and including
the last key column is either a key column itself or one the registry declares `determined_by` a
subset of the key. A validator **MUST** report a departure as an **error**.

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a
column that is a function of the key takes the same value in both. So the scan that establishes
order settles uniqueness in the same pass, which is the means §5.1 leaves to the profile to supply.

Adjacency is what the condition should have said. `02` §10.1 required the sort to **begin with** the
primary key, which is a prefix test, and `analysis.spike_events` fails it — its sort opens with
`clock_id` and `time_bucket_tick`, two columns the key does not contain — so the waiver as written
never covered the one table that most needs it. `02` §10.1's literal text reaches **24 of 38**
tables where `escapewheel_validator.generate.adjacency_settles_uniqueness` waives **25**, and the
extra one is `analysis.spike_events`, whose 286,876,859-row aggregate the validator is already
skipping without authority. The adjacency form authorises it and still excludes what should be
excluded: a sort of `(a, x, b)` under key `(a, b)` lets `x` order duplicates apart, and there the
aggregate is the only correct check.

A reader **MUST NOT** depend on stored order for correctness. Establishing the order is the
validator's work, and a reader that assumed it would be trusting a property of the profile rather
than of the logical standard.

### 5.3 What the level costs

`03` §5.3's SHOULD becomes a **MUST**, and its **warning** an **error**. The uniqueness query is
skipped for 25 of 38 tables today and for all 38 under §5.2, so the level decides whether that many
correctness checks rest on a requirement or on a recommendation.

Cost does not decide it. Re-measured on `core.spike_events`'s 286,896,563 rows under a 4 GB memory
limit, the aggregate the waiver avoids runs in **8.8 s** and returns 0 duplicate keys. The 26 GB
the validator still records for it was measured when the key was four string columns, which R53
replaced with three integers, so what the waiver saves today is nine seconds on the largest table
either packet holds.

The fallback stays. Where the scan finds a departure, uniqueness **MUST** be settled by aggregate
rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of
neighbours. A packet reaching that path has already failed §5.2.

### 5.4 A `determined_by` declaration is verified by the scan

Where §5.2 lets a `determined_by` declaration stand in for a key column, the ordering scan **MUST**
verify it: of two adjacent rows sharing a primary key, every sort column declared `determined_by` a
subset of that key **MUST** hold the same value in both, and a validator **MUST** report a
difference as an **error**.

Verifying it in the scan costs nothing, and verifying it as a query costs everything the
declaration saves. Measured on `analysis.spike_events`' 286,876,859 rows, the aggregate that checks
`time_bucket_tick` is a function of `t_tick` runs in **8.5 s** against the **8.8 s** uniqueness
aggregate the declaration waives, so a rule per declaration would spend the saving to protect it.
The scan already compares each row with its predecessor, which makes this one more equality on a
pass being made anyway, and it belongs in the shim where R12 §4 puts what SQL cannot observe.

The failure it catches is a silent one. A wrong `determined_by` **waives** a check rather than
failing one, where every other structural declaration that can be wrong fails loudly: a wrong
reference generates an anti-join, and a wrong `clock_from` is refused by R56 §2.4 with no packet in
hand. Two columns declare `determined_by` today, both on `analysis.spike_events` — `clock_id` on
`session_id`, `time_bucket_tick` on `t_tick` — and both hold, at **0** offending rows each.

## 6. What this does not change

- **No packet's rows move for this part.** The thirteen tables declaring no sort are already in
  primary-key order in both packets, so §5.2 asks nothing new of them, and the writer takes its
  order from the registry.
- **`analysis.spike_events` keeps its three-column key**, and no table, column, reference or rule
  is added anywhere.
- **R30's layout and its MUST both stand.** Bucketing by time and sorting by unit within a bucket
  is why the table exists, and §5.2 accommodates it rather than requiring it be argued away.
- **No extension is invalidated.** All **11** tables across `aind_opto`, `aind_unit_qc`,
  `dynamic_foraging` and `vr_foraging` sort by their primary key outright, so §5.2 holds for each
  of them without a `determined_by` declaration.
- **The general form of this belongs to another part.**
  `separation-of-the-logical-standard-from-the-physical-profile` §3.1 and §3.2 state that no clause
  of Part 02 may name a physical property or depend on a clause of Part 03, and sweep the crossings
  this part does not touch. §5.1 repairs only the one clause this part was already rewriting,
  rather than leaving a physical condition in the logical standard for a later part to move.
- **`03` §5.2's partitioning rules are untouched.** A partitioned table's order across files is
  still undefined by the profile, and §5.2 is a statement about a table's contents rather than
  about file boundaries.
- **An assigned identifier's numbering is already constrained.** §5.2 leans on a rebuild
  reproducing the order a table is stored in, which R75 §2.1 requires of every assigned identifier:
  the same recipe and sources produce the same numbers, never wall-clock time or iteration order.
  Which order each is numbered in beyond that is an optimisation, deliberate once — R81 §2.2 chose
  run-major for `unit_id` and measured 7.0x on reading a whole probe — and unmeasured for the 14
  that remain. The one with comparable leverage already clusters usefully by construction:
  `electrode_id` is assigned from a name composed probe-first, so ascending `electrode_id` is
  probe-major across `ecephys_776259`'s 4,608 electrodes, 8,832 coordinates, 171,280
  `core.unit_electrodes` rows and 29,568 quality labels.

## 7. Consequence

No column, reference or rule changes.

`registry/build.py` loses `core.events` from its `OVERRIDE` table, and fills `sort` from the
primary key for every table declaring none, in a pass at the **end** of the build: the thirteen
nulls of §2 are tables added after that pass ran, and a pass that runs last cannot be outrun by a
later block. `escapewheel_validator.generate.adjacency_settles_uniqueness` is unchanged, §5.2 being
that function stated as a rule rather than left as an optimisation the validator happens to make;
the ordering scan gains §5.4's comparison.

Tier 1 uniqueness goes from **13** generated `GROUP BY` checks to none on a conforming packet, all
thirteen from the filled sorts. Ordering scans go from 25 tables to all 38, and the writer stamps
`RowGroup.sorting_columns` on 38 rather than 25, since `writer.py` writes it for a table that
declares an order.

**No rebuild is owed by this part.** §3 records the one table that fails §5.2 in the committed
packets, and the rebuild R87 §2.1, R88 §2 and R91 §5 already require is what clears it.

## 8. Open

- **Whether an amendment may append.** §5.2 requires a table to be in an order its key settles, and
  no case exists yet: R32's amendment writes new resources rather than appending to existing ones,
  and R14 §2.3 forbids mutating packet-owned bytes at all. Neither answer is obvious. Read per
  file, a later batch would be ordered within itself but forbidden from re-entering an earlier
  batch's key range, which makes appending useful only where data arrives in key order; read per
  table, the whole table must be re-established, which makes appending no cheaper than a rewrite.
  What would decide it is the Iceberg profile `07` defers to Phase 7, where a snapshot versions a
  table's rows and appending is the ordinary operation.

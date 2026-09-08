# R92 — A Table's Uniqueness Is Established by Its Stored Order

| | |
|---|---|
| **Status** | **Accepted** 2026-09-08 |
| **Amends** | `02` §10.1 (the uniqueness obligation, losing its physical condition), `02` §8 (a new §8.5 defining `determined_by`), `03` §5.3 (the ordering rule and the level a departure is reported at), `06` §4 (when `analysis.spike_events` is not materialised) |
| **Depends on** | R10 §2 (sort by primary key), R30 §3.2 (`analysis.spike_events`' layout), R81 §2.4 (that layout narrowed to five columns), R75 §2.1 (an assigned identifier is reproducible), R91 §3.2 (`core.events`' key) |
| **Profile** | `escapewheel-portable-v0.1` |

§2 is normative; every other section is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`02` §10.1 lets a validator skip the primary-key uniqueness query "where a table's physical sort
begins with its primary key", since duplicates are then adjacent and the ordering scan settles
them. Two things are wrong with that. Stored order is a physical property and every clause of
Part 02 must hold under any profile, so the logical standard is discharging its own MUST with
something only a profile can promise; and `03` §5.3 promises nothing, making ordering a SHOULD
reported at **warning**, on the ground that a mis-sorted packet is readable and slower rather than
wrong. A correctness check is skipped on the strength of a recommendation.

§2 puts the obligation and the means on opposite sides of that line. `02` §10.1 keeps the
requirement that uniqueness be established and loses the condition; `03` §5.3 gains the ordering
rule as a **MUST** reported at **error**, shaped so that it admits `analysis.spike_events`, whose
layout is what justified materialising it; `determined_by`, the declaration that shaping leans on,
is defined in `02` §8 and verified against rows by the scan rather than believed; and `06` §4 says
what a writer does when the conversion that table performs collides two spikes onto one tick. No
column, reference or Tier 2 rule changes, and no packet's rows move.

Measurements are from the two packaged sessions: **`ecephys_776259`**, twelve probes and 6,781
sorted units, and **`ecephys_786867`**, ten probes and 4,505.

## 2. Decision

### 2.1 Uniqueness is the logical standard's; establishing it is the profile's

`02` §10.1 states two things about uniqueness and both change. Its list of what a validator **MUST**
generate from the declaration alone keeps required-column non-null checks, foreign-key anti-joins
and closed-vocabulary membership, and loses primary-key uniqueness; its sentence waiving the
uniqueness query where the sort begins with the key is **struck**. In their place the logical
standard requires the fact alone: a validator **MUST** establish that a table's primary key is
unique, by query or by any means a physical profile defines as establishing it.

Both sentences move together. Striking the waiver alone would leave the list requiring a query for
every table, which is the opposite of what the waiver permitted, so one subsection would contradict
itself.

### 2.2 The order a table is stored in

A column **MAY** declare `determined_by`, naming the columns whose values fix its own: two rows
agreeing on every column named agree on this one, and an empty list declares a constant. The
declaration is structural, decidable from the registry with no packet in hand, and §2.3 is what
verifies it against rows. It belongs in `02` §8 as a new §8.5, beside role, identity, discriminator
and unit — a statement about values holds under any profile, where the rule below consuming it does
not.

A table under `escapewheel-portable-v0.1` **MUST** be stored in an order that settles its primary
key by adjacency: every key column appears in the sort, and every sort column up to and including
the last key column is either a key column itself or one the registry declares `determined_by` a
subset of the key. Where the registry declares no sort for a table, the order required is its
primary key's. A validator **MUST** report a departure as an **error**, where `03` §5.3 made it a
SHOULD reported at warning.

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a
column that is a function of the key takes the same value in both. So the scan that establishes
order settles uniqueness in the same pass, which is the means §2.1 leaves to the profile to supply.

Where the scan finds a departure, uniqueness **MUST** be settled by aggregate rather than by
adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of neighbours.

A reader **MUST NOT** depend on stored order for correctness. Establishing the order is the
validator's work, and a reader that assumed it would be trusting a property of the profile rather
than of the logical standard.

### 2.3 A `determined_by` declaration is verified by the scan

Where §2.2 lets a `determined_by` declaration stand in for a key column, the ordering scan **MUST**
verify it: of two adjacent rows sharing a primary key, every sort column declared `determined_by` a
subset of that key **MUST** hold the same value in both, and a validator **MUST** report a
difference as an **error**.

A wrong declaration otherwise **waives** a check rather than failing one, where every other
structural declaration that can be wrong fails loudly: a wrong reference generates an anti-join,
and a wrong `clock_from` is refused by R56 §2.4 with no packet in hand.

What the comparison reaches is bounded by what a scan of neighbours can see. Two rows sharing a key
and disagreeing on a declared column are adjacent, so the scan reports both the duplicate and the
false declaration, and the second is what says which to repair. A declaration false enough to sort
two duplicates apart is beyond it, since the rows are then never neighbours — and proving the
dependency instead costs §3.5's 8.5 s against the 8.8 s it saves. So this buys the diagnosis, and
the detection it rests on stays the duplicate-key check itself.

### 2.4 A conversion that collides is not materialised

`analysis.spike_events` is keyed on the converted tick (R30 §3.2, `06` §4), and a conversion
preserves distinctness only where it expands. A writer that finds two spikes of one unit landing on
one reference tick **MUST NOT** materialise the table, and **MUST** record the reason in the
producing run's parameters, as R40 §2.3 requires of an omitted row.

Refusing costs the packet nothing it can use. `06` §4 justifies the table on a ten-second
population window costing 0.025 s against 7.7 s, and a histogram built on collapsed spikes
undercounts them, so a reference clock too coarse to separate one unit's spikes makes this table
the wrong instrument rather than a broken one — and `06` §2 already contemplates its not being
built. Carrying the probe tick instead, and keying on that, is rejected on the cost §3.3 measures.

## 3. Why the rule takes this shape

### 3.1 Adjacency admits `analysis.spike_events`; a prefix does not

`analysis.spike_events` is keyed `(session_id, unit_id, t_tick)` and stored in `(session_id,
clock_id, time_bucket_tick, unit_id, t_tick)` — R30 §3.2's layout under a MUST, in seven columns,
narrowed to these five by R81 §2.4 and still keeping the time bucket ahead of the unit. Its sort
therefore does not begin with its key, and `02` §10.1's prefix test never covered it.

Measured against the current registry, that test reaches **24 of 38** tables where
`escapewheel_validator.generate.adjacency_settles_uniqueness` waives **25**. The extra one is
`analysis.spike_events`, whose 286,876,859-row aggregate the validator is already skipping without
authority, so §2.2 authorises what the implementation does rather than changing it.

Adjacency still excludes what a prefix test excludes: a sort of `(a, x, b)` under key `(a, b)` lets
`x` order duplicates apart, and there the aggregate is the only correct check.

Reordering the table to fit a prefix test is not available. R30 §1 weighed the table's existence on
that layout rather than on the conversion — at 29 M spikes a second a materialised copy in core's
order "buys a few milliseconds on the queries anyone would run", so what a common clock buys is the
layout, which core cannot have with its spikes on their probes' own clocks.

### 3.2 Widening the key would buy no uniqueness

Widening the key to the five stored columns is the other repair, and it is **rejected**. Measured
over all 286,876,859 rows of `ecephys_776259`, `clock_id` holds **one** distinct value and
`time_bucket_tick` is a strict function of `t_tick` — **0** ticks map to two buckets. Neither column
can separate any pair of rows, so a key containing them is a superkey rather than a candidate key.

Key width also decides what may reference a table and how much a referencing row must carry, which
R90 §3.6 already turns on, admitting a paired discriminator only for a resource with a single-column
key. Widening this key from three columns to five would make every future reference to it five
columns wide, to gain nothing.

Renumbering is not available either: `unit_id` is shared with core and `t_tick` is a coordinate
converted from a measurement, so neither may be reassigned to suit a layout, and both are
load-bearing in the sort.

### 3.3 The converted tick is distinct only because the reference clock is faster

`core.spike_events` keys a spike by its tick on the probe's clock, where the sorter guarantees
distinctness. `analysis.spike_events` inherits that key on the converted tick — R30 §3.2 says
"below the bucket the key is `core.spike_events`'s own, unchanged" — and nothing states the premise
that makes inheriting it safe.

In both packets the premise holds by rate. Every probe clock is **30,000 Hz** and the session's
reference clock, `harp`, is **31,250 Hz**, so the map expands by 1.0417 and two distinct probe
ticks cannot meet: **0** duplicate keys over 286,876,859 rows.

Physiology does not supply the premise. The smallest gap between consecutive spikes of one unit is
**7 probe ticks**, 233 µs, and **16,181,534** gaps are under a millisecond, so the sorter emits ISI
violations freely and nothing forbids a one-tick gap — which collapses under any reference clock
slower than the source. The clock graph does not supply it either: R27 requires a well-founded
parent chain and bounds the alignment error, and says nothing about rate, so a rig syncing 30 kHz
probes to a 1 kHz clock is conforming.

Carrying the probe tick as a column would key the table on `core.spike_events`' own key — three
natural columns, no surrogate, and R46 §2 admits a composite reference. It is rejected on cost:
`t_tick` is **487.1 MB** of this table's 494.1 MB at 13.6 bits a row, and a source tick costs what
core's does at 12.9, taking the table to about **955 MB, 1.93x**, to gain a key no reference
targets.

### 3.4 The aggregate the waiver avoids costs nine seconds

Cost does not decide the level. Re-measured on `core.spike_events`'s 286,896,563 rows under a 4 GB
memory limit, the aggregate runs in **8.8 s** and returns 0 duplicate keys. The 26 GB the validator
still records for it was measured when the key was four string columns, which R53 replaced with
three integers, so what the waiver saves today is nine seconds on the largest table either packet
holds — against the 25 tables §3.1 counts whose uniqueness rests on a recommendation, and all 38
under §2.2.

### 3.5 Verifying the declaration as a query would cost what it saves

Measured on `analysis.spike_events`' 286,876,859 rows, the aggregate that checks `time_bucket_tick`
is a function of `t_tick` runs in **8.5 s**, against §3.4's 8.8 s for the uniqueness aggregate the
declaration waives. A rule per declaration would spend the saving to protect it, where the scan
already compares each row with its predecessor and §2.3 is one more equality on a pass being made
anyway — in the shim, where R12 §4 puts what SQL cannot observe.

Two columns declare `determined_by` today, both on `analysis.spike_events`: `clock_id` on
`session_id`, `time_bucket_tick` on `t_tick`. Both hold, at **0** offending rows each.

### 3.6 Every table but one is already stored in key order

Both packets predate R88 §2 and R91 §3.2, so what they measure is the writer's habit rather than
the registry's present state.

| packet | tables present | in primary-key order | registry declares no sort |
|---|---:|---:|---:|
| `ecephys_776259` | 26 | 24 | 9 |
| `ecephys_786867` | 28 | 26 | 10 |

**13 of 38** tables declare no sort, and the validator skips a table that declares none, so R10 §2
has never been checked on `core.unit_electrodes`, `core.processing_runs`,
`core.electrode_coordinates` or the ten others. The writer sorts them regardless, which is why
§2.2's baseline costs nothing.

`core.events` is the one table failing §2.2 today — **1,293** rows out of key order in
`ecephys_776259` and **1,001** in `ecephys_786867` — because both packets were written under the
override R91 §3.2 removed when it keyed the table on `(session_id, stream_id, t_tick)`. The rebuild
R91 §5 already requires is what clears it.

## 4. What this does not change

- **No packet's rows move for this part.** The thirteen tables declaring no sort are already in
  primary-key order in both packets, so §2.2 asks nothing new of them.
- **`analysis.spike_events` keeps its three-column key**, and no table, column or reference is
  added anywhere.
- **R30's layout and its MUST both stand.** Bucketing by time and sorting by unit within a bucket
  is why the table exists, and §2.2 accommodates it rather than requiring it be argued away.
- **Neither packet is invalidated by §2.4.** The conversion collides in neither, so the table
  stays materialisable in both; §3.3 measures why.
- **No extension is invalidated.** All **11** tables across `aind_opto`, `aind_unit_qc`,
  `dynamic_foraging` and `vr_foraging` sort by their primary key outright, so §2.2 holds for each
  of them without a `determined_by` declaration.
- **The `sort` field is not filled in.** §2.2 makes a missing declaration mean primary-key order
  rather than requiring one be written for each of the thirteen tables that lack it. Filling the
  field and later removing it would implement one rule twice, and the field is a physical
  declaration sitting in the logical standard's machine form, so its removal is a question about
  where a declaration belongs rather than about what order a table is in.
- **Only one boundary crossing is repaired.** §2.1 moves the clause this part was already
  rewriting; Part 02 names a physical property in other places, and stating the general
  prohibition — that no clause of Part 02 may name one or depend on a clause of Part 03 — is a
  question about which part holds which rule, not about uniqueness.
- **`03` §5.2's partitioning rules are untouched.** A partitioned table's order across files is
  still undefined by the profile, and §2.2 is a statement about a table's contents rather than
  about file boundaries.
- **An assigned identifier's numbering is already constrained.** §2.2 leans on a rebuild
  reproducing the order a table is stored in, which R75 §2.1 requires of every assigned identifier:
  the same recipe and sources produce the same numbers, never wall-clock time or iteration order.
  Which order each is numbered in beyond that is an optimisation, deliberate once — R81 §2.2 chose
  run-major for `unit_id` and measured 7.0x on reading a whole probe — and unmeasured for the 14
  that remain. The one with comparable leverage already clusters usefully by construction:
  `electrode_id` is assigned from a name composed probe-first, so ascending `electrode_id` is
  probe-major across `ecephys_776259`'s 4,608 electrodes, 8,832 coordinates, 171,280
  `core.unit_electrodes` rows and 29,568 quality labels.

## 5. Consequence

No column, reference or Tier 2 rule changes, so `registry/build.py` gains no block and this part is
recorded in its `UNSTAMPED` tuple. It loses `core.events` from the `OVERRIDE` table its R10 block
reads, dead since the R91 block rewrites the same field afterwards.

`06` §4 gains §2.4's clause beside its "Rows are not preserved" paragraph, and `02` §8 gains §8.5.
The writer compares the two ticks at conversion, which is one comparison in a loop it already runs.
`escapewheel_validator.generate.adjacency_settles_uniqueness` gains one line, reading a table's
primary key where it declares no sort; today it returns `False` for those thirteen and the
validator checks nothing about their order. The ordering scan gains §2.3's comparison. Nothing else
in the validator changes.

Tier 1 uniqueness goes from **13** generated `GROUP BY` checks to none on a conforming packet, all
thirteen from the tables that declare no sort. Ordering scans go from 25 tables to all 38.
`RowGroup.sorting_columns` is unaffected: `writer.py` stamps it for a table declaring an order, and
§2.2 adds no declaration.

**No rebuild is owed by this part.** §3.6 records the one table that fails §2.2 in the committed
packets, and the rebuild R87 §2.1, R88 §2 and R91 §5 already require is what clears it.

## 6. Open

- **Whether an amendment may append.** §2.2 requires a table to be in an order its key settles, and
  no case exists yet: R32's amendment writes new resources rather than appending to existing ones,
  and R14 §2.3 forbids mutating packet-owned bytes at all. Neither answer is obvious. Read per
  file, a later batch would be ordered within itself but forbidden from re-entering an earlier
  batch's key range, which makes appending useful only where data arrives in key order; read per
  table, the whole table must be re-established, which makes appending no cheaper than a rewrite.
  What would decide it is the Iceberg profile `00` §7.3 holds open, where a snapshot versions a
  table's rows and appending is the ordinary operation.

# R90 — Primary-Key Order for Every Table

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `02` §12 (the override table), `03` §5.3 and §5.4, R10 §3, R30 §3.2, R81 §2.4 |
| **Depends on** | R10 (sort by primary key), R30 (`analysis.spike_events` layout), R81 (renumbering an assigned identifier) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2 and §7, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

Two tables are stored in an order other than their primary key, and both can be brought into line
by changing the key rather than the layout. This part removes the two overrides, requires
primary-key order under the portable profile, and drops the per-table `sort` field from the
registry.

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
fills `sort` from the primary key in a single pass inside its R10 block, so every table a later
revision adds keeps `sort: null` — thirteen of thirty-five, among them `core.unit_electrodes`,
`core.processing_runs` and `core.electrode_coordinates`. The validator skips a table with no
declared sort, so R10 §2 has never been checked on any of them; the writer sorts them regardless.

## 3. `core.events`

`core.events` is keyed `(session_id, event_id)` and stored in `(session_id, clock_id, t_tick,
event_type)` order, which R10 §3 records as an override for pruning by time.

The stored order is itself unique: 5,485 distinct `(session_id, clock_id, t_tick, event_type)`
over 5,485 rows in `ecephys_776259`, and 6,256 over 6,256 in `ecephys_786867`. Key order and
stored order disagree on 5,483 and 6,255 rows, so `event_id` today is assigned in an order that
serves nothing.

`event_id` is an **assigned** identifier (R53 §2.3), so the packet mints it and may mint it in any
order that a rebuild reproduces.

### 3.1 Decision

A writer **MUST** assign `core.events.event_id` by ascending `(session_id, clock_id, t_tick,
event_type)`, densely from 0 as every other assigned identifier in a packet is — `unit_id`,
`electrode_id` and `device_id` all run 0 to n-1 with no gap. A rebuild then reproduces the
numbering (R81 §2.2), the key order becomes the pruning order, and `03` §5.4's override for
`core.events` is struck.

This is R81 §2.4 applied a second time: numbering `unit_id` run-major made `core.spike_events`'s
default order cluster a probe's spikes exactly as its override had, and the override became
unnecessary rather than being argued away.

## 4. `analysis.spike_events`

`analysis.spike_events` is keyed `(session_id, unit_id, t_tick)` and stored in `(session_id,
clock_id, time_bucket_tick, unit_id, t_tick)` order, which R30 §3.2 requires under a MUST because
the layout is the table's reason for existing.

Renumbering cannot reconcile these: `unit_id` is shared with core and `t_tick` is a measured
coordinate, so neither may be reassigned to suit a layout. The stored order is a valid key
instead — 286,876,859 distinct tuples over 286,876,859 rows in `ecephys_776259`, and
131,387,137 over 131,387,137 in `ecephys_786867`.

Uniqueness is unchanged by construction, not only by measurement. `clock_id` is declared
`determined_by` `session_id` and `time_bucket_tick` is declared `determined_by` `t_tick`, so
the two added columns take the same value in any two rows the old key could not separate.

### 4.1 Decision

`analysis.spike_events`'s primary key becomes `(session_id, clock_id, time_bucket_tick, unit_id,
t_tick)`. Its stored order is then its key order, and `03` §5.4's second override is struck along
with R30 §3.2's separate MUST, which the ordering rule of §5 now carries.

## 5. Ordering under the portable profile

With both overrides gone, one rule replaces the per-table declaration.

A table under `escapewheel-portable-v0.1` **MUST** be written in its primary key's order, in the
order the key declares. A validator **MUST** report a departure as an **error**.

A reader **MUST NOT** depend on stored order for correctness. Establishing the order is the
validator's work, and a reader that assumed it would be trusting a property of the profile rather
than of the logical standard.

The level is the substantive change. `03` §5.3 makes ordering a SHOULD reported at **warning**,
on the ground that a mis-sorted packet is readable and slower rather than wrong — but `02` §10.3
waives the uniqueness query for any table whose sort begins with its key, which is 21 of 35 today
and all 35 under this part. A MUST discharged by a SHOULD is the defect; raising the level is the
cheaper of the two repairs, because the alternative is to run a `GROUP BY` over 286,876,859 rows
that spilled 26 GB when it was last measured (R81 §3).

The fallback stays. Where the scan finds a departure, uniqueness **MUST** be settled by aggregate
rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of
neighbours. A packet reaching that path has already failed.

## 6. The registry drops `sort`

Every table's stored order is now its primary key, so the registry states it once as a rule and
not thirty-five times as data.

The `sort` field is removed from `registry.schema.json` and from every table in
`logical_schemas.json`. A profile derives the order from `primary_key`.

The `determined_by` field is removed with it. `analysis.spike_events` carries the only two
declarations in the registry, and `adjacency_settles_uniqueness` is their only consumer; §4.1 puts
both columns in the key, so nothing computes over them.

## 7. What this does not change

Informative.

- **No packet's rows move except `core.events`.** `analysis.spike_events` is already stored in the
  order §4.1 makes its key, so the change is to the registry rather than to any file.
- **R30's layout stands.** Bucketing by time and sorting by unit within a bucket is why the table
  exists, and §4.1 preserves that order exactly while making it derivable from the key.
- **No table, column or reference is added.** `analysis.spike_events` gains two key columns it
  already holds.
- **`03` §5.2's partitioning rules are untouched.** A partitioned table's order across files is
  still undefined by the profile, and §5's MUST is a statement about a table's contents rather
  than about file boundaries.
- **The thirteen tables with `sort: null` gain a check rather than an obligation.** They are
  already in primary-key order in both packets; what changes is that a departure would now be
  seen.

## 8. Consequence

`registry/build.py` loses its `OVERRIDE` table and the fill pass that produced the thirteen nulls.
`escapewheel_validator.generate.adjacency_settles_uniqueness` reduces to a check that the sort
begins with the key, which is true by construction, so the `aggregate` parameter survives only for
a packet that fails §5.

Tier 1 uniqueness goes from 14 generated `GROUP BY` checks to none on a conforming packet, and
ordering scans go from 22 tables to all 35.

**Both packets must be rebuilt.** `core.events` is renumbered, so every packet built before this
carries `event_id` values a rebuild will not reproduce. R61 §5 makes a correction a rebuild, and
this one re-reads no external resource.

## 9. Open

- **Whether `event_id` needs to exist.** Its stored order is a unique key of four columns the
  table already holds, so the identifier adds a fifth column that nothing outside the table
  references. Striking it is a larger change than this part, and `core.events` is the only table
  where the question arises.
- **Whether an amendment may append.** §5 requires a table to be in key order, and R32's
  amendment writes new resources rather than appending to existing ones, so no case exists yet.
  A profile that permitted appending would need to say whether a later batch may re-enter the
  key range of an earlier one.

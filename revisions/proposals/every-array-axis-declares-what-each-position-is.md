# Every array axis declares what each position is

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-28 |
| **Based on** | `d7c0dcefdb2374d73e5a05c9dff9828afd6f48c4` |
| **Decision domain** | specification |
| **Affects** | Part 03 §6.3; Part 02 §8.3 and Part 02 §11.6; `core.array_dimensions` and `analysis.array_dimensions`; a new core coordinate table for unit axes; `core.unit_electrodes`' description; the reference writer's waveform source; the reader's axis description; the `outside_array_floor` and `unresolved_externals` fixtures; both session packets |

## 1. Problem

A per-unit waveform array has three axes: unit, channel and sample. R20 gives an axis four ways to
declare what its positions are, and the sample axis uses one of them: a numeric origin and step.
The channel axis uses another. It names `core.unit_electrodes` as the table whose rows are its
positions and `channel_index` as the column holding each position. The unit axis declares nothing.

So no fact in a packet says which unit a position of the unit axis holds, and a consumer has
nothing to read but the order. The reference writer filled that order from its analyzer files,
which list units in a different order from `unit_id`. Every consumer reading position *k* as
`unit_id` *k* paired templates with the wrong units, and nothing reported it.

The channel axis's positions also depend on the unit axis. `core.unit_electrodes` is keyed by
unit, so the rows for channel position *j* are those of whichever unit the same array's unit axis
holds at its own position. Nothing declares that dependency, and it breaks R20 §2.4's rule that a
coordinate table is keyed by `array_asset_id`. R100 §2.3 recorded the case and left it open: "a
third case would say whether the tie belongs in the registry or stays the named resource's own
business." The unit axis is that third case.

Two statements about silence disagree. R20 §3 permits an axis to declare no coordinates.
Part 03 §6.3 requires every axis to declare them. The ledger records R20 §3 as applied at
Part 03 §6.3. Commit `4ce6f09`, which compiled v0.2 from v0.1 and the first 64 revisions, wrote
the requirement there and dropped the permission. No rule checks either statement, so the unit axis
breaks the current text without any validator noticing.

## 2. Evidence

### 2.1 The two session packets

The measurements were taken on the two packaged sessions built at the baseline:
`ecephys_786867` (ten probes, 4,505 units) and `ecephys_776259` (twelve probes, 6,781 units). Each
packet has the resource `core.waveform_mean`. Its shape is (4,505, 26, 150) in the first and
(6,781, 26, 150) in the second. `ecephys_776259` also has `core.waveform_sd` with the same shape.
Both packets validate with no errors.

| | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| `core.array_dimensions` rows | 23 | 30 |
| …declaring no coordinate form | 1 | 2 |
| …of which are a waveform array's `unit` axis | 1 | 2 |
| …naming `core.unit_electrodes` | 1 | 2 |
| `core.unit_electrodes` rows | 114,945 | 171,280 |

Across both packets, the only axes that declare nothing are the waveform unit axes. The only axes
whose coordinate table lacks an `array_asset_id` column are the waveform channel axes. Among the 64
fixture packets under `fixtures/packets/`, two carry arrays: `outside_array_floor` and
`unresolved_externals`. All 10 of their axes declare no coordinates, since `fixtures/build.py`
catalogues each array with a `unit` and a `sample` axis and no form.

### 2.2 The unit axis held units out of `unit_id` order

The first test reads position *k* as `unit_id` *k*. Each position's template has signal on some
number of channels. The masked template leaves every channel outside a unit's sparsity at zero, so
under the right mapping that number is at most the unit's `core.unit_electrodes` row count.

| positions under the `unit_id` *k* reading | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| more live channels than that unit has electrodes, which is impossible | 558 | 1,680 |
| live channel count equal to the unit's electrode count | 3,354 | 3,368 |

The true order was recovered by fitting each sorting run's units, in `unit_id` order, as one
contiguous block of positions. Exactly one run fitted at each step, and that run was taken. The
blocks follow the analyzer's run order, not `sorting_run_id` order: `sorting_run_id` 0, 2, 3, 4, 9,
1, 5, 6, 7, 8 in `ecephys_786867`, and 4 to 9, 11, 0 to 3, 10 in `ecephys_776259`. Under that mapping, **3,971 of 4,505** positions in
`ecephys_786867` and **6,781 of 6,781** in `ecephys_776259` hold a unit other than `unit_id` *k*.
In the first packet only the first block, 534 units, is in place.

### 2.3 The writer fix holds by a convention no rule states

Since commit `0ab4e89`, the reference writer's waveform source places the units in `unit_id`
order. It writes an empty template for a unit with no analyzer template, so every unit keeps a
position. Rebuilt with it, `core.waveform_mean` has every position at the live-channel count of
`unit_id` *k*: **4,505 of 4,505** in `ecephys_786867` and **6,781 of 6,781** in `ecephys_776259`.
In `core.waveform_sd`, 6,779 positions match and 2 have fewer live channels, where a deviation is
exactly zero on a contact; no position has more. Every table except the build run's timestamps
matches the baseline build row for row.

The fix holds only because of how the writer numbers identifiers. Part 05 §4.3 requires numbering
to be packet-wide and deterministic, not to follow any order, and the writer numbers units in the
sorted order of their composed names. An array holding one probe's units, or a packet holding two
sessions, would put a different unit at position *k*. The waveform source records no mapping, and
no coordinate form can express one. A labelled axis needs a table with one row per position of this
array and a `structural_index` column for the position, and no such table exists for units.

### 2.4 R20 §2.4's keying rule is stated nowhere

R20 §2.4 says a coordinate table is keyed by `array_asset_id` alongside its position column. The
ledger disposes of it as `registry`, pointing at the whole of `core.array_dimensions`. No
declaration there or on any coordinate table expresses the rule. The registry can require a named
column to be a `structural_index` (R100 §2.2), but not that its table carries an `array_asset_id`.
No current part states the rule in prose.

The two coordinate tables in use differ:

| table | primary key | narrowed to one axis by |
|---|---|---|
| `core.array_channels` | `array_asset_id`, `channel_index` | its `array_asset_id` and `axis_index`, which reference `core.array_dimensions` |
| `core.unit_electrodes` | `session_id`, `unit_id`, `electrode_id` | the unit at the same array's unit-axis position, which nothing declares |

### 2.5 A reader sketch refuses the waveform arrays

An uncommitted reader function resolves every axis of a catalogued array into its coordinates. It
resolves all 22 LFP arrays in the two packets. It refuses `core.waveform_mean` and
`core.waveform_sd` at the channel axis, whose named table has no `array_asset_id`. That refusal is
the only safe behaviour, because any other answer would be a guess, as §2.2 shows.

### 2.6 Two registry rules share one predicate

`core.array_dimensions.labelled_axis_complete` and `core.array_dimensions.coordinate_pair_complete`
both select rows whose `coordinate_resource` and `coordinate_position_column` are not null
together. R100 §2.2 added the second. Only their messages differ.

## 3. Desired outcome and constraints

- A consumer holding an array and its declared coordinates can say which entity every position of
  every axis stands for, without knowing how the writer that built it numbers identifiers.
- A packet whose array axis says nothing about its positions is detectably non-conforming, so the
  defect in §2.2 is reported instead of discovered in an analysis.
- An axis whose positions depend on another axis's position says so, in a declaration a generic
  consumer can follow without knowing the named table.
- `core.unit_electrodes` keeps its meaning. It is a fact about units that holds with no waveform
  array present.
- R20 §2.4's reason stands: coordinates belong to one array, not to a dimension name. A typed
  reference is still a table's own declaration and never a generic column.
- The cost stays proportional to the axis. One row per unit position is acceptable. One row per
  unit-channel pair per array would repeat `core.unit_electrodes`.

## 4. Options and tradeoffs

### 4.1 What a unit axis declares

- **Keep silence and restore R20 §3's permission.** No schema change, but the defect in §2.2 stays
  conforming and undetectable.
- **Read position *k* as `unit_id` *k* by convention.** No schema change. An identifier is not a
  position, and Part 02 gives the two different roles. Part 05 §4.3
  does not fix the numbering order, and an array holding a subset of the units breaks the
  convention.
- **An irregular axis whose 1-D array holds `unit_id` values.** It uses an existing form, but an
  array value is not a reference. Nothing checks that the value names a unit, and the key's type is
  the array's data type.
- **A position column on `core.units`.** It ties a position to the unit rather than to an array,
  so two arrays holding different subsets cannot both use it.
- **A core coordinate table for unit axes.** It has one row per position of one array's unit axis:
  `session_id`, `array_asset_id`, `axis_index`, a `structural_index` position column, and
  `unit_id` referencing `core.units`. Its key is the array and the position, and it references the
  axis row, following `core.array_channels`. The cost is 4,505 rows in `ecephys_786867` and 13,562
  in `ecephys_776259`, one set for each of its two arrays. **Preferred direction.**

### 4.2 How a channel axis that depends on the unit declares it

- **Keep R100 §2.3's position that narrowing is the resource's own business, and state the rule
  for `core.unit_electrodes` in Part 02.** The change is the smallest, but a consumer has to know
  each such table, and the reader sketch in §2.5 would special-case one resource by name.
- **A per-array coordinate table for per-unit channels.** It holds the unit position, channel
  position and electrode for each array. It satisfies R20 §2.4 as written, but it repeats
  `core.unit_electrodes` once per array (114,945 rows per array in `ecephys_786867`, 171,280 in `ecephys_776259`), and the two
  statements can disagree.
- **A declared scope axis.** An axis row names another axis of the same array whose label narrows
  the named table's rows. The rows for position *j* at that axis's position *i* are those for the
  entity *i* is labelled with, whose position column holds *j*. `core.unit_electrodes` is unchanged,
  and a generic consumer follows two declarations. **Preferred direction.**

### 4.3 Whether an axis may declare nothing

- **Keep Part 03 §6.3's requirement, add a rule reporting an axis with no form, and record R20 §3's
  permission as superseded.** Affected: 3 axes in the two packets and 10 fixture axes.
  **Preferred direction.**
- **Restore R20 §3's permission in Part 03 §6.3.** This matches the accepted revision, but it keeps
  §2.2's defect conforming.

Under each preferred option, R20 §2.4's keying rule becomes a stated rule. A coordinate table's rows
are narrowed to one axis by the array's key, or by a declared scope axis, and by nothing else. The
rule is placed in the part that owns array axes. The ledger's `registry` disposition for R20 §2.4
is replaced when the revision is accepted.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic standard (Part 01) | unchanged; it says nothing about array axes |
| logical resources (Part 02, registry) | affected: one new core table; one new nullable column on `core.array_dimensions` and its analysis copy; a rule for silence and a rule for a scope axis naming an axis of the same array; Part 02 §11.6's index gains the table; Part 02 §8.3 says how a by-position discriminator is narrowed by a scope axis |
| physical profile (Part 03 §6.3) | affected: the keying rule and the scope axis are stated where axis coordinates are |
| packet manifest (Part 04) | unchanged; no resource-entry field changes |
| import and validation (Part 05) | unchanged prose; the new rules run in Tier 2, and whether Tier 1 generates the scope-axis check is unknown |
| reference writer | affected: the waveform source writes the unit coordinate table and declares the channel axis's scope |
| reference reader | affected: the uncommitted axis description resolves a scope axis instead of refusing |
| reference validator | affected: new rules; nothing else unless Tier 1 generates the scope check |
| extension registries | unchanged; no extension declares an array |
| adapters (Part 12) | unchanged; the protocol carries tables and arrays whatever their columns |
| existing packets | affected: both session packets are rebuilt, and each gains one set of unit-axis rows per waveform array |
| conformance fixtures | affected: `outside_array_floor` and `unresolved_externals` declare forms on their 10 axes, or are deliberately non-conforming for that reason |
| revision tooling | unchanged |
| documentation | affected: Part 08's table listing gains the new table |

§2.6's duplicate rule is maintenance independent of this proposal.

## 6. Open questions

1. **How a scope axis identifies the shared entity.** One way is to infer it from the references
   both tables declare to one target, since the unit coordinate table and `core.unit_electrodes`
   both reference `core.units`. The other is to name the joining columns explicitly. The preferred
   direction is inference, with explicit naming added only when a table declares two references
   that could qualify.
2. **Whether the new table covers units only.** R20 §2.4 argues against a generic entity table,
   because the typed key differs in width. R20 §7 left trial coordinate tables to a
   materialization. The preferred direction is units only.
3. **Whether any axis has positions that mean only their order.** None was found in the packets or
   fixtures other than the defect above. If one exists, requiring a form would need a fifth form
   for an ordinal axis. The preferred direction adds none.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

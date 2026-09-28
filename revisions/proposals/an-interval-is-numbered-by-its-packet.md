# An interval is numbered by its packet

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-28 |
| **Based on** | `8938863b52926f43ec71b26245ed45836ca08369` |
| **Decision domain** | specification |
| **Affects** | Part 02 §12, beside §12.1's unit identity; `core.intervals`; `dynamic_foraging.trials`, `vr_foraging.sites` and `vr_foraging.site_odors`; the reference writer's NWB source and numbering; the reference reader's interval accessor; the fixtures carrying intervals; both session packets |

## 1. Problem

`core.intervals` holds every bounded span of experimental time a packet declares, whatever its kind
(Part 01 §3.10). Each row names its kind in `interval_kind`, the dotted resource ID of the table
that specialises it, and carries the source's own number for it in `interval_id`, whose identity is
`carried`. The primary key is (`session_id`, `interval_kind`, `interval_id`).

### 1.1 No single identifier names an interval

The kind is in the key because a source numbers each kind of interval separately, so a session
holding task trials and stimulation pulses can hold a trial 0 and a pulse 0. An interval is
therefore identified by three columns, and anything referring to one carries all three.

Part 02 §8.3's paired value holds one identifier, so it cannot name an interval. The companion
proposal `every-array-axis-declares-what-each-position-is` labels an axis position with one integer
identifier, so no array axis can stand for trials. That is the axis R20 §7 anticipated for a
trial × unit × time array. A core axis cannot name `dynamic_foraging.trials` in place of
`core.intervals` either: R20 §5.1 keeps a core axis to core resources, and the rule
`core.array_dimensions.coordinate_resource_is_core` reports one that is not.

### 1.2 Each detail table carries a constant column to widen its reference

Part 02 §8.3 requires a detail table's reference to its discriminated table to cover that table's
whole key. `dynamic_foraging.trials` and `vr_foraging.sites` each carry `interval_kind` holding one
value in every row, `dynamic_foraging.trials` and `vr_foraging.sites` respectively, only so that
their references reach (`session_id`, `interval_kind`, `interval_id`). Both columns describe
themselves as carrying the key and resolving nothing a consumer of the row does not already know.

### 1.3 R81 resolved the same shape for units

R81 §1.2 found a carried unit label recurring across sorting runs, and a unit's identity grown to
four columns to keep it unique. R81 §2.1 made `unit_id` assigned and the key `unit_id` alone, which
Part 02 §12.1 now states. The carried interval number recurs across kinds in the same way, and
identity has grown `interval_kind` to keep it unique.

## 2. Evidence

- **Both session packets hold one kind.** `core.intervals` has 450 rows in `ecephys_786867` and 708
  in `ecephys_776259`, all of kind `dynamic_foraging.trials`, with `interval_id` running 0 to 449
  and 0 to 707. No two kinds collide in either packet, so the composite key is doing no work there.
- **The sources number from zero.** The reference writer's NWB source passes the NWB's
  `intervals/trials/id` through as `interval_id` and uses the row's offset where the NWB has none.
  The `dynamic_foraging` tables in both packets come from a delivery that takes `trial_id` from the
  same `id`. The interval-kinds conformance probe builds a session of 400 task trials and 120
  optotagging pulses on one clock; a source numbering each kind from zero would give 120 numbers
  to two intervals each.
- **Two tables reference intervals, and one references them in turn.** `dynamic_foraging.trials`
  and `vr_foraging.sites` reference `core.intervals` through the constant column of §1.2.
  `vr_foraging.site_odors` references `vr_foraging.sites` by (`session_id`, `site_id`). No core
  table references `core.intervals`, and `dynamic_foraging.blocks` carries its own ticks rather
  than rows of `core.intervals`.
- **Ordering units by their label is read two ways.** Part 02 §12.1 numbers units by ascending
  `local_unit_label`, a string. The reference writer orders it as a number, which differs from
  ascending string order for 4,486 of 4,505 units in `ecephys_786867` and 6,757 of 6,781 in
  `ecephys_776259`: as a string, `"10"` precedes `"2"`. The numbering rule for intervals should not
  inherit that ambiguity.

## 3. Desired outcome and constraints

- One integer identifies an interval, so a paired value or an axis label can name one.
- Intervals of two kinds that a source numbers alike coexist.
- The source's own number survives, so a consumer can relate an interval to its source.
- Two builds from the same sources number intervals identically, as Part 05 §4.3 and R75 require
  of any assigned identifier, and a validator can check the order from the table alone.
- A detail table references core through `core.intervals`' whole key.
- An adapter still hands over the source's names and never a number, as Part 12 §5 requires.

## 4. Options and tradeoffs

The preferred direction applies R81's pattern to intervals.

### 4.1 A packet numbers its intervals

`core.intervals.interval_id` becomes assigned: an integer the packet gives each interval, unique
within it, and the primary key becomes (`interval_id`). `session_id` and `interval_kind` stay
required columns, and `interval_kind` stays the discriminator: resolution by shared key now joins on
`interval_id` alone.

Part 02 §8.2 then requires `core.intervals` to declare `interval_name`, unique within the packet,
recording what the number stands for. The source's own number moves to `local_interval_label`, a
string like every source-provenance label Part 02 §4 lists, and null where a source numbers
nothing. A consumer relating an interval to its source uses (`session_id`, `interval_kind`,
`local_interval_label`), as Part 02 §12.1 has one use (`sorting_run_id`, `local_unit_label`) for a
unit.

### 4.2 The numbering follows time within each kind

A writer numbers intervals from zero by ascending (`session_id`, `interval_kind`, `start_tick`,
`stop_tick`), breaking any remaining tie by `local_interval_label`. Every column is in the table, so
a declared rule can check the numbering, and a consumer reading a kind in `interval_id` order reads
it in time order.

`core.intervals` is stored in its primary key's order (Part 03 §5.3), so the numbering also sets its
layout. Kind-major numbering keeps each kind contiguous, as run-major numbering keeps a probe's
spikes contiguous in `core.spike_events`.

| alternative | why it falls short |
|---|---|
| ascending (`session_id`, `interval_kind`, `local_interval_label`), as §12.1 orders units | the label is a string, so the order is read two ways (§2), and a source numbering nothing leaves it undefined |
| the order the source lists intervals in | nothing in the packet records it, so no rule can check it |
| time order across kinds | the kinds interleave in the stored table, and reading one kind scans all of them |

### 4.3 Detail tables reference one column

`dynamic_foraging.trials.trial_id` and `vr_foraging.sites.site_id` become assigned identifiers
referencing `core.intervals.interval_id` alone, and each table's constant `interval_kind` is struck.
Part 02 §8.3 requires a detail table's primary key to begin with the discriminated table's own
identifier, so the keys become (`trial_id`) and (`site_id`). `session_id` stays a required column
of each and references `core.sessions` directly, since a reference without `session_id` is not a
session-preserving edge (Part 02 §7.1).

`vr_foraging.site_odors` follows: its `site_id` becomes assigned, because a reference pairs
identifiers of one identity (Part 02 §7), its key becomes (`site_id`, `odor_channel_index`), and its
reference to `vr_foraging.sites` narrows to `site_id`.

Part 02 §8.3's provision for a constant column stays as the rule for any composite discriminated
key, with no table currently using it.

### 4.4 An adapter names an interval by its source label

Under Part 12 §5 an adapter hands over each identifier as the name its source used, and the build
numbers it. The name a source uses for an interval is its own number, which repeats across kinds,
so the build identifies an interval by its kind and that label. The adapter producing
`core.intervals` hands over the label with the row's `interval_kind`; an adapter producing a detail
table hands over the same label, and the table it delivers is the kind. Neither adapter needs the
other's output, and the build composes `interval_name`. This changes no Part 12 term.

### 4.5 Alternatives to numbering intervals

| alternative | why it falls short |
|---|---|
| keep the carried number and the composite key | no single identifier names an interval, so no axis can hold trials, and two constant columns remain |
| keep the carried number and key on it alone | two kinds a source numbers alike collide |
| add an assigned identifier beside the composite key | each row has two keys and each reference picks one |
| label trial axes through `dynamic_foraging.trials` | a core axis cannot name an extension resource (R20 §5.1), and that table's key is composite too |

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose (Part 01) | unchanged; §3.10 requires an interval's session, bounds and kind, which all stay |
| logical prose (Part 02) | affected: a subsection of §12 beside §12.1 states interval identity and its numbering order; §8.3 is unchanged |
| registry declarations | affected: `core.intervals` changes `interval_id`'s identity and its key, and gains `interval_name` and `local_interval_label`; the three extension tables in §4.3 change identities, keys and references, and two lose `interval_kind`; a rule checks the numbering order |
| physical profile (Part 03) | unchanged; §5.3 already sorts `core.intervals` by its key |
| packet manifest (Part 04) | unchanged |
| validation and import (Part 05) | unchanged prose; §4.3 already requires identifiers to be assigned packet-wide before any table is written |
| extension registries | affected: `dynamic_foraging` and `vr_foraging` advance their versions |
| reference writer | affected: the NWB source hands over the source's label, and numbering identifies an interval by its kind and label |
| reference reader | affected: the interval accessor and discriminator resolution join on `interval_id` alone |
| reference validator | affected only through the registry: the generated reference checks narrow |
| adapters (Part 12) | unchanged protocol; the delivery building `dynamic_foraging` tables hands over the source's trial number as a name, which it does for `block_id` already |
| existing packets | affected: both session packets are rebuilt; numbering by §4.2's order reproduces every existing `interval_id` in both, 450 of 450 and 708 of 708 |
| conformance fixtures | affected: the fixtures carrying intervals gain the new columns, and a fixture with two kinds numbered alike becomes the positive case; a misordered numbering is the negative case |
| revision tooling | unchanged |
| documentation | affected: the interval-kinds conformance probe's notes, and Part 08's example packet where it shows `core.intervals` |

## 6. Open questions

None would change the decision. How an axis names an interval is the companion proposal's; this
one only makes an interval nameable by one identifier.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

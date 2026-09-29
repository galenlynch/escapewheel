# An interval is numbered by its packet

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `b773b21810ee648c36b2b64cbdf361f864946300` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§8.3, 9.2 and 12; Part 08 §§2 and 3; the core registry; the `dynamic_foraging` and `vr_foraging` extension registries |
| **Depends on** | R147 §3.8 (the core registry version this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2 and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

`core.intervals` holds every bounded span of experimental time a packet declares, whatever its kind
(Part 01 §3.10). Each row names its kind in `interval_kind`, the dotted resource ID of the table
that specialises it, and carries the source's own number for it in `interval_id`, whose identity is
`carried`. The primary key is (`session_id`, `interval_kind`, `interval_id`), because a source
numbers each kind of interval separately, so a session holding task trials and stimulation pulses
can hold a trial 0 and a pulse 0.

Three columns therefore identify an interval, and two consequences follow:

- **No single identifier names an interval.** A paired value of Part 02 §8.3 holds one identifier,
  and so does an axis label under R147, so no array axis can stand for trials.
- **Each specialising table carries a constant column.** Part 02 §8.3 requires a specialising
  table's reference to cover the discriminated table's whole key, so `dynamic_foraging.trials` and
  `vr_foraging.sites` each carry an `interval_kind` holding its own resource ID in every row.

This revision has the packet number its intervals, as R81 has it number its units. `interval_id`
becomes an assigned identifier and the whole key; the source's number moves to a label column; a
writer numbers intervals in an order a declared rule checks; and a specialising table references
an interval by `interval_id` alone, dropping its constant column.

The change is structural because it revises Part 02 §8.3's shared-key paragraph, which states that
a detail table carries the discriminator's value as a constant column. An appended section would
leave that statement describing no table.

### 1.1 Structural crosswalk

Every affected existing section carries a canonical anchor, so no bootstrap is needed. The new
section is created with its anchor.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §8.3, the shared-key paragraph's constant column | revise in place | same section | a detail table carries the discriminator's value only where the discriminator is a member of the discriminated table's key | §3.3 |
| Part 02 §9.2, the core registry version | revise in place | same section | the core registry version advances to 0.10.0 | §3.4 |
| none | add | a new final subsection of Part 02 §12, *Interval identity*, anchor `ew-interval-identity` | a packet assigns `interval_id` in a declared order, and the source's number is a label | §3.1, §3.2 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none | none |

## 2. Background

Section 2 is informative. The measurements use the two session packets the reference writer built
at this baseline, the `packet-wf` builds: `ecephys_786867`, ten probes and 4,505 sorted units, and
`ecephys_776259`, twelve probes and 6,781 sorted units. Queries ran in DuckDB 1.5.5 over their
Parquet tables.

### 2.1 The session packets hold one kind of interval, numbered from zero

`core.intervals` has 450 rows in `ecephys_786867` and 708 in `ecephys_776259`, all of kind
`dynamic_foraging.trials`, with `interval_id` running 0 to 449 and 0 to 707. The reference writer's
NWB source passes the NWB's `intervals/trials/id` through as `interval_id`, and takes each
`dynamic_foraging.trials.trial_id` from the same `id`. No two kinds collide in either packet, so
the kind in the key does no work there.

Of the 64 fixture packets under `fixtures/packets/`, 63 carry `core.intervals`, each holding the
valid packet's two trials, numbered 1 and 2; `dup_pk` adds a third row repeating trial 1. The
interval-kinds conformance probe builds a session of 400 task trials and 120 optotagging pulses on
one clock; a source numbering each kind from zero gives 120 numbers to two intervals each.

### 2.2 R81 resolved the same shape for units

R81 §1.2 found a carried unit label recurring across sorting runs, and a unit's identity grown to
four columns to keep it unique. R81 §2.1 made `unit_id` assigned and the whole key, which
Part 02 §12.1 now states, and a consumer relates a unit to its source through (`sorting_run_id`,
`local_unit_label`). The carried interval number recurs across kinds in the same way, and the key
has grown `interval_kind` to keep it unique.

### 2.3 Numbering by time reproduces every existing identifier

Numbering each packet's intervals from zero by ascending (`session_id`, `interval_kind`,
`start_tick`, `stop_tick`) reproduces every existing `interval_id`, 450 of 450 and 708 of 708. No
two intervals of one kind in one session share both bounds in either packet, so no tie arises
there.

The order uses no label. Part 02 §12.1 numbers units by ascending `local_unit_label`, a string, and
the reference writer compares it as a number. The two orders differ for 4,486 of 4,505 units in
`ecephys_786867` and 6,757 of 6,781 in `ecephys_776259`, since as a string `"10"` precedes `"2"`.
An interval's bounds already order it, so a label could only break a tie between intervals of one
kind with equal bounds, and neither packet holds one.

### 2.4 Three extension tables reference intervals through the composite key

`dynamic_foraging.trials` and `vr_foraging.sites` reference `core.intervals` on (`session_id`,
`interval_kind`, `trial_id`) and (`session_id`, `interval_kind`, `site_id`), through the constant
column of §1. `vr_foraging.site_odors` references `vr_foraging.sites` on (`session_id`,
`site_id`). No core table references `core.intervals`, and `dynamic_foraging.blocks` carries its
own ticks. Of the registry's shared-key discriminators, only `core.intervals.interval_kind` is a
member of its own table's key, so the constant column has no use once §3.1 changes that key.

The rule `dynamic_foraging.blocks.contains_its_trials` joins a trial to its interval on the
constant column. Seven `vr_foraging.sites` rules rely on how sites are numbered:
`a_patch_is_contiguous` and `a_block_is_contiguous` require a patch's or a block's `site_id` values
to be consecutive, and the five rules checking the `site_index_*` columns count sites in `site_id`
order. All seven hold under §3.2's order, which keeps one session's intervals of one kind
consecutive and in time order, provided no two sites of a session share both bounds. No packet or
fixture carries `vr_foraging` tables.

### 2.5 The declared rules were run on both packets

Each packet's `core.intervals` was renumbered by §3.2's order, with its source number as
`local_interval_label`, and its `dynamic_foraging.trials` stripped of `interval_kind`. Every trial
still names an interval. §3.2's rule and the revised `contains_its_trials` both pass the Part 11
static check and return no rows. Swapping two identifiers draws 2 rows from §3.2's rule, a gap
after the hundredth identifier draws 350 and 608, and moving one trial's start outside its block
draws 1 from `contains_its_trials`. Two trials with equal bounds draw no row from §3.2's rule
whichever is numbered first. The 17 `vr_foraging.sites` rules pass the static check against
the revised declarations.

### 2.6 Alternatives

| alternative | why it falls short |
|---|---|
| keep the carried number and the composite key | no single identifier names an interval, so no axis can hold trials, and two constant columns remain |
| keep the carried number and key on it alone | two kinds a source numbers alike collide |
| add an assigned identifier beside the composite key | each row has two keys, and each reference picks one |
| label a trial axis through `dynamic_foraging.trials` | a core axis names only core resources, and that table's key is composite too |
| number by (`session_id`, `interval_kind`, `local_interval_label`), as Part 02 §12.1 orders units | the label is a string read two ways (§2.3), and a source numbering nothing leaves the order undefined |
| break ties between equal bounds by `local_interval_label` | it decides no identifier in either packet, and it needs an order for labels that Part 02 §12.1 leaves unstated for units |
| number in the order the source lists intervals | nothing in the packet records that order, so no rule can check it |
| number in time order across kinds | the kinds interleave in the stored table, and reading one kind scans all of them |

## 3. Decision

Four subsections give the interval its identifier, fix the order that numbers it, have specialising
tables reference it by that identifier, and advance the registry versions. The crosswalk in §1.1
places each.

### 3.1 A packet numbers its intervals

`interval_id` identifies an interval on its own. A writer assigns it, and records the number or
name its source gave the interval in `local_interval_label`, null where the source gave none. A
consumer relating an interval to anything outside the packet uses (`session_id`, `interval_kind`,
`local_interval_label`). Part 02 §12's new subsection *Interval identity* states this with §3.2.

The incorporated core registry MUST declare `core.intervals` with primary key (`interval_id`) and
these changed or added columns, its other columns, references and rules unchanged:

| column | type | presence | role | identity | vocabulary | description |
|---|---|---|---|---|---|---|
| `interval_id` | `int32` | `required` | `identifier` | `assigned` | — | Interval ID, assigned by the packet in order of session, kind and bounds. |
| `interval_name` | `string` | `required` | `data` | — | `free` | What `interval_id` stands for, unique within the packet. |
| `local_interval_label` | `string` | `nullable` | `data` | — | `free` | The source's own number or name for this interval; undefined base, not an offset. |

`start_tick` and `stop_tick` describe "the interval" in place of "the trial". `interval_kind`
remains a `required` discriminator resolving `required` by a shared key, which is now
`interval_id`.

### 3.2 Intervals are numbered by kind and time

A writer MUST number a packet's intervals from 0, in ascending order of `session_id`,
`interval_kind`, `start_tick` and `stop_tick`, comparing kinds by Unicode scalar value. Intervals of
one session and kind with equal bounds MAY be numbered in either order. `core.intervals` is stored
in its key's order (Part 03 §5.3), so each kind of one session is one contiguous run.

The incorporated core registry MUST declare this rule on `core.intervals`, at level `error`:

| id | message |
|---|---|
| `core.intervals.numbered_in_order` | `interval_id does not number intervals from 0 by session, kind and bounds` |

```sql
SELECT interval_id, expected
FROM (
  SELECT interval_id,
    ROW_NUMBER() OVER (ORDER BY session_id, interval_kind, start_tick, stop_tick, interval_id) - 1 AS expected
  FROM core.intervals
) AS numbered
WHERE interval_id <> expected
```

### 3.3 A specialising table references an interval by `interval_id` alone

Part 02 §8.3's shared-key reference covers the discriminated table's whole key, and a detail table
carries the discriminator's value as a constant column only where the discriminator is a member of
that key.

The `dynamic_foraging` registry MUST declare `dynamic_foraging.trials` with primary key
(`trial_id`), without `interval_kind`, with `trial_id` an `int32` `required` `identifier` of
identity `assigned`, and with these references in place of its reference to `core.intervals`:

- `trial_id` to `core.intervals.interval_id`; and
- `session_id` to `core.sessions.session_id`.

Its reference to `dynamic_foraging.blocks` is unchanged. Its rule
`dynamic_foraging.blocks.contains_its_trials` MUST read:

```sql
SELECT t.session_id, t.trial_id
FROM dynamic_foraging.trials AS t
JOIN dynamic_foraging.blocks AS b ON b.session_id = t.session_id
  AND b.block_id = t.block_id
JOIN core.intervals AS c ON c.session_id = t.session_id
  AND c.interval_id = t.trial_id
WHERE c.start_tick < b.start_tick
  OR c.stop_tick > b.stop_tick
```

The `vr_foraging` registry MUST declare:

- `vr_foraging.sites` with primary key (`site_id`), without `interval_kind`, with `site_id` an
  `int32` `required` `identifier` of identity `assigned`, and with references from `site_id` to
  `core.intervals.interval_id` and from `session_id` to `core.sessions.session_id` in place of its
  reference to `core.intervals`; and
- `vr_foraging.site_odors` with primary key (`site_id`, `odor_channel_index`), with `site_id` of
  identity `assigned`, and with references from `site_id` to `vr_foraging.sites.site_id` and from
  `session_id` to `core.sessions.session_id` in place of its reference to `vr_foraging.sites`.

Neither registry declares `trial_name` or `site_name`: each identifier is a source member of a
reference, so neither table owns it (Part 02 §8.2).

### 3.4 The core registry version advances

The incorporated core registry's `registry_version` MUST advance from `0.9.0`, which
R147 assigns, to `0.10.0`. The `dynamic_foraging` and
`vr_foraging` registries advance their own versions, which the core specification does not assign
(Part 09 §5.5).

## 4. What this does not change

Part 01 §3.10 is unchanged: an interval still belongs to one session, has bounds on a declared
clock, and declares its kind. `interval_kind` stays the discriminator and resolves by the shared
key. Part 12 gains no term: an adapter hands over an interval's identifier as its source's name
for the interval (Part 12 §5), and no adapter needs the number the build assigns.

## 5. Consequence

Every packet carrying `core.intervals` is rebuilt, and binds core registry 0.10.0. In both session
packets every `interval_id` keeps its value, `local_interval_label` records the NWB's `id` as a
string, and `dynamic_foraging.trials` loses a constant column. The fixture packets' two trials
become 0 and 1, labelled `"1"` and `"2"`.

These accepted clauses change: R54 §2.2, which put the kind in the key so each kind keeps its
source's numbering, is superseded by §§3.1 and 3.2. R54 §2.1's ledger entry gains a note that
§3.1 replaces the identity and key it declared, and R90 §§3.3 and 3.6 gain notes that their
constant columns are struck and the whole key is now `interval_id`. Their rules stand.
`revisions/registry-targets.toml`'s target for R54 §2.2 retires with the clause.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §3.10 requires an interval's session, bounds and kind, and all three stay. | None required. |
| logical prose and registry | Part 02 §8.3 takes §3.3's sentence, Part 02 §12 gains *Interval identity* with its anchor, and Part 02 §9.2 takes §3.4's version. The core registry source declares §3.1's columns and key and §3.2's rule. `registry/check.py`'s naming exceptions for `dynamic_foraging.trials.interval_kind` and `vr_foraging.sites.interval_kind` are removed with the columns, and its expected core version follows. | `evidence/R<N>.json` names each anchor and registry pointer; `registry/check.py` passes. |
| physical profiles | Unchanged. Part 03 §5.3 already stores `core.intervals` in its key's order. | None required. |
| packet manifest and JSON Schemas | Unchanged. No manifest field names an interval. | None required. |
| validation and import | Unchanged prose. Part 05 §4.3 already has a writer assign identifiers packet-wide before any table is written, which covers `interval_id`. | The corpus variants below. |
| extensions | `dynamic_foraging` and `vr_foraging` take §3.3's declarations and advance their versions. `aind_opto` and `aind_unit_qc` reference no interval. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The writer's NWB source hands over the NWB's `id` as the label for the interval and its trial row; its numbering assigns `interval_id` by §3.2 and composes `interval_name`. The reader's interval accessor and discriminator resolution join on `interval_id` alone. The validator's generated reference checks follow the registry, and its join-name comment for `dynamic_foraging.trials` follows the new reference. No `escapewheel-aind` adapter produces an interval table. | The writer, reader and validator suites; both session packets rebuilt and validated with no error. |
| conformance fixtures and tests | `fixtures/build.py` writes the new columns and numbers from 0. Positive variants hold two kinds numbered alike by their source, and two trials with equal bounds numbered in each order; negative variants hold a misordered numbering and a gap, each drawing `core.intervals.numbered_in_order`, which `dup_pk`'s repeated interval also draws. `conformance/interval-kinds/probe.py` and `prototype/registry-codegen/` follow the declarations. | `fixtures/corpus.py`. |
| revision process and tooling | The ordinary ledger and evidence records, and the superseded and annotated clauses above. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | `registry/tables.md` renders the new columns; Part 08 §§2 and 3 regenerate with the new registry versions; the specification README's identifier table, `framework.py`'s expected version, the combined specification and the heading index follow. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1 and 3.2 are `applied` at Part 02's *Interval identity*, and `registry` for §3.1's
declarations and §3.2's rule. §3.3 is `applied` at Part 02 §8.3 and `registry` for the
extension declarations. §3.4 is `applied` at Part 02 §9.2. Each is placed by canonical anchor.

These cases distinguish the new rules from the current ones:

- a packet holding trial 0 and optotagging pulse 0 of one session, numbered by §3.2 and both
  labelled `"0"`, is conforming, as it is today only through the composite key;
- a packet holding two trials of one session with equal bounds is conforming whichever is numbered
  first;
- a packet whose two trials are numbered 1 and 2 draws `core.intervals.numbered_in_order`, where
  the current registry accepts it;
- a packet numbering a later trial before an earlier one draws the same rule;
- a packet repeating an `interval_id` draws the numbering rule beside the primary-key check; and
- a `dynamic_foraging.trials` row whose `trial_id` names no interval draws the generated reference
  check on `core.intervals.interval_id`.

The positive cases are the two rebuilt session packets and the valid corpus packet.

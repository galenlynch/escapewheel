# An interval is numbered by its packet

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `4d4501063a42b2c9815f8a0dd97555c4dcc5f2e3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§4, 8.3, 9.2 and 12; Part 08 §§2 and 3; the core registry |
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
- **Each specialising table carries a constant column.** Part 02 §8.3 requires a shared-key
  reference to cover the discriminated table's whole key, so a table specialising an interval
  carries an `interval_kind` column holding its own resource ID in every row.

This revision has the packet number its intervals, as R81 has it number its units. `interval_id`
becomes an assigned identifier and the whole key; the source's number moves to a label column, which
a declared rule keeps unique within each session and kind; a writer numbers each session's intervals
of one kind consecutively, in an order a declared rule checks; and a specialising table references
an interval by `interval_id` alone, dropping its constant column.

The change is structural because it revises Part 02 §8.3's shared-key paragraph, which states that a
detail table carries the discriminator's value as a constant column. An appended section would leave
that statement describing no table.

### 1.1 Structural crosswalk

Every affected existing section carries a canonical anchor, so no bootstrap is needed. The new
section is created with its anchor.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §4, the source-provenance labels | extend in place | same section | `local_interval_label` is a source-provenance label | §3.1 |
| Part 02 §8.3, the shared-key paragraph's constant column | revise in place | same section | a detail table carries the discriminator's value only where the discriminator is a member of the discriminated table's key | §3.3 |
| Part 02 §9.2, the core registry version | revise in place | same section | the core registry version advances to 0.10.0 | §3.4 |
| none | add | a new final subsection of Part 02 §12, *Interval identity*, anchor `ew-interval-identity` | a packet assigns `interval_id` in a declared order, and the source's number is a label | §3.1, §3.2 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none | none |

## 2. Background

Section 2 is informative. The measurements use the two session packets the reference writer built
under this baseline's registry, the `packet-r147` builds: `ecephys_786867`, ten probes and 4,505
sorted units, and `ecephys_776259`, twelve probes and 6,781 sorted units. Queries ran in DuckDB
1.5.5 over their Parquet tables.

### 2.1 The session packets hold one kind of interval, numbered from zero

`core.intervals` has 450 rows in `ecephys_786867` and 708 in `ecephys_776259`, all of kind
`dynamic_foraging.trials`, with `interval_id` running 0 to 449 and 0 to 707. The reference writer's
NWB source passes the NWB's `intervals/trials/id` through as `interval_id`, and takes each
`dynamic_foraging.trials.trial_id` from the same `id`. No two kinds collide in either packet, so the
kind in the key does no work there.

Of the 76 fixture packets under `fixtures/packets/`, 75 carry `core.intervals`, each holding the
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

Numbering each packet's intervals from zero by ascending (`session_id`, `interval_kind`, `clock_id`,
`start_tick`, `stop_tick`) reproduces every existing `interval_id`, 450 of 450 and 708 of 708. Each
packet's trials sit on one clock, and no two intervals of one kind in one session share both bounds,
so no tie arises there.

The clock precedes the bounds because ticks on two clocks do not compare. Part 01 §3.10 puts each
interval on a declared clock and does not require one clock per kind, so an order by bounds alone
would interleave two clocks' intervals by tick value rather than by time.

The order uses no label. Part 02 §12.1 numbers units by ascending `local_unit_label`, a string, and
the reference writer compares it as a number. The two orders differ for 4,486 of 4,505 units in
`ecephys_786867` and 6,757 of 6,781 in `ecephys_776259`, since as a string `"10"` precedes `"2"`. An
interval's bounds already order it, so a label could only break a tie between intervals of one kind
with equal bounds, and neither packet holds one.

### 2.4 Two shipped extensions specialise intervals

No core table references `core.intervals`, and of the core registry's shared-key discriminators only
`core.intervals.interval_kind` is a member of its own table's key, so §3.3 changes no core
declaration. The repository's `dynamic_foraging` and `vr_foraging` extensions each declare a table
specialising intervals, and each carries the constant column of §1.

Each can follow §3.3 at the cost of one check. Paired with `interval_id` alone, a specialising
table's identifier takes the assigned identity Part 02 §7 requires, and its `session_id` needs a
reference of its own to `core.sessions`, since a reference to a key without `session_id` is no
session-preserving edge (Part 02 §7.1). The three-column reference then no longer checks that a
specialising row's session is its interval's. No table referencing `core.units` checks that either,
since R123 §3.1 has each reference `unit_id` alone, and in both session packets every trial's
session is its interval's. An extension may declare a rule comparing the two; one joining
`dynamic_foraging.trials` to `core.intervals` on `interval_id` passes the Part 11 static check.

Neither extension checks that its constant column holds its own resource ID, so no check confirms
that a specialising row names an interval of its own kind, before §3.3 or after it. In both session
packets, with `interval_kind` removed from `dynamic_foraging.trials`, every trial still names an
interval by `interval_id`, and `dynamic_foraging.blocks.contains_its_trials`, joined on
`interval_id` in place of the constant column, passes the Part 11 static check and returns no rows;
moving one trial's start outside its block draws 1. Seven `vr_foraging.sites` rules require one
session's sites to be numbered consecutively in time order, which §3.2 gives wherever one session's
sites share a clock and no two share both bounds, and all 17 `vr_foraging.sites` rules pass the
static check with the constant column removed. No packet or fixture carries `vr_foraging` tables.

Part 02 §8.3 also has a detail table's primary key begin with the discriminated table's identifier,
so after §3.1 each table is keyed by its interval's identifier alone, and `vr_foraging.site_odors`,
the one table referencing either, references `site_id` alone. Keyed so, every declared rule of both
extensions but the rewritten one still passes the static check. Each extension declares its own
change, and the core specification assigns no extension's version (Part 09 §5.5).

### 2.5 The numbering rule was run on both packets

Each packet's `core.intervals` was renumbered by §3.2's order, with its source number as
`local_interval_label`. §3.2's rule passes the Part 11 static check and returns no rows, in 1.6 and
1.4 ms, the median of 9 runs. From misnumbered variants it draws these rows, the first packet's
count and then the second's:

| variant | rows drawn |
|---|---:|
| two identifiers swapped | 2 / 2 |
| a gap after the hundredth identifier | 350 / 608 |
| a numbering from 1 | 450 / 708 |
| a second kind, numbered with the trials in time order across the two kinds | 565 / 820 |
| one kind's intervals on two clocks, numbered by tick value across the clocks | 448 / 706 |
| two trials with equal bounds, numbered in either order | 0 / 0 |

120 synthetic intervals of a kind named `aind_opto.pulses`, which sorts before
`dynamic_foraging.trials` and which no registry declares, numbered after the trials draw nothing,
since the rule checks each kind's numbering and not the order of kinds. A rule checking one order
across the packet draws 570 and 828 rows from the same packets. Of the 75 fixture packets carrying
`core.intervals`, numbered from 0 by subtracting 1 from each identifier, the 73 holding the valid
packet's two trials return no rows, `dup_pk`'s repeated trial draws 2, and `missing_column` lacks
`clock_id`.

Today the primary key refuses a source that repeats an interval's number within one session and
kind, and a writer assigning `interval_id` would accept it. §3.1's label rule keeps the refusal. It
passes the Part 11 static check, returns no rows on either packet in 0.8 ms with each NWB `id` as
the label, and draws the repeated label where one trial is repeated, as it does in `dup_pk`.

### 2.6 Alternatives

| alternative | why it falls short |
|---|---|
| keep the carried number and the composite key | no single identifier names an interval, so no axis can hold trials, and every specialising table keeps a constant column |
| keep the carried number and key on it alone | two kinds a source numbers alike collide |
| add an assigned identifier beside the composite key | each row has two keys, and each reference picks one |
| label a trial axis through a table specialising trials | a core axis names only core resources, and that table identifies a trial by more than one column too |
| number by (`session_id`, `interval_kind`, `local_interval_label`), as Part 02 §12.1 orders units | the label is a string read two ways (§2.3), and a source numbering nothing leaves the order undefined |
| break ties between equal bounds by `local_interval_label` | it decides no identifier in either packet, and it needs an order for labels that Part 02 §12.1 leaves unstated for units |
| leave a source's labels free to repeat within a session and kind | the relation §3.1 gives a consumer would name two intervals, and a source repeating a number would pass where the key refuses it today |
| number in the order the source lists intervals | nothing in the packet records that order, so no rule can check it |
| number in time order across kinds | the kinds interleave in the stored table, and reading one kind scans all of them |
| number by bounds without the clock | ticks on two clocks do not compare, so the order is not chronological where one kind uses two clocks |
| check one order across the packet, the order of kinds included | a kind added after the packet was built, numbered after the largest identifier, fails the check wherever it sorts before a kind the packet holds, and numbered in the one order it moves every later identifier: 120 pulses sorting before the trials move every trial's identifier by 120 |

## 3. Decision

Four subsections give the interval its identifier, fix the order that numbers it, have specialising
tables reference it by that identifier, and advance the core registry version. The crosswalk in §1.1
places each.

### 3.1 A packet numbers its intervals

`interval_id` identifies an interval on its own. A writer assigns it, and records the number or name
its source gave the interval in `local_interval_label`, null where the source gave none. A consumer
relating an interval to anything outside the packet uses (`session_id`, `interval_kind`,
`local_interval_label`). Part 02 §12's new subsection *Interval identity* states this with §3.2.

The incorporated core registry MUST declare `core.intervals` with primary key (`interval_id`) and
these changed or added columns, its other columns, references and rules unchanged:

| column | type | presence | role | identity | vocabulary | description |
|---|---|---|---|---|---|---|
| `interval_id` | `int32` | `required` | `identifier` | `assigned` | — | Interval ID, assigned by the packet; a session's intervals of one kind are numbered consecutively by clock and bounds. |
| `interval_name` | `string` | `required` | `data` | — | `free` | What `interval_id` stands for: the name a source or an earlier packet used for this interval. The only bridge between two packets that numbered it differently (Part 05 §4.3). |
| `local_interval_label` | `string` | `nullable` | `data` | — | `free` | The source's own number or name for this interval; undefined base, not an offset. |

`start_tick` and `stop_tick` describe "the interval" in place of "the trial". `interval_kind`
remains a `required` discriminator resolving `required` by a shared key, which is now `interval_id`.

The incorporated core registry MUST declare this rule on `core.intervals`, at level `error`. It
draws each label two intervals of one session and kind share.

| id | message |
|---|---|
| `core.intervals.label_unique_within_kind` | `two intervals of one session and kind carry the same local_interval_label` |

```sql
SELECT session_id, interval_kind, local_interval_label, COUNT(*) AS n
FROM core.intervals
WHERE local_interval_label IS NOT NULL
GROUP BY session_id, interval_kind, local_interval_label
HAVING COUNT(*) > 1
```

### 3.2 Intervals are numbered by kind, clock and bounds

A writer MUST number a packet's intervals densely from 0. It MUST number each session's intervals of
one kind consecutively, in ascending order of `clock_id`, `start_tick` and `stop_tick`, and MUST
number the intervals one build adds session by session and kind by kind, in ascending order of
`session_id`, then `interval_kind` compared by Unicode scalar value. Intervals of one session, kind
and clock with equal bounds MAY be numbered in any order. `core.intervals` is stored in its key's
order (Part 03 §5.3), so each kind of one session is one contiguous run, and within it each clock's
intervals are in tick order.

The incorporated core registry MUST declare this rule on `core.intervals`, at level `error`. It
checks that identifiers are dense from 0 and that each session's intervals of one kind are numbered
consecutively in order; the order of sessions and kinds binds the writer alone, and no rule checks
it (§2.6).

| id | message |
|---|---|
| `core.intervals.numbered_in_order` | `interval_id is not dense from 0, or does not number a session's intervals of one kind consecutively by clock and bounds` |

```sql
SELECT numbered.interval_id
FROM (
  SELECT interval_id, session_id, interval_kind,
    ROW_NUMBER() OVER (ORDER BY interval_id) - 1 AS dense,
    ROW_NUMBER() OVER (
      PARTITION BY session_id, interval_kind
      ORDER BY clock_id, start_tick, stop_tick, interval_id) - 1 AS rank_in_kind
  FROM core.intervals
) AS numbered
JOIN (
  SELECT session_id, interval_kind, MIN(interval_id) AS first_id
  FROM core.intervals
  GROUP BY session_id, interval_kind
) AS kinds
  ON kinds.session_id = numbered.session_id AND kinds.interval_kind = numbered.interval_kind
WHERE numbered.interval_id <> numbered.dense
   OR numbered.interval_id <> CAST(kinds.first_id AS DECIMAL(38,0)) + numbered.rank_in_kind
```

### 3.3 A specialising table references an interval by `interval_id` alone

Part 02 §8.3's shared-key reference covers the discriminated table's whole key, and a detail table
carries the discriminator's value as a constant column only where the discriminator is a member of
that key. A table specialising an interval therefore references `core.intervals.interval_id` alone
and carries no `interval_kind`.

### 3.4 The core registry version advances

The incorporated core registry's `registry_version` MUST advance from `0.9.0`, which R147 assigns,
to `0.10.0`.

## 4. What this does not change

Part 01 §3.10 is unchanged: an interval still belongs to one session, has bounds on a declared
clock, and declares its kind. `interval_kind` stays the discriminator and resolves by the shared
key. Part 12 gains no term: an adapter hands over an interval's identifier as its source's name for
the interval (Part 12 §5), and no adapter needs the number the build assigns. Part 02 §8.2 has
whatever composes an assigned identifier's name make it unique within the packet, so a name built
from a source's number carries the interval's session and kind.

## 5. Consequence

Every packet carrying `core.intervals` is rebuilt, and binds core registry 0.10.0. In both session
packets every `interval_id` keeps its value, and `local_interval_label` records the NWB's `id` as a
string. The fixture packets' two trials become 0 and 1, labelled `"1"` and `"2"`. An extension table
specialising intervals conforms to Part 02 §§7 and 8.3 only once it drops its constant column, is
keyed by an assigned identifier referencing `interval_id` alone, and references `core.sessions`
directly; §2.4 shows that both shipped extensions can, and that they then no longer check that a
row's session is its interval's.

These accepted clauses change: R54 §2.2, which put the kind in the key so each kind keeps its
source's numbering, is superseded by §§3.1 and 3.2. R54 §2.1's ledger entry gains a note that §3.1
replaces the identity and key it declared, and R90 §§3.3 and 3.6 gain notes that `core.intervals`'
whole key is now `interval_id`, so a detail table carries no constant column for it. Their rules
stand. `revisions/registry-targets.toml`'s target for R54 §2.2 retires with the clause, and
`escapewheel-writer/tests/test_extensions.py` cites it for a site and a pulse both numbered 0, which
after §3.1 are two intervals labelled `"0"`.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §3.10 requires an interval's session, bounds and kind, and all three stay. | None required. |
| logical prose and registry | Part 02 §8.3 takes §3.3's sentence, Part 02 §12 gains *Interval identity* with its anchor, and Part 02 §9.2 takes §3.4's version. The core registry source declares §3.1's columns, key and rule and §3.2's rule. `registry/check.py`'s expected core version follows, and its naming exceptions for extension constant columns go with those columns. | `evidence/R<N>.json` names each anchor and registry pointer; `registry/check.py` passes. |
| physical profiles | Unchanged. Part 03 §5.3 already stores `core.intervals` in its key's order. | None required. |
| packet manifest and JSON Schemas | Unchanged. No manifest field names an interval. | None required. |
| validation and import | Unchanged prose. Part 05 §4.3 already has a writer assign identifiers packet-wide before any table is written, which covers `interval_id`. | The corpus variants below. |
| extensions | Each shipped extension with a table specialising intervals, `dynamic_foraging` and `vr_foraging`, drops its constant column, is keyed by an assigned identifier referencing `interval_id` alone, and references `core.sessions` directly, declaring the change, any rule comparing a row's session with its interval's, and its version itself (§2.4). `aind_opto` and `aind_unit_qc` specialise no interval. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The writer's NWB source hands over the NWB's `id` as the interval's label; its numbering assigns `interval_id` by §3.2 and composes `interval_name`. The reader's interval accessor and discriminator resolution join on `interval_id` alone. The validator's generated reference checks follow the registry. No `escapewheel-aind` adapter produces an interval table. | The writer, reader and validator suites; both session packets rebuilt and validated with no error. |
| conformance fixtures and tests | `fixtures/build.py` writes the new columns and numbers from 0. Positive variants hold two kinds numbered alike by their source, the second declared by a fixture-local extension, two kinds numbered out of Unicode order with each contiguous, two trials with equal bounds numbered in each order, and an array axis labelled with trials; negative variants hold a misordered numbering, a numbering by tick value across two clocks, and a gap, each drawing `core.intervals.numbered_in_order`, which `dup_pk`'s repeated interval also draws beside `core.intervals.label_unique_within_kind`. `conformance/interval-kinds/probe.py` and `prototype/registry-codegen/` follow the declarations. | `fixtures/corpus.py`. |
| revision process and tooling | The ordinary ledger and evidence records, and the superseded and annotated clauses above. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | `registry/tables.md` renders the new columns; Part 08 §§2 and 3 regenerate with the new registry versions; the specification README's identifier table, `framework.py`'s expected version, the combined specification and the heading index follow. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1 and 3.2 are `applied` at Part 02's *Interval identity*, §3.1 also at Part 02 §4, and
`registry` for §3.1's declarations and rule and §3.2's rule. §3.3 is `applied` at Part 02 §8.3, and
§3.4 at Part 02 §9.2. Each is placed by canonical anchor.

These cases distinguish the new rules from the current ones:

- a packet holding trial 0 of one session and interval 0 of a second kind, declared by a
  fixture-local extension, numbered by §3.2 and both labelled `"0"`, is conforming, as it is today
  only through the composite key;
- a packet holding two trials of one session with equal bounds is conforming whichever is numbered
  first;
- an array axis whose `coordinate_resource` is `core.intervals` and whose labels name trials by
  `interval_id` is conforming, where today it draws
  `core.array_dimensions.coordinate_resource.key_fits_paired_value`;
- a packet whose two trials are numbered 1 and 2 draws `core.intervals.numbered_in_order`, where the
  current registry accepts it;
- a packet numbering a later trial before an earlier one draws the same rule, as does one numbering
  a kind's intervals on two clocks by tick value across the clocks;
- a packet numbering that second kind after its `dynamic_foraging.trials`, each kind contiguous and
  in order, passes the rule although the second kind sorts first;
- a packet repeating an `interval_id` draws the numbering rule beside the primary-key check;
- a packet holding two intervals of one session and kind labelled alike draws
  `core.intervals.label_unique_within_kind`, where today the key refuses their repeated number; and
- a row of a table specialising intervals that names no `interval_id` draws the generated reference
  check on `core.intervals.interval_id`.

The positive cases are the two rebuilt session packets and the valid corpus packet.

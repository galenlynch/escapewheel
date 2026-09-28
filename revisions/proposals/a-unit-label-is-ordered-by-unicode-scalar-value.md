# A unit label is ordered by Unicode scalar value

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-28 |
| **Based on** | `3685a5960ad5d94034d0f995c4f0932c8d818f9b` |
| **Decision domain** | specification |
| **Affects** | Part 02 §12.1's numbering of units; the rules declared on `core.units`; the reference writer's unit numbering; both session packets |

## 1. Problem

Part 02 §12.1 has a packet assign each unit its `unit_id`, "numbering units by ascending
`(sorting_run_id, curation_id, local_unit_label)` so a rebuild reproduces the same numbers".
R81 §2.2 made that rule. `local_unit_label` is a `string` holding the sorter's own name for the
unit, and the rule has two gaps.

### 1.1 Two conforming writers order a run's units differently

Part 02 §12.1 does not say how two labels compare. Compared as text, by Unicode scalar value as
Part 11 compares every string, `"10"` precedes `"2"`; compared as numbers, `"2"` precedes `"10"`.
The reference writer takes the second reading. A writer taking the first numbers the same units
differently, and no declared rule checks the numbering, so neither packet draws a finding.

### 1.2 Part 02 §12.1 does not say where the numbering starts

R81 §2.2 starts the numbering at zero, and the ledger records that clause as applied at
Part 02 §12.1, whose text omits the start. No other part states where an assigned numbering
begins.

### 1.3 The order fixes a unit's number only within its run

No part fixes how `sorting_run_id` and `curation_id` are numbered, and Part 12 §5 leaves numbering
to the build. The label comparison therefore decides only the order of one run and curation's
units, and two writers agree on every `unit_id` only where they also number runs and curations
alike. Under the draft `every-array-axis-declares-what-each-position-is`, a waveform array's unit
axis is labelled with `unit_id`, so each packet binds templates to units through its own numbering
whichever reading it takes.

## 2. Evidence

The measurements use the two session packets the reference writer built with the fixed waveform
source, the `packet-wf` builds: `ecephys_786867`, ten probes, and `ecephys_776259`, twelve probes.
Queries ran in DuckDB 1.5.5 over their Parquet tables.

| `core.units` | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| units | 4,505 | 6,781 |
| sorting runs, and curations | 10 and 10 | 12 and 12 |
| units in one run | 365 to 579 | 241 to 806 |
| `unit_id` values | 0 to 4,504 | 0 to 6,780 |
| labels that are null or not a canonical decimal | 0 | 0 |
| longest label, in characters | 3 | 3 |
| units numbered otherwise by text order | 4,486 | 6,757 |
| units numbered otherwise by numeric order | 0 | 0 |
| units numbered otherwise by shortlex order | 0 | 0 |

A canonical decimal is a string of digits with no leading zero. Shortlex order puts the shorter
label first and compares labels of one length by Unicode scalar value, which on canonical decimals
equals numeric order.

This rule, within Part 11's profile, passes the static rule check against the core registry:

```sql
SELECT unit_id, expected
FROM (
  SELECT unit_id,
    ROW_NUMBER() OVER (ORDER BY sorting_run_id, curation_id, local_unit_label, unit_id) - 1 AS expected
  FROM core.units
) AS numbered
WHERE unit_id <> expected
```

It returns 4,486 and 6,757 rows on the current numbering, in 2.3 and 2.6 ms. Once each packet's
units are renumbered by text order it returns none, and each run's units still hold consecutive
identifiers, so the clustering of `core.spike_events` that R81 §2.4 measured is kept. Of the 64
fixture packets under `fixtures/packets/`, 61 carry `core.units`, each holding two units labelled
`"17"` and `"42"` in one run; every reading orders them alike, and the rule returns no rows on any.

Part 11 cannot state numeric or shortlex order. Its scalar routines include no length, and `CAST`
to `DECIMAL(38,0)` fails on a label that is not a decimal, which `local_unit_label`'s free
vocabulary admits.

## 3. Desired outcome and constraints

A resolution gives Part 02 §12.1 one reading, so that two writers numbering runs and curations
alike number units alike; states where the numbering starts; and lets a validator report a packet
numbering otherwise, preferably within Part 11 as it stands. It keeps the order run-major, which
R81 §2.4's clustering relies on, and leaves `local_unit_label` the source's own spelling, `free`
and nullable.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep Part 02 §12.1 as written | two conforming writers keep numbering a run's units differently, and nothing reports either |
| compare labels as text, by Unicode scalar value (preferred direction) | one comparison, the one Part 11 applies to every string and the draft `an-interval-is-numbered-by-its-packet` applies to `local_interval_label`; the rule of §2 checks it with Part 11 unchanged; the reference writer renumbers 4,486 and 6,757 units within their runs |
| compare labels as numbers where every label of a run is a canonical decimal, and as text otherwise | reproduces every current `unit_id`; two comparisons and a switch between them, and no Part 11 rule can check it |
| shortlex order | one comparison, reproducing every current `unit_id`; unchecked unless Part 11 gains a length routine, which means a new rule-language descriptor that every registry binds |
| drop the label and require only run-major, curation-major numbering | numbers units as the build numbers any assigned identifier, but leaves a run's order to each writer where the interval draft fixes a full order for intervals |

Under the preferred direction, a run's `unit_id` values no longer follow the sorter's numbering. No
consumer may read that numbering from them: Part 01 §2.1 forbids a writer to encode meaning in an
assigned identifier, and `local_unit_label` records the sorter's number. The renumbering lands in
the rebuild the array-axis draft already requires of both session packets.

A null label sorts after every other under Part 11, so units of one run and curation with null
labels tie. The rule's final `unit_id` admits either order among them, as the interval draft admits
either order among intervals equal in every key it orders by.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §2.1 already forbids meaning in an assigned identifier. |
| logical prose and registry | Part 02 §12.1 states that numbering starts at 0 and that labels compare by Unicode scalar value, with null last. The core registry declares the rule of §2 on `core.units` at level `error` and advances its version after the interval draft's. R81 §2.2 stands, and its ledger entry gains a note naming the comparison and the rule. |
| physical profiles | Unchanged. Part 03 §5.3 stores `core.units` by `unit_id` whatever the numbering. |
| packet manifest and JSON Schemas | Unchanged. |
| validation and import | The declared rule; no generated check changes. |
| extensions | Unchanged. No extension numbers units, and `aind_unit_qc`'s adapter resolves a unit by probe and label. |
| reader, writer, validator, adapters | The writer's unit numbering compares labels as text, and its test asserting numeric order follows. The reader and validator are unchanged, and no adapter numbers units (Part 12 §5). |
| existing packets | Both session packets renumber 4,486 and 6,757 units within their runs, and every unit-keyed table follows; the fixture packets are unchanged. |
| conformance fixtures and tests | New negative variants: a run whose units labelled `"2"` and `"10"` are numbered in numeric order, and a numbering starting at 1, each drawing the rule. |
| revision process and tooling | The ordinary ledger and evidence records, and the note on R81 §2.2. |
| generated publications and documentation | `registry/tables.md` lists the rule; Part 08's generated example and the specification README's identifier table follow the core registry version. |

## 6. Open questions

1. Text order, checked by a declared rule, or shortlex order, which keeps every current `unit_id`
   and stays unchecked? The preferred direction is text order.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

# Unit labels order by length, then by Unicode scalar value

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-28 |
| **Based on** | `13fe339ed316c8077b4805366e00e354254795b7` |
| **Decision domain** | specification |
| **Affects** | Part 02 §12.1's numbering of units; Part 11 §§1, 2 and 5 and the rule-language descriptor; the registry-contract descriptor and Part 02 §§1, 9.2 and 9.4; the rules declared on `core.units`; every repository registry's `rule_language`; the reference validator's rule checker |

## 1. Problem

Part 02 §12.1 has a packet assign each unit its `unit_id`, "numbering units by ascending
`(sorting_run_id, curation_id, local_unit_label)` so a rebuild reproduces the same numbers".
R81 §2.2 made that rule. `local_unit_label` is a `string` holding the sorter's own name for the
unit, and the rule has two gaps, which the rule language cannot currently close.

### 1.1 Two conforming writers order a run's units differently

Part 02 §12.1 does not say how two labels compare. Compared as text, by Unicode scalar value as
Part 11 compares every string, `"10"` precedes `"2"`; compared as numbers, `"2"` precedes `"10"`.
The reference writer takes the second reading. A writer taking the first numbers the same units
differently, and no declared rule checks the numbering, so neither packet draws a finding.

### 1.2 Part 02 §12.1 does not say where the numbering starts

R81 §2.2 starts the numbering at zero, and the ledger records that clause as applied at
Part 02 §12.1, whose text omits the start. No other part states where an assigned numbering
begins.

### 1.3 Part 11 cannot state the order the reference writer uses

A declared rule can check text order today, but not numeric order. Part 11's scalar routines
include no length, and `CAST` to `DECIMAL(38,0)` fails on a label that is not a decimal, which
`local_unit_label`'s `free` vocabulary admits.

### 1.4 The order fixes a unit's number only within its run

No part fixes how `sorting_run_id` and `curation_id` are numbered, and Part 12 §5 leaves numbering
to the build. The label comparison therefore decides only the order of one run and curation's
units, and two writers agree on every `unit_id` only where they also number runs and curations
alike. Under the draft `every-array-axis-declares-what-each-position-is`, a waveform array's unit
axis is labelled with `unit_id`, so each packet binds templates to units through its own numbering
whichever reading it takes.

## 2. Evidence

The measurements use the two session packets the reference writer built with the fixed waveform
source, the `packet-wf` builds: `ecephys_786867`, ten probes, and `ecephys_776259`, twelve probes.
Queries ran in DuckDB 1.5.5 over their Parquet tables, timings as the median of 9 runs.

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
| units numbered otherwise by length, then text order | 0 | 0 |

A canonical decimal is a string of digits with no leading zero. Ordering labels by length and then
by Unicode scalar value puts `"2"` before `"10"`, and on canonical decimals it equals numeric order.
On any other label it is still a total order, and it places `"7"` before `"007"`, where numeric
order would tie them.

### 2.1 One ISO routine lets a rule state that order

SQL/Foundation's `CHARACTER_LENGTH`, ISO feature E021-04, counts a string's characters. With it,
this rule states Part 02 §12.1's order:

```sql
SELECT unit_id, expected
FROM (
  SELECT unit_id,
    ROW_NUMBER() OVER (ORDER BY sorting_run_id, curation_id, label_length, local_unit_label, unit_id) - 1 AS expected
  FROM (
    SELECT unit_id, sorting_run_id, curation_id, local_unit_label,
      CHARACTER_LENGTH(local_unit_label) AS label_length
    FROM core.units
  ) AS labelled
) AS numbered
WHERE unit_id <> expected
```

The length is computed in a derived table because Part 11 orders a window by column references
only. With the routine admitted in a probe, the reference validator's static rule check passes the
rule, including its proof that the ordering identifies one row. The unchanged checker rejects it
for the routine alone.

On the current numbering the rule returns no rows, in 1.8 and 1.9 ms. Renumbered by text order, it
returns 4,486 and 6,757 rows, and numbered from 1, all 4,505 and 6,781. Of the 64 fixture packets
under `fixtures/packets/`, 61 carry `core.units`, each holding two units labelled `"17"` and `"42"`
in one run, and the rule returns no rows on any.

Part 11 §5 compares characters as Unicode scalars, and DuckDB 1.5.5's `character_length` counts
the same thing: 2 for `e` followed by a combining acute accent, and 1 for a character outside the
Basic Multilingual Plane. SQLGlot 30.18.0, the reference validator's parser, reads `LENGTH`,
`CHAR_LENGTH` and `CHARACTER_LENGTH` as one node, so the checker cannot tell the engine's spelling
from the standard's by node type.

## 3. Desired outcome and constraints

A resolution gives Part 02 §12.1 one reading, so that two writers numbering runs and curations
alike number units alike; states where the numbering starts; and lets a validator report a packet
numbering otherwise. It keeps the order run-major, which R81 §2.4's clustering of
`core.spike_events` relies on, and leaves `local_unit_label` the source's own spelling, `free` and
nullable. A change to the rule language admits standard SQL/Foundation surface only, and keeps one
rule language in the release.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep Part 02 §12.1 as written | two conforming writers keep numbering a run's units differently, and nothing reports either |
| order by length, then by Unicode scalar value, and admit `CHARACTER_LENGTH` in a new rule language (preferred direction) | reproduces every current `unit_id`, with integer order on every canonical decimal label and a total order on any label; a declared rule checks it; the rule language gains one ISO routine and a new ID, and the registry-contract descriptor advances |
| order by Unicode scalar value alone | checked with Part 11 unchanged; renumbers 4,486 and 6,757 units within their runs, whose `unit_id` values then stop following the sorter's numbering |
| order as numbers where every label of a run is a canonical decimal, and as text otherwise | Part 11 would need a pattern predicate and a guarded `CAST` that relies on `CASE` leaving its untaken branch unevaluated; a label longer than 38 digits overflows, and a second order still covers the rest |
| order by length, then by Unicode scalar value, unchecked | no language change, and a requirement no rule verifies |
| drop the label and require only run-major, curation-major numbering | numbers units as the build numbers any assigned identifier, but leaves a run's order to each writer where the draft `an-interval-is-numbered-by-its-packet` fixes an order for intervals |

Part 11 §1 requires a changed language contract to take a new language ID. Two ways follow for the
registries. Under the preferred direction every repository registry names the new language, and
the registry-contract descriptor admits only it, so the release carries one rule language and
`escapewheel-rule-sql-v0.1`, never released, retires. Admitting both leaves the four extension
registries untouched, but a validator then implements two languages that differ by one routine.

The new routine counts Unicode scalars, as Part 11 §5 already defines characters, and is admitted
only as `CHARACTER_LENGTH` with one argument; `LENGTH` stays outside the profile as an engine
spelling. It returns `BIGINT`, as `COUNT` does, and a null argument gives null, which Part 11 orders
last, so a null label follows every other in its run and ties among null labels admit either order.

The interval draft numbers intervals by session, kind and bounds, and admits either order for
intervals of one kind with equal bounds, so no label enters it. The order proposed here is then the
only label order Part 02 states.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §2.1 already forbids meaning in an assigned identifier. |
| logical prose and registry | Part 02 §12.1 states that numbering starts at 0 and that labels order by length, then by Unicode scalar value, with null last. The core registry declares the rule of §2.1 on `core.units` at level `error`, names the new language, and advances its version after the interval draft's. Part 02 §9.2 names the new language; the registry-contract descriptor advances after the array-axis draft's, admitting only the new language, and Part 02 §§1 and 9.4 follow. R81 §2.2 stands, and its ledger entry gains a note naming the order and the rule. |
| rule language | Part 11 §1 names and incorporates the new language's descriptor; §2 admits one-argument `CHARACTER_LENGTH` over a character string, returning `BIGINT`; §5 states that it counts Unicode scalars. The new descriptor adds E021-04 and otherwise matches the current one. The ledger entries for R125 §3.1 and R125 §3.2, which name the current language and its exact descriptor, gain notes. |
| physical profiles | Unchanged. Part 03 §5.3 stores `core.units` by `unit_id`. |
| packet manifest and JSON Schemas | Unchanged. The rule-language profile schema admits the new descriptor, and the registry meta-schema requires only a non-empty `rule_language`. |
| validation and import | The declared rule. The validator admits the routine under the new language ID, rejects the `LENGTH` and `CHAR_LENGTH` spellings its parser folds into the same node, and selects the new descriptors. |
| extensions | Each of the four repository extension registries names the new language and advances its version; no rule changes. |
| reader, writer, validator, adapters | The writer's numbering already follows this order for its non-negative integer labels; its test names the order. The reader is unchanged, and no adapter numbers units (Part 12 §5). |
| existing packets | No `unit_id` changes. Both session packets bind the new core registry at the rebuild the array-axis draft already requires. |
| conformance fixtures and tests | New negative variants: a run whose units labelled `"2"` and `"10"` are numbered in text order, and a numbering starting at 1, each drawing the rule. The rule-language vectors gain cases counting a combining sequence and a null, and rejecting `LENGTH`; their profile ID follows. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes on R81 §2.2, R125 §3.1 and R125 §3.2. |
| generated publications and documentation | `registry/tables.md` lists the rule; Part 08's generated example, the specification README's identifier table and the framework's expected values follow the new identifiers. |

## 6. Open questions

1. Every repository registry moves to the new language and the old one retires, or the descriptor
   admits both? The preferred direction is one language.

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

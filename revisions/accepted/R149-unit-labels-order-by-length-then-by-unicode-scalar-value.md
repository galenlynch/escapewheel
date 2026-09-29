# Unit labels order by length, then by Unicode scalar value

| | |
|---|---|
| **Status** | **Accepted** 2026-09-29 |
| **Based on** | `4d4501063a42b2c9815f8a0dd97555c4dcc5f2e3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§1, 9.2, 9.4 and 12.1; Part 08 §§2 and 3; Part 11 §§1, 2 and 5; the rule-language descriptor; the registry-contract descriptor; the core registry; the four extension registries |
| **Depends on** | R148 §3.4 (the core registry version this advances from); R147 §3.8 (the registry-contract descriptor this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2 and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

`core.units` holds one row per sorted unit. A packet assigns each unit its `unit_id`, and
`local_unit_label`, a nullable `string`, records the sorter's own name for the unit. Part 02 §12.1,
applying R81 §2.2, has a packet number units "by ascending
`(sorting_run_id, curation_id, local_unit_label)` so a rebuild reproduces the same numbers". The
rule has three gaps:

- **Labels compare two ways.** Part 02 §12.1 does not say how two labels compare. Compared by
  Unicode scalar value, as Part 11 §5 compares every string, `"10"` precedes `"2"`; compared as
  numbers, `"2"` precedes `"10"`. The reference writer takes the numeric reading; a writer taking
  the other numbers the same units differently, and no declared rule checks either.
- **The numbering has no stated start.** R81 §2.2 numbers from zero, and the ledger records that
  clause as applied at Part 02 §12.1, whose text omits the start.
- **No routine states the numeric reading.** Part 11 admits no cast from a character value and has
  no length routine, so a declared rule can check the scalar-value order and not the numeric one.

This revision orders labels by length, then by Unicode scalar value. That order equals numeric order
on every label written as a decimal without leading zeros, and is a total order on any label. The
revision states the start, numbers each curation's units consecutively, declares a rule checking the
numbering within each curation, and admits `CHARACTER_LENGTH` in the rule language so the rule can
state the order. Part 11 §1 gives a changed language contract a new language ID, so the language
becomes `escapewheel-rule-sql-v0.2`, every registry selects it, and `escapewheel-rule-sql-v0.1`
retires unreleased.

The change is structural because it revises rules inside Part 02 §12.1 and Part 11 §§1 and 2, and
replaces identifiers that Part 02 §§1, 9.2 and 9.4 state. Appended sections would leave
Part 02 §12.1 stating an order with two readings, and Part 11 §1 naming a language no registry
selects.

### 1.1 Structural crosswalk

Every affected section carries a canonical anchor, so no bootstrap is needed. No section moves,
splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §1, the incorporated descriptor file | revise in place | same section | the v0.7 descriptor is incorporated | §3.4 |
| Part 02 §9.2, the core registry version and rule language | revise in place | same section | the version advances to 0.11.0 and the language to `escapewheel-rule-sql-v0.2`; an extension migrated to the new language changes its version | §3.4 |
| Part 02 §9.4, the descriptor ID | revise in place | same section | the descriptor advances to v0.7 and admits only the new language | §3.4 |
| Part 02 §12.1, the numbering clause | revise in place | same section | numbering is dense from 0, each curation's units are consecutive, and labels order by length, then by Unicode scalar value | §3.1 |
| Part 11 §1, the language ID and incorporated descriptor | revise in place | same section | the language is `escapewheel-rule-sql-v0.2` | §3.3 |
| Part 11 §2, the scalar routines and their result domains | extend in place | same section | `CHARACTER_LENGTH` is admitted in one spelling and returns `BIGINT` | §3.2 |
| Part 11 §5, the character semantics | extend in place | same section | `CHARACTER_LENGTH` counts Unicode scalars | §3.2 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none | none |

## 2. Background

Section 2 is informative. The measurements use the two session packets the reference writer built
under this baseline's registry, the `packet-r147` builds: `ecephys_786867`, ten probes and 4,505
sorted units, and `ecephys_776259`, twelve probes and 6,781 sorted units. Queries ran in DuckDB
1.5.5 over their Parquet tables, with timings the median of 9 runs.

### 2.1 Every label in both packets is a short decimal, numbered as a number

| `core.units` | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| units | 4,505 | 6,781 |
| sorting runs, and curations | 10 and 10 | 12 and 12 |
| units in one run | 365 to 579 | 241 to 806 |
| `unit_id` values | 0 to 4,504 | 0 to 6,780 |
| labels that are null or not a canonical decimal | 0 | 0 |
| longest label, in characters | 3 | 3 |
| units numbered otherwise by scalar-value order | 4,486 | 6,757 |
| units numbered otherwise by numeric order | 0 | 0 |
| units numbered otherwise by length, then scalar-value order | 0 | 0 |

A canonical decimal is `0`, or a nonzero digit followed by any digits, and on canonical decimals
ordering by length and then by Unicode scalar value equals numeric order. On other labels it is
still a total order, and it places `"7"` before `"007"`, which numeric order would tie.

### 2.2 The numbering rule ran on both packets and the fixtures

§3.1's rule returns no rows on either packet, in 3.3 and 2.8 ms. Renumbered by scalar-value order
within each curation, the packets draw 4,486 and 6,757 rows, and numbered from 1, all 4,505 and
6,781. Numbered with their curations in reverse order, each curation's units consecutive and in
order, they draw nothing, where a rule checking one order across the packet draws all 4,505 and
6,781. Of the 76 fixture packets under `fixtures/packets/`, 73 carry `core.units`, each holding two
units labelled `"17"` and `"42"` in one run, and the rule returns no rows on any.

With `CHARACTER_LENGTH` admitted in a probe, the reference validator's static check accepts the
rule, whose window ordering identifies one input row. The unchanged checker rejects the rule for the
routine alone. The rule computes the length in a derived table because Part 11 §2 orders a window by
column references only.

### 2.3 `CHARACTER_LENGTH` counts what Part 11 compares

SQL/Foundation's `CHARACTER_LENGTH`, ISO feature E021-04, counts a string's characters, and
Part 11 §5 takes characters to be Unicode scalars. DuckDB 1.5.5 counts the same: 2 for `e` followed
by a combining acute accent, 1 for a character outside the Basic Multilingual Plane, and null for
null. SQL/Foundation also spells the routine `CHAR_LENGTH` and admits a `USING` clause naming the
unit counted; DuckDB accepts `CHAR_LENGTH` and `LENGTH` as well. SQLGlot 30.18.0, the reference
validator's parser, reads all three spellings as one node, so a checker cannot tell them apart by
node type.

### 2.4 Alternatives

| alternative | why it falls short |
|---|---|
| keep Part 02 §12.1 as written | two conforming writers keep numbering a run's units differently, and nothing reports either |
| order by Unicode scalar value alone | checkable with Part 11 unchanged, but it renumbers 4,486 and 6,757 units within their runs, whose `unit_id` values then stop following the sorter's numbering |
| order as numbers where every label of a run is a canonical decimal, and by scalar value otherwise | Part 11 would need a pattern predicate and a guarded `CAST` relying on `CASE` leaving its untaken branch unevaluated; a label of more than 38 digits overflows, and a second order still covers the rest |
| order by length, then by scalar value, without a rule | a requirement no rule verifies |
| drop the label and require only run-major, curation-major numbering | it leaves a run's order to each writer, where R148 fixes an order for intervals |
| check one order across the packet, the order of curations included | a curation added after the packet was built, numbered after the largest identifier, fails the check wherever it sorts before a curation the packet holds: a curation of the first sorting run draws 4,505 and 6,781 rows |
| add `CHARACTER_LENGTH` under a new language ID and keep `escapewheel-rule-sql-v0.1` beside it | the four extension registries stay unchanged, but a validator implements two languages differing by one routine, neither of them released |

## 3. Decision

Four subsections fix the unit order, admit the routine that states it, name the language admitting
the routine, and advance the registry identifiers. The crosswalk in §1.1 places each.

### 3.1 Units are numbered from 0 by run, curation and label

A writer MUST number a packet's units densely from 0. It MUST number each curation's units, those
sharing `sorting_run_id` and `curation_id`, consecutively in ascending order of `local_unit_label`,
and MUST number the units one build adds curation by curation, in ascending order of
`sorting_run_id`, then `curation_id`. It MUST compare two labels by their length in Unicode scalars,
shorter first, and two labels of equal length by Unicode scalar value (Part 11 §5). A null label
follows every other label. Units of one curation that tie on their label, two null labels included,
MAY be numbered in either order.

The incorporated core registry MUST declare this rule on `core.units`, at level `error`. It checks
that identifiers are dense from 0 and that each curation's units are numbered consecutively in label
order; the order of curations binds the writer alone, and no rule checks it (§2.4).

| id | message |
|---|---|
| `core.units.numbered_in_order` | `unit_id is not dense from 0, or does not number a curation's units consecutively by label` |

```sql
SELECT numbered.unit_id
FROM (
  SELECT unit_id, sorting_run_id, curation_id,
    ROW_NUMBER() OVER (ORDER BY unit_id) - 1 AS dense,
    ROW_NUMBER() OVER (
      PARTITION BY sorting_run_id, curation_id
      ORDER BY label_length, local_unit_label, unit_id) - 1 AS rank_in_curation
  FROM (
    SELECT unit_id, sorting_run_id, curation_id, local_unit_label,
      CHARACTER_LENGTH(local_unit_label) AS label_length
    FROM core.units
  ) AS labelled
) AS numbered
JOIN (
  SELECT sorting_run_id, curation_id, MIN(unit_id) AS first_id
  FROM core.units
  GROUP BY sorting_run_id, curation_id
) AS curations
  ON curations.sorting_run_id = numbered.sorting_run_id AND curations.curation_id = numbered.curation_id
WHERE numbered.unit_id <> numbered.dense
   OR numbered.unit_id <> CAST(curations.first_id AS DECIMAL(38,0)) + numbered.rank_in_curation
```

### 3.2 The rule language admits `CHARACTER_LENGTH`

The profile admits one-argument `CHARACTER_LENGTH` over a `CHARACTER VARYING` value as a scalar
routine. It returns `BIGINT`: the number of Unicode scalars in its argument, and null for a null
argument. `CHAR_LENGTH`, `LENGTH` and a `USING` clause are outside the profile.

### 3.3 The rule language is `escapewheel-rule-sql-v0.2`

The language Part 11 defines is identified by `escapewheel-rule-sql-v0.2`, and Part 11 incorporates
`registry/rule_languages/escapewheel-rule-sql-v0.2.json` in place of the v0.1 descriptor. That
descriptor MUST contain the exact data of R125 §3.2, except that its `id` is
`escapewheel-rule-sql-v0.2` and its `iso_feature_dependencies` add `E021-04`. The rule-language
profile schema is unchanged.

Every registry published with this candidate MUST carry `rule_language: escapewheel-rule-sql-v0.2`.

### 3.4 The registry identifiers advance

The registry-contract descriptor's `rule_languages` MUST list `escapewheel-rule-sql-v0.2` alone. The
meta-schema it selects, its phases and its invariants are unchanged.

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.6`, which R147 assigns | `escapewheel-registry-contract-v0.7` |
| core registry `registry_version` | `0.10.0`, which R148 assigns | `0.11.0` |
| core registry `rule_language` | `escapewheel-rule-sql-v0.1` | `escapewheel-rule-sql-v0.2` |

Part 02 §1 incorporates the descriptor as
`registry/registry_contracts/escapewheel-registry-contract-v0.7.json`.

An extension registry migrated to `escapewheel-rule-sql-v0.2` MUST carry a `registry_version`
different from the one it carried under `escapewheel-rule-sql-v0.1`; the core specification does not
assign it (Part 09 §5.5). No checker verifies this.

## 4. What this does not change

`local_unit_label` stays the source's own spelling, `free` and nullable, and Part 02 §12.1's other
paragraphs are unchanged. Within one build the order stays run-major, which R81 §2.4's clustering of
`core.spike_events` relies on. No part fixes how sorting runs and curations are numbered, and
Part 12 §5 leaves numbering to the build, so this revision fixes a unit's number within its run and
curation; two writers agree on every `unit_id` only where they also number runs and curations alike.
The rule language's other routines, type bindings and execution settings are unchanged.

## 5. Consequence

No `unit_id` changes in either session packet or in any fixture packet. Every packet binds core
registry 0.11.0 and is rebuilt at the rebuild R148 already
requires. The release carries one rule language: every repository registry names the new one, and
the four repository extension registries advance their versions without changing a rule. A registry
naming `escapewheel-rule-sql-v0.1` selects no descriptor, so its evaluation is unsupported
(Part 02 §9.4) until it names the new language.

R81 §2.2 stands. Its ledger entry gains a note that §3.1 states its start and its label order,
declares its rule, and lets units tying on their label be numbered in either order, and its
destination, which names Part 02 §12.1 by number, moves to the section's anchor. R123 §3.1, which
has a packet assign `unit_id` by that rule, gains a note that two writers may number such units
differently. R125 §3.1, R125 §3.2 and R125 §3.11 name `escapewheel-rule-sql-v0.1`, its exact
descriptor and a validator's claim to support it. Their ledger entries gain notes that §3.3 renames
the language and adds E021-04, and that their obligations carry to the new identifier.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §2.1 already has a writer assign an identifier without encoding meaning in it, and an order encodes none. | None required. |
| logical prose and registry | Part 02 §12.1 takes §3.1, and Part 02 §§1, 9.2 and 9.4 take §3.4's identifiers. The core registry source declares §3.1's rule, the new language and the new version; `registry/build.py` and `registry/check.py` follow the new identifiers. | `evidence/R<N>.json` names each anchor and registry pointer; `registry/check.py` passes. |
| physical profiles | Unchanged. Part 03 §5.3 stores `core.units` by `unit_id`. | None required. |
| packet manifest and JSON Schemas | Unchanged. The rule-language profile schema's patterns admit the new ID and feature, the registry-contract schema admits any versioned language ID, and the registry meta-schema requires only a non-empty `rule_language`. | None required. |
| validation and import | Part 11 §1 takes §3.3, and Part 11 §§2 and 5 take §3.2. `registry/rule_languages/` holds the v0.2 descriptor in place of the v0.1 descriptor. | `evidence/R<N>.json` names the anchors; the rule-language vectors below. |
| extensions | Each of the four repository extension registries names `escapewheel-rule-sql-v0.2` and advances its `registry_version`; no rule changes. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The validator admits `CHARACTER_LENGTH` in that spelling alone, binding its one argument as `CHARACTER VARYING` and rejecting `CHAR_LENGTH` and `LENGTH`, which its parser reads as the same node, and selects the v0.2 language and v0.7 contract descriptors. The writer already numbers its labels, non-negative integers written as canonical decimals, in this order; its test of the order a unit's name sorts in names the order, and its scaffold names the new language. The reader is unchanged, and no `escapewheel-aind` adapter numbers units (Part 12 §5). | The writer and validator suites; both session packets rebuilt and validated with no error. |
| conformance fixtures and tests | New negative variants: a curation whose units labelled `"2"` and `"10"` are numbered in scalar-value order, and a numbering from 1, each drawing `core.units.numbered_in_order`. Positive variants hold two null labels in one curation, numbered in each order, and two curations numbered in reverse order with each contiguous. The rule-language vectors take the new profile ID and gain cases counting a combining sequence and a null, and rejecting `CHAR_LENGTH`, `LENGTH`, `USING` and a non-character argument. `conformance/rule-language/probe.py`, which reads the v0.1 descriptor by path, `conformance/interval-kinds/probe.py`, `prototype/registry-codegen/` and the package tests naming `escapewheel-rule-sql-v0.1` follow the new identifier. | `fixtures/corpus.py` and `conformance/rule-language/probe.py`. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes on R81 §2.2 and on R125 §3.1, R125 §3.2 and R125 §3.11. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | `registry/tables.md` lists the rule; Part 08 §§2 and 3 regenerate with the new registry versions; the specification README's identifier table, `framework.py`'s expected version, the rule language root `STATUS.md` names, `registry/README.md`, the validator's README, the combined specification and the heading index follow. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 02 §12.1 and `registry` for its rule. §3.2 is `applied` at Part 11 §§2
and 5. §3.3 is `applied` at Part 11 §1 and `registry` for each registry's `rule_language`. §3.4 is
`applied` at Part 02 §§1, 9.2 and 9.4. Each is placed by canonical anchor.

These cases distinguish the new rules from the current ones:

- a curation whose units labelled `"2"` and `"10"` are numbered 1 and 0 draws
  `core.units.numbered_in_order`, where the current registry accepts it;
- a packet numbering its units from 1 draws the same rule;
- a packet numbering a later sorting run's curation before an earlier one's, each curation's units
  consecutive and in order, passes the rule;
- a unit labelled `"7"` is numbered before one labelled `"007"` in the same curation, where numeric
  order ties them;
- a curation holding two units with null labels is conforming whichever is numbered first, and both
  follow every labelled unit of the curation;
- a rule calling `CHARACTER_LENGTH` over a string column passes static validation, and one calling
  it over an integer column, or calling `CHAR_LENGTH`, `LENGTH` or `CHARACTER_LENGTH` with
  `USING OCTETS`, fails it;
- `CHARACTER_LENGTH` returns 2 for `e` followed by U+0301, and null for null; and
- a registry naming `escapewheel-rule-sql-v0.1` selects no registry-contract descriptor, and its
  evaluation is unsupported.

The positive cases are the two rebuilt session packets and the valid corpus packet. §2.2's static
check and data runs establish feasibility.

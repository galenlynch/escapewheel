# Absence is defined once, in the logical standard

| | |
|---|---|
| **Status** | **Accepted** 2026-10-06 |
| **Opened** | 2026-10-05 |
| **Based on** | `8e218b9193592bf69634bed803cbb95d52016ac6` |
| **Change form** | structural |
| **Amends** | Part 02 §5.4 and Part 02 §6; Part 03's One null section; Part 05 §15.6; Part 12 §5 |
| **Depends on** | R139 §3.1 (the finiteness rule this narrows) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

A packet's columns and arrays can each lack a value, and the specification states what that means
in one place that is misplaced and leaves four questions open.

**The one-null rule sits in the physical profile.** Part 03's One null section says a column value is present or
null, that inapplicable, unrecorded and unknown values all arrive as the same null, that NaN is a
value rather than an absence, and that a writer adopts no sentinel. Part 02 §5.4, the finiteness
rule, depends on it and cites it. Nothing in Part 03's One null section depends on Parquet: its Parquet sentence
explains why one marker suffices, and a second profile would need the same rule. Under the
placement test of the specification style guide, a statement that would not change with the profile
belongs in the logical standard.

**An absent optional column has no general reading.** Part 02 §6 lets an `optional` column be
missing from a table's file. Part 05 §15.6 compares amended rows as if the missing column held null
in every row, and Part 11 §3 does not expose the column to a rule. No part says what a reader or
consumer makes of the missing column.

**`finite: false` has no stated purpose.** Part 02 §5.4 admits NaN and infinity in a column
declaring `finite: false`, and turns a source's NaN meaning "not recorded or not computable" into
null. No column the core registry or a repository extension registry declares is `finite: false`,
so nothing shows what a non-finite value of a column means.

**A source NaN of unknown meaning has no default.** Part 02 §5.4 conditions the conversion on what
the source's NaN means, and a writer often cannot tell: a data frame or a numerical export uses NaN
for both a missing value and a computed one.

**Nothing says whether an array element can be absent.** Zarr has no null: every element is a
value, and an element of a chunk never written reads as the array's `fill_value`. The specification
does not say whether it adds a marker of its own, so a reader cannot tell whether a NaN or a
`fill_value` in an array is a claim about the data.

The change is structural: it moves Part 03's One null section into Part 02 and narrows Part 02 §5.4 and two other
sections in place. Appending a section would leave the one-null rule stated in two parts.

### 1.1 Structural crosswalk

Part 03 §5, which loses its last subsection, has no anchor and takes `ew-table-storage` in this
change, which is the only anchor bootstrap. The new subsection of Part 02 §6 takes `ew-absence`
when it is created.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03's One null section (`ew-one-null`) | move and retire | new last subsection of Part 02 §6, Absence (`ew-absence`), with `ew-one-null` as its alias | none for the moved rule | §3.1 |
| Part 03's One null section, its sentences on Parquet's definition level and on NaN in page statistics | remove | Parquet and Arrow, which state both | none | §3.4 |
| none | add | Part 02 §6, Absence | an absent `optional` column holds null in every row; a source's non-finite value of unstated meaning is written as null | §3.1 |
| Part 02 §5.4 Finite values, last paragraph | replace in place | same section | `finite: false` is for a non-finite value carrying a meaning, which the column's description states | §3.2 |
| none | add | Part 02 §6, Absence | an array element is always a value, and the specification adds no marker of an absent one | §3.3 |
| Part 05 §15.6, an `optional` column a file omits reads as null | replace that clause with a citation | same section | none | §3.5 |
| Part 12 §5, first paragraph, "Part 02 §5's presence" | correct the citation | same section | cites Part 02 §6 | §3.5 |

## 2. Evidence

Section 2 is informative. Counts were taken at the baseline.

- No column of `spec/artifacts/logical_schemas.json` or of an extension registry declares
  `finite: false`. R139 §3.4 set every core float column `finite: true`, and R139 §2.5 rejected
  `finite: false` for four quotients because an infinite quotient would publish "not computable",
  which Part 03's One null section assigns to null.
- R139 §2.4 records that the reference writer's NWB adapter and the `aind_unit_qc` adapter write
  null for every source NaN. Neither knows what the source meant by it.
- Part 12 §5 already states the delivery counterpart of the absent-column reading: an adapter
  delivers a column wherever any row carries a value, so an absent delivered column of any presence
  says that no row does. It cites that as "Part 02 §5's presence"; presence is Part 02 §6.
- The reference writer omits an `optional` column from a table's file when no row carries it, so
  every packet it writes exercises the unstated reading.
- Parquet's definition level and Arrow's validity bitmap carry one bit, so the one null of a column
  is what the storage already holds. Zarr carries no such bit for an element.

A marker of an absent array element was drafted and withdrawn. It declared each float array's
finiteness, let NaN mean "no value" by default, and used a clock's observation windows for a
dropped stretch. Each piece failed on a case the arrays already hold: an integer array, raw
electrophysiology among them, has no non-finite value to mark with; a clock's observation window
covers every stream on the clock, so it cannot say that one camera dropped frames; and what a missing
element means differs between a spatial bin never visited, a channel that dropped out and a
stimulus never presented, so no one marker states it. A companion mask array or a table of
absent regions is exact for any element type, and both were set aside: neuroscience formats state a
bad channel or a bad stretch of time rather than a missing element, and a packet already holds both
as rows of its channel and interval tables.

Leaving Part 03's One null section in place costs no migration and keeps the logical standard depending on a
storage part for the meaning of its own nulls. Giving null several kinds would need a second
validity bit that neither Parquet nor Arrow carries.

## 3. Decision

Five subsections state a column's absence, a column's non-finite values, an array's elements, the
removal from Part 03, and the citations that follow. The crosswalk in §1.1 places each.

### 3.1 A column's absence

A new last subsection of Part 02 §6, Absence, states these rules.

A column value is present or null; there is no second marker. A value that is inapplicable, one
that was never recorded, one a source recorded as unknown and one that could not be computed, such
as a ratio of zero to zero or the mean of no values, are each null. A writer MUST NOT
adopt a sentinel value meaning absent. Where the reason for an absence matters, a registry records
the fact that distinguishes it in a column of its own rather than encoding the reason in the value:
a run's `scope` distinguishes an undeterminable scope from an unambiguous one, and
`normalized_label` is null where a source's label has no honest projection.

A table whose file omits an `optional` column holds null in that column in every row. A reader
need not expose the omitted column, and one that does MUST expose it as null in every row. Part 11 §3 still exposes no omitted column to a rule, which Part 02 §10.2 keeps
from naming one.

Where a writer cannot tell whether a source's non-finite value is a value or an absence, it MUST
write null. One null merges every reason a value is absent, so the conversion states nothing the
source did not. No checker verifies this, since a packet does not hold what the source meant.

### 3.2 A column's non-finite values

The last paragraph of Part 02 §5.4 is replaced by this rule. A column declares `finite: false` only
where a non-finite value carries a meaning no finite value can, such as an interval with no end,
and the column's `description` MUST state what each non-finite value it admits means. No checker
verifies this, since a description is prose. A computation whose result is non-finite where
the column gives that result no meaning has computed nothing, and its value is null under §3.1; a
non-finite value in a column is therefore always one its description gives a meaning.

### 3.3 An array's elements

The Absence subsection also states this rule. Every element of a dense array is a value, an element
of a chunk the array does not store included, and this specification defines no marker of an
absent element. A NaN or a `fill_value` in an array is therefore a value, whose meaning the array's
data type states where it states one. A data type that needs to say a stretch or a channel holds no
observation states it as rows, such as an interval of a kind it specialises or a status of the
channel.

### 3.4 Part 03

Part 03's One null section is removed. Its sentences on Parquet's one-bit definition level and on Parquet's
statistics excluding NaN describe the formats, which state both, and are not restated.

### 3.5 Citations

Part 12 §5 cites Part 02 §6 for an absent delivered column, in place of "Part 02 §5's presence".
Part 05 §15.6 cites §3.1's rule for an `optional` column a file omits rather than stating it.

## 4. Questions

1. Does an array declare whether its elements are finite?
   **Answered 2026-10-05:** No. A first answer added a declaration and a default meaning for NaN;
   it was withdrawn when Section 2's cases showed that no marker states a missing element across
   the arrays a packet holds.
2. How does a packet state a dropped sample?
   **Answered 2026-10-05:** It does not, in general. A clock's observation windows already state
   when the whole acquisition paused (Part 02 §12.5); a gap in one stream is the data type's to
   declare.
3. Does a packet-owned array write every chunk?
   **Answered 2026-10-05:** It need not. An element of an unwritten chunk is the array's
   `fill_value`, a value like any other, which Zarr already states and §3.3 does not qualify.
4. Does the absent-column reading also govern an `optional` column a build receives from an adapter,
   or only one a packet holds?
   **Answered 2026-10-05:** Only one a packet holds. Part 12 §5 already states the delivery rule for a
   column of any presence, and it cites the new subsection rather than restating it.

## 5. Consequence

No packet, registry or validator check changes. A writer that wrote a sentinel for a missing value
was already non-conforming. A writer that wrote NaN into a `finite: false` column for an unknown
value now writes null; no column declares `finite: false`, so no packet holds one.

No accepted clause is superseded. R139 §3.1's closing paragraph is replaced by §3.2, and its ledger
destination keeps `ew-finite-values`. The ledger destinations naming `ew-one-null`, those of
R101 §3.10 and R139 §3.1, move to `ew-absence`.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: absence is a property of values, which Part 02 owns. | None required. |
| logical prose and registry | Part 02 §6 gains Absence; Part 02 §5.4's last paragraph is replaced. The registry is unchanged. | `evidence/R<N>.json` names `ew-absence` and `ew-finite-values`. |
| physical profiles | Part 03's One null section is retired, its anchor an alias of `ew-absence`; Part 03 §5 takes `ew-table-storage`. | The anchor index and `headings.py`. |
| packet manifest and JSON Schemas | Unchanged. | None required. |
| validation and import | Part 05 §15.6 cites §3.1. No check changes. | None required. |
| extensions | Unchanged: no extension declares a `finite: false` column. | None required. |
| reader, writer, validator, adapters | Unchanged in behaviour: the reader's optional-table read already exposes an omitted `optional` column as null, and the reference adapters already write null for a source NaN (R139 §2.4). | The reader and writer suites. |
| conformance fixtures and tests | §6's cases. | The reader suite. |
| revision process and tooling | The ordinary ledger and evidence records; the two `ew-one-null` destinations move. | `ledger.py`, `evidence.py`. |
| generated publications and developer documentation | The combined specification regenerates. `extensions/AUTHORING.md` states §3.1's default for a source NaN and §3.3's rule that an array element is a value. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1 to 3.5 are `applied` at their anchors.

A reader test reads a table whose file omits an `optional` column through the reader's
optional-table read and finds null in that column in every row. An adapter test converts a source
NaN of unstated meaning and finds null in the delivered row. No case distinguishes §3.3, which forbids nothing a packet can
hold.

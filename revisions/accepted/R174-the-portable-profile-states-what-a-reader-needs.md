# The portable profile states what a reader needs

| | |
|---|---|
| **Status** | **Accepted** 2026-10-06 |
| **Opened** | 2026-10-05 |
| **Based on** | `8e218b9193592bf69634bed803cbb95d52016ac6` |
| **Change form** | structural |
| **Amends** | Part 03 §1, Part 03 §2, Part 03 §3.2, Part 03 §5.1, Part 03 §5.5, Part 03 §6.3, Part 03 §6.4 and Part 03's array-metadata section; Part 02 §6.2 and Part 02 §12; Part 05 §5.3; Part 10 §1 and Part 10 §2 |
| **Depends on** | none |
| **Profile** | `escapewheel-portable-v0.1` |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Problem

Part 03 is meant to say how the logical resources of Part 02 are stored, and a reader opening it
to learn how a `float64` column is stored finds no answer. The part states the Parquet type of a
timestamp and of a date, in the middle of the Parquet floor, and of no other type. A reader infers
`DOUBLE` from the type's name and Part 11 §5's IEEE binding, which governs rule evaluation rather
than storage.

Around that gap, the part carries three kinds of material that do not tell a reader how to read a
packet:

- **Writer guidance.** Part 03 §5.5 spends 437 words on how a writer chooses each column's encoding:
  four ordered rules, per-column overrides that record what they measured, and an `info` report on
  a column costing more than 1.5x its best encoding. Its own last sentence says a packet is
  conforming whichever encoding it uses, and a reader decodes every encoding in the floor the same
  way.
- **Logical rules.** Part 03 §6.3 states how an array axis declares its coordinates: rational steps,
  order-only axes, labelled and dependent axes, and the limit of a core axis to core resources.
  None depends on Zarr, and Part 02 §6.2 already cites Part 03 §6.3 for two readings of a null, so the
  logical standard depends on the storage part for its own declarations.
- **Restatements.** Part 03 §6.4's table of floor definitions restates `artifacts/physical_profile.schema.json`,
  which Part 03 §1 says owns the shape. Its two JSON blocks restate the descriptor's floors by hand.
  Part 03's array-metadata section's rule that `core.array_assets` carries no dtype or shape repeats Part 02 §6. The Zstandard
  recommendation appears in both Part 03 §5.1 and Part 03 §5.5. Part 03 §3.2 forbids a file, `schemas/semantic_version.txt`,
  that no writer has reason to write and no checker looks for.

The change is structural. It moves material between parts and retires one section; an appended
section cannot remove a misplaced one.

### 1.1 Structural crosswalk

Every section the change moves, splits or retires already carries a canonical anchor. Part 03 §3,
whose subsection Part 03 §3.2 is retired, and Part 03 §6, whose subsection Part 03 §6.3 moves out, have none, and
take `ew-portable-directory-layout` and `ew-array-storage` in this change, which is the only anchor
bootstrap. The two new subsections take `ew-descriptor-conformance` and
`ew-encoding-choice` when they are created. Retiring Part 03 §3.2 renumbers the two subsections after it, and moving
Part 03 §6.3 renumbers the two after it.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §1, its second paragraph from "A conforming distributed copy" and its third and fourth: the checker obligations, the schema `$id` and the anchor rule | move | new first subsection of Part 03 §2, Descriptor conformance (`ew-descriptor-conformance`) | none | §3.1 |
| Part 03 §1, the scope, incorporation and ownership sentences | keep | Part 03 §1 | none | §3.1 |
| Part 03 §3.2 Files that MUST NOT be written (`ew-portable-forbidden-files`) | retire, no alias | none | a writer may write `schemas/semantic_version.txt`, which is a stray | §3.2 |
| none | add | Part 03 §5.1 | a packet-owned column of each logical type has one Parquet physical and logical type; an external column at another type of its family is outside the portability guarantee | §3.3 |
| Part 03 §5.5, the wall-clock timestamp and date sentences | replace | Part 03 §5.1's type table | none | §3.3 |
| Part 05 §5.3, "no part fixes which Parquet type represents each declared type" | replace in place | same section | `schema.column_type` judges a packet-owned column against Part 03 §5.1's table and an external one against its family; a new `info` finding reports an external column at another type of its family | §3.3 |
| Part 03 §5.5, the encoding-choice rules, overrides and 1.5x report | move and lose force | new last subsection of Part 10 §2, Choosing an encoding (`ew-encoding-choice`) | the rules become informative | §3.4 |
| Part 03 §5.5, "and SHOULD use Zstd" | remove | Part 03 §5.1 keeps the Zstandard recommendation | none | §3.4 |
| Part 10 §1, "states none of its own" | replace in place | same section | the part also carries that guidance | §3.4 |
| Part 03 §6.3 Axis coordinates (`ew-array-axis-coordinates`) | move | new last subsection of Part 02 §12, An array's axis coordinates, keeping the anchor | none | §3.5 |
| Part 03 §6.4, the physical-profile schema's definition table | remove | `artifacts/physical_profile.schema.json` | none | §3.6 |
| Part 03 §6.4, the two floor JSON blocks | replace with generated regions | same section, rendered from the descriptor | none | §3.6 |
| Part 03's array-metadata section (`ew-array-metadata-placement`), its first paragraph on dtype and shape | remove | that section's third paragraph and Part 02 §6 | none | §3.7 |

## 2. Evidence

Word counts are `wc -w` over the baseline's line ranges of `spec/parts/03_portable_physical_profile.md`,
which holds 5,943 words. `revisions/impact.py` listed the citers.

| passage | words | citers |
|---|---:|---|
| Part 03 §5.5's encoding-choice rules | 437 | the writer's `encoding.py` and its tests, Part 10 §2.8 to Part 10 §2.11, the writer's performance documentation |
| Part 03 §6.3 Axis coordinates | 607 | Part 02 §6.2 by anchor |
| Part 03 §6.4's floor-definition table | 139 | none |
| Part 03 §3.2 | 41 | none |

The encoding-choice rules came from R110 and R118, which measured column costs and found that no
declaration predicts the best encoding. That finding stands; the question here is only whether a
recommendation no reader can observe belongs in the part that defines how to read a packet.

The floors themselves stay. They are what makes Part 03 §1's portability claim true: readers in
different languages implement different subsets of Parquet encodings and Zarr codecs, and a writer
held to the floor writes nothing a conforming reader cannot open.

Alternatives:

- **Keep the part as it is.** No migration; a reader keeps inferring storage types from type names,
  and the part's length keeps hiding its few traps.
- **Delete the encoding-choice rules.** Loses a measured result that a writer still benefits from.
- **Keep the encoding rules in Part 03 under their own heading.** Separates them from the floor
  without changing their force; it still leaves a writer recommendation in the profile.

## 3. Decision

Seven subsections each settle one part of Part 03, and the crosswalk in §1.1 places each moved
statement. Every moved passage keeps its words except where a subsection says otherwise.

### 3.1 Descriptor conformance

Part 03 §1's second paragraph from "A conforming distributed copy" to its end, and its third and
fourth paragraphs, which bind the generic cross-member checker, state the physical-profile schema's
`$id` and state the anchor rule, move to a new first subsection of Part 03 §2, Descriptor
conformance. Part 03 §1 keeps its first paragraph, the four sentences of its second saying what the
part incorporates and which of the schema, the descriptor and the prose owns what, and its last
three paragraphs.

### 3.2 A forbidden file

Part 03 §3.2 is removed, and its anchor is retired with no alias. A `schemas/semantic_version.txt`
that no manifest names is a stray under Part 03 §9, which no part reads as packet content, so it
restates a manifest field without being able to contradict it.

### 3.3 The Parquet type of each logical type

Part 03 §5.1 states this rule after its first paragraph. A writer MUST write each column of a
packet-owned table, of each logical type of Part 02 §5.1, with the Parquet physical type and
logical type the table gives.

| logical type | Parquet physical type | Parquet logical type |
|---|---|---|
| `int32` | `INT32` | none, or `INTEGER` with bit width 32 and signed |
| `int64` | `INT64` | none, or `INTEGER` with bit width 64 and signed |
| `float32` | `FLOAT` | none |
| `float64` | `DOUBLE` | none |
| `bool` | `BOOLEAN` | none |
| `string` | `BYTE_ARRAY` | `STRING` |
| `json_string` | `BYTE_ARRAY` | `STRING` |
| `timestamp` | `INT64` | `TIMESTAMP` with `isAdjustedToUTC=true` and unit `MICROS` |
| `date` | `INT32` | `DATE`, days since the Unix epoch |

An external table's column may instead be at another type of its declared type's **family**:

| family | its declared types | the Parquet types of the family |
|---|---|---|
| integer | `int32`, `int64` | `INT32` or `INT64`, with no logical type or with `INTEGER` of any bit width, signed or not |
| float | `float32`, `float64` | `FLOAT` or `DOUBLE`, with no logical type |
| boolean | `bool` | `BOOLEAN` |
| text | `string`, `json_string` | `BYTE_ARRAY` with `STRING`, `ENUM` or `JSON` |
| instant | `timestamp` | `INT64` with `TIMESTAMP`, `isAdjustedToUTC=true`, of any unit |
| date | `date` | `INT32` with `DATE` |

Such a column is outside the portability guarantee, as a valid feature outside a reader-only floor
is (Part 03 §2): a reader MAY expose its values as the declared type, and the column's type alone
does not make the packet non-conforming. A column at a type outside its family is at the wrong type.

Part 03 §5.5's last paragraph, which states the timestamp and date types and forbids `INT96`, is
removed. Part 05 §5.3's sentence saying no part fixes which Parquet type represents each declared
type, apart from the timestamp, is replaced by these rules. A validator reports under `schema.column_type` a
packet-owned table's column at a type other than the table gives, and an external table's column
at a type outside its family. For an external table's column at another type of its family it MUST
instead report one finding at `info` under the check ID `physical.outside_type_mapping`, naming the
resource, the column, its declared type and its observed Parquet physical and logical type, and
MUST NOT report that column under `schema.column_type`.

### 3.4 Encoding choice is guidance

Part 03 §5.5's paragraphs from "A writer SHOULD choose the encoding" through "a packet is
conforming whichever it uses", and its clause "and SHOULD use Zstd", are removed. A new last
subsection of Part 10 §2, Choosing an encoding, states the same four rules, the per-column override that
records what it measured, and the `info` report on a column costing more than 1.5x its best
encoding, as guidance for a writer: it uses no BCP 14 keyword, and it cites Part 10 §2.8 to Part 10 §2.11
for the measurements each rule rests on. It states that a packet is conforming whichever encoding
within Part 03 §5.5's floor it uses. Part 10 §1 says that the part also carries that guidance.

### 3.5 Axis coordinates are logical

Part 03 §6.3 moves, keeping its anchor `ew-array-axis-coordinates`, to a new last subsection of
Part 02 §12, An array's axis coordinates. Part 02 §6.2 then cites it within Part 02.

### 3.6 The Zarr floors are stated once

Part 03 §6.4's table of the physical-profile schema's definitions, and the sentence introducing it,
are removed; Part 03 §1 incorporates the schema, which owns them. Its two JSON blocks stating the v3
and v2 reader floors are replaced by generated regions rendered from
`interfaces.zarr.variants.v3.reader_floor` and `interfaces.zarr.variants.v2.reader_floor` of the
portable descriptor, as Part 03 §2's kind-to-interface table is.

### 3.7 An array states its own dtype and shape

Part 03's array-metadata section's first paragraph is removed. Its third paragraph already requires a self-describing
physical fact, dtype and shape among them, to be obtained from the resource, and no array-asset
table declares either.

## 4. Questions

1. Does any of the encoding guidance stay a recommendation in BCP 14's sense? The preferred answer was no: every encoding
   in the floor is conforming and no reader can tell which rule chose it. The alternative keeps the
   rules normative in a Part 03 subsection of their own.
   **Answered 2026-10-05:** No. The encoding-choice rules become informative guidance in Part 10.
2. Does the type table also state Zarr data types for array elements? The preferred answer was no:
   Part 03's array-metadata section leaves dtype to the array's own metadata, and the registry declares no element type
   for an array.
   **Answered 2026-10-05:** No. The array's own Zarr metadata owns its data type.
3. Does `json_string` carry Parquet's `JSON` annotation rather than `STRING`? A reader that does not
   know `JSON` might refuse a column it could have read as text.
   **Answered 2026-10-05:** `STRING`.
4. Should the descriptor-checker obligations of Part 03 §1, which bind a checker of the
   specification's own artifact rather than any packet actor, move with them to the part or guide
   that owns the descriptor's conformance?
   **Answered 2026-10-05:** They stay in Part 03 and leave its scope section, under §3.1.
   Part 00 §2.3 states consistency for every artifact, and the registry-contract and physical-profile
   descriptors are checked differently, so a shared home would hold two unrelated contracts; a
   developer guide cannot hold a condition on the candidate's consistency.

## 5. Consequence

No packet changes and no registry changes. A writer that writes a type the table excludes, such as
an `int64` column annotated unsigned or a `json_string` column annotated `JSON`, now draws
`schema.column_type`; the reference writer writes none. An external table's column at another type
of its family now draws an `info` finding rather than an error, so a referenced `timestamp` column
at unit `MILLIS`, which Part 03 §5.5 refused, is outside the portability guarantee and conforming.
An external column outside its family, such as text where `int64` is declared or a local-time
`TIMESTAMP` where `timestamp` is, still draws `schema.column_type`. A writer may now write
`schemas/semantic_version.txt`, which is a stray. A writer that departs from the encoding
rules was already conforming and is still.

Eight ledger clauses lose their normative home. The encoding-choice clauses R110 §3.3, R110 §3.5
and R118 §3.1 to §3.6 become `superseded`, since Part 10 is informative and no `applied`
destination; R110 §3.4, applied at Part 05 §3.8, is unchanged. R146 §3.7 loses its destination
`ew-portable-forbidden-files` and keeps its other two. The destinations of R20 §4, R33 §2 and
R147 §3.4 at `ew-array-axis-coordinates` change part from 03 to 02, and R137 §3.3's note stops
naming Part 03 §6.4's table. R6 §2 and R3 §2.1, which name `ew-parquet-reader-floor` for the
timestamp and type sentences, gain `ew-table-encoding` in its place where those sentences were
their subject, and R129 §3.3 keeps both anchors.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: no concept's meaning moves. | None required. |
| logical prose and registry | Part 02 §12 gains An array's axis coordinates under §3.5; Part 02 §6.2's citation of it stays in Part 02. The registry is unchanged. | `evidence/R<N>.json` names `ew-array-axis-coordinates` in Part 02. |
| physical profiles | Part 03 §1, Part 03 §2, Part 03 §3.2, Part 03 §5.1, Part 03 §5.5, Part 03 §6.3, Part 03 §6.4 and Part 03's array-metadata section change as §§3.1 to 3.7 state. The descriptor and its schema are unchanged. | The anchor index, `headings.py` and the generated regions of §3.6. |
| packet manifest and JSON Schemas | Unchanged. | None required. |
| validation and import | Part 05 §5.3's sentence on Parquet types is replaced under §3.3, adding `physical.outside_type_mapping`. The floor checks and Part 05's citations of them are unchanged. | A validator test per row of the type table. |
| extensions | Unchanged: an extension declares logical types, which the table maps. | None required. |
| reader, writer, validator, adapters | The validator compares each column's Parquet physical and logical type with the table, reporting a packet-owned mismatch and an external column outside its family as errors, and an external column at another type of its family at `info`. The writer's encoding code and its tests cite Part 10's Choosing an encoding instead of Part 03 §5.5. No behaviour of the writer or reader changes. | The validator and writer suites. |
| conformance fixtures and tests | §6's cases. | `fixtures/corpus.py`. |
| revision process and tooling | The ledger changes above. The specification generator renders the two floor regions of §3.6. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification regenerates. The writer's design and performance documents cite Part 10's Choosing an encoding for the encoding rules. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1, 3.3, 3.5, 3.6 and 3.7 are `applied` at their anchors. §3.2 is `applied` at
`ew-portable-directory-layout` and §3.4 at `ew-parquet-reader-floor` and `ew-encoding-choice`,
each with a note saying what was removed.

These cases distinguish the new rules from the current ones:

- a table whose `int64` column is annotated `INTEGER` with bit width 64 and unsigned draws
  `schema.column_type`;
- a table whose `json_string` column is annotated `JSON` draws `schema.column_type`;
- a packet-owned table whose `timestamp` column is `INT64` `TIMESTAMP` with unit `MILLIS` draws
  `schema.column_type`, and an external table holding the same column draws
  `physical.outside_type_mapping` at `info` and no `schema.column_type`;
- an external table whose `int64` column is `BYTE_ARRAY` with `STRING`, or whose `timestamp` column
  has `isAdjustedToUTC=false`, draws `schema.column_type`; and
- a test reads the footer of every table in the valid corpus packet and finds each column at the
  physical and logical type the table gives its declared type.

A generator test fails where the descriptor's floors and the rendered regions of Part 03's
Codecs section differ.

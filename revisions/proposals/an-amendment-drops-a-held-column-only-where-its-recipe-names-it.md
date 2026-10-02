# An amendment drops a held column only where its recipe names it

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `0318f7896790e26a16905c08200b29a835d8cbdd` |
| **Decision domain** | specification |
| **Affects** | Part 02 §6, which says which declared columns a table holds and nothing of an undeclared one; Part 05 §3.1's recipe keys and schema identifier; Part 05 §3.5's refusals of an amending build; Part 05 §4.3, under which a table gaining no row is not written; Part 05 §5.3's shim checks; Part 05 §15.2's table of what an amendment may change; Part 05 §15.6's comparison over declared columns; the recipe schema |

## 1. Problem

An amending build binds each registry its recipe names (Part 05 §15.1), and that registry may be a
later version that no longer declares a column a held table's file holds. Nothing then accounts
for the column's values.

Where the amendment writes the table, it writes the rows without the column. Part 05 §15.6
compares rows "over the columns the amended manifest's registry declares", so a held row that
differs only in the column counts as unchanged, and no finding names the loss. The values survive
only in the superseded file, until cleanup removes it.

Where the amendment does not write the table, the held file keeps the column, and the packet now
binds a registry that gives the column no type, description or check. No part says whether such a
file conforms, and no check reports it.

A build refuses to discard a value a source stated unless its recipe names the column
(Part 05 §3.4). Discarding every value of a held column is the larger loss, and it is neither
refused nor reported.

## 2. Evidence

Observed at the baseline commit, where the quick verifier passed all 37 of its stages. Scratch
packets were built outside the tree. No other draft is open; one proposal is, on Part 11, and it
does not touch these sections.

### 2.1 A rewritten table drops the values, and nothing reports it

The writer suite holds a test of this case, named in R163 §5. It builds a packet under a copy of
the core registry at version `0.0.1` whose `core.source_files` declares one more `optional`
`json_string` column, holding `{"slope":2.0,"offset":5.0}` in the packet's one row. It then amends
the packet under the baseline registry, adding a second `core.source_files` row. Run at the
baseline, it passes (1 test, 1.7 s), asserting that:

- the amendment's validation passes;
- the rewritten `core.source_files` file holds no such column, and both rows' `uri` values; and
- the superseded file still holds the value.

The test asserts the reference build's present behaviour so that a change to it is seen. It does
not assert that the behaviour is wanted.

### 2.2 A table left alone keeps a column its bound registry does not declare

A probe built the same packet under the same `0.0.1` copy, then amended it under the baseline
registry adding only a `core.processing_runs` row. The reference validator, run with checksums
and advisory checks:

| | findings | naming the column |
|---|---|---|
| before the amendment | 6 `info` | 0 |
| after the amendment | 7 `info` | 0 |

The amendment passed. `core.source_files` kept its resource entry and its file, which still holds
eight columns, the added one among them. The amended manifest binds core `0.18.0`, which does not
declare it. R163 §2.5 reports the same result for `core.clocks.transform_to_parent`.

### 2.3 Registry changes have removed 76 columns

The committed core registry was read at each of its 104 versions in the repository's history, and
each version's set of declared `resource.column` pairs compared with the one before. Fifteen
commits removed at least one column, 76 in all, a rename counting as a removal, since a held
file's column then has no declaration either. The eight latest:

| change | columns removed |
|---|---|
| R95 | 7 |
| R96 | 4 |
| R97 | 3 |
| R103 | 2 |
| R105 | 6 |
| R128 | 6 |
| R147 | 4 |
| R163 | 1 |

None of the eight changed `logical_standard_version`, so Part 05 §3.5's refusal of an amendment
binding a registry of another standard version would have refused none of them. The seven earlier
removals predate the registry's version numbers, and the extension registries were not counted.
Removing a column is an ordinary change to a v0.2 registry, not a rare one.

### 2.4 No part makes an undeclared file column non-conforming

A search of the numbered parts found no rule on a table file's column that its bound registry does
not declare.

- Part 02 §6 states which declared columns are present: `required` and `nullable` columns are, an
  `optional` one may be absent. It says nothing of a column no declaration names.
- Part 03 §5.1 makes a table one Parquet file and states nothing of its columns.
- Part 05 §5.3 has the shim check Parquet types, for declared columns.
- Part 11 §3 exposes to a rule each table's "registry-declared columns ... and no others", so no
  rule can see the column.
- Part 12 §5 says what a delivered column's absence means, and nothing of an undeclared one.

The reference validator checks each declared column's presence and type, and no other column. The
reference build refuses a delivered record holding a column no loaded registry declares, and three
writer tests assert it, but no part requires that refusal (R163 §2.5). An amendment never delivers
the held rows, so that refusal does not reach them.

### 2.5 Part 05 §15.2 is ambiguous on the point

Part 05 §15.2 forbids an amendment to "change or remove any other row of a canonical table". A
held row rewritten without one column's values is changed by one reading and not by the other.
Part 05 §15.6 takes the second, comparing only declared columns. The current contract therefore
does not already answer the question.

### 2.6 No corpus or measured packet carries an undeclared column

A scan compared every table file's columns with the declarations of the registries its packet
binds.

| population | packets | table files | with an undeclared column |
|---|---|---|---|
| the conformance corpus, built at the baseline | 135 | 4078 | 0 |
| readable scratch packets from earlier probes and test runs | 146 | 1057 | 2 |

Both scratch packets are probes that carry the column on purpose: the one in §2.2 and one of
R163's. No corpus fixture exercises an undeclared column. No packet built from a real session was
scanned.

## 3. Desired outcome and constraints

An amending build should not lose a held column's values unless its recipe says it may, and a
packet's current version should hold no column that its bound registries cannot describe. A recipe
that intends the loss should be able to say so and build. The resolution should keep the rest of
Part 05 §15: superseded bytes are never modified, rows are compared over the columns the bound
registry declares, and nothing is deleted except by cleanup.

## 4. Options and tradeoffs

### 4.1 What an amending build does with a held column the bound registry does not declare

- **Keep the current rule.** A rewritten table loses the values silently, and a table left alone
  keeps data that no bound registry describes (§§2.1 and 2.2).
- **Refuse outright.** A packet built under an earlier registry could then never be amended under a
  later one that drops a column, though dropping is ordinary (§2.3), and the only remedy would be a
  replacement.
- **Preserve the column.** A rewrite would carry forward a column that no registry the packet binds
  types, describes or checks, which leaves the second half of the problem in place.
- **Report only.** A report records the loss after the build has made it and leaves the packet
  conforming with the undeclared column. Part 05 §3.4 refuses a smaller discard unless the recipe
  names the column, and a report would not match it.
- **Reuse the column override.** Part 05 §3.5 refuses a column override whose column the resource
  does not declare, and here the column is by definition undeclared. Its meaning, releasing a
  passed-over source's value, also differs from this one.
- **Refuse by default, and release where the recipe names the column.** This is the preferred
  direction. An amending build refuses, naming the table and the column, where a table the packet
  holds has a column that no registry the amended manifest binds declares for it. A recipe entry
  naming `resource.column` releases that refusal and means "drop this column on amendment". Once
  released, the build writes the table without the column, including a table the amendment would
  otherwise leave alone.

Under the preferred direction the refusal would join the list in Part 05 §3.5 of what an amending
build refuses before it opens any source. Held files are part of the packet, not a source, so the
build can read their columns at that point.

### 4.2 The release entry

The preferred direction is a new top-level recipe table, `[drop]`, whose key is a resource's
dotted identifier followed by a column name, spelled as Part 05 §3.6 spells a column override's key,
and whose value is a non-empty string giving the reason, as an override's value is. An alternative
is a member of `[packet]` beside `amends`, which ties the entry to an amendment by placement. Open
question 1 asks which.

A build would refuse a `[drop]` entry before it opens any source:

- in a recipe that does not amend, since there is no held column to drop;
- naming a resource that no registry the amended manifest binds declares as a table; or
- naming a column that such a registry declares for the resource, since dropping a declared
  column's values changes rows Part 05 §15.2 forbids an amendment to change.

An entry naming a column that the held file does not hold releases nothing. As Part 05 §3.6 treats
an idle column override, the build would report it as a warning and not refuse it. The build would
report each dropped column as information, naming the table and the reason.

### 4.3 What the release changes elsewhere in Part 05

- **Part 05 §4.3** has a table to which the build adds no row keep its resource entry, so the
  amendment does not write it. A released column is the exception: the table is written without the
  column.
- **Part 05 §15.2** would say that removing a column no bound registry declares changes no row,
  settling §2.5 in the reading Part 05 §15.6 already takes.
- **Part 05 §15.2** also has an amendment that writes a canonical table, other than the three
  provenance tables, derive again or remove every analysis and compatibility-projection resource
  reached from it. The preferred direction keeps that duty for a table rewritten to drop a column.
  The earlier registry declared the column, so a derivation may have read it. Open question 2 asks
  whether to exempt such a rewrite instead.
- **Part 05 §15.5** is unchanged: the superseded file keeps the values until cleanup, which the
  release does not hasten.

### 4.4 The validator finding

The preferred direction adds a rule to Part 02 §6 that a table holds no column its declaration does
not declare, and has the shim of Part 05 §5.3 report each such column of a table the current
manifest names at `error`, whatever path produced it. A superseded version's files are judged
against the registries their own manifest binds, and are not checked again.

`error` rather than `warning`:

- a column no bound registry declares has no type, presence or description in the packet, and no
  rule can read it (Part 11 §3), so the packet cannot say what it holds;
- the reference build already refuses to deliver one (§2.4), so a packet built by it holds one only
  through the amendment path this proposal closes; and
- no corpus or measured packet holds one other than two deliberate probes (§2.6).

A `warning` would leave the file conforming. Then a second build that writes undeclared columns,
which no part forbids today, would also conform.

The two halves answer different cases. The validator finding catches a table left alone, and a
fresh build that wrote an extra column. It cannot see a rewrite that dropped the values, because
the column is then gone. Only the build's refusal covers that.

### 4.5 Placement, anchors and bootstrap

Every Part 05 section the change touches carries a canonical anchor: `ew-recipe-purpose`,
`ew-recipe-check`, `ew-import-normalization`, `ew-validation-shim`, `ew-amendment-scope` and
`ew-amendment-comparison`. Part 02 §6 carries none, so placing the rule there needs an anchor
bootstrap. Placing it in Part 03 §5.1 (`ew-table-encoding`) instead needs none, but it would make a
logical fact a property of one physical profile. The preferred direction is Part 02 §6 with a
bootstrap.

### 4.6 Compatibility

- **Recipe schema.** A new top-level key advances the schema's `$id` one minor version, from
  `https://escapewheel.org/schemas/recipe/0.4.0` at the baseline, and Part 05 §3.1 names the new
  identifier. A recipe that does not amend, or whose amendment drops nothing, is unchanged.
- **Check ID.** The finding takes a new check ID. The reference validator's two existing
  file-against-declaration checks, `schema.column_absent` and `schema.column_type`, are named by no
  part, so the draft would name the new one in Part 05 §5.3 and say whether to name those two
  beside it (open question 3).
- **Existing packets.** No corpus packet changes verdict (§2.6). A packet amended by the reference
  build since R163 without writing `core.clocks`, from one holding `transform_to_parent`, would gain
  an error. No measured packet holds that column (R163 §2.4).

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose (Part 01) | unchanged: no concept changes |
| logical prose (Part 02), meta-schema, declarations and rules | affected: Part 02 §6 states that a table holds no undeclared column, after an anchor bootstrap; the meta-schema, declarations and rules are unchanged |
| physical profiles (Part 03) | unchanged under the preferred placement; Part 03 §9's account of a rewritten table already covers a table written without a column |
| packet manifest and JSON Schemas | affected: the recipe schema admits the release entry and its `$id` advances; the manifest schema is unchanged |
| validation and import (Part 05) | affected: Part 05 §3.1's key table, Part 05 §3.5's refusals and the entry's refusals, Part 05 §4.3's exception, Part 05 §5.3's finding, Part 05 §15.2's sentence on an undeclared column |
| extension registries | unchanged: the rule applies to every bound registry, and no extension declaration changes |
| reader, writer, validator, adapters, code generation | affected: the reference build gains the refusal, the release and its reports, and its named amendment test changes to assert the refusal; the reference validator gains the finding; readers, adapters and generated code are unchanged |
| existing packets and migration | unknown in part: no corpus packet changes verdict, and no packet built from a real session was scanned |
| conformance fixtures and tests | affected: a fixture holding an undeclared column, expected at `error`; amendment tests for the refusal, the release, the idle entry and each static refusal |
| revision lifecycle and tooling | unchanged: one anchor bootstrap, as the existing sequence provides |
| generated publications and documentation | affected: the combined rendering, the recipe schema publication, and the writer's account of amendment |

## 6. Open questions

1. **Where does the release entry live?** The preferred direction is a top-level `[drop]`. A member
   of `[packet]` beside `amends`, such as `[packet.drop]`, is the alternative.
2. **Does a drop-only rewrite oblige re-derivation?** The preferred direction keeps Part 05 §15.2's
   duty, since a derivation may have read the column under the earlier registry. Exempting a
   rewrite that changes no declared value is the alternative.
3. **Does Part 05 §5.3 name the existing column checks?** Naming the new check ID alone leaves two
   file-against-declaration checks unnamed beside it. The preferred direction names all three.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [ ] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

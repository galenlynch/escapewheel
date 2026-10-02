# An amendment drops a held column only where its recipe names it

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `deb048c5d1f9bad541c0a32ad34e043cf926b5d2` |
| **Decision domain** | specification |
| **Affects** | a new subsection at the end of Part 02 §6, under its account of which declared columns a table holds; Part 05 §3.1's recipe keys and schema identifier; Part 05 §3.5's refusals of an amending build; Part 05 §4.3, under which a table gaining no row is not written; Part 05 §5.3's shim checks and their declared inputs; Part 05 §15.2's table of what an amendment may change; Part 05 §15.6's comparison over declared columns; the recipe schema |

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
packets were built outside the tree. One draft is open, on Part 11 §§1, 4 and 8 and Part 05 §9.4,
and none of those sections is touched here. Two other proposals are open: one on a frame's `pts`
and `dropped` flag, which touches Part 01 §3.18 and core declarations only, and one on what a null
identifier says, which also adds a rule to Part 02 §6 (§4.5 orders the two).

### 2.1 A rewritten table drops the values, and nothing reports it

The writer suite holds a test of this case, named in R163 §5. It builds a packet under a copy of
the core registry at version `0.0.1` whose `core.source_files` declares one more `optional`
`json_string` column, holding `{"slope":2.0,"offset":5.0}` in the packet's one row. It then amends
the packet under the baseline registry, adding a second `core.source_files` row. Run at the
baseline, it passes (1 test, 3.7 s), asserting that:

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

### 2.3 Registry changes have removed 63 columns from tables that remain

The committed core registry was read at each of its 104 versions in the repository's history, and
each version's set of declared `resource.column` pairs compared with the one before. Fifteen
commits removed at least one pair, 76 in all, a rename counting as a removal, since a held file's
column then has no declaration either.

Thirteen of the 76 went with one table: R54 renamed `core.trials` to `core.intervals`. A held file
whose resource entry names a declaration no bound registry carries already fails under
`packet.resource.declaration_unknown` (Part 04 §10), so a removed table is outside this proposal.
The other 63 columns were removed from tables that remain, by 14 commits. The eight latest:

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
binding a registry of another standard version would have refused none of them. Twelve of the
fifteen commits, every one before R128, left the registry's version at `0.1.0`, which did not then
advance with each change. The extension registries were not counted. Removing a column is an
ordinary change to a v0.2 registry, not a rare one.

### 2.4 A registry that adds a column already fails loudly

A probe built a packet under a copy of the baseline core registry without the `nullable` column
`core.source_files.format`, then amended it under the baseline registry.

| amendment | outcome |
|---|---|
| adds only a `core.processing_runs` row, leaving `core.source_files` alone | refused, with one `error`: `schema.column_absent` on `core.source_files.format` |
| adds a `core.source_files` row | passes; the rewritten file holds `format`, null in both rows |

Ten of the 14 commits in §2.3 also added a column that is not `optional` to a table that remains,
and 29 commits in all added or retyped one. A held file then fails Part 02 §6 unless the amendment
happens to rewrite it, and the build reports the failure by name. An amending build that names no
core registry binds the packet's own (Part 05 §15.1), which declares the file's columns as they
are; that remedy serves both directions.

### 2.5 No part makes an undeclared file column non-conforming

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

### 2.6 Part 05 §15.2 is ambiguous on the point

Part 05 §15.2 forbids an amendment to "change or remove any other row of a canonical table". A
held row rewritten without one column's values is changed by one reading and not by the other.
Part 05 §15.6 takes the second, comparing only declared columns. The current contract therefore
does not already answer the question.

### 2.7 No corpus or measured packet carries an undeclared column

A scan compared every table file's columns with the declarations of the registries its packet
binds.

| population | packets | table files | with an undeclared column |
|---|---|---|---|
| the conformance corpus | 135 | 4078 | 0 |
| packets built from two recorded sessions, including one rebuilt at core `0.18.0` | 26 | 1040 | 0 |
| readable scratch packets from earlier probes and test runs | 146 | 1057 | 2 |

The corpus was scanned at `c0f9214b` and the session packets on 2026-10-02. Both scratch packets
are probes that carry the column on purpose: the one in §2.2 and one of R163's. No corpus fixture
exercises an undeclared column.

## 3. Desired outcome and constraints

An amending build should not lose a held column's values unless its recipe says it may, and a
packet's current version should hold no column that its bound registries cannot describe. A recipe
that intends the loss should be able to say so and build. The resolution should keep the rest of
Part 05 §15: superseded bytes are never modified, rows are compared over the columns the bound
registry declares, and nothing is deleted except by cleanup.

A column a later registry adds is out of scope. The build already refuses where a held file lacks
it (§2.4), and naming the packet's own core is the remedy.

## 4. Options and tradeoffs

### 4.1 What an amending build does with a held column the bound registry does not declare

- **Keep the current rule.** A rewritten table loses the values silently, and a table left alone
  keeps data that no bound registry describes (§§2.1 and 2.2).
- **Refuse outright.** The packet would remain amendable only under its own core (§2.4), never
  under a later registry that drops a column, though dropping is ordinary (§2.3).
- **Preserve the column.** A rewrite would carry forward a column that no registry the packet binds
  types, describes or checks, which leaves the second half of the problem in place.
- **Report only.** A report records the loss after the build has made it and leaves the packet
  conforming with the undeclared column. Part 05 §3.4 refuses a smaller discard unless the recipe
  names the column, and a report would not match it.
- **Reuse the column override.** Part 05 §3.5 refuses a column override whose column the resource
  does not declare, and here the column is by definition undeclared. Its meaning, releasing a
  passed-over source's value, also differs from this one.
- **Release declared by the registry.** A registry recording the columns it removed would need a
  meta-schema change and would give consent to the registry's author, who cannot judge one packet's
  values, where a per-packet remedy already exists (§2.4).
- **Refuse by default, and release where the recipe names the column.** This is the preferred
  direction. An amending build refuses, naming the table and the column, where a canonical table
  the packet holds has a column that no registry the amended manifest binds declares for it. The
  refusal names the remedy of binding the packet's own core. A recipe entry naming
  `resource.column` releases that refusal and means "drop this column on amendment". Once released,
  the build writes the table without the column, including a table the amendment would otherwise
  leave alone.

Under the preferred direction the refusal would join the list in Part 05 §3.5 of what an amending
build refuses before it opens any source. Held files are part of the packet, not a source, so the
build can read their columns at that point.

The refusal and the release reach canonical tables only. Part 05 §15.2 already lets an amendment
remove or replace an analysis, compatibility-projection or documentation resource, and a build
about to derive such a table again would otherwise need a release entry for nothing. A table of
those kinds that the amendment leaves holding the column still fails the validator finding (§4.4).

### 4.2 The release entry

The release entry is a new top-level recipe table, `[drop]`, whose key is a resource's dotted
identifier followed by a column name, spelled as Part 05 §3.6 spells a column override's key, and
whose value is a non-empty string giving the reason, as an override's value is. The recipe schema
requires `packet.amends` wherever `[drop]` appears, so a recipe that does not amend fails the
schema rather than a build-time check.

A build would refuse a `[drop]` entry before it opens any source:

- naming a resource that no registry the amended manifest binds declares as a canonical table; or
- naming a column that such a registry declares for the resource, since dropping a declared
  column's values changes rows Part 05 §15.2 forbids an amendment to change.

An entry naming a column that the held file does not hold releases nothing. The build would report
it as a warning and not refuse it, because a recipe reused after its drop was applied is
legitimate and would otherwise fail on its second run. The build would report each dropped column
as information, naming the table and the reason.

### 4.3 What the release changes elsewhere in Part 05

- **Part 05 §4.3** has a table to which the build adds no row keep its resource entry, so the
  amendment does not write it. A released column is the exception: the table is written without the
  column.
- **Part 05 §15.2** would say that removing a column no bound registry declares changes no row,
  settling §2.6 in the reading Part 05 §15.6 already takes.
- **Part 05 §15.2** also has an amendment that writes a canonical table, other than the three
  provenance tables, derive again or remove every analysis and compatibility-projection resource
  reached from it. That duty holds for a table rewritten to drop a column: the earlier registry
  declared the column, so a derivation may have read it, and Part 05 §15.6's
  `amendment.derived_resource_stale` keys on a canonical table the amendment wrote.
- **Part 05 §15.5** is unchanged: the superseded file keeps the values until cleanup, which the
  release does not hasten.

### 4.4 The validator finding

The preferred direction adds a rule, in a new subsection at the end of Part 02 §6, that a table
holds no column its declaration does not declare. The shim of Part 05 §5.3 reports each such column
of a table the current manifest names at `error`, whatever path produced it, under the check ID
`schema.column_undeclared`. Part 05 §9.5 already attributes a finding about one resource entry to
the registry whose declaration the entry's `declaration_id` names. A superseded version's files are
judged against the registries their own manifest binds, and are not checked again.

The check declares the packet manifest among its inputs. Part 05 §15.4 re-runs a shim check only
where the amendment wrote a member of its input set, and in §2.2 the table is not written; since
installing a manifest writes the manifest input, the check runs on every amendment, as the
session-inventory check does.

`error` rather than `warning`:

- a column no bound registry declares has no type, presence or description in the packet, and no
  rule can read it (Part 11 §3), so the packet cannot say what it holds;
- the reference build already refuses to deliver one (§2.5), so a packet built by it holds one only
  through the amendment path this proposal closes; and
- no corpus or measured packet holds one other than two deliberate probes (§2.7).

A `warning` would leave the file conforming. Then a second build that writes undeclared columns,
which no part forbids today, would also conform.

The two halves answer different cases. The validator finding catches a table left alone, a
non-canonical table an amendment did not replace, and a fresh build that wrote an extra column. It
cannot see a rewrite that dropped the values, because the column is then gone. Only the build's
refusal covers that.

Part 05 §5.3 would name the reference validator's two existing file-against-declaration checks,
`schema.column_absent` and `schema.column_type`, beside the new one. No part names them today, and
the conformance corpus already expects both.

### 4.5 Placement, anchors and order

Every Part 05 section the change touches carries a canonical anchor: `ew-recipe-purpose`,
`ew-recipe-check`, `ew-import-normalization`, `ew-validation-shim`, `ew-amendment-scope` and
`ew-amendment-comparison`. Part 02 §6 carries none, and has no subsection. A new subsection
appended at its end is an ordinary amendment that takes its own anchor when created, so §6 itself
is unchanged and needs no anchor bootstrap. Placing the rule in Part 03 §5.1 (`ew-table-encoding`)
instead would make a logical fact a property of one physical profile.

The proposal on what a null identifier says also adds to Part 02 §6. This proposal goes first, so
that one appends its subsection after this one's.

### 4.6 Compatibility

- **Recipe schema.** A new top-level key advances the schema's `$id` one minor version, from
  `https://escapewheel.org/schemas/recipe/0.4.0` at the baseline, and Part 05 §3.1 names the new
  identifier. A recipe that does not amend, or whose amendment drops nothing, is unchanged.
- **Check IDs.** `schema.column_undeclared` is new. Naming `schema.column_absent` and
  `schema.column_type` changes no outcome.
- **Existing packets.** No corpus or session packet changes verdict (§2.7). A packet amended by the
  reference build since R163 without writing `core.clocks`, from one holding `transform_to_parent`,
  would gain an error. No measured packet holds that column.

### 4.7 A related writer defect

The reference build passes only the resources it wrote as the set to re-check, so a rule a newer
registry adds to a table the amendment leaves alone never runs during the amendment. That breaks
Part 05 §15.4's over-inclusive test whatever this proposal decides, and is an implementation defect
to fix separately.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose (Part 01) | unchanged: no concept changes |
| logical prose (Part 02), meta-schema, declarations and rules | affected: a new subsection at the end of Part 02 §6 states that a table holds no undeclared column; the meta-schema, declarations and rules are unchanged |
| physical profiles (Part 03) | unchanged under the preferred placement; Part 03 §9's account of a rewritten table already covers a table written without a column |
| packet manifest and JSON Schemas | affected: the recipe schema admits `[drop]`, requires `packet.amends` beside it, and its `$id` advances; the manifest schema is unchanged |
| validation and import (Part 05) | affected: Part 05 §3.1's key table, Part 05 §3.5's refusal and the entry's refusals, Part 05 §4.3's exception, Part 05 §5.3's three named column checks and the new check's declared inputs, Part 05 §15.2's sentence on an undeclared column |
| extension registries | unchanged: the rule applies to every bound registry, and no extension declaration changes |
| reader, writer, validator, adapters, code generation | affected: the reference build gains the refusal, the release and its reports, and its named amendment test changes to assert the refusal; the reference validator gains the finding with the manifest among its inputs; readers, adapters and generated code are unchanged |
| existing packets and migration | unchanged: no corpus or session packet changes verdict (§2.7) |
| conformance fixtures and tests | affected: a fixture holding an undeclared column, expected at `error`; amendment tests for the refusal, the release, the idle entry, each static refusal and a non-canonical table left holding the column |
| revision lifecycle and tooling | unchanged: the new subsection takes its anchor when created, so no bootstrap is needed |
| generated publications and documentation | affected: the combined rendering, the recipe schema publication, and the writer's account of amendment |

## 6. Open questions

1. **Where does the release entry live?** **Answered 2026-10-02: a top-level `[drop]`,** and the
   recipe schema requires `packet.amends` beside it (§4.2).
2. **Does a drop-only rewrite oblige re-derivation?** **Answered 2026-10-02: yes,** Part 05 §15.2's
   duty holds (§4.3).
3. **Does Part 05 §5.3 name the existing column checks?** **Answered 2026-10-02: yes,** all three
   (§4.4).
4. **Does the proposal cover a column a later registry adds?** **Answered 2026-10-02: no,** it is
   out of scope (§§2.4 and 3).
5. **Which tables do the refusal and the release reach?** **Answered 2026-10-02: canonical tables
   only;** the validator finding still covers every table (§4.1).

No question that would change the decision is open.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

# A unit is identified outside its packet by its name

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `9c180d6c919ce2942271a92f9df28f3bb230c185` |
| **Decision domain** | specification |
| **Affects** | Part 02 §12.1's sentence on relating a unit to anything outside its packet; Part 02 §12.9's sentence of the same form for an interval; Part 02 §8.2's statement of the name an owned assigned identifier is paired with, which gains a presence, and its sentences on what checks the pairing and on checking that a name is unique; Part 02 §9.4's statement of the incorporated descriptor and of the meta-schema it selects; Part 02 §10.1 and Part 05 §5.1, which gain a generated check; the presence of the nine nullable core names; the registry meta-schema `$id`, the registry-contract descriptor ID and the core `registry_version`, with Part 02 §1's incorporation of the descriptor and Part 02 §9.2's statement of the other two; the ledger entries for R81 §2.5, R85 §2.2, R123 §3.1 and R148 §3.1, and for the clause that assigns the three identifiers |

## 1. Problem

Part 02 §12.1 tells a consumer to relate a unit to anything outside its packet by
`(sorting_run_id, local_unit_label)`. That pair does not identify a unit. Its first member is a
number the packet assigns, and the same paragraph forbids identifying a unit by `unit_id` outside
the packet because such a number means nothing there. The pair omits the curation, so two curations
of one sorting run that hold one label share a value of it. Its second member is nullable and is
permitted to repeat within one curation. Four packets of the conformance corpus that pass
validation with no finding hold units that share the pair.

The specification already states a relation that does this job. Part 01 §2.1 pairs every assigned
identifier with a name so that a process outside the packet can reference the object without the
number, the registry describes `unit_name` as the only bridge between two packets that numbered a
unit differently, and an amending build matches the rows a packet holds by that name. Part 02 §12.1
names a different relation from the one the rest of the specification uses.

Two accepted clauses stand behind the sentence and disagree about it. R81 §2.5 names the pair.
R123 §3.1 names no columns and defers to whatever relation Part 02 §12.1 defines. Part 02 §12.9
states a sentence of the same form for an interval, with an assigned number in it and a nullable
label.

## 2. Evidence

Observed in the tracked files at the baseline commit, and in the conformance corpus built from
them. The quick verifier passed all 37 of its stages at the baseline and built 120 packets. Each
corpus count below was made by reading the tables each packet's manifest lists and grouping their
rows. An amended packet also keeps the table files its amendment replaced, which its manifest no
longer lists and which are not counted. Each registry count was made by reading the generated
registry documents. §2.7 also reads two packets held outside the tree and says where it does.

### 2.1 Two accepted clauses state the relation, and the part states it without a keyword

R81 §2.5 says that `local_unit_label` is the `*_name` R53 §2.3 requires of an assigned identifier's
owner. It then binds a consumer, with a keyword, to use `(sorting_run_id, local_unit_label)` for
anything outside the packet, and forbids `unit_id` there.

R123 §3.1 binds a consumer, with a keyword, to use "the source-facing relation Part 02 §12.1
defines" outside the packet. It names no column.

Part 02 §12.1 states the pair in the indicative: a consumer "uses" it. The prohibition on `unit_id`
carries a keyword and the statement that no checker verifies it. The ledger entries for both
clauses record that the relation is stated without a keyword, and the entry for R81 §2.5 gives the
reason: the pair it names no longer identifies a unit.

The premise of R81 §2.5 does not hold in the registry. `core.units` declares `local_unit_label` and
a separate `unit_name`, and Part 02 §8.2 requires the name of `unit_id` to be the column formed by
replacing `_id` with `_name`.

### 2.2 The pair's first member is a number the packet assigns

`core.sorting_runs.sorting_run_id` declares the `assigned` identity. Part 05 §4.3 says that a
packet's identifiers are a function of the sequence of recipes that built and amended it, and that
an amending build numbers each name it adds from one past the largest value the packet holds.
R149 §4 records that no part fixes how sorting runs and curations are numbered.

One sorting run can therefore carry different values of `sorting_run_id` in two packets built by
different recipes. That is the reason Part 02 §12.1 gives for forbidding `unit_id` outside the
packet, and it applies equally to the number in the pair.

### 2.3 The pair omits the curation

Part 01 §3.13 has a unit belong to one sorting run and one curation version. Part 05 §12 says that
nothing forbids a packet holding two curations of one sorting. R81 §2.6 says that the units of two
curations of one run receive different numbers and are told apart by the run and curation columns.
R81 §1.4 says that two curations of one run disagree about what a label means. `core.units`
declares `(sorting_run_id, curation_id)` as an amendment group, so an amendment adds a curation's
units to a run the packet already holds.

Two curations of one run share a value of the pair wherever both keep one of the sorter's labels.

### 2.4 A label is nullable and is permitted to repeat within a curation

The registry declares `local_unit_label` nullable. Part 02 §12.1 orders a null label after every
other label and permits the units of one curation that tie on their label, two null labels
included, to be numbered in either order; R149 §3.1 is the clause behind that permission.
`core.units` declares six rules, and none of them requires a label to be present or to be unique.
R81 §1.4 says why a label is not always the sorter's: after a merge or a split, the label a unit
carries is the curation's.

### 2.5 Four passing corpus packets hold units that share the pair

Of the 120 corpus packets, 117 carry `core.units`, with 238 unit rows between them.

| measure over `core.units` | packets | unit rows |
|---|---:|---:|
| `local_unit_label` is null | 2 | 4 |
| the unit shares `(sorting_run_id, local_unit_label)` with another unit | 4 | 12 |
| the unit shares `(sorting_run_name, curation_name, local_unit_label)` with another unit | 2 | 4 |
| the unit's run or curation has a null name | 0 | 0 |
| `unit_name` is null | 0 | 0 |
| the unit shares `unit_name` with another unit | 0 | 0 |

The four packets in the second row are `amended_curation`, `amended_preference`,
`null_unit_labels` and `null_unit_labels_swapped`. The corpus expects each to pass with no finding.

`amended_curation` and `amended_preference` each hold one sorting run with two curations, and each
curation holds a unit labelled "17" and a unit labelled "42". The four units of each packet form
two values of the pair, and their names are "1", "2", "recurated.1" and "recurated.2".

`null_unit_labels` and `null_unit_labels_swapped` each hold two units of one curation with null
labels. The two packets number the same two units in the two orders Part 02 §12.1 permits: the unit
named "1" is the first unit in one packet and the second in the other. Their names are the only
column that says which unit is which.

### 2.6 The name is the relation the rest of the specification uses

- Part 01 §2.1 says that an assigned identifier is paired with the name it was assigned from, so
  that a process outside the packet can reference the object without knowing the number.
- Part 02 §8.2 declares the pairing and requires, with a keyword, that a name be unique within its
  packet. R85 §2.2 is the clause behind that requirement.
- The registry describes `unit_name` as what `unit_id` stands for, "the identifier a source or an
  earlier packet used for this unit", and as the only "bridge between two packets that numbered it
  differently".
- Part 05 §4.3 has an amending build number a name the packet holds with the packet's identifier
  for it. Part 05 §3.5 has an amending build refuse a packet that holds a null name for an assigned
  identifier a row owns.
- Part 02 §8.3 has a `string` paired value match the named row's key where that key is carried and
  its `*_name` where it is assigned. `core.processing_runs.scope` and `core.preferred_runs.scope`
  are such values, and both resolve `optional`, so no check reports one that names no row.
- Part 05 §3.1 has a recipe name the row a preferred run is scoped to as Part 02 §8.3 has a paired
  value name it, so that a recipe can name it before any identifier is assigned.
- Part 12 §5 has an adapter hand over identifiers as names and never as numbers.

None of these uses is particular to a unit. An amending build matches each of the 17 names of
§2.7. A paired value names a row of a table whose primary key is one column, and each of the 17
tables that own an assigned identifier has such a key.

Inside a packet nothing uses the pair. The core registry declares six references into `core.units`
and the `aind_unit_qc` extension registry declares three, and all nine are on `unit_id` alone.

### 2.7 Nine core names are declared nullable, and no check reports a name two rows share

The core registry, at `registry_version` 0.14.0, declares 45 tables, and 17 of them own an assigned
identifier as Part 02 §8.2 defines owning: the identifier is in the table's primary key and is not
a source member of a reference the table declares. Each of the 17 has a primary key of one column.
Eight of the 17 names are `required`: those of `analysis.array_assets`, `core.array_assets`,
`core.calibrations`, `core.clocks`, `core.devices`, `core.event_streams`, `core.intervals` and
`core.media_assets`. Nine are `nullable`: those of `core.curation_versions`, `core.electrodes`,
`core.probes`, `core.processing_runs`, `core.sessions`, `core.sorting_runs`, `core.source_files`,
`core.subjects` and `core.units`. R95 §2.1 observed that a generated name is nullable while it
carries the obligation to bridge two packets.

The repository holds four extension registries, `dynamic_foraging`, `vr_foraging`, `aind_opto` and
`aind_unit_qc`, which declare 3, 3, 2 and 3 tables. One of those 11 tables owns an assigned
identifier: `dynamic_foraging.blocks`, whose primary key is `(session_id, block_id)` and whose
`block_name` is `nullable`. Its registry describes that name as the block's own, "where the source
has one". The repository therefore holds 18 names of owned assigned identifiers, of which ten are
`nullable`.

Three populations were measured. In each packet, every table the current manifest lists that owns
an assigned identifier was read, and its name column was grouped by value. For the corpus the
owning tables were taken from the five generated registry documents. The other two packets are held
outside the tree. Each holds one recorded session and binds core 0.14.0 and the four extension
registries at the versions the repository carries, and its owning tables were taken from the
registries it embeds.

| population | name columns it holds, of 18 | names | null names | names two rows of one table share |
|---|---:|---:|---:|---:|
| the 120 corpus packets | 14 | 2,777 | 0 | 1 |
| a packet of 6,781 units | 16 | 12,243 | 0 | 0 |
| a packet of 4,505 units | 17 | 8,932 | 0 | 0 |

The one shared name is in `dup_pk`, where an `interval_name` occurs twice. That packet duplicates a
whole row of `core.intervals`, and the corpus expects it to draw `core.intervals.primary_key_unique`
at `error`. The corpus runner counts a failing packet as behaving where its expected check fires.
A further finding beside it changes that only where the packet's record names the check as one
that must be absent, and the record of `dup_pk` names none. No packet the corpus expects to pass
holds a shared name, and no packet of the three populations holds a null one.

The corpus holds no row of `analysis.array_assets`, `core.calibrations`, `core.media_assets` or
`dynamic_foraging.blocks`. Between them the two other packets hold rows of the last three, 37 in
`dynamic_foraging.blocks`. No measured packet holds a row of `analysis.array_assets`, so its name is
the one of the 18 for which nothing was measured.

Every measured packet holds exactly one session. The two packets outside the tree name their
blocks `block_01`, `block_02` and so on, with nothing of the session in the name. By inference from
that spelling, a packet of two sessions would hold `block_01` in two rows of
`dynamic_foraging.blocks` that differ in `session_id`, unless its recipe told the two sessions'
names apart, as the `prefix` option of §2.8 does for an adapter that accepts it. No tracked source
names that table, so what composes its names was not read. Part 02 §8.2 requires a name to be
unique within its packet, and the key of that table would distinguish those two rows. The 17 core
tables do not raise the question, since each has a key of one column.

Part 01 §2.1 says that an assigned identifier is paired with the name it was assigned from, and
Part 12 §5 requires an adapter to hand over each identifier as a name. A build that follows both
holds a name for every row it numbers. Observed in the reference implementation: the writer
numbers an assigned identifier from the text an adapter delivers in the identifier's column, and
fills the name with that text wherever the adapter delivered no name of its own. A row it writes
therefore holds a name for each assigned identifier it owns, whichever of the 17 tables it is in.
The reader presents `session_name` and admits a null one.

Part 02 §8.2 says that no rule can check uniqueness, because a writer that numbers an identifier
per distinct name has already merged two things sharing a name into one row. That reasoning covers
the merge. A packet in which two rows of one table carry one name is a different defect. It arises
where a writer numbers its rows from something other than the name it records, as the reference
writer does for a row whose adapter delivers a name beside the identifier's text. A query that
groups one table's rows on the name and reports each group of more than one draws it, as the
declared rule `core.intervals.label_unique_within_kind` does for a label. No table declares such a
rule for a name, and Part 02 §10.1 has a validator generate no such check.

### 2.8 No part says how a unit's name is composed

Part 12 §5 has an adapter hand over "the names its source used". A sorter's own name for a unit is
its label, and R81 §1.2 measured 810 distinct labels across 6,781 units over 12 runs in one
session. A name that is unique within the packet therefore includes more than the label. R85 §2.2
places the obligation on whatever composes the name, and no part says what a unit's name is
composed from.

Observed in the reference implementation:

- The sorter adapter composes a unit's name from the run's name, the curation's name and the label
  padded with zeros to the width of the stream's largest label, joined by `|`. It composes the
  run's name from the stream's key, and the curation's name from that key and a recipe option that
  names the curation.
- The writer numbers one identifier per distinct name and writes that name to `unit_name`.
- Each of the seven adapters the reference writer ships, and three of the four in the AIND
  package, accepts a recipe option, `prefix`, whose text the adapter prepends to the names it
  composes. No part or artifact defines it: a search of `spec/parts/` and `spec/artifacts/` for
  "prefix" finds only a resource that is a prefix of objects.
- The corpus builder names its units "1", "2", "recurated.1" and "recurated.2".

Two producers in the tree thus compose different names for a unit, and one recipe option changes
the names a build composes.

The following is inference from those observations and from Part 05 §4.3. Two builds give a unit
the same name where one recipe produced both, or where both composers follow one convention with
the same options. Nothing in the specification makes two independently written writers agree on a
name. The same holds for `sorting_run_name` and `curation_name`. Of the columns in the three
candidate relations, only `local_unit_label` is the source's own value.

### 2.9 A build relates a later source's units by a third relation

Part 12 §4 has a build supply the term `units`: one record per unit, holding the source's label
for it and the identifier assigned. In the reference build each record holds the label, the unit's
name, and the text after the last `.` of the sorting run's name, which is a device's name. Three
reference adapters find a unit of their own source by the device's name and the label: the one
that reads a sorting's waveforms, the AIND dialect of the NWB adapter and the AIND unit-quality
adapter. Each relates a unit to a file outside the packet by a probe and the sorter's label, and
none by the unit's name, which the file does not hold. Two curations of one run, or two runs over
one probe, share a value of that pair wherever both hold a label, as two curations share the pair
of Part 02 §12.1.

### 2.10 The interval sentence has the same form and two of the same weaknesses

Part 02 §12.9 says that a consumer relating an interval to anything outside the packet uses
`(session_id, interval_kind, local_interval_label)`. `core.sessions.session_id` declares the
`assigned` identity, so the first member is a number the packet assigns. `local_interval_label` is
nullable. `core.intervals.label_unique_within_kind` draws a label two intervals of one session and
kind share, and skips a null label.

R148 §3.1 states that relation in the indicative and declares the rule with it. R148 §2.6 gives the
reason for the rule: were a source's labels free to repeat within a session and kind, the relation
would name two intervals. The same clause declares `interval_name` as `required` and describes it,
as the registry describes `unit_name`, as the only bridge between two packets that numbered an
interval differently. For a unit, R149 §3.1 later went the other way and permits tied and null
labels.

Of the 120 corpus packets, 119 carry `core.intervals`, with 366 rows between them. No label is
null. Two packets hold intervals that share the triple, `dup_pk` and `repeated_interval_label`, and
both are expected to fail. The corpus therefore shows no passing packet in which the interval
triple fails, where it shows four for the unit pair. The triple identifies an interval whose label
is present, by a checked rule. What remains is the assigned `session_id` and an interval with a
null label.

Observed in the reference implementation: the NWB adapter composes an interval's name from the
session's name, the interval's kind and its label, joined by `/`. The corpus builder composes its
names the same way. In 363 of the corpus's 366 interval rows the name is the triple with the
session's name in place of its number, and the other three are in two packets built to fail,
`orphan_manifest_session` and `repeated_interval_label`.

### 2.11 Nothing in the tree depends on the pair

`revisions/impact.py` lists 115 citations of Part 02 §12.1, Part 02 §12.9, Part 02 §8.2 and
Part 01 §2.1 outside this proposal: 59 in the parts, the packages, the fixtures and the
conformance probes, 54 in the audit notes under `revisions/audit/`, and two in an open draft.
Each citer of Part 02 §12.1 and of Part 02 §12.9 in the reader, the writer, Part 03 §5.3, the
fixtures and the conformance probes was read. Each concerns the key, the numbering or the clock of
a unit, or the key or the numbering of an interval, and none uses the pair or the triple. No
validator source cites either section. No reader or validator source reads `local_unit_label` or
`unit_name`.

Each of the 29 citers of Part 02 §8.2 outside the audit notes was read at its line. None says that
a name may be null or relies on a nullable one. One restates the sentence this change rewrites: a
docstring in the specification tools' conventions module says that no rule can enforce uniqueness.
The two in the sidecar draft concern the pairing (§2.12).

The structural form of §4 also changes Part 02 §1, Part 02 §9.2, Part 02 §9.4, Part 02 §10.1 and
Part 05 §5.1. `revisions/impact.py` lists 191 citations of those five outside this proposal: 33 in
the parts, the packages, the tools and the root documents, 124 in the audit notes,
28 in the three other open proposals, five in the open drafts and their index, and one in another
file under `revisions/`. Each citer outside the audit notes and the other proposals was read at
its line. Those of Part 02 §1, Part 02 §9.2 and Part 02 §9.4 concern the incorporated artifacts,
the identifiers and the complete registry result, and none states which invariants the contract
holds. Of the seven citers of Part 02 §10.1, the validator's design document lists the generated
kinds, as Part 05 §5.1 does, and the other five concern one existing kind or the generator as a
whole. Part 05 §5.1 is cited only from the audit notes.

### 2.12 Other open work advances the core version and no other surface this change touches

Two drafts are open.

- "A build records a recipe without its credentials" amends Part 05 §3.2, Part 05 §3.5 and
  Part 05 §7 and changes no registry, schema or descriptor. It adds a refusal to Part 05 §3.5 and
  leaves that section's refusal of a null name, which §2.6 cites.
- "Core declares a catalog of sidecars" adds three declarations to the core registry, taking it
  from 48 to 51 declarations and from 45 to 47 tables, and says that the meta-schema and the
  registry-contract descriptor are unchanged. In Part 02 it amends Part 02 §2.2, Part 02 §2.6,
  Part 02 §4, Part 02 §5.3, Part 02 §9.2 and Part 02 §13, and adds a subsection at the end of
  Part 02 §11 and of Part 02 §12. It amends none of Part 02 §1, Part 02 §8.2, Part 02 §9.4,
  Part 02 §10.1, Part 02 §12.1, Part 02 §12.9 and Part 05 §5.1, and neither `core.units` nor
  `core.intervals`. Its amendment of Part 05 §4.3 concerns how an amending build settles a
  delivered row, and leaves the numbering of names that §2.6 cites. A subsection added after
  Part 02 §12.9 renumbers no section this change touches. Neither of its tables owns an assigned
  identifier, so the 17 of §2.7 stand, and neither declares a name the structural form of §4 would
  check. Its two citations of Part 02 §8.2 concern the pairing of a name with an assigned
  identifier, which this change keeps.

That draft's `core.sidecar_scopes.scope` is a `string` paired value whose discriminator resolves
`required`. A scope therefore names a row by its `*_name` where the row's key is assigned, and the
paired-value check of Part 02 §8.3 reports at `error` a scope that matches no row. The rule reads
Part 02 §8.3 as it stands and does not depend on this change. This change helps it in two ways. A
row whose name is null cannot be named by a scope, and nine of the 17 tables a scope can name
declare a nullable name. A scope whose value two rows share matches both and passes the check,
and no check reports the shared name. Under the structural form each of the 17 names is `required`
and each is checked for a value two rows share.

Three further drafts are open, each promoted after the `Based on` commit.

| draft | core registry | `core.units`, `core.intervals` | Part 02 §8.2, Part 02 §10.1, Part 02 §12.1, Part 02 §12.9, Part 05 §5.1 | meta-schema `$id`, descriptor ID | `registry_version` |
|---|---|---|---|---|---|
| "Core declares a clock's transform in typed columns alone" | removes one column of `core.clocks` | no | no | no | advances |
| "A null producing run on an array says the packet names none" | rewords the description of `processing_run_id` in the two array-asset tables | no | no | no | advances |
| "A recipe accepts a discarded value by naming its column" | no | no | no | no | no |

This change, the sidecar draft and the first two drafts in the table each advance the core
`registry_version` and restate it in Part 02 §9.2. This change alone also advances the meta-schema
`$id` and the descriptor ID (§2.13), which Part 02 §1, Part 02 §9.2 and Part 02 §9.4 state. Apart
from those statements, no one of the four changes text or a declaration another changes, so they
can be incorporated in any order, and each takes the core version after the one the registry
carries when it is incorporated. None of the other three declares a table that owns an assigned
identifier, so each meets the new contract whether it is incorporated before this change or after
it. The clock-transform draft says that the ledger entry for R152 §3.4 stays `applied` because
its meta-schema and descriptor rows remain. Under this change those two identifiers advance as
well, so whichever of the two is incorporated second restates what that entry holds (§4). The credential draft and the recipe
draft change no registry and are independent of all four. Whatever is incorporated after the
sidecar draft counts 47 tables where §2.7 counts 45.

### 2.13 The registry-document contract checks the pairing, and a changed contract takes a new descriptor

Part 02 §9.4 incorporates one descriptor, `escapewheel-registry-contract-v0.9`, which selects the
0.11.0 meta-schema and lists 29 invariants. `registry.identity.name` is one of them, at phase
`semantic`, for the classes `core` and `extension`, with the anchors of Part 02 §8.2 and
Part 02 §9.4. Part 02 §9.4 says that a descriptor holds identities and applicability only and that
the prose of the parts owns each algorithm. What the invariant reports is therefore what
Part 02 §8.2 states: each owned assigned identifier has exactly one name, the name is a `string`
`data` column declaring no `identity`, and no table that carries or references the identifier
declares the same-base name. Part 02 §8.2 states no presence for the name. Observed in the tree:
the specification tools and the validator hold byte-identical copies of the invariant, and it reads
the name column's type, role and `identity` and does not read its `presence`.

The following is inference. The requirement relates two columns of one table through the table's
key and references, so the meta-schema, which validates each column object by its own members,
cannot state it as shape. It belongs to the `semantic` phase, where the pairing is checked.

Part 02 §9.4 requires a registry's class and its registry-schema, semantic-standard,
logical-standard and rule-language identifiers to select exactly one local descriptor, and forbids
reinterpreting a descriptor ID, or a tuple that selected a contract, after publication.
Part 02 §9.2 forbids reusing a development identifier for an incompatible contract. The core
registry at the baseline is valid under the v0.9 descriptor and declares nine nullable names
(§2.7). A contract under which a nullable name is a defect makes that document invalid, so it is a
different contract, and it takes a new descriptor ID. The tuple that selects v0.9 keeps selecting
it, so the new descriptor is selected by a tuple that differs in one component.

One accepted clause changed the contract's invariants and no shape. R145 §3.5 added an invariant,
advanced the meta-schema `$id` from 0.7.0 to 0.8.0, the descriptor ID from v0.4 to v0.5 and the
core `registry_version`, and said that the meta-schema changes only its `$id`. R152 §3.4 advanced
the same three identifiers, the `$id` from 0.10.0 to 0.11.0 and the descriptor ID from v0.8 to
v0.9, with the invariant R152 §3.3 added. Each also required an extension registry migrated to the
new meta-schema to carry a `registry_version` different from the one it carried before, said that
no checker verifies this, and left the value to the extension, as Part 09 §5.5 does. Part 02 §9.2
carries one such sentence for each of four migrations, three of the meta-schema and one of the
rule language. No accepted clause that was read widens what an existing invariant ID reports,
which is why §6 asks where the presence is checked.

The three identifiers are carried as follows. Each count is of files in the tree that hold the
identifier's text, outside the accepted revisions, their evidence, the audit notes and the built
corpus.

| identifier | files | which |
|---|---:|---|
| meta-schema `$id` ending `registry/0.11.0` | 26 | the meta-schema and the validator's copy of it; the descriptor and the validator's copy; the core registry's source and its generated document; the sources and generated documents of the four extension registries; Part 02 and the combined specification; the specification tree's checker; and nine test and probe files |
| descriptor ID `escapewheel-registry-contract-v0.9` | 11 | the descriptor and the validator's copy; Part 02 and the combined specification; the two registry-document checkers; the specification tree's checker and its test; the fact generator; the registry source's guide; and the validator's package metadata |
| core `registry_version` 0.14.0 | 10 | Part 02 §9.2, Part 08's example and the combined specification; the core registry's source, its generated document and its generated table listing; the specification README's identifier table; the specification tree's checker and one of its data modules; and one writer test. Each packet's manifest records it, and the `dynamic_foraging` registry carries the same text as its own version |

Each of the four extension registries in the repository names the 0.11.0 meta-schema in `$schema`,
so each migrates, and each then carries a version other than the 0.14.0, 0.13.0, 0.12.0 and 0.13.0
that `dynamic_foraging`, `vr_foraging`, `aind_opto` and `aind_unit_qc` carry now.

Observed in the tree: the validator holds one meta-schema and one descriptor. Part 02 §9.4 makes
evaluation `unsupported` for a selector it does not hold, Part 05 §14.5 lets only a `valid`
context direct packet checks, and Part 05 §9.5 gives a registry whose result is `unsupported` a
verdict of `incomplete`. A validator that holds only the new pair therefore reports `incomplete`
for a packet that binds a registry under the 0.11.0 meta-schema, until that packet is rebuilt.

### 2.14 A check generated from structure is stated in two sections and reaches these surfaces

Part 02 §10.1 states what a validator generates from a declaration alone: a non-null check for
each `required` column, an anti-join for each foreign key, a membership check for each closed
vocabulary, and, for each column declaring `finite: true`, a check that reports each row holding a
non-finite value, at `error`, under the ID `<declaration_id>.<column>.finite`. For that last check
it says that an `optional` column a table omits draws nothing, places the finding with the
registry that holds the declaration, and points to the section that applies the check to an
extension's columns. It separately requires a validator to establish that a primary key is unique,
by query or by a means a physical profile defines. Part 05 §5.1 lists the same kinds.

Three sections cover a generated check without naming its kind, and so cover a new kind as they
stand. Part 05 §5.4 applies to an extension's resources every check of Part 05 §5.1 that a core
resource receives because of its declarations. Part 05 §9.5 gives a generated check's finding to
the registry whose declaration generated it. Part 05 §15.4 takes a generated check's inputs from
the declarations that generated it and re-runs the check when its resource is written.

A check generated for the name of every owned assigned identifier is generated for 17 columns of
the core registry and one of `dynamic_foraging`. The core registry yields 175 generated non-null
checks at the baseline, one for each `required` column, and nine `required` names make it 184. The
`dynamic_foraging` registry yields eight, and a `required` `block_name` makes it nine.

The surfaces below were found by searching the tree for the IDs of the two generated kinds that
carry one, `primary_key_unique` and `finite`, and by reading each citer of Part 02 §10.1 and
Part 05 §5.1 that `revisions/impact.py` lists outside the audit notes.

| surface | what a new generated kind changes |
|---|---|
| Part 02 §10.1 and Part 05 §5.1 | the statement of the check and the list of kinds |
| the validator's generator of Tier 1 checks | one more check for each table declaration that owns an assigned identifier |
| the validator's table of check IDs | one more ID family; the validator's guide has each ID written once there, and a test holds that |
| the validator's tests, README and design document | tests of the new kind; the README's table of kinds and what declares each; the design document's list of kinds |
| generated counts | the sentence of Tier 1 counts the fact generator computes into the validator's README, and the per-kind counts the specification renderer computes into the registry source's guide, each of which lists kinds by name |
| the conformance corpus | a failing packet's record states the check it draws, and the corpus guide describes the packets |
| the specification tree's checkers | none: they check a registry document and generate no packet check |
| reader and writer | none found: no reader or writer source holds either existing ID |

## 3. Desired outcome and constraints

Part 02 §12.1 names a relation that identifies exactly one unit of a packet without the packet's
numbers, every unit of a conforming packet has a value for it, and a validator reports a packet in
which it is absent or shared. The interval sentence of Part 02 §12.9 takes the same form. The name
of every other owned assigned identifier, in core and in an extension, is present and checked in
the same way. The ledger says which accepted clause each sentence now carries.

Each affected fact has one owner. Part 02 §12.1 and Part 02 §12.9 own the two sentences.
Part 02 §8.2 owns what a name is, its presence, that it is unique, and what a check can report of
that. Part 02 §9.4 owns the contract that checks a registry's declaration of a name, and
Part 02 §10.1 owns the checks a validator generates from one. Each registry owns its names'
declarations, which follow Part 02 §8.2. Part 02 §1, Part 02 §9.2 and Part 02 §9.4 own the
statements of the three identifiers. Part 01 §2.1 owns the purpose of a name and is not changed.
The change is at the logical level: it alters no concept of Part 01 and no storage property.

The resolution preserves:

- `unit_id` as the whole key of `core.units` and of every reference into it;
- the prohibition on identifying a unit by `unit_id` outside the packet that assigned it;
- `local_unit_label` as the source's own spelling, nullable, with the numbering order and the
  permission for tied and null labels that R149 §3.1 states;
- Part 05 §13.1's rule that a reader presenting several packets distinguishes them by a session
  discriminator it does not derive from a name; and
- the conformance of every packet the corpus expects to pass.

## 4. Options and tradeoffs

Questions 3 and 4 of §6 are answered: a name's presence and its uniqueness are stated once, for
every owned assigned identifier, and follow from structure. This section describes the options
under that form and keeps the alternatives each answer set aside.

| option | effect |
|---|---|
| keep `(sorting_run_id, local_unit_label)` | the sentence names a relation that fails in four passing corpus packets (§2.5), contains a packet-assigned number (§2.2) and omits the curation (§2.3) |
| strike the sentence and keep the prohibition | Part 02 §12.1 then says what a consumer does not use and leaves the positive relation to Part 01 §2.1; R81 §2.5 and R123 §3.1 each keep a positive duty with no text carrying it |
| `(sorting_run_name, curation_name, local_unit_label)` | removes the assigned number and adds the curation; identifies a unit only where its label is present and unique within its curation, which Part 02 §12.1 does not require (§2.4) |
| state the relation once, in Part 02 §8.2, for every owned assigned identifier | one owner for a rule that is the same for all 17 identifiers, and true of every row once each name is `required`; it extends a consumer-facing statement to 15 identifiers for which no accepted clause makes one, and R123 §3.1 still has Part 02 §12.1 define a relation |
| `unit_name` (preferred direction) | the relation Part 01 §2.1, Part 02 §8.2 and Part 05 §4.3 already use (§2.6); unique and present in every unit row measured (§2.5, §2.7); the name is `required` and a generated check draws one two units share, as for every owned assigned identifier |

The three candidate relations compare as follows.

| question | `(sorting_run_id, local_unit_label)` | `(sorting_run_name, curation_name, local_unit_label)` | `unit_name` |
|---|---|---|---|
| unique within a packet by an existing key or check | no key and no check; shared in 4 passing corpus packets | no key and no check; shared in 2 passing corpus packets | Part 02 §8.2 requires it; no key and no check at the baseline; shared in no measured packet |
| null | the label is nullable, and null in 4 corpus rows | all three columns are nullable at the baseline; the label is null in 4 corpus rows | declared nullable at the baseline; null in no measured row; an amending build refuses a packet where it is null |
| the same value from two builds of one source | the label yes; the run's number only under the same sequence of recipes | the label yes; the two names where the composer and its options are the same | where the composer and its options are the same; one recipe reproduces it (Part 05 §4.3) |
| held by a file the sorter or a later pipeline wrote | the label only | the label only | no (§2.9) |
| what the reference writer records | the run's number and the sorter's label | the adapter's composed names and the sorter's label | the adapter's composed name: run, curation and padded label (§2.8) |

What each costs:

| cost | keep the pair | the triple of names and label | `unit_name` (preferred direction) |
|---|---|---|---|
| part text | none; the sentence stays untrue | Part 02 §12.1's sentence; the permission for null and tied labels is withdrawn, or the sentence is limited to units whose label is present and untied | one sentence in Part 02 §12.1 and one in Part 02 §12.9; under the structural form, Part 02 §8.2's pairing statement and its sentences on checking, a paragraph of Part 02 §10.1, a phrase of Part 05 §5.1, and the identifiers in Part 02 §1, Part 02 §9.2 and Part 02 §9.4 |
| registry declarations and rules | none | `local_unit_label` becomes `required`; a rule draws a label two units of one curation share; the description of `unit_name` as the only bridge is reworded | `unit_name` and the eight other nullable core names become `required`; their descriptions stand; no rule is declared |
| identifiers | none | the core `registry_version` advances | the meta-schema `$id`, the registry-contract descriptor ID and the core `registry_version` advance, and each extension registry migrates (§2.13) |
| writer | none | a writer composes a label for a unit its source did not label, which the column is defined not to hold | none observed: the reference writer fills every name in every row |
| validator | none | evaluates one more declared rule | generates one more kind of check (§2.14) and holds the new contract; the core registry yields nine more non-null checks |
| corpus | none | `null_unit_labels` and `null_unit_labels_swapped` become failures or are removed, with the cases of R149 §3.1 they exercise; negatives for a null and a repeated label | no packet changes verdict, and `dup_pk` draws the new check beside its key check; negatives for a null name and a shared name, and negative registry documents for a nullable name |
| consumer | a relation that does not identify | two joins, to `core.sorting_runs` and `core.curation_versions` | one column of `core.units` |

Under the preferred direction, Part 02 §12.1's sentence says that a consumer relating a unit to
anything outside the packet uses `unit_name`. The prohibition on `unit_id` that follows it is
unchanged.

**The name reaches what holds a name, and the label reaches the sorter's own files.** Another
packet, a recipe and a later build each hold names, and `unit_name` identifies a unit to them. A
file the sorter or a later pipeline wrote holds the sorter's label and no name, and the three
adapters of §2.9 relate a unit to such a file by a probe and the label. "Anything outside the
packet" in the present sentence covers both, and the name serves only the first. A draft's
sentence says which it covers (question 1).

**The label stays a fact about the unit and stops being presented as an identity.**
`local_unit_label` keeps its column, its type, its nullability and its place in the numbering
order. It records what the sorter called the unit within its run and curation, and a consumer
looking for the sorter's own record of a unit reads it together with the unit's run and curation
rows. Part 02 §12.1's first paragraph already says what the label records.

**The name of every owned assigned identifier is `required`, stated once.** A relation a consumer
is told to use has a value in every row. Every source can supply one: Part 01 §2.1 has each
assigned identifier assigned from a name, Part 12 §5 has an adapter deliver each identifier as a
name, and a writer that numbers its rows by any other means can record whatever it numbered each
row from. No writer change is observed to be needed, since the reference writer fills every name
in every row it writes (§2.7) and the three measured populations hold no null among 23,952 names.
Part 05 §3.5 already refuses to amend a packet in which a name is null, and `interval_name` has
been `required` since R148 §3.1 declared it.

The argument is the same for every owned assigned identifier, in core or in an extension, so the
requirement sits where the pairing does. Part 02 §8.2's pairing statement has the name be a
`string` `data` column that declares no `identity`, and under the structural form it also has the
name's presence be `required`. The registry-document contract reports a registry that declares it
otherwise (§2.13). The nine nullable core names change as a consequence, since the core registry
conforms to its own contract, and Part 02 §10.1 then generates a non-null check for each with no
further text. An extension table that owns an assigned identifier is bound in the same way when
its registry migrates. One table in the repository is in that position, and its registry's
description of the name as present "where the source has one" no longer holds for it (§2.7).

A packet that holds a null name keeps conforming to the registry it binds and fails the generated
non-null check once it binds the new one. Its writer records a name for the row and rebuilds. No
measured packet holds one.

The alternative declared the presence table by table. It changes nine declarations and no
contract, leaves an extension free to declare a nullable name, and leaves each later core table to
make the choice again. It is not the direction taken.

**A generated check reports a name two rows share.** Part 02 §8.2 requires a name to be unique
within its packet and says that no rule can check it. A query that groups one table's rows on the
name reports two rows that carry one (§2.7). Under the structural form Part 02 §10.1 states that
check once, generated from the declaration for the name of every owned assigned identifier, in the
way it states the check for a column declaring `finite: true`: what the check reports, its level
and its ID. Part 05 §5.1 lists it among the generated kinds. Part 05 §5.4, Part 05 §9.5 and
Part 05 §15.4 cover it as they stand (§2.14), so it reaches an extension's table, is attributed to
the registry that declares the table, and is re-run when the table is written, with no further
text. No registry declares a rule. One measured packet draws the check: `dup_pk`, on
`interval_name`, beside the key check it is built to draw.

Part 02 §8.2's paragraph on uniqueness changes in two places and keeps the rest.

- The sentence that the registry-document contract checks the pairing as `registry.identity.name`
  says that the contract checks the pairing and the name's presence. Question 9 asks under which
  invariant.
- The sentence that begins "No rule can check uniqueness" is replaced, because a check now reports
  one of the two defects it covers. The replacement says that the check Part 02 §10.1 generates
  reports two rows of one table that carry one name. It then says that no check reports two things
  a composer merged under one name. The present sentence's reason is kept for that case alone: a
  writer numbering an assigned identifier per distinct name has emitted one row for both, and that
  row cannot be told from the correct case, which the sentence illustrates with four streams that
  name one serial and become one device.
- The closing sentence, that the obligation falls on whatever composes the name, stays. A composer
  remains the only guard against the merge.
- The requirement itself, that an assigned identifier's name is unique within its packet, and the
  sentence on a name that names a kind of thing, are unchanged, subject to question 11.

The alternative declared a rule per table: two, on the tables whose sections tell a consumer to use
the name, or 17. It leaves an extension's names unchecked and each later table to declare its own
rule. It is not the direction taken.

**The structural form changes the registry-document contract, and with it three identifiers.** A
registry that is valid under the incorporated descriptor and declares a nullable name is invalid
under the new requirement. Part 02 §9.4 forbids reinterpreting a published descriptor, so the
contract takes a new descriptor ID, and the tuple that selects it differs in the meta-schema
`$id`, which changes in nothing else (§2.13). The core `registry_version` advances with the nine
declarations. Each extension registry migrates to the new `$id` and takes a version of its own
choosing. Part 02 §9.2 says so for this migration as it does for the earlier ones, and no checker
verifies it. Question 8 asks how the clause states the three advances.

**The generated check reads structure that every registry has.** The check for a column declaring
`finite: true` is triggered by a member that only a registry under the meta-schema defining it can
carry. The check for a name is triggered by a key, the references and a column name, which a
registry under an earlier contract declares too. A validator that holds an earlier descriptor
beside the new one therefore generates the check for a packet bound to an earlier registry. It
reports there a shared name that Part 02 §8.2 already forbade and that nothing checked. Such a
packet can hold a null name, since its registry declares the name nullable. A null name is no
value two rows share, and the check does not count it. Question 10 carries the check's form.

**A name whose table has a key of several columns.** Part 02 §8.2 scopes a name's uniqueness to the
packet. Each of the 17 core tables that own an assigned identifier has a key of one column, so a
row's name and its key agree about which rows are distinct. One extension table has a key of a
session and an assigned identifier, and the names measured in it do not include the session
(§2.7). The generated check either groups on the name alone, as Part 02 §8.2 states the
requirement, or groups on the name within the key's other members. Question 11 asks which.

**The name is not a global identity.** A consumer relating units of several packets still says
which packet or session a name belongs to, as Part 05 §13.1 has a reader do. Two builds agree on a
name under the conditions §2.8 states, and the preferred direction leaves the composition of a
name where R85 §2.2 placed it (question 5).

**The interval sentence takes the same form.** Part 02 §12.9's sentence says that a consumer
relating an interval to anything outside the packet uses `interval_name`.
`core.intervals.label_unique_within_kind` and the clause that states it are unchanged: the rule
still refuses a source that repeats a label within a session and kind, and no longer has to carry
an identity. The change removes the assigned `session_id` from the relation and covers an interval
whose label is null (§2.10).

A third form keeps the triple and puts `session_name` in place of `session_id`. It removes the
assigned number, keeps a relation an existing rule checks, and reads the source's own label, which
a file outside the packet also holds. It leaves an interval with a null label without a relation.
It relies on `session_name`, which the structural form makes `required`. In the reference
implementation and the corpus the name already spells that triple as one string (§2.10), so the
two forms name the same intervals there. Question 2 asks which form the interval sentence takes.

**The triple is not preferred** because it identifies a unit only after `local_unit_label` is made
present and unique within a curation. That withdraws the permission R149 §3.1 gave, turns two
passing fixtures into failures, and asks a writer to invent a label for a merged or split unit that
its source did not label (§2.4). Its two names are composed by the same adapter that composes
`unit_name`, so it is no more stable across writers (§2.8).

**Stating the consumer's relation once in Part 02 §8.2 is not preferred.** With every name
`required`, a general sentence there is true of every row, which it was not while nine names were
nullable. Three reasons against it remain. Part 01 §2.1 already gives the general purpose of a
name. Only two sections state a relation for a consumer, the two this change corrects, and a
general sentence would extend that statement to 15 identifiers for which no accepted clause makes
one. R123 §3.1 defers to the relation Part 02 §12.1 defines, so that section keeps a sentence
whichever option is chosen.

**The ledger keeps R81 §2.5 and R123 §3.1 `applied`, each with a note.** Neither is replaced
whole, so neither becomes `superseded`.

- R81 §2.5 states three things: the label keeps its column, a consumer uses the pair, and a
  consumer does not use `unit_id`. The new clause replaces the second and keeps the other two. The
  entry stays `applied` at the anchor `ew-unit-identity`, with a note that the new clause replaces
  the pair it named and that the name it took the label to be is `unit_name`. Two ledger entries
  already record a clause replaced in part this way, those for R79 §2.1 and R93 §3.5.
- R123 §3.1 defers to the relation Part 02 §12.1 defines and names no column, so it remains true.
  Its entry stays `applied` at both of its anchors, with a note that the relation Part 02 §12.1
  defines is `unit_name` under the new clause.
- R148 §3.1's destination at `ew-interval-identity` records that the clause states what a consumer
  relates outside the packet. Its entry stays `applied`, with a note that the new clause replaces
  the triple it named.
- R85 §2.2's destination at Part 02 §8.2 records that a name is unique within its packet. Its
  entry stays `applied`, with a note that the new clause restates what a check reports.
- R149 §3.1 is unchanged.
- R152 §3.4 assigns the meta-schema `$id`, the descriptor ID and the core version the tree carries
  at the baseline, and its entry is `applied` at Part 02 §1, Part 02 §9.2 and Part 02 §9.4. The new
  clause advances all three. The ledger holds two precedents. The entries for R145 §3.5 and
  R150 §3.10, each of which assigned a meta-schema `$id` that a later clause advanced, are
  `applied`. The entry for R151 §3.2, whose whole content was a core version, is `superseded`.
  R152 §3.4's sentence on an extension's migration stays in Part 02 §9.2, so its entry follows the
  first precedent and stays `applied`, and a draft says what its notes then read. Where another
  change has advanced the core version first, the entry of that change's version clause follows
  the second.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §2.1 already says that a name is what a process outside the packet references, and Part 01 §3.13 prescribes no key. |
| logical prose, registry meta-schema, declarations and rules | Affected. Part 02 §12.1 and Part 02 §12.9 each change one sentence. Part 02 §8.2 gains the presence of a name and restates what is checked (§4). Part 02 §10.1 gains a generated check. The nine nullable core names become `required`, and no rule is declared. The meta-schema changes only its `$id`. The registry-contract descriptor takes a new ID and selects the new `$id`, and whether its list of invariants changes is question 9. Part 02 §1 incorporates the new descriptor, Part 02 §9.2 restates the `$id` and the core version and gains a sentence on an extension's migration, and Part 02 §9.4 restates the descriptor ID and the meta-schema it selects. |
| physical profiles | Unchanged. No storage property is involved. Part 03 §5.3 cites Part 02 §12.1 for the numbering of units, which stays as it is. The generated check is a query over one table and asks nothing of a profile. |
| packet manifest and other JSON Schemas | Unchanged. The manifest schema, the descriptor schema and the registry-result schema keep their shape, and none names the relation, a column's presence or an invariant ID. A manifest records each bound registry's version as it does now. |
| validation and import | Affected. Part 05 §5.1 lists one more generated kind. Part 05 §5.4, Part 05 §9.5 and Part 05 §15.4 cover it as they stand (§2.14), and the generated non-null check covers each `required` name. Part 05 §3.5's refusal of a null name stays as a guard against a packet that does not conform. Part 05 §14.5 is unchanged: a registry the new contract finds invalid directs no packet check. |
| extension registries | Affected. Each registry that migrates to the new `$id` takes a new version of its own. One that declares a nullable name for an owned assigned identifier is invalid under the new contract until its owner declares the name `required`. Of the four registries in the repository, `dynamic_foraging` is in that position, for one column of one table. The three references of `aind_unit_qc` into `core.units` are on `unit_id` and are unaffected. Unknown for an extension registry outside the repository, since none was read. |
| reader, writer, validator, adapters, code generation | The generated registry documents and tables regenerate, and the validator's copies of the meta-schema and the descriptor follow their sources. The validator gains one generated kind on the surfaces of §2.14, and both copies of the registry-document checker gain the presence requirement. No change to the reader is expected: it reads neither the label nor the unit's name (§2.11), and it admits a null `session_name`, which a packet bound to an earlier registry can hold. The reference writer already fills every name in every row (§2.7). Unknown whether whatever produces `dynamic_foraging.blocks` always delivers a name, since no tracked source names that table. Whether the `units` term of Part 12 §4 and the three adapters that use it change is question 6. |
| existing packets | Every existing packet binds registries under the 0.11.0 meta-schema, and a validator that holds only the new contract reports it `incomplete` until it is rebuilt (§2.13). A rebuilt packet whose every name is present, and distinct within its table, meets the new registries. One holding a null or a shared name does not, and its writer records or corrects the name. No measured packet holds a null name, and the one shared name is in a packet built to fail (§2.7). Unknown for packets other than the 122 measured. |
| conformance fixtures and implementation tests | The corpus rebuilds under the new identifiers, and no packet changes verdict. `dup_pk` draws the new check beside its key check, which its expectation admits. Added packets and documents are listed below the table. `amended_curation`, `amended_preference`, `null_unit_labels` and `null_unit_labels_swapped` stay passing, and serve as the evidence that a name tells apart units the pair does not. |
| revision lifecycle, ledger, evidence and tooling | The ordinary ledger and evidence records for the new clauses. The entries for R81 §2.5, R85 §2.2, R123 §3.1 and R148 §3.1 stay `applied` and each gains a note, and the entry for R152 §3.4 follows §4. The specification tree's checker and the fact generator follow the three identifiers (§2.13). No revision tool changes. |
| generated publications and developer documentation | The combined specification, the registry's generated table documentation and Part 08's example regenerate, and the specification README's identifier table follows the version. The validator's README and design document and the registry source's guide name the generated kinds and their counts (§2.14). The writer's design document describes how its adapter names a unit and needs no change unless question 5 fixes a composition. |

**Compatibility.** The change only narrows what a packet may hold: tables that meet the new
declarations, with every name present, also meet the present ones. A reader written for a
nullable name reads a `required` one without change. The presence binds only a packet that binds the new registries. The uniqueness
check reports a defect Part 02 §8.2 already forbids, so it withdraws no permission. Where a
validator holds an earlier descriptor it reaches a packet bound to an earlier registry (§4), and a
packet that passed there while holding a shared name then fails. A registry valid under the present
contract is valid under the new one once it names the new `$id`, unless it declares a name of an
owned assigned identifier that is not `required`.

**Affected sections.** The change amends Part 02 §1, Part 02 §8.2, Part 02 §9.2, Part 02 §9.4,
Part 02 §10.1, Part 02 §12.1, Part 02 §12.9 and Part 05 §5.1. Each carries a canonical anchor at
the baseline: `ew-core-logical-schema-scope`, `ew-identifier-semantics`,
`ew-registry-self-description`, `ew-registry-conformance`, `ew-tier-1-rules`, `ew-unit-identity`,
`ew-interval-identity` and `ew-tier-1-validation`. None lacks one, so a draft needs no bootstrap
commit. Part 02 §6, which defines the three presences, has no anchor and is not amended.

**Conformance evidence.** What tells a conforming implementation or packet from one that is not:

- the core registry, with 17 `required` names, is valid under the new descriptor;
- a core-class and an extension-class registry document that each declare a nullable name for an
  owned assigned identifier are invalid under it, at the invariant question 9 fixes;
- a registry document naming the 0.11.0 `$id` is `unsupported` to a checker that holds only the new
  meta-schema and descriptor;
- a packet with a null name in a table that owns an assigned identifier draws that column's
  generated non-null check at `error`;
- a packet with two rows of such a table that carry one name and different keys draws the new
  check and no key check, which no existing packet isolates, since `dup_pk` draws both;
- the same defect in an extension's table gives a finding that belongs to the extension, a `failed`
  verdict for it and `passed` for core, as Part 05 §9.5 composes them;
- the four fixtures of §2.5 pass, holding units that share the pair and differ in name; and
- every packet the corpus expects to pass still passes.

The corpus holds no row of four of the 18 tables (§2.7), so whether each takes a packet of its own
is for a draft to say. No tool checks that a migrated extension registry changed its version, and
no check sees two things merged under one name (§4).

## 6. Open questions

1. Which relation Part 02 §12.1 names for a unit, and what the sentence covers.
   **Answered 2026-10-02: `unit_name`.** The options are
   `unit_name` (preferred direction); the triple
   `(sorting_run_name, curation_name, local_unit_label)`; stating the relation once in
   Part 02 §8.2 for every owned assigned identifier; striking the positive sentence; and keeping
   the pair. Of the three candidate relations `unit_name` is the only one shared by no two units
   of any measured packet and null in none (§4). A file the sorter wrote holds the label and no
   name. Under the preferred direction the sentence therefore covers what holds a name, which is
   another packet, a recipe and a later build, and Part 02 §12.1's first paragraph stays the
   statement of what the label records. The answers to questions 3 and 4 make the name `required`
   and checked whichever relation is named, so this question now decides the sentence alone. They
   also make the general statement in Part 02 §8.2 true of every row. It differs from the
   preferred direction in extending a consumer-facing sentence to 15 other identifiers (§4). The
   triple withdraws the permission of R149 §3.1 and fails two passing fixtures, and keeping the
   pair leaves a sentence that four passing packets contradict. Questions 2, 6 and 7 depend on
   this one.
2. Which form Part 02 §12.9's interval sentence takes. **Answered 2026-10-02: it names
   `interval_name`.** The options are to name `interval_name`
   (preferred direction); to keep the triple with `session_name` in place of `session_id`; and to
   keep the triple as it is. Naming `interval_name` gives the two sections one form, covers an
   interval whose label is null, and changes no declaration, since the name is already `required`.
   Under the answer to question 4 a generated check covers that name. The triple on `session_name`
   removes the assigned number, keeps a relation an existing rule checks and a file outside the
   packet can state, leaves an interval with a null label without a relation, and leaves the two
   sections in different forms. It relies on a name the answer to question 3 makes `required`.
   Keeping the triple as it is leaves the assigned `session_id` in the relation. No packet changes
   verdict under any of the three.
3. Which names become `required`, and where the requirement is stated. **Answered 2026-10-02: the
   structural form.** The name of every owned assigned identifier is `required`, stated once in
   Part 02 §8.2 and checked by the registry-document contract. The options set aside were
   `unit_name` alone, and the nine nullable core names each in its own declaration. The nine core
   names change as a consequence. The contract takes a new descriptor and a new meta-schema `$id`
   (§2.13). An extension registry that declares a nullable name for an owned assigned identifier is
   invalid once it migrates, as one of the four in the repository would be for one column. A packet
   holding a null name fails once it binds the new registry, and no measured packet holds one. The
   answer raises question 9 and widens question 8.
4. How far a check reports a name two rows share, and what generates it. **Answered 2026-10-02: the
   structural form.** A validator generates a check for the name of every owned assigned
   identifier. Part 02 §10.1 states it as it states the check for a column declaring
   `finite: true`, and Part 05 §5.1 lists it. The options set aside were no check; a declared rule
   on `core.units` and one on `core.intervals`; and a declared rule on each of the 17 tables. No
   registry declares a rule, the check reaches an extension's table through Part 05 §5.4, and every
   validator generates one more kind (§2.14). Part 02 §8.2's sentence that no rule can check
   uniqueness is replaced as §4 describes. `dup_pk` is the one measured packet that draws the
   check, and it keeps its verdict. The answer raises questions 10 and 11.
5. Whether the specification says what a unit's name is composed from. **Answered 2026-10-02: it
   does not.** The options are to leave it
   to whatever composes the name, as R85 §2.2 does (preferred direction); to state that a unit's
   name distinguishes its run, its curation and the unit, without fixing a spelling; and to fix a
   spelling. Leaving it open keeps the name opaque and makes agreement between two packets a
   property of the recipe that built them (§2.8), so nothing makes two independently written
   writers agree on a name. A fixed spelling makes them agree and invites a consumer to parse the
   name. It also changes the name of every unit a writer spelled otherwise, and by inference from
   Part 05 §4.3 an amending build that composes the new spelling matches no unit such a packet
   holds. The generated check reports a composer whose names collide in two rows and none whose
   names merge two units into one row (§4), so under the preferred direction the merge stays the
   composer's obligation alone.
6. Whether the `units` term of Part 12 §4 states a unit's run and curation. **Answered 2026-10-02: the
   term stays as it is.** The options are to
   leave the term as it is (preferred direction), and to have each record carry the names of the
   unit's run and curation beside its label. The second widens the change to the adapter interface
   and to three adapters. The first leaves a build unable to tell two curations of one run apart
   when a later source names a unit by its label (§2.9), which is a defect of the same kind in
   another part and wants a proposal of its own. The answers to questions 3 and 4 do not touch the
   term.
7. Whether the positive sentence carries a keyword. **Answered 2026-10-02: the indicative in both
   sections, with the prohibition kept for a unit.** The options are the indicative in both
   sections, with the keyworded prohibition kept for a unit as it is (preferred direction); a
   keyworded duty in both, stated as unchecked; and either of those with the prohibition added for
   `interval_id`, which Part 02 §12.9 lacks. No tool can check what a consumer does outside a
   packet, and a prohibition for an interval is a new duty on a consumer. Under the answers to
   questions 3 and 4 the checked requirements sit on the name itself, in Part 02 §8.2, so the
   sentence for a consumer adds nothing a tool could check. No packet is affected under any option.
8. How the clause states the three advances. **Answered 2026-10-02: two named targets and one
   minor step for the core version.** The options are to name the targets of the
   meta-schema `$id` and the descriptor ID, 0.12.0 and v0.10, and to advance the core
   `registry_version` by one minor version from the one the registry carries at incorporation,
   naming no target (preferred direction); to name all three targets; and to name none. R145 §3.5
   and R152 §3.4 each named all three. Three other pieces of open work advance the core version and
   none advances the other two (§2.12), so a named core target holds only for whichever is
   incorporated first, while the other two targets hold in any order. Leaving any of the three as
   it is is not an option under the answer to question 3: Part 02 §9.2 forbids reusing an
   identifier for an incompatible contract, and one core version would identify two registries
   that declare nine columns differently. Under each option the clause says, as R152 §3.4 did, that
   a migrated extension registry carries a different version and that no checker verifies it. A
   packet built afterwards binds the new identifiers, and an earlier packet keeps the ones it
   binds.
9. Under which invariant the contract reports a name that is not `required`. **Answered 2026-10-02:
   `registry.identity.name`.** The options are to
   have `registry.identity.name` report it (preferred direction), and to add an invariant. The
   first keeps one invariant for the one statement of Part 02 §8.2, which already reports the
   name's type, role and `identity` together. The new descriptor then differs from v0.9 in its ID
   and the meta-schema it selects, and holds 29 invariants. The second tells a consumer of a
   registry result which requirement failed, takes the same two anchors and a position in the
   descriptor, adds a row to the table of Part 02 §9.4, and makes 30. R145 §3.5 and R152 §3.3 each
   added an invariant for a new requirement, and no accepted clause that was read widens one. Both
   options need the new descriptor and `$id`, and a registry is valid under one exactly where it
   is valid under the other.
10. What the generated check reports, at which level, under which ID, and for which packets.
    **Answered 2026-10-02: the five parts of the preferred direction.** The
    preferred direction has five parts. The check reports each row whose name another row of the
    same table holds. It does not count a null name, which the non-null check reports where the
    name is `required`. Its level is `error`. Its ID has the form of the `finite` check's,
    `<declaration_id>.<column>.unique`. A validator generates it wherever a valid registry context
    directs packet checks, whichever contract that registry was checked under. The options that
    differ are to report at `warning` for a registry checked under an earlier contract, and to
    generate the check only under the new contract. Under the preferred direction a validator that
    holds an earlier descriptor reports at `error` a packet that passed before while holding a
    shared name, which Part 02 §8.2 already forbade. Of the 122 measured packets only `dup_pk`,
    which is built to fail, holds one.
    The validator in the tree holds one descriptor, so under every option it reports a packet bound
    to an earlier registry `incomplete` (§2.13).
11. Over which rows a name is unique where its table's key has several columns. **Answered
    2026-10-02: the whole table, on the name alone.** The options are the
    whole table, on the name alone, as Part 02 §8.2 states the requirement (preferred direction);
    and the rows that share the key's other members. The first changes no requirement. It matches
    Part 05 §4.3, which assigns identifiers packet-wide, and Part 01 §2.1, which pairs a name with
    an identifier so that a process outside the packet needs no number the packet assigned. It
    gives the check one shape for every table. Under it a packet of two sessions that names a
    block of each `block_01` draws the check (§2.7), and whatever composes those names distinguishes the sessions. The second
    relaxes Part 02 §8.2 for such a table, makes a name identify a row only together with the
    key's other members, one of which is an assigned number in the measured case, and gives the
    check a shape that depends on the key. No core table is affected under either, and no measured
    packet holds two sessions.

Every question is answered: 3 and 4 as the structural form, and each of the other nine as its
preferred direction.

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
- [x] The proposal has explicit approval to advance to a revision draft.

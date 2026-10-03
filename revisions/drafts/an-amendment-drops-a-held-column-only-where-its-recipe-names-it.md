# An amendment drops a held column only where its recipe names it

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `18d05c61eb7eeaea900659ffdf34f5e57d568525` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §6, by a new subsection at its end; Part 05 §§3.1, 3.5, 4.3, 5.3 and 15.2; the recipe schema |
| **Depends on** | R150 §3.3 (the change table this reads); R150 §3.4 (the comparison over declared columns this keeps); R150 §3.5 (the amending build's refusals this extends); R150 §3.6 (the unwritten table this makes an exception to); R125 §3.10 (a shim check's declared inputs); R162 §3.6 (the recipe schema identifier this advances from) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

An amending build binds each registry its recipe names (Part 05 §15.1), and that registry may be a
later version that no longer declares a column a held table's file holds. Nothing then accounts for
the column's values. Where the amendment writes the table, it writes the rows without the column,
and Part 05 §15.6 compares rows over the columns the amended manifest's registry declares, so no
finding names the loss. Where the amendment does not write the table, the held file keeps a column
that no registry the packet binds types, describes or checks, and no part says whether that file
conforms.

This revision makes a table that holds an undeclared column non-conforming, and has a validator
report each such column. It has an amending build refuse, before it opens any source, where a
table the packet holds has a column the registry the build binds does not declare, unless the
recipe derives that table again. It gives a recipe a `[drop]` entry that releases the refusal and
drops the column, even from a table the amendment would otherwise leave alone. It says which entries a build refuses and what it reports, settles that removing an
undeclared column changes no row, and advances the recipe schema's identifier.

The change is structural because it revises rules inside existing sections: the refusals and
reports of an amending build in Part 05 §3.5, the sentence of Part 05 §4.3 under which a table
gaining no row is not written, the shim checks of Part 05 §5.3, the change table of Part 05 §15.2,
and the member table and schema identifier of Part 05 §3.1. Appended sections would leave
Part 05 §4.3 saying such a table keeps its entry beside a later section that has the build write
it, and would split an amending build's refusals between two places.

A column a later registry adds is out of scope: §2.4 shows the build already refuses where a held
file lacks one.

### 1.1 Structural crosswalk

Part 02 §6 had no canonical anchor, so the `Based on` commit is an anchor bootstrap that inserts
`ew-column-presence` before its heading and changes nothing else. At that commit Part 05 §§3.1,
3.5, 4.3, 5.3 and 15.2 carry `ew-recipe-purpose`, `ew-recipe-check`, `ew-import-normalization`,
`ew-validation-shim` and `ew-amendment-scope` in that order. The new subsection is created at the
end of Part 02 §6 with the anchor `ew-undeclared-columns`. No section moves, splits, merges or
retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §6, which states which declared columns a table holds | extend by a new subsection at its end | a new subsection at the end of Part 02 §6 | a table holds no column its declaration does not declare | §3.1 |
| Part 05 §5.3, the shim's check of resource-owned metadata | extend in place | same section | the three checks of a file's columns against its declaration are named, at `error`, with their inputs | §3.2 |
| Part 05 §3.5, the amending build's refusals before it opens a source | extend in place | same section | a held undeclared column is refused unless the recipe derives its table again or a `[drop]` entry names it; an entry that names a declared column, a table the recipe derives again or no held table is refused | §3.3; §3.5 |
| Part 05 §3.5, beside the amending build's admission of a column override | extend in place | same section | a `[drop]` entry is defined, releases the refusal, and draws a warning when idle and information when it drops | §3.4; §3.6 |
| Part 05 §4.3, a table to which an amending build adds no row is not written | revise in place | same section | a table holding a column a `[drop]` entry names is written without it | §3.4 |
| Part 05 §15.2, the change table | extend in place | same section | removing an undeclared column changes no row; the re-derivation duty holds for such a rewrite | §3.7 |
| Part 05 §3.1, what a recipe declares, the member table and the schema identifier | revise and extend in place | same section | a recipe declares the held columns an amendment drops; `drop` is a member; the identifier advances | §3.8 |

## 2. Background

The facts below were observed in the tracked files at the `Based on` commit, which adds only the
anchor of §1.1 to its parent. The commit holding this draft regenerates the projections that anchor
changes, and there `verify.py --quick` passes all 38 of its stages. The probes of §§2.2 and 2.4 ran
at `deb048c5`. Between that commit and the baseline the reader and writer sources, the validator's
column checks, the core registry and the artifacts are unchanged, Part 02 has gained only that
anchor, and Part 05 has changed only in §9.4.
None of the probes changed a tracked file.

### 2.1 A rewritten table loses the values, and nothing reports it

The writer suite holds a test of this case, which R163 §5 names:
`test_an_amendment_binding_a_registry_without_a_held_column_rewrites_its_rows_without_it`. It builds
a packet under a copy of the core registry at version `0.0.1` whose `core.source_files` declares one
more `optional` `json_string` column, holding `{"slope":2.0,"offset":5.0}` in the packet's one row,
then amends the packet under the baseline registry, adding a second `core.source_files` row. Run at
the baseline it passes (1 test, 4.2 s), asserting that:

- the amendment's validation passes;
- the rewritten `core.source_files` file holds no such column, and both rows' `uri` values; and
- the superseded file still holds the value.

The test asserts the reference build's present behaviour so that a change to it is seen, not that
the behaviour is wanted.

### 2.2 A table left alone keeps a column its bound registry does not declare

A probe built the same packet under the same `0.0.1` copy, then amended it under the baseline
registry adding only a `core.processing_runs` row. The reference validator ran with checksums and
advisory checks:

| | findings | naming the column |
|---|---|---|
| before the amendment | 6 `info` | 0 |
| after the amendment | 7 `info` | 0 |

The amendment passed. `core.source_files` kept its resource entry and its file, which holds eight
columns, the added one among them, and the amended manifest binds core `0.18.0`, which does not
declare it. R163 §2.5 reports the same for `core.clocks.transform_to_parent`.

### 2.3 Registry changes have removed 63 columns from tables that remain

The committed core registry was read at each of its 104 versions in the repository's history, each
version's file located through its renames, and each version's set of declared `resource.column`
pairs compared with the one before. Fifteen commits removed at least one pair, 76 in all, a rename
counting as a removal, since a held file's column then has no declaration either.

Thirteen of the 76 went with one table when R54 renamed `core.trials` to `core.intervals`. A held
file whose entry names a declaration no bound registry carries already fails under
`packet.resource.declaration_unknown` (Part 04 §10), so a removed table is outside this revision.
The other 63 were removed from tables that remain, by 14 commits. The eight latest:

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

None of the eight changed `logical_standard_version` or `semantic_standard_version`, so the refusal
of Part 05 §3.5 of a registry of another standard version would have refused none of them. Twelve of
the 15 commits, every one before R128, left the registry's version at `0.1.0`, which did not then
advance with each change. The extension registries were not counted. Removing a column is an
ordinary change to a registry, not a rare one.

### 2.4 A registry that adds a column already fails loudly

A probe built a packet under a copy of the baseline core registry without the `nullable` column
`core.source_files.format`, then amended it under the baseline registry.

| amendment | outcome |
|---|---|
| adds only a `core.processing_runs` row | refused, with one `error`: `schema.column_absent` on `core.source_files.format` |
| adds a `core.source_files` row | passes; the rewritten file holds `format`, null in both rows |

Ten of the 14 commits of §2.3 also added a column not declared `optional` to a table that remains,
and 29 commits in all added or retyped one. A recipe that names no core registry binds the
packet's own (Part 05 §15.1), which declares the file's columns as they are, and that remedy serves
both directions.

### 2.5 No part makes an undeclared column non-conforming

A search of the numbered parts found no rule on a column a table's file holds and its declaration
does not declare:

- Part 02 §6 says which declared columns are present, and nothing of an undeclared one;
- Part 03 §5.1 makes a table one Parquet file and says nothing of its columns;
- Part 05 §5.3 has the shim check Parquet types, which reach declared columns;
- Part 11 §3 exposes to a rule each table's registry-declared columns and no others; and
- Part 12 §5 says what a delivered column's absence means, and nothing of an undeclared one.

The reference validator checks each declared column's presence and type under `schema.column_absent`
and `schema.column_type`, which no part names and the conformance corpus expects at `error`, and
checks no other column. The reference build refuses a delivered record holding a column no loaded
registry declares, and three writer tests assert it, but no part requires that refusal (R163 §2.5).
An amendment never delivers the held rows, so that refusal does not reach them.

### 2.6 Part 05 §15.2 reads two ways

Part 05 §15.2 forbids an amendment to "change or remove any other row of a canonical table". A held
row rewritten without one column's values is changed under one reading and not under the other.
Part 05 §15.6 takes the second, comparing only declared columns, so the current text does not
answer the question.

### 2.7 No corpus or measured packet carries an undeclared column

A scan compared each table file's column names with the declarations of the registries its packet
binds.

| population | packets | table files | with an undeclared column |
|---|---|---|---|
| the conformance corpus, rebuilt at the baseline | 135 | 4078 | 0 |
| packets built from two recorded sessions, each with a packet at core `0.18.0`, scanned on 2026-10-02 | 27 | 1083 | 0 |

No corpus fixture exercises an undeclared column. The probe packets of §2.2 and R163 §2.5 carry one
on purpose.

### 2.8 The release entry and its schema

A recipe's `[overrides]` keys a column override `resource.column` (Part 05 §3.6), and `[encoding]`
keys its entries the same way (Part 05 §3.8). Part 05 §3.5 refuses a column override whose column
the resource does not declare, and here the column is undeclared by definition. A JSON Schema engine
was run over the baseline recipe schema with a `drop` member added, whose keys match the three-
segment alternative of the `overrides` key pattern and whose values match `\S`, and with
`dependentSchemas` requiring `packet.amends` where `drop` is present. It admitted an amending recipe
carrying a `drop` entry and a recipe with neither member, and refused a non-amending recipe carrying
`drop` ("'amends' is a required property"), a two-segment key and a blank reason.

An amending build reads every held row before it settles delivered rows against them (Part 05
§4.3), and held files are part of the packet, not a source, so it can read a held table's column
names before it opens any source. Each `[[materialize]]` entry names the resource it derives
(Part 05 §3.1), so the build also knows before any source which held tables it derives again.

### 2.9 Alternatives

| alternative | why it is not taken |
|---|---|
| keep the current rule | a rewritten table loses the values silently and a table left alone keeps data no bound registry describes (§§2.1 and 2.2) |
| refuse outright, with no release | the packet stays amendable only under its own registry (§2.4), never under a later one that removed a column, though removal is ordinary (§2.3) |
| carry the column forward on a rewrite | the packet then holds a column no registry it binds types, describes or checks, which is the second half of the problem |
| report the loss and refuse nothing | the report follows the loss and leaves the packet conforming with the column; Part 05 §3.4 refuses a smaller discard unless the recipe names the column |
| release by a column override | Part 05 §3.5 refuses a column override for an undeclared column, and an override's meaning, giving up a passed-over source's value, is another |
| a registry records the columns it removed | needs a meta-schema change, and gives consent to the registry's author, who cannot judge one packet's values, where a per-packet remedy exists (§2.4) |
| the build refuses only over a canonical table | a non-canonical table left holding the column then fails only at validation, after every source has run; the reviewer chose an early refusal over every held table, since failing after the build has written is expensive |
| the build refuses over a table it derives again | a `[[materialize]]` entry replaces the held file whole, so no column is carried and the recipe would need an entry for nothing |
| the validator reports an undeclared column at `warning` | the file stays conforming, so a build that writes undeclared columns, which nothing else forbids, also conforms; the column has no type or description in the packet and no rule can read it (Part 11 §3); no measured packet holds one (§2.7) |
| the rule lives in Part 03 §5.1 | a fact about a table's logical columns becomes a property of one physical profile |

### 2.10 Other open work

One other draft is open; it changes the revision process and amends no part. R165, accepted and incorporated at the baseline, amended Part 11 §§1, 4
and 8 and Part 05 §9.4, none of which is amended here. Two proposals are open. One,
on what a null identifier says, also adds a subsection to Part 02 §6; this revision is ordered first,
so that subsection follows this one's. The other, on a frame's `pts` and `dropped` flag, touches Part 01
§3.18 and core declarations only.

The reference build passes only the resources it wrote as the set a validator re-checks
(`escapewheel-writer/src/escapewheel_writer/publication.py`, line 233), so a rule a newer registry
adds to a table the amendment leaves alone does not run during the amendment. That breaks the
over-inclusive test of Part 05 §15.4 whatever this revision decides, and is an implementation defect
outside it.

No part states which Parquet type represents each declared type, apart from Part 03 §5.5's
timestamp; §3.2 names `schema.column_type` by the declared type it compares with, as the reference
validator does.

`revisions/impact.py` lists 314 citations of Part 02 §6 and Part 05 §§3.1, 3.5, 4.3, 5.3 and 15.2
outside this document. Those that concern a held or undeclared column lie in the reference build,
the reference validator's shim and their tests, which §5 has change, and in the records under
`revisions/audit/`, which describe the parts as an audit found them.

## 3. Decision

The subsections state the rule a table's columns obey, the validator's report of it, an amending
build's refusal, the `[drop]` entry that releases it, the entry's refusals and reports, the row an
amendment leaves unchanged, and the recipe schema.

### 3.1 A table holds no column its declaration does not declare

A table MUST NOT hold a column that its declaration does not declare. Its declaration is the one its
resource entry's `declaration_id` names in a registry the packet's manifest binds (Part 04 §10). A
column is undeclared whatever its values, every value null included, and whatever wrote it.

### 3.2 A validator reports each file column against its table's declaration

For each table resource the current manifest names whose file's columns it reads, a validator MUST
report at `error`, naming the resource and the column:

- under the check ID `schema.column_absent`, a `required` or `nullable` column the file does not
  hold;
- under the check ID `schema.column_type`, a declared column the file holds at a type other than its
  declared type; and
- under the check ID `schema.column_undeclared`, a column the file holds that the resource's
  declaration does not declare (§3.1).

This revision does not fix which Parquet type represents each declared type (§2.10); the reference
validator compares a column with the Arrow type it maps the declared type to.

Each finding concerns one resource, so Part 05 §9.5 attributes it to the registry whose declaration
the resource's entry names. The shim declares as the inputs of each check the packet manifest,
which binds the registry holding the declaration, and the table resource, so Part 05 §15.4 re-runs
each check on every amendment. A file that only a superseded manifest names is not checked again.

### 3.3 An amending build refuses a held column no bound registry declares

An amending build (Part 05 §15.1) MUST refuse, before it opens any source and naming the table and
the column, a table resource the packet's current manifest names whose file holds a column that the
table's declaration, in the registry the build binds for it, does not declare, unless:

- a `[drop]` entry names that column (§3.4); or
- a `[[materialize]]` entry of the recipe names that resource, so that the build derives the table
  again rather than carrying its held rows.

A `[drop]` entry resolves the refusal in every case. Where the registry the packet's current
manifest binds under the registry ID of the table's declaration declares the column, a recipe also
resolves it by naming no registry under that ID, so that the build binds that registry
(Part 05 §15.1).

### 3.4 A `[drop]` entry releases the refusal and drops the column

A recipe's top-level `[drop]` table names held columns an amending build drops. An entry's key is a
resource's dotted identifier followed by a column name, spelled as a column override's key
(Part 05 §3.6), and its value is a non-empty string saying why the recipe gives up the column's
values. A recipe carrying `[drop]` MUST give `[packet].amends`.

Where a `[drop]` entry names a column that the file of the resource the packet's current manifest
names holds, an amending build MUST NOT refuse under §3.3 over that column, and MUST write the table
without it, whether or not the build adds a row to the table. The written table holds every held row
with its other columns' values unchanged, and the rows the build adds.

A table to which an amending build adds no row and from which it drops no column keeps its resource
entry, so the amendment does not write it.

### 3.5 A build refuses a `[drop]` entry that names a declared column or no held table

An amending build MUST refuse, before it opens any source and naming the entry's key, a `[drop]`
entry:

- whose resource the packet's current manifest does not name;
- whose resource a `[[materialize]]` entry of the recipe also names; or
- whose column the resource's declaration, in the registry the build binds, declares.

### 3.6 A build reports each dropped column and each idle entry

A `[drop]` entry is **idle** where the packet's current manifest names no file of its resource that
holds its column. An amending build MUST report an idle entry as a warning and MUST NOT refuse on it.

An amending build MUST report as information each column it drops, naming the table, the column and
the entry's reason.

A refusal under §3.3 MUST name a `[drop]` entry as a remedy, and MUST name binding the registry the
packet's current manifest binds only where that registry declares the column.

No checker verifies these reports.

### 3.7 Removing an undeclared column changes no row

A row of a canonical table is compared over the columns its declaration declares in the registry
the amended manifest binds, as Part 05 §15.6 compares rows, so an amendment that removes a column
that declaration does not declare changes no row.

An amendment that writes a canonical table only to remove such a column writes that table, and the
duty of Part 05 §15.2 to derive again, or remove, every analysis and compatibility-projection
resource whose `derived_from` chain reaches it holds as for any other written table.

### 3.8 The recipe schema admits `drop` and its identifier advances

The recipe schema admits a top-level `drop` member: a table whose keys are a resource identifier and
a column name joined by a dot, each spelled as the registry meta-schema spells it, and whose values
are strings holding a character that is not white space. The schema requires `packet.amends`
wherever `drop` is present.

The schema's `$id` advances one minor version from the identifier Part 05 §3.1 incorporates when
this revision is incorporated. At the baseline that identifier is
`https://escapewheel.org/schemas/recipe/0.4.0`. Part 05 §3.1 names the new identifier; its list of
what a recipe declares gains, where it amends a packet, the held columns the amendment drops; and its
informative table lists `drop`.

## 4. What this does not change

Part 05 §15.6 is unchanged. A table's rows are still compared over the columns the amended
manifest's registry declares, so a rewrite that drops a released column draws no
`amendment.row_changed`, and one that drops a column without a release cannot happen, since §3.3
refuses it.

Part 05 §15.5 is unchanged. The superseded file keeps the dropped values until cleanup removes it,
and a `[drop]` entry does not hasten cleanup. Part 03 §9 already has every resource an amendment
writes written as a new file, so a table written without a column needs no profile rule.

A column a later registry adds is not released or refused here; the validator's
`schema.column_absent` reports a held file lacking it, and §2.4's remedy applies.

## 5. Consequence

The revised recipe schema admits every recipe the baseline schema admits, with unchanged meaning,
and also admits `drop` in an amending recipe. A build written to the baseline schema refuses a
recipe carrying `drop`, naming the member. No corpus or session packet changes verdict (§2.7), and
none is rebuilt.

A packet that holds an undeclared column now fails under `schema.column_undeclared`, whatever wrote
it. Two kinds of packet the baseline admits are affected. A packet amended by the reference build
since R163, from a version holding `core.clocks.transform_to_parent`, without writing `core.clocks`,
holds that column; no measured packet does. A writer that stores a data frame's index as a Parquet
column writes a column no declaration declares; the reference writer does not.

An amending build that binds a registry which removed a column from a table the packet holds now
refuses before any source, unless its recipe derives that table again. The recipe proceeds by
dropping the column or, where the packet's own registry still declares it, by binding that
registry. A packet amended since R163 from a version holding `core.clocks.transform_to_parent`
binds core `0.18.0`, which does not declare that column, so only a `[drop]` entry lets it be amended.

A drop rewrites its table as a new file, so Part 05 §15.2 requires every analysis or
compatibility-projection resource whose `derived_from` chain reaches that table to be derived again
or removed (§3.7). Dropping `core.clocks.transform_to_parent` rewrites `core.clocks`, so the
amendment carries the cost of re-deriving every held resource that reaches it.

The refusal of §3.3 and those of §3.5 are decided from the recipe, the registries the build binds
and the held files' column names, which the build reads before it opens any source (§2.8).

No accepted clause is superseded whole and no destination moves, so no existing ledger entry
changes. R150 §3.3, whose change table §3.7 reads, R150 §3.6, whose unwritten table §3.4 excepts
where a column is dropped, and R162 §3.6, whose recipe identifier §3.8 replaces, are each replaced
only in part and keep `applied` at their anchors.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. No concept of Part 01 changes. | None required. |
| logical prose and registry | A new subsection at the end of Part 02 §6 takes §3.1. The meta-schema, declarations and rules are unchanged. | `evidence/R<N>.json` names `ew-undeclared-columns`. |
| physical profiles | Unchanged. Part 03 §9 already writes a rewritten table as a new file, and the rule is logical (§2.9). | None required. |
| packet manifest and JSON Schemas | The recipe schema gains `drop`, requires `packet.amends` beside it, and advances its `$id` (§3.8). The manifest schema is unchanged. | The schema artifact; schema tests admitting an amending recipe with `drop` and refusing a non-amending one, a two-segment key and a blank reason. |
| validation and import | Part 05 §3.1 takes §3.8; Part 05 §3.5 takes §§3.3, 3.4, 3.5 and 3.6; Part 05 §4.3 takes §3.4; Part 05 §5.3 takes §3.2; Part 05 §15.2 takes §3.7. | `evidence/R<N>.json` names the five anchors. |
| extensions | Unchanged. §§3.1 to 3.6 reach an extension table as a core one, and no extension declaration changes. | None required. |
| reader, writer, validator, adapters | The reference build refuses a held undeclared column of a table it does not derive again, naming the remedies that apply, honours `[drop]`, writes a table it adds no row to where it drops a column, refuses the three entries of §3.5, and reports a drop and an idle entry; its packaged recipe schema regenerates. The reference validator adds `schema.column_undeclared` and declares the manifest an input of the three column checks. Readers and adapters are unchanged. | The writer and validator suites' cases of §6; the copies check of `verify.py`. |
| conformance fixtures and tests | A corpus fixture whose table holds an undeclared column, expected at `error` under `schema.column_undeclared`. The writer test of §2.1 asserts the refusal instead of the loss. | The corpus test; the writer suite. |
| revision process and tooling | A ledger entry for each Decision clause and the ordinary evidence record; no existing entry changes. No tool changes. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification regenerates. The writer's guide documents `[drop]` in its account of an amending recipe. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at the new subsection at the end of Part 02 §6, §3.2 at Part 05 §5.3, §§3.3, 3.5 and 3.6 at Part 05 §3.5, §3.4
at Part 05 §3.5 and Part 05 §4.3, §3.7 at Part 05 §15.2, and §3.8 at Part 05 §3.1, each by
canonical anchor.

These validator cases distinguish §§3.1 and 3.2:

- a packet whose `core.source_files` file holds a column core does not declare fails with one
  `error` under `schema.column_undeclared`, attributed to core, and the same column added to an
  extension table is attributed to that extension;
- the corpus's `missing_column` and `bad_type` packets keep their findings; and
- the packet of §2.2, after its amendment, fails under `schema.column_undeclared` though the
  amendment did not write `core.source_files`.

These build cases distinguish §§3.3 to 3.7:

- the amendment of §2.1 is refused, naming `core.source_files` and the column, before any source
  opens;
- with a `[drop]` entry for the column it builds, the written file lacks the column, the superseded
  file keeps it, and the build reports the drop with its reason;
- the amendment of §2.2 with that entry writes `core.source_files` as a new file without the column,
  though it adds no row to it;
- the same amendment naming no core registry binds the packet's own and builds without an entry;
- an amendment of a packet whose own registry also lacks the column is refused naming only the
  `[drop]` remedy;
- an entry for a column the held file does not hold is reported as a warning and the build
  proceeds;
- an entry naming a resource the packet does not hold, a resource a `[[materialize]]` entry names,
  or a declared column is refused before any source opens, naming the key;
- an amendment that leaves a held analysis table holding an undeclared column is refused before any
  source opens; with a `[drop]` entry it writes that table without the column, and with a
  `[[materialize]]` entry deriving the table again it builds without one; and
- an amendment that only drops a column of a canonical table that a held analysis resource derives
  from draws `amendment.derived_resource_stale` unless it derives that resource again or removes it.

These schema cases distinguish §3.8: the schema admits an amending recipe whose `drop` holds
`core.source_files.extra`, and refuses `drop` in a recipe without `packet.amends`, a key of two
segments and a reason of white space.

The probes of §2 establish feasibility: the reference build already reads held rows before it
settles delivered ones, the validator already reads each table file's column names, and a JSON
Schema engine expresses the `drop` member and its dependence on `packet.amends` (§2.8).

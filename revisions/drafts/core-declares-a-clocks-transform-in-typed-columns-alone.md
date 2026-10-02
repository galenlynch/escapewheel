# Core declares a clock's transform in typed columns alone

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `cf9e816a13575a419d6917d8285992d7cb09f2f3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§5.2 and 9.2; Part 08 §§2 and 3; the core registry |
| **Depends on** | R3 §3.4 (the replacement of the column this removes); R152 §3.4 (the core registry version at the baseline) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3 |

Section 3 is normative. Sections 1, 2, 4, 5, 6 and 7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

`core.clocks` holds one row for each clock of a session. It states a clock's linear alignment to
its parent clock in two typed columns, `transform_slope` and `transform_offset`. It also declares a
third column on the same subject: `transform_to_parent`, an optional `json_string` described as
"Clock alignment transform."

R3 §3.4 replaced `transform_to_parent` with the two typed columns. The registry gained the typed
columns and kept the column they replaced. No part says what that column holds, no rule reads it,
and no declared rule could read it. A writer can therefore state an alignment in JSON beside the
typed columns, and nothing compares the two.

This revision removes the declaration and advances the core registry's version. It also restates
one sentence of Part 02 §5.2, which counts two `json_string` columns in core where the registry
declares such columns under four names, and under three once this one is removed, and which names
only two of the sections that state such a column's content. It adds no check and changes no rule.

The change is structural because the two sentences it restates sit inside Part 02 §5.2 and
Part 02 §9.2. An appended section would leave the first miscounting and the second naming a version
the registry no longer carries.

R159 amends only sections of Part 05. Of the four other open drafts, three advance the same
`registry_version`. `core-declares-a-catalog-of-sidecars.md`, whose acceptance is authorized and
whose incorporation is under way, adds three declarations to the core registry and takes `0.15.0`
where it is incorporated first.
`a-null-producing-run-on-an-array-says-the-packet-names-none.md` rewords the description of
`processing_run_id` on the core tables that declare it nullable.
`a-unit-is-identified-outside-its-packet-by-its-name.md` makes the name of every owned assigned
identifier `required` and has a validator report a name two rows of a table share; it also advances
the registry meta-schema and the registry-contract descriptor. The fourth,
`a-recipe-accepts-a-discarded-value-by-naming-its-column.md`, changes no registry declaration.
None of the four changes a declaration of `core.clocks` or Part 02 §5.2, and §3.3 names no target
version, so this draft and those apply in any order.

### 1.1 Structural crosswalk

The `Based on` commit is a metadata-only bootstrap adding `ew-no-nested-types` before the heading
of Part 02 §5.2, and changes nothing else. The commit after it regenerated the heading index and
the combined rendering. Part 02 §9.2, Part 08 §2 and Part 08 §3 already carried canonical anchors.
No section moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| core registry, the columns of `core.clocks` | remove one column | same declaration | core declares no JSON transform for a clock, and a file column of that name is undeclared under the new version | §3.1 |
| Part 02 §5.2, the sentence on "the two `json_string` columns core declares" | revise in place | same section | the sentence names each section that states such a column's content, says which two columns no part describes, and counts no columns; no requirement changes | §3.2 |
| Part 02 §9.2, the core registry version | revise in place | same section | the version advances by one minor version | §3.3 |
| Part 08 §§2 and 3, the example packet's core registry version | revise the informative example in place | same sections | none | none |

## 2. Background

Each observation below was made on the tracked files at the baseline. The draft was first
appraised on the bootstrap `955c6d5043bd701816442784c8cd25a3142aa8f0`, and nothing incorporated
since changes the core registry, Part 02 §5.2 or Part 02 §9.2. At the baseline
`verify.py --quick` passes all 37 of its stages, and the registry check reports 45 tables, 360
columns, 116 references and 91 rules for the core registry.

### 2.1 R3 replaced the column and the registry kept it

R3 §3.4 is headed with the column's name and opens "Replaced by typed columns on `core.clocks`".
R3 §2.2's table of affected columns gives it the disposition "typed columns", where the rows for
`core.events.payload`, the two `parameters` columns and `metadata` each become `json_string`.

A search of `revisions/accepted/` for the name finds five lines in four records. Two are the R3
lines above. R13 §1 says that R3 §3.4 replaced the column with two typed columns, and R99 §2.2
that it converted the column to typed columns. R94 §2 counts it among the 25 optional columns the
registry declared when that revision was accepted. R99 §2.2 and R94 §2 are informative background.
No record keeps the column or gives it a meaning.

`spec/source/core/core.clocks.toml` declares 15 columns and 12 rules. `transform_to_parent` is the
twelfth column: type `json_string`, presence `optional`, role `data`. The tenth and eleventh are
`transform_slope` and `transform_offset`, each a nullable finite `float64`. The registry document
as first committed, in `8db71976aaf893ae9e6236e1641f3499ee2e5f86` on 2026-08-26, the day R3 was
accepted, already declares the column. The replacement therefore never reached the registry.

### 2.2 No rule reads the column and no declared rule could

Five of the twelve rules of `core.clocks` read `transform_slope`. None of the registry's 91 rules
names `transform_to_parent`, counted by searching each rule's SQL. Part 02 §10.2 forbids a rule to
reference a column whose presence is `optional`, and Part 02 §6 makes every `json_string` column
optional, so a rule on this column is not expressible.

Part 01 §3.9 has a clock declare "either a linear transform or anchor points, never both".
`core.clocks.one_alignment_model` checks that for `transform_slope` against `core.clock_anchors`.
Nothing checks a JSON transform against either.

### 2.3 No part says what the column holds, and Part 02 §5.2 miscounts

A search of the 13 files of `spec/parts/` for the column's name finds no line. Part 02 §5.2 says
that what may go in "the two `json_string` columns core declares" is stated by Part 02 §8.6 for
`metadata` and by Part 02 §12.6 for `core.processing_runs.parameters`.

That count disagrees with the registry. Reading every column of the generated registry finds 22
`json_string` columns, all optional and the only optional columns core declares, under four names:
`metadata` in 18 tables, `parameters` in `core.processing_runs` and `core.sorting_runs`,
`core.events.payload`, and `core.clocks.transform_to_parent`.

Part 02 §8.6 and Part 02 §12.6 are the only sections of Part 02 that state such a column's
content. Other parts place content in a run's `parameters` as well: Part 05 §3.2 the recipe,
Part 05 §4.3 the compensations stated to a writer, and Part 06 §5 a materialization's transform
parameters. Part 01 §3.11 permits an event a structured payload without saying what it holds, and
no part states what `core.sorting_runs.parameters` holds. The sentence has never listed any of
these.

Of the four names, only `transform_to_parent` covers a subject that typed declarations already
state. Part 02 §12.6 puts three alignment facts in columns because a consumer needs them to place a
tick, and Part 02 §8.6 says that "A fact required to interpret the data belongs in a column, never
in a key." Every alignment fact a part names has a typed home: the two transform columns,
`core.clock_anchors`, `core.clock_phase_steps`, `core.sessions.alignment_bound`, and
`withheld_first_anchor` and `withheld_last_anchor` on `core.clocks`.

### 2.4 Nothing in the tree reads or writes the column

A search of the 862 tracked files finds the name in 19.

| where | tracked files | lines naming the column |
|---|---:|---:|
| `spec/parts/` | 13 | 0 |
| the four packages, source and tests, with the two extension registries one of them holds | 360 | 0 |
| `extensions/`, the other two extension registries | 13 | 0 |
| `fixtures/` and `integration/` | 32 | 0 |
| `conformance/` | 59 | 1 |
| the registry source, the generated registry and the generated listing | 3 | 3 |

The one line under `conformance/` lists the columns R3 §2.2 names, in a sweep of the frozen v0.1
tables. The other 15 files are four accepted records, three frozen v0.1 documents, the ledger with
its note on R3 §3.4, this draft and the drafts README, and five working documents outside the
specification.

The built conformance corpus holds 120 packets and 3,629 Parquet files. Reading each file's schema
finds 119 `core.clocks` files and the column in none of them, nor in any other table.

No package source names the column, so no adapter in the tree delivers it. That is an inference
from the search and not a test. The session packets that R99 §2 measured are outside the tree and
were not inspected.

### 2.5 A column that no bound registry declares draws no finding

A probe copied the corpus's valid packet twice, each time adding a `transform_to_parent` string
column to the `core.clocks` file and restating that file's digest in the manifest. One copy bound
the baseline registry. The other bound a registry with the declaration removed and
`registry_version` set to `0.15.0`. The reference validator, verifying checksums, passed both with
no error and no warning. It reported for each the 18 `info` findings it reports for the unchanged
packet, none naming the column.

A search of the numbered parts found no check for a file column that no bound registry declares.
Part 11 §3 exposes to a rule a table's registry-declared columns "and no others", and Part 05 §15.6
compares an amendment's rows over declared columns. The reference build refuses a record or a batch
carrying a column that no loaded registry declares, naming the column, and three tests of the
writer's suite assert that refusal. No part requires it.

A third probe committed a packet under the registry of the first appraisal whose clock row held
`{"slope":2.0,"offset":5.0}` in the column, then amended it under a registry without the
declaration, adding a second clock. The amendment passed, the rewritten `core.clocks` file held no
such column, and the validator and the reader reported nothing of it. The same amendment under the
earlier registry kept the value. An amendment that wrote only `core.processing_runs` bound the new
version and kept the held `core.clocks` file, column included.

### 2.6 The version is stated in a known set of places

Part 02 §9.2 states the core `registry_version` as `0.14.0` and forbids reusing a development
identifier "for an incompatible contract". R151 §3.2 and R152 §3.4 each advanced the version by one
minor version. R151 added one rule to one table and changed nothing else in the registry, which is
the nearest case to removing one column.

Outside `revisions/`, the version is stated in these tracked places: the registry source's
`registry.toml`; the generated registry and listing; Part 02 §9.2; the specification README's
identifier table and the sentence after it; the `core` lines of the layout in Part 08 §2 and of the
manifest excerpt in Part 08 §3; five lines of the combined rendering; two constants in the tree's
tools, one the registry check's expected version and one the README projection's; and two lines of
one writer test. No package source states it, and no package carries a copy of the core registry.
The column count of 360 appears in five generated lines.

`revisions/impact.py` lists the lines citing the sections this revision restates. Outside
`revisions/` and working documents, Part 02 §5.2 is cited by Part 07 §2.2, by Part 09 §8.1 and by
seven lines of the packages. Each cites its ban on nested types, its rule on a repeated value or
its rule on a value constant across a table, and none cites the sentence §3.2 restates.
Part 02 §9.2 is cited there by the specification README's identifier table, which states the
version and follows it, and by the tree's check and two package sources, which cite the registry
meta-schema.
Part 08 §3 is cited by one line of `integration/`, for the entries its excerpt shows, and
Part 08 §2 by none.

### 2.7 The tree regenerates without the column

A second probe copied `spec/`, deleted the column's entry, and set the version to `0.15.0` in the
registry source, Part 02 §9.2, the README and the two tool constants. The tree's build regenerated
the registry, the listing and the source guide, and the tree's check passed at 45 tables, 359
columns, 116 references and 91 rules. The generated registry lost the seven lines of the column's
object and changed its version line. `0.15.0` is the value §3.3 gives only where this revision is
the next to advance the version.

### 2.8 No ledger pointer moves

The ledger records R3 §3.4 as `registry`, with the note "core.clocks gains transform_slope and
transform_offset; the replaced transform_to_parent is still declared". Its four targets are the
names of the tenth and eleventh columns of `core.clocks` and the identifiers of its fourth and
fifth rules. A target stores a zero-based JSON Pointer index, so those columns appear there as 9
and 10.

The registry-target map holds eight pointers into the columns of `core.clocks` and the evidence
manifests three. Each names the fourth, tenth or eleventh column. Removing the twelfth shifts the
three columns after it, which no pointer names, and removes no rule.

### 2.9 Alternatives

| alternative | why it falls short |
|---|---|
| keep the declaration | the registry keeps a column R3 §3.4 replaced, and a JSON alignment stays admissible beside the typed columns with no rule reading it (§2.2) |
| keep the column and give it a meaning | it reverses R3 §3.4. If the meaning is an alignment, a consumer needs a JSON parser to place a tick, against Part 02 §8.6 and Part 02 §12.6, and Part 01 §3.9 needs a third model that no declared rule can check. If the meaning is the source's own description, `core.clocks.metadata` already holds it |
| keep the column and forbid a writer to fill it | the declaration's only rule would be that it stays empty, which no declared rule can check, and every listing would still show the column |
| remove the column and keep the version | two documents with different declarations would share one identifier, against Part 02 §9.2 |
| remove the column as a correction with no revision | the change alters the incorporated registry's contract: a writer that fills the column writes a declared column before it and an undeclared one after |
| name the new version as a value | three other open changes advance the same identifier (§1), so a named value is wrong once any of them is incorporated first, and changing a Decision clause after acceptance returns the draft for approval |
| add a validator check for a file column that no bound registry declares | the property predates the removal and covers every table of every registry (§2.5). Such a check changes the validator, the corpus and each extension's packets, and the removal does not depend on it |

## 3. Decision

Three subsections remove the declaration, restate the sentence that counted it, and advance the
version the removal changes. The crosswalk in §1.1 places each.

### 3.1 `core.clocks` declares no JSON transform

The incorporated core registry MUST NOT declare `transform_to_parent` on `core.clocks`. The table's
other 14 columns keep their declarations and their order, so `withheld_first_anchor` follows
`transform_offset`. Its primary key, references, amendment groups and 12 rules are unchanged.

### 3.2 Each section stating a core `json_string` column's content is named

Part 02 §8.6 states what a `metadata` column may hold, and Part 02 §12.6 what
`core.processing_runs.parameters` may hold. Part 05 §3.2 and Part 05 §4.3 state what a build
records in an import run's `parameters`, and Part 06 §5 what a writer records in a materialization
run's. Part 01 §3.11 permits an event a structured payload. No part states what
`core.events.payload` or `core.sorting_runs.parameters` holds. Part 02 §5.2 states no count of
core's `json_string` columns; the core registry declares them, as the authority for the `core` and
`analysis` namespaces (Part 02 §2).

### 3.3 The core registry version advances

The core registry's `registry_version` MUST advance by one minor version from the version the
incorporated registry carries when this revision is incorporated. At the baseline that version is
`0.14.0`, which R152 §3.4 assigns. Other open work advances the same identifier, so this draft
takes the next free version at incorporation and fixes no order among them. The registry
meta-schema, the registry-contract descriptor and the rule language are unchanged.

## 4. What this does not change

No validator check is added for a file column that no bound registry declares. A packet built under
the new version by a writer that still fills the column passes with the column unreported, as a
packet holding any undeclared column does today (§2.5).

No part gains a sentence for the removal. Part 01 §3.9 states the two alignment models, and the
registry's descriptions and rules state the typed columns. R3 §3.4's two typed columns and the
rules on them are unchanged.

No fact loses its home. Each alignment fact a part names has typed declarations (§2.3). What a
source states about a clock that no declaration models goes in `core.clocks.metadata` under
Part 02 §8.6.

`core.events.payload` and `core.sorting_runs.parameters` stay declared, and §3.2 states nothing
about what either holds (§7).

The name `transform_to_parent` is not reserved. A later declaration of the name would bind only
packets that bind its registry, since a declaration resolves in the registry a packet binds
(Part 04 §8), so reuse cannot change how an earlier packet reads.

No part defines a minor version of `registry_version`. Part 02 §9.2 forbids reusing an identifier
for an incompatible contract and says nothing of which component advances; §3.3 takes one minor
version as R151 §3.2 and R152 §3.4 did, and that step is precedent, not a rule a part states.

## 5. Consequence

A packet bound to an earlier version validates as before while it is not amended. It embeds the
registry it binds, and a declaration resolves only there (Part 04 §8), so it validates the same
whether or not it holds the column. No corpus packet changes verdict, and each binds the new version
once rebuilt. Nothing needs rebuilding sooner.

A packet built afterwards binds the new version. The reference build refuses an adapter that still
delivers the column, as it refuses any column no loaded registry declares (§2.5). No adapter in the
tree delivers it (§2.4).

An amendment of an earlier packet binds the new version, and that loses a value the column held.
Part 05 §15.6 compares the rows of `core.clocks` over the columns the amended manifest's registry
declares, so a held row that differs only in the column is unchanged. An amending build that
rewrites `core.clocks` writes those rows without the column, and nothing reports the loss (§2.5).
The value then survives only in the superseded file, until cleanup removes it. An amendment that
does not write `core.clocks` keeps the held file, and the packet then binds a registry that does not
declare a column a file holds, which no check reports either. No measured packet holds the column
(§2.4), and no part says what it held. The blind spot is not particular to this column: it applies
to every column a later version stops declaring, and it is left to a proposal of its own (§7).

At incorporation R3 §3.4 stays `registry` in the ledger and keeps its four targets. Its note says
that the replaced column is no longer declared and names §3.1.

The ledger entry of the clause that last assigned the version follows R158. A clause that also
states something that remains, as R152 §3.4 states the meta-schema and descriptor, stays `applied`
and its note names §3.3 (R158 §3.2). A clause that states only the version becomes `superseded`
and names this revision as the one that replaced it (R158 §3.1). If the sidecar catalog is
incorporated first, as its authorized acceptance makes likely, the clause is its version clause.

The registry's totals depend on the same order. This revision takes the columns from 360 to 359
where it is incorporated first, and removes one from whatever total the changes before it leave.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §3.9 already admits two alignment models and neither is JSON. | None required. |
| logical prose and registry | The core registry source drops the twelfth column of `core.clocks` and carries §3.3's version. Part 02 §5.2 restates one sentence and Part 02 §9.2 states the version. The meta-schema, the descriptor and every rule are unchanged. No citer of Part 02 §5.2 cites the restated sentence (§2.6). | `evidence/R<N>.json` names the registry pointer and the two anchors. `spec/tools/check.py` passes with one column fewer, 359 at the baseline, and `core.clocks` at 14. |
| physical profiles | Unchanged. No stored order or encoding rule names the column. | None required. |
| packet manifest and JSON Schemas | Unchanged. The manifest schema constrains a registry entry's `version` by a pattern and fixes no value. | None required. |
| validation and import | Unchanged. No check names the column, and no check is added for an undeclared file column (§4). Under Part 05 §15.6 an amendment binding the new version compares `core.clocks` without the column, so rewriting the table drops a value the column held and nothing reports it; an amendment not writing the table binds the new version over a file that still holds the column (§5). | The corpus verdicts are unchanged. |
| extensions | Unchanged. None of the four extension registries declares, references or reads the column, and each advances its own version independently. | The extension registry checks pass. |
| reader, writer, validator, adapters | No package source changes (§2.4). The two lines of the writer test that pin the core version follow it. An adapter outside the tree that delivers the column is refused by the reference build until it stops. An amending build binding the new version rewrites held `core.clocks` rows without the column, leaving the value only in the superseded file (§5); no source changes for it. | The package suites pass, the writer's three tests of the undeclared-column refusal among them. A writer test in `tests/test_amending.py`, `test_an_amendment_binding_a_registry_without_a_held_column_rewrites_its_rows_without_it`, asserts the behaviour §5 states, so a change to it is seen. |
| conformance fixtures and tests | The corpus regenerates under the new version with no verdict changed. No fixture is added, since no check distinguishes a file with the column from one without (§2.5). | `fixtures/corpus.py`. |
| revision process and tooling | Three new ledger entries and one registry target; the note on R3 §3.4; the entry of the clause that last assigned the version. No existing pointer moves (§2.8). The expected version in `spec/tools/check.py` and in `spec/tools/framework_data.py` follows. No process rule changes. | `ledger.py`, `evidence.py` and `verify.py` pass. |
| generated publications and developer documentation | The generated registry, listing, source guide and combined rendering regenerate, and the specification README's identifier table follows. Part 08 §2 and Part 08 §3 show the new version on their `core` lines alone, since an extension shown there carries its own version. The five generated count lines state one column fewer. The root work list drops its item on the column. | The generators leave the candidate state unchanged. |

## 6. Conformance and implementation evidence

§3.1 is `registry`, placed by the pointer `/resources/core.clocks/table/columns/11/name` in the
generated registry with `equals = "withheld_first_anchor"`. The removed column held that position,
so the guard fails if the column is declared again in its place, where a pointer to the table would
resolve either way. No tool enforces §3.1's MUST NOT beyond that guard and the generated registry:
no invariant or check rejects a core registry that declares the column elsewhere. §3.2 is `applied` at Part 02 §5.2 and §3.3 is `applied` at Part 02 §9.2, each placed
by its canonical anchor. Part 08 §2 and Part 08 §3 follow §3.3 as the informative example, as they
followed R152 §3.4, whose entry names no target in Part 08.

These cases distinguish the incorporated registry from the current one:

- the generated registry declares 14 columns on `core.clocks`, none named `transform_to_parent`,
  and the registry check reports one column fewer for the registry as a whole;
- a search of the tracked files outside `revisions/` finds the name only in the conformance sweep
  of the frozen v0.1 tables; and
- the registry carries a version one minor version above the one it advanced from, and
  Part 02 §9.2, the README's identifier table and the `core` lines of Part 08 state the same value.

No packet case distinguishes the two registries. A packet without the column passes under both, and
a packet with it passes under both, with the same findings (§2.5). The corpus rebuilt under the new
version, with every verdict unchanged, is the positive packet evidence.

§2.7's probe establishes that the tree regenerates and passes its check without the column, and
§2.5's that the removal changes no validator verdict. The writer's three tests of its refusal of an
undeclared column cover a build that is still delivered this one; they are tests of the reference
build, not of a requirement of a part.

## 7. Open

What `core.events.payload` and `core.sorting_runs.parameters` hold is stated by no part;
Part 01 §3.11 only permits the payload. Stating either decides what an event carries or what a
sorting run records, and neither answer changes the removal, so the question is left to a proposal
of its own.

Neither Part 05 §15.6 nor any validator check sees a column that a held file carries and the
amended manifest's registry does not declare (§5). Whether an amending build should refuse,
preserve or report such a column decides the fate of every column a later version stops declaring,
and the removal does not depend on the answer, so it too is left to a proposal of its own.

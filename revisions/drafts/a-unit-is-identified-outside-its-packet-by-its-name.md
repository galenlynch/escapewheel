# A unit is identified outside its packet by its name

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `0815350e32f1a583964d51d7ec01d211de337747` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§1, 8.2, 9.2, 9.4, 10.1, 12.1 and 12.9; Part 05 §5.1; Part 08 §§2 and 3; the registry meta-schema; the registry-contract descriptor; the core registry |
| **Depends on** | R85 §2.2 (the uniqueness of a name, which this checks); R152 §3.4 (the meta-schema and descriptor identifiers this advances from); R160 §3.8 (the core registry version at the baseline) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

Part 02 §12.1 tells a consumer to relate a unit to anything outside its packet by
`(sorting_run_id, local_unit_label)`. That pair does not identify a unit. Its first member is a
number the packet assigns, which the same paragraph forbids using outside the packet. It omits the
curation, so two curations of one run that keep one label share a value of it. Its second member is
nullable and may repeat within a curation. Four corpus packets that pass with no finding hold units
sharing the pair. Part 02 §12.9 states the interval sentence in the same form, with the assigned
`session_id` in it and a nullable label.

The rest of the specification relates a row to anything outside its packet by the row's name.
Part 01 §2.1 pairs every assigned identifier with the name it was assigned from, so that a process
outside the packet needs no number the packet assigned; Part 02 §8.2 requires the name to be unique
within its packet; and Part 05 §4.3 has an amending build match the rows a packet holds by name.
Two weaknesses leave that relation unreliable: nine core names are declared `nullable`, and no
check reports a name two rows share.

This revision makes the name of every owned assigned identifier `required`, has the
registry-document contract check that, has a validator generate a check reporting a name two rows
of one table share, and has Part 02 §12.1 and Part 02 §12.9 name `unit_name` and `interval_name`.
The contract change takes a new descriptor and a new meta-schema `$id`, and the core registry takes
a new version.

The change is structural because it revises in place the pairing statement and the uniqueness
paragraph of Part 02 §8.2, one sentence each of Part 02 §12.1 and Part 02 §12.9, and the
identifier statements of Part 02 §§1, 9.2 and 9.4. An appended section would
leave §8.2 saying that no rule can check uniqueness and §12.1 naming a relation four passing
packets contradict.

### 1.1 Structural crosswalk

Every affected existing section carries a canonical anchor at the baseline, so no bootstrap is
needed.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §8.2, the pairing statement | revise in place | same section | the name of an owned assigned identifier is `required` | §3.1 |
| Part 02 §8.2, the sentence on what checks the pairing | revise in place | same section | `registry.identity.name` also checks the name's presence | §3.1 |
| the core registry, nine name declarations | revise in place | same declarations | each name's presence is `required` | §3.2 |
| Part 02 §8.2, the sentence that no rule can check uniqueness | replace in place | same section | a generated check reports a shared name; no check reports a merge | §3.3 |
| Part 02 §10.1, the generated checks | extend in place | same section | a validator generates a uniqueness check for every name of an owned assigned identifier | §3.3 |
| Part 05 §5.1, the list of generated kinds | extend in place | same section | the list names the new kind | §3.3 |
| Part 02 §12.1, the relation a consumer uses outside the packet | revise in place | same section | the relation is `unit_name` | §3.4 |
| Part 02 §12.9, the relation a consumer uses outside the packet | revise in place | same section | the relation is `interval_name` | §3.4 |
| Part 02 §12.9, the sentence that `core.intervals.label_unique_within_kind` draws a shared label | keep, as a sentence of its own | same section | none: it states what the rule checks of a label | none |
| Part 02 §§1, 9.2 and 9.4, the incorporated identifiers | revise in place | same sections | the meta-schema, descriptor and core registry identifiers advance, and §9.2 states the migration of an extension | §3.5 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none: they show the core version and the four extension versions the example binds | none |

## 2. Background

Section 2 is informative. Each count of the tree and the corpus was rerun at the baseline, and §2.3
reports a probe made at an earlier one. The registry counts read the five
generated registry documents and the incorporated descriptor. The corpus counts read the 132
packets `verify.py --quick` built, where all 37 stages passed, taking from each the tables its
manifest lists and the declarations its embedded registries hold. Two packets held outside the tree
were read the same way at an earlier baseline: the `packet-r153` builds of `ecephys_776259` and `ecephys_786867`, each of
one recorded session, binding core 0.14.0 and the four extension registries at the versions the
repository carries.

### 2.1 The pair does not identify a unit, and the name does

Of the 132 corpus packets, 128 carry `core.units`, with 260 unit rows between them.

| measure over `core.units` | packets | unit rows |
|---|---:|---:|
| `local_unit_label` is null | 2 | 4 |
| the unit shares `(sorting_run_id, local_unit_label)` with another unit | 4 | 12 |
| the unit shares `(sorting_run_name, curation_name, local_unit_label)` with another unit | 2 | 4 |
| `unit_name` is null | 0 | 0 |
| the unit shares `unit_name` with another unit | 0 | 0 |

The four packets sharing the pair are `amended_curation`, `amended_preference`, `null_unit_labels`
and `null_unit_labels_swapped`, each expected to pass with no finding. The first two hold one run
with two curations, each holding units labelled "17" and "42". The other two hold two units of one
curation with null labels, numbered in the two orders Part 02 §12.1 permits, so in them the name is
the only column that says which unit is which.

`sorting_run_id` is assigned, and Part 05 §4.3 makes a packet's identifiers a function of the
recipes that built and amended it, so one run can carry two numbers in two packets. The triple of
names and label fails wherever two units of one curation share a label or lack one, which Part 02
§12.1 permits. Every candidate relation other than the name relies on a column that is either
assigned or nullable and free to repeat.

Part 02 §12.9's triple `(session_id, interval_kind, local_interval_label)` holds the assigned
`session_id`, and `local_interval_label` is nullable. `core.intervals.label_unique_within_kind`
draws a label two intervals of one session and kind share, so the triple identifies an interval
whose label is present. `interval_name` has been `required` since R148 §3.1.

Inside a packet nothing uses either relation: every reference into `core.units`, six in core and
three in `aind_unit_qc`, is on `unit_id` alone, and no reader or validator source reads
`local_unit_label` or `unit_name`.

### 2.2 Nine core names are nullable, and no check reports a shared name

The core registry, at `registry_version` 0.15.0, declares 47 tables, and 17 own an assigned
identifier as Part 02 §8.2 defines owning. Each of the 17 has a primary key of one column. The
names of `analysis.array_assets`, `core.array_assets`, `core.calibrations`, `core.clocks`,
`core.devices`, `core.event_streams`, `core.intervals` and `core.media_assets` are `required`. The
names of `core.curation_versions`, `core.electrodes`, `core.probes`, `core.processing_runs`,
`core.sessions`, `core.sorting_runs`, `core.source_files`, `core.subjects` and `core.units` are
`nullable`.

Of the four extension registries in the repository, one table owns an assigned identifier:
`dynamic_foraging.blocks`, keyed by `(session_id, block_id)`, whose `block_name` is `nullable` and
described as the block's own name "where the source has one". The other three own none.

| population | name columns it holds, of 18 | names | null names | names two rows of one table share |
|---|---:|---:|---:|---:|
| the 132 corpus packets | 14 | 3,044 | 0 | 1 |
| `ecephys_776259`, 6,781 units | 16 | 12,243 | 0 | 0 |
| `ecephys_786867`, 4,505 units | 17 | 8,932 | 0 | 0 |

The one shared name is an `interval_name` in `dup_pk`, which duplicates a whole row of
`core.intervals` and is expected to draw `core.intervals.primary_key_unique`; its record names no
check that must be absent. No measured packet holds a row of `analysis.array_assets`, and the corpus
holds none of `core.calibrations`, `core.media_assets` or `dynamic_foraging.blocks`.

Every measured packet holds one session. The two packets outside the tree hold 37 rows of
`dynamic_foraging.blocks` named `block_01`, `block_02` and so on, with nothing of the session in
the name. No tracked source names that table, so what composes those names was not read.

Part 02 §8.2 says that no rule can check uniqueness, because a writer numbering an identifier per
distinct name has already merged two things sharing a name into one row. That covers the merge.
Two rows of one table carrying one name is a different defect, which arises where a writer numbers
its rows from something other than the name it records, and a query grouping one table's rows on
the name draws it. No table declares such a rule for a name, and Part 02 §10.1 generates none.

### 2.3 The contract checks the pairing, and a contract that changes takes a new descriptor

Part 02 §9.4 incorporates `escapewheel-registry-contract-v0.9`, which selects meta-schema 0.11.0
and lists 29 invariants. `registry.identity.name` checks what Part 02 §8.2 states of the pairing:
exactly one name, a `string` `data` column declaring no `identity`, and no same-base name on a
table that only carries or references the identifier. Part 02 §8.2 states no presence, and the two
copies of the invariant, in the specification tools and the validator, do not read one.

A contract under which a nullable name is a defect finds the baseline core registry invalid, so it
is a different contract. Part 02 §9.4 forbids reinterpreting a published descriptor, and Part 02
§9.2 forbids reusing a development identifier for an incompatible contract. The new contract
therefore takes a new descriptor ID, selected by a new meta-schema `$id`; the meta-schema changes in
nothing else. R145 §3.5 and R152 §3.4 each advanced the same three identifiers for a change of the
invariants alone. The tree holds the meta-schema `$id` in 26 files, the descriptor ID in 11 and the
core version in 11, outside the accepted records, their evidence, the audit notes, the open
proposals and drafts, and the built corpus; the `dynamic_foraging` registry also carries 0.14.0 as
its own version.

A probe ran on a copy of `spec/` at an earlier baseline, before R160 was incorporated, with each of
the nine names `required` and the copy's `registry.identity.name` also requiring a `required` name.
The copy regenerated and passed the tree's own check at 45 tables and 360 columns, with 184
`required` columns where that baseline had 175; the baseline has 179. Under the probe checker that
baseline's core registry is invalid, with one `registry.identity.name` outcome for each of the nine tables, and the probe registry is valid.
Against the probe registry, `vr_foraging`, `aind_opto` and `aind_unit_qc` are valid and
`dynamic_foraging` is invalid with one outcome, `registry.identity.name` on
`dynamic_foraging.blocks`. The probe kept the v0.9 descriptor and meta-schema, so it shows the
effect of the presence requirement and not of the identifier advance.

The validator holds one meta-schema and one descriptor. Part 02 §9.4 makes evaluation `unsupported`
for a selector a checker does not hold, Part 05 §14.5 lets only a `valid` context direct packet
checks, and Part 05 §9.5 gives an `unsupported` registry the verdict `incomplete`. A validator
holding only the new pair therefore reports `incomplete` for a packet bound under meta-schema
0.11.0 until the packet is rebuilt.

### 2.4 A generated check reaches every table that owns an assigned identifier

The check for a column declaring `finite: true` is the model: Part 02 §10.1 states what it
reports, its level and its ID, and Part 05 §5.1 lists it. Part 05 §5.4 applies to an extension's
resources every check a core resource receives because of its declarations, Part 05 §9.5 gives a
generated check's finding to the registry whose declaration generated it, and Part 05 §15.4 takes
a generated check's inputs from those declarations. A new generated kind is therefore covered by
those three sections as they stand.

The check for a name is triggered by a key, the references and a column name, which a registry
under an earlier contract declares too. A validator holding an earlier descriptor beside the new
one therefore generates the check for a packet bound to an earlier registry, where it reports a
shared name Part 02 §8.2 already forbade. Such a packet can hold a null name, and a null is no value
two rows share.

### 2.5 A table with a key of several columns

Each core table that owns an assigned identifier has a key of one column, so its name and its key
agree about which rows are distinct. `dynamic_foraging.blocks` is keyed by a session and an
assigned identifier, and a packet of two sessions whose blocks are each named `block_01` would hold
that name in two rows that differ in `session_id`. Part 02 §8.2 scopes uniqueness to the packet,
Part 05 §4.3 assigns identifiers packet-wide, and Part 01 §2.1 pairs a name with an identifier so
that a process outside the packet needs no number. A check grouping on the name alone keeps that
requirement and has one shape for every table; one grouping within the key's other members would
make a name identify a row only together with an assigned number.

### 2.6 Alternatives

| option | effect |
|---|---|
| keep the pair | a relation four passing packets contradict, holding an assigned number and omitting the curation |
| strike the sentence and keep the prohibition | Part 02 §12.1 says only what a consumer does not use, and R123 §3.1 defers to a relation no section defines |
| the triple of run name, curation name and label | identifies a unit only once the label is present and untied within a curation, which withdraws the permission R149 §3.1 gave and fails two passing fixtures |
| one general sentence in Part 02 §8.2 for every owned assigned identifier | extends a consumer-facing relation to 15 identifiers no accepted clause addresses, and R123 §3.1 still has Part 02 §12.1 define one |
| the nine names `required` declaration by declaration | changes no contract and leaves each extension and each later core table to choose again |
| a declared rule on each table | leaves an extension's names unchecked and each later table to declare its own |
| `unit_name`, with every name `required` and checked from structure | the relation the rest of the specification uses; null and shared in no measured passing packet; one owner for a rule that is the same for every table |

## 3. Decision

Five subsections make every name of an owned assigned identifier `required`, apply that to the core
registry, generate a check for a shared name, name the relation a consumer uses for a unit and an
interval, and advance the registry identifiers. The crosswalk in §1.1 places each.

### 3.1 The name of an owned assigned identifier is required

For every owned assigned identifier, a table MUST declare exactly one corresponding name formed by
replacing `_id` with `_name`. The name MUST be a string data column whose presence is `required`,
and MUST NOT declare `identity`.

The registry-document contract checks, as `registry.identity.name`, the pairing and the name's
presence together. A checker reports that invariant for an owned assigned identifier whose name is
absent, declared twice, not a `string` `data` column, declaring `identity`, or of a presence other
than `required`, and for a table that carries or references an assigned identifier and declares the
same-base name.

### 3.2 The core registry declares every name it pairs as required

The core registry declares the presence `required` for `core.curation_versions.curation_name`,
`core.electrodes.electrode_name`, `core.probes.probe_name`,
`core.processing_runs.processing_run_name`, `core.sessions.session_name`,
`core.sorting_runs.sorting_run_name`, `core.source_files.source_file_name`,
`core.subjects.subject_name` and `core.units.unit_name`. Each keeps its type, role, vocabulary and
description.

### 3.3 A generated check reports a name two rows share

A validator MUST generate, from the declaration alone, for the name of every owned assigned
identifier, a check that reports each row whose name another row of the same table holds, at level
`error`, under the check ID `<declaration_id>.<column>.unique`, such as `core.units.unit_name.unique`.
The check groups a table's rows on the name alone, whatever other columns the table's primary key
holds, and counts no null name. Two names are equal where their sequences of Unicode scalar values
are equal, compared as Part 11 §5 compares characters, without case folding or normalization.
Where the name is `optional` and a table omits it, the check reports nothing. A validator generates
the check wherever a valid registry context directs packet checks, whichever registry-contract
descriptor that registry was checked under. The finding belongs to the registry holding the declaration under Part 05 §9.5, and Part 05 §5.4 applies the
check to the names an extension declares.

The check reports two rows of one table that carry one name. No check reports two things a writer
merged under one name: a writer numbering an assigned identifier per distinct name emits one row
per name, so two things wrongly sharing a name are already one row by the time the packet exists,
and that row is indistinguishable from the correct case where four streams naming one serial
become one device. The obligation not to merge falls on whatever composes the name. An assigned
identifier's name remains unique within its packet, and a name column pairing with no assigned
identifier names a kind of thing and is expected to repeat.

Part 05 §5.1 lists the uniqueness of the name of every owned assigned identifier among the checks
generated from structure.

### 3.4 A consumer relates a unit and an interval outside the packet by name

A table keyed on a unit carries `unit_id` and not the run or the curation. A consumer relating a
unit to anything outside the packet that holds a name, such as another packet, a recipe or a later
build, uses `unit_name`. A consumer MUST NOT identify a unit by its `unit_id` outside the packet
that assigned it, where the number means nothing. No checker verifies this.

A consumer relating an interval to anything outside the packet that holds a name uses
`interval_name`.

### 3.5 The registry identifiers advance

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry meta-schema `$id` | `https://escapewheel.org/schemas/registry/0.11.0`, which R152 §3.4 assigns | `https://escapewheel.org/schemas/registry/0.12.0` |
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.9`, which R152 §3.4 assigns | `escapewheel-registry-contract-v0.10` |

The core registry's `registry_version` MUST advance by one minor version from the version the
incorporated registry carries when this revision is incorporated. At the baseline that version is
`0.15.0`, which R160 §3.8 assigns. Other open work advances the same identifier, so this revision
takes the next free version at incorporation and fixes no order among them.

The meta-schema changes only its `$id`. The v0.10 descriptor selects meta-schema 0.12.0, lists
`escapewheel-rule-sql-v0.2` alone in `rule_languages`, and holds the 29 invariants of v0.9 in their
order; it differs from v0.9 in its ID, the meta-schema it selects, and what §3.1 has
`registry.identity.name` report. Part 02 §1 incorporates it as
`artifacts/registry_contracts/escapewheel-registry-contract-v0.10.json`.

An extension registry migrated to meta-schema 0.12.0 MUST carry a `registry_version` different from
the one it carried under 0.11.0; the core specification does not assign it (Part 09 §5.5). No
checker verifies this.

## 4. What this does not change

The specification does not say what a unit's name is composed from; that obligation stays with
whatever composes it. Part 12 §4's `units` term is unchanged, so a build that relates a later
source's unit by its label and a device's name still cannot tell two curations of one run apart;
that is a defect of the adapter interface and is not addressed here. Part 05 §3.5's refusal to
amend a packet holding a null name stays, as a guard against a packet that does not conform.
Part 05 §13.1's rule that a reader presenting several packets distinguishes them by a session
discriminator it does not derive from a name is unchanged: a name is unique within its packet and
is not a global identity.

## 5. Consequence

Every packet is rebuilt, binding meta-schema 0.12.0 and the new core version. No row of a measured
packet changes, and no packet the corpus expects to pass changes verdict: none holds a null or a
shared name (§2.2). `dup_pk` draws `core.intervals.interval_name.unique` beside the key check it is
built to draw, which its record admits. A packet holding a null name fails the generated non-null
check once it binds the new registry, and one holding a shared name fails the new check; its writer
records or corrects the name and rebuilds.

Each of the four extension registries in the repository names meta-schema 0.11.0 and migrates, each
taking a version of its own choosing. `dynamic_foraging` is invalid under the new contract, on
`dynamic_foraging.blocks`, until its owner changes that declaration (§2.3); the core specification
does not say how. The other three need only the new `$id` and version, and the repository's copy of
each of the four is made valid at incorporation.

A validator holding only the new contract reports a packet bound under meta-schema 0.11.0
`incomplete` until it is rebuilt (§2.3). A validator holding an earlier descriptor beside the new
one reports, under the new check, a shared name in such a packet that passed before; Part 02 §8.2
already forbade it. Two conforming validators can therefore disagree on such a packet: one holding
only v0.10 reports it `incomplete`, and one also holding v0.9 reports it `failed` where it holds a
shared name. The reference validator holds one descriptor and exhibits only the first.

The check has these limits:

- a duplicated row of a table that owns an assigned identifier draws both
  `<declaration_id>.primary_key_unique` and the new check, and a validator reports both;
- a table has one instance (Part 02 §2.4), so the check groups all of a table's rows in the packet
  and no grouping by instance arises;
- a name an adapter delivers as null in a `required` column fails the generated non-null check, so
  a build does not promote the packet (Part 05 §6), and no part states more of that case; and
- a name is unique among the names of one identifier, and two names of different identifiers, such
  as a probe's and a device's, may be equal.

R159 and R160 are accepted and incorporated at the baseline. R160 advanced the core registry to
0.15.0 and added two tables and a catalog, none of which owns an assigned identifier, so the 17
owners and nine names of §2.2 are unaffected. Of the three other open drafts,
`a-null-producing-run-on-an-array-says-the-packet-names-none.md` and
`core-declares-a-clocks-transform-in-typed-columns-alone.md` advance the same core version, and
`a-recipe-accepts-a-discarded-value-by-naming-its-column.md` changes no registry declaration. §3.5
names no core target, so it takes the version after whichever advance lands before it.

These accepted clauses change:

- R81 §2.5's ledger entry stays `applied` at `ew-unit-identity` and gains a note that §3.4 replaces
  the pair it named with `unit_name` and keeps the label's column and the prohibition on `unit_id`.
- R123 §3.1's entry stays `applied` and gains a note that the relation Part 02 §12.1 defines is
  `unit_name`.
- R148 §3.1's entry stays `applied` and gains a note that §3.4 replaces the triple it named at
  `ew-interval-identity` with `interval_name`.
- R85 §2.2's entry stays `applied` and gains a note that §3.3 restates what a check can report of a
  name's uniqueness.
- R152 §3.4's entry stays `applied`, since its sentence on migrating to meta-schema 0.11.0 remains in
  Part 02 §9.2, and gains a note that §3.5 advances the meta-schema and descriptor identifiers it
  assigned, as the entries for R145 §3.5 and R150 §3.10 record.
- R160 §3.8, which assigns only the core version, becomes `superseded` by this revision, as the
  entry for R151 §3.2 did. Where another revision has advanced the core version first, the entry
  for that revision's version clause is the one replaced: it becomes `superseded` where that clause
  assigns only the version, and otherwise stays `applied` and gains a note.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §2.1 already says that a name is what a process outside the packet references. | None required. |
| logical prose and registry | Part 02 §8.2 takes §3.1 and §3.3's paragraph, Part 02 §10.1 takes §3.3, Part 02 §§12.1 and 12.9 take §3.4, and Part 02 §§1, 9.2 and 9.4 take §3.5. The nine core declarations of §3.2 change their presence. The meta-schema changes its `$id`; a v0.10 descriptor is added. | `evidence/R<N>.json` names each anchor and registry pointer; the tree's registry check passes at the new identifiers. |
| physical profiles | Unchanged. The check is a query over one table and asks nothing of a profile; Part 03 §5.3 cites Part 02 §12.1 for the numbering of units, which is unchanged. | None required. |
| packet manifest and JSON Schemas | The registry meta-schema `$id`. The manifest, descriptor and registry-result schemas keep their shape. | The packages' copies regenerate from their sources. |
| validation and import | Part 05 §5.1 lists the new kind. Part 05 §§5.4, 9.5 and 15.4 cover it as they stand; Part 05 §3.5 and §14.5 are unchanged. | The validator suite. |
| extensions | Each repository extension registry migrates to the new `$id` and takes its own version, and the repository's copy of `dynamic_foraging` changes its declaration of `dynamic_foraging.blocks` so that it is valid under v0.10. The core specification chooses neither the versions nor that declaration. | The registry check over every extension registry finds each valid under v0.10. |
| reader, writer, validator, adapters | Both registry-document checkers implement §3.1's presence requirement and the new identifiers; the validator generates §3.3's check, adds its ID family to its table of check IDs, and follows the new descriptor. The reader is unchanged: it reads neither the label nor the unit's name. The writer already fills every name in every row it writes; no adapter changes. | The validator, reader and writer suites; both session packets rebuilt and validated with no error. |
| conformance fixtures and tests | §6's packets and registry documents join the corpus and the registry-conformance vectors; `dup_pk`'s record is unchanged. | `fixtures/corpus.py`; the registry-conformance vectors. |
| revision process and tooling | The ordinary ledger and evidence records and the notes above. The specification tree's checker and the fact generator follow the three identifiers. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification, the registry's table listing and Part 08 §§2 and 3 regenerate, with the new core version and each extension's new version; the specification README's identifier table follows the version. The validator's README and design document and the registry source's guide name the new kind and its counts; the specification tools' conventions module stops saying that no rule can enforce uniqueness. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 02 §8.2 (`ew-identifier-semantics`). §3.2 is `registry`, with one pointer
to each of the nine columns. §3.3 is `applied` at Part 02 §8.2, Part 02 §10.1 (`ew-tier-1-rules`)
and Part 05 §5.1 (`ew-tier-1-validation`). §3.4 is `applied` at Part 02 §12.1 (`ew-unit-identity`)
and Part 02 §12.9 (`ew-interval-identity`). §3.5 is `applied` at Part 02 §1
(`ew-core-logical-schema-scope`), §9.2 (`ew-registry-self-description`) and §9.4
(`ew-registry-conformance`), as R152 §3.4 was. Part 08 §§2 and 3 are a projection of the example
packet and carry no clause.

These cases distinguish the new rules from the current ones:

- the core registry, with 17 `required` names, is valid under the v0.10 descriptor;
- a core-class and an extension-class registry document each declaring a nullable name for an
  owned assigned identifier draw `registry.identity.name`, where under v0.9 both are valid;
- a core-class registry document declaring a name for an owned assigned identifier `optional`
  draws `registry.identity.name` under v0.10;
- a registry document naming meta-schema 0.11.0 is `unsupported` to a checker holding only the new
  meta-schema and descriptor;
- a packet with a null name in a table that owns an assigned identifier draws that column's
  generated non-null check at `error`;
- a packet with two rows of such a table that carry one name and different keys draws the new check
  and no key check, which no existing packet isolates, since `dup_pk` draws both;
- a packet bound to a registry checked under v0.9 whose fixture-local extension table declares an
  owned name `optional` and whose file omits that column draws no finding from the new check;
- two rows of such a table whose names differ only in case or in Unicode normalization draw no
  finding from the new check;
- a packet whose fixture-local extension table, keyed by a session and an assigned identifier, holds
  one name in two rows that differ in session draws the new check, and the finding belongs to the
  extension, with a `failed` verdict for it and `passed` for core;
- `amended_curation`, `amended_preference`, `null_unit_labels` and `null_unit_labels_swapped` pass,
  holding units that share the pair and differ in name; and
- every packet the corpus expects to pass still passes.

The probe of §2.3 establishes that the core registry meets the presence requirement with the nine
declarations changed and that one repository extension declaration does not. The counts of §2.2
establish that the check returns the one shared name of the corpus and none in the two packets
outside the tree. No tool checks that a migrated extension registry changed its version, and no
check sees two things merged under one name.

# A unit is identified outside its packet by its name

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `e60b54e064d98c4479cf58dc18ba831fdfa75ea4` |
| **Decision domain** | specification |
| **Affects** | Part 02 §12.1's sentence on relating a unit to anything outside its packet; Part 02 §12.9's sentence of the same form for an interval; the presence of `core.units.unit_name`; a rule over it; Part 02 §8.2's sentence on checking that a name is unique; the core `registry_version`; the ledger entries for R81 §2.5, R85 §2.2, R123 §3.1 and R148 §3.1 |

## 1. Problem

Part 02 §12.1 tells a consumer to relate a unit to anything outside its packet by
`(sorting_run_id, local_unit_label)`. That pair does not identify a unit. Its first member is a
number the packet assigns, and the same paragraph forbids identifying a unit by `unit_id` outside
the packet because such a number means nothing there. The pair omits the curation, so two curations
of one sorting run that hold one label share a value of it. Its second member is nullable and is
permitted to repeat within one curation. Three packets of the conformance corpus that pass
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
corpus count below was made by reading every packet's Parquet tables and grouping their rows. Each
registry count was made by reading the generated registry documents.

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

### 2.5 Three passing corpus packets hold units that share the pair

Of the 120 corpus packets, 117 carry `core.units`, with 236 unit rows between them.

| measure over `core.units` | packets | unit rows |
|---|---:|---:|
| `local_unit_label` is null | 2 | 4 |
| the unit shares `(sorting_run_id, local_unit_label)` with another unit | 3 | 8 |
| the unit shares `(sorting_run_name, curation_name, local_unit_label)` with another unit | 2 | 4 |
| the unit's run or curation has a null name | 0 | 0 |
| `unit_name` is null | 0 | 0 |
| the unit shares `unit_name` with another unit | 0 | 0 |

The three packets in the second row are `amended_preference`, `null_unit_labels` and
`null_unit_labels_swapped`. The corpus expects each to pass with no finding.

`amended_preference` holds one sorting run with two curations, and each curation holds a unit
labelled "17" and a unit labelled "42". Its four units form two values of the pair.

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
  earlier packet used for this unit", and as "the only bridge between two packets that numbered it
  differently".
- Part 05 §4.3 has an amending build number a name the packet holds with the packet's identifier
  for it. Part 05 §3.5 has an amending build refuse a packet that holds a null name for an assigned
  identifier a row owns.
- Part 05 §3.1 has a recipe name the row a preferred run is scoped to by the row's name where its
  key is assigned, so that a recipe can name it before any identifier is assigned.
- Part 12 §5 has an adapter hand over identifiers as names and never as numbers.

Inside a packet nothing uses the pair. The core registry declares six references into `core.units`
and the `aind_unit_qc` extension registry declares three, and all nine are on `unit_id` alone.

### 2.7 `unit_name` is declared nullable, and no rule checks that a name is unique

The core registry, at `registry_version` 0.14.0, declares 45 tables, and 17 of them own an assigned
identifier. Eight of the 17 names are `required`: those of `analysis.array_assets`,
`core.array_assets`, `core.calibrations`, `core.clocks`, `core.devices`, `core.event_streams`,
`core.intervals` and `core.media_assets`. Nine are `nullable`: those of `core.curation_versions`,
`core.electrodes`, `core.probes`, `core.processing_runs`, `core.sessions`, `core.sorting_runs`,
`core.source_files`, `core.subjects` and `core.units`. R95 §2.1 observed that a generated name is
nullable while it carries the obligation to bridge two packets.

Across the 120 corpus packets the 17 name columns hold 2,642 values. None is null. One name
repeats, in `dup_pk`, a packet that duplicates a whole row of `core.intervals` and is expected to
fail the primary-key check.

Part 02 §8.2 says that no rule can check uniqueness, because a writer that numbers an identifier
per distinct name has already merged two things sharing a name into one row. That reasoning covers
the merge. A packet in which two rows of one table carry one name is a different defect, and a rule
of the form of `core.intervals.label_unique_within_kind` draws it. No table declares such a rule
for a name.

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
- Five adapters the reference writer ships accept a recipe option, `prefix`, whose text is
  prepended to every name the adapter composes. No part or artifact defines it: a search of
  `spec/parts/` and `spec/artifacts/` for "prefix" finds only an object store's key prefix.
- The corpus builder names its units "1", "2", "recurated.1" and "recurated.2".

Two producers in the tree thus compose different names for a unit, and one recipe option changes
every name a build composes.

The following is inference from those observations and from Part 05 §4.3. Two builds give a unit
the same name where one recipe produced both, or where both composers follow one convention with
the same options. Nothing in the specification makes two independently written writers agree on a
name. The same holds for `sorting_run_name` and `curation_name`. Of the columns in the three
candidate relations, only `local_unit_label` is the source's own value.

### 2.9 A build relates a later source's units by a third relation

Part 12 §4 has a build supply the term `units`: one record per unit, holding the source's label
for it and the identifier assigned. In the reference build each record holds the label, the unit's
name, and the text after the last `.` of the sorting run's name, which is a device's name. Three
reference adapters find a unit of their own source by the device's name and the label. Two
curations of one run, or two runs over one probe, share a value of that pair wherever both hold a
label, as two curations share the pair of Part 02 §12.1.

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

Of the 120 corpus packets, 119 carry `core.intervals`, with 245 rows between them. No label is
null. Two packets hold intervals that share the triple, `dup_pk` and `repeated_interval_label`, and
both are expected to fail. The corpus therefore shows no passing packet in which the interval
triple fails, where it shows three for the unit pair. The triple identifies an interval whose label
is present, by a checked rule. What remains is the assigned `session_id` and an interval with a
null label.

### 2.11 Nothing in the tree depends on the pair

`revisions/impact.py` lists 114 citations of Part 02 §12.1, Part 02 §12.9, Part 02 §8.2 and
Part 01 §2.1. Each citer of Part 02 §12.1 in the reader, the writer, the validator, Part 03 §5.3
and the fixtures was read. Each concerns the key, the numbering or the clock of a unit, and none
uses the pair. No reader or validator source reads `local_unit_label` or `unit_name`.

No other proposal is open. Five drafts are open, and none amends Part 02 §8.2, Part 02 §12.1,
Part 02 §12.9 or the declaration of `core.units`. One of them, "Core declares a catalog of
sidecars", adds declarations to the core registry and so touches the same `registry_version`.

## 3. Desired outcome and constraints

Part 02 §12.1 names a relation that identifies exactly one unit of a packet without the packet's
numbers, every unit of a conforming packet has a value for it, and a validator reports a packet in
which it is absent or shared. The interval sentence of
Part 02 §12.9 takes the same form. The ledger says which accepted clause each sentence now carries.

Each affected fact has one owner. Part 02 §12.1 and Part 02 §12.9 own the two sentences. The core
registry owns the presence of `unit_name` and any rule over it. Part 02 §8.2 owns what a name is,
that it is unique, and what a rule can check of that. Part 01 §2.1 owns the purpose of a name and
is not changed. The change is at the logical level: it alters no concept of Part 01 and no storage
property.

The resolution preserves:

- `unit_id` as the whole key of `core.units` and of every reference into it;
- the prohibition on identifying a unit by `unit_id` outside the packet that assigned it;
- `local_unit_label` as the source's own spelling, nullable, with the numbering order and the
  permission for tied and null labels that R149 §3.1 states;
- Part 05 §13.1's rule that a reader presenting several packets distinguishes them by a session
  discriminator it does not derive from a name; and
- the conformance of every packet the corpus expects to pass.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep `(sorting_run_id, local_unit_label)` | the sentence names a relation that fails in three passing corpus packets (§2.5), contains a packet-assigned number (§2.2) and omits the curation (§2.3) |
| strike the sentence and keep the prohibition | Part 02 §12.1 then says what a consumer does not use and leaves the positive relation to Part 01 §2.1; R81 §2.5 and R123 §3.1 each keep a positive duty with no text carrying it |
| `(sorting_run_name, curation_name, local_unit_label)` | removes the assigned number and adds the curation; identifies a unit only where its label is present and unique within its curation, which Part 02 §12.1 does not require (§2.4) |
| state the relation once, in Part 02 §8.2, for every owned assigned identifier | one owner for a rule that is the same for all 17 identifiers; true only for a row whose name is present, and nine of the 17 names are nullable (§2.7) |
| `unit_name` (preferred direction) | the relation Part 01 §2.1, Part 02 §8.2 and Part 05 §4.3 already use (§2.6); unique and present in every unit row of the corpus (§2.5); `unit_name` becomes `required`, and a rule draws a name two units share |

The three candidate relations compare as follows.

| question | `(sorting_run_id, local_unit_label)` | `(sorting_run_name, curation_name, local_unit_label)` | `unit_name` |
|---|---|---|---|
| unique within a packet by an existing key or rule | no key and no rule; shared in 3 passing corpus packets | no key and no rule; shared in 2 passing corpus packets | Part 02 §8.2 requires it; no key and no declared rule; shared in no corpus packet |
| null | the label is nullable, and null in 4 corpus rows | all three columns are nullable; the label is null in 4 corpus rows | declared nullable; null in no corpus row; an amending build refuses a packet where it is null |
| the same value from two builds of one source | the label yes; the run's number only under the same sequence of recipes | the label yes; the two names where the composer and its options are the same | where the composer and its options are the same; one recipe reproduces it (Part 05 §4.3) |
| what the reference writer records | the run's number and the sorter's label | the adapter's composed names and the sorter's label | the adapter's composed name: run, curation and padded label (§2.8) |

What each costs:

| cost | keep the pair | the triple of names and label | `unit_name` (preferred direction) |
|---|---|---|---|
| part text | none; the sentence stays untrue | Part 02 §12.1's sentence; the permission for null and tied labels is withdrawn, or the sentence is limited to units whose label is present and untied | one sentence in Part 02 §12.1 and one in Part 02 §12.9; Part 02 §8.2's sentence on what a rule can check; Part 02 §9.2 restates the registry version |
| registry declarations and rules | none | `sorting_run_name`, `curation_name` and `local_unit_label` become `required`; a rule draws a label two units of one curation share; the description of `unit_name` as the only bridge is reworded | `unit_name` becomes `required`; its description stands; one rule draws a name two units share, and one a name two intervals share (question 4) |
| registry version | none | advances | advances |
| writer | none | a writer composes a label for a unit its source did not label, which the column is defined not to hold | none observed: the reference writer fills `unit_name` in every row |
| validator | none | evaluates one more declared rule | evaluates two more declared rules; Part 05 §5.1 already generates the non-null check of a `required` column |
| corpus | none | `null_unit_labels` and `null_unit_labels_swapped` become failures or are removed, with the cases of R149 §3.1 they exercise; negatives for a null and a repeated label | no packet changes verdict; negatives for a null `unit_name`, a shared `unit_name` and a shared `interval_name` |
| consumer | a relation that does not identify | two joins, to `core.sorting_runs` and `core.curation_versions` | one column of `core.units` |

Under the preferred direction, Part 02 §12.1's sentence says that a consumer relating a unit to
anything outside the packet uses `unit_name`. The prohibition on `unit_id` that follows it is
unchanged.

**The label stays a fact about the unit and stops being presented as an identity.**
`local_unit_label` keeps its column, its type, its nullability and its place in the numbering
order. It records what the sorter called the unit within its run and curation, and a consumer
looking for the sorter's own record of a unit reads it together with the unit's run and curation
rows. Part 02 §12.1's first paragraph already says what the label records, so no further text is
needed there.

**`unit_name` becomes `required`.** A relation a consumer is told to use has a value in every row.
The reference writer fills the column in all 236 corpus rows, a writer that numbers units per
distinct name always holds a name, and Part 05 §3.5 already refuses to amend a packet in which a
name is null. `interval_name` has been `required` since R148 §3.1 declared it.

**A rule draws a name two units share.** Part 02 §8.2 requires a name to be unique within its
packet and says that no rule can check it. A rule of the form of
`core.intervals.label_unique_within_kind` draws two rows that carry one name (§2.7), so
`core.units` declares one, and `core.intervals` declares one for `interval_name`. Part 02 §8.2's
sentence then says what a rule checks and what it cannot: two things a composer merged under one
name are one row, which no rule can tell from one thing seen twice. The obligation on whatever
composes the name stays. Question 4 asks how far the rule reaches.

**The name is not a global identity.** A consumer relating units of several packets still says
which packet or session a name belongs to, as Part 05 §13.1 has a reader do. Two builds agree on a
name under the conditions §2.8 states, and the preferred direction leaves the composition of a
name where R85 §2.2 placed it (question 5).

**The interval sentence takes the same form.** Part 02 §12.9's sentence says that a consumer
relating an interval to anything outside the packet uses `interval_name`.
`core.intervals.label_unique_within_kind` and the sentence that states it are unchanged: the rule
still refuses a source that repeats a label within a session and kind, and no longer has to carry
an identity. The change removes the assigned `session_id` from the relation and covers an interval
whose label is null (§2.10). Question 2 asks whether the interval sentence changes at all.

**The triple is not preferred** because it identifies a unit only after `local_unit_label` is made
present and unique within a curation. That withdraws the permission R149 §3.1 gave, turns two
passing fixtures into failures, and asks a writer to invent a label for a merged or split unit that
its source did not label (§2.4). Its two names are composed by the same adapter that composes
`unit_name`, so it is no more stable across writers (§2.8).

**Stating the rule once in Part 02 §8.2 is not preferred** because Part 01 §2.1 already gives the
general purpose of a name, and only two sections state a relation for a consumer, the two this
change corrects. A general sentence would extend a consumer-facing statement to 15 identifiers for
which no accepted clause makes one.

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
  entry stays `applied`, with a note that the new clause restates what a rule can check.
- R149 §3.1 is unchanged.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 §2.1 already says that a name is what a process outside the packet references, and Part 01 §3.13 prescribes no key. |
| logical prose, registry meta-schema, declarations and rules | Affected. Part 02 §12.1 and Part 02 §12.9 each change one sentence. `core.units.unit_name` changes presence from `nullable` to `required`, and the eight other nullable names change with it under question 3's preferred answer. `core.units` and `core.intervals` each declare one rule, and Part 02 §8.2's sentence on checking uniqueness is restated. Part 02 §9.2 restates the core `registry_version`. The registry meta-schema is unchanged. |
| physical profiles | Unchanged. No storage property is involved. Part 03 §5.3 cites Part 02 §12.1 for the numbering of units, which stays as it is. |
| packet manifest and other JSON Schemas | Unchanged. No schema names the relation or the column's presence. |
| validation and import | Unchanged in text. Part 05 §5.1's generated non-null check covers a `required` name, and a validator evaluates the two declared rules as it evaluates any other. Part 05 §3.5's refusal of a null name stays as a guard against a packet that does not conform. |
| extension registries | Unchanged. The three references of `aind_unit_qc` into `core.units` are on `unit_id`, and an extension's `registry_version` advances independently of the core's (Part 02 §9.2). Under question 3's preferred answer, `dynamic_foraging.blocks.block_name`, which is nullable, raises the same question for its own registry, which this change does not touch. |
| reader, writer, validator, adapters, code generation | The generated registry documents and tables regenerate. No change to the reader or the validator is expected: neither reads the label or the name (§2.11). The reference writer already fills `unit_name` in every row. Whether the `units` term of Part 12 §4 and the three adapters that use it change is question 6. |
| existing packets | A packet's manifest records the core registry version it was built under, so an existing packet is rebuilt to bind the new one, as after each earlier advance. A packet whose every `unit_name` is present and distinct meets the changed declarations, and one holding a null or a shared `unit_name` does not; the corpus holds none among the packets it expects to pass. Unknown for packets outside the tree, which were not read. |
| conformance fixtures and implementation tests | The corpus rebuilds under the new registry version, and no packet changes verdict. Three negative packets are added: a null `unit_name`, a `unit_name` two units share, and an `interval_name` two intervals share. `amended_preference`, `null_unit_labels` and `null_unit_labels_swapped` stay passing, and serve as the evidence that a name tells apart units the pair does not. |
| revision lifecycle, ledger, evidence and tooling | The ordinary ledger and evidence records for the new clauses. The entries for R81 §2.5, R85 §2.2, R123 §3.1 and R148 §3.1 stay `applied` and each gains a note (§4). No tool changes. |
| generated publications and developer documentation | The combined specification, the registry's generated table documentation and Part 08's example regenerate, and the specification README's identifier table follows the version. The writer's design document describes how its adapter names a unit and needs no change unless question 5 fixes a composition. |

## 6. Open questions

1. Which relation Part 02 §12.1 names for a unit. The options are `unit_name` (preferred); the
   triple `(sorting_run_name, curation_name, local_unit_label)`; striking the positive sentence;
   and keeping the pair. The evidence favours `unit_name` on every row of the two comparisons
   in §4. The answer replaces a column pair an accepted clause named, and every later question
   depends on it.
2. Whether Part 02 §12.9's interval sentence changes with it. The options are to name
   `interval_name` (preferred), which gives the two sections one form; and to keep the triple,
   which a checked rule already makes identifying for an interval whose label is present (§2.10).
   Keeping it leaves the assigned `session_id` in the relation, leaves an interval with a null
   label without one, and leaves the two sections in different forms.
3. Which names become `required`. The options are `unit_name` alone, and all nine nullable names
   of §2.7 in one change (preferred). The evidence is the same for each of the nine: none is null
   in the corpus, Part 05 §3.5 refuses to amend a packet where one is, and the generated non-null
   check needs no new rule. Changing all nine advances the registry version once. The narrower
   answer leaves eight names nullable, among them `processing_run_name`, by which Part 05 §3.1 has
   a recipe name the run it prefers.
4. How far a rule checks that no two rows share a name. The options are no rule, as now; a rule on
   `core.units` and one on `core.intervals`, the two tables whose sections tell a consumer to use
   the name (preferred); and a rule for each of the 17 tables. With no rule, a packet in which two
   units share a name passes validation, and the relation rests on a requirement no tool checks. A
   rule on every table adds 15 rules and their negative packets for names no section presents as a
   relation.
5. Whether the specification says what a unit's name is composed from. The options are to leave it
   to whatever composes the name, as R85 §2.2 does (preferred); to state that a unit's name
   distinguishes its run, its curation and the unit, without fixing a spelling; and to fix a
   spelling. A fixed spelling makes two independent writers agree on a name and invites a consumer
   to parse it. Leaving it open keeps the name opaque and makes agreement between two packets a
   property of the recipe that built them (§2.8).
6. Whether the `units` term of Part 12 §4 states a unit's run and curation. The options are to
   leave the term as it is (preferred), and to have each record carry the names of the unit's run
   and curation beside its label. The second widens the change to the adapter interface and to
   three adapters. The first leaves a build unable to tell two curations of one run apart when a
   later source names a unit by its label (§2.9), which is a defect of the same kind in another
   part and wants a proposal of its own.
7. Whether the positive sentence carries a keyword. The options are the indicative in both
   sections, with the keyworded prohibition kept for a unit as it is (preferred); a keyworded
   duty in both, stated as unchecked; and either of those with the prohibition added for
   `interval_id`, which Part 02 §12.9 lacks. No tool can check what a consumer does outside a
   packet, and a prohibition for an interval is a new duty on a consumer.
8. Whether the core `registry_version` advances from 0.14.0. The options are to advance it
   (preferred), as R148 §3.4, R149 §3.4, R150 §3.10, R151 §3.2 and R152 §3.4 each did for a
   changed declaration or rule, and to leave it. One open draft also changes the core registry,
   and whichever of the two is accepted second advances from the other's value.

Each answer fixes a Decision clause or a declaration, so all eight are needed before a draft is
appraised. Question 1 is the one the others depend on.

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

# A null producing run says the packet names none

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `cf9e816a13575a419d6917d8285992d7cb09f2f3` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 01 §3.12; Part 01 §3.17; Part 02 §9.2; Part 08 §2; Part 08 §3; the core registry |
| **Depends on** | R102 §3.1 (the column on both array tables and the writer's obligation, whose reading of a null and whose clause on an acquired array this replaces); R23 §2 (the column on `core.event_streams`, whose reading of a null this replaces); R152 §3.4 (the core registry version at the baseline) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

`core.array_assets` and `analysis.array_assets` are the two catalog tables whose rows describe a
packet's dense arrays, and `core.event_streams` describes the streams its events belong to. Each of
the three declares a nullable `processing_run_id` referencing `core.processing_runs`. The two array
tables describe it as "The run that produced this array. Null means it was acquired rather than
computed." The stream table's description opens "The run that produced it. Null means it came off
the device as recorded."

Both readings are false of conforming packets. A packet need record no provenance, so an array or a
stream that a run computed carries a null wherever the packet does not record that run. A consumer
learns what the null means from the description alone, since no part states it, and so takes a
computed array for an acquired one. Part 01 §3.17 adds a clause of its own, that an acquired array
names no run, which forbids naming a recorded run that processed an array on acquisition.

This revision has Part 01 state what a missing producing run says and what a consumer may conclude
from it, replaces the clause on an acquired array with one a writer can apply to any array, gives
all seven nullable `processing_run_id` columns of the core registry one description, and advances
the core registry version, since the registry's bytes change.

The change is structural because it revises existing sections in place: Part 01 §3.17 and
Part 01 §3.12 each gain the reading beside the sentence it qualifies, Part 01 §3.17's writer
sentence loses its clause on an acquired array, and Part 02 §9.2 restates the version. An appended
section would leave Part 01 §3.17 saying "an acquired array names none" with the reading of that
sentence elsewhere.

### 1.1 Structural crosswalk

Every amended section already carries a canonical anchor, so no bootstrap is needed. No section
moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 01 §3.17, a writer names the run that produced an array where the packet records it | extend in place | same section | an array asset naming no run says only that the packet names none, and a consumer does not read it as acquisition | §3.1 |
| Part 01 §3.17, "an acquired array names none" | replace in place | same section | a writer names no run for an array that no recorded run produced, so an acquired array may name a recorded run that processed it | §3.3 |
| Part 01 §3.12, a stream may name a processing run | extend in place | same section | a stream naming no run says only that the packet names none, and a consumer does not read it as recorded off the device | §3.2 |
| Part 02 §9.2, the core registry version | revise in place | same section | the version advances | §3.5 |
| Part 08 §2 and Part 08 §3, the example packet's core registry version | revise the informative example in place | same sections | none | none |

## 2. Background

The observations below were made in the tracked files at the baseline, where the quick verifier
passes all 37 stages. §2.7 reports a scratch copy of `spec/`. The core registry artifact, Part 01,
Part 02 and Part 08 are byte-identical to those of `9c180d6c`, the commit this draft was first
appraised on, so the corpus measurement of §2.5, taken there, stands.

### 2.1 Three rules let a computed array carry a null

- Part 01 §2.4 makes a packet that carries no provenance conforming, and Part 05 §10 makes
  provenance a recommendation within packet conformance.
- Part 01 §3.17 requires a writer to name the run that produced an array only where the packet
  records that run and the writer knows which run it is.
- Part 06 §5 permits a writer to record a run for a materialization and does not require one.

Every array of `analysis.array_assets` is computed: Part 02 §2.2 defines the `analysis` content
class as products reproducible from canonical resources. In that table the description's second
sentence is therefore false of every null. The example packet's `unit_rates` is one such array: it
is computed, and its row names no run in a packet that records a materialization run.

The reference writer shows the same in core. Its adapters build `core.array_assets` rows for
local-field-potential series, for the mean and deviation waveforms of a sorting, and for acquired
streams. A search of the writer's and the AIND package's sources for `processing_run_id` finds it
set on rows of `core.sorting_runs`, `core.curation_versions` and `core.processing_runs` and on no
array or stream row, so a packet it builds carries a null on acquired and computed arrays alike.
R102 §5 measured as much when the column was added: 12 of 14 arrays in one packaged session and 10
of 11 in the other were computed by a run neither packet records.

### 2.2 A null leaves a consumer no other fact that says an array was acquired

| fact | what it states |
|---|---|
| `semantic_type` | An open label that Part 01 §3.17 makes optional and gives no contract. |
| `band` | Which band an array holds. Part 01 §3.17 calls a band value a shorthand for a filter the packet does not record, so it does not say whether an instrument or a computation applied the filter. |
| `device_id` | Which instrument the array came from, for an acquired and a computed array alike. |
| content class | Every `analysis` array is computed. A `core` array is either. |
| a run's scope | `core.processing_runs.scope_kind` may name `core.array_assets`, which says what the run is about and not that the run produced the row. |

No rule reads the column on an array or stream table. Of the rules in the core registry, those
whose text names `processing_run_id` belong to `core.preferred_runs` and `core.processing_runs`.

### 2.3 The reading is a meaning, which numbered prose owns

Part 00 §2.2 gives meanings to numbered prose and lets an incorporated artifact own only the
structures it is incorporated for. Part 02 §1 incorporates the registry for its exact declarations,
and Part 02 §3 forbids a description to contradict a machine declaration, which says nothing of a
description that disagrees with a part. The two descriptions disagree with the three rules of §2.1,
and no sentence of a part says what a null on the column means. A search of `spec/parts/` for
`acquired` finds four lines, of which one concerns an array: the clause of Part 01 §3.17 saying that
an acquired array names none.

A description is nonetheless where the registry tells a consumer what a null means. Of the 360
column descriptions in the core registry, 24 contain the word `null`, counted with a
case-insensitive whole-word search, and 6 contain "Null means".

### 2.4 Seven columns state a producing run, three of them falsely

Part 01 §3.12 lets a stream name a processing run and does not require one, and Part 01 §2.4
applies to a stream as it does to an array, so a stream detected offline in a packet recording no
provenance carries a null. R23 §5 lets a packet leave every `processing_run_id` null.

Seven tables of the core registry declare a nullable `processing_run_id`, each as an `int32`
assigned identifier referencing `core.processing_runs`:

| table | description at the baseline |
|---|---|
| `core.array_assets` | The run that produced this array. Null means it was acquired rather than computed. |
| `analysis.array_assets` | The run that produced this array. Null means it was acquired rather than computed. |
| `core.event_streams` | The run that produced it. Null means it came off the device as recorded. The manifest records outputs per resource and cannot distinguish streams within one table. |
| `core.sorting_runs` | The run that produced this record, where provenance is recorded. |
| `core.curation_versions` | The run that produced this record, where provenance is recorded. |
| `core.electrode_coordinates` | The run that produced this coordinate. |
| `core.unit_coordinates` | The run that produced this coordinate. |

The stream description's last sentence is also false. Part 04 §7 says that a manifest entry names no
producing run, and the manifest schema has no member recording a resource's outputs. The four
descriptions that read no null as acquisition still differ in form, and the two coordinate
descriptions say nothing of where the run is recorded, though Part 01 §3.8 has a coordinate name its
run only where the writer knows it.

### 2.5 A registry whose bytes change under one version blocks an amendment

Part 05 §15.3 has a writer refuse an amendment that would bind two different digests under one
registry ID and version anywhere in a packet's current and retained manifests. A core registry
whose descriptions change while its version stays `0.14.0` therefore cannot amend a packet built on
the earlier bytes, and a manifest does not show which reading its registry states. The generated
corpus holds 120 manifests, and all 120 bind `registries/core/0.14.0.json.gz` under one digest.

The history of `spec/artifacts/logical_schemas.json`, followed across its rename, holds 19 commits
from the one that first moved `registry_version` off `0.1.0`. Thirteen advance the version, from
`0.2.0` to the `0.14.0` that R152 §3.4 assigns. Five change the bytes and leave the version, and
none of the five changes the meaning a description states: one rewrote a cited section number in 15
descriptions, one corrected a rule's SQL, and three changed serialization, column order and SQL
layout. One moves the file.

### 2.6 Other open work advances the same version

At the baseline R159 is accepted, four other drafts are open and no proposal is. R159 amends only
Part 05. R160, accepted after this draft was revised, adds three declarations to the core registry
and takes the next core version, `0.15.0`. Two of the three other drafts change the core registry:

- `core-declares-a-clocks-transform-in-typed-columns-alone.md` removes one column of `core.clocks`;
  and
- `a-unit-is-identified-outside-its-packet-by-its-name.md` makes nine name columns `required` and
  advances the registry meta-schema and the registry-contract descriptor as well as the core
  version. It declares no rule.

The fourth, `a-recipe-accepts-a-discarded-value-by-naming-its-column.md`, changes the recipe schema.
None of them amends Part 01 §3.12 or Part 01 §3.17 or changes a declaration of a
`processing_run_id` column. The only shared text is the core version in Part 02 §9.2 and its
projections in Part 08 §2 and Part 08 §3. Once the sidecar catalog is incorporated, the core
registry holds 48 tables and its version is `0.15.0`, so this revision takes a later version than
the probe of §2.7 used, and §3.5 names no target.

### 2.7 The registry change builds and checks in a scratch copy

A copy of `spec/` at the baseline was edited as §3.4 and §3.5 state: the seven descriptions took
their new text, and the version was set to `0.15.0` in the registry source, in Part 02 §9.2, in the
specification README and in the two specification tools that state the expected version. The
registry build regenerated `logical_schemas.json` and the rendered table listing, and the registry
check passed, reporting 45 tables, 360 columns, 116 references and 91 rules. The regenerated
artifact holds the new sentence in seven descriptions and "acquired rather than computed" in none.
The framework check reported one failure, the combined specification being stale, which it was
because the probe did not regenerate it. No meta-schema, descriptor or rule differed from the tree.
The probe did not edit Part 01 or Part 08, regenerate the corpus or run a package suite.

### 2.8 Alternatives

Requiring a run on every computed array would make the old description true. A writer would then
record a run row for arrays whose source states no software, version or parameters, against
Part 01 §2.4, Part 05 §10 and Part 06 §5, and a writer that cannot tell whether its source computed
an array could not comply.

A column stating that an array was acquired would give a consumer the fact directly. R23 §1.1
rejected the same axis for events, because one detection is thresholded in hardware on one rig and
in software on another, and placed the fact in provenance. A band filter has the same boundary, and
the same boundary is why the Decision names no case a null may stand for: a list of acquired and
computed cases would rebuild the axis R23 §1.1 set aside.

Rewording the descriptions alone would leave the registry as the only statement of what a null
means, which Part 00 §2.2 gives to numbered prose.

## 3. Decision

The subsections state the reading for an array asset, the same reading for an event stream, the
writer's sentence on an array no recorded run produced, the seven descriptions, and the registry
version.

### 3.1 An array asset naming no producing run says the packet names none

An array asset that names no producing run states only that the packet names no run that produced
the array.

A consumer MUST NOT conclude from an array asset naming no producing run that the array was
acquired. A consumer that reports an array's producing run MUST report, for such an array, that the
packet names no producing run. A consumer that reports no array's producing run owes only the first
of these. No checker verifies either.

### 3.2 An event stream naming no processing run says the packet names none

An event stream that names no processing run states only that the packet names no run that produced
its events.

A consumer MUST NOT conclude from an event stream naming no processing run that its events came off
a device as recorded. A consumer that reports a stream's producing run MUST report, for such a
stream, that the packet names no producing run. A consumer that reports no stream's producing run
owes only the first of these. No checker verifies either.

### 3.3 A writer names no run for an array no recorded run produced

Where a packet records the processing run that produced an array and the writer knows which run
that is, the writer MUST name that run on the array asset, and it names no run for an array that no
run the packet records produced. No checker verifies this.

### 3.4 Seven descriptions state the reading

The core registry declares `processing_run_id` on the seven tables below with these descriptions.
Every other field of each column stands: type `int32`, presence `nullable`, role `identifier`,
identity `assigned`, and a reference to `core.processing_runs`.

| table | description |
|---|---|
| `core.array_assets` | The run that produced this array, where the packet records it. Null says only that the packet names no producing run. |
| `analysis.array_assets` | The run that produced this array, where the packet records it. Null says only that the packet names no producing run. |
| `core.event_streams` | The run that produced its events, where the packet records it. Null says only that the packet names no producing run. |
| `core.sorting_runs` | The run that produced this record, where the packet records it. Null says only that the packet names no producing run. |
| `core.curation_versions` | The run that produced this record, where the packet records it. Null says only that the packet names no producing run. |
| `core.electrode_coordinates` | The run that produced this coordinate, where the packet records it. Null says only that the packet names no producing run. |
| `core.unit_coordinates` | The run that produced this coordinate, where the packet records it. Null says only that the packet names no producing run. |

### 3.5 The core registry version advances

The core registry's `registry_version` MUST advance by one minor version from the version the
incorporated registry carries when this revision is incorporated. Other open work advances the same
identifier, so this revision fixes no order among them. This revision changes neither the registry
meta-schema, the registry-contract descriptor nor the rule language.

## 4. What this does not change

The writer's obligation of Part 01 §3.17 stands with both its conditions. A writer is not required
to record a run for a computed array or for a stream detected offline, and a packet that records no
provenance conforms as before. An array whose acquisition-time processing the packet records as a
run may name that run, as a stream may under Part 01 §3.12.

Core gains no fact stating that an array was acquired. Where the packet names no producing run, the
specification gives a consumer no way to learn it, for the reason §2.8 gives against a column.

Part 01 gains no reading for the four other columns. Their new descriptions state only that a null
names no run, which Part 01 §2.4 already implies, and their concepts invite no inference of
acquisition.

## 5. Consequence

No packet's rows change, and every existing packet conforms as it did. A packet binds the registry
it was built with, so an earlier packet embeds the earlier descriptions. A consumer reading only
that registry sees the old reading, and §3.1 and §3.2 bind it whatever that description says. A
packet built afterwards binds the new version at a new path with a new digest. The specification
README says that development packets are regenerated.

A consumer that treated a null as acquisition followed the registry's words before this revision
and departs from Part 01 afterwards. No reference package reads the column that way: the reference
reader uses the name only to resolve a preferred run.

Three limits follow from the Decision:

- §§3.1 and 3.2 forbid only the inference from a missing run. A consumer that concludes acquisition
  from other evidence, such as a source path under an NWB `acquisition` group, is outside them.
- A run whose `scope_kind` names `core.array_assets` and whose scope names an array is about that
  array and is not its producing run (§2.2). A consumer reporting that the packet names no
  producing run for that array, beside such a run, reports correctly.
- §3.3 is indicative where it says a writer names no run, since the reference of `processing_run_id`
  already lets a writer name only a run the packet records. Its effect is to remove the clause that
  barred an acquired array from naming one.

No accepted clause is superseded whole by §§3.1 to 3.4. Two ledger entries gain notes naming the
clauses that replace part of each, as R158 §3.2 requires of a clause replaced in part:

- R102 §3.1, `applied` at Part 01 §3.17, keeps its column and its writer obligation; its reading of
  a null is replaced by §3.1 and §3.4, and its clause on an acquired array by §3.3; and
- R23 §2, a `registry` entry, keeps its declaration; its reading of a null is replaced by §3.2 and
  §3.4.

The four other descriptions state what their declaring clauses already meant, so no other entry
gains a note for §3.4.

§3.5 replaces the version that the clause assigning the incorporated registry's version states. Where
that clause assigns only the version, as R160 §3.8 does, its entry becomes `superseded` by this revision, as
R151 §3.2's did. Where it also assigns other identifiers, as R152 §3.4 assigns the meta-schema and
the descriptor, its entry keeps its disposition and gains a note.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 01 §3.17 takes §3.1 beside the writer's obligation and §3.3 in place of its clause on an acquired array, and Part 01 §3.12 takes §3.2, each labelled as unchecked. | `evidence/R<N>.json` names the two anchors. |
| logical prose and registry | The seven descriptions of §3.4 change in the registry source, and the registry source and Part 02 §9.2 state the new version, as do the specification README and the two specification tools that state the version they expect. The meta-schema, the registry-contract descriptor, every other field of the seven columns and every rule are unchanged. | The registry build and check pass, and a guarded registry target names each of the seven columns. |
| physical profiles | Unchanged. No storage property is involved, and a bound registry is stored at the path its descriptor records (Part 03 §3.3). | None required. |
| packet manifest and JSON Schemas | Unchanged. A manifest built afterwards records a new version, path and digest in members the schema already has. | None required. |
| validation and import | Unchanged. No rule reads the column on any of the seven tables, and a validator cannot tell an acquired array from a computed one. | None required. |
| extensions | Unchanged. No extension registry in the repository declares the column, and an extension's version advances independently (Part 09 §5.5). | None required. |
| reader, writer, validator, adapters | No package carries a copy of the core registry, so none regenerates. One writer test asserts the bound core registry's version and path and takes the new values. No package reads a null run as acquisition, so no behaviour changes, and the reference adapters keep writing a null on every array and stream. The stream adapter's documentation repeats the old reading and is reworded. | The writer suite. |
| conformance fixtures and tests | The corpus regenerates under the new version and digest. No fixture is added, since no packet fact distinguishes the cases. | The corpus build and its expected findings pass unchanged. |
| revision process and tooling | The ordinary ledger and evidence records, the notes above, the version clause's entry as §5 states, and seven guarded registry targets. No process rule changes. | `ledger.py`, `evidence.py` and `verify.py` pass. |
| generated publications and developer documentation | The rendered table listing and the combined specification regenerate. The specification README's identifier table and its sentence naming the development version are edited by hand, and Part 08 §2 and Part 08 §3 carry the new registry path as the informative example. | The framework check compares the README's table with Part 02 §9.2, and the example-packet check compares Part 08's text with the packet the writer builds. |

## 6. Conformance and implementation evidence

§§3.1 and 3.3 are `applied` at Part 01 §3.17 and §3.2 at Part 01 §3.12, each by canonical anchor.
§3.4 is `registry`, with a target on each of the seven columns guarded by the column's name. §3.5 is
`applied` at Part 02 §9.2 by its canonical anchor. Part 08 §2 and Part 08 §3 follow §3.5 as the
informative example and are no ledger destination, as R152 §3.4's entry names none in Part 08.

No validator finding distinguishes the rule, and no packet is a negative case: a packet states
nothing that separates an acquired array from a computed one whose run is unrecorded, which is what
§3.1 says. The consumer's obligation is evidenced by the text of Part 01, and it binds no reference
package to a change, since none reports an array's or a stream's producing run.

These checks distinguish the incorporated state from the baseline:

- the registry artifact and the rendered table listing carry the seven descriptions of §3.4, and
  the phrase "acquired rather than computed" occurs in neither;
- the registry check, which asserts the core registry version, passes at the new version and fails
  at the version it replaces;
- the framework check finds the specification README's identifier table equal to Part 02 §9.2;
- the example-packet check finds Part 08 §2 and Part 08 §3 equal to the packet the writer builds;
- the writer test asserting the bound core registry's version and path passes at the new values;
  and
- every manifest of the regenerated corpus binds the core registry at the new version under one
  digest.

The scratch probe of §2.7 establishes that the registry change builds and passes the registry check
with no change to a meta-schema, descriptor or rule.

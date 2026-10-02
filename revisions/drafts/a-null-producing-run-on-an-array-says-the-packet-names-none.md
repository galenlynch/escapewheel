# A null producing run says the packet names none

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `9c180d6c919ce2942271a92f9df28f3bb230c185` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 01 §3.12; Part 01 §3.17; Part 02 §9.2; Part 08 §2; Part 08 §3; the core registry |
| **Depends on** | R102 §3.1 (the column on both array tables and the writer's obligation, whose reading of a null this replaces); R23 §2 (the column on `core.event_streams`, whose reading of a null this replaces); R152 §3.4 (the core registry version at the baseline) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

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
computed array for an acquired one.

This revision has Part 01 state what a missing producing run says and what a consumer may conclude
from it, rewrites the three descriptions to follow, and advances the core registry version, since
the registry's bytes change.

The change is structural because it revises existing sections in place: Part 01 §3.17 and
Part 01 §3.12 each gain the reading beside the sentence it qualifies, and Part 02 §9.2, Part 08 §2
and Part 08 §3 restate the version. An appended section would leave Part 01 §3.17 saying "an
acquired array names none" with the reading of that sentence elsewhere.

### 1.1 Structural crosswalk

Every amended section already carries a canonical anchor, so no bootstrap is needed. No section
moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 01 §3.17, a writer names the run that produced an array where the packet records it | extend in place | same section | an array asset naming no run says the packet names none, and a consumer does not read it as acquisition | §3.1 |
| Part 01 §3.12, a stream may name a processing run | extend in place | same section | a stream naming no run says the packet names none, and a consumer does not read it as recorded off the device | §3.2 |
| Part 02 §9.2, the core registry version | revise in place | same section | the version advances | §3.4 |
| Part 08 §2 and Part 08 §3, the example packet's core registry version | revise in place | same sections | the version advances | §3.4 |

## 2. Background

The observations below were made in the tracked files at the baseline, where the quick verifier
passes all 37 stages. The corpus count of §2.5 is taken from the corpus the verifier generates, and
§2.7 reports a scratch copy of `spec/`.

### 2.1 Three rules let a computed array carry a null

- Part 01 §2.4 makes a packet that carries no provenance conforming, and Part 05 §10 makes
  provenance a recommendation within packet conformance.
- Part 01 §3.17 requires a writer to name the run that produced an array only where the packet
  records that run and the writer knows which run it is.
- Part 06 §5 permits a writer to record a run for a materialization and does not require one.

Every array of `analysis.array_assets` is computed: Part 02 §2.2 defines the `analysis` content
class as products reproducible from canonical resources. In that table the description's second
sentence is therefore false of every null.

The reference writer shows the same in core. Its adapters build `core.array_assets` rows for
local-field-potential series, for the mean and deviation waveforms of a sorting, and for acquired
streams, and a search of the writer's and the AIND package's sources for `processing_run_id` finds
it set on no array row. A packet it builds carries a null on acquired and computed arrays alike.
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

No rule reads the column on an array or stream table. Of the rules in `spec/source/core/`, those
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
column descriptions in `spec/source/core/`, 24 contain the word `null`, counted with a
case-insensitive whole-word search, and 6 contain "Null means".

### 2.4 The stream column makes the same claim

Part 01 §3.12 lets a stream name a processing run and does not require one, and Part 01 §2.4
applies to a stream as it does to an array, so a stream detected offline in a packet recording no
provenance carries a null. R23 §5 lets a packet leave every `processing_run_id` null.

Seven tables of the core registry declare a nullable `processing_run_id`. The descriptions in
`core.sorting_runs` and `core.curation_versions` end "where provenance is recorded", and those in
`core.electrode_coordinates` and `core.unit_coordinates` say nothing of a null. The two array tables
and the stream table are the three that read a null as acquisition.

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

At the baseline two drafts and three other proposals are open. Three of the five change the core
registry: `core-declares-a-catalog-of-sidecars.md` adds three declarations,
`core-declares-a-clocks-transform-in-typed-columns-alone.md` removes one column of `core.clocks`,
and `a-unit-is-identified-outside-its-packet-by-its-name.md` changes name columns and adds rules.
None of the five amends Part 01 §3.12 or Part 01 §3.17, and none changes a declaration of
`core.array_assets`, `analysis.array_assets` or `core.event_streams`. The only shared text is the
version in Part 02 §9.2, Part 08 §2 and Part 08 §3.

### 2.7 The registry change builds and checks in a scratch copy

A copy of `spec/` at the baseline was edited as §3.3 and §3.4 state: the three descriptions took
their new text, and the version was set to `0.15.0` in the registry source, in Part 02 §9.2 and in
the two specification tools that state the expected version. The registry build regenerated
`logical_schemas.json` and the rendered table listing, and the registry check passed, reporting 45
tables, 360 columns, 116 references and 91 rules. The framework check reported two failures, both
following from the version: the specification README's identifier table disagreed with
Part 02 §9.2, and the combined specification was stale. No meta-schema, descriptor or rule
differed from the tree. The probe did not edit Part 01 or Part 08, regenerate the corpus or run a
package suite.

### 2.8 Alternatives

Requiring a run on every computed array would make the old description true. A writer would then
record a run row for arrays whose source states no software, version or parameters, against
Part 01 §2.4, Part 05 §10 and Part 06 §5, and a writer that cannot tell whether its source computed
an array could not comply.

A column stating that an array was acquired would give a consumer the fact directly. R23 §1.1
rejected the same axis for events, because one detection is thresholded in hardware on one rig and
in software on another, and placed the fact in provenance. A band filter has the same boundary.

Rewording the descriptions alone would leave the registry as the only statement of what a null
means, which Part 00 §2.2 gives to numbered prose.

## 3. Decision

The subsections state the reading for an array asset, the same reading for an event stream, the
three descriptions, and the registry version.

### 3.1 An array asset naming no producing run says the packet names none

An array asset that names no producing run states that the packet names no run that produced the
array, and states nothing more. The array may be acquired, may be computed by a run the packet does
not record, or may be computed by a run the writer could not identify.

A consumer MUST NOT conclude from an array asset naming no producing run that the array was
acquired, and where it reports the array's producing run it MUST report that run as unrecorded. No
checker verifies this.

### 3.2 An event stream naming no processing run says the packet names none

An event stream that names no processing run states that the packet names no run that produced its
events, and states nothing more. The events may have come off a device as recorded, or may have
been detected by a run the packet does not record.

A consumer MUST NOT conclude from an event stream naming no processing run that its events came off
a device as recorded, and where it reports the stream's producing run it MUST report that run as
unrecorded. No checker verifies this.

### 3.3 Three descriptions state the reading

The core registry declares `processing_run_id` on the three tables below with these descriptions.
Every other field of each column stands: type `int32`, presence `nullable`, role `identifier`,
identity `assigned`, and a reference to `core.processing_runs`.

| table | description |
|---|---|
| `core.array_assets` | The run that produced this array, where the packet records it. Null says the packet names no producing run: the array may be acquired, or computed by a run the packet does not record. |
| `analysis.array_assets` | The run that produced this array, where the packet records it. Null says the packet names no producing run. |
| `core.event_streams` | The run that produced it, where the packet records it. Null says the packet names no producing run: the events may have come off the device as recorded, or been detected by a run the packet does not record. The manifest records outputs per resource and cannot distinguish streams within one table. |

### 3.4 The core registry version advances

The core registry's `registry_version` MUST advance by one minor version from the version the
incorporated registry carries when this revision is incorporated. At the baseline that version is
`0.14.0`, which R152 §3.4 assigns. Other open work advances the same identifier, so this revision
takes the next free version at incorporation and fixes no order among them. The registry
meta-schema, the registry-contract descriptor and the rule language are unchanged.

## 4. What this does not change

The writer's obligation of Part 01 §3.17 stands with both its conditions, and its clause that an
acquired array names none stays, as a statement about a writer. A writer is not required to record a
run for a computed array or for a stream detected offline, and a packet that records no provenance
conforms as before.

Core gains no fact stating that an array was acquired. Where the packet names no producing run, the
specification gives a consumer no way to learn it, for the reason §2.8 gives against a column.

The four other nullable `processing_run_id` columns keep their descriptions, none of which reads a
null as acquisition.

## 5. Consequence

No packet's rows change, and every existing packet conforms as it did. A packet binds the registry
it was built with, so an earlier packet embeds the earlier descriptions, and a consumer reading one
applies §3.1 and §3.2 whatever that description says. A packet built afterwards binds the new
version at a new path with a new digest. The specification README says that development packets
are regenerated.

A consumer that treated a null as acquisition followed the registry's words before this revision
and departs from Part 01 afterwards. No reference package reads the column that way: the reference
reader uses the name only to resolve a preferred run.

No accepted clause is superseded. Three ledger entries gain notes naming the clause that replaces
part of each, as R158 §3.2 requires of a clause replaced in part:

- R102 §3.1, `applied` at Part 01 §3.17, keeps its column and its writer obligation, and its
  reading of a null is replaced by §3.1 and §3.3;
- R23 §2, a `registry` entry, keeps its declaration, and its reading of a null is replaced by §3.2
  and §3.3; and
- the clause assigning the version the registry carries at incorporation, which at the baseline is
  R152 §3.4, keeps its disposition for the meta-schema and descriptor it also assigns, and its
  version is replaced by §3.4.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 01 §3.17 takes §3.1 beside the writer's obligation, and Part 01 §3.12 takes §3.2, each labelled as unchecked. | `evidence/R<N>.json` names the two anchors. |
| logical prose and registry | The three descriptions of §3.3 change in the registry source, and the registry source and Part 02 §9.2 state the new version, as do the two specification tools that state the version they expect. The meta-schema, the registry-contract descriptor, every other field of the three columns and every rule are unchanged. | The registry build and check pass, and a guarded registry target names each of the three columns. |
| physical profiles | Unchanged. No storage property is involved, and a bound registry is stored at the path its descriptor records (Part 03 §3.3). | None required. |
| packet manifest and JSON Schemas | Unchanged. A manifest built afterwards records a new version, path and digest in members the schema already has. | None required. |
| validation and import | Unchanged. No rule reads the column on an array or stream table, and a validator cannot tell an acquired array from a computed one. | None required. |
| extensions | Unchanged. No extension registry in the repository declares the column, and an extension's version advances independently (Part 09 §5.5). | None required. |
| reader, writer, validator, adapters | No package carries a copy of the core registry, so none regenerates. One writer test asserts the bound core registry's version and path and takes the new values. No package reads a null run as acquisition, so no behaviour changes, and the reference adapters keep writing a null. The stream adapter's documentation repeats the old reading and is reworded. | The writer suite. |
| conformance fixtures and tests | The corpus regenerates under the new version and digest. No fixture is added, since no packet fact distinguishes the cases. | The corpus build and its expected findings pass unchanged. |
| revision process and tooling | The ordinary ledger and evidence records, the three notes above, and three guarded registry targets. No process rule changes. | `ledger.py`, `evidence.py` and `verify.py` pass. |
| generated publications and developer documentation | The rendered table listing and the combined specification regenerate. The specification README's identifier table and its sentence naming the development version are edited by hand, and Part 08 §2 and Part 08 §3 carry the new registry path. | The framework check compares the README's table with Part 02 §9.2, and the example-packet check compares Part 08's text with the packet the writer builds. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at Part 01 §3.17 and §3.2 at Part 01 §3.12, each by canonical anchor. §3.3 is
`registry`, with a guarded target on each of the three columns. §3.4 is `applied` at Part 02 §9.2,
Part 08 §2 and Part 08 §3, each by canonical anchor.

No validator finding distinguishes the rule, and no packet is a negative case: a packet states
nothing that separates an acquired array from a computed one whose run is unrecorded, which is what
§3.1 says. The consumer's obligation is evidenced by the text of Part 01, and it binds no reference
package to a change, since none reports an array's or a stream's producing run.

These checks distinguish the incorporated state from the baseline:

- the registry artifact and the rendered table listing carry the three descriptions of §3.3, and
  the phrase "acquired rather than computed" occurs in neither;
- the registry check, which asserts the core registry version, passes at the new version and fails
  at `0.14.0`;
- the framework check finds the specification README's identifier table equal to Part 02 §9.2;
- the example-packet check finds Part 08 §2 and Part 08 §3 equal to the packet the writer builds;
- the writer test asserting the bound core registry's version and path passes at the new values;
  and
- every manifest of the regenerated corpus binds the core registry at the new version under one
  digest.

The scratch probe of §2.7 establishes that the registry change builds and passes the registry check
with no change to a meta-schema, descriptor or rule.

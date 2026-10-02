# A null producing run on an array says the packet names none

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-02 |
| **Based on** | `e60b54e064d98c4479cf58dc18ba831fdfa75ea4` |
| **Decision domain** | specification |
| **Affects** | Part 01 §3.17's sentence on an array's producing run; the description of `processing_run_id` in `core.array_assets` and `analysis.array_assets`; the core registry version in Part 02 §9.2; possibly Part 01 §3.12 and the description of `core.event_streams.processing_run_id` |

## 1. Problem

`core.array_assets` and `analysis.array_assets` are the two catalog tables whose rows describe a
packet's dense arrays. Each declares a nullable `processing_run_id` referencing
`core.processing_runs`, and each gives it the description "The run that produced this array. Null
means it was acquired rather than computed."

The second sentence is false of conforming packets. A packet need record no provenance, so an array
that a run computed carries a null wherever the packet does not record that run. Every array of
`analysis.array_assets` is computed, by the definition of its content class. The packets the
reference writer builds carry a null on local-field-potential and mean-waveform arrays, which are
computed.

A consumer learns what the null means from the description alone. Part 01 §3.17 binds a writer to
name a run the packet records and says nothing of what a consumer concludes from a null, so a
consumer reading the registry a packet embeds takes a computed array for an acquired one.

## 2. Evidence

Observed in the tracked files at the baseline commit, where the quick verifier passes all 37 stages.
The reading of §2.6 is an inference from the parts it cites.

### 2.1 The description entered with the column and reads a null as acquisition

R102 §3.1 added the column to both tables. Its rule is that an array a run produced names that run
and that an acquired array declares none, "which is the reading R23 §2 gives a stream". The commit
that incorporated R102 wrote the description with that phrase, and the phrase has since been
removed. The description is the same string in `spec/source/core/core.array_assets.toml` and
`spec/source/core/analysis.array_assets.toml`.

The record contradicts the reading it adopts. R102 §5 measures that 12 of 14 arrays in one packaged
session and 10 of 11 in the other were computed by a run neither packet records, and says that each
"declares null until one does".

### 2.2 Three rules let a computed array carry a null

- Part 01 §2.4 makes a packet that carries no provenance conforming, and Part 05 §10 makes
  provenance a recommendation within packet conformance.
- Part 01 §3.17 requires a writer to name the run that produced an array only where the packet
  records that run and the writer knows which run it is. It adds that an acquired array names none
  and that no checker verifies the rule.
- Part 06 §5 permits a writer to record a run for a materialization and does not require one.
  R130 §3.7 removed the requirement and left the row-level columns unchanged.

A search of `spec/parts/` for `acquired` finds four lines. One concerns an array, the sentence of
Part 01 §3.17 above, and no part says what makes an array acquired.

### 2.3 No analysis array is acquired

Part 02 §2.2 defines the `analysis` content class as products reproducible from canonical
resources, and Part 06 §1 calls an analysis resource a derived product computed from canonical core
or extension resources. In `analysis.array_assets` the description's second sentence is therefore
false of every null. The generator of Part 08's example packet writes one row of that table,
`unit_rates`, a binned firing rate, and sets no run on it.

### 2.4 The reference writer's computed arrays carry a null

Three adapters of the reference writer build `core.array_assets` rows: one for series under an NWB
file's `processing/ecephys/LFP` group, one for the mean and deviation waveforms a sorting analyzer
computed, and one for the sampled streams under an NWB file's `acquisition` group. None of the
three sets `processing_run_id`. A search of the writer's and the AIND package's sources for
`processing_run_id` finds it set on rows of `core.processing_runs`, `core.processing_run_inputs`,
`core.preferred_runs`, `core.sorting_runs` and `core.curation_versions`, and on no array row.

A packet the reference writer builds therefore carries a null on its acquired streams, its computed
LFP series and its computed waveforms alike.

### 2.5 A null leaves a consumer no other fact that separates acquired from computed

| fact | what it states |
|---|---|
| `semantic_type` | An open label that Part 01 §3.17 makes optional, with absence the ordinary case, and gives no contract. |
| `band` | Which band an array holds. Part 01 §3.17 calls a band value a shorthand for a filter the packet does not record, so it does not say whether an instrument or a computation applied the filter. |
| `device_id` | Which instrument the array came from, for an acquired and a computed array alike. |
| content class | Every `analysis` array is computed (§2.3). A `core` array is either: both kinds of row in §2.4 are core. |
| lineage | Part 02 §2.7 makes `derived_from` optional on a core array instance, and a present value names packet resources only. An array computed from a recording the packet does not hold has nothing to name, and R130 §2.5 found the field on no core entry of four development packets. |
| a run's scope | `core.processing_runs.scope_kind` may name `core.array_assets`, and its description says what the run is about, which is no statement that the run produced the row. |

A non-null `processing_run_id` states that a run produced the array. Where it is null, a
`core.array_assets` row carries no declared fact that says whether the array was acquired.

No rule reads the column. A search of the `sql` of every rule in `spec/source/core/` for
`processing_run_id` finds it in rules of `core.preferred_runs` and `core.processing_runs` only, and
the reference reader uses the name only to resolve a preferred run.

### 2.6 No part says what standing a column description has

Part 02 §1 incorporates `artifacts/logical_schemas.json` for the exact resource declarations,
"including table columns, keys, references, vocabularies, and rules". Part 00 §2.2 gives meanings
to numbered prose and lets an incorporated artifact own only the structures or assignments it is
incorporated for. Part 02 §3 forbids a description to contradict or override a machine declaration,
which protects the declaration and says nothing of a description that disagrees with a part.
R126 §3.8 calls a contradiction in descriptive prose an authoring defect to be corrected, and no
part carries that sentence.

Part 04 §5.5 says of another incorporated artifact that the schema's descriptions are informative.
No part says so of a registry description.

A description is nonetheless where the registry states what a null means. Of the 360 column
descriptions in `spec/source/core/`, 24 contain the word `null`, counted with a case-insensitive
whole-word search, and 6 contain "Null means". The description is embedded in every packet and
covered by the digest the manifest records (Part 04 §8).

The inference: what a null says is a meaning, so Part 00 §2.2 gives it to Part 01. The description
is then a second statement of it, and it disagrees with the three rules listed in §2.2 of this
proposal.

### 2.7 The core registry version advanced with each of 13 revisions that changed it

The history of `spec/artifacts/logical_schemas.json`, followed across its rename, holds 19 commits
from the one that first moved `registry_version` off `0.1.0`. Thirteen change the version, each
incorporating an accepted revision, and they run from `0.2.0` to the `0.14.0` that R152 §3.4
assigns. One, incorporating R155, moves the file and changes no byte.

The other five change the bytes under the ordinary workflow and leave the version:

- `6c60f588` rewrote a section number cited in 15 name-column descriptions;
- `123ecb44` corrected the SQL of one rule;
- `12140953`, `88b9bb34` and `776dd637` changed serialization, column order and SQL layout.

No accepted revision in that range changed only a description of the core registry. R107 rewrote
35 descriptions while the version stood at `0.1.0`. R155 §5 changed the description of
`resources.schema.json` and records that this changes the schema's bytes and not its `$id`.

### 2.8 Two digests under one registry version block an amendment

Part 03 §3.3 stores a bound registry at its descriptor's path, which the example packet of Part 08
gives as `registries/core/0.14.0.json.gz`. Part 05 §15.3 has a writer refuse an amendment that would
bind two different digests under one registry ID and version anywhere in a packet's current and
retained manifests. A core registry whose bytes change while its version stays `0.14.0` therefore
cannot amend a packet built on the earlier bytes.

All 120 corpus manifests under `fixtures/packets/` bind `registries/core/0.14.0.json.gz` and record
its digest, counted by searching each `packet.json` for that path.

Part 02 §9.2 forbids reusing a development identifier for an incompatible contract, and no part
says whether a description belongs to that contract (§2.6).

### 2.9 The event stream column makes the same claim

`core.event_streams.processing_run_id` is described "The run that produced it. Null means it came
off the device as recorded." Part 01 §3.12 lets a stream name a processing run and does not require
one, and §2.2's first rule applies to a stream as it does to an array, so a stream detected offline
in a packet recording no provenance carries a null.

No reference packet shows the claim false. The one reference adapter that builds stream rows reads
an NWB file's `acquisition` group.

Seven tables of the core registry declare a nullable `processing_run_id`. The descriptions in
`core.sorting_runs` and `core.curation_versions` end "where provenance is recorded", and those in
`core.electrode_coordinates` and `core.unit_coordinates` say nothing of a null. The two array tables
and the stream table are the three that read a null as acquisition.

### 2.10 One open draft changes the core registry and names no version

`revisions/proposals/` holds no other proposal. Of the five open drafts, none amends Part 01 §3.17
or either array table, and a search of the five for `registry_version` finds no line.
`core-declares-a-catalog-of-sidecars` adds two declarations to the core registry, so its
incorporation changes the registry's bytes.

`core.clocks` still declares `transform_to_parent`, which the ledger's note on R3 §3.4 records as
replaced and still declared. A revision removing that column changes the same registry.

## 3. Desired outcome and constraints

A consumer reading a null `processing_run_id` on an array asset concludes what the packet supports
and nothing more, and one statement owns that reading. The resolution preserves:

- the column, its type, its presence and its reference in both tables;
- Part 01 §3.17's obligation on a writer, with its two conditions;
- the conformance of a packet that records no provenance (Part 01 §2.4, Part 05 §10) and of a
  materialization that records no run (Part 06 §5); and
- the rows of every packet the reference writer builds.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the description | A consumer takes a computed array for an acquired one, in every analysis row and in the LFP and waveform rows of §2.4. |
| require a run on every computed array | The description becomes true. A writer records a run row for arrays whose source states no software, version or parameters, against Part 01 §2.4, Part 05 §10 and Part 06 §5. A writer that cannot tell whether its source computed an array cannot comply, no validator can decide the rule, and the reference LFP and waveform adapters and their packets change. |
| add a column stating that an array was acquired | A consumer gets the fact directly. R23 §1.1 rejected the same axis for events, because one detection is thresholded in hardware on one rig and in software on another, and placed the fact in provenance. A band filter has the same boundary. |
| reword the description only | The registry stops stating the false reading. The description remains the only statement of what a null means, which Part 00 §2.2 gives to numbered prose. |
| Part 01 §3.17 states the reading and the description follows it (preferred direction) | One owner states the meaning, the registry restates it, and no packet's rows change. The core registry's bytes change. |

Under the preferred direction a null `processing_run_id` on an array asset says that the packet
names no producing run for the array. That covers an acquired array, a computed array whose run the
packet does not record, and a computed array whose run the writer could not identify.

Part 01 §3.17 states the reading beside the writer's obligation. A consumer does not conclude from a
null that an array was acquired, and reports the producing run as unrecorded, as Part 01 §3.18
has a consumer treat a media asset with no device. No checker can verify the rule, and the part
labels it so. The clause "an acquired array names none" stays, as a statement about a writer.

The description follows the part. The draft owns its wording. A candidate for `core.array_assets`
is "The run that produced this array, where the packet records it. Null says the packet names no
producing run, which an acquired array and a computed array whose run is unrecorded both show." The
description in `analysis.array_assets` drops the mention of acquisition, since no analysis array is
acquired (§2.3).

The specification then gives a consumer no way to learn that a core array was acquired (§2.5). The
direction states that plainly and adds no fact to fill the gap, for the reason the third option
fails.

The change is a revision. The scope section of `revisions/CONTRIBUTING.md` sends to the revision
process a change to what a consumer is permitted to do and to the contract an incorporated registry
carries. A consumer that treats a null as acquisition follows the registry's own words today and
would break Part 01 §3.17 afterwards, so an implementation that conforms before the change does not
conform after it. The citation rewrite of §2.7 left every description's meaning as it was, and this
change does not.

The core registry version advances, from `0.14.0` to the next value unassigned at acceptance.
Advancing keeps one digest for each version (§2.8), lets a consumer tell from a packet's manifest
which reading its embedded registry states, and follows the 13 revisions of §2.7. Question 1 asks
whether a description alone warrants it.

The version orders this change against any other that advances it. The revision accepted later
takes the value the earlier one assigns as its starting value, as R149 §3.4, R150 §3.10, R151 §3.2
and R152 §3.4 each did. This change shares no declaration with the removal of
`core.clocks.transform_to_parent` or with the sidecar declarations of §2.10, so the three are
independent in substance and each re-measures the version when another lands first.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Affected. Part 01 §3.17 gains the reading of a null and the consumer's rule, labelled as unchecked. Part 01 §3.12 gains the same if question 2 is answered that way. |
| logical prose, registry meta-schema, declarations and rules | Affected. The description of `processing_run_id` changes in `core.array_assets` and `analysis.array_assets`, and Part 02 §9.2 names the new core registry version. The meta-schema, the registry-contract descriptor, every other field of the two columns and every rule are unchanged. |
| physical profiles | Unchanged. No storage property is involved, and Part 03 §3.3's path follows the version. |
| packet manifest and other JSON Schemas | Unchanged. A manifest built afterwards records a new version, path and digest in members the schema already has. |
| validation and import | Unchanged. No rule reads the column on an array table, and a validator cannot tell an acquired array from a computed one. |
| extension registries | Unchanged. No extension registry under `extensions/` or `escapewheel-aind/extensions/` declares the column, and an extension's version advances independently (Part 09 §5.5). |
| reader, writer, validator, adapters, code generation | Each package's copy of the registry regenerates, and the writer test that asserts version `0.14.0` and its path changes. No package reads a null run on an array as acquisition, so no behaviour changes, and the three adapters of §2.4 keep writing a null. |
| existing packets | Unchanged in rows and in conformance. A packet binds the registry it was built with, so an earlier packet embeds the earlier description. The specification README says that development packets are regenerated. |
| conformance fixtures and implementation tests | The 120 corpus packets regenerate for the new version and digest. No fixture is added: no packet fact distinguishes the cases, so the consumer's rule is evidenced by the part's text and by the regenerated registry and table listing. |
| revision lifecycle, ledger, evidence and tooling | The ordinary ledger and evidence records, with a guarded registry target for each of the two columns. R102 §3.1 keeps its `applied` disposition at Part 01 §3.17, since its column and its writer obligation stand, and gains a note naming the clause that replaces its reading of a null. The ledger already records R101 §3.10 that way, with a note naming R139 §3.1. R152 §3.4 keeps its disposition for the meta-schema and descriptor it assigns and gains a note naming the clause that advances the version. |
| generated publications and developer documentation | The rendered table listing, the combined specification and the specification README's identifier table regenerate. Part 08's example shows the new registry path. |

## 6. Open questions

1. Whether the core registry version advances for a change to a description alone.
   - It advances (preferred). Each version keeps one digest, and an amendment across the change
     binds two versions and not two digests of one (§2.8).
   - It stays `0.14.0`, as in the five commits of §2.7. Two byte strings then carry `core`
     `0.14.0`, a packet built on the earlier one cannot be amended by a build binding the later,
     and a manifest does not show which reading its registry states.
2. Whether the same reading reaches `core.event_streams.processing_run_id` (§2.9).
   - It does (preferred). Every nullable `processing_run_id` then reads one way, Part 01 §3.12
     gains the consumer's rule, a third description changes, and the `registry` entry of R23 §2
     gains a note.
   - It does not. The stream's description keeps a claim that Part 01 §2.4 does not support, and
     one column name reads a null two ways.
3. Whether core gains a fact that states an array was acquired.
   - It does not (preferred). Section 4 gives the reason, and a consumer that needs the fact reads
     it as unrecorded.
   - It does. The decision becomes a new column or vocabulary on both array tables, a writer
     obligation with a source feasibility question for each adapter of §2.4, and a larger registry
     change that still advances the version.

Each answer fixes a Decision clause, so all three are needed before a draft is appraised.

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

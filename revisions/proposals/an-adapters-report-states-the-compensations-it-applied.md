# An adapter's report states the compensations it applied

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-01 |
| **Based on** | `0130e51d311e1f90ec0b48925f99a86d3bf579a2` |
| **Decision domain** | specification |
| **Affects** | Part 05 §4.3's sentence on a compensation; Part 12 §9's members of a run report |

## 1. Problem

A compensation is what an adapter does about a known defect in its source, including passing the
defect through on purpose. Part 05 §4.3 has an adapter declare each compensation and a writer record
every one applied in the import run's parameters, because a packet shows no other trace of a
correction.

An adapter reached by a protocol of Part 12 has no way to tell the build which compensations it
applied. A delivery carries tables, arrays, payloads and a resource document, and a run report
carries three members, none of them a compensation. The build therefore records none for such an
adapter, and one adapter reading one source yields a packet that records its corrections when it
runs in the writer's process and omits them when it is delivered.

## 2. Evidence

Observed in the tracked files at the baseline commit.

### 2.1 One sentence states the rule and no part gives it a channel

Part 05 §4.3 says that an adapter compensating for a known defect in its source declares the
compensation, that a writer records every compensation applied in the import run's parameters, and
that choosing not to correct a known defect is equally a compensation. A search of `spec/parts/` and
`spec/artifacts/` for "compensat" finds that sentence and nothing else. No part says what a
compensation consists of, how an adapter declares one, or what form the record takes.

### 2.2 Out of process is the default

Part 05 §3.9 has a build deliver a source out of process where its adapter declares a protocol,
unless the recipe says that it runs in the writer's process. Part 12 §3 requires an adapter released
independently of a build to declare a protocol. The path that cannot carry a compensation is
therefore the ordinary one for every adapter a build does not ship.

### 2.3 A delivery and a report have no member for one

Part 12 §5 lists what a delivery states: one table for each resource asked for, a packet-owned
array or payload as bytes at a location the build supplies, and a referenced resource as an entry
of a resource document. Part 12 §9 gives a report three optional members: `problems`, `read` and
`stated`. Part 12 §7's declaration document carries eight members, none of which names a
compensation.

### 2.4 Which compensations applied depends on the source read

A compensation is applied where the defect is met. An adapter that keeps a malformed offset it
finds on one field applies that compensation only to a source that carries the offset. A static
document cannot say which compensations a run applied, which is the reason Part 12 §7 gives for
carrying a source's stated values in the run's report and not in the declaration document.

### 2.5 The report already carries a fact an adapter owes

Part 12 §7 requires an adapter that declares a non-empty `states` to return the stated values, and
they travel under `stated` in the report. A build reads a declared field absent from the report as
unstated. Part 12 §9 forbids a build to require a report or to fail on a report's contents alone,
and requires it to report what one contains.

Part 12 §5 keeps the resource document out of the report for a stated reason: a fact a manifest
cannot be written without does not travel in a report. A manifest can be written without a
compensation, which is recorded in a row of `core.processing_runs`.

### 2.6 The reference build records a delivered adapter's compensations nowhere

The reference build keeps a registry of compensations, each an identifier with a defect, an action
and the evidence for the defect. It holds six: three for adapters the writer ships and three for
adapters shipped apart from it. An adapter in the writer's process names the identifiers it applied,
and the build writes each one's identifier, defect, action and evidence under `compensations` in the
import run's parameters.

The report the reference build's serving code composes for a delivered adapter carries `stated` and
`problems`, and the build reads `problems`, `read` and `stated` from a report. Nothing carries the
identifiers across, so the import run of a packet built from a delivered adapter records an empty
list.

An adapter written in another language, or installed where the build cannot import it, cannot add
to the build's registry, so an identifier alone would name a compensation the build cannot describe.

## 3. Desired outcome and constraints

An adapter reached by a protocol can state the compensations it applied, and the packet records
them as it records an in-process adapter's. The record does not depend on the build being able to
import the adapter. The resolution preserves:

- Part 05 §4.3's rule that every compensation applied is recorded;
- Part 12 §9's rules that a build requires no report and does not fail on a report's contents alone;
- the three protocols and their reserved resource identifiers (Part 12 §6); and
- the conformance of every existing packet and every existing adapter that applies no compensation.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the current rules | an adapter reached by a protocol cannot comply with Part 05 §4.3, and its packets omit the record |
| the declaration document lists an adapter's compensations | a static document says which compensations an adapter may apply and not which a run applied (§2.4); the schema is closed and requires all eight members, so it changes for every adapter |
| a reserved delivery resource carries them, as `resources` carries referenced resources | part of the delivery, so a build can refuse a malformed list; it reserves a second undotted identifier under `stream-v0.1`, adds a file under `files-v0.1` and a descriptor under `flight-v0.1`, and a schema for the document, for a list of a few strings |
| the report carries them under a new member (preferred direction) | follows `stated` (§2.5): an adapter that applied a compensation returns it in its report, and a build records what the report holds; one member is added to Part 12 §9 and no protocol changes |

Under the preferred direction a report gains an optional member, `compensations`, an array with one
entry for each compensation the run applied. An adapter that applied one returns it there, as an
adapter that declares `states` returns its values under `stated`. An absent or empty member says
that the run applied none.

**An entry describes itself.** It carries an identifier, the defect and the action as text, so a
build records it without knowing the adapter (§2.6). An identifier is a name the adapter's author
chooses, namespaced as a resource identifier is, so two adapters do not collide.

**A build records each entry it is given** in the import run's parameters, beside those of the
adapters in its own process, and reports each as it reports a problem. Part 05 §4.3 says what a
recorded compensation states: its identifier, the defect and the action. It keeps the rule that a
pass-through is a compensation.

**A build does not fail on the member.** Part 12 §9 stands: a report is not required, and a
malformed entry is reported and does not fail the build. A run whose report never appears records no
compensation, as it reports no problem and no stated value. That is the cost of this route against
the reserved resource, which could refuse. It is the cost Part 12 already accepts for a stated
value, and a compensation is the same kind of fact: something the adapter alone knows about its run
that the packet can be written without.

**Part 05 §4.3's "declare" is read as stating at run time.** The sentence gains the two channels:
an adapter in the writer's process states its compensations to the build directly, and an adapter
reached by a protocol states them in its report.

A delivered sync source's withheld-anchor result is a second fact that no delivery carries. It
concerns another source's rows and is a separate decision.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. A compensation is a fact about an import and no concept of Part 01. |
| logical prose, registry meta-schema, declarations and rules | Unchanged. `core.processing_runs.parameters` keeps its declaration, and no rule reads it for a compensation. |
| physical profiles | Unchanged. No storage property is involved. |
| packet manifest and other JSON Schemas | Unchanged. A report's shape is stated in Part 12 §9's prose and no schema; the adapter declaration and delivery schemas are untouched. |
| validation and import | Part 05 §4.3 says what a recorded compensation states and names the two channels. Part 12 §9 gains the `compensations` member and the build's duty to record it. No validator check is added: a validator cannot tell from a packet which compensations a run applied. |
| extension registries | Unchanged. |
| reader, writer, validator, adapters, code generation | The reference build's serving code writes the member and its reading code records it. An adapter the build ships is unchanged. An adapter released apart writes the member where it applies a compensation; one that applies none is unchanged. The reader and validator are unchanged. |
| existing packets | Unchanged in conformance. A packet built from a delivered adapter before the change lacks the record, and only a rebuild adds it. |
| conformance fixtures and implementation tests | No packet fixture, since no validator decides the rule. Build tests: a delivered adapter's compensation is recorded as an in-process one's is; a report without the member records none; a malformed entry is reported and does not fail the build. |
| revision lifecycle, ledger, evidence and tooling | The ordinary ledger and evidence records. A note on the accepted clause placed at Part 05 §4.3's sentence, if the draft finds one. |
| generated publications and developer documentation | The combined specification regenerates. The writer's adapter guide documents the member. |

## 6. Open questions

1. Whether an entry carries the evidence for its defect as a third text member. The reference build
   requires one of every registered compensation. Either answer leaves the direction unchanged.

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

# A delivery carries the compensations its adapter applied

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `9bcc3efe83da05c7ab192d1a16b56191dfe0c9a7` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 05 §4.3; Part 12 §§5 and 6 |
| **Depends on** | R111 §3.5 (the sentence on a compensation that this restates); R117 §3.2 (the reserved resource identifier `resources`, beside which this reserves another) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A compensation is what an adapter does about a known defect in its source, including leaving the
defect uncorrected on purpose. Part 05 §4.3 has an adapter declare each compensation and a writer
record every one applied in the import run's `parameters`, because a packet shows no other trace of
a correction.

No part says what a compensation consists of or how an adapter declares one. An adapter reached by
a protocol of Part 12 has no channel for it: a delivery carries tables, arrays, payloads and a
resource document, and a run report carries three members, none of them a compensation. Such an
adapter cannot comply, and its packets omit the record that the same adapter leaves when it runs in
the writer's process.

This revision says what a compensation states, binds an adapter to state each one it applies and a
writer to record what it is given, and carries a delivered adapter's compensations as a table of
the delivery under a reserved resource identifier.

The change is structural because it revises statements inside existing sections: Part 05 §4.3's
sentence on a compensation, Part 12 §5's list of what a delivery states, and Part 12 §6's statement
that two reserved values are the whole of what `stream-v0.1` adds to Arrow. An appended section
would leave that last statement false.

### 1.1 Structural crosswalk

Part 05 §4.3 and Part 12 §§5 and 6 already carry the canonical anchors `ew-import-normalization`,
`ew-referenced-resource-delivery` and `ew-arrow-ipc-floor`, so no anchor bootstrap was needed. No
section moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 05 §4.3, an adapter declares a compensation and a writer records every one applied | revise in place | same section | a compensation states an identifier, a defect and an action; an adapter states each one it applies, by the channel its way of running gives it; a writer records each one stated to it | §§3.1, 3.2 |
| Part 12 §5, what a delivery states | extend in place | same section | a delivery may carry a table of compensations, which a build records and may refuse | §3.3 |
| Part 12 §6, two reserved values of `resource_id` | revise in place | same section | `compensations` is a third reserved value, and no protocol is added or renamed | §3.4 |

## 2. Background

### 2.1 One sentence states the rule and no part gives it a channel

Part 05 §4.3 says that an adapter compensating for a known defect in its source declares the
compensation, that a writer records every compensation applied in the import run's parameters, and
that choosing not to correct a known defect is equally a compensation. A search of `spec/parts/` and
`spec/artifacts/` for "compensat" finds that sentence and nothing else.

### 2.2 Out of process is the default

Part 05 §3.9 has a build deliver a source out of process where its adapter declares a protocol,
unless the recipe says that it runs in the writer's process. Part 12 §3 requires an adapter released
independently of a build to declare a protocol. The path with no channel is therefore the ordinary
one for every adapter a build does not ship.

### 2.3 Which compensations applied depends on the source read

A compensation is applied where the defect is met: an adapter that keeps a malformed offset it finds
on one field applies that compensation only to a source that carries the offset. A static document
such as Part 12 §7's declaration cannot say which compensations a run applied.

### 2.4 A report is optional and a delivery is not

Part 12 §9 forbids a build to require a report or to fail on a report's contents alone, and has a
build treat a report it did not see appear as absent. A fact carried there is lost without a failure
where the report is not written. Part 12 §5 keeps the resource document for a referenced resource
out of the report for that reason and carries it in the delivery under the reserved resource
identifier `resources`.

### 2.5 A delivery already carries rows by one rule in every protocol

Part 12 §3 gives each protocol its way of carrying a table: a Parquet file named by the resource
identifier under `files-v0.1`, an Arrow IPC stream whose schema names the resource under
`stream-v0.1`, and a descriptor for each resource under `flight-v0.1`. The reference build receives
tables by listing the Parquet files, by reading each stream's `resource_id`, and by listing the
flights, so a table under one more name arrives under each protocol by the means already there.

A resource identifier is dotted, so Part 12 §6 reserves undotted values of `resource_id` without a
collision: `end` and `resources`.

### 2.6 The reference build records a delivered adapter's compensations nowhere

The reference build keeps a registry of compensations, each an identifier with a defect, an action
and the evidence for the defect. It holds six: three for adapters the writer ships and three for
adapters shipped apart from it. An adapter in the writer's process names the identifiers it applied,
and the build writes each one's identifier, defect, action and evidence under `compensations` in the
import run's parameters. Nothing carries the identifiers across a protocol, so the import run of a
packet built from a delivered adapter records an empty list.

An adapter written in another language, or installed where the build cannot import it, cannot add
to the build's registry. An identifier alone would then name a compensation the build cannot
describe, so what crosses has to describe itself.

### 2.7 Alternatives

A member of the run report would follow the `stated` member, which carries values an adapter owes,
and would change no protocol. A report is optional, so a record Part 05 §4.3 requires would ride on
a channel that loses it without a failure (§2.4).

A member of the declaration document would say which compensations an adapter may apply and not
which a run applied (§2.3).

A JSON document under a reserved identifier, as the resource document is carried, needs a schema and
travels as text in a single-row table under `stream-v0.1`, for what are already rows.

A second version of each protocol would keep `files-v0.1`, `stream-v0.1` and `flight-v0.1` free of
the table. Part 12 §3 makes a protocol that changes how rows cross a new member of its group. The
table crosses as every table does, so how rows cross is unchanged, and every build would have to
support both versions of each protocol for the sake of one optional table.

Requiring an empty table of an adapter that applied no compensation would let a build tell a run
that applied none from an adapter that states none. It would also make every existing adapter
non-conforming until it delivered one.

## 3. Decision

The subsections state what a compensation is, who states and records one, the table that carries a
delivered adapter's, and the reserved identifier.

### 3.1 A compensation states its identifier, its defect and its action

A compensation is what an adapter does about a known defect in its source. Leaving a known defect
uncorrected on purpose is a compensation.

A compensation states:

- an identifier, which is non-empty text that the adapter's author chooses;
- the defect, as non-empty text saying what is wrong at the source; and
- the action, as non-empty text saying what the adapter does about it.

A compensation MAY also state the evidence for the defect, as text.

Two compensations with one identifier and the same defect, action and evidence are one compensation.

### 3.2 An adapter states each compensation it applies, and a writer records it

An adapter MUST state to the build every compensation it applies in a run. An adapter that a build
runs in the writer's process states them by the means that build provides. An adapter reached by a
protocol (Part 12 §3) MUST state them in the table of §3.3. No build or validator can check that an
adapter stated every compensation it applied, so this rule binds the adapter alone.

A writer MUST record every compensation stated to it in the import run's `parameters`
(Part 05 §4.3), each with its identifier, its defect, its action, and its evidence where one is
stated. Where two compensations stated to it share an identifier and differ in any other text, a
writer MUST record both.

### 3.3 A delivery carries its compensations as a table

A delivery MAY carry one table under the reserved resource identifier `compensations` (§3.4), with
one row for each compensation the adapter applied. The table crosses as a table of the delivery
crosses under the protocol in use (Part 12 §3).

The table has these columns, each of a string type:

| column | presence | holds |
|---|---|---|
| `id` | required, and no row is null or empty | the compensation's identifier |
| `defect` | required, and no row is null or empty | the defect |
| `action` | required, and no row is null or empty | the action |
| `evidence` | the column may be absent, and a row may be null | the evidence for the defect |

An adapter that applied no compensation MAY deliver no such table, or an empty one. A build MUST
read an absent table, and an empty one, as a run that applied none.

A build MUST refuse a delivery, naming the source, whose `compensations` table lacks a required
column or holds a row that is null or empty in one. A build MUST NOT refuse the table for carrying
a column this section does not name.

The table is no resource of the packet. A build MUST NOT stage it, MUST NOT resolve a declaration
for it, and MUST NOT count it among the resources the recipe left the source owning
(Part 05 §4.4).

### 3.4 `compensations` is a reserved resource identifier

`compensations` is reserved as `end` and `resources` are (Part 12 §6): under `stream-v0.1` it is a
value of the `resource_id` key that names the table of §3.3 and no resource of a registry. An
adapter MUST NOT deliver anything else under it.

This revision adds no protocol to a group and renames none. `files-v0.1`, `stream-v0.1` and
`flight-v0.1` carry the table as they carry any other.

## 4. What this does not change

A run report keeps its three members and stays optional. A compensation does not travel in one, so
a build still fails on no report's contents.

The declaration document keeps its eight members: an adapter does not announce beforehand which
compensations it may apply.

## 5. Consequence

Every existing packet conforms unchanged, and no packet's shape changes: a compensation is recorded
in `core.processing_runs.parameters`, which no rule reads. A packet built earlier from a delivered
adapter lacks the record, and only a rebuild adds it.

An adapter that applies no compensation conforms unchanged. An adapter reached by a protocol that
applies one delivers the table from now on. A build written to the earlier text meets a table it has
no rule for; the specification that names the protocols has no release, so no such build is in
service.

A writer is now bound to what is stated to it and no longer to what was applied, which it could not
know. The obligation to state falls on the adapter and is unchecked (§3.2).

No accepted clause is superseded. Two ledger entries gain notes: R111 §3.5, placed at Part 05 §4.3,
that §§3.1 and 3.2 restate its sentence on a compensation; and R117 §3.2, placed at Part 12 §6, that
§3.4 reserves a third identifier beside its second.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. A compensation is a fact about an import and no concept of Part 01. | None required. |
| logical prose and registry | Unchanged. `core.processing_runs.parameters` keeps its declaration, and no rule reads it for a compensation. | None required. |
| physical profiles | Unchanged. No storage property is involved. | None required. |
| packet manifest and JSON Schemas | Unchanged. The table's columns are stated in Part 12 §5's prose, and no schema describes a delivery's tables. The adapter declaration schema and the delivery schema are untouched. | None required. |
| validation and import | Part 05 §4.3 takes §§3.1 and 3.2, Part 12 §5 takes §3.3, and Part 12 §6 takes §3.4. No validator check is added, since a packet does not show which compensations a run applied. | `evidence/R<N>.json` names the three anchors. |
| extensions | Unchanged. An extension declares no compensation. | None required. |
| reader, writer, validator, adapters | The reference build delivers the table when it serves an adapter out of process and records the rows it receives. An adapter it runs in process is unchanged. An adapter released apart delivers the table where it applies a compensation. The reader and validator are unchanged. | The writer suite's cases of §6, under each protocol. |
| conformance fixtures and tests | No packet fixture distinguishes the rule, since a validator cannot decide it. Build tests cover §6's cases. | The writer suite. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes on R111 §3.5 and R117 §3.2. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification regenerates. The writer's adapter guide documents the table. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1 and 3.2 are `applied` at Part 05 §4.3, §3.3 at Part 12 §5, and §3.4 at Part 12 §6, each by
canonical anchor.

No validator finding distinguishes the rule. These build cases do, each under `files-v0.1`,
`stream-v0.1` and `flight-v0.1`:

- an adapter that applies a compensation, delivered out of process, yields an import run whose
  `parameters` hold that compensation's identifier, defect and action, as the same adapter run in
  the writer's process does;
- a delivery with no `compensations` table, and one with an empty table, each record none;
- a table without an `evidence` column, and one with a null `evidence`, are each recorded;
- a table lacking `id`, `defect` or `action`, and one holding a null or an empty value in one of
  them, are each refused, naming the source;
- a table carrying a further column is recorded and not refused;
- two sources stating one identifier with different text yield two recorded compensations, and with
  the same text one; and
- the table is absent from the staged packet and from its manifest.

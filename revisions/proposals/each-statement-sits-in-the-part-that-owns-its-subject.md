# Each statement sits in the part that owns its subject

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-27 |
| **Based on** | `523685027ddbcf18b31e6891ada3034e09aac80f` |
| **Decision domain** | specification |
| **Affects** | Part 00 §§2.4, 3.2, 4.1–4.2, 5.2, 7.3 and 8; Part 01 §§2.1, 2.2, 3.8, 3.9, 3.17, 3.23 and 3.24; Part 02 §§8.2, 8.3, 8.6 and 10.3; Part 03 §9; Part 04 §5.3; Part 05 §§1, 3.4, 3.7, 4.3, 4.4, 5.3, 10, 13 and a new amendment section; Part 06 §§3, 4 and 6; Part 07 §§5–7; Part 08 §§1 and 5; Part 09 §5.7; Part 10 as a destination; `revisions/applied.toml` destinations for clauses placed in moved sections; citations in the writer, validator and reader |

## 1. Problem

Part 00 §9 assigns every numbered part a subject and forbids a part to state a second version of a
rule another part owns. R145 resolved the statements that disagreed with their owners. What remains
in the placement-defect inventory agrees with its owner, or has no other statement, but sits at the
wrong layer, where an editor changing the owner has no reason to look:

- **restatements** of a rule another part owns, which drift the next time the owner changes;
- **operational rules in the semantic and logical parts**: an importer's procedure in Part 01, a
  reader's and a validator's in Part 02;
- **profile-independent lifecycle in a profile**: Part 03 §9's amendment, revalidation and version
  rules bind only packets under the portable profile, though none depends on its storage;
- **evidence and history in normative text**: dataset counts, benchmark timings and records of v0.1
  withdrawals, several of them stale;
- **implementation planning** in Part 00 §8, Part 07 and Part 08; and
- **Part 05's actor boundary**, which Part 05 §10 draws late and Part 00 §2.4 misdescribes.

One further entry is a gap rather than a misplacement. R39 §§2.1–2.3 define a session's time origin
as the earliest observation start on the reference clock, and seconds from it through the reference
clock's rational rate. No part's prose states either, yet the reference validator fails a packet
that departs from the first, citing Part 01 §2.2, which does not state it.

## 2. Evidence

Observations are from the recorded baseline, whose quick verifier passes all 32 stages. The
maintenance commit that forms the baseline replaced three word-for-word restatements with
citations: Part 00 §7.1's serverless reading, Part 00 §7.2's external-resource statements and
Part 10 §3's row-group recommendation. It changes no rule.

### 2.1 Restatements

| entry | restating text | owner | observation |
|---|---|---|---|
| PD-007 | Part 00 §3.2's content-class table | Part 02 §2.2 | The same five rows and columns. |
| PD-007 | Part 00 §4.1's grain paragraph | Part 02 §11 | "One row per trial in `core.intervals`", where Part 02 §11.4 declares `core.intervals` as bounded spans of every kind. |
| PD-007 | Part 00 §4.2 | Part 01 §3.14 and the registry | The sole canonical spike representation, and the `core.units` summary columns the registry declares with the rule `core.units` carries. |
| PD-032 | Part 00 §5.2 | Part 06 §7 | Materialization is a realization, not a kind. |
| PD-009 | Part 00 §7.3's last paragraph and Part 03 §9.6 | none | Two versions of one rule: Part 00's binds every writer, Part 03's binds a writer "under a future lakehouse profile". |
| PD-011 | Part 01 §§3.8 and 3.24 | Part 02 §12.7 | A frame's values are one row per axis. |
| PD-012 | Part 02 §10.3's second sentence | Part 05 §5.3 | Why a storage check written as SQL fails silently. |
| PD-014 | Part 04 §5.3's last paragraph | Part 05 §14.3 | A reader needs no validation receipt; Part 04 adds the per-resource inspection a reader performs. |
| PD-031 | Part 05 §§3.4, 3.7 and 4.4 | Part 12 §§4, 5 and 7 | An adapter declares what it supplies; a build writes the supplied object to standard input and closes it; an owned resource arrives empty; which stream carries a failure under each protocol. R144 §7 left these for placement. |
| PD-019 | Part 09 §5.7 | Part 12 §§3 and 5 | `files-v0.1` "remains the route every implementation supports", where Part 12 §3 obliges a build to support every protocol of the group and an adapter one of them. |

### 2.2 Operational rules in Parts 01 and 02

Part 01 §3.9 obliges an importer to examine a source in acquisition order and not assume
monotonicity (PD-011). That is a writer's normalization procedure, which Part 05 §4.3 owns. The
same section's consumer rules, to report unmapped ticks and count those dropped, state what a
converted value means and stay.

Part 02 §8.3 says a reader should offer a discriminator's resolution, and Part 02 §8.6 says a
validator should report an unfilled `metadata` column at `info` (PD-012). Part 05 §13 owns reader
operations, and Part 05 §5.3 already states the comparable `columns_duplicated` report.

Part 01 §3.8 forbids a table to carry an atlas structure's full name or ancestry path as columns,
which is a constraint on declarations (PD-011). Part 01 §3.17 calls `semantic_type` "nullable",
Part 02's presence term, where the semantic statement is that a writer leaves it unfilled.

### 2.3 Amendment in the portable profile

Part 03 §9 holds the amendment rules (PD-013). Part 03 §1 makes the part normative only for a packet
declaring `escapewheel-portable-v0.1`, so a packet under any other profile has no amendment rule at
all. Most of Part 03 §9 depends on no storage property:

- what an amendment may change (Part 03 §9.2), and that its `packet_version` sorts after the one
  it supersedes (Part 03 §9.1);
- the refusal to bind two digests under one registry ID and version (Part 03 §9.3);
- that an amendment validates the whole packet and which checks a validator re-runs (Part 03 §9.4);
- cleanup's order, the protection of strays and the retention floors (Part 03 §9.5); and
- that `packet_version` versions the bundle (Part 03 §9.6).

What is the portable profile's is how an amendment is realized: a table that gains rows becomes a
new file, retained manifests live under `manifests/`, and a stray is a file under the packet root.

Outside accepted records, `revisions/impact.py` lists 55 live citations of Part 03 §9 and its
subsections: the writer's amendment, cleanup and verification code and its tests, the validator's
revalidation, and one each in Parts 04 and 05.

### 2.4 Part 05's actor boundary

Part 05 §1 opens "Validation is importation", a build rule. The part first says which actors it
binds in Part 05 §10, which defines a writer as conforming "when it satisfies this part" (PD-015).
The part also binds validators (Part 05 §§5 and 9) and readers (Part 05 §§13 and 14.3), so no
writer can satisfy all of it, and Part 00 §2.4 calls the writer "the actor Part 05 binds
throughout". The sections themselves already group by actor: the build's pipeline in Part 05 §§2–4
and 6–8, validation in Part 05 §§5 and 9, reader operations in Part 05 §13, and registry-document
boundaries for every actor in Part 05 §14.

### 2.5 Evidence and history

| entry | location | content | state |
|---|---|---|---|
| PD-029 | Part 01 §3.17 | `ElectricalSeries` on 22 of 25 arrays | recorded in R103 |
| PD-029 | Part 01 §3.23 | calibrations 133 and 302 days old | recorded in R89 |
| PD-029 | Part 01 §3.24 | 8,448 of 27,557 coordinate rows | recorded in R105 |
| PD-012 | Part 02 §8.2 | 16 name columns, 6 naming a kind; `registry/check.py` sorts them | `registry/check.py` now reports 16 and 10; the contract checks the name pairing as `registry.identity.name`, and only the script records which names name a kind |
| PD-012 | Part 02 §8.6 | 17 and 3 tables per `metadata` band; 286,896,563 unfilled rows; 1.9 kB and 394.6 ms; 20 keys; `registry/check.py` enforces the bands | a recount under the section's own definition gives 16 and 5; the contract checks the bands as `registry.metadata.eligibility` |
| PD-007 | Part 00 §4.2 | the v0.1 ragged representation and `canonical_representations` block are withdrawn | history |
| PD-016 | Part 06 §§3 and 4 | alignment timings, a 100.6% size ratio, a 708-row view, a ten-second window at 0.025 s against 7.7 s | performance evidence, which Part 10 owns |
| PD-016 | Part 06 §6 | four v0.1 resources withdrawn | history; its last sentence repeats Part 09 §3's placement of task-shaped columns |

### 2.6 Implementation planning

Part 00 §8 lists five components of "the first implementation", which Part 07 §2's distributions
no longer match (PD-010); its last sentence repeats Part 05 §1. Part 07 §5 is a phase-status table,
Part 07 §6 instructs developers when to run the corpus, and Part 07 §7 opens with a rule for where
a number belongs (PD-017). Part 08 §5 is a six-item conformance checklist beside Part 05 §10's definition, and
Part 08 §1 says the spike tables carry "four identifiers, a tick, and a clock per row" (PD-018).

### 2.7 The time origin (PD-030)

R39 §2.1 defines the origin as the earliest `start_tick` among the session's clocks' observation
intervals, expressed on the reference clock. R39 §2.2 adds that a packet declaring no observation
intervals declares no `t_zero_tick`, and R39 §2.3 derives seconds as `(t_tick - t_zero_tick)`
divided by the reference clock's rational rate, admitting negative values. The ledger places
R39 §§2.2–2.4 in Part 01 §2.2 and R39 §2.1 in the registry. Part 01 §2.2 states only that seconds
derive from the origin, that a consumer lacking one refuses, and that a writer unable to map a clock's start
declares none. The registry's `t_zero_tick` description names the earliest observed tick.

The reference validator reports `time.origin_not_earliest` at `error` where a declared
`t_zero_tick` differs from the mapped minimum by more than one reference-clock tick, and
`time.origin_unmappable` where a clock's start does not map. No part states either check or the
tolerance, so whether a packet passes depends on an implementation constant, and no test or corpus
fixture asserts either check.

## 3. Desired outcome and constraints

Each statement sits in the part that owns its subject, and every other part cites it. The
resolution should preserve:

- every packet's verdict and every registry document's bytes, so no identifier advances and no
  packet is rebuilt;
- the reference implementation's behavior, with citations repointed; and
- every accepted clause's destination, moved with its text where the text moves.

The time origin is the one item that adds normative prose. It states what R39 accepted and what the
validator enforces, so it changes no verdict either.

A move changes numbering, so the draft is structural and needs a crosswalk. Several affected
sections carry no anchor, so an anchor bootstrap will precede the draft.

## 4. Options and tradeoffs

### 4.1 Part 05's actor boundary

1. Rewrite Part 05 §1 as the part's scope: which actors it binds, and which sections bind each.
   Correct Part 05 §10's definition to the writer's obligations, and Part 00 §2.4's description.
   The build-order content of Part 05 §1 joins Part 05 §2. No section is renumbered.
2. Regroup Part 05 into actor-headed sections, renumbering most of it.

The preferred direction is option 1. The sections already group by actor, so option 2 would
renumber most of Part 05's fifteen sections, and every citation of them, to state a boundary one
scope section can state.

### 4.2 Amendment rules

1. Move Part 03 §9's profile-independent rules (§2.3) into a new Part 05 section on amendment, which
   then binds every profile. Part 03 §9 keeps the portable realization and cites Part 05.
   Part 00 §7.3's `packet_version` sentence and Part 03 §9.6 both give way to the Part 05 statement.
2. Keep Part 03 §9 where it is and say that another profile defines its own amendment rules.

The preferred direction is option 1. Part 00 §9 gives Part 05 the publication of a packet, and an
amendment is a publication. Only one profile exists, so widening the rules changes no packet,
writer or validator. Option 2 would leave a future profile free to let an amendment rewrite core,
which the portable profile forbids for a reason (Part 03 §9.2) that is not about storage.

### 4.3 Evidence and history

1. Delete dataset counts and history from normative text, since the accepted revisions that
   measured them keep them. Move the performance measurements of Part 06 §§3–4 into Part 10. Keep
   each rationale sentence without its number where the rule still needs it.
2. Move every measurement into Part 10.

The preferred direction is option 1. Part 10 §1 carries numbers that support a rule about bytes; a
count of one dataset's arrays or calibrations supports a decision already recorded. Several of the
counts are stale (§2.5), which is what leaving them costs.

### 4.4 The time origin

State R39 §§2.1–2.3 in Part 01 §2.2, and the validator's check in Part 05 §5.3. The open choice is
the tolerance:

1. one tick of the reference clock, which the reference validator applies;
2. exact equality; or
3. Part 01 §3.9's alignment tolerance.

The preferred direction is option 1. A writer's own estimator may fit anchors it does not record,
so the validator's mapping cannot reproduce the writer's exactly, and option 2 would fail a correct
origin on rounding. Option 3 is a percentile over an alignment, not a bound on one value.

### 4.5 Entries with one credible destination

| entry | preferred direction |
|---|---|
| PD-007 | Part 00 §3.2 names the classes and cites Part 02 §2.2 for the table; Part 00 §§4.1–4.2 give way to Part 02 §11, Part 01 §3.14 and the registry, and Part 00 §4.2 is retired. |
| PD-032 | Part 00 §5.2 is retired into Part 00 §5.1's citation of Part 06. |
| PD-010 | Part 00 §8 is retired; Part 07 §2 describes the distributions. |
| PD-011 | Part 01 §2.1 keeps the meaning of an assigned identifier's name and cites Part 02 §8.2 for the column; the axis rows and atlas-column restriction move to Part 02 §12.7 and the coordinate declarations; the importer procedure moves to Part 05 §4.3; Part 01 §3.17 says unfilled rather than nullable. |
| PD-012 | Part 02 §8.3's reader rule moves to Part 05 §13 and Part 02 §8.6's validator report to Part 05 §5.3; Part 02 §§8.2 and 8.6 cite the registry-document contract rather than a script. |
| PD-014 | Part 04 §5.3's reader paragraph moves to Part 05 §14.3. |
| PD-017 | Part 07 §5's phase table and Part 07 §6's instruction are removed, and Part 07 §7 opens descriptively. |
| PD-018 | Part 08 §5 is replaced by a citation of Part 05 §10, and Part 08 §1 names the spike tables' columns. |
| PD-019 | Part 09 §5.7 cites Part 12 §§3 and 5 in place of its restatement. |
| PD-031 | Part 05 §§3.4, 3.7 and 4.4 keep what a build does with an adapter's declarations and delivery, and cite Part 12 for what the adapter declares and what each protocol carries. |

Part 09 §5.7's determinism rule for an extension's command stays: moving it to Part 12 would extend
it to every adapter, which is a contract change outside placement.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | affected: Part 01 §§2.1, 2.2, 3.8, 3.9, 3.17, 3.23 and 3.24 |
| logical prose | affected: Part 02 §§8.2, 8.3, 8.6, 10.3 and 12.7 |
| registry meta-schema, declarations and rules | unchanged: no declaration moves, and the `t_zero_tick` description already names the earliest tick |
| physical profiles | affected: Part 03 §9 keeps the portable realization only; descriptor unchanged |
| packet manifest and other schemas | unchanged; Part 04 §5.3 loses a reader paragraph |
| validation and import | affected: Part 05 gains a scope section, an amendment section, the time-origin check and the moved reader and validator rules |
| extension registries | unchanged |
| reader, writer, validator, adapters | citations only; the validator's time-origin messages cite the new statements |
| existing packets | unchanged; no verdict changes and no rebuild |
| conformance fixtures and tests | affected: the corpus and the validator's tests have no case of a wrong or an unmappable origin, and the draft names one of each; nothing else changes behavior |
| architecture, analysis and informative prose | affected: Part 00 §§2.4, 3.2, 4, 5.2, 7.3 and 8; Part 06 §§3, 4 and 6; Parts 07, 08 and 10 |
| revision tooling and ledger | affected: destinations for clauses placed in moved or retired sections; R39 §§2.1–2.4 gain prose destinations; an anchor bootstrap before the draft |
| generated publications and documentation | the single-file rendering, headings record and root facts; the placement-defect inventory closes the entries above |

## 6. Open questions

1. **Does Part 05 state its actors in a scope section, without renumbering?** Resolved
   2026-09-27: yes (§4.1, option 1).
2. **Do the profile-independent amendment rules move to Part 05 and bind every profile?**
   Resolved 2026-09-27: yes (§4.2, option 1).
3. **Are dataset counts and history deleted, and benchmarks moved to Part 10?** Resolved
   2026-09-27: yes (§4.3, option 1).
4. **Is a declared origin checked to within one reference-clock tick?** Resolved 2026-09-27: yes
   (§4.4, option 1).

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

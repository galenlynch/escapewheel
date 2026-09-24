# A Packet Passes Only When Its Manifest, Core, and Every Bound Extension Pass

| | |
|---|---|
| **Status** | **Accepted** 2026-09-23 |
| **Based on** | `0b82c8a9b981990ce9f1486263abef44b13974f6` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §4.1; Part 04 §§9 and 10; Part 05 §§5.3, 5.4, 9.2, 10, and 14.5, and a new section 9.5; Part 09 §5.4 |
| **Depends on** | [R130 §§3.6 and 3.9](../accepted/R130-a-packet-binds-the-exact-registries-that-declare-its-resources.md#3-decision); [R131 §3.3](../accepted/R131-a-validator-checks-every-unit-value-against-ucum.md#3-decision) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6 |

Section 3 is normative. Sections 1, 2, and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A packet binds one core registry and any number of extension registries.
[Part 09 §5.4](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-verdicts)
reports a verdict for core and for each extension separately, and makes the packet's verdict the
conjunction of them all. The specification defines no part of that conjunction: no clause assigns a
finding to core, to an extension, or to neither; gives a verdict to a subject whose evaluation was
incomplete or withheld; names the checks an extension's resources receive; or says what a report or
a writer does with the result.
[Part 05 §14.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validator-registry-boundary)
records the gap, leaving extension-table byte validation and the final composition of core,
extension, and packet verdicts undefined.

This revision defines three verdict states, assigns every finding to one subject, extends every
packet check to an extension's resources, gates publication on the packet verdict, and states what a
report carries. Part 05 §9 already owns findings, the error policy, and incomplete validation, so
verdict composition joins it as a new section 9.5, "Verdicts"; Part 09 §5.4 keeps only the extension-specific
separation and the consumer rule.

The change is structural because it replaces rules inside existing sections: Part 05 §5.4's
separate-verdict sentence, Part 05 §9.2's commit rule, Part 09 §5.4's composition, and the
sentences in Part 00 §4.1, Part 04 §10, and Part 05 §§5.3, 10, and 14.5 that state or defer the old
rule. Appending sections would leave each of them contradicting its replacement.

### 1.1 Structural crosswalk

Commit `0b82c8a` added the canonical anchors `ew-validation-extensions` and `ew-error-policy` to Part
05 §§5.4 and 9.2 and changed nothing else. Every other affected section was already anchored, and
the planned Part 05 section 9.5 receives `ew-verdict-composition` when it is created.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 00 §4.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-core-content-requirements), a writer validates core resources before committing them | replace the obligation with a citation | Part 05 §9.2 | the obligation covers every packet resource and is stated once | §3.4 |
| [Part 04 §9](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-validation-block), validation block | extend in place with a citation | Part 05 §9.2 | states that Part 05 §9.2 permits only `passed` in a published manifest's `status` | §3.4 |
| [Part 04 §10](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-manifest-conformance), Part 09 §5.4 attributes an extension's findings and composes the verdicts; a writer publishes no manifest with an early-phase finding | replace the first sentence; add a citation to the second | Part 05 §9.2 and planned section 9.5 | no rule changes here; the owners move | §§3.2, 3.4 |
| [Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim), the unit-code check covers core's tables and its finding is core's | replace in place | same section | the check covers every registry directing packet checks, and its finding belongs to the declaring registry | §3.3 |
| [Part 05 §5.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-extensions), each extension is validated on core's terms with its verdict reported separately | replace in place | same section; separation moves to planned Part 05 section 9.5 | every check core's resources receive reaches an extension's | §3.3 |
| [Part 05 §9.2](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-error-policy), an import refuses to commit on any error | replace the first sentence | same section | a writer publishes a manifest, first or later version, only for a `passed` packet, and records that verdict | §3.4 |
| no current section composes verdicts | add | planned Part 05 section 9.5, "Verdicts", `ew-verdict-composition` | verdict states, finding subjects, conjunction, and report content | §§3.1, 3.2, 3.5 |
| [Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes), Part 09 §5.4 defines how verdicts compose | replace the citation | planned Part 05 section 9.5 | no rule changes here | §3.1 |
| [Part 05 §14.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validator-registry-boundary), extension-table byte validation and verdict composition are not defined here | replace with citations | Part 05 §5.4 and planned section 9.5 | the deferred subjects are decided | §§3.1, 3.3 |
| [Part 09 §5.4](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-verdicts), separate verdicts and their conjunction | replace in place | same section, citing planned Part 05 section 9.5 | the separation and the consumer rule stay; composition and incomplete evaluation move | §3.6 |
| [Specification README §2](../../escapewheel_poc_docs_v0.2/README.md#2-authority-and-conformance), extension independence and verdict composition are defined by Part 09 | revise the informative pointer | README | none | §3.6 |

## 2. Background

Section 2 is informative. The observations were reproduced at `d9b6686`, whose full repository
verifier passed all 35 stages, and are unchanged at the recorded baseline, which adds only anchors.

### 2.1 The reported status counts only core's findings

`Report.passed` in `escapewheel-validator` counts error-level findings that carry no extension, and
`Report.to_dict` writes that value as the report's top-level `status`. A packet whose extension
table `task.trials` holds a value outside its closed vocabulary validates to `"status": "passed"`
with `"errors": 1`; the one error is `task.trials.choice.in_vocabulary`, attributed in memory to
extension `task`. The serialized findings carry only `level`, `check`, `message`, and `rows`, so the
JSON loses that attribution. Two validator tests assert the core-only verdict:
`test_an_extension_finding_does_not_fail_core` and
`test_validator_preserves_an_available_unparseable_extension_result`.

### 2.2 The writer publishes on core's verdict

A first commit and an amendment in `escapewheel-writer/src/escapewheel_writer/writer.py` each refuse
only when `report.passed` is false, and each writes the manifest's `validation.status` from that
value. The validator command line exits 0 on it. A build whose extension fails therefore publishes a
packet recorded as `passed`, although Part 05 §9.2 requires an import to refuse to commit on any
error. The writer records `not_run` only in the staging manifest it writes before validation.

### 2.3 Extension tables receive only generated and declared queries

The validator's column-presence and type check, physical-order scan, functional-dependence
duplication check, unfilled-`metadata` check, reserved-value check, and unit-code check each iterate
the core registry's tables. An extension table receives its generated Tier 1 queries and its
declared Tier 2 rules and nothing else, although
[Part 09 §5.1](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-definition)
gives an extension's declarations the same applicable terms as core's.

A probe ran the same six checks over the union of core and extension tables. It reported one new
defect, the validator's own extension fixture writing `task.trials.session_id` as `int64` against a
declared `int32`, which failed the two validator tests that build that fixture. The writer's 565
tests, the 66 tests of the AIND extension package, and all 29 packets of the conformance corpus,
whose valid packet carries the `dynamic_foraging` extension, behaved as before.

### 2.4 An extension's array and file defects fail core

Findings from dense-array metadata checks, owned-digest checks, and missing-file checks carry no
extension, whichever registry declares the resource they concern. A defect in an extension's array
therefore counts against core's verdict, which Part 09 §5.4 forbids.

### 2.5 Incomplete evaluation and failure share one Boolean

An incomplete Tier 2 evaluation makes `Report.passed` false exactly as an error does.
[Part 05 §9.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-incomplete-validation)
requires a report to distinguish the two, and the report does so only in a separate list of rule
evaluations, never in a verdict.

### 2.6 Alternatives

Two verdict values would force an incomplete evaluation to read as `failed`, conflating the
validator's inability with a packet defect, or as `passed`, letting an unjudged packet claim
conformance; Part 05 §§9.4 and 10 forbid each. Filing every non-extension finding against core, the
current behavior, counts a manifest-structure defect as a core-data defect and lets an extension's
array fail core. A partial-publication mode that commits a packet with a failing extension would need
a new content class or manifest marker, because
[Part 00 §3.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet-content-classes) makes
an extension's resources canonical, and no consumer has asked for one. A closed validation-report
schema would also have to settle the external-verification level, the advisory flag, and
rule-evaluation records, while no v0.2 consumer reads a report other than the tool that wrote it.
Keeping composition in Part 09 would make the extension part own packet-scope findings and verdict
states that concern no extension.

## 3. Decision

Six subsections define verdicts and the subjects findings belong to, extend packet checks to
extension resources, gate publication, state report content, and keep Part 09's separation.

### 3.1 Verdicts

A validator reports a **verdict** for the packet, for its core registry, and for each extension
registry its manifest binds. A verdict is `passed`, `failed`, or `incomplete`. A subject's verdict
is:

1. `failed` where the subject has an error-level finding under §3.2, or its bound registry's Part
   02 result is `invalid`;
2. otherwise `incomplete` where an evaluation the subject requires did not complete or was withheld,
   or its bound registry's result is `unsupported` or `incomplete`; and
3. otherwise `passed`.

The packet verdict is the worst, in the order `failed`, `incomplete`, `passed`, of the verdict its
own findings give the packet, core's verdict, and every bound extension's verdict. Only a packet
verdict of `passed` supports the packet conformance claim of Part 05 §10.

Where Part 04 §10 or Part 05 §14.5 withholds an evaluation, the subject it was withheld from is at
best `incomplete`. A finding in the `json`, `shape`, or `entries` phase withholds every registry's
evaluation; a core registry that fails binding or whose result is not `valid` withholds every
extension's packet checks; and an extension registry that fails binding withholds its own.

### 3.2 Finding subjects

A validator MUST attribute each finding to exactly one subject:

- a `registry_binding` finding, and each outcome of a bound registry's Part 02 result, belongs to
  the registry it concerns;
- a finding produced by a generated check or a declared rule belongs to the registry whose
  declaration generated or declares it;
- any other finding about one resource entry, or the resource it locates, belongs to the registry
  whose declaration the entry's `declaration_id` names; for a reference, dependency, or lineage
  finding, that entry is the one holding the reference, the `requires` declaration, or the
  `derived_from` member, and for `packet.resource.required_missing` it is the absent singleton's
  declaration; and
- every other finding belongs to the packet, including every finding of the `json`, `shape`, and
  `entries` phases, `packet.resource.declaration_unknown`, and `packet.resource.lineage_cycle`.

### 3.3 Extension resources

A validator MUST apply to each resource an extension declares every check of Part 05 §§5.1–5.3 that
a core resource receives because of its logical kind or its declarations, directed by that
extension's checked context. A check that applies to one named core resource, such as the
session-inventory check, does not extend. The shim's unit-code check therefore covers every table
resource whose declaration a registry directing packet checks holds, and its finding belongs to the
declaring registry.

### 3.4 Publication

A writer MUST NOT publish a manifest, whether as a first commit or as a later version, unless the
verdict of the packet it describes is `passed`, and MUST record `passed` as that manifest's
`validation.status`. A packet whose extension fails is therefore published in no partial form; its
writer corrects the extension or builds the packet without it.

### 3.5 Report content

A validator's report MUST state the packet verdict, core's verdict, and each bound extension's
verdict, and MUST state each finding's subject. This specification defines no validation-report
schema.

### 3.6 Extension separation

An extension is validated on core's terms under §3.3, and its verdict and core's are composed under
§3.1, so an extension's findings never change core's verdict and core's findings never change an
extension's. A consumer MAY read core from a packet whose extension fails, and MUST NOT read that
packet's verdict as though the failure were external to it.

## 4. What this does not change

A reader still opens and reads a packet without a verdict, under
[Part 05 §14.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-reader-registry-independence),
and still reads core when an extension registry fails binding under Part 04 §10. An incomplete
evaluation remains no packet finding under Part 05 §9.4. The manifest schema keeps `failed` and
`not_run` for a manifest the writer does not publish.

## 5. Consequence

A packet published with a failing extension, or whose evaluation was incomplete, no longer
validates as `passed`. Its bytes are unchanged, and a corrected build replaces it. The two local
development packets predate the registry-binding manifest and are rebuilt regardless. No registry,
meta-schema, registry contract, or manifest schema changes, so no version identifier advances.

No accepted clause is superseded. R17 §4 and R72 §2.4 keep their meaning, and their ledger
destinations move from Part 05 §5.4 and Part 09 §5.4 to the planned Part 05 section 9.5. R71 §2.2's destination moves
from Part 00 §4.1 to Part 05 §9.2, where the obligation widens to every packet resource. R79 §§2.1–2.3
remain at Part 05 §10. R130 §3.6 loses one sentence deferring composition to Part 09. R131 §3.3's
check widens from core's tables to every registry directing packet checks. R127 §3.6 left
composition for a later decision, which this revision supplies.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. No scientific meaning changes. | None required. |
| logical prose and registry | Unchanged. A declaration already names its registry, and no rule, column, or identity changes. | None required. |
| physical profiles | Unchanged. The physical checks that reach extension resources are those Part 03 and Part 05 §5.3 already define. | None required. |
| packet manifest and JSON Schemas | Part 04 §9 cites Part 05 §9.2 for a published manifest's `status`, and Part 04 §10 cites Part 05 §9.2 and the planned section 9.5. The schema is unchanged. | `evidence/R132.json` names both anchors. |
| validation and import | Part 05 gains section 9.5 and revises §§5.3, 5.4, 9.2, 10, and 14.5; Part 00 §4.1 cites Part 05 §9.2. | The fixtures and tests below. |
| extensions | Registry content is unchanged. Their resources receive core's packet checks, which every extension exercised by the §2.3 probe passes. | The AIND extension suite and the corpus. |
| reader, writer, validator, adapters | The validator reports three-state verdicts for the packet, core, and each bound extension; findings carry their subject into JSON; top-level `status` becomes the packet verdict; array, digest, and file findings are attributed by declaration; every packet check reaches extension resources; and the command line reports and exits on the packet verdict. The writer's commit and amendment gates, its `verify` command, and its command-line import use the packet verdict. The reader and adapters are unchanged; Tier 1 generation already runs per registry. | Validator and writer tests below. |
| conformance fixtures and tests | Correct the validator's extension fixture to write `task.trials.session_id` as `int32`. Rewrite the two tests asserting the core-only verdict. Add tests for a packet with one passing and one failing extension, an extension-table type mismatch attributed to the extension, an extension dense-array defect that leaves core `passed`, an incomplete core evaluation reported as `incomplete`, a manifest `shape` failure that leaves every registry `incomplete`, JSON findings carrying their subject, and writer refusals of a failing extension and of an incomplete verdict. Add a corpus variant whose extension table holds a type mismatch. | `fixtures/corpus.py` and the package suites. |
| revision process and tooling | Ledger destinations for R17 §4, R71 §2.2, and R72 §2.4 move as stated above; otherwise the ordinary revision and evidence records. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | The combined specification and heading index regenerate. The validator and writer READMEs describe the verdicts and the gate, and the specification README's pointer names Part 05's verdict section. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied`: §§3.1, 3.2, and 3.5 at the planned Part 05 section 9.5 and §3.1 also at Part 05 §§10 and
14.5; §3.3 at Part 05 §§5.3 and 5.4; §3.4 at Part 05 §9.2 and Part 04 §§9 and 10; and §3.6 at Part
09 §5.4, each by its canonical anchor.

The negative cases distinguish the new rule from the current one: a packet whose only error is an
extension finding validates `failed` rather than `passed`; an extension table whose column type
differs from its declaration, which no check now reads, produces `schema.column_type` attributed to
the extension; an extension array defect leaves core `passed` and fails the extension; and a writer
refuses to publish a packet whose extension fails or whose evaluation is incomplete. The positive
cases are the valid corpus packet and every current extension test, which keep passing with their
fixtures corrected.

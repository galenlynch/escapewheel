# A packet passes only when its manifest, core, and every bound extension pass

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `7bee7a43d8ed0a2e10ba8a1dc449437d4b972d5b` |
| **Decision domain** | specification |
| **Affects** | Part 05 §§5.3, 5.4, 6, 9, 10, and 14.5; Part 09 §5.4; Part 04 §§9 and 10; Part 00 §4.1; the reference validator's report and the writer's publication gate |

## 1. Problem

A packet binds one core registry and any number of extension registries, and
[Part 09 §5.4](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-verdicts)
reports a verdict for core and for each extension separately. The same section makes the packet's
verdict the conjunction of core's and every extension's, so a validator does not report a packet
whose extension fails as conforming.

The specification defines no part of that conjunction. No clause assigns a finding to core, to an
extension, or to neither; gives a verdict to a subject whose evaluation was incomplete or withheld;
names the checks an extension's resources receive; or says what a report or a writer does with the
result.
[Part 05 §14.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validator-registry-boundary)
states the gap: extension-table byte validation and the final composition of core, extension, and
packet verdicts are not defined there.

The reference implementation fills the gap with a core-only verdict. Its report states `passed` for
a packet whose extension fails, its writer publishes that packet, and its physical checks never
read an extension's tables. It also files findings about an extension's arrays and files against
core, so an extension's defect can fail core, which Part 09 §5.4 forbids.

## 2. Evidence

All observations below were reproduced at the recorded baseline, where the full repository
verifier passed all 35 stages.

### 2.1 The reported status counts only core's findings

`Report.passed` in `escapewheel-validator` counts error-level findings that carry no extension, and
`Report.to_dict` writes that value as the report's top-level `status`. A packet whose extension
table `task.trials` holds a value outside its closed vocabulary validates to `"status": "passed"`
with `"errors": 1`; the one error is `task.trials.choice.in_vocabulary`, attributed in memory to
extension `task`. The serialized findings carry only `level`, `check`, `message`, and `rows`, so the
JSON loses that attribution.

Two validator tests assert the core-only verdict.
`test_an_extension_finding_does_not_fail_core` asserts `report.passed` beside
`not report.extension_passed("task")`, and
`test_validator_preserves_an_available_unparseable_extension_result` asserts `report.passed` for a
packet binding an extension registry whose Part 02 result is `invalid`.

### 2.2 The writer publishes on core's verdict

A first commit and an amendment in `escapewheel-writer/src/escapewheel_writer/writer.py` each refuse
only when `report.passed` is false, and each writes the manifest's `validation.status` from that
value. The validator command line exits 0 on it. A build whose extension fails therefore publishes a
packet recorded as `passed`, although Part 05 §9.2 requires an import to refuse to commit on any
error.

### 2.3 Extension tables receive only generated and declared queries

The validator's column-presence and type check, physical-order scan, functional-dependence
duplication check, unfilled-`metadata` check, and reserved-value check each iterate the core
registry's tables. An extension table receives its generated Tier 1 queries and its declared Tier 2
rules and nothing else, although
[Part 09 §5.1](../../escapewheel_poc_docs_v0.2/09_metadata_and_extensions.md#ew-extension-definition)
gives an extension's declarations the same applicable terms as core's and Part 05 §5.4 validates each
extension on the same terms as core.

The validator's own extension fixture shows the cost. It writes `task.trials.session_id` as `int64`
against a declared `int32`, and no check reports it. A probe that ran the same five checks over the
union of core and extension tables reported that mismatch, and changed no other outcome in the
writer's 26 extension tests or the 66 tests of the AIND extension package.

### 2.4 An extension's array and file defects fail core

Findings from dense-array metadata checks, owned-digest checks, and missing-file checks carry no
extension, whichever registry declares the resource they concern. A defect in an extension's array
therefore counts against core's verdict.

### 2.5 Incomplete evaluation and failure share one Boolean

An incomplete Tier 2 evaluation makes `Report.passed` false exactly as an error does.
[Part 05 §9.4](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-incomplete-validation)
requires a report to distinguish the two, and the report does so only in a separate list of rule
evaluations, never in a verdict.

### 2.6 Baseline, overlap, and feasibility

No other proposal or draft is open.
[R127](../accepted/R127-registry-documents-are-checked-at-conformance-boundaries.md) left missing
registries, extension-table byte validation, and the final composition of core, extension, and
packet verdicts as separate decisions.
[R130](../accepted/R130-a-packet-binds-the-exact-registries-that-declare-its-resources.md) decided
the first as named binding findings and left Part 09 §5.4 unchanged. The reverse-citation scan of the
affected sections finds live citers in Part 04 §10, Part 05 §10, the specification README, the
validator's contribution guide, and reader and validator source comments; each changes with this
decision.

The reference validator already reports per-extension findings in memory and already records
incomplete rule evaluations, so composition needs no new information from the packet. The probe in
§2.3 shows that extension parity is implementable with the existing checks.

## 3. Desired outcome and constraints

A report states a packet verdict, core's verdict, and each bound extension's verdict, and a
consumer can tell from each whether its subject failed or could not be judged. A finding belongs to
exactly one subject, fixed by the declaration that governs what it concerns. Only the packet
verdict decides conformance, and it decides whether a writer publishes.

The resolution preserves:

- Part 09 §5.4's separation, under which an extension's failure never changes core's verdict and a
  core failure is never attributed to an extension;
- Part 05 §9.4's refusal to turn an incomplete evaluation into a packet finding;
- [Part 04 §10](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-manifest-conformance)'s
  binding behavior, under which a failed extension registry withholds only its own declarations and
  a failed core registry withholds the `declaration` phase;
- [Part 05 §14.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-reader-registry-independence)'s
  reader independence, so a reader still reads core from a packet whose extension fails; and
- the manifest schema, the registry meta-schema, and every registry document.

## 4. Options and tradeoffs

### 4.1 Verdict states

**Keep two values, `passed` and `failed`.** An incomplete evaluation must then read as one or the
other. As `failed` it conflates the validator's inability with the packet's defect, which Part 05
§9.4 forbids; as `passed` it lets an unjudged packet claim conformance, which
[Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes)
forbids.

**Use three values, `passed`, `failed`, and `incomplete`.** A subject with an error-level finding is
`failed`; one without, whose required evaluation did not complete, is `incomplete`; any other is
`passed`. Conjunction takes the worst in that order, so a known error decides a verdict even beside
an unfinished evaluation. A bound registry whose result is `invalid` fails its subject, since Part 05
§14.5 already reports its outcomes as registry-document findings, and one whose result is
`unsupported` or `incomplete` leaves its subject `incomplete`. This proposal prefers three values,
which carry the distinctions Part 05 §§9.4 and 10 already draw into the verdict itself.

### 4.2 Finding attribution

**File everything that is not an extension's query result against core.** This is the current
behavior. It counts a manifest-structure finding as a core-data defect and, as §2.4 shows, lets an
extension's array defect fail core.

**Attribute a finding to the registry whose declaration governs it, and otherwise to the packet.** A
binding finding or registry-document outcome belongs to the bound registry it concerns. A finding
about a resource entry belongs to the registry declaring that entry's `declaration_id`; for a
reference or lineage finding, that entry is the one holding the reference or the `derived_from`
member. The findings no single declaration governs belong to the packet: those of the `json`,
`shape`, and `entries` phases, `packet.registry.core_count`, `packet.registry.path_unique`, an
entry whose declaration no bound registry supplies, and a lineage cycle. The packet verdict then
conjoins the packet-scope findings, core's verdict, and every bound extension's verdict. This
proposal prefers it, because a declaration ID already names exactly one registry and the rule needs
no new mechanism.

A withheld evaluation leaves its subject `incomplete`. A manifest that fails `shape` leaves core and
every extension unjudged, and a failed core registry leaves every extension unjudged. A missing or
mismatched extension registry fails that extension through its own binding finding.

### 4.3 Checks over extension resources

**Run only the generated and declared queries.** This is the current behavior and the gap §2.3
shows.

**Run every check core's resources receive.** Column presence and type, physical order,
duplication, unfilled `metadata`, reserved values, dense-array metadata, and owned digests reach an
extension's resources exactly as they reach core's, directed by the extension's checked context and
attributed to it under §4.2. This proposal prefers it. Part 09 §5.1 and Part 05 §5.4 already require
the same terms, so the change corrects the implementation and closes the scope Part 05 §14.5 leaves
open, rather than adding an obligation.

### 4.4 Publication gate

**Publish on core's verdict.** This is the current behavior. It contradicts Part 05 §9.2 and
publishes a packet a validator reports as not conforming.

**Publish a failing extension in an explicit partial-publication mode.** The project review
suggested a mode that commits such a packet as a non-canonical artifact.
[Part 00 §3.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet-content-classes) makes
an extension's resources canonical, so an honest partial packet would need a new content class or
manifest marker, and no consumer has asked for one.

**Publish only a `passed` packet.** A first commit and an amendment each refuse a packet whose
verdict is `failed` or `incomplete`, and the manifest's `validation.status` records the packet
verdict. This proposal prefers it. Part 05 §§6 and 9.2 already require it once validation means the
packet verdict, and a build whose extension fails recovers by correcting the extension or by leaving
it out of the recipe.

### 4.5 Report content

**State the required content in prose.** Part 05 §9 requires a report to carry the packet verdict,
core's verdict, each bound extension's verdict, and each finding's subject, and the reference
implementation serializes them. This proposal prefers it.

**Publish a closed validation-report schema.** A schema would make reports portable, as
`registry/registry_result.schema.json` does for registry results, but it would also have to settle
the external-verification level of
[Part 04 §5.3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-external-resource-verification),
the advisory flag, and rule-evaluation records. No v0.2 consumer reads a report other than the tool
that wrote it, so the schema can follow as its own decision.

### 4.6 Owner of verdict composition

**Keep the rule in Part 09 §5.4.** Its packet-scope findings and verdict states are not about
extensions, so the extension part would own a validation-reporting rule.

**Move the rule to Part 05 §9.** Part 05 §9 already owns findings, the error policy, and incomplete
validation, and Part 05 §§10 and 14.5 already defer to wherever composition lives. Part 09 §5.4
keeps the extension-specific separation and cites Part 05. This proposal prefers Part 05.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. No scientific meaning changes. |
| logical prose, registry meta-schema, registry declarations, and declarative rules | Unchanged. A declaration already names its registry, and no rule, column, or identity changes. |
| physical profiles | Unchanged. The physical checks that reach extension resources are those Part 03 and Part 05 §5.3 already define. |
| packet manifest and incorporated JSON Schemas | Schema unchanged. Part 04 §9 states that `validation.status` records the packet verdict, and Part 04 §10's writer clause cites the publication gate. |
| validation and import | Affected directly: verdict states, finding attribution, packet-scope findings, extension parity, the publication gate, and required report content, in Part 05 §§5.3, 5.4, 6, 9, 10, and 14.5 and Part 09 §5.4. [Part 00 §4.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-core-content-requirements)'s obligation to validate core resources before commit widens to every packet resource. |
| extension registries | Content unchanged. Their resources receive core's physical checks, which the four example extensions pass under the probe. |
| reader | Unchanged. Part 04 §10 and Part 05 §14.3 already let a reader read core when an extension registry fails. |
| writer | The commit and amendment gates and the recorded `validation.status` use the packet verdict. |
| validator | The report gains three-state verdicts for the packet, core, and each bound extension; findings carry their subject into JSON; top-level `status` becomes the packet verdict; array, digest, and file findings are attributed by declaration; physical checks reach extension tables; and the command line reports and exits on the packet verdict. |
| adapters and code generation | Unchanged. Tier 1 generation already runs per registry. |
| existing packets and migration | A packet published with a failing extension or an incomplete evaluation no longer validates as `passed`. Its bytes are unchanged, and a corrected build replaces it. The two local development packets predate the registry-binding manifest and are rebuilt regardless. Test fixtures whose extension tables disagree with their declared types are corrected. |
| conformance fixtures and tests | Add a packet with one passing and one failing extension, an extension-table type mismatch, an extension dense-array defect that leaves core `passed`, an incomplete core evaluation, a manifest `shape` failure that leaves every registry `incomplete`, and writer refusals of a failing extension and of an incomplete verdict. Rewrite the two tests that assert the core-only verdict. |
| revision lifecycle, ledger, evidence, and process tooling | Unchanged except for the ordinary revision and evidence records. |
| generated publications and developer documentation | The combined specification regenerates, and the validator and writer READMEs describe the report and the gate. |

## 6. Resolved direction

1. Row-valued UCUM checking is a separate decision,
   [R131](../accepted/R131-a-validator-checks-every-unit-value-against-ucum.md), which checks core's
   unit columns. Decision 4 extends that check, with every other, to an extension's resources.
2. A verdict is `passed`, `failed`, or `incomplete`. A subject with an error-level finding is
   `failed`; one without, whose required evaluation did not complete or was withheld, is
   `incomplete`; any other is `passed`. Conjunction takes the worst in that order. A bound registry
   whose result is `invalid` fails its subject, and one whose result is `unsupported` or
   `incomplete` leaves it `incomplete`.
3. A finding belongs to the bound registry whose declaration governs what it concerns: a binding
   finding or registry-document outcome to that registry, and a finding about a resource entry to
   the registry declaring the entry's `declaration_id`. Findings that no single declaration governs
   belong to the packet. The packet verdict conjoins the packet-scope findings, core's verdict, and
   every bound extension's verdict.
4. Every check that core's resources receive reaches an extension's resources, directed by that
   extension's checked context and attributed to it.
5. A writer publishes, by first commit or amendment, only a packet whose verdict is `passed`, and
   records that verdict as the manifest's `validation.status`. No partial-publication mode exists.
6. Part 05 §9 owns verdict composition and requires a report to carry the packet verdict, core's
   verdict, each bound extension's verdict, and each finding's subject. Part 09 §5.4 keeps the
   extension-specific separation and cites Part 05. No validation-report schema is published.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

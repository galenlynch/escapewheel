# A packet passes only when its manifest, core, and every bound extension pass

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-23 |
| **Based on** | `7bee7a43d8ed0a2e10ba8a1dc449437d4b972d5b` |
| **Decision domain** | specification |
| **Affects** | Part 05 §§5.3, 5.4, 6, 9, 10, and 14.5; Part 09 §5.4; Part 04 §§9 and 10; Part 00 §4.1; the reference validator's report and the writer's publication gate |

## 1. Problem

Part 09 §5.4 states the composition rule in one sentence: a packet's verdict is the conjunction of
core's and every extension's, and a validator does not report a packet whose extension fails as
conforming. Nothing defines the parts of that conjunction. No clause says which subject a finding
belongs to, what verdict a subject has when its evaluation is incomplete or was withheld, which
checks apply to an extension's resources, or what a report or a writer does with the result. Part
05 §14.5 says so directly: "Extension-table byte validation and final composition of core,
extension, and packet verdicts are not defined here."

The reference implementation fills the gap with a core-only verdict. A report states `passed` for
a packet whose extension fails, the writer publishes that packet, and core's physical checks never
run over an extension's tables. A finding about an extension's array or file is filed against core,
so an extension's defect can also fail core, which Part 09 §5.4 forbids.

## 2. Evidence

The observations below were reproduced at the recorded baseline, where the full verifier passed
all 35 stages.

- **The serialized status is core's.** `Report.passed` counts only findings whose `extension` is
  null, and `Report.to_dict` writes it as the top-level `status`
  (`escapewheel-validator/src/escapewheel_validator/validator.py`, `Report.passed` and
  `Report.to_dict`). A packet given one extension table holding an out-of-vocabulary value
  validates to `"status": "passed"` with `"errors": 1`, the error being
  `task.trials.choice.in_vocabulary` attributed to extension `task`. The serialized findings carry
  only `level`, `check`, `message`, and `rows`, so the attribution is lost in the JSON.
- **Tests assert the core-only verdict.** `test_an_extension_finding_does_not_fail_core` asserts
  `report.passed` beside `not report.extension_passed("task")`, and
  `test_validator_preserves_an_available_unparseable_extension_result` asserts `report.passed` for
  a packet binding an extension registry whose result is `invalid`.
- **The writer publishes on the core verdict.** A first commit and an amendment each refuse only
  when `report.passed` is false (`escapewheel-writer/src/escapewheel_writer/writer.py`, the commit
  and `amend` gates), and the manifest's `validation.status` is written from the same value. The
  validator command line exits 0 on it.
- **Extension tables receive no physical checks.** Column presence and type, physical order,
  functional-dependence duplication, unfilled `metadata`, and reserved-value checks iterate the
  core registry's tables only (`validate`, which passes `_tables(effective)` to each). An extension
  table receives only its generated Tier 1 and declared Tier 2 queries. The validator's own
  extension fixture writes `task.trials.session_id` as `int64` against a declared `int32`, and no
  check reports it. Running the same five checks over core and extension tables together reports
  that mismatch; the writer's 26 extension tests and the 66 tests of the AIND extension package
  pass unchanged under that probe.
- **Findings about an extension's resources are filed against core.** Dense-array metadata,
  owned-digest, and missing-file findings are recorded with no extension, whichever registry
  declares the resource (`_check_packet_owned_arrays`, `_check_owned_digests`).
- **Incomplete and failed collapse into one Boolean.** An incomplete Tier 2 evaluation makes
  `passed` false exactly as an error does. Part 05 §9.4 requires a report to distinguish the two,
  and the report does so only in a separate `evaluations` list, never in a verdict.

## 3. Desired outcome and constraints

A report states one packet verdict and one verdict for core and for each bound extension, and a
consumer can tell from each whether its subject failed or could not be judged. A finding belongs to
exactly one subject, fixed by the declaration that governs what it is about. The packet verdict is
the only one that decides whether a packet conforms, and it decides whether a writer may publish.

The resolution preserves:

- Part 09 §5.4's separation: an extension's failure never changes core's verdict, and a core
  failure is never attributed to an extension;
- Part 05 §9.4's refusal to turn an incomplete evaluation into a packet finding;
- Part 04 §10's binding behavior, in which a failed extension registry withholds only its own
  declarations and a failed core registry withholds the `declaration` phase;
- Part 05 §14.3's reader independence, so a reader still reads core from a packet whose extension
  fails; and
- the manifest schema, the registry meta-schema, and every registry document unchanged.

## 4. Options and tradeoffs

### 4.1 What a verdict can say

**Two values, `passed` and `failed`.** Simple, and the current Boolean. An incomplete evaluation
must then read as one or the other: as `failed` it conflates the validator's inability with the
packet's defect, which Part 05 §9.4 forbids; as `passed` it lets an unjudged packet claim
conformance, which Part 05 §10 forbids.

**Three values, `passed`, `failed`, and `incomplete`.** A subject is `failed` when it has an
error-level finding, `incomplete` when it has none but some required evaluation of it did not
complete, and `passed` otherwise. Conjunction takes the worst of its parts in that order, so a
known error decides a verdict even beside an unfinished evaluation. A bound registry whose result
is `invalid` fails its subject, since Part 05 §14.5 already reports its outcomes as registry-document
findings; one whose result is `unsupported` or `incomplete` leaves its subject `incomplete`. This
proposal prefers three values: they are the distinctions Part 05 §§9.4 and 10 already draw, now
carried into the verdict rather than beside it.

### 4.2 Which subject a finding belongs to

**Core or an extension, with everything else filed against core.** This is the current behavior.
It files a manifest-structure finding against core, and it has no rule for a finding about an
extension resource that is not a query result, which is how an extension's array defect fails core.

**The registry whose declaration governs it, and otherwise the packet.** A binding finding and a
registry-document outcome belong to the bound registry they concern. A finding about one resource
entry belongs to the registry that declares that entry's `declaration_id`; for a reference or
lineage finding that is the entry holding the reference or the `derived_from` member. What no single
registry's declaration governs belongs to the packet: the `json`, `shape`, and `entries` phases,
`packet.registry.core_count`, `packet.registry.path_unique`, an entry whose declaration no bound
registry can supply, and a lineage cycle. The packet verdict is then the conjunction of the
packet-scope findings, core's verdict, and every bound extension's verdict. This proposal prefers
it. It needs no new mechanism, because a declaration ID already names exactly one registry, and it
stops a manifest defect from reading as a core-data defect.

Under this rule a subject whose evaluation was withheld is `incomplete`, not `passed`: a manifest
that fails `shape` leaves core and every extension unjudged, and a failed core registry leaves
every extension unjudged. A missing or mismatched extension registry fails that extension through
its own binding finding.

### 4.3 Which checks reach an extension's resources

**Only the generated and declared queries.** The current behavior, and the gap the evidence shows.

**Every check core's resources receive, from the extension's own checked context.** Part 09 §5.1
already gives an extension's declarations "the same applicable terms as core", and Part 05 §5.4
already says each extension "is validated on the same terms as core". Column presence and type,
physical order, duplication, unfilled `metadata`, reserved values, dense-array metadata, and owned
digests would run over an extension's resources exactly as over core's, with findings attributed
under §4.2. This proposal prefers it; it corrects stale implementation and states the scope that
Part 05 §14.5 disclaims rather than adding a new obligation.

### 4.4 Whether a writer may publish a packet that is not `passed`

**Publish on core's verdict.** The current behavior. It contradicts Part 05 §9.2, which requires an import to
refuse to commit on any error, and publishes a packet a validator will report as not conforming.

**Publish only a `passed` packet, with an explicit partial-publication mode.** A mode that commits
a packet with a failing extension as a non-canonical artifact was suggested by the project review.
No consumer has asked for one, and Part 00 §3.2 makes an extension's resources canonical, so a
partial packet would need a new content class or manifest marker to be honest about itself.

**Publish only a `passed` packet.** A first commit and an amendment each refuse a packet whose
verdict is `failed` or `incomplete`, and the manifest's `validation.status` records the packet
verdict. This proposal prefers it. It is what Part 05 §§6 and 9.2 already require once "validated"
means the packet verdict, and a failing extension is fixed by correcting it or leaving it out of
the recipe.

### 4.5 How far to specify the report

**State required content in prose.** Part 05 §9 would require a report to carry the packet
verdict, core's verdict, each bound extension's verdict, and each finding's subject; the reference
implementation serializes them. This proposal prefers it.

**Publish a closed validation-report schema.** A schema would make reports portable in the way
`registry/registry_result.schema.json` makes registry results portable, and would also have to
settle the external-verification level of Part 04 §5.3, the advisory flag, and rule evaluations.
That is a larger decision than composition, and nothing in v0.2 consumes a report other than the
tool that wrote it; it can follow as its own change.

### 4.6 Where the composition rule lives

**Part 09 §5.4**, where the conjunction is stated today. The rule would remain in the extension
part although its packet-scope findings and its three states are not about extensions.

**Part 05 §9**, beside findings, the error policy, and incomplete validation, with Part 09 §5.4
keeping the extension-specific separation and citing it. This proposal prefers Part 05: the verdict
is a property of validation reporting, and Part 05 §10 and §14.5 already defer to wherever it lives.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. No scientific meaning changes. |
| logical prose, registry meta-schema, registry declarations, and declarative rules | Unchanged. Declarations already name their registry, and no rule, column, or identity changes. |
| physical profiles | Unchanged. The physical checks that now reach extension resources are the ones Part 03 and Part 05 §5.3 already define. |
| packet manifest and incorporated JSON Schemas | Schema unchanged. Part 04 §9's `validation.status` is stated to record the packet verdict, and Part 04 §10's writer clause cites the publication gate instead of listing phases. |
| validation and import | Affected directly: verdict states, finding attribution, packet-scope findings, extension parity, the publication gate, and required report content, in Part 05 §§5.3, 5.4, 6, 9, 10, and 14.5 and Part 09 §5.4. Part 00 §4.1's "validate core resources before it commits them" widens to every packet resource. |
| extension registries | Unchanged in content. Their resources receive core's physical checks. The four example extensions pass them under the probe. |
| reader | Unchanged. Part 04 §10 and Part 05 §14.3 already let a reader read core when an extension registry fails. |
| writer | The commit and amendment gates and the recorded `validation.status` use the packet verdict. |
| validator | `Report` gains per-subject verdicts in three states; findings carry their subject into JSON; top-level `status` becomes the packet verdict; array, digest, and file findings are attributed by declaration; physical checks run over extension tables; the command line reports and exits on the packet verdict. |
| adapters and code generation | Unchanged. Tier 1 generation already runs per registry. |
| existing packets and migration | A packet published with a failing extension or an incomplete evaluation no longer validates as `passed`; its bytes are unchanged, and it is rebuilt or amended after the extension is corrected. The two local development packets predate the registry-binding manifest and are rebuilt regardless. Fixtures whose extension tables disagree with their declared types are corrected. |
| conformance fixtures and tests | Add a packet with one passing and one failing extension, an extension-table type mismatch, an extension dense-array defect that leaves core `passed`, an incomplete core evaluation, a manifest `shape` failure leaving every registry `incomplete`, and writer refusals of both a failing extension and an incomplete verdict. The two tests asserting the core-only verdict are rewritten. |
| revision lifecycle, ledger, evidence, and process tooling | Unchanged except for the ordinary revision and evidence records. |
| generated publications and developer documentation | The combined specification regenerates; the validator and writer READMEs describe the new report and gate. |

## 6. Open questions

1. **Scope.** Row-valued UCUM checking was scheduled with this work. It adds one check and does
   not depend on how verdicts compose, so it is split into the separate proposal
   [A validator checks every unit value against UCUM](a-validator-checks-every-unit-value-against-ucum.md),
   which uses this proposal's attribution. Keep the split, or merge the two?
2. **Verdict states.** Adopt `passed`, `failed`, and `incomplete`, with conjunction taking the worst
   (§4.1)?
3. **Attribution.** Attribute each finding to the registry whose declaration governs it and
   otherwise to the packet, with the packet verdict conjoining packet-scope findings, core, and
   every bound extension (§4.2)?
4. **Publication.** Refuse to publish anything but a `passed` packet, with no partial-publication
   mode (§4.4)?
5. **Report and placement.** Require report content in Part 05 prose without a report schema, and
   move the composition rule to Part 05 §9 with Part 09 §5.4 citing it (§§4.5–4.6)?

Extension parity (§4.3) follows from Part 09 §5.1 and Part 05 §5.4 as they stand and is not a
separate question.

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

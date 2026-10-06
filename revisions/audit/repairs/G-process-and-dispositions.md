# Process rules and dispositions

The audit set two lists apart from the confirmed rules: six rules of R120 that a process tool enforces and the revision guide does not state, and twelve clauses recorded as `applied` that no target states. A reading of each then asked whether the guide owes the rule, and whether the proposed disposition is what the later revisions decided and what `ledger.py` accepts.

Its verdicts on the six tool-enforced rules: not owed (4), owed, reworded (2). On the twelve dispositions: confirmed (9), needs a decision (1), corrected (1), keep as applied (1). The reading of the ledger targets found a thirteenth clause of the second kind, R112 §3.1, listed in [applied-target-pointers.md](../applied-target-pointers.md).

Applied on 2026-10-02: the ledger notes for the four tool-enforced rules not owed, the nine confirmed dispositions, R102 §3.1 as corrected and restored, and R112 §3.1 as `superseded` by R120. R57 §2.1 and the two guide sentences waited on decisions 14 and 21 of [decisions.md](decisions.md), and both are entered. The audit record is [applied-targets.md](../applied-targets.md).

## Rules a process tool enforces

### 1. R120 §3.2

- **The rule:** `stages.py` rejects an absent or unknown domain where the prospective rule applies and accepts the legacy default only for older accepted records
- **Third reading: owed, reworded.** The guide states the metadata rule for artifacts and its §12 row understates what `stages.py` checks, so add one indicative sentence to §2 inside the anchor the ledger already names. Do not also restate it in §12; at most change that row's subject from 'Open documents' to 'Open documents and accepted records from R120'.
- **Text to enter:** `stages.py` rejects an absent or unknown domain or change form wherever the field applies, and accepts the legacy default only for an accepted record below R120.
- **Placement:** revisions/CONTRIBUTING.md §2 (ew-decision-domains), at the end of the paragraph that ends 'declares its applicable fields.'
- **Fix or revision:** fix: the sentence restates R120 §3.2, which the tool and its tests already carry, so nothing that conformed before behaves differently; guide §1 and R120 §3.1 put a meaning-preserving correction of the guide in the ordinary workflow.
- **By lens:**
  - *Wording:* The guide writes in the indicative with no BCP 14 keywords, so the sentence takes none. 'This revision' becomes R120.
  - *Clause:* R120 §3.2's last paragraph binds `stages.py` with five MUSTs (domain, legacy default, `Profile` and `Amends` forms, change form, no `structural` for a process artifact). R120 §3.1 makes the guide the current owner of the material rules by which a change is evidenced, and the ledger records §3.2 as `applied` at `ew-decision-domains`.
  - *Guide states:* Guide §2 states the rule for the artifacts (below R120 a missing domain reads as `specification`; from R120 every artifact declares its fields) and never names `stages.py` there. Guide §12's row for `stages.py` says only that open documents have the required status, baseline, sections and clause list, which omits lifecycle metadata and omits accepted records from R120 onward.
  - *Other documents:* The root `CONTRIBUTING.md` §8 table states it at tool grain ('an open or prospective accepted artifact with invalid lifecycle metadata ...'). `revisions/README.md` says nothing of the check. The root guide is a developer document, not the process owner.
  - *Grain:* The guide does state tool checks at this grain elsewhere: §8.1 says what the ledger resolves and that it requires an `equals` guard, §8.4 says what the heading checker rejects. So a one-clause statement fits the guide's practice.
  - *Second owner:* A tool is an implementation, not an owner (guide §10: code does not become authority by implementing a rule). One sentence in §2 creates no second owner, but the same fact must not also be added to the §12 row in different words; correct that row's subject or leave it.
  - *Tool:* Enforced: `revisions/stages.py` `lifecycle_metadata` rejects a domain outside `specification`/`process` (absent included) and an absent or unknown change form; `accepted` returns no defect for a record numbered below 120 and applies `lifecycle_metadata` from R120. Tests: `revisions/test_process.py` `test_decision_domain_legacy_cutoff`, `test_decision_domain_required_prospectively`, `test_change_form_required_prospectively`. No test passes an unknown (as opposed to absent) domain; the same branch handles both.
  - *Process revision:* Not a process revision. Guide §1 reserves the lifecycle for a change that alters a gate, authority, ledger disposition or evidence meaning, and R120 §3.1 lets a meaning-preserving correction to contribution prose use the ordinary workflow. The sentence restates an accepted rule the tool already enforces, so no behaviour differs.

### 2. R120 §3.4

- **The rule:** a process section named by an `Amends` target, ledger destination, evidence owner or current citation uses the canonical raw-HTML anchor form
- **Third reading: owed, reworded.** The guide states uniqueness of process anchors and never says a named process section needs the canonical raw-HTML anchor, which a process draft's author needs to know before writing `Amends`. Add the one sentence in §8.4; note that the citation checker enforces it only for `ew-` fragments.
- **Text to enter:** Canonical and alias IDs are unique in the combined specification. A section of this guide that an `Amends` target, ledger destination, evidence owner, or citation names carries an anchor of the same canonical form, and process anchors are unique in this document.
- **Placement:** revisions/CONTRIBUTING.md §8.4 (ew-stable-section-anchors), replacing the clause 'process anchors are unique in this document' in the sentence beginning 'Canonical and alias IDs are unique'
- **Fix or revision:** fix: restates R120 §3.4 in the section that owns anchors; the tools already refuse a named process section without a canonical anchor, so no conforming practice changes.
- **By lens:**
  - *Wording:* Fold it into the sentence that already states uniqueness, so the guide says once what a process anchor is.
  - *Clause:* R120 §3.4: 'A process section named by an `Amends` target, ledger destination, evidence owner, or current citation MUST use the same canonical raw-HTML form, and each of its canonical anchors MUST be unique within that document.'
  - *Guide states:* Guide §8.4 gives the canonical form only for 'every numbered section structurally affected', then says 'process anchors are unique in this document' and 'Process anchors resolve directly and do not enter that index'. It states the uniqueness half and presupposes process anchors without saying which sections need one or in what form. §2, §8.1, §5.3 and §9 each say a process target is `path` plus `anchor` and none says the anchor must be the canonical raw-HTML one.
  - *Reader cost:* A process draft must name an anchor in `Amends` (guide §2). Only seven guide sections carry one; §1, §3, §4, §7, §9, §10, §12, §13 and §14 carry none, and the open ledger draft changes §13's failure-handling rule without being able to name it in `Amends`. A reader cannot learn from the guide that a section must first carry the canonical form to be named.
  - *Other documents:* `revisions/README.md`, `revisions/evidence/README.md` and the root `CONTRIBUTING.md` do not state it.
  - *Tool:* Enforced for three of the four namers through `revisions/process_rules.py` `canonical_anchors`, which matches only `specdoc.ANCHOR` lines of kind `canonical`: `stages.lifecycle_metadata` (an `Amends` target), `ledger.unresolved` (a `path` target), `evidence.owner_defects` (a Markdown owner). `check_citations.anchored` enforces it for a citation only where the fragment begins `ew-`; a link to a GitHub heading slug such as `#5-...` is not examined. Tests: `test_process.py` `test_ledger_process_owner_resolves`, `test_canonical_anchor_shape_and_identity` (uniqueness and a count of seven), `test_evidence.py` `test_owner_targets_resolve_by_anchor_and_pointer`. No negative test names an alias or a malformed process anchor.
  - *Second owner:* None: no current document states it, and §8.4 is the section the ledger records for R120 §3.4.
  - *Process revision:* Not a process revision: it restates an accepted rule three tools already enforce and changes no gate, authority, disposition or evidence meaning.

### 3. R120 §3.6

- **The rule:** the citation checker verifies that the displayed number agrees with the anchor's current heading
- **Third reading: not owed.** Not owed: guide §5.3 already requires the displayed number to agree with the anchor's heading, and `check_citations.anchored` with `test_linked_part_number_matches_anchor` enforces it. A ledger note on R120 §3.6 may record that the checker's duty is carried by `revisions/check_citations.py`.
- **Fix or revision:** none: the guide states the rule as a property of the citation and the checker observes it.
- **By lens:**
  - *Clause:* R120 §3.6: a linked part citation 'MUST target the stable anchor, and the citation checker MUST verify that the displayed number agrees with the anchor's current heading'.
  - *Guide states:* Stated. Guide §5.3 (ew-citation-context, the ledger's target for R120 §3.6): 'once its target has a stable anchor, a link targets that anchor and its displayed number must agree with the anchor's current heading.' The rule a contributor can follow is the citation's property; the checker's duty is its enforcement. §12 gives the checker's row ('Citations resolve and use the required spelling') and §6.7 and §11 run it.
  - *Other documents:* Root `CONTRIBUTING.md` §8 says the checker catches 'a citation that does not resolve'; neither it nor `revisions/README.md` mentions the number agreement.
  - *Tool:* Enforced: `revisions/check_citations.py` `anchored` matches `LINKED_PART` (`[Part NN §x.y](path#ew-...)`), finds the heading after the anchor with `anchor_heading`, and reports 'linked Part NN §x disagrees with #anchor's current heading' where the part file, part number or section differs. Test: `revisions/test_process.py` `test_linked_part_number_matches_anchor` (one agreeing and one disagreeing link). The pattern needs the link text to be exactly `Part NN §x`; a link whose text adds words is not compared.
  - *Second owner:* Adding 'the citation checker verifies this' would state the same rule twice in one paragraph, once for the citation and once for the tool.
  - *Process revision:* No change proposed.

### 4. R120 §3.6

- **The rule:** the citation checker normalizes the resolved link to a canonical repository-relative target
- **Third reading: not owed.** Not owed: the guide states the document-relative and repository-relative citation forms, and the normalization is an internal method with no outcome beyond both forms resolving. The audit overstates the tool: `check_citations.anchored` resolves the link and produces no normalized target, and no test covers it.
- **Fix or revision:** ledger-only: a note on R120 §3.6 can record that the checker resolves both citation forms to one file and that the guide states the two forms.
- **By lens:**
  - *Clause:* R120 §3.6: a process document cites a process rule with a Markdown link resolving from the citing document, 'The citation checker MUST normalize the resolved link to a canonical repository-relative target such as `revisions/CONTRIBUTING.md#ew-citation-context`', and a source comment uses that canonical target in backticks.
  - *Guide states:* Guide §5.3 states both citation forms: 'A current process document links to this guide using a document-relative Markdown `path#anchor`; a source comment or docstring uses the canonical repository-relative target ... in backticks.' The normalization is how the checker treats the two forms as one target; it is a method inside the tool and gives a contributor nothing to do.
  - *Tool:* Carried only in effect. `revisions/check_citations.py` `anchored` resolves a Markdown link with `(path.parent / relative).resolve()`, refuses one that leaves the repository, and looks the anchor up in the resolved file; it resolves a backticked source target (`SOURCE_ANCHOR`, `.py` files only) against the repository root. Both forms therefore reach the same file, but the tool builds, reports and compares no repository-relative string. No test is about normalization; `test_linked_part_number_matches_anchor` passes a document-relative link that resolves.
  - *Unobservable:* Whether the checker 'normalizes' is not observable apart from whether both forms resolve, which the guide's two forms and the checker's resolution already fix.
  - *Second owner:* Stating it would put a tool's internal method into the guide, which spec/CONTRIBUTING.md §4 forbids for a requirement (an outcome, not a method) and which guide §12 avoids ('Do not describe a checker as proving more than it observes').
  - *Process revision:* No change proposed.

### 5. R120 §3.7

- **The rule:** the ledger and evidence checker resolve each anchor before applying destination checks
- **Third reading: not owed.** Not owed: guide §8.1, §11 and §12 state that every named owner resolves, which is all the sentence can be observed to require. Do not add it, since `ledger.unresolved` applies its process-owner check before it looks up the anchor and the sentence would misdescribe the tool.
- **Fix or revision:** none: the guide states the observable outcome and the order of the tool's steps is not a rule a guide reader follows.
- **By lens:**
  - *Clause:* R120 §3.7: 'The ledger and evidence checker MUST resolve each anchor before applying destination checks.' The next paragraph gives the outcome: every named destination exists and each current-format clause identifies its current owner.
  - *Guide states:* The outcome is stated three times: §8.1 ('A new process destination uses `path` plus `anchor` and resolves to a process owner in this guide'), §11 ('traceability from accepted clause to disposition to an existing current owner') and §12 ('every named current owner or registry target resolves'; for evidence, 'paths and pointers resolve'). The order of two internal steps is not stated and has no reader.
  - *Tool:* Resolution is enforced; the stated order is not what the ledger does. `revisions/ledger.py` `unresolved` checks a `path` target's domain and recognized owner first and looks the anchor up last, and for a `part` plus `anchor` target finds the part file and then the anchor in `canonical_anchors`. `revisions/evidence.py` `owner_defects` does look the anchor up before it checks the owner's field set. Tests: `test_process.py` `test_ledger_process_owner_resolves`, `test_evidence.py` `test_owner_targets_resolve_by_anchor_and_pointer`.
  - *Unobservable:* The order changes only which defect message a doubly wrong target gets; every unresolved anchor is reported either way. No further destination check exists for an anchored target today: `unresolved` tests only that the anchor is among the file's canonical anchors.
  - *Second owner:* Stating the order would prescribe a method and would be false of `ledger.py` for a process target as written.
  - *Process revision:* No change proposed.

### 6. R120 §3.7

- **The rule:** mechanical verification rejects a malformed or duplicate anchor, a vanished canonical anchor, and an anchor record that disagrees with its heading
- **Third reading: not owed.** Not owed: guide §8.4 already says the heading checker rejects malformed, duplicate, missing or unreviewedly reassigned anchors, and `headings.py --check` enforces all four cases. Record §8.4 as a second target of R120 §3.7, and note that no unit test covers `headings.anchors`.
- **Fix or revision:** ledger-only: add `{ path = "revisions/CONTRIBUTING.md", anchor = "ew-stable-section-anchors" }` to R120 §3.7's `where`, since §8.4 states its heading-record and anchor-rejection rules; `ledger.py` accepts a second process target of that form.
- **By lens:**
  - *Wording:* If the sentence is touched at all, 'missing' could read 'a recorded canonical anchor that has disappeared' and 'a record that disagrees with the heading its anchor precedes' could be named; that is an optional editorial tightening, not a restoration.
  - *Clause:* R120 §3.7: 'Mechanical verification MUST reject a malformed or duplicate anchor, disappearance of a recorded canonical anchor, disagreement between an anchor record and the heading it precedes, or reassignment not recorded by the reviewed candidate diff.' The sentence sits in the paragraph on the `headings.toml` anchor index, so it concerns numbered-part anchors.
  - *Guide states:* Stated, contrary to the audit. Guide §8.4 (ew-stable-section-anchors): '`headings.toml` ... adds a partial index for explicitly anchored numbered sections, recording the canonical ID's part, section, title, and aliases. ... The heading checker rejects malformed, duplicate, missing, or unreviewedly reassigned anchors; human review decides crosswalk completeness'. 'Missing' is the vanished anchor and 'unreviewedly reassigned' covers a record that no longer agrees with the heading its anchor precedes. §12's `headings.py` row and §11's command list name the check.
  - *Ledger target:* The sentence is in §8.4, which the ledger records for R120 §3.4, while R120 §3.7 is recorded only at `ew-current-owner-ledger` (§8.1). The gap the audit saw is a missing ledger target, not a missing sentence.
  - *Tool:* Enforced: `spec/tools/headings.py` `anchors` reports a duplicate anchor, a malformed `data-spec-anchor` line, a heading with other than one canonical anchor and an anchor preceding no heading; `main` compares the computed index with the recorded one and under `--check` fails on any difference, which catches a vanished anchor, a changed part, section or title, and a reassignment. `verify.py` runs it as 'spec: every changed heading has been read' and `tools/tree.py` lists it. No unit test exercises `headings.anchors`: `spec/tools/tests/test_specdoc.py` tests only the `ANCHOR` pattern, and `test_process.py` `test_canonical_anchor_shape_and_identity` reads only the guide's own seven anchors.
  - *Process revision:* No guide change is needed. Adding a second `where` target to the R120 §3.7 ledger entry is a ledger correction.

## Clauses recorded as applied that no target states

### 1. R15 §3

- **Reading: confirmed.** Confirmed: R129 §3.6 and §3.7 replaced every rule of the clause and Part 04 §3 states none of it. Replace the entry with `superseded`, `by = "R129"` and no `where`; `ledger.py` accepts it now and under the open draft.
- **Fix or revision:** ledger-only: no part, registry or tool changes, and a disposition that describes what R129 already decided alters no ledger semantics.
- **Where:** revisions/applied.toml, [clause."R15 §3"]
- **Entry:**

  ```toml
  [clause."R15 §3"]
  disposition = "superseded"
  by = "R129"
  note = "R129 §3.6 removes `required_codecs` and introduces no packet capability union; R129 §3.7 replaces the reader's SHOULD with a MUST to fail the unopenable resource specifically; was Part 04 §3"
  ```

- **By lens:**
  - *Clause:* R15 §3 decides three things: the manifest's top-level `required_codecs` is retained and MUST equal the union of every resource's `codecs`; the rule `manifest.required_codecs_is_the_union`; and a reader SHOULD report which resources it cannot open.
  - *What became:* Verified. R129 §3.6: 'A manifest root MUST NOT contain `required_codecs`' and 'No replacement ... packet-capability-union field is introduced'. R129 §3.7: a reader 'MUST fail that resource specifically and identify the missing support' and 'MUST NOT refuse the packet merely because an unopened resource uses such a feature', which replaces the SHOULD with a stronger rule. `required_codecs` occurs nowhere in `spec/parts`, `spec/artifacts/*.json` or `spec/source`.
  - *Target:* Part 04 §3's generated field table has no `required_codecs` and the section says a manifest MUST NOT carry an undeclared member. It states none of the clause. Part 04 `ew-packet-codecs` says 'The manifest carries no replacement capability union or per-resource selector', and Part 03 §6.1 states R129 §3.7's reader rule.
  - *Still owed:* Nothing. All three rules were replaced whole, so the draft's §3.2 (a clause replaced in part keeps its disposition) does not apply.
  - *Ledger today:* Tested on a scratch copy with the repository's `ledger.py`: the entry passes (exit 0). Today the check reads nothing of a `superseded` entry, so one with a stale `where` or an earlier `by` also passes.
  - *Ledger after draft:* Passes the open draft's §3.1: `by` is one `R<N>` string, R129 is accepted and later than R15, and the entry carries no `where`.
  - *Neighbour:* R15 §2 (per-resource `codecs`) is recorded `applied` at Part 03 `ew-array-codecs`, and R129 §3.6 also removed `codecs` from a resource entry; that entry is outside this class and deserves the same reading.

### 2. R79 §2.3

- **Reading: confirmed.** Confirmed: R130 §3.7 withdrew the obligation the clause classifies and forbids Part 05 §10 to impose it. Record `superseded`, `by = "R130"`, matching R31 §3.
- **Fix or revision:** ledger-only: the entry is corrected to describe what R130 decided; nothing else changes.
- **Where:** revisions/applied.toml, [clause."R79 §2.3"]
- **Entry:**

  ```toml
  [clause."R79 §2.3"]
  disposition = "superseded"
  by = "R130"
  note = "R130 §3.7 removes the resource-entry member `processing_run_id` and has Part 05 §10 not require an analysis resource to name a run, so the packet obligation this clause classified no longer exists; was Part 05 §10"
  ```

- **By lens:**
  - *Clause:* R79 §2.3 classifies R31 §3's MUST (an analysis resource names its producing run) as a packet obligation, so that provenance is SHOULD for a packet and MUST for its analysis resources.
  - *What became:* Verified. R130 §3.7: 'The resource-entry member `processing_run_id` MUST be removed without replacement' and 'Part 05 §10 MUST NOT require an analysis resource to name a run; provenance remains optional within packet conformance.' The ledger already records R31 §3 as `superseded`, `by = "R130"`.
  - *Target:* Part 05 §10 (`ew-conformance-classes`) states R79 §2.1 and §2.2 and says nothing of an analysis resource naming a run.
  - *Alternative:* `rationale` is arguable, since the clause explains how §2.1 reads against R31 §3. It is weaker: the clause does decide which conformance class the MUST belongs to, and that decision was removed by a named later revision, which is what `superseded` records. It also keeps the entry parallel with R31 §3.
  - *Still owed:* Nothing. What survives, required lineage for an analysis resource, is R130 §3.7's own and is recorded there.
  - *Ledger today:* Tested on a scratch copy: passes.
  - *Ledger after draft:* Passes: `by = "R130"` names a later accepted revision and there is no `where`.

### 3. R107 §3.1

- **Reading: confirmed.** Confirmed: R126 §3.8 replaced the ban on restating a declaration with a ban on contradicting one, and Part 02 §3 states the replacement. Record `superseded`, `by = "R126"`, and drop the note's claim of a check.py invariant.
- **Fix or revision:** ledger-only: the part already states R126's rule; only the ledger still claims the older one.
- **Where:** revisions/applied.toml, [clause."R107 §3.1"]
- **Entry:**

  ```toml
  [clause."R107 §3.1"]
  disposition = "superseded"
  by = "R126"
  note = "R126 §3.8 makes non-duplicative wording a matter of style, removes prose-restatement heuristics from registry conformance, and forbids only a description that contradicts or overrides a declaration; was Part 02 ew-column-declaration, enforced by a check.py invariant R126 removed"
  ```

- **By lens:**
  - *Clause:* One rule: 'A column's `description` MUST NOT restate what one of that column's own fields declares.' The rest explains the cut, exempts a part's prose, and says which earlier sentences it replaces.
  - *What became:* Verified. R126 §3.8: 'prose-restatement heuristics ... MUST NOT be registry conformance requirements. A description MUST NOT contradict or override a machine declaration; concise and non-duplicative wording remains specification style rather than a machine comparison of English text.' The ban on restating became style and only contradiction is forbidden.
  - *Target:* Part 02 §3 (`ew-column-declaration`) reads 'A description MUST NOT contradict or override a machine declaration. Concise, non-duplicative wording remains authoring style', which is R126 §3.8's rule and not this clause's. No checker carries a restatement invariant: a search of `spec/tools/check.py`, `spec/tools/checkers/` and the registry-contract descriptor for 'restat' finds only an unrelated comment.
  - *Note now false:* The current note says the rule is 'enforced by one new check.py invariant taking the structural checks from 29 to 30', which R126 undid; the note has to go with the disposition.
  - *Still owed:* Nothing: the clause's one rule was replaced whole.
  - *Ledger today:* Tested on a scratch copy: passes.
  - *Ledger after draft:* Passes: `by = "R126"`, later than R107, no `where`.
  - *Neighbour:* R107 §3.1 says it replaces R48 §2.5 entirely, and the ledger records R48 §2.5 as `registry` ('a column, key or reference the registry declares'). That entry is outside this class and looks wrong in the same way.

### 4. R148 §3.4

- **Reading: confirmed.** Confirmed: R149 §3.4 replaced the value this clause assigned and the recorded target states 0.14.0. Record `superseded`, `by = "R149"`.
- **Fix or revision:** ledger-only: the registry and Part 02 already carry R152's value.
- **Where:** revisions/applied.toml, [clause."R148 §3.4"]
- **Entry:**

  ```toml
  [clause."R148 §3.4"]
  disposition = "superseded"
  by = "R149"
  note = "R149 §3.4 advances the core `registry_version` from 0.10.0 to 0.11.0, and R150 §3.10, R151 §3.2 and R152 §3.4 advance it again; was Part 02 ew-registry-self-description"
  ```

- **By lens:**
  - *Clause:* One rule: the core registry's `registry_version` MUST advance from `0.9.0` to `0.10.0`.
  - *What became:* Verified in each record. R149 §3.4: '`0.10.0`, which R148 assigns' to `0.11.0`. R150 §3.10: `0.11.0` to `0.12.0`. R151 §3.2: `0.12.0` to `0.13.0`. R152 §3.4: `0.13.0` to `0.14.0`. The incorporated registry declares `registry_version: 0.14.0` and Part 02 §9.2 states that value; `0.10.0` appears in §9.2 only as a meta-schema version.
  - *Target:* Part 02 §9.2 (`ew-registry-self-description`) states R152's value. The target's own note, 'core 0.10.0', names a value the section does not hold.
  - *Successor:* R149 is the right `by`: it is the revision that replaced the value R148 assigned, and the open draft's §3.1 asks for one later revision. The note can name the chain.
  - *Alternative:* `rationale` would misdescribe a clause that did decide a value. `registry` would be right only for the clause whose value the registry now carries, R152 §3.4.
  - *Still owed:* Nothing: the clause is a single value, replaced whole.
  - *Consistency:* The same reading reaches clauses outside this class. R147 §3.8, R149 §3.4 and R150 §3.10 are `applied` at the same anchor for core 0.9.0, 0.11.0 and 0.12.0, but each also carries an extension-migration rule Part 02 §9.2 still states, so under the draft's §3.2 they stay `applied` with a note naming the later clause. R148 §3.4 and R151 §3.2 are the two clauses that decide a version and nothing else.
  - *Ledger today:* Tested on a scratch copy: passes.
  - *Ledger after draft:* Passes: `by = "R149"` is later than R148 and the entry has no `where`.

### 5. R151 §3.2

- **Reading: confirmed.** Confirmed: R152 §3.4 replaced the value and Part 02 §9.2 states 0.14.0. Record `superseded`, `by = "R152"`.
- **Fix or revision:** ledger-only.
- **Where:** revisions/applied.toml, [clause."R151 §3.2"]
- **Entry:**

  ```toml
  [clause."R151 §3.2"]
  disposition = "superseded"
  by = "R152"
  note = "R152 §3.4 advances the core `registry_version` from 0.13.0 to 0.14.0; was Part 02 ew-registry-self-description"
  ```

- **By lens:**
  - *Clause:* One rule: the core `registry_version` MUST advance from `0.12.0` to `0.13.0`. Its second sentence says the meta-schema, the registry-contract descriptor and the rule language are unchanged, which decides nothing.
  - *What became:* Verified. R152 §3.4's table: core registry `registry_version` '`0.13.0`, which R151 §3.2 assigns' to `0.14.0`; the same clause advances the meta-schema to 0.11.0 and the descriptor to v0.9. The registry declares `0.14.0`.
  - *Target:* Part 02 §9.2 states `registry_version: 0.14.0`; `0.13.0` appears in no part. The target's note 'core 0.13.0' is false of the section.
  - *Still owed:* Nothing.
  - *Ledger today:* Tested on a scratch copy: passes.
  - *Ledger after draft:* Passes: `by = "R152"` is later than R151 and the entry has no `where`.

### 6. R57 §2.1

- **Reading: needs a decision.** The proposed entry contradicts itself: a clause cannot be `superseded` whole and still have a rule owed. Decide the emit-first SHOULD first; if it is dropped, record `superseded` by R126 with the note above, and if it is restored, keep `applied` at Part 02 §9.2 with a note naming R126 §3.2.
- **The choice:** Is R57 §2.1's SHOULD to emit `$schema` first still a rule of the specification? (1) No, recommended: record the clause `superseded` by R126 with a note saying the ordering recommendation is not carried; Part 02, the registry, the checker and the corpus are unchanged. (2) Yes: restore it in Part 02 §9.2 naming an actor that can comply (a registry's author, which Part 00 §2.4 does not define), keep `applied` at `ew-registry-self-description`, and label it unchecked. (3) Retire it by a revision: the same end state as (1) with a decision record, at the cost of a revision for a recommendation no actor can be bound by.
- **Fix or revision:** ledger-only for option 1, since no part ever stated the SHOULD and no implementation's conformance turns on it, but it records that a decided recommendation is dropped, which is a maintainer's decision and not the recorder's. Option 2 is a fix to Part 02 §9.2 plus the ledger note.
- **Where:** revisions/applied.toml, [clause."R57 §2.1"]
- **Entry:**

  ```toml
  # Option 1, the recommended one: the emit-first SHOULD is not carried forward
  [clause."R57 §2.1"]
  disposition = "superseded"
  by = "R126"
  note = "R126 §3.2 requires `$schema` on every registry document and selects the meta-schema from it, replacing the MAY and the SHOULD to emit it; the SHOULD to emit it first reached no part and is not carried, since a writer stores a bound registry's exact bytes and a checker reads the decoded document; was Part 02 ew-registry-self-description"
  
  # Option 2: the emit-first SHOULD is restored in Part 02 §9.2
  [clause."R57 §2.1"]
  disposition = "applied"
  where = [{ part = "02", anchor = "ew-registry-self-description" }]
  note = "R126 §3.2 requires `$schema`, replacing the MAY and the SHOULD to emit it; the SHOULD to emit it first was absent and is restored"
  ```

- **By lens:**
  - *Clause:* Three rules: a registry document MAY carry a top-level `$schema` whose value is the `$id` of the meta-schema it conforms to; a writer producing one SHOULD emit it; and SHOULD emit it first.
  - *What became:* Verified in part. R126 §3.2: 'Every registry document MUST carry `$schema`' and a checker selects a local meta-schema from it, so the MAY and the first SHOULD became a MUST and the key's meaning was restated; the registry meta-schema lists `$schema` in `required`. The claim that the recommendation to emit it first is in no part is true, and `git log -S'emit it first'` shows it never reached one: the commit that added R57 touched only the record.
  - *Target:* Part 02 §9.2 does state the clause's key at greater force: 'The incorporated registry meta-schema has `$id` ... Every registry document conforming to that schema MUST carry that value in `$schema`.' So the audit's 'the target states none of its rules' holds only if a rule restated with more force by a later revision counts as that revision's, which is how the ledger treats R29 §2.1 ('MAY raised to SHOULD', superseded by R77) and R55 §2.5 ('restated whole in R90 §3').
  - *Proposed is inconsistent:* `superseded` with a rule 'confirmed missing' cannot stand as written. The open draft's §3.2 says `superseded` describes a clause replaced whole, and R126 did not replace the emit-first SHOULD: its crosswalk row for §9.2 ('replace in place') and §3.8's list of things that are not conformance requirements name column order and never root member order. The disposition follows from what is decided about that SHOULD (D9, which class D holds).
  - *Emit first:* Reasons not to restore it: it names 'a writer producing a registry document', and a Part 00 §2.4 writer stores a bound registry as the exact bytes its digest covers (Part 03 §3.2), so it cannot reorder members; R126 has a checker decode the document before reading `$schema`, and a mapping entry point never sees member order; nothing could check it. The incorporated core registry does emit `$schema` first.
  - *Ledger today:* Tested on a scratch copy: both candidate entries pass.
  - *Ledger after draft:* Both pass: the `applied` form is unchanged by the draft, and the `superseded` form has `by = "R126"`, later than R57, and no `where`.

### 7. R22 §4

- **Reading: confirmed.** Confirmed: the registry rule carries the clause exactly and Part 05 §5.2 states none of it. Change the entry to `registry`, remove `where`, and add the guarded pointer, without which `ledger.py` fails.
- **Fix or revision:** ledger-only: the entry and one registry target; no part or registry change.
- **Where:** revisions/applied.toml, [clause."R22 §4"], and revisions/registry-targets.toml
- **Entry:**

  ```toml
  [clause."R22 §4"]
  disposition = "registry"
  note = "the projection is a function, checked by the Tier 2 rule core.unit_quality_labels.projection_is_consistent; no part states it"
  
  # revisions/registry-targets.toml
  [target."R22 §4"]
  locations = [{ path = "spec/artifacts/logical_schemas.json", pointer = "/resources/core.unit_quality_labels/table/rules/0/id", equals = "core.unit_quality_labels.projection_is_consistent" }]
  ```

- **By lens:**
  - *Clause:* One rule and its predicate: within a packet one `(source, label)` pair MUST project to one `normalized_label`, checked by `core.unit_quality_labels.projection_is_consistent` at error, with the `COALESCE` that makes a null beside a value inconsistent.
  - *What became:* Verified. The incorporated registry declares `core.unit_quality_labels.projection_is_consistent` at `error` as the table's first rule (stored index 0), with the clause's SQL including the `COALESCE`. It is the table's only rule.
  - *Target:* Part 05 §5.2 (`ew-tier-2-validation`) is the general clause on how a validator runs any Tier 2 rule and names no table. A search of the parts for `normalized_label` finds Part 02 §9.3 (R22 §3's writer rules, restored 2026-10-01), Part 03 and the example; none says a pair projects to one value.
  - *Still owed:* No. `registry` is defined for exactly this, 'the exact declaration or predicate is carried by the incorporated registry', and an error-level rule makes a violating packet non-conforming, so no force is lost. A part sentence would be a second statement of a predicate the registry owns.
  - *Ledger today:* Tested on a scratch copy: the entry passes with the target below; without a `registry-targets.toml` entry it fails ('registry disposition has no exact target'), and it fails if `where` is kept.
  - *Ledger after draft:* Unchanged: the draft alters only `superseded` entries and the ratchet.
  - *Guard:* The pointer passes through an array, so `ledger.py` requires `equals`; pointing at the rule's `id` follows the 24 existing targets of that form.

### 8. R27 §3

- **Reading: confirmed.** Confirmed: only the registry rule carries the clause and Part 01 §3.9 never stated it. Change the entry to `registry` with the guarded pointer at rule index 7; a prose sentence beside the device and run analogues is optional.
- **Fix or revision:** ledger-only. The optional Part 01 §3.9 sentence would be a fix, since the registry already rejects the packet.
- **Where:** revisions/applied.toml, [clause."R27 §3"], and revisions/registry-targets.toml
- **Entry:**

  ```toml
  [clause."R27 §3"]
  disposition = "registry"
  note = "a clock is not its own ancestor, checked by the Tier 2 rule core.clocks.parent_chain_well_founded; no part states it"
  
  # revisions/registry-targets.toml
  [target."R27 §3"]
  locations = [{ path = "spec/artifacts/logical_schemas.json", pointer = "/resources/core.clocks/table/rules/7/id", equals = "core.clocks.parent_chain_well_founded" }]
  ```

- **By lens:**
  - *Clause:* One rule and its predicate: a clock MUST NOT be its own ancestor, checked by `core.clocks.parent_chain_well_founded` at error with a depth guard of 64.
  - *What became:* Verified. The registry declares `core.clocks.parent_chain_well_founded` at `error` as the eighth rule of `core.clocks` (stored index 7), with the clause's recursive query and guard.
  - *Target:* Part 01 §3.9, read whole after the 2026-10-01 restorations, says of a parent only 'MAY declare a parent clock, and if so MUST be alignable to it'. `git log -S'clock MUST NOT be its own ancestor'` finds only the commit that added R27, so the sentence never reached a part.
  - *Still owed:* Not owed for force: the error-level rule makes a cyclic packet non-conforming. One observation for a reviewer: Part 01 states the sibling rules in prose (§2.6 for a run's supersession chain, §3.5 'a device MUST NOT be its own ancestor'), and Part 02 §12.5 says of clocks 'the chain is required to be well founded' without saying where. Adding the clock sentence to Part 01 §3.9 would be a fix that states what the registry already enforces; it is optional and the ledger entry does not wait on it.
  - *Ledger today:* Tested on a scratch copy: passes with the target below; a pointer to index 6 fails the `equals` guard, which is the protection against a reorder.
  - *Ledger after draft:* Unchanged by the draft.

### 9. R30 §3.1

- **Reading: confirmed.** Confirmed, with the note doing real work: the registry carries the column and the partition predicate, and the bucket-width rule is now R130 §3.7's at Part 06 §4. Change the entry to `registry` with three guarded pointers and name R130 §3.7 in the note.
- **Fix or revision:** ledger-only.
- **Where:** revisions/applied.toml, [clause."R30 §3.1"], and revisions/registry-targets.toml
- **Entry:**

  ```toml
  [clause."R30 §3.1"]
  disposition = "registry"
  note = "time_bucket_tick on analysis.spike_events and the two rules that make buckets partition the tick axis; R130 §3.7 replaces the bucket-width rule, which Part 06 §4 states as a parameter of a recorded materialization run"
  
  # revisions/registry-targets.toml
  [target."R30 §3.1"]
  locations = [
    { path = "spec/artifacts/logical_schemas.json", pointer = "/resources/analysis.spike_events/table/columns/4/name", equals = "time_bucket_tick" },
    { path = "spec/artifacts/logical_schemas.json", pointer = "/resources/analysis.spike_events/table/rules/0/id", equals = "analysis.spike_events.bucket_contains_spike" },
    { path = "spec/artifacts/logical_schemas.json", pointer = "/resources/analysis.spike_events/table/rules/1/id", equals = "analysis.spike_events.buckets_partition_time" },
  ]
  ```

- **By lens:**
  - *Clause:* Three things: the column `time_bucket_tick` (`int64`, required, the bucket's first tick); buckets MUST partition the tick axis into contiguous non-overlapping ranges per `(session_id, clock_id)`; and the bucket width is a transform parameter that MUST be declared as Part 06 requires.
  - *What became:* Verified. The registry declares `time_bucket_tick` on `analysis.spike_events` as `int64`, required, with the clause's description and `determined_by: [t_tick]` (column index 4), and two error rules: `analysis.spike_events.bucket_contains_spike` (index 0) and `analysis.spike_events.buckets_partition_time` (index 1), whose SQL is the clause's test that a later bucket's smallest tick exceeds an earlier bucket's largest. R130 §3.7 changed the third rule: 'Part 06 §4 MUST state its bucket width ... as parameters of such a recorded run', and a writer need not record one.
  - *Target:* Part 03 §5.4 states the stored order and the row-group recommendation, which are R30 §3.2's, and names `time_bucket_tick` only as a member of that order.
  - *Mixed clause:* The clause is not registry-only. Part 06 §4 (`ew-analysis-spike-events`) holds the generated column table and says 'The bucket width cannot be recovered from the data, so it is a parameter of a recorded materialization run (§5)'. That sentence is R130 §3.7's rule, already recorded under R130 §3.7 at that anchor. By the open draft's §3.2 a clause replaced in part takes the disposition of what remains and names the later clause in its note; what remains of R30 §3.1 is the column and the partition predicate, which the registry carries.
  - *Alternative:* `applied` at Part 06 §4 and §5 would resolve, but it would vouch for the partition MUSTs at sections that do not state them and would lose the guarded pointers to the two rules. `registry` is the better of the two single dispositions the ledger allows.
  - *Still owed:* No part owes the partition rule: both predicates are error-level registry rules.
  - *Ledger today:* Tested on a scratch copy: passes with the three guarded pointers below.
  - *Ledger after draft:* Unchanged by the draft.

### 10. R41 §2.3

- **Reading: confirmed.** Confirmed: the clause is a table declaration the registry carries, with the key R49 §2.3 changed, and Part 01 §2.4 says nothing of it. Change the entry to `registry` with the table pointer, as R49 §2.3 is recorded.
- **Fix or revision:** ledger-only.
- **Where:** revisions/applied.toml, [clause."R41 §2.3"], and revisions/registry-targets.toml
- **Entry:**

  ```toml
  [clause."R41 §2.3"]
  disposition = "registry"
  note = "declared: core.preferred_runs; R49 §2.3 adds scope_kind to its key"
  
  # revisions/registry-targets.toml
  [target."R41 §2.3"]
  locations = [{ path = "spec/artifacts/logical_schemas.json", pointer = "/resources/core.preferred_runs/table" }]
  ```

- **By lens:**
  - *Clause:* A table declaration: new table `core.preferred_runs` with six columns and primary key `(session_id, activity_type, scope)`, so at most one preference per purpose. It carries no keyword.
  - *What became:* Verified. The registry declares `core.preferred_runs` with the clause's columns plus `scope_kind`, and primary key `(session_id, activity_type, scope_kind, scope)`; R49 §2.3 states that key change in terms. Two details the claim omits: the identifiers are `int32` where the clause wrote `string` (R53 makes every identifier `int32`), and `scope`'s description no longer says a session-wide preference names the session.
  - *Target:* Part 01 §2.4 is Provenance and mentions no preference. The number is stale: the Currency text is now §2.6.
  - *Alternative:* `applied` at Part 01 §2.6 is arguable, since it says 'A preference is declared, keyed on the producing run'. That sentence gives the concept and none of what the clause decides (the table, its columns, its key). The ledger disposes the same table's key change, R49 §2.3, as `registry` at `/resources/core.preferred_runs/table`, and R41 §2.1 as `registry`; `registry` is the exact owner and keeps the three entries alike.
  - *Still owed:* No part owes it. Part 02 §11 lists the table and Part 05 §12 states the writer and build duties, which are other clauses'.
  - *Ledger today:* Tested on a scratch copy: passes with the table-level pointer below, which needs no `equals` because it crosses no array; guide §8.1 allows a table pointer where the clause governs the whole declaration.
  - *Ledger after draft:* Unchanged by the draft.
  - *Neighbour:* R41 §2.4 is recorded `applied` at Part 01 §2.4 and its consumer rules are in §2.6; that stale number is outside this class.

### 11. R102 §3.1

- **Reading: corrected.** Corrected: `registry` with a rule still missing is not a coherent entry, and the note's manifest claim is false since R130 §3.7. Restore the conditioned MUST in Part 01 §3.17 and keep the clause `applied` there by anchor; fall back to `registry` only if that restoration is refused.
- **The choice:** The entry follows D4 in class D. If the conditioned sentence is restored in Part 01 §3.17, keep `applied` there by anchor with the corrected note; if it is declined, use `registry` with the pointers given. Either way remove the note's claim about the manifest's field. Use the date of the actual restoration in the note.
- **Fix or revision:** ledger-only for the entry. The part sentence it depends on is a fix in its conditioned form (class D, D4); the bare sentence would change behaviour for the reference LFP and waveform adapters and is not a fix.
- **Where:** revisions/applied.toml, [clause."R102 §3.1"]; registry-targets.toml only for the fallback
- **Entry:**

  ```toml
  # With the conditioned sentence restored in Part 01 §3.17 (recommended)
  [clause."R102 §3.1"]
  disposition = "applied"
  where = [{ part = "01", anchor = "ew-array-asset-concept" }]
  note = "restored 2026-10-01; the writer's obligation to name the run that produced an array, where the packet records that run, was absent. The registry declares processing_run_id on core.array_assets and analysis.array_assets, int32 nullable, each referencing core.processing_runs. R130 §3.7 removes the manifest member this clause kept"
  
  # Fallback, only if the restoration is declined
  [clause."R102 §3.1"]
  disposition = "registry"
  note = "processing_run_id on core.array_assets and analysis.array_assets, int32 nullable, each referencing core.processing_runs; no part states that a produced array names its run; R130 §3.7 removes the manifest member this clause kept"
  
  # revisions/registry-targets.toml, fallback only
  [target."R102 §3.1"]
  locations = [
    { path = "spec/artifacts/logical_schemas.json", pointer = "/resources/core.array_assets/table/columns/8/name", equals = "processing_run_id" },
    { path = "spec/artifacts/logical_schemas.json", pointer = "/resources/core.array_assets/table/references/3/columns", equals = ["processing_run_id"] },
    { path = "spec/artifacts/logical_schemas.json", pointer = "/resources/analysis.array_assets/table/columns/8/name", equals = "processing_run_id" },
    { path = "spec/artifacts/logical_schemas.json", pointer = "/resources/analysis.array_assets/table/references/3/columns", equals = ["processing_run_id"] },
  ]
  ```

- **By lens:**
  - *Clause:* Three things: `processing_run_id` (`int32`, nullable, referencing `core.processing_runs`) on `core.array_assets` and `analysis.array_assets`; an array a run produced MUST name it and an acquired array declares none; and the manifest's field keeps R9 §4's meaning for resources that are not rows.
  - *What became:* Verified. Both tables declare the column at index 8 with a reference at index 3 to `core.processing_runs`. R130 §3.7 says 'The resource-entry member `processing_run_id` MUST be removed without replacement' and 'Row-level `processing_run_id` columns ... are unchanged', so the third thing is gone and the entry's note ('the manifest's field keeps R9 §4's meaning') is now false. The MUST is in no part: `processing_run_id` occurs in the parts only at Part 05 §12.
  - *Target:* Part 01 §3.17 no longer mentions a producing run. It carried the MUST until R128's incorporation removed it under a crosswalk row that sent producing-run statements elsewhere, and no part received it.
  - *Proposed is inconsistent:* `registry` 'with one rule confirmed missing' records a clause as carried while saying part of it is not. The registry does not carry the MUST: the column is nullable and no Tier 2 rule on either array table reads it; the description 'Null means it was acquired rather than computed' is indicative and, by R102 §5 (computed arrays declare null until the packet records their run), not true of every null.
  - *Follows the restoration:* class D judges the restoration safe once conditioned on the packet recording the run, at Part 01 §3.17, as a fix. If that sentence goes in, a part states the clause's keyword rule, and the ledger's practice for a clause with both a column and a stated rule is `applied` with the column in the note (R102 §3.2 and §3.3, and this entry before R128). `registry` is right only if the restoration is declined.
  - *Ledger today:* Tested on a scratch copy: the `applied` form by anchor resolves (`ew-array-asset-concept` is canonical in Part 01); the `registry` form passes with the four guarded pointers below.
  - *Ledger after draft:* Either form is unchanged by the draft. Its §3.2 asks that the note name R130 §3.7, which replaced the manifest half.

### 12. R37 §3.1

- **Reading: keep as applied.** Keep `applied`: Part 01 §3.9 now states both the terminal-anchored formula and the ban on the whole-sequence intercept, and the entry's note records the restoration. The only change worth making is optional, naming the target by its anchor `ew-clock-concept`.
- **Fix or revision:** none: the entry is right as it stands. Moving the target from the section number to the anchor is an optional ledger-only tidy.
- **Where:** revisions/applied.toml, [clause."R37 §3.1"]; states it: Part 01 §3.9 (ew-clock-concept)
- **Entry:**

  ```toml
  [clause."R37 §3.1"]
  disposition = "applied"
  where = [{ part = "01", anchor = "ew-clock-concept" }]
  note = "restored 2026-10-01; the extrapolation from the nearest terminal anchor at the fitted rate, and the prohibition on the whole-sequence intercept, were absent"
  ```

- **By lens:**
  - *Clause:* Two rules: beyond the terminal anchors a consumer MUST compute `parent(t) = parent(a) + rate * (t - a)` with `a` the nearest terminal anchor and `rate` fitted over that clock's anchors; and a consumer MUST NOT use the intercept of a fit over the whole sequence.
  - *Restoration:* Part 01 §3.9 (`ew-clock-concept`) now reads: 'Beyond the terminal anchors a consumer MUST compute the mapping as `parent(t) = parent(a) + rate * (t - a)`, where `a` is the nearest terminal anchor and `rate` is fitted over the clock's full anchor sequence. A consumer MUST NOT extend the terminal segment's slope, and MUST NOT use the intercept of a fit over the whole anchor sequence.' Both rules are stated with the clause's actor and force.
  - *Differences:* 'The clock's full anchor sequence' is narrower than the clause's 'that clock's anchors'; it is R27 §5.3's wording, which the clause itself quotes as already binding, and R40 §3 keeps the globally fitted rate. The middle prohibition on extending the terminal segment's slope is R27 §5.3's, not this clause's, and sits correctly between them. The clause's measured effect is rationale and rightly absent.
  - *Entry:* The ledger entry already reads `applied` at Part 01 §3.9 with the note 'restored 2026-10-01; the extrapolation from the nearest terminal anchor at the fitted rate, and the prohibition on the whole-sequence intercept, were absent', which is accurate.
  - *Target form:* The numeric target `{ part = "01", section = "3.9" }` resolves. The section has a canonical anchor, and the anchor form survives a renumbering; guide §8.1 requires migration only for a structurally affected destination, which a sentence restoration is not. Tested on a scratch copy: the anchor form also passes.
  - *Ledger after draft:* Unchanged by the draft.

# The ledger locks the text an applied clause lands in

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-01 |
| **Based on** | `65d04a5ce0a012f7c4a3fcaf34b1163aadf363a3` |
| **Decision domain** | process |
| **Affects** | the revision guide's ledger dispositions and destination forms at `revisions/CONTRIBUTING.md#ew-current-owner-ledger`; its statement of what the ledger proves at `revisions/CONTRIBUTING.md#ew-process-incorporation-boundary`; its sweep of changed sections; the ledger's row in its table of what each mechanical artifact establishes; its failure-handling rule on a ledger ratchet; the root contribution guide's sentence on the ledger's high-water mark |

## 1. Problem

The clause ledger, `revisions/applied.toml`, records where each Decision clause of each accepted
revision now lives. A clause disposed `applied` names one or more sections of a numbered part or of
the revision guide, and `revisions/ledger.py` checks that each named section exists. The check reads
nothing inside the section. A section can therefore lose the sentence that states a clause, and the
ledger goes on reporting the clause as applied.

The revision guide says that the ledger claims no semantic fidelity and leaves fidelity to review.
That review happens once, when the clause is incorporated. A later change that edits the same
section is not told which accepted clauses the section carries, so nothing asks for the review
again at the moment the text changes.

The same tool has two smaller defects. A `superseded` entry names the revision that replaced its
clause in a field no tool reads. And the check for undisposed clauses is written as a ratchet that
rewrites the ledger from inside the checker, in a branch that can no longer run.

## 2. Evidence

Observed in the tracked files at the baseline commit. The counts come from reading the ledger with
`ledger.py`'s own parser and the headings of the thirteen numbered parts.

### 2.1 The ledger resolves a target and reads no text

For an `applied` entry, `ledger.py` checks the shape of each target, that the named part declares
the section number or the canonical anchor, and that a process target names an anchor of the
revision guide. Its module documentation states that target existence is mechanically checkable
while semantic fidelity remains a review judgment, and the guide repeats this at
`revisions/CONTRIBUTING.md#ew-process-incorporation-boundary` and in its table of what each
mechanical artifact establishes.

A probe confirms it. Five applied clauses land in Part 02 §7.1. With the 1,279 characters of that
section's body removed from a copy of the parts, the ledger's target check reports no dangling and
no malformed target.

### 2.2 A part lacked a clause that the ledger recorded as applied

R8 §4 forbids a value outside a reserved set for data that a reserved value describes. The ledger
records the clause as applied at the Part 02 anchor `ew-registry-vocabularies`, which heads Part 02
§9.3. In the parent of commit `cac91dc083ced39dff98231cad7731d198688647` the one sentence of that
section that mentions a reserved set says what a validator does with a value outside it. The ledger
entry was the same then as it is now apart from a note, and the anchor resolved, which is all the
check asks. The commit added the prohibition. Thirteen applied clauses land in that section.

### 2.3 The applied clauses land in 199 sections

The ledger holds 830 clauses: 501 applied, 177 rationale, 109 registry, 43 superseded, and none
undisposed. The applied clauses name 770 targets, 187 by part and section number, 575 by part and
anchor, and 8 by path and anchor in the revision guide.

Those targets resolve to 199 of the 302 numbered sections of the parts and to 7 anchors of the
guide. A landed section carries a median of 2 clauses and at most 19; 14 sections carry ten or
more. Ten landed sections have subsections.

### 2.4 The heading record already locks one property of a section

`spec/tools/headings.toml` records the heading that each section number carries. `headings.py
--check` fails where a heading differs from the record, and `headings.py` run without the flag
rewrites the record and reports each changed section, so that committing the record states that the
section's citers were read. The record covers a heading and no body text.

The record lives in the specification tree, which a verifier stage regenerates and checks from a
copy holding the tree alone. The ledger, its targets in the revision guide, and the accepted
revisions all live under `revisions/`, outside that copy.

### 2.5 Seven landed sections enclose a generated region

Three parts hold regions that a generator rewrites from a machine-readable source: seven regions in
all, enclosed by nine sections, seven of which carry applied clauses. The text of such a region
changes whenever its source does, with no edit to the part's own prose.

### 2.6 No tool reads a superseded entry's successor

The guide defines `superseded` as a clause that a later accepted revision replaced, and names no
field for the successor. Of the 43 superseded entries, 42 carry `by`, each naming an accepted
revision numbered later than the clause's own. No tool under `revisions/`, `spec/tools/` or `tools/`
reads `by`, so a misspelled or missing successor passes.

The remaining entry, R107 §3.5, carries no `by`. Its clause strikes a requirement that R7 §2 had
set and puts nothing in its place, so no later revision replaced it. Its `where` is a string in a
form the applied targets no longer use.

### 2.7 The ratchet cannot fire

The ledger records `undisposed = 0` as a high-water mark. `ledger.py` fails where the count of
undisposed clauses exceeds the mark, and where the count falls below it the tool rewrites the mark
in `applied.toml` and exits successfully. No count is below zero, so the rewriting branch is
unreachable and the check is already a plain one: any undisposed clause fails.

Four texts still describe a ratchet: the guide's failure-handling rule, which forbids raising one;
the root contribution guide, which says the high-water mark lowers itself; the tool's closing line,
which reports the count as at the recorded mark; and a comment on the verifier's ledger stage.

### 2.8 R120 settled two neighbouring questions

R120 §3.6 forbids making a current owner cite a revision back, and R120 §3.7 removed the check that
did so. R120 §3.7 also forbids either checker to claim semantic fidelity from the existence of a
target, from a backlink, or from a passing test. R120's statement of what it does not change says
that it adds no content hashes; that sentence bounds R120's own scope and decides nothing about a
later revision.

## 3. Desired outcome and constraints

An edit to a section that carries accepted clauses puts those clauses in front of whoever makes the
edit, before the edit is committed. The resolution preserves:

- one-way traceability, under which no current owner cites a revision back;
- R120 §3.7's rule that no checker claims fidelity: a mechanical record states only that a text is
  the text someone last compared with its clauses;
- every accepted revision, unedited;
- silence for a change that alters no prose, such as rewrapped lines or a regenerated region;
- the specification tree's ability to regenerate and check itself alone; and
- a checker that writes no file it checks unless it is asked to.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the ledger as it is | a clause can leave its section unnoticed (§2.2); fidelity is reviewed once and never prompted again |
| record a witness phrase for each applied target and require the section to contain it | detects a lost sentence directly; needs a phrase chosen for each of 770 targets, and fails on any rewording that keeps the meaning |
| record the count of requirement keywords in each landed section | needs no backfill; an edit that removes one requirement and adds another leaves the count unchanged |
| require each landed section to cite the revisions it carries | R120 §3.6 forbids it (§2.8) |
| lock a digest of each landed section, and on a change name the clauses that land there (preferred direction) | needs no backfill and no per-clause authoring; reports any change to the prose, including one that preserves meaning, and leaves the comparison to a reader |

Under the preferred direction the ledger gains a lock, a generated file holding one digest for each
section that an applied clause lands in.

**The digest covers a section and its subsections.** A section runs from its heading to the next
heading of the same or a higher level, which is the extent a citation of that section number names.
An edit inside a subsection therefore changes the digest of each enclosing section that carries
clauses, as well as its own. Ten landed sections have subsections (§2.3).

**Rewrapping and regeneration leave the digest unchanged.** The digest is taken over the section's
text with each run of whitespace collapsed and each generated region left out. A generated region
is a projection whose owner the verifier already compares with it (§2.5).

**A changed digest fails the check and names the clauses.** The ledger check fails where a landed
section's digest differs from the lock, and lists that section with every applied clause landing in
it. A separate invocation rewrites the lock and prints the same list. Committing the rewritten lock
states that each listed clause was read against the changed section, as committing the heading
record states that a section's citers were read (§2.4). The guide's sweep of changed sections gains
this step beside the reading of citers.

**The lock lives beside the ledger.** It is written by the ledger tool and kept under `revisions/`.
The heading record cannot hold it: the specification tree is checked alone (§2.4), the ledger that
says which sections are landed lies outside that tree, and 8 targets land in the revision guide
(§2.3).

**The first lock claims nothing about the past.** It records each landed section as it stands when
the lock is created. A clause already missing from its section, as R8 §4 was (§2.2), stays missing
until someone reads for it. From that point the lock reports every later change.

**A superseded entry names its successor.** `by` becomes a required field of a `superseded` entry
and names an accepted revision numbered later than the clause's own, which the ledger check
resolves. A clause that strikes a requirement and leaves no successor is recorded `applied` at the
section the requirement was struck from, where the lock then covers the absence. R107 §3.5's entry
changes to that form (§2.6).

**The ratchet is removed.** The ledger check fails on any undisposed clause. The ledger loses its
high-water mark, the tool loses the branch that rewrites the ledger, and the four texts of §2.7
describe a plain check.

The cost falls on each later incorporation and each editorial fix to a landed section: the editor
reads the clauses the tool lists, a median of 2 and at most 19 for one section (§2.3), and commits
the lock. The lock does not see a clause's meaning change through an edit elsewhere, such as a
changed definition of a term the section uses. It does not cover the 109 `registry` dispositions,
whose targets the ledger already resolves by pointer with an equality guard.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. The decision is in the process domain and states no packet rule. |
| logical prose, registry meta-schema, declarations and rules | Unchanged. No numbered part, registry or rule is edited. |
| physical profiles | Unchanged. |
| packet manifest and other JSON Schemas | Unchanged. |
| validation and import | Unchanged. No validator or build reads the ledger. |
| extension registries | Unchanged. |
| reader, writer, validator, adapters, code generation | Unchanged. No package reads the ledger or its lock. |
| existing packets | Unchanged. |
| conformance fixtures and implementation tests | No packet fixture. The process tests gain cases: a changed landed section fails and names its clauses; a rewrapped section and a regenerated region pass; a `superseded` entry with no `by`, or one naming no later accepted revision, fails; an undisposed clause fails. |
| revision lifecycle, ledger, evidence and tooling | The revision guide states the lock, its extent and normalization, the relock step in the sweep of changed sections, the required `by`, and the plain undisposed check; its table row for the ledger adds that a landed section is unchanged since it was last read, and its failure-handling rule drops the ratchet. The ledger tool writes and checks the lock. The ledger loses its high-water mark and R107 §3.5's entry changes disposition. Whether the verifier runs the lock check as part of the existing ledger stage or as its own stage is unknown, and either answer leaves the direction unchanged. |
| generated publications and developer documentation | The root contribution guide's sentence on the ledger's high-water mark is restated. No generated publication changes. |

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

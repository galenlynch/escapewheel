# The ledger reads no text of the section a clause lands in

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-01 |
| **Based on** | `61fb6f0732b63ee27820c5c3990b94c887c83caa` |
| **Decision domain** | process |
| **Affects** | the revision guide's destination forms at `revisions/CONTRIBUTING.md#ew-current-owner-ledger`; its statement of what the ledger proves at `revisions/CONTRIBUTING.md#ew-process-incorporation-boundary`; its sweep of changed sections; the ledger's row in its table of what each mechanical artifact establishes |

## 1. Problem

The clause ledger, `revisions/applied.toml`, records where each Decision clause of each accepted
revision now lives. A clause disposed `applied` names one or more sections of a numbered part or of
the revision guide, and `revisions/ledger.py` checks that each named section exists. The check reads
nothing inside the section.

Two failures pass that check. A clause can be recorded as applied at a section that never stated it,
and a section can later lose the sentence that stated a clause. The first has happened and was found
by hand (§2.2). The second has no recorded instance, and the check could not have shown one.

The revision guide says that the ledger claims no semantic fidelity and leaves fidelity to review.
That review happens once, when the clause is incorporated, and nothing records which text the
reviewer took to state the clause.

A companion proposal, `the-ledger-resolves-a-superseded-entrys-successor-and-keeps-no-ratchet.md`,
carries two smaller defects of the same tool. Neither proposal depends on the other.

## 2. Evidence

Observed in the tracked files at the baseline commit unless a subsection says otherwise. The counts
come from reading the ledger as TOML and the headings of the thirteen numbered parts.

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

### 2.2 Two clauses were recorded as applied at sections that never stated them

R8 §4 forbids a value outside a reserved set for data that a reserved value describes. The ledger
records the clause as applied at the Part 02 anchor `ew-registry-vocabularies`. In the parent of
commit `cac91dc083ced39dff98231cad7731d198688647` the one sentence of that section that mentions a
reserved set says what a validator does with a value outside it, and the commit added the
prohibition.

R3 §7.1 requires an array to be little-endian and to set `fill_value` explicitly. The ledger records
the clause as applied at Part 03 §6.1, and a case-insensitive search of the thirteen parts for
`endian` and for `fill_value` finds no occurrence.

A search of the history of both parts finds no commit that removed either rule. Both are omissions
at incorporation, and no later edit lost them.

### 2.3 Forty-three ledger notes record text restored on one day

The ledger carries 48 notes that say a clause's text was restored. Of these, 43 are dated
2026-09-04 and one is dated 2026-10-01, the R8 §4 repair of §2.2.

R3 §7.1's note is one of the 43: it says that the regular chunk grid was absent and was restored.
That reading left the clause's byte-order and `fill_value` sentences unfound (§2.2). The ledger
records one disposition for a clause, and a clause can hold several rules.

### 2.4 The applied clauses land in 199 sections

The ledger holds 830 clauses, of which 501 are applied. The applied clauses name 770 targets: 187
by part and section number, 575 by part and anchor, and 8 by path and anchor in the revision guide.

Those targets resolve to 199 of the 302 numbered sections of the parts and to 7 anchors of the
guide. A landed section carries a median of 2 clauses and at most 19, and 14 sections carry ten or
more. Ten landed sections have subsections.

### 2.5 The heading record already locks one property of a section

`spec/tools/headings.toml` records the heading that each section number carries. `headings.py
--check` fails where a heading differs from the record, and `headings.py` run without the flag
rewrites the record and reports each changed section, so that committing the record states that the
section's citers were read. The record covers a heading and no body text.

The record lives in the specification tree, which a verifier stage regenerates and checks from a
copy holding the tree alone. The ledger, its targets in the revision guide, and the accepted
revisions all live under `revisions/`, outside that copy.

### 2.6 Seven landed sections enclose a generated region

Three parts hold regions that a generator rewrites from a machine-readable source: seven regions in
all, enclosed by nine sections, seven of which carry applied clauses. The text of such a region
changes whenever its source does, with no edit to the part's own prose.

### 2.7 A section digest would have changed in 80 of 180 commits

A replay measured what a digest of each landed section would have reported. It covers the
first-parent commits that touch a numbered part from 2026-09-06, the first commit holding the
ledger as a file, to 2026-10-01. For each commit it takes the landed sections from the parent's ledger and
compares each section's text before and after, with whitespace collapsed and with generated regions
and anchor lines left out. A section includes its subsections.

| commits | count | changed a landed section | sections changed | clauses listed | median per changing commit |
|---|---:|---:|---:|---:|---|
| adding an accepted record | 68 | 61 | 577 | 2,026 | 5 sections, 20 clauses |
| any other | 112 | 19 | 68 | 282 | 2 sections, 7 clauses |
| all | 180 | 80 | 645 | 2,308 | 3.5 sections, 16 clauses |

The largest commit changed 108 landed sections carrying 293 clauses. Collapsing whitespace and
leaving out generated regions silenced 3 commits that would otherwise have reported.

Of the 645 changed sections, 54 only gained paragraphs. The other 591 removed or altered a
paragraph, 1,201 paragraphs in all. A changed section lists every clause landing in it, so the
2,308 listings count a clause once for each commit that changed its section, whichever paragraph
changed.

The landed sections grew from 62 to 199 over the period, so the same replay over a later period
would report more.

### 2.8 R120 settled two neighbouring questions

R120 §3.6 forbids making a current owner cite a revision back, and R120 §3.7 removed the check that
did so. R120 §3.7 also forbids either checker to claim semantic fidelity from the existence of a
target, from a backlink, or from a passing test. R120's statement of what it does not change says
that it adds no content hashes; that sentence bounds R120's own scope and decides nothing about a
later revision.

### 2.9 Nine of forty sampled targets do not fully state their clause

A sample of 40 of the 770 targets, drawn with a fixed seed, was read once against the target
section, and the reading was not reviewed. Each target was classed by whether the section states the
clause's rules, and a passage was quoted for each rule found.

| result | targets |
|---|---:|
| the section states the clause | 31 |
| the section states part of it, and a rule is weakened or missing | 6 |
| the section states none of it | 3 |

The six partial targets include a recommendation that the section states as a permission, a
requirement that the section states in the indicative, and four whose sentences appear in no part. Of the three absent
targets, two belong to clauses with a second target that states the rule, and one names a section
number whose subject is now in the section after it.

A quotable passage existed wherever the rule did. Of the 37 targets with any stating text, 13 were
covered by one passage, 20 needed two or three, and 4 had the rule spread across a list and its
lead-in so that no one excerpt held both the keyword and the content. The 76 quoted passages have a
median of 21 words and a maximum of 68. Of the 76, 31 span a line wrap and seven are table rows.

Five of the 40 targets belong to a clause with several targets and no note saying which rule lands
at which. For those the reading had no defined share to look for.

## 3. Desired outcome and constraints

The ledger records which text states each applied clause, an applied clause with no such text is
found, and an edit that removes that text is reported with the clause it stated. The resolution
preserves:

- one-way traceability, under which no current owner cites a revision back;
- R120 §3.7's rule that no checker claims fidelity: a mechanical record states only that the text
  someone identified as stating a clause is still present;
- every accepted revision, unedited;
- silence for a change that alters no prose, such as rewrapped lines or a regenerated region;
- silence for an edit that leaves a clause's own statement alone;
- the specification tree's ability to regenerate and check itself alone; and
- a checker that writes no file it checks unless it is asked to.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| keep the ledger as it is | a clause can be recorded at a section that does not state it (§2.2), and a later loss would go unreported |
| lock a digest of each landed section, and on a change list the clauses that land there | needs no authoring for the existing targets; reports 61 of 68 incorporations with a median of 20 clauses to re-read (§2.7); finds no clause that was never stated, since the first digest records each section as it stands |
| report the clauses of each changed landed section when asked, and store nothing | costs nothing to keep; cannot fail a check, and has the digest's volume and its blindness to the past |
| record the count of requirement keywords in each landed section | needs no authoring; an edit that removes one requirement and adds another leaves the count unchanged |
| require each landed section to cite the revisions it carries | R120 §3.6 forbids it (§2.8) |
| record, for each applied target, a passage of the section that states the clause, and require the section to contain it (preferred direction) | finds a never-stated clause when the passage is first sought; reports only an edit to the stating text; needs a passage chosen for each of 770 targets, and reports a rewording that keeps the meaning |

Under the preferred direction an applied target gains a **witness**: one or more passages quoted
from the target section that together state the clause's rule there.

**The check compares text and claims no fidelity.** The ledger check fails where a target section
does not contain a witness passage, comparing with each run of whitespace collapsed, and names the
clause and the passage. A present witness shows that the text a reviewer identified is still in
the section. It does not show that the text is faithful to the clause.

**A new target carries a witness from incorporation.** The guide's step that records clause
destinations asks for the passage, which makes the reviewer of an incorporation point at the
sentence. An omission of the kind in §2.2 then fails at the incorporation that makes it.

**The existing targets are witnessed by one audit.** Each of the 770 targets is read against its
section. A target with no stating text is a finding, resolved by the ordinary process: the rule is
restored where the omission was an error, or a later revision supersedes it, or the entry's
disposition or target is corrected. The audit is what finds the remaining clauses of the §2.2 kind,
which a digest never would. The sample of §2.9 found 9 such targets in 40, which projects to
roughly 170 of the 770, with a wide margin on a sample that small.

**A target of a multi-target clause says which rule it carries.** Its witness is the passage for
that rule, so the audit gives each such target the share that §2.9 found undefined.

**An edit to a stating passage is reported once, for its own clause.** Rewording a witnessed
sentence fails the check until the entry quotes the new text, and updating the quotation states
that the clause was read against the new sentence. An edit elsewhere in the section reports
nothing. The 1,201 altered paragraphs of §2.7 bound the reports the replayed period would have
drawn, since a report needs an altered paragraph that holds a witness.

**A witness may be several passages or a table row.** A rule spread across a list and its lead-in
is witnessed by both (§2.9). A weakened keyword is found by the reader choosing the passage and not
by the check, which compares text.

**A witness is prose of the part.** A passage inside a generated region is not eligible (§2.6): its
owner is the machine-readable source, and a clause whose rule lives only there is disposed
`registry`.

**The witnesses live in the ledger.** They sit beside the targets they describe, under `revisions/`.
The heading record cannot hold them: the specification tree is checked alone (§2.5), and 8 targets
land in the revision guide (§2.4).

The cost is the audit and a passage for every later target. The preferred direction does not see a
clause's meaning change through an edit elsewhere, such as a changed definition of a term the
passage uses. It does not cover the 109 `registry` dispositions, whose targets the ledger already
resolves by pointer with an equality guard.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged by the decision. The audit may find a clause no part states, and each such finding is repaired by its own change. |
| logical prose, registry meta-schema, declarations and rules | Unchanged. |
| physical profiles | Unchanged. |
| packet manifest and other JSON Schemas | Unchanged. |
| validation and import | Unchanged. No validator or build reads the ledger. |
| extension registries | Unchanged. |
| reader, writer, validator, adapters, code generation | Unchanged. No package reads the ledger. |
| existing packets | Unchanged. |
| conformance fixtures and implementation tests | No packet fixture. The process tests gain cases: a section lacking a witness passage fails and names the clause; a rewrapped section passes; an edit to another paragraph of the section passes; an applied target with no witness fails once the audit is complete. |
| revision lifecycle, ledger, evidence and tooling | The revision guide states the witness, its comparison, and its place in the step that records clause destinations and in the sweep of changed sections; its table row for the ledger adds that each applied clause's identified text is present. The ledger tool checks witnesses. The ledger gains a witness for each applied target, and a note of its share for each target of a multi-target clause. Unknown: how many targets the full audit finds unstated; the sample of §2.9 suggests about a fifth. |
| generated publications and developer documentation | Unchanged. |

## 6. Open questions

1. Is the audit's cost accepted? It reads 770 targets and, on the sample's rate, raises about 170
   findings, each needing a restoration, a supersession or a corrected entry. Declining it leaves
   the digest or the current ledger, and neither finds those targets.
2. Does the check require a witness of every applied target from the day it lands, which makes the
   audit a precondition of incorporation, or only of targets added afterwards, with the audit
   proceeding part by part?
3. Is the diff-time report of §4's third row worth keeping beside the witness, for an editor who
   wants the clauses of a section before changing it?

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [ ] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

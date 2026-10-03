# A change is one document from Open to Accepted

| | |
|---|---|
| **Status** | **Accepted** 2026-10-02 |
| **Based on** | `9462b393a00e9e681b7a38528112483b6a5aa206` |
| **Decision domain** | process |
| **Change form** | ordinary |
| **Amends** | `revisions/CONTRIBUTING.md#ew-revision-scope`; `revisions/CONTRIBUTING.md#ew-decision-domains`; `revisions/CONTRIBUTING.md#ew-baseline`; `revisions/CONTRIBUTING.md#ew-proposal-evaluation`; `revisions/CONTRIBUTING.md#ew-draft-writing`; `revisions/CONTRIBUTING.md#ew-citation-context`; `revisions/CONTRIBUTING.md#ew-structural-reorganization`; `revisions/CONTRIBUTING.md#ew-pre-acceptance-gates`; `revisions/CONTRIBUTING.md#ew-structural-reorganization-sequence`; `revisions/CONTRIBUTING.md#ew-acceptance`; `revisions/CONTRIBUTING.md#ew-current-owner-ledger`; `revisions/CONTRIBUTING.md#ew-process-incorporation-boundary`; `revisions/CONTRIBUTING.md#ew-mechanical-artifacts`; `revisions/CONTRIBUTING.md#ew-failure-handling`; `revisions/CONTRIBUTING.md#ew-length-and-focus` |
| **Depends on** | R120 §3.1 and §3.2 (decision domains and lifecycle metadata); R158 §3.1 and §3.2 (a superseded entry's successor and a clause replaced in part) |
| **Profile** | not applicable |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

The revision guide, `revisions/CONTRIBUTING.md`, carries a change to the specification through two
documents. A proposal under `revisions/proposals/` states the problem, evidence, options and
questions. Once the reviewer approves promotion, its facts are carried into a new revision draft
under `revisions/drafts/`, which states the candidate rule, and the proposal is deleted. The stage
check, `revisions/stages.py`, checks a different header and heading set for each.

This revision makes the two one document. A change document keeps one file from the moment it is
opened until it is accepted, and its status says how far it has come: Open while its questions are
being answered, Ready once they are answered and it states its Decision, and Accepted when the
reviewer authorizes it.

It separates the rules of the lifecycle from advice on working within it. The rules are what a
change document carries at each status, who authorizes acceptance, and what the process tools
check. How to appraise a change before asking for acceptance, how to keep it fresh against its
baseline and how to keep it focused become guidance that binds no one.

It also settles two process questions that the current guide answers differently from the accepted
records. The guide's ledger section no longer asks a ledger entry for a note, while R158 §3.2 still
requires one; this revision ratifies the guide. And the guide's scope sends a change to the guide
itself through the full revision lifecycle; this revision returns such changes to the ordinary
repository workflow, under the reviewer's approval.

It changes no packet requirement, numbered part, registry declaration, schema or package behavior.

## 2. Background

Counts below were taken at the baseline commit, by reading `revisions/applied.toml` as TOML and the
repository history with `git log`.

### 2.1 Promotion rewrites a document

The history holds 38 commits whose subject begins `docs(revisions): promote`. A promotion does not
extend a proposal. It deletes it and writes a draft from it, under a different header and a
different heading set: Problem, Evidence, Desired outcome and constraints, Options and tradeoffs and
Impact sketch become Scope, Background, Decision and Consequence.

The most recently accepted revision, R165, shows the cost. Its proposal was revised and had its last
answers recorded. Its promotion deleted the 348-line proposal and added a 304-line draft, which was
revised again before acceptance. The problem statement and evidence were the same facts in two
files, and what the draft added was the normative text that acceptance approves.

### 2.2 Most pre-acceptance gates are judgment, not checks

The guide's §6 lists seven gates to pass, in order, before acceptance is requested. Its mechanical
gate runs the stage, citation, repointing and verifier checks, each of which fails a defect without
anyone's judgment. The other six ask whether the baseline is still the relevant one, whether
overlapping work is ordered, whether each rule sits with its owner, whether each obligation is
feasible, whether compatibility is stated and whether the impact inventory is complete. Those
questions are answered by reading, and the reviewer weighs the answers when deciding whether to
authorize acceptance.

Stated as requirements, they make the lifecycle depend on a way of working: an appraisal in a set
order, recorded in a README row with its date, baseline and word count. The same holds for the
baseline steps of the guide's §3, the proposal steps of its §4 and the advice on length in its §14.
What binds an author is what the reviewer will authorize and what the tools fail.

### 2.3 Ledger notes are unchecked and drift

The ledger holds 877 entries, which carry 879 `note` fields on 726 of them, at the top level of an
entry or inside one of its destinations. The ledger check reads a note only to confirm that it is a
string, and no other tool reads one.

A note restates, in free text, what the entry's disposition and destination already prove, and it
goes stale when a later revision changes the rule. The entry for R69 §2.3 is `registry`, and its
note names the rule `core.media_frames.pts_increasing_in_frame_index`. The registry target the same
clause pins, and the registry itself, name `core.media_frames.pts_increases_with_frame_index`. No
check could have caught the difference.

R158 §3.2 requires an entry for a clause replaced only in part to name the later clause in its
note, and R158 §3.1 permits a `superseded` entry's note to name the replacing clause. The guide's
ledger section, edited on 2026-10-02 by an ordinary commit, now says that a new entry and a new
destination carry no note and that existing notes are not maintained. The guide and the accepted
record disagree, and the guide is the current owner.

### 2.4 The guide's own changes pass through the lifecycle

The guide's §1 lists, among the changes that need this process, a change to "a lifecycle gate,
process authority, structural-editing permission, ledger disposition, or evidence meaning defined
by this guide". R120 §3.1 introduced the process decision domain for such changes. Two accepted
revisions, R120 and R158, are process-domain records.

A process change has no packet to rebuild, no implementation that could diverge, and no reader
outside this repository. What its acceptance supplies is the reviewer's approval, which a guide
commit can carry directly; the lifecycle adds two documents, a revision number, ledger entries and
an evidence manifest to a change whose only owner is the guide that states it. The ledger entries
of R120 and R158 point at 14 destinations in the guide, across 11 clauses.

The threshold for a revision number stays where it is: a change to the packet contract or to an
artifact that owns part of it gets a number when it is accepted. Only the guide's account of its
own procedure leaves the lifecycle.

### 2.5 Where the document lives

A change document needs one directory. Keeping `proposals/` would name a Ready document wrongly,
and keeping `drafts/` an Open one. A directory named for a status would collide with that status.
`revisions/changes/` names what the directory holds whatever its status.

### 2.6 Alternatives

Keeping both documents and making promotion a rename would keep the file's history but would still
change the header and every heading, so the document would be rewritten in place.

Keeping the pre-acceptance gates binding but shorter would still leave the lifecycle's validity
resting on judgments no tool can decide, which the reviewer already makes when authorizing.

Keeping the process domain while exempting small guide edits would need a line between a small and
a large process change, and the reviewer approves both kinds alike.

## 3. Decision

The seven clauses below define the change document and its statuses, what an Open and a Ready
document carry, what the process tools check, how ledger entries are recorded, and how the revision
guide itself changes.

### 3.1 One change document carries a change from Open to Accepted

A specification change **MUST** be carried by one change document, at
`revisions/changes/<slug>.md`, from the commit that opens it until its acceptance. Its status
**MUST** be Open or Ready while it is under `revisions/changes/`. A change from Open to Ready
**MUST** be made by editing the document in place.

Only the reviewer may authorize acceptance, and acceptance **MUST NOT** proceed without the
reviewer's explicit authorization of the document's text. On that authorization the document is
numbered `R<N>` from the end of the accepted range, moved to `revisions/accepted/R<N>-<slug>.md`
and given the Accepted status with its date. A change document **MUST NOT** carry a revision number
before then. A later change to a Decision clause, a compatibility effect, a required implementation
surface or a feasibility claim returns the document to Ready, and acceptance then needs the
reviewer's authorization again.

A document of either status is withdrawn by deleting it in a commit whose message records why,
after any finding worth keeping has been committed.

A rule of the revision guide that applies to a proposal applies to an Open document, and a rule that
applies to a revision draft applies to a Ready document, except where this revision states
otherwise. A change document **MAY** cite another by its file name. An accepted revision **MUST
NOT** cite a document that has not been accepted.

### 3.2 An Open document states the problem, the evidence, a preferred direction and its questions

An Open document **MUST** declare its status as Open, the date it was opened, its full `Based on`
commit hash, and the concepts and current locations it affects. It **MUST** state, in this order:

1. the problem and the boundary of the change;
2. the evidence, and the alternatives considered with their costs;
3. the preferred direction;
4. the questions that must be answered before the Decision can be stated; and
5. a sketch of the consequence, with each affected surface marked affected, unchanged with a reason,
   or unknown.

An answer **MUST** be recorded in the document beneath the question it answers. An Open document
**MUST NOT** prescribe behavior with BCP 14 keywords.

### 3.3 A Ready document has answered its questions and states its Decision

A Ready document **MUST** declare its status as Ready, the date it was opened, its full `Based on`
commit hash, its change form, what it amends, what it depends on, its profile, and its Decision
clauses. It keeps the problem, evidence and questions of §3.2, replaces the preferred direction with
the normative Decision as its section 3, and adds the complete impact inventory and its conformance
and implementation evidence. Every question **MUST** carry its recorded answer.

A document **MAY** be opened Ready when its problem and direction need no question answered. A
document becomes Ready when its questions are answered and its Decision is written; no
authorization other than those answers is required.

### 3.4 The process tools check structure, citations and the ledger

The stage check **MUST** fail, naming the document:

- a document under `revisions/changes/` that lacks a field or a section its status requires,
  declares a status other than Open or Ready, or carries a revision number;
- an Open document that prescribes behavior with a BCP 14 keyword;
- a Ready document with a question that has no answer, or with no Decision section, or whose
  `Decision clauses` do not enumerate exactly the clauses under its section 3; and
- a document under `revisions/proposals/` or `revisions/drafts/`.

The citation check **MUST** fail a citation in a change document or an accepted revision that does
not resolve or does not use the required spelling, and a citation in an accepted revision of a
document that has not been accepted.

The ledger check **MUST** fail, naming the clause, where a Decision clause of an accepted revision
has no ledger entry, where an entry's disposition is not one of `applied`, `registry`,
`superseded` and `rationale`, and where a destination it names does not resolve.

Beyond these checks, the conditions of §3.1 to §3.3 and the reviewer's authorization, no
requirement governs whether a change document may be accepted. The revision guide's advice on
appraising a change before acceptance, refreshing it against its baseline, ordering it against
overlapping work and keeping it focused is informative.

### 3.5 A new ledger entry carries no note

A ledger entry or destination recorded for a clause of this revision or a later one **MUST NOT**
carry a `note`, and the ledger check **MUST** fail one that does. A later revision **MUST** leave an
existing entry unchanged unless it supersedes that entry's clause whole or moves the clause's rule
to a destination the entry does not name. A note that an existing entry carries is not maintained,
and a stale one is left as it stands.

A clause that a later revision replaced only in part is not `superseded`; its entry keeps the
disposition of the part that remains and names no later clause.

### 3.6 The revision guide changes by the ordinary workflow

This lifecycle governs changes to the packet contract, to an artifact that owns part of it, and to
the composition or identity of a specification release. It **MUST NOT** be required for a change to
the revision guide, its templates or its process tools.

Such a change **MUST** be made as an ordinary repository commit that the reviewer has approved, and
it carries no change document, revision number, ledger entry or evidence manifest. It **MUST**
update in the same commit the templates, tools, tests and documents that implement or describe the
rule it changes. Only the reviewer may approve a change to the guide.

A change document **MUST NOT** declare a decision domain. An accepted record keeps the domain it
declares, and a record that declares none is read as specification.

### 3.7 A guide change keeps the ledger's destinations in the guide resolving

Where an accepted record's ledger entry names a section of the revision guide, a commit that
changes the guide **MUST** keep that entry resolving. Where the commit moves the rule the entry
names, it **MUST** update the entry's destination. Where it removes that rule whole, it **MUST**
give the entry the `rationale` disposition. Where it changes the rule only in part, the entry is
left as it stands. A guide section that such an entry names keeps its canonical anchor.

## 4. What this does not change

Acceptance still requires the reviewer's explicit authorization, and acceptance and incorporation
are still one commit. An accepted record, its ledger entries other than as §3.7 requires, and its
evidence manifest are unchanged, including the domain R120 and R158 declare. The four ledger
dispositions keep their meanings. The ordinary and structural change forms, the anchor rules and
the anchor bootstrap a structural change makes, the crosswalk it carries and the incorporation
sequence are unchanged.

## 5. Consequence

No packet, part, registry, schema or package changes, so no packet is rebuilt and no release
identity moves. The cost is confined to `revisions/`, two rows of the root contribution guide, the
documents-count tool and the citation check.

Every proposal and draft open at incorporation moves into `revisions/changes/` with the status of
its stage, Open for a proposal and Ready for a draft. Its header takes the fields of §3.2 or §3.3 and
its sections take the required headings; its Decision text and recorded answers are carried
unchanged. The application order moves into the new directory's guide.

The guide's workflow material moves, unchanged in substance, into a new informative section at the
end of the guide that says it binds no one:

| material | current place | after incorporation |
|---|---|---|
| a critical appraisal of the Ready text, with its findings reported, before acceptance is requested | §6 preamble and §6.7 | guidance section; the revisions directory's agent instructions gain one line asking for it |
| the order of the gates, and that a later one does not excuse an earlier failure | §6 preamble | dropped |
| freshness against `Based on`: rerun counts, recheck after another revision lands | §3 steps 3 to 5 and closing paragraph; §6.1 | guidance section |
| overlap with open changes and their order | §3 step 4; §4.4; §6.1 | guidance section |
| ownership, structural, feasibility, compatibility and traceability questions | §4.1 to §4.7; §6.2 to §6.6 | guidance section, as one appraisal checklist |
| reading every citation for meaning, not only resolution | §6.7 | guidance section; the resolution and spelling stay checked under §3.4 |
| the appraisal record in a README row: date, baseline, word count, finding | §6.7; the drafts README's appraisal and word columns | guidance section; the changes README keeps the order and placement columns |
| committing the exact text before asking for acceptance | §4.8; §6.7 | guidance section; the promotion check of §4.8 is removed with promotion |
| length and focus, and when to split a change | §14 | guidance section |

The failure-handling list of §13 returns a changed decision to Ready and the reviewer's
authorization rather than to draft appraisal. The anchor bootstrap of §6.8 stays as it is, since a
process check compares the bootstrap commit with its parent.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged: the decision is in the process domain and states no packet rule. | No numbered part differs from the baseline. |
| logical prose and registry | Unchanged: no part, registry declaration or rule is edited. | The registry checks pass unchanged. |
| physical profiles | Unchanged: no profile is edited. | The profile descriptors are byte-identical. |
| packet manifest and JSON Schemas | Unchanged: no schema is edited. | The schemas are byte-identical. |
| validation and import | Unchanged: no validator or build reads a change document. | The conformance corpus passes unchanged. |
| extensions | Unchanged: no extension registry is edited. | The extension registry checks pass unchanged. |
| reader, writer, validator, adapters | Unchanged: no package reads a change document or the ledger. | The package suites pass unchanged. |
| conformance fixtures and tests | No packet fixture. The process tests gain the cases of §6, and the tests of process-domain metadata on an open document are replaced. | The process tests pass. |
| revision process and tooling | The guide's scope loses its process bullet and gains §3.6; its artifacts table, gates and phases name one change document and its three statuses; promotion becomes the change of status; §3.4, the ledger rule of §3.5 and the upkeep of §3.7 are stated; the workflow material moves as tabled above. One change template replaces the proposal and draft templates, and the accepted template follows its headings. The stage check reads `revisions/changes/`, checks the fields and headings of each status and the answers of a Ready document, and accepts an accepted record from this revision onward with no domain. The ledger check fails a note on an entry of this revision or later. The citation check reads change documents in their own pass. | `stages.py`, `ledger.py`, `check_citations.py` and `verify.py --quick` pass; the evidence manifest places §3.1 to §3.7 at the amended anchors. |
| generated publications and developer documentation | The revisions guide's lifecycle table, the change directory's guide, the template guide and the root contribution guide's file table name one change document; the document-count tool counts Open and Ready documents. No generated publication changes. | A search of the tracked Markdown and Python for `proposals/` and `drafts/` finds only accepted records and history. |

## 6. Conformance and implementation evidence

The decision is checked by process tests and by no packet fixture.

Positive cases:

- an Open document with the fields and sections of §3.2, and questions some of which are
  unanswered, passes the stage check;
- a Ready document with the fields and sections of §3.3 and an answer beneath every question passes;
- an accepted record numbered after this revision with no decision domain passes, and R120 and
  R158 still pass with theirs; and
- the ledger as incorporated passes, with this revision's entries carrying no note.

Negative cases, each failing and naming the document or clause:

- a Ready document with a question that has no answer;
- an Open document that prescribes behavior with a BCP 14 keyword;
- a change document under `revisions/changes/` that declares a decision domain, carries a revision
  number, or declares a status other than Open or Ready;
- a document left under `revisions/proposals/` or `revisions/drafts/`; and
- a ledger entry, or a destination within one, for a clause of this revision or a later one that
  carries a `note`.

The reviewer's authorization in §3.1, §3.6, and the part of §3.7 that chooses between updating and
retiring an entry bind the reviewer and the author of a guide change; no tool checks them. The
ledger check already fails an entry whose destination no longer resolves.

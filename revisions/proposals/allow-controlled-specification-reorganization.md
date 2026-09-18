# Allow Controlled Reorganization of the Working Specification

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-17 |
| **Based on** | `15cf4e16cae5e197db55af6598d32bceeb0c5ed6` |
| **Affects** | Part 00 §10.3; R112 §3.4; stable section anchors; current and historical citation rules; incorporation, heading, impact, ledger, and evidence procedures; the authority draft's landing plan |

## 1. Problem

Part 00 §10.3, incorporating R112 §3.4, requires every new section or subsection to be appended.
That rule is valuable for an ordinary amendment: existing section citations keep their target, and
a small change cannot casually reorganize unrelated prose. It is unconditional, however. It also
applies when the purpose of a revision is to repair the specification's organization.

The current authority draft exposes the resulting conflict. Its subject is the framework that
explains the specification's authority, abstraction levels, part ownership, status, conformance,
and references. Under the current rule, that framework would be added after Part 00's implementation
thesis, part-status table, and citation rules. Normative material moved out of the specification
README would likewise be appended to the ends of its subject-owning parts even when it belongs near
their scopes or definitions. The identifiers would remain stable, but the document would teach its
organizing model after the material that depends on it.

Citation stability and coherent organization are not mutually exclusive. Current references need
current targets. Historical references need the Git commit in which they were valid. References
to an edition that the publication rules declare immutable need that edition's unchanged bytes.
Stable section anchors can identify a subject independently of its displayed number within the
unpublished working specification and across later editions. This proposal governs those editing
and reference mechanics; it does not decide which artifacts are authoritative or what constitutes
a candidate or published release.

A silent exception is not acceptable. It would leave Part 00, the lifecycle guide, and the tools
describing a rule the project no longer follows. The process needs a narrow, auditable exception
before the authority draft can rely on it.

## 2. Evidence

### 2.1 Current rule and baseline

At the baseline commit, Part 00 §10.3 says that whoever amends a part adds at the end and does not
insert between existing sections. R112 §3.4 is the accepted decision from which that text came.
The lifecycle guide repeats the same policy in Phase E: new prose is appended so citations retain
their numbers.

The quick repository verifier passed all 24 stages at the baseline. It reported 262 recorded
sections across 11 parts, no repeated part numbers, no unresolved live citations, no undisposed
revision clauses, and one open draft. The first invocation could not write the environment's
default `uv` cache; rerunning the same command with `UV_CACHE_DIR=/tmp/uv-cache` passed. This is an
environment constraint, not a baseline defect.

Before this proposal was added, the stage inventory contained no proposal and one draft:
`define-specification-artifacts-and-normative-ownership`. There is no configured Git remote, and
the project has no known external consumers whose section links require a compatibility period.
The process should nevertheless establish a release-safe model rather than depend on that
temporary fact.

### 2.2 The authority draft is a concrete counterexample

Part 00 currently proceeds from scope and definitions through packet organization, storage stance,
an implementation thesis, part status, and citation rules. The authority draft needs to make the
specification framework antecedent to those details. Appending a new final framework section would
make it formally reachable but pedagogically inverted.

The same problem recurs across the numbered parts. For example, unit identity is already owned by
Part 02, while the contradictory statement appears in Part 00 §4.3. Moving such a statement to its
owner, or removing it in favor of the owner's rule, is a structural repair. Adding another section
at the end of Part 00 cannot remove the misplaced abstraction, and adding a duplicate at the end of
Part 02 creates another statement to reconcile.

The authority draft's first pre-acceptance appraisal therefore found that an append-only landing
plan would preserve numbering at the expense of the ownership and comprehensibility the draft is
intended to establish. The draft remains non-authoritative and can wait on this prerequisite.

### 2.3 The repository already has most of the required controls

Every current proposal and draft records a full `Based on` commit. Git retains every accepted
revision and the incorporation commit in which its references were valid. The citation checker
already distinguishes live sources from accepted historical revisions: a missing current target
fails, while an old accepted reference is reported as history rather than silently rewritten.

`escapewheel_poc_docs_v0.2/headings.py` records each current section number and heading. It reports
a changed or removed heading and lists known citers. `revisions/impact.py` provides the reverse
lookup from a current section to tracked citers. `check_citations.py` rejects duplicate numbers and
unresolved live citations. `ledger.py` verifies that every accepted decision clause has a current
destination, and `evidence.py` verifies the owners recorded by current-format evidence manifests.

The ledger currently has 375 applied targets across 125 part sections. Twenty-one targets point
into 11 sections of Part 00. A reorganization therefore has to update more than prose citations,
but those current destinations are already explicit and checked; they do not need a second
historical relocation database.

`combine.py` concatenates the authored Markdown without interpreting it. Explicit HTML anchors in
the part sources would therefore survive in both the individual parts and the combined rendering.
A checker can associate each anchor with the numbered heading that immediately follows it.

### 2.4 Established specification patterns

The proposed model combines three established patterns:

- The [RFC Series](https://www.rfc-editor.org/series/rfc/) treats a published RFC as archival.
  Changes are published in another identified document, with update and obsolescence relationships,
  rather than by renumbering the published document in place.
- [W3C publication rules](https://www.w3.org/pubrules/doc/rules/?profile=STMT) distinguish a dated
  version, a latest version, and a history. That separates a stable reviewed snapshot from an
  evolving entry point.
- [RFCXML](https://www.rfc-editor.org/rfc/rfc7991.html) gives document elements explicit anchors,
  while [Bikeshed](https://speced.github.io/bikeshed/) supports explicit heading IDs, aliases for old
  IDs, and checks for required IDs. Section identity therefore need not be the displayed number.

These patterns do not require paragraph hashes or a cross-version graph for every prose block. A
full requirements-object system would provide that machinery, but it would make the specification
source and its change history into another data model. Escapewheel needs data-driven packet
contracts; it does not need a requirements database to reorganize an unpublished draft.

### 2.5 References have three different time contexts

A reference in the current specification, implementation, test, or developer documentation is
live and needs to resolve against the current working specification. A structural incorporation
updates every such reference it affects.

An accepted revision is historical. Its incorporation commit is the first commit in its file
history, following renames, whose metadata records `Status` as `Accepted`; if the file was already
accepted when first introduced, that introduction commit is the incorporation commit. The citation
checker resolves its references against the specification sources present in that commit rather
than merely exempting them from current resolution. For current-format revisions, `Based on`
separately records the pre-change state against which the draft was appraised. Historical files are
not edited merely to name the current organization.

Some early revisions predate the v0.2 source layout and current citation form. Incorporation of
this process change includes an audit that either resolves each such citation against the source
tree present in its incorporation commit or records it in an exact, reviewed legacy-exception
inventory. That inventory is a compatibility baseline, not a general exemption: later revisions
cannot add entries, and existing entries are removed when they become mechanically recoverable.
No citation passes merely because it appears in an accepted file.

When the publication rules established by their owning revision declare a specification edition
immutable, its files, numbers, anchors, and links remain available as that edition. A later
reorganization does not alter those bytes.

### 2.6 The authority draft can use the exception, but cannot land unchanged

The focused 2026-09-18 re-appraisal compared this proposal with every decision and consequence in
`define-specification-artifacts-and-normative-ownership`. The proposed process supplies a mechanism
for each structural consequence:

| authority-draft consequence | mechanism supplied here | work the authority draft still owes |
|---|---|---|
| Put the specification framework before details that depend on it, and separate abstraction level from packet content class. | A reviewed structural revision may move, split, merge, replace, or retire sections despite the append-only default. | Refresh its baseline after this process is incorporated, declare the accepted process revision as a dependency, and give the exact resulting Part 00 outline. |
| Make the specification README informational and distribute its binding statements to Parts 00, 02, 03, 04, 05, and 09. | The required crosswalk expressly includes unnumbered README statements and permits relocation into subject-owning parts. | Replace its subject-level README table with a paragraph-level old-location, disposition, destination, semantic-effect, and decision-clause crosswalk. |
| Replace local-header precedence with one owner and checked status projections. | A semantic change can accompany relocation when it is tied to an enumerated Decision clause and all affected projections and checks change atomically. | Name the exact Part 00 destination, every local-header update, and the positive and negative framework-checker cases. |
| Centralize the normative bibliography and repoint subject-owning parts. | Live citations and generated renderings are swept in the same structural incorporation; historical revisions remain in their incorporation context. | List each current citation or reference whose meaning or target changes and preserve the new process section if Part 00 is reorganized. |
| Preserve traceability while section numbers move. | Canonical anchors, crosswalk history, commit-relative historical citations, and anchor-aware ledger and evidence targets separate current identity from historical numbering. | Bootstrap anchors for every affected existing source and destination, assign anchors and aliases to new destinations, convert affected `applied.toml` and evidence targets, and record each authority Decision clause's final owner. |
| Add a framework checker while leaving packet behavior unchanged. | Process-tool changes and specification changes can be incorporated atomically without changing packet schemas, registries, fixtures, or runtime behavior. | Add its separate ownership/status/README/bibliography checker after the anchor, citation, heading, impact, ledger, and evidence support from this process exists. |

The authority draft therefore cannot use this exception from its current
`8d3a9c8598dd0152930ee0aab4de9a19a5496f22` baseline. Once this process is accepted and
incorporated, the authority draft first identifies its exact affected section set. A separate
metadata-only commit then bootstraps anchors for every affected existing source and destination,
and the draft re-establishes freshness against that post-bootstrap commit. Its crosswalk must
include the appended Part 00 process section introduced here if that section is moved, renumbered,
split, or merged. This is a required revision and re-appraisal of the authority draft, not a defect
in the dependency order.

## 3. Desired outcome and constraints

This proposal governs only whether and how specification text and citations may be reorganized. It
does not define specification authority, artifact roles or membership, release identity, or
publication terminology. P1 remains the sole owner of those candidate decisions. This proposal can
condition editing behavior on an edition later declared immutable by the owning publication rule;
it does not declare such an edition itself.

The append-only policy remains the default for an ordinary amendment to the working specification.
An accepted structural revision may make a reviewed exception when reorganization produces a
materially clearer owner, dependency order, or document structure.

The exception should have these properties:

1. The revision identifies itself as a structural reorganization, records the exact baseline
   commit, and explains why append-only placement would impair the specification.
2. The revision contains a human-readable crosswalk accounting for every moved, split, merged,
   replaced, duplicated, or retired section and every unnumbered README statement whose normative
   ownership changes. Each row gives the old location, disposition, new location, semantic effect,
   and any decision clause that changes meaning. It is reviewed history, not a second normative
   owner and not a machine-readable paragraph inventory.
3. Relocation and normative change remain distinguishable. Moving text does not authorize a change
   in meaning, and a changed rule is tied to an enumerated Decision clause.
4. Every numbered section structurally affected after this change has a canonical stable anchor
   independent of its displayed number. A section is affected when it is a source or destination
   of relocated prose; when its heading, level, number, or order changes; or when it is added,
   split, merged, replaced, or retired. An existing affected section receives its anchor in a
   separate metadata-only bootstrap commit before the structural draft's final pre-acceptance
   appraisal and acceptance request; the draft refreshes its baseline to that bootstrap commit. A
   section created by the incorporation receives its anchor when it is created. Untouched existing
   sections need not be migrated. The source form is explicit raw HTML placed immediately before
   the heading, for example:

   ```html
   <a id="ew-content-classes" data-spec-anchor="canonical"></a>
   ```

   Anchor names use lowercase ASCII letters, digits, and hyphens, are unique across the combined
   specification, and are chosen rather than regenerated from the heading text. Moving or
   renumbering the same subject preserves its canonical anchor.
5. Where a replaced or split section has an honest primary successor, its former anchor may remain
   beside that successor as an explicitly marked alias:

   ```html
   <a id="ew-layer-model" data-spec-anchor="alias"></a>
   ```

   An alias preserves a link; it does not claim that every former statement remains in that one
   destination. The crosswalk records splits and semantic changes. A retired subject with no honest
   successor receives no misleading alias.
6. Current prose citations continue to display `Part NN §x.y`. When a Markdown link is useful, its
   target is the stable anchor. Citation checks verify the displayed number against the anchor's
   current heading. Source-code comments may retain the textual form and are updated during the
   ordinary impact sweep.
7. `applied.toml` and evidence manifests may identify a prose owner by stable anchor instead of
   section number. The ledger and evidence checkers resolve that anchor to its current section
   before applying their existing destination and corroboration checks. A structural revision
   converts every affected machine target to its anchor; untouched legacy section targets need not
   be migrated merely to adopt this process.
8. The heading record associates each canonical anchor with its current part, number, and title.
   Duplicate or malformed anchors fail verification. Disappearance or reassignment appears as
   heading drift with the anchor's known citers and remains a failure until it is reviewed and the
   heading record is updated in the structural incorporation. The impact tool can report the
   anchor's current numbered section and its live citers.
9. Every affected live citation, ledger target, evidence owner, corroboration exception, generated
   rendering, and human document is updated in the same incorporation change. Accepted historical
   revisions remain unchanged, and their citations are mechanically checked against their
   incorporation commits subject only to the exact legacy baseline described in §2.5.
10. Once an owning publication rule declares an edition immutable, this process does not permit its
    bytes to be reorganized in place. A later working specification may preserve stable anchors and
    aliases, but a version-specific historical reference continues to target the earlier edition.

The process revision itself can be incorporated under the existing rule by appending a narrow
exception after Part 00 §10.4. That appended section can carry the first canonical anchor without
moving any existing section. Only a later revision, beginning with the authority revision, uses the
exception to reorganize existing material.

After the process revision is committed, adding canonical anchors to existing numbered headings is
an expressly permitted metadata-only maintenance change. A structural draft first identifies every
affected existing source and destination that lacks an anchor. Those anchors are then bootstrapped
and committed separately before the draft's final pre-acceptance appraisal. The draft refreshes its
`Based on` commit to that bootstrap, is finally appraised and committed in that state, and only then
may be presented for acceptance authorization. The bootstrap exception applies only when the
change leaves heading text and level, section number and order, body prose, normativity, and meaning
untouched and assigns one unique canonical anchor to each affected heading. It does not permit
removing or reassigning an anchor, adding an alias, or moving prose; those operations require the
structural process above. The heading check records the resulting one-to-one assignments. An anchor
may retain a historical word or part prefix after its subject moves; stability takes precedence
over making an identifier continuously descriptive.

No packet bytes, registry declarations, schema identities, profile behavior, or runtime
conformance change merely because this process changes. A structural revision still uses the
ordinary proposal, draft, acceptance, incorporation, and evidence gates for every semantic change
it contains.

## 4. Options and tradeoffs

### 4.1 Keep unconditional append-only numbering

This has the smallest tooling cost and keeps every current section number stable. It makes the
authority repair accumulate framework text at the end of Part 00 and related ownership text at the
ends of other parts. Forwarding prose can reduce ambiguity, but it leaves the document organized by
change history rather than by subject. That is a poor long-term choice for an unpublished
specification still under active design.

### 4.2 Make an undocumented exception for the authority revision

This produces a better-organized specification immediately, but makes the accepted process and the
actual process disagree. Reviewers cannot tell whether later renumbering was intentional, and the
tools cannot distinguish an authorized reorganization from drift. This option is rejected.

### 4.3 Combine Git history, publication immutability, and stable anchors

This is the preferred direction. Git commits preserve the working specification's history, the
accepted revision carries a readable crosswalk, stable anchors preserve subject identity while
numbers move, and the editing process respects any immutability declaration made by the owning
publication rule. Automation remains focused on the current contract and its current owners rather
than reconstructing prose blocks across time.

The cost is a small explicit-anchor convention and extensions to the existing heading, citation,
ledger, evidence, and impact tools. Only structurally affected machine targets need migration.

### 4.4 Build a machine-readable relocation and requirement-identity system

Baseline-bound paragraph selectors, content hashes, relocation chains, and persistent requirement
objects could make every prose movement queryable. They would also introduce a second structured
model of the specification, require rules for splits and semantic continuity, and duplicate facts
already preserved by Git and accepted revisions. This option is rejected as disproportionate.

### 4.5 Rewrite historical revisions or preserve old section numbers with permanent stubs

Rewriting accepted revisions would make them describe an organization that did not exist when they
were accepted. Permanent forwarding sections would preserve numbers but leave a misleading second
skeleton in the normative parts. Historical interpretation belongs to the historical commit;
stable aliases are sufficient where a current link has an honest successor.

## 5. Impact sketch

| surface | expected effect |
|---|---|
| semantic prose | Part 00 gains an appended exception to Part 00 §10.3's default and defines structural-edit, anchor, and citation-time mechanics. P1 remains the owner of authority, artifact-role, candidate, release, and publication terminology. No scientific concept changes. |
| logical prose and registry | No logical resource, declaration, registry source, or generated registry changes. |
| physical profiles | No storage requirement or profile identifier changes. |
| packet catalog and schemas | No packet field, JSON Schema, or catalog behavior changes. |
| validation and import | Packet validation and import are unchanged. Specification-process verification gains anchor checks. |
| extensions | Extension registries and extension behavior are unchanged. |
| reader, writer, validator, adapters, and code generation | Runtime behavior is unchanged. Source comments that cite renumbered sections are updated during structural incorporation. |
| existing packets and migration | No packet migration or regeneration is needed. |
| revision ledger and evidence manifests | `ledger.py` and `evidence.py` accept anchor-based prose targets and resolve them to current sections. Affected targets are converted during reorganization; the full set of 375 current applied targets is not subject to an immediate global migration. |
| citation, heading, and impact tooling | `check_citations.py` checks canonical anchors, aliases, uniqueness, and linked citation display; identifies each accepted revision's incorporation commit by its status transition while following renames; and resolves historical citations against the source tree in that commit. Any genuinely unrecoverable pre-v0.2 references are limited to an exact, reviewed, non-growing legacy baseline. `headings.py` records anchor-to-part/number/title assignments; `impact.py` accepts an anchor and reports its current section and live citers. |
| process-tool tests | Positive cases cover a separately committed metadata-only bootstrap for every affected existing source and destination, a structural draft whose refreshed baseline names that commit before final appraisal and acceptance, anchors assigned to new destinations, preserved anchors through renumbering, honest aliases, anchor-based ledger and evidence targets, an accepted-status transition found through a rename, and a historical reference valid at its incorporation commit. Negative cases cover an acceptance request based before the required bootstrap, a structural incorporation with an unanchored affected source or destination, a bootstrap that changes prose or structure, duplicate or missing anchors, anchor reassignment, a stale displayed number, an unresolved live target, a historical citation that was never valid, growth of the legacy baseline, and a missing affected ledger destination. |
| generated publications and developer documentation | The combined specification preserves source anchors and is checked for global uniqueness. The lifecycle guide explains structural appraisal, current versus historical references, anchor handling, and the editing consequence of an edition being declared immutable elsewhere. |
| current authority draft | It remains blocked from acceptance. After this process change lands, its landing plan can reorganize by subject, assign stable anchors, and provide a human-readable section and README-statement crosswalk. |
| release compatibility | The current working specification has no known external consumer or remote. When the owning publication rule declares an edition immutable, later work does not modify it in place and preserves honest anchors and aliases where useful. |

## 6. Open questions

The 2026-09-17 promotion appraisal exposed five questions in the earlier relocation-database
design. The revised direction resolves those questions as follows:

1. Unnumbered prose has no machine selector. The authority revision's reviewed crosswalk identifies
   README statements in human-readable terms, and Git preserves their exact baseline bytes.
2. Section locations need no temporal relocation identity or chain. Historical references resolve
   in their incorporation commit; current subject identity uses a stable anchor; an edition
   declared immutable by the owning publication rule does not change.
3. The crosswalk and ledger no longer compete. The crosswalk records historical movement, while
   `applied.toml` and evidence manifests identify current owners, using anchors for affected prose
   targets.
4. Live references are checked against the current working specification. Accepted revisions are
   historical and interpreted in the commit that incorporated them. A version-specific reference
   continues to name the edition it originally targeted.
5. There is no new relocation artifact or checker. Stable anchors live in the numbered source,
   crosswalks live in accepted revisions, and the existing heading, citation, impact, ledger, and
   evidence tools gain the focused checks described above.

The 2026-09-18 re-appraisal found three narrower questions. All are resolved:

1. The process revision expressly authorizes a separate metadata-only canonical-anchor bootstrap
   after it is committed. The exception's no-prose, no-structure, no-semantics boundary is checked;
   anchor removal, reassignment, aliases, and relocation remain structural work.
2. P0.1 owns only editing and citation mechanics. P1 remains the sole owner of candidate authority,
   artifact roles and membership, release identity, and publication terminology. P0.1 recognizes
   the editing consequence of a future immutable-edition declaration without defining it.
3. Historical citations are mechanically checked in their incorporation commits. The checker
   identifies the accepted-status transition while following renames and rejects a citation that
   was never valid. Incorporation audits pre-v0.2 references; any genuinely unrecoverable cases are
   an exact reviewed compatibility baseline that cannot grow.

Those three questions remain resolved.

The authority-draft-focused re-appraisal found one further question: whether the anchor rule also
covers an existing section that remains in place while receiving relocated README prose. It is now
resolved. Every structurally affected source and destination receives an anchor; existing affected
headings are bootstrapped in a separate metadata-only commit, while new headings receive anchors
when created. Untouched sections remain outside the migration.

The subsequent lifecycle re-appraisal found one sequencing ambiguity: Phase D prohibits a separate
commit after acceptance authorization until incorporation closes. It is now resolved. The general
process uses the order already recorded by the authority draft's §7: identify the affected set,
commit the metadata-only bootstrap, refresh the draft baseline, perform the final pre-acceptance
appraisal, commit that exact draft, and only then request acceptance.

No substantive promotion blocker remains. This process will enable every structural consequence
of the authority draft, but it will not make the current draft acceptance-ready by itself; §2.6
lists the draft changes and post-P0.1 re-appraisal still required. Promotion still waits for the
exact appraised proposal state to be committed and for explicit authorization to draft.

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

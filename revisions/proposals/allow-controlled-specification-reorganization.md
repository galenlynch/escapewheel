# Allow Controlled Reorganization of the Working Specification

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-17 |
| **Based on** | `1891ac253d194fd187fcfe3bb69385506d2c6629` |
| **Decision domain** | process |
| **Affects** | Revision-lifecycle and process authority; structural-editing procedure; stable section anchors; incorporation, heading, impact, ledger, and evidence procedures; the provisional release manifest's ledger path; coordination with the dependent authoritative-source cleanup and the authority draft |

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

The first acceptance appraisal exposed a more basic ownership problem. The proposal had assumed
that specification-maintenance rules belonged in normative Part 00 and that a specification
section should cite the revision that produced it so the ledger could corroborate the placement.
That makes the current contract depend backward on its change records. The intended direction is
the reverse: an accepted revision and the ledger point to the current authoritative owner, while
the specification and incorporated machine-readable artifacts remain readable without the
revision archive. The proposal has returned from Draft so that the location of maintenance policy,
the ledger's evidence model, and the disposition of revision provenance can be settled before any
candidate rule is written.

The revised direction also exposes a lifecycle gap. The current guide and directory descriptions
define accepted revisions as changes incorporated into the generated specification, while this
proposal deliberately places its current rules in the revision contribution guide. The process
must distinguish process authority from packet-specification authority without allowing material
changes to its own gates or evidence semantics to pass as ordinary documentation maintenance.

## 2. Evidence

### 2.1 Current rule and baseline

At the baseline commit, Part 00 §10.3 says that whoever amends a part adds at the end and does not
insert between existing sections. R112 §3.4 is the accepted decision from which that text came.
The lifecycle guide repeats the same policy in Phase E: new prose is appended so citations retain
their numbers.

The quick repository verifier passed all 24 stages at the baseline. It reported 262 recorded
sections across 11 parts, no repeated part numbers, no unresolved live citations, no undisposed
revision clauses, this proposal, and one open draft. The first invocation could not write the
environment's default `uv` cache; rerunning the same command with `UV_CACHE_DIR=/tmp/uv-cache`
passed. This is an environment constraint, not a baseline defect.

The other open lifecycle artifact is the draft
`define-specification-artifacts-and-normative-ownership`. There is no configured Git remote, and the
project has no known external consumers whose section links require a compatibility period. The
process should nevertheless establish a release-safe model rather than depend on that temporary
fact.

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
revision and the specification-source histories needed to inspect it, including the early parallel
histories measured in §2.8. The citation checker already distinguishes live sources from accepted
historical revisions: a missing current target fails, while an old accepted reference is reported
as history rather than silently rewritten.

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

### 2.5 References have different time contexts

A reference in the current specification, implementation, test, or developer documentation is
live and needs to resolve against the current working specification. A structural incorporation
updates every such reference it affects.

An accepted revision is historical. Git can recover the commit where its status first became
Accepted, following later renames, while a current-format revision's `Based on` field separately
identifies its appraised pre-change state. Early revision records and specification sources began
in parallel histories, so some citations need an explicitly selected historical source tree.
Historical files are not edited merely to name the current organization.

The promoted draft treated complete commit-relative resolution as a required process invariant.
The later appraisal established that it is mechanically feasible but not necessary to maintain the
current contract. Section 2.8 records the full measured population retained as review evidence. A
historical citation does not authorize a current specification section to cite the revision back.

When the publication rules established by their owning revision declare a specification edition
immutable, its files, numbers, anchors, and links remain available as that edition. A later
reorganization does not alter those bytes.

### 2.6 Earlier appraisal showed the authority draft needs the mechanism

The focused 2026-09-18 re-appraisal compared this proposal with every decision and consequence in
`define-specification-artifacts-and-normative-ownership`. The proposed process supplies a mechanism
for each structural consequence. That mechanical conclusion survives; the later appraisal in
§2.7 rejects the presumed Part 00 owner and reverse-provenance model.

| authority-draft consequence | mechanism supplied here | work the authority draft still owes |
|---|---|---|
| Put the specification framework before details that depend on it, and separate abstraction level from packet content class. | A reviewed structural revision may move, split, merge, replace, or retire sections despite the append-only default. | Refresh its baseline after this process is incorporated, declare the accepted process revision as a dependency, and give the exact resulting Part 00 outline. |
| Make the specification README informational and distribute its binding statements to Parts 00, 02, 03, 04, 05, and 09. | The required crosswalk expressly includes unnumbered README statements and permits relocation into subject-owning parts. | Replace its subject-level README table with a paragraph-level old-location, disposition, destination, semantic-effect, and decision-clause crosswalk. |
| Replace local-header precedence with one owner and checked status projections. | A semantic change can accompany relocation when it is tied to an enumerated Decision clause and all affected projections and checks change atomically. | Name the exact Part 00 destination, every local-header update, and the positive and negative framework-checker cases. |
| Centralize the normative bibliography and repoint subject-owning parts. | Live citations and generated renderings are swept in the same structural incorporation; historical revisions remain unchanged in Git. | List each current citation or reference whose meaning or target changes and remove misplaced maintenance prose rather than preserving a new process section in Part 00. |
| Preserve traceability while section numbers move. | Canonical anchors, crosswalk history, and anchor-aware ledger and evidence targets separate current identity from historical records. | Bootstrap anchors for every affected existing source and destination, assign anchors and aliases to new destinations, convert affected `applied.toml` and evidence targets, and record each authority Decision clause's final owner. |
| Add a framework checker while leaving packet behavior unchanged. | Process-tool changes and specification changes can be incorporated atomically without changing packet schemas, registries, fixtures, or runtime behavior. | Add its separate ownership/status/README/bibliography checker after the anchor, citation, heading, impact, ledger, and evidence support from this process exists. |

The authority draft therefore cannot use this exception from its current
`8d3a9c8598dd0152930ee0aab4de9a19a5496f22` baseline. Once this process is accepted and
incorporated, the authority draft first identifies its exact affected section set. A separate
metadata-only commit then bootstraps anchors for every affected existing source and destination,
and the draft re-establishes freshness against that post-bootstrap commit. Its crosswalk must
apply the resulting boundary between maintenance policy and specification content. This is a
required revision and re-appraisal of the authority draft, not a defect in the dependency order.

### 2.7 The current ledger reverses the intended dependency

The ledger's useful invariant is one-way: every binding accepted clause has an exact disposition
and, where it remains current, an exact prose or registry owner. `applied.toml` supplies that map.
The current checker adds a reverse condition: an applied specification section normally has to
name the revision whose clause the ledger maps there. `corroboration-exceptions.toml` enumerates
legacy locations that lack that backlink.

This reverse condition is neither authority nor strong evidence of semantic fidelity. A section
can name a revision while misstating its rule, and the ledger checker describes the citation as
corroboration rather than proof. It also prevents the current contract from standing alone. At the
baseline, the authored Markdown under `escapewheel_poc_docs_v0.2`, excluding the combined
rendering, contains 478 `R<N>` occurrences across the README and ten parts. Registry source
descriptions and validation messages contain further revision references, and the registry's
`since` fields identify revisions rather than specification editions.

The cleaner dependency is:

```text
accepted revision clause -> ledger disposition -> current specification or registry owner
```

Evidence manifests may continue from that clause to implementations, tests, and documentation.
No reverse edge from a current authoritative owner to its historical change record is needed.

### 2.8 Historical citation checking is archival, not specification authority

The demoted draft's acceptance appraisal scanned every Part citation in every record whose current
metadata says Accepted. It found 419 occurrences across 117 records: 394 resolve to numbered
headings in automatically derived or already proposed historical contexts, 13 are the previously
identified Part 06 line locators, and 12 in R2, R16, R54, R55, R65, R68, and R70 need additional
exact source contexts. The early records can be resolved against the frozen v0.1 source at
`52a587e9d72472ab0595e861fd8450f620249f47`; R65, R68, and R70 can be resolved against the compiled
v0.2 source at `4ce6f09cce0d2c8c1f1cb75815f833f0fbbb9cee`.

Those references run from historical revisions to the specification state they discussed. The
audit is useful evidence that the archive can be interpreted, but it does not justify references in
the opposite direction and is not an input to current normative interpretation. It remains a
recorded review rather than becoming a repository gate or a rule of packet conformance.

### 2.9 Process decisions and the provisional release bundle need explicit treatment

The current lifecycle applies the ordinary repository workflow to developer documentation and
describes an accepted revision as a decision incorporated into the generated v0.2 specification.
That wording does not account for a material decision whose current owner is the lifecycle guide
itself. Treating this proposal as an ordinary documentation edit would avoid the wording conflict
only by bypassing the appraisal, exact-state, acceptance, ledger, and evidence controls whose
semantics it changes.

The current release assembly also includes
`escapewheel_poc_docs_v0.2/applied.toml` in its `provenance` category. Moving that ledger beside the
revision records therefore requires an update to `release.py` and `RELEASE.json`. Updating the path
does not decide whether provenance belongs in a future specification release; it preserves the
current provisional membership until the authority and publication work makes that decision.

### 2.10 Citations into the current Part 00 process material divide by lifecycle

The reverse-impact query for Part 00 §§10.1–10.4 reports 30 citations at the appraisal baseline.
Twenty-two are in the process tools `check_citations.py`, `repoint.py`, `impact.py`, `verify.py`, and
the ledger that this change moves. Two are in the live roadmap. One is in current Part 07 prose.
Three are in accepted R113, and two are baseline evidence in this proposal that will become part of
its historical record if the decision is accepted.

Those populations need different treatment. This process change repoints the 22 process-tool
references and the two live-roadmap references to the new process owner. The dependent
authoritative-source cleanup dispositions the current Part 07 statement together with Part 00
§§10.1–10.4. R113 and the accepted form of this decision remain unchanged as historical records of
the specification state they discussed. Re-measurement at incorporation accounts for any change in
the population rather than treating these counts as permanent exceptions.

## 3. Desired outcome and constraints

This proposal explores whether and how specification text and citations may be reorganized. It
does not define specification authority, artifact roles or membership, release identity, or
publication terminology. The authority-and-normative-ownership draft, called P1 in the roadmap,
remains the owner of those candidate decisions. The present proposal can condition editing behavior
on an edition later declared immutable by the owning publication rule; it does not declare such an
edition itself. The roadmap labels P0.1, P0.2, and P1 are coordination identifiers, not sections of
this proposal and not accepted-revision numbers.

The current specification, registry, and schemas should stand alone as the current contract. Their
meaning should not require access to an accepted revision, and their source should not carry
revision citations merely to corroborate the ledger. Change provenance belongs in the accepted
revision, `applied.toml`, and the evidence manifest. If a registry field needs an introduction
version for compatibility, that value should identify a specification edition rather than a
revision record. The dependent cleanup appraises whether such a field is needed before choosing an
edition-valued replacement.

Specification-maintenance rules live at the layer they bind. Crosswalks, bootstrap commits,
acceptance sequencing, and ledger procedures bind repository maintainers rather than packet
producers or consumers, so `revisions/CONTRIBUTING.md` owns them. A separate maintenance-policy
artifact would add an authority class the project does not need. Stable anchors remain metadata in
the published Markdown, while the rules for assigning and checking them belong to the contribution
guide and publication tooling. The earlier plan to place the complete process in a new normative
Part 00 section is rejected.

The lifecycle should recognize two decision domains without making either historical revision
record independently normative:

- A **specification** decision changes the packet contract or an artifact that owns part of that
  contract. Its current owner remains a numbered part, incorporated registry or schema, or another
  artifact assigned that role by the authority model.
- A **process** decision changes the material rules by which specification changes are proposed,
  appraised, accepted, incorporated, or evidenced. Its current owner is an exact anchored section
  of `revisions/CONTRIBUTING.md` or a process artifact that guide expressly recognizes.

Proposals, drafts, accepted records, the ledger, and evidence manifests use the same lifecycle and
one `R<N>` incorporation sequence for both domains. New and open artifacts declare `Decision
domain` as `specification` or `process`, and the stage, ledger, and evidence tools validate the
destinations appropriate to it. The P0.1 draft declares `process`. When this decision is
incorporated, every other open artifact, including the P1 draft, is migrated to an explicit
`specification` value. Existing accepted revisions without the field are defined as
`specification` decisions and remain byte-for-byte unchanged; tools apply that legacy default only
to accepted records that predate this process decision. Every proposal or draft created or promoted
after incorporation must declare the field, and its accepted form preserves the value.

For a process draft, `Profile` is `not applicable`, and `Amends` names the exact repository path and
stable anchor of each process owner rather than a numbered specification part. Templates and
`stages.py` enforce those forms prospectively. An accepted record preserves the decision and
provenance; authority arises from the current incorporated owner, not from the record. A change that
materially alters lifecycle gates, process authority, structural-editing permission, ledger
dispositions, or evidence semantics uses this lifecycle. Meaning-preserving edits to contribution
prose, examples, and implementation details remain ordinary repository maintenance. The lifecycle
guide, stage templates, directory READMEs, and evidence terminology are updated together when this
decision is incorporated.

The append-only policy remains the default for an ordinary amendment to the working specification.
An accepted structural revision may make a reviewed exception when reorganization produces a
materially clearer owner, dependency order, or document structure.

The process guide owns the exception, and the mechanism should have these properties:

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
7. The ledger, `applied.toml`, and registry-target map move from the specification directory to
   `revisions/`. A prose destination may use `part` and a stable `anchor` for a specification part,
   or an exact repository `path` and stable `anchor` for another recognized current owner such as
   `revisions/CONTRIBUTING.md`. The ledger and evidence checkers resolve that anchor before applying
   destination checks. They check completeness and existence, not semantic fidelity, and do not
   require the owner to cite its revision back. The reverse-corroboration check and
   `corroboration-exceptions.toml` are removed. A structural revision converts every affected
   machine target to anchor form; untouched numeric section targets need not be migrated merely to
   adopt this process.
8. The heading record associates each canonical anchor with its current part, number, and title.
   Duplicate or malformed anchors fail verification. Disappearance or reassignment appears as
   heading drift with the anchor's known citers and remains a failure until it is reviewed and the
   heading record is updated in the structural incorporation. The impact tool can report the
   anchor's current numbered section and its live citers.
9. Every affected live citation, ledger target, evidence owner, generated rendering, and human
   document is updated in the same incorporation change. Accepted historical revisions remain
   unchanged. The completed historical-citation audit remains review evidence, not a permanent
   conformance or incorporation gate. Current proposals and drafts continue to have their citations
   checked against the live specification and their recorded baseline is re-established before
   appraisal; Git preserves the contexts of accepted records without a compatibility inventory or
   backlink from the current specification.
10. Once an owning publication rule declares an edition immutable, this process does not permit its
    bytes to be reorganized in place. A later working specification may preserve stable anchors and
    aliases, but a version-specific historical reference continues to target the earlier edition.

The root authority model describes the numbered parts as the behavioral specification, while
`revisions/CONTRIBUTING.md` already says that it governs the change lifecycle. This process change
therefore lands in the contribution guide and its tools; it does not need Part 00 to authorize it.
Part 00 §10 mixes repository-maintenance, citation-presentation, revision-provenance, and
current-owner statements, but it is not the owner of repository governance. The dependent cleanup
accounts for each statement in §§10.1–10.4: it removes process-owned rules after their current
owners exist in the contribution guide, removes historical provenance from authoritative sources,
and preserves any current-contract ownership semantics until the authority draft places them
finally. That cleanup is not a reason to reproduce the process in another specification section.

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

The authoritative-source cleanup, called P0.2 in the roadmap, is split from this process decision.
It gives every statement in Part 00 §§10.1–10.4 an explicit disposition; removes process rules and
revision citations from the numbered parts and incorporated registry, schema, and rule sources;
removes the registry-provenance `derived_from` object; and either removes revision-valued `since` or
replaces it only if a separate appraisal establishes a genuine specification-edition compatibility
need. It does not remove a still-needed current-contract ownership rule merely because historical
provenance appears in the same section. The split is necessary because changing the registry
meta-schema and regenerated registry can affect embedded registries and existing packets, while
relocating process ownership cannot. That cleanup depends on this structural process and precedes
the authority revision.

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

### 4.6 Put the complete maintenance procedure in normative Part 00

This was the promoted draft's direction. It gives the structural exception an authoritative home
and makes the generated specification carry every rule needed to edit itself. It also mixes packet
conformance with repository governance, places historical-revision mechanics in the current data
contract, and encourages the specification to retain backward references to its change records.
The acceptance appraisal found that cost larger than the apparent simplicity.

### 4.7 Let the revision process own maintenance and keep provenance one-way

Under this option, the revision contribution guide and its tools own structural crosswalks,
bootstrap ordering, historical audits, and acceptance mechanics. The ledger maps accepted clauses
to current owners but no longer asks those owners to cite the revision back. This process decision
makes no Part 00 change. The dependent authoritative-source cleanup removes process and provenance
material from Part 00 while preserving any current-contract statement needed until the authority
draft supplies its final owner.

This is the selected direction. It matches the existing boundary in which the root authority model
defines the behavioral artifacts and the revision contribution guide governs their change
lifecycle. The ledger moves beside the records it indexes and replaces weak backlink corroboration
with exact current destinations and incorporation evidence.

### 4.8 Publish a separate specification-maintenance policy

A dedicated policy could be more durable and discoverable than contribution instructions while
remaining outside the packet specification. It would, however, introduce another authority class
before P1 has defined artifact roles and release membership. Unless the process needs distribution
independent of this repository, the revision contribution guide is the smaller starting point.
This option is rejected.

### 4.9 Remove every historical reference in this process change

Combining the cleanup with the structural-process decision would reach the desired standalone
contract in one incorporation. It would also combine repository governance with removal of 478
Markdown occurrences, hundreds of registry provenance values, a registry meta-schema change, and
the compatibility question raised by embedded registries. Those are independently appraisable
effects. The cleanup is therefore split into a dependent proposal that lands before P1.

## 5. Impact sketch

| surface | expected effect |
|---|---|
| semantic prose | No packet-behavior rule changes. Part 00 §§10.1–10.4 are recorded for clause-level disposition by the dependent authoritative-source cleanup; this process does not edit Part 00 or append a replacement specification section. |
| logical prose and registry | No logical declaration or registry source changes in this process. Revision citations, registry-provenance `derived_from`, and revision-valued `since` move to the dependent cleanup because their removal changes the registry meta-schema and generated registry. |
| physical profiles | No storage requirement or profile identifier changes. |
| packet catalog and schemas | No packet field, JSON Schema, or catalog behavior changes. |
| validation and import | Packet validation and import are unchanged. Repository-process verification gains structural-change and anchor checks. |
| extensions | Extension registries and extension behavior are unchanged. |
| reader, writer, validator, adapters, and code generation | Runtime behavior is unchanged. Source comments that cite renumbered sections are updated during structural incorporation. |
| existing packets and migration | No packet migration or regeneration is needed. |
| conformance fixtures and packet implementation tests | Unchanged because this process decision changes no packet shape, behavior, or interpretation. Process-tool tests change as described below. |
| revision ledger and evidence manifests | The ledger files move under `revisions/`; prose destinations accept exact part-or-path plus anchor targets; reverse corroboration and its exceptions are removed. Evidence manifests remain clause-to-owner and clause-to-evidence maps. |
| citation, heading, and impact tooling | P0.1 repoints the measured 22 process-tool citations and two live-roadmap citations from Part 00 to the new process owner. P0.2 dispositions the current Part 07 citation; accepted R113 and the eventual accepted P0.1 record remain historical. Live specification citations, stable anchors, aliases, uniqueness, and displayed-number agreement remain affected. The completed legacy audit is retained as proposal evidence rather than implemented as a permanent gate. |
| process-tool tests | Structural bootstrap, anchor, crosswalk, impact, and candidate-state cases remain required. New cases prove that a process-owned clause resolves to `revisions/CONTRIBUTING.md`, a current owner needs no revision backlink, and every accepted clause still has an exact disposition. |
| generated publications and developer documentation | The lifecycle guide owns structural appraisal, anchors, and bootstrap ordering. Its scope, artifact definitions, templates, and directory READMEs distinguish specification and process decisions. Publication tooling preserves source anchors and checks global uniqueness once a structural revision introduces them; no new process prose is generated into the specification. |
| provisional release assembly | `release.py` and `RELEASE.json` update the ledger path from `escapewheel_poc_docs_v0.2/applied.toml` to `revisions/applied.toml` while preserving its existing `provenance` category. P1 remains responsible for eventual release membership. |
| dependent authoritative-source cleanup | A separate proposal gives Part 00 §§10.1–10.4 clause-level dispositions, removes process and revision-provenance material from authoritative Markdown and incorporated JSON, preserves any current-contract ownership semantics pending P1, removes registry build provenance, and appraises `since` removal and embedded-registry compatibility. It depends on this process and blocks P1. |
| current authority draft | It remains blocked from acceptance. After this process and the dependent authoritative-source cleanup land, its landing plan can reorganize by subject, assign stable anchors, and provide a human-readable section and README-statement crosswalk. |
| release compatibility | The current working specification has no known external consumer or remote. When the owning publication rule declares an edition immutable, later work does not modify it in place and preserves honest anchors and aliases where useful. |

## 6. Resolved questions

The 2026-09-17 promotion appraisal exposed five questions in the earlier relocation-database
design. The revised direction resolves those questions as follows:

1. Unnumbered prose has no machine selector. The authority revision's reviewed crosswalk identifies
   README statements in human-readable terms, and Git preserves their exact baseline bytes.
2. Section locations need no temporal relocation identity or chain. Current subject identity uses
   a stable anchor, Git preserves historical states, and an edition declared immutable by the
   owning publication rule does not change.
3. The crosswalk and ledger no longer compete. The crosswalk records historical movement, while
   `applied.toml` and evidence manifests identify current owners, using anchors for affected prose
   targets.
4. Live references are checked against the current working specification. Accepted revisions are
   immutable historical records rather than inputs to current interpretation. A version-specific
   reference continues to name the edition it originally targeted.
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
3. The historical-citation probe and its complete follow-up audit remain appraisal evidence rather
   than production machinery. Current citation and freshness checks govern open artifacts, and no
   legacy compatibility inventory is introduced.

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

The 2026-09-18 acceptance appraisal reopened the proposal after finding an abstraction-layer
defect. The resulting questions are now resolved:

1. `revisions/CONTRIBUTING.md` owns structural-editing procedure. No separate maintenance-policy
   artifact is introduced.
2. The root authority model already limits the numbered parts to the behavioral specification and
   the revision guide already governs the change lifecycle. This process lands in that guide and
   its tools without seeking authorization from Part 00. The dependent cleanup removes Part 00
   §10 rather than appending another process section.
3. Exact ledger destinations, the atomic incorporation diff, evidence manifests, and later
   supersession records replace reverse-citation corroboration. The ledger verifies completeness
   and resolution and leaves semantic fidelity to appraisal; its corroboration exceptions are
   removed.
4. Historical revision references are excluded from every authoritative source, including
   specification prose, registry and schema descriptions, rule messages, registry build
   provenance, and revision-valued `since`. Because the registry changes have separate
   compatibility effects, a dependent proposal performs that cleanup and appraises whether any
   edition-valued replacement is justified.
5. The 419-citation audit is retained as evidence about the existing archive, not implemented as a
   permanent gate. Current open artifacts remain subject to live citation and freshness checks;
   Git preserves accepted history.
6. Anchor assignment, alias handling, bootstrap ordering, current-link verification, and combined
   rendering checks are maintenance and publication procedure. The anchors themselves remain
   stable metadata in the published Markdown; none of these rules becomes packet-conformance prose.

The subsequent promotion appraisal found four bounded omissions. They are now resolved:

1. Material lifecycle and process-authority changes use the same appraised revision lifecycle as
   specification decisions, declare the process decision domain, and land in exact process owners.
   Accepted records remain historical, and ordinary documentation maintenance remains ordinary.
2. This process decision makes no Part 00 or registry-source change. The dependent cleanup gives
   §§10.1–10.4 clause-level dispositions, removes maintenance and historical material, and preserves
   needed current-contract semantics pending the authority draft.
3. Moving the ledger updates its path in the provisional release assembly without deciding future
   release membership.
4. Packet conformance fixtures and packet implementation tests are explicitly unchanged; focused
   process-tool tests provide the new executable evidence.

The focused re-appraisal found two remaining migration questions. They are now resolved:

1. `Decision domain` classifies lifecycle handling without defining P1's specification authority
   model. Legacy accepted revisions default to `specification` without being edited; current open
   artifacts are migrated at incorporation; and future open and accepted artifacts declare the
   field. Process drafts use `Profile: not applicable` and exact path-plus-anchor `Amends` targets.
2. The 30 citations into Part 00 §§10.1–10.4 are partitioned by lifecycle. P0.1 repoints 22
   process-tool and two roadmap citations, P0.2 dispositions the one current numbered-part citation,
   and five citations carried by accepted history remain unchanged. Incorporation re-measures the
   population.

The earlier anchor, crosswalk, bootstrap, and immutable-edition research therefore survives with a
different owner. The revised proposal requires a new promotion appraisal. Promotion would then
still require the exact proposal and coordination state to be committed and explicit authorization
to draft.

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

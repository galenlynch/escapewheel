# The Revision Process Governs Structural Reorganization

| | |
|---|---|
| **Status** | **Accepted** 2026-09-18 |
| **Based on** | `f7064ee0b76aca46429338ce147cfa5d5f44d973` |
| **Decision domain** | process |
| **Change form** | ordinary |
| **Amends** | `revisions/CONTRIBUTING.md#ew-decision-domains`; `revisions/CONTRIBUTING.md#ew-structural-reorganization`; `revisions/CONTRIBUTING.md#ew-stable-section-anchors`; `revisions/CONTRIBUTING.md#ew-structural-reorganization-sequence`; `revisions/CONTRIBUTING.md#ew-citation-context`; `revisions/CONTRIBUTING.md#ew-current-owner-ledger`; `revisions/CONTRIBUTING.md#ew-process-incorporation-boundary` |
| **Depends on** | None |
| **Profile** | not applicable |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8 |

Section 3 is normative. Sections 1, 2, and 4–7 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision assigns structural editing, stable-anchor, lifecycle, ledger, and evidence procedure
to the revision process. It permits a reviewed revision to reorganize the unpublished working
specification when append-only placement would impair ownership, dependency order, or
comprehensibility. It keeps an ordinary amendment append-only, requires a human-readable
crosswalk, gives affected sections stable anchors, and preserves accepted history through Git
rather than backward citations from current owners.

This is a process-domain decision. It changes no packet requirement, numbered specification part,
registry declaration, schema, physical profile, implementation behavior, or release-membership
rule. A dependent revision will dispose the maintenance and historical material currently in Part
00 §§10.1–10.4 and elsewhere in authoritative sources. The authority-and-normative-ownership draft
will later define specification authority, artifact roles, release identity, and publication
terminology.

## 2. Background

### 2.1 Append-only numbering prevents the required structural repair

Part 00 §10.3 and the current lifecycle guide require new prose to be appended. That is a useful
default for an ordinary amendment because a small change does not renumber unrelated citations.
It is unsuitable when the change exists to repair document structure. The blocked authority draft
needs its framework before the details that rely on it and needs normative README statements in
their subject-owning parts. Appending those rules would preserve numbers while organizing the
specification by editing chronology.

The working specification has no known external consumer or remote, but the process should remain
safe after publication. Git preserves the source state against which a revision was appraised, an
edition declared immutable by its owning publication rule can preserve its bytes, and explicit
anchors can identify a current subject independently of its displayed section number.

### 2.2 Maintenance procedure belongs outside the packet contract

The root authority model describes the numbered parts as the behavioral specification, while
`revisions/CONTRIBUTING.md` governs the change lifecycle. Crosswalks, bootstrap commits, acceptance
sequencing, ledger dispositions, and evidence closure bind repository maintainers rather than
packet producers or consumers. Putting those rules in normative Part 00 would mix repository
governance with packet conformance and make the current contract depend backward on its change
records.

The present lifecycle nevertheless describes accepted revisions only as specification changes
incorporated into generated v0.2. It therefore needs a prospective process decision domain without
rewriting the 119 numbered historical records that predate it: 117 accepted and two withdrawn. The
same incorporation sequence can preserve both kinds of decision while their current authority
remains in different owners.

### 2.3 One-way traceability is sufficient

The ledger's useful invariant is one-way:

```text
accepted decision clause -> ledger disposition -> current owner
```

The present checker adds a reverse condition: an applied specification section normally cites the
revision that the ledger maps there. That backlink is neither authority nor evidence of semantic
fidelity. It also forces current prose to retain project history. Exact current destinations,
atomic incorporation diffs, evidence manifests, human appraisal, and later supersession records
provide the needed traceability without a reverse edge.

At the appraisal baseline, `applied.toml` has 375 applied targets across 125 part sections,
including 21 targets in 11 sections of Part 00. The authored specification Markdown contains 478
`R<N>` occurrences, and the registry contains further revision provenance. Removing that history
from authoritative sources is intentionally deferred because registry `derived_from` and `since`
raise separate schema and compatibility questions.

### 2.4 Current citations divide from historical citations

The reverse-impact query for Part 00 §§10.1–10.4 reports 29 citations at the appraisal baseline:
22 in process tools, two in the live roadmap, one in current Part 07 prose, three in accepted R113,
and one in this revision. This revision repoints the 24 live process references. The dependent
authoritative-source cleanup handles Part 07. The four citations in R113 and the eventual accepted
form of this revision remain unchanged as history.

The complete archival audit found 419 Part citations across 117 accepted records. It established
that the archive can be interpreted from Git and known historical source trees. It did not show
that historical citations should become inputs to current conformance or that current owners
should cite their revisions back. The audit remains review evidence rather than a production gate.

### 2.5 Existing controls provide the implementation base

`headings.py` records current section numbers and titles, `check_citations.py` resolves live
citations, `impact.py` reports reverse citations, `ledger.py` resolves accepted clauses, and
`evidence.py` resolves current-format closure manifests. `combine.py` preserves raw HTML in the
combined rendering. These tools can add explicit-anchor and process-owner support without a
paragraph-selector database, relocation chains, or persistent requirement objects.

The current provisional release assembly selects
`escapewheel_poc_docs_v0.2/applied.toml` for its `provenance` category. Moving the ledger beside the
revision records therefore changes the selector in `release.py`. The tracked `RELEASE.json` also
records a source commit and whether its generating tree was clean, so it cannot identify the same
atomic commit that first contains it. This revision leaves that provisional snapshot unchanged;
the authority and publication work owns its regeneration and final membership.

## 3. Decision

### 3.1 Decision domains and process authority

`revisions/CONTRIBUTING.md` **MUST** be the current owner of the material rules by which a
specification change is proposed, appraised, accepted, incorporated, and evidenced. A separate
specification-maintenance part **MUST NOT** be created.

Every open lifecycle artifact **MUST** declare one `Decision domain`:

- `specification` changes the packet contract or an artifact that owns part of that contract; and
- `process` changes the material lifecycle, process-authority, structural-editing, ledger, or
  evidence rules.

Both domains **MUST** use the proposal, draft, acceptance, incorporation, ledger, and evidence
gates in this guide and one `R<N>` sequence recording incorporation order. An accepted record
**MUST** preserve the decision and provenance but **MUST NOT** become the current owner merely by
being accepted. Its ledger destination **MUST** identify the incorporated current owner.

A change to a lifecycle gate, process authority, structural-editing permission, ledger
disposition, or evidence meaning **MUST** use this lifecycle. A meaning-preserving correction to
contribution prose, an example, or a process implementation **MAY** use the ordinary repository
workflow.

From incorporation of this revision, `revisions/CONTRIBUTING.md` **MUST** govern repository-change
procedure. The maintenance statements in Part 00 §§10.1–10.4 **MUST NOT** be treated as a second
owner of that procedure while they await disposition by the dependent authoritative-source
cleanup. This transition changes no packet-contract rule and does not permit a maintainer to
disregard a numbered-part statement on a subject the specification owns.

### 3.2 Metadata and legacy migration

The proposal, draft, and accepted templates **MUST** carry `Decision domain`. The draft and
accepted templates **MUST** also carry `Change form`, whose value is `ordinary` or `structural`.
Proposals need not select a change form. A specification-domain draft **MUST** use the existing
`Profile` and part-or-artifact `Amends` forms. A process-domain draft **MUST** use `Profile: not
applicable` and `Change form: ordinary`; each `Amends` target **MUST** give an exact
repository-relative Markdown path and the stable anchor of the process section it changes.

The 117 accepted revisions that predate this revision and lack `Decision domain` **MUST** be
interpreted as `specification` and **MUST NOT** be edited to add the field. The legacy default
**MUST** apply exactly to an accepted record whose revision number is lower than the number assigned
to this revision. The two withdrawn records require no domain interpretation and **MUST** remain
unchanged. During incorporation of this revision, every other open proposal and draft **MUST**
receive an explicit domain, and every other open draft **MUST** receive an explicit change form.
Every artifact created or promoted afterward **MUST** declare its applicable field or fields, and
an accepted form **MUST** preserve the draft's declared values. An accepted record older than this
revision need not be assigned or interpreted as having a change form.

`stages.py` **MUST** reject an absent or unknown domain where the prospective rule applies. It
**MUST** accept the legacy default only for accepted records older than this revision and **MUST**
validate the domain-specific `Profile` and `Amends` forms. It **MUST** reject an absent or unknown
change form in a prospective draft or accepted record and **MUST** reject `structural` for a
process-domain artifact.

### 3.3 Ordinary amendments and structural revisions

A specification-domain draft with `Change form: ordinary` that adds a section or subsection to the
working specification **MUST** append it at the end of its part or containing section. A
specification-domain draft **MAY** instead declare `Change form: structural` when moving, splitting,
merging, replacing, or retiring material produces a materially clearer owner, dependency order, or
document structure. Its Scope **MUST** identify it as a structural reorganization and explain why
append-only placement would impair the specification.

A structural revision **MUST** contain a human-readable crosswalk that accounts for every moved,
split, merged, replaced, duplicated, or retired numbered section and every unnumbered README
statement whose normative ownership changes. Each row **MUST** give the old location, disposition,
new location, semantic effect, and any Decision clause that changes meaning.

Relocation alone **MUST NOT** authorize a semantic change. Every changed rule **MUST** be stated in
an enumerated Decision clause. The crosswalk **MUST** remain reviewed history rather than a second
normative owner or a machine-readable paragraph inventory.

### 3.4 Stable section anchors and aliases

Every numbered section structurally affected as a source or destination **MUST** have one canonical
stable anchor independent of its displayed number. A section is affected when prose moves from or
to it; when its heading, level, number, or order changes; or when it is added, split, merged,
replaced, or retired. Untouched existing sections **MAY** remain without explicit anchors.

A canonical anchor **MUST** use lowercase ASCII letters, digits, and hyphens and **MUST** appear as
explicit raw HTML immediately before its heading:

```html
<a id="ew-content-classes" data-spec-anchor="canonical"></a>
```

Every canonical or alias anchor in a numbered part **MUST** be unique in the combined
specification. A process section named by an `Amends` target, ledger destination, evidence owner,
or current citation **MUST** use the same canonical raw-HTML form, and each of its canonical
anchors **MUST** be unique within that document.

Moving or renumbering a subject **MUST** preserve its canonical anchor even when an old word or
part prefix becomes less descriptive. A replaced or split section **MAY** retain a former anchor
beside one honest primary successor as an explicitly marked alias. An alias **MUST NOT** imply that
every former statement remains at that destination, and a retired subject without an honest
successor **MUST NOT** receive a misleading alias.

```html
<a id="ew-layer-model" data-spec-anchor="alias"></a>
```

### 3.5 Anchor bootstrap and structural sequencing

Before the final pre-acceptance appraisal of a structural draft, its author **MUST** identify every
affected existing source and destination that lacks a canonical anchor. If any does, a separate
metadata-only commit **MUST** add those anchors and **MUST** be the commit named by the draft's
`Based on` field. That commit **MUST NOT** change heading text or level, section number or order,
body prose, normativity, meaning, or any alias. A process check **MUST** compare the `Based on`
commit with its parent and reject a change outside insertion of one valid canonical anchor
immediately before each identified heading. If every affected existing section is already
anchored, the crosswalk **MUST** record that no bootstrap was required.

After any bootstrap, the author **MUST** refresh every affected measurement, impact query, and
citation inventory; perform the final appraisal; commit that exact draft; and only then request
acceptance authorization. A section created during incorporation **MUST** receive its canonical
anchor when it is created.

The structural incorporation **MUST** update every affected live citation, ledger target, evidence
owner, heading record, generated rendering, and human document in the same atomic change. It
**MUST** update or remove an alias only as reviewed structural work.

### 3.6 Current references and historical records

A citation offered as authority for a current rule **MUST** resolve to the current owner. A prose
citation to a numbered part **MUST** continue to display `Part NN §x.y`; when it is linked, the link
**MUST** target the stable anchor, and the citation checker **MUST** verify that the displayed
number agrees with the anchor's current heading. A current process document **MUST** cite a process
rule with a Markdown link that resolves from the citing document to the owner's path and anchor.
The citation checker **MUST** normalize the resolved link to a canonical repository-relative target
such as `revisions/CONTRIBUTING.md#ew-citation-context`. A source comment or docstring **MUST** use
that canonical `path#anchor` target directly in backticks. Current process tools and documents
**MUST** use those forms rather than cite Part 00 for a maintenance rule.

A revision already committed with Accepted status **MUST** remain unchanged as a historical
record. Its citations **MAY** be interpreted using its `Based on` commit, acceptance history, or
another exact historical source tree established by review. A current document **MAY** cite an
accepted revision for clearly identified rationale or provenance that no current owner carries.
Historical resolution **MUST NOT** require a current owner to cite the revision back.
It **MUST NOT** become a packet-conformance or incorporation gate.

Once an owning publication rule declares an edition immutable, a maintainer **MUST NOT** reorganize
that edition's bytes in place. A later working specification **MAY** preserve honest canonical
anchors and aliases, but a version-specific historical reference continues to identify the
earlier edition.

### 3.7 Ledger, evidence, heading, and impact semantics

The maintainer incorporating this revision **MUST** move `ledger.py`, `applied.toml`, and
`registry-targets.toml` from `escapewheel_poc_docs_v0.2/` to `revisions/`. They **MUST** remove the
reverse-corroboration check and `corroboration-exceptions.toml`.

An `applied` ledger destination **MUST** have exactly one of these forms, with `note` as the only
optional additional field:

```toml
{ part = "02", section = "7.1" }
{ part = "02", anchor = "ew-session-scope" }
{ path = "revisions/CONTRIBUTING.md", anchor = "ew-decision-domains" }
```

`part` and `path` **MUST** be mutually exclusive, as **MUST** `section` and `anchor`. A new process
target **MUST** use `path` plus `anchor`. A structurally affected specification target **MUST**
migrate to `part` plus `anchor`; an untouched numeric `part` plus `section` target **MAY** remain
until affected by later work. A process-domain clause **MUST** resolve to a process owner recognized
by `revisions/CONTRIBUTING.md`.

A new evidence-manifest owner for Markdown **MUST** use exact `path` plus `anchor`, whether the owner
is a numbered part or a process document:

```json
{"path": "revisions/CONTRIBUTING.md", "anchor": "ew-decision-domains"}
```

A JSON owner **MUST** continue to use exact `path` plus RFC 6901 `pointer`. No accepted evidence
manifest needs a numeric Markdown-owner compatibility form at this revision's baseline. The ledger
and evidence checker **MUST** resolve each anchor before applying destination checks.

The ledger **MUST** establish that every accepted Decision clause has an exact disposition and
that every named destination exists. The evidence checker **MUST** establish that each
current-format clause identifies its current owner and downstream evidence. Neither checker
**MUST** claim semantic fidelity from existence, a backlink, or a passing implementation test.

The existing numeric heading record **MUST** remain intact. For every explicitly anchored numbered
section, `headings.toml` **MUST** add a partial anchor index of this exact form:

```toml
[anchor.ew-session-scope]
part = "02"
section = "7.1"
title = "Session scope"
aliases = []
```

The index **MUST** associate each canonical anchor with its current part, displayed number, title,
and aliases. Process-document anchors **MUST** resolve directly within their declared path and
**MUST NOT** enter the numbered-part heading record. Mechanical verification **MUST** reject a
malformed or duplicate anchor, disappearance of a recorded canonical anchor, disagreement between
an anchor record and the heading it precedes, or reassignment not recorded by the reviewed
candidate diff. The pre-acceptance appraisal **MUST** determine whether the crosswalk omits an
affected section and whether an alias names an honest primary successor. The impact tool **MUST**
report an anchor's current numbered section and live citers.

### 3.8 Incorporation boundary and provisional release path

The maintainer incorporating this revision **MUST** repoint the process-tool and live-roadmap
citations measured in §2.4 to their new anchored process owners. They **MUST** leave accepted R113
and the accepted form of this revision unchanged. They **MUST** remeasure the citation population
instead of treating the appraisal counts as permanent exceptions.

The maintainer **MUST** update the provisional `provenance` selector in `release.py` from
`escapewheel_poc_docs_v0.2/applied.toml` to `revisions/applied.toml`. They **MUST** verify that the
generator selects the moved file and its current digest, but **MUST NOT** regenerate or hand-edit
the tracked `RELEASE.json` in this incorporation. That snapshot's commit semantics, regeneration,
and final membership remain P1 work.

This incorporation **MUST NOT** change Part 00, another numbered part, a registry or rule source, a
JSON Schema, a packet field, a physical profile, a conformance fixture, or runtime packet behavior.

## 4. What this does not change

This revision does not define which specification artifacts are authoritative, the status or role
of a numbered part, release identity or membership, publication terminology, or an immutable
edition. It recognizes the editing consequence when another owning rule makes an edition
immutable.

It does not remove historical references from authoritative sources, change registry
`derived_from` or `since`, or resolve their compatibility effect on embedded registries and
existing packets. It does not rewrite accepted revisions or introduce a permanent historical
citation inventory. It does not add paragraph selectors, content hashes, relocation chains, or
requirement objects.

It does not publish or refresh `RELEASE.json`; changing the release generator's provisional ledger
selector is not a release-membership decision.

## 5. Consequence

The revision changes repository governance and process tooling without changing packet behavior.
Its principal compatibility effect is on future revision artifacts and ledger targets, not on data
packets or independent implementations.

Each Decision clause has this exact planned owner and current-guide edit surface:

| Decision clause | current owner after incorporation | existing `revisions/CONTRIBUTING.md` material replaced or extended |
|---|---|---|
| §3.1 | `#ew-decision-domains` | §§1–2 |
| §3.2 | `#ew-decision-domains` | §§2, 5, 7, and 12 |
| §3.3 | `#ew-structural-reorganization` | §§4.8 and 8.2 |
| §3.4 | `#ew-stable-section-anchors` | new material adjacent to §8.3 |
| §3.5 | `#ew-structural-reorganization-sequence` | §§6.1, 6.6, 7, 8.3, and 11 |
| §3.6 | `#ew-citation-context` | §§5.3, 8.3, and 12 |
| §3.7 | `#ew-current-owner-ledger` | §§8.1, 9, 11, and 12 |
| §3.8 | `#ew-process-incorporation-boundary` | §§8–11 and provisional-release guidance |

The incorporation inventory is exact at this baseline:

- Process owners and guides: `revisions/CONTRIBUTING.md`, `revisions/README.md`,
  `revisions/accepted/README.md`, `revisions/evidence/README.md`, `revisions/templates/README.md`,
  all three authored-stage templates, `revisions/templates/change-evidence.json`, root
  `CONTRIBUTING.md`, and `Escapewheel_Specification_Change_Process_Audit.md`.
- Open coordination: this draft, `revisions/drafts/README.md`,
  `revisions/drafts/define-specification-artifacts-and-normative-ownership.md`, and
  `revisions/proposals/ROADMAP.md`.
- Process tools: `revisions/stages.py`, `revisions/evidence.py`, `revisions/repoint.py`,
  `revisions/impact.py`, `revisions/check_citations.py`, `revisions/test_evidence.py`, the new
  `revisions/test_process.py`, `registry/check.py`, `facts.py`, and `verify.py`.
- Specification tooling: `escapewheel_poc_docs_v0.2/headings.py`, `headings.toml`, and
  `combine.py`.
- Ledger relocation: move `ledger.py`, `applied.toml`, and `registry-targets.toml` to `revisions/`
  and remove `corroboration-exceptions.toml`.
- Provisional release selection: update `release.py`; leave `RELEASE.json` unchanged.
- Generated stage-count projections: regenerate `STATUS.md`, `TODO.md`,
  `escapewheel_poc_docs_v0.2/README.md`, and the combined specification.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Numbered-part bodies are unchanged. Acceptance changes only the generated revision-count region in the specification README and combined rendering. | Numbered-part body diffs are empty; the README and combined-rendering fact regions report the new accepted and open-stage counts. |
| logical prose and registry | Unchanged. Historical-reference and registry-provenance cleanup is deferred. | Registry generation is unchanged and structural checks pass. |
| physical profiles | Unchanged because no storage requirement or profile identifier changes. | Profile sources and generated output are unchanged. |
| packet catalog and JSON Schemas | Unchanged because no packet document contract changes. | Schema and catalog diffs are empty. |
| validation and import | Packet validation and import are unchanged; repository verification gains process checks. | Registry, validator, corpus, and focused process checks pass; new process negatives fail their focused checks. |
| extensions | Unchanged because extension declarations and validity are outside this process decision. | Extension registry checks pass without extension diffs. |
| reader, writer, validator, adapters | Runtime behavior is unchanged. Only process-related source comments are repointed where measured. | The quick verifier passes. The full reader and writer stages reproduce the bounded sandbox timeouts documented in the process audit; validator and AIND pass, and no runtime package code changes. |
| conformance fixtures and tests | Packet fixtures and expectations are unchanged. `revisions/test_process.py` adds domain, anchor, bootstrap, ledger, and no-backlink cases; `test_evidence.py` changes to anchored Markdown owners. | Corpus generation is unchanged; the named process tests exercise every positive and negative case. |
| revision lifecycle and templates | Add decision domains, prospective change forms, process-specific metadata forms, structural crosswalk and sequencing rules, and stable anchors to the guide and templates. Update directory READMEs and migrate current open artifacts. | `stages.py` accepts both domains and both change forms, rejects invalid new artifacts, and accepts immutable legacy records through the exact defaults. |
| ledger and evidence | Move ledger files under `revisions/`, add part-or-path anchor targets, remove reverse corroboration, and accept anchored process owners. | Every accepted clause has a disposition; process and specification owner fixtures resolve; no owner backlink is required. |
| citation, heading, and impact tooling | Repoint 22 process-tool and two roadmap citations; add canonical-anchor, alias, number-agreement, bootstrap, heading-drift, and anchor-impact behavior. | The remeasured impact population has the required disposition; malformed and stale anchor fixtures fail. |
| generated publications and human documentation | Preserve anchors in the combined rendering; update process documentation and authority-draft coordination without generating process prose into numbered parts. Regenerate the four stage-count projections. | A second generation is stable, anchors are unique at their defined boundaries, current links resolve, and generated counts agree. |
| provisional release assembly | Change the ledger selector in `release.py` while retaining the provisional `provenance` category. Leave `RELEASE.json` unchanged for P1. | A focused release-generator test selects `revisions/applied.toml` and obtains its current digest without treating the tracked snapshot as current. |
| existing packets and migration | Unchanged because no packet bytes or interpretation change. | No packet migration or regeneration is required. |

## 6. Conformance and implementation evidence

Incorporation adds `revisions/test_process.py` as a directly executed verifier stage named
`revisions: process semantics tests`, and updates `revisions/test_evidence.py`. The evidence
manifest cites the stable identifiers shown below.

Focused process tests cover at least these cases:

1. `decision_domain_legacy_cutoff`: a new specification proposal and an ordinary specification
   draft with `Decision domain: specification` and valid specification metadata pass; a new
   process proposal and ordinary process draft with `Decision domain: process`, `Profile: not
   applicable`, and path-plus-anchor `Amends` targets pass.
2. `decision_domain_required_prospectively`: a new or promoted artifact with a missing or unknown
   domain fails. A pre-revision accepted record without the field passes as `specification`; the
   same omission in a later accepted record fails. No historical accepted file changes.
3. `change_form_required_prospectively`: a proposal without a change form passes. A prospective
   draft or accepted record with `ordinary` or `structural` passes where its domain permits that
   value; a missing or unknown value and a structural process artifact fail. A pre-revision
   accepted record needs no change-form interpretation.
4. `process_amends_requires_path_anchor`: a process draft with a numeric, mixed, or unresolved
   `Amends` target fails.
5. `ledger_process_owner_resolves`: a process clause resolves through `applied.toml` to an anchored
   section of `revisions/CONTRIBUTING.md`; a missing path, missing anchor, unrecognized process
   owner, or specification target for that process clause fails.
6. `owner_backlink_not_required`: a current owner need not cite its accepted revision. A missing
   clause disposition or unresolved destination still fails. Removing reverse corroboration does
   not weaken completeness.
7. `canonical_anchor_shape_and_identity`: a canonical anchor immediately before a numbered heading
   passes. A duplicate or malformed anchor, disappearance of a recorded anchor, or an unrecorded
   reassignment fails; a well-formed alias resolves without becoming the canonical identity.
8. `anchor_bootstrap_is_metadata_only`: the focused bootstrap check uses a structural draft's
   `Based on` commit. A commit containing only valid canonical-anchor insertions passes. A changed
   heading, number, order, body byte, normativity marker, or alias fails.
9. `linked_part_number_matches_anchor`: a linked `Part NN §x.y` citation whose anchor and displayed
   number agree passes. A stale number, missing anchor, or unresolved current link fails. Accepted
   historical citations are not rewritten or made inputs to current conformance.
10. `anchor_impact_reports_live_citers`: `impact.py` reports the current part, number, title, and
    live citers for an anchor. The heading record reports disappearance or reassignment as reviewed
    drift.
11. `combined_rendering_preserves_unique_anchors`: `combine.py` preserves canonical and alias
    anchors and the combined rendering contains no duplicate identifier.
12. `part00_process_citations_are_repointed`: the reverse-impact query for Part 00 §§10.1–10.4 is
    remeasured. Every then-current process-tool and roadmap citation resolves, after Markdown-link
    normalization where applicable, to the canonical `revisions/CONTRIBUTING.md#anchor` owner;
    Part 07 is recorded for the dependent cleanup; accepted history remains unchanged.
13. `release_generator_selects_moved_ledger`: the release generator selects
    `revisions/applied.toml` in the same provisional category and obtains its digest. The test does
    not rewrite `RELEASE.json` or treat that category as a final release-membership decision.

The human pre-acceptance appraisal verifies the structural crosswalk's affected-section
completeness and whether an alias names an honest primary successor. Mechanical checks establish
anchor shape, recorded identity, resolution, candidate stability, and ledger completeness; they
do not infer an omitted affected section, honest semantic continuity, or alias suitability from
matching text or identifiers.

## 7. Open

The dependent authoritative-source cleanup still must decide the exact clause-level disposition
of Part 00 §§10.1–10.4, remove historical references from authoritative Markdown and incorporated
JSON, remove registry-build provenance, and appraise whether revision-valued `since` has a genuine
edition-compatibility replacement. Those choices do not alter this revision's process mechanism.

The authority-and-normative-ownership draft still must define specification authority, artifact
roles and status, release identity and membership, publication terminology, and the final homes of
preserved current-contract statements. Those choices do not alter the process owner's structural
editing rules.

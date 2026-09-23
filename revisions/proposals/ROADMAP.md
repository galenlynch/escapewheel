# Escapewheel v0.2 reconciliation roadmap

| | |
|---|---|
| **Status** | Non-authoritative coordination record |
| **Updated** | 2026-09-23 |
| **Review baseline** | `8d3a9c8598dd0152930ee0aab4de9a19a5496f22` |
| **Objective** | Reconcile the data-driven contract, then publish one internally consistent and immutable v0.2 specification release |

This document preserves the project review, the appraisal of the first authority proposal, and the
dependency order for the resulting work. It exists so that narrowing or replacing an individual
proposal does not discard research needed by later proposals.

This is not a proposal, a revision draft, or an authority for packet behavior. It cannot settle a
normative question or bypass the lifecycle in the [specification change guide](../CONTRIBUTING.md).
Each contract change below still needs its own reproduced problem, appraisal, promotion decision,
draft, acceptance authorization, incorporation evidence, and verification. The current generated
v0.2 material remains authoritative while this roadmap is being worked.

Labels such as P0.1, P0.2, and P1 are coordination identifiers for work items in this roadmap. They
are not section numbers in a proposal or draft, and they are not the permanent `R<N>` numbers
assigned to accepted revisions.

The principal inputs are the
[project sanity check](../../Escapewheel_Project_Sanity_Check_2026-09-17.md), the
[change-process audit](../../Escapewheel_Specification_Change_Process_Audit.md), the root
[TODO](../../TODO.md), and the research carried into the current
[R122 authority revision](../accepted/R122-define-specification-artifacts-and-normative-ownership.md). The project review
was performed at commit `32f9e06884b483818c7156f80ea81f7e3a6ce002`. Subsequent commits through
the review baseline changed documentation, revision workflow, lint findings, and formatting rather
than resolving the packet-contract findings mapped below.

This roadmap tracks dependency and disposition at the work-item level. The separate
[placement-defect inventory](../PLACEMENT-DEFECTS.md) tracks individual statements that appear to
occupy the wrong owner or duplicate another rule; those details do not belong in this sequencing
document.

## 1. How to use and maintain this roadmap

This document owns the durable plan: design direction, work-item scope, dependency order, exit
evidence, and the mapping from review findings to work. It does not track transient working state;
keep the current artifact, baseline, appraisal state, pending decisions, and next action outside the
version-controlled roadmap.

Update this roadmap when appraisal changes a work item's scope, dependency graph, exit evidence,
finding disposition, or the long-term design direction. Do not update it merely because a lifecycle
artifact changes stage, and do not copy generated counts into it. Before appraising any proposal,
re-establish the baseline and overlap inventory described in the change-process guide; this ordering
is a plan, not evidence that a later proposal remains fresh.

## 2. Long-term design direction preserved from the authority research

The research supports a role-partitioned specification rather than either “prose always wins” or
“JSON always wins.” The intended endpoint has the following properties. They are design constraints
for later appraisal, not decisions made by this roadmap.

### 2.1 Authority is divided by concern

- Numbered prose owns meanings, processing semantics, actor obligations, conformance, and
  relationships that structural data cannot express faithfully.
- A registry meta-schema owns the permitted structure of registry documents after its vocabulary
  and semantics have been reconciled with Part 02.
- Released core and extension registries own their exact declarations: resources, tables, columns,
  keys, references, vocabularies, and executable rules whose language has been specified.
- Incorporated JSON Schemas own the exact structure of the documents they cover. Named semantic
  validation owns constraints that JSON Schema cannot express.
- Part 00 owns artifact-role semantics and the exact normative, informative, or mixed status of
  each numbered part. A specification release manifest eventually owns release identity,
  membership, member-role assignments, sizes, and digests; any numbered-part status it records is
  a checked projection of Part 00.
- Revisions own history and rationale. Implementations, adapters, generators, tests, and developer
  documentation provide behavior or evidence but acquire no independent normative subject.

Each fact should have one owner. A second representation is either a checked projection or a
consistency check. A disagreement among owning artifacts makes a candidate release invalid; a
blanket precedence rule must not turn a known inconsistent bundle into a release.

Normativity and generation are independent properties. A generated registry can be normative for
exact assignments, while a generated Markdown table can remain an informative projection. The
combined specification can reproduce normative text without becoming a separately edited owner.

### 2.2 Part 00 is the framework; the specification README is an entry point

Part 00 is the natural owner of specification identity, conformance targets, normative-language
conventions, normative-reference policy and cross-cutting references, artifact roles, status
conventions, actors, abstraction boundaries, part ownership, dependency direction, and publication
conventions. A reference used by only one numbered part should live with that part's subject; a
shared reference should retain one entry in Part 00. Part 00 should distinguish:

- **abstraction levels:** semantic, logical, and physical; and
- **packet content classes:** the architectural relationship of core, extension, analysis, and
  projection content to the packet's interoperable facts.

Those axes intersect. A core table, an extension table, and an analysis table are all logical
resources and all have physical representations. Namespace remains the dotted-identifier ownership
mechanism, while table, array, media, document, and view remain resource kinds. Exact keys,
resource counts, profile encodings, performance measurements, and implementation plans therefore
do not belong in Part 00.

The specification README should be an informational navigation and release entry point.
Cross-cutting conformance rules should live in Part 00, and detailed rules should move to their
owning numbered parts. Its release inventory should eventually be a view of the release manifest
rather than a manually maintained second list.

### 2.3 Machine-readable authority is layered, not absolute

The useful analogy is the separation among vocabulary, meta-schema, and instance:

```text
prose field semantics and processing rules
                 |
                 v
registry or document meta-schema
                 |
                 v
released registry or packet document
                 |
                 v
generated validation plan and implementations
```

A meta-schema can establish JSON shape but cannot, by itself, establish key compatibility,
namespace policy, reference validity, rule execution semantics, or extension parity. A generated
artifact can own an exact released declaration when a reviewed source and deterministic compiler
produce it; the generator is then a compiler, not the authority.

The data path remains:

```text
specification prose + schemas + released registries
                         |
                         v
                 data-driven contract
                         |
source files -> adapter -> writer -> validated packet -> reader / consumer
```

Lab- or task-specific packet facts enter through extension registries. Lab- or task-specific source
formats enter through adapters. An adapter translates into registry-declared resources; it does not
silently extend the packet contract or relax its validation rules.

### 2.4 The eventual release is an explicit bundle

The preferred publication target is a directly declared, machine-readable release manifest. Its
member descriptors should be appraised for path, role, normative status, media type, byte size,
digest, and any stable identifier or version exposed by the member. Membership and roles should not
be inferred from Python constants, directory globs, or repository co-location. Lab-specific
extension registries, tests, conformance programs, provenance records, and implementations should
not become core release members merely because they live in this monorepo.

The manifest need not contain its own digest. Its exact bytes can be addressed externally, while it
content-addresses its members. Publication tooling can verify declared membership and refresh
mechanical size and digest fields, but it should not choose the members. Candidate verification and
publication from a clean commit are workflow states; the final publication proposal must decide
whether and how those states appear in machine-readable identity.

This direction follows established patterns rather than a repository-specific precedence rule:

| reference | useful pattern |
|---|---|
| [JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core) | vocabulary semantics are distinct from meta-schema validation |
| [Unicode Standard Annex #44](https://www.unicode.org/reports/tr44/) | prose algorithms and exact published data are integral, complementary parts of one standard |
| [IANA protocol registration](https://www.iana.org/help/protocol-registration) | registry structure and allocation policy are separate from exact assignments |
| [Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html) | prose and machine-readable schemas coexist; generated renderings need not be separate owners |
| [Zarr v3 core specification](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html) | normative status is explicit and informative material is marked |
| [OCI descriptors](https://github.com/opencontainers/image-spec/blob/main/descriptor.md) | media type, size, and digest identify an addressed artifact without a self-digest cycle |

## 3. Promotion history of the authority work

**Original disposition: revise before promotion. Current state: accepted and incorporated as R122
on 2026-09-20.**
The original proposal contained sound research and a useful target model, but combined the first
enabling decision with the final publication step. Its scope was narrowed on 2026-09-17, and the
first promotion appraisal's ownership, terminology, impact, and evidence findings were
incorporated. A second appraisal assigned the normative bibliography to Part 00, separated the
placement-defect inventory from both the specification and this roadmap, and clarified that a
release manifest records numbered-part status only as a checked projection. The user then
authorized promotion.

### 3.1 What the promoted draft retains

The promoted draft retains the framework needed by every later proposal:

- the generated v0.2 material is the current authority during development;
- Part 00 owns the specification framework and explicit abstraction model;
- the specification README is informational and carries no unique rule;
- authority is assigned by concern, each fact has one owner, and conflicts invalidate a candidate;
- normative status, source form, generated form, and implementation are separate axes;
- candidate and released states are distinct; and
- later machine-readable artifacts become authoritative only through an explicit incorporation and
  publication rule.

This scope can establish the vocabulary by which later proposals identify their owners without
claiming that today's unresolved registries and schemas already form a final release.

### 3.2 What remains outside the first revision

The narrowing left the following work in later entries in this roadmap:

- exact final release membership, `release.schema.json`, final `RELEASE.json` contents, and the
  publication implementation;
- incorporation of the current registry meta-schema as normative;
- the executable meaning of Tier 2 SQL rules;
- the full unit-identity reconciliation across prose, examples, reader APIs, fixtures, types, and
  integration tests;
- packet resource classification, including `layer` and `canonical`;
- packet identification of core and extension registries;
- incorporation of the remaining packet, resource, source, and adapter schemas; and
- final semantic, logical, profile, registry, schema, and rule-language identifiers.

### 3.3 Material findings that narrowed the proposal

1. The proposal incorrectly says there is no committed `RELEASE.json`. One is tracked, but it is a
   stale output of the current prototype: it records commit
   `2a3a05ea10604e037016ae426054cab3955fa2db`, its membership is selected by `release.py`, and the
   monorepo verifier does not establish it as the current release authority.
2. Incorporating `registry/registry.schema.json` now would overstate what it proves. It validates
   document shape, while the review's D1, D2, I2, I7, and I11 findings require shared semantic
   registry conformance for core, extensions, embedded copies, and public construction boundaries.
3. Part 02 §10.2 calls Tier 2 predicates SQL but does not define a dialect or execution contract.
   R2 §7.2 and §7.3 historically selected DuckDB, and the reference validator uses it, but neither
   historical rationale nor implementation behavior defines the current normative language. The
   77 released rules use behavior such as `median`, `INTERVAL`, window functions, `USING`, and
   `IS DISTINCT FROM`.
4. Exact executable rules require a named and versioned language or restricted subset, relation
   naming, logical-to-SQL type mapping, null and numerical semantics, allowed statement and function
   sets, failure behavior, and language-version negotiation. Empty-table parse checks are not
   sufficient evidence; representative positive and negative data cases are needed.
5. Unit identity is settled in Part 02 and the core registry, but the proposal understates its
   repair surface. Part 08 queries, `Packet.spike_times()`, reader fixtures, public types and docs,
   extension joins, and a writer-reader-validator integration test must agree before that
   contradiction is closed.
6. Final membership and immutable hashes cannot sensibly freeze artifacts known to disagree on
   resource requiredness, manifest structure, extension validity, recipe arbitration, and version
   identity. Publication is the last convergence step, not the mechanism for overlooking those
   disagreements.

The promotion appraisals rechecked the narrowed impact inventory, dependency order, evidence plan,
and resolved questions. The first pre-acceptance appraisal then found that exact relocation and
citer dispositions, maintainer binding, and the structural landing still needed revision. The
ordinary-change rule in the [revision process](../CONTRIBUTING.md#ew-structural-reorganization)
would force the new framework and relocated README material to the
ends of their parts, so the separate controlled-reorganization process change is now a prerequisite.
Promotion did not accept or incorporate the authority decision.

## 4. Work-item dependency order and records

The ordering below follows normative dependencies. It does not require unrelated proposals in the
same family to wait when their owners and evidence are independent.

```text
P0 process foundation (complete)
 |
 v
P0.1 controlled reorganization
 |
 v
P0.2 remove historical and misplaced maintenance material from authoritative artifacts
 |
 v
P1 authority framework
 |\
 | +--> P2 placement and unit-identity reconciliation
 |
 +--> P2.1 subject-owned normative references
       |
       v
     P3 executable rule language
       |
       v
     P4.1 registry conformance contract
       |
       v
     P4.2 uniform registry-validation boundaries
       |
       v
     P5.1 logical resource declarations
       |
       v
     P5.2 physical profile and reader floor
       |
       v
     P6 packet manifest contract
       |                \
       v                 v
     P7 validity       P8 recipe/adapter contract
       \                 /
        +---- P9 remaining reconciliations
                      |
                      v
        P10 identifiers and source cleanup
                      |
                      v
        P11 immutable v0.2 publication
```

| ID | Work item | Depends on | Accepted record or target |
|---|---|---|---|
| P0 | Revision-process foundation | — | [Change-process guide](../CONTRIBUTING.md) and process audit |
| P0.1 | Controlled reorganization of specification parts | P0 | [R120](../accepted/R120-allow-controlled-specification-reorganization.md) |
| P0.2 | Remove historical and misplaced maintenance material from authoritative artifacts | P0.1 | [R121](../accepted/R121-remove-historical-and-misplaced-maintenance-material.md) |
| P1 | Specification authority, abstraction levels, and normative ownership | P0.1, P0.2 | [R122](../accepted/R122-define-specification-artifacts-and-normative-ownership.md) |
| P2 | Placement cleanup and unit-identity reconciliation | P1 | [R123](../accepted/R123-a-unit-is-identified-by-its-packet-assigned-unit-id.md) |
| P2.1 | Locate normative references with their subject owners | P1; executed after P2 | [R124](../accepted/R124-normative-references-reside-with-their-subject-owners.md) |
| P3 | Executable declarative-rule language | P2.1 | [R125](../accepted/R125-tier-2-rules-use-a-versioned-escapewheel-sql-profile.md) |
| P4.1 | Registry-document conformance contract | P3 | [R126](../accepted/R126-a-registry-document-has-one-complete-conformance-contract.md) |
| P4.2 | Uniform registry-validation boundaries | P4.1 | [R127](../accepted/R127-registry-documents-are-checked-at-conformance-boundaries.md) |
| P5.1 | Logical resource declarations and resource classification | P4.2 | [R128](../accepted/R128-every-packet-resource-instantiates-a-logical-declaration.md) |
| P5.2 | Portable-profile interfaces and reader floor | P5.1 | [R129](../accepted/R129-a-portable-profile-declares-its-interfaces-and-reader-floor.md) |
| P6 | Packet manifest, requiredness, and registry binding | P5.1, P5.2 | Active draft |
| P7 | Core, extension, and packet validity composition | P4.2, P6 | Proposal to be scoped |
| P8 | Recipe arbitration and adapter contract | P5.1, P5.2, P6 | Proposal to be scoped |
| P9 | Remaining lifecycle, integrity, portability, and scope reconciliations | P5.1–P8 as applicable | Proposal family; split before promotion |
| P10 | Final identifiers, direct registry source, and release integration | P2, P2.1, and P3–P9 | Proposal plus ordinary maintenance |
| P11 | Immutable v0.2 specification publication | P1–P10 | Proposal to be scoped |

### P0 — Revision-process foundation

The process audit has already separated proposal appraisal, draft appraisal, acceptance,
incorporation, regeneration, implementation alignment, and atomic closure. Exact registry targets,
corroboration exceptions, per-revision evidence manifests, runtime capability probes, proposal
structure checks, and candidate-state regeneration checks are implemented. These controls make the
following sequence tractable; they do not decide any packet contract.

### P0.1 — Controlled specification reorganization

The [revision process](../CONTRIBUTING.md#ew-structural-reorganization) makes append-only numbering
the safe default for an ordinary
amendment, but it would put P1's organizing framework after the material it organizes and would
force relocated README rules to the ends of their subject-owning parts. The proposal retains the
stable-anchor, human-crosswalk, metadata-bootstrap, and immutable-edition research while reopening
which artifact owns the procedure. Its acceptance appraisal found that placing repository
maintenance and historical-revision mechanics in normative Part 00 crosses the packet-contract
boundary. It also found that the ledger currently reverses the intended dependency by requiring a
current specification section to cite its historical revision. R120 resolves those questions by
placing process in `revisions/CONTRIBUTING.md`, moving ledger traceability under `revisions/`, and
splitting authoritative-source cleanup into P0.2, without taking P1's ownership of artifact roles,
release membership, or publication identity.

R120 also extends the lifecycle narrowly to material decisions about its own gates, process
authority, structural-editing permissions, ledger dispositions, and evidence semantics. Such a
revision declares the process decision domain and lands its clauses in exact anchored process
owners; it does not make those clauses packet requirements. Meaning-preserving documentation and
implementation maintenance remain ordinary repository work. The same `R<N>` sequence records
incorporation order for specification and process decisions. Existing accepted records default to
the specification decision domain without being edited. R120 declares the process domain, current
open artifacts gain an explicit domain during incorporation, and later artifacts must declare one.
For a process draft, `Profile` is `not applicable`, `Change form` is `ordinary`, and `Amends` names
exact path-plus-anchor process owners. A specification draft declares an `ordinary` or `structural`
change form; the latter is the explicit switch for the crosswalk and anchor-bootstrap procedure.

**Exit evidence:** the accepted process distinguishes routine amendment from structural
reorganization and requires a complete human-readable crosswalk; stable anchors, current
destinations, live citations, ledger targets, and evidence owners resolve; maintenance rules live
outside packet-conformance prose; and the ledger maps accepted clauses to standalone current
owners without requiring those owners to cite history back. The completed historical-revision
audit remains non-gating evidence and is not part of current normative interpretation. Editions
declared immutable elsewhere cannot be reorganized in place.
Before a structural draft's final appraisal and acceptance request, a checked, separately committed
metadata-only bootstrap assigns anchors wherever an affected existing source or destination lacks
one, without changing prose, structure, normativity, or meaning; the draft names that commit as its
baseline, and new destinations receive anchors in the structural incorporation. If no bootstrap is
needed, the human-readable crosswalk records that fact.

The final appraisal baseline's reverse-impact query reports 29 citations into Part 00
§§10.1–10.4. R120 repoints the 22 process-tool citations and two live-roadmap citations to the
contribution guide. P0.2 dispositions the one current Part 07 citation. Three R113 citations and
the one citation carried into R120 remain unchanged as history.
Incorporation re-measures these populations.

**Revised after promotion appraisal:** the earlier machine-readable paragraph selectors, content
hashes, relocation chains, and separate relocation artifact were rejected as a disproportionate
requirements-management system. The replacement combines the RFC-style immutable-edition model,
W3C-style version history, and explicit section anchors with aliases. Existing tools are extended
to check the current working specification; the accepted revision and Git history preserve the old
state.

**Re-appraisal resolution:** retain that simplified model. The revised proposal expressly permits a
strictly metadata-only anchor bootstrap after P0.1 lands; confines P0.1 to edit and reference
mechanics while P1 owns authority, artifact, release, and publication semantics; and requires
historical citations to be checked against the appraised pre-change and incorporated post-change
contexts. The R112 history demonstrates that its acceptance commit and newly incorporated Part 00
§10.3 are recoverable through Git. Pre-v0.2 references are audited individually.

**Acceptance-appraisal revision:** resolving only at incorporation was rejected because R93 removes
the former Part 02 section its decision discusses. The 38 historical references divide into 18
frozen-v0.1 headings, seven R93 references that resolve pre-change, and 13 frozen Part 06 line
locators. Because the early revision records and specification sources began in parallel histories,
the draft adds exact legacy source contexts as well as the non-growing line-locator inventory. It
leaves crosswalk completeness to human review, requires every extant affected section to carry a
canonical anchor, and gives §§3.1–3.8 exact planned destinations in a new Part 00 section 11.
Production enforcement remains in atomic incorporation; disposable feasibility probes precede
acceptance.

**Returned to proposal after acceptance appraisal:** the complete citation audit found 419 Part
citations in accepted records rather than only the 38 that fail against today's tree, but that
measurement exposed a more important direction error. Historical citations run from revision
records to the specification state they discuss; they do not justify the 478 revision references
in the authored specification Markdown or the ledger check that requires those backlinks. The
proposal now treats accepted-revision resolution as an archival-process question, reopens the
owner of maintenance procedure, and requires one-way revision-to-ledger-to-current-owner
traceability. It also reopens whether registry `since` and other authoritative-source provenance
should be removed or expressed as specification-edition identity.

**Ownership resolution:** `revisions/CONTRIBUTING.md` owns structural-editing procedure; no process
section is added to Part 00. The ledger and its maps move under `revisions/`, accept exact
part-or-path plus stable-anchor prose destinations, and stop requiring current owners to cite their
revision back. The completed historical audit remains non-gating evidence. Removing the existing
historical references and misplaced maintenance text is split into P0.2 because Part 00 needs a
clause-level disposition and revision-valued `since` and registry build provenance change the
registry meta-schema and generated registry rather than process alone.

**Authority-draft-focused re-appraisal:** the process permits every kind of edit P1 requires, but
P1 cannot land unchanged. With R120 incorporated, P1 identifies its exact affected sections;
a separately committed metadata-only change bootstraps their existing source and destination
headings; and P1 refreshes its baseline to that commit. It then depends on the accepted P0.1
revision, applies the resulting boundary between maintenance policy and specification content,
replaces its subject-level README disposition with an exact paragraph crosswalk, names its
resulting Part 00 outline, assigns anchors and aliases to new destinations, converts affected
ledger and evidence targets, and reruns appraisal. The earlier assumption that P0.1 contributes an
appended Part 00 process section is rejected.

**Resolved anchor coverage:** every structurally affected source and destination receives an
anchor. Existing affected headings are anchored in a separately committed metadata-only bootstrap
before structural incorporation; new headings receive anchors when created. Untouched sections
remain outside the migration.

**Resolved lifecycle sequencing:** the existing acceptance sequence forbids an intervening commit
after acceptance authorization. P0.1 therefore requires the structural draft to identify affected
headings and declare `Change form: structural`; where anchors are missing, it commits their
metadata-only bootstrap, names that commit as `Based on`, and finally appraises the draft against
it. Where every affected heading is already anchored, its crosswalk records that no bootstrap was
required. The exact appraised draft is committed before acceptance is requested. P1 §7 already
records this order.
The restored and re-appraised proposal is preserved at
`07439b738b55264bffd2c6ffbf3cc41390acc024`. Promotion on 2026-09-18 carried its process owner,
decision-domain migration, one-way ledger model, structural controls, and P0.2 boundary into the
draft. Its complete pre-acceptance appraisal then passed, and the exact candidate was committed as
`166f09d130a6892794a61e752266dc8f8d7635a5` before acceptance.

**Completed as R120 on 2026-09-18.** Its accepted record and incorporation evidence are
[preserved together](../accepted/R120-allow-controlled-specification-reorganization.md).

### P0.2 — Remove historical and misplaced maintenance material from authoritative artifacts

The [accepted revision](../accepted/R121-remove-historical-and-misplaced-maintenance-material.md) carries the
measured inventory, compatibility analysis, candidate Decision, structural crosswalk, and evidence
plan for this work. Its appraised proposal is preserved at
`4baad5df16c74d6cea445f05594d57d45c74c7a2`.

Apply the strict one-way model now that R120 supplies the structural process. Remove revision
citations from the specification README and numbered parts, incorporated registry and schema
descriptions, validation-rule messages, and extension registry sources. Remove the registry-build
`derived_from` object, which is change provenance rather than packet meaning, and remove
revision-valued `since` without replacement because no compatibility behavior consumes it. Give
the cleaned meta-schema a new `0.2.0` identity, advance the core registry to `0.2.0`, and regenerate
development packets. Replace the generator's one history-valued name-column selector with the
equivalent assigned-primary-key derivation. Do not confuse this registry-build provenance with the
packet manifest's `derived_from`, which names source resources and remains part of the packet
contract.

**Completed as R121 on 2026-09-19.** The cleaned current owners, projections, implementation,
evidence manifest, and process/documentation updates were incorporated atomically.

Account separately for every statement in Part 00 §§10.1–10.4. Remove repository-maintenance and
citation-presentation rules after their current process owners exist in
`revisions/CONTRIBUTING.md`; and remove revision provenance. Part 00 §9 and Part 02 §1 already carry
the current-contract ownership meaning that remains before P1, so §§10.1–10.4 need no temporary
normative replacement. Remove the specification README's revision-status projection and the stale
provisional `RELEASE.json`; move its useful digest experiment to non-writing prototype tooling. P1
still owns candidate and released authority classification, while P11 owns future release-manifest
and publication-tooling design.

**Exit evidence:** authoritative prose and incorporated machine-readable artifacts contain no
references to revision records; the ledger and evidence manifests preserve change provenance;
registry generation is internally consistent under the new meta-schema identity; development
packets are regenerated against core registry `0.2.0`; and no provisional release snapshot claims
current publication state. P1 begins only after this cleanup lands.

### P1 — Authority framework

R122 makes Part 00 capable of locating later decisions without publishing the final release
bundle prematurely. It states the relationship between semantic, logical, and physical
abstraction levels and the separate packet content classes, and it incorporates no
machine-readable artifact whose semantics or current contents remain under dispute.
P1, not P0.1, owns the semantics of specification-candidate authority, artifact roles and candidate
membership, and candidate-versus-release terminology. It does not select final release membership,
identifiers, or the publication record; P11 owns those decisions.

R122 was appraised against the metadata-only anchor bootstrap
`41da62e3fd4924e5526f8f812492e90607d14d97`, immediately after R121. Its 2026-09-20
pre-acceptance appraisal is complete: the exact old-to-new structural crosswalk, statement-level
README disposition, authority and reference rules, affected citation and tooling surfaces,
owner/evidence plan, and mechanical gates have no remaining blocker. Eleven pre-existing semantic
citation defects found during the required citation reading have explicit incorporation
dispositions rather than being silently carried through the reorganization.

**Exit evidence:** Part 00 and the informational README boundary are unambiguous; every numbered
part has a stated subject and dependency direction; candidate disagreements are classified as
release defects; normative references have exactly one owner under the hybrid policy completed by
R124; later proposals can name an
authoritative owner without invoking an informal precedence rule. Individual placement problems
remain traceable in the [placement-defect inventory](../PLACEMENT-DEFECTS.md) rather than in Part 00
or this roadmap.

### P2 — Placement cleanup and unit identity

Perform the first ownership-driven placement pass. Reconcile unit identity around the already
selected Part 02 rule: packet-assigned, packet-unique `unit_id` as the primary key. Remove or demote
misplaced composite-key statements and update Part 08 examples, reader APIs, generated or shared
fixtures, extension joins, public typing and documentation, and integration evidence. Also remove
stale exact counts and measured implementation facts from Part 00 and repair the stale part
inventory.

Broader moves that merely preserve meaning can use the ordinary documentation workflow after their
owner is clear. Any move that changes what a conforming implementation can do remains a separate
proposal. Any large reorganization uses P0.1's relocation and citation controls; forwarding text
remains available when a published anchor needs a compatibility period.

**Completed as R123 on 2026-09-21.** Part 02 now solely owns packet-local unit identity and logical
session scope; Part 05 owns reader presentation, same-session correlation, exact-unit selection,
and registry-derived public identifier types. The composite statements and stale counts and
measurements were removed from Part 00 and Part 01, and the reader, fixtures, examples, evidence,
and current documentation were reconciled. Meaning-preserving cleanup elsewhere in Parts 01 and
02 remains ordinary placement maintenance; any semantic difference returns through a separate
proposal.

**Review coverage:** S0, S1, S8, S9, I3, I10, and the unit-identity portion of I9.

### P2.1 — Subject-owned normative references

R122 deliberately gave Part 00 the complete normative bibliography. Review of P3's proposed SQL
and IEEE dependencies reopened that choice: the numbered parts are separately readable normative
documents, and an external authority used by one part is easier to find and better placed beside
the subject that invokes it. Part 00 should retain the reference policy and one copy of genuinely
cross-cutting references, while Part 03 receives the portable-format references, Part 04 receives
the SHA-256 reference, and the future Part 11 receives its SQL and floating-point references.

This is a small structural precursor rather than an incidental P3 edit because it changes an
accepted ownership rule independently of the rule language. It preserves every existing external
identity, candidate edition state, invocation scope, packet behavior, and release-time requirement
to pin exact editions. The framework checker moves from a central-only inventory to an exact-owner
inventory. P3 then rebases on the resulting general policy instead of creating a language-specific
exception.

**Exit evidence:** Part 00 states the general and shared-reference rule; each existing bibliography
entry appears once in its approved owner; framework mutations reject a missing, misplaced, or
duplicated entry; current packet and corpus behavior is unchanged; and P3 can place the ISO SQL and
IEEE 754 references in Part 11.

**Completed as R124 on 2026-09-21.** Part 00 now owns reference policy and the four shared entries;
Part 03 owns the six portable-profile rows; and Part 04 owns FIPS 180-4. Direct invocation, rather
than transitive reliance on another part's contract, determines placement. The distributed
framework check and its mutation probes enforce exact ownership, invocation, and the ban on
implementation-valued authorities. P3 may now place its SQL and IEEE references in Part 11.

### P3 — Executable declarative-rule language

Define the language in which a registry's Tier 2 predicates execute before calling their exact SQL
text normative. Appraise whether this is a versioned Escapewheel subset specified in terms of tested
DuckDB behavior or another portable contract. Define relation naming, type mapping, null/NaN/time
and arithmetic semantics, allowed query shape and functions, failure behavior, and language-version
negotiation. Keep Tier 1 invariant meaning distinct from any generated SQL used to implement it.

**Exit evidence:** independent validators can tell whether a rule is supported and obtain the same
offending-row meaning; representative rule fixtures exercise data semantics rather than parse only
empty tables.

**Review coverage:** the executable portion of D1 and the lower-priority SQL-fixture finding.

### P4.1 — Registry-document conformance contract

Reconcile Part 02 with the meta-schema after P3 supplies a rule language. Define core and extension
document classes and specify the complete invariants JSON Schema cannot establish: stable and
unique identifiers, namespace restrictions, compatible primary and foreign keys, roles, presence,
vocabulary, rule references, and extension restrictions. Separate those invariants from
repository-only authoring conventions and give independent implementations portable positive and
negative evidence. Only then consider the meta-schema and released registries coherent enough to
validate uniformly.

This is separated from invocation because defining a document contract and deciding how each
public boundary reacts to its result are independently reviewable decisions. The accepted
[R126](../accepted/R126-a-registry-document-has-one-complete-conformance-contract.md) records the
contract and the exact boundary with the next item.

**Review coverage:** the registry-semantics portion of D1 and I2, plus the registry-fixture portion
of I9.

### P4.2 — Uniform registry-validation boundaries

Apply P4.1's one registry-document result at every trust boundary: the released core registry,
released extensions, embedded packet copies, writer startup, validator registry loading, extension
author tooling, and direct public writer construction. Define phase ordering so malformed shape is
reported without running unsafe semantic checks, and so an invalid or unsupported registry is not
used to generate data checks.

Preserve P7's ownership of missing declared registries, extension table physical validation,
partial reader access, and composition of core, extension, and packet verdicts. P4.2 establishes
the document result those policies consume; it does not decide the overall packet result.

**Review coverage:** D2, the invocation portions of D1 and I2, I11, and the registry-boundary
portion of I9. I7's physical extension-table parity remains with P7.

### P5.1 — Logical resource declarations and classification

Extend the data-driven logical model beyond tables. Make resources the registry's primary
declarations and give table, dense-array, and opaque payloads one declaration model. Define
singleton, catalog, and family instances, presence, catalog-row binding, dependencies,
canonicality derived from content class, lineage, and extension-owned non-table assets. Bind each
packet resource to one declaration and remove packet classification fields that merely repeat the
declaration.

Keep the decision storage-agnostic. It may define the logical field through which a later physical
encoding is selected, but it does not declare formats, codecs, a portable reader floor, or the
Part 03 descriptor that owns them.

**Review coverage:** S3, S6, D3's logical half, D8, I4, I5, and the first live TODO.

**Completed as R128 on 2026-09-23.** Registry resources now own logical classification and
instance policy for 43 singleton tables and the three incorporated catalog families. Packet
entries bind `declaration_id` without repeating logical facts; catalog rows carry packet resource
identity; and the registry, reader, writer, validator, adapters, extensions, fixtures, and schemas
use the incompatible 0.5/0.2 shapes. The closed logical-kind vocabulary is `table`, `dense_array`,
and `opaque`; physical interfaces and the reader floor remain with the next work item.

### P5.2 — Portable-profile interfaces and reader floor

Give Part 03 a machine-readable descriptor for generic physical interfaces and the portable reader
floor. Define the relationship between each modeled logical resource kind and its permitted
interface, leave opaque representations open and unenumerated, declare the minimum features every
conforming reader supports directly for each interface or variant, and represent materialized or
view realization without changing logical kind. The descriptor does not create general capability
IDs or enumerate optional implementation support. It remains a physical-layer authority consumed
by packet binding and validation, not a second logical registry.

The selected profile and resolved logical kind choose the current generic interface; the current
profile fixes each table as one Parquet object, while array metadata identifies Zarr format version,
codecs, and other self-describing physical features. Packet entries do not duplicate those facts as
selectors, layout declarations, codec declarations, or capability summaries.
The current Parquet interface is single-file only. Partitioned tables remain future-profile work
until demonstrated need justifies explicit immutable membership, row-order, partition-value, and
schema semantics.

This stage determines the physical-profile model needed by P6 and records the measured current
floor in terms that compare exactly with Parquet and Zarr metadata. P9.3 may later reconsider floor
membership and owns standardized portability findings and verdict composition.

**Review coverage:** S10 in model form, D3's physical half, and I8's capability-model portion.

### P6 — Packet manifest, requiredness, and registry binding

Reconcile Part 04 with `manifest.schema.json` and the resource schema using P5.1's logical
declarations and P5.2's physical-profile model.
Generate shared structural definitions where possible and add named semantic checks for uniqueness,
format, state, and cross-field invariants. Decide how a packet identifies each core and extension
registry by stable identifier, version, and digest; whether it embeds a copy; what validators
compare; and whether the candidate packet corpus is regenerated.

Do not confuse the packet manifest with the later specification release manifest. The former binds
one dataset to its resources and registries; the latter binds one publication of the standard.

**Review coverage:** S2, S3, S11, I6, packet registry identity from the TODO, and the audits of
`manifest.schema.json` and `resources.schema.json`.

### P7 — Validity composition and extension parity

Define `core_passed`, a result for every declared extension, and overall `packet_passed`. Specify
how missing, unreadable, structurally invalid, semantically invalid, and unsupported registries and
resources compose into those verdicts; P6 defines a missing, unreadable, or mismatched bound
registry as a named manifest binding finding that withholds only that registry's declaration checks,
and bars a writer from publishing a manifest with such a finding. Make writer publication depend on
the resulting packet verdict. Preserve useful partial reader access without reporting an invalid
declared extension as a valid packet.

Validate row-valued unit codes under the same case-sensitive UCUM edition selected by P4.1 when a
column's `unit_from` resolves to a packet column. P4.1 proves that the declaration resolves to a
string column carrying the canonical UCUM authority and validates literal `unit` attributes; P7
owns the value scan and its contribution to resource, extension, and packet verdicts.

**Review coverage:** I1, the validity portions of D2/I2/I7, Part 09 consistency, extension finding
serialization, and the valid/invalid extension portion of I9.

### P8 — Recipe arbitration and adapter contract

Move source preference and shared-contribution policy from writer or lab code into the session
recipe. Publish and reconcile the recipe, source, resource-delivery, and adapter declaration
schemas. Specify array and non-table delivery capability, close the adapter no-write contradiction,
and validate declarations at every public boundary. Keep source-format knowledge in adapters and
packet semantics in registries and profiles.

**Review coverage:** S5, D4, D5, D6, I11, and the audits of `sources.schema.json` and
`adapter.schema.json`.

### P9 — Remaining independent reconciliations

Split this family wherever the decisions can stand independently:

1. **Build validation and publication ordering** — reconcile Part 00 summaries with the detailed
   Part 05 lifecycle and the writer's commit gate (S4).
2. **External and prefix integrity** — define checksum behavior for prefix resources consistently
   across the physical and packet contracts (S7).
3. **Codec capability and portability** — settle exact reader-floor membership and distinguish
   features outside the floor, validity, and portability reporting (the remaining part of S10/I8).
4. **Profile scope and document organization** — state the present electrophysiology/profile scope
   accurately and consider moving the adapter/build interface out of the physical-storage part in
   the next version (S12 and documentation organization).
5. **Non-finite domain semantics** — after P3 defines deterministic floating-point language
   behavior, audit each scientific rule that can receive NaN and decide whether its domain
   predicate intentionally accepts or rejects that value. Do not confuse that domain decision with
   the rule language's comparison semantics.

Analysis lineage and canonicality belong in P5.1 rather than this catch-all; adapter write capability
belongs in P8. This placement keeps the earlier review's “remaining reconciliations” from becoming
one omnibus revision.

### P10 — Final identifiers, direct source, and integration

After the contract stabilizes, assign correct semantic, logical, physical-profile, registry,
meta-schema, packet-schema, and rule-language identifiers. Lift the deliberate
`registry_version` hold and ensure identifiers change whenever governed bytes or contracts are
incompatible. Apply the packet registry-binding decision from P6 using the final identifiers and
digests.

The hold is provisional rather than permission to reuse an identifier for incompatible bytes.
P4.1 advances the registry meta-schema and core registry when it changes the document contract,
and advances each affected extension independently. P10 assigns and verifies the final release
identifiers after the remaining contract work stabilizes.

Replace historical imperative registry replay with one reviewed declarative current state or
deterministically assembled fragments. Preserve each declaration's provenance and prove byte
identity or a defined canonical-form equivalence. This migration is ordinary maintenance if it
does not alter the published contract; any semantic change returns through a proposal.

Add a current-registry writer-to-reader-to-validator integration matrix covering core, valid and
invalid extensions, a non-table derived resource, an external resource, packet-schema format
checking, and the executable Part 08 examples. This is where the TODO items for direct registry
authoring and final registry versions close.

**Review coverage:** D7, I9, identifier findings, and final-value portions of the packet-registry
TODO.

### P11 — Immutable v0.2 publication

Only after P1–P10 close should a publication proposal decide the exact release-manifest schema,
initial membership, member-role assignments, checked status projections, external root-digest
model, and release tooling. It must not redefine the numbered-part statuses owned by Part 00.
Use the deleted prototype snapshot's Git history and the surviving non-writing bundle probe as
design evidence rather than assuming either is a release. Replace or revise that prototype so
verification cannot select membership implicitly, add the resulting publication checks to the
repository verifier, and give publication failures their own tests rather than treating them as
malformed packets.

Positive evidence should cover complete membership, roles, status projections, sizes, digests,
incorporated schemas, registries, and generated views. Negative evidence should cover missing,
escaping, duplicate, stale, structurally invalid, and digest-mismatched members. Freeze the released
bytes or tag and direct subsequent breaking changes to the next version.

**Review coverage:** R5, publication portions of S0/D1, final generated-view checks, and the release
model research preserved in §2.4.

## 5. Complete finding-to-work map

This table prevents a finding from disappearing merely because it was split out of P1.

| Findings or tracked work | Primary disposition |
|---|---|
| S0 authority and abstraction boundaries | P1; concrete placement cleanup continues in P2, P5.1, P8, and P9 |
| S1 contradictory unit identity | P2 |
| S2 manifest prose/schema disagreement | P6 |
| S3 unexpressed resource requiredness | P5.1 then P6 |
| S4 validation/publication order | P9.1 |
| S5 adapter no-write contradiction | P8 |
| S6 analysis lineage/canonicality | P5.1 |
| S7 prefix-resource checksum | P9.2 |
| S8 stale table of contents | P2 or ordinary generated-document maintenance |
| S9 stale normative counts | P2; generate future counts rather than copying them |
| S10 codec floor | P5.2 model, then P9.3 wording and reporting |
| S11 uniqueness and cross-field invariants | P6 |
| S12 profile scope | P9.4 |
| D1 incomplete registry semantics | P3, P4.1, and P4.2 |
| D2 extension registry parity | P4.1 and P4.2 for registry documents; P7 for declared resources and verdicts |
| D3 missing whole-packet profile model | P5.1 logical declarations and P5.2 physical profile |
| D4 hidden arbitration | P8 |
| D5 missing session-recipe schema | P8 |
| D6 underspecified adapter declarations | P8 |
| D7 imperative registry replay | P10 |
| D8 extension non-table assets | P5.1 |
| D9 cross-language proof | Deferred interoperability hardening; reconsider as a P11 release criterion if independent implementation is required for v0.2 |
| R1–R4 and R6–R7 process gaps | P0 is complete; continue using its gates and evidence artifacts |
| R5 mutable publication | P11 |
| R8 historical review labeling | Ordinary documentation maintenance |
| I1 core-only overall verdict | P7 |
| I2 embedded registry validation | P4.1 defines the result, P4.2 invokes it, and P7 composes it |
| I3 obsolete reader unit contract | P2 |
| I4 overbroad canonical marking | P5.1 |
| I5 missing non-table lineage | P5.1 |
| I6 manifest lookup and state validation | P6 |
| I7 incomplete extension physical checks | P7, using P4.1-conforming extension declarations |
| I8 codec capability reporting | P5.2 and P9.3 |
| I9 missing cross-package release proof | P2–P10 incrementally; final matrix in P10 |
| I10 stale public types and docs | P2 |
| I11 constructor validation bypass | P4.2 for registry inputs and P8 for adapter/declaration inputs |
| `layer` and `canonical` TODO | P5.1 |
| packet registry ID/version/digest TODO | shape in P6; final values in P10 |
| direct declarative registry authoring TODO | P10, ordinarily if contract-preserving |
| remaining JSON Schema audits | manifest/resources in P6; sources/adapter in P8 |
| held `registry_version` and stale `$id` values | P10 |

## 6. Final publication gate

P11 should not be promoted merely because all earlier files exist. Before immutable publication,
the accumulated revisions and evidence should establish all of the following:

- every authoritative artifact has one declared role and one identifiable owner for each fact;
- no numbered part, incorporated registry, or incorporated schema disagrees on identity, presence,
  validity, lifecycle, canonicality, lineage, or publication order;
- exact registry data passes both meta-schema validation and named semantic invariants for core,
  extensions, and embedded copies;
- the manifest schema and semantic validator accept and reject the same named conformance cases;
- every registered resource has a computable presence rule and every non-table derived resource can
  express lineage;
- every declared extension contributes to overall packet validity and failed validation prevents
  committed publication;
- recipe resolution contains no undeclared lab/task preference policy;
- identifier and digest fields identify the actual contracts and bytes they govern;
- one packet built from the current recipe and registries passes public reader and validator paths;
- negative evidence covers duplicates, missing required resources, invalid registries, physical
  mismatches, bad lineage, canonicality contradictions, and unsupported capabilities; and
- the release manifest and publication verifier bind the exact reconciled artifacts without adding
  members by convention.

Meeting this gate produces the endpoint the original broad authority proposal was reaching for,
while allowing each prerequisite to be appraised and verified at the abstraction level it owns.

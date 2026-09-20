# Escapewheel v0.2 reconciliation roadmap

| | |
|---|---|
| **Status** | Non-authoritative coordination record |
| **Updated** | 2026-09-19 |
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
[authority draft](../drafts/define-specification-artifacts-and-normative-ownership.md). The project review
was performed at commit `32f9e06884b483818c7156f80ea81f7e3a6ce002`. Subsequent commits through
the review baseline changed documentation, revision workflow, lint findings, and formatting rather
than resolving the packet-contract findings mapped below.

This roadmap tracks dependency and disposition at the work-item level. The separate
[placement-defect inventory](../PLACEMENT-DEFECTS.md) tracks individual statements that appear to
occupy the wrong owner or duplicate another rule; those details do not belong in this sequencing
document.

## 1. How to maintain this roadmap

The status table is a coordination aid; the lifecycle artifact named in its `Artifact` column is
the record of the actual decision. Use these statuses:

- **Not started:** no proposal has reproduced and bounded the problem.
- **Proposal:** an exploratory proposal exists but has not been promoted.
- **Revise before promotion:** appraisal found a material scope, dependency, or evidence defect.
- **Draft:** promotion was authorized and an appraised candidate decision exists.
- **In incorporation:** acceptance was authorized and the atomic incorporation change is open.
- **Complete:** incorporation closure passed and the accepted revision and all affected surfaces
  were committed together.
- **Ordinary maintenance:** the work changes no contract and follows the normal repository workflow.
- **Deferred:** the work is intentionally outside the v0.2 release gate.

Whenever a lifecycle artifact changes stage, update its row, baseline, dependencies, and material
findings here in the same commit. Do not copy generated counts into this document. Before appraising
any proposal, re-establish the baseline and overlap inventory described in the change-process guide;
this ordering is a plan, not evidence that a later proposal remains fresh.

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
conventions, normative-reference policy and bibliography, artifact roles, status conventions,
actors, abstraction boundaries, part ownership, dependency direction, and publication conventions.
It should distinguish:

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

**Original disposition: revise before promotion. Current state: promoted to Draft on 2026-09-17;
first pre-acceptance appraisal requires revision and a process prerequisite.**
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

## 4. Proposal dependency order and status

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
 +----> P3 executable rule language --> P4 registry conformance
                                         |
                                         v
                               P5 resource/profile model
                                         |
                                         v
                               P6 packet manifest contract
                                  |                \
                                  v                 v
                         P7 validity composition   P8 recipe/adapter contract
                                  \                 /
                                   +---- P9 remaining reconciliations
                                                  |
                                                  v
                                  P10 identifiers and source cleanup
                                                  |
                                                  v
                                  P11 immutable v0.2 publication
```

| ID | Work item | Status | Artifact | Depends on |
|---|---|---|---|---|
| P0 | Revision-process foundation | **Complete** | [change-process guide](../CONTRIBUTING.md) and process audit | — |
| P0.1 | Controlled reorganization of specification parts | **Complete** | [R120](../accepted/R120-allow-controlled-specification-reorganization.md) | P0 |
| P0.2 | Remove historical and misplaced maintenance material from authoritative artifacts | **Draft** — appraised ready for acceptance; commit the exact candidate and coordination records before requesting authorization | [current draft](../drafts/remove-historical-and-misplaced-maintenance-material.md) | R120 |
| P1 | Specification authority, abstraction levels, and normative ownership | **Draft** — revise before acceptance; blocked on P0.2 | [current draft](../drafts/define-specification-artifacts-and-normative-ownership.md) | R120, P0.2 |
| P2 | Placement cleanup and unit-identity reconciliation | **Not started** | anticipated proposal; slug to be assigned | P1 |
| P3 | Executable declarative-rule language | **Not started** | anticipated proposal; slug to be assigned | P1 |
| P4 | Registry-document semantics and uniform conformance | **Not started** | anticipated proposal; slug to be assigned | P3 |
| P5 | Resource/profile declarations and resource classification | **Not started** | anticipated proposal; slug to be assigned | P4 |
| P6 | Packet manifest, requiredness, and registry binding | **Not started** | anticipated proposal; slug to be assigned | P5 |
| P7 | Core, extension, and packet validity composition | **Not started** | anticipated proposal; slug to be assigned | P4, P6 |
| P8 | Recipe arbitration and adapter contract | **Not started** | anticipated proposal; slug to be assigned | P5, P6 |
| P9 | Remaining lifecycle, integrity, portability, and scope reconciliations | **Not started** | proposal family; split before promotion | P5–P8 as applicable |
| P10 | Final identifiers, direct registry source, and release integration | **Not started** | proposal plus ordinary maintenance | P2–P9 |
| P11 | Immutable v0.2 specification publication | **Not started** | anticipated proposal; slug to be assigned | P1–P10 |

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

The [active draft](../drafts/remove-historical-and-misplaced-maintenance-material.md) carries the
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
packet catalog's `derived_from`, which names source resources and remains part of the packet
contract.

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

The draft makes Part 00 capable of locating later decisions without publishing the final release
bundle prematurely. It states the relationship between semantic, logical, and physical
abstraction levels and the separate packet content classes, and it incorporates no
machine-readable artifact whose semantics or current contents remain under dispute.
P1, not P0.1, owns candidate authority, artifact roles and membership, release identity, and
publication terminology.

P1 is rebased on R120's incorporation commit. Its pre-acceptance appraisal remains open and P0.2
remains a gating predecessor rather than an accepted dependency. After P0.2 lands, revise P1 with
an exact human-readable old-location-to-new-location crosswalk, a statement-level disposition of
the specification README, stable anchors for reorganized sections, all affected citation and
tooling surfaces, and explicit binding for specification-candidate and publication obligations;
then rerun the appraisal from its freshness gate.

**Exit evidence:** Part 00 and the informational README boundary are unambiguous; every numbered
part has a stated subject and dependency direction; candidate disagreements are classified as
release defects; normative references have one central owner; later proposals can name an
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

**Review coverage:** S0, S1, S8, S9, I3, I10, and the unit-identity portion of I9.

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

### P4 — Registry-document semantics and uniform conformance

Reconcile Part 02 with the meta-schema after P3 supplies a rule language. Specify invariants JSON
Schema cannot establish: stable and unique identifiers, namespace restrictions, compatible primary
and foreign keys, roles, presence, vocabulary, rule references, and extension restrictions. Use one
validation path for the released core registry, extension registries, embedded packet copies,
writer startup, validator loading, and public constructors. Only then consider the meta-schema and
released registry ready for incorporation into an immutable bundle.

**Review coverage:** D1, D2, I2, I7, I11, and the registry-validation part of I9.

### P5 — Resource/profile declarations and classification

Extend the data-driven model beyond tables. Declare resource kinds, required/optional conditions,
physical capabilities, canonicality, lineage, and extension non-table assets. Resolve whether the
packet's `layer` and `canonical` fields are declared facts or derived from resource IDs, namespaces,
extension declarations, and profile rules. The clean starting option is to remove redundant fields
when the same answer is derivable, because there are no external compatibility constraints.

This stage should make derivation and processing-run rules apply uniformly to tables, arrays,
media, and documents, and should distinguish mandatory portability capabilities from optional but
recognized ones.

**Review coverage:** S3, S6, S10 in model form, D3, D8, I4, I5, I8, and the first live TODO.

### P6 — Packet manifest, requiredness, and registry binding

Reconcile Part 04 with `manifest.schema.json` and the resource schema using P5's declarations.
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
missing, unreadable, structurally invalid, semantically invalid, and unsupported registries and
resources. Make writer publication depend on the resulting packet verdict. Preserve useful partial
reader access without reporting an invalid declared extension as a valid packet.

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
3. **Codec capability and portability** — distinguish the mandatory codec floor, recognized
   optional capabilities, validity, and portability reporting (the remaining part of S10/I8).
4. **Profile scope and document organization** — state the present electrophysiology/profile scope
   accurately and consider moving the adapter/build interface out of the physical-storage part in
   the next version (S12 and documentation organization).

Analysis lineage and canonicality belong in P5 rather than this catch-all; adapter write capability
belongs in P8. This placement keeps the earlier review's “remaining reconciliations” from becoming
one omnibus revision.

### P10 — Final identifiers, direct source, and integration

After the contract stabilizes, assign correct semantic, logical, physical-profile, registry,
meta-schema, packet-schema, and rule-language identifiers. Lift the deliberate
`registry_version` hold and ensure identifiers change whenever governed bytes or contracts are
incompatible. Apply the packet registry-binding decision from P6 using the final identifiers and
digests.

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
| S0 authority and abstraction boundaries | P1; concrete placement cleanup continues in P2, P5, P8, and P9 |
| S1 contradictory unit identity | P2 |
| S2 manifest prose/schema disagreement | P6 |
| S3 unexpressed resource requiredness | P5 then P6 |
| S4 validation/publication order | P9.1 |
| S5 adapter no-write contradiction | P8 |
| S6 analysis lineage/canonicality | P5 |
| S7 prefix-resource checksum | P9.2 |
| S8 stale table of contents | P2 or ordinary generated-document maintenance |
| S9 stale normative counts | P2; generate future counts rather than copying them |
| S10 codec floor | P5 model, then P9.3 wording and reporting |
| S11 uniqueness and cross-field invariants | P6 |
| S12 profile scope | P9.4 |
| D1 incomplete registry semantics | P3 and P4 |
| D2 extension registry parity | P4 and P7 |
| D3 missing whole-packet profile model | P5 |
| D4 hidden arbitration | P8 |
| D5 missing session-recipe schema | P8 |
| D6 underspecified adapter declarations | P8 |
| D7 imperative registry replay | P10 |
| D8 extension non-table assets | P5 |
| D9 cross-language proof | Deferred interoperability hardening; reconsider as a P11 release criterion if independent implementation is required for v0.2 |
| R1–R4 and R6–R7 process gaps | P0 is complete; continue using its gates and evidence artifacts |
| R5 mutable publication | P11 |
| R8 historical review labeling | Ordinary documentation maintenance |
| I1 core-only overall verdict | P7 |
| I2 embedded registry validation | P4 and P7 |
| I3 obsolete reader unit contract | P2 |
| I4 overbroad canonical marking | P5 |
| I5 missing non-table lineage | P5 |
| I6 manifest lookup and state validation | P6 |
| I7 incomplete extension physical checks | P4 and P7 |
| I8 codec capability reporting | P5 and P9.3 |
| I9 missing cross-package release proof | P2–P10 incrementally; final matrix in P10 |
| I10 stale public types and docs | P2 |
| I11 constructor validation bypass | P4 and P8 |
| `layer` and `canonical` TODO | P5 |
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

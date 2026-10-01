# Escapewheel v0.2 reconciliation roadmap

| | |
|---|---|
| **Status** | Non-authoritative coordination record |
| **Updated** | 2026-09-30 |
| **Review baseline** | `8d3a9c8598dd0152930ee0aab4de9a19a5496f22` |
| **Objective** | Reconcile the data-driven contract, then publish one internally consistent and immutable v0.2 specification release |

This document preserves the design direction from the project review and the dependency order for
the resulting work. It exists so that narrowing or replacing an individual
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
[project sanity check](../reviews/2026-09-17-project-sanity-check.md), the
[change-process audit](../reviews/2026-09-17-change-process-audit.md), the root
[TODO](../../TODO.md), and the research carried into the current
[R122 authority revision](../accepted/R122-define-specification-artifacts-and-normative-ownership.md). The project review
was performed at commit `32f9e06884b483818c7156f80ea81f7e3a6ce002`. Subsequent commits through
the review baseline changed documentation, revision workflow, lint findings, and formatting rather
than resolving the packet-contract findings mapped below.

This roadmap tracks dependency and disposition at the work-item level. The separate
[placement-defect inventory](../reviews/2026-09-29-placement-defects.md) tracks individual statements that appear to
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

## 3. Work-item dependency order and records

The ordering below follows normative dependencies. It does not require unrelated proposals in the
same family to wait when their owners and evidence are independent. A completed item's scope and
rationale are in the accepted record the table names; only open items are described after it.

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
        P10.1 registry source and integration matrix
                      |
                      v
        P10.2 release-candidate field test ---- P10.2a summaries agree with owners
                      |                              |   (beside the field test)
                      |                              v
                      |                         P10.2b placement cleanup
                      |                              (beside the field test)
                      v
        P10.3 final identifiers (after P10.2a and P10.2b)
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
| P6 | Packet manifest, requiredness, and registry binding | P5.1, P5.2 | [R130](../accepted/R130-a-packet-binds-the-exact-registries-that-declare-its-resources.md) |
| P7 | Core, extension, and packet validity composition | P4.2, P6 | [R131](../accepted/R131-a-validator-checks-every-unit-value-against-ucum.md); [R132](../accepted/R132-a-packet-passes-only-when-its-manifest-core-and-every-bound-extension-pass.md) |
| P8 | Recipe arbitration and adapter contract | P5.1, P5.2, P6 | [R133](../accepted/R133-a-build-decides-ownership-only-from-the-recipe-and-adapter-declarations.md); [R134](../accepted/R134-an-adapter-declares-its-whole-contract-and-delivers-only-where-a-build-points-it.md) |
| P9 | Remaining lifecycle, integrity, portability, and scope reconciliations | P5.1–P8 as applicable | [R135](../accepted/R135-a-build-owns-its-staging-area-and-validates-everything-it-stages-before-publishing.md); [R136](../accepted/R136-every-packet-owned-resource-records-a-named-whole-object-digest.md); [R137](../accepted/R137-the-zarr-floor-admits-blosc-zstd-and-sharding-and-a-feature-outside-a-floor-is-a-resource-finding.md); [R138](../accepted/R138-a-recipe-names-each-extension-registry-once.md); [R139](../accepted/R139-a-float-column-declares-whether-it-admits-non-finite-values.md); [R140](../accepted/R140-a-nomenclature-that-governs-an-open-core-column-has-a-reference-entry.md); [R141](../accepted/R141-the-core-vocabulary-targets-extracellular-electrophysiology.md); [R142](../accepted/R142-a-build-supplies-an-adapter-a-persistent-source-cache.md); [R143](../accepted/R143-a-packet-owned-opaque-resource-crosses-as-its-bytes-in-a-directory-named-by-its-resource-id.md); [R144](../accepted/R144-the-adapter-interface-is-its-own-part-at-the-physical-level.md) |
| P10.1 | Direct registry source and release integration matrix | P2, P2.1, and P3–P9 | Ordinary maintenance unless the contract changes |
| P10.2 | Release-candidate field test | P10.1 | [R147](../accepted/R147-every-array-axis-declares-what-each-position-is.md); revisions for what the field finds; the user ends the test |
| P10.2a | Summaries in Parts 00, 01 and 06 agree with the parts owning their rules | P10.1; runs beside P10.2 | [R145](../accepted/R145-each-rule-is-stated-by-its-owner-and-a-canonical-resource-depends-only-on-canonical-resources.md) |
| P10.2b | Placement cleanup from the re-appraised placement-defect inventory | P10.2a; runs beside P10.2 | [R146](../accepted/R146-each-statement-sits-in-the-part-that-owns-its-subject.md); structural revision, verbatim duplicates as maintenance |
| P10.3 | Final identifiers and registry binding | P10.2, P10.2a, P10.2b | Proposal |
| P11 | Immutable v0.2 specification publication | P1–P10 | Proposal to be scoped |

### P10 — Registry source, field test, and final identifiers

P10 runs in three steps, because the contract is tested in the field as a release candidate before
its identifiers are frozen. Through the field test every identifier stays a development identifier
(Part 02 §9.2): a contract change advances the version it governs, as it has since R126,
and no identifier is reused for an incompatible contract. A packet built from the candidate
identifies each registry it binds by that version and by the SHA-256 in its manifest (Part 04).

#### P10.2 — Release-candidate field test

Build and use packets from the candidate in the field. What the test finds returns through the
ordinary lifecycle: a defect in a numbered part, registry, or schema is a revision, and an
implementation defect is maintenance. The user decides when the test ends; P10.3 does not start
before then.

#### P10.3 — Final identifiers and registry binding

Assign correct semantic, logical, physical-profile, registry, meta-schema, packet-schema, and
rule-language identifiers, replacing the development identifiers; the semantic, logical,
physical-profile, and rule-language identifiers still name v0.1 in a v0.2 specification. Ensure
identifiers change whenever governed bytes or contracts are incompatible. Apply the packet registry-binding decision from P6
using the final identifiers and digests. The TODO item for final registry versions closes here.

Until then a contract change advances the registry meta-schema and core registry, and each
affected extension independently, as P4.1 established. P10.3 assigns and verifies the final release
identifiers after the field test's revisions are incorporated.

**Review coverage:** D7 and I9 in P10.1; identifier findings and final-value portions of the
packet-registry TODO in P10.3.

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

## 4. Complete finding-to-work map

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
| D7 imperative registry replay | P10.1 |
| D8 extension non-table assets | P5.1 |
| D9 cross-language proof | Deferred interoperability hardening; reconsider as a P11 release criterion if independent implementation is required for v0.2. The adapter source-cache location moved into v0.2 as P9.8; a cache storage format shared across implementations, likely content-addressed, stays deferred here, with the `cache-v` subdirectory names reserved for it |
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
| I9 missing cross-package release proof | P2–P10 incrementally; final matrix in P10.1 |
| I10 stale public types and docs | P2 |
| I11 constructor validation bypass | P4.2 for registry inputs and P8 for adapter/declaration inputs |
| `layer` and `canonical` TODO | P5.1 |
| packet registry ID/version/digest TODO | shape in P6; final values in P10.3 |
| direct declarative registry authoring TODO | P10.1, ordinarily if contract-preserving |
| remaining JSON Schema audits | manifest/resources in P6; sources/adapter in P8 |
| development `registry_version` and `$id` values | P10.3, after the P10.2 field test |

## 5. Final publication gate

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
- the release candidate has been field tested, and each finding is incorporated or deferred by the
  user's decision;
- identifier and digest fields identify the actual contracts and bytes they govern;
- one packet built from the current recipe and registries passes public reader and validator paths;
- negative evidence covers duplicates, missing required resources, invalid registries, physical
  mismatches, bad lineage, canonicality contradictions, and unsupported capabilities; and
- the release manifest and publication verifier bind the exact reconciled artifacts without adding
  members by convention.

Meeting this gate produces the endpoint the original broad authority proposal was reaching for,
while allowing each prerequisite to be appraised and verified at the abstraction level it owns.

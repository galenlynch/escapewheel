# The Specification Assigns Authority by Concern

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `41da62e3fd4924e5526f8f812492e90607d14d97` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §1, §§2–3, §§4–5, §9, and new §10 (scope, authority, conformance, classifications, content-class terminology, part ownership and status, normative references); Part 01 §1 (semantic-standard identity); Part 02 §1 (logical-standard identity); Part 03 §1 (profile identity and external-reference policy); Part 04 §§1 and 3 (catalog role and recorded identifiers); Part 05 §10 (packet and writer conformance); specification README status and §§1–7 (informational entry point) |
| **Depends on** | R93 §3.2 and §3.6 (part subjects, profile boundary, and current status precedence); R111 §§3.1–3.3 (actors and requirement subjects); R112 §3.1 (current requirements live in parts); R120 §§3.1 and 3.3–3.7 (process authority, structural change, anchors, citations, and current-owner traceability); R121 §§3.1–3.2 (history-free registry shape and current registry identity) |
| **Profile** | all |
| **Decision clauses** | §3.1, §3.2, §3.3, §3.4, §3.5, §3.6, §3.7, §3.8, §3.9 |

Section 3 is normative. Sections 1–2 and 4–8 are informative.

Normative keywords follow BCP 14.

## 1. Scope

The generated v0.2 specification and the machine-readable declarations it expressly incorporates
are the current authority, but they do not give an independent implementer one coherent framework
for locating that authority. The specification README acts as an unnumbered normative preamble;
Part 00 duplicates parts of it; exact declarations and operational rules appear at several
abstraction levels; and the word *layer* names two orthogonal classifications.

This revision assigns authority by concern, makes Part 00 the specification framework, separates
abstraction level from packet content class, states the dependency direction among the data
contract, packet catalog, ingestion, and conformance concerns, assigns every numbered part a
subject and status, and makes the specification README informational. It also distinguishes an
authoritative working candidate from an immutable release.

This is a structural reorganization under R120. An ordinary append-only amendment would place the
authority framework after the rules it classifies, leave the README acting as a preamble, and leave
duplicate owners in place. Those results would impair the framework's dependency order and the
reader's ability to locate a rule, so the controlled structural form is required.

This revision changes the organization and interpretation of the specification, not the packet
contract. It does not select among the known disagreements about unit identity, resource
classification, requiredness, validation composition, registry conformance, executable rules,
adapter behavior, integrity, or publication artifacts.

## 2. Background

This section is informative.

### 2.1 The current framework has overlapping owners

The specification README contains the only top-level conformance, normative-language, and
normative-reference clauses. `combine.py` prepends it because it says the README carries those
clauses and the version identifiers. A file normally used for navigation and publication guidance
therefore acts as normative prose outside the numbered parts.

The README and [Part 00 §9](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-numbered-part-ownership)
both classify parts. The README says that the specification has eleven parts but lists only Parts
00–09. Part 00 includes Part 10 and the section-level exceptions for mixed Part 06, but its final
sentence says that a local part header wins if the two disagree. Three maintained representations
can therefore drift while a precedence rule still produces an answer.

[Part 00 §1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-architecture-scope)
says that the part defines no schema or file format. Part 00 nevertheless fixes a unit key, reports
exact registry counts, names columns and resources, prescribes reader behavior, gives a measured
join cost, and describes the first implementation. One copied measurement says that 33 of 35 core
and analysis tables are session-scoped and that eight reach `core.sessions` without carrying
`session_id`; the baseline registry check reports 41 of 43 session-scoped tables and none lacking
the column. The count drift is evidence that architecture is not the owner of the declaration or
its current measurements. Those placement defects remain assigned to later work; this revision
defines the ownership framework without silently repairing their packet meaning.

[Part 02 §1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-core-logical-schema-scope)
already demonstrates a narrower authority model. It makes `registry/logical_schemas.json`
normative for exact current declarations and `registry/tables.md` an informative generated
listing. Prose governs the declaration model and semantics, the incorporated registry carries
exact assignments, and the table listing is a projection. File format alone determines none of
those roles.

### 2.2 Two classifications currently share one name

Part 00 §§2.1–2.3 describe semantic, logical, and physical levels. Part 00 §3 uses *layer* for the
relationship of core, extension, analysis, and projection content to the packet. A core resource
has semantic meaning, a logical declaration, and a physical representation; an extension resource
can have the same three aspects. Neither classification refines the other.

The current wording obscures two further classifications. A namespace assigns ownership through
dotted identifiers, while a resource kind describes a logical resource's form and the catalog
encodes that kind. Neither answers whether content is core, extension, derived analysis, or a
compatibility projection. Part 04 currently defines some kind values through Parquet and Zarr,
which is a separate placement defect assigned to the resource-contract work rather than a reason
for Part 00 to own the kind vocabulary.

### 2.3 The full architecture has a sound center and unclear edges

The project's central data flow is coherent. Part 01 supplies substrate-independent meaning; Part
02 and its incorporated registry describe logical tables, columns, identities, references, and
rules; Part 03 maps logical resources to commodity bytes; Part 04 binds concrete resources in a
packet; and Part 05 constructs and validates packet instances. Extension registries use the same
declaration model, while adapters are source-specific producers feeding a writer rather than
alternate definitions of the packet contract.

That design is genuinely data driven where the registry owns exact logical assignments and the
validator derives structural checks from them. It is not yet a complete declarative architecture:
the registry does not declare all resource requiredness and catalog conditions, Tier 2 SQL lacks a
specified execution language, adapter and lifecycle rules remain coupled to the portable profile,
and the registry's direct authoring source is still imperative Python. Those are tracked by later
work. They do not prevent this revision from stating which concern owns each answer.

R121 removed the provisional release snapshot and moved its useful digest experiment to
non-writing prototype tooling. The absence of a release artifact does not make the generated v0.2
candidate optional. It makes current authority and publication state visibly independent:
development needs one inspectable contract before a later publication decision freezes exact
members and bytes.

### 2.4 Existing decisions, baseline, and impact

R93 §3.6 makes Part 00 list each part but gives a conflicting local-header precedence. R111
§§3.1–3.2 defines the actors Part 00 already carries, and R112 §3.1 places current requirements in
their owning parts. R120 assigns repository-change procedure and citation presentation to
`revisions/CONTRIBUTING.md`; this revision therefore does not relocate process rules into Part 00.
R121 removes revision history and maintenance procedure from current contract artifacts and gives
the registry its current history-free identity. This revision supersedes only R93 §3.6's
local-header precedence sentence.

The baseline is `41da62e3fd4924e5526f8f812492e90607d14d97`, the metadata-only anchor bootstrap
committed immediately after R121's incorporation. It is the only open lifecycle artifact. The
impact query over the 22 structurally affected existing sections reports 145 citation occurrences
in the appraisal tree: 42 in immutable accepted records, 59 in this draft's analysis and
crosswalk, and 44 other live occurrences. The selectors are Part 00 §1, §2 and §§2.1–2.8, §3,
§4, §4.1, §5, §5.1, and §9; Part 01 §1; Part 02 §1; Part 03 §1; Part 04 §§1 and 3; and Part 05
§10. Incorporation leaves historical records unchanged and reads and repoints every live
occurrence whose displayed section number or target changes.

Reading the 44 external live occurrences found two existing semantic citation defects. Part 03 §4
cites current Part 00 §3 for the permissible forms of a packet root, but that rule is current
`ew-packet` in §2.4 and moves with that anchor. Ten validator, writer, and test citations cite Part
04 §3 for an analysis resource's `processing_run_id`, but that field and obligation are in Part 04
§4.1. Incorporation corrects those targets while preserving behavior; they are not deferred merely
because they predate this draft.

There are no published remote, external consumers, or released packets. No packet bytes or
implementation behavior change here, so packet migration is not required. The organizational
change is nevertheless material: a conflict becomes a candidate defect rather than a case where a
file-format or local-header precedence rule chooses a winner.

## 3. Decision

### 3.1 The current specification is an authoritative candidate

The current generated v0.2 numbered parts and every artifact that a numbered part expressly
incorporates **MUST** constitute the authoritative working specification. An incorporated artifact
participates only for the subject and extent the incorporating part states. A file outside that
set **MUST NOT** override it.

The working specification **MUST** be called a **specification candidate** until a publication
decision identifies and freezes an exact release. *Authoritative* describes what governs current
development and conformance; *candidate* describes publication state. Candidate status **MUST NOT**
make the working specification optional.

A **specification release** **MUST** be an immutable publication whose publication record identifies
its exact members and versions. This revision defines the distinction but does not select release
membership or a publication-record format. The combined specification **MUST** be a reproducible
convenience rendering of its inputs and **MUST NOT** become a separately edited owner.

### 3.2 Authority is assigned by concern

Numbered prose **MUST** own terms, meanings, processing semantics, actor obligations,
conformance, and relationships that a structural declaration cannot express faithfully.

A machine-readable artifact **MUST** acquire normative authority only when a numbered part
expressly incorporates it. It **MUST** own only the exact structures or assignments for which that
part incorporates it. The incorporating prose **MUST** continue to own the vocabulary's meaning,
the semantics of declared fields, and every applicable processing or conformance rule not fully
expressed by the artifact.

Implementations and evidence **MUST NOT** acquire an independent normative subject by implementing
or testing a rule.

Normativity, representation, and production **MUST** remain independent properties. Prose is not
normative merely because it is prose; JSON is not authoritative merely because it is structured;
generated output is not informative merely because it is generated. The declared artifact role
and subject ownership determine authority.

### 3.3 Each fact has one owner and every other representation agrees

Each normative fact **MUST** have one owner. Another artifact that presents the same fact **MUST**
be one of:

1. a mechanically checked projection;
2. an explicitly informative explanation that links to its owner; or
3. an explicit consistency condition between different owners' subjects.

A disagreement between owners, an unfaithful projection, or an incorporated artifact that
violates its governing prose **MUST** make the candidate internally inconsistent. No general
prose-wins, data-wins, generated-wins, or local-file-wins rule **MAY** turn that disagreement into
conformance. The inconsistent candidate remains the authoritative material to inspect and repair;
a specification release **MUST NOT** contain an unresolved ownership conflict.

### 3.4 Part 00 owns the specification framework

Part 00 **MUST** own:

- specification-candidate identity and candidate/release terminology;
- conformance targets and normative-language conventions;
- the normative-reference policy and complete normative bibliography;
- actors and the terms that resolve to them;
- normative, informative, and mixed status;
- artifact roles and the authority-by-concern rule;
- abstraction levels and their dependency direction;
- packet content classes as a separate classification;
- the subject owned by every numbered part; and
- specification-candidate and release states and their conformance-relevant distinction.

Part 00 **MUST NOT** become the owner of exact keys, columns, registry counts, profile encodings,
performance measurements, implementation plans, or detailed lifecycle algorithms merely because
it summarizes the architecture. Where those statements remain during development, Part 00
**MUST** link to the actual owner or identify the summary as informative once the owner is settled.

### 3.5 Abstraction levels and packet content classes are separate axes

The specification **MUST** call semantic, logical, and physical classifications **abstraction
levels**:

- the semantic level defines what concepts mean, independently of representation and storage;
- the logical level defines concepts as computable resources and relationships, independently of
  a storage profile; and
- the physical level maps logical resources to stored bytes under a declared profile.

A lower abstraction level **MUST NOT** redefine a rule owned by the level above it. A physical
profile **MAY** map a logical resource to a storage technology and **MUST NOT** change that
resource's logical identity or semantic meaning. A workflow **MAY** describe how an actor satisfies
an owned invariant and **MUST NOT** restate a second version of that invariant.

The specification **MUST** call the architectural relationship of core, extension, derived
analysis, and compatibility-projection content to a packet its **packet content class**. Content
class **MUST** remain independent of abstraction level, namespace, and resource kind. Resources of
different kinds may share a content class, and resources of one kind may occupy different content
classes.

**Namespace** **MUST** remain the dotted-identifier ownership mechanism. **Resource kind** **MUST**
classify a logical resource's form independently of its content class and physical encoding. Part
02 **MUST** own logical resource-kind meaning, while Part 04 **MUST** own the catalog field and
vocabulary that record a kind. Part 00 **MUST NOT** duplicate either detailed vocabulary. This
clause does not require a packet to serialize its content class, change the current catalog
`layer` field, or settle the known technology-dependent wording in Part 04.

### 3.6 Each numbered part owns a stated subject and dependency direction

Part 00 **MUST** assign the following subjects to the numbered parts:

| part | owned subject |
|---|---|
| Part 00 | specification framework, authority, abstractions, part ownership and publication conventions |
| Part 01 | substrate-independent meanings of scientific and provenance concepts |
| Part 02 | logical resources, declarations, identities, references, and registry semantics |
| Part 03 | the portable physical mapping of logical resources to stored bytes |
| Part 04 | packet catalog structure, resource entries, and dataset-to-resource bindings |
| Part 05 | validation, import, writer lifecycle, reporting, and publication of a packet |
| Part 06 | analysis policy, examples, and explanation, subject to its mixed status in §3.7 |
| Part 07 | informative reference-implementation design and examples |
| Part 08 | informative executable packet example |
| Part 09 | extension boundaries, namespace ownership, extension declarations, and extension independence |
| Part 10 | informative performance measurements and rationale |

A part **MUST NOT** state a second version of a rule owned by another part. It **MAY** cite the
owner, or summarize the rule only when the summary is explicitly informative. An informative
section **MUST NOT** be the sole statement of an obligation.

The numbered parts **MUST** observe this dependency direction:

1. Part 01 defines meaning without selecting a resource shape or storage technology.
2. Part 02 and an expressly incorporated registry represent Part 01 concepts as logical resources,
   identities, relationships, and constraints without selecting a storage technology.
3. Part 03 maps logical resources to bytes under a profile without changing their logical identity
   or semantic meaning.
4. Part 04 binds concrete packet resources to the semantic, logical, registry, and profile
   identifiers that govern them without redefining those contracts.
5. Part 05 specifies how writers, readers, and validators construct and judge instances under the
   upstream contracts rather than becoming a second owner of those contracts.
6. Part 09 permits namespaced extension declarations under the same applicable semantic, logical,
   physical, catalog, and conformance boundaries without altering core.

A writer **MUST** interpret adapter declarations and output under the owning numbered parts and
incorporated declarations. An adapter's participation in ingestion **MUST NOT** let it redefine the
packet contract. Authority follows express incorporation and subject ownership, not the direction
of a software call or generation step.

### 3.7 Part 00 owns numbered-part status

Part 00 **MUST** assign the following normative status:

| part | status |
|---|---|
| Part 00 | normative |
| Part 01 | normative |
| Part 02 | normative |
| Part 03 | normative |
| Part 04 | normative |
| Part 05 | normative |
| Part 06 | informative except §§2 and 5, which are normative |
| Part 07 | informative |
| Part 08 | informative |
| Part 09 | normative |
| Part 10 | informative |

The status line at the head of each part **MUST** be a checked projection of Part 00. A
disagreement **MUST** make the candidate inconsistent; the local line **MUST NOT** take precedence.
A local status remains a projection and never a precedence source.

A future release manifest **MAY** record numbered-part status, but that value **MUST** be a checked
projection of Part 00. The manifest **MUST NOT** become a second owner of numbered-part status.

### 3.8 The specification README is informational

The specification README **MUST** be an informational entry point. It **MAY** provide navigation,
candidate status, an architectural summary, build guidance, informative references, generated
status summaries, and links to owning artifacts. It **MUST NOT** be the sole statement of a
requirement or supply a normative preamble through its position in the combined rendering.

The subjects now stated in the README **MUST** have these normative owners:

| current README subject | normative owner |
|---|---|
| purpose, applicability, conformance targets, actor summary, normative-language convention, document organization, specification-candidate identity, and candidate/release distinction | Part 00 |
| semantic-standard identifier and the meaning of that identifier | Part 01 |
| logical-standard identifier, registry document structure, embedding, compatibility, and `registry_version` semantics | Part 02 |
| portable-profile identifier and the profile-dependent meaning of that identifier | Part 03 |
| packet catalog fields and the obligation to record applicable identifiers | Part 04 |
| packet and writer conformance composition and validation consequences | Part 05, with extension-verdict composition in Part 09 |
| extension independence, namespace ownership, and extension-related reader or validator behavior | Part 09 |

A paragraph combining several subjects **MUST** be split among their owners. An existing detailed
clause **MUST** be cited rather than duplicated. A concise README summary **MAY** remain only when
it is identified as informative and links to the owner.

The combined-document generator **MAY** continue to place the README first for orientation. Its
ordering **MUST NOT** supply normative force, and the numbered part set **MUST** remain intelligible
without repository-specific developer documentation.

### 3.9 Part 00 owns the normative bibliography

Part 00 **MUST** carry the complete normative bibliography and the rule for how a normative
reference applies. The initial central bibliography **MUST** identify every external authority on
which the current candidate directly relies:

- BCP 14, comprising RFC 2119 and RFC 8174, for normative keywords;
- RFC 8259 for JSON;
- RFC 3986 for URI syntax;
- JSON Schema Draft 2020-12 Core and Validation for incorporated schemas;
- the Apache Parquet format, including its logical types;
- the Apache Arrow columnar, IPC, and Flight specifications;
- the Zarr v3 specification set used by the portable profile: core, data types, the regular chunk
  grid, the default chunk-key encoding, and the Bytes, Gzip, Blosc, CRC32C, transpose, and
  sharding-indexed codec specifications; together with the Zarr v2 storage specification;
- RFC 8878 for Zstandard framing; and
- NIST FIPS 180-4 for SHA-256.

An informative technology mention does not make its specification normative. A normative
reference's own dependencies apply through that reference and need not be copied into the central
bibliography unless this specification relies on them directly. The candidate bibliography
**MUST** distinguish an exact edition from an unversioned external specification. A specification
release **MUST** identify the exact external editions on which its conformance requirements depend.

A subject-owning part whose requirements depend on an external specification **MUST** cite the
corresponding Part 00 bibliography entry. It **MUST NOT** maintain a second normative bibliography.
Centralizing the reference **MUST NOT** move the subject requirement into Part 00.

Where required behavior has no sufficient language-neutral authority, Part 00 **MUST NOT** promote
an implementation or library's observed behavior into a normative reference. The missing authority
**MUST** remain a candidate defect and **MUST** prevent release until the subject-owning part defines
the behavior or cites an adequate specification. This applies initially to the unspecified Tier 2
rule language and to any required Zarr codec configuration or binary behavior not determined by the
listed Zarr and Zstandard specifications. This revision identifies those gaps without deciding the
rule language or codec floor.

The informational README **MAY** retain informative references and links to Part 00's normative
bibliography. It **MUST NOT** contain a normative-reference section of its own.

## 4. What this does not change

- No packet field, resource, table, column, key, reference, rule, vocabulary, physical encoding,
  validation result, reader API, writer behavior, or adapter contract changes. Existing packets do
  not require migration or regeneration.
- No new registry, meta-schema, JSON Schema, rule language, or release manifest is incorporated.
  Part 02's existing incorporation of the core logical registry remains in force.
- The normative status assigned to each part and Part 06 section remains unchanged; only ownership
  and checking of that status change.
- The draft does not decide unit identity, resource requiredness, serialized content
  classification, `layer`, `canonical`, lineage, packet registry binding, validity composition,
  recipe arbitration, adapter capabilities, integrity, codecs, or final version identifiers.
- The draft does not define final release-manifest membership, roles, hashes, identifiers, or
  publication tooling.

## 5. Consequence

The change is specification-organizational and incompatible only with tools or readers that treat
the README, a local status header, a revision, or an implementation as an independent precedence
source. It preserves packet shape and interpretation. Incorporation requires document relocation,
generation, citation review, and framework checks, not packet migration.

### 5.1 Resulting Part 00 outline

The structural incorporation produces this exact outline. A parenthetical anchor already exists
at the baseline; a new heading receives its anchor during incorporation.

| section | heading | canonical anchor |
|---|---|---|
| 1 | Scope | `ew-architecture-scope` |
| 2 | Specification authority and conformance | `ew-specification-authority` (new) |
| 2.1 | Specification candidate and release | `ew-specification-candidate` (new) |
| 2.2 | Authority by concern | `ew-authority-by-concern` (new) |
| 2.3 | Internal consistency | `ew-candidate-consistency` (new) |
| 2.4 | Conformance targets and actors | `ew-specification-actors` |
| 2.5 | Normative language | `ew-normative-language` (new) |
| 3 | Architecture classifications | `ew-architecture-classifications` (new) |
| 3.1 | Abstraction levels | `ew-abstraction-levels` (new) |
| 3.1.1–3.1.3 | Semantic standard; Logical standard; Physical profile | `ew-semantic-standard`; `ew-logical-standard`; `ew-physical-profile` |
| 3.2 | Packet content classes | `ew-packet-content-classes` |
| 3.3–3.6 | Packet; Packet catalog; Iceberg catalog; Resource identity | `ew-packet`; `ew-packet-catalog`; `ew-iceberg-catalog`; `ew-resource-identity` |
| 4 | Core content class | `ew-core-content-class` |
| 4.1–4.3 | Requirements; Spike representation; Unit identity | existing subsection numbering; §4.1 retains `ew-core-content-requirements` |
| 5 | Analysis content class | `ew-analysis-content-class` |
| 5.1–5.2 | Requirements; Materialization is justified by layout, not by arithmetic | existing subsection numbering; §5.1 retains `ew-analysis-content-requirements` |
| 6–8 | Deferred NWB projection; Storage stance; Implementation thesis | unchanged headings and numbering |
| 9 | Part subjects and normative status | `ew-numbered-part-ownership` |
| 10 | Normative references | `ew-normative-references` (new) |

The former `ew-architecture-terms` anchor has no honest single successor because current §2 splits
between authority, conformance, abstractions, packet terms, and actors. It is retired without an
alias. Every other moved subject retains its canonical anchor. No existing heading lacks an anchor
needed by this crosswalk after bootstrap commit `41da62e3fd4924e5526f8f812492e90607d14d97`.

### 5.2 Numbered-section crosswalk

| old location | disposition | new location | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 00 §1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-architecture-scope) | revise in place | Part 00 §1, same anchor | Scope names the specification framework and defers exact declarations and encodings to their owners; no packet rule changes. | §§3.1, 3.4 |
| [Part 00 §2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-architecture-terms) | split; retire source anchor | Part 00 §§2–3 | Separates authority and conformance from architectural classifications instead of retaining one mixed term list. | §§3.1–3.6 |
| [Part 00 §2.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-semantic-standard) | move with anchor | planned Part 00 subsection 3.1.1 | Names semantic as an abstraction level and preserves its meaning. | §3.5 |
| [Part 00 §2.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-logical-standard) | move with anchor | planned Part 00 subsection 3.1.2 | Names logical as an abstraction level and preserves its meaning. | §3.5 |
| [Part 00 §2.3](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-physical-profile) | move with anchor | planned Part 00 subsection 3.1.3 | Names physical as an abstraction level and preserves its meaning. | §3.5 |
| [Part 00 §2.4](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet) | move with anchor | planned Part 00 subsection 3.3 | Renumbers the packet term without changing its current rules; P2 retains the lower-level placement defects within it. | §3.5 |
| [Part 00 §2.5](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet-catalog) | move with anchor | planned Part 00 subsection 3.4 | Renumbers the packet-catalog term without changing catalog meaning. | §3.5 |
| [Part 00 §2.6](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-iceberg-catalog) | move with anchor | planned Part 00 subsection 3.5 | Renumbers the informative Iceberg-catalog distinction without making Iceberg normative. | §3.5 |
| [Part 00 §2.7](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-resource-identity) | move with anchor | planned Part 00 subsection 3.6 | Renumbers the resource-identity principle without changing it. | §3.5 |
| [Part 00 §2.8](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-specification-actors) | move and merge | Part 00 §2.4 | Keeps the four actors and aliases, adds the README's conformance-target summary, and preserves actor obligations. | §§3.4, 3.8 |
| [Part 00 §3](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet-content-classes) | rename and clarify | planned Part 00 subsection 3.2 | Replaces overloaded *layer* with *packet content class* while leaving the catalog `layer` field and its meaning for later appraisal. | §3.5 |
| [Part 00 §4](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-core-content-class) | rename heading | Part 00 §4 | Calls core a content class; exact core declarations remain unchanged. | §3.5 |
| [Part 00 §4.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-core-content-requirements) | revise terminology | Part 00 §4.1 | Uses *content class* while leaving its current requirements and the unit-identity defect unchanged. | §3.5 |
| [Part 00 §5](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-analysis-content-class) | rename heading | Part 00 §5 | Calls analysis a content class; its downstream contract remains unchanged. | §3.5 |
| [Part 00 §5.1](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-analysis-content-requirements) | revise terminology | Part 00 §5.1 | Uses *content class* while leaving lineage, canonicality, and materialization defects assigned downstream. | §3.5 |
| [Part 00 §9](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-numbered-part-ownership) | replace in place | Part 00 §9, same anchor | Makes subjects and statuses authoritative here and removes local-header precedence. | §§3.6–3.7 |
| Part 00, no current section | add | Part 00 §§2.1–2.3, 2.5, 3.1, and 10 | Adds candidate/release, authority, consistency, normative-language, abstraction-axis, and bibliography owners before dependent detail. | §§3.1–3.5, 3.9 |
| [Part 01 §1](../../escapewheel_poc_docs_v0.2/01_semantic_standard.md#ew-semantic-standard-scope) | revise in place | Part 01 §1, same anchor | Makes `escapewheel-semantic-v0.1` the semantic standard's own identifier without changing it. | §§3.2, 3.8 |
| [Part 02 §1](../../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md#ew-core-logical-schema-scope) | revise in place | Part 02 §1, same anchor | Makes `escapewheel-logical-v0.1` the logical standard's own identifier; existing registry incorporation remains unchanged. | §§3.2, 3.8 |
| [Part 03 §1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-scope) | revise in place | Part 03 §1, same anchor | Retains `escapewheel-portable-v0.1` as the profile's own identifier and points technology terms to Part 00's bibliography. | §§3.2, 3.8–3.9 |
| [Part 04 §1](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-catalog-scope) | revise in place | Part 04 §1, same anchor | States that the catalog binds concrete resources to the contracts that govern them. | §§3.2, 3.6 |
| [Part 04 §3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-identifiers) | revise in place | Part 04 §3, same anchor | States that the catalog records identifiers owned by Parts 01–03 and the incorporated registry; fields and packet shape do not change. | §§3.2, 3.8 |
| [Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes) | revise in place | Part 05 §10, same anchor | Receives the README's packet-conformance composition while retaining separate packet and writer conformance; extension verdict composition remains in Part 09. | §§3.6, 3.8 |

### 5.3 Specification README statement crosswalk

The rows below account for every paragraph, list, and table in the current README. A retained
summary is explicitly informative and links to its owner.

| current README statement | disposition and destination | semantic effect | Decision clause |
|---|---|---|---|
| Status: v0.2 proof-of-principle contract and independent document/packet identifiers | retain as informative summary; link to Part 00 §§2.1 and 9 and Parts 01–04 identifier owners | Removes preamble authority; no identifier changes. | §§3.1, 3.8 |
| §1.1 purpose paragraph and five-item composition list | retain a concise informative summary; normative scope and part subjects move to Part 00 §§1 and 9 | One owner for scope and organization. | §§3.4, 3.6, 3.8 |
| §1.2 out-of-scope paragraphs | move to Part 00 §1; retain only a linked summary if useful | Scope limits become numbered prose. | §§3.4, 3.8 |
| §1.3 commodity-substrate design goal and placeholder-name note | retain as informative context | No normative relocation; the profile owns storage requirements. | §3.8 |
| §2.1 actor table and its introductory sentence | merge into Part 00 §2.4; README links to it | Preserves the four actors while removing a duplicate definition. | §§3.4, 3.8 |
| §2.2 first paragraph defining a conforming packet | move to Part 05 §10, with extension-verdict composition linked to Part 09 §5.4 | Preserves current packet-conformance composition without deciding P7's broader validity work. | §§3.6, 3.8 |
| §2.2 optional-resource permission and unknown-resource validator prohibition | split: requiredness links to Parts 02 and 09 §4; validator behavior moves to Part 05 §10 | Preserves the open-world rule without making README its owner. | §§3.2, 3.8 |
| §2.3 reader paragraph | replace with informative links to Part 04 §2 and Part 03 §§6.1–6.2 | Removes duplicated reader obligations. | §§3.3, 3.8 |
| §2.4 extension definition and behavior paragraph | replace with informative links to Part 09 §§4, 5.1, 5.3, 6.1, and 8 | Removes duplicated extension obligations. | §§3.3, 3.8 |
| §3 normative-keyword paragraph | move to Part 00 §2.5 and update the reference from RFC 2119 alone to BCP 14 | Makes the already-used uppercase convention explicit through its complete authority. | §§3.4, 3.9 |
| §3 citation-syntax paragraph | remove from the specification; the contribution guide already owns editorial citation form | Removes repository editing guidance without changing packet meaning. | — |
| §4 part-count sentence and status table | replace with a checked informative projection of Part 00 §9, including Part 10 and Part 06's mixed status | Eliminates the stale ten-row table and precedence ambiguity. | §§3.7–3.8 |
| §4 combined-rendering sentence | retain as informative link; Part 00 §2.1 owns its projection status | Clarifies that concatenation creates no new owner. | §§3.1, 3.8 |
| §5 introductory sentence | split among Part 00 §2.1 and the identifier-owning Parts 01–04 | Separates candidate version from packet-recorded identifiers. | §§3.1–3.2, 3.8 |
| §5.1 identifier table | retain only as a checked informative summary; exact values live in Part 01 §1, Part 02 §§1 and 9.2, and Part 03 §1, while Part 04 §3 owns recording | Adds the previously missing semantic-identifier owner; values do not change. | §§3.2, 3.8 |
| §5.1 compatibility and regeneration paragraphs and §5.2 | replace with an informative link to Part 02 §9.2 and the applicable profile/catalog rules | Removes a duplicate compatibility statement. | §§3.3, 3.8 |
| §6 normative-reference list | replace with a link to the planned Part 00 normative bibliography | Centralizes direct external authorities. | §§3.8–3.9 |
| §7 Iceberg item | retain as informative reference | Iceberg remains non-normative and deferred. | §3.8 |
| §7 Zarr v2 item | move to the planned Part 00 normative bibliography because Part 03 permits external Zarr v2 arrays | Corrects its current misclassification as merely informative. | §3.9 |

### 5.4 Affected-surface inventory

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Part 01 §1 receives the unchanged semantic-standard identifier. Unit identity and lower-level representation defects remain deferred. | Part 01 diff changes scope/identity only; its concept rules and registry-facing representation remain unchanged. |
| logical prose and registry | Part 02 §1 receives the unchanged logical-standard identifier. Its existing registry incorporation and §9.2 identity remain authoritative; registry declarations, rules, and meta-schema do not change. | Registry generation preserves every declaration byte; the framework checker resolves the logical identifier and incorporation owner. |
| physical profiles | Part 03 §1 retains the profile identifier as its owner and cites the central external-reference policy without changing storage rules. | Profile identifiers, fixtures, and physical probes remain unchanged. |
| packet catalog and JSON Schemas | Part 04 explains that its identifier fields record the identifiers their subject parts own. Packet schemas, requiredness, `layer`, `canonical`, and registry binding remain deferred. | JSON Schemas and packet corpus remain unchanged; the checker finds each required identifier and its owner. |
| validation and import | Part 05 §10 receives the general packet-conformance statement and links extension composition rather than redefining it. Procedures and verdicts do not change. | Existing corpus results remain unchanged; the relocation inventory accounts for every conformance paragraph. |
| extensions | Part 09 already owns every README extension statement, so its normative body and extension registries remain unchanged; the README replaces duplicates with links. | Existing Part 09 and extension-registry checks remain unchanged. |
| reader, writer, validator, adapters | No runtime behavior changes. Repoint the ten validator, writer, and test citations that name Part 04 §3 for `processing_run_id` to Part 04 §4.1. A new specification-framework check is repository tooling rather than packet validation. | Existing package tests pass; the evidence manifest records the citation-only changes and marks every other implementation surface unchanged with a reason. |
| conformance fixtures and tests | Packet fixtures remain unchanged because the packet contract does not change. Add positive and negative cases for the specification-framework checker. | `conformance/specification-framework/probe.py` covers every numbered part, mixed status, README informativity, normative-reference placement, and combined-rendering reproducibility. |
| revision process and tooling | R120 already owns structural sequencing, stable anchors, citation presentation, ledger destinations, and evidence-owner forms. This revision uses those rules and does not restate or amend them in Part 00. | The process, stage, citation, repointing, heading, ledger, and evidence checks pass against the incorporation. |
| generated publications and developer documentation | The specification README becomes informational; `combine.py` no longer claims it supplies conformance; the combined specification is regenerated; root authority and contribution guidance point to Part 00. Repoint Part 03 §4's packet-root citation from current Part 00 §3 to `ew-packet`. The placement-defect inventory remains non-authoritative. | Generated output is stable on a second run; every current README statement has a disposition; authority summaries link to the same owner. |

The non-authoritative `revisions/PLACEMENT-DEFECTS.md` inventory remains the observation-level audit
trail for known misplaced or duplicate statements. Part 00 does not acquire a changing defect
list, and the reconciliation roadmap remains a dependency plan rather than a list of individual
maladies.

## 6. Conformance and implementation evidence

Incorporation adds `escapewheel_poc_docs_v0.2/framework.py`, a focused
specification-framework checker. It parses Part 00's authority declarations, part-subject and
status table, every local part status, identifier-owner statements, normative bibliography, the
informational README, and the combined rendering. It is specification-maintenance tooling, not a
packet validator and not a normative owner.

Positive cases establish that:

- Parts 00–10 each appear exactly once;
- every local status agrees with Part 00, including Part 06's mixed-section exceptions;
- each candidate component and packet-recorded identifier has exactly the owner the framework
  declares;
- Part 00 contains each direct external authority required by §3.9, does not present an
  implementation as the missing Tier 2 or codec authority, and no normative-reference section
  remains in the README;
- the README contains neither a normative-reference section nor a normative-keyword obligation;
- the README part and identifier summaries agree with their owners; and
- the combined specification is a reproducible projection that includes Part 00.

`conformance/specification-framework/probe.py` supplies the negative cases: a missing or duplicate
part row, an unknown part, a conflicting local status, a missing or conflicting mixed-section
exception, a missing or duplicate identifier owner, a normative-reference section or normative
keyword introduced into the README, a stale README projection, a missing central bibliography
entry, an implementation mislabeled as the Tier 2 or codec authority, and a combined rendering
that is stale or omits Part 00. The verifier runs the current-tree check and the mutation probe as
separate stages named `spec: framework declarations agree` and `spec: framework rejects conflicting
projections`.

Keyword scanning cannot prove that informative prose contains no unique rule. A human relocation
inventory therefore gives every current README paragraph one disposition: moved to an owner,
replaced by a citation, retained as an informative summary, or removed as a duplicate. The
incorporation evidence records that inventory and the framework check's positive and negative
tests.

The impact query over the 22 structurally affected existing sections was rerun against the anchor
bootstrap and the exact revised draft. Incorporation reads all 44 external live citation
occurrences, repoints the 11 semantic defects described in §2.4, and separately sweeps every
destination that receives README text. The 42 occurrences in immutable accepted records remain
unchanged, and the 59 occurrences in this draft remain reviewed history. The evidence manifest
records that no registry declaration, packet schema, fixture, implementation behavior, or version
identifier changed.

The planned authoritative destinations are exact:

| Decision clause | current owner after incorporation |
|---|---|
| §3.1 | Part 00 `ew-specification-candidate` |
| §3.2 | Part 00 `ew-authority-by-concern` |
| §3.3 | Part 00 `ew-candidate-consistency` |
| §3.4 | Part 00 `ew-specification-authority` |
| §3.5 | Part 00 `ew-architecture-classifications` |
| §3.6 | Part 00 `ew-numbered-part-ownership` |
| §3.7 | Part 00 `ew-numbered-part-ownership` |
| §3.8 | Part 00 `ew-specification-candidate` |
| §3.9 | Part 00 `ew-normative-references` |

The mechanical closure commands are the stage and citation checks, the evidence checker, the
revision ledger, the heading check, the combined-specification check, and the complete repository
verifier. Their passing establishes structural and generated agreement; the relocation inventory
and citation reading establish semantic placement.

## 7. Pre-acceptance appraisal

This section records appraisal rather than adding a Decision clause. The draft is rebased on the
post-R121 anchor bootstrap. It contains the exact Part 00 outline, complete numbered-section and
README crosswalks, planned owner anchors, implementation surfaces, and positive and negative
evidence. R120 remains the process owner and R121 remains the cleanup prerequisite; neither is
restated in the specification.

The pre-acceptance appraisal completed on 2026-09-20 against
`41da62e3fd4924e5526f8f812492e90607d14d97` with no remaining blocker:

- **Freshness:** the baseline exists and is the metadata-only anchor bootstrap immediately after
  R121; this is the sole open lifecycle artifact; registry counts, the 22-section impact query,
  and the 44 external live citations were rerun and read.
- **Decision:** §§3.1–3.9 separate authority, representation, generation, and implementation;
  distinguish abstraction level from content class; assign one owner per subject; and permit an
  inconsistent candidate without permitting a conflicting release. No deferred packet-contract
  question is decided implicitly.
- **Structural:** no registry, meta-schema, packet schema, rule, key, field, or vocabulary changes,
  so the declaration-specific gate is not applicable. The document reorganization has an exact
  outline, source/README crosswalks, and stable source and destination anchors.
- **Feasibility:** the framework check and mutation probe name their inputs, outputs, failure cases,
  and verifier stages. Bibliography checking does not mistake DuckDB, zarr-python, Numcodecs, or
  another implementation for a missing language-neutral authority.
- **Compatibility:** packet shape, packet interpretation, and runtime behavior remain unchanged;
  only tools or readers relying on the README, local status headers, revisions, or implementations
  as independent precedence sources are incompatible. No packet migration or regeneration is
  required.
- **Traceability and evidence:** every Decision clause has an anchored destination; every current
  README statement has a disposition; every affected surface has a change or unchanged reason;
  and incorporation must repair the 11 semantic citation defects found by reading the impact set.
- **Mechanical:** `stages.py`, `check_citations.py`, and `repoint.py --quiet` pass;
  `headings.py --check` reports 255 recorded sections with no defect; and `verify.py --quick`
  passes all 25 stages, including the 28-packet corpus.

The material appraisal findings were incorporated into the draft: direct Zarr codec authorities
are no longer hidden behind a generic core-specification citation, absent Tier 2 and codec
authorities cannot be supplied by implementation behavior, and the 11 incorrect live citations
have explicit incorporation dispositions. The draft is ready for acceptance authorization once
these exact bytes and the appraisal record in `drafts/README.md` are committed.

## 8. Deferred work

The following questions do not change §3 and remain separate proposals or maintenance work:

- repair of unit identity and other misplaced lower-level statements;
- the executable Tier 2 rule language and whole-registry conformance semantics;
- resource kinds, resource requiredness, serialized content classification, `layer`, `canonical`,
  and lineage;
- packet identification of core and extension registries and incorporation of packet-related JSON
  Schemas;
- core, extension, and whole-packet validity composition;
- recipe arbitration, the adapter/build-interface boundary, integrity, and codec portability;
- direct declarative authoring of the registry instead of imperative Python construction;
- final semantic, logical, profile, registry, schema, and rule-language identifiers; and
- exact immutable release-manifest structure, membership, role assignments, status projections,
  hashes, and publication tooling.

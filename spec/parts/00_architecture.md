# Part 00 — Architecture

Normative.

<a id="ew-architecture-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines the Escapewheel specification framework: its authority and conformance model,
architectural classifications, numbered-part ownership and status, and publication conventions. It
also states the cross-cutting architecture of an Escapewheel packet. Detailed concept meanings,
logical declarations, physical encodings, manifest fields, and construction and validation rules
belong to the subject-owning parts listed in §8.

This specification defines a portable data packet as a small semantic and logical standard over
commodity storage formats. Its packet mechanism comprises the packet manifest (Part 04), the logical
declaration and registry model (Part 02 §§2–10), the physical profile (Parts 03 and 12), validation
and import (Part 05), extensions (Part 09), and the Tier 2 rule language (Part 11), and it confines
no packet to a recording modality. Which resources a packet carries is decided by the registries it
binds and their presence policies (Part 02 §2.5).

The **core vocabulary** comprises the concepts Part 01 defines and the declarations of the core
registry that Part 02 incorporates. It targets extracellular electrophysiology and the session it
was recorded in. The target states what the vocabulary was designed to represent and requires no
resource of any packet. Another recording modality declares the concepts and resources it needs
beyond the core vocabulary in an extension registry under Part 09 (Part 01 §2.7). They enter the
core vocabulary only through a revision of this specification under Part 09 §7. Data of another
modality that a core declaration already represents, such as a sampled quantity held as an array
asset (Part 01 §3.17), needs no extension.

The specification does not define a storage engine, a PyNWB-compatible object model, an NWB
exporter, a distributed-compute model, or ontology machinery. It has no runtime dependency on NWB, HDMF, or PyNWB, and conformance does not require a
compatibility projection into NWB.

The design objectives are that a packet be fast to query, straightforward to produce from existing
acquisition and sorting outputs, readable from more than one language, independent of HDMF as a
runtime data model, and precise enough to drive validation.

<a id="ew-specification-authority" data-spec-anchor="canonical"></a>
## 2. Specification authority and conformance

Part 00 MUST own specification-candidate identity and candidate/release terminology; conformance
targets and normative-language conventions; the normative-reference policy and shared bibliography;
actors and the terms that resolve to them; normative, informative, and mixed status; artifact
roles and authority by concern; abstraction levels and their dependency direction; packet content
classes; each numbered part's subject; and publication-state conventions.

Part 00 MUST NOT become the owner of exact keys, columns, registry counts, profile encodings,
performance measurements, implementation plans, or detailed lifecycle algorithms merely because
it summarizes the architecture. A lower-level statement that remains here during reconciliation
MUST link to its actual owner or be explicitly informative once that owner is settled.

<a id="ew-specification-candidate" data-spec-anchor="canonical"></a>
### 2.1 Specification candidate and release

The current generated v0.2 numbered parts and every artifact that a numbered part expressly
incorporates MUST constitute the authoritative working specification. An incorporated artifact
MUST participate only for the subject and extent the incorporating part states. A file outside
that set MUST NOT override it.

The **specification's tree** is the directory holding the specification README. The numbered parts
MUST lie within it, and every artifact a numbered part incorporates MUST lie in its `artifacts/`
directory, which MUST hold no other file.

Where a numbered part or an incorporated artifact gives the path of a file other than one within a
packet, and not in a link from one part to another, the path MUST be relative to the tree's root and
MUST name a file within the tree. A numbered part MAY name evidence outside the tree, such as a
conformance probe, by what it is, and MUST NOT give its path.

The working specification MUST be called a **specification candidate** until a publication decision
identifies and freezes an exact release. *Authoritative* describes what governs current development
and conformance; *candidate* describes publication state. Candidate status MUST NOT make the
working specification optional.

A **specification release** MUST be an immutable publication whose publication record identifies
its exact members and versions, and its members MUST lie within the tree. This candidate
distinguishes that state without selecting which of the tree's other files a release includes or a
publication-record format.

The specification README, `README.md`, MUST be an informational entry point. It MAY provide
navigation, candidate status, architectural summaries, build guidance, informative references,
checked status and identifier summaries, and links to owning artifacts. It MUST NOT be the sole
statement of a requirement or supply a normative preamble through its position in a rendering. The
numbered parts MUST remain intelligible without repository-specific developer documentation. The
combined-document generator MAY place the README first for orientation, but that ordering MUST NOT
supply normative force.

`informative/Escapewheel_POC_v0.2_Implementation_Spec.md` MUST be a reproducible convenience
rendering of its inputs. It MUST NOT become a separately edited owner or acquire normative force
from its placement.

<a id="ew-authority-by-concern" data-spec-anchor="canonical"></a>
### 2.2 Authority by concern

Numbered prose MUST own terms, meanings, processing semantics, actor obligations, conformance, and
relationships that a structural declaration cannot express faithfully.

A machine-readable artifact MUST acquire normative authority only when a numbered part expressly
incorporates it. It MUST own only the exact structures or assignments for which that part
incorporates it. The incorporating prose MUST continue to own the vocabulary's meaning, the
semantics of declared fields, and every applicable processing or conformance rule not fully
expressed by the artifact.

Implementations and evidence MUST NOT acquire an independent normative subject by implementing or
testing a rule.

Normativity, representation, and production MUST remain independent properties. Prose is not
normative merely because it is prose; JSON is not authoritative merely because it is structured;
generated output is not informative merely because it is generated. The declared artifact role
and subject ownership determine authority.

<a id="ew-candidate-consistency" data-spec-anchor="canonical"></a>
### 2.3 Internal consistency

Each normative fact MUST have one owner. Another artifact that presents the same fact MUST be one
of:

1. a mechanically checked projection;
2. an explicitly informative explanation that links to its owner; or
3. an explicit consistency condition between different owners' subjects.

A disagreement between owners, an unfaithful projection, or an incorporated artifact that violates
its governing prose MUST make the candidate internally inconsistent. No general prose-wins,
data-wins, generated-wins, or local-file-wins rule MAY turn that disagreement into conformance.
The inconsistent candidate remains the authoritative material to inspect and repair; a
specification release MUST NOT contain an unresolved ownership conflict.

<a id="ew-specification-actors" data-spec-anchor="canonical"></a>
### 2.4 Conformance targets and actors

Requirements in this specification apply to five actors. Every requirement binds one of them or
states a property of an artifact.

A **writer** produces a packet from sources. It stages, validates and commits. Part 05 §1 states
which of Part 05's sections bind each actor.

A **reader** opens a committed packet and returns its resources — rows, arrays, resolved references.
It is bound by what it returns.

A **checker** decides whether a document conforms to the contract governing it, and reports its
findings. The documents are a registry document under Part 02 §9.4, a physical-profile descriptor
under Part 03 §1, and a manifest under Part 04 §10.

A **validator** is the checker of a packet: it decides whether a packet conforms, and reports
findings. It checks each of those documents that the packet carries as a checker does, so a
requirement on a checker binds a validator checking one of them.

A **consumer** interprets values a reader returned and acts on them. It is bound by what it
concludes, and it is the only actor that may be a person rather than a program.

An actor is a part someone plays, not a distribution: one program is commonly all five. Naming them
separately is what lets a clause say who owes an obligation.

Three further terms resolve to those five. A **build** is one execution of a writer against one
recipe, so a requirement on a build binds the writer performing it. An **adapter** is the part of a
writer that reads one source, and an obligation on an adapter binds the writer that ships it. An
**implementation** is software performing one or more of the five, and is the right subject only
where a requirement binds every actor alike, as §3.6's ban on path-based identity does.

`importer` is another name for a writer, `client` and `binding` for a reader, and `caller` for a
consumer. A requirement using one binds the actor it names.

<a id="ew-normative-language" data-spec-anchor="canonical"></a>
### 2.5 Normative language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, NOT
RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in BCP 14 when, and only when,
they appear in all capitals.

<a id="ew-architecture-classifications" data-spec-anchor="canonical"></a>
## 3. Architecture classifications

<a id="ew-abstraction-levels" data-spec-anchor="canonical"></a>
### 3.1 Abstraction levels

The specification MUST call semantic, logical, and physical classifications **abstraction
levels**. A lower abstraction level MUST NOT redefine a rule owned by the level above it. A
physical profile MAY map a logical resource to a storage technology and MUST NOT change that
resource's logical identity or semantic meaning. A workflow MAY describe how an actor satisfies an
owned invariant and MUST NOT restate a second version of that invariant.

<a id="ew-semantic-standard" data-spec-anchor="canonical"></a>
#### 3.1.1 Semantic standard

The **semantic standard** defines what concepts mean. A Trial is a bounded interval of experimental
time; a Unit is a sorted or curated spiking entity; an ElectricalSeries is sampled extracellular
voltage over time and channels.

The semantic standard is independent of storage format and of whether a concept is represented as
a table or an array. Part 01 specifies it.

<a id="ew-logical-standard" data-spec-anchor="canonical"></a>
#### 3.1.2 Logical standard

The **logical standard** defines how semantic concepts are represented as computable resources.
Its three logical kinds are tables, dense arrays, and opaque payloads. A view or materialization is
a realization of one of those kinds rather than another kind.

The logical standard is storage-agnostic but not shape-agnostic: trials are logically table-shaped.
Part 02 and the artifacts it incorporates specify it.

<a id="ew-physical-profile" data-spec-anchor="canonical"></a>
#### 3.1.3 Physical profile

A **physical profile** defines how logical resources are stored, and can also define the adapter
interface by which a build writing a packet under it receives what adapters read. Two are
contemplated:

| profile | tables | arrays | manifest |
|---|---|---|---|
| portable | Parquet | Zarr | JSON manifest |
| lakehouse | Iceberg over Parquet | Zarr | JSON manifest plus Iceberg catalog references |

Only the portable profile, `escapewheel-portable-v0.1`, is specified, and it defines both. Part 03
specifies how it stores a packet and is normative for a packet whose manifest declares its
`profile_id` and binds no other packet; Part 12 specifies its adapter interface. A physical profile
is the only abstraction level whose rules may depend on a storage technology, and Parts 03 and 12,
which form the physical level, are the only parts whose rules may.

<a id="ew-packet-content-classes" data-spec-anchor="canonical"></a>
### 3.2 Packet content classes

The specification MUST call content's architectural relationship to a packet its **packet content
class**. Part 02 §2.2 defines the five classes, their serialized values, and which are canonical.

Part 02 §2.2 owns which content classes a declaration may reference, require, or bind to, and
Part 09 §§6.1–6.2 own which registry it may reference and how a discriminator names a resource
without referencing it.

A packet's **canonical** resources are exactly its `core` and `extension` resources. Core is not
the whole of what is canonical: Part 09 sends a task's own facts
— which side the animal licked, whether it was rewarded — to a typed extension, and no computation
over core recovers them. Core is what every consumer can read without an extension registry. Part
02's declaration presence policies, not the content class alone, determine which core resources
every packet has.

A consumer MAY read core alone, and what it reads is complete for every core resource. It MUST NOT
conclude it has read every canonical fact the packet holds; a discriminator resolving `required`
is the case where the omission is guaranteed.

Content class MUST remain independent of abstraction level, namespace, and resource kind.
Resources of different kinds may share a content class, and resources of one kind may occupy
different content classes.

**Namespace** MUST remain the dotted-identifier ownership mechanism. Extension namespaces are
specified in Part 09. **Resource kind** MUST classify a logical resource's form independently of
its content class and physical encoding. Part 02 owns the exact serialized content-class and kind
vocabularies, declaration eligibility, presence, canonicality derivation, and lineage relation. A
packet entry names a declaration and MUST NOT repeat content class, kind, or canonicality.

<a id="ew-packet" data-spec-anchor="canonical"></a>
### 3.3 Packet

A **packet** is one concrete dataset bundle under a declared profile. It may be a local directory,
an object-store prefix, or a manifest pointing at distributed assets.

A packet contains a packet manifest, the registries it binds, and resources of the three logical
kinds (§3.1.2), each in one content class (§3.2).

A packet is primarily single-session. Multi-session packets are a permitted extension, and a
packet declares its sessions in the manifest.

<a id="ew-packet-catalog" data-spec-anchor="canonical"></a>
### 3.4 Packet manifest

The **packet manifest** is the dataset-level map. In the portable profile it is `packet.json`,
specified in Part 04.

It records which resource instances exist, the logical declarations they instantiate, their
locations, and their instance-level validation and provenance facts. The checked registry
declaration supplies logical kind, content class, canonicality, presence, and provenance policy.
The packet's profile and the declaration's kind derive a generic physical interface under Part
03; format-owned metadata supplies the representation's version and physical features.

<a id="ew-iceberg-catalog" data-spec-anchor="canonical"></a>
### 3.5 Iceberg catalog

An **Iceberg catalog** is distinct from the packet manifest. It is relevant only to the lakehouse
profile and manages only tabular resources. It does not catalog dense arrays, opaque payloads, or
semantic relationships across a packet, and therefore does not replace the packet manifest.

<a id="ew-resource-identity" data-spec-anchor="canonical"></a>
### 3.6 Resource identity

Resources and rows reference each other by stable identifier. An implementation MUST NOT use HDF5
object references, Zarr hierarchy paths, host object identity, or file layout as the primary
identity system.

<a id="ew-core-content-class" data-spec-anchor="canonical"></a>
## 4. Core content class

<a id="ew-core-content-requirements" data-spec-anchor="canonical"></a>
### 4.1 Requirements

The core content class MUST contain canonical facts in the logical schemas of Part 02. A writer
publishes a packet, core resources included, only as
[Part 05 §9.2](05_validation_and_import.md#ew-error-policy) permits. The required minimum is the closure of Part
02's declaration presence, dependency, populated-reference, and catalog rules; membership in the core class alone does not require an instance.

A fact belongs in core when common interpretation, validation, joining or analysis would break
without it (Part 09 §3). A fact a single domain owns belongs in that domain's extension, typed,
with its own vocabularies and rules — not in core, and not in a free-form column.

Core resources are normalized enough to avoid drift and no further. Part 02 §11 declares each core
resource's grain.

<a id="ew-analysis-content-class" data-spec-anchor="canonical"></a>
## 5. Analysis content class

<a id="ew-analysis-content-requirements" data-spec-anchor="canonical"></a>
### 5.1 Requirements

The analysis content class MAY contain denormalized, prejoined, binned, aligned, or otherwise
transformed products. Part 06 owns its disposability, when a view or a materialization is
justified, and its exact lineage, realization, and promotion requirements and its optional run
provenance.

## 6. Deferred NWB projection

A packet SHOULD preserve enough semantic metadata to support an NWB-like projection later. This
specification does not require PyNWB-compatible object reconstruction, NWB/HDF5 or NWB-Zarr export,
or a complete mapping onto the `NWBFile` hierarchy.

Reserved NWB names are not honoured. A projection is therefore a mapping exercise and not a
renaming.

## 7. Storage stance

### 7.1 Portable profile first

The portable profile stores tables as Parquet, dense arrays as Zarr, and each packet-owned opaque
payload as one file or one directory, under a JSON manifest. Part 03 §1 requires a packet under it
to be readable without a server.

<a id="ew-external-resource-referencing" data-spec-anchor="canonical"></a>
### 7.2 Referencing

A packet need not own every byte it describes. Externality changes ownership and what can be
inspected; it does not move format-owned metadata into the manifest. Part 04 §5 specifies how a
packet declares, records, and verifies a resource it does not own.

<a id="ew-later-physical-profiles" data-spec-anchor="canonical"></a>
### 7.3 Iceberg later

Iceberg is a later table-management profile, useful for table snapshots, schema and partition
evolution, concurrent writers, catalog integration, and reproducible release tags. An
implementation of this specification MUST NOT require it.

A physical profile — Iceberg's or any other — MUST declare a `profile_id` that a packet's manifest
names, MUST bind only the packets declaring it, MUST say how each logical resource of Part 02
is stored, and MUST say how an amendment (Part 05 §15) is realized under it: how a resource that
gains rows is stored, where superseded manifests are retained, and what a stray is. It MUST NOT require an amendment to Part 01 or Part 02; where one would be needed, the
defect is in those parts rather than in the profile. A physical profile's adapter interface binds a
build only while the build writes a packet declaring the profile, and binds an adapter only while
such a build reaches it. No clause of Part 01 or Part 02 may depend on a clause of Part 03 or
Part 12.

<a id="ew-numbered-part-ownership" data-spec-anchor="canonical"></a>
## 8. Part subjects and normative status

Part 00 MUST assign the subject and normative status of every numbered part. A local status line
MUST be a checked projection of this table and MUST NOT become a precedence source. A disagreement
MUST make the candidate inconsistent.

| part | subject | status |
|---|---|---|
| 00 | specification framework, authority, abstractions, part ownership and publication conventions | normative |
| 01 | substrate-independent meanings of scientific and provenance concepts | normative |
| 02 | logical resources, declarations, identities, references, and registry semantics | normative |
| 03 | portable physical mapping of logical resources to stored bytes | normative |
| 04 | packet manifest structure, resource entries, and dataset-to-resource bindings | normative |
| 05 | validation, import, writer and reader operations, reporting, and publication of a packet | normative |
| 06 | analysis policy, examples, and explanation | informative except §§2, 4, and 5, which are normative |
| 07 | reference-implementation design and examples | informative |
| 08 | executable packet example | informative |
| 09 | extension boundaries, namespace ownership, extension declarations, and extension independence | normative |
| 10 | performance measurements and rationale | informative |
| 11 | portable language and execution semantics for registry-declared validation rules | normative |
| 12 | exchange between a build and the adapters it reaches under the portable profile | normative |

An informative section MUST NOT be the sole statement of an obligation. A part MUST NOT state a
second version of a rule another part owns. It MAY cite the owner, or summarize the rule only when
the summary is explicitly informative.

The numbered parts MUST observe this dependency direction:

1. Part 01 defines meaning without selecting a resource shape or storage technology.
2. Part 02 and an expressly incorporated registry represent Part 01 concepts as logical resources,
   identities, relationships, and constraints without selecting a storage technology.
3. Part 11 maps Part 02's declared resources and types into portable rule evaluation without
   redefining logical declarations or Part 05's validation and reporting workflow.
4. Part 03 maps logical resources to bytes under a profile without changing their logical identity
   or semantic meaning.
5. Part 04 binds concrete packet resources to the semantic, logical, registry, and profile
   identifiers that govern them without redefining those contracts.
6. Part 05 specifies how writers, readers, and validators construct and judge instances under the
   upstream contracts rather than becoming a second owner of those contracts.
7. Part 12 specifies what a build and the adapters it reaches exchange under a profile, within
   Part 05's import pipeline, without changing Part 02's logical resources and identities or how
   Part 03 stores them; Part 05 cites it for what a build supplies an adapter and what a delivery
   states.
8. Part 09 permits namespaced extension declarations under the same applicable semantic, logical,
   physical, manifest, and conformance boundaries without altering core.

A writer MUST interpret adapter declarations and output under the owning numbered parts and
incorporated declarations. An adapter's participation in ingestion MUST NOT let it redefine the
packet contract. Authority follows express incorporation and subject ownership, not the direction
of a software call or generation step.

A future release manifest MAY record numbered-part status, but that value MUST be a checked
projection of this section. The manifest MUST NOT become a second owner of numbered-part status.

<a id="ew-normative-references" data-spec-anchor="canonical"></a>
## 9. Normative-reference policy and shared references

Part 00 MUST own the specification-wide policy for external normative references. An external
authority that normative prose in exactly one numbered part invokes directly MUST have its
bibliographic entry in a normative-reference section of that part. An external authority that
normative prose in more than one numbered part invokes directly, or that the Part 00 framework
itself invokes, MUST have one shared bibliographic entry in Part 00.

Normative prose invokes an external authority **directly** when it identifies that authority as
the basis for one or more requirements. A citation to another numbered part's Escapewheel contract
is not a direct invocation of the external authorities on which that contract relies.

Each direct external normative authority MUST have exactly one bibliographic entry in the numbered
parts. Each part whose normative prose invokes an external authority directly MUST identify the
applicable entry from the prose that establishes the authority's use and MUST state the extent to
which it applies. That invocation MAY govern a defined group of requirements and need not be
repeated in each requirement. A bibliographic entry identifies the external document and edition;
it MUST NOT become the owner of the Escapewheel meaning, processing rule, actor obligation, or
conformance behavior that invokes it.

An informative mention of a technology MUST NOT make its specification normative. Moving a
bibliographic entry MUST NOT change the referenced behavior, and a reference used by several
parts through direct invocation MUST NOT be copied into several normative-reference sections. The
informational specification README MUST NOT contain a normative-reference section or become an
independent bibliographic owner.

An **exact** bibliographic entry MUST identify the edition used by the candidate. An
**unversioned** entry MUST be identified as such and follows the linked external specification
during candidate development. A **living-registry** entry identifies a registry that assigns names
or identifiers as they are registered, by the registry's name and URI, and gives `living registry`
as its candidate edition. A numbered part MAY give an authority a living-registry entry only where
the authority is such a registry and no validator verdict depends on its content. A requirement
invoking a living registry refers to the registry as it stood when the bound actor acted; for a
spelling requirement, when the writer wrote the value, so a later registration or renaming leaves
the value conforming.

A specification release MUST identify the exact external edition on which every conformance
requirement depends, and MUST identify each living registry by its entry's name and URI in place of
an edition.

A normative reference's own dependencies MUST apply through that reference and need not be copied
into an Escapewheel reference section unless this specification relies on them directly. Where
required behavior has no sufficient language-neutral authority, a numbered part MUST NOT promote
an implementation or library's observed behavior into a normative reference. The missing authority
MUST remain a candidate defect and MUST prevent release until the subject-owning part defines the
behavior or cites an adequate specification.

The application column states the extent to which the specification invokes each shared authority:

| reference | candidate edition | application |
|---|---|---|
| [BCP 14](https://www.rfc-editor.org/info/bcp14), comprising RFC 2119 and RFC 8174 | exact RFC editions | normative keywords |
| [RFC 8259](https://www.rfc-editor.org/info/rfc8259) | exact | JSON |
| [RFC 3986](https://www.rfc-editor.org/info/rfc3986) | exact | URI syntax |
| [JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core) and [Validation](https://json-schema.org/draft/2020-12/json-schema-validation) | Draft 2020-12 | incorporated JSON Schemas |
| [RFC 1952](https://www.rfc-editor.org/info/rfc1952) | exact | gzip member format of a bound registry (Part 03 §3.3) and CRC-32 (Part 04 §4.3) |
| [Apache Parquet format](https://github.com/apache/parquet-format), including [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md) | unversioned | Parquet files and logical types of stored tables (Part 03 §5) and of `files-v0.1` deliveries (Part 12 §3) |

The missing-authority release block applies currently to any required Zarr codec configuration or
binary behavior not determined by the authorities in
[Part 03 §12](03_portable_physical_profile.md#ew-portable-profile-normative-references).

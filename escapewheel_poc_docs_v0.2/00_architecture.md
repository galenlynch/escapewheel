# Part 00 — Architecture

Normative.

<a id="ew-architecture-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines the Escapewheel specification framework: its authority and conformance model,
architectural classifications, numbered-part ownership and status, and publication conventions. It
also states the cross-cutting architecture of an Escapewheel packet. Detailed concept meanings,
logical declarations, physical encodings, catalog fields, and construction and validation rules
belong to the subject-owning parts listed in §9.

This specification defines a portable representation of extracellular electrophysiology data as a
small semantic and logical standard over commodity storage formats. It does not define a storage
engine, a PyNWB-compatible object model, an NWB exporter, a distributed-compute model, or ontology
machinery. It has no runtime dependency on NWB, HDMF, or PyNWB, and conformance does not require a
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

The working specification MUST be called a **specification candidate** until a publication decision
identifies and freezes an exact release. *Authoritative* describes what governs current development
and conformance; *candidate* describes publication state. Candidate status MUST NOT make the
working specification optional.

A **specification release** MUST be an immutable publication whose publication record identifies
its exact members and versions. This candidate distinguishes that state without selecting final
release membership or a publication-record format.

`README.md` MUST be an informational entry point. It MAY provide navigation, candidate status,
architectural summaries, build guidance, informative references, checked status and identifier
summaries, and links to owning artifacts. It MUST NOT be the sole statement of a requirement or
supply a normative preamble through its position in a rendering. The numbered parts remain
intelligible without repository-specific developer documentation. The combined-document generator
MAY place the README first for orientation, but that ordering MUST NOT supply normative force.

`Escapewheel_POC_v0.2_Implementation_Spec.md` MUST be a reproducible convenience rendering of its
inputs. It MUST NOT become a separately edited owner or acquire normative force from its
placement.

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

Requirements in this specification apply to four actors. Every requirement binds one of them or
states a property of an artifact.

A **writer** produces a packet from sources. It stages, validates and commits, and it is the actor
Part 05 binds throughout.

A **reader** opens a committed packet and returns its resources — rows, arrays, resolved references.
It is bound by what it returns.

A **validator** decides whether a packet conforms, and reports findings.

A **consumer** interprets values a reader returned and acts on them. It is bound by what it
concludes, and it is the only actor that may be a person rather than a program.

An actor is a part someone plays, not a distribution: one program is commonly all four. Naming them
separately is what lets a clause say who owes an obligation.

Three further terms resolve to those four. A **build** is one execution of a writer against one
recipe, so a requirement on a build binds the writer performing it. An **adapter** is the part of a
writer that reads one source, and an obligation on an adapter binds the writer that ships it. An
**implementation** is software performing one or more of the four, and is the right subject only
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

A **physical profile** defines how logical resources are stored. Two are contemplated:

| profile | tables | arrays | catalog |
|---|---|---|---|
| portable | Parquet | Zarr | JSON manifest |
| lakehouse | Iceberg over Parquet | Zarr | JSON manifest plus Iceberg catalog references |

Only the portable profile, `escapewheel-portable-v0.1`, is specified. Part 03 specifies it and is
normative for a packet whose manifest declares its `profile_id` and binds no other packet. A
physical profile is the only abstraction level whose rules may depend on a storage technology.

<a id="ew-packet-content-classes" data-spec-anchor="canonical"></a>
### 3.2 Packet content classes

The specification MUST call content's architectural relationship to a packet its **packet content
class**.

| serialized value | contents | canonical | required by class |
|---|---|:---:|:---:|
| `core` | domain-general normalized facts | yes | no |
| `extension` | typed facts a domain owns (Part 09) | yes | no |
| `analysis` | products reproducible from canonical resources | no | no |
| `compatibility_projection` | a projection into another representation | no | no |
| `documentation` | human-readable sidecars that assert no semantic or conformance fact | no | no |

A content class MAY reference a class beneath it and MUST NOT reference one above. Core does not
reference analysis, and neither references an extension — a discriminator names without
referencing, which is why core is allowed that one.

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

A packet contains a packet catalog, core tables, and any of: dense arrays, media, documents and
sidecars, analysis materializations, and validation and provenance records.

A packet is primarily single-session. Multi-session packets are a permitted extension, and a
packet declares its sessions in the catalog.

<a id="ew-packet-catalog" data-spec-anchor="canonical"></a>
### 3.4 Packet catalog

The **packet catalog** is the dataset-level map. In the portable profile it is `packet.json`,
specified in Part 04.

It records which resource instances exist, the logical declarations they instantiate, their
locations and physical encodings, and their instance-level validation and provenance facts. The
checked registry declaration supplies logical kind, content class, canonicality, presence, and
provenance policy.

<a id="ew-iceberg-catalog" data-spec-anchor="canonical"></a>
### 3.5 Iceberg catalog

An **Iceberg catalog** is distinct from the packet catalog. It is relevant only to the lakehouse
profile and manages only tabular resources. It does not catalog dense arrays, media, documents, or
semantic relationships across a packet, and therefore does not replace the packet catalog.

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
MUST validate core resources before it commits them. The required minimum is the closure of Part
02's declaration presence, dependency, populated-reference, catalog, and producing-run rules;
membership in the core class alone does not require an instance.

A fact belongs in core when common interpretation, validation, joining or analysis would break
without it (Part 09 §3). A fact a single domain owns belongs in that domain's extension, typed,
with its own vocabularies and rules — not in core, and not in a free-form column.

Core resources are normalized enough to avoid drift and no further. One row per trial in
`core.intervals`; one row per unit in a sorting and curation context in `core.units`; one row per
spike in `core.spike_events`.

### 4.2 Spike representation

`core.spike_events`, one row per spike with primitive columns only, is the sole canonical spike
representation. The ragged chunked representation of v0.1 is withdrawn, as is the catalog's
`canonical_representations` block.

`core.units` carries `n_spikes`, `first_spike_tick` and `last_spike_tick` as a denormalization that
a validator checks against `core.spike_events`.

<a id="ew-analysis-content-class" data-spec-anchor="canonical"></a>
## 5. Analysis content class

<a id="ew-analysis-content-requirements" data-spec-anchor="canonical"></a>
### 5.1 Requirements

The analysis content class MAY contain denormalized, prejoined, binned, aligned, or otherwise
transformed products. Part 06 owns its exact lineage, producing-run, realization, and promotion
requirements.

Analysis resources are disposable. A writer MAY delete and recompute any of them. An analysis
resource becomes canonical only through an explicit revision of this specification.

<a id="ew-analysis-materialization-criterion" data-spec-anchor="canonical"></a>
### 5.2 Materialization is justified by layout, not by arithmetic

A materialization is a physical realization of an analysis resource, not a logical kind. Part 06
defines when analysis views and materializations are justified and how their lineage is recorded.

## 6. Deferred NWB projection

A packet SHOULD preserve enough semantic metadata to support an NWB-like projection later. This
specification does not require PyNWB-compatible object reconstruction, NWB/HDF5 or NWB-Zarr export,
or a complete mapping onto the `NWBFile` hierarchy.

Reserved NWB names are not honoured. A projection is therefore a mapping exercise and not a
renaming.

## 7. Storage stance

### 7.1 Portable profile first

The portable profile is a JSON manifest, Parquet tables, Zarr arrays, ordinary media files, and
text sidecars. It MUST be readable without a server.

### 7.2 Referencing

A packet need not own every byte it describes. Referencing is expected for large resources: a
resource the packet does not own sets `external: true` with an absolute URI and declares its own
codecs.

Externalizing a table costs more than externalizing an array, because a table's validation rules
cannot run at all while it is unreachable.

### 7.3 Iceberg later

Iceberg is a later table-management profile, useful for table snapshots, schema and partition
evolution, concurrent writers, catalog integration, and reproducible release tags. An
implementation of this specification MUST NOT require it.

A physical profile — Iceberg's or any other — MUST declare a `profile_id` that a packet's manifest
names, MUST bind only the packets declaring it, and MUST say how each logical resource of Part 02
is stored. It MUST NOT require an amendment to Part 01 or Part 02; where one would be needed, the
defect is in those parts rather than in the profile. No clause of Part 01 or Part 02 may depend on a
clause of Part 03.

`packet_version` versions the bundle; an Iceberg snapshot would version a table's rows. A writer
MUST NOT increment `packet_version` for a rewrite of rows.

## 8. Implementation thesis

The first implementation is not a generic NWB backend. It is:

1. a specification of core logical resources;
2. a validator generated from that specification;
3. an importer that turns source data into validated resources;
4. a packet catalog recording the committed resources;
5. a small access library querying tables and arrays with standard engines.

An import succeeds only when validation succeeds (Part 05 §1).

<a id="ew-numbered-part-ownership" data-spec-anchor="canonical"></a>
## 9. Part subjects and normative status

Part 00 MUST assign the subject and normative status of every numbered part. A local status line
MUST be a checked projection of this table and MUST NOT become a precedence source. A disagreement
MUST make the candidate inconsistent.

| part | subject | status |
|---|---|---|
| 00 | specification framework, authority, abstractions, part ownership and publication conventions | normative |
| 01 | substrate-independent meanings of scientific and provenance concepts | normative |
| 02 | logical resources, declarations, identities, references, and registry semantics | normative |
| 03 | portable physical mapping of logical resources to stored bytes | normative |
| 04 | packet catalog structure, resource entries, and dataset-to-resource bindings | normative |
| 05 | validation, import, writer and reader operations, reporting, and publication of a packet | normative |
| 06 | analysis policy, examples, and explanation | informative except §§2 and 5, which are normative |
| 07 | reference-implementation design and examples | informative |
| 08 | executable packet example | informative |
| 09 | extension boundaries, namespace ownership, extension declarations, and extension independence | normative |
| 10 | performance measurements and rationale | informative |
| 11 | portable language and execution semantics for registry-declared validation rules | normative |

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
7. Part 09 permits namespaced extension declarations under the same applicable semantic, logical,
   physical, catalog, and conformance boundaries without altering core.

A writer MUST interpret adapter declarations and output under the owning numbered parts and
incorporated declarations. An adapter's participation in ingestion MUST NOT let it redefine the
packet contract. Authority follows express incorporation and subject ownership, not the direction
of a software call or generation step.

A future release manifest MAY record numbered-part status, but that value MUST be a checked
projection of this section. The manifest MUST NOT become a second owner of numbered-part status.

<a id="ew-normative-references" data-spec-anchor="canonical"></a>
## 10. Normative-reference policy and shared references

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
during candidate development. A specification release MUST identify the exact external edition on
which every conformance requirement depends.

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

The missing-authority release block applies currently to any required Zarr codec configuration or
binary behavior not determined by the authorities in
[Part 03 §12](03_portable_physical_profile.md#ew-portable-profile-normative-references).

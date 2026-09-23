# A Portable Profile Declares Its Interfaces and Reader Floor

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `a52e4fc56dbbf7dd6be4d7d64145404b1c838b5d` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 00 §§3.4 and 7.2; Part 03 §§1–2, 5.1–5.2, 5.5, 6.1, 6.4–6.5, 11.3, and 12; Part 04 §§3, 4.1, 5.3, and 6; Part 05 §5.3; `registry/manifest.schema.json`; `registry/resources.schema.json`; a new physical-profile descriptor and schema |
| **Depends on** | [R122 §§3.2–3.3 and 3.6](../accepted/R122-define-specification-artifacts-and-normative-ownership.md#3-decision); [R124 §3](../accepted/R124-normative-references-reside-with-their-subject-owners.md#3-decision); [R128 §§3.3–3.4 and 3.8–3.9](../accepted/R128-every-packet-resource-instantiates-a-logical-declaration.md#3-decision) |
| **Profile** | `escapewheel-portable-v0.1` |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8; §3.9; §3.10; §3.11 |

Section 3 is normative. Sections 1, 2, and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

This revision gives the portable profile one machine-readable physical descriptor. The selected
profile and a resource's resolved logical kind determine the generic interface. The descriptor
also states the minimum physical features every conforming reader supports for that interface or
variant.

The packet continues to select one profile with `profile_id`, but it no longer repeats derived or
self-describing physical facts in each resource entry. Parquet and Zarr remain responsible for
their own format metadata. The descriptor owns the profile's exact kind-to-interface mapping,
resource form, ownership compatibility, discoverable variants, reader floor, and whether that
floor also bounds a packet writer.

This revision is structural because the present rules are divided among an architectural summary,
Part 03 prose tables, packet fields, JSON Schema enums, and implementation constants. Appending one
more declaration would leave several apparent owners. Incorporation therefore consolidates exact
assignments in the descriptor, retains their semantics and actor obligations in Part 03, and
removes redundant packet claims.

This revision does not complete the manifest's registry-identity model, define final packet-verdict
composition, define an offline capability-negotiation index, add partitioned tables, or introduce
a serialized view representation.

### 1.1 Structural crosswalk

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| [Part 00 §3.4](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-packet-catalog), the catalog records each resource's physical encoding | replace with an architectural summary | Part 03 and its incorporated descriptor | the catalog selects one profile and locates instances; it does not repeat the interface or self-describing format metadata | §§3.1–3.2, 3.6 |
| [Part 00 §7.2](../../escapewheel_poc_docs_v0.2/00_architecture.md#ew-external-resource-referencing), an external resource declares its codecs | replace in place | Part 03 and resource-owned metadata | externality changes ownership and inspection reach, not codec authority | §§3.5–3.8 |
| [Part 03 §1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-scope), profile scope and identity | expand in place | same section plus incorporated artifacts | expressly incorporates the physical-profile descriptor and schema | §3.1 |
| [Part 03 §2](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-technologies), hand-authored required-technologies table | replace with a generated projection and opaque explanation | physical-profile descriptor | exact generic interface assignments become data; opaque representations remain unenumerated | §§3.1–3.2, 3.9 |
| [Part 03 §§5.1–5.2](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-table-encoding), Parquet file encoding and partitioning | consolidate and replace | Part 03 table-interface section and descriptor | every current table is one Parquet object; the unsupported multi-file case no longer has partial rules | §3.3 |
| [Part 03 §5.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-parquet-reader-floor), hand-authored Parquet reader and writer floor | replace exact assignments with a generated projection | physical-profile descriptor | expresses the measured modern floor with the enum names reported by Parquet metadata and applies it to packet-owned writer output | §§3.3, 3.5 |
| [Part 03 §6.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-array-version), catalog-declared Zarr version | revise in place | Zarr metadata, interpreted under the descriptor | version is discovered from the resource; ownership still restricts v2 to external resources | §3.4 |
| [Part 03 §6.4](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-array-codecs), hand-authored codec table and packet codec declarations | split | descriptor owns the reader-only floor; Zarr metadata owns actual use; Part 03 owns reader and writer behavior | replaces pseudo-codec names with metadata patterns, leaves valid Zarr writer choices open, and removes the optional-capability list and duplicated packet claims | §§3.4–3.8 |
| [Part 03 §6.5](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-array-metadata-placement), all validation metadata must also be in tables or the catalog | narrow in place | logical declarations and resource metadata in their respective layers | logical and scientific facts stay outside optional attributes; self-describing physical facts need not be copied | §3.11 |
| [Part 03 §11.3](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-referenced-resource-delivery), a build derives packet codec fields from delivered arrays | revise in place | resource metadata and build inspection | adapters deliver bytes or locations without restating version or codec metadata | §3.11 |
| [Part 03 §12](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-normative-references), portable-profile normative references | extend in place | same section | adds the official Zarr `zstd` extension specification as the metadata and configuration authority while retaining RFC 8878 for the encoded frame | §3.4 |
| [Part 04 §3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-identifiers), top-level `required_codecs` | retire | no replacement packet field | whole-packet codec negotiation is not part of the current contract | §3.6 |
| [Part 04 §4.1](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-resource-entry-fields), `physical_profile` and `codecs` resource fields | retire, together with schema-only `partitioning` | descriptor derivation and resource metadata | packet entries stop duplicating interface, layout, version, and codec facts | §§3.2, 3.6 |
| [Part 04 §5.3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-external-resource-verification), external-resource physical assessment | clarify in place | resource metadata when reachable | an unavailable external resource remains physically unassessed | §§3.7–3.8 |
| [Part 04 §6](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-codecs), per-resource codecs and packet union | retire §§6.1–6.2 | descriptor reader floor and resource metadata | readers inspect only resources they access; no packet codec projection remains | §§3.5–3.8 |
| [Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim), hard-coded physical dispatch | revise in place | descriptor-driven physical checks | validation resolves logical kind, derives the interface, and then inspects available resource metadata | §§3.2, 3.8 |
| `registry/manifest.schema.json` | remove the four redundant physical fields and their conditional branches | Part 04 schema projection | incompatible development-schema migration with no replacement selector or codec summary | §3.6 |
| `registry/resources.schema.json` | remove any physical selector or metadata summary inherited from a manifest entry | Part 03 delivery schema | an adapter supplies resource identity and location, not unverifiable physical claims | §§3.6, 3.11 |
| no current machine-readable physical-profile artifact | add a closed schema, one descriptor, and a generic semantic checker | Part 03 and its incorporated artifacts | local shape, exact assignments, and cross-member invariants each gain one explicit owner; the checker enforces without becoming authority | §§3.1–3.5 |

No normative statement in the informational specification README changes owner. Its inventory and
physical-profile summary are regenerated as informative projections.

## 2. Background

### 2.1 Current disagreement

At the baseline, `profile_id` identifies the whole portable profile while a resource field also
called `physical_profile` contains one of nine interface, version, layout, or opaque-format names.
The logical registry now declares only `table`, `dense_array`, and `opaque`, but no incorporated
artifact maps those kinds to the interfaces the profile supplies.

The reader, writer, and validator each reconstruct the mapping and codec floor with local
constants. Their Zarr sets differ. The validator's set named `FLOOR` includes features Part 03
calls optional, while the reader and writer recognize other combinations. A bare packet codec name
also loses the Zarr-version and configuration context that determines support.

Parquet and Zarr already carry the facts needed to open them. A Parquet footer identifies
compression and value encoding. Zarr metadata identifies format version, shape, dtype, chunking,
and the complete codec pipeline. Copying selected facts into `packet.json` creates a second,
weaker record that can become stale and cannot establish anything about an unavailable external
resource.

### 2.2 Selected model

The selected model has three layers:

1. the logical registry declares a resource's logical kind;
2. the packet's `profile_id` and that kind select one generic physical interface through the
   physical-profile descriptor; and
3. the resource's own metadata supplies its discoverable variant and actual physical features.

The descriptor contains a direct reader floor for each applicable interface or variant. That floor
is a conformance minimum, not an exhaustive vocabulary of upstream format features and not a claim
about every feature one implementation supports. It can drive conformance vectors, validator
comparison, and writer defaults without becoming a capability-negotiation protocol.

The floor has deliberately different force for the two modeled interfaces. Packet-owned tables
are the common query substrate that makes a packet useful without specialized payload support, so
their writers stay inside the Parquet floor. Dense arrays retain modeled identity, axes, and
logical-value access, but their payloads are selected individually and Zarr implementation support
varies more widely; the Zarr floor is therefore a reader minimum rather than a writer ceiling.
This distinction does not turn a dense array into an `opaque` logical resource.

### 2.3 Single-object tables

Withdrawn R42 measured a 650 MB, 286,896,563-row table as one file, an explicit member list, a
globbed dataset, and a Hive layout. DuckDB was faster on the single file for every measured query;
PyArrow's multi-file gains occurred where scan parallelism rather than partition pruning dominated.
The experiment also exposed unresolved snapshot membership and cross-file ordering semantics.

The current writer and fixture corpus use one Parquet file per table. The current profile therefore
chooses that complete and exercised contract rather than retaining an unused `parquet_dataset`
branch with no immutable membership or defined row order.

### 2.4 The Parquet floor covers current output

The appraisal inspected 898 generated repository Parquet files comprising 6,844 column chunks.
Every chunk used `ZSTD`, `PLAIN`, and `RLE`; 6,578 also used `RLE_DICTIONARY`. The reference
writer's ordinary and streamed packet-table paths fix compression to Zstd and select only plain,
dictionary, or `DELTA_BINARY_PACKED`; the committed-packet end-to-end suite exercises that delta
path and passes.

The selected compression floor therefore exceeds current output by also admitting `UNCOMPRESSED`,
`SNAPPY`, and `GZIP`. The encoding floor contains every enum current output reports and additionally
admits the writer's exercised `DELTA_BINARY_PACKED` path. It does not admit
`DELTA_LENGTH_BYTE_ARRAY`, `DELTA_BYTE_ARRAY`, or `BYTE_STREAM_SPLIT`: the reference writer does
not use them, and existing probe notes record reader gaps for the byte-array delta forms. A later
measured change can widen the floor without weakening the present compatibility guarantee.

The Parquet format has independent compatibility dimensions that a single format-version number
does not summarize. In particular, `FileMetaData.version` has not been assigned consistently and
does not record the parquet-format release. Data Page V2 is a separate page layout. The
[Apache Parquet implementation matrix](https://parquet.apache.org/docs/file-format/implementationstatus/)
reports read support for both page layouts in every implementation it lists, including Arrow,
DuckDB, Polars, parquet-java, Arrow Go, Arrow Rust, cuDF, hyparquet, and DataHaskell. The floor
therefore admits both `DATA_PAGE` (Data Page V1) and `DATA_PAGE_V2` directly rather than treating a
nominal file version as a capability declaration. The reference writer currently uses PyArrow's
V1 default and no Parquet modular encryption; page layout remains a writer choice because V2 is
not a universal performance improvement and does not reduce file-footer access.

A local feasibility probe rewrote all 30 Parquet tables in the valid packet fixture with PyArrow
25.0.1 and `data_page_version="2.0"`. The actual `Packet.table` path, DuckDB 1.5.5, and Polars
1.44.1 read every rewritten table, and all three paths reported the same 142 total rows. The
reference writer does not currently expose a page-layout choice, but its PyArrow dependency writes
V2 through that one existing option. Permitting V2 therefore creates no reader-stack gap and does
not require packet metadata or a new storage interface.

### 2.5 Compatibility

This is an incompatible development change to packet and delivery schemas. Existing generated
packets, fixtures, and vendored schemas are regenerated. There are no released consumers or remote
compatibility obligations, so implementations need not dual-read the removed fields.

## 3. Decision

### 3.1 Part 03 incorporates one physical-profile descriptor

Part 03 MUST incorporate `registry/physical_profile.schema.json` and
`registry/physical_profiles/escapewheel-portable-v0.1.json`. The schema MUST own the reusable,
closed local shape of a physical-profile descriptor. The incorporated descriptor MUST satisfy that
schema, own the current profile's exact identifiers and assignments, and contain exactly these root
members:

- `$schema`, equal to `https://escapewheel.org/schemas/physical-profile/0.1.0`;
- `id`, equal to `escapewheel-portable-v0.1`;
- `logical_standard`, equal to `escapewheel-logical-v0.1`;
- `kind_interfaces`, a closed object governed by §3.2; and
- `interfaces`, a closed object governed by §§3.3–3.4.

Part 03 MUST define the semantics, cross-member invariants, and actor obligations for those
members. A generic profile checker MUST enforce those invariants without embedding this profile's
identifiers or assignments. The schema MUST validate member types, locally closed object shapes,
identifier syntax, and local cardinality; it MUST NOT hard-code the current profile ID, logical
standard ID, kind keys, interface keys, variants, ownership sequence, anchors, or floor members. A
rendered table of descriptor values MUST be an informative generated projection and MUST NOT become
a second edited authority.

Each descriptor interface and variant MUST carry a nonempty `anchors` array of distinct canonical
`ew-` identifiers. The generic checker MUST require every listed anchor to resolve uniquely in Part
03 to the clause that defines the entry's meaning.

An implementation that distributes the incorporated descriptor MUST validate its source or
vendored copy against the schema and generic checker at a packaging or equivalent conformance
boundary. It MAY cache that result. Opening or reading a packet MUST NOT require revalidating an
unchanged bundled descriptor.

### 3.2 Profile and logical kind derive the generic interface

For a packet whose `profile_id` is `escapewheel-portable-v0.1`, a reader, writer, validator, or
build MUST resolve each packet resource's checked logical declaration and apply this exact
`kind_interfaces` mapping:

| logical kind | interface |
|---|---|
| `table` | `parquet` |
| `dense_array` | `zarr` |
| `opaque` | none |

The mapping MUST be encoded in the descriptor as the strings `parquet` and `zarr` and JSON `null`
respectively. A packet resource entry MUST NOT select or repeat the derived interface. Declaration
ID, namespace, URI suffix, and directory placement MUST NOT act as alternative interface
selectors.

Part 03 MUST require the mapping keys to equal the logical standard's complete kind vocabulary,
every non-null mapped interface to exist exactly once in `interfaces`, and every declared interface
to be referenced by at least one kind. The generic checker MUST enforce those cross-artifact and
cross-member requirements. The current descriptor's interface names form the exact vocabulary for
this profile; an implementation MUST NOT substitute an unincorporated name.

### 3.3 The Parquet interface is one materialized object

The descriptor's `parquet` interface MUST declare:

- `realization: "materialized"`;
- `access: "logical_values"`;
- `resource_form: "single_object"`;
- `ownership: ["packet", "external"]` in that order;
- `floor_role: "reader_and_packet_writer"`;
- the `reader_floor` in this section; and
- `anchors: ["ew-table-encoding", "ew-parquet-reader-floor"]` in that order.

Every table resource under this profile MUST resolve to exactly one file or object containing one
valid Parquet file. A directory, prefix, glob, explicit member set, or multi-file dataset MUST NOT
realize a table under this profile. A writer MUST NOT emit one, and a validator that can inspect the
resource MUST reject one. No packet entry may declare partitioning or table layout.

The Parquet `reader_floor` MUST contain exactly:

- `compressions`: `UNCOMPRESSED`, `SNAPPY`, `GZIP`, and `ZSTD`;
- `encodings`: `PLAIN`, `RLE`, `RLE_DICTIONARY`, and `DELTA_BINARY_PACKED`;
- `data_page_types`: `DATA_PAGE` and `DATA_PAGE_V2`; and
- `encryption`: `none`.

A conforming reader MUST expose logical table values for every otherwise-valid current-profile
Parquet resource whose footer-reported compression and encodings are all members of the respective
floor arrays, whose data page headers use `DATA_PAGE` or `DATA_PAGE_V2`, and whose footer and
columns are not encrypted. A writer emitting a packet-owned table MUST use one of the four floor
compressions, every encoding reported by the written footer MUST be in the floor, every data page
MUST use one of the two floor page types, and neither its footer nor a column may use Parquet
modular encryption. The profile neither requires nor prefers one floor page type over the other. A
writer MUST configure the selected page type and absence of encryption before writing, inspect the
footer after writing, and refuse to commit a packet-owned table whose reported compression or
encoding is outside the floor.
`PLAIN_DICTIONARY` is a deprecated but valid upstream encoding and is not in this measured floor;
a packet writer therefore MUST NOT emit it. Neither the descriptor nor an implementation may use
`FileMetaData.version` as a substitute for checking these floor features. Existing Part 03 rules
for Parquet types, order, row groups, nulls, and the preference for Zstd remain in force.

### 3.4 The Zarr interface has metadata-discovered variants

The descriptor's `zarr` interface MUST declare:

- `realization: "materialized"`;
- `access: "logical_values"`;
- `resource_form: "prefix"`;
- `floor_role: "reader_only"`;
- variants `v3` and `v2`, in that order; and
- `anchors: ["ew-array-version", "ew-array-codecs"]` in that order.

A reader or validator MUST determine the variant from the Zarr metadata's `zarr_format` value when
it accesses or physically assesses the resource. A packet entry MUST NOT state the variant.

The `v3` variant MUST declare `format_version: 3`,
`ownership: ["packet", "external"]`,
`anchors: ["ew-array-version", "ew-array-codecs"]`, and a `reader_floor.codec_sequences` array
containing exactly these three ordered name sequences:

- `["bytes"]`;
- `["bytes", "gzip"]`; and
- `["bytes", "zstd"]`.

The `v2` variant MUST declare `format_version: 2`, `ownership: ["external"]`,
`anchors: ["ew-array-version", "ew-array-codecs"]`, and a `reader_floor.metadata_patterns` array
containing exactly these three patterns:

- `{"filters": null, "compressor": null}`;
- `{"filters": null, "compressor": {"id": "zstd"}}`; and
- `{"filters": null, "compressor": {"id": "blosc", "cname": "zstd"}}`.

No packet-owned resource MAY use the `v2` variant.

A conforming reader MUST expose logical dense-array values for every valid current-profile Zarr
resource whose codec sequence or metadata matches an applicable floor entry. A floor entry matches
the stated codec names and configuration discriminants. For a v2 pattern, JSON `null` matches only
JSON `null`, every stated object member must compare equal, and unmentioned configuration members
do not participate in the floor match. Other configuration members remain governed by the
applicable upstream Zarr or codec specification. The descriptor does not enumerate optional codecs.
A writer MAY use any codec permitted by the applicable Zarr specification, subject to the existing
prohibition on `transpose` and the current regular-chunk-grid rule.

Part 03's normative references MUST identify the official Zarr `zstd` extension specification as
the authority for that codec's metadata object and configuration, and RFC 8878 as the authority for
the encoded Zstandard frame. Part 03 MUST NOT cite a library implementation, including zarr-python
or Numcodecs, as the normative authority for that contract.

### 3.5 Floor role is declared per interface

An interface or variant's `reader_floor` MUST state only the physical features every conforming
profile reader supports for generic logical-value access. It MUST NOT enumerate recognized optional
features, assign global capability IDs, advertise one implementation's support, or define a packet
negotiation vocabulary.

Each interface MUST declare `floor_role` as `reader_and_packet_writer` or `reader_only`. For
`reader_and_packet_writer`, a writer emitting a packet-owned resource through that interface MUST
keep every floor-governed feature within the interface's `reader_floor`. For `reader_only`, the
floor imposes no writer ceiling; the writer remains bound by the interface's other profile rules
and the applicable upstream format.

An upstream feature absent from a `reader_only` floor is outside the profile's portability
guarantee. For an external resource, or for an interface whose `floor_role` is `reader_only`,
absence from the descriptor alone MUST NOT establish that the upstream representation is malformed
or decide packet conformance. An implementation MAY support additional upstream features without
changing the descriptor or packet. A later portability decision may change floor membership and
define standardized findings, severities, and verdict composition.

The physical-profile schema MUST close every locally defined floor object and require nonempty
arrays with no duplicate members. It MUST admit configuration discriminants only where Part 03
gives them floor semantics and MUST NOT copy the complete Parquet footer schema or Zarr codec
schemas. Part 03 MUST define sequence and pattern matching; a reader or validator comparing
resource metadata with the floor MUST apply those rules.

### 3.6 The packet does not project self-describing physical facts

`profile_id` MUST remain the packet's sole physical-profile selector. A manifest resource entry and
a referenced-resource delivery entry MUST NOT contain `physical_profile`, `partitioning`, or
`codecs`. A manifest root MUST NOT contain `required_codecs`. The incorporated manifest and
resource-delivery schemas MUST remove those properties, their enums, and every conditional branch
that exists only to govern them. The manifest schema MUST reject the removed properties. The
resource-delivery schema MUST reject them without otherwise closing an entry shape that the
extension mechanism deliberately leaves extensible.

No replacement per-resource interface, variant, layout, codec, capability-requirement, or
packet-capability-union field is introduced. Writer codec-selection and Parquet-encoding settings
MAY remain build inputs; they MUST NOT become packet claims merely because they affected output.

### 3.7 Ordinary packet access does not require validation

A reader MUST be able to open the packet catalog, resolve declarations, list resources, and select
a session without a validation receipt and without physically inspecting every resource. Session
scoping, declaration resolution, and discriminator resolution remain ordinary access operations;
they do not imply whole-packet physical validation.

Before exposing logical values from a selected table or dense array, a reader MUST inspect the
metadata needed to open that resource. If the representation uses a format version or feature the
reader does not support, the reader MUST fail that resource specifically and identify the missing
support. It MUST NOT refuse the packet merely because an unopened resource uses such a feature.

### 3.8 Physical assessment uses available resource metadata

A validator performing physical checks MUST derive interface variant and actual feature use from
the available resource's format-owned metadata. It MUST compare those observations with a
descriptor that has passed the schema and generic checker rather than with a packet claim or a
local duplicate floor constant. It need not revalidate that unchanged descriptor for each packet
or resource.

When an external resource is unavailable, the validator MUST report its physical assessment as
unassessed. It MUST NOT infer its variant, codec pipeline, compression, value encoding, dtype,
shape, or chunking from the URI, a packet field, an adapter claim, or a local stand-in.

A validator MUST distinguish upstream-format invalidity from use of a valid feature outside the
reader floor. This revision assigns no automatic profile violation merely because a valid upstream
feature is outside that floor. A later portability-reporting revision may standardize finding IDs,
severity, and summaries without changing the source of the observation or the meaning of the
floor.

### 3.9 Opaque representations remain open

An `opaque` logical resource MUST map to no generic physical interface. The descriptor MUST NOT
enumerate opaque formats, media containers, document serializations, codecs, or renderer
capabilities. Lack of a recognized payload format or specialized decoder MUST NOT by itself
invalidate the resource.

A generic reader MUST resolve and list an opaque resource and expose its catalog identity and
location. It need not integrity-check, retrieve, stream, parse, decode, render, or expose logical
values from the payload. Requested validation owns any integrity check the packet permits. A
specialized implementation MAY expose members, objects, bytes, parsing, rendering, or other
representation-aware operations without changing the resource's logical kind or the portable
reader floor.

### 3.10 Current profile interfaces are materialized

Every interface in the current descriptor MUST declare `realization: "materialized"`. Packet
ownership and external reference are ownership states and MUST NOT be represented as realization
kinds. The descriptor MUST NOT declare a view interface until a profile defines a view language,
serialized definition, input binding, and evaluation contract.

A view created by a reader or analysis system over packet resources is an operation and MUST NOT be
treated as an independently declared packet resource solely because the operation exists.

### 3.11 Logical facts and physical metadata keep separate owners

Logical and scientific facts required for validation MUST remain in the logical resources or
packet fields that own them and MUST NOT be reachable only through optional Zarr attributes.
Self-describing physical facts—including Zarr version, shape, dtype, chunking, and codec
configuration, and Parquet compression and value encoding—MUST be obtained from the resource and
MUST NOT be duplicated merely to make physical validation possible.

An adapter delivering a packet-owned array MUST continue to write its bytes at the build-supplied
location. An adapter delivering an external resource MUST continue to supply its resource identity,
logical declaration, and location. A build MUST inspect reachable output as needed and MUST NOT
require the adapter to restate a Zarr version, codec pipeline, Parquet layout, or other
self-describing physical fact in its delivery document.

## 4. What this does not change

This revision makes the measured current Parquet and Zarr reader-floor membership exact enough to
compare with format metadata. The Parquet family names become the modern upstream encoding enum
members the probes exercise; the Zarr pseudo-codec `none` becomes the actual v3 codec sequence or
v2 metadata pattern. A later revision may reconsider membership and standardize portability
findings without changing the descriptor architecture.

The Parquet floor is both a reader minimum and a packet-owned writer ceiling. The Zarr floor is a
reader minimum only. This preserves tables as the universally readable query substrate while
allowing dense-array payloads to use valid Zarr features that a reader may decline per resource.

This revision does not change logical resource declarations, axes semantics, Parquet logical types,
stored-order rules, Zarr axis order, chunk-grid requirements, packet integrity fields, or external
source resolution. It does not define immutable membership or cross-file ordering for a future
partitioned-table interface.

An optional open media-type or format hint may later improve discovery of opaque resources. Such a
hint would be informative, would not select a generic interface, and would not make an unrecognized
opaque representation invalid.

## 5. Consequence

Existing development packets and delivery documents are incompatible and must be regenerated.
Independent implementations must consume identical copies of the incorporated descriptor and
schema. The Python packages may keep one bundled copy in the reader package and share its checked,
cached projection through their existing dependency graph rather than maintain three vendored
copies. The generator must render profile tables from the descriptor, and implementation constants
that independently state the mapping or floor must be removed or reduced to checked projections.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | unchanged; resource meaning does not depend on storage interface or reader floor | specification diff and semantic-part verifier |
| logical prose and registry | unchanged; checked declarations supply only `table`, `dense_array`, or `opaque` to this decision | registry validation and cross-package descriptor tests |
| physical profiles | incorporate the closed local-shape schema and current descriptor; define derivation, cross-member invariants, resource forms, variants, per-interface floor role, metadata ownership, and materialized-only realization; add the official Zarr `zstd` extension reference | descriptor-schema and generic-checker validation, anchor check, and generated-table comparison |
| packet catalog and JSON Schemas | remove `physical_profile`, `partitioning`, `codecs`, and `required_codecs` without replacement fields | positive minimal manifests and negative fixtures containing each retired property |
| validation and import | derive the interface from checked kind, inspect available resource metadata, compare it with the descriptor, and preserve unassessed external state | focused validator tests for every interface, variant, ownership state, and unavailable resource |
| extensions | unchanged in shape; extension resources use the same kind mapping without extension code or physical declarations | extension registry and packet fixtures for table, dense-array, and opaque declarations |
| reader, writer, validator, adapters | consume one checked descriptor projection per implementation distribution; remove duplicated selectors and floor sets; keep inspection lazy; emit one-object tables whose footer features remain within the floor; leave Zarr codec choice open; stop requiring adapter codec claims | package tests and cross-package end-to-end builds |
| conformance fixtures and tests | regenerate packet shapes and cover floor, outside-floor, bad variant ownership, table prefix, arbitrary opaque representation, and per-resource failure cases | fixture suite and repository verifier |
| revision process and tooling | unchanged; the ordinary specification lifecycle and ledger apply | lifecycle scripts |
| generated publications and developer documentation | render descriptor facts, update packet examples and API guidance, and explain that normal reads require no validation receipt | clean regeneration and documentation checks |

## 6. Conformance and implementation evidence

Incorporation must establish at least these positive cases:

- the source descriptor satisfies its local-shape schema and every cross-member invariant, and
  every distributed copy is byte-identical to it;
- an implementation validates a distributed descriptor at its packaging or first-use conformance
  boundary, caches the result, and does not repeat that check for each packet or resource;
- one packet-owned and one external single-object Parquet table derive the `parquet` interface;
- every packet-owned table emitted by the writer reports only floor compression and encoding
  enums, is configured to use `DATA_PAGE` or `DATA_PAGE_V2`, and is configured without Parquet
  modular encryption;
- otherwise-equivalent `DATA_PAGE` and `DATA_PAGE_V2` tables both expose the same logical values
  through every conforming reader;
- packet-owned Zarr v3 and external Zarr v2 and v3 arrays derive `zarr`, discover their variants
  from metadata, and read with every applicable floor entry;
- an extension table, dense array, and opaque resource use the same mapping without extension code;
- an opaque resource with an unrecognized representation remains resolvable and listable with its
  catalog identity and location, without requiring byte access;
- an unavailable external resource remains physically unassessed; and
- opening and session-scoping a packet do not inspect every resource or require a validation
  receipt.

It must also establish these negative or boundary cases:

- the descriptor schema rejects a malformed identifier, ownership state, floor-pattern shape,
  duplicate local-array member, or extra local property, while the generic checker rejects an
  incomplete or unknown kind mapping, an unreferenced or unresolved interface, or an
  unresolved/non-unique anchor;
- real Parquet footer enum values and real Zarr v2 and v3 metadata match every floor entry, while
  deprecated `PLAIN_DICTIONARY` and valid features outside the floor do not match merely by family;
- a packet writer refuses a packet-owned table whose footer reports an outside-floor compression
  or encoding; its configuration cannot select an unrecognized data-page type, an encrypted
  footer, or an encrypted column; and it may emit a valid packet-owned Zarr v3 array whose codec
  pipeline is outside the reader floor;
- the packet and delivery schemas reject each retired physical field;
- a table URI resolving to a prefix or multiple Parquet objects is rejected;
- a packet-owned Zarr v2 resource is rejected after its metadata is inspected;
- malformed upstream Parquet or Zarr metadata is distinguished from a valid feature outside the
  reader floor;
- lack of support for one selected resource fails that resource without rejecting unopened
  resources; and
- no reader, writer, or validator maintains an unchecked copy of the profile mapping or floor.

The incorporation evidence must include descriptor generation and vendoring checks, focused package
tests, regenerated fixtures, the full repository verifier, and a diff proving that generated
specification tables agree with the descriptor.

### 6.1 Completed anchor bootstrap

Commit `a52e4fc56dbbf7dd6be4d7d64145404b1c838b5d` added one canonical anchor immediately
before each of these affected existing headings:

| current heading | canonical anchor |
|---|---|
| Part 00 §7.2 | `ew-external-resource-referencing` |
| Part 03 §2 | `ew-portable-profile-technologies` |
| Part 03 §5.1 | `ew-table-encoding` |
| Part 03 §5.2 | `ew-table-partitioning` |
| Part 03 §5.5 | `ew-parquet-reader-floor` |
| Part 03 §6.1 | `ew-array-version` |
| Part 03 §6.4 | `ew-array-codecs` |
| Part 04 §5.3 | `ew-external-resource-verification` |
| Part 04 §6 | `ew-packet-codecs` |
| Part 04 §6.1 | `ew-resource-codecs` |
| Part 04 §6.2 | `ew-packet-codec-union` |

The other affected existing headings already had canonical anchors. The metadata-only comparator
found no change other than these eleven insertions. New destination headings receive their anchors
when created. This draft's baseline, impact scan, citation inventory, generated heading index, and
combined rendering were refreshed against the bootstrap commit.

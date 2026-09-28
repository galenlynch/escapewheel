# Part 04 — Packet Manifest

Normative.

<a id="ew-packet-catalog-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines the packet manifest: the document that binds each concrete packet resource to one
logical declaration in a bound registry and to its location. In the portable profile it is
`packet.json` at the packet root.

This part incorporates `registry/manifest.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/manifest/0.5.0`. The schema owns the manifest's exact local JSON
structure: member names, JSON types, required members, object closure, patterns, enumerations,
formats, and conditional shape within one entry. This prose owns every field's meaning,
declaration-selected presence, and the checks of §10. A disagreement between this part and the
incorporated schema makes the specification candidate internally inconsistent. The field tables in
§§3, 4.1, 8, and 9 are informative projections of the schema.

Its requirements directly invoke the shared JSON, URI, JSON Schema, and RFC 1952 authorities
identified in [Part 00 §9](00_architecture.md#ew-normative-references) and the SHA-256, CRC64NVME,
and CRC32C authorities identified in [Part 04 §11](#ew-packet-catalog-normative-references). The
application columns in those sections state their extent.

<a id="ew-packet-catalog-principles" data-spec-anchor="canonical"></a>
## 2. Principles

The manifest is the packet's map. A reader MUST resolve resources through it and MUST NOT infer them from file layout.

The manifest binds every resource instance. Part 02's declaration supplies logical content class,
kind, canonicality, instance mode, presence, table contract, and lineage policy; the packet
entry supplies instance and location facts. Part 03 derives a generic interface from the selected
profile and logical kind, while the resource owns self-describing physical metadata. An Iceberg catalog manages only tabular resources and
therefore does not replace the packet manifest.

The manifest identifies by name. `packet_id`, every registry ID, every entry's `resource_id`, and
the session list hold names rather than assigned numbers, because the manifest is read before any
table and a number resolves against nothing.

<a id="ew-packet-identifiers" data-spec-anchor="canonical"></a>
## 3. Required top-level fields

The manifest records the semantic-standard identifier owned by Part 01, the logical-standard
identifier owned by Part 02, the bound registries of §8, and the physical-profile identifier owned
by Part 03. The fields below record those identifiers; they do not redefine their values or
meaning. Every object the incorporated schema declares is closed, so a manifest MUST NOT carry a
member the schema does not declare. [Part 05 §15.5](05_validation_and_import.md#ew-packet-cleanup) owns the meaning of `retention`.

<!-- BEGIN GENERATED MANIFEST FIELDS: manifest -->
| member | JSON type | required | constraint |
|---|---|:---:|---|
| `packet_id` | string | yes | nonempty |
| `packet_version` | string | yes | pattern `^\d+\.\d+\.\d+$` |
| `profile_id` | string | yes | `escapewheel-portable-v0.1` |
| `semantic_standard_version` | string | yes | — |
| `logical_standard_version` | string | yes | — |
| `registries` | object of registry descriptor (§8) | yes | at least one member; member names match `^[a-z][a-z0-9_]*$` |
| `created_at` | string | yes | format `date-time` |
| `sessions` | array of string | yes | nonempty; unique items |
| `resources` | array of resource entry (§4.1) | yes | — |
| `validation` | validation block (§9) | yes | — |
| `description` | string | no | — |
| `retention` | object | no | — |
<!-- END GENERATED MANIFEST FIELDS: manifest -->

## 4. Resource entries

<a id="ew-packet-resource-entry-fields" data-spec-anchor="canonical"></a>
### 4.1 Common fields

<!-- BEGIN GENERATED MANIFEST FIELDS: resource -->
| member | JSON type | required | constraint |
|---|---|:---:|---|
| `resource_id` | string | yes | pattern `^[a-z][a-z0-9_]*\.[a-z0-9_.-]+$` |
| `declaration_id` | string | yes | pattern `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` |
| `uri` | string | yes | nonempty |
| `validation_state` | string | yes | one of `passed`, `failed`, `not_run` |
| `external` | boolean | no | — |
| `source` | string | no | nonempty |
| `digest` | digest (§4.3) | no | — |
| `size_bytes` | integer | no | at least 0 |
| `verified_at` | string | no | format `date-time` |
| `members` | array of member (§5.4) | no | nonempty |
| `derived_from` | array of string | no | nonempty; unique items; each item pattern `^[a-z][a-z0-9_]*\.[a-z0-9_.-]+$` |
<!-- END GENERATED MANIFEST FIELDS: resource -->

`derived_from` follows the declaration's lineage policy (§7), `external` and `source` follow §5,
and `members` follows §5.4. `digest` follows [§4.3](#ew-resource-digests), which states when a
writer records one, and
[Part 03 §10](03_portable_physical_profile.md#ew-owned-resource-digests) states what a portable
resource's digest covers.

<a id="ew-logical-resource-kinds" data-spec-anchor="canonical"></a>
### 4.2 Resolved logical facts

The checked declaration named by `declaration_id` supplies the entry's owning registry, content
class, logical kind, instance mode, canonicality, table contract where applicable, presence, and
lineage policy. A reader, writer, or validator MUST NOT infer a declaration
from URI, directory placement, namespace alone, or logical kind.

A singleton entry's `resource_id` equals its declaration ID. A catalog entry binds through the
catalog row's `resource_id` under Part 02 §2.6. A family entry uses a packet-unique dotted resource
ID in a namespace its declaration's registry owns. An unknown declaration or inadmissible instance
binding makes a conformance claim invalid.

<a id="ew-resource-digests" data-spec-anchor="canonical"></a>
### 4.3 Resource digests

An entry's `digest` records a digest of the resource's bytes and names the function that produced
it, its **algorithm**, which is one of:

| algorithm | function | authority | single-object width |
|---|---|---|---|
| `sha256` | SHA-256 | FIPS 180-4 | 64 digits |
| `crc64nvme` | the NVMe 64-bit CRC | NVM Express NVM Command Set Specification, §5.3.1.3 | 16 digits |
| `crc32c` | CRC32C | RFC 9260, Appendix A | 8 digits |
| `crc32` | the gzip CRC-32 | RFC 1952, §8 | 8 digits |

[Part 04 §11](#ew-packet-catalog-normative-references) identifies the editions of FIPS 180-4, the
NVM Command Set Specification, RFC 9260, and RFC 8785, and
[Part 00 §9](00_architecture.md#ew-normative-references) that of RFC 1952.

A single object's digest value is the function of the object's bytes, written as lowercase
hexadecimal of exactly the width above, most significant digit first. For a CRC, the digits are the
checksum as an unsigned integer. The value of the nine ASCII bytes `123456789` is
`15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225` under `sha256`,
`ae8b14860a799888` under `crc64nvme`, `e3069283` under `crc32c`, and `cbf43926` under `crc32`.

A resource whose URI names a prefix holds one or more objects. A prefix holding none does not
exist, and a validator reports it as it reports a resource that does not exist.

A prefix's digest value is the SHA-256 of the UTF-8 encoding of
`[["<key>",<size>,"<value>"], ...]`, where each `<value>` is that object's digest value under the
resource's algorithm. The listing is compact JSON with `,` and `:` separators and no whitespace,
with one entry per object, sorted by the bytes of each key's UTF-8 encoding. A key, and a member's
`key` (§5.4), is the object's path relative to the resource's location: its names as they are,
joined by `/`, and never percent-encoded. Each key is a string serialized under RFC 8785, Section
3.2.2.2: `"` and `\` as `\"` and `\\`; U+0008, U+0009, U+000A, U+000C, and U+000D as `\b`, `\t`,
`\n`, `\f`, and `\r`; every other code point from U+0000 through U+001F as `\u` followed by four
lowercase hexadecimal digits; and every other code point as itself. Each size is a JSON integer with
no sign, fraction, or exponent, and no leading zero unless the size is zero, which is written `0`. A
prefix's value therefore has 64 digits under every algorithm. `size_bytes` is the sum of the
objects' sizes.

Sorting the keys is what makes the value reproducible without knowing the store, since two
implementations enumerate an object-store prefix and a local directory in different orders.
Listing each object's key beside its own value means a chunk moving between keys, which makes a
different Zarr array, changes the resource's value.

A writer MUST record a `digest` for every resource the packet owns, and MAY record it under any
admitted algorithm. An external resource's `digest` is optional, and §5.2 states what a writer
records about a URI it cannot reach. A checker reports `packet.resource.digest_missing` (§10) for
each entry that does not declare `external: true` and records no `digest`.

## 5. External resources

### 5.1 Declaration

A resource the packet does not own MUST set `external: true`. A resource whose `uri` is absolute MUST declare `external: true`; **the converse does not hold**, so a packet MAY declare a resource external and still resolve it relatively, which is how a packet published beside its data records that it does not own it.

Referencing is expected for large resources. Externalizing a table costs more than externalizing an array: its validation rules cannot run at all while it is unreachable.

<a id="ew-external-resource-record" data-spec-anchor="canonical"></a>
### 5.2 What is recorded

`digest`, `size_bytes`, and `verified_at` record what was true when the resource was checked. They are not a claim about now.

A writer that cannot reach a URI MUST record nothing rather than copying a value from a local stand-in.

<a id="ew-external-resource-verification" data-spec-anchor="canonical"></a>
### 5.3 Verification levels

Verification of an external resource is layered, and a report MUST state which level it reached.

| level | establishes |
|---|---|
| 1 | the manifest is internally consistent |
| 2 | packet-owned resources' recorded digests hold |
| 3a | the external resource exists and lists |
| 3b | its recorded per-member store digests still match |
| 3c | its recorded `digest` holds |

Structural validation MUST NOT reach the network. Levels 3a to 3c run only in a requested mode.

A validator establishes that a recorded digest holds by computing it from the bytes under §4.3. A
validator MAY instead establish it by comparing it with checksums the store reports, object by
object. A store's checksum counts only where the store reports it as a full-object value in the
resource's algorithm; a validator MUST NOT compare a composite value, and MUST read any object for
which the store reports no full-object value. For a single object it compares the store's value,
converted to §4.3's form, with the recorded value. For a prefix it builds §4.3's listing from those
values and compares its SHA-256.

A report MUST state, for each digest it establishes, whether the validator computed it, matched the
store's checksums, or combined the two. Level 2 establishes that packet-owned resources' recorded
digests hold, and level 3c that an external resource's recorded digest holds, each reached by
either route. Level 3b remains the comparison of recorded store digests (§5.4).
When an external resource is unavailable, its physical version, codec pipeline, compression,
encoding, dtype, shape, and chunking are unassessed; a validator MUST NOT infer them from its URI,
the packet, an adapter claim, or a stand-in.

<a id="ew-prefix-resources" data-spec-anchor="canonical"></a>
### 5.4 Prefix resources

Where a resource is a prefix rather than a single object — an external store, a packet-owned Zarr array, or a packet-owned opaque resource whose payload is a directory ([Part 03 §11](03_portable_physical_profile.md#ew-opaque-storage)) — its `digest` and `size_bytes` are defined over its objects by [§4.3](#ew-resource-digests).

Such a resource MAY additionally declare a `members` array recording what was seen, one member per object. A member records its object's single-object value as `digest`, a string under its entry's algorithm, and MAY carry a `store_digest`. The incorporated schema requires every member to record `digest` where its entry records one, and forbids a member recording one where its entry does not. Carrying each member's own value is what lets a consumer that fetched three chunks verify those three without the other two hundred.

A member array is a record, not a resolution rule: a reader hands the prefix to the array library and does not enumerate it.

Where `members` accompanies `digest`, the listing digested MUST be the declared one, so the enumeration and the digest cannot disagree.

A member's `store_digest` records evidence that an object changed in place. A writer MUST record a store's entity tag, where it records one, verbatim under the algorithm `etag`, whether the object was uploaded in one part or several and whatever its encryption. A writer MUST NOT record an entity tag under any other algorithm name, and a validator MUST NOT read one as a digest of the object's bytes.

Where a validator is asked to verify content **without reading**, it compares each member's recorded `store_digest` against the value the store reports now — a third level between listing and reading. A member whose value differs has changed; a member with no recorded `store_digest`, or whose store reports none, is **not checked**, and the report MUST say how many were skipped.

A store digest answers whether anything changed in place. It never establishes that a `digest` holds, and it is unstable across a copy. A validator MUST report what a verification pass skipped, and **MUST NOT** report a store-digest pass as a checksum verification: it establishes something weaker and store-specific, so it gets its own finding.

<a id="ew-source-resolution" data-spec-anchor="canonical"></a>
### 5.5 Source resolution

An external resource entry MAY carry `source`, an identifier naming the body of data it belongs to;
its `uri` is then a relative reference resolved against wherever that source is
([Part 03 §4](03_portable_physical_profile.md#ew-portable-uri-rules)), and neither field is a
location. An
entry carrying no `source` keeps the meaning §5.1 gives it.

Where a source is, is stated by a **source resolution document**: a JSON document, conventionally
`sources.json`, carrying `sources_standard_version` and a `sources` object mapping each source name
to an entry with a required `uri`. This section incorporates `registry/sources.schema.json`, whose
`$id` is `https://escapewheel.org/schemas/sources/0.1.0`, as the exact shape of a source resolution
document. The schema owns member names, JSON types, required members, closure, patterns, and the
version constant; this prose owns what each member means. The schema's descriptions are
informative. A source name is any string an external resource entry's `source` can hold.

A resolution document MUST NOT be a packet resource. Immutability (§5.1) does not reach
it, which is what lets a location be corrected when a mirror moves without rebuilding the packet.

A reader MUST accept one or more resolution documents from its caller, and resolves a `source` in
this order: the documents the caller supplied, in the order supplied; then `sources.json` at the
packet root if it is there; then the source is unresolved. A writer SHOULD write that default.

A writer that writes a resolution document MUST write one that satisfies the schema. A reader MAY
validate a resolution document against the schema, and need not. A reader MUST NOT resolve a source
through a document whose `sources_standard_version` it does not know.

A reader MUST report an unresolved `source` as unresolved, and a validator MUST NOT fail structural validation for one:
which mirrors a reader can reach is a property of the reader. Structural validation MUST NOT
require a resolution document.

A consumer MUST NOT read resolution through a different document as invalidating a recorded `digest`,
`size_bytes` or `members`. Where a reader verifies a resolved source and finds a mismatch, it MUST
report it against the resource entry, and MUST NOT silently prefer either the recorded digest or
the bytes it found.

<a id="ew-packet-codecs" data-spec-anchor="canonical"></a>
## 6. Physical metadata is not projected

`profile_id` is the manifest's sole physical-profile selector. Generic interfaces derive under Part
03, and resource-owned metadata supplies actual versions, layouts, compression, encodings, and
codec pipelines. The manifest carries no replacement capability union or per-resource selector.

<a id="ew-resource-lineage" data-spec-anchor="canonical"></a>
## 7. Resource lineage

The declaration's `lineage` policy, which Part 02 §2.7 defines, governs `derived_from` for every
logical kind. A present `derived_from` is a nonempty array of distinct existing packet resource IDs
and obeys that section's content-class relation and acyclic graph rule.

An entry names no producing run. Provenance resides in `core.source_files`,
`core.processing_runs`, and `core.processing_run_inputs`, and the manifest records outputs at
resource granularity only. [Part 06 §5](06_analysis_layer.md#ew-analysis-materialization-provenance)
owns when a writer records the run that materialized an analysis resource.

<a id="ew-packet-registry-bindings" data-spec-anchor="canonical"></a>
## 8. Registry bindings

The root member `registries` binds the registry documents that declare the packet's resources.
Each member name is a registry ID under
[Part 02 §9.1](02_core_logical_schemas.md#ew-registry-document), and each value is a closed
registry descriptor:

<!-- BEGIN GENERATED MANIFEST FIELDS: registry -->
| member | JSON type | required | constraint |
|---|---|:---:|---|
| `role` | string | yes | one of `core`, `extension` |
| `version` | string | yes | pattern `^\d+\.\d+\.\d+$` |
| `path` | string | yes | pattern `^(?![A-Za-z][A-Za-z0-9+.-]*:)(?!\.{1,2}(?:/\|$))(?!.*/\.{1,2}(?:/\|$))[^/\\]+(?:/[^/\\]+)*$` |
| `sha256` | string | yes | pattern `^[0-9a-f]{64}$` |
<!-- END GENERATED MANIFEST FIELDS: registry -->

A descriptor's `path` is a relative reference to a location under the packet root: one or more
nonempty segments separated by `/`, with no scheme, no leading `/`, no `\`, and no segment equal
to `.` or `..`. Its `sha256` is the SHA-256 digest of the exact bytes of the registry document,
without decoding, re-serialization, or any other canonicalization. The packet's physical profile
owns how those bytes are stored;
[Part 03 §3.3](03_portable_physical_profile.md#ew-portable-bound-registries) owns the portable
profile's storage.

A manifest MUST contain exactly one descriptor with role `core` and MUST NOT give two descriptors
the same `path`. The document at a descriptor's path MUST:

- carry `registry_id` equal to the descriptor's member name;
- be a core registry exactly when the descriptor's role is `core`;
- carry `registry_version` equal to the descriptor's `version`; and
- carry `logical_standard_version` equal to the manifest's, and, for the core registry,
  `semantic_standard_version` equal to the manifest's.

A packet MUST bind the core registry and every extension registry that declares one of its
resources. Binding an extension registry activates its required declarations under
[Part 02 §2.5](02_core_logical_schemas.md#ew-resource-presence). Every `declaration_id` resolves
only in the bound registries.

<a id="ew-packet-validation-block" data-spec-anchor="canonical"></a>
## 9. Validation block

<!-- BEGIN GENERATED MANIFEST FIELDS: validation -->
| member | JSON type | required | constraint |
|---|---|:---:|---|
| `status` | string | yes | one of `passed`, `failed`, `not_run` |
| `validated_at` | string | yes | format `date-time` |
| `validator_name` | string | yes | — |
| `validator_version` | string | yes | — |
<!-- END GENERATED MANIFEST FIELDS: validation -->

A failed or incomplete validation result cannot support a conformance claim. It does not alter a
resource's declaration-derived content class or canonicality.
[Part 05 §9.2](05_validation_and_import.md#ew-error-policy) permits only `passed` as the `status` of
a published manifest. A writer keeps staged resources out
of a committed manifest until the applicable publication gate passes rather than representing
staging by changing canonicality.

<a id="ew-packet-manifest-conformance" data-spec-anchor="canonical"></a>
## 10. Manifest conformance

A checker evaluates manifest conformance in these phases, in order:

1. `json`, which decodes the manifest as UTF-8 JSON under RFC 8259;
2. `shape`, which validates it against the incorporated schema;
3. `entries`, which runs checks that need only the manifest;
4. `registry_binding`, which acquires and compares every bound registry; and
5. `declaration`, which runs checks derived from the bound declarations.

A checker MUST NOT run a later phase over a manifest with a finding in `json`, `shape`, or
`entries`. A checker evaluating manifest shape MUST assert the `date-time` format that JSON Schema
Validation Draft 2020-12 defines. A shape finding carries the check ID `packet.manifest.schema`
and the schema-location pointer. Every finding in the table below is at `error` and names the
owning resource ID or registry ID where one applies.

| check ID | phase | a finding exists when |
|---|---|---|
| `packet.manifest.invalid_json` | json | the bytes are not UTF-8 or not JSON |
| `packet.manifest.duplicate_member` | json | an object repeats a member name |
| `packet.manifest.schema` | shape | the manifest violates the incorporated schema |
| `packet.resource.id_unique` | entries | two entries share a `resource_id` |
| `packet.resource.member_unique` | entries | two members of one entry share a `key` |
| `packet.resource.member_size` | entries | an entry with `members` records `size_bytes` unequal to the sum of the members' sizes |
| `packet.resource.member_digest` | entries | an entry records `digest` and `members`, and its value differs from the §4.3 value of that member list |
| `packet.resource.digest_missing` | entries | an entry that does not declare `external: true` records no `digest` |
| `packet.resource.uri_form` | entries | an entry's `uri` is neither absolute nor a relative reference in the one form of [Part 03 §4](03_portable_physical_profile.md#ew-portable-uri-rules) |
| `packet.registry.core_count` | entries | the number of core descriptors differs from one |
| `packet.registry.path_unique` | entries | two descriptors share a `path` |
| `packet.registry.missing` | registry_binding | nothing exists at a descriptor's path |
| `packet.registry.unreadable` | registry_binding | the stored copy does not decode as the packet's physical profile requires |
| `packet.registry.digest` | registry_binding | the decoded bytes' SHA-256 differs from `sha256` |
| `packet.registry.identity` | registry_binding | the document's `registry_id` differs from the descriptor's name |
| `packet.registry.role` | registry_binding | the document's class differs from the descriptor's role |
| `packet.registry.version` | registry_binding | the document's `registry_version` differs from `version` |
| `packet.registry.standard` | registry_binding | a standard identifier differs from the manifest's under §8 |
| `packet.resource.declaration_unknown` | declaration | `declaration_id` names no declaration in a bound registry |
| `packet.resource.singleton_identity` | declaration | a singleton entry's `resource_id` differs from its declaration ID |
| `packet.resource.family_namespace` | declaration | a family entry's `resource_id` lies outside its declaration's namespace |
| `packet.resource.required_missing` | declaration | an active required singleton has no entry |
| `packet.resource.dependency_missing` | declaration | a present declaration's transitive `requires` names an absent singleton |
| `packet.resource.array_axes_missing` | declaration | a dense-array entry's axes resource is absent |
| `packet.resource.reference_target_missing` | declaration | a populated table reference targets an absent singleton |
| `packet.resource.catalog_table_unreadable` | declaration | a catalog table's resource-ID column cannot be read |
| `packet.resource.catalog_row_binding` | declaration | a catalog row and a family entry do not bind one-to-one under Part 02 §2.6 |
| `packet.resource.derived_from_required` | declaration | the `lineage` policy is `required` and `derived_from` is absent |
| `packet.resource.derived_from_forbidden` | declaration | the `lineage` policy is `forbidden` and `derived_from` is present |
| `packet.resource.lineage_unresolved` | declaration | a `derived_from` member names no entry with a bound declaration |
| `packet.resource.lineage_class` | declaration | a lineage edge violates Part 02 §2.7's content-class relation |
| `packet.resource.lineage_cycle` | declaration | the lineage graph has a self-edge or cycle |

In the `registry_binding` phase, a checker MUST evaluate `missing`, `unreadable`, and `digest`
first. Only for decoded bytes that match the digest does it then obtain the
[Part 02 §9.4](02_core_logical_schemas.md#ew-registry-conformance) registry result through the
byte-oriented entry point, supplying the core context to every extension, and evaluate the four
comparison checks for each shape-valid document. The `declaration` phase runs only from checked
contexts that [Part 05 §14.5](05_validation_and_import.md#ew-validator-registry-boundary) permits
to direct packet checks.

A binding finding for an extension registry withholds only that registry. The `declaration` phase
MUST run from every bound registry that passed binding, and a checker MUST NOT report a
declaration finding for an entry whose `declaration_id` namespace is the ID of an extension
registry that failed. A failed core registry withholds the whole `declaration` phase, because every
extension's checked context needs core.
[Part 05 §9.5](05_validation_and_import.md#ew-verdict-composition) attributes each finding and
composes the verdicts.

A reader loading a manifest MUST decode it as UTF-8 JSON, MUST reject a repeated object member, and
MUST reject a repeated `resource_id` before it builds a lookup by resource ID or exposes an entry.
It MUST check the JSON type of each member it reads and fail naming a member that is absent where
the schema requires it or has the wrong type. A reader need not apply the incorporated schema or
assert its closure, patterns, or formats. A reader MAY expose the decoded JSON of a rejected
manifest as raw data but MUST NOT resolve declarations or resources through it.

A reader resolving a declaration MUST acquire the bound registry that declares it through its
descriptor, decode it as the packet's physical profile requires, and verify its digest. When the
registry is missing, unreadable, or fails the digest, the reader MUST fail the operation that needed
it and name the registry ID. It MUST NOT substitute other bytes or silently omit a bound registry.
Operations that need no such declaration proceed, and a reader need not run any other manifest check
or obtain a registry result for ordinary access.

A writer MUST serialize each registry document, compute its digest over those exact bytes, store it
as the packet's physical profile requires, and record its descriptor before writing the final
manifest. A writer MUST NOT publish a manifest with a finding in the `json`, `shape`, `entries`, or
`registry_binding` phase, and publishes any manifest only as
[Part 05 §9.2](05_validation_and_import.md#ew-error-policy) permits.

<a id="ew-packet-catalog-normative-references" data-spec-anchor="canonical"></a>
## 11. Normative references

The application column states the extent to which this part invokes each external authority:

| reference | candidate edition | application |
|---|---|---|
| [NIST FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) | exact | SHA-256 |
| [NVM Express NVM Command Set Specification, Revision 1.2](https://nvmexpress.org/specifications/) | exact | CRC64NVME (§5.3.1.3) |
| [RFC 9260](https://www.rfc-editor.org/info/rfc9260) | exact | CRC32C (Appendix A) |
| [RFC 8785](https://www.rfc-editor.org/info/rfc8785) | exact | the serialization of a prefix listing's keys (§4.3), Section 3.2.2.2 |

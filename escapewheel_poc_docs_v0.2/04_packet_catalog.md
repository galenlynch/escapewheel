# Part 04 — Packet Manifest

Normative.

<a id="ew-packet-catalog-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines the packet manifest: the document that binds each concrete packet resource to one
logical declaration in a checked registry context and to its location. In the portable profile it
is `packet.json` at the packet root.

Its requirements directly invoke the shared JSON and URI authorities identified in
[Part 00 §10](00_architecture.md#ew-normative-references) and the SHA-256 authority identified in
[Part 04 §10](#ew-packet-catalog-normative-references). The application columns in those sections
state their extent.

<a id="ew-packet-catalog-principles" data-spec-anchor="canonical"></a>
## 2. Principles

The manifest is the packet's map. A reader MUST resolve resources through it and MUST NOT infer them from file layout.

The manifest binds every resource instance. Part 02's declaration supplies logical content class,
kind, canonicality, instance mode, presence, table contract, and provenance policy; the packet
entry supplies instance and location facts. Part 03 derives a generic interface from the selected
profile and logical kind, while the resource owns self-describing physical metadata. An Iceberg catalog manages only tabular resources and
therefore does not replace the packet manifest.

The manifest identifies by name. `packet_id`, every entry's `resource_id`, the session list, and a resource's `processing_run_id` hold names rather than assigned numbers, because the manifest is read before any table and a number resolves against nothing.

<a id="ew-packet-identifiers" data-spec-anchor="canonical"></a>
## 3. Required top-level fields

The manifest records the semantic-standard identifier owned by Part 01, the logical-standard and
registry identifiers owned by Part 02, and the physical-profile identifier owned by Part 03. The
fields below record those identifiers; they do not redefine their values or meaning.

| field | type | requirement |
|---|---|---|
| `packet_id` | string | MUST |
| `packet_version` | string | MUST |
| `profile_id` | string | MUST |
| `semantic_standard_version` | string | MUST |
| `logical_standard_version` | string | MUST |
| `registry_version` | string | MUST |
| `created_at` | timestamp | MUST |
| `sessions` | array of string | MUST |
| `resources` | array of entry | MUST |
| `validation` | object | MUST |
| `extensions` | object | where extensions are present (§8) |
| `description` | string | MAY |

## 4. Resource entries

<a id="ew-packet-resource-entry-fields" data-spec-anchor="canonical"></a>
### 4.1 Common fields

| field | type | requirement |
|---|---|---|
| `resource_id` | string | MUST, dotted and namespaced |
| `declaration_id` | string | MUST, names a visible checked logical declaration |
| `uri` | string | MUST |
| `validation_state` | string | MUST |
| `sha256` | string | SHOULD for a packet-owned resource |
| `external` | bool | MUST where true (§5) |
| `source` | string | MAY, on an external entry (§5.5) |
| `derived_from` | array of string | according to the declaration's `lineage` policy (§7) |
| `processing_run_id` | string | according to the declaration's `producing_run` policy (§7) |

An entry MUST NOT contain `layer`, `kind`, `canonical`, `schema_id`, `extension_id`,
`catalog_table_ref`, `array_asset_id`, `media_asset_id`, `physical_profile`, `partitioning`, or
`codecs`. The top-level `extensions` map remains
the packet's extension-registry selection.

<a id="ew-logical-resource-kinds" data-spec-anchor="canonical"></a>
### 4.2 Resolved logical facts

The checked declaration named by `declaration_id` supplies the entry's owning registry, content
class, logical kind, instance mode, canonicality, table contract where applicable, presence,
lineage, and producing-run policy. A reader, writer, or validator MUST NOT infer a declaration
from URI, directory placement, namespace alone, or logical kind.

A singleton entry's `resource_id` equals its declaration ID. A catalog entry binds through the
catalog row's `resource_id` under Part 02 §2.6. A family entry uses a packet-unique dotted resource
ID in a namespace its declaration's registry owns. An unknown declaration or inadmissible instance
binding makes a conformance claim invalid.

<a id="ew-withdrawn-catalog-blocks" data-spec-anchor="canonical"></a>
### 4.3 Withdrawn blocks

The `canonical_representations` block is withdrawn: spikes have one canonical representation, so there is nothing to arbitrate.

A top-level provenance block is withdrawn. Provenance is carried in `core.source_files`, `core.processing_runs`, and `core.processing_run_inputs`; the manifest records outputs at resource granularity only.

## 5. External resources

### 5.1 Declaration

A resource the packet does not own MUST set `external: true`. A resource whose `uri` is absolute MUST declare `external: true`; **the converse does not hold**, so a packet MAY declare a resource external and still resolve it relatively, which is how a packet published beside its data records that it does not own it.

Referencing is expected for large resources. Externalizing a table costs more than externalizing an array: its validation rules cannot run at all while it is unreachable.

### 5.2 What is recorded

`sha256`, `size_bytes`, and `verified_at` record what was true when the resource was checked. They are not a claim about now.

A writer that cannot reach a URI MUST record nothing rather than copying a value from a local stand-in.

<a id="ew-external-resource-verification" data-spec-anchor="canonical"></a>
### 5.3 Verification levels

Verification of an external resource is layered, and a report MUST state which level it reached.

| level | establishes |
|---|---|
| 1 | the manifest is internally consistent |
| 2 | packet-owned resources match their recorded digests |
| 3a | the external resource exists and lists |
| 3b | its recorded per-member store digests still match |
| 3c | its bytes read and hash to the recorded `sha256` |

Structural validation MUST NOT reach the network. Levels 3a to 3c run only in a requested mode.
When an external resource is unavailable, its physical version, codec pipeline, compression,
encoding, dtype, shape, and chunking are unassessed; a validator MUST NOT infer them from its URI,
the packet, an adapter claim, or a stand-in.

Opening the manifest, resolving declarations, listing resources, and selecting a session MUST NOT
require a validation receipt or physical inspection of every resource. Before exposing logical
values, a reader inspects only the metadata needed for the selected resource and fails that
resource specifically when support is absent.

### 5.4 Prefix resources

Where a resource is a prefix rather than a single object — an external store, or a packet-owned Zarr array — `sha256` and `size_bytes` are **defined over its members**, not undefined:

- `sha256` is the SHA-256 of the UTF-8 encoding of `[["<key>",<size>,"<sha256>"], ...]`, serialised as compact JSON with `,` and `:` separators, no whitespace and ASCII-escaped keys, one entry per object, `<key>` relative to the resource's `uri` with `/` separators, sorted by `<key>` in byte order.
- `size_bytes` is the sum of the members' sizes.

Sorting the keys is what makes the digest reproducible without knowing the store, since two implementations enumerate an object-store prefix and a local directory in different orders. Carrying each member's own digest is what lets a consumer that fetched three chunks verify those three without the other two hundred.

Such a resource MAY additionally declare a `members` array recording what was seen, each member optionally carrying a `store_digest`.

A member array is a record, not a resolution rule: a reader hands the prefix to the array library and does not enumerate it.

Where `members` accompanies `sha256`, the listing digested MUST be the declared one, so the enumeration and the digest cannot disagree.

Where a validator is asked to verify content **without reading**, it compares each member's recorded `store_digest` against the value the store reports now — a third level between listing and reading. A member whose value differs has changed; a member with no recorded `store_digest`, or whose store reports none, is **not checked**, and the report MUST say how many were skipped.

A store digest answers whether anything changed in place. It does not verify a recorded `sha256` — they are different functions — is absent for multipart uploads, and is unstable across a copy. A validator MUST report what a verification pass skipped for these reasons, and **MUST NOT** report a store-digest pass as a checksum verification: it establishes something weaker and store-specific, so it gets its own finding.

### 5.5 Source resolution

An external resource entry MAY carry `source`, an identifier naming the body of data it belongs to;
its `uri` is then a path relative to wherever that source is, and neither field is a location. An
entry carrying no `source` keeps the meaning §5.1 gives it.

Where a source is, is stated by a **source resolution document**: a JSON document, conventionally
`sources.json`, whose shape is published as `https://escapewheel.org/schemas/sources/0.1.0`. It carries
`sources_standard_version` and a `sources` object mapping each source name to an entry with a
required `uri`, and both objects are closed.

A resolution document MUST NOT be a packet resource. Immutability (§5.1) does not reach
it, which is what lets a location be corrected when a mirror moves without rebuilding the packet.

A reader MUST accept one or more resolution documents from its caller, and resolves a `source` in
this order: the documents the caller supplied, in the order supplied; then `sources.json` at the
packet root if it is there; then the source is unresolved. A writer SHOULD write that default.

A reader MUST report an unresolved `source` as unresolved, and a validator MUST NOT fail structural validation for one:
which mirrors a reader can reach is a property of the reader. Structural validation MUST NOT
require a resolution document.

A consumer MUST NOT read resolution through a different document as invalidating a recorded `sha256`,
`size_bytes` or `members`. Where a reader verifies a resolved source and finds a mismatch, it MUST
report it against the resource entry, and MUST NOT silently prefer either the recorded digest or
the bytes it found.

<a id="ew-packet-codecs" data-spec-anchor="canonical"></a>
## 6. Physical metadata is not projected

`profile_id` is the manifest's sole physical-profile selector. Generic interfaces derive under Part
03, and resource-owned metadata supplies actual versions, layouts, compression, encodings, and
codec pipelines. The manifest carries no replacement capability union or per-resource selector.

<a id="ew-resource-lineage" data-spec-anchor="canonical"></a>
## 7. Resource lineage and producing runs

The declaration's `lineage` and `producing_run` policies govern `derived_from` and
`processing_run_id` for every logical kind. `forbidden` requires absence, `optional` permits
presence, and `required` requires presence. A present `derived_from` is a nonempty array of
distinct existing packet resource IDs and obeys Part 02 §2.7's content-class relation and acyclic
graph rule.

The exact identity represented by a present `processing_run_id` remains the manifest's name rather
than an assigned table number. Complete row-to-entry reconciliation of that value is deferred; a
validator MUST NOT make the nullable source bridge
`core.processing_runs.processing_run_name` packet-unique merely to create a join.

<a id="ew-packet-registry-bindings" data-spec-anchor="canonical"></a>
## 8. Extensions

Where a packet carries extension resources, the manifest MUST declare each extension namespace, its version, and the path to its registry document:

```json
"extensions": {
  "dynamic_foraging": { "version": "0.1.0", "registry": "extensions/dynamic_foraging.json" }
}
```

A validator MUST check that a declared extension registry exists. It MUST NOT require an extension's schema in order to validate core.

<a id="ew-packet-validation-block" data-spec-anchor="canonical"></a>
## 9. Validation block

| field | requirement |
|---|---|
| `status` | MUST: `passed`, `failed`, or `not_run` |
| `validated_at` | MUST |
| `validator_name` | MUST |
| `validator_version` | MUST |

A failed or incomplete validation result cannot support a conformance claim. It does not alter a
resource's declaration-derived content class or canonicality. A writer keeps staged resources out
of a committed manifest until the applicable publication gate passes rather than representing
staging by changing canonicality.

<a id="ew-packet-catalog-normative-references" data-spec-anchor="canonical"></a>
## 10. Normative references

The application column states the extent to which this part invokes the external authority:

| reference | candidate edition | application |
|---|---|---|
| [NIST FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) | exact | SHA-256 |

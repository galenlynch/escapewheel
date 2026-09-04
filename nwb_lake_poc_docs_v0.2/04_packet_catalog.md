# Part 04 — Packet Catalog

Normative.

## 1. Scope

This part defines the packet catalog: the document that binds a packet's resources together. In the portable profile it is `nwb.packet.json` at the packet root.

## 2. Principles

The catalog is the packet's map. A reader MUST resolve resources through it and MUST NOT infer them from file layout.

The catalog binds every resource kind, including tables, dense arrays, media, and sidecar documents. An Iceberg catalog manages only tabular resources and therefore does not replace it.

The catalog identifies by name. `packet_id`, every entry's `resource_id`, the session list, and a resource's `processing_run_id` hold names rather than assigned numbers, because the catalog is read before any table and a number resolves against nothing.

## 3. Required top-level fields

| field | type | requirement |
|---|---|---|
| `packet_id` | string | MUST |
| `packet_version` | string | MUST |
| `profile_id` | string | MUST |
| `semantic_standard_version` | string | MUST |
| `logical_standard_version` | string | MUST |
| `registry_version` | string | MUST |
| `created_at` | timestamp | MUST |
| `sessions` | array of string | MUST (R1 §2) |
| `resources` | array of entry | MUST |
| `validation` | object | MUST |
| `required_codecs` | array of string | MUST (§6.2) |
| `extensions` | object | where extensions are present (§8) |
| `description` | string | MAY |

## 4. Resource entries

### 4.1 Common fields

| field | type | requirement |
|---|---|---|
| `resource_id` | string | MUST, dotted and namespaced |
| `layer` | string | MUST |
| `kind` | string | MUST, per §4.2 |
| `physical_profile` | string | MUST |
| `uri` | string | MUST |
| `canonical` | bool | MUST |
| `validation_state` | string | MUST |
| `sha256` | string | SHOULD for a packet-owned resource (R52 §2.1) |
| `schema_id` | string | MUST for a table |
| `codecs` | array of string | MUST for an array (§6.2) |
| `external` | bool | MUST where true (§5) |
| `derived_from` | array of string | MUST for a derived resource (§7) |
| `processing_run_id` | string | MUST for an analysis resource (R31 §3); SHOULD for any other derived resource |

### 4.2 Kinds

| kind | contents |
|---|---|
| `table` | a Parquet table |
| `dense_array_asset` | a Zarr array |
| `media_asset` | an image or video |
| `document` | a sidecar |

### 4.3 Withdrawn blocks

The `canonical_representations` block is withdrawn: spikes have one canonical representation, so there is nothing to arbitrate (R5 §2).

A top-level provenance block is withdrawn. Provenance is carried in `core.source_files`, `core.processing_runs`, and `core.processing_run_inputs`; the catalog records outputs at resource granularity only (R9 §2).

## 5. External resources

### 5.1 Declaration

A resource the packet does not own MUST set `external: true`. A resource whose `uri` is absolute MUST declare `external: true`; **the converse does not hold** (R14 §2.3), so a packet MAY declare a resource external and still resolve it relatively, which is how a packet published beside its data records that it does not own it.

Referencing is expected for large resources. Externalizing a table costs more than externalizing an array: its validation rules cannot run at all while it is unreachable.

### 5.2 What is recorded

`sha256`, `size_bytes`, and `verified_at` record what was true when the resource was checked. They are not a claim about now.

A writer that cannot reach a URI MUST record nothing rather than copying a value from a local stand-in (R36 §2.4).

### 5.3 Verification levels

Verification of an external resource is layered, and a report MUST state which level it reached.

| level | establishes |
|---|---|
| 1 | the catalog is internally consistent |
| 2 | packet-owned resources match their recorded digests |
| 3a | the external resource exists and lists |
| 3b | its recorded per-member store digests still match (R51 §2) |
| 3c | its bytes read and hash to the recorded `sha256` (R36 §2.2) |

Structural validation MUST NOT reach the network. Levels 3a to 3c run only in a requested mode.

### 5.4 Prefix resources

Where a resource is a prefix rather than a single object — an external store, or a packet-owned Zarr array — `sha256` and `size_bytes` are **defined over its members** (R36 §2.2), not undefined:

- `sha256` is the SHA-256 of the UTF-8 encoding of `[["<key>",<size>,"<sha256>"], ...]`, serialised as compact JSON with `,` and `:` separators, no whitespace and ASCII-escaped keys, one entry per object, `<key>` relative to the resource's `uri` with `/` separators, sorted by `<key>` in byte order.
- `size_bytes` is the sum of the members' sizes.

Sorting the keys is what makes the digest reproducible without knowing the store, since two implementations enumerate an object-store prefix and a local directory in different orders. Carrying each member's own digest is what lets a consumer that fetched three chunks verify those three without the other two hundred.

Such a resource MAY additionally declare a `members` array recording what was seen, each member optionally carrying a `store_digest` (R51 §2.1).

A member array is a record, not a resolution rule: a reader hands the prefix to the array library and does not enumerate it.

Where `members` accompanies R36 §2.2's `sha256`, the listing digested MUST be the declared one, so the enumeration and the digest cannot disagree (R51 §2.1).

A validator asked to verify content **without reading** compares each member's recorded `store_digest` against the value the store reports now — a third level between listing and reading (R51 §2.3). A member whose value differs has changed; a member with no recorded `store_digest`, or whose store reports none, is **not checked**, and the report MUST say how many were skipped.

A store digest answers whether anything changed in place. It does not verify a recorded `sha256` — they are different functions — is absent for multipart uploads, and is unstable across a copy. A verification pass MUST report what it skipped for these reasons, and a store-digest pass **MUST NOT** be reported as a checksum verification (R51 §2.4): it establishes something weaker and store-specific, so it gets its own finding.

## 6. Codecs

### 6.1 Per resource

Every array resource MUST declare the codecs it uses. A reader checks a resource's own declaration before opening it (R15 §2).

### 6.2 Packet union

`required_codecs` is the union of every resource's codecs, present so a reader can answer whether it can open the packet at all. A reader MUST NOT refuse a packet over a codec used only by resources it does not open.

A codec declared for an external resource is a claim rather than an observation, and a validator reports it as `info` rather than silently accepting it.

## 7. Derived resources

A derived resource MUST declare `derived_from`, naming the resources it was computed from.

It SHOULD declare `processing_run_id`, naming a run recorded in `core.processing_runs` (R31 §2). A validator resolves that name against the run table's `*_name` column, since the catalog names and the table numbers (§2).

## 8. Extensions

Where a packet carries extension resources, the catalog MUST declare each extension namespace, its version, and the path to its registry document (R17 §4):

```json
"extensions": {
  "dynamic_foraging": { "version": "0.1.0", "registry": "extensions/dynamic_foraging.json" }
}
```

A validator MUST check that a declared extension registry exists. It MUST NOT require an extension's schema in order to validate core.

## 9. Validation block

| field | requirement |
|---|---|
| `status` | MUST: `passed`, `failed`, or `not_run` |
| `validated_at` | MUST |
| `validator_name` | MUST |
| `validator_version` | MUST |

A packet whose committed manifest records `failed` MUST NOT present its resources as canonical.

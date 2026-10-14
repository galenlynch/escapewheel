# Part 03 — Portable Physical Profile

Normative. Profile identifier: `escapewheel-portable-v0.1`.

<a id="ew-portable-profile-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines how the logical resources of Part 02 are stored in the portable profile. A packet under this profile MUST be readable without a server.

This part incorporates `artifacts/physical_profile.schema.json` and
`artifacts/physical_profiles/escapewheel-portable-v0.1.json`. The schema owns the reusable closed
shape. The descriptor owns the profile's exact identifiers, kind-to-interface mapping, interface
forms, ownership compatibility, variants, reader floors, floor roles, overriding orders, and
anchors. This prose owns their meaning and actor obligations.

The portable physical profile defined by this part is identified by
`escapewheel-portable-v0.1`.
Its requirements directly invoke the shared JSON, URI, JSON Schema, Parquet, and RFC 1952
authorities identified in [Part 00 §9](00_architecture.md#ew-normative-references) and the
portable-profile authorities identified in [Part 03 §12](#ew-portable-profile-normative-references).
The application columns in those sections state their extent. The `digest` field belongs to
[Part 04 §4.1](04_packet_catalog.md#ew-packet-resource-entry-fields), and its functions, a prefix's
value, and when a writer records one to
[Part 04 §4.3](04_packet_catalog.md#ew-resource-digests); this part determines what a portable
resource's digest covers rather than invoking a digest authority independently.

This part is normative for a packet whose manifest declares `profile_id: escapewheel-portable-v0.1` and binds no other packet. [Part 00 §3.1.3](00_architecture.md#ew-physical-profile) makes it and Part 12, which specifies this profile's adapter interface, the only parts whose rules may depend on a storage technology. Where a number here supports a rule rather than stating one, the rule stays and the number is Part 10's.

<a id="ew-portable-profile-technologies" data-spec-anchor="canonical"></a>
## 2. Descriptor and interfaces

The packet's `profile_id` and a resource's checked logical kind select its interface. A packet
entry MUST NOT select or repeat that interface, and a declaration ID, namespace, URI suffix, or
directory placement MUST NOT act as an alternative selector.

<!-- BEGIN GENERATED PHYSICAL PROFILE -->
| logical kind | generic interface |
|---|---|
| `table` | `parquet` |
| `dense_array` | `zarr` |
| `opaque` | none |
<!-- END GENERATED PHYSICAL PROFILE -->

The descriptor's mapping keys MUST equal the logical standard's complete kind vocabulary. Every
non-null mapped interface MUST exist exactly once, and every declared interface MUST be mapped. An
opaque resource has no generic value interface: a reader MUST list it with its identity and
location, and need not retrieve, parse, decode, or render it. A validator MUST NOT report an opaque
resource, or the packet holding it, as non-conforming solely because it does not recognize the
payload's format or has no decoder for it. The descriptor states ownership per interface and maps `opaque` to none, so this section
states it: an opaque resource MAY be packet-owned or external (§11 and
[Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery)). Every current interface is
`materialized`; ownership is not a realization kind, and a view requires a separately specified
language and evaluation contract.

An interface's `reader_floor` states what every conforming reader supports for logical-value
access. `reader_and_packet_writer` also bounds packet-owned writer output; `reader_only` does not.
A valid feature outside a reader-only floor is outside the portability guarantee, but that fact
alone neither makes the upstream representation malformed nor decides packet conformance. A reader
MAY expose the logical values of a resource that uses a valid feature outside its interface's
floor, and doing so changes neither the descriptor nor the packet.

<a id="ew-descriptor-conformance" data-spec-anchor="canonical"></a>
### 2.1 Descriptor conformance

A conforming distributed copy MUST pass the schema and the generic cross-member checker at a
packaging or equivalent conformance boundary; an implementation MAY cache that result and MUST
NOT revalidate an unchanged bundled descriptor for each packet. The generic cross-member checker MUST enforce the requirements this
part places on a descriptor's members, and MUST NOT rely on this profile's identifiers or
assignments to do so: a descriptor that satisfies the schema and differs from the incorporated one
only in those is judged by the same requirements. No check verifies the second obligation, since
this specification incorporates one descriptor.

The physical-profile schema's `$id`, and the `$schema` value it requires of a descriptor, are
`https://escapewheel.org/schemas/physical-profile/0.4.0`, and the portable descriptor's `$schema`
names it. `overriding_orders` is a member only of the interface the descriptor's `kind_interfaces`
maps `table` to, and the generic cross-member checker MUST refuse it on any other interface.

Each descriptor interface and variant lists `anchors`, which the schema requires to be a nonempty
array of distinct canonical `ew-` identifiers. Each anchor MUST name a section of this part that
defines the entry's meaning, and the generic cross-member checker MUST refuse a descriptor any of
whose anchors does not resolve exactly once in this part. No checker verifies that the section an
anchor names defines the entry's meaning.

<a id="ew-portable-directory-layout" data-spec-anchor="canonical"></a>
## 3. Directory layout

<a id="ew-portable-packet-layout" data-spec-anchor="canonical"></a>
### 3.1 Recommended layout

```text
packet_root/
  packet.json

  tables/
    core/           <resource>.parquet
    analysis/       <resource>.parquet
    <namespace>/    <resource>.parquet      extension tables

  arrays/
    core/           <array_asset_id>.zarr/
    analysis/       <array_asset_id>.zarr/

  opaque/
    <resource_id>/  <name>                  a packet-owned opaque resource under its own name

  registries/
    <registry_id>/  <version>.json.gz       bound registries (§3.2)

  manifests/        <packet_version>.json   superseded manifests

  validation/       validation_report.json
```

The manifest MUST record the actual layout. A reader MUST resolve resources through the manifest and MUST NOT infer them from paths.

<a id="ew-portable-bound-registries" data-spec-anchor="canonical"></a>
### 3.2 Bound registries

A writer MUST store each registry that the manifest binds under
[Part 04 §8](04_packet_catalog.md#ew-packet-registry-bindings) at its descriptor's `path`, as
exactly one gzip member under RFC 1952 using the DEFLATE compression method of RFC 1951. The
decompressed bytes MUST be exactly the bytes the descriptor's `sha256` covers. A gzip header's
modification time, operating system, file name, and comment carry no meaning, and a reader MUST
ignore them.

A conforming packet MUST contain every bound registry. A writer MUST NOT bind a registry by remote
location or omit the stored copy, and a validator MUST NOT resolve a bound registry from anywhere
else. A reader obtains a bound registry under
[Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance). A descriptor's `path` names a file for the immutability, amendment, and cleanup rules
of §8.1 and [Part 05 §15](05_validation_and_import.md#ew-packet-amendment).

<a id="ew-staging-area" data-spec-anchor="canonical"></a>
### 3.3 The staging area

In this profile a build's staging area ([Part 05 §2](05_validation_and_import.md#ew-import-pipeline))
is the directory `staging/` directly under the packet root, and a writer MUST stage an import or an
amendment there and nowhere else under the packet root. Under the packet root, promotion moves a
staged resource to its final path by a rename within one filesystem; the fixed name lets a writer
and a cleanup tell a staging area from a directory this specification does not govern
([Part 05 §15.5](05_validation_and_import.md#ew-packet-cleanup)).

<a id="ew-portable-uri-rules" data-spec-anchor="canonical"></a>
## 4. URI rules

A URI in the manifest or in a table MAY be relative to the packet root or absolute, or — where the entry names a `source` — relative to that source (Part 04 §5.5). A portable local packet SHOULD use relative URIs.

A manifest entry's `uri` is **absolute** where it begins with a scheme under RFC 3986, Section 3.1,
followed by `://`. Every other `uri` is a **relative reference**: one or more segments under RFC
3986, Section 3.3, separated by `/`, with no leading `/`, each of which decodes to a representable
name (§11). A segment decodes by replacing each percent-encoded octet of RFC 3986, Section 2.1,
with that octet and reading the octets as UTF-8. A reader or validator MUST resolve a relative
reference by appending its decoded names, in order, to the packet root, or, where the entry names a
`source`, to that source's location ([Part 04 §5.5](04_packet_catalog.md#ew-source-resolution)), as
path components or object-key segments; it MUST NOT resolve one by RFC 3986, Section 5.

A writer MUST write each segment of a relative reference in one form: every unreserved character of
RFC 3986, Section 2.3, as itself, and every other octet of the name's UTF-8 encoding as a
percent-encoded octet with uppercase hexadecimal digits. A checker MUST report an entry whose `uri`
is not absolute and is not a relative reference in that form, at `error` in
[Part 04 §10](04_packet_catalog.md#ew-packet-manifest-conformance)'s `entries` phase, under the
check ID `packet.resource.uri_form`, naming the entry's `resource_id`. This section governs a
manifest entry's `uri`; a URI a table holds keeps the spelling its producer gave it.

An absolute URI MAY name an external asset. A manifest entry for an external asset MUST declare it external (Part 04 §5).

A packet root MAY itself be an object-store prefix rather than a directory, in which case a
relative URI resolves under that prefix
([Part 00 §3.3](00_architecture.md#ew-packet)).

<a id="ew-table-storage" data-spec-anchor="canonical"></a>
## 5. Table storage

<a id="ew-table-encoding" data-spec-anchor="canonical"></a>
### 5.1 Encoding

A table MUST be exactly one object containing one valid Parquet file. A directory, prefix, glob,
explicit member set, or multi-file dataset MUST NOT realize a table in this profile. Compression
SHOULD be Zstandard where available.

A writer MUST write each column of a packet-owned table, of each logical type of
Part 02 §5.1, with the Parquet physical type and
logical type this table gives.

| logical type | Parquet physical type | Parquet logical type |
|---|---|---|
| `int32` | `INT32` | none, or `INTEGER` with bit width 32 and signed |
| `int64` | `INT64` | none, or `INTEGER` with bit width 64 and signed |
| `float32` | `FLOAT` | none |
| `float64` | `DOUBLE` | none |
| `bool` | `BOOLEAN` | none |
| `string` | `BYTE_ARRAY` | `STRING` |
| `json_string` | `BYTE_ARRAY` | `STRING` |
| `timestamp` | `INT64` | `TIMESTAMP` with `isAdjustedToUTC=true` and unit `MICROS` |
| `date` | `INT32` | `DATE`, days since the Unix epoch |

An external table's column may instead be at another type of its declared type's **family**:

| family | its declared types | the Parquet types of the family |
|---|---|---|
| integer | `int32`, `int64` | `INT32` or `INT64`, with no logical type or with `INTEGER` of any bit width, signed or not |
| float | `float32`, `float64` | `FLOAT` or `DOUBLE`, with no logical type |
| boolean | `bool` | `BOOLEAN` |
| text | `string`, `json_string` | `BYTE_ARRAY` with `STRING`, `ENUM` or `JSON` |
| instant | `timestamp` | `INT64` with `TIMESTAMP`, `isAdjustedToUTC=true`, of any unit |
| date | `date` | `INT32` with `DATE` |

Such a column is outside the portability guarantee, as a valid feature outside a reader-only floor
is (§2): a reader MAY expose its values as the declared type, and the column's type alone does not
make the packet non-conforming. A column at a type outside its family is at the wrong type.

A large table SHOULD use row groups sized for analytical scans. Part 10 carries the sizes measured for one.

An identifier column is `int32`, or `int64` where its range requires it (Part 02 §5.3) and MUST NOT be dictionary-encoded in a way that requires unification across row groups before it can be compared.

<a id="ew-table-partitioning" data-spec-anchor="canonical"></a>
### 5.2 Partitioning

Partitioned tables are not part of this profile. A future interface may define immutable member
selection and cross-file ordering; the present `parquet` interface is one object.

<a id="ew-table-ordering" data-spec-anchor="canonical"></a>
### 5.3 Ordering

A table MUST be stored in an order that settles its primary key by adjacency: every key column appears in the sort, and every sort column up to and including the last key column is either a key column itself or one the registry declares `determined_by` a subset of the key (Part 02 §8.5). A table's **primary key's order** lists its primary key's columns in the order its registry declares them, and it is the order required of every table §5.4 does not name. A validator MUST report a departure as an **error**.

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a column that is a function of the key takes the same value in both. So the scan that establishes order settles uniqueness in the same pass, which is the means Part 02 §10.1 leaves to a profile to supply. A validator establishes order by scan rather than by query, because physical order is not visible to SQL (Part 02 §10.3).

The scan MUST verify each `determined_by` declaration it relies on: of two adjacent rows sharing a primary key, every sort column declared `determined_by` a subset of that key MUST hold the same value in both, and a validator MUST report a difference as an **error**. A wrong declaration otherwise waives a check rather than failing one. The comparison reaches a declaration that is false between two adjacent rows, which the scan reports as a duplicate key as well, the second finding saying which to repair; a declaration false enough to sort two duplicates apart is beyond a scan of neighbours.

Where the scan finds a departure, uniqueness MUST be settled by aggregate rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of neighbours.

A reader MUST NOT depend on stored order for correctness. Establishing the order is the validator's work, and a reader that assumed it would be trusting a property of the profile rather than of the logical standard.

§5.4 names the tables stored in another order, and its consistency conditions make each satisfy this section. `core.events` needs no override: its key is `(session_id, stream_id, t_tick)`, the order it is stored in. `core.spike_events` needs none either: its key is `(session_id, unit_id, t_tick)`, and because a build numbers units curation by curation ([Part 02 §12.1](02_core_logical_schemas.md#ew-unit-identity)) and an amendment numbers the units it adds after every unit the packet holds ([Part 05 §4.3](05_validation_and_import.md#ew-import-normalization)), the default order clusters each curation's spikes.

<a id="ew-overriding-orders" data-spec-anchor="canonical"></a>
### 5.4 The overriding orders

The descriptor's table interface declares `overriding_orders`. Each member names a table and lists,
in order, the columns that table is stored by. This table projects them:

<!-- BEGIN GENERATED OVERRIDING ORDERS -->
| resource | order |
|---|---|
| `analysis.spike_events` | `session_id, clock_id, time_bucket_tick, unit_id, t_tick` |
<!-- END GENERATED OVERRIDING ORDERS -->

A writer **MUST** store each table that `overriding_orders` names in the order named, and every
other table in its primary key's order (§5.3). Only a physical-profile descriptor declares an
overriding order, and a registry document declares none. A table of an extension is therefore
stored in its primary key's order, and an extension chooses that order by the order in which it
declares its key's columns.

Each overriding order and the core registry the specification candidate incorporates MUST satisfy
all of the following:

- the order's key names a table that the core registry declares;
- every column the order names is a column of that table;
- the order names every column of the table's primary key;
- every column before the last primary-key column in the order is a primary-key column or is
  declared `determined_by` a subset of the primary key (Part 02 §8.5); and
- the order differs from the table's primary key's order.

These make each override satisfy §5.3's adjacency rule without a packet. A descriptor and core
registry that fail them make the candidate internally inconsistent
([Part 00 §2.3](00_architecture.md#ew-candidate-consistency)).

Where a packet's bound core registry declares a table that `overriding_orders` names, but not every
column its order names, the table cannot be stored in its required order. A validator **MUST**
report that table's order as a departure under §5.3.

`analysis.spike_events` is the one resource whose layout is part of its reason for existing: bucketing by time and sorting by unit within each bucket leaves both columns with informative row-group statistics, so a unit filter and a time filter each prune.

A writer **SHOULD** start a new row group at each bucket boundary. A group cut at a fixed row count straddles boundaries and spans two buckets' worth of time. Row-group size and encoding are otherwise not normative: the right values follow from session length and unit count rather than from the schema.

<a id="ew-parquet-reader-floor" data-spec-anchor="canonical"></a>
### 5.5 The Parquet floor

A reader MUST support footer-reported compressions `UNCOMPRESSED`, `SNAPPY`, `GZIP`, and `ZSTD`;
encodings `PLAIN`, `RLE`, `RLE_DICTIONARY`, and `DELTA_BINARY_PACKED`; and data-page types
`DATA_PAGE` and `DATA_PAGE_V2`, in a file whose footer and columns are not encrypted. A packet writer MUST keep every written
table within that same floor. It MUST configure its page type and absence of
encryption before writing, inspect the footer afterwards, and refuse an outside-floor compression
or encoding. `PLAIN_DICTIONARY` is valid upstream but outside this writer floor.

The descriptor is the exact machine-readable owner of these members and declares this interface
`materialized`, `logical_values`, `single_object`, available for packet and external ownership,
with floor role `reader_and_packet_writer`. `FileMetaData.version` is not a substitute for checking
the independent floor features.

A validator assessing a Parquet resource MUST compare each column chunk's footer-reported
compression and encodings with the floor's `compressions` and `encodings`. It need not read page
headers or determine data-page types. A validator that does not compare data-page types MUST state
in its report that it did not assess them.

<a id="ew-array-storage" data-spec-anchor="canonical"></a>
## 6. Array storage

<a id="ew-array-version" data-spec-anchor="canonical"></a>
### 6.1 Version

A packet-owned array MUST be Zarr v3. A referenced array MAY be Zarr v2 or v3. A reader or
validator determines the version from the resource's `zarr_format` metadata when it accesses or
assesses that resource; a packet entry MUST NOT state it.

An array MUST use a **regular chunk grid**: every chunk the same shape, the last along each axis permitted to be partial. An irregular grid is expressible in Zarr and is not readable by every binding.

No packet-owned resource may have metadata declaring Zarr v2. Lack of implementation support for
one selected resource MUST fail that resource specifically and MUST NOT reject unopened resources.

### 6.2 Axis order

Array axes are stored order, slowest-varying first. An array's codec chain MUST NOT include `transpose`.

A reader MUST NOT treat the order in which its language enumerates an array's axes as the declared order: `axis_index` counts axes in stored order, and a column-major binding enumerates them in reverse. The client adapts; the format does not. No check observes this.

<a id="ew-array-codecs" data-spec-anchor="canonical"></a>
### 6.3 Codecs

A writer MAY use any codec permitted by the applicable Zarr specification, subject to §6.2's
`transpose` prohibition and the regular-grid rule. The resource's own metadata is the sole owner of
the actual pipeline; the manifest does not repeat it.

A writer MAY store an array in either byte order. In Zarr v3 the byte order is the `bytes` codec's
`endian` configuration, and in Zarr v2 it is the first character of each type string of `dtype`, a
term this section defines with the v2 reader floor.

The applicable Zarr specification alone decides which members an array's metadata document requires.
A metadata document lacking a member that specification requires, `fill_value` among them, is
upstream invalidity under this section, and this profile states no separate requirement of that
member.

The v3 reader floor admits exactly these unsharded codec sequences, in pipeline order: `bytes`;
`bytes` then `gzip`; `bytes` then `zstd`; and `bytes` then `blosc` with `cname` `zstd`. It also
admits a sharded pipeline whose shard holds one of those sequences, under the rules below. A
conforming reader MUST expose the logical values of every valid v3 array whose pipeline matches the
floor. The descriptor's `interfaces.zarr.variants.v3.reader_floor` is exactly:

<!-- BEGIN GENERATED ZARR V3 FLOOR -->
```json
{
  "codec_sequences": [
    [{"name": "bytes"}],
    [{"name": "bytes"}, {"name": "gzip"}],
    [{"name": "bytes"}, {"name": "zstd"}],
    [{"name": "bytes"}, {"name": "blosc", "configuration": {"cname": "zstd"}}]
  ],
  "sharding": {
    "index_codec_sequences": [[{"name": "bytes"}], [{"name": "bytes"}, {"name": "crc32c"}]],
    "index_location": "end"
  }
}
```
<!-- END GENERATED ZARR V3 FLOOR -->

A reader or validator comparing a v3 array's metadata with the floor MUST apply these rules. A
codec matches a codec pattern when its `name` equals the pattern's and every configuration member
the pattern states compares equal. Members the pattern does not state do not participate, and a
codec stated by its name alone has no configuration members. An unsharded pipeline matches a floor
sequence when both have the same length and each codec matches the pattern at its position. A
sharded pipeline matches the floor when:

- the pipeline is exactly one `sharding_indexed` codec;
- that codec's `codecs` match an entry of `codec_sequences`;
- its `index_codecs` match an entry of `sharding.index_codec_sequences`; and
- its `index_location` equals `sharding.index_location`, an absent `index_location` comparing as
  `end`, the default the sharding-indexed codec specification gives it.

A floor without `sharding` admits no sharded pipeline, and a pipeline matching no entry is outside
the floor. Metadata the applicable Zarr specification makes invalid, including an invalid
configuration of a codec the validator implements, is upstream invalidity rather than a floor
observation. A validator MUST treat a codec name it does not recognize as valid metadata outside
the floor, because Zarr v3 admits extension codecs.

A **type string** of a Zarr v2 array is its `dtype` where that is a string. Where `dtype` is a
structured type, the array's type strings are those of each field's data type, taken recursively
where a field's data type is itself structured. The Zarr v2 storage specification makes the first
character of a type string its byte order: `<` for little-endian, `>` for big-endian, and `|` for a
type that has none.

A valid v2 array is inside the v2 reader floor when both of the following hold:

- its `filters` and `compressor` match one of the floor's `metadata_patterns`; and
- the first character of every one of its type strings is a member of the floor's
  `dtype_byte_orders`.

Any other valid v2 array is outside the floor. In a v2 pattern, JSON null matches only null, every
stated member compares equal, and unmentioned configuration members do not participate. The
descriptor's `interfaces.zarr.variants.v2.reader_floor` is exactly:

<!-- BEGIN GENERATED ZARR V2 FLOOR -->
```json
{
  "metadata_patterns": [
    {"filters": null, "compressor": null},
    {"filters": null, "compressor": {"id": "zstd"}},
    {"filters": null, "compressor": {"id": "blosc", "cname": "zstd"}}
  ],
  "dtype_byte_orders": ["<", "|"]
}
```
<!-- END GENERATED ZARR V2 FLOOR -->

A reader or validator comparing a v2 array's metadata with the floor MUST apply these rules. A
conforming reader MUST expose the logical values of every valid v2 array that the v2 reader floor
admits. The descriptor declares the Zarr interface `materialized`, `logical_values`, and `prefix`,
with floor role `reader_only`; v3 permits packet and external ownership, while v2 permits external
ownership only. It does not enumerate optional codecs.

<a id="ew-array-metadata-placement" data-spec-anchor="canonical"></a>
### 6.4 What the array declares, and what the tables declare

The declaration-selected axes table owns axis names, since a Zarr v2 array has no field for them.
A packet-owned array MUST carry Zarr v3 `dimension_names`, holding at each position the
`dimension_name` of the axes-table row with that `axis_index`. A referenced array may carry other
names or none, and its axes-table rows govern. A validator resolves that table from the
dense-array declaration rather than from a fixed namespace or resource ID.

Zarr attributes MAY duplicate helpful metadata. Logical and scientific facts required for
validation MUST also be represented in their logical resources or packet fields. Self-describing
physical facts—version, shape, dtype, chunking, and codec configuration—MUST be obtained from the
resource and need not be copied into a table or the manifest.

<a id="ew-metadata-placement" data-spec-anchor="canonical"></a>
## 7. Metadata placement

| kind | location |
|---|---|
| packet-level facts | the manifest |
| queryable scientific facts | tables |
| semi-structured, lab-specific values | a `json_string` column, or an extension's table |
| context the packet asserts nothing through | a sidecar that `core.sidecars` lists |

A value used for filtering, grouping, joining, or validation MUST be a first-class typed column.

## 8. Immutability

<a id="ew-packet-owned-bytes" data-spec-anchor="canonical"></a>
### 8.1 Packet-owned bytes

A writer MUST NOT modify a resource the packet owns once it is committed. A correction is a replacement ([Part 04 §3](04_packet_catalog.md#ew-packet-identifiers)), not an edit and not an amendment.

This promise is what allows an amendment to skip revalidating untouched files, so it is verified rather than assumed: a writer records a checksum for every packet-owned resource (§10).

### 8.2 External bytes

This specification promises nothing about bytes the packet does not own. What a packet records about an external resource is what was true when it was checked, not a claim about now.

<a id="ew-portable-amendment" data-spec-anchor="canonical"></a>
## 9. Amendment and retention

[Part 05 §15](05_validation_and_import.md#ew-packet-amendment) states what an amendment is and may
change, what it retains, what it revalidates, and how cleanup proceeds. This section is how this
profile realizes an amendment, as Part 00 §7.3 requires of a profile.

Every resource an amendment writes
([Part 05 §15.1](05_validation_and_import.md#ew-amendment-definition)), a table gaining a group or a
provenance table gaining rows included, is written as a **new file** that the amended manifest
names; no byte of the old one changes. Immutability is thereby a property of files, and a
resource's *content* may be superseded by naming different bytes. Since §5.1 makes a table one
Parquet file and §5.2 defers member files, a table gaining a group is rewritten whole, in the order
§5.3 requires.

Every superseded manifest is retained under `manifests/`, so a later cleanup can distinguish a file
an old version named from a file nothing ever named. A packet never amended retains nothing and
carries no `manifests/` directory at all, so the common case costs nothing.

A **stray** is a file under the packet root that no manifest ever named, that lies outside the
staging area (§3.3), and that neither is listed by nor lies inside a directory listed by a promotion
record whose `packet_version` is unpublished ([Part 05 §6](05_validation_and_import.md#ew-import-commit)).

<a id="ew-owned-resource-digests" data-spec-anchor="canonical"></a>
## 10. Checksums

In this profile a packet-owned table's `digest` covers its one Parquet file, and a packet-owned
array's covers its Zarr prefix as
[Part 04 §4.3](04_packet_catalog.md#ew-resource-digests) defines a prefix's value. A packet-owned
opaque resource's `digest` covers its payload (§11): the one object where the payload is a file,
and otherwise its files, as Part 04 §4.3 defines a prefix's value, with each file's key its path
relative to the payload. `size_bytes` covers the same bytes. Part 04 §4.3
requires a writer to record one for every packet-owned resource, which is the one case where a
digest verifies what the packet itself claims.

A digest is whole-file, not per-row-group. Parquet cannot be appended to, so "which pages moved" is not a question the format can be asked, and Parquet's own page CRC32 is a corruption detector that a rewritten file passes.

Verification of packet-owned and external resources is layered
([Part 04 §5.3](04_packet_catalog.md#ew-external-resource-verification)).

<a id="ew-opaque-storage" data-spec-anchor="canonical"></a>
## 11. Opaque storage

A packet stores a packet-owned opaque resource as its **payload**: one regular file, or one
directory whose every member is a regular file or a directory. No directory within a payload, the
payload included, is empty, since a prefix consists of objects. A payload that is a file is a single
object, and one that is a directory is a prefix
([Part 04 §5.4](04_packet_catalog.md#ew-prefix-resources)).

**A payload keeps its names.** A name is **representable** where it is nonempty, is valid UTF-8,
contains neither NUL nor `/`, and is neither `.` nor `..`. A representable name need not be in any
Unicode normalization form, and two names in one directory may differ only in case.

A build MUST publish each payload under the name it was delivered with
([Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery)), and every file and
directory within it under theirs, and MUST NOT rename, normalize, or case-fold any of them. It MUST
publish each payload in a directory under the packet root that holds nothing else, since two
payloads may share a name. §3.1's recommended layout places that directory at
`opaque/<resource_id>/`, so a payload lies at `opaque/<resource_id>/<name>`. No validator checks
that a payload kept its names or has its directory to itself, since a packet records neither the
names as the source spelled them nor which files a build placed; a build's own tests are the
evidence. A payload's manifest `uri` names the payload itself, the file where the payload is one and
otherwise the directory, as a relative reference (§4). A validator warns of names that would not
survive a copy to a filesystem that folds case or normalization or that Windows governs
([Part 05 §5.3](05_validation_and_import.md#ew-validation-shim)).

<a id="ew-portable-profile-normative-references" data-spec-anchor="canonical"></a>
## 12. Normative references

The application column states the extent to which this part invokes each external authority:

| reference | candidate edition | application |
|---|---|---|
| [Zarr v3 core](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html), [data types](https://zarr-specs.readthedocs.io/en/latest/v3/data-types/index.html), [regular chunk grid](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-grids/regular-grid/index.html), and [default chunk-key encoding](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-key-encodings/default/index.html) | core v3.0; other entries unversioned | Zarr v3 arrays |
| Zarr v3 [Bytes](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/bytes/), [Gzip](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/gzip/), [Blosc](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/blosc/), [CRC32C](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/crc32c/), [transpose](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/transpose/), and [sharding-indexed](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/) codec specifications | unversioned | permitted Zarr v3 codec pipeline components |
| [Zarr v3 Zstandard codec specification](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/zstd/) | unversioned | `zstd` codec metadata object and configuration |
| [Zarr v2 storage specification](https://zarr-specs.readthedocs.io/en/latest/v2/v2.0.html) | 2.0 | permitted external Zarr v2 arrays |
| [RFC 8878](https://www.rfc-editor.org/info/rfc8878) | exact | Zstandard framing |
| [RFC 1951](https://www.rfc-editor.org/info/rfc1951) | exact | DEFLATE compression of a bound registry (§3.2) |

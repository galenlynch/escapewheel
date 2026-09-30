# Part 03 — Portable Physical Profile

Normative. Profile identifier: `escapewheel-portable-v0.1`.

<a id="ew-portable-profile-scope" data-spec-anchor="canonical"></a>
## 1. Scope

This part defines how the logical resources of Part 02 are stored in the portable profile. A packet under this profile MUST be readable without a server.

This part incorporates `registry/physical_profile.schema.json` and
`registry/physical_profiles/escapewheel-portable-v0.1.json`. The schema owns the reusable closed
shape. The descriptor owns the profile's exact identifiers, kind-to-interface mapping, interface
forms, ownership compatibility, variants, reader floors, floor roles, and anchors. This prose owns
their meaning and actor obligations. A conforming distributed copy MUST pass the schema and the
generic cross-member checker at a packaging or equivalent conformance boundary; an implementation
MAY cache that result and MUST NOT revalidate an unchanged bundled descriptor for each packet.

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
opaque resource has no generic value interface: a generic reader lists its identity and location but
need not retrieve, parse, decode, or render it. Unknown opaque representations do not invalidate a
packet. The descriptor states ownership per interface and maps `opaque` to none, so this section
states it: an opaque resource MAY be packet-owned or external (§11 and
[Part 12 §5](12_adapter_interface.md#ew-referenced-resource-delivery)). Every current interface is
`materialized`; ownership is not a realization kind, and a view requires a separately specified
language and evaluation contract.

An interface's `reader_floor` states what every conforming reader supports for logical-value
access. `reader_and_packet_writer` also bounds packet-owned writer output; `reader_only` does not.
A valid feature outside a reader-only floor is outside the portability guarantee, but that fact
alone neither makes the upstream representation malformed nor decides packet conformance.

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
    <registry_id>/  <version>.json.gz       bound registries (§3.3)

  manifests/        <packet_version>.json   superseded manifests

  docs/                                     human-readable sidecars

  validation/       validation_report.json
```

The manifest MUST record the actual layout. A reader MUST resolve resources through the manifest and MUST NOT infer them from paths.

<a id="ew-portable-forbidden-files" data-spec-anchor="canonical"></a>
### 3.2 Files that MUST NOT be written

A writer MUST NOT write `schemas/semantic_version.txt`, which would restate `semantic_standard_version`, a field the manifest is required to carry. No checker verifies this.

<a id="ew-portable-bound-registries" data-spec-anchor="canonical"></a>
### 3.3 Bound registries

A writer MUST store each registry that the manifest binds under
[Part 04 §8](04_packet_catalog.md#ew-packet-registry-bindings) at its descriptor's `path`, as
exactly one gzip member under RFC 1952 using the DEFLATE compression method of RFC 1951. The
decompressed bytes MUST be exactly the bytes the descriptor's `sha256` covers. A gzip header's
modification time, operating system, file name, and comment carry no meaning, and a reader MUST
ignore them.

A conforming packet MUST contain every bound registry. A writer MUST NOT bind a registry by remote
location or omit the stored copy, and a reader or validator MUST NOT resolve a bound registry from
anywhere else. A descriptor's `path` names a file for the immutability, amendment, and cleanup rules
of §8.1 and [Part 05 §15](05_validation_and_import.md#ew-packet-amendment).

<a id="ew-staging-area" data-spec-anchor="canonical"></a>
### 3.4 The staging area

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

## 5. Table storage

<a id="ew-table-encoding" data-spec-anchor="canonical"></a>
### 5.1 Encoding

A table MUST be exactly one object containing one valid Parquet file. A directory, prefix, glob,
explicit member set, or multi-file dataset MUST NOT realize a table in this profile. Compression
SHOULD be Zstandard where available.

A large table SHOULD use row groups sized for analytical scans. Part 10 carries the sizes measured for one.

An identifier column is `int32`, or `int64` where its range requires it (Part 02 §5.3) and MUST NOT be dictionary-encoded in a way that requires unification across row groups before it can be compared.

<a id="ew-table-partitioning" data-spec-anchor="canonical"></a>
### 5.2 Partitioning

Partitioned tables are not part of this profile. A future interface may define immutable member
selection and cross-file ordering; the present `parquet` interface is one object.

<a id="ew-table-ordering" data-spec-anchor="canonical"></a>
### 5.3 Ordering

A table MUST be stored in an order that settles its primary key by adjacency: every key column appears in the sort, and every sort column up to and including the last key column is either a key column itself or one the registry declares `determined_by` a subset of the key (Part 02 §8.5). Where §5.4 gives no order for a table, the order required is its primary key's. A validator MUST report a departure as an **error**.

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a column that is a function of the key takes the same value in both. So the scan that establishes order settles uniqueness in the same pass, which is the means Part 02 §10.1 leaves to a profile to supply. A validator establishes order by scan rather than by query, because physical order is not visible to SQL (Part 02 §10.3).

The scan MUST verify each `determined_by` declaration it relies on: of two adjacent rows sharing a primary key, every sort column declared `determined_by` a subset of that key MUST hold the same value in both, and a validator MUST report a difference as an **error**. A wrong declaration otherwise waives a check rather than failing one. The comparison reaches a declaration that is false between two adjacent rows, which the scan reports as a duplicate key as well, the second finding saying which to repair; a declaration false enough to sort two duplicates apart is beyond a scan of neighbours.

Where the scan finds a departure, uniqueness MUST be settled by aggregate rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of neighbours.

A reader MUST NOT depend on stored order for correctness. Establishing the order is the validator's work, and a reader that assumed it would be trusting a property of the profile rather than of the logical standard.

One table is stored in an order other than its primary key's, `analysis.spike_events`, under a `MUST`; Part 03 §5.4 gives it, and it satisfies this section because `clock_id` and `time_bucket_tick` are each declared `determined_by` a subset of the key. `core.events` needs no override: its key is `(session_id, stream_id, t_tick)`, the order it is stored in. `core.spike_events` needs none either: its key is `(session_id, unit_id, t_tick)`, and because a build numbers units curation by curation ([Part 02 §12.1](02_core_logical_schemas.md#ew-unit-identity)) and an amendment numbers the units it adds after every unit the packet holds ([Part 05 §4.3](05_validation_and_import.md#ew-import-normalization)), the default order clusters each curation's spikes.

### 5.4 The overriding orders

| resource | order |
|---|---|
| `analysis.spike_events` | `session_id, clock_id, time_bucket_tick, unit_id, t_tick` |

A writer **MUST** emit `analysis.spike_events` in that order. It is the one resource whose layout is part of its reason for existing: bucketing by time and sorting by unit within each bucket leaves both columns with informative row-group statistics, so a unit filter and a time filter each prune.

A writer **SHOULD** start a new row group at each bucket boundary. A group cut at a fixed row count straddles boundaries and spans two buckets' worth of time. Row-group size and encoding are otherwise not normative: the right values follow from session length and unit count rather than from the schema.

<a id="ew-parquet-reader-floor" data-spec-anchor="canonical"></a>
### 5.5 The Parquet floor

A reader MUST support footer-reported compressions `UNCOMPRESSED`, `SNAPPY`, `GZIP`, and `ZSTD`;
encodings `PLAIN`, `RLE`, `RLE_DICTIONARY`, and `DELTA_BINARY_PACKED`; and data-page types
`DATA_PAGE` and `DATA_PAGE_V2`, in a file whose footer and columns are not encrypted. A packet writer MUST keep every written
table within that same floor and SHOULD use Zstd. It MUST configure its page type and absence of
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

A writer SHOULD choose the encoding of each integer, float, string, timestamp and date column from
the column's declarations and from four counts over the rows it holds when it chooses: the rows,
nulls included; the distinct non-null values; the runs, a run being a maximal sequence of equal
values once nulls are set aside; and, for an integer, whether its non-null values never decrease.
Where a writer writes a table whole the rows are the table's; where it streams a table,
they are the row group it is about to write, or the first row group where the writer keeps one
encoding for the whole file. The first of the four rules below that applies decides.

1. A writer SHOULD write plain a column in which every row is null.
2. A writer SHOULD dictionary-encode a column holding one distinct non-null value where it holds
   50,000 rows or more, and below that SHOULD encode it with `DELTA_BINARY_PACKED` where it is an
   integer and plain otherwise. A dictionary page costs its bytes in every row group,
   and only a long row group repays them (Part 10 §2.8).
3. An integer column is **ordered** where its name ends `_tick`; where it is the first column of its
   table's sort order other than `session_id` and its role is `identifier`; where its role is
   `structural_index` or `sequence_position` (Part 02 §8.1); where it is an `assigned` identifier
   (Part 02 §8.2); or where its non-null values never decrease. A writer SHOULD encode an ordered
   integer with `DELTA_BINARY_PACKED`, and SHOULD write it plain where it holds at least 50 rows for
   each run. A declaration states no distribution, but it marks a column likely to climb
   within groups, which no count over the whole column sees (Part 10 §2.9).
4. A writer SHOULD dictionary-encode any other column, a float included, where it holds at least 50
   rows for each distinct non-null value, and SHOULD write it plain otherwise. Repetition
   is what a dictionary indexes, and no declaration says how often a value repeats (Part 10 §2.10).

None of the four is the property it stands in for, so a writer MUST be able to override each per
column, and every override MUST record what it measured and on what. An exception
recording nothing cannot be re-judged when the data changes. A writer SHOULD refuse an exception
naming a column no table declares, which is decidable with no packet in hand.

A writer SHOULD report, at `info`, a column whose encoding costs more than **1.5x** the smallest
available to it, measured over a sample of the rows it wrote. It SHOULD measure a column
by its own compressed chunks rather than by a file carrying it, and SHOULD judge a string, timestamp
or date column between a dictionary and plain, the two encodings the rules choose among for it.
These rules are good guesses, and the report is how the author of a table learns that
theirs is one a guess misses. A report and not a refusal: every encoding above is permitted, so a
packet is conforming whichever it uses.

Wall-clock timestamps MUST be Parquet `TIMESTAMP` with `isAdjustedToUTC=true` and `MICROS`
precision; A wall-clock column MUST NOT use `INT96`. Dates MUST be Parquet `DATE`, int32 days since the Unix epoch.

<a id="ew-one-null" data-spec-anchor="canonical"></a>
### 5.6 One null

Under `escapewheel-portable-v0.1` a column value is present or null and there is no second marker. Parquet's definition level carries one bit and Arrow's validity bitmap carries one, so a value that is inapplicable, one that was never recorded, and one a source recorded as unknown all arrive as the same null.

NaN is not the exception it looks like. It is a value of a float column rather than an absent one, so it reaches only a float column declaring `finite: false` under [Part 02 §5.4](02_core_logical_schemas.md#ew-finite-values), and Parquet's statistics exclude it from a page's bounds — a page holding only NaN publishes no minimum and no maximum.

A writer MUST NOT adopt a sentinel value meaning absent; an absent value is null. Where the reason for the absence matters, core records the fact that distinguishes it rather than encoding the reason in the value: a run's `scope` distinguishes an undeterminable scope from an unambiguous one, and `normalized_label` is null where a source's label has no honest projection.

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

A column-major binding enumerates axes in reverse. The client adapts; the format does not.

<a id="ew-array-axis-coordinates" data-spec-anchor="canonical"></a>
### 6.3 Axis coordinates

Every axis MUST declare its coordinates in the dense-array declaration's `array.axes_resource`, in
one of its declared coordinate forms. A regularly sampled axis declares an origin tick, a step,
and a length rather than storing per-sample values.

A step MAY be rational, declared as a numerator and denominator: a 30 ms bin at 31,250 Hz is 937.5 ticks.


An axis MUST declare no more than one coordinate form: two descriptions of the same positions can disagree and nothing would say which governs.

A rational step is a numerator and a denominator. `step_tick_den`, where present, MUST be positive, the numerator MUST be present wherever an origin is, and the pair SHOULD be in lowest terms so two packets describing the same axis describe it identically.

Where an array declares both a sampling rate and a regular tick axis, the two describe the same thing and MUST agree. The rate is retained as a validated denormalization, not as a second source of truth.

A writer MUST declare an axis whose positions carry only their order in the numeric form, with
`step_value` 1, `coordinate_unit` `1` and `origin_value` the number its source gives the first
position, or 0 where the source numbers none. A principal-component axis is one. No rule can tell
an order-only axis from a measured one, so nothing checks this.

No form labels a position with text. An axis whose positions are categories that are not rows of a
resource is declared order-only, or the array is split along it into one array per category, each
naming its category in `semantic_type`
([Part 01 §3.17](01_semantic_standard.md#ew-array-asset-concept)).

An axis is **labelled** where its row declares `coordinate_resource`, and each of its positions
then stands for the row its label names, or for none. Its labels are rows of the table that
`coordinate_resource`'s `discriminates_via` names: `core.array_labels` for a core array and
`analysis.array_labels` for an analysis one. A label's `label_id` is the identifier of the row its
position stands for, in the resource `coordinate_resource` names, and a null `label_id` stands for
no row, which is how a packet states padding.

An axis is **dependent** where its row declares `depends_on_axis_index`: which row each of its
positions stands for changes along the axis `depends_on_axis_index` names, and each label row's
`depends_on_position_index` is the position on that axis. A packet MUST satisfy each of these:

- a labelled axis has one label row at each of its positions, and a dependent axis one at each of
  its positions for each position of the axis it depends on;
- a dependent axis is labelled;
- the axis a dependent axis names is not itself dependent, which excludes an axis naming itself;
- every label row of an axis that is not dependent has `depends_on_position_index` 0; and
- no two label rows of one axis at one `depends_on_position_index` hold one non-null `label_id`, so
  a row is at most one position.

A core axis MUST name a `core` resource. A label must resolve, and an analysis resource may be
deleted ([Part 06 §2](06_analysis_layer.md#ew-analysis-rules)), which would leave a core array's
positions standing for nothing. A core axis has no need to name an extension resource: a kind of
interval an extension specialises is a row of `core.intervals`. Only a core axis is limited to core
resources, so an analysis array may instead label a category axis with a resource whose rows are
the categories, such as an extension's table.

<a id="ew-array-codecs" data-spec-anchor="canonical"></a>
### 6.4 Codecs

A writer MAY use any codec permitted by the applicable Zarr specification, subject to §6.2's
`transpose` prohibition and the regular-grid rule. The resource's own metadata is the sole owner of
the actual pipeline; the manifest does not repeat it.

The v3 reader floor admits exactly these unsharded codec sequences, in pipeline order: `bytes`;
`bytes` then `gzip`; `bytes` then `zstd`; and `bytes` then `blosc` with `cname` `zstd`. It also
admits a sharded pipeline whose shard holds one of those sequences, under the rules below. A
conforming reader MUST expose the logical values of every valid v3 array whose pipeline matches the
floor. The descriptor's `interfaces.zarr.variants.v3.reader_floor` is exactly:

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

The v2 reader floor is exactly `filters: null` with compressor null, compressor `id: zstd`, or
compressor `id: blosc` and `cname: zstd`. In a v2 pattern, JSON null matches only null, every stated
member compares equal, and unmentioned configuration members do not participate. The descriptor
declares the Zarr interface `materialized`, `logical_values`, and `prefix`, with floor role
`reader_only`; v3 permits packet and external ownership, while v2 permits external ownership only.
It does not enumerate optional codecs.

The physical-profile schema's `$id`, and the `$schema` value it requires of a descriptor, are
`https://escapewheel.org/schemas/physical-profile/0.2.0`, and the portable descriptor's `$schema`
names it. The schema declares the v3 floor with these definitions:

| definition | shape |
|---|---|
| `codec_pattern` | closed object; requires `name`, a string; admits `configuration` only where `name` is `blosc`, and there `configuration` is a closed object requiring `cname`, a string |
| `codec_sequence` | array of one or more `codec_pattern` |
| `sharding_floor` | closed object; requires `index_codec_sequences`, an array of one or more distinct `codec_sequence`, and `index_location`, `start` or `end` |
| `zarr_v3_floor` | closed object; requires `codec_sequences`, an array of one or more distinct `codec_sequence`; admits `sharding`, a `sharding_floor` |

<a id="ew-array-metadata-placement" data-spec-anchor="canonical"></a>
### 6.5 What the array declares, and what the tables declare

`core.array_assets` MUST NOT carry dtype or shape. The Zarr array declares them, and restating them buys no otherwise-unavailable access.

The declaration-selected axes table owns axis names, since a Zarr v2 array has no field for them.
A packet-owned array MUST carry Zarr v3 `dimension_names`, holding at each position the
`dimension_name` of the axes-table row with that `axis_index`. A referenced array may carry other
names or none, and its axes-table rows govern. A physical checker resolves that table from the
dense-array declaration rather than from a fixed namespace or resource ID.

Zarr attributes MAY duplicate helpful metadata. Logical and scientific facts required for
validation MUST also be represented in their logical resources or packet fields. Self-describing
physical facts—version, shape, dtype, chunking, and codec configuration—MUST be obtained from the
resource and need not be copied into a table or the manifest.

## 7. Metadata placement

| kind | location |
|---|---|
| packet-level facts | the manifest |
| queryable scientific facts | tables |
| semi-structured, lab-specific values | a `json_string` column, or a sidecar |
| human-readable context | `docs/` |

A value used for filtering, grouping, joining, or validation MUST be a first-class typed column.

## 8. Immutability

<a id="ew-packet-owned-bytes" data-spec-anchor="canonical"></a>
### 8.1 Packet-owned bytes

A writer MUST NOT modify a resource the packet owns once it is committed. A correction is a new packet version, not an edit.

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
staging area (§3.4), and that neither is listed by nor lies inside a directory listed by a promotion
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
| [RFC 1951](https://www.rfc-editor.org/info/rfc1951) | exact | DEFLATE compression of a bound registry (§3.3) |

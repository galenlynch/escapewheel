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

This part also incorporates `registry/resources.schema.json`, whose `$id` is
`https://escapewheel.org/schemas/resources/0.4.0`, as the exact shape of the resource document of
§11.3. Its closed envelope admits an optional `$schema` string and requires `resources`, an array
of closed entries. An entry requires `resource_id`, `declaration_id`, and `uri`, and admits
`external`, `source`, `sha256`, `size_bytes`, `verified_at`, and `members`. The delivery schema
defines each of those members, and the entry's conditional shape, exactly as the manifest schema
[Part 04 §1](04_packet_catalog.md#ew-packet-catalog-scope) incorporates defines them; a difference
makes the specification candidate internally inconsistent.

The portable physical profile defined by this part is identified by
`escapewheel-portable-v0.1`. Its requirements directly invoke the shared JSON and URI authorities
identified in [Part 00 §10](00_architecture.md#ew-normative-references) and the portable-profile
authorities identified in [Part 03 §12](#ew-portable-profile-normative-references). The application
columns in those sections state their extent. The `sha256` field and prefix-resource digest meaning
belong to Part 04 §4.1 and Part 04 §5.4; this part determines when portable-profile resources record
and verify that manifest field rather than invoking FIPS 180-4 independently.

This part is normative for a packet whose manifest declares `profile_id: escapewheel-portable-v0.1` and binds no other packet. It is the only part whose rules may depend on a storage technology. Where a number here supports a rule rather than stating one, the rule stays and the number is Part 10's.

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
non-null mapped interface MUST exist exactly once, and every declared interface MUST be mapped.
An opaque resource has no generic value interface: a generic reader lists its identity and
location but need not retrieve, parse, decode, or render it. Unknown opaque representations do not
invalidate a packet. Every current interface is `materialized`; ownership is not a realization
kind, and a view requires a separately specified language and evaluation contract.

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

  media/            <media_asset_id>.<ext>

  registries/
    <registry_id>/  <version>.json.gz       bound registries (§3.3)

  manifests/        <packet_version>.json   superseded manifests

  docs/                                     human-readable sidecars

  validation/       validation_report.json
```

The manifest MUST record the actual layout. A reader MUST resolve resources through the manifest and MUST NOT infer them from paths.

### 3.2 Files that MUST NOT be written

`schemas/semantic_version.txt` is struck. It restated `semantic_standard_version`, which the manifest is required to carry, and so bought no otherwise-available access.

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
of §§8.1, 9.1, and 9.5.

## 4. URI rules

A URI in the manifest or in a table MAY be relative to the packet root or absolute, or — where the entry names a `source` — relative to that source (Part 04 §5.5). A portable local packet SHOULD use relative URIs.

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

### 5.3 Ordering

A table MUST be stored in an order that settles its primary key by adjacency: every key column appears in the sort, and every sort column up to and including the last key column is either a key column itself or one the registry declares `determined_by` a subset of the key (Part 02 §8.5). Where the registry declares no sort for a table, the order required is its primary key's. A validator MUST report a departure as an **error**.

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a column that is a function of the key takes the same value in both. So the scan that establishes order settles uniqueness in the same pass, which is the means Part 02 §10.1 leaves to a profile to supply. A validator establishes order by scan rather than by query, because physical order is not visible to SQL (Part 02 §10.3).

The scan MUST verify each `determined_by` declaration it relies on: of two adjacent rows sharing a primary key, every sort column declared `determined_by` a subset of that key MUST hold the same value in both, and a validator MUST report a difference as an **error**. A wrong declaration otherwise waives a check rather than failing one. The comparison reaches a declaration that is false between two adjacent rows, which the scan reports as a duplicate key as well, the second finding saying which to repair; a declaration false enough to sort two duplicates apart is beyond a scan of neighbours.

Where the scan finds a departure, uniqueness MUST be settled by aggregate rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of neighbours.

A reader MUST NOT depend on stored order for correctness. Establishing the order is the validator's work, and a reader that assumed it would be trusting a property of the profile rather than of the logical standard.

One table is stored in an order other than its primary key's, `analysis.spike_events`, under a `MUST`; Part 03 §5.4 gives it, and it satisfies this section because `clock_id` and `time_bucket_tick` are each declared `determined_by` a subset of the key. `core.events` needs no override: its key is `(session_id, stream_id, t_tick)`, the order it is stored in. `core.spike_events` needs none either: its key is `(session_id, unit_id, t_tick)`, and because units are numbered run-major the default order clusters a probe's spikes exactly as the old override did.

### 5.4 The overriding orders

| resource | order |
|---|---|
| `analysis.spike_events` | `session_id, clock_id, time_bucket_tick, unit_id, t_tick` |

A writer **MUST** emit `analysis.spike_events` in that order. It is the one resource whose layout is part of its reason for existing: bucketing by time and sorting by unit within each bucket leaves both columns with informative row-group statistics, so a unit filter and a time filter each prune.

A writer **SHOULD** start a new row group at each bucket boundary. A group cut at a fixed row count straddles boundaries and spans two buckets' worth of time. Row-group size and encoding are otherwise not normative: the right values follow from session length and unit count rather than from the schema.

<a id="ew-parquet-reader-floor" data-spec-anchor="canonical"></a>
### 5.5 The Parquet floor

A reader MUST support footer-reported compressions `UNCOMPRESSED`, `SNAPPY`, `GZIP`, and `ZSTD`;
encodings `PLAIN`, `RLE`, `RLE_DICTIONARY`, and `DELTA_BINARY_PACKED`; data-page types `DATA_PAGE`
and `DATA_PAGE_V2`; and no Parquet modular encryption. A packet writer MUST keep every written
table within that same floor and SHOULD use Zstd. It MUST configure its page type and absence of
encryption before writing, inspect the footer afterwards, and refuse an outside-floor compression
or encoding. `PLAIN_DICTIONARY` is valid upstream but outside this writer floor.

The descriptor is the exact machine-readable owner of these members and declares this interface
`materialized`, `logical_values`, `single_object`, available for packet and external ownership,
with floor role `reader_and_packet_writer`. `FileMetaData.version` is not a substitute for checking
the independent floor features.

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

### 5.6 One null

Under `escapewheel-portable-v0.1` a column value is present or null and there is no second marker. Parquet's definition level carries one bit and Arrow's validity bitmap carries one, so a value that is inapplicable, one that was never recorded, and one a source recorded as unknown all arrive as the same null.

NaN is not the exception it looks like. It is a value of a float column rather than an absent one, so it reaches 30 of the registry's 330 columns and none of the rest, and Parquet's statistics exclude it from a page's bounds — a page holding only NaN publishes no minimum and no maximum.

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

<a id="ew-array-codecs" data-spec-anchor="canonical"></a>
### 6.4 Codecs

A writer MAY use any codec permitted by the applicable Zarr specification, subject to §6.2's
`transpose` prohibition and the regular-grid rule. The resource's own metadata is the sole owner of
the actual pipeline; the manifest does not repeat it.

The descriptor's v3 reader floor is exactly the ordered sequences `bytes`, `bytes` then `gzip`,
and `bytes` then `zstd`. Its v2 reader floor is exactly `filters: null` with compressor null,
compressor `id: zstd`, or compressor `id: blosc` and `cname: zstd`. In a v2 pattern, JSON null
matches only null, every stated member compares equal, and unmentioned configuration members do
not participate. The descriptor declares the Zarr interface `materialized`, `logical_values`, and
`prefix`, with floor role `reader_only`; v3 permits packet and external ownership, while v2 permits
external ownership only. It does not enumerate optional codecs.

<a id="ew-array-metadata-placement" data-spec-anchor="canonical"></a>
### 6.5 What the array declares, and what the tables declare

`core.array_assets` MUST NOT carry dtype or shape. The Zarr array declares them, and restating them buys no otherwise-unavailable access.

The declaration-selected axes table carries axis names, because a Zarr binding in another language
cannot see them. A physical checker resolves that table from the dense-array declaration rather
than from a fixed namespace or resource ID.

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

### 8.1 Packet-owned bytes

A writer MUST NOT modify a resource the packet owns once it is committed. A correction is a new packet version, not an edit.

This promise is what allows an amendment to skip revalidating untouched files, so it is verified rather than assumed: a writer records a checksum for every packet-owned resource (§10).

### 8.2 External bytes

This specification promises nothing about bytes the packet does not own. What a packet records about an external resource is what was true when it was checked, not a claim about now.

## 9. Amendment, versioning, and retention

### 9.1 What an amendment is

An **amendment** produces a new version of an existing packet and MUST NOT modify any file the superseded manifest names. A table that gains rows is written as a **new file**, and the amended manifest names the new file; no byte of the old one changes. Immutability is thereby a property of files, and a resource's *content* may be superseded by naming different bytes.

An amendment MUST set a `packet_version` that sorts strictly after the superseded one, compared as a semantic version.

### 9.2 What an amendment may and may not do

| | |
|---|---|
| Add an analysis resource | MAY |
| Add rows to a provenance table (`core.processing_runs`, `core.source_files`, `core.processing_run_inputs`), as a new file | MAY |
| Remove an analysis resource | MAY — Part 06 makes them disposable |
| Add a core resource | MAY |
| Change the content of a core resource other than the provenance tables | MUST NOT |
| Remove a core resource | MUST NOT |
| Change `packet_id`, `profile_id`, or the standard versions | MUST NOT |

The asymmetry is the design: an amendment **extends** what a packet says and does not revise it. A packet whose core data was wrong is a new packet, not a new version of an old one, because anything already derived from the old core is silently invalidated and nothing in the format can detect that.

Provenance tables are the exception because they are append-only by nature — a row records that something ran, and a later run does not change what an earlier one did.

<a id="ew-superseded-manifest-retention" data-spec-anchor="canonical"></a>
### 9.3 The manifest

Every superseded manifest is retained under `manifests/`, so a later cleanup can distinguish a file an old version named from a file nothing ever named. A retained manifest keeps its own `created_at` and its own validation record; an amendment MUST NOT rewrite either.

Where an amendment binds a different registry document, the packet retains the superseded copy at
the path the superseded manifest records. A writer MUST refuse an amendment that would bind,
anywhere in the packet's current and retained manifests, two different digests under the same
registry ID and version, because that version would then be ambiguous within one packet.

<a id="ew-incremental-revalidation" data-spec-anchor="canonical"></a>
### 9.4 Scope of revalidation

An amendment MUST validate the whole packet, not only what it added. What is bounded is the
*work*, not the verdict: the resources an amendment did not write are immutable, so their
verdict is determined rather than assumed, and re-establishing it costs nothing.

A writer performing an amendment MUST establish the physical order of the resources it writes, and a validator MUST NOT
require it to re-establish that order for any other packet-owned resource.

A validator MUST derive a complete input set from the layer that owns each check. A generated
Tier 1 check takes its inputs from the registry declarations that generated it: the attached
resource, both ends of a foreign key, and every specialization or discriminator branch it reads.
A Tier 2 check takes its inputs from the parsed base-resource set Part 11 §3 requires static
validation to return. A Part 05 shim check declares its inputs explicitly.

A validator MUST re-run a check when it is attached to a resource the amendment writes or any
member of its input set was written. A Tier 2 dependency MUST NOT be inferred by searching query
text: an alias, common table expression, literal, or comment that resembles a resource does not
create one. The session-inventory shim declares the packet manifest and `core.sessions`; installing
a manifest writes the manifest input for this purpose. A shim without a complete declaration MUST
run rather than be skipped.

A validator **MUST make that test over-inclusive where it is uncertain**. Matching a resource name inside
a string literal or a comment re-runs a check that did not need it, which costs time; failing to
match one costs correctness. A validator that cannot show an input is immutable MUST run the
check: skipping a check whose inputs *could* have changed stays forbidden.

### 9.5 Cleanup

Cleanup is a separate operation and MUST proceed orphans first, superseded manifests second. Expiring a manifest first would make an orphan indistinguishable from a stray, permanently.

A writer MUST NOT remove a **stray** — a file no manifest ever named. A packet may carry
files this specification does not govern, and cleanup that deletes the ungoverned is a data-loss
bug wearing an operation's name. The operation reports by default and acts only when asked.

An amendment **MUST NOT** delete anything as part of amending. A file that no manifest
version names any longer MAY be deleted, but by cleanup, as a separate operation — which is what
keeps an amendment's failure from having removed something.

A packet MAY declare its own retention, and a writer SHOULD emit one: how many superseded manifests to keep, and an optional age beyond which one may be dropped. Both are **floors** — a manifest is expired only when both permit it — and both default to one kept version and no age limit, because a packet is archival where a table is operational. A packet never amended retains nothing and carries no `manifests/` directory at all, so the common case costs nothing.

### 9.6 What a version is not

`packet_version` versions the bundle. A writer MUST NOT increment it for a rewrite of a table's rows under a future lakehouse profile.

## 10. Checksums

A writer records a `sha256` over each packet-owned resource by default. This is the one case where a digest verifies what the packet itself claims, and it is cheap: whole-file, one file per resource.

A digest is whole-file, not per-row-group. Parquet cannot be appended to, so "which pages moved" is not a question the format can be asked, and Parquet's own page CRC32 is a corruption detector that a rewritten file passes.

A packet-owned resource recording no digest is not checked, and a verification report MUST state how many it skipped for that reason. A pass that does not say what it skipped reports clean on resources it never looked at.

Verification of external resources is optional and layered (Part 04 §5.3).

## 11. Reaching a source

An adapter reads one source and returns records, and a build assembles a packet from several (Part 05 §3.1). This section is what passes between them: the protocols rows may cross by, what a build supplies an adapter, what a delivery states, and how an adapter declares itself. It is the profile's rather than the pipeline's because every rule in it would change if the profile changed, and because an adapter is the first thing an implementation in another language writes.

An **adapter** here is code that reads one source, whether the reference implementation ships it or a third party does. A clause binding an adapter binds one it does not ship identically.

### 11.1 Protocol groups

A profile names a **group** for each way rows cross a process boundary, and the protocols in it. `escapewheel-portable-v0.1` names one group, out of process, holding three:

| protocol | rows cross as |
|---|---|
| `files-v0.1` | Parquet the recipe names, one file per resource |
| `stream-v0.1` | a sequence of Arrow IPC streams on standard output, each schema naming its resource |
| `flight-v0.1` | Arrow Flight over a Unix socket the build names, one descriptor per resource |

An adapter **released independently of a build** MUST declare and support at least one protocol in a group, and a build MUST support every protocol in every group this profile names. The asymmetry is deliberate: there is one build and there will be many adapters, so no negotiation can fail. A build meeting such an adapter that declares no protocol of the group MUST refuse it, naming the group, before any source is opened.

An adapter a build ships with need not declare one, and a build reaches it directly. The test is the release boundary rather than who wrote the code: an adapter inside a build's distribution is upgraded in the commit that changes a dependency, where one released apart is on the far side of a version boundary the build moves without asking, and the protocol is what keeps that move from being an outage. A build MAY serve an adapter it ships over any protocol of the group, which is how one becomes reachable out of process without declaring anything.

A protocol carries its version in its name, semantically versioned from `v0.1`. A profile MUST NOT change what a named protocol means; a protocol that changes how rows cross is a new member of the group, and a build MUST NOT read support for one version as support for another. Retiring a protocol is a change to this profile and not a decision a build makes.

An adapter a recipe opts into the writer's process (Part 05 §3.9) is bound by this section too: the opt-in decides where a build runs an adapter, not what the adapter supports.

### 11.2 What a build supplies

An adapter MUST declare every value a build supplies it, and a build MUST supply exactly what the adapter declares and MUST NOT decide it from the source's kind. Everything supplied is data: a build MUST NOT require an adapter to accept a live handle — an open store, a connection, an object of the implementation's own — because what crosses a process boundary is text, and an adapter with two ways in has one that depends on where it is running.

The vocabulary is closed. Each term names one value and the form it takes, so an adapter and a build written by different people pass the same thing:

| term | what a build passes |
|---|---|
| `root` | the source's location as a URI, which the adapter opens for itself |
| `session_id` | the session's own name, never the integer a build assigns (§11.3) |
| `reference_clock` | the reference clock's row: identifier, rational tick rate, origin |
| `clocks` | one such row per clock declared before this source runs |
| `first_samples` | one record per stream: its name, and the integer its samples start at |
| `units` | one record per unit: the source's label for it, and the identifier assigned |
| `wanted` | the resource IDs the recipe leaves this source owning, so it produces no more |
| `array_location` | a location under the staging area to write an array to (§11.3) |
| an option, by its name | the value the recipe carries under it — a `zone`, an `interval_kind` |

A build MUST resolve each declared name against that list first and the recipe's options second, and MUST refuse a recipe where a name resolves to neither. A profile adding a term amends this section.

An adapter MUST declare in `accepts` every option it reads and can be constructed without, and in `needs` every value it cannot; it MUST NOT name one option in both, and MUST NOT name in `accepts` a term of the list above or a term a protocol requires. Declaring a name in `needs` is what makes a recipe carry it, so an option holding a default is declarable only as an accepted one. An adapter MUST apply its own default where the recipe sets no value, so what an omitted option means is the adapter's statement rather than a value the build invents.

A build MUST supply an option the recipe sets and the adapter names in either list, and MUST NOT require a recipe to set one named in `accepts`. A build MUST refuse a recipe whose source entry sets an option the adapter names in neither, naming the source and the option, before any source is opened. A build MUST NOT supply an option the adapter names in neither list, including one it adds itself rather than reading from the recipe, and MUST NOT apply a facility of its own to an adapter that does not name the option carrying it.

A build MUST refuse a recipe where a term the list carries cannot be filled, naming the term and the source, and MUST NOT pass such a term absent or empty: `first_samples` needs a source that states them and `units` one that produced them, and an adapter cannot tell a term nobody filled from one whose value is legitimately empty.

A build MUST pass a collection as records carrying its key as columns. A mapping's keys are a type the crossing does not keep: an integer key returns as a string, and a compound key does not cross at all.

Some terms belong to a protocol rather than to an adapter. `flight-v0.1` requires `socket`, the address to serve on; `files-v0.1` requires `delivery_root`, the directory to write the delivery into; both `files-v0.1` and `stream-v0.1` require `report_path` where a report is expected (Part 09 §5.8). A build MUST supply whichever terms its adapter's protocol requires, and an adapter MUST NOT declare one — declaring the protocol is what asks for it.

What crosses is one JSON object keyed by the term. A build MUST write it to the command's standard input and MUST close that stream when it has, MUST NOT pass it as an argument, and MUST NOT add any argument to the command the recipe carries. An adapter MUST read its standard input to end of file and parse it as that object before it writes any rows, and a build supplies nothing else on that stream. An option appears under `options`, keyed by its name, so no option collides with a term.

An argument list is not the channel because it has a size no profile can raise — 131,072 bytes for one argument on Linux, 32,767 characters for a whole command line on Windows — and a term carrying one record per unit reached 322,799 bytes on a real session, where an adapter's whole object measured 721 against a fixture that had none. Standard input carries nothing under any protocol of the group and has no such limit.

The wanted set is a term a build supplies and an adapter MAY act on. A build settles ownership before any source is opened (Part 05 §3.4), so an adapter told what is wanted may extract no more; acting on it is permitted rather than required, because for some sources producing three resources costs what producing all of them costs, and a build cannot tell an adapter that extracted three from one that extracted everything and discarded the rest.

<a id="ew-referenced-resource-delivery" data-spec-anchor="canonical"></a>
### 11.3 What a delivery states

A delivery carries one table per resource asked for. Which columns that table holds is a statement: an adapter MUST deliver a column wherever any row of that resource carries a value, and an absent column says the source produced no value for it in any row, which is Part 02 §5's presence and nothing else. A build MUST NOT read an absent column as saying anything more.

An adapter MUST hand over identifiers as the names its source used and never as numbers, because a writer mints every assigned identifier packet-wide and the numbers do not exist until it has (Part 05 §8). Types, column order, numbering and the declared sort are the build's: it holds the registry and settles all four on arrival.

A resource an adapter owns and has no rows for MUST arrive empty rather than not arriving. An empty delivery states that the source had nothing to say; a resource that does not arrive states that the run failed, and a build that cannot tell them apart cannot report either.

An adapter's arrays MUST NOT cross as rows. A dense array crosses by identity and location. Where
the packet will own the array, a build MUST supply a location under the staging area (Part 05 §1)
and the adapter MUST write the array there, so commit moves it by the rename Part 05 §6 already
performs. Where the array is external (§8.2), a build supplies no location and the producer returns
the URI its source already has.

**A packet-owned array crosses as the bytes themselves.** A build MUST supply `array_location`,
one directory per source, since two sources may each deliver an asset of one name and a shared
directory would make them one array. The adapter MUST write each array into it as Zarr v3 (§6.1),
in a directory named by the catalog row's `resource_id` with the suffix `.zarr`. The build resolves
the unique catalog-family declaration for that table-and-column pair, uses the row's
`resource_id` as packet identity, and MUST NOT substitute an assigned row ID or source label. It
MUST refuse a delivery where bytes and catalog rows do not bind one-to-one.

Nothing else crosses for such an array, and a build MUST NOT require an adapter to restate a Zarr
version, codec pipeline, layout, or other self-describing physical fact. A build inspects reachable
output as needed; `size_bytes` and `sha256` come from the packet-owned bytes it digests (Part 03
§8.1). An adapter delivering an array therefore writes bytes where one delivering rows performs no
I/O at all, which is the cost of an array not being records.

**A referenced resource crosses as a resource document.** An adapter that delivers one MUST
deliver that document with it, under the reserved resource identifier `resources` (§11.4): a JSON
object carrying `resources`, an array with one entry per such resource. Each entry is a manifest
resource entry as [Part 04 §4.1](04_packet_catalog.md#ew-packet-resource-entry-fields) declares
one, without the members a build supplies, so it MUST NOT carry `validation_state` or
`derived_from`. A build preserves that binding, rejects one that does not resolve or admit the
resource ID, and merges the entry into the manifest. Its shape is the delivery schema §1
incorporates. A build MUST refuse a document that does not satisfy it before writing a manifest,
naming what is wrong.

The document is part of the delivery and not a report. A build MUST NOT require a report and MUST NOT fail on one's contents (Part 09 §5.8), so a fact a manifest cannot be written without does not travel in one; a resource that does not arrive is already a failed run (Part 05 §4.4), which is the rule this needs and does not restate. A build MUST NOT count the document among the resources the recipe left the source owning.

### 11.4 The Arrow IPC floor

An Arrow IPC stream carries one schema and an adapter returns many resources, so under `stream-v0.1` the streams concatenate: each ends with the format's own end-of-stream marker, and the resource identifier rides in the schema's key-value metadata under the key `resource_id`. That key and two reserved values of it — `end`, and `resources` for the document §11.3 requires of an adapter delivering a referenced resource — are the whole of what this protocol adds to Arrow. A resource identifier is dotted, so no undotted token collides with either. A document carried this way travels as text in a single-row table rather than as a column per field, so the manifest's schema stays the one description of an entry.

"Arrow IPC" names a family, so this profile pins one member of it, as §5.5 pins Parquet's compressions. An adapter MUST write uncompressed record-batch bodies at metadata version V5, and MUST send each dictionary whole rather than as a delta against one already sent. Compressing buys nothing on a pipe and costs an adapter author a codec in a language whose Arrow binding may not carry one; V5 has been the default since Arrow 1.0, and a delta dictionary is the least evenly implemented part of the format.

An adapter MUST terminate every resource's stream with the end-of-stream marker and a build MUST consume exactly to it, so the next resource's schema begins at the next byte. An adapter that omits one delivers bytes no reader can frame; a build that consumes past one loses every resource after it and reports a truncation on a delivery that finished.

A reader treats end of file as end of stream, so a delivery cut at a message boundary parses clean and cannot be told from a short one. `stream-v0.1` therefore ends a delivery with an empty stream whose `resource_id` is `end`. A build MUST refuse a delivery that did not end with it, and MUST name the last resource it read as the one the adapter died inside rather than the first that never arrived. A resource identifier is dotted, so no undotted token can collide with the reserved value.

Where rows travel on standard output they are bytes. An adapter MUST write the stream to a binary handle and a build MUST read one, because a platform translating a line ending corrupts the stream, which then fails as malformed data rather than as an encoding error.

<a id="ew-adapter-declaration-document" data-spec-anchor="canonical"></a>
### 11.5 The declaration document

A build reads what an adapter declares before it opens any source, and for a class it reads that by importing the adapter — which this section forbids requiring. An adapter a build cannot import MUST publish its declarations as a JSON document the recipe names, and a build MUST read that document before it launches anything.

The document carries what belongs to the adapter and nothing that belongs to the machine: `kind`, `protocol`, `produces`, `contributes`, `states`, `needs`, `accepts` and `consumes`. The command, the root and the options stay in the recipe, because which interpreter is installed where is the recipe author's fact and the resources an adapter can supply is not. Its shape is published as `registry/adapter.schema.json`.

A document carries `accepts` where the adapter names any, as an array of option names in the same form as `needs`, and a build MUST read a document without it as an adapter accepting no option beyond what it needs. A document written before `accepts` existed therefore accepts none, and a recipe setting an option for such an adapter is refused until its document declares one.

A document carries `contributes` where the adapter supplies any resource only in part (Part 05 §3.4), as an array of dotted resource identifiers, and a build MUST read a document without it as declaring none.

A build MUST treat a document and an importable declaration of the same facts as one declaration, and MUST NOT prefer either where both are present. An implementation shipping both MUST generate the document rather than maintain it.

A build MUST refuse a declaration whose `protocol` names no protocol of a group this profile names, whose `produces` names a resource no loaded registry declares, whose `contributes` names a resource its `produces` does not, whose `states` names a field no recipe block carries, or whose `needs` names what §11.2 resolves to neither a term nor an option. A build MUST also refuse one whose `accepts` names a term, names an option its `needs` also names, or is not an array of names. None of those need the adapter opened or imported.

`states` names the recipe fields a source can state and the values need the source read, so no static document carries them: they travel under `stated` in the run's report (Part 09 §5.8), keyed by the same `block.field` name. An adapter declaring a non-empty `states` MUST return them. A build MUST read a declared field absent from the report as unstated rather than as disagreeing, since a source stating nothing is a fact and not a mismatch (Part 05 §3.6).

### 11.6 Reaching an adapter that must be running

Where a protocol needs the adapter running — `flight-v0.1` does, `files-v0.1` and `stream-v0.1` do not — the protocol MUST say how a build establishes that. `flight-v0.1` says it by connection: a build retries the address it supplied until the socket answers or the adapter's process exits, and reports the exit. A readiness line on standard output is weaker, because a build waiting for a line that never comes cannot tell *not yet* from *never* unless it watches the process as well, which is the whole of what retrying already does.

The retry puts one obligation on the adapter: it MUST NOT bind before it can answer `ListFlights`. A build's first call arrives as soon as the socket answers, so an adapter that binds and then extracts serves discovery from a half-built server.

A build that started a process owns it and terminates it once it holds the rows and the report, so an adapter MUST NOT rely on running code after its last response.

<a id="ew-portable-profile-normative-references" data-spec-anchor="canonical"></a>
## 12. Normative references

The application column states the extent to which this part invokes each external authority:

| reference | candidate edition | application |
|---|---|---|
| [Apache Parquet format](https://github.com/apache/parquet-format), including [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md) | unversioned | Parquet files and logical types |
| [Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html), [IPC](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc), and [Flight](https://arrow.apache.org/docs/format/Flight.html) | unversioned | Arrow data, IPC, and Flight |
| [Zarr v3 core](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html), [data types](https://zarr-specs.readthedocs.io/en/latest/v3/data-types/index.html), [regular chunk grid](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-grids/regular-grid/index.html), and [default chunk-key encoding](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-key-encodings/default/index.html) | core v3.0; other entries unversioned | Zarr v3 arrays |
| Zarr v3 [Bytes](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/bytes/), [Gzip](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/gzip/), [Blosc](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/blosc/), [CRC32C](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/crc32c/), [transpose](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/transpose/), and [sharding-indexed](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/) codec specifications | unversioned | permitted Zarr v3 codec pipeline components |
| [Zarr v3 Zstandard codec specification](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/zstd/) | unversioned | `zstd` codec metadata object and configuration |
| [Zarr v2 storage specification](https://zarr-specs.readthedocs.io/en/latest/v2/v2.0.html) | 2.0 | permitted external Zarr v2 arrays |
| [RFC 8878](https://www.rfc-editor.org/info/rfc8878) | exact | Zstandard framing |
| [RFC 1952](https://www.rfc-editor.org/info/rfc1952) | exact | gzip member format of a bound registry (§3.3) |
| [RFC 1951](https://www.rfc-editor.org/info/rfc1951) | exact | DEFLATE compression of a bound registry (§3.3) |

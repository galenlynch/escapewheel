# Part 03 — Portable Physical Profile

Normative. Profile identifier: `escapewheel-portable-v0.1`.

## 1. Scope

This part defines how the logical resources of Part 02 are stored in the portable profile. A packet under this profile MUST be readable without a server.

This part is normative for a packet whose manifest declares `profile_id: escapewheel-portable-v0.1` and binds no other packet. It is the only part whose rules may depend on a storage technology (R93 §3.2). Where a number here supports a rule rather than stating one, the rule stays and the number is Part 10's (R93 §3.4).

## 2. Required technologies

| resource kind | format |
|---|---|
| catalog | JSON |
| tables | Apache Parquet |
| dense arrays | Zarr, v3 for packet-owned arrays (§6.1) |
| media | ordinary containers, such as MP4 |
| documents | Markdown, JSON, text, or PDF |

## 3. Directory layout

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

  extensions/       <name>.json             extension registries

  schemas/
    logical_schemas.json                    the embedded registry

  manifests/        <packet_version>.json   superseded manifests

  docs/                                     human-readable sidecars

  validation/       validation_report.json
```

The catalog MUST record the actual layout. A reader MUST resolve resources through the catalog and MUST NOT infer them from paths.

### 3.2 Files that MUST NOT be written

`schemas/semantic_version.txt` is struck (R62 §2). It restated `semantic_standard_version`, which the catalog is required to carry, and so bought no otherwise-available access.

## 4. URI rules

A URI in the catalog or in a table MAY be relative to the packet root or absolute, or — where the entry names a `source` — relative to that source (Part 04 §5.5). A portable local packet SHOULD use relative URIs.

An absolute URI MAY name an external asset. A catalog entry for an external asset MUST declare it external (Part 04 §5).

A packet root MAY itself be an object-store prefix rather than a directory, in which case a relative URI resolves under that prefix (Part 00 §3).

## 5. Table storage

### 5.1 Encoding

A table MUST be a valid Parquet file. Compression SHOULD be Zstandard where available.

A large table SHOULD use row groups sized for analytical scans. Part 10 carries the sizes measured for one (R93 §3.4).

An identifier column is `int32`, or `int64` where its range requires it (Part 02 §5.3) and MUST NOT be dictionary-encoded in a way that requires unification across row groups before it can be compared.

### 5.2 Partitioning

A large multi-session table SHOULD be partitioned by `session_id`. A table MUST NOT be partitioned by `unit_id`, which produces many small files.

A partitioned table's row order across files is not defined by this profile. A single file is therefore preferred where the table's sort is load-bearing.

### 5.3 Ordering

A table MUST be stored in an order that settles its primary key by adjacency: every key column appears in the sort, and every sort column up to and including the last key column is either a key column itself or one the registry declares `determined_by` a subset of the key (`02` §8.5). Where the registry declares no sort for a table, the order required is its primary key's. A validator MUST report a departure as an **error** (R92 §2.2).

Two rows sharing a key are then neighbours, because nothing in the sort can order between them: a column that is a function of the key takes the same value in both. So the scan that establishes order settles uniqueness in the same pass, which is the means `02` §10.1 leaves to a profile to supply. A validator establishes order by scan rather than by query, because physical order is not visible to SQL (R12 §4, `02` §10.3).

The scan MUST verify each `determined_by` declaration it relies on: of two adjacent rows sharing a primary key, every sort column declared `determined_by` a subset of that key MUST hold the same value in both, and a validator MUST report a difference as an **error** (R92 §2.3). A wrong declaration otherwise waives a check rather than failing one. The comparison reaches a declaration that is false between two adjacent rows, which the scan reports as a duplicate key as well, the second finding saying which to repair; a declaration false enough to sort two duplicates apart is beyond a scan of neighbours.

Where the scan finds a departure, uniqueness MUST be settled by aggregate rather than by adjacency, since a duplicate anywhere but beside its twin is invisible to a scan of neighbours.

A reader MUST NOT depend on stored order for correctness. Establishing the order is the validator's work, and a reader that assumed it would be trusting a property of the profile rather than of the logical standard.

One table is stored in an order other than its primary key's, `analysis.spike_events`, under a `MUST` (R30 §3.2); `03` §5.4 gives it, and it satisfies this section because `clock_id` and `time_bucket_tick` are each declared `determined_by` a subset of the key. `core.events` needs no override: R91 §3.2 keys it on `(session_id, stream_id, t_tick)`, the order it is stored in. `core.spike_events` needs none either: R81 §2.4 makes its key `(session_id, unit_id, t_tick)`, and because units are numbered run-major the default order clusters a probe's spikes exactly as the old override did.

### 5.4 The overriding orders

| resource | order |
|---|---|
| `analysis.spike_events` | `session_id, clock_id, time_bucket_tick, unit_id, t_tick` |

A writer **MUST** emit `analysis.spike_events` in that order (R30 §3.2). It is the one resource whose layout is part of its reason for existing: bucketing by time and sorting by unit within each bucket leaves both columns with informative row-group statistics, so a unit filter and a time filter each prune.

A writer **SHOULD** start a new row group at each bucket boundary (R30 §3.3). A group cut at a fixed row count straddles boundaries and spans two buckets' worth of time. Row-group size and encoding are otherwise not normative: the right values follow from session length and unit count rather than from the schema.

### 5.5 The Parquet floor

A reader MUST support the compressions **uncompressed, Snappy, Gzip and Zstd**. A writer MUST use
one of those four and SHOULD use Zstd (R3 §2). Dictionary, RLE and delta encodings MAY be used and
MUST be supported by readers.

A writer SHOULD encode tick columns with `DELTA_BINARY_PACKED` and SHOULD NOT dictionary-encode
them. On a high-cardinality tick column a writer builds a dictionary nearly as large as the column,
abandons it at its size threshold, and emits a mix of partial-dictionary and plain pages larger
than either encoding alone.

A writer SHOULD encode with `DELTA_BINARY_PACKED`, and SHOULD NOT dictionary-encode, the first
column of a table's sort order whose role is `identifier` (R110 §3.1). Sorting a table by its key
(R10 §2) makes that column ascend across the whole table, which is what delta encoding exists for
and which no later key column has. `session_id` is not that column, being one value in a
single-session packet and already 0.03 bits a row under run-length encoding; a writer skips it and
takes the next.

A writer SHOULD NOT dictionary-encode a floating-point column, and SHOULD write one whose values
repeat as a declared exception (R110 §3.2). Repetition is what a dictionary indexes, and four
floats in five do not repeat enough to pay for one.

Neither rule is the property it stands in for, so a writer MUST be able to override each per
column, and every override MUST record what it measured and on what (R110 §3.3). An exception
recording nothing cannot be re-judged when the data changes. A writer SHOULD refuse an exception
naming a column no table declares, which is decidable with no packet in hand.

A writer SHOULD report, at `info`, a column whose encoding costs more than **1.5x** the smallest
available to it, measured over a sample of the rows it wrote (R110 §3.5). These rules are good
guesses, and the report is how the author of a table learns that theirs is one a guess misses. A
report and not a refusal: every encoding above is permitted, so a packet is conforming whichever
it uses.

Wall-clock timestamps MUST be Parquet `TIMESTAMP` with `isAdjustedToUTC=true` and `MICROS`
precision; A wall-clock column MUST NOT use `INT96`. Dates MUST be Parquet `DATE`, int32 days since the Unix epoch.

### 5.6 One null

Under `escapewheel-portable-v0.1` a column value is present or null and there is no second marker. Parquet's definition level carries one bit and Arrow's validity bitmap carries one, so a value that is inapplicable, one that was never recorded, and one a source recorded as unknown all arrive as the same null (R101 §3.10).

NaN is not the exception it looks like. It is a value of a float column rather than an absent one, so it reaches 30 of the registry's 330 columns and none of the rest, and Parquet's statistics exclude it from a page's bounds — a page holding only NaN publishes no minimum and no maximum.

A writer MUST NOT adopt a sentinel value meaning absent; an absent value is null. Where the reason for the absence matters, core records the fact that distinguishes it rather than encoding the reason in the value: R44 §2.3 gave a run a `scope` so an undeterminable one is distinguishable from an unambiguous one, and R22 §3 nulls `normalized_label` where a source's label has no honest projection.

## 6. Array storage

### 6.1 Version

A packet-owned array MUST be Zarr v3 (R21 §3.1). A referenced array MAY be Zarr v2, because a packet does not control how an external producer wrote it.

An array MUST use a **regular chunk grid** (R3 §7.1): every chunk the same shape, the last along each axis permitted to be partial. An irregular grid is expressible in Zarr and is not readable by every binding.

Stated as the prohibition a validator can check: `physical_profile: "zarr_v2"` MUST NOT appear on a resource that is not `external: true` (R21 §3.2).

Each array resource declares its own Zarr version in the catalog. A reader MUST check a resource's `physical_profile` together with its `codecs` before opening it, and MUST fail **for that resource**, naming whichever it lacks — the per-resource degradation R15 §2 requires applies to the version as much as to the codec, because a reader may support a codec in one Zarr version and not the other.

### 6.2 Axis order

Array axes are stored order, slowest-varying first (R3 §5). An array's codec chain MUST NOT include `transpose`.

A column-major binding enumerates axes in reverse. The client adapts; the format does not.

### 6.3 Axis coordinates

Every axis MUST declare its coordinates in `core.array_dimensions`, in one of the forms of R20 §2. A regularly sampled axis declares an origin tick, a step, and a length rather than storing per-sample values.

A step MAY be rational, declared as a numerator and denominator (R33 §2): a 30 ms bin at 31,250 Hz is 937.5 ticks.


An axis MUST declare no more than one coordinate form: two descriptions of the same positions can disagree and nothing would say which governs (R20 §3).

A rational step is a numerator and a denominator. `step_tick_den`, where present, MUST be positive, the numerator MUST be present wherever an origin is, and the pair SHOULD be in lowest terms so two packets describing the same axis describe it identically (R33 §2).

Where an array declares both a sampling rate and a regular tick axis, the two describe the same thing and MUST agree (R20 §4). The rate is retained as a validated denormalization, not as a second source of truth.

### 6.4 Codecs

A writer MAY use any Zarr codec. The catalog MUST name every codec a resource uses. A reader MUST check a resource's declared codecs before opening it, and MUST fail naming what it lacks rather than returning partial data (R14 §2.2, R15 §2).

The floor a reader is required to support is stated per Zarr version, because implementations differ between them (R21 §3):

| `physical_profile` | a reader MUST support | a writer MAY also use |
|---|---|---|
| `zarr_v3` | `none`, `gzip`, `zstd` | `blosc` (cname=zstd, shuffle=shuffle), `sharding_indexed` |
| `zarr_v2` | `none`, `zstd`, `blosc` (cname=zstd) | — |

The asymmetry between the versions is measured, not chosen: `gzip` is in the v3 floor and not the v2 one because a v2 array compressed with gzip raises `KeyError: "gzip"` in a reader that reads every other combination. Codecs are declared per resource, not per packet: a reader MUST NOT refuse a packet over a codec used only by resources it does not open. The catalog's packet-level codec list is their union, for a whole-packet capability answer.

### 6.5 What the array declares, and what the tables declare

`core.array_assets` MUST NOT carry dtype or shape. The Zarr array declares them, and restating them buys no otherwise-unavailable access (R3 §3.0).

`core.array_dimensions` carries axis names, because a Zarr binding in another language cannot see them.

Zarr attributes MAY duplicate helpful metadata. Metadata required for validation MUST also be represented in tables or the catalog, so that it is not reachable only through an array store.

## 7. Metadata placement

| kind | location |
|---|---|
| packet-level facts | the catalog |
| queryable scientific facts | tables |
| semi-structured, lab-specific values | a `json_string` column, or a sidecar |
| human-readable context | `docs/` |

A value used for filtering, grouping, joining, or validation MUST be a first-class typed column.

## 8. Immutability

### 8.1 Packet-owned bytes

A writer MUST NOT modify a resource the packet owns once it is committed (R14 §2.3). A correction is a new packet version, not an edit.

This promise is what allows an amendment to skip revalidating untouched files (R35 §2), so it is verified rather than assumed: a writer records a checksum for every packet-owned resource (§10).

### 8.2 External bytes

This specification promises nothing about bytes the packet does not own. What a packet records about an external resource is what was true when it was checked, not a claim about now (R14 §2.3.1).

## 9. Amendment, versioning, and retention

### 9.1 What an amendment is

An **amendment** produces a new version of an existing packet and MUST NOT modify any file the superseded manifest names (R32 §2). A table that gains rows is written as a **new file**, and the amended manifest names the new file; no byte of the old one changes. Immutability is thereby a property of files, and a resource's *content* may be superseded by naming different bytes.

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

### 9.3 The manifest

Every superseded manifest is retained under `manifests/` (R32 §4), so a later cleanup can distinguish a file an old version named from a file nothing ever named. A retained manifest keeps its own `created_at` and its own validation record; an amendment MUST NOT rewrite either.

Where an amendment installs a different registry, the packet retains the superseded copy alongside it (R32 §4.1). Installing different content under a `registry_version` the packet has already retained makes that version ambiguous **within one packet**, and a writer MUST refuse it.

### 9.4 Scope of revalidation

An amendment MUST validate the whole packet, not only what it added (R32 §5). What R35 bounds is
the *work*, not the verdict: the resources an amendment did not write are immutable, so their
verdict is determined rather than assumed, and re-establishing it costs nothing.

A writer performing an amendment MUST establish the physical order of the resources it writes, and a validator MUST NOT
require it to re-establish that order for any other packet-owned resource (R35 §4).

A validator MUST re-run a check when it is **attached to** a resource the amendment writes, **or when its
query names one**; a check meeting neither condition MAY be skipped (R35 §2). The second test is
syntactic — a generated check refers to a resource by its flattened name — so a rule that names a
resource added later is caught without the registry having to declare that it might.

A validator **MUST make that test over-inclusive where it is uncertain** (R35 §5). Matching a resource name inside
a string literal or a comment re-runs a check that did not need it, which costs time; failing to
match one costs correctness. A validator that cannot show an input is immutable MUST run the
check (R35 §6): skipping a check whose inputs *could* have changed stays forbidden, which is what
R32 §5 was protecting.

### 9.5 Cleanup

Cleanup is a separate operation and MUST proceed orphans first, superseded manifests second (R61 §2.1). Expiring a manifest first would make an orphan indistinguishable from a stray, permanently.

A writer MUST NOT remove a **stray** — a file no manifest ever named (R61 §2.1). A packet may carry
files this specification does not govern, and cleanup that deletes the ungoverned is a data-loss
bug wearing an operation's name. The operation reports by default and acts only when asked.

An amendment **MUST NOT** delete anything as part of amending (R32 §6). A file that no manifest
version names any longer MAY be deleted, but by cleanup, as a separate operation — which is what
keeps an amendment's failure from having removed something.

A packet MAY declare its own retention, and a writer SHOULD emit one (R61 §2.2): how many superseded manifests to keep, and an optional age beyond which one may be dropped. Both are **floors** — a manifest is expired only when both permit it — and both default to one kept version and no age limit, because a packet is archival where a table is operational. A packet never amended retains nothing and carries no `manifests/` directory at all, so the common case costs nothing.

### 9.6 What a version is not

`packet_version` versions the bundle. A writer MUST NOT increment it for a rewrite of a table's rows under a future lakehouse profile (R61 §4).

## 10. Checksums

A writer records a `sha256` over each packet-owned resource by default (R52 §2). This is the one case where a digest verifies what the packet itself claims, and it is cheap: whole-file, one file per resource.

A digest is whole-file, not per-row-group. Parquet cannot be appended to, so "which pages moved" is not a question the format can be asked, and Parquet's own page CRC32 is a corruption detector that a rewritten file passes.

A packet-owned resource recording no digest is not checked, and a verification report MUST state how many it skipped for that reason (R52 §2.3). A pass that does not say what it skipped reports clean on resources it never looked at.

Verification of external resources is optional and layered (Part 04 §5.3).

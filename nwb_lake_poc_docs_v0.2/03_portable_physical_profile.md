# Part 03 — Portable Physical Profile

Normative. Profile identifier: `nwb-lake-portable-v0.1`.

## 1. Scope

This part defines how the logical resources of Part 02 are stored in the portable profile. A packet under this profile MUST be readable without a server.

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
  nwb.packet.json

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

A URI in the catalog or in a table MAY be relative to the packet root or absolute. A portable local packet SHOULD use relative URIs.

An absolute URI MAY name an external asset. An external asset MUST be declared as such in the catalog (Part 04 §5).

## 5. Table storage

### 5.1 Encoding

A table MUST be a valid Parquet file. Compression SHOULD be Zstandard where available.

A large table SHOULD use row groups sized for analytical scans; 100,000 to 1,000,000 rows is a starting point to be adjusted by profiling.

An identifier column is `int32`, or `int64` where its range requires it (Part 02 §5.3) and MUST NOT be dictionary-encoded in a way that requires unification across row groups before it can be compared.

### 5.2 Partitioning

A large multi-session table SHOULD be partitioned by `session_id`. A table MUST NOT be partitioned by `unit_id`, which produces many small files.

A partitioned table's row order across files is not defined by this profile. A single file is therefore preferred where the table's sort is load-bearing.

### 5.3 Ordering

Physical order is normative, not advisory: a reader relies on it for pruning, and a validator establishes it by scan rather than by query (Part 02 §10.3).

A writer MUST sort every table by its primary key except where §12 of Part 02 overrides it.

## 6. Array storage

### 6.1 Version

A packet-owned array MUST be Zarr v3. A referenced array MAY be Zarr v2, because a packet does not control how an external producer wrote it (R21 §3).

Each array resource declares its own Zarr version in the catalog.

### 6.2 Axis order

Array axes are stored order, slowest-varying first (R3 §5). The `transpose` codec MUST NOT be used.

A column-major binding enumerates axes in reverse. The client adapts; the format does not.

### 6.3 Axis coordinates

Every axis MUST declare its coordinates in `core.array_dimensions`, in one of the forms of R20 §2. A regularly sampled axis declares an origin tick, a step, and a length rather than storing per-sample values.

A step MAY be rational, declared as a numerator and denominator (R33 §2): a 30 ms bin at 31,250 Hz is 937.5 ticks.

### 6.4 Codecs

A writer MAY use any Zarr codec. The catalog MUST name every codec a resource uses. A reader MUST check a resource's declared codecs before opening it, and MUST fail naming what it lacks rather than returning partial data (R14 §2.2, R15 §2).

The floor a reader is required to support is stated per Zarr version, because implementations differ between them. Codecs are declared per resource, not per packet: a reader MUST NOT refuse a packet over a codec used only by resources it does not open. The catalog's packet-level codec list is their union, for a whole-packet capability answer.

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

A resource the packet owns MUST NOT be modified in place once committed (R14 §2.3). A correction is a new packet version, not an edit.

This promise is what allows an amendment to skip revalidating untouched files (R35 §2), so it is verified rather than assumed: a writer records a checksum for every packet-owned resource (§10).

### 8.2 External bytes

This specification promises nothing about bytes the packet does not own. What a packet records about an external resource is what was true when it was checked, not a claim about now (R14 §2.3.1).

## 9. Amendment, versioning, and retention

### 9.1 Adding a resource

Adding a resource to a committed packet produces a new `packet_version` and modifies no existing file. Every superseded manifest is retained (R32 §4), so that a later cleanup can distinguish a file an old version named from a file nothing ever named.

### 9.2 Scope of revalidation

An amendment re-establishes physical order only for what it writes, and re-runs only the rules naming an added resource (R35 §2).

### 9.3 Cleanup

Cleanup is a separate operation and MUST proceed orphans first, superseded manifests second (R61 §2.1). Expiring a manifest first would make an orphan indistinguishable from a stray, permanently.

A **stray** — a file no manifest ever named — MUST NOT be removed. The operation reports by default and acts only when asked.

A packet MAY declare its own retention, and a writer SHOULD emit one (R61 §2.2): how many superseded manifests to keep, and an optional age beyond which one may be dropped. Both are **floors** — a manifest is expired only when both permit it — and both default to one kept version and no age limit, because a packet is archival where a table is operational. A packet never amended retains nothing and carries no `manifests/` directory at all, so the common case costs nothing.

### 9.4 What a version is not

`packet_version` versions the bundle. It MUST NOT be incremented for a rewrite of a table's rows under a future lakehouse profile (R61 §4).

## 10. Checksums

A writer records a `sha256` over each packet-owned resource by default (R52 §2). This is the one case where a digest verifies what the packet itself claims, and it is cheap: whole-file, one file per resource.

A digest is whole-file, not per-row-group. Parquet cannot be appended to, so "which pages moved" is not a question the format can be asked, and Parquet's own page CRC32 is a corruption detector that a rewritten file passes.

A packet-owned resource recording no digest is not checked, and a verification report MUST state how many it skipped for that reason (R52 §2.3). A pass that does not say what it skipped reports clean on resources it never looked at.

Verification of external resources is optional and layered (Part 04 §5.3).

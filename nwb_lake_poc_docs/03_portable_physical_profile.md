# 03 - Portable Physical Profile

## Scope

This document defines the first physical profile: `nwb-lake-portable-v0.1`.

This profile is intended for local filesystems, shared filesystems, and object-store prefixes. It MUST be readable without a server.

## Required technologies

A conforming portable packet uses:

```text
packet catalog: JSON
tables: Parquet
arrays: Zarr v3
media: ordinary media files, e.g. MP4
documents: ordinary sidecar files, e.g. Markdown/JSON/text/PDF
```

Parquet is used for logical tables because it is a column-oriented open format designed for efficient storage and retrieval.

Zarr v3 is used for dense arrays because it specifies chunked n-dimensional typed arrays with explicit metadata.

## Directory layout

Recommended layout:

```text
packet_root/
  nwb.packet.json
  README.md

  tables/
    core/
      sessions.parquet
      subjects.parquet
      devices.parquet
      probes.parquet
      electrodes.parquet
      clocks.parquet
      trials.parquet
      events.parquet
      units.parquet
      unit_spike_chunks.parquet
      array_assets.parquet
      array_channels.parquet
      processing_runs.parquet
      source_files.parquet
      provenance_entities.parquet
      provenance_activities.parquet
      provenance_edges.parquet
    analysis/
      trials_wide.parquet
      spike_events.parquet
      spikes_by_trial.parquet

  arrays/
    session_id=<session_id>/
      <array_asset_id>.zarr/

  media/
    session_id=<session_id>/
      <media_asset_id>.mp4

  docs/
    protocol.md
    task_config.json

  validation/
    validation_report.json
    validation_report.md

  schemas/
    semantic_version.txt
    logical_schemas.json
```

Implementations MAY use partitioned Parquet datasets instead of single Parquet files for large tables:

```text
tables/core/unit_spike_chunks/
  session_id=s001/
    part-000.parquet
    part-001.parquet
```

The packet catalog MUST record the actual layout.

## URI rules

URIs in the manifest and tables MAY be relative to packet root or absolute.

Relative URIs SHOULD be preferred in portable local packets.

Absolute URIs MAY be used for external assets, but external assets MUST be explicitly declared in the manifest.

## Table storage rules

### Parquet encoding

Tables MUST be stored as valid Parquet.

Compression SHOULD be Zstd when available.

Large tables SHOULD be written with row groups sized for analytical scans. As a starting point, use row groups in the 100k to 1M row range and adjust after profiling.

### Partitioning

For large multi-session datasets, tables SHOULD be partitioned by `session_id`.

For probe-specific large tables, partitioning by `(session_id, probe_id)` MAY be useful.

Tables SHOULD NOT be partitioned by `unit_id` because that can create too many small files.

### Sorting

The writer SHOULD sort large spike tables and spike chunk tables to support pruning and locality.

Recommended ordering for `core.unit_spike_chunks`:

```text
session_id, sorting_run_id, curation_id, unit_id, chunk_index
```

Recommended ordering for `core.spike_events` or `analysis.spike_events`:

```text
session_id, sorting_run_id, curation_id, unit_id, t_tick
```

Recommended ordering for `core.events`:

```text
session_id, clock_id, t_tick, event_type
```

## Array storage rules

Dense arrays SHOULD be stored as Zarr v3.

The `core.array_assets` table MUST record at least:

- URI;
- dtype;
- shape;
- dimension names;
- semantic type;
- clock ID when time-indexed;
- physical unit/conversion when applicable.

Zarr attrs MAY duplicate helpful metadata, but scientific metadata required for packet validation MUST also be represented in tables or the manifest.

This prevents critical metadata from being trapped only inside array-store attributes.

## Metadata placement rules

Metadata belongs in different places depending on role.

### Packet metadata

Packet-level metadata belongs in `nwb.packet.json`:

- packet ID;
- profile;
- version;
- resource registry;
- schema versions;
- release ID;
- validation report references.

### Queryable scientific metadata

Queryable scientific metadata belongs in tables:

- sessions;
- subjects;
- probes;
- electrodes;
- trials;
- units;
- array assets;
- processing runs;
- provenance.

### Semi-structured metadata

Semi-structured metadata MAY be stored as struct/map columns or JSON string columns.

Fields frequently used in queries SHOULD be promoted to typed columns.

### Human-readable metadata

Human-readable material SHOULD be stored as sidecar documents:

- `docs/protocol.md`;
- `docs/surgery_notes.md`;
- `docs/task_config.json`;
- `docs/calibration_report.pdf`.

The manifest SHOULD reference these documents.

## Immutability and updates

A portable packet SHOULD be treated as immutable after validation.

Corrections SHOULD create a new packet release or new resource version rather than mutating existing validated resources in place.

During development, local mutation is acceptable, but a committed packet MUST have a validation report corresponding to its current bytes.

## Checksums

A portable packet SHOULD include checksums for important files and resource groups.

The checksum policy MAY initially be coarse-grained, e.g. one checksum per Parquet file and one manifest-level hash per Zarr store.

For large Zarr arrays, implementations MAY use per-chunk checksums later.

## Lakehouse upgrade path

The portable profile is the reference implementation. A future Iceberg profile can reuse the same logical schemas.

Migration path:

```text
portable Parquet tables
  -> Iceberg tables backed by the same or rewritten Parquet data

portable Zarr arrays
  -> remain Zarr arrays, with their URIs referenced from Iceberg/manifest metadata
```

Iceberg is a table-management layer. It does not replace the packet catalog or dense array storage.

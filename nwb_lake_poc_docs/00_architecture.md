# 00 - Architecture

## Purpose

This document defines the implementation architecture for **NWB-Lake POC v0.1**. The goal is to make an ecephys data packet that is:

- fast to query;
- easy to create from existing NWB/acquisition/sorting data;
- not locked into Python;
- not dependent on HDMF as a runtime data model;
- compatible with modern commodity tooling;
- precise enough to drive validation and downstream analysis.

The initial proof-of-principle prioritizes `core` and `analysis`. An `nwb` projection is intentionally deferred.

## Core terms

### Semantic standard

The semantic standard defines what concepts mean.

Examples:

- A `Trial` is a bounded interval of experimental time.
- A `Unit` is a sorted or curated spiking entity.
- An `ElectricalSeries` is sampled extracellular voltage over time and channels.

The semantic standard is independent of storage format and independent of whether the logical representation is a table or array.

### Logical standard

The logical standard defines how semantic concepts are represented as computable resources:

- tables;
- dense array assets;
- media assets;
- document assets;
- views;
- materialized tables;
- materialized arrays;
- references between resources.

The logical standard is storage-agnostic but not shape-agnostic. For example, trials are logically table-shaped.

### Physical profile

A physical profile says how logical resources are stored.

Examples:

- Portable profile: Parquet tables, Zarr v3 arrays, JSON manifest.
- Lakehouse profile: Iceberg tables backed by Parquet, Zarr v3 arrays, JSON manifest plus Iceberg catalog references.

### Packet

A packet is a concrete dataset bundle. It can be a local directory, an object-store prefix, or a release manifest that points to distributed assets.

A packet contains:

- a packet catalog/manifest;
- core tables;
- dense arrays;
- optional media;
- optional docs and sidecars;
- optional analysis materializations;
- validation and provenance records.

### Packet catalog

The packet catalog is the dataset-level map. In the portable profile it is `nwb.packet.json`.

It records:

- what resources exist;
- where they live;
- what semantic type they represent;
- what logical schema they use;
- what physical profile they use;
- what resources are canonical;
- what resources are derived;
- what validation reports and provenance activities apply.

### Iceberg catalog

An Iceberg catalog is different from the packet catalog. It is only relevant for the lakehouse profile and only manages tabular Iceberg resources. It does not catalog Zarr arrays, MP4 files, free-form documents, or semantic relationships across the whole packet.

## Layer model

The proof-of-principle uses two primary logical layers and one deferred layer.

```text
core
  Canonical normalized data. This is the source of truth.

analysis
  Derived products optimized for downstream analysis. These are reproducible from core.

nwb
  Deferred compatibility projection. Not required for v0.1 implementation.
```

## Core layer

The core layer MUST contain canonical facts in stable logical schemas.

Core resources SHOULD be normalized enough to avoid drift but pragmatic enough for science. For example:

- `core.trials` is one row per trial.
- `core.units` is one row per unit in a sorting/curation context.
- `core.unit_spike_chunks` is a compact canonical ragged spike-train representation.
- `core.spike_events` MAY also exist, but if both spike representations exist, their relationship MUST be declared.
- `core.array_assets` records dense array assets stored outside tables.

Core resources MUST be validated before commit.

## Analysis layer

The analysis layer MAY contain denormalized, prejoined, binned, aligned, or otherwise transformed products.

Examples:

- `analysis.spike_events`, if `core.unit_spike_chunks` is canonical.
- `analysis.spikes_by_trial`.
- `analysis.trials_wide`.
- `analysis.unit_condition_rates`.
- `analysis.binned_spikes`.
- `analysis.lfp_bandpower`.

Analysis resources MUST declare lineage to core resources.

Analysis resources SHOULD be treated as disposable cache/products unless explicitly promoted into core by a future schema version.

## Deferred NWB projection

The packet SHOULD preserve enough semantic metadata to build an NWB-like projection later. However, v0.1 does not require:

- PyNWB-compatible object reconstruction;
- NWB/HDF5 export;
- NWB-Zarr export;
- a complete mapping to `NWBFile` hierarchy.

The initial goal is to get core data and analysis products correct.

## Storage stance

### Portable profile first

The first implementation SHOULD use:

```text
manifest: JSON
tables: Parquet
arrays: Zarr v3
media: MP4 or ordinary files
docs: Markdown/JSON/text/PDF sidecars
```

This profile MUST be readable without a server.

### Iceberg later

Iceberg SHOULD be treated as a later table-management profile. It is useful when you need:

- table snapshots;
- schema evolution;
- partition evolution;
- concurrent writers;
- cloud catalog integration;
- reproducible release tags across large table collections.

Iceberg MUST NOT be required for the first proof-of-principle.

## Implementation thesis

The correct first implementation is not a generic NWB backend. It is:

1. A spec for core logical resources.
2. A validator for those resources.
3. An importer that turns source data into validated resources.
4. A packet catalog that records the committed resources.
5. A small access library that can query tables and arrays using standard engines.

The importer is successful only when validation succeeds.

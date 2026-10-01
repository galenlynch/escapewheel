# 04 - Packet Catalog / Manifest

## Scope

The packet catalog is the top-level dataset index. In the portable profile it is a JSON file named:

```text
nwb.packet.json
```

It tells readers what resources exist, where they live, what they mean, what schemas they follow, and what validation/provenance applies.

## Catalog principles

The packet catalog MUST be small enough to read quickly.

The packet catalog MUST NOT contain all scientific data.

The packet catalog SHOULD contain resource discovery and binding metadata.

The packet catalog MUST distinguish canonical core resources from derived analysis resources.

## Required top-level fields

```json
{
  "packet_id": "string",
  "packet_version": "0.1.0",
  "profile_id": "nwb-lake-portable-v0.1",
  "semantic_standard_version": "nwb-lake-semantic-v0.1",
  "logical_standard_version": "nwb-lake-logical-v0.1",
  "created_at": "2026-08-25T00:00:00Z",
  "resources": [],
  "validation": {},
  "provenance": {}
}
```

A manifest SHOULD also include:

```json
{
  "dataset_id": "string",
  "release_id": "string",
  "description": "string",
  "creators": ["string"],
  "license": "string",
  "keywords": ["string"],
  "source_summary": {}
}
```

## Resource entries

Every table, array, media object, document, view, materialized table, and materialized array MUST have a resource entry.

### Core table example

```json
{
  "resource_id": "core.trials",
  "layer": "core",
  "kind": "table",
  "semantic_type": "Trial",
  "schema_id": "core.trials.v0.1",
  "physical_profile": "parquet",
  "uri": "tables/core/trials.parquet",
  "canonical": true,
  "validation_state": "passed"
}
```

### Partitioned table example

```json
{
  "resource_id": "core.unit_spike_chunks",
  "layer": "core",
  "kind": "table",
  "semantic_type": "SpikeTrain",
  "schema_id": "core.unit_spike_chunks.v0.1",
  "physical_profile": "parquet_dataset",
  "uri": "tables/core/unit_spike_chunks/",
  "partitioning": ["session_id"],
  "canonical": true,
  "validation_state": "passed"
}
```

### Zarr array asset example

```json
{
  "resource_id": "array.probe0_lfp",
  "layer": "core",
  "kind": "dense_array_asset",
  "semantic_type": "ElectricalSeries",
  "schema_id": "core.array_asset.v0.1",
  "physical_profile": "zarr_v3",
  "uri": "arrays/session_id=s001/probe0_lfp.zarr",
  "catalog_table_ref": "core.array_assets",
  "array_asset_id": "probe0_lfp",
  "validation_state": "passed"
}
```

### Analysis table example

```json
{
  "resource_id": "analysis.spikes_by_trial",
  "layer": "analysis",
  "kind": "materialized_table",
  "semantic_type": "DerivedSpikeTrialAlignment",
  "schema_id": "analysis.spikes_by_trial.v0.1",
  "physical_profile": "parquet",
  "uri": "tables/analysis/spikes_by_trial.parquet",
  "canonical": false,
  "derived_from": [
    "core.unit_spike_chunks",
    "core.trials"
  ],
  "activity_id": "activity.align_spikes_to_trials.20260825T104200",
  "validation_state": "passed"
}
```

### Document example

```json
{
  "resource_id": "docs.protocol",
  "layer": "docs",
  "kind": "document_asset",
  "semantic_type": "ProtocolDocument",
  "physical_profile": "markdown",
  "uri": "docs/protocol.md"
}
```

## Canonical representation registry

For resource families that may have multiple representations, the manifest MUST declare canonical status.

Spike example:

```json
{
  "canonical_representations": {
    "spikes": [
      {
        "session_id": "s001",
        "sorting_run_id": "sort_ks4_001",
        "curation_id": "curation_001",
        "canonical_resource": "core.unit_spike_chunks",
        "derived_resources": [
          "analysis.spike_events",
          "analysis.spikes_by_trial"
        ]
      }
    ]
  }
}
```

## Validation block

The manifest MUST include validation status.

```json
{
  "validation": {
    "status": "passed",
    "validated_at": "2026-08-25T17:42:00Z",
    "validator_name": "nwb_lake_validate",
    "validator_version": "0.1.0",
    "report_uri": "validation/validation_report.json"
  }
}
```

If validation failed, the packet MUST NOT present itself as an import-complete core packet.

## Provenance block

The manifest SHOULD summarize provenance locations:

```json
{
  "provenance": {
    "entities_resource": "core.provenance_entities",
    "activities_resource": "core.provenance_activities",
    "edges_resource": "core.provenance_edges",
    "import_activity_id": "activity.import.s001.20260825T104200"
  }
}
```

Detailed provenance belongs in tables, not the manifest.

## Iceberg profile entries

In a future lakehouse profile, table resources MAY point to Iceberg tables instead of Parquet files.

Example:

```json
{
  "resource_id": "core.trials",
  "layer": "core",
  "kind": "table",
  "semantic_type": "Trial",
  "schema_id": "core.trials.v0.1",
  "physical_profile": "iceberg",
  "iceberg": {
    "catalog_type": "rest",
    "catalog_uri": "https://catalog.example.org",
    "namespace": "nwb_lake.s001",
    "table": "trials",
    "snapshot_id": 123456789
  },
  "canonical": true
}
```

The packet catalog still exists in this profile because Iceberg does not catalog non-table resources such as Zarr arrays, media files, document sidecars, or semantic cross-resource bindings.

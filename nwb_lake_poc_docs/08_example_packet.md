# 08 - Example Packet

This document gives a minimal concrete packet example.

## Directory layout

```text
session_001.nwbpkt/
  nwb.packet.json
  README.md

  tables/
    core/
      sessions.parquet
      subjects.parquet
      clocks.parquet
      trials.parquet
      units.parquet
      sorting_runs.parquet
      curation_versions.parquet
      unit_spike_chunks.parquet
      processing_runs.parquet
      provenance_entities.parquet
      provenance_activities.parquet
      provenance_edges.parquet
    analysis/
      spike_events.parquet
      spikes_by_trial.parquet

  arrays/
    session_id=s001/
      probe0_lfp.zarr/

  validation/
    validation_report.json
    validation_report.md

  docs/
    protocol.md
```

## Minimal manifest

```json
{
  "packet_id": "session_001",
  "packet_version": "0.1.0",
  "profile_id": "nwb-lake-portable-v0.1",
  "semantic_standard_version": "nwb-lake-semantic-v0.1",
  "logical_standard_version": "nwb-lake-logical-v0.1",
  "created_at": "2026-08-25T17:42:00Z",
  "dataset_id": "example_dataset",
  "release_id": "dev_001",
  "resources": [
    {
      "resource_id": "core.sessions",
      "layer": "core",
      "kind": "table",
      "semantic_type": "Session",
      "schema_id": "core.sessions.v0.1",
      "physical_profile": "parquet",
      "uri": "tables/core/sessions.parquet",
      "canonical": true,
      "validation_state": "passed"
    },
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
    },
    {
      "resource_id": "core.unit_spike_chunks",
      "layer": "core",
      "kind": "table",
      "semantic_type": "SpikeTrain",
      "schema_id": "core.unit_spike_chunks.v0.1",
      "physical_profile": "parquet",
      "uri": "tables/core/unit_spike_chunks.parquet",
      "canonical": true,
      "validation_state": "passed"
    },
    {
      "resource_id": "analysis.spike_events",
      "layer": "analysis",
      "kind": "materialized_table",
      "semantic_type": "SpikeEvent",
      "schema_id": "analysis.spike_events.v0.1",
      "physical_profile": "parquet",
      "uri": "tables/analysis/spike_events.parquet",
      "canonical": false,
      "derived_from": ["core.unit_spike_chunks"],
      "activity_id": "activity.materialize_spike_events.001",
      "validation_state": "passed"
    },
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
  ],
  "canonical_representations": {
    "spikes": [
      {
        "session_id": "s001",
        "sorting_run_id": "sort_001",
        "curation_id": "curation_001",
        "canonical_resource": "core.unit_spike_chunks",
        "derived_resources": ["analysis.spike_events"]
      }
    ]
  },
  "validation": {
    "status": "passed",
    "validated_at": "2026-08-25T17:42:00Z",
    "validator_name": "nwb_lake_validate",
    "validator_version": "0.1.0",
    "report_uri": "validation/validation_report.json"
  },
  "provenance": {
    "entities_resource": "core.provenance_entities",
    "activities_resource": "core.provenance_activities",
    "edges_resource": "core.provenance_edges",
    "import_activity_id": "activity.import.001"
  }
}
```

## Example rows

### `core.clocks`

| clock_id | session_id | name | tick_rate_hz | origin |
|---|---|---|---:|---|
| `imec_ap_s001` | `s001` | `Neuropixels AP sample clock` | 30000.0 | `sample 0 at acquisition start` |
| `behavior_s001` | `s001` | `behavior acquisition clock` | 1000.0 | `tick 0 at behavior start` |

### `core.trials`

| session_id | trial_id | start_tick | stop_tick | clock_id | condition_id | choice | rewarded |
|---|---|---:|---:|---|---|---|---|
| `s001` | `trial_0001` | 1000 | 5000 | `behavior_s001` | `A_high_B_low` | `left` | true |
| `s001` | `trial_0002` | 6000 | 10000 | `behavior_s001` | `A_high_B_low` | `right` | false |

### `core.unit_spike_chunks`

| session_id | unit_id | sorting_run_id | curation_id | chunk_index | t_min_tick | t_max_tick | clock_id | n_spikes | spike_ticks |
|---|---|---|---|---:|---:|---:|---|---:|---|
| `s001` | `unit_001` | `sort_001` | `curation_001` | 0 | 30100 | 60000 | `imec_ap_s001` | 3 | `[30100, 45000, 60000]` |

## Example SQL with DuckDB

Count spikes per unit from materialized long table:

```sql
SELECT unit_id, COUNT(*) AS n_spikes
FROM analysis_spike_events
GROUP BY unit_id;
```

Count spike chunks and total spikes from canonical chunk table:

```sql
SELECT unit_id, COUNT(*) AS n_chunks, SUM(n_spikes) AS n_spikes
FROM core_unit_spike_chunks
GROUP BY unit_id;
```

Trial counts by condition:

```sql
SELECT condition_id, COUNT(*) AS n_trials
FROM core_trials
GROUP BY condition_id;
```

## Minimal validation checklist

A minimal packet passes when:

- `nwb.packet.json` parses.
- All required resources exist.
- All Parquet files open.
- All required columns exist.
- Primary keys are unique.
- All references resolve.
- Trial intervals are valid.
- Spike chunks are sorted and bounded.
- Zarr arrays declared in `core.array_assets` exist and match declared shape/dtype.
- Import provenance exists.

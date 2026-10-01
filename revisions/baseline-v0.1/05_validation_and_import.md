# 05 - Validation and Import

## Core principle

**Validation is importation.**

A resource is not imported into the core layer until it has passed all required validation checks for its semantic type, logical schema, and physical profile.

Copying or converting bytes is only staging.

## Import pipeline overview

Recommended import stages:

```text
1. Discover source data.
2. Extract candidate resources into staging.
3. Normalize candidate resources to logical schemas.
4. Validate candidate resources.
5. Commit validated resources into core.
6. Write/update packet catalog.
7. Record provenance.
8. Materialize optional analysis resources.
9. Validate analysis resources.
```

## Stage 1: Discover

Discovery inspects source data without committing anything.

Inputs may include:

- NWB-HDF5 files;
- raw acquisition binaries;
- spike sorting outputs;
- behavioral logs;
- video files;
- experiment metadata spreadsheets;
- lab-specific JSON/YAML configs.

Discovery SHOULD produce a source inventory.

The source inventory SHOULD include:

```text
source_file_id
uri
format
size_bytes
sha256 or other checksum
modified_at
recognized semantic candidates
```

## Stage 2: Extract to staging

Extraction writes candidate resources into a staging area.

Example:

```text
packet_root/
  staging/
    tables/core/trials.parquet
    tables/core/unit_spike_chunks.parquet
    arrays/probe0_lfp.zarr
```

Staged resources MUST NOT be listed as committed canonical resources in the packet manifest.

## Stage 3: Normalize

Normalization converts source-specific representations into logical schemas.

Examples:

- Convert floating source spike times to integer ticks on a declared clock when possible.
- Convert NWB trial intervals to `core.trials`.
- Convert NWB units/spike_times to `core.unit_spike_chunks`.
- Convert source electrode metadata to `core.electrodes`.
- Create stable IDs.
- Resolve clock IDs.
- Normalize units and conversion metadata.

Normalization SHOULD be deterministic for the same source inputs and parameters.

## Stage 4: Validate

Validation checks candidate resources before commit.

### Manifest-independent validators

These checks can run before final manifest commit:

- required columns exist;
- column types are compatible;
- primary keys are unique;
- required values are non-null;
- intervals are valid;
- spike ticks are sorted;
- array files exist and match declared dtype/shape;
- source files exist/checksum where required.

### Cross-resource validators

These checks require multiple resources:

- foreign keys resolve;
- every `clock_id` exists;
- every unit references an existing sorting/curation context;
- every array channel maps to an existing electrode when declared;
- every trial's session exists;
- every spike unit exists;
- every event trial reference resolves;
- provenance edges reference valid entities and activities.

### Physical validators

Portable profile validators:

- Parquet files are readable;
- Zarr arrays are readable as Zarr v3;
- declared URIs resolve;
- media/doc resources resolve if declared.

### Semantic validators

Semantic validators check domain invariants:

- trial stop >= start;
- spike ticks are nonnegative or justified by clock origin;
- array time dimension/sample rate/clock metadata are consistent;
- unit IDs are unique within sorting/curation context;
- curation references a valid sorting run.

## Stage 5: Commit

Commit moves validated resources from staging into packet locations and updates `nwb.packet.json`.

A commit MUST be atomic at the packet level as far as practical. For a local POC, this can be approximated by:

1. Write staged resources.
2. Validate staged resources.
3. Write a candidate manifest.
4. Move candidate resources into final paths.
5. Rename candidate manifest to `nwb.packet.json` last.

If commit fails, the packet MUST NOT present a partial import as valid.

## Stage 6: Record provenance

Every import SHOULD create at least:

- one `core.processing_runs` row;
- one `core.provenance_activities` row;
- source `core.provenance_entities` rows;
- target `core.provenance_entities` rows;
- `core.provenance_edges` linking source entities to target entities via the activity.

The packet manifest SHOULD reference the import activity ID.

## Stage 7: Materialize analysis resources

Analysis materializations are optional.

Examples:

- explode `core.unit_spike_chunks` into `analysis.spike_events`;
- assign spikes to trials as `analysis.spikes_by_trial`;
- create `analysis.trials_wide`;
- compute `analysis.unit_condition_rates`.

Analysis materializations MUST declare:

- source core resources;
- transform activity;
- parameters;
- software version;
- validation status.

## Validation report

A validation report SHOULD be written as JSON and MAY also be rendered as Markdown.

Suggested JSON structure:

```json
{
  "packet_id": "s001",
  "status": "passed",
  "validated_at": "2026-08-25T17:42:00Z",
  "validator": {
    "name": "nwb_lake_validate",
    "version": "0.1.0"
  },
  "checks": [
    {
      "check_id": "core.trials.primary_key_unique",
      "resource_id": "core.trials",
      "level": "error",
      "status": "passed",
      "message": "All trial keys are unique."
    }
  ],
  "summary": {
    "errors": 0,
    "warnings": 3
  }
}
```

## Error policy

Validation findings SHOULD have levels:

```text
error
warning
info
```

A packet with validation errors MUST NOT be considered imported.

A packet with warnings MAY be considered imported if warnings are explicitly allowed by policy and recorded in the validation report.

## Importer design

The importer SHOULD be organized as small, testable transforms:

```text
source adapter
  reads source-specific objects

normalizer
  maps source objects to logical records

writer
  writes staged Parquet/Zarr/media resources

validator
  validates staged resources

committer
  finalizes resources and manifest
```

Do not combine source parsing, normalization, validation, and writing into one opaque step.

## Suggested command line

Example commands for a future implementation:

```bash
nwb-lake inspect-source source.nwb --out source_inventory.json
nwb-lake import source.nwb --packet packet_root --staging packet_root/staging
nwb-lake validate packet_root
nwb-lake materialize packet_root analysis.spike_events
nwb-lake materialize packet_root analysis.spikes_by_trial
```

## Minimum acceptance criteria for first importer

The first importer should be considered successful when it can:

1. Create `core.sessions`, `core.subjects`, `core.clocks`, `core.trials`, `core.units`, and `core.unit_spike_chunks` from at least one real source dataset.
2. Write valid Parquet tables.
3. Write a valid packet manifest.
4. Run validation and fail on deliberate schema/reference/time errors.
5. Load the packet with a reference API and run at least one downstream query.

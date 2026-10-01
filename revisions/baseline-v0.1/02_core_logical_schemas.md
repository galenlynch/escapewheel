# 02 - Core Logical Schemas

## Scope

This document defines the core logical schemas for the first ecephys proof-of-principle. The core layer is the canonical normalized data model. It is storage-agnostic: these schemas can be implemented as Parquet, Iceberg tables, relational tables, or another compatible table backend.

For the first implementation, use the portable physical profile defined in `03_portable_physical_profile.md`.

## General schema rules

### Table resource requirements

Every core table MUST have:

- a schema ID;
- stable column names;
- declared column types;
- declared required/optional fields;
- declared primary key or uniqueness rule;
- declared references to other tables;
- validation rules.

### Field naming

Column names MUST be lowercase snake case.

Stable IDs SHOULD use the suffix `_id`.

Tick-valued columns SHOULD use the suffix `_tick`.

URI-valued columns SHOULD use the suffix `_uri` or be named `uri` when unambiguous.

### Type system

Logical schemas SHOULD use Arrow-compatible types:

```text
string
int32
int64
float32
float64
bool
timestamp
date
list<T>
struct<...>
map<string, T>
json_string
```

For first-pass Parquet implementation, `struct`, `list`, and `map` MAY be used if the writer/reader stack supports them reliably. Otherwise, semi-structured values MAY be stored as UTF-8 JSON strings with declared JSON schemas.

### Required fields

Required fields MUST be present and non-null unless explicitly stated otherwise.

Optional fields MAY be missing from early implementations only if the schema version declares them optional. Prefer present nullable columns over absent columns when practical, because stable columns simplify query code.

### Metadata fields

Every core table MAY include a `metadata` field.

The `metadata` field SHOULD be a struct/map when stable, or a JSON string when the metadata is lab-specific or evolving.

Fields used for filtering, grouping, joining, or validation SHOULD be promoted to first-class typed columns.

## Core table index

MVP core tables:

```text
core.sessions
core.subjects
core.devices
core.probes
core.electrodes
core.clocks
core.trials
core.events
core.units
core.unit_spike_chunks
core.spike_events        optional or derived, see spike policy
core.sorting_runs
core.curation_versions
core.array_assets
core.array_channels
core.media_assets
core.media_frames
core.processing_runs
core.source_files
core.provenance_entities
core.provenance_activities
core.provenance_edges
```

## Spike representation policy

The MVP SHOULD use `core.unit_spike_chunks` as the canonical compact spike-train representation.

An implementation MAY instead declare `core.spike_events` canonical if a long event table is more natural for the source pipeline.

If both `core.unit_spike_chunks` and `core.spike_events` exist, the packet manifest MUST declare:

- which representation is canonical for each `(session_id, sorting_run_id, curation_id)`;
- which representation is derived;
- the transform activity that produced the derived representation;
- whether equivalence validation passed.

This policy avoids prematurely choosing one universal spike layout. It also lets the POC compare compact ragged storage against long SQL-friendly event storage.

---

# Required schemas

## `core.sessions`

One row per recording session.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Stable session ID. |
| `subject_id` | string | yes | Subject ID. |
| `session_start_time` | timestamp | yes | Session start time if known; if unknown use explicit null only in non-strict test packets. |
| `session_description` | string | no | Human-readable session description. |
| `institution` | string | no | Institution/lab. |
| `experimenter` | list<string> or json_string | no | Experimenter names. |
| `task_name` | string | no | Task/protocol name. |
| `source_session_id` | string | no | Source-system session ID if different. |
| `metadata` | struct/map/json_string | no | Additional session metadata. |

Primary key: `session_id`.

References:

- `subject_id` -> `core.subjects.subject_id`.

Validation:

- `session_id` MUST be unique.
- `subject_id` MUST resolve unless subject data are intentionally redacted and the packet declares redaction.

## `core.subjects`

One row per subject.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `subject_id` | string | yes | Stable subject ID. |
| `species` | string | no | Species. |
| `strain` | string | no | Strain/background. |
| `sex` | string | no | Sex if recorded. |
| `date_of_birth` | date or timestamp | no | Date of birth if known. |
| `genotype` | string | no | Genotype summary. |
| `metadata` | struct/map/json_string | no | Additional subject metadata. |

Primary key: `subject_id`.

## `core.devices`

One row per device.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `device_id` | string | yes | Stable device ID. |
| `session_id` | string | no | Session if device record is session-scoped. |
| `name` | string | yes | Human-readable name. |
| `manufacturer` | string | no | Manufacturer. |
| `model` | string | no | Model. |
| `serial_number` | string | no | Serial number. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `device_id`.

## `core.probes`

One row per recording probe/insertion/logical probe.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `probe_id` | string | yes | Stable probe ID. |
| `session_id` | string | yes | Session ID. |
| `device_id` | string | no | Associated device. |
| `name` | string | no | Probe name. |
| `probe_type` | string | no | Probe type, e.g. Neuropixels 1.0. |
| `manufacturer` | string | no | Manufacturer. |
| `serial_number` | string | no | Serial number. |
| `insertion_name` | string | no | Insertion label. |
| `target_region` | string | no | Intended target. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `probe_id`.

References:

- `session_id` -> `core.sessions.session_id`.
- `device_id` -> `core.devices.device_id`, when present.

## `core.electrodes`

One row per electrode/contact/channel site.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `electrode_id` | string | yes | Stable electrode ID. |
| `session_id` | string | yes | Session ID. |
| `probe_id` | string | no | Probe ID. |
| `local_electrode_index` | int64 | no | Index within probe geometry. |
| `local_channel_index` | int64 | no | Acquisition channel index if applicable. |
| `x_um` | float64 | no | X coordinate in micrometers. |
| `y_um` | float64 | no | Y coordinate in micrometers. |
| `z_um` | float64 | no | Z coordinate in micrometers. |
| `coordinate_frame` | string | no | Coordinate frame ID/name. |
| `brain_region` | string | no | Region label. |
| `impedance_ohm` | float64 | no | Impedance. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `electrode_id`.

References:

- `session_id` -> `core.sessions.session_id`.
- `probe_id` -> `core.probes.probe_id`, when present.

## `core.clocks`

One row per clock/time basis.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `clock_id` | string | yes | Stable clock ID. |
| `session_id` | string | yes | Session ID. |
| `name` | string | yes | Human-readable clock name. |
| `tick_rate_hz` | float64 | conditional | Tick rate as float, required unless exact tick rate provided. |
| `tick_rate_num` | int64 | conditional | Exact rational numerator. |
| `tick_rate_den` | int64 | conditional | Exact rational denominator. |
| `origin` | string | yes | Origin description. |
| `parent_clock_id` | string | no | Parent/reference clock. |
| `transform_to_parent` | struct/map/json_string | no | Clock alignment transform. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `clock_id`.

References:

- `session_id` -> `core.sessions.session_id`.
- `parent_clock_id` -> `core.clocks.clock_id`, when present.

Validation:

- Either `tick_rate_hz` OR both `tick_rate_num` and `tick_rate_den` MUST be present.
- Tick rates MUST be positive.

## `core.trials`

One row per trial.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Session ID. |
| `trial_id` | string | yes | Stable trial ID. |
| `start_tick` | int64 | yes | Trial start tick. |
| `stop_tick` | int64 | yes | Trial stop tick. |
| `clock_id` | string | yes | Clock for start/stop ticks. |
| `condition_id` | string | no | Experimental condition. |
| `stimulus_id` | string | no | Stimulus ID. |
| `choice` | string | no | Choice label. |
| `rewarded` | bool | no | Reward outcome. |
| `tags` | list<string> or json_string | no | Tags. |
| `metadata` | struct/map/json_string | no | Additional trial metadata. |

Primary key: `(session_id, trial_id)`.

References:

- `session_id` -> `core.sessions.session_id`.
- `clock_id` -> `core.clocks.clock_id`.

Validation:

- `stop_tick >= start_tick`.
- `clock_id` MUST resolve.

## `core.events`

One row per event.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Session ID. |
| `event_id` | string | yes | Stable event ID. |
| `event_type` | string | yes | Event type. |
| `t_tick` | int64 | yes | Event tick. |
| `clock_id` | string | yes | Event clock. |
| `trial_id` | string | no | Trial if known/materialized. |
| `payload` | struct/map/json_string | no | Event payload. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `(session_id, event_id)`.

References:

- `session_id` -> `core.sessions.session_id`.
- `clock_id` -> `core.clocks.clock_id`.
- `(session_id, trial_id)` -> `core.trials`, when present.

## `core.sorting_runs`

One row per spike sorting run.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `sorting_run_id` | string | yes | Stable sorting run ID. |
| `session_id` | string | yes | Session ID. |
| `probe_id` | string | no | Probe ID. |
| `sorter_name` | string | no | Sorter name. |
| `sorter_version` | string | no | Sorter version. |
| `parameters` | struct/map/json_string | no | Sorter parameters. |
| `input_array_asset_id` | string | no | Input array asset. |
| `started_at` | timestamp | no | Start time. |
| `ended_at` | timestamp | no | End time. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `sorting_run_id`.

## `core.curation_versions`

One row per curation version.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `curation_id` | string | yes | Stable curation ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `session_id` | string | yes | Session ID. |
| `curator` | string | no | Curator. |
| `curation_tool` | string | no | Tool. |
| `curation_tool_version` | string | no | Tool version. |
| `parent_curation_id` | string | no | Parent curation. |
| `created_at` | timestamp | no | Creation time. |
| `notes` | string | no | Notes. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `curation_id`.

## `core.units`

One row per unit in a sorting/curation context.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Stable unit ID. |
| `probe_id` | string | no | Probe ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `local_unit_index` | int64 | no | Source/local unit index. |
| `quality_label` | string | no | Quality label. |
| `default_electrode_id` | string | no | Default electrode. |
| `firing_rate_hz` | float64 | no | Firing rate if known. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `(session_id, unit_id, sorting_run_id, curation_id)`.

References:

- `session_id` -> `core.sessions.session_id`.
- `probe_id` -> `core.probes.probe_id`, when present.
- `sorting_run_id` -> `core.sorting_runs.sorting_run_id`.
- `curation_id` -> `core.curation_versions.curation_id`.
- `default_electrode_id` -> `core.electrodes.electrode_id`, when present.

## `core.unit_spike_chunks`

Canonical compact ragged spike-train representation for the recommended MVP.

One row per unit per spike-time chunk.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `chunk_index` | int64 | yes | Chunk index for this unit. |
| `t_min_tick` | int64 | yes | Minimum tick in chunk. |
| `t_max_tick` | int64 | yes | Maximum tick in chunk. |
| `clock_id` | string | yes | Clock for spike ticks. |
| `n_spikes` | int64 | yes | Number of spikes in chunk. |
| `spike_ticks` | list<int64> or json_string | yes | Sorted spike ticks. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `(session_id, unit_id, sorting_run_id, curation_id, chunk_index)`.

References:

- `(session_id, unit_id, sorting_run_id, curation_id)` -> `core.units`.
- `clock_id` -> `core.clocks.clock_id`.

Validation:

- `spike_ticks` MUST be sorted ascending within each row.
- `n_spikes` MUST equal the length of `spike_ticks`.
- `t_min_tick` and `t_max_tick` MUST bound all ticks in `spike_ticks`.
- Chunks for one unit SHOULD be non-overlapping and ordered by `chunk_index`.

## `core.spike_events`

Long event representation. Optional in core if `core.unit_spike_chunks` is canonical. Useful as a canonical alternative or analysis materialization.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `t_tick` | int64 | yes | Spike tick. |
| `clock_id` | string | yes | Clock ID. |
| `trial_id` | string | no | Trial assignment if materialized. |
| `amplitude` | float32 | no | Spike amplitude if available. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Recommended ordering:

```text
session_id, sorting_run_id, curation_id, unit_id, t_tick
```

## `core.array_assets`

One row per dense array asset.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `array_asset_id` | string | yes | Stable array asset ID. |
| `session_id` | string | yes | Session ID. |
| `semantic_type` | string | yes | Semantic type, e.g. ElectricalSeries. |
| `name` | string | yes | Human-readable name. |
| `kind` | string | yes | `raw`, `ap`, `lfp`, `waveform`, etc. |
| `uri` | string | yes | URI/path to array store. |
| `format` | string | yes | `zarr_v3` for portable profile. |
| `dtype` | string | yes | Array dtype. |
| `shape` | list<int64> or json_string | yes | Array shape. |
| `dimension_names` | list<string> or json_string | yes | Dimension names. |
| `clock_id` | string | no | Clock for time axis. |
| `sample_rate_hz` | float64 | no | Sample rate if regularly sampled. |
| `unit` | string | no | Physical unit. |
| `conversion` | float64 | no | Multiply stored values by this before offset. |
| `offset` | float64 | no | Add after conversion. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `array_asset_id`.

Validation:

- `uri` MUST resolve within the packet or to an allowed external URI.
- Actual array dtype and shape SHOULD match declared metadata.
- If time-indexed, `clock_id` SHOULD resolve.

## `core.array_channels`

Mapping from array channel axis positions to electrodes.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `array_asset_id` | string | yes | Array asset ID. |
| `channel_index` | int64 | yes | Channel dimension index. |
| `electrode_id` | string | no | Electrode ID. |
| `channel_label` | string | no | Human-readable channel label. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `(array_asset_id, channel_index)`.

## `core.media_assets`

One row per media file.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `media_asset_id` | string | yes | Stable media asset ID. |
| `session_id` | string | yes | Session ID. |
| `semantic_type` | string | yes | e.g. BehaviorVideo. |
| `name` | string | yes | Name. |
| `uri` | string | yes | Media file URI. |
| `format` | string | yes | e.g. mp4. |
| `clock_id` | string | no | Clock for frame timing. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

## `core.media_frames`

Frame timing table for media assets.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `media_asset_id` | string | yes | Media asset ID. |
| `frame_index` | int64 | yes | Frame index. |
| `t_tick` | int64 | yes | Frame time tick. |
| `clock_id` | string | yes | Clock ID. |
| `pts` | float64 | no | Media presentation timestamp if relevant. |
| `dropped` | bool | no | Dropped-frame flag. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Primary key: `(media_asset_id, frame_index)`.

## `core.processing_runs`

One row per processing/import/materialization run.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `processing_run_id` | string | yes | Stable processing run ID. |
| `session_id` | string | no | Session ID if session-scoped. |
| `activity_type` | string | yes | import, validation, sorting, curation, materialization, etc. |
| `software_name` | string | no | Software name. |
| `software_version` | string | no | Software version. |
| `code_uri` | string | no | Code reference. |
| `parameters` | struct/map/json_string | no | Parameters. |
| `started_at` | timestamp | no | Start time. |
| `ended_at` | timestamp | no | End time. |
| `status` | string | yes | succeeded, failed, partial, etc. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

## `core.source_files`

One row per source file/object used in import.

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `source_file_id` | string | yes | Stable source file ID. |
| `uri` | string | yes | Source URI/path. |
| `format` | string | no | Source format. |
| `sha256` | string | no | Checksum. |
| `size_bytes` | int64 | no | Size. |
| `modified_at` | timestamp | no | Modification time if known. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

## Provenance tables

### `core.provenance_entities`

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `entity_id` | string | yes | Stable provenance entity ID. |
| `entity_type` | string | yes | source_file, table, array, media, report, etc. |
| `resource_id` | string | no | Packet resource ID if applicable. |
| `uri` | string | no | URI/path. |
| `sha256` | string | no | Checksum. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

### `core.provenance_activities`

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `activity_id` | string | yes | Stable activity ID. |
| `activity_type` | string | yes | import, validation, transform, materialization. |
| `processing_run_id` | string | no | Processing run. |
| `started_at` | timestamp | no | Start time. |
| `ended_at` | timestamp | no | End time. |
| `status` | string | yes | succeeded, failed, partial. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

### `core.provenance_edges`

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `source_entity_id` | string | yes | Input/source entity. |
| `activity_id` | string | yes | Activity. |
| `target_entity_id` | string | yes | Output/target entity. |
| `relationship_type` | string | yes | used, generated, derived_from, validated, etc. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

## Validation summary

A valid core packet MUST pass at least:

- required column checks;
- type checks;
- primary key uniqueness checks;
- reference integrity checks;
- clock existence checks;
- trial interval checks;
- spike ordering/chunk checks when spikes exist;
- array asset existence checks when arrays exist;
- provenance checks for imported resources.

<!-- BEGIN README.md -->


# NWB-Lake POC v0.1 Implementation Kit

This package is a standalone implementation basis for a proof-of-principle ecephys data lake inspired by NWB semantics but not dependent on NWB, HDMF, or PyNWB as runtime storage abstractions.

The project name **NWB-Lake** is a placeholder. The design goal is to test whether neurophysiology data can be represented as a small semantic/logical standard over commodity storage formats:

- **Tables:** Parquet first; Iceberg later when table versioning/cataloging becomes necessary.
- **Dense arrays:** Zarr v3 first.
- **Media:** standard media files such as MP4, with frame timing in tables.
- **Packet catalog:** a JSON manifest that binds resources together.
- **Access:** DuckDB/Polars/PyArrow for tables, Zarr/xarray for arrays, and a small reference Python package over the packet.

The current focus is **not** the NWB compatibility projection. That can come later. The primary implementation focus is:

1. The semantic standard.
2. The logical core schemas.
3. The portable physical profile.
4. Validation-driven import.
5. Optional analysis-layer materializations.

## Design commitments

### 1. Validation is importation

A source object is not "imported" merely because bytes were copied into a packet. Importation means:

1. Source data were discovered.
2. Candidate resources were extracted into staging.
3. Candidate resources were normalized to the logical schemas.
4. Candidate resources passed validation.
5. Validated resources were committed into `core` and recorded in the packet catalog.
6. The import activity and source lineage were recorded as provenance.

Nothing should become `core` data until it has passed the relevant validators.

### 2. Core owns truth

The `core` layer contains canonical normalized facts. Derived products in `analysis` are reproducible from `core` and may be deleted/recomputed. A later `nwb` projection can be built from `core`, but it is not a requirement for the first proof-of-principle.

### 3. Stable IDs, not object paths

Resources and rows reference each other with stable IDs. Do not rely on HDF5 object references, Zarr hierarchy paths, Python object identity, or implicit file layout as the primary identity system.

### 4. Time is integer ticks on declared clocks

Ecephys data should not use floating-point seconds as the sole canonical time representation. Event and interval times use integer ticks plus a `clock_id`. Derived seconds may be provided for convenience.

### 5. Physical profiles are replaceable

The logical schemas should work whether tables are stored as plain Parquet, Iceberg tables, a relational database, or another compatible table system. The first implementation should use the portable Parquet/Zarr profile. Iceberg is a future scale/versioning profile, not a requirement for the first import pipeline.

## Document map

- `00_architecture.md`: Concepts, layers, packet/profile model, and implementation stance.
- `01_semantic_standard.md`: Domain meanings and invariants for ecephys concepts.
- `02_core_logical_schemas.md`: Core table/asset schemas and constraints.
- `03_portable_physical_profile.md`: Parquet/Zarr packet layout and file conventions.
- `04_packet_catalog_manifest.md`: Manifest/catalog fields and examples.
- `05_validation_and_import.md`: Validation-first import pipeline.
- `06_analysis_layer.md`: Optional derived analysis products and lineage rules.
- `07_reference_api_and_implementation_plan.md`: Suggested package/API and phased implementation plan.
- `08_example_packet.md`: Minimal packet layout and example manifest snippets.

A consolidated single-file version is also provided as `NWB_Lake_POC_v0.1_Implementation_Spec.md`.

## Normative language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, and OPTIONAL are used in the RFC 2119 sense.

## External technology references

These references are not the standard. They are the intended commodity substrates for the first implementation profiles.

- RFC 2119 normative keywords: https://www.rfc-editor.org/info/rfc2119
- Apache Parquet overview: https://parquet.apache.org/docs/overview/
- Apache Arrow documentation: https://arrow.apache.org/docs/
- Zarr v3 core specification: https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html
- Apache Iceberg specification: https://iceberg.apache.org/spec/


<!-- END README.md -->


<!-- BEGIN 00_architecture.md -->


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


<!-- END 00_architecture.md -->


<!-- BEGIN 01_semantic_standard.md -->


# 01 - Semantic Standard

## Scope

This document defines semantic concepts for an ecephys-focused packet. The goal is to describe meaning, not storage.

Semantic concepts MUST be represented in the logical standard, but the semantic standard itself does not decide whether a concept is stored in Parquet, Zarr, Iceberg, or anything else.

## Global semantic rules

### Stable identity

Any object that can be referenced by another object MUST have a stable ID.

IDs SHOULD be opaque strings. Implementations MUST NOT require semantic meaning to be encoded in IDs.

### Time basis

Every event, interval, spike time, dense time axis, and media frame timing record MUST have a declared time basis.

For ecephys, the canonical time representation SHOULD be integer ticks on a declared clock.

### Provenance

Every imported core resource MUST be traceable to source data or source activities.

Every derived analysis resource MUST be traceable to source core resources and a transform activity.

### Units of measure

Measured quantities SHOULD declare units. Stored integer values that require conversion to physical units MUST declare conversion metadata.

### Extension

Lab-specific semantic concepts MAY be added through namespaced extensions. Extensions MUST NOT alter the meaning of core semantic concepts without declaring a new semantic version.

## Required semantic concepts

### Dataset

A `Dataset` is a coherent scientific collection containing one or more sessions and their associated resources.

Semantic requirements:

- MUST have a stable dataset ID.
- SHOULD have a human-readable description.
- SHOULD declare creators, license, and version/release information.

### Packet

A `Packet` is a concrete representation of a dataset or dataset subset under a declared physical profile.

Semantic requirements:

- MUST have a packet ID.
- MUST declare a profile.
- MUST declare the semantic and logical standard versions it conforms to.
- MUST include a packet catalog.

### Session

A `Session` is one experimental recording session.

Semantic requirements:

- MUST have a stable session ID.
- MUST belong to a subject unless the subject is intentionally unknown.
- MUST have a session start time when known.
- SHOULD declare experiment/task context.

### Subject

A `Subject` is the biological subject of one or more sessions.

Semantic requirements:

- MUST have a stable subject ID.
- MAY include species, strain, sex, genotype, and date of birth.
- Sensitive or controlled metadata MAY be redacted or stored outside the packet.

### Device

A `Device` is a physical or virtual instrument used to acquire, stimulate, process, or synchronize data.

Semantic requirements:

- MUST have a stable device ID.
- SHOULD include manufacturer/model/serial information when relevant.

### Probe

A `Probe` is an electrode-bearing recording instrument or logical recording probe.

Semantic requirements:

- MUST belong to a session.
- SHOULD reference a device.
- SHOULD include probe type and geometry when known.

### Electrode

An `Electrode` is a recording contact or channel-associated electrode site.

Semantic requirements:

- MUST have a stable electrode ID.
- MUST belong to a session.
- SHOULD belong to a probe.
- SHOULD define local channel/contact indices.
- MAY declare anatomical or coordinate metadata.

### Clock

A `Clock` defines a time basis for ticks.

Semantic requirements:

- MUST have a stable clock ID.
- MUST belong to a session.
- MUST declare tick rate or exact rational tick rate.
- MUST declare an origin description.
- MAY declare transform/alignment to another clock.

### Trial

A `Trial` is a bounded interval of experimental time corresponding to one behavioral, task, or stimulus-response unit of a session.

Semantic requirements:

- MUST belong to one session.
- MUST have start and stop times on a declared clock.
- Stop time MUST be greater than or equal to start time.
- MAY have condition, stimulus, choice, outcome, tags, and arbitrary task annotations.

### Event

An `Event` is an instantaneous or near-instantaneous timestamped observation or annotation.

Semantic requirements:

- MUST belong to one session.
- MUST have an event type.
- MUST have a time on a declared clock.
- MAY reference a trial.
- MAY include structured payload metadata.

Examples:

- stimulus onset;
- reward delivery;
- lick;
- wheel movement threshold crossing;
- TTL edge;
- synchronization pulse.

### Unit

A `Unit` is a sorted or curated spiking entity produced by a spike sorting and/or curation process.

Semantic requirements:

- MUST belong to one session.
- MUST be defined within a sorting run and curation version.
- MUST have stable identity within that context.
- MAY have spike times.
- MAY have quality labels and metrics.
- MAY reference electrodes/channels.

A unit does not necessarily mean a single biological neuron; it may be a single unit, multi-unit cluster, noise cluster, or other sorted entity depending on curation labels.

### Spike train

A `SpikeTrain` is the ordered collection of spike times associated with one unit in one sorting/curation context.

Semantic requirements:

- MUST reference a unit.
- MUST use a declared clock.
- Spike times SHOULD be sorted ascending.
- Spike times SHOULD be integer ticks.

### Spike event

A `SpikeEvent` is one spike timestamp for one unit.

Semantic requirements:

- MUST reference a unit.
- MUST have a time on a declared clock.
- MAY reference a trial if trial assignment has been materialized.

### ElectricalSeries

An `ElectricalSeries` is a sampled extracellular electrical signal over time and channels.

Semantic requirements:

- MUST belong to one session.
- MUST have physical units or conversion metadata sufficient to interpret stored values.
- MUST have a declared time basis.
- MUST define dimensional meaning.
- SHOULD map channels to electrodes.

Examples:

- raw voltage;
- AP band;
- LFP.

### ArrayAsset

An `ArrayAsset` is a dense n-dimensional array stored outside a table and described by core metadata.

Semantic requirements:

- MUST have a stable array asset ID.
- MUST have a semantic type.
- MUST have URI, format, dtype, shape, and dimension names.
- SHOULD have chunking/storage metadata when useful.

### MediaAsset

A `MediaAsset` is an externally stored media file, such as video or audio.

Semantic requirements:

- MUST have a stable media asset ID.
- MUST have URI and media format.
- SHOULD be accompanied by timing tables when synchronization matters.

### ProcessingRun

A `ProcessingRun` is an execution of software or manual procedure that transforms or annotates data.

Semantic requirements:

- MUST have a stable processing run ID.
- SHOULD include software name, version, parameters, start/end time, and operator if known.
- MUST be represented in provenance if it produces committed resources.

### SortingRun

A `SortingRun` is a processing run that produces sorted units/spike trains.

Semantic requirements:

- MUST belong to a session.
- MUST identify input data.
- SHOULD include sorter name, version, and parameters.

### CurationVersion

A `CurationVersion` is a versioned interpretation of sorting outputs after manual or automated curation.

Semantic requirements:

- MUST reference a sorting run.
- MUST have a stable curation ID.
- SHOULD include curator/tool/version/notes.

### ProvenanceEntity

A `ProvenanceEntity` is a source or derived data object.

Examples:

- source NWB file;
- source binary file;
- Parquet table;
- Zarr array;
- derived analysis table.

### ProvenanceActivity

A `ProvenanceActivity` is an import, validation, processing, or materialization activity.

Semantic requirements:

- MUST identify inputs and outputs through provenance edges.
- SHOULD identify software, version, parameters, and time.


<!-- END 01_semantic_standard.md -->


<!-- BEGIN 02_core_logical_schemas.md -->


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


<!-- END 02_core_logical_schemas.md -->


<!-- BEGIN 03_portable_physical_profile.md -->


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


<!-- END 03_portable_physical_profile.md -->


<!-- BEGIN 04_packet_catalog_manifest.md -->


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


<!-- END 04_packet_catalog_manifest.md -->


<!-- BEGIN 05_validation_and_import.md -->


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


<!-- END 05_validation_and_import.md -->


<!-- BEGIN 06_analysis_layer.md -->


# 06 - Analysis Layer

## Scope

The analysis layer contains derived products optimized for real analysis. It is optional for minimal core compliance but central to the proof-of-principle as an analysis system.

The analysis layer is allowed to be denormalized, prejoined, binned, aligned, or cached. It is not allowed to become an undocumented second source of truth.

## Analysis-layer rules

Analysis resources MUST declare lineage to core resources.

Analysis resources MUST declare transform parameters and software version.

Analysis resources SHOULD be reproducible from core resources.

Analysis resources MAY be deleted and recomputed.

Analysis resources MUST NOT be edited manually without recording a new provenance activity.

Analysis resources SHOULD NOT introduce new canonical scientific facts unless those facts are promoted into core through a schema revision.

## Recommended initial analysis resources

### `analysis.spike_events`

Long spike table derived from `core.unit_spike_chunks` when chunked spikes are canonical.

Suggested schema:

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `t_tick` | int64 | yes | Spike tick. |
| `clock_id` | string | yes | Clock ID. |

Recommended ordering:

```text
session_id, sorting_run_id, curation_id, unit_id, t_tick
```

### `analysis.spikes_by_trial`

Spike table with trial assignment and relative time.

Suggested schema:

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `session_id` | string | yes | Session ID. |
| `trial_id` | string | yes | Trial ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `t_abs_tick` | int64 | yes | Absolute spike tick. |
| `t_rel_tick` | int64 | yes | Relative to alignment event. |
| `clock_id` | string | yes | Clock ID. |
| `alignment_event` | string | yes | e.g. trial_start, stimulus_on. |
| `condition_id` | string | no | Copied from trial for convenience. |
| `metadata` | struct/map/json_string | no | Additional metadata. |

Materialization parameters MUST include:

- alignment event;
- inclusion window;
- source spike representation;
- source trial table version.

### `analysis.trials_wide`

Convenience trial table with event-derived columns.

Suggested columns:

```text
session_id
trial_id
start_tick
stop_tick
clock_id
condition_id
stimulus_id
choice
rewarded
stimulus_on_tick
go_cue_tick
response_tick
reward_tick
reaction_time_ticks
previous_choice
previous_rewarded
block_id
metadata
```

This table SHOULD be derived from `core.trials` and `core.events`.

### `analysis.good_units`

View or materialized table selecting units that pass a declared quality policy.

Suggested columns:

```text
all core.units columns
quality_policy_id
is_good
quality_reason
```

The quality policy MUST be recorded.

### `analysis.unit_condition_rates`

Aggregated firing-rate table.

Suggested columns:

```text
session_id
unit_id
sorting_run_id
curation_id
condition_id
epoch_name
epoch_start_rel_tick
epoch_stop_rel_tick
n_spikes
n_trials
duration_ticks
rate_hz
```

### `analysis.binned_spikes`

Dense binned spike tensor. This SHOULD be a materialized array asset rather than a giant table when the natural shape is dense.

Suggested dimensions:

```text
trial, unit, time_bin
```

Associated metadata should be stored in `core.array_assets` or an `analysis.array_assets` extension table.

### `analysis.lfp_bandpower`

Tabular or dense representation depending on access pattern.

If sparse/summary-like:

```text
session_id
array_asset_id
channel_index
trial_id
band
t_bin_start_tick
t_bin_stop_tick
power
```

If dense tensor-like, store as Zarr and describe in an asset table.

## Analysis materialization policy

A materialization activity MUST record:

```text
activity_id
source resources
source validation state or source packet release
code version
parameters
created_at
output resource_id
output validation status
```

If source core resources change, dependent analysis resources SHOULD be invalidated unless their manifest pins exact source resource versions.

## Views versus materialized products

Use a view when the transformation is cheap:

- selecting good units;
- converting ticks to seconds for display;
- selecting trials for one condition.

Use a materialized table when the transformation is expensive or frequently reused:

- spike-to-trial assignment;
- event-aligned spike expansion;
- trial-wide event extraction;
- aggregate rates by condition;
- feature extraction.

Use a materialized array when the result is naturally dense:

- binned spikes;
- trial-aligned LFP;
- spectrograms;
- decoding design matrices.

## Promotion into core

An analysis resource MAY be promoted into core only through a schema change.

Promotion requires:

1. A new core schema or extension schema.
2. A semantic definition.
3. A validation rule.
4. A migration path.
5. Updated provenance.

Do not silently treat an analysis cache as canonical.


<!-- END 06_analysis_layer.md -->


<!-- BEGIN 07_reference_api_and_implementation_plan.md -->


# 07 - Reference API and Implementation Plan

## Goal

The first reference implementation should be small, boring, and useful. It should prove that a packet can be created, validated, and queried without HDMF/PyNWB in the hot path.

PyNWB MAY be used as an import adapter for source NWB files.

## Suggested package layout

```text
nwb_lake/
  __init__.py
  packet.py
  manifest.py
  schemas.py
  validate.py
  importers/
    nwb.py
    spike_sorting.py
    behavior.py
  writers/
    parquet.py
    zarr.py
  materialize/
    spike_events.py
    spikes_by_trial.py
    trials_wide.py
  access/
    duckdb.py
    polars.py
    arrays.py
  cli.py
```

## User-facing API

Minimum API:

```python
import nwb_lake as nwl

pkt = nwl.open_packet("/path/to/session_001.nwbpkt")

pkt.validate()

trials = pkt.table("core.trials")
units = pkt.table("core.units")
spike_chunks = pkt.table("core.unit_spike_chunks")
lfp = pkt.array("probe0_lfp")
```

SQL access:

```python
con = pkt.duckdb()

con.sql("""
    SELECT unit_id, COUNT(*) AS n_chunks, SUM(n_spikes) AS n_spikes
    FROM core_unit_spike_chunks
    GROUP BY unit_id
""").df()
```

Convenience accessors:

```python
pkt.trials()
pkt.units()
pkt.spike_times(unit_id="unit_001")
pkt.events(event_type="reward")
pkt.array_asset("probe0_lfp")
```

Analysis materialization:

```python
pkt.materialize("analysis.spike_events")
pkt.materialize("analysis.spikes_by_trial", alignment_event="trial_start")
pkt.materialize("analysis.trials_wide")
```

## Command-line API

Suggested commands:

```bash
nwb-lake inspect-source source.nwb --out source_inventory.json
nwb-lake import source.nwb --packet session_001.nwbpkt
nwb-lake validate session_001.nwbpkt
nwb-lake ls session_001.nwbpkt
nwb-lake sql session_001.nwbpkt "SELECT COUNT(*) FROM core_trials"
nwb-lake materialize session_001.nwbpkt analysis.spike_events
```

## Internal object model

Do not create a large custom object hierarchy. Use a thin wrapper around standard backends.

Suggested objects:

### `Packet`

Responsibilities:

- load manifest;
- resolve resource URIs;
- list resources;
- validate manifest;
- provide table/array access;
- provide SQL registration;
- update manifest during controlled writes.

### `Resource`

Responsibilities:

- expose resource metadata;
- resolve URI;
- know layer/kind/schema/profile;
- know validation state;
- know lineage.

### `TableResource`

Responsibilities:

- open as PyArrow table/dataset;
- register with DuckDB;
- optionally expose Polars scan.

### `ArrayResource`

Responsibilities:

- open Zarr array/group;
- expose xarray adapter when dimensions/coords are available.

### `Validator`

Responsibilities:

- run schema checks;
- run resource existence checks;
- run cross-reference checks;
- produce machine-readable validation report.

## Implementation phases

### Phase 0: Spec fixtures

Create a tiny synthetic packet by hand.

Requirements:

- one session;
- one subject;
- one clock;
- two trials;
- two units;
- spike chunks;
- validation report.

This packet is the first test fixture.

### Phase 1: Manifest and table reader

Implement:

- `open_packet`;
- manifest parsing;
- resource listing;
- Parquet table loading;
- DuckDB registration.

Success criterion:

```python
pkt = open_packet("example_packet")
pkt.table("core.trials")
pkt.duckdb().sql("SELECT COUNT(*) FROM core_trials")
```

### Phase 2: Validator

Implement checks for:

- required resources;
- required columns;
- type compatibility;
- primary key uniqueness;
- reference integrity;
- trial interval validity;
- spike chunk validity.

Success criterion:

- Valid fixture passes.
- Deliberately broken fixtures fail with clear errors.

### Phase 3: NWB source importer

Use PyNWB only at the boundary if source is NWB.

Implement extraction for:

- session/subject metadata;
- trials;
- units/spike times;
- electrodes when possible;
- clocks/time basis as best effort.

Success criterion:

- Import one real source into a valid packet.

### Phase 4: Analysis materializations

Implement:

- `analysis.spike_events` from `core.unit_spike_chunks`;
- `analysis.spikes_by_trial`;
- `analysis.trials_wide`.

Success criterion:

- Run a simple PSTH-like query from packet data.

### Phase 5: Dense arrays

Add Zarr array assets for one dense time series such as LFP.

Success criterion:

- `core.array_assets` validates against actual Zarr dtype/shape.
- `pkt.array("...")` opens the array.

### Phase 6: Release/version discipline

Add:

- immutable packet release IDs;
- checksums;
- provenance completeness;
- dependency invalidation for analysis resources.

### Phase 7: Iceberg experiment

Only after the portable profile is useful, implement the same logical schemas as Iceberg tables.

Success criterion:

- same queries work against portable Parquet and Iceberg table resources through the same high-level API.

## Testing strategy

Tests should include:

- schema tests;
- manifest tests;
- validation pass/fail fixtures;
- import golden-data tests;
- round-trip tests for spike chunk -> spike event -> chunk equivalence;
- query tests using DuckDB;
- array asset validation tests.

## Do not overbuild early

Avoid in the first proof-of-principle:

- a custom storage engine;
- a full PyNWB-compatible object model;
- a full NWB exporter;
- distributed compute;
- Iceberg-first design;
- complicated extension registries;
- generalized ontology machinery.

The first goal is simple:

```text
Can I validate, open, query, and analyze my own ecephys data from this packet layout?
```


<!-- END 07_reference_api_and_implementation_plan.md -->


<!-- BEGIN 08_example_packet.md -->


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


<!-- END 08_example_packet.md -->



---

# 09. Metadata Minimalism and Extension Policy

## Status

This document is part of **NWB-Lake POC v0.1**. It defines the role of subject, experimental, institutional, procedural, and free-form metadata in a packet. It is intended to prevent the core packet from becoming a large ontology while still preserving enough metadata for analysis, validation, and reproducibility.

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are used in the RFC 2119 sense.

## 1. Motivation

A neurophysiology packet needs metadata, but not all metadata has the same role. Some metadata is required to interpret numerical data. Some metadata is required to validate relationships. Some metadata is useful for institutional discovery, compliance, or archiving. Some metadata is lab-specific context that should remain available but should not block analysis.

The core packet specification therefore takes a **metadata-minimal** position:

> A conforming packet MUST contain metadata sufficient to identify, interpret, validate, query, and reproduce the imported data. Rich institutional, procedural, biological, or ontology-backed metadata MAY be provided through extensions or sidecar documents, but MUST NOT be required for core conformance.

This is especially important for proof-of-principle implementation. If core compliance requires a broad ontology, packets become difficult to create, difficult to validate, and difficult to use as an analysis substrate.

## 2. Metadata tiers

The spec divides metadata into four tiers.

### 2.1 Tier 1: Packet metadata

Packet metadata describes the packet as a dataset bundle. It belongs in the packet catalog / manifest.

A packet manifest MUST include:

```text
packet_id
packet_version
profile_id
semantic_standard_version
logical_standard_version
created_at
resources
schemas
validation_status or validation_requirements
```

A packet manifest SHOULD include:

```text
dataset_id
release_id
description
creators
license_or_restrictions
source_files
keywords
checksums
```

Packet metadata SHOULD remain small. It SHOULD identify and bind resources, not duplicate all scientific metadata.

### 2.2 Tier 2: Core analysis metadata

Core analysis metadata is structured metadata required for numerical interpretation, validation, joining, querying, and provenance. It belongs in `core` tables.

Examples include:

```text
sessions
subjects
clocks
devices
probes
electrodes
array_assets
array_channels
processing_runs
sorting_runs
curation_versions
provenance_entities
provenance_activities
provenance_edges
```

This tier is mandatory when the relevant data are present. For example, a packet with sorted spikes MUST define sorting and curation context. A packet with time-indexed dense arrays MUST define clock or sampling metadata. A packet with channelized voltage arrays MUST define channel mapping.

### 2.3 Tier 3: Domain-rich extension metadata

Domain-rich metadata is useful but not required for core analysis-layer conformance. It MAY be included as named extensions or sidecars.

Examples include:

```text
surgery details
viral injections
implant history
animal husbandry
training history
water restriction history
complete rig/instrument ontology
full acquisition metadata ontology
full procedural metadata ontology
quality-control ontology
institutional asset model
compliance or administrative metadata
```

These metadata MAY be validated by extension-specific validators. A core packet validator MUST NOT require understanding these extension schemas unless the user explicitly asks for extension validation.

### 2.4 Tier 4: Human-readable context

Human-readable context SHOULD be preserved as sidecar documents when useful.

Examples include:

```text
README.md
protocol.md
surgery_notes.txt
task_notes.md
calibration_report.pdf
experiment_log.txt
```

These documents SHOULD be registered in the packet catalog as document assets. They SHOULD NOT be forced into normalized core tables unless fields from them become analysis-critical.

## 3. Core metadata inclusion rule

A metadata field belongs in the core spec only if common interpretation, validation, joining, or analysis would break without it.

A field SHOULD be promoted into core when it is commonly needed to:

```text
interpret units, clocks, channels, arrays, or spike times
validate required relationships
join tables
filter or group common analyses
reproduce processing or curation
trace provenance from source data to packet resources
```

A field SHOULD remain in an extension or sidecar when it is primarily:

```text
institutional
administrative
lab-specific
rarely queried
free-form descriptive
procedural but not required for analysis
biologically rich but not required to interpret the recording
```

## 4. Required minimum metadata by resource

### 4.1 Subjects

The core spec intentionally requires very little subject metadata.

`core.subjects` MUST include:

```text
subject_id
```

`core.subjects` SHOULD include when known:

```text
species
sex
date_of_birth or age_at_session
genotype
strain
```

`core.subjects` MAY include:

```text
metadata: struct/map/json
```

The core spec MUST NOT require a full subject ontology, complete genotype ontology, source/vendor ontology, housing metadata, or procedural history.

### 4.2 Sessions

`core.sessions` MUST include:

```text
session_id
subject_id
session_start_time
```

`core.sessions` SHOULD include:

```text
session_description
task_name
institution
experimenter
```

`core.sessions` MAY include:

```text
metadata: struct/map/json
```

The core spec MUST NOT require a full experiment ontology or complete protocol description to perform core validation.

### 4.3 Clocks

Clock metadata is core metadata, not optional descriptive metadata.

Every clock referenced by events, intervals, spikes, dense arrays, or media frame tables MUST be declared in `core.clocks`.

`core.clocks` MUST include:

```text
clock_id
session_id
name
tick_rate_hz or exact_tick_rate
origin
```

`core.clocks` SHOULD include synchronization relationships when available:

```text
parent_clock_id
transform_to_parent
sync_quality
sync_method
```

### 4.4 Devices, probes, electrodes, and channels

A packet MUST include enough device/probe/electrode/channel metadata to interpret any channelized data it contains.

For ecephys arrays, the packet MUST define:

```text
probe_id or device_id
array_asset_id
channel_index
channel label or channel ID when available
electrode_id or explicit null if no electrode mapping exists
```

When known, the packet SHOULD include:

```text
probe_type
manufacturer
brain_region
electrode coordinates
coordinate frame
impedance or quality metadata
```

The core spec MUST NOT require a complete instrument ontology, part hierarchy, serial-number ontology, or rig configuration ontology.

### 4.5 Array assets

Every dense array asset MUST have enough metadata to open and interpret the array.

`core.array_assets` MUST include:

```text
array_asset_id
session_id
semantic_type
name
kind
uri
format
dtype
shape
dimension_names
```

A time-indexed array MUST include:

```text
clock_id and/or sample_rate_hz
```

A physically calibrated array SHOULD include:

```text
unit
conversion
offset
```

### 4.6 Processing, sorting, and curation

Every derived resource MUST have provenance. When sorted units or processed arrays are present, the packet MUST define the processing context.

`core.processing_runs` SHOULD include:

```text
processing_run_id
software_name
software_version
parameters
created_at
```

`core.sorting_runs` MUST be present when sorted units or spike events are present. It MUST identify the sorting process sufficiently to distinguish outputs from different sorters, versions, or parameterizations.

`core.curation_versions` MUST be present when curated unit identities or quality labels are present. Unit identity MUST be interpreted within a sorting and curation context.

### 4.7 Provenance

The packet MUST record enough provenance to trace:

```text
source resources -> import activity -> core packet resources
core packet resources -> analysis materialization activity -> analysis resources
```

The core provenance model SHOULD remain simple. It SHOULD prioritize reproducibility over complete institutional process modeling.

## 5. Metadata extensions

A metadata extension MAY define richer schemas for subject, procedure, instrument, acquisition, processing, quality control, task, stimulus, or institutional metadata.

An extension MUST declare:

```text
extension_id
version
owner or namespace
schema locations
resources provided
validation rules
core mappings, if any
```

An extension SHOULD specify which fields, if any, map into core tables.

A packet MAY include multiple metadata extensions.

A packet MUST remain core-readable even if extension validators are unavailable, unless the packet explicitly declares that a given extension is required for a specific derived resource.

## 6. Extension registration in the packet catalog

The packet catalog SHOULD register extension resources explicitly.

Example:

```json
{
  "extensions": {
    "aind": {
      "version": "example-version",
      "resources": {
        "data_description": "metadata/aind/data_description.json",
        "subject": "metadata/aind/subject.json",
        "procedures": "metadata/aind/procedures.json",
        "instrument": "metadata/aind/instrument.json",
        "acquisition": "metadata/aind/acquisition.json",
        "processing": "metadata/aind/processing.json",
        "quality_control": "metadata/aind/quality_control.json"
      },
      "required_for_core_conformance": false
    }
  }
}
```

The core validator MUST verify that declared extension files exist if they are listed in the manifest. The core validator MAY skip schema validation for extensions unless an extension validator is installed and requested.

## 7. Mapping extension metadata into core

When importing from a rich metadata system, the importer SHOULD map only analysis-critical fields into core tables.

Example mappings:

```text
extension subject identifier -> core.subjects.subject_id
extension species            -> core.subjects.species
extension session/acquisition start time -> core.sessions.session_start_time
extension probe/device records -> core.devices / core.probes / core.electrodes
extension acquisition timing -> core.clocks / core.array_assets
extension processing records -> core.processing_runs / provenance tables
```

All unmapped extension metadata SHOULD remain available as sidecar metadata.

The importer SHOULD record the mapping activity in provenance, especially when core fields are normalized or derived from extension metadata.

## 8. Metadata promotion policy

The spec SHOULD evolve conservatively. New core metadata fields SHOULD be added only when there is clear evidence that the field is broadly required for interpretation, validation, joining, or analysis.

Before promoting an extension field into core, ask:

```text
Is the field required to interpret a standard resource?
Is the field required to validate a standard relationship?
Is the field commonly used for filtering, grouping, or joining across datasets?
Is the field stable across labs and acquisition systems?
Can the field be typed and validated without a large ontology?
```

If the answer is no, the field SHOULD remain extension metadata.

## 9. Anti-patterns

The core spec SHOULD avoid these patterns:

```text
Requiring complete procedural ontologies for basic packet conformance.
Hiding analysis-critical metadata inside free-form JSON.
Using object paths as the only way to identify resources.
Making extension metadata required to open standard tables or arrays.
Treating the packet manifest as a dumping ground for all metadata.
Duplicating large metadata documents into multiple tables without lineage.
Blocking import because optional institutional metadata is incomplete.
```

## 10. Implementation guidance

A first implementation SHOULD validate metadata in this order:

1. Validate packet manifest fields needed to discover resources.
2. Validate required core tables and required columns.
3. Validate primary keys and references.
4. Validate clocks and time-bearing resources.
5. Validate array asset metadata against actual array stores.
6. Validate provenance for imported and derived resources.
7. Optionally validate extension metadata.

Importation MUST NOT fail solely because optional extension metadata is absent, unless the packet or import job explicitly declares that extension as required.

## 11. Summary

The role of metadata in NWB-Lake POC v0.1 is to make packets identifiable, interpretable, validatable, queryable, and reproducible. The core spec SHOULD require only the metadata needed for those purposes. Richer metadata systems are valuable, but they belong in named extensions and sidecars, not in the mandatory core conformance surface.

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

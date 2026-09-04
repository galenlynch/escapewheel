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

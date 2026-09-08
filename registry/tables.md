# Logical schemas, as the registry stands

**Generated** by `render.py` from `logical_schemas.json`. Do not edit; run
`python registry/build.py` to regenerate.

This is not a specification. `nwb_lake_poc_docs/` is frozen and the revisions bind
where they disagree with it — this states what the two together produced, which is
otherwise answerable only by reading a frozen document and then every amendment to it.

```text
38 tables, 335 columns, 97 references, 70 Tier 2 rules
registry 0.1.0   logical standard escapewheel-logical-v0.1
derived from nwb_lake_poc_docs/02_core_logical_schemas.md, revisions R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40, R41, R43, R44, R45, R46, R47, R48, R49, R50, R51, R52, R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63, R64, R65, R66, R67, R68, R69, R70, R71, R72, R74, R75, R76, R77, R78, R79, R80, R81, R82, R83, R84, R85, R86, R87, R88, R89, R90
```

## Contents

**analysis** (3) — [`analysis.array_assets`](#analysisarray_assets) · [`analysis.array_dimensions`](#analysisarray_dimensions) · [`analysis.spike_events`](#analysisspike_events)

**core** (35) — [`core.array_assets`](#corearray_assets) · [`core.array_channels`](#corearray_channels) · [`core.array_dimensions`](#corearray_dimensions) · [`core.calibration_devices`](#corecalibration_devices) · [`core.calibration_points`](#corecalibration_points) · [`core.calibrations`](#corecalibrations) · [`core.clock_anchors`](#coreclock_anchors) · [`core.clock_observation_intervals`](#coreclock_observation_intervals) · [`core.clocks`](#coreclocks) · [`core.curation_versions`](#corecuration_versions) · [`core.devices`](#coredevices) · [`core.electrode_coordinates`](#coreelectrode_coordinates) · [`core.electrodes`](#coreelectrodes) · [`core.event_stream_observation_intervals`](#coreevent_stream_observation_intervals) · [`core.event_streams`](#coreevent_streams) · [`core.events`](#coreevents) · [`core.intervals`](#coreintervals) · [`core.media_assets`](#coremedia_assets) · [`core.media_frames`](#coremedia_frames) · [`core.preferred_runs`](#corepreferred_runs) · [`core.probes`](#coreprobes) · [`core.processing_run_inputs`](#coreprocessing_run_inputs) · [`core.processing_runs`](#coreprocessing_runs) · [`core.session_experimenters`](#coresession_experimenters) · [`core.sessions`](#coresessions) · [`core.sorting_run_channels`](#coresorting_run_channels) · [`core.sorting_runs`](#coresorting_runs) · [`core.source_files`](#coresource_files) · [`core.spike_events`](#corespike_events) · [`core.subjects`](#coresubjects) · [`core.unit_coordinates`](#coreunit_coordinates) · [`core.unit_electrodes`](#coreunit_electrodes) · [`core.unit_observation_intervals`](#coreunit_observation_intervals) · [`core.unit_quality_labels`](#coreunit_quality_labels) · [`core.units`](#coreunits)

## `analysis`

### `analysis.array_assets`

*Introduced by R20 §5 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `array_asset_id` | int32 | **required** | R20 §5 | Stable array asset ID. |
| `array_asset_name` | string | nullable | R53 §2.3.1 | What `array_asset_id` stands for: the identifier a source or an earlier packet used for this array asset. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** | R20 §5 | Session ID. |
| `semantic_type` | string | **required** | R20 §5 | Semantic type, e.g. ElectricalSeries. |
| `name` | string | **required** | R20 §5 | Human-readable name. |
| `kind` | string | **required** | R20 §5 | `raw`, `ap`, `lfp`, `waveform`, etc. |
| `uri` | string | **required** | R20 §5 | URI/path to array store. |
| `format` | string | **required** | R20 §5 | `zarr_v3` for portable profile. |
| `clock_id` | int32 | nullable | R20 §5 | Clock for time axis. |
| `device_id` | int32 | nullable | R20 §5 | The device that produced this array. |
| `sample_rate_hz` | float64 | nullable | R20 §5 | Sample rate if regularly sampled. |
| `unit` | string | nullable | R20 §5 | Physical unit. |
| `conversion` | float64 | nullable | R20 §5 | Multiply stored values by this before offset. |
| `offset` | float64 | nullable | R20 §5 | Add after conversion. |
| `metadata` | json_string | optional | R20 §5 | Additional metadata. |

**Primary key** — `array_asset_id`  
**Sort** — `array_asset_id`

**References**

- `device_id` → `core.devices` (`device_id`)
- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

### `analysis.array_dimensions`

*Introduced by R20 §5 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `array_asset_id` | int32 | **required** | R20 §5 | Array asset ID. |
| `axis_index` | int64 | **required** | R20 §5 | 0-based axis position in stored order (R3 §5). |
| `dimension_name` | string | **required** | R20 §5 | Axis name. |
| `coordinate_position_column` | string | nullable | R20 §5 | Which column of that resource holds the 0-based position. |
| `coordinate_resource` | string | nullable | R20 §5 | Resource whose rows are this axis's positions (labelled axis). |
| `coordinate_array_asset_id` | int32 | nullable | R20 §5 | A 1-D array holding one value per position (irregular axis). |
| `coordinate_unit` | string | nullable | R20 §5 | Unit of the numeric coordinate values. |
| `step_value` | float64 | nullable | R20 §5 | Increment per position. |
| `origin_value` | float64 | nullable | R20 §5 | Value at position 0 (regular numeric axis). |
| `step_tick_num` | int64 | nullable | R20 §5 | Ticks advanced per position (numerator). |
| `step_tick_den` | int64 | nullable | R20 §5 | Denominator of the step, in ticks. Absent means 1. |
| `origin_tick` | int64 | nullable | R20 §5 | Tick at position 0. |
| `clock_id` | int32 | nullable | R20 §5 | Clock the ticks are counted on (regular tick axis). |

**Primary key** — `array_asset_id`, `axis_index`  
**Sort** — `array_asset_id`, `axis_index`

**References**

- `array_asset_id` → `analysis.array_assets` (`array_asset_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `session_id` → `core.sessions` (`session_id`)

### `analysis.spike_events`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** |  | Session ID. |
| `unit_id` | int32 | **required** |  | Unit ID. |
| `t_tick` | int64 | **required** |  | Spike tick on clock_id, mapped through core.clock_anchors. |
| `clock_id` | int32 | **required** |  | The clock these ticks are on, normally the session's reference. |
| `time_bucket_tick` | int64 | **required** | R30 §3.1 | First tick of the bucket this spike falls in, on clock_id. |

**Primary key** — `session_id`, `unit_id`, `t_tick`  
**Sort** — `session_id`, `clock_id`, `time_bucket_tick`, `unit_id`, `t_tick`

**References**

- `unit_id` → `core.units` (`unit_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `analysis.spike_events.bucket_contains_spike` — error: a spike precedes the start of the bucket it is labelled with
- `analysis.spike_events.buckets_partition_time` — error: buckets overlap in tick range, so the layout they declare is not a partition

## `core`

### `core.array_assets`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `array_asset_id` | int32 | **required** |  | Stable array asset ID. |
| `array_asset_name` | string | nullable | R53 §2.3.1 | What `array_asset_id` stands for: the identifier a source or an earlier packet used for this array asset. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** |  | Session ID. |
| `semantic_type` | string | **required** | R8 §3-4 | Semantic type, e.g. ElectricalSeries. |
| `name` | string | **required** |  | Human-readable name. |
| `kind` | string | **required** | R8 §3-4 | `raw`, `ap`, `lfp`, `waveform`, etc. |
| `uri` | string | **required** |  | URI/path to array store. |
| `format` | string | **required** |  | `zarr_v3` for portable profile. |
| `clock_id` | int32 | nullable |  | Clock for time axis. |
| `device_id` | int32 | nullable | R65 §2.1 | The device that produced this array. |
| `sample_rate_hz` | float64 | nullable |  | Sample rate if regularly sampled. |
| `unit` | string | nullable |  | Physical unit. |
| `conversion` | float64 | nullable |  | Multiply stored values by this before offset. |
| `offset` | float64 | nullable |  | Add after conversion. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `array_asset_id`  
**Sort** — `array_asset_id`

**References**

- `device_id` → `core.devices` (`device_id`)
- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 2

- `core.array_assets.one_scaling_level` — error: scaling is declared both on the array and per channel
- `core.array_assets.sample_rate_matches_axis` — error: sample_rate_hz disagrees with the time axis step

### `core.array_channels`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `array_asset_id` | int32 | **required** |  | Array asset ID. |
| `axis_index` | int64 | **required** | R3 §6.1 | Axis that channel_index indexes, in stored order. |
| `channel_index` | int64 | **required** |  | Channel dimension index. |
| `electrode_id` | int32 | nullable |  | Electrode ID. |
| `channel_label` | string | nullable |  | Human-readable channel label. |
| `inter_sample_shift` | float64 | nullable | R19 §2 | Acquisition time offset within one sample period, in sample periods. |
| `unit` | string | nullable | R19 §2 | Physical unit of the converted value. |
| `offset` | float64 | nullable | R19 §2 | Add after conversion. |
| `conversion` | float64 | nullable | R19 §2 | Multiply stored values by this before offset. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `array_asset_id`, `channel_index`  
**Sort** — `array_asset_id`, `channel_index`

**References**

- `array_asset_id`, `axis_index` → `core.array_dimensions` (`array_asset_id`, `axis_index`)
- `electrode_id` → `core.electrodes` (`electrode_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 1

- `core.array_channels.scaling_pair_complete` — error: a conversion without a unit yields a number in no known quantity

### `core.array_dimensions`

*Introduced by R3 §3.1-3.3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `array_asset_id` | int32 | **required** | R3 §3.1-3.3 | Array asset ID. |
| `axis_index` | int64 | **required** | R3 §3.1-3.3 | 0-based axis position in stored order (R3 §5). |
| `dimension_name` | string | **required** | R3 §3.1-3.3 | Axis name. |
| `coordinate_position_column` | string | nullable | R20 §2 | Which column of that resource holds the 0-based position. |
| `coordinate_resource` | string | nullable | R20 §2 | Resource whose rows are this axis's positions (labelled axis). |
| `coordinate_array_asset_id` | int32 | nullable | R20 §2 | A 1-D array holding one value per position (irregular axis). |
| `coordinate_unit` | string | nullable | R20 §2 | Unit of the numeric coordinate values. |
| `step_value` | float64 | nullable | R20 §2 | Increment per position. |
| `origin_value` | float64 | nullable | R20 §2 | Value at position 0 (regular numeric axis). |
| `step_tick_num` | int64 | nullable | R20 §2 | Ticks advanced per position (numerator). |
| `step_tick_den` | int64 | nullable | R33 §2 | Denominator of the step, in ticks. Absent means 1. |
| `origin_tick` | int64 | nullable | R20 §2 | Tick at position 0. |
| `clock_id` | int32 | nullable | R20 §2 | Clock the ticks are counted on (regular tick axis). |

**Primary key** — `array_asset_id`, `axis_index`  
**Sort** — `array_asset_id`, `axis_index`

**References**

- `array_asset_id` → `core.array_assets` (`array_asset_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `coordinate_array_asset_id` → `core.array_assets` (`array_asset_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 7

- `core.array_dimensions.axis_index_contiguous` — error: axis_index is not contiguous from 0
- `core.array_dimensions.one_coordinate_form` — error: an axis declares more than one coordinate form
- `core.array_dimensions.tick_axis_complete` — error: a regular tick axis needs clock_id, origin_tick and step_tick_num
- `core.array_dimensions.numeric_axis_complete` — error: a regular numeric axis needs origin_value, step_value and coordinate_unit
- `core.array_dimensions.labelled_axis_complete` — error: coordinate_resource and coordinate_position_column must be present together
- `core.array_dimensions.coordinate_resource_is_core` — error: a core axis points outward at a non-core resource (R20 §5.1)
- `core.array_dimensions.step_denominator_positive` — error: a step denominator is not positive, so the step it defines is meaningless

### `core.calibration_devices`

*Introduced by R89 §2.2 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R89 §2.2 | Session ID. |
| `calibration_id` | int32 | **required** | R89 §2.2 | The calibration this row names a device for. |
| `device_id` | int32 | **required** | R89 §2.2 | A device the calibration covers. |

**Primary key** — `calibration_id`, `device_id`  
**Sort** — `calibration_id`, `device_id`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `calibration_id` → `core.calibrations` (`calibration_id`)
- `device_id` → `core.devices` (`device_id`)

### `core.calibration_points`

*Introduced by R89 §2.3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R89 §2.3 | Session ID. |
| `calibration_id` | int32 | **required** | R89 §2.3 | The calibration this point belongs to. |
| `point_index` | int64 | **required** | R89 §2.3 | 0-based position in the curve's own order. The key is not `input_value` even though the inputs are distinct: an equality join on a float64 is not safe, which is why R47 could strike `interval_index` and this stays. |
| `input_value` | float64 | **required** | R89 §2.3 | The setting the point was measured at. |
| `output_value` | float64 | **required** | R89 §2.3 | What the instrument then delivered. |

**Primary key** — `calibration_id`, `point_index`  
**Sort** — `calibration_id`, `point_index`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `calibration_id` → `core.calibrations` (`calibration_id`)

### `core.calibrations`

*Introduced by R89 §2.1 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `calibration_id` | int32 | **required** | R89 §2.1 | Stable calibration ID. |
| `session_id` | int32 | **required** | R89 §2.1 | Session ID. |
| `calibration_name` | string | **required** | R89 §2.1 | What `calibration_id` stands for: the identifier a source or an earlier packet used for this calibration. Required, and composed by the writer where the source names none, since R85 §2.2 makes two calibrations sharing a name one row. |
| `calibration_type` | string | **required** | R89 §2.1 | What was calibrated: `water_volume`, `light_power`, `manipulator_transform`. Open (R8 §4). Named `_type` rather than `_kind` because a `_kind` column is a discriminator (R55 §2.1), and this holds a value that resolves to no table. |
| `calibrated_at` | timestamp | nullable | R89 §2.1 | When the calibration was measured, which is not when it was in force: R89 §1.2 measures 133 and 302 days between them. Null where the source states none, since what a source did not say is not invented (R66 §2.1). |
| `description` | string | nullable | R89 §2.1 | What the source said the calibration was. |
| `input_unit` | string | nullable | R89 §2.1 | The unit of measure of `core.calibration_points.input_value`. On the calibration because it varies per calibration -- seconds for water, volts for opto -- so no literal unit can sit on the value column (R89 §2.3). |
| `output_unit` | string | nullable | R89 §2.1 | The unit of measure of `core.calibration_points.output_value`. |
| `array_asset_id` | int32 | nullable | R89 §2.1 | The array holding this calibration where its content is one rather than a curve: a manipulator transform, a camera's intrinsics (R89 §2.4). |
| `detail_kind` | string | nullable | R89 §2.1 | A table carrying a calibration shape core does not define, as a dotted resource ID. Open, and `resolves: optional`, so a kind the packet cannot resolve records that the content is elsewhere rather than that the row is wrong (R89 §2.5). |
| `metadata` | json_string | optional | R89 §2.1 | What the source stated about this calibration that no column above models. Only the calibration declares one: its key holds an identifier of its own, where both child tables are keyed by other tables' identifiers (R89 §2.6). |

**Primary key** — `calibration_id`  
**Sort** — `calibration_id`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `array_asset_id` → `core.array_assets` (`array_asset_id`)

**Tier 2 rules** — 2

- `core.calibrations.unit_pair_complete` — error: a calibration declares one unit of measure and not the other; the pair is what makes a point readable (R89 §2.3)
- `core.calibrations.points_declare_units` — error: a calibration carries points and declares no units, so nothing says what its values are measured in (R89 §2.3)

### `core.clock_anchors`

*Introduced by R13 §3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `clock_id` | int32 | **required** | R13 §3 | The clock being aligned. |
| `anchor_index` | int64 | **required** | R13 §3 | 0-based position in this clock's anchor sequence. |
| `t_tick` | int64 | **required** | R13 §3 | Tick on clock_id. |
| `parent_tick` | int64 | **required** | R13 §3 | The corresponding tick on parent_clock_id. |

**Primary key** — `clock_id`, `anchor_index`  
**Sort** — the primary key (R10 §2)

**References**

- `clock_id` → `core.clocks` (`clock_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 4

- `core.clock_anchors.requires_parent` — error: anchors are declared for a clock with no parent
- `core.clock_anchors.anchor_index_contiguous` — error: anchor_index is not contiguous from 0
- `core.clock_anchors.monotonic` — error: anchor sequences do not increase together, so interpolation is undefined
- `core.clock_anchors.gap_within_bound` — warning: an anchor gap exceeds twice the median, leaving ticks the mapping does not define (R27 5.3)

### `core.clock_observation_intervals`

*Introduced by R38 §2.1 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R38 §2.1 | Session ID. |
| `clock_id` | int32 | **required** | R38 §2.1 | The clock that was observing. |
| `start_tick` | int64 | **required** | R38 §2.1 | First tick observed, on `clock_id` itself. |
| `stop_tick` | int64 | **required** | R38 §2.1 | Last tick observed, on `clock_id` itself. |

**Primary key** — `session_id`, `clock_id`, `start_tick`  
**Sort** — the primary key (R10 §2)

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 2

- `core.clock_observation_intervals.interval_valid` — error: stop_tick precedes start_tick
- `core.clock_observation_intervals.non_overlapping` — error: observation windows overlap, which would double-count observed time

### `core.clocks`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `clock_id` | int32 | **required** |  | Stable clock ID. |
| `clock_name` | string | nullable | R53 §2.3.1 | What `clock_id` stands for: the identifier a source or an earlier packet used for this clock. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** |  | Session ID. |
| `name` | string | **required** |  | Human-readable clock name. |
| `tick_rate_hz` | float64 | nullable |  | Tick rate as float, required unless exact tick rate provided. |
| `tick_rate_num` | int64 | nullable |  | Exact rational numerator. |
| `tick_rate_den` | int64 | nullable |  | Exact rational denominator. |
| `origin` | string | **required** |  | Origin description. |
| `tick_zero_utc` | timestamp | nullable | R6 §2 | Wall-clock instant of tick 0 on this clock. |
| `parent_clock_id` | int32 | nullable |  | Parent/reference clock. |
| `transform_slope` | float64 | nullable | R3 §3.4 | Parent ticks per this clock's tick, as measured. |
| `transform_offset` | float64 | nullable | R3 §3.4 | Parent-clock tick at this clock's tick 0. |
| `transform_to_parent` | json_string | optional |  | Clock alignment transform. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `clock_id`  
**Sort** — `clock_id`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `parent_clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 8

- `core.clocks.tick_rate_declared` — error: neither tick_rate_hz nor an exact rational rate is present
- `core.clocks.tick_rate_positive` — error: tick rate is not positive
- `core.clocks.transform_pair_complete` — error: transform_slope and transform_offset must be present together
- `core.clocks.transform_requires_parent` — error: a clock transform is declared without a parent clock
- `core.clocks.tick_zero_plausible` — warning: tick_zero_utc is more than a day from session_start_time
- `core.clocks.one_alignment_model` — error: a clock declares both a linear transform and anchor points
- `core.clocks.parent_chain_well_founded` — error: a clock is its own ancestor, so walking the chain does not terminate (R27 3)
- `core.clocks.alignment_declared_for_conversion` — error: a non-reference clock declares no alignment, so it cannot be converted (R27 4)

### `core.curation_versions`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `curation_id` | int32 | **required** |  | Stable curation ID. |
| `curation_name` | string | nullable | R53 §2.3.1 | What `curation_id` stands for: the identifier a source or an earlier packet used for this curation. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `sorting_run_id` | int32 | **required** |  | Sorting run ID. |
| `session_id` | int32 | **required** |  | Session ID. |
| `curator` | string | nullable |  | Curator. |
| `curation_tool` | string | nullable |  | Tool. |
| `curation_tool_version` | string | nullable |  | Tool version. |
| `processing_run_id` | int32 | nullable | R41 §2.1 | The run that produced this record, where provenance is recorded. |
| `parent_curation_id` | int32 | nullable |  | Parent curation. |
| `created_at` | timestamp | nullable |  | Creation time. |
| `notes` | string | nullable |  | Notes. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `curation_id`  
**Sort** — `curation_id`

**References**

- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)
- `sorting_run_id` → `core.sorting_runs` (`sorting_run_id`)
- `parent_curation_id` → `core.curation_versions` (`curation_id`)

### `core.devices`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `device_id` | int32 | **required** |  | Stable device ID. |
| `device_name` | string | nullable | R53 §2.3.1 | What `device_id` stands for: the identifier a source or an earlier packet used for this device. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** | R88 §2.1 | Session if device record is session-scoped. |
| `name` | string | **required** |  | Human-readable name. |
| `manufacturer` | string | nullable |  | Manufacturer. |
| `model` | string | nullable |  | Model. |
| `firmware_version` | string | nullable | R66 §2.1 | The firmware the instrument was running, verbatim as its source stated it. |
| `hardware_version` | string | nullable | R66 §2.1 | The instrument's hardware revision, verbatim as its source stated it. |
| `serial_number` | string | nullable |  | Serial number. |
| `parent_device_id` | int32 | nullable | R67 §2.1 | The device this one was attached to -- a probe's headstage, a headstage's connect board. Null at the root of a chain, or where no source states it. |
| `parent_port` | string | nullable | R85 §2.1 | Which port, dock or slot of `parent_device_id` this device attached to. Null where the attachment is stated and its coordinate is not. Establishes nothing about identity: two rows may share a parent and a port (R85 §2.3). |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `device_id`  
**Sort** — `device_id`

**References**

- `parent_device_id` → `core.devices` (`device_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.devices.parent_chain_well_founded` — error: a device is its own ancestor, or its attachment chain does not terminate (R67 §2.3)
- `core.devices.serial_identifies_one_device` — error: one serial number appears on more than one device row; a device is the physical object (R67 §2.2)

### `core.electrode_coordinates`

*Introduced by R19 §3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `electrode_id` | int32 | **required** | R19 §3 | Electrode ID. |
| `coordinate_frame` | string | **required** | R19 §3 | The frame these coordinates are in. |
| `coordinate_basis` | string | **required** | R58 §2.1 | What the coordinate asserts: `planned` where the probe was meant to go, `measured` where it was, `nominal` where it is by construction and nothing aimed or observed it (R64 §2.1). A consumer that does not recognise a basis MUST NOT treat it as measured (R58 §2.2). |
| `region_id` | int32 | nullable | R59 §2.1 | The atlas structure this position falls in, numbered by the atlas that `coordinate_frame` names. |
| `region_label` | string | nullable | R59 §2.1 | That structure's short name, so a consumer without the atlas can read the annotation. |
| `processing_run_id` | int32 | nullable | R58 §2.3 | The run that produced this coordinate. |
| `x_um` | float64 | nullable | R19 §3 | X in micrometres, in that frame. |
| `y_um` | float64 | nullable | R19 §3 | Y in micrometres. |
| `z_um` | float64 | nullable | R19 §3 | Z in micrometres. |

**Primary key** — `electrode_id`, `coordinate_frame`, `coordinate_basis`  
**Sort** — the primary key (R10 §2)

**References**

- `electrode_id` → `core.electrodes` (`electrode_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)

### `core.electrodes`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `electrode_id` | int32 | **required** |  | Stable electrode ID. |
| `electrode_name` | string | nullable | R53 §2.3.1 | What `electrode_id` stands for: the identifier a source or an earlier packet used for this electrode. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** |  | Session ID. |
| `probe_id` | int32 | nullable |  | Probe ID. |
| `local_electrode_label` | string | nullable | R8 §2 | Opaque source label; undefined base, not an offset. |
| `local_channel_label` | string | nullable | R8 §2 | Opaque source label; undefined base, not an offset. |
| `impedance_ohm` | float64 | nullable |  | Impedance. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `electrode_id`  
**Sort** — `electrode_id`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `probe_id` → `core.probes` (`probe_id`)

### `core.event_stream_observation_intervals`

*Introduced by R25 §2 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `event_stream_id` | int32 | **required** | R25 §2 | The stream being observed. |
| `start_tick` | int64 | **required** | R25 §2 | First observed tick, on the stream's clock. |
| `stop_tick` | int64 | **required** | R25 §2 | Last observed tick, on the stream's clock. |

**Primary key** — `event_stream_id`, `start_tick`  
**Sort** — the primary key (R10 §2)

**References**

- `event_stream_id` → `core.event_streams` (`event_stream_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.event_stream_observation_intervals.interval_valid` — error: stop_tick precedes start_tick
- `core.event_stream_observation_intervals.non_overlapping` — error: observation windows overlap, which would double-count observed time

### `core.event_streams`

*Introduced by R23 §2-3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `event_stream_id` | int32 | **required** | R23 §2-3 | Stable ID. |
| `event_stream_name` | string | nullable | R53 §2.3.1 | What `event_stream_id` stands for: the identifier a source or an earlier packet used for this event stream. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** | R23 §2-3 | Session ID. |
| `name` | string | **required** | R23 §2-3 | Human-readable name, e.g. left_lick_sensor. |
| `device_id` | int32 | nullable | R23 §2-3 | The device that produced it, where one is identified. |
| `clock_id` | int32 | **required** | R23 §2-3 | The clock its events are timed on. |
| `processing_run_id` | int32 | nullable | R23 §2-3 | The run that produced it. Null means it came off the device as recorded. A narrow exception to R9 §4: the manifest records outputs per resource and cannot distinguish streams within one table. |
| `metadata` | json_string | optional | R23 §2-3 | Free-form metadata. |

**Primary key** — `event_stream_id`  
**Sort** — the primary key (R10 §2)

**References**

- `session_id` → `core.sessions` (`session_id`)
- `device_id` → `core.devices` (`device_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)

**Tier 2 rules** — 1

- `core.event_streams.observation_declared` — info *(advisory, R26)*: streams carry no observation intervals and their clock declares none, so no rate over them has a denominator

### `core.events`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** |  | Session ID. |
| `event_id` | int32 | **required** |  | Stable event ID. |
| `event_name` | string | nullable | R53 §2.3.1 | What `event_id` stands for: the identifier a source or an earlier packet used for this event. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `stream_id` | int32 | **required** | R23 §2-3 | The stream this event belongs to. |
| `event_type` | string | **required** | R11 §3-4 | Event type. |
| `t_tick` | int64 | **required** |  | Event tick. |
| `clock_id` | int32 | **required** |  | Event clock. |
| `payload` | json_string | optional |  | Event payload. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `session_id`, `event_id`  
**Sort** — `session_id`, `clock_id`, `t_tick`, `event_type`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `stream_id` → `core.event_streams` (`event_stream_id`)

**Tier 2 rules** — 2

- `core.events.clock_matches_stream` — error: an event's clock_id disagrees with its stream's
- `core.events.within_observation` — warning: events fall outside the observation window in force for their stream

### `core.intervals`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** |  | Session ID. |
| `interval_kind` | string | **required** | R54 §2.1 | The resource that specialises this interval, as a dotted resource ID. Open (R8 §4); resolved as R55 §2.3's shared key. |
| `interval_id` | int32 | **required** | R54 §2.1 | Stable trial ID. |
| `start_tick` | int64 | **required** | R45 §2.4 | First tick of the trial, inclusive, on `clock_id`. |
| `stop_tick` | int64 | **required** | R45 §2.4 | Last tick of the trial, inclusive, on `clock_id`. |
| `clock_id` | int32 | **required** |  | Clock for start/stop ticks. |
| `metadata` | json_string | optional |  | Additional trial metadata. |

**Primary key** — `session_id`, `interval_kind`, `interval_id`  
**Sort** — `session_id`, `interval_kind`, `interval_id`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 1

- `core.intervals.interval_valid` — error: stop_tick precedes start_tick

### `core.media_assets`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `media_asset_id` | int32 | **required** |  | Stable media asset ID. |
| `media_asset_name` | string | nullable | R53 §2.3.1 | What `media_asset_id` stands for: the identifier a source or an earlier packet used for this media asset. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** |  | Session ID. |
| `semantic_type` | string | **required** | R8 §3-4 | e.g. BehaviorVideo. |
| `name` | string | **required** |  | Name. |
| `uri` | string | **required** |  | Media file URI. |
| `format` | string | **required** |  | e.g. mp4. |
| `pts_rate_num` | int64 | nullable | R70 §2.1 | Presentation timestamps per second in this asset's container: numerator. |
| `pts_rate_den` | int64 | nullable | R70 §2.1 | Presentation timestamps per second in this asset's container: denominator. |
| `clock_id` | int32 | nullable |  | Clock for frame timing. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `media_asset_id`  
**Sort** — the primary key (R10 §2)

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 3

- `core.media_assets.pts_rate_pair_complete` — error: an asset declares one half of its presentation-timestamp rate; half a rational is unusable (R70 §2.2)
- `core.media_assets.pts_rate_declared_where_frames_carry_pts` — error: frames carry pts for an asset that does not say what those timestamps count (R70 §2.2)
- `core.media_assets.pts_rate_positive` — error: a presentation-timestamp rate is not positive

### `core.media_frames`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `media_asset_id` | int32 | **required** |  | Media asset ID. |
| `frame_index` | int64 | **required** |  | Frame index. |
| `t_tick` | int64 | **required** |  | Frame time tick. |
| `clock_id` | int32 | **required** |  | Clock ID. |
| `pts` | int64 | nullable | R68 §2.1 | Container presentation timestamp, verbatim in the container's own time base. |
| `dropped` | bool | nullable |  | Dropped-frame flag. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `media_asset_id`, `frame_index`  
**Sort** — `media_asset_id`, `frame_index`

**References**

- `clock_id` → `core.clocks` (`clock_id`)
- `media_asset_id` → `core.media_assets` (`media_asset_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.media_frames.frame_index_contiguous` — error: frame_index is not contiguous from 0 within an asset
- `core.media_frames.pts_increases_with_frame_index` — error: pts is not strictly increasing in frame_index order within an asset, so the frames are not numbered in presentation order (R69 §2.1)

### `core.preferred_runs`

*Introduced by R41 §2.3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R41 §2.3 | Session ID. |
| `activity_type` | string | **required** | R41 §2.3 | Which kind of output this preference is about. Open, as R9 §6 leaves it. |
| `scope_kind` | string | **required** | R49 §2.1 | The resource whose primary key `scope` holds, as a dotted resource ID (R49 §2.2). Open. |
| `scope` | string | **required** | R41 §2.3 | What it applies to -- a probe_id, an array_asset_id, a camera -- or the session_id itself where the preference is session-wide. |
| `processing_run_id` | int32 | **required** | R41 §2.3 | The preferred run. |
| `chosen_at` | timestamp | nullable | R41 §2.3 | When the choice was made. |
| `reason` | string | nullable | R41 §2.3 | Why, in one line. |

**Primary key** — `session_id`, `activity_type`, `scope_kind`, `scope`  
**Sort** — the primary key (R10 §2)

**References**

- `session_id` → `core.sessions` (`session_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)

**Tier 2 rules** — 3

- `core.preferred_runs.activity_matches_run` — error: a preference names a run whose activity_type differs from the preference's
- `core.preferred_runs.run_in_session` — error: a preference names a run belonging to another session
- `core.preferred_runs.not_superseded` — warning: the preferred run is superseded by another run

### `core.probes`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `probe_id` | int32 | **required** |  | Stable probe ID. |
| `probe_name` | string | nullable | R53 §2.3.1 | What `probe_id` stands for: the identifier a source or an earlier packet used for this probe. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** |  | Session ID. |
| `device_id` | int32 | nullable |  | Associated device. |
| `name` | string | nullable |  | Probe name. |
| `probe_type` | string | nullable |  | Probe type, e.g. Neuropixels 1.0. |
| `manufacturer` | string | nullable |  | Manufacturer. |
| `serial_number` | string | nullable |  | Serial number. |
| `insertion_name` | string | nullable |  | Insertion label. |
| `target_region` | string | nullable |  | Intended target. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `probe_id`  
**Sort** — `probe_id`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `device_id` → `core.devices` (`device_id`)

### `core.processing_run_inputs`

*Introduced by R9 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R88 §2.1 | Session ID. |
| `processing_run_id` | int32 | **required** | R9 | The run. |
| `source_file_id` | int32 | **required** | R9 | A source file the run consumed. |

**Primary key** — `processing_run_id`, `source_file_id`  
**Sort** — `processing_run_id`, `source_file_id`

**References**

- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `source_file_id` → `core.source_files` (`source_file_id`)
- `session_id` → `core.sessions` (`session_id`)

### `core.processing_runs`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `processing_run_id` | int32 | **required** |  | Stable processing run ID. |
| `processing_run_name` | string | nullable | R53 §2.3.1 | What `processing_run_id` stands for: the identifier a source or an earlier packet used for this processing run. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** | R88 §2.1 | Session ID if session-scoped. |
| `activity_type` | string | **required** | R8 §3-4 | import, validation, sorting, curation, materialization, etc. |
| `scope` | string | nullable | R44 §2.1 | What this run is about -- a probe_id, an array_asset_id, a camera -- or the session_id itself where the run is session-wide. Open, as activity_type is. |
| `scope_kind` | string | nullable | R49 §2.1 | The resource whose primary key `scope` holds, as a dotted resource ID -- `core.probes`, `core.array_assets`. Open (R8 §4); a value naming no declared resource means the scope is not a packet resource. Set with `scope` or not at all. |
| `supersedes_run_id` | int32 | nullable | R50 §2 | The run this one replaces, if any. |
| `software_name` | string | nullable |  | Software name. |
| `software_version` | string | nullable |  | Software version. |
| `code_uri` | string | nullable |  | Code reference. |
| `parameters` | json_string | optional |  | Parameters. |
| `started_at` | timestamp | nullable |  | Start time. |
| `ended_at` | timestamp | nullable |  | End time. |
| `status` | string | **required** | R8 §3-4 | succeeded, failed, partial, etc. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `processing_run_id`  
**Sort** — the primary key (R10 §2)

**References**

- `supersedes_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 7

- `core.processing_runs.no_failed_runs` — error: a failed run is recorded in a committed packet
- `core.processing_runs.materialization_records_software` — error: a materialization run does not record the software that produced it
- `core.processing_runs.supersedes_not_self` — error: a run supersedes_run_id itself
- `core.processing_runs.supersedes_well_founded` — error: the supersedes chain contains a cycle
- `core.processing_runs.undeclared_currency` — error: several runs share an activity and scope and none is preferred, so a consumer cannot choose between them (R82 §2.1)
- `core.processing_runs.scope_undeclared` — error: an activity has several runs and at least one records no scope, so whether they compete cannot be determined (R82 §2.2)
- `core.processing_runs.scope_pair_complete` — error: a run declares one half of its scope; the pair is what carries the meaning (R49 §2.4)

### `core.session_experimenters`

*Introduced by R3 §3.1-3.3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R3 §3.1-3.3 | Session ID. |
| `experimenter` | string | **required** | R3 §3.1-3.3 | One experimenter. |

**Primary key** — `session_id`, `experimenter`  
**Sort** — `session_id`, `experimenter`

**References**

- `session_id` → `core.sessions` (`session_id`)

### `core.sessions`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** |  | Stable session ID. |
| `session_name` | string | nullable | R53 §2.3.1 | What `session_id` stands for: the identifier a source or an earlier packet used for this session. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `subject_id` | int32 | **required** |  | Subject ID. |
| `session_start_time` | timestamp | **required** |  | Session start time if known; if unknown use explicit null only in non-strict test packets. |
| `session_end_time` | timestamp | nullable | R25 §2 | When the session ended, UTC. Metadata, not derived from the tables (R25 5). |
| `reference_clock_id` | int32 | nullable | R27 §2 | The clock this session's times are reported on by default (R27 2). |
| `session_description` | string | nullable |  | Human-readable session description. |
| `institution` | string | nullable |  | Institution/lab. |
| `task_name` | string | nullable |  | Task/protocol name. |
| `source_session_id` | int32 | nullable |  | Source-system session ID if different. |
| `metadata` | json_string | optional |  | Additional session metadata. |
| `t_zero_tick` | int64 | nullable | R39 §2.2 | Earliest observed tick, on `reference_clock_id`; the origin seconds count from. |

**Primary key** — `session_id`  
**Sort** — `session_id`

**References**

- `subject_id` → `core.subjects` (`subject_id`)
- `reference_clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 4

- `core.sessions.manifest_sessions_match` — error: the manifest's session inventory and core.sessions disagree; the manifest names a session by its session_name, since an assigned session_id means nothing outside the packet that assigned it (R53 §2.3.1)
- `core.sessions.session_interval_valid` — error: session_end_time precedes session_start_time
- `core.sessions.reference_clock_declared` — error: a session declaring more than one clock names no reference clock (R27 2)
- `core.sessions.every_clock_reaches_the_reference` — error: a clock does not reach the session's reference clock, so it cannot be converted to it

### `core.sorting_run_channels`

*Introduced by R83 §2.1 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R83 §2.1 | Session ID. |
| `sorting_run_id` | int32 | **required** | R83 §2.1 | The run whose channel list this row belongs to. |
| `channel_index` | int64 | **required** | R83 §2.1 | 0-based position in the run's own channel order, which is what a source's channel index counts (R83 §1.1). int64 as every structural index is. |
| `electrode_id` | int32 | **required** | R83 §2.1 | The contact at that position. |

**Primary key** — `session_id`, `sorting_run_id`, `channel_index`  
**Sort** — `session_id`, `sorting_run_id`, `channel_index`

**References**

- `sorting_run_id` → `core.sorting_runs` (`sorting_run_id`)
- `electrode_id` → `core.electrodes` (`electrode_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.sorting_run_channels.contact_listed_once` — error: a contact appears more than once in one run's channel list
- `core.sorting_run_channels.index_contiguous` — error: channel_index is not contiguous from 0 within a run

### `core.sorting_runs`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `sorting_run_id` | int32 | **required** |  | Stable sorting run ID. |
| `sorting_run_name` | string | nullable | R53 §2.3.1 | What `sorting_run_id` stands for: the identifier a source or an earlier packet used for this sorting run. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `session_id` | int32 | **required** |  | Session ID. |
| `probe_id` | int32 | nullable |  | Probe ID. |
| `clock_id` | int32 | **required** | R38 §2.2 | Clock the run's spike ticks are counted on. |
| `sorter_name` | string | nullable |  | Sorter name. |
| `sorter_version` | string | nullable |  | Sorter version. |
| `processing_run_id` | int32 | nullable | R41 §2.1 | The run that produced this record, where provenance is recorded. |
| `amplitude_unit` | string | nullable | R11 §2 | Unit of core.spike_events.amplitude for this run, e.g. uV, adc. |
| `parameters` | json_string | optional |  | Sorter parameters. |
| `input_array_asset_id` | int32 | nullable |  | Input array asset. |
| `started_at` | timestamp | nullable |  | Start time. |
| `ended_at` | timestamp | nullable |  | End time. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `sorting_run_id`  
**Sort** — `sorting_run_id`

**References**

- `clock_id` → `core.clocks` (`clock_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)
- `probe_id` → `core.probes` (`probe_id`)
- `input_array_asset_id` → `core.array_assets` (`array_asset_id`)

**Tier 2 rules** — 1

- `core.sorting_runs.amplitude_unit_declared` — error: spikes carry amplitudes but the sorting run declares no amplitude_unit

### `core.source_files`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `source_file_id` | int32 | **required** |  | Stable source file ID. |
| `source_file_name` | string | nullable | R53 §2.3.1 | What `source_file_id` stands for: the identifier a source or an earlier packet used for this source file. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `uri` | string | **required** |  | Source URI/path. |
| `format` | string | nullable |  | Source format. |
| `sha256` | string | nullable |  | Checksum. |
| `size_bytes` | int64 | nullable |  | Size. |
| `modified_at` | timestamp | nullable |  | Modification time if known. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `source_file_id`  
**Sort** — the primary key (R10 §2)

### `core.spike_events`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** |  | Session ID. |
| `unit_id` | int32 | **required** |  | Unit ID. |
| `t_tick` | int64 | **required** |  | Spike tick. |
| `clock_id` | int32 | **required** |  | Clock ID. |
| `amplitude` | float32 | nullable |  | Spike amplitude if available. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `session_id`, `unit_id`, `t_tick`  
**Sort** — `session_id`, `unit_id`, `t_tick`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `unit_id` → `core.units` (`unit_id`)

**Tier 2 rules** — 2

- `core.spike_events.ticks_within_clock_span` — warning: negative ticks on a clock with no absolute reference
- `core.spike_events.within_observation` — warning: spikes fall outside the observation window in force for their unit

### `core.subjects`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `subject_id` | int32 | **required** |  | Stable subject ID. |
| `subject_name` | string | nullable | R53 §2.3.1 | What `subject_id` stands for: the identifier a source or an earlier packet used for this subject. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `species` | string | nullable |  | Species. |
| `strain` | string | nullable |  | Strain/background. |
| `sex` | string | nullable |  | Sex if recorded. |
| `date_of_birth` | date | nullable |  | Date of birth if known. |
| `genotype` | string | nullable |  | Genotype summary. |
| `metadata` | json_string | optional |  | Additional subject metadata. |

**Primary key** — `subject_id`  
**Sort** — `subject_id`

### `core.unit_coordinates`

*Introduced by R28 §2-4 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R28 §2-4 | Session ID. |
| `unit_id` | int32 | **required** | R28 §2-4 | Unit ID. |
| `coordinate_frame` | string | **required** | R28 §2-4 | The frame these coordinates are in. Open, as R19 §3 left it. |
| `coordinate_basis` | string | **required** | R58 §2.1 | What the coordinate asserts: `planned` where the probe was meant to go, `measured` where it was, `nominal` where it is by construction and nothing aimed or observed it (R64 §2.1). A consumer that does not recognise a basis MUST NOT treat it as measured (R58 §2.2). |
| `region_id` | int32 | nullable | R59 §2.1 | The atlas structure this position falls in, numbered by the atlas that `coordinate_frame` names. |
| `region_label` | string | nullable | R59 §2.1 | That structure's short name, so a consumer without the atlas can read the annotation. |
| `processing_run_id` | int32 | nullable | R58 §2.3 | The run that produced this coordinate. |
| `x_um` | float64 | nullable | R28 §2-4 | X in micrometres, in that frame. |
| `y_um` | float64 | nullable | R28 §2-4 | Y in micrometres. |
| `z_um` | float64 | nullable | R28 §2-4 | Z in micrometres. |

**Primary key** — `session_id`, `unit_id`, `coordinate_frame`, `coordinate_basis`  
**Sort** — the primary key (R10 §2)

**References**

- `unit_id` → `core.units` (`unit_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)

### `core.unit_electrodes`

*Introduced by R28 §2-4 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R28 §2-4 | Session ID. |
| `unit_id` | int32 | **required** | R28 §2-4 | Unit ID. |
| `electrode_id` | int32 | **required** | R28 §2-4 | An electrode this unit was detected on. |
| `channel_index` | int64 | nullable | R50 §2 | 0-based position of this electrode in the unit's channel list, where a dense array axis is indexed by it (R20 §2). Nothing joins on it. |
| `is_primary` | bool | nullable | R28 §2-4 | Whether this is the unit's peak electrode. |

**Primary key** — `session_id`, `unit_id`, `electrode_id`  
**Sort** — the primary key (R10 §2)

**References**

- `unit_id` → `core.units` (`unit_id`)
- `electrode_id` → `core.electrodes` (`electrode_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 3

- `core.unit_electrodes.one_primary` — warning: a unit designates more than one peak electrode (R28 2)
- `core.unit_electrodes.channel_index_contiguous` — error: channel_index is not contiguous from 0, so a dense axis indexed by it addresses rows that are not there
- `core.unit_electrodes.electrode_is_a_run_channel` — error: a unit sits on an electrode its sorting run did not use

### `core.unit_observation_intervals`

*Introduced by R18 §2 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R18 §2 | Session ID. |
| `unit_id` | int32 | **required** | R18 §2 | Unit ID. |
| `start_tick` | int64 | **required** | R18 §2 | First tick, inclusive. |
| `stop_tick` | int64 | **required** | R18 §2 | Last tick, inclusive. |
| `clock_id` | int32 | **required** | R18 §2 | Clock for the interval bounds. |

**Primary key** — `session_id`, `unit_id`, `start_tick`  
**Sort** — the primary key (R10 §2)

**References**

- `unit_id` → `core.units` (`unit_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.unit_observation_intervals.interval_valid` — error: stop_tick precedes start_tick
- `core.unit_observation_intervals.non_overlapping` — error: observation windows overlap, which would double-count observed time

### `core.unit_quality_labels`

*Introduced by R16 §2-3 (R29 §2). A column with no revision came from `02` unamended.*

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** | R16 §2-3 | Session ID. |
| `unit_id` | int32 | **required** | R16 §2-3 | Unit ID. |
| `source` | string | **required** | R16 §2-3 | What produced the label, e.g. kilosort, decoder, bombcell. |
| `label` | string | **required** | R16 §2-3 | The source's own label, verbatim. |
| `normalized_label` | string | nullable | R16 §2-3 | Declared projection onto the closed set. Null where the source's label does not project. |
| `confidence` | float64 | nullable | R16 §2-3 | The source's confidence, where it reports one. |

**Primary key** — `session_id`, `unit_id`, `source`  
**Sort** — the primary key (R10 §2)

**References**

- `unit_id` → `core.units` (`unit_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 1

- `core.unit_quality_labels.projection_is_consistent` — error: a (source, label) pair projects onto more than one normalized_label

### `core.units`

| Column | Type | Presence | Since | Description |
|---|---|:---:|---|---|
| `session_id` | int32 | **required** |  | Session ID. |
| `unit_id` | int32 | **required** |  | Stable unit ID. |
| `unit_name` | string | nullable | R53 §2.3.1 | What `unit_id` stands for: the identifier a source or an earlier packet used for this unit. The only bridge between two packets that numbered it differently (R53 §2.5). |
| `probe_id` | int32 | nullable |  | Probe ID. |
| `sorting_run_id` | int32 | **required** |  | Sorting run ID. |
| `curation_id` | int32 | **required** |  | Curation ID. |
| `local_unit_label` | string | nullable | R8 §2 | Opaque source label; undefined base, not an offset. |
| `quality_label` | string | nullable | R11 §3-4 | Quality label. |
| `quality_label_source` | string | nullable | R16 §2-3 | Which core.unit_quality_labels source the designated label came from. |
| `firing_rate_hz` | float64 | nullable |  | Firing rate if known. |
| `n_spikes` | int64 | nullable | R5 | Total spikes for this unit in this context. |
| `first_spike_tick` | int64 | nullable | R5 | Lowest t_tick for this unit. |
| `last_spike_tick` | int64 | nullable | R5 | Highest t_tick for this unit. |
| `metadata` | json_string | optional |  | Additional metadata. |

**Primary key** — `unit_id`  
**Sort** — `unit_id`

**References**

- `session_id` → `core.sessions` (`session_id`)
- `probe_id` → `core.probes` (`probe_id`)
- `sorting_run_id` → `core.sorting_runs` (`sorting_run_id`)
- `curation_id` → `core.curation_versions` (`curation_id`)

**Tier 2 rules** — 4

- `core.units.spike_summary_consistent` — error: n_spikes, first_spike_tick or last_spike_tick disagrees with core.spike_events
- `core.units.designated_label_is_recorded` — error: the designated quality label is not among the recorded ones
- `core.units.designated_label_pair_complete` — error: quality_label and quality_label_source must be present together
- `core.units.observation_declared` — info *(advisory, R26)*: units carry no observation intervals and their clock declares none, so no rate over them has a denominator

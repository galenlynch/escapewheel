# Logical schemas, as the registry stands

**Generated** by `render.py` from `logical_schemas.json`. Do not edit; run
`python registry/build.py` to regenerate.

This is not a specification. `nwb_lake_poc_docs/` is frozen and the revisions bind
where they disagree with it — this states what the two together produced, which is
otherwise answerable only by reading a frozen document and then every amendment to it.

```text
43 tables, 351 columns, 111 references, 77 Tier 2 rules
registry 0.1.0   logical standard escapewheel-logical-v0.1
derived from nwb_lake_poc_docs/02_core_logical_schemas.md, revisions R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36, R37, R38, R39, R40, R41, R43, R44, R45, R46, R47, R48, R49, R50, R51, R52, R53, R54, R55, R56, R57, R58, R59, R60, R61, R62, R63, R64, R65, R66, R67, R68, R69, R70, R71, R72, R74, R75, R76, R77, R78, R79, R80, R81, R82, R83, R84, R85, R86, R87, R88, R89, R90, R91, R92, R93, R94, R95, R96, R97, R98, R99, R100, R101, R102, R103, R104, R105, R106, R107, R108, R109, R110, R111, R112, R113, R114, R115, R116, R117, R118, R119
```

## Contents

**analysis** (3) — [`analysis.array_assets`](#analysisarray_assets) · [`analysis.array_dimensions`](#analysisarray_dimensions) · [`analysis.spike_events`](#analysisspike_events)

**core** (40) — [`core.array_assets`](#corearray_assets) · [`core.array_channels`](#corearray_channels) · [`core.array_dimensions`](#corearray_dimensions) · [`core.calibration_devices`](#corecalibration_devices) · [`core.calibration_points`](#corecalibration_points) · [`core.calibrations`](#corecalibrations) · [`core.clock_anchors`](#coreclock_anchors) · [`core.clock_observation_intervals`](#coreclock_observation_intervals) · [`core.clock_phase_steps`](#coreclock_phase_steps) · [`core.clocks`](#coreclocks) · [`core.coordinate_frame_axes`](#corecoordinate_frame_axes) · [`core.coordinate_frames`](#corecoordinate_frames) · [`core.curation_versions`](#corecuration_versions) · [`core.devices`](#coredevices) · [`core.electrode_coordinate_values`](#coreelectrode_coordinate_values) · [`core.electrode_coordinates`](#coreelectrode_coordinates) · [`core.electrodes`](#coreelectrodes) · [`core.event_stream_observation_intervals`](#coreevent_stream_observation_intervals) · [`core.event_streams`](#coreevent_streams) · [`core.events`](#coreevents) · [`core.intervals`](#coreintervals) · [`core.media_assets`](#coremedia_assets) · [`core.media_frames`](#coremedia_frames) · [`core.preferred_runs`](#corepreferred_runs) · [`core.probes`](#coreprobes) · [`core.processing_run_inputs`](#coreprocessing_run_inputs) · [`core.processing_runs`](#coreprocessing_runs) · [`core.session_experimenters`](#coresession_experimenters) · [`core.sessions`](#coresessions) · [`core.sorting_run_channels`](#coresorting_run_channels) · [`core.sorting_runs`](#coresorting_runs) · [`core.source_files`](#coresource_files) · [`core.spike_events`](#corespike_events) · [`core.subjects`](#coresubjects) · [`core.unit_coordinate_values`](#coreunit_coordinate_values) · [`core.unit_coordinates`](#coreunit_coordinates) · [`core.unit_electrodes`](#coreunit_electrodes) · [`core.unit_observation_intervals`](#coreunit_observation_intervals) · [`core.unit_quality_labels`](#coreunit_quality_labels) · [`core.units`](#coreunits)

## `analysis`

### `analysis.array_assets`

*Introduced by R20 §5 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R20 §5 | Session ID. |
| `array_asset_id` | int32 | **required** | — | R20 §5 | Stable array asset ID. |
| `array_asset_name` | string | **required** | free | R95 §3.1 | What `array_asset_id` stands for: the identifier a source or an earlier packet used for this array asset. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `semantic_type` | string | nullable | open | R107 §3.1 | What quantity the asset holds, where the row's declared facts do not already say. Null is the ordinary case: a writer MUST NOT fill it where the device, the unit, the channel map or the dimensions carry the answer. An unrecognised value is a label carrying no contract (Part 01 §3.17). |
| `band` | string | nullable | open; reserving `wideband`, `ap`, `lfp` | R107 §3.1 | Which band of a sampled signal this array holds: `wideband` unfiltered, `ap` the action-potential band, `lfp` the local field potential band, with Part 02 §9.3's meanings. A conventional shorthand for a filter the packet does not record. Null where the signal was not split. |
| `uri` | string | **required** | free | R20 §5 | URI/path to array store. |
| `format` | string | **required** | open | R20 §5 | `zarr_v3` for portable profile. |
| `clock_id` | int32 | nullable | — | R20 §5 | Clock for time axis. |
| `device_id` | int32 | nullable | — | R20 §5 | The device that produced this array. |
| `processing_run_id` | int32 | nullable | — | R102 §3.1 | The run that produced this array. Null means it was acquired rather than computed, which is the reading R23 §2 gives a stream. |
| `sample_rate_hz` | float64 | nullable | — | R20 §5 | Sample rate if regularly sampled. |
| `unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The physical unit of the array's values, as a UCUM code. |
| `conversion` | float64 | nullable | — | R20 §5 | Multiply stored values by this before offset. |
| `offset` | float64 | nullable | — | R20 §5 | Add after conversion. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `array_asset_id`  

**References**

- `device_id` → `core.devices` (`device_id`)
- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)

### `analysis.array_dimensions`

*Introduced by R20 §5 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `array_asset_id` | int32 | **required** | — | R20 §5 | Array asset ID. |
| `axis_index` | int64 | **required** | — | R20 §5 | 0-based axis position in stored order (Part 03 §6.2). |
| `dimension_name` | string | **required** | free | R20 §5 | Axis name. |
| `coordinate_position_column` | string | nullable | free | R20 §5 | Which column of that resource holds the 0-based position. |
| `coordinate_resource` | string | nullable | resolves required | R100 §2.1 | The table whose rows are this axis's positions, as a dotted resource ID. The column of it holding the 0-based position is `coordinate_position_column` (R20 §2.4). |
| `coordinate_array_asset_id` | int32 | nullable | — | R20 §5 | A 1-D array holding one value per position (irregular axis). |
| `coordinate_unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The physical unit of this axis's coordinate values, as a UCUM code. |
| `step_value` | float64 | nullable | — | R20 §5 | Increment per position. |
| `origin_value` | float64 | nullable | — | R20 §5 | Value at position 0 (regular numeric axis). |
| `step_tick_num` | int64 | nullable | — | R20 §5 | Ticks advanced per position (numerator). |
| `step_tick_den` | int64 | nullable | — | R20 §5 | Denominator of the step, in ticks. Absent means 1. |
| `origin_tick` | int64 | nullable | — | R20 §5 | Tick at position 0. |
| `clock_id` | int32 | nullable | — | R20 §5 | Clock the ticks are counted on (regular tick axis). |

**Primary key** — `array_asset_id`, `axis_index`  

**References**

- `array_asset_id` → `analysis.array_assets` (`array_asset_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `session_id` → `core.sessions` (`session_id`)
- `coordinate_array_asset_id` → `analysis.array_assets` (`array_asset_id`)

**Tier 2 rules** — 1

- `analysis.array_dimensions.coordinate_pair_complete` — error: an axis declares one half of its labelled coordinates; the resource says where the positions are and the column says which of its columns holds them (R100 2.2)

### `analysis.spike_events`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `unit_id` | int32 | **required** | — |  | Unit ID. |
| `t_tick` | int64 | **required** | — |  | Spike tick on clock_id, mapped through core.clock_anchors. |
| `clock_id` | int32 | **required** | — |  | The clock these ticks are on, normally the session's reference. |
| `time_bucket_tick` | int64 | **required** | — | R30 §3.1 | First tick of the bucket this spike falls in, on clock_id. |

**Primary key** — `session_id`, `unit_id`, `t_tick`  

**References**

- `unit_id` → `core.units` (`unit_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `analysis.spike_events.bucket_contains_spike` — error: a spike precedes the start of the bucket it is labelled with
- `analysis.spike_events.buckets_partition_time` — error: buckets overlap in tick range, so the layout they declare is not a partition

## `core`

### `core.array_assets`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `array_asset_id` | int32 | **required** | — |  | Stable array asset ID. |
| `array_asset_name` | string | **required** | free | R95 §3.1 | What `array_asset_id` stands for: the identifier a source or an earlier packet used for this array asset. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `semantic_type` | string | nullable | open | R107 §3.1 | What quantity the asset holds, where the row's declared facts do not already say. Null is the ordinary case: a writer MUST NOT fill it where the device, the unit, the channel map or the dimensions carry the answer. An unrecognised value is a label carrying no contract (Part 01 §3.17). |
| `band` | string | nullable | open; reserving `wideband`, `ap`, `lfp` | R107 §3.1 | Which band of a sampled signal this array holds: `wideband` unfiltered, `ap` the action-potential band, `lfp` the local field potential band, with Part 02 §9.3's meanings. A conventional shorthand for a filter the packet does not record. Null where the signal was not split. |
| `uri` | string | **required** | free |  | URI/path to array store. |
| `format` | string | **required** | open |  | `zarr_v3` for portable profile. |
| `clock_id` | int32 | nullable | — |  | Clock for time axis. |
| `device_id` | int32 | nullable | — | R65 §2.1 | The device that produced this array. |
| `processing_run_id` | int32 | nullable | — | R102 §3.1 | The run that produced this array. Null means it was acquired rather than computed, which is the reading R23 §2 gives a stream. |
| `sample_rate_hz` | float64 | nullable | — |  | Sample rate if regularly sampled. |
| `unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The physical unit of the array's values, as a UCUM code. |
| `conversion` | float64 | nullable | — |  | Multiply stored values by this before offset. |
| `offset` | float64 | nullable | — |  | Add after conversion. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `array_asset_id`  

**References**

- `device_id` → `core.devices` (`device_id`)
- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)

**Tier 2 rules** — 2

- `core.array_assets.one_scaling_level` — error: scaling is declared both on the array and per channel
- `core.array_assets.sample_rate_matches_axis` — error: sample_rate_hz disagrees with the time axis step

### `core.array_channels`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `array_asset_id` | int32 | **required** | — |  | Array asset ID. |
| `axis_index` | int64 | **required** | — | R3 §6.1 | Axis that channel_index indexes, in stored order. |
| `channel_index` | int64 | **required** | — |  | Channel dimension index. |
| `electrode_id` | int32 | nullable | — |  | Electrode ID. |
| `channel_label` | string | nullable | free |  | Human-readable channel label. |
| `inter_sample_shift` | float64 | nullable | — | R19 §2 | Acquisition time offset within one sample period, in sample periods. |
| `unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The physical unit of the converted value, as a UCUM code. |
| `offset` | float64 | nullable | — | R19 §2 | Add after conversion. |
| `conversion` | float64 | nullable | — | R19 §2 | Multiply stored values by this before offset. |

**Primary key** — `array_asset_id`, `channel_index`  

**References**

- `array_asset_id`, `axis_index` → `core.array_dimensions` (`array_asset_id`, `axis_index`)
- `electrode_id` → `core.electrodes` (`electrode_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 1

- `core.array_channels.scaling_pair_complete` — error: a conversion without a unit yields a number in no known quantity

### `core.array_dimensions`

*Introduced by R3 §3.1-3.3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `array_asset_id` | int32 | **required** | — | R3 §3.1-3.3 | Array asset ID. |
| `axis_index` | int64 | **required** | — | R3 §3.1-3.3 | 0-based axis position in stored order (Part 03 §6.2). |
| `dimension_name` | string | **required** | free | R3 §3.1-3.3 | Axis name. |
| `coordinate_position_column` | string | nullable | free | R20 §2 | Which column of that resource holds the 0-based position. |
| `coordinate_resource` | string | nullable | resolves required | R100 §2.1 | The table whose rows are this axis's positions, as a dotted resource ID. The column of it holding the 0-based position is `coordinate_position_column` (R20 §2.4). |
| `coordinate_array_asset_id` | int32 | nullable | — | R20 §2 | A 1-D array holding one value per position (irregular axis). |
| `coordinate_unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The physical unit of this axis's coordinate values, as a UCUM code. |
| `step_value` | float64 | nullable | — | R20 §2 | Increment per position. |
| `origin_value` | float64 | nullable | — | R20 §2 | Value at position 0 (regular numeric axis). |
| `step_tick_num` | int64 | nullable | — | R20 §2 | Ticks advanced per position (numerator). |
| `step_tick_den` | int64 | nullable | — | R33 §2 | Denominator of the step, in ticks. Absent means 1. |
| `origin_tick` | int64 | nullable | — | R20 §2 | Tick at position 0. |
| `clock_id` | int32 | nullable | — | R20 §2 | Clock the ticks are counted on (regular tick axis). |

**Primary key** — `array_asset_id`, `axis_index`  

**References**

- `array_asset_id` → `core.array_assets` (`array_asset_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `coordinate_array_asset_id` → `core.array_assets` (`array_asset_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 8

- `core.array_dimensions.axis_index_contiguous` — error: axis_index is not contiguous from 0
- `core.array_dimensions.one_coordinate_form` — error: an axis declares more than one coordinate form
- `core.array_dimensions.tick_axis_complete` — error: a regular tick axis needs clock_id, origin_tick and step_tick_num
- `core.array_dimensions.numeric_axis_complete` — error: a regular numeric axis needs origin_value, step_value and coordinate_unit
- `core.array_dimensions.labelled_axis_complete` — error: coordinate_resource and coordinate_position_column must be present together
- `core.array_dimensions.coordinate_resource_is_core` — error: a core axis points outward at a non-core resource (R20 §5.1)
- `core.array_dimensions.step_denominator_positive` — error: a step denominator is not positive, so the step it defines is meaningless
- `core.array_dimensions.coordinate_pair_complete` — error: an axis declares one half of its labelled coordinates; the resource says where the positions are and the column says which of its columns holds them (R100 2.2)

### `core.calibration_devices`

*Introduced by R89 §2.2 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R89 §2.2 | Session ID. |
| `calibration_id` | int32 | **required** | — | R89 §2.2 | The calibration this row names a device for. |
| `device_id` | int32 | **required** | — | R89 §2.2 | A device the calibration covers. |

**Primary key** — `calibration_id`, `device_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `calibration_id` → `core.calibrations` (`calibration_id`)
- `device_id` → `core.devices` (`device_id`)

### `core.calibration_points`

*Introduced by R89 §2.3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R89 §2.3 | Session ID. |
| `calibration_id` | int32 | **required** | — | R89 §2.3 | The calibration this point belongs to. |
| `point_index` | int64 | **required** | — | R89 §2.3 | 0-based position in the curve's own order. The key is not `input_value` even though the inputs are distinct: an equality join on a float64 is not safe, which is why R47 could strike `interval_index` and this stays. |
| `input_value` | float64 | **required** | — | R89 §2.3 | The setting the point was measured at. |
| `output_value` | float64 | **required** | — | R89 §2.3 | What the instrument then delivered. |

**Primary key** — `calibration_id`, `point_index`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `calibration_id` → `core.calibrations` (`calibration_id`)

### `core.calibrations`

*Introduced by R89 §2.1 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R89 §2.1 | Session ID. |
| `calibration_id` | int32 | **required** | — | R89 §2.1 | Stable calibration ID. |
| `calibration_name` | string | **required** | free | R89 §2.1 | What `calibration_id` stands for: the identifier a source or an earlier packet used for this calibration. Required, and composed by the writer where the source names none, since Part 02 §8.2 makes two calibrations sharing a name one row. |
| `calibration_type` | string | **required** | open | R107 §3.1 | What was calibrated: `water_volume`, `light_power`, `manipulator_transform`. Named `_type` rather than `_kind` because a `_kind` column is a discriminator (Part 02 §8.3), and this holds a value that resolves to no table. |
| `calibrated_at` | timestamp | nullable | — | R89 §2.1 | When the calibration was measured, which is not when it was in force: R89 §1.2 measures 133 and 302 days between them. Null where the source states none, since what a source did not say is not invented (Part 01 §3.5). |
| `description` | string | nullable | free | R89 §2.1 | What the source said the calibration was. |
| `input_unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The unit of `core.calibration_points.input_value`, as a UCUM code. On the calibration because it varies per calibration -- `s` for water, `V` for opto -- so no literal unit can sit on the value column (R89 §2.3). |
| `output_unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The unit of `core.calibration_points.output_value`, as a UCUM code. |
| `array_asset_id` | int32 | nullable | — | R89 §2.1 | The array holding this calibration where its content is one rather than a curve: a manipulator transform, a camera's intrinsics (R89 §2.4). |
| `detail_kind` | string | nullable | resolves optional | R107 §3.1 | A table carrying a calibration shape core does not define, as a dotted resource ID. A kind the packet cannot resolve records that the content is elsewhere rather than that the row is wrong (Part 02 §12.3). |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `calibration_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `array_asset_id` → `core.array_assets` (`array_asset_id`)

**Tier 2 rules** — 2

- `core.calibrations.unit_pair_complete` — error: a calibration declares one unit of measure and not the other; the pair is what makes a point readable (R89 §2.3)
- `core.calibrations.points_declare_units` — error: a calibration carries points and declares no units, so nothing says what its values are measured in (R89 §2.3)

### `core.clock_anchors`

*Introduced by R13 §3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `clock_id` | int32 | **required** | — | R13 §3 | The clock being aligned. |
| `anchor_index` | int64 | **required** | — | R13 §3 | 0-based position in this clock's anchor sequence. |
| `t_tick` | int64 | **required** | — | R13 §3 | Tick on clock_id. |
| `parent_tick` | int64 | **required** | — | R13 §3 | The corresponding tick on parent_clock_id. |

**Primary key** — `clock_id`, `anchor_index`  

**References**

- `clock_id` → `core.clocks` (`clock_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 4

- `core.clock_anchors.requires_parent` — error: anchors are declared for a clock with no parent
- `core.clock_anchors.anchor_index_contiguous` — error: anchor_index is not contiguous from 0
- `core.clock_anchors.monotonic` — error: anchor sequences do not increase together, so interpolation is undefined
- `core.clock_anchors.gap_within_bound` — warning: an anchor gap exceeds twice the median, leaving ticks the mapping does not define (R27 5.3)

### `core.clock_observation_intervals`

*Introduced by R38 §2.1 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R38 §2.1 | Session ID. |
| `clock_id` | int32 | **required** | — | R38 §2.1 | The clock that was observing. |
| `start_tick` | int64 | **required** | — | R38 §2.1 | First tick observed, on `clock_id` itself. |
| `stop_tick` | int64 | **required** | — | R38 §2.1 | Last tick observed, on `clock_id` itself. |

**Primary key** — `session_id`, `clock_id`, `start_tick`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 2

- `core.clock_observation_intervals.interval_valid` — error: stop_tick precedes start_tick
- `core.clock_observation_intervals.non_overlapping` — error: observation windows overlap, which would double-count observed time

### `core.clock_phase_steps`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R99 §3.3 | Session. |
| `clock_id` | int32 | **required** | — | R99 §3.3 | The clock whose alignment stepped. |
| `t_tick` | int64 | **required** | — | R99 §3.3 | Where the step is, on `clock_id`. |
| `parent_tick` | int64 | **required** | — | R99 §3.3 | The same instant on the parent clock. |
| `shift_seconds` | float64 | **required** | — | R99 §3.3 | How far the parent's phase moved. Signed. |
| `anchor_interval_span` | int32 | **required** | — | R99 §3.3 | How many consecutive anchor intervals the step spans. |

**Primary key** — `session_id`, `clock_id`, `t_tick`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 1

- `core.clock_phase_steps.step_needs_parent` — error: a phase step is recorded on a clock with no parent, and a step is a movement of the parent's phase (R99 3.3)

### `core.clocks`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `clock_id` | int32 | **required** | — |  | Stable clock ID. |
| `clock_name` | string | **required** | free | R95 §3.1 | What `clock_id` stands for: the identifier a source or an earlier packet used for this clock. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `tick_rate_hz` | float64 | nullable | — |  | Tick rate as float, required unless exact tick rate provided. |
| `tick_rate_num` | int64 | nullable | — |  | Exact rational numerator. |
| `tick_rate_den` | int64 | nullable | — |  | Exact rational denominator. |
| `origin` | string | **required** | open | R107 §3.1 | Where this clock's tick 0 is, in the source's own terms -- for a sample clock, tick 0 is sample 0, and a writer MUST NOT re-base a source's index (Part 01 §2.2). |
| `tick_zero_utc` | timestamp | nullable | — | R6 §2 | Wall-clock instant of tick 0 on this clock. |
| `parent_clock_id` | int32 | nullable | — |  | Parent/reference clock. |
| `transform_slope` | float64 | nullable | — | R3 §3.4 | Parent ticks per this clock's tick, as measured. |
| `transform_offset` | float64 | nullable | — | R3 §3.4 | Parent-clock tick at this clock's tick 0. |
| `transform_to_parent` | json_string | optional | — |  | Clock alignment transform. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |
| `withheld_first_anchor` | bool | nullable | — | R99 §3.2 | Whether Part 02 §12.6's terminal-anchor test withheld this clock's first anchor. Null means the test did not run. |
| `withheld_last_anchor` | bool | nullable | — | R99 §3.2 | Whether Part 02 §12.6's terminal-anchor test withheld this clock's last anchor. Null means the test did not run. |

**Primary key** — `clock_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `parent_clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 11

- `core.clocks.tick_rate_declared` — error: neither tick_rate_hz nor an exact rational rate is present
- `core.clocks.tick_rate_one_form` — error: a clock declares both a float rate and a rational one (R95 §3.2)
- `core.clocks.tick_rate_positive` — error: tick rate is not positive
- `core.clocks.transform_pair_complete` — error: transform_slope and transform_offset must be present together
- `core.clocks.transform_requires_parent` — error: a clock transform is declared without a parent clock
- `core.clocks.tick_zero_plausible` — warning: tick_zero_utc is more than a day from session_start_time
- `core.clocks.one_alignment_model` — error: a clock declares both a linear transform and anchor points
- `core.clocks.parent_chain_well_founded` — error: a clock is its own ancestor, so walking the chain does not terminate (R27 3)
- `core.clocks.alignment_declared_for_conversion` — error: a non-reference clock declares no alignment, so it cannot be converted (R27 4)
- `core.clocks.observation_declared` — error: a clock that is anchored or is the session's reference declares no observation interval, so nothing on it has a window to inherit (R98 3.1)
- `core.clocks.withheld_needs_anchors` — error: a clock with no anchors records the outcome of a terminal-anchor test that cannot have run on it (R99 3.2)

### `core.coordinate_frame_axes`

*Introduced by R105 §3.2 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R105 §3.2 | Session. |
| `coordinate_frame` | string | **required** | open | R105 §3.2 | The frame these axes belong to. |
| `axis_index` | int64 | **required** | — | R105 §3.2 | Which axis, 0-based (Part 02 §8.1.1). |
| `axis_name` | string | **required** | open | R105 §3.2 | Whatever the source called the field these values came from, verbatim (Part 02 §9.3). A writer MUST NOT normalise it or replace it with what the quantity is conventionally taken to be. |
| `axis_direction` | string | nullable | open | R105 §3.2 | Which way the values increase -- `right`, `anterior`, `superior`. Null where the source does not state it, which no inference may fill (R105 §3.4). |
| `unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R101 §3.6 | The axis's unit, as a UCUM code (Part 02 §8.4). |

**Primary key** — `session_id`, `coordinate_frame`, `axis_index`  

**References**

- `session_id`, `coordinate_frame` → `core.coordinate_frames` (`session_id`, `coordinate_frame`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 1

- `core.coordinate_frame_axes.axis_names_distinct` — error: two axes of one frame name the same field, so which axis a coordinate value sits on cannot be told (R105 3.2)

### `core.coordinate_frames`

*Introduced by R105 §3.1 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R105 §3.1 | Session. |
| `coordinate_frame` | string | **required** | open | R105 §3.1 | The session's own name for this space. |
| `atlas` | string | nullable | open | R105 §3.1 | The published atlas this space is, where it is one. Null where no source names it; a writer MUST NOT read one out of the frame's name. |
| `atlas_version` | string | nullable | open | R105 §3.1 | That atlas's version, spelled as the atlas spells it -- `CCFv3`. Two packets naming one atlas at different versions are in different spaces. |
| `description` | string | nullable | free | R105 §3.1 | What the frame is, for a reader without the atlas. |

**Primary key** — `session_id`, `coordinate_frame`  

**References**

- `session_id` → `core.sessions` (`session_id`)

### `core.curation_versions`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `curation_id` | int32 | **required** | — |  | Stable curation ID. |
| `curation_name` | string | nullable | free | R53 §2.3.1 | What `curation_id` stands for: the identifier a source or an earlier packet used for this curation. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `sorting_run_id` | int32 | **required** | — |  | Sorting run ID. |
| `curator` | string | nullable | free |  | Curator. |
| `curation_tool` | string | nullable | free |  | Tool. |
| `curation_tool_version` | string | nullable | free |  | Tool version. |
| `processing_run_id` | int32 | nullable | — | R41 §2.1 | The run that produced this record, where provenance is recorded. |
| `parent_curation_id` | int32 | nullable | — |  | Parent curation. |
| `created_at` | timestamp | nullable | — |  | Creation time. |
| `notes` | string | nullable | free |  | Notes. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `curation_id`  

**References**

- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)
- `sorting_run_id` → `core.sorting_runs` (`sorting_run_id`)
- `parent_curation_id` → `core.curation_versions` (`curation_id`)

### `core.devices`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session if device record is session-scoped. |
| `device_id` | int32 | **required** | — |  | Stable device ID. |
| `device_name` | string | **required** | free | R95 §3.1 | What `device_id` stands for: the identifier a source or an earlier packet used for this device. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `manufacturer` | string | nullable | open | R107 §3.1 | The manufacturer's own name for itself, as the source states it, compared exactly, so two spellings are two manufacturers. |
| `model` | string | nullable | free |  | Model. |
| `firmware_version` | string | nullable | free | R66 §2.1 | The firmware the instrument was running, verbatim as its source stated it. |
| `hardware_version` | string | nullable | free | R66 §2.1 | The instrument's hardware revision, verbatim as its source stated it. |
| `serial_number` | string | nullable | free |  | Serial number. |
| `parent_device_id` | int32 | nullable | — | R67 §2.1 | The device this one was attached to -- a probe's headstage, a headstage's connect board. Null at the root of a chain, or where no source states it. |
| `parent_port` | string | nullable | open | R85 §2.1 | Which port, dock or slot of `parent_device_id` this device attached to. Null where the attachment is stated and its coordinate is not. Establishes nothing about identity: two rows may share a parent and a port (Part 01 §3.5). |
| `device_kind` | string | nullable | resolves optional | R104 §3.1 | The table carrying this device's kind-specific facts, as a dotted resource ID. Its primary key begins `device_id`, so resolution is Part 02 §8.3's shared-key join. Core declares no such table (Part 02 §8.3); an extension does, and a value naming a resource the packet does not carry is a fact rather than a defect (Part 02 §8.3). |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `device_id`  

**References**

- `parent_device_id` → `core.devices` (`device_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.devices.parent_chain_well_founded` — error: a device is its own ancestor, or its attachment chain does not terminate (R67 §2.3)
- `core.devices.serial_identifies_one_device` — error: one serial number appears on more than one device row; a device is the physical object (R67 §2.2)

### `core.electrode_coordinate_values`

*Introduced by R105 §3.3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R105 §3.3 | Session. |
| `electrode_id` | int32 | **required** | — | R105 §3.3 | The thing positioned. |
| `coordinate_frame` | string | **required** | open | R105 §3.3 | The frame, naming a `core.coordinate_frames` row of this session; with `coordinate_basis` it completes the parent's key. |
| `coordinate_basis` | string | **required** | open | R105 §3.3 | What the coordinate asserts (Part 01 §3.8). |
| `axis_index` | int64 | **required** | — | R105 §3.3 | Which of the frame's axes this value is on. |
| `axis_value` | float64 | **required** | — | R105 §3.3 | The value, in the axis's unit. |

**Primary key** — `electrode_id`, `coordinate_frame`, `coordinate_basis`, `axis_index`  

**References**

- `electrode_id`, `coordinate_frame`, `coordinate_basis` → `core.electrode_coordinates` (`electrode_id`, `coordinate_frame`, `coordinate_basis`)
- `session_id`, `coordinate_frame`, `axis_index` → `core.coordinate_frame_axes` (`session_id`, `coordinate_frame`, `axis_index`)
- `session_id` → `core.sessions` (`session_id`)

### `core.electrode_coordinates`

*Introduced by R19 §3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `electrode_id` | int32 | **required** | — | R19 §3 | Electrode ID. |
| `coordinate_frame` | string | **required** | open | R107 §3.1 | The space these coordinates are in, naming a `core.coordinate_frames` row of this session, which declares that space's axes and the published atlas it is. |
| `coordinate_basis` | string | **required** | open | R58 §2.1 | What the coordinate asserts: `planned` where the probe was meant to go, `measured` where it was, `nominal` where it is by construction and nothing aimed or observed it (Part 01 §3.8). A consumer that does not recognise a basis MUST NOT treat it as measured (Part 01 §3.8). |
| `region_id` | int32 | nullable | — | R59 §2.1 | The atlas structure this position falls in, numbered by the atlas that `coordinate_frame` names. |
| `region_label` | string | nullable | open | R59 §2.1 | That structure's short name, so a consumer without the atlas can read the annotation. |
| `processing_run_id` | int32 | nullable | — | R58 §2.3 | The run that produced this coordinate. |

**Primary key** — `electrode_id`, `coordinate_frame`, `coordinate_basis`  

**References**

- `electrode_id` → `core.electrodes` (`electrode_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)
- `session_id`, `coordinate_frame` → `core.coordinate_frames` (`session_id`, `coordinate_frame`)

### `core.electrodes`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `electrode_id` | int32 | **required** | — |  | Stable electrode ID. |
| `electrode_name` | string | nullable | free | R53 §2.3.1 | What `electrode_id` stands for: the identifier a source or an earlier packet used for this electrode. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `probe_id` | int32 | nullable | — |  | Probe ID. |
| `local_electrode_label` | string | nullable | free | R8 §2 | Opaque source label; undefined base, not an offset. |
| `local_channel_label` | string | nullable | free | R8 §2 | Opaque source label; undefined base, not an offset. |
| `impedance_ohm` | float64 | nullable | — |  | Impedance. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `electrode_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `probe_id` → `core.probes` (`probe_id`)

### `core.event_stream_observation_intervals`

*Introduced by R25 §2 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `event_stream_id` | int32 | **required** | — | R25 §2 | The stream being observed. |
| `start_tick` | int64 | **required** | — | R25 §2 | First observed tick, on the stream's clock. |
| `stop_tick` | int64 | **required** | — | R25 §2 | Last observed tick, on the stream's clock. |

**Primary key** — `event_stream_id`, `start_tick`  

**References**

- `event_stream_id` → `core.event_streams` (`event_stream_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.event_stream_observation_intervals.interval_valid` — error: stop_tick precedes start_tick
- `core.event_stream_observation_intervals.non_overlapping` — error: observation windows overlap, which would double-count observed time

### `core.event_streams`

*Introduced by R23 §2-3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R23 §2-3 | Session ID. |
| `event_stream_id` | int32 | **required** | — | R23 §2-3 | Stable ID. |
| `event_stream_name` | string | **required** | free | R95 §3.1 | What `event_stream_id` stands for: the identifier a source or an earlier packet used for this event stream. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `event_type` | string | **required** | open | R107 §3.1 | What kind of event this stream emits. A stream emits one kind, so a source emitting several on one channel is written as several streams. |
| `detail_kind` | string | nullable | resolves optional | R107 §3.1 | A table specialising this stream's events, as a dotted resource ID. A kind the packet cannot resolve records that the detail is elsewhere (Part 02 §8.3). Resolved against `core.events`' key by Part 02 §8.3's shared key, through the reference `discriminates_via` names. |
| `device_id` | int32 | nullable | — | R23 §2-3 | The device that produced it, where one is identified. |
| `clock_id` | int32 | **required** | — | R23 §2-3 | The clock its events are timed on. |
| `processing_run_id` | int32 | nullable | — | R23 §2-3 | The run that produced it. Null means it came off the device as recorded. A narrow exception to R9 §4: the manifest records outputs per resource and cannot distinguish streams within one table. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `event_stream_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `device_id` → `core.devices` (`device_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)

**Tier 2 rules** — 1

- `core.event_streams.observation_declared` — info *(advisory, R26)*: streams carry no observation intervals and their clock declares none, so no rate over them has a denominator

### `core.events`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `stream_id` | int32 | **required** | — | R23 §2-3 | The stream this event belongs to. |
| `t_tick` | int64 | **required** | — |  | Event tick. |
| `payload` | json_string | optional | — |  | Event payload. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `session_id`, `stream_id`, `t_tick`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `stream_id` → `core.event_streams` (`event_stream_id`)

**Tier 2 rules** — 1

- `core.events.within_observation` — warning: events fall outside the observation window in force for their stream

### `core.intervals`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `interval_kind` | string | **required** | resolves required | R107 §3.1 | The resource that specialises this interval, as a dotted resource ID, resolved as Part 02 §8.3's shared key. |
| `interval_id` | int32 | **required** | — | R54 §2.1 | Stable trial ID. |
| `start_tick` | int64 | **required** | — | R45 §2.4 | First tick of the trial, inclusive, on `clock_id`. |
| `stop_tick` | int64 | **required** | — | R45 §2.4 | Last tick of the trial, inclusive, on `clock_id`. |
| `clock_id` | int32 | **required** | — |  | Clock for start/stop ticks. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `session_id`, `interval_kind`, `interval_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 1

- `core.intervals.interval_valid` — error: stop_tick precedes start_tick

### `core.media_assets`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `media_asset_id` | int32 | **required** | — |  | Stable media asset ID. |
| `media_asset_name` | string | **required** | free | R95 §3.1 | What `media_asset_id` stands for: the identifier a source or an earlier packet used for this media asset. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `semantic_type` | string | nullable | open | R107 §3.1 | What quantity the asset holds, where the row's declared facts do not already say. Null is the ordinary case: a writer MUST NOT fill it where the device, the unit, the channel map or the dimensions carry the answer. An unrecognised value is a label carrying no contract (Part 01 §3.17). |
| `uri` | string | **required** | free |  | Media file URI. |
| `format` | string | **required** | open | R107 §3.1 | The container format, as the file extension names it: `mp4`, `avi`. |
| `device_id` | int32 | nullable | — | R102 §3.2 | The device that recorded this asset. A writer names it where its source states one, and MUST NOT infer it from a file name (Part 01 §3.5). |
| `pts_rate_num` | int64 | nullable | — | R70 §2.1 | Presentation timestamps per second in this asset's container: numerator. |
| `pts_rate_den` | int64 | nullable | — | R70 §2.1 | Presentation timestamps per second in this asset's container: denominator. |
| `clock_id` | int32 | nullable | — |  | Clock for frame timing. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `media_asset_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `clock_id` → `core.clocks` (`clock_id`)
- `device_id` → `core.devices` (`device_id`)

**Tier 2 rules** — 3

- `core.media_assets.pts_rate_pair_complete` — error: an asset declares one half of its presentation-timestamp rate; half a rational is unusable (R70 §2.2)
- `core.media_assets.pts_rate_declared_where_frames_carry_pts` — error: frames carry pts for an asset that does not say what those timestamps count (R70 §2.2)
- `core.media_assets.pts_rate_positive` — error: a presentation-timestamp rate is not positive

### `core.media_frames`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `media_asset_id` | int32 | **required** | — |  | Media asset ID. |
| `frame_index` | int64 | **required** | — |  | Frame index. |
| `t_tick` | int64 | **required** | — |  | Frame time tick. |
| `clock_id` | int32 | **required** | — |  | Clock ID. |
| `pts` | int64 | nullable | — | R68 §2.1 | Container presentation timestamp, verbatim in the container's own time base. |
| `dropped` | bool | nullable | — |  | Dropped-frame flag. |

**Primary key** — `media_asset_id`, `frame_index`  

**References**

- `clock_id` → `core.clocks` (`clock_id`)
- `media_asset_id` → `core.media_assets` (`media_asset_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.media_frames.frame_index_contiguous` — error: frame_index is not contiguous from 0 within an asset
- `core.media_frames.pts_increases_with_frame_index` — error: pts is not strictly increasing in frame_index order within an asset, so the frames are not numbered in presentation order (R69 §2.1)

### `core.preferred_runs`

*Introduced by R41 §2.3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R41 §2.3 | Session ID. |
| `activity_type` | string | **required** | open | R107 §3.1 | Which kind of output this preference is about, in the vocabulary `core.processing_runs.activity_type` uses (Part 02 §9.3). |
| `scope_kind` | string | **required** | resolves optional | R107 §3.1 | The resource whose primary key `scope` holds, as a dotted resource ID (R49 §2.2). |
| `scope` | string | **required** | free | R41 §2.3 | What it applies to -- a probe_id, an array_asset_id, a camera -- or the session_id itself where the preference is session-wide. |
| `processing_run_id` | int32 | **required** | — | R41 §2.3 | The preferred run. |
| `chosen_at` | timestamp | nullable | — | R41 §2.3 | When the choice was made. |
| `reason` | string | nullable | free | R41 §2.3 | Why, in one line. |

**Primary key** — `session_id`, `activity_type`, `scope_kind`, `scope`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)

**Tier 2 rules** — 3

- `core.preferred_runs.activity_matches_run` — error: a preference names a run whose activity_type differs from the preference's
- `core.preferred_runs.run_in_session` — error: a preference names a run belonging to another session
- `core.preferred_runs.not_superseded` — warning: the preferred run is superseded by another run

### `core.probes`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `probe_id` | int32 | **required** | — |  | Stable probe ID. |
| `probe_name` | string | nullable | free | R95 §3.1 | What `probe_id` stands for: the identifier a source or an earlier packet used for this probe. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `device_id` | int32 | nullable | — |  | Associated device. |
| `probe_type` | string | nullable | open | R107 §3.1 | The probe's model, as the manufacturer names it: `Neuropixels 1.0`. |
| `manufacturer` | string | nullable | open | R107 §3.1 | The manufacturer's own name for itself, as the source states it, compared exactly, so two spellings are two manufacturers. |
| `serial_number` | string | nullable | free |  | Serial number. |
| `insertion_name` | string | nullable | free |  | Insertion label. |
| `target_region` | string | nullable | open | R107 §3.1 | The structure the probe was aimed at, as an atlas acronym where the source gives one. Not resolvable: no column here names the atlas, which only a coordinate frame does (Part 01 §3.24). |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `probe_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `device_id` → `core.devices` (`device_id`)

### `core.processing_run_inputs`

*Introduced by R9 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID. |
| `processing_run_id` | int32 | **required** | — | R9 | The run. |
| `source_file_id` | int32 | **required** | — | R9 | A source file the run consumed. |

**Primary key** — `processing_run_id`, `source_file_id`  

**References**

- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `source_file_id` → `core.source_files` (`source_file_id`)
- `session_id` → `core.sessions` (`session_id`)

### `core.processing_runs`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R88 §2.1 | Session ID if session-scoped. |
| `processing_run_id` | int32 | **required** | — |  | Stable processing run ID. |
| `processing_run_name` | string | nullable | free | R53 §2.3.1 | What `processing_run_id` stands for: the identifier a source or an earlier packet used for this processing run. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `activity_type` | string | **required** | open | R107 §3.1 | What kind of work the run did: `import`, `validation`, `sorting`, `curation`, `materialization`. A pipeline names its own. |
| `scope` | string | nullable | free | R107 §3.1 | What this run is about -- a probe_id, an array_asset_id, a camera -- or the session_id itself where the run is session-wide. Read only with the `scope_kind` beside it, which names the table the value keys into (R49 §2.2). |
| `scope_kind` | string | nullable | resolves optional | R107 §3.1 | The resource whose primary key `scope` holds, as a dotted resource ID -- `core.probes`, `core.array_assets`. A value naming no declared resource means the scope is not a packet resource. Set with `scope` or not at all. |
| `supersedes_run_id` | int32 | nullable | — | R50 §2 | The run this one replaces, if any. |
| `software_name` | string | nullable | free |  | Software name. |
| `software_version` | string | nullable | free |  | Software version. |
| `code_uri` | string | nullable | free |  | Code reference. |
| `parameters` | json_string | optional | — |  | Parameters. |
| `started_at` | timestamp | nullable | — |  | Start time. |
| `ended_at` | timestamp | nullable | — |  | End time. |
| `status` | string | **required** | closed: `succeeded`, `failed`, `partial` | R107 §3.1 | Whether the run completed, with the meanings Part 02 §9.3 declares. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `processing_run_id`  

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

*Introduced by R3 §3.1-3.3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R3 §3.1-3.3 | Session ID. |
| `experimenter` | string | **required** | free | R3 §3.1-3.3 | One experimenter. |

**Primary key** — `session_id`, `experimenter`  

**References**

- `session_id` → `core.sessions` (`session_id`)

### `core.sessions`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Stable session ID. |
| `session_name` | string | nullable | free | R53 §2.3.1 | What `session_id` stands for: the identifier a source or an earlier packet used for this session. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `subject_id` | int32 | **required** | — |  | Subject ID. |
| `session_start_time` | timestamp | **required** | — |  | Session start time if known; if unknown use explicit null only in non-strict test packets. |
| `session_end_time` | timestamp | nullable | — | R25 §2 | When the session ended, UTC. Metadata, not derived from the tables (R25 5). |
| `reference_clock_id` | int32 | nullable | — | R27 §2 | The clock this session's times are reported on by default (R27 2). |
| `session_description` | string | nullable | free |  | Human-readable session description. |
| `institution` | string | nullable | free |  | Institution/lab. |
| `task_name` | string | nullable | free |  | Task/protocol name. |
| `source_session_id` | int32 | nullable | — |  | Source-system session ID if different. |
| `t_zero_tick` | int64 | nullable | — | R39 §2.2 | Earliest observed tick, on `reference_clock_id`; the origin seconds count from. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |
| `alignment_bound` | float64 | nullable | — | R99 §3.1 | How far past its anchors the writer mapped, in median anchor intervals (Part 01 §3.9). Null means the default of one. |

**Primary key** — `session_id`  

**References**

- `subject_id` → `core.subjects` (`subject_id`)
- `reference_clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 5

- `core.sessions.manifest_sessions_match` — error: the manifest's session inventory and core.sessions disagree; the manifest names a session by its session_name, since an assigned session_id means nothing outside the packet that assigned it (R53 §2.3.1)
- `core.sessions.session_interval_valid` — error: session_end_time precedes session_start_time
- `core.sessions.reference_clock_declared` — error: a session declaring more than one clock names no reference clock (R27 2)
- `core.sessions.every_clock_reaches_the_reference` — error: a clock does not reach the session's reference clock, so it cannot be converted to it
- `core.sessions.alignment_bound_at_least_default` — error: a session declares an alignment bound below R27 5.3's default of one median anchor interval, which reaches no further than declaring nothing (R99 3.1)

### `core.sorting_run_channels`

*Introduced by R83 §2.1 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R83 §2.1 | Session ID. |
| `sorting_run_id` | int32 | **required** | — | R83 §2.1 | The run whose channel list this row belongs to. |
| `channel_index` | int64 | **required** | — | R83 §2.1 | 0-based position in the run's own channel order, which is what a source's channel index counts (R83 §1.1). int64 as every structural index is. |
| `electrode_id` | int32 | **required** | — | R83 §2.1 | The contact at that position. |

**Primary key** — `session_id`, `sorting_run_id`, `channel_index`  

**References**

- `sorting_run_id` → `core.sorting_runs` (`sorting_run_id`)
- `electrode_id` → `core.electrodes` (`electrode_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.sorting_run_channels.contact_listed_once` — error: a contact appears more than once in one run's channel list
- `core.sorting_run_channels.index_contiguous` — error: channel_index is not contiguous from 0 within a run

### `core.sorting_runs`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `sorting_run_id` | int32 | **required** | — |  | Stable sorting run ID. |
| `sorting_run_name` | string | nullable | free | R53 §2.3.1 | What `sorting_run_id` stands for: the identifier a source or an earlier packet used for this sorting run. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `probe_id` | int32 | nullable | — |  | Probe ID. |
| `sorter_name` | string | nullable | free |  | Sorter name. |
| `sorter_version` | string | nullable | free |  | Sorter version. |
| `processing_run_id` | int32 | nullable | — | R41 §2.1 | The run that produced this record, where provenance is recorded. |
| `parameters` | json_string | optional | — |  | Sorter parameters. |
| `input_array_asset_id` | int32 | nullable | — |  | Input array asset. |
| `started_at` | timestamp | nullable | — |  | Start time. |
| `ended_at` | timestamp | nullable | — |  | End time. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `sorting_run_id`  

**References**

- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)
- `probe_id` → `core.probes` (`probe_id`)
- `input_array_asset_id` → `core.array_assets` (`array_asset_id`)

### `core.source_files`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `source_file_id` | int32 | **required** | — |  | Stable source file ID. |
| `source_file_name` | string | nullable | free | R53 §2.3.1 | What `source_file_id` stands for: the identifier a source or an earlier packet used for this source file. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `uri` | string | **required** | free |  | Source URI/path. |
| `format` | string | nullable | open | R107 §3.1 | The file's format in the producer's own terms, which this specification does not constrain. |
| `sha256` | string | nullable | free |  | Checksum. |
| `size_bytes` | int64 | nullable | — |  | Size. |
| `modified_at` | timestamp | nullable | — |  | Modification time if known. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `source_file_id`  

### `core.spike_events`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `unit_id` | int32 | **required** | — |  | Unit ID. |
| `t_tick` | int64 | **required** | — | R96 §3.3 | Spike tick. |
| `amplitude` | float32 | nullable | — | R96 §3.3 | Spike amplitude if available. |

**Primary key** — `session_id`, `unit_id`, `t_tick`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `unit_id` → `core.units` (`unit_id`)

**Tier 2 rules** — 2

- `core.spike_events.ticks_within_clock_span` — warning: negative ticks on a clock with no absolute reference
- `core.spike_events.within_observation` — warning: spikes fall outside the observation window in force for their unit

### `core.subjects`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `subject_id` | int32 | **required** | — |  | Stable subject ID. |
| `subject_name` | string | nullable | free | R53 §2.3.1 | What `subject_id` stands for: the identifier a source or an earlier packet used for this subject. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `species` | string | nullable | open; [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy) | R101 §3.6 | The scientific name of the organism the subject derives from, as NCBI Taxonomy spells it: `Mus musculus`, never `mouse`. Null where the subject derives from no organism -- Part 01 §3.4 admits a preparation, and a phantom or a simulation has no species. |
| `strain` | string | nullable | open; [MGI](https://www.informatics.jax.org/), [RGD](https://rgd.mcw.edu/) | R101 §3.6 | The strain in its registry's nomenclature: MGI for mouse, where `C57BL/6J`'s substrain letter is what distinguishes it from the Nnt-deleted `C57BL/6N`, and RGD for rat stocks such as `Long-Evans`. |
| `sex` | string | nullable | closed: `male`, `female`, `hermaphrodite`, `other`; [HL7 FHIR administrative gender](https://hl7.org/fhir/valueset-administrative-gender.html) | R101 §3.6 | The subject's sex. Null where the source states none, states it unknown, or describes a preparation that has none. |
| `date_of_birth` | date | nullable | — |  | Date of birth if known. |
| `genotype` | string | nullable | open | R101 §3.5 | The genotype as the source states it, in MGI allele nomenclature where it uses one. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `subject_id`  

### `core.unit_coordinate_values`

*Introduced by R105 §3.3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R105 §3.3 | Session. |
| `unit_id` | int32 | **required** | — | R105 §3.3 | The thing positioned. |
| `coordinate_frame` | string | **required** | open | R105 §3.3 | The frame, naming a `core.coordinate_frames` row of this session; with `coordinate_basis` it completes the parent's key. |
| `coordinate_basis` | string | **required** | open | R105 §3.3 | What the coordinate asserts (Part 01 §3.8). |
| `axis_index` | int64 | **required** | — | R105 §3.3 | Which of the frame's axes this value is on. |
| `axis_value` | float64 | **required** | — | R105 §3.3 | The value, in the axis's unit. |

**Primary key** — `session_id`, `unit_id`, `coordinate_frame`, `coordinate_basis`, `axis_index`  

**References**

- `session_id`, `unit_id`, `coordinate_frame`, `coordinate_basis` → `core.unit_coordinates` (`session_id`, `unit_id`, `coordinate_frame`, `coordinate_basis`)
- `session_id`, `coordinate_frame`, `axis_index` → `core.coordinate_frame_axes` (`session_id`, `coordinate_frame`, `axis_index`)
- `session_id` → `core.sessions` (`session_id`)

### `core.unit_coordinates`

*Introduced by R28 §2-4 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R28 §2-4 | Session ID. |
| `unit_id` | int32 | **required** | — | R28 §2-4 | Unit ID. |
| `coordinate_frame` | string | **required** | open | R107 §3.1 | The space these coordinates are in, naming a `core.coordinate_frames` row of this session, which declares that space's axes and the published atlas it is. |
| `coordinate_basis` | string | **required** | open | R58 §2.1 | What the coordinate asserts: `planned` where the probe was meant to go, `measured` where it was, `nominal` where it is by construction and nothing aimed or observed it (Part 01 §3.8). A consumer that does not recognise a basis MUST NOT treat it as measured (Part 01 §3.8). |
| `region_id` | int32 | nullable | — | R59 §2.1 | The atlas structure this position falls in, numbered by the atlas that `coordinate_frame` names. |
| `region_label` | string | nullable | open | R59 §2.1 | That structure's short name, so a consumer without the atlas can read the annotation. |
| `processing_run_id` | int32 | nullable | — | R58 §2.3 | The run that produced this coordinate. |

**Primary key** — `session_id`, `unit_id`, `coordinate_frame`, `coordinate_basis`  

**References**

- `unit_id` → `core.units` (`unit_id`)
- `processing_run_id` → `core.processing_runs` (`processing_run_id`)
- `session_id` → `core.sessions` (`session_id`)
- `session_id`, `coordinate_frame` → `core.coordinate_frames` (`session_id`, `coordinate_frame`)

### `core.unit_electrodes`

*Introduced by R28 §2-4 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R28 §2-4 | Session ID. |
| `unit_id` | int32 | **required** | — | R28 §2-4 | Unit ID. |
| `electrode_id` | int32 | **required** | — | R28 §2-4 | An electrode this unit was detected on. |
| `channel_index` | int64 | nullable | — | R50 §2 | 0-based position of this electrode in the unit's channel list, where a dense array axis is indexed by it (R20 §2). Nothing joins on it. |
| `is_primary` | bool | nullable | — | R28 §2-4 | Whether this is the unit's peak electrode. |

**Primary key** — `session_id`, `unit_id`, `electrode_id`  

**References**

- `unit_id` → `core.units` (`unit_id`)
- `electrode_id` → `core.electrodes` (`electrode_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 3

- `core.unit_electrodes.one_primary` — warning: a unit designates more than one peak electrode (R28 2)
- `core.unit_electrodes.channel_index_contiguous` — error: channel_index is not contiguous from 0, so a dense axis indexed by it addresses rows that are not there
- `core.unit_electrodes.electrode_is_a_run_channel` — error: a unit sits on an electrode its sorting run did not use

### `core.unit_observation_intervals`

*Introduced by R18 §2 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R18 §2 | Session ID. |
| `unit_id` | int32 | **required** | — | R18 §2 | Unit ID. |
| `start_tick` | int64 | **required** | — | R96 §3.4 | First tick, inclusive. |
| `stop_tick` | int64 | **required** | — | R96 §3.4 | Last tick, inclusive. |

**Primary key** — `session_id`, `unit_id`, `start_tick`  

**References**

- `unit_id` → `core.units` (`unit_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 2

- `core.unit_observation_intervals.interval_valid` — error: stop_tick precedes start_tick
- `core.unit_observation_intervals.non_overlapping` — error: observation windows overlap, which would double-count observed time

### `core.unit_quality_labels`

*Introduced by R16 §2-3 (R29 §2). A column with no revision came from Part 02 unamended.*

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — | R16 §2-3 | Session ID. |
| `unit_id` | int32 | **required** | — | R16 §2-3 | Unit ID. |
| `source` | string | **required** | open | R16 §2-3 | What produced the label, e.g. kilosort, decoder, bombcell. |
| `label` | string | **required** | open | R16 §2-3 | The source's own label, verbatim. |
| `normalized_label` | string | nullable | closed: `sua`, `mua`, `noise` | R16 §2-3 | Declared projection onto the closed set. Null where the source's label does not project. |
| `confidence` | float64 | nullable | — | R16 §2-3 | The source's confidence, where it reports one. |

**Primary key** — `session_id`, `unit_id`, `source`  

**References**

- `unit_id` → `core.units` (`unit_id`)
- `session_id` → `core.sessions` (`session_id`)

**Tier 2 rules** — 1

- `core.unit_quality_labels.projection_is_consistent` — error: a (source, label) pair projects onto more than one normalized_label

### `core.units`

| Column | Type | Presence | Declares | Since | Description |
|---|---|:---:|---|---|---|
| `session_id` | int32 | **required** | — |  | Session ID. |
| `unit_id` | int32 | **required** | — |  | Stable unit ID. |
| `unit_name` | string | nullable | free | R53 §2.3.1 | What `unit_id` stands for: the identifier a source or an earlier packet used for this unit. The only bridge between two packets that numbered it differently (Part 05 §8). |
| `probe_id` | int32 | nullable | — |  | Probe ID. |
| `sorting_run_id` | int32 | **required** | — |  | Sorting run ID. |
| `curation_id` | int32 | **required** | — |  | Curation ID. |
| `local_unit_label` | string | nullable | free | R8 §2 | Opaque source label; undefined base, not an offset. |
| `quality_label` | string | nullable | closed: `sua`, `mua`, `noise` | R11 §3-4 | Quality label. |
| `amplitude_unit` | string | nullable | open; [UCUM](https://ucum.org/ucum.html) | R107 §3.1 | Unit of measure of `core.spike_events.amplitude` for this unit's spikes -- microvolts, or ADC counts. |
| `quality_label_source` | string | nullable | open | R16 §2-3 | Which core.unit_quality_labels source the designated label came from. |
| `firing_rate_hz` | float64 | nullable | — |  | Firing rate if known. |
| `n_spikes` | int64 | nullable | — | R5 | Total spikes for this unit in this context. |
| `first_spike_tick` | int64 | nullable | — | R5 | Lowest t_tick for this unit. |
| `last_spike_tick` | int64 | nullable | — | R5 | Highest t_tick for this unit. |
| `clock_id` | int32 | **required** | — | R96 §3.2 | The clock every tick of this unit is counted on. |
| `metadata` | json_string | optional | — | R97 §3.4 | What the source stated about this row that the standard does not model, carried in the source's own vocabulary and read by no rule. |

**Primary key** — `unit_id`  

**References**

- `session_id` → `core.sessions` (`session_id`)
- `probe_id` → `core.probes` (`probe_id`)
- `sorting_run_id` → `core.sorting_runs` (`sorting_run_id`)
- `curation_id` → `core.curation_versions` (`curation_id`)
- `clock_id` → `core.clocks` (`clock_id`)

**Tier 2 rules** — 5

- `core.units.spike_summary_consistent` — error: n_spikes, first_spike_tick or last_spike_tick disagrees with core.spike_events
- `core.units.designated_label_is_recorded` — error: the designated quality label is not among the recorded ones
- `core.units.designated_label_pair_complete` — error: quality_label and quality_label_source must be present together
- `core.units.observation_declared` — info *(advisory, R26)*: units carry no observation intervals and their clock declares none, so no rate over them has a denominator
- `core.units.amplitude_unit_declared` — error: a unit's spikes carry an amplitude and the unit declares no amplitude_unit (R96 §3.5)

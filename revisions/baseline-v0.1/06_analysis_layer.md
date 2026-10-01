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

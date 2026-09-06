# R20 — Array Axis Coordinates

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | `02_core_logical_schemas.md`, `06_analysis_layer.md`, R2 §12, R3 §3.3 |
| **Depends on** | R3 §3.3 (`array_dimensions`), R3 §6.1 (`array_channels`), R13 (clock anchors) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R3 §3.3 gives each axis a name. Nothing says what a *position* along it means.

The consequence is present, not hypothetical. A raw recording of shape
`(191 631 595, 384)` declares `clock_id` and `sample_rate_hz` on `core.array_assets`, and
neither states which axis carries time nor which tick position 0 corresponds to. AIND's
recordings live under `ecephys_clipped/` and begin partway into acquisition, so position 0 is
some nonzero tick. A consumer aligning spikes to voltage assumes zero and is silently wrong —
the failure class R12 was written about: no error, plausible output, wrong answer.

`core.array_channels` already answers the question for one axis, mapping channel index to
electrode. It is a special case of a general need, and there is no general case.

## 2. Four forms

An axis declares its coordinates in exactly one of four ways.

### 2.1 Regular tick axis

| Field | Type | Description |
|---|---|---|
| `clock_id` | string | Clock the ticks are counted on. |
| `origin_tick` | int64 | Tick at position 0. |
| `step_ticks` | int64 | Ticks advanced per position. |

For time, and for event-relative axes, where a window from 500 ticks before an alignment
event uses `origin_tick = -500`.

**This is the compact form, and it is the point.** Three integers describe 191 631 595
positions. xarray materialises coordinates as arrays and would store 191M float64 values,
about 1.5 GB per stream; the AIND recordings actually do, in `times_seg0`.

They do so because after HARP alignment the times are not regular *in seconds*. On the
array's own clock they remain perfectly regular — one tick per sample — and R13's
`core.clock_anchors` carries the mapping to any other clock. Ticks plus a declared alignment
replace 1.5 GB with three numbers and a lookup, which is the tick invariant (R3 §2.1) paying
for itself.

### 2.2 Regular numeric axis

| Field | Type | Description |
|---|---|---|
| `origin_value` | float64 | Value at position 0. |
| `step_value` | float64 | Increment per position. |
| `coordinate_unit` | string | Unit of those values, e.g. `um`, `Hz`. |

For uniformly spaced axes that are not time. The drift field's depth bins are one:
143.25 µm at position 0, 286.5 µm apart.

### 2.3 Irregular numeric axis

| Field | Type | Description |
|---|---|---|
| `coordinate_array_asset_id` | string | A 1-D array asset holding one value per position. |

References `core.array_assets.array_asset_id`. For log-spaced frequency bins, unevenly
sampled depths, or any axis whose values follow no rule. Length is unconstrained, so this
also serves a large irregular axis that a table could not hold.

The referenced array's length MUST equal the axis extent, and it MUST be one-dimensional.

### 2.4 Labelled axis

| Field | Type | Description |
|---|---|---|
| `coordinate_resource` | string | Resource ID of a table whose rows are this axis's positions. |
| `coordinate_position_column` | string | Which of its columns holds the 0-based position. |

For axes whose positions are entities or categories — `trial`, `unit`, `band`, `condition`.

This is a pointer rather than a schema because the thing pointed at differs in shape. A
channel axis resolves to one column; a trial axis to two; a unit axis to four:

```text
channel  ->  electrode_id                                          1 column
trial    ->  (session_id, trial_id)                                2
unit     ->  (session_id, unit_id, sorting_run_id, curation_id)    4
```

No single generic table can carry a typed foreign key across those widths. Pointing lets each
coordinate table declare its own columns and its own reference, validated like any other
table.

`core.array_channels` is the first instance, not an exception: an array's channel axis
declares `coordinate_resource = "core.array_channels"` and
`coordinate_position_column = "channel_index"`.

A coordinate table MUST be keyed by `array_asset_id` alongside its position column, so
coordinates belong to one array rather than a dimension name globally.

## 3. Exactly one form

An axis MUST declare no more than one of the four. Two descriptions of the same positions can
disagree and nothing would say which governs — the pattern R13 §4 applies to clock alignment
and R19 §2.1 to array scaling.

```sql
-- core.array_dimensions.one_coordinate_form  (error)
SELECT array_asset_id, axis_index FROM core_array_dimensions
WHERE (CASE WHEN origin_tick IS NOT NULL THEN 1 ELSE 0 END
     + CASE WHEN origin_value IS NOT NULL THEN 1 ELSE 0 END
     + CASE WHEN coordinate_array_asset_id IS NOT NULL THEN 1 ELSE 0 END
     + CASE WHEN coordinate_resource IS NOT NULL THEN 1 ELSE 0 END) > 1
```

```sql
-- core.array_dimensions.tick_axis_complete  (error)
SELECT array_asset_id, axis_index FROM core_array_dimensions
WHERE origin_tick IS NOT NULL AND (step_ticks IS NULL OR clock_id IS NULL)
```

```sql
-- core.array_dimensions.numeric_axis_complete  (error)
SELECT array_asset_id, axis_index FROM core_array_dimensions
WHERE origin_value IS NOT NULL AND (step_value IS NULL OR coordinate_unit IS NULL)
```

```sql
-- core.array_dimensions.labelled_axis_complete  (error)
SELECT array_asset_id, axis_index FROM core_array_dimensions
WHERE (coordinate_resource IS NULL) <> (coordinate_position_column IS NULL)
```

Declaring none is permitted: an axis whose positions carry no meaning beyond their order is
common, and silence is honest.

## 4. `sample_rate_hz` becomes a validated denormalization

`core.array_assets.sample_rate_hz` is retained. Where a time axis declares a regular tick
form, the two describe the same thing and MUST agree:

```sql
-- core.array_assets.sample_rate_matches_axis  (error)
SELECT a.array_asset_id, a.sample_rate_hz
FROM core_array_assets a
JOIN core_array_dimensions d USING (array_asset_id)
JOIN core_clocks c ON c.clock_id = d.clock_id
WHERE a.sample_rate_hz IS NOT NULL AND d.step_ticks IS NOT NULL
  AND c.tick_rate_hz IS NOT NULL
  AND abs(a.sample_rate_hz - c.tick_rate_hz / d.step_ticks) > 1e-6
```

It survives R3 §3.0's duplication test on the same grounds as `core.units.n_spikes` (R5 §4):
deriving the rate otherwise requires joining through `core.clocks`, so the scalar buys
join-free filtering, and a rule keeps it honest.

## 5. Analysis arrays are described by analysis tables

An analysis array registered in `core.array_assets`, with axis rows in
`core.array_dimensions` pointing at an analysis coordinate table, would make a core table
reference a resource the analysis layer owns. `00` says analysis resources may be deleted and
recomputed; a core table pointing at one would dangle. R17 §2 forbids core referencing an
extension for the same reason.

`06` anticipated this, saying array metadata belongs in "`core.array_assets` or an
`analysis.array_assets` extension table." This revision defines the latter.

Two tables mirror their core counterparts exactly, column for column:

| Table | Mirrors |
|---|---|
| `analysis.array_assets` | `core.array_assets` |
| `analysis.array_dimensions` | `core.array_dimensions` |

R2 §12 excluded analysis schemas from the registry because "their shapes depend on
materialization parameters." These do not: they describe arrays rather than results, and
their columns are fixed. The exclusion stands for the tables it was written about —
`analysis.spikes_by_trial`, `analysis.binned_spikes` and the rest, whose columns follow from
a materialization's parameters.

### 5.1 References point inward

A layer MAY reference a layer beneath it and MUST NOT reference one above.

```text
extension  ->  analysis  ->  core        permitted
core       ->  analysis                  forbidden
core       ->  extension                 forbidden (R17 §2)
```

So `core.array_dimensions.coordinate_resource` MUST name a `core` resource;
`analysis.array_dimensions.coordinate_resource` MAY name a `core` or `analysis` one. Core
stays interpretable when analysis resources are deleted, which is what makes them disposable.

### 5.2 Where a materialization's coordinate tables are declared

A labelled axis (§2.4) points at a table, and that table needs a schema or the pointer cannot
be validated. `analysis.binned_spikes_units` is exactly the parameter-dependent shape R2 §12
keeps out of the core registry.

Such a table is declared in a registry of its own, in R2's format, by whatever produces it —
which is R17's mechanism, applied to a materialization rather than an institutional
extension. A validator holding that registry checks the coordinate table like any other; one
without it reports the pointer as unresolved and continues.

## 6. Resource references are checked by the shim

`coordinate_resource` names a resource, and no table of resources exists to join against, so
it cannot be an SQL foreign key. A validator resolves it against the manifest, alongside
verifying that `coordinate_array_asset_id` resolves to a one-dimensional array of the right
length — both storage-layer facts, which R12 §4 places outside SQL.

## 7. What is deferred

**The `trial` and `unit` coordinate tables themselves.** §2.4 defines how an axis points at
one; what those tables contain for `analysis.binned_spikes` waits for a materialisation that
constrains it. The mechanism does not wait, because without it no analysis array is
describable at all.

**Non-dimension coordinates.** xarray permits a coordinate spanning several axes — a 2-D
latitude field over a curvilinear grid. Reaching an electrode's CCF position from a channel
axis is a join through `core.array_channels` and `core.electrode_coordinates` (R19 §3), which
is more normalized and needs no new mechanism.

## 8. Table count

28 tables, from R19 §5's 26: `analysis.array_assets` and `analysis.array_dimensions` (§5).
The coordinate columns themselves add no table, only fields on `core.array_dimensions` and
its analysis mirror.

# R19 — Per-Channel Scaling and Coordinate Frames

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | `02_core_logical_schemas.md` |
| **Depends on** | R3 §3.0 (duplication test, multiplicity rule), R3 §6.1 (`array_channels` axis) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Three properties in the intended data are per-channel or per-frame, and `02` represents each
as a single value (`inventory/nwb-core-schema-comparison.md` §2.4, §2.5).

**Scaling is per channel.** `core.array_assets` carries `conversion`, `offset`, and `unit` as
scalars for a whole array. Core NWB has `ElectricalSeries.channel_conversion` — "channel-specific
conversion factor" — and the AIND file carries `gain_to_physical_unit`,
`offset_to_physical_unit`, and `physical_unit` per electrode. An array whose channels differ
in gain cannot be converted to physical units from a packet.

**Sampling is not simultaneous.** Neuropixels multiplexes channels through shared ADCs, so
channels within one sample index are acquired at slightly different times. The file records
this as `inter_sample_shift`, and it is nonzero and varies: `[0, 0, 0.0625, 0.0625]`
in fractions of a sample period. The registry has no way to say it, and its tick model
otherwise implies a sample index is one instant across all channels.

**Electrodes sit in more than one coordinate frame.** `core.electrodes` has one `x_um`,
`y_um`, `z_um` triple and one `coordinate_frame`. The file populates probe-relative geometry
*and* CCF coordinates simultaneously:

```text
rel_x / rel_y       0, 32, 0, 32  /  0, 0, 15, 15        probe-relative µm
ccf_ml / ap / dv    -1968.4, 8768.5, -5142.2, …          CCF µm
x / y / z           nan                                   NWB's own frame, unused
```

A single triple holds one of these. Which one a packet keeps is a loss either way: probe
geometry or anatomy.

## 2. Per-channel scaling and timing

`core.array_channels` gains:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `conversion` | float64 | no | Multiply stored values by this before `offset`. |
| `offset` | float64 | no | Add after `conversion`. |
| `unit` | string | no | Physical unit of the converted value. |
| `inter_sample_shift` | float64 | no | Acquisition time offset within one sample period, in sample periods. |

Scaling lives on the channel rather than the electrode because it is a property of the
acquisition path for that channel in that array. One electrode recorded into an AP-band and
an LFP-band array may be scaled differently in each; NWB places it on the electrode, which
cannot express that.

### 2.1 An array declares scaling at one level, not two

`core.array_assets.conversion`, `offset`, and `unit` are retained for the uniform case, which
is the common one. An array MUST NOT declare scaling at both levels: two statements of the
same relation can disagree, and nothing would say which governs — the same reasoning R13 §4
applies to clock alignment.

```sql
-- core.array_assets.one_scaling_level  (error)
SELECT a.array_asset_id FROM core_array_assets a
WHERE a.conversion IS NOT NULL
  AND EXISTS (SELECT 1 FROM core_array_channels c
              WHERE c.array_asset_id = a.array_asset_id AND c.conversion IS NOT NULL)
```

```sql
-- core.array_channels.scaling_pair_complete  (error)
-- A conversion without a unit yields a number in no known quantity.
SELECT array_asset_id, channel_index FROM core_array_channels
WHERE conversion IS NOT NULL AND unit IS NULL
```

`inter_sample_shift` has no array-level counterpart; it is per channel or absent.

## 3. New table: `core.electrode_coordinates`

Replaces `core.electrodes`' single `x_um`, `y_um`, `z_um`, `coordinate_frame` columns, which
are struck.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `electrode_id` | string | yes | Electrode ID. |
| `coordinate_frame` | string | yes | The frame these coordinates are in. |
| `x_um` | float64 | no | X in micrometres, in that frame. |
| `y_um` | float64 | no | Y in micrometres. |
| `z_um` | float64 | no | Z in micrometres. |

Primary key: `(electrode_id, coordinate_frame)`.
References: `electrode_id` -> `core.electrodes.electrode_id`.
Sort: the primary key (R10 §2).

An electrode has zero or more coordinate assignments, one per frame, which is R3 §3.0's
multiplicity rule. `coordinate_frame` is an open vocabulary on R8 §4's terms — `probe`,
`ccf`, and `stereotaxic` are reserved with those meanings; a lab's own frame is conforming.

Axes are named `x_um`, `y_um`, `z_um` in every frame, and their meaning is the frame's. CCF's
`ml`, `ap`, `dv` map onto them in that order, which the frame's definition fixes rather than
this specification.

All three are nullable because a two-dimensional frame is normal: probe geometry has no depth
component, and the file's `rel_x`/`rel_y` carry no third axis.

## 4. What this does not do

**No frame registry.** `coordinate_frame` is a name. What a frame means, its origin, and its
handedness are outside this specification — a registration extension (R17) is where that
belongs.

**No transforms between frames.** A packet carrying both probe and CCF coordinates states
both; it does not state how one maps to the other.

**No unit position.** `estimated_x`, `estimated_y`, `estimated_z` and `depth` in the NWB file
locate a *unit*, derived from its waveform by a method with parameters. That is pipeline-
specific in the way quality metrics are, and belongs in an extension (R16 §5, R17).

## 5. Table count

26 tables, from R18 §6's 25.

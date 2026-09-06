# R28 — Where a Unit Sits

| | |
|---|---|
| **Status** | **Accepted** 2026-08-28 |
| **Amends** | `02_core_logical_schemas.md` (`core.units`, `core.array_channels`), R19 §3 |
| **Depends on** | R16 (unit quality labels), R19 (per-channel scaling and coordinate frames), R20 (array axis coordinates) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

A unit is recorded on several electrodes and has a position. `core.units` can express neither.
It carries `default_electrode_id`, one electrode, which is the peak channel and not the set;
and no coordinates at all, so *"which units are in this region"* — the first step of most
analyses this format exists to serve — cannot be asked.

Both facts are in the source. On one AIND stream the SortingAnalyzer carries:

```text
sparsity_mask               [836, 382]  bool     which contacts carry each unit
extensions/unit_locations   [836, 3]    float64  position, triangulated between contacts
```

and the NWB carries per-unit `ccf_ap`/`ccf_dv`/`ccf_ml` beside `estimated_x`/`estimated_y`/
`estimated_z` — the same unit located in two frames, which is the situation R19 §3 addressed
one level down and did not extend upward.

### 1.1 What NWB does here, and why not to copy it

NWB relates a unit to its electrodes through three index spaces in one row, none of them ids.

| column | space | on real data |
|---|---|---|
| `electrodes` | row index into the global electrode table, ragged via `electrodes_index` | 0..4607 |
| `extremum_channel_index` | index **within the unit's own region** | 0..382 on every probe |
| `waveform_mean`'s third axis | position within that same region | 384 wide |

So the peak electrode of unit *i* is `electrodes[start_i + extremum_channel_index[i]]`, and
the waveform on axis position *k* belongs to `electrodes[start_i + k]`. Two integer columns
named `…_index` on one row, one global and one local, distinguishable only by knowing the
convention. The measured file is internally consistent — each device's units do point into
that device's own block — but nothing in the data says which space a column is in.

`waveforms` is worse and is not written by this pipeline: doubly ragged, with
`waveforms_index_index` indexing `waveforms_index` indexing `waveforms`, and the electrode of
each row again recoverable only positionally.

This revision therefore does not mirror NWB's shape. Positional indexing into a ragged region
is precisely what R3 §2.1's physical floor rules out, and the alternative is ordinary: name
the electrode.

### 1.2 The sparsity is real and NWB discards it

The mask above is genuinely sparse — a unit occupies tens of contacts, not hundreds. The NWB
export densifies it: every one of 6781 units declares all 384 electrodes, so `electrodes` is
2,603,904 entries carrying no information, and `waveform_mean` is `[6781, 150, 384]` float64,
**3.1 GB**, with `waveform_sd` another 3.1 GB. Storing the set as rows keeps what the mask
knows and costs a few tens of thousands of rows per stream.

## 2. New table: `core.unit_electrodes`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `electrode_id` | string | yes | An electrode this unit was detected on. |
| `channel_ordinal` | int64 | no | 0-based position of this electrode in the unit's channel list, where a dense array axis is indexed by it. |
| `is_primary` | bool | no | Whether this is the unit's peak electrode. |
| `amplitude` | float64 | no | The unit's amplitude on this electrode, in `core.sorting_runs.amplitude_unit`. |

Primary key: `(session_id, unit_id, sorting_run_id, curation_id, electrode_id)`.
References: the four-column unit key -> `core.units`; `electrode_id` -> `core.electrodes`.
Sort: the primary key (R10 §2).

`channel_ordinal` exists so a dense per-unit array — a mean waveform — can say what its
electrode axis means. R20 §2 already lets an axis name a resource and the column holding its
0-based position; this is that column. It is optional because a packet with no such array
needs no ordinal, and it is **not** an identifier: R5 §5's rule holds, and nothing may join
on it.

`is_primary` is nullable rather than required because a source may not designate one. Where
it is present exactly one row per unit SHOULD carry it.

```sql
-- core.unit_electrodes.one_primary  (warning)
-- Two peak channels is not a peak; the reader has no rule for choosing.
SELECT session_id, unit_id, sorting_run_id, curation_id, COUNT(*) AS n
FROM core_unit_electrodes WHERE is_primary
GROUP BY session_id, unit_id, sorting_run_id, curation_id HAVING COUNT(*) > 1
```

```sql
-- core.unit_electrodes.ordinal_contiguous  (error)
-- A dense axis indexed by a gapped ordinal addresses rows that are not there.
SELECT session_id, unit_id, sorting_run_id, curation_id,
       COUNT(*) AS n, MAX(channel_ordinal) AS hi
FROM core_unit_electrodes WHERE channel_ordinal IS NOT NULL
GROUP BY session_id, unit_id, sorting_run_id, curation_id
HAVING MAX(channel_ordinal) <> COUNT(*) - 1 OR MIN(channel_ordinal) <> 0
```

### 2.1 `default_electrode_id` stays

It is the peak channel as a single column, and it stays for the same reason
`core.units.n_spikes` does: the summary is what most queries want, and recomputing it from
the child table on every read is work the writer already did. It becomes a validated
denormalization rather than the only way to say where a unit is.

```sql
-- core.units.default_electrode_is_declared  (error)
-- The designated electrode must be one the unit was actually detected on.
SELECT u.session_id, u.unit_id, u.sorting_run_id, u.curation_id, u.default_electrode_id
FROM core_units u
WHERE u.default_electrode_id IS NOT NULL
  AND EXISTS (SELECT 1 FROM core_unit_electrodes e
              WHERE e.session_id = u.session_id AND e.unit_id = u.unit_id
                AND e.sorting_run_id = u.sorting_run_id AND e.curation_id = u.curation_id)
  AND NOT EXISTS (SELECT 1 FROM core_unit_electrodes e
                  WHERE e.session_id = u.session_id AND e.unit_id = u.unit_id
                    AND e.sorting_run_id = u.sorting_run_id AND e.curation_id = u.curation_id
                    AND e.electrode_id = u.default_electrode_id)
```

## 3. New table: `core.unit_coordinates`

Exactly R19 §3's `core.electrode_coordinates`, one level up, because the argument is the same:
a unit has a position in the probe's frame *and* in an atlas, the two are not convertible
without a registration the packet does not carry, and a single `x_um` column would force a
writer to choose one and lose the other.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `coordinate_frame` | string | yes | The frame these coordinates are in. |
| `x_um` | float64 | no | X in micrometres, in that frame. |
| `y_um` | float64 | no | Y in micrometres. |
| `z_um` | float64 | no | Z in micrometres. |

Primary key: `(session_id, unit_id, sorting_run_id, curation_id, coordinate_frame)`.
References: the four-column unit key -> `core.units`.
Sort: the primary key.

`coordinate_frame` is **open**, as R19 left it. Real data uses at least the probe frame and
CCF, and an atlas this revision has not heard of is not an error.

The estimate is deliberately not snapped to an electrode. A unit triangulated between two
contacts has a depth that `default_electrode_id` cannot express, and depth-ordered analysis
is a reason this table exists rather than a refinement of it.

## 4. `core.array_channels.electrode_id` gains its reference

The column exists and has no foreign key. Its only declared reference is to
`core.array_dimensions`, so nothing checks that a channel's electrode is one the packet
declares — the single link between a dense array's channels and the electrodes they came from
is unvalidated.

References: `electrode_id` -> `core.electrodes.electrode_id`, nullable-guarded (R2 §7.1), since
an array whose channels are not electrodes leaves it null.

## 5. What this does not do

- **No waveform tables.** A mean waveform is a dense array: `core.array_assets` with
  `core.array_dimensions` naming its axes, which is Phase 5 and needs no new schema. §2's
  `channel_ordinal` is what makes its electrode axis addressable under R20 §2, and that is
  the whole of this revision's involvement with waveforms.
- **No per-spike waveforms.** NWB's doubly-ragged `waveforms` has no analogue here, and this
  pipeline does not write them. If one ever must, it is an array asset keyed by
  `core.spike_events`' primary key, not a ragged column.
- **No unit-to-unit relations.** Whether two units share electrodes is derivable from §2 by
  self-join, which is what a child table buys. A materialization belongs in `analysis`.
- **No lineage across curations.** §2 and §3 are keyed by the full unit identity, so a unit's
  electrodes under one curation say nothing about another's. `02` still has no table for a
  merge or a split, and this revision does not add one.
- **Nothing about `extremum_channel_index`.** An importer resolves NWB's local index against
  the unit's region and writes `electrode_id`; the positional form does not survive into a
  packet.

## 6. Consequences for the registry

- Two new tables: 30 -> **32**. `conformance/spec-sweep/tables.py` gains both.
- One new reference on `core.array_channels`, nullable-guarded.
- Four Tier 2 rules: `one_primary`, `ordinal_contiguous`, `default_electrode_is_declared`, and
  the Tier 1 checks the two tables generate from structure.
- No column is removed and no existing rule changes, so a packet written before this revision
  stays conforming — both tables are absent, which R2 §5 already means *unknown*.

## 7. Open

- **Whether `is_primary` and `default_electrode_id` should both exist.** They say the same
  thing in two places, and §2.1's rule exists to keep them agreeing. Dropping the column in
  favour of the flag would cost every "where is this unit" query a join; dropping the flag
  would make the child table unable to answer it alone.
- **Whether `amplitude` belongs here.** It is per (unit, electrode), so it fits, and it is
  what a sparsity mask is usually thresholded from. But it is also the first quality-like
  number in a structural table, and R17's extension registry may be the better home.
- **Whether a unit's coordinates should carry an uncertainty.** Triangulation produces one,
  the analyses that care about depth would use it, and no source in hand writes it down.

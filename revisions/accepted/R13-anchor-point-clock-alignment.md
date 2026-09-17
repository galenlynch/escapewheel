# R13 — Anchor-Point Clock Alignment

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02_core_logical_schemas.md`, R3 §3.4 |
| **Depends on** | R3 (typed clock transform), R6 (wall-clock binding) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R3 §3.4 replaced `core.clocks.transform_to_parent` with two typed columns,
`transform_slope` and `transform_offset`, and recorded the limitation explicitly:

> **Open:** non-linear alignment (piecewise, anchor-point) needs a child table. This
> revision does not define one; packets requiring it are out of scope for
> `escapewheel-portable-v0.1`.

Discovery against a real AIND session finds that the intended data requires it
(`inventory/ecephys_776259_2025-04-09.md` §5). Alignment is performed twice, both times
through observed sync pulses rather than a fitted line:

```python
local_aligned = align_timestamps_to_anchor_points(
    stream.sample_numbers,
    sync_events.sample_number.values,
    main_events.sample_number.values / 30000,
)
harp_aligned = align_timestamps_to_anchor_points(local_aligned, start_times, harp_times)
```

The raw acquisition carries the consequence: each compressed stream stores `times_seg0`, one
`float64` per sample — 191.6M values for a 1.77 h probe recording — because the relation
between the probe counter and wall time is not two numbers.

A clock model that cannot express this puts the specification's own target data outside its
portable profile.

## 2. What is not affected

Ticks remain exact. A probe's sample index is still the canonical `t_tick` on its own clock,
and R3 §2.1's integer-tick invariant is untouched. Alignment concerns only the relation
*between* clocks.

Nor does this revisit the linear case. A pair of clocks genuinely related by a rate ratio
and an offset continues to use R3 §3.4's two columns, which stay the cheaper and clearer
representation where they apply.

## 3. New table: `core.clock_anchors`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `clock_id` | string | yes | The clock being aligned. |
| `anchor_index` | int64 | yes | 0-based position in this clock's anchor sequence. |
| `t_tick` | int64 | yes | Tick on `clock_id`. |
| `parent_tick` | int64 | yes | The corresponding tick on `parent_clock_id`. |

Primary key: `(clock_id, anchor_index)`.
References: `clock_id` -> `core.clocks.clock_id`.

Sort: `clock_id, anchor_index` (R10 §2).

An anchor records one observed correspondence — typically a sync pulse seen on both clocks.
Between consecutive anchors the mapping is **linear interpolation**; outside the first and
last anchor it is **undefined**, and a consumer MUST NOT extrapolate.

`parent_tick` is expressed on the parent's own clock, so the pair is two integers and the
tick invariant holds on both sides. A parent expressed in wall-clock time uses R6's
`tick_zero_utc` on the parent clock rather than storing seconds here.

## 4. Which representation a clock uses

A clock with a `parent_clock_id` declares its alignment in exactly one of three states:

| State | Meaning |
|---|---|
| neither transform columns nor anchors | parentage known, alignment not measured |
| `transform_slope` and `transform_offset` | linear alignment |
| rows in `core.clock_anchors` | piecewise alignment |

A clock MUST NOT declare both. Two models of the same relation can disagree, and nothing
would say which governs.

```sql
-- core.clocks.one_alignment_model  (error)
SELECT c.clock_id FROM core_clocks c
WHERE c.transform_slope IS NOT NULL
  AND EXISTS (SELECT 1 FROM core_clock_anchors a WHERE a.clock_id = c.clock_id)
```

```sql
-- core.clock_anchors.requires_parent  (error)
SELECT DISTINCT a.clock_id FROM core_clock_anchors a
JOIN core_clocks c USING (clock_id) WHERE c.parent_clock_id IS NULL
```

```sql
-- core.clock_anchors.anchor_index_contiguous  (error)
SELECT clock_id, COUNT(*) AS n, MAX(anchor_index) AS hi FROM core_clock_anchors
GROUP BY clock_id HAVING MAX(anchor_index) <> COUNT(*) - 1 OR MIN(anchor_index) <> 0
```

```sql
-- core.clock_anchors.monotonic  (error)
-- Interpolation between anchors is only defined if both sequences increase together.
SELECT clock_id, anchor_index FROM (
  SELECT *, LAG(t_tick) OVER (PARTITION BY clock_id ORDER BY anchor_index) AS prev_t,
            LAG(parent_tick) OVER (PARTITION BY clock_id ORDER BY anchor_index) AS prev_p
  FROM core_clock_anchors)
WHERE prev_t IS NOT NULL AND (t_tick <= prev_t OR parent_tick <= prev_p)
```

## 5. What this deliberately does not do

**No per-sample timestamps.** `times_seg0` holds one value per sample; anchors hold one per
sync pulse, which is smaller by orders of magnitude and is the form the correction was
derived from. Storing the expanded result would restate what the anchors already determine,
contrary to R3 §3.0.

**No interpolation kind.** Linear between anchors is the only defined rule. A packet needing
spline or drift-model interpolation is out of scope, as anchor-point alignment was before
this revision.

**No alignment quality.** R4 §3.2 keeps `sync_quality` and `sync_method` in
`core.clocks.metadata`; this revision does not promote them.

## 6. Table count

23 tables, from R9 §2's 22. `conformance/spec-sweep/tables.py` gains the step.

# R6 — Clock Wall-Clock Binding

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02`, `05` |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

The specification carries two disjoint time systems (R3 §2.1): integer `*_tick` columns on a
declared clock for experimental time, and wall-clock `timestamp` columns for administrative
and provenance time. Nothing machine-readable connects them.

`core.clocks.origin` is a free-text `string` — `02:237`, "Origin description" — and `08`'s
example value is `sample 0 at acquisition start`. Searching the specification for UTC,
wall-clock, absolute time, or epoch returns nothing relevant; the only "epoch" matches are
`epoch_name` and `epoch_start_rel_tick` in the analysis layer, which are task epochs.

Two consequences:

1. The wall-clock time of a spike cannot be computed from a packet. Nothing states that a
   clock's tick 0 coincides with `core.sessions.session_start_time`, and for most acquisition
   systems it does not.
2. `05:131` lists a semantic validator — "spike ticks are nonnegative or justified by clock
   origin" — that cannot be implemented. No validator can evaluate "justified by" against
   prose.

## 2. `core.clocks.tick_zero_utc`

`core.clocks` gains:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `tick_zero_utc` | timestamp | no | Wall-clock instant of tick 0 on this clock. |

Optional, because it is not always known: an acquisition system may report sample counts with
no absolute reference. `origin` is retained unchanged as the human-readable description of
where tick 0 falls; `tick_zero_utc` states the same thing in a form a program can use.

Per R3 §2.1 it is a wall-clock column: Parquet `TIMESTAMP`, `isAdjustedToUTC=true`, `MICROS`,
never `INT96`.

Where present, the wall-clock time of any tick is:

```text
tick_zero_utc + t_tick / effective_tick_rate
```

using `tick_rate_hz`, or `tick_rate_num / tick_rate_den` where the exact rational rate is
given.

## 3. Retiring the unenforceable rule

With `tick_zero_utc` present, `05:131` becomes checkable and is restated as two rules:

```sql
-- core.spike_events.ticks_within_clock_span  (warning)
-- A negative tick is legal only where the clock's origin post-dates the event.
SELECT DISTINCT s.session_id, s.clock_id, MIN(s.t_tick) AS min_tick
FROM core_spike_events s
JOIN core_clocks c USING (clock_id)
WHERE s.t_tick < 0 AND c.tick_zero_utc IS NULL
GROUP BY s.session_id, s.clock_id
```

```sql
-- core.clocks.tick_zero_plausible  (warning)
-- Tick zero should not precede the session by an implausible margin.
SELECT c.clock_id, c.tick_zero_utc, s.session_start_time
FROM core_clocks c JOIN core_sessions s USING (session_id)
WHERE c.tick_zero_utc IS NOT NULL
  AND (c.tick_zero_utc < s.session_start_time - INTERVAL 1 DAY
    OR c.tick_zero_utc > s.session_start_time + INTERVAL 1 DAY)
```

Both are warnings, not errors. A negative tick on a clock with no absolute reference is
unusual but not invalid, and the one-day window is a sanity bound on data entry, not a
semantic requirement.

Where `tick_zero_utc` is absent, `05:131` is simply struck — an unimplementable rule is worse
than an absent one.

## 4. Relationship to `session_start_time`

The two are independent and MUST NOT be conflated.

`core.sessions.session_start_time` is when the session began as an experimental event.
`tick_zero_utc` is when a particular clock's counter was zero. They coincide only if
acquisition started exactly at session start on that clock, which is a fact about a rig, not a
rule. A session with several clocks has one `session_start_time` and potentially a different
`tick_zero_utc` per clock — which is precisely the information needed to relate them.

## 5. Scope

This revision adds no drift model, leap-second handling, or alignment quality metadata. R4
§3.2 keeps synchronization quality in `core.clocks.metadata`, and R3 §3.4 covers
clock-to-clock alignment through `transform_slope` and `transform_offset`. `tick_zero_utc`
records the wall-clock instant of tick 0 and nothing further.

Under R1 a single-session packet rarely requires it. It applies to relating sessions to one
another and to aligning packet data against external streams recorded on wall-clock time.

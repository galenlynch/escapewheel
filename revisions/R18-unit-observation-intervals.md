# R18 — Unit Observation Intervals

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | `02_core_logical_schemas.md`, `06_analysis_layer.md` |
| **Depends on** | R3 §3.0 (multiplicity rule), R5 (flat spikes) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`02` defines `core.units.firing_rate_hz` as "Firing rate if known" and never says over what
window. The column is therefore uninterpretable: a unit with 100 spikes observed for ten
minutes of a sixty-minute session has a rate of 10/min or 1.7/min depending on an answer no
packet carries.

The specification has no way to say when a unit was observable at all. Nothing distinguishes
*the neuron was silent* from *we were not recording it*. R5 §4's `first_spike_tick` and
`last_spike_tick` bound the spikes, not the observation, and cannot: a unit that fires,
disappears, and returns has spikes at both ends of a gap it was absent from.

Core NWB carries the concept — `Units.obs_intervals`, shaped `[num_intervals, start|end]` and
indexed per unit — precisely because units drift in and out of a recording. Neuropixels units
do exactly that, and a single window cannot express it.

SpikeInterface computes `firing_rate = num_spikes / recording_duration`, over the whole
recording regardless of observability. That is a defensible default and it is not what this
specification says, because this specification says nothing.

## 2. New table: `core.unit_observation_intervals`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session ID. |
| `unit_id` | string | yes | Unit ID. |
| `sorting_run_id` | string | yes | Sorting run ID. |
| `curation_id` | string | yes | Curation ID. |
| `interval_index` | int64 | yes | 0-based position in this unit's interval sequence. |
| `start_tick` | int64 | yes | First tick of the interval, inclusive. |
| `stop_tick` | int64 | yes | Last tick of the interval, inclusive. |
| `clock_id` | string | yes | Clock for the interval bounds. |

Primary key: `(session_id, unit_id, sorting_run_id, curation_id, interval_index)`.

References: `(session_id, unit_id, sorting_run_id, curation_id)` -> `core.units`;
`clock_id` -> `core.clocks`.

Sort: the primary key (R10 §2).

Multiple intervals per unit are the point. A unit observed continuously has one row; a unit
that drifts out and returns has several. R3 §3.0's multiplicity rule gives the shape.

Absence of rows for a unit means observability was not recorded, not that the unit was never
observed. A consumer MUST NOT infer zero observation from an absent row.

## 3. Rules

```sql
-- core.unit_observation_intervals.interval_valid  (error)
SELECT session_id, unit_id, interval_index, start_tick, stop_tick
FROM core_unit_observation_intervals WHERE stop_tick < start_tick
```

```sql
-- core.unit_observation_intervals.index_contiguous  (error)
SELECT session_id, unit_id, sorting_run_id, curation_id, COUNT(*) AS n
FROM core_unit_observation_intervals
GROUP BY session_id, unit_id, sorting_run_id, curation_id
HAVING MAX(interval_index) <> COUNT(*) - 1 OR MIN(interval_index) <> 0
```

```sql
-- core.unit_observation_intervals.non_overlapping  (error)
-- Overlapping windows would double-count observation time.
SELECT session_id, unit_id, interval_index FROM (
  SELECT *, LAG(stop_tick) OVER (
    PARTITION BY session_id, unit_id, sorting_run_id, curation_id ORDER BY interval_index
  ) AS prev_stop
  FROM core_unit_observation_intervals)
WHERE prev_stop IS NOT NULL AND start_tick <= prev_stop
```

```sql
-- core.spike_events.within_observation  (warning)
-- A spike outside every declared window means the windows or the spikes are wrong.
SELECT s.session_id, s.unit_id, s.t_tick
FROM core_spike_events s
WHERE EXISTS (SELECT 1 FROM core_unit_observation_intervals o
              WHERE o.session_id = s.session_id AND o.unit_id = s.unit_id
                AND o.sorting_run_id = s.sorting_run_id AND o.curation_id = s.curation_id)
  AND NOT EXISTS (SELECT 1 FROM core_unit_observation_intervals o
                  WHERE o.session_id = s.session_id AND o.unit_id = s.unit_id
                    AND o.sorting_run_id = s.sorting_run_id AND o.curation_id = s.curation_id
                    AND s.t_tick BETWEEN o.start_tick AND o.stop_tick)
```

The last is a warning rather than an error: a boundary convention may legitimately place a
spike at an edge, and a packet is not worthless because one spike falls outside a window.

## 4. `firing_rate_hz` gets a defined denominator

`core.units.firing_rate_hz`, where present, is the unit's spike count divided by its total
observed duration — the summed length of its `core.unit_observation_intervals`, converted to
seconds using the interval clock's tick rate.

Where a unit has no observation intervals, `firing_rate_hz` is the spike count divided by the
recording's extent. A packet SHOULD state which denominator it used in
`core.units.metadata`, because the two differ and a consumer cannot tell them apart from the
value.

## 5. Consequence for the analysis layer

`06`'s `analysis.unit_condition_rates` carries `duration_ticks` per epoch without saying
whether the unit was observed for it. With observation intervals present, a materialization
MUST intersect the epoch with the unit's observed windows rather than assume the whole epoch,
or a unit absent for half a condition will appear to have fired at half its true rate.

`06`'s `analysis.spikes_by_trial` is unaffected: it aligns spikes that exist and makes no
rate claim.

## 6. Table count

25 tables, from R16 §6's 24.

# R25 — Event Stream Support, and Why Session Extent Is Not a Tick Range

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | `02_core_logical_schemas.md` (`core.sessions`) |
| **Depends on** | R23 (event streams), R24 (rule templates), R13 (anchor alignment), R18 (observation intervals) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R18 gave units observation intervals because the absence of a spike is ambiguous: a unit that
fired nothing between two ticks either was quiet or was not being observed. Without windows,
`firing_rate_hz` has no denominator.

Event streams have the same ambiguity and no answer to it. No licks between two ticks either
means the animal did not lick or means the sensor was not recording, and every rate computed
over a stream needs to know which. The session inventoried in
`inventory/nwb-zarr-776259-2025-04-09.md` §3.7 makes it concrete: behaviour runs 7792 s,
ephys 6388 s, and licks continue 23 minutes past the last spike. A consumer asking "how many
licks per second during the recording" is asking about an interval no table currently
declares.

R24's `interval` template makes this cost one declaration rather than three hand-copied rules,
which is the payoff that revision was for.

## 2. New table: `core.event_stream_observation_intervals`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `event_stream_id` | string | yes | The stream being observed. |
| `interval_index` | int64 | yes | 0-based position in this stream's interval sequence. |
| `start_tick` | int64 | yes | First observed tick, on the stream's clock. |
| `stop_tick` | int64 | yes | Last observed tick, on the stream's clock. |

Primary key: `(event_stream_id, interval_index)`.

References: `event_stream_id` -> `core.event_streams`.

Sort: the primary key (R10 §2).

A stream MAY have no rows here, and absence means the packet declares nothing about when the
stream was observed — the same honest state R18 permits for units. Where rows are present they
are validated.

### 2.1 It carries no `clock_id`, and `core.unit_observation_intervals` does

The asymmetry is deliberate and follows R3 §3.0. `core.units` declares no clock, so R18's
table has to carry one or its ticks are meaningless. `core.event_streams` **does** declare a
`clock_id` (R23 §2), so repeating it here would restate what the parent already says.

R23 §4.2 kept `clock_id` on `core.events` under the same rule, and the difference is what the
duplication buys. An event row is legitimately read without its stream — `03` sorts
`core.events` by `session_id, clock_id, t_tick, event_type`, so scanning a session's timeline
never touches `core.event_streams`. An observation interval is meaningless without knowing
whose interval it is, so the join to the stream always happens, and the clock comes with it
for free.

Duplication that buys nothing is duplication that can disagree.

## 3. Declared through R24's template

```json
"core.event_stream_observation_intervals": [
  {
    "use": "interval",
    "start": "start_tick",
    "stop": "stop_tick",
    "partition_of": ["event_stream_id"],
    "index": "interval_index",
    "overlap_op": "<=",
    "overlap_message": "observation windows overlap, which would double-count observed time"
  }
]
```

`overlap_op` is `<=`: closed intervals, so two windows may not share an endpoint. Two windows
that touch are one window, and writing them as two double-counts the shared tick in exactly
the denominator §1 exists to provide. This is stated rather than inherited, per R24 §5.

Three checks are generated — `interval_valid`, `index_contiguous`, `non_overlapping` — and no
SQL is written.

### 3.1 Events must fall inside the windows their stream declares

Observation intervals are **supplied, never inferred**. Nothing derives a window from the
events in it, and nothing may: a window is a claim about when the sensor was recording, which
the events themselves cannot establish — that is the whole point of §1's ambiguity.

Supplied claims need checking against the data, which is the counterpart R18 §3 wrote for
spikes and this revision owes for events:

```sql
-- core.events.within_observation  (warning)
SELECT e.session_id, e.event_id, e.stream_id, e.t_tick FROM core_events e
WHERE EXISTS (SELECT 1 FROM core_event_stream_observation_intervals o
              WHERE o.event_stream_id = e.stream_id)
  AND NOT EXISTS (SELECT 1 FROM core_event_stream_observation_intervals o
                  WHERE o.event_stream_id = e.stream_id
                    AND e.t_tick BETWEEN o.start_tick AND o.stop_tick)
```

The `EXISTS` guard means a stream declaring no windows is unchecked rather than in violation —
absence stays legal (§2), and R26's advisory rule is what mentions it.

`warning` rather than `error`, on R18 §3's reasoning: a boundary convention may legitimately
place an event at an edge, and one stray event does not void a packet.

## 4. Session extent is not a tick range

An earlier sketch of this revision gave `core.sessions` a `clock_id`, `start_tick` and
`stop_tick` holding the convex hull of its modalities' support, as a validated denormalization
on the model of `core.units.n_spikes`. That does not work, and the reason is worth recording
so it is not proposed again.

**A session's modalities are on different clocks.** In the AIND case that is the ordinary
situation, not a corner: twelve probe clocks plus HARP. A hull expressed on one clock does not
bound data on another without converting between them.

**R13 makes that conversion undefined exactly where a hull needs it.** Alignment may be
anchor-based, and outside the first and last anchor the mapping is undefined and a consumer
MUST NOT extrapolate. A hull's endpoints are by construction the extremes of the data — which
is precisely where anchor coverage is thinnest. The one conversion a hull requires is the one
most likely to be unavailable.

**So the rule could not be written.** Checking that a declared hull contains its modalities'
support would either compare ticks across incomparable clocks, or check only the sources that
happen to share the session's clock — which, given twelve probe clocks, is often none of them.
R12 §4 exists because a storage-layer check written as SQL fails silently rather than loudly;
a cross-clock containment check written as SQL would fail the same way.

A per-modality answer is exact, on a declared clock, and already expressible. A session-level
one is either wrong or unverifiable. The support tables are the answer, and there is no
cheaper summary that is also true.

## 5. `core.sessions` gains `session_end_time`

What a session-level extent is actually asked for — which sessions ran on a given day, which
overlap a date range — is a wall-clock question, and wall clock has no clock-conversion
problem.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_end_time` | timestamp | no | When the session ended, UTC. |

`02` defines `session_start_time` and no counterpart, so the duration of a session is not
recorded anywhere in the core layer today.

This is **metadata, not a derived summary**. It is what the acquisition system recorded as the
session's end, not a claim computed from the data, and nothing validates it against the tables
— relating a tick to wall clock requires the clock's `tick_zero_utc` (R6), which is optional,
so the check would be unavailable exactly when the metadata is least trustworthy. The only
rule is the one that needs no clock:

```sql
-- core.sessions.session_interval_valid  (error)
SELECT session_id, session_start_time, session_end_time FROM core_sessions
WHERE session_end_time < session_start_time
```

It is `TIMESTAMP(MICROS, UTC)` like every other wall-clock column (R3 §2.2), and it is
explicitly not a tick. The inventory records `session.json` disagreeing with its own NWB by
seven hours on the start time, so an importer writing this column MUST NOT trust a source
offset it has not checked.

## 6. Table count

29 tables after R23, plus `core.event_stream_observation_intervals` -> **30**. See
`conformance/spec-sweep/tables.py` for the ledger.

## 7. What this does not do

- **No support table for arrays.** R20's `origin_tick`, `step_ticks` and the array's own shape
  already determine its extent; declaring it again would restate what the array says.
- **No support table for media.** `core.media_frames` carries a tick per frame.
- **No general support mechanism.** Two tables now use R24's `interval` template with
  `partition_of`, which is the shape recurring, not a new abstraction.
- **Nothing about trial closure.** `core.trials` still declares no `partition_of` and still
  gets no overlap test; whether its `stop_tick` is inclusive remains a question for `02`.

## 8. Open

- **Whether a stream with no observation rows should warn.** Silence is honest, but a packet
  that declares streams and never says when they were observed is one where every rate over
  them is uncomputable. A `warning`-level rule would say so without making the rows required.
  R18 left the same question open for units and it should be answered the same way for both.

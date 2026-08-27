# R23 — Event Streams

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | `02_core_logical_schemas.md` (`core.events`), R9 §4 |
| **Depends on** | R9 (provenance simplification), R10 (default sort order) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`core.events` is the only core stream with no context table.

`core.units` is meaningless without `core.sorting_runs` and `core.curation_versions` — the
specification says so, and makes unit identity contextual on both. `core.spike_events`
inherits that context. Dense arrays have `core.array_assets`. Events have nothing: 2641 rows
repeating `event_type = 'left_lick'` with no declared answer to *what produced them*.

That matters because event times carry different uncertainty depending on where they came
from. A hardware comparator's timestamp, an online software threshold, and an offline
threshold over a stored trace are three different measurements, and an analysis aligning
neural data to licks is entitled to know which it has.

### 1.1 The categorical version of this does not work

The obvious design is a `detection` vocabulary — `hardware`, `online`, `offline`. It fails on
contact with real rigs. Lick detection by capacitance may be thresholded in hardware on one
rig and in software on the acquisition machine on another; the licks are the same licks, and
the boundary falls wherever someone put a comparator. A vocabulary would force a choice
between two labels for one fact.

Line up what actually differs:

| | time uncertainty | recomputable | parameters recorded |
|---|---|:---:|:---:|
| hardware comparator | lowest | no | often not |
| online software threshold | low | no | yes |
| offline threshold on a stored trace | varies | yes | yes |

None of that is a category. It is *parameters, and whether they can be changed* — which is
`core.processing_runs`, a table that already carries `software_name`, `software_version`,
`parameters` and `code_uri`. So the stream points at a processing run rather than declaring a
kind, and the online-threshold case becomes expressible rather than awkward.

This is also the resolution of a question raised and rejected during R20's review: whether
`core` should carry an acquired-versus-derived axis at all. It should not. The layer axis is
"is this the source of truth" — LFP and sorted units are both computed and both canonical.
Acquired-ness is not a property of a fact but of how one came to know it, and it belongs in
provenance.

## 2. New table: `core.event_streams`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `event_stream_id` | string | yes | Stable ID. |
| `session_id` | string | yes | Session ID. |
| `name` | string | yes | Human-readable, e.g. `left_lick_sensor`. |
| `device_id` | string | no | The device that produced it, where one is identified. |
| `clock_id` | string | yes | The clock its events are timed on. |
| `processing_run_id` | string | no | The run that produced it. Null means it came off the device as recorded. |
| `metadata` | json_string | optional | |

Primary key: `event_stream_id`. This follows every other context table — `core.clocks`,
`core.sorting_runs`, `core.probes`, `core.devices`, `core.array_assets` all key on a single
ID, while fact tables such as `core.events` and `core.trials` are session-scoped.

References: `session_id` -> `core.sessions`; `device_id` -> `core.devices` (nullable);
`clock_id` -> `core.clocks`; `processing_run_id` -> `core.processing_runs` (nullable).

Sort: the primary key (R10 §2).

## 3. `core.events` gains a required reference

| Field | Type | Required | Description |
|---|---|:---:|---|
| `stream_id` | string | yes | The stream this event belongs to. |

References: `stream_id` -> `core.event_streams`.

Required, not nullable, on the precedent of `core.units.sorting_run_id`: a packet with sorted
units MUST carry `core.sorting_runs`, and by the same rule **a packet with events MUST carry
`core.event_streams`**. The cost is one row per stream — seven for the session in
`inventory/nwb-zarr-776259-2025-04-09.md`. The benefit is that no event time is unattributed
and the reference needs no `IS NOT NULL` guard; six of the registry's references already do.

## 4. What stays on the event

### 4.1 `event_type` stays, because it is not constant per stream

A stream is a source, not a kind. One DIO line emits rising and falling edges; one stream,
two event types. `event_type` is therefore a per-event fact, not a restatement of what the
stream declares, and R3 §3.0 does not apply to it.

### 4.2 `clock_id` stays, as a validated denormalization

This one *is* a restatement — a sensor is wired to one acquisition system, so the stream
determines the clock. It is kept for two reasons. `03` sorts `core.events` by
`session_id, clock_id, t_tick, event_type`, and a sort key that requires a join to evaluate
is not a sort key. And a tick without its clock is meaningless, so a table that carries ticks
and not clocks is self-describing only to a reader who joins.

R3 §3.0 permits duplication that buys otherwise-unavailable access, and requires a rule to
keep it honest — the same bargain as `core.units.n_spikes`:

```sql
-- core.events.clock_matches_stream  (error)
SELECT e.session_id, e.event_id, e.clock_id, s.clock_id AS stream_clock_id
FROM core_events e
JOIN core_event_streams s ON e.stream_id = s.event_stream_id
WHERE e.clock_id <> s.clock_id
```

## 5. A narrow exception to R9

R9 withdrew the entity/activity/edge graph and stated that outputs are recorded at resource
granularity in the manifest, not per row. `core.event_streams.processing_run_id` is a per-row
link to a processing run, and is an exception to that.

It is justified because the manifest cannot answer the question. The manifest records that
`core.events` — the whole table — was produced by some run. It cannot distinguish a
hardware-detected lick stream from an offline-thresholded one *inside that table*, and those
are the two things an analyst needs to tell apart.

The exception is narrow on purpose. R9 objected to a general graph in which any entity could
be linked to any activity through an edge table. This is one nullable foreign key on one
table, pointing at a table R9 kept. It does not reintroduce
`core.provenance_entities`, `core.provenance_activities`, or `core.provenance_edges`, and it
MUST NOT be read as licence to add similar links elsewhere: a further per-row provenance link
requires its own revision and its own argument that the manifest cannot answer.

Provenance remains SHOULD (R9 §5). A packet may leave every `processing_run_id` null, and
`core.processing_runs` may be absent entirely. What R9 requires — that provenance is
validated where present — still holds, through the nullable foreign key.

## 6. What is deferred

**Latency.** The measurement that motivated this — how far an event time sits from the
physical event — is not given a column. A `latency_tick` that does not say whether it has
already been applied is a convention read two ways, which is the failure `03` records for
`core.media_frames.frame_index`. Until a real behaviour import forces the question, latency
belongs in `metadata`.

**Sort order.** `03` sorts `core.events` clock-major, serving "the session timeline". A
stream-major order would serve "all the licks". Which is better is a measurement, not an
argument, and R3 §7.3's ranking for `core.spike_events` came from one. `03`'s order stands
until someone runs it.

## 7. Table count

28 tables after R20, plus `core.event_streams` -> **29**. See
`conformance/spec-sweep/tables.py` for the ledger.

# R38 — Observation Belongs to the Clock

| | |
|---|---|
| **Status** | **Accepted** 2026-08-31 |
| **Amends** | R18 §2 (unit observation intervals), R25 §3 (event stream observation intervals) |
| **Depends on** | R23 (event streams), R27 (clock graph integrity) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R18 gives a unit observation intervals so a firing rate has a denominator. R25 gives an event
stream the same. Both are right about the need and wrong about where the fact lives.

**The fact is about the device, not the thing observed.** A unit was observable while its probe
was running. A lick sensor was watched while its acquisition was running. Written per unit, that
is one window copied 6,781 times on a session of this size; written per stream, ten more copies
of a second window. Nothing distinguishes the copies, and a packet that acquires two more
modalities gets a third table.

**A unit does not name its clock.** `core.units` carries `probe_id`, `sorting_run_id` and
`curation_id`; the clock is recovered by the string convention `{sorting_run_id}.samples`, which
the two adapters agree on and which no rule can see. `core.event_streams.clock_id` exists and is
required, so the two halves of the same idea are expressed differently.

**The interval table's ticks are on an unnamed clock.** `core.event_stream_observation_intervals`
has `start_tick` and `stop_tick` and no `clock_id`, against the invariant that every tick carries
the clock it was counted on. It is consistent today only because this packet's behaviour streams
happen to share one clock.

**And R25 §4 already named the answer.** Rejecting a session-level tick hull, it concluded: *"A
per-modality answer is exact, on a declared clock, and already expressible."* A per-clock answer
is that, generalized — and it never meets R25's objection, because a window on a clock bounds
data on that clock and is never asked to bound data on another.

## 2. Decision

### 2.1 A clock declares when it was observing

New table `core.clock_observation_intervals`.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session. References `core.sessions`. |
| `clock_id` | string | yes | The clock. References `core.clocks`. |
| `interval_index` | int64 | yes | 0-based position in this clock's interval sequence. |
| `start_tick` | int64 | yes | First tick observed, **on `clock_id` itself**. |
| `stop_tick` | int64 | yes | Last tick observed, on `clock_id` itself. |

Primary key `(session_id, clock_id, interval_index)`. The three interval rules come from the
`interval` template (R24), as they do for the two existing tables.

**The ticks need no clock column because the key is the clock.** That is the whole of why this
shape works: every containment check against it is a same-clock comparison, so the conversion
R25 §4 could not write is never required.

More than one interval is permitted, for an acquisition paused and resumed. A counter that
*resets* mid-session is two clocks, as R27 §3 already requires, not two intervals.

### 2.2 A sorting run declares its clock

`core.sorting_runs` gains `clock_id` (required, references `core.clocks`, `since: R38`). A
unit's clock is then its run's clock: twelve rows carry the fact rather than 6,781, and the
string convention stops being load-bearing.

### 2.3 Observation is inherited, and may be refined

A thing observed on a clock is observed during that clock's declared intervals. A packet MAY
narrow that with a per-thing interval — `core.unit_observation_intervals` for a unit,
`core.event_stream_observation_intervals` for a stream — and where it does, the narrower
intervals apply instead of the clock's, not in addition to them.

A refinement MUST come from something that measured it. A writer MUST NOT derive one from the
timestamps of the thing observed: R25 §3 states the reason, that a denominator taken from the
numerator makes every rate identical and every coverage check vacuous, and it holds unchanged
for units.

A clock's own interval is not derived from what it recorded either. It is the extent of the
acquisition — for a sample clock whose `origin` is sample 0 of a recording, `start_tick` is 0 by
construction and `stop_tick` is the recording's length. That is an independent fact: a unit that
fires nothing still has a denominator.

### 2.4 The two `observation_declared` rules accept an inherited window

Both remain `info`. Each now reports only a subject that has neither its own interval nor an
interval on the clock it is observed on, reached through `core.sorting_runs.clock_id` for a unit
and `core.event_streams.clock_id` for a stream.

### 2.5 `within_observation` checks the inherited window

`core.events.within_observation` and `core.spike_events.within_observation` remain `warning` and
keep their guard — a subject with no window anywhere is not checked. Where a subject has its own
intervals they are checked against those; otherwise against its clock's.

Checking the inherited window is cheap and it is not vacuous: it is the recording's extent, not
the data's, so a tick outside it is a real defect rather than a tautology. It also removes a
false positive the declared-window form produces. On `ecephys_776259_2025-04-09` the last spike
falls **0.88 s after** the acquisition window `session.json` declares, because that document
truncates to whole seconds; against the probe clock's own `[0, n_samples]` the same spike is
inside. The clock's window is the more correct one as well as the cheaper one.

## 3. What this does not do

- **No merge of units into event streams.** A unit emitting timestamped events on a clock is a
  Part 01-level likeness, not a Part 02-level one: unit identity is four columns and `core.spike_events`
  carries R30's measured layout over 287 M rows. Both remain their own resources.
- **No new requirement.** Declaring no observation anywhere stays legal and stays `info`, as
  R18 and R25 left it.
- **No change to the refinement tables' schemas**, beyond what §2.4 and §2.5 do to their rules.
- **No session-level extent.** R25 §4's rejection stands; this revision is the per-modality
  answer it pointed at, not a hull.
- **No zero.** Deriving a session time origin from these windows is R39.

## 4. Measured

On `ecephys_776259_2025-04-09`, one session, twelve probe clocks and HARP:

| | rows |
|---|---:|
| per-unit intervals, one window each | 6,781 |
| per-stream intervals, one window each | 10 |
| **per-clock intervals under this revision** | **13** |

The probe clocks' windows need no metadata: `core.clocks.origin` already reads *"sample 0 of
experiment1 on Neuropix-PXI-100.45883-1"*, so `start_tick` is 0 and `stop_tick` is the recording
length. HARP's window is the span of the barcode train that defines HARP time on this rig, which
is HARP-native and needs no wall clock either. No window in this packet requires a conversion to
write.

The recording length survives into the sorted asset: SpikeInterface records the sorted
recording's attributes as `recording_info` beside the sorting, so a packet built from a sorting
plus a sync tree needs neither the compressed AP data nor a metadata document that rounds to
whole seconds. Measured across the twelve probe clocks, the last spike falls 4 to 14 samples
inside its clock's window — one waveform's half-width, which is what a sorter that cannot centre
a template at the very end leaves.

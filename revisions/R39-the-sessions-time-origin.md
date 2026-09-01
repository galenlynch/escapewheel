# R39 — The Session's Time Origin

| | |
|---|---|
| **Status** | **Accepted** 2026-08-31 |
| **Amends** | R6 §3 (what `tick_zero_utc` is for), R25 §5 (what locates a session in time) |
| **Depends on** | R38 (observation belongs to the clock), R37 (error-bounded alignment), R27 §2 (reference clock) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Every consumer works in seconds. `pl_inputs_analysis` takes windows, bin widths and PSTH ranges
in seconds; `align_to_events` takes a window in seconds. A packet stores integer ticks and says
nothing about what second zero is, so each consumer picks one, and the arithmetic that follows
is silently relative to that choice.

**The obvious candidate is circular.** `core.sessions.session_start_time` converted through
`core.clocks.tick_zero_utc` returns tick 361,746,131,857 on this packet — **exactly the first
spike**, to 0.00 s. It must: `tick_zero_utc` was derived by pairing the ephys stream's declared
start with the first spike, and `session_start_time` is that same stream start. Second zero
would mean "the first spike in the session", which nothing declares and no one would guess.

**And it would move without anything changing shape.** Anchoring the epoch on the first trial
instead — which an earlier inventory note did — shifts every second in the packet by **163.64 s**,
with no file differing. The first behaviour event is a third candidate, 166.31 s away.

**Two facts about a clock were being conflated.** `tick_zero_utc` locates a counter's zero: here
2024-11-27, 134 days before the session, because HARP free-runs from power-on. When observation
*began* is a different fact entirely, and R38 gives it a home. Separating them is what makes an
origin definable without circularity — and without any wall clock, since R38's windows are in
each clock's own ticks and R27 guarantees every clock reaches the reference.

## 2. Decision

### 2.1 The origin is the earliest observation

A session's time origin is the earliest `start_tick` among its clocks' observation intervals
(R38 §2.1), expressed on the session's `reference_clock_id` (R27 §2).

It is the earliest across **all** clocks, with no modality preferred. Which device begins first
is a property of a rig on a day: on this session ephys precedes HARP by 0.78 s, and a rig whose
behaviour acquisition opens first must get a behaviour-anchored origin from the same rule.

### 2.2 It is declared, not inferred

`core.sessions` gains `t_zero_tick` (int64, optional, `since: R39`), on the reference clock.

A writer computing it MUST take the minimum defined in §2.1. Declaring it rather than leaving
every reader to recompute it is deliberate: it survives amendment (R32) unchanged, it is visible
in one place when it changes, and a reader need not know which resources carry windows.

A packet that declares no observation intervals declares no `t_zero_tick`.

### 2.3 Seconds are defined from it, or not at all

Where `t_zero_tick` is present, the seconds of a tick on the reference clock are

```text
seconds = (t_tick - t_zero_tick) / reference_tick_rate
```

using the reference clock's rational rate (`tick_rate_num`/`tick_rate_den`) in preference to
`tick_rate_hz`, which is already rounded.

A consumer asked for seconds by a packet that declares no `t_zero_tick` MUST refuse rather than
substitute an origin of its own. Tick zero, the session's wall-clock start and the first datum
are all available and all wrong, and a consumer that picks one silently produces numbers that
cannot be compared with another consumer's.

**Seconds may be negative.** Data outside its own observation window is a real and reported
condition (R38 §2.5), not an impossibility, and the origin is not clamped to hide it.

### 2.4 The check belongs to the shim

That `t_zero_tick` equals §2.1's minimum cannot be written in SQL: the minimum is taken across
clocks, and converting a clock's `start_tick` to the reference is R13's anchor-based mapping,
which is arithmetic no query expresses. R12 §4 settles where such a check lives — *"SQL for what
the data says; the shim for how it is stored"* — and this is the shim's kind of question, for
the same reason physical ordering is.

The conversion in §2.1 is subject to R37: a window's `start_tick` is by construction the
earliest tick of its clock, which is the least-anchored place on it, and where R37's bound
leaves the mapping undefined the origin is undefined with it. A writer that cannot convert one
of its clocks' window starts MUST NOT declare `t_zero_tick`.

## 3. What this does not do

- **No change to what is stored.** Ticks remain canonical and integer; seconds remain derived.
  This revision says what they are derived *from*, not that anything stores them.
- **No withdrawal of `tick_zero_utc`.** It stays optional and stays what R6 made it: the binding
  between a counter's zero and wall clock, for answering wall-clock questions. It is not the
  origin and is not needed to compute one.
- **No withdrawal of `session_start_time` or `session_end_time`.** They remain the wall-clock
  extent R25 §5 defines, for the wall-clock questions R25 §4 says a session extent is actually
  asked for.
- **No requirement to declare an origin.** A packet without one is conforming; its consumers
  work in ticks.

## 4. Measured

On `ecephys_776259_2025-04-09`, reference clock `harp` at 31,250 Hz:

| candidate origin | tick | offset from the declared start |
|---|---:|---:|
| `session_start_time` through `tick_zero_utc` | 361,746,131,857 | 0.00 s |
| first spike | 361,746,131,857 | 0.00 s |
| first trial start | 361,751,245,672 | +163.64 s |
| first behaviour event | 361,751,328,953 | +166.31 s |

Under §2.1 the origin is the earliest clock observation start: a probe clock's tick 0, which
maps to **361,746,131,857**. HARP's own window, the barcode span, begins 0.78 s later.

The value is the same as the circular derivation gives. That is the point: the number was never
wrong, only unjustified, and it now follows from what the packet declares rather than from which
datum an importer happened to pair with a JSON timestamp.

# R45 — A Tick Interval Is Closed

| | |
|---|---|
| **Status** | **Accepted** 2026-09-02 |
| **Amends** | R38 §2.3, §4 (a clock's own interval); `02_core_logical_schemas.md` §`core.trials` (`stop_tick`); R25 §7 (the deferred question) |
| **Depends on** | R18 (unit observation intervals), R24 (the `interval` template), R25 (event stream support), R38 (observation belongs to the clock), R39 (the session's time origin) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Four tables carry a `start_tick` and a `stop_tick`. Three of them say the interval is closed and
one says nothing, and **R38 contradicts itself in prose** about the table it introduced.

R38 §2.2 defines the column:

> | `stop_tick` | int64 | yes | **Last tick observed**, on `clock_id` itself. |

R38 §2.3 then describes what a writer puts there:

> for a sample clock whose `origin` is sample 0 of a recording, `start_tick` is 0 by construction
> and `stop_tick` is **the recording's length**

and §4 repeats it. Those cannot both hold. A recording of *n* samples has indices 0 to *n*−1, so
the last tick observed is *n*−1 and the recording's length is one greater. One statement is
normative and the other is the one an implementer reads while writing the code.

**Nothing is broken, and that is the point.** Everything that had to choose chose *closed*:

| | |
|---|---|
| `core.unit_observation_intervals` | *"First tick, inclusive"* / *"Last tick, inclusive"* |
| `core.clock_observation_intervals` | *"First tick observed"* / *"Last tick observed"* |
| `core.event_stream_observation_intervals` | *"First observed tick"* / *"Last observed tick"* |
| all three, R24 overlap rule | `overlap_op` is `<=`, so a start must **exceed** the previous stop |
| the writer | `sources/sorter.py` writes `length - 1` |

So the defect is one sentence written twice, and the cost of leaving it is that the next
implementer writes `stop_tick = length` and is one tick long on every denominator. Small — one
tick in 191,632,977 on the session this was measured against, about 5 × 10⁻⁹ — and invisible
until an interval is short, which is exactly when someone reaches for a recording gap.

**`core.trials` is the real gap.** Its `stop_tick` is described only as *"Trial stop tick"*, and
R25 §7 saw this and deferred it:

> Nothing about trial closure. `core.trials` still declares no `partition_of` and still gets no
> overlap test; whether its `stop_tick` is inclusive **remains a question for `02`**.

A consumer counting events in a trial has to choose `<` or `<=` and the packet does not say
which. On the session this was measured against **no event lands on a boundary tick at all**, so
the convention is not recoverable from the data — it has to be declared or it is guessed.

## 2. Decision

### 2.1 Every tick interval is closed

> A pair of columns naming a tick interval — `start_tick` and `stop_tick`, or a prefixed form of
> them — denotes the **closed** set of ticks from `start_tick` to `stop_tick`. Both ends are
> members. A writer MUST NOT emit a `stop_tick` one past the last tick the interval covers, and
> a consumer MUST NOT treat one as excluded.

Stated once, for every such table present and future, rather than per column. Three of the four
already comply and the fourth states nothing, so this makes explicit what the registry enforces.

### 2.2 The length of an interval

> An interval covers `stop_tick - start_tick + 1` ticks. A one-tick interval has
> `start_tick == stop_tick` and covers one tick, not zero.

Written down because it is the arithmetic the closure decides, and because a duration is what
almost every use of these tables is for: R38 §1's whole argument is that a rate needs a
denominator.

### 2.3 R38's two sentences

**Strike** from R38 §2.3:

> and `stop_tick` is the recording's length

**Replace with:**

> and `stop_tick` is the last sample's index, one less than the recording's length

**Strike** from R38 §4:

> so `start_tick` is 0 and `stop_tick` is the recording length

**Replace with:**

> so `start_tick` is 0 and `stop_tick` is the recording length minus one

R38 §2.2's column definition is unchanged and was correct throughout.

### 2.4 `core.trials.stop_tick`

**Replace** `02`'s description of `core.trials.stop_tick`:

> | `stop_tick` | int64 | yes | Last tick of the trial, inclusive, on `clock_id`. |

and `start_tick` correspondingly as *"First tick of the trial, inclusive"*. This settles R25 §7's
deferral in favour of the convention every other interval table already uses.

**No overlap rule is added.** R25 §7's other observation stands: `core.trials` declares no
`partition_of` and gets no overlap test, because trials need not partition a session and in some
paradigms may nest or overlap by design. §2.1 says what a trial's ticks *mean*; it does not say
that two trials may not share one.

### 2.5 A tick is a coordinate, and R3 §6 does not cover it

R3 §6 already pinned the base of every column called an index, and did it as a cross-language
decision rather than a host-language one:

> **Structural indices** address positions in a stored resource. These MUST be 0-based offsets.
> Clients converting to 1-based languages MUST convert at the boundary.
>
> **Source labels** are integers copied verbatim from acquisition or sorting software. Their base
> is whatever that software used [...] and MUST NOT be used as offsets into any packet resource.

Nothing here reopens that. It is the same call R3 §5 makes for axis order — the format picks one
and clients adapt — and it is the right one, because an offset that changes base per reader is
not an offset.

**A tick is neither category**, and that is why R38's prose could drift without contradicting
anything. A sample tick is copied verbatim from acquisition, like a source label, but is used
arithmetically, which R3 §6 forbids a source label. And it addresses nothing in a packet
resource, so it is not a structural index. It is a **coordinate**: a point on a clock's axis
whose zero is declared, not chosen.

> A tick is a coordinate on its clock. Its zero is where `core.clocks.origin` says it is — for a
> sample clock whose origin is sample 0 of a recording, tick 0 **is** that sample. A writer MUST
> NOT re-base a source's sample index, and a reader MUST NOT assume any base beyond what `origin`
> declares.

The prohibition is what makes a tick exact. Adding one so the first sample is "tick 1" would mean
the packet's ticks no longer match the recording they came from, and every comparison against the
raw acquisition would be off by one — a cost paid at every boundary, to spare 1-based clients a
single subtraction they must already perform for `axis_index`. It also keeps R39 §2.3's
`(t_tick - t_zero_tick) / rate` free of a correction term, since a coordinate difference is
base-free either way.

## 3. Evidence

`/mnt/Data/escapewheel/packets/r40-full`, 708 trials, 5,485 events:

| | |
|---|---|
| trials whose `start_tick` equals the previous `stop_tick` | **0** |
| smallest gap between consecutive trials | **5,407 ticks** (~0.17 s) |
| events landing exactly on a `start_tick` or `stop_tick` | **0** |

So §2.4 costs nothing: no trial becomes an overlap under the closed reading, and no event changes
which trial it falls in. The third row is the argument for declaring it — the data cannot settle
the boundary, so silence leaves every consumer to guess and they will not all guess alike.

Probe clocks, same packet: `start_tick` 0 and `stop_tick` 191,632,976 for a recording of
191,632,977 samples. The writer's `length - 1` is the closed reading, and R38 §2.3's prose
describes the other one.

## 4. What this does not do

- **No change to any stored value.** Every packet already written is conforming and unchanged;
  this states the convention those values were written under.
- **No overlap test for `core.trials`.** §2.4.
- **No change to the observation tables' columns.** R18 §2 and R38 §2.2 already say *inclusive*
  and stay as they are; §2.1 generalises them rather than restating them.
- **No new column and no new rule.** The `interval` template's `overlap_op` already encodes the
  closure per table, and all three declaring one declare `<=`.

## 5. Open

- **Whether `overlap_op` should stop being a parameter.** With §2.1 fixing the closure globally,
  a table that passes `<` would be declaring an exclusive interval the specification no longer
  permits. Removing the knob would make §2.1 checkable in `registry/check.py` rather than
  observed. Left alone here because nothing passes `<` today and R24's template is not otherwise
  in question.
- **R3 §6's taxonomy has fallen behind, and this revision only widens the gap.** It classifies
  columns into structural indices and source labels, listing three of each. Three columns added
  since fit neither: `core.clock_anchors.anchor_index` (R13) and the three
  `*_observation_intervals.interval_index` (R18, R25, R38) are **ordering keys** — contiguous
  from 0 and checked to be, but addressing no position in any stored resource — and
  `core.unit_electrodes.channel_ordinal` (R28) is structural by the registry's own rule message
  yet postdates the list. §2.5 adds a fourth kind, the coordinate. A revision that re-states
  R3 §6 over the tables as they now stand would settle all of them at once; this one deliberately
  does not, because the question it was raised to answer is closure and not classification.
- **Whether `core.trials` should gain a closure rule of its own.** §2.4 declines the overlap
  test, but *`stop_tick` precedes `start_tick`* is already caught by the `interval` template's
  `interval_valid`, which `core.trials` does invoke. Nothing further seems needed; naming it here
  so a later reader does not have to re-derive that it was considered.

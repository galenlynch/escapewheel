# R27 — Clock Graph Integrity and Bounded Extrapolation

| | |
|---|---|
| **Status** | **Accepted** 2026-08-28 |
| **Amends** | `02_core_logical_schemas.md` (`core.sessions`), R13 §3, R6 §2 (derived `tick_zero_utc`) |
| **Depends on** | R3 (typed clock transform), R6 (wall-clock binding), R13 (anchor-point alignment) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R13 gave a clock a parent and a way to align to it. Nothing since has required that the
resulting graph be usable. A packet may declare a cycle. It may declare clocks that reach no
common reference. Where the graph is sound, R13 forbids the one operation that real recording
boundaries need. And nothing says what to do when a clock's counter resets mid-session, which
on a free-running device is not an anomaly but a thing that happens.

Every one is reachable on the data the specification targets. A Neuropixels rig aligns
`probe → nidaq → harp`: the probes observe a shared sync pulse the NI-DAQ also records, while
only the NI-DAQ decodes the time-carrying HARP signal. Two levels, twelve leaves, one root. A
one-level tree hides all four defects; this one does not. The HARP clock at the root
free-runs from device power-on, and sessions exist where it resets as the task begins.

They matter more because a reader's default is to return synchronized data. That makes the
clock graph load-bearing rather than advisory: a packet whose graph is unusable fails the
primary read path, not a corner of it.

### 1.1 What the ignored alignment costs

Measured on one three-probe session against its 1 Hz sync line, 311 s:

| stream | samples/pulse | error vs nominal 30 kHz | max deviation from a straight line |
|---|---|---|---|
| probe A | 29999.5695 | −14.4 ppm | 0.96 samples |
| probe B | 29999.5705 | −14.3 ppm | 0.77 samples |
| probe C | 29999.6509 | −11.6 ppm | 1.07 samples |
| NI-DAQ | 30002.7114 | +90.4 ppm | 0.52 samples |

Taking the nominal rate and never consulting the sync line diverges by ~20 ms probe-to-probe
and ~750 ms probe-to-NI-DAQ over a two-hour session. Both are silently wrong answers rather
than failures, which is what makes the graph's integrity a validation concern.

## 2. New column: `core.sessions.reference_clock_id`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `reference_clock_id` | string | no | The clock this session's times are reported on by default. |

References: `reference_clock_id` -> `core.clocks.clock_id`.

A session SHOULD declare it. A session declaring more than one clock MUST declare it,
because "synchronized" otherwise names no clock: a graph with two unparented clocks has two
roots and nothing chooses between them.

The reference clock SHOULD be the one with the widest observation window, which is what makes
the choice more than a convention. Streams native to it need no conversion and are
representable wherever they occur; streams below it convert. Choosing a probe clock as the
reference on a rig whose behaviour outlasts its ephys would make the behaviour outside the
ephys window unrepresentable, while choosing the rig clock costs nothing.

```sql
-- core.sessions.reference_clock_declared  (error)
-- More than one clock and no reference: "synchronized" names nothing.
SELECT s.session_id, COUNT(*) AS n_clocks
FROM core_sessions s JOIN core_clocks c USING (session_id)
WHERE s.reference_clock_id IS NULL
GROUP BY s.session_id HAVING COUNT(*) > 1
```

```sql
-- core.sessions.every_clock_reaches_the_reference  (error)
-- A clock that does not reach the reference cannot be converted to it.
WITH RECURSIVE up(clock_id, ancestor, depth) AS (
  SELECT clock_id, clock_id, 0 FROM core_clocks
  UNION ALL
  SELECT u.clock_id, c.parent_clock_id, u.depth + 1
  FROM up u JOIN core_clocks c ON c.clock_id = u.ancestor
  WHERE c.parent_clock_id IS NOT NULL AND u.depth < 64)
SELECT c.session_id, c.clock_id
FROM core_clocks c JOIN core_sessions s USING (session_id)
WHERE s.reference_clock_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM up u
                  WHERE u.clock_id = c.clock_id AND u.ancestor = s.reference_clock_id)
```

## 3. The parent chain MUST be well-founded

`core.clocks.parent_clock_id` references `core.clocks.clock_id`, and no rule requires the
chain to terminate. R13's `requires_parent` and R3's `transform_requires_parent` both check
only that a parent *exists*. So `A parent B, B parent A` validates clean today, and a
consumer walking the chain to convert a tick does not terminate.

A clock MUST NOT be its own ancestor.

```sql
-- core.clocks.parent_chain_well_founded  (error)
-- A cycle validates under every existing rule and hangs any consumer that walks it.
WITH RECURSIVE up(clock_id, ancestor, depth) AS (
  SELECT clock_id, parent_clock_id, 1 FROM core_clocks WHERE parent_clock_id IS NOT NULL
  UNION ALL
  SELECT u.clock_id, c.parent_clock_id, u.depth + 1
  FROM up u JOIN core_clocks c ON c.clock_id = u.ancestor
  WHERE c.parent_clock_id IS NOT NULL AND u.depth < 64)
SELECT DISTINCT clock_id FROM up WHERE ancestor = clock_id OR depth >= 64
```

The depth guard is not a limit on legitimate nesting — a rig topology is two or three levels
— but the termination condition for a cycle that does not pass back through the clock the
walk started from.

## 4. Alignment MUST exist where conversion is expected

R13 §4 admits a clock with a parent and no measured alignment: *"parentage known, alignment
not measured."* That state stays legal in general, and becomes a defect once a session
declares a reference clock, because every non-reference clock must then be convertible.

```sql
-- core.clocks.alignment_declared_for_conversion  (error)
SELECT c.clock_id FROM core_clocks c JOIN core_sessions s USING (session_id)
WHERE s.reference_clock_id IS NOT NULL
  AND c.clock_id <> s.reference_clock_id
  AND c.transform_slope IS NULL
  AND NOT EXISTS (SELECT 1 FROM core_clock_anchors a WHERE a.clock_id = c.clock_id)
```

## 5. Bounded extrapolation

R13 §3 states:

> Between consecutive anchors the mapping is **linear interpolation**; outside the first and
> last anchor it is **undefined**, and a consumer MUST NOT extrapolate.

**This revision replaces that sentence.**

### 5.1 Why the current rule is wrong in both directions

It forbids a safe operation and permits an unsafe one, because it keys on *bracketing* when
what predicts error is *distance to the nearest anchor*.

A free-running sync pulse means acquisition starts at a random phase against it, so the
unanchored region at each end is bounded by one pulse period by construction. Measured on
four streams against a 1 Hz line: 0.784–0.797 s before the first pulse, 0.293–0.313 s after
the last. Under R13 that is real recorded data with no defined time — systematically at the
session boundaries, where task onset and offset live.

Meanwhile a 300 s hole in the pulse train is "inside" the anchor span, so R13 permits
interpolation straight across it, unaudited.

### 5.2 The error is a property of the slope, not of extrapolating

Measured by holding out terminal anchors and predicting them, four streams, errors in probe
samples at 30 kHz (1 sample = 33.3 µs):

| distance beyond the last anchor | rate fitted over the full sequence | terminal segment's slope |
|---|---|---|
| 1 s | 6–18 µs | 0–33 µs |
| 5 s | 17–27 µs | 33–133 µs |
| 20 s | 18–36 µs | 233–500 µs |
| 60 s | 18–46 µs | 566–866 µs |

A globally fitted rate stays under 1.4 samples at a full minute. The terminal segment's slope
— which is what piecewise-linear interpolation extends by default — is estimated from two
anchors and degrades linearly, reaching ~0.9 ms. R13's ban was a correct response to the
right-hand column and an unnecessary one for the left.

At the distance that actually occurs, under one anchor interval, extrapolation with a fitted
rate costs **less than the probe's own sample period**. It introduces less error than the
quantization already present in the data it recovers.

### 5.3 The replacement rule

Let *m* be the median interval between consecutive anchors of a clock, in ticks on that
clock.

- Between two anchors separated by at most 2*m*, the mapping is linear interpolation on the
  bracketing pair.
- Beyond the terminal anchors it is defined out to *m*, and a consumer computing it MUST use
  the rate fitted over the clock's full anchor sequence. A consumer MUST NOT extend the
  terminal segment's slope.
- Anywhere further than *m* from every anchor — past the ends, or inside a gap wider than
  2*m* — the mapping is **undefined**, and a consumer MUST NOT extrapolate.
- The bound applies per edge of the chain. A two-level topology is evaluated at each edge
  against that edge's own *m*, so an edge anchored at 1 Hz and one anchored every 30 s each
  get a bound proportional to their own anchor density.

Expressing the bound as a multiple of the observed anchor interval rather than as a declared
duration is deliberate: it needs no new column, and it scales automatically with an edge's
anchor rate. It also makes the two clauses one idea — the mapping is defined within one
anchor interval of an observed anchor, whichever side.

A consumer MUST report ticks it cannot map rather than omitting them, so that a converted
table has the same row count as its source with nulls where the mapping is undefined.

```sql
-- core.clock_anchors.gap_within_bound  (warning)
-- A gap wider than twice the median leaves ticks inside the anchor span that the mapping
-- does not define. The span alone does not reveal this.
WITH gaps AS (
  SELECT clock_id, anchor_index,
         t_tick - LAG(t_tick) OVER (PARTITION BY clock_id ORDER BY anchor_index) AS gap
  FROM core_clock_anchors),
typical AS (
  SELECT clock_id, median(gap) AS m FROM gaps WHERE gap IS NOT NULL GROUP BY clock_id)
SELECT g.clock_id, g.anchor_index, g.gap, t.m
FROM gaps g JOIN typical t USING (clock_id)
WHERE g.gap IS NOT NULL AND g.gap > t.m * 2
```

## 6. A clock reset is a new clock

A free-running counter can reset mid-session — a device power-cycles, or the task controller
resets it as it starts. Observed on real sessions of the data this specification targets, at
task start, which is the worst place for it: everything scientifically interesting is on the
far side.

The identity of a free-running clock is its epoch. R6 defines `tick_zero_utc` as *the*
wall-clock instant of tick 0, one value per clock, and a counter with two epochs has no such
value. So the reset is not a defect in a clock; it is the boundary between two of them.

A counter that resets during a session MUST be represented as two clocks, one per epoch, each
with its own `clock_id`, `origin` and `tick_zero_utc`. Every tick-bearing row MUST carry the
`clock_id` of the epoch it was recorded on. The two SHOULD share a parent, which is what makes
a query spanning the reset expressible: both convert to the reference and are comparable
there, while the raw ticks are not.

A packet MUST NOT represent a reset as a discontinuity within one clock. There is no way to
express it and no way to read it: `core.clock_anchors` requires both sequences to increase
together (R13 §3), and a bare tick would not say which epoch it belongs to — the same integer
occurs twice in one session with two different meanings.

### 6.1 Detection belongs to the importer

The reset is invisible in a committed packet. A table is sorted by tick on write (R10 §2), so
the backward step that reveals it is gone before any rule runs. This is R12 §4's division
exactly — SQL for what the data says, the shim for how it was stored — and a reset is a fact
about the source's native order.

An importer MUST examine the source in acquisition order and MUST NOT assume monotonicity.

Two existing rules act as backstops where an importer misses it. R13's
`core.clock_anchors.monotonic` fires if both epochs' anchors are placed on one clock. §2's
`every_clock_reaches_the_reference` fires if the second epoch gets a clock but no parent. Both
report a symptom rather than the cause, which is why neither replaces the import-time check.

### 6.2 A derived `tick_zero_utc` MUST be anchored within one epoch

Where `tick_zero_utc` is derived rather than declared, the tick it is anchored on MUST lie in
the same epoch as the instant it is paired with.

The failure is quiet and total. Deriving an epoch from the earliest tick in a session is
natural and, on a rig that resets at task start, wrong: the earliest tick is pre-reset, the
declared instant it is matched against is post-reset, and the derived `tick_zero_utc` is wrong
for every row after the reset. Nothing in the packet then disagrees with anything else.

The check is the one that validates any derived epoch — a window declared in wall clock,
placed on the resulting clock, must contain the events observed in that window. An epoch
derived across a reset fails it by the size of the reset.

## 7. What this does not do

- **No new table.** The ledger stays at 30 (R25 §6); `core.sessions` gains one column.
- **No interpolation kind.** R13 §5's exclusion of splines and drift models stands. This
  revision bounds where linear interpolation applies, and does not add a second rule.
- **No declared extrapolation limit.** A per-clock column was considered and rejected: the
  median anchor interval already carries the information, and a declared limit could disagree
  with the anchors it governs.
- **No reset-detection rule.** §6 fixes how a reset is represented, which is a packet-level
  question. Noticing one is not: it lives in the source's native order, so it is an
  import-time check (§6.1), and no rule added here looks for it.
- **No link between the two clocks a reset creates.** Nothing records that `harp_pre` and
  `harp_post` are the same physical device before and after. See §9.
- **Nothing about which clock ticks are stored on.** Whether `core.spike_events` carries a
  probe's own sample index or a reference-clock tick is a writer's choice, unchanged here.
  This revision only requires that whatever is stored can be converted.

## 8. Consequences for the registry

- `core.sessions` gains `reference_clock_id` (nullable string) and one reference.
- Five Tier 2 rules are added: `reference_clock_declared`,
  `every_clock_reaches_the_reference`, `parent_chain_well_founded`,
  `alignment_declared_for_conversion`, `gap_within_bound`.
- Four are `error`; `gap_within_bound` is `warning`. None is advisory (R26): each reports a
  packet whose primary read path is compromised, which is not an enable-if-you-want finding.
- Two rules use a recursive CTE, which is new in the registry. `registry/check.py`'s
  empty-table execution covers them, and the corpus needs variants that actually trip them —
  a cycle, an unreachable clock, and an oversized gap — because an empty table proves a rule
  binds, not that it can report.
- All five were executed while drafting, against a clean `probe → nidaq → harp` topology and
  against each defect in turn: every rule returns no rows on the clean case and rows on its
  own. That is the execution contract (R2 §7), not a substitute for the corpus variants.
- **§6 adds no rule and no column.** A reset is represented with `core.clocks` as it already
  stands — one row per epoch — so the registry change is nil and the burden falls on the
  importer. The corpus should still gain a two-epoch packet, because nothing today exercises
  a session whose rows are split across two clocks with the same parent.

## 9. Open

- **Where the measurements live.** §1.1 and §5.2 were measured against a local Open Ephys
  session and are not reproducible from this repository. They belong in
  `conformance/clock-probe/` beside the Zarr and Parquet probes, run against a raw asset, so
  the thresholds here can be rechecked against other rigs. The multiple in §5.3 rests on
  them.
- **Whether 2*m* is the right gap threshold.** It follows from stating the bound once and
  applying it symmetrically, which is its main justification. A rig with deliberately
  irregular anchors would trip it without being defective, and only more rigs will say
  whether that case is real.
- **Whether a single-clock session should declare a reference.** MUST above applies only to
  multi-clock sessions, since one clock is unambiguous. Requiring it always would make the
  column uniformly present and the reader's default uniform, at the cost of a redundant
  field on the common case.
- **Whether the two clocks a reset creates should be linked.** §6 makes them independent, and
  nothing records that they are one physical device before and after. That is enough to read
  the packet, and not enough to answer "how many clocks did this rig have" or to warn that a
  session reset twice. `core.clocks.metadata` could carry it without a schema change; a typed
  column would need one, and neither is worth adding before a query wants it.
- **Whether a reset should be reported at all.** It is a fact about the recording that
  survives nowhere in the packet once represented correctly: two clocks with unrelated epochs
  look the same as two independent devices. A `docs/` note is the current answer, which is to
  say there is none.

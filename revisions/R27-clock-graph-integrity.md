# R27 — Clock Graph Integrity and Bounded Extrapolation

| | |
|---|---|
| **Status** | **Proposed** 2026-08-28 |
| **Amends** | `02_core_logical_schemas.md` (`core.sessions`), R13 §3 |
| **Depends on** | R3 (typed clock transform), R6 (wall-clock binding), R13 (anchor-point alignment) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R13 gave a clock a parent and a way to align to it. Nothing since has required that the
resulting graph be usable: a packet may declare a cycle, may declare clocks that reach no
common reference, and — where the graph is sound — R13 forbids the one operation that real
recording boundaries need.

Each gap is reachable on the data the specification targets. A Neuropixels rig aligns
`probe → nidaq → harp`: the probes observe a shared sync pulse the NI-DAQ also records,
while only the NI-DAQ decodes the time-carrying HARP signal. Two levels, twelve leaves, one
root. A one-level tree hides all three defects; this one does not.

The gaps matter more because a reader's default is to return synchronized data. That makes
the clock graph load-bearing rather than advisory: a packet whose graph is unusable fails the
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

## 6. What this does not do

- **No new table.** The ledger stays at 30 (R25 §6); `core.sessions` gains one column.
- **No interpolation kind.** R13 §5's exclusion of splines and drift models stands. This
  revision bounds where linear interpolation applies, and does not add a second rule.
- **No declared extrapolation limit.** A per-clock column was considered and rejected: the
  median anchor interval already carries the information, and a declared limit could disagree
  with the anchors it governs.
- **No detection of a clock reset.** A free-running counter that power-cycles mid-session
  sends time backwards, and no SQL rule can see it: a packet is sorted by tick on write, so
  the discontinuity is gone before the rules run. Detecting it means checking the source's
  native order at import, which is the shim's half of R12 §4, not this revision's.
- **Nothing about which clock ticks are stored on.** Whether `core.spike_events` carries a
  probe's own sample index or a reference-clock tick is a writer's choice, unchanged here.
  This revision only requires that whatever is stored can be converted.

## 7. Consequences for the registry

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

## 8. Open

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

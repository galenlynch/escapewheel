# R43 — An Alignment Is a Query, Not a Table

| | |
|---|---|
| **Status** | **Accepted** 2026-09-01 |
| **Amends** | `06_analysis_layer.md` §46 (`analysis.spikes_by_trial`), §73 (`analysis.trials_wide`), §117 (`analysis.unit_condition_rates`), §186 ("Views versus materialized products"); `07_reference_api_and_implementation_plan.md` §217 (Phase 4) |
| **Depends on** | R3 (no nested Parquet types), R5 (flat spikes), R13/R27/R37 (anchor-point alignment), R17 (extension registries), R30 (`analysis.spike_events` purpose and layout) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

Part 07 Phase 4 names three analysis resources. R30 built one and, in §7, deferred the next:

> `analysis.spikes_by_trial` in particular has the same problem in a milder form: it says
> spikes carry `t_abs_tick` and `t_rel_tick` without saying which clock either is on. That
> wants its own revision once something builds it.

Something tried. **The answer is that nothing should build it**, and the clock ambiguity R30
noticed is the smallest of three reasons. Phase 4's success criterion — "run a simple PSTH-like
query from packet data" — is met without either remaining table, three separate ways, all
verified bin-for-bin identical.

Part 06 chose these tables before anything measured them, and says so: they are "recommended
initial analysis resources" with "suggested" schemas. This revision records what the
measurement says, so that a later implementer does not read their absence as an oversight.

## 2. `analysis.spikes_by_trial` is withdrawn

**Strike Part 06 §46 in its entirety.** A packet MUST NOT be judged incomplete for lacking it, and
Part 07 Phase 4 no longer requires it (§5). A writer MAY still materialize such a table as a
private resource under an R17 extension namespace; it is not a core-adjacent recommendation.

Three arguments, in descending strength.

### 2.1 It is a table per query

Part 06 requires the materialization parameters to fix an **alignment event** and an **inclusion
window**. Those are the two things a question varies. So each `(event, window)` pair is a
separate table, and the tables do not compose: a copy built at ±0.5 s cannot answer a question
at ±1 s, and one built on the go cue cannot answer one on the lick.

Four alignments from a single real analysis:

| alignment event | events | window | rows | seconds |
|---|---:|---:|---:|---:|
| `go_cue` | 708 | ±0.50 s | 36,230,515 | 0.480 |
| `left_lick` | 2,641 | ±1.00 s | 224,024,539 | 1.724 |
| `reward_outcome` | 708 | ±0.25 s | 19,000,247 | 0.373 |
| `right_reward_delivery` | 46 | ±2.00 s | 9,295,691 | 0.126 |
| | | | **288,550,992** | **2.703** |

**288,550,992 rows is 100.6% of the entire spike table** — the packet's largest resource,
duplicated, to save 2.7 s of arithmetic against arrays already in memory.

The second row is the general case, not an outlier. Where events are spaced closer than the
window is wide, the windows overlap, and a correct copy must **repeat** each spike once per
window it falls in. 2,641 licks at ±1 s expand 287 M spikes into 224 M rows — 78% of the spike
table for one question — and a wider window expands further without bound.

### 2.2 Part 06's own test puts it on the other side of the line

Part 06 §186 says: *view when the transformation is cheap, materialized table when expensive or
frequently reused.* It then lists "spike-to-trial assignment" and "event-aligned spike
expansion" as materialized — a judgement made without a number.

Measured, the assignment is two `searchsorted` calls per unit against sorted spike times:
**0.13 s to 1.72 s** for the whole population, depending on how many rows the window selects.
Reading and grouping the spikes costs 1.81 s once, and every subsequent alignment pays only the
column above. That is cheap by the document's own criterion.

**Strike** "spike-to-trial assignment" and "event-aligned spike expansion" from §186's
materialized list, and **add** to its view list:

> - aligning spikes to an event and a window.

### 2.3 The schema predates the revisions it would have to satisfy

Weakest of the three, and listed because it is a specification defect worth recording rather
than a reason on its own. One column of eleven cannot be written as specified, and one must
have its type narrowed:

- **`clock_id`** is one column, and after R13/R27 there are two clocks in a row. `t_abs_tick`
  is the spike's measured tick on its probe's clock; `t_rel_tick` is a difference on the
  reference clock, because the event and the spike are only comparable there. R30 §6 made the
  same point for `analysis.spike_events` and resolved it by carrying one clock and one tick.
  Here the table's purpose requires both, and one column cannot name them. This is exactly the
  defect R30 §7 predicted.
- **`metadata`** is typed `struct/map/json_string`. R3 §2.1 forbids nested Parquet types, which
  leaves only `json_string`, and only in an optional column — which this one is. The type must
  be narrowed to match `core.trials.metadata`.

`condition_id` is sound: `core.trials.condition_id` exists and is nullable, so copying it is
well defined.

## 3. `analysis.trials_wide` and `analysis.unit_condition_rates` are task-shaped

**Strike Part 06 §73 and §117**, and replace both with:

> A convenience trial table and a per-condition rate table are useful and are **not
> core-adjacent**. Their columns name a task's structure, which varies between experiments in
> ways no single column set survives. Publish them through an R17 extension registry,
> namespaced to the task family, where the column set can be closed against one paradigm and
> validated. Deriving one at read time is a view (§186).

Two separate objections, and the first disposes of the table on Part 06's own terms.

### 3.1 It is the cheapest thing in the document

`core.trials` is **708 rows** and `core.events` is 5,485. The whole of §73 — the interval and
identity columns joined to a pivot of the event types, plus the lagged previous-trial columns —
is one query returning 708 rows in **7.5 ms**. There is nothing to amortize. §186's materialized
list names "trial-wide event extraction"; measured, it is on the view side by three orders of
magnitude.

**Strike** "trial-wide event extraction" and "aggregate rates by condition" from §186's
materialized list.

### 3.2 The column set is not portable, so it should not be normative

What remains is whether Part 06 should recommend a *shape*. It should not, because the shape is a
task's and not a format's.

Measured against the session this was built on, a foraging task:

- `stimulus_id` is **null in all 708 rows**, and no stimulus event exists in `core.events` —
  the seven event types are `go_cue`, `delay_start`, `reward_outcome`, the two licks and the
  two reward deliveries. So `stimulus_on_tick` has nothing to derive from.
- There is no `block_id`. The task has blocks, but they live among 58 keys in the optional
  `metadata` JSON — `block_beta`, `block_min`, `block_max` — as parameters, not as an identity.
- The columns that do hold are `core.trials`'s own plus three event extractions, one of which
  (`response_tick`) is present for 499 of 708 trials because the rest have no lick.

And a second real source disagrees in the other direction.
`Aind.Behavior.VrForaging.Packaging`, the pipeline most behaviour data in this collection will
pass through, has **no go cue, no condition, and no trial** in §73's sense: its structure is
site → patch → block, with eleven index columns that Part 06 never contemplates.
`inventory/vr-foraging-packaging.md:104` reached the same conclusion for the site table
independently — *"everything task-shaped ... is an R17 extension, not core."*

Any column set that fits one misfits the other, and a union of both fits neither: it would be a
table of mostly-null columns whose meaning depends on which pipeline wrote it, which is the
shape Part 09's metadata minimalism exists to prevent.

`analysis.unit_condition_rates` inherits both objections. Its `condition_id` and `epoch_name`
are task-shaped for the same reason, and the aggregation is a `GROUP BY` over a table §2 has
already shown is queried in fractions of a second.

### 3.3 The resulting §186

§2.2 and §3.1 between them strike four of §186's five materialized entries. Stated as a
replacement rather than as four separate strikes, §186's two lists become:

> Use a view when the transformation is cheap:
>
> - selecting good units;
> - converting ticks to seconds for display;
> - selecting trials for one condition;
> - aligning spikes to an event and a window;
> - deriving a wide trial table from `core.trials` and `core.events`;
> - aggregating rates over a grouping.
>
> Use a materialized table when the transformation is expensive or frequently reused:
>
> - mapping spikes onto a common clock and laying them out for both a unit filter and a time
>   filter (R30);
> - feature extraction.

The array list (§202) is unchanged; those resources are dense by nature and Phase 5's concern.

That the "expensive" list is now nearly empty is the finding, not an accident of editing. **A
transformation over a well-laid-out columnar table is cheap**, and Part 06's original list was
written against an intuition formed on row stores and HDF5, where it would have been right.

## 4. What replaces them

Not a resource. A query against `analysis.spike_events`, which R30 already laid out so that
both a unit filter and a time filter prune.

Two spellings, both correct, on the same packet:

```sql
-- ASOF against the window start, then a bounded filter.
SELECT ...
FROM analysis_spike_events s
ASOF JOIN cues c ON s.t_tick >= c.t_tick - :half
WHERE s.t_tick <= c.t_tick + :half
```

```python
# Per-unit sorted trains, two searchsorted per unit.
lo = np.searchsorted(train, cue - half, "left")
hi = np.searchsorted(train, cue + half, "right")
```

Both are ordinary work a user writes unaided, which is why neither belongs to the format. Two
hazards do belong to a reader, and are named here because withdrawing the table is what exposes
them:

1. **A general two-inequality range join is 4.6x slower than the ASOF form** and returns the
   same rows — 22.658 s against 4.822 s for the whole population, with `EXPLAIN ANALYZE`
   attributing 22.01 s of the first to `IE_JOIN`. A reader SHOULD offer the alignment as a
   table macro so that the fast spelling is the default one.
2. **`analysis.spike_events` is bucketed by time (R30 §3.2), so one unit's spikes arrive as one
   run per bucket.** Concatenating those runs in file order yields a *non-monotonic* array, and
   `searchsorted` against it returns wrong answers with no error. A reader that returns per-unit
   trains MUST return them sorted.

Neither is a specification change. They are recorded because R43 removes the resource that
would have hidden them.

## 5. Part 07 Phase 4

**Replace** §217's implementation list with:

> - `analysis.spike_events` from `core.spike_events` and `core.clock_anchors` (R5, R30).

Part 06 §46 and §73 are withdrawn by §2 and §3 above, and Phase 4's success criterion is unchanged
and met.

The list also still names `core.unit_spike_chunks` as the source, a table **R5 withdrew**. That
is corrected here rather than left to the reader of a frozen document.

## 6. Evidence

`/mnt/Data/escapewheel/packets/r40-full` — 286,896,563 spikes, 6,781 units, 708 go cues, ±0.5 s
around the go cue, 51 bins of 20 ms. Every path verified to return an identical histogram.
Warm, seconds.

| path | one unit | 24 units | all 6,781 |
|---|---:|---:|---:|
| PyArrow + numpy trains | 0.074 | 0.976 | 2.286 |
| DuckDB, two-inequality range join | 0.127 | 1.950 | 22.658 |
| DuckDB, ASOF join | — | — | 4.822 |
| hand-built `spikes_by_trial` copy | 0.012 | 0.102 | 0.201 |

The numpy path is read 1.048 s + regroup into trains 0.765 s + align 0.473 s. The first 1.81 s
is paid once per session; §2.1's table is the align step alone, which is what a second question
against held trains costs.

**The materialized copy is genuinely faster — 6x to 11x on the question it was built for.**
That is the honest number and it is not the reason to decline it. The reason is §2.1: it
answers one question, costs a duplicate of the packet's largest table, and the query it
replaces already returns in 0.13 s for the unit-filtered case anyone actually runs interactively.

The copy itself: 36,230,515 rows for one alignment, 254.9 MB as written, ~18 s to build. A
build with `DELTA_BINARY_PACKED` on the ticks came to 148.5 MB, but differed in more than one
variable — PyArrow refuses `column_encoding` alongside `use_dictionary=True` — so the size of a
well-encoded copy is bounded at roughly 150–255 MB rather than measured.

§3.1's pivot, same packet, DuckDB, median of five warm runs: **708 rows in 0.0075 s** from 708
trials and 5,485 events. `stimulus_id` is null in all 708 rows; `go_cue` and `reward_outcome`
resolve for all 708; a lick resolves for 499.

Two measurement hazards found in the course of this, unrecorded anywhere and worth carrying
into the reader's own notes:

- **`read_dictionary` combined with `filters` costs 29x** — 1.05 s against 0.036 s for the same
  filtered read of one unit.
- **Arrow dictionary-*typed* columns defeat row-group pruning** through `pq.read_table(filters=)`:
  0.235 s against 0.002 s reading the same three row groups directly. Write plain string
  columns and let Parquet dictionary-*encode* them, which is what the writer already does.

Both silently penalise the query path against the materialized one, which is to say they
penalise the conclusion this revision reaches. They were corrected before the numbers above
were taken.

## 7. What this does not do

- **No change to `analysis.spike_events`.** R30 stands entirely; §4's queries are what its
  layout was measured for.
- **No change to `analysis.good_units`.** Part 06 §104 already offers it as a view, and §186
  already lists selecting good units on the view side. R16 and R22 make the quality policy the
  user's, which is the same argument arriving at the same place.
- **No change to `analysis.binned_spikes` or the array-shaped resources.** Those are Phase 5
  and are dense by nature; §2's row-multiplication argument does not reach them.
- **No prohibition on materializing an alignment.** A writer with one fixed question and a
  standing need MAY build the table under an extension namespace. What is withdrawn is the
  recommendation that a conforming packet carry one.

## 8. Open

- **Whether the alignment macro is normative.** §4 says a reader SHOULD offer it. That could
  instead be specified as a named table macro every profile-conforming DuckDB registration
  provides, which would make the fast spelling checkable rather than advisory.
- **Whether an R17 extension registry for a task family should be written now.** §3 sends
  `trials_wide` there without demonstrating that the extension mechanism carries it; the
  foraging and VR-foraging column sets are both available and would be the test.
- **Whether §4's per-unit sort requirement belongs in the shim.** It is a physical-order property of
  a *read*, not of a file, so R12's rule does not obviously reach it, and nothing else checks a
  reader's output.

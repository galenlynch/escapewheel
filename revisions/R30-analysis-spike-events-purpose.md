# R30 — What `analysis.spike_events` Is For, and How It Is Laid Out

| | |
|---|---|
| **Status** | **Accepted** 2026-08-28 |
| **Amends** | `06_analysis_layer.md` §23 (`analysis.spike_events`); `03_portable_physical_profile.md` §"Sorting" |
| **Depends on** | R5 (flat spike representation), R10 (default sort order), R12 (physical order is a shim check), R13 (anchor-point alignment), R27 (clock graph integrity) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`06` introduces the table like this:

> Long spike table derived from `core.unit_spike_chunks` when chunked spikes are canonical.

**R5 withdrew `core.unit_spike_chunks`.** `core.spike_events` became canonical, one row per
spike, all primitives — which is exactly the long flat table `06` described building. So the
table's stated derivation is from a table that no longer exists, to produce a shape core now
has. The schema survived R5 and the reason for it did not.

Meanwhile R27 created a need the analysis layer is the right home for. A packet's spikes are
on their probes' sample clocks, which is what makes them exact and what makes two probes
incomparable without conversion. A reader's default is to return times on the session's
reference clock, and doing that conversion on every read is work a writer can do once.

That much would justify a table with `06`'s schema and `03`'s ordering. Measurement says it
would not be worth writing. A copy that keeps core's order differs from core only by the
clock conversion, and conversion is measured at 29 M spikes a second — so the materialization
buys a few milliseconds on the queries anyone would run. What it can buy, and core cannot, is
a **layout**: a common clock is what makes ordering by time meaningful at all.

## 2. Replacement: purpose

**Strike** `06`'s sentence introducing `analysis.spike_events` and replace it with:

> Spikes on the session's reference clock (R27 §2), mapped from `core.spike_events` through
> `core.clock_anchors`, and laid out so that both a unit filter and a time filter prune.
> Its `clock_id` is the reference; `core.spike_events` keeps each spike's exact tick on the
> clock it was measured on.

## 3. Replacement: layout

`03` recommends one ordering for "`core.spike_events` or `analysis.spike_events`". **Strike
`analysis.spike_events` from that recommendation**; the order below governs it instead.
`core.spike_events` is unaffected.

### 3.1 The bucket column

The table gains one column:

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `time_bucket_tick` | int64 | yes | First tick of the bucket this spike falls in, on `clock_id`. |

It MUST be the same value for every row in a bucket, and buckets MUST partition the tick axis
into contiguous non-overlapping ranges — for two buckets of one `(session_id, clock_id)`, the
later bucket's smallest `t_tick` MUST exceed the earlier bucket's largest. That is what makes
the column mean anything, and it is checkable in SQL without knowing the bucket width.

The bucket width is a **transform parameter** and MUST be declared as `06` already requires,
not inferred. It is not recoverable from a table whose buckets are all non-empty only by
accident.

The column stores the bucket's first tick rather than a bucket number so that it is in the
same units as `t_tick`, comparable to it directly, and free of any question of what a bucket
number is counted from.

### 3.2 The order

```text
session_id, clock_id, time_bucket_tick, sorting_run_id, curation_id, unit_id, t_tick
```

This is R10 §2's "sort by the primary key unless overridden", overridden. A writer MUST emit
the table in this order; R12 §4 puts the check in the shim, because physical order is not
visible to SQL.

Below the bucket the key is `core.spike_events`'s own, unchanged. `curation_id` is part of it
even though nothing queries by it, because leaving it out would make a packet carrying two
curations of one sorting run violate its own declared order — core emits each curation's units
in turn, so unit order only holds within a curation. Keeping it also means a writer that visits
core in order and appends into buckets satisfies this order by construction, with nothing
sorted twice.

Ordering by time alone and ordering by unit alone are duals — each destroys the pruning the
other provides — and neither is worth a second copy of a table this size. Bucketing time and
sorting by unit within each bucket leaves **both** columns with informative row-group
statistics: a row group lies inside one bucket, so its `t_tick` range is narrow, and holds a
contiguous run of units, so its `unit_id` range is narrow too.

A writer SHOULD start a new row group at each bucket boundary. Row groups cut at a fixed row
count straddle boundaries, and a straddling group spans two buckets' worth of time — measured
at twice the intended width in the worst case, which is pruning given away for nothing.

### 3.3 What is not specified

Bucket width, row-group size and column encoding are **not** normative. `03` mandates nothing
about Parquet encodings and calls row-group size a starting point to "adjust after profiling",
and the right values depend on session length, unit count and firing rate. §6 records what was
measured; it is evidence for a default, not a rule.

## 4. Rows are not preserved

A spike whose tick falls outside the region where the mapping is defined (R27 §5.3) MUST be
omitted rather than given an extrapolated value. So this table MAY have fewer rows than
`core.spike_events`, and a consumer MUST NOT assume the two are row-aligned or that a count
from one applies to the other.

On the session this was built against, none were dropped: all 247,758,402 spikes fell within
one median anchor interval of an anchor. That is a property of a well-anchored recording and
not a guarantee — a session whose sync pulses start late will lose the spikes before them,
which is the honest outcome and the reason the omission is specified rather than left to a
writer.

## 5. It is still disposable

R30 does not make this table canonical, and `06`'s promotion rules are untouched. It is
derived, regenerable from `core.spike_events` and `core.clock_anchors`, and a packet without
it is complete. `06` already requires an analysis resource to declare lineage to core; for
this table that lineage is those two resources and `core.clocks`.

## 6. Why the analysis layer, and why core cannot do this

Because the value is derived, and because core has no common time axis to lay out against.

Putting reference-clock ticks in `core.spike_events` would mean either replacing the measured
tick — losing the only exact number in the table — or carrying both, which doubles the largest
table in a packet.

The layout argument is stronger, because it is not a trade-off. `core.spike_events` carries
each spike on the clock it was measured on: twelve clocks in the session this was built
against. A bucket over raw ticks is meaningful only within one clock, and R27 lets a counter
that resets mid-session become two clocks. A reference-clock bucket column in core would put a
derived, anchor-dependent value into the layer that holds measured facts, and make it
load-bearing for the file's physical order — so revising the anchors would silently invalidate
the layout. Per-clock buckets are well defined but require the anchors to be applied before
they are usable, which is the work this table exists to have done once.

**The time-clustered layout is not something core declines. It is something core cannot
express.**

### Evidence

`conformance/parquet-probe/real.py`, against the committed 247,758,402-row table. PyArrow,
warm, seconds. `U` is unit-major, `T` time-major, `H<n>` bucketed at *n* seconds; the suffix is
the row-group size.

| layout | MB | 24 adjacent units | 10 s window | 24 scattered units | units + window |
|---|---:|---:|---:|---:|---:|
| `U-delta-1M` | 426 | 0.026 | 0.764 | 0.234 | 0.032 |
| `U-delta-128K` | 429 | 0.030 | 0.301 | 0.056 | 0.041 |
| `T-delta-1M` | 688 | 2.606 | 0.008 | 2.586 | 0.030 |
| `H60-delta-128K` | 511 | 0.099 | 0.049 | 1.039 | 0.044 |
| **`H300-delta-128K`** | **453** | **0.045** | **0.045** | **0.319** | **0.047** |
| `H300-delta-32K` | 462 | 0.107 | 0.155 | 0.195 | 0.141 |

Two dedicated copies cost 1,114 MB. One bucketed table costs 453 MB, is within 6x of the best
layout on every query and best on none, and removes the standing obligation that two copies of
the same facts agree.

Sorting does not reduce information, it moves it between columns. Time-major drives `t_tick`
to 1.87 bit/row — consecutive spikes across 7,291 units are ~0.8 ticks apart — and pays 20.3
bits for the context that unit-major run-length-encodes into 0.17, ending 61% larger.

Encoding, same table: dictionary on `t_tick` is the worst option at every row-group size and in
every order, because the writer builds a dictionary nearly as large as the column, overflows
the page limit, abandons it mid-column and emits both. Unit-major totals: dictionary 593.9 MB,
`PLAIN` 531.6 MB, `DELTA_BINARY_PACKED` 426.4 MB. Bloom filters on `unit_id` cannot prune —
a time-major row group holds 6,651 to 6,874 of 7,291 units — and PyArrow does not read the
page index.

## 7. What this does not do

- **No change to `core.spike_events`.** Its order and its per-probe ticks stand.
- **No new canonical fact.** `time_bucket_tick` is a function of `t_tick` and the declared
  bucket width, carried so the order is declarable as a column list and checkable by R12's
  shim. It is not a scientific claim.
- **No treatment of the other analysis resources.** `06` names six more, and
  `analysis.spikes_by_trial` in particular has the same problem in a milder form: it says
  spikes carry `t_abs_tick` and `t_rel_tick` without saying which clock either is on. That
  wants its own revision once something builds it.
- **No `since` stamp on the columns `06` already defined.** Under R29 §2 only
  `time_bucket_tick` carries one, because only it is new here.

## 8. Open

- **Whether a dropped spike should be recorded anywhere.** §4 omits it silently, and a count of
  what the mapping could not place is a real quality signal — a session losing thousands is one
  whose sync started late. `core.processing_runs` could carry it as a materialization
  parameter, which is `06` §169's mechanism, and nothing currently writes one.
- **Whether the reference clock should be named in the resource rather than the rows.** Every
  row carries the same `clock_id`, which dictionary-encodes to nothing but is still a column
  restating a per-resource fact. R3 §3.0 would normally strike it; it stays because the foreign
  key to `core.clocks` is what makes the claim checkable at all.
- **Whether one bucket width can serve every session.** 300 s was measured on one 5,364 s
  session with 7,291 units. The dial trades scattered-unit access against time-window access
  through row groups per bucket, so a much shorter or much sparser session will want a
  different value, and nothing here tells a writer how to pick one.

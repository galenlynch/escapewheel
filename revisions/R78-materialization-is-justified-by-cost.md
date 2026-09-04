# R78 — Materialization Is Justified by Cost, Not by Layout Alone

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | `06` §2 (when an analysis resource is materialized), R43 §3 (which generalised a measurement) |
| **Depends on** | R43 (an alignment is a query), R30 (what `analysis.spike_events` is for), R65 (an array names its instrument) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R43 withdrew four of `06`'s five materialized resources on measured grounds and stated the test
that survived them as **layout, not arithmetic**: a resource is worth materializing when its
physical organization answers a question core's cannot, and not when it merely saves computation.

The measurements were right and the generalisation is too narrow.

### 1.1 What the rule forbids that it should not

R43's evidence is four alignments of one real analysis coming to **100.6%** of the spike table to
save 2.7 s against arrays already in memory. That is a decisive argument about *alignments*. Read
as a universal rule it also forbids persisting:

```
a filtered or resampled signal        a spectral decomposition
a current-source-density estimate     a waveform feature matrix
a pose estimate                       a model embedding
```

None of these is a re-sort of core. Each is the result of a transformation whose cost is the
reason to keep it, and each has a stable parameterisation that makes the stored result meaningful
rather than incidental.

### 1.2 The gap is wider than it was

R65 §2.2 makes an array asset hold **any** sampled quantity, from any instrument, with no
enumeration in the standard. A rig fitting a respiration sensor or a thermistor produces
core-owned arrays whose derived products are exactly §1.1's list. A rule admitting only layout
would send every one of them outside the format.

### 1.3 What the narrow rule got right

Cheapness is still disqualifying, and R43 §2.2 measured it: a wide trial table is 708 rows in
7.5 ms, and `analysis.good_units` is a filter. A resource that a query reproduces in milliseconds
is a view whatever else is true of it, and nothing here reopens the four withdrawals.

## 2. Decision

### 2.1 The test

> An analysis resource **SHOULD** be materialized only where doing so materially reduces repeated
> computational or I/O cost, gives an access layout core cannot, preserves the result of an
> expensive transformation, or provides a stable interface to an explicitly parameterised
> derivation.
>
> A cheap filter, projection, rename or small join **SHOULD** remain a view.

Four grounds where `06` had one. The last two are what R43's wording excluded.

### 2.2 An expensive result declares what produced it

A materialized resource whose justification is §2.1's third or fourth ground **MUST** record the
parameters of the transformation in its producing run (R31 §3), not only that a run occurred. A
spectrogram whose window and overlap are unrecorded is not reproducible, and an irreproducible
derived asset fails `06`'s disposability test — a consumer cannot delete and recompute it.

### 2.3 Nothing is grandfathered

The four resources R43 withdrew stay withdrawn. Their measurements stand: they were re-sorts and
filters, and §2.1's first two grounds are the ones they failed.

## 3. What this does not change

- **No table, no column, no rule.** One sentence of `06` is replaced by four grounds.
- **No new obligation on a writer**, which materializes what a recipe asks for.
- **No change to disposability.** An analysis resource remains deletable and recomputable (`06`),
  which §2.2 is what protects.
- **No change to lineage.** R71 §2.3 already requires it to name every canonical resource it
  derived from.

## 4. Open

- **Whether "materially" can be given a number.** R43 measured its case and this states a
  judgement. A threshold — a ratio of stored bytes to seconds saved — would be checkable and
  would also be wrong for the first workload that did not fit it, which is why R43's own test was
  a measurement and not a constant.

# R37 — Bounding Clock Alignment by Error, Not Distance

| | |
|---|---|
| **Status** | **Accepted** 2026-08-31 |
| **Amends** | R27 §5.2, §5.3 |
| **Depends on** | R13 (anchor alignment), R27 (clock graph integrity) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R27 §5.3 defines the mapping between a clock and its parent out to **one median anchor
interval** beyond the terminal anchors, and undefined past that. The bound is a distance. Three
findings say distance is the wrong axis, and that the rule as written now deletes real data.

**R27 §5.2's measured table does not reproduce.** It records 6–18 µs at one second for a rate
fitted over the full anchor sequence. Measured again on `ecephys_776259_2025-04-09` — twelve
probe clocks, 6,388 anchors each, 1,140 held-out predictions — the same quantity is **525 µs at
p95**. The gap is the estimator, not the data: `align()` extrapolates from the fitted line,
`slope * tick + intercept`, and the intercept carries the whole session's wander.

**The wander is real and large.** A single straight line fits 6,387 s of anchors to no better
than **±1,739 µs**, rms 331 µs. It is not noise and not a defect: 388 of 6,387 pulse intervals
are one sample short, so the probe clock runs ~2 ppm fast against HARP and that offset wanders
~0.3 ppm with temperature. The anchors record it faithfully — interpolating between adjacent
anchors is accurate to **16 µs, exactly half a HARP tick**, which is quantization and nothing
else. Only a global line misses it, because a line cannot bend.

**The terminal anchors cannot be trusted, and dropping them hits the bound.** The first sync
pulse of every stream is displaced by 150–290 µs, traced in §5 to a defect in the upstream
alignment. Dropping it moves the first usable anchor from 0.662 s to 1.662 s, which is outside
the one-second bound — stranding **23,126 spikes, the first second of every stream**. That is
the same class of loss R27 §5.1 was written to stop: *"real recorded data with no defined time
— systematically at the session boundaries, where task onset and offset live."*

So the correction a writer must make to keep its anchors honest is, under the current rule,
punished by the loss of the data the rule exists to preserve.

## 2. The error budget

Measured on the same session. Each term is stated against one probe sample, 33.3 µs at 30 kHz.

| term | magnitude | what it is |
|---|---|---|
| interpolation between anchors | 16 µs median, 49 µs p95 | tick quantization |
| one-interval extrapolation from a clean anchor at a locally fitted rate | 26 µs median, 78 µs max | quantization plus local rate error |
| rate error over one interval | < 1 µs | 0.3 ppm × 1 s |
| extrapolation from a globally fitted **line** | 376–525 µs p95, **flat in distance** | the line's offset from local truth |
| a terminal anchor placed outside the upstream anchor span | 150–290 µs | §5 |

The fourth row is the finding. Its being flat in distance — 525 µs at one second, 376 µs at
sixty — is the signature of a constant offset rather than accumulating drift. Distance is not
what costs; the estimator and the terminal anchor's own quality are.

## 3. Decision

### 3.1 Extrapolation is anchored at the terminal anchor

Beyond the terminal anchors a consumer MUST compute the mapping as

```text
parent(t) = parent(a) + rate * (t - a)
```

where `a` is the nearest terminal anchor and `rate` is fitted over that clock's anchors. A
consumer MUST NOT use the intercept of a fit over the whole sequence. R27 §5.3 already says
"MUST use the rate fitted over the clock's full anchor sequence"; this states the offset the
rate is applied from, which it left open and which the reference implementation got wrong.

Measured effect: p95 error at the ends falls from 525 µs to 258 µs with a global rate, and to
26 µs median / 78 µs max with a rate fitted over the nearest 30 anchors.

### 3.2 An anchor a writer cannot trust is not written

A writer MUST NOT emit an anchor whose parent tick it has reason to believe is misplaced, and
MUST record any anchor it withheld — count and clock — in the producing run's parameters.

A writer SHOULD test each terminal anchor by predicting it from a fit over its neighbours and
comparing the residual against the distribution of the same residual over that clock's interior
anchors. On this session the interior residual is 26 µs median with a maximum of 78 µs, while
10 of 12 first anchors exceed their own clock's interior 99th percentile.

The test is stated on the clock's own spread rather than as a fixed tolerance because anchor
quality is a property of a rig and a session, not of the format.

### 3.3 The bound is on error, not distance

R27 §5.3's third clause is replaced. The mapping beyond a terminal anchor is defined while the
**predicted error** of §3.1's estimator remains within a declared tolerance, and undefined
beyond it. The tolerance defaults to one tick of the parent clock.

A writer establishing a bound wider than one median anchor interval MUST measure it, by
holding out terminal anchors of the same clock and predicting them at the intended distance.
Where a writer does not measure it, R27 §5.3's one-median-interval bound stands as the default,
so a packet that says nothing is unchanged by this revision.

The clause on gaps is unchanged: a gap wider than 2*m* leaves its middle undefined.

**Why this and not a wider distance.** A distance bound proportional to anchor spacing was
chosen in R27 §5.3 because it "needs no new column and scales automatically with an edge's
anchor rate". That reasoning holds; the axis was wrong. A clock with three anchors has a rate
barely determined and should get almost no allowance; one with 6,388 anchors, measured, can be
extrapolated seconds at a cost below its own quantization. Error expresses that and distance
cannot.

## 4. What this does not do

- **No change to interpolation.** Between anchors no more than 2*m* apart the rule is
  unchanged, and it is already accurate to quantization.
- **No new table or column.** The withheld-anchor record goes in `core.processing_runs.parameters`,
  which R31 already uses for materialization parameters.
- **No claim about which anchors are bad in general.** §3.2 gives a test, not a list. The
  specific upstream defect in §5 is evidence that the test is needed, not part of the rule.
- **No change to `core.clock_anchors`' schema.** A dropped anchor is simply absent;
  `anchor_index` stays contiguous over what is written, as R27 requires.

## 5. The upstream defect this was found through

`harp.clock.align_timestamps_to_anchor_points` builds one linear model per barcode segment plus,
at index 0, a least-squares fit over every barcode. It then selects a model per timestamp:

```python
nearest = np.searchsorted(start_times, timestamps_to_align, side="left")
nearest[nearest == N] = 0
aligned = timestamps_to_align * slopes[nearest] + offsets[nearest]
```

`searchsorted` yields 0 before the first anchor and `N` after the last, and the second line
folds `N` onto 0. Both out-of-range regions are therefore mapped by the global fit while every
interior point uses its own segment — the same defect §3.1 corrects in this specification.

It predicts the measurement exactly. The barcode anchors span 11,575,877.001 → 11,582,264.039;
the sync pulses span 11,575,876.947 → 11,582,263.930. The first pulse falls 54 ms **before** the
first barcode and is displaced 150–290 µs; the last falls 109 ms **inside** the last barcode and
is clean at −28 µs. Only the first anchor of each stream is affected.

The layers below are sound. Open Ephys's `sample_numbers` are exact and its
`original_timestamps` carry no terminal anomaly, only ±1.2 ms of software jitter throughout,
which the alignment otherwise removes to a single sample.

## 6. Reproduction

Every figure above comes from `core.clock_anchors` of a packet built from
`ecephys_776259_2025-04-09`, and from the Open Ephys events tree beneath
`Record Node 111/experiment1/recording1/events/`. The estimator comparisons hold out terminal
anchors and predict them; the interior control applies the identical test at interior positions,
which is what distinguishes a displaced anchor from a poorly conditioned estimator.

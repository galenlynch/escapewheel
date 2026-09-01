# R40 — A Tolerance That Gates on Quality, Not on Noise

| | |
|---|---|
| **Status** | **Accepted** 2026-09-01 |
| **Amends** | R37 §3.3 (the tolerance and the statistic), R27 §5.3 (what a writer must say when it drops) |
| **Depends on** | R37 (error-bounded alignment), R13 (anchor alignment) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R37 §3.3 replaced R27 §5.3's distance bound with a bound on error, and set the tolerance at
one tick of the parent clock. Implementing it against `ecephys_776259_2025-04-09` shows the
number is wrong by two orders of magnitude, and that the statistic it is compared against says
nothing about the tail.

**One parent tick is below the estimator's own median.** A HARP tick is 32.0 µs. The R37 §3.1
estimator, measured on twelve probe clocks at interior positions, costs 31 µs at the median one
interval out. So the default tolerance sits *at* the typical error rather than above it, and
whether a packet passes is decided by which side of its own median it lands on. This session
passed at 0.96 ticks against a tolerance of 1.00 — a margin of 4%, on a quantity that is
measurement noise.

**And failing is not cheap.** Falling back leaves the bound at one median anchor interval, which
strands the first 1.73 intervals of every stream — the 23,126 spikes R37 §1 was written to
preserve, plus every event at task onset. A gate that decides that on a 4% margin is deciding
it arbitrarily.

**The error is flat in distance, now measured out to two minutes.** R37 §2 found this over
sixty seconds; extending the same measurement:

| intervals beyond the terminal anchor | ≈ seconds | p50 | p95 | max |
|---:|---:|---:|---:|---:|
| 1 | 1 | 31.4 µs | 66.9 µs | 837 µs |
| 2 | 2 | 30.8 µs | 116.5 µs | 1611 µs |
| 10 | 10 | 58.8 µs | 112.2 µs | 1626 µs |
| 60 | 60 | 53.8 µs | 386.3 µs | 1688 µs |
| 120 | 120 | 60.7 µs | 804.6 µs | 1711 µs |

Two minutes costs twice one second. That is the signature R37 §2 identified — a constant offset,
not accumulating drift — and it means the quantity a tolerance should be set against is the
estimator's floor, not the distance travelled.

**The median hides the tail.** At the two intervals this session needs, p50 is 31 µs and p95 is
117 µs. A gate on the median admits a clock whose 95th percentile is four times worse without
noticing.

## 2. Decision

### 2.1 The tolerance is stated as a duration, and defaults to three milliseconds

R37 §3.3's default is replaced. The tolerance is a duration, not a tick count, and defaults to
**3 ms**. A profile or a recipe MAY state a different one; a writer MUST record the value it
used.

Stated as a duration because it is a claim about time and not about a particular clock's
granularity — the same packet read against a 1 kHz reference and a 31,250 Hz one should admit
the same mappings. Three milliseconds because it is above every measured p95 in §1 by a factor
of four or more while remaining far below anything that changes an analysis: the finest PSTH bin
in the capsules this format was measured against is 30 ms, and a probe sample is 33 µs.

A tolerance this wide still refuses what it exists to refuse. R37 §3.3's example — a clock with
three anchors, whose rate is barely determined — misses by seconds, not milliseconds.

### 2.2 The statistic is the 95th percentile

The measured error is compared at p95 rather than at the median. A bound is a statement about
what a consumer may rely on, and the median is not one.

Both are reported: a writer recording its measurement MUST record median, p95 and maximum, so
that a reader can judge the packet by a stricter rule than the writer applied.

### 2.3 A dropped row is reported, never silent

A writer that omits a row because the mapping is undefined MUST record how many rows it omitted
and on which clock, in the producing run's `parameters` (R37 §4). A reader that omits rows for
the same reason SHOULD make the count available.

This is not bookkeeping. Reading `core.spike_events` through R13's map and reading
`analysis.spike_events` are supposed to give the same spikes, and where the two used different
bounds they did not — a difference of two spikes in 40,774 on one unit, found only by comparing
against an unrelated implementation. Neither side said anything, because neither counted.

**A packet that drops nothing says so.** A recorded count of zero is the evidence that the bound
was sufficient, and it is what makes §2.1's default checkable on a session other than this one.

## 3. What this does not do

- **No change to the estimator.** R37 §3.1 stands: the globally fitted rate, applied from the
  terminal anchor.
- **No removal of the undefined region.** A clock with no anchors reaches no reference, and a gap
  wider than 2*m* still leaves its middle undefined (R27 §5.3). Widening a tolerance does not
  make an unanchored tick knowable; it stops a well-anchored one being refused.
- **No new table or column.** As R37 §4, the record goes in `core.processing_runs.parameters`.
- **No claim that 3 ms is right for every rig.** It is the default, measured against one session
  on one rig. §2.1 makes it stateable, and §2.2 makes the evidence for changing it a measurement
  rather than an argument.

## 4. Measured

On `ecephys_776259_2025-04-09`, twelve probe clocks against HARP, 6,387 anchors each.

**What must be reached.** Data lies beyond the terminal anchors by, at worst, **1.73 median
anchor intervals** — before the first anchor on every stream, because the sync train starts after
the recording does, and 0.09–0.17 intervals after the last. Withholding the displaced first
anchor (R37 §3.2) is what moves the leading figure from 0.60 to 1.73.

**What reaching it costs.** At two intervals, **p95 = 116.5 µs**, which is 3.6 HARP ticks and
3.5 probe samples. Against a 3 ms tolerance that passes by a factor of 26; against the tolerance
R37 §3.3 set, it fails by a factor of 3.6 while the median passes by 4%.

**What is dropped under this revision:** nothing. 286,896,563 spikes, twelve clocks, zero rows
without a defined mapping at either end — recorded as zero rather than assumed.

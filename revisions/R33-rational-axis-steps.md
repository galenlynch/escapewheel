# R33 — An Axis Step May Be Rational

| | |
|---|---|
| **Status** | **Accepted** 2026-08-29 |
| **Amends** | R20 §2 (`core.array_dimensions`, the regular form), R20 §5's rate-agreement rule |
| **Depends on** | R20 (array axis coordinates), R2 §4 (type vocabulary) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R20 §2 gives a regularly sampled axis an origin and a step in ticks:

| Field | Type | Meaning |
|---|---|---|
| `origin_tick` | int64 | Tick at position 0. |
| `step_ticks` | int64 | Ticks advanced per position. |

An `int64` step can only describe a rate that divides the clock. Ordinary ones do not:

```text
clock 31,250 Hz (HARP)
  10 ms bin    312.5 ticks
  30 ms bin    937.5 ticks
  50 ms bin  1,562.5 ticks
  29.97 fps  1,042.708333... ticks
```

Every one of those is exact as a fraction and impossible as an integer. `06` lists
`analysis.binned_spikes`, so the first packet that bins spikes at a standard PSTH width meets
this immediately.

**Rounding is not available.** Taking 937.5 as 938 drifts half a tick per bin: over an hour of
30 ms bins that is 60,000 ticks, 1.9 s, and it accumulates silently in the direction of the
rounding. The whole reason R20 stores a step rather than an array of positions is that the
step is exact; a rounded step is worse than the array it replaced.

**The float form is the wrong escape.** R20 §2 also permits `step_value` in a declared unit,
and a caller could put 0.03 seconds there. That contradicts the invariant the format is built
on -- time is integer ticks on a declared clock, and float seconds are derived only -- and it
gives up the exactness for a quantity that *is* exact.

**The registry already disagrees with itself.** `core.clocks` carries `tick_rate_num` and
`tick_rate_den`, because a clock's rate is a rational and rounding it would be wrong. An axis
step is the same kind of quantity measured against the same clock, and has no denominator.
R33 removes the asymmetry rather than introducing an idea.

## 2. Replacement

`core.array_dimensions` gains one column:

| Field | Type | Required | Description |
|---|---:|:---:|---|
| `step_tick_den` | int64 | no | Denominator of the step, in ticks. Absent means 1. |

`step_ticks` becomes the **numerator**: an axis advances `step_ticks / step_tick_den` ticks per
position. A row that omits `step_tick_den` means what it meant before, so every packet written
under R20 stays conforming and unchanged.

`step_tick_den`, where present, MUST be positive. `step_ticks` MUST still be present whenever
`origin_tick` is (R20 §5's existing rule), and the pair SHOULD be in lowest terms, so that two
packets describing the same axis describe it identically.

`origin_tick` stays an integer. An origin is one position and can always be named on the
clock; it is only the repeated advance that needs to be exact between positions.

### 2.1 The position of an element

The tick of element *k* on such an axis is

```text
origin_tick + k * step_ticks / step_tick_den
```

which is generally not an integer. That is the point, and it is not a defect: the *coordinate*
is exact, and a consumer that needs an integer tick rounds at the moment it needs one, once,
rather than accumulating a rounding at every step. A consumer MUST NOT assume element
positions are integers.

## 3. Validation

R20 §5's rule that a declared `sample_rate_hz` agrees with the axis becomes

```sql
SELECT a.array_asset_id, a.sample_rate_hz, d.step_ticks, d.step_tick_den, c.tick_rate_hz
FROM core_array_assets a
JOIN core_array_dimensions d ON d.array_asset_id = a.array_asset_id
JOIN core_clocks c ON c.clock_id = d.clock_id
WHERE a.sample_rate_hz IS NOT NULL AND d.step_ticks IS NOT NULL
  AND c.tick_rate_hz IS NOT NULL
  AND abs(a.sample_rate_hz
          - c.tick_rate_hz * COALESCE(d.step_tick_den, 1) / d.step_ticks) > 1e-6
```

and one rule is added:

```sql
SELECT array_asset_id, axis_index, step_tick_den FROM core_array_dimensions
WHERE step_tick_den IS NOT NULL AND step_tick_den <= 0
```

## 4. What this does not do

- **No change to the other three coordinate forms.** A coordinate array, a coordinate column
  and the float form are untouched, and R20 §2's rule that an axis declares exactly one form
  still holds.
- **No rational origin.** §2 says why.
- **No change to `core.clocks`.** Its rate was already rational; this makes the step match it.
- **No new type.** `int64` throughout, so R3 §2.1's primitive floor is unaffected and a reader
  needs no new machinery to see the numbers.

## 5. Open

- **Whether a writer should be required to reduce the fraction.** §2 says SHOULD. Requiring it
  would make two descriptions of one axis byte-identical, which is worth something for
  comparison; it also means a writer that has 1875/2 must know to leave it alone while one
  that has 3750/4 must not. Nothing yet depends on the answer.
- **Whether `core.media_frames` should use this rather than a row per frame.** An hour of
  29.97 fps video is 107,892 frames, which is cheap to store explicitly and exact either way.
  The regular form would be three numbers instead, and the argument is the same one R20 makes
  for arrays -- but media frames can drop, and a dropped frame breaks regularity in a way a
  sampled signal does not.

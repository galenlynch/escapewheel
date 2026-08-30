# R34 — Amplitude Is Not a Structural Column

| | |
|---|---|
| **Status** | **Accepted** 2026-08-29 |
| **Amends** | R28 §2 (`core.unit_electrodes`), R16 §5 |
| **Depends on** | R16 (unit quality labels), R17 (extension registries), R28 (unit electrodes) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R28 §2 gave `core.unit_electrodes` an `amplitude` column — *"the unit's amplitude on this
electrode"* — and R28 §7 flagged it in the same document: it is the first quality-like number
in a structural table, and R17's extension registry may be the better home. Building the first
packet carrying waveforms settles the question, because the column cannot be filled.

### 1.1 Three quantities wear the name

| Grain | Where it lives today | What it is |
|---|---|---|
| per spike | `core.spike_events.amplitude` | one detection's height |
| per unit | nowhere in core | a summary of that unit's spike-amplitude distribution |
| per (unit, electrode) | R28's column | the template's height on one contact |

Sources emit the second. R28 defined the third. Nothing connects them.

### 1.2 The two are not the same statistic

Measured on 6,781 units, comparing the source's per-unit `amplitude` against every plausible
reduction of the same unit's mean waveform **at its own extremum channel**:

| Candidate reduction | Rows reproduced |
|---|---|
| trough (minimum) | 0.0% |
| peak (maximum) | 0.0% |
| absolute extremum | 0.0% |
| peak-to-trough | 18.7% |

The per-unit number is not a template reduction at all. It is computed from the spike
amplitude distribution, which the mean waveform has already averaged away.

So a writer filling R28's column has three options and each is wrong:

- **repeat the per-unit value across the support** — asserts the unit had equal amplitude on
  every contact, which is false for all but one of them;
- **write it on the peak row only** — a column that is 96% null and whose one value is a
  different quantity from the one the column defines;
- **compute a template reduction** — a genuinely per-electrode number, but one the source
  disagrees with by a median of 20 µV at the very contact where both are defined.

A column no conforming writer can populate honestly is a defect in the column.

## 2. Amplitude leaves core

`core.unit_electrodes` MUST NOT carry `amplitude`. The column is struck from R28 §2's
definition. What remains is structural and complete without it:

| Column | Role |
|---|---|
| the four-column unit key | which unit |
| `electrode_id` | which contact it was detected on |
| `channel_ordinal` | that contact's position along a dense array's channel axis (R20 §2) |
| `is_primary` | which of them is the peak |

This is `09`'s minimalism test applied. Amplitude is needed to identify no unit, to interpret
no array — R20 §2's labelled axis is indexed by `channel_ordinal`, not by amplitude — to
validate no rule, and to reproduce nothing. It is a measured quality-like number, and R16 §5
already routes those to a namespaced extension. R16 §5's list omits amplitude only because
R28 had not yet placed it in core.

Sorters that threshold a sparsity mask on amplitude are unaffected: the mask's *result* is
the row set of `core.unit_electrodes`, and the threshold that produced it is a parameter of
the sorting run, not a fact about the packet's electrodes.

## 3. Which amplitude a packet records

A packet MAY carry none: `core.unit_electrodes` is conforming with the structure alone, and a
reader that wants a template amplitude computes it from the waveform array the packet already
holds. This is R3 §3.0's duplication test coming out the other way from R3 §4's — the array
declares the trace, the reduction is cheap for a reader holding it, and no SQL rule needs it.

## 4. What this does not do

- **Does not say where amplitude goes instead.** R16 §5 routes continuous quality metrics
  to a namespaced extension, but which metrics, under what names, and on which key are all
  left open. Nothing here requires an extension to exist.
- **Does not touch `core.spike_events.amplitude`.** Per-spike amplitude is a fact about a
  detection, is required to interpret nothing else, and `core.sorting_runs.amplitude_unit`
  (R11 §2) already gives it a unit. It stays.
- **Does not settle `is_primary` versus `default_electrode_id`.** R28 §7's other open
  question stands; both still earn their place, since dropping either costs a query the
  other answers alone.
- **Does not change the table count.** 33 tables, as R28 left it. The registry loses one
  column: 277 → 276.

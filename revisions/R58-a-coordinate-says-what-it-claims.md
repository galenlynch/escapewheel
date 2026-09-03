# R58 — A Coordinate Says What It Is A Claim About

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | R19 §3 (`core.electrode_coordinates`), R28 §3 (`core.unit_coordinates`), R41 §2 (what currency covers) |
| **Forces** | R59 (an atlas annotation attaches to a coordinate, so it needs a basis to attach to) |
| **Corrected by** | R60 (§2.3's currency claim; the key admits one row per basis, so R41 has nothing to arbitrate) |
| **Depends on** | R8 (open vocabularies), R19 (coordinate frames), R28 (unit coordinates), R41 (currency), R44 (a run declares its scope) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

An electrode's CCF position is known twice. Before perfusion it is a target picked from an atlas
and reached through a manipulator: intent, imprecise. After histology it is a measurement,
registered to the same atlas. `core.electrode_coordinates` is keyed
`(electrode_id, coordinate_frame)`, so the two collide, and a packet holds one of them without
recording which. The two differ by however far the probe missed.

### 1.1 What the source actually carries

Measured on two AIND ecephys sessions:

| column | `776259_2025-04-09`, 4608 electrodes | `786867_2025-09-25`, 3840 electrodes |
|---|---|---|
| `ccf_ap`, `ccf_dv`, `ccf_ml` | 4224 present; one probe's 384 unregistered | 3840 present |
| `rel_x`, `rel_y` | present, probe frame | 0–782 µm × 0–2865 µm |
| `x`, `y`, `z` | NaN for all 4608 | NaN for all 3840 |

One CCF estimate per electrode, with no field naming its kind. The 384 unregistered contacts make
the gap concrete: that probe has a plan and no measurement, and the packet represents it exactly as
it represents a probe with neither.

### 1.2 Currency is the wrong axis

R41 offers the obvious move: key the choice on the producing run and let `core.preferred_runs`
declare that histology wins.

R41 governs alternatives — three sortings of one probe, where a consumer wants one and MUST NOT
silently choose. A plan and a measurement are both wanted, and their difference is the targeting
error. Superseding the plan therefore discards a result, and discards it exactly when the probe
missed.

Spelling the two as `ccf_planned` and `ccf_registered` is the other obvious move. It costs no
schema change, and it folds what space a coordinate is in and what kind of claim it makes into one
string a consumer must parse — the conflation R49 removed from `scope` and R55 named.

## 2. Decision

### 2.1 A coordinate declares its basis

`core.electrode_coordinates` and `core.unit_coordinates` each gain `coordinate_basis`, a required
`string` with R48 role `data`, saying what the coordinate asserts:

| | |
|---|---|
| `planned` | where the probe was meant to go. Intent, before the fact. |
| `measured` | where it was, established after the fact. |

The primary keys extend to include it:

```
core.electrode_coordinates   (electrode_id, coordinate_frame, coordinate_basis)
core.unit_coordinates        (session_id, unit_id, sorting_run_id, curation_id,
                              coordinate_frame, coordinate_basis)
```

Both rows persist, and neither supersedes the other. Targeting error is a self-join on
`(electrode_id, coordinate_frame)`.

`coordinate_frame` says what space a coordinate is in; `coordinate_basis` says what claim it makes.
A packet carrying one basis is conforming — a session before histology has `planned` alone.

### 2.2 The vocabulary is open, and an unrecognised basis is not ground truth

A rig may establish a position in ways this specification has not seen, so `coordinate_basis` is
open (R8 §4) and a validator **MUST NOT** reject a value outside the two above.

Openness alone would be unsafe, so the column carries a rule the other open vocabularies do not
need: a consumer that does not recognise a basis **MUST NOT** treat the coordinate as `measured`.
A permissive default would read an unknown basis as ground truth, which is the failure this column
exists to prevent.

### 2.3 Currency applies within a basis, not across bases

Two histology registrations of one probe, from a different alignment tool or a re-run against
better slices, are alternatives, and R41 governs them. Both tables therefore gain a nullable
`processing_run_id` with R46's reference to `core.processing_runs`, and R41 applies unchanged
within one `(frame, basis)`.

- `coordinate_basis` separates different questions, and is never superseded.
- `processing_run_id` separates different answers to one question, where R41 §2.4 governs and
  `core.preferred_runs` records the choice.

R41 §2 is amended to say so: currency relates runs answering the same question, so a column
distinguishing questions is not a currency axis. R44 §2 already implies this by keying a preference
on `(activity_type, scope)` — a plan and a measurement are not one activity.

## 3. What this does not change

- **No new table.** One column added to each of two tables.
- **No change to `coordinate_frame`.** R19 §3's frames are orthogonal to a basis.
- **No requirement to carry both bases.** Most packets will carry one.
- **No stored coordinate changes value.** Where histology produced a row, it becomes `measured`,
  which is what R19 §3's rows have meant in practice.

## 4. Open

- ~~**Whether a coordinate should carry uncertainty.**~~ **Settled 2026-09-03: no column is
  added.** Nothing measured records a quantitative uncertainty on either basis, so a column for it
  would be present and empty in every packet — which R3 §3.0 refuses for the same reason it refuses
  any duplication that buys nothing. `coordinate_basis` carries what is actually known: that a
  `planned` position is an intent and a `measured` one is not. A pipeline that begins recording an
  interval or a covariance can have a column then, argued from what it emits.
- **Whether `coordinate_basis` is meaningful outside an atlas frame.** A probe-frame coordinate is
  the probe's own geometry, exact by construction and neither planned nor measured. It wants a
  third value, or a nullable column where the frame makes the question empty. Left until a packet
  carries such a frame.
- **Whether a unit's basis is its own or inherited.** R28 §3 computes a unit's position from its
  electrodes, so a unit computed from `planned` electrodes is `planned`. That argues for
  inheritance rather than an independent declaration, but nothing forbids a writer from asserting
  otherwise and no packet yet carries `core.unit_coordinates`.

# R58 — A Coordinate Says What It Is A Claim About

| | |
|---|---|
| **Status** | **Proposed** |
| **Amends** | R19 §3 (`core.electrode_coordinates`), R28 §3 (`core.unit_coordinates`), R41 §2 (what currency covers) |
| **Depends on** | R8 (open vocabularies), R19 (coordinate frames), R28 (unit coordinates), R41 (currency), R44 (a run declares its scope) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

A probe's position is known twice, and the two are not the same fact.

Before the animal is perfused, an electrode's CCF position is where the experimenter **meant** the
probe to be: a target picked from an atlas, reached through a manipulator, imprecise and about
intent. After histology it is where the probe **was**: measured, registered, and localised to the
same atlas. Both are in CCF. `core.electrode_coordinates` is keyed
`(electrode_id, coordinate_frame)`, so the two collide on the key and a packet can hold one.

Which one it holds, it does not say. A consumer reading a CCF coordinate cannot tell whether it is
looking at a plan or a measurement, and the two differ by however far the probe missed.

### 1.1 What the source actually carries

Measured on the ecephys session in `inventory/nwb-zarr-776259-2025-04-09.md`, over 4608 electrodes:

| column | state |
|---|---|
| `ccf_ap`, `ccf_dv`, `ccf_ml` | present for 4224; one probe's 384 unregistered |
| `ccf_acronym` | 72 distinct, one of them empty |
| `rel_x`, `rel_y` | present, probe frame |
| `x`, `y`, `z` | **NaN for all 4608** — the frame NWB itself specifies |

One CCF estimate per electrode and no field naming what kind it is. The 384 unregistered contacts
are the case that makes the gap concrete: that probe has a plan and no measurement, and the packet
represents it identically to a probe with neither.

### 1.2 Currency is the wrong axis

The obvious move is R41 — key the choice on the producing run, let `core.preferred_runs` say that
histology wins. It is wrong, and wrong in the case that matters most.

R41 is about **alternatives**: three sortings of one probe, where a consumer wants one and MUST NOT
silently choose. A plan and a measurement are not alternatives. They are different facts, and the
difference between them is itself a result — targeting error is `measured - planned`. A model in
which histology supersedes the plan destroys the quantity precisely when the probe missed, which is
when someone wants it.

Nor is it a frame distinction. Spelling the two as `ccf_planned` and `ccf_registered` works and
costs no schema change, but folds *what space* and *what kind of claim* into one string a consumer
must parse — the conflation R49 removed from `scope` and R55 named.

### 1.3 The ambiguity already ships

`core.electrodes.brain_region` is one string with no qualifier. It answers either "the structure
you targeted" or "the structure histology found the contact in", and a packet cannot say which. In
the session above it is `ccf_acronym`, derived from the registered coordinates — but a targeting
record has a planned structure too, and there is nowhere to put it that does not overwrite.

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

Both rows persist. Neither supersedes the other, ever. Targeting error is a self-join on
`(electrode_id, coordinate_frame)`.

`coordinate_frame` continues to say **what space**; `coordinate_basis` says **what the number is a
claim about**. A packet carrying only one basis is conforming: a session before histology has
`planned` alone, and that is the honest state rather than a gap.

### 2.2 The vocabulary is open, and an unrecognised basis is not ground truth

`coordinate_basis` is **open** (R8 §4): a rig may establish a position in ways this specification
has not seen, and a validator **MUST NOT** reject a value outside the two above.

Openness alone would be unsafe here, so it carries a rule the other open vocabularies do not need.
A consumer that does not recognise a basis **MUST NOT** treat the coordinate as `measured`. Reading
an unknown basis as ground truth is the exact failure this column exists to prevent, and it is the
failure a permissive default produces.

### 2.3 Currency applies within a basis, not across bases

Two histology registrations of one probe — a different alignment tool, a re-run against better
slices — genuinely are alternatives, and R41 is exactly right for them. So both tables gain a
nullable `processing_run_id`, with R46's reference to `core.processing_runs`, and R41's machinery
applies unchanged **within** one `(frame, basis)`.

- `coordinate_basis` separates different **questions**. Never superseded.
- `processing_run_id` separates different **answers to one question**. R41 §2.4 governs, and
  `core.preferred_runs` records the choice.

R41 §2 is amended to say so: currency is a relation between runs answering the same question, and a
column distinguishing questions is not a currency axis. That is what R44 §2 already implies by
keying a preference on `(activity_type, scope)` — a plan and a measurement are not one activity.

### 2.4 A structure label belongs to a position

`core.electrodes.brain_region` is struck. A structure label is a fact about a position — which
atlas, which coordinate — so it moves to the coordinate row as
`core.electrode_coordinates.region_label`, nullable, open, alongside the coordinate it describes.

Keeping it on `core.electrodes` is R3 §3.0 duplication that can answer only one of the two
questions, and which one it answers is not recorded. Moving it makes a planned structure and a
measured structure both expressible, and each attached to the coordinate that justifies it.

## 3. What this does not change

- **No new table.** Two columns and a struck one.
- **No change to `coordinate_frame`.** R19 §3's frames are unaffected; this is orthogonal to them.
- **No requirement to carry both bases.** Most packets will carry one.
- **No stored coordinate changes value.** A packet built today carries `measured` where histology
  produced it, which is what R19 §3's rows have always meant in practice.

## 4. Open

- **Whether a coordinate should carry uncertainty.** A planned position is imprecise and a measured
  one is not exact either, and nothing here can say how well either is known. Deliberately not
  added: it must first be established that the targeting pipeline records anything quantitative.
  If it does not, `planned` carries the imprecision by itself and columns for it would never be
  filled.
- **Whether `coordinate_basis` is meaningful outside an atlas frame.** A probe-frame coordinate is
  the probe's own geometry, exact by construction and neither planned nor measured. It needs a
  third value, or the column needs to be nullable where the frame makes the question empty. Left
  until a packet carries a frame where this bites.
- **Whether a unit's basis is its own or inherited.** R28 §3 gives a unit a position in several
  frames, computed from its electrodes. A unit computed from `planned` electrode positions is
  `planned`, which suggests inheritance rather than an independent declaration — but nothing
  forbids a writer from asserting otherwise, and no packet yet carries `core.unit_coordinates`.

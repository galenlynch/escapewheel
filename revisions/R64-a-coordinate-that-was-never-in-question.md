# R64 — A Coordinate That Was Never In Question

| | |
|---|---|
| **Status** | **Accepted** 2026-09-03 |
| **Amends** | R58 §2.1 (the basis vocabulary), R58 §4 (settles the second open question, corrects the third) |
| **Depends on** | R8 (open vocabularies), R19 (coordinate frames), R58 (a coordinate declares its basis) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R58 §2.1 gives `coordinate_basis` two values. `planned` is where the probe was meant to go and
`measured` is where it was, and the difference between them is the targeting error — which is
why R58 put the column in the primary key rather than letting histology supersede the plan.

Both values presuppose that the position was in question. A probe-frame contact position is
not: contact 47 sits 470 µm up the shank because the shank was manufactured that way. Nothing
aimed at it and nothing measured it afterwards, and yet R58 made the column **required**.

### 1.1 The deferral was false when it was written

R58 §4 left this open "until a packet carries such a frame". Both packets on hand already did,
including the one R58 was argued from:

| packet | `probe` frame | `ccf` frame |
|---|---|---|
| `ecephys_776259`, built before R58 | 4,608 | 4,224 |
| `ecephys_786867`, built after it | 3,840 | 3,840 |

### 1.2 What the writer did with a required column and no honest value

All 3,840 probe-frame rows carry `measured`. The importer sets it in a loop over both frames,
justified by an argument that holds for only one of them:

> An exported file records where the probe was found, never where it was aimed: a targeting
> record does not reach NWB, so `planned` (R58 §2.1) cannot be imported from one.

True of `ccf`, and no argument at all about `probe`. R58 §2.2 forbids a **consumer** from
reading an unrecognised basis as ground truth — "a permissive default would read an unknown
basis as ground truth, which is the failure this column exists to prevent" — and nothing
stopped a **writer** asserting it outright. A consumer computing targeting error by
self-joining on `(electrode_id, coordinate_frame)` finds a `measured` probe-frame row that no
instrument ever measured.

### 1.3 The basis is about the claim, not about the frame

The tempting reading of §1.1 is that the frame decides the basis — atlas frames get one,
geometric frames do not. It is wrong, and a case in hand shows why:
`ecephys_786867`'s NWB carries `estimated_x`, `estimated_y` and `estimated_z`, a unit position
computed from its waveform. That is a probe-frame coordinate and an **observation**: it is
`measured`, in the same frame where a contact position is not.

So R58 §2.1's two axes are genuinely orthogonal, as it claimed. What was missing is a value on
the basis axis for a quantity that is true by construction.

## 2. Decision

### 2.1 A third value

`coordinate_basis` gains `nominal`:

| | |
|---|---|
| `planned` | where the probe was meant to go. Intent, before the fact, and possibly missed. |
| `measured` | where it was, established after the fact by observation. |
| `nominal` | where it is by construction. The geometry the instrument was built to, not an observation of this instance. |

A writer recording a position that no instrument observed and no one aimed **MUST** record
`nominal` and **MUST NOT** record `measured`.

`nominal` differs from `planned` in what a discrepancy would mean. A planned position can be
missed, and the miss is the measurement R58 exists to preserve. A nominal position cannot be
missed, because nothing was aimed: a contact that is not where the layout says it is means the
layout is wrong, not that the insertion went astray.

### 2.2 No schema change, and the migration is safe by construction

`coordinate_basis` is already declared `vocabulary: open` (R58 §2.2), so no validator rejects
`nominal` and no registry structure changes. Only the column's description and the writer move.

R58 §2.2's consumer rule is what makes the addition safe rather than merely permitted: a
consumer that does not recognise `nominal` **MUST NOT** treat it as `measured`, so an
unmodified reader downgrades a nominal coordinate to "not ground truth", which is exactly the
right answer. A vocabulary whose extensions degrade correctly is the reason R8 §4 makes these
open, and this is the first case to exercise it.

### 2.3 Why not the other two shapes R58 §4 named

**Nullable where the frame makes the question empty.** `coordinate_basis` is in the primary key
of both tables (R58 §2.1), and a null in a key column is not a value a key can be built on.

**Scoped to atlas frames, so `coordinate_frame` decides whether `coordinate_basis` applies.**
`coordinate_frame` is **open** (R19 §3). An open vocabulary cannot drive a requirement: a frame
nobody has declared yet would carry no defined obligation, so a writer adding one would not
know whether the column applies and a validator could not check that it had decided correctly.

## 3. What this does not change

- **No column is added or removed**, no type changes, and no primary key changes.
- **No rule changes.** The vocabulary was already open, so nothing was rejecting a third value.
- **`planned` and `measured` keep their meanings**, and every row correctly carrying one of
  them stays correct.
- **`coordinate_frame` is untouched.** R19 §3's frames stay orthogonal to a basis, which §1.3
  is the evidence for rather than an exception to.

## 4. Migration

Existing packets record `measured` on probe-frame rows: 3,840 in `ecephys_786867` and 4,608 in
`ecephys_776259`. Migration is regeneration, as R53 §5's was — these are importer outputs, and
no packet's bytes are edited in place (R14 §2.3).

Until a packet is rebuilt it overstates what it knows about a probe-frame coordinate. It does
not misstate an atlas one, which is where the claim is load-bearing, so a rebuild is warranted
rather than urgent.

## 5. Open

- **Whether a unit's basis is its own or inherited** — R58 §4's third open question, which
  stands. It is stated there as "no packet yet carries `core.unit_coordinates`"; that is
  **stale**, since `ecephys_776259` carries 6,540 rows of it, all in the `ccf` frame. The
  question itself is untouched by this revision, and §1.3's `estimated_*` case is now the
  concrete instance to settle it against: a unit position computed from a waveform is an
  observation whatever its electrodes' basis was, which argues against plain inheritance.
- **Whether `core.unit_coordinates.coordinate_frame` should declare `vocabulary: open`.** Its
  twin on `core.electrode_coordinates` does and it does not, though R28 §2-4's description says
  "Open, as R19 §3 left it". A registry inconsistency rather than a specification one, found
  while reading the declaration this revision amends.

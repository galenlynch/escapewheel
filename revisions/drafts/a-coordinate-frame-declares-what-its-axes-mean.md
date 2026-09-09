# A Coordinate Frame Declares What Its Axes Mean

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R19 §3 (the axis meaning, and the three reserved frame names); adds `core.coordinate_frames` and the reference `coordinate_frame` has never had |
| **Depends on** | R101 §3.1 (every string column declares `closed`, `open` or `free`), R19 §3 (the coordinate table and its axes), R46 §2 (a reference is declared or nothing checks it), R58 §2.1 (a frame and a basis are two facts), R59 §2.2 (the frame names the atlas), R83 §3 (report unresolvable rather than resolve), R88 §2 (session scope) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.electrode_coordinates` and `core.unit_coordinates` hold a position as `x_um`, `y_um` and
`z_um`, and R19 §3 names each of them the same way in every frame: *"their meaning is the
frame's."* Which way x points is therefore a fact about the frame, and a packet has nowhere to
put a fact about a frame — `coordinate_frame` is a bare string in two primary keys, resolving to
nothing.

This part gives a frame a row: what each axis measures, which anatomical convention the triple
follows where it follows one, and a reference so that the name is checked rather than assumed.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25), which
between them hold **27,557 coordinate rows** — 16,512 electrode positions and 11,045 unit
positions — in two frames, `ccf` and `probe`.

## 2. Background

Informative.

### 2.1 What R19 §3 left to the frame

R19 §3 introduced the three axis columns and settled their naming in one sentence: *"Axes are
named `x_um`, `y_um`, `z_um` in every frame, and their meaning is the frame's. CCF's `ml`, `ap`,
`dv` map onto them in that order, which the frame's definition fixes rather than this
specification."*

Deferring to the frame's definition is the right instinct — a rig frame and an atlas frame have
nothing in common, so no single mapping could serve both. The sentence assumes a frame *has* a
definition somewhere a consumer can read, and none of the three reserved names carries one. R19 §3 reserved `probe`, `ccf` and `stereotaxic` "with those meanings", and the
meanings it points at are the frames' own.

### 2.2 Where the axis order is written down

One artifact states the mapping, and it is not in any packet:

```python
#: R19 §3: CCF's `ml`, `ap`, `dv` occupy `x_um`, `y_um`, `z_um` in that order.
CCF_AXES = ("ccf_ml", "ccf_ap", "ccf_dv")
```

That is `escapewheel-writer`'s NWB adapter. A second implementation reading these packets has the
column names, the unit, and nothing else, so it must guess. The obvious guess is the order the
Allen CCFv3 array is indexed by: anterior-posterior, then dorsal-ventral, then medial-lateral.

Guessing that way is undetectable on the values. Under the adapter's order, `x_um` holds ML and
runs 1,828–5,780 µm across both packets, and `y_um` holds AP and runs 2,580–9,360; under the
volume's order the same two columns would be AP and DV. ML's extent is 0–11,400 µm and AP's is
0–13,200, so **both columns fall inside both extents** and a consumer who swaps them places every
electrode somewhere plausible and wrong. Nothing in the packet, and no range check a validator
could write, distinguishes the two readings.

`z_um` is the one column that does not fit either reading: it runs to **−1,607 µm** in
`ecephys_776259` and **−786** in `ecephys_786867`, against a DV extent starting at zero. A frame
declaring its axes would make that a question a consumer can ask.

### 2.3 What `coordinate_frame` resolves to

`coordinate_frame` sits in the primary key of both coordinate tables, carries R48 role `data`, and
declares no reference, so R46 §2's consequence applies unchanged: Tier 1 generates an anti-join
from a declared reference and from nothing else. A packet spelling the frame `ccf` in
`core.electrode_coordinates` and `CCF` in `core.unit_coordinates` holds two frames that no check
compares, and R58 §2.1 put the column in the key precisely so that the two rows would not collide.

The 8,448 `probe` rows show the second half of the problem. Their axes are `rel_x` and `rel_y`
from the NWB — across the shank and along it — so `z_um` is null in every one of them, and no
anatomical convention applies at all. A frame may have two axes rather than three, and they need
not be directions of the brain.

## 3. Decision

### 3.1 `core.coordinate_frames`

`core.coordinate_frames` is added:

| column | type | presence | role | vocabulary | description |
|---|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | — | The session, per R88 §2. |
| `coordinate_frame` | `string` | required | data | open | The frame's name, unique within the session. |
| `x_axis` | `string` | nullable | data | open | What `x_um` measures in this frame. |
| `y_axis` | `string` | nullable | data | open | What `y_um` measures. |
| `z_axis` | `string` | nullable | data | open | What `z_um` measures; null where the frame has two axes. |
| `orientation` | `string` | nullable | data | open | The anatomical convention the triple follows, where it follows one. |
| `description` | `string` | nullable | data | free | What the frame is, for a reader without the atlas. |

`coordinate_frame` declares `open` here as it does on both coordinate tables, which is what the
vocabulary draft's name-consistency check requires of one name across three tables.

Primary key `(session_id, coordinate_frame)`; sorted by it (R10 §2).

`core.electrode_coordinates.coordinate_frame` and `core.unit_coordinates.coordinate_frame`
**MUST** reference it on `(session_id, coordinate_frame)`, so a coordinate row naming an
undeclared frame is an orphan Tier 1 reports. A packet carrying coordinates **MUST** declare every
frame they name.

Session-scoped, because a frame's definition is a session's. R88 §2 scopes a table by whether it
reaches `core.sessions`, and R85 §1.3 measured why that is right rather than incidental for a
table keyed by a name: `headstage.slot3.port4` is `hardware_version` **1.8** in one session and
**0.1** in the other, so a name two sessions reuse names different things. Two rigs calling their
frame `stereotaxic` is the same collision one table over.

### 3.2 What each axis column holds

`x_axis`, `y_axis` and `z_axis` are open vocabularies naming what each column measures — `ml`,
`ap`, `dv` for an atlas or stereotaxic frame, `along_shank` and `across_shank` for a probe frame,
and a lab's own term where neither fits. Two axes of one frame **MUST NOT** name the same thing,
and one Tier 2 rule checks it.

`orientation` is separate because it answers a different question: an axis name says which
quantity the column holds, and the orientation says which way each one increases. It holds a
three-letter anatomical code — `RAS`, `LPS`, `PIR` and the rest — where the frame follows one, and
is null otherwise. Splitting them is what lets a packet state the half it knows: the NWB says its
CCF columns are `ccf_ml`, `ccf_ap` and `ccf_dv`, which fixes the axes and says nothing about
signs, so both packets declare three axes and no orientation.

A single compound value was the alternative, and it fails on the 8,448 `probe` rows: their axes
are not anatomical, so no three-letter code names them, and folding a permutation into the same
string that carries a sign convention repeats the conflation R58 §2.1 undid when it separated a
frame from a basis.

### 3.3 Where an axis value comes from

A writer **MUST** fill an axis from what its source states, and **MUST NOT** infer one from a
column's name, from the values' range, or from what the frame is usually taken to mean. This is
R67 §2.4's rule in a third place, and R83 §2 gives the reason: an inference that is right on the
data at hand fixes the wrong convention for every packet built afterwards, and a coordinate is
where a wrong convention is least visible.

Where the source states nothing, the column is null. A frame declaring no axes is conforming, and
what it buys over today is that the absence is a value a consumer can test.

### 3.4 A consumer meeting an undeclared axis

A consumer needing to know which quantity `x_um` holds, for a frame whose `x_axis` is null,
**MUST** report the coordinate unusable rather than assume a convention. That is R83 §3's rule for
a run that declares no channels, and it holds here for the same reason: the packet is conforming,
so failing it would be wrong, and resolving against a default would produce a plausible number in
the wrong place.

## 4. What this does not change

- **No coordinate value changes.** §2.2 is about the values being read wrongly, not written
  wrongly: `x_um`, `y_um` and `z_um` hold what they held, and nothing here re-bases or reorders
  one.
- **The frame stays in the coordinate tables' key.** R58 §2.1 keys both on `(electrode_id,
  coordinate_frame, coordinate_basis)`, and the new reference does not replace the name with an
  identifier. A frame name still appears in every coordinate row, because it is the key rather
  than a repetition the table could drop.

## 5. Consequence

39 tables become **40**, 330 columns become **337**, and 97 references become **99**. Tier 2 rules
go from 76 to **77**, the new one checking that two axes of one frame do not name the same thing,
and Tier 1 gains the anti-joins, the uniqueness check and the not-null checks the new table's
structure implies, none of them hand-written.

Six of the new columns are strings, so R101 §5's counts move with them: 39 open become **44** and
52 free become **53**, over 108 string columns.

Both packets declare two frames each: `ccf` with `x_axis` `ml`, `y_axis` `ap`, `z_axis` `dv` and
no orientation, and `probe` with `across_shank`, `along_shank` and null. The NWB adapter reads
those from `CCF_AXES` and from the `rel_x`/`rel_y` pair it already maps, so the comment at
`nwb.py:103` becomes a value in the packet rather than knowledge in the writer. Both packets are
rebuilt, which R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98 and R99 already require.

What the rebuild does **not** recover is the sign convention. The NWB states which quantity each
CCF column holds and never which way it increases, so `orientation` is null in both packets and
§3.4 makes a consumer say so. Declaring the frame does not answer the question §2.2 raises; it
makes the absence of an answer visible, where today a consumer guesses and gets a number.

`fixtures/build.py` gains the table and a `frame_without_axes` variant whose expected finding is
the orphan frame, taking the corpus from 27 packets to **28**.

## 6. Open

- **What a `stereotaxic` frame would declare.** R19 §3 reserved the name and neither packet uses
  it. Such a frame is measured from an animal's own skull landmark, so two sessions' frames of
  that name differ by where bregma was, and §3.1's row carries no origin to record that. The one
  artifact that could supply one declares nothing either: the AIND `rig.json` for
  `ecephys_786867` carries `rig_axes` and `origin` as **null**. Nothing has asked for it.
- **Whether `ccf` should name the atlas version.** R59 §2.2 makes the frame name the atlas, and
  `ccf` does not distinguish CCFv3 from a successor whose structure ids would differ. That is
  R59's question and it reaches `region_id` as much as the axes.
- **Whether a frame should declare its extent.** §2.2's `z_um` of −1,607 µm falls outside the DV
  extent of the atlas it claims, and a frame declaring bounds would make that checkable in SQL
  rather than noticeable by eye. It would also be the first core column asserting what an external
  atlas contains, which R3 §3.0 argues against.

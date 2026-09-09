# A Coordinate Frame Declares What Its Axes Mean

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R19 §3 (the axis meaning, and the three reserved frame names); adds `core.coordinate_frames` and `core.coordinate_frame_axes`, and the reference `coordinate_frame` has never had |
| **Depends on** | R101 §3.1 (every string column declares `closed`, `open` or `free`), R19 §3 (the coordinate table and its axes), R46 §2 (a reference is declared or nothing checks it), R58 §2.1 (a frame and a basis are two facts), R59 §2.2 (the frame names the atlas), R83 §3 (report unresolvable rather than resolve), R88 §2 (session scope), R3 §3.0 (a repeated value is a child table) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.electrode_coordinates` and `core.unit_coordinates` hold a position as `x_um`, `y_um` and
`z_um`, and R19 §3 names each of them the same way in every frame: *"their meaning is the
frame's."* Which way x points is therefore a fact about the frame, and a packet has nowhere to put
a fact about a frame — `coordinate_frame` is a bare string in two primary keys, resolving to
nothing.

This part gives a frame a row and each of its axes a row of its own: what the axis measures, which
way its values increase, and what unit they are in, however many axes the frame has. It also gives
`coordinate_frame` the reference it has never had, so that the name is checked rather than assumed.

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
definition somewhere a consumer can read, and none of the three reserved names carries one. R19 §3
reserved `probe`, `ccf` and `stereotaxic` "with those meanings", and the meanings it points at are
the frames' own.

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

### 2.4 Three axes is not how many a frame has

**8,448 of 27,557 coordinate rows — 31% — carry a null `z_um`.** Those are the `probe` rows, whose
axes are `rel_x` and `rel_y` from the NWB: a contact's position on a shank is two numbers, and the
third column is a hole every one of them leaves. A frame is not three-dimensional because the
table has three columns.

It reaches the other way too. A Neuroglancer coordinate space is routinely five-dimensional, and
nothing about an atlas registration or a rig makes three the limit; three is what `02` happened to
declare.

R3 §3.0 settles the shape for a repeated value: it is a child table, never a list, a delimited
string, or a column per occurrence. `core.array_dimensions` is what that looks like already —
keyed `(array_asset_id, axis_index)`, one row per axis, carrying each axis's name and unit — and
an array has as many axes as it has.

## 3. Decision

### 3.1 `core.coordinate_frames` and its axes

Two tables are added. The frame:

| column | type | presence | role | vocabulary | description |
|---|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | — | The session, per R88 §2. |
| `coordinate_frame` | `string` | required | data | open | The frame's name, unique within the session. |
| `description` | `string` | nullable | data | free | What the frame is, for a reader without the atlas. |

Primary key `(session_id, coordinate_frame)`; sorted by it (R10 §2); referencing `core.sessions`.

And its axes, one row each:

| column | type | presence | role | vocabulary | description |
|---|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | — | The session, per R88 §2. |
| `coordinate_frame` | `string` | required | data | open | The frame these axes belong to. |
| `axis_index` | `int64` | required | structural_index | — | Which axis, 0-based (R3 §6). |
| `axis_name` | `string` | required | data | open | What this axis measures. |
| `axis_direction` | `string` | nullable | data | open | Which way its values increase. |
| `unit` | `string` | nullable | data | open | The axis's unit, as a UCUM code (R101 §3.6). |

Primary key `(session_id, coordinate_frame, axis_index)`; referencing `core.coordinate_frames` on
`(session_id, coordinate_frame)` and `core.sessions` on `session_id`. A frame declares as many
axes as it has, which is two for a shank and five for a Neuroglancer space.

`core.electrode_coordinates.coordinate_frame` and `core.unit_coordinates.coordinate_frame`
**MUST** reference the frame table on `(session_id, coordinate_frame)`, so a coordinate row naming
an undeclared frame is an orphan Tier 1 reports. A packet carrying coordinates **MUST** declare
every frame they name.

Session-scoped, because a frame's definition is a session's. R88 §2 scopes a table by whether it
reaches `core.sessions`, and R85 §1.3 measured why that is right rather than incidental for a
table keyed by a name: `headstage.slot3.port4` is `hardware_version` **1.8** in one session and
**0.1** in the other, so a name two sessions reuse names different things. Two rigs calling their
frame `stereotaxic` is the same collision one table over.

### 3.2 What an axis row holds

`axis_name` says **which quantity** the axis measures — `ml`, `ap`, `dv` for an atlas or
stereotaxic frame, `along_shank` and `across_shank` for a probe frame, a lab's own term where
neither fits. Two axes of one frame **MUST NOT** name the same quantity, which one Tier 2 rule
checks.

`axis_direction` says **which way** its values increase: `right`, `left`, `anterior`, `posterior`,
`superior`, `inferior` and the rest, open so a frame that increases along something unanatomical
can say so. It is separate because it is a different fact, and nullable because a source may state
the quantity without stating the sign — which is the ordinary case, and what makes an anatomical
code like `RAS` three axis rows rather than a fourth column on the frame.

`x_um`, `y_um` and `z_um` are the frame's axes 0, 1 and 2 in that order. The columns are the
portable profile's slots and carry no meaning of their own; §6 records that a frame with more than
three axes can be declared and its coordinates cannot yet be stored.

### 3.3 Where an axis value comes from

A writer **MUST** fill an axis from what its source states. **A source's own naming of a field is
such a statement**: an NWB column called `ccf_ml` says its values are ML, and reading it is
reading the source rather than guessing.

A writer **MUST NOT** infer an axis from the packet's own column — `x_um` is a slot and not a
claim — nor from the values' range, nor from what a frame is conventionally taken to mean. `rel_x`
names a relative position and not an across-shank one, so a source stating only that states no
axis. This is R67 §2.4's rule in a third place, and R83 §2 gives the reason: an inference that is
right on the data at hand fixes the wrong convention for every packet built afterwards, and a
coordinate is where a wrong convention is least visible.

Where the source states nothing, the frame declares no axis row for it. A frame declaring none is
conforming, and what that buys over today is that the absence is a value a consumer can test.

### 3.4 A consumer meeting an undeclared axis

A consumer needing to know which quantity `x_um` holds, for a frame declaring no axis 0,
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

39 tables become **41**, 334 columns become **343**, and 100 references become **105**. Tier 1's
not-null checks go from 149 to **155**, and Tier 2 rules from 76 to **77**, the new one checking
that two axes of one frame do not name the same quantity. Tier 1 also gains the anti-joins and the
uniqueness checks the two tables' structure implies, none of them hand-written.

Six of the new columns are strings, so R101 §5's counts move with them: 39 open become **44** and
52 free become **53**, over 109 string columns. The counts are measured against the registry as
R104 left it.

Both packets declare two frames. `ccf` declares three axes — `ml`, `ap` and `dv`, from the NWB
columns `ccf_ml`, `ccf_ap` and `ccf_dv` that name them — with no direction, since the file states
which quantity each column holds and never which way it increases. `probe` declares **none**: its
source states `rel_x` and `rel_y`, which name a relative position and not an across-shank one, so
§3.3 forbids the adapter writing what its comment at `nwb.py:103` has been assuming. The 8,448
probe coordinates become coordinates whose axes are undeclared, which is what they have been all
along and what §3.4 now makes a consumer say.

A Stage 1 survey says that is not the adapter's oversight. The NWB describes `rel_x` as "rel_x
from merged", `settings.xml` offers `ELECTRODE_XPOS` and `ELECTRODE_YPOS`, and the sorted asset's
preprocessed record carries none of ProbeInterface's `ndim`, `si_units` or `contact_positions` —
three artifacts, three spellings of x and y, and no sentence saying which way either runs. What
all three do state is the probe model, `NP2000` and `Neuropixels 2.0 - Single Shank`, whose
geometry imec's specification fixes; so a probe frame's axes are held outside the packet, as a
species name is held by NCBI Taxonomy. Filling them is a lookup keyed on what
`core.probes.probe_type` already carries.

Both packets are rebuilt, which R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98, R99, R101 and R103
already require.

`fixtures/build.py` gains the two tables and a `frame_without_axes` variant whose expected finding
is the orphan frame, taking the corpus from 27 packets to **28**.

## 6. Open

- **Whether a coordinate should be a child table too.** §3.1 lets a frame declare five axes and
  §3.2 leaves the coordinate tables holding three, so a frame is declarable whose positions cannot
  be stored. Making a coordinate a row per axis is the same R3 §3.0 move one table over, and it
  costs a rewrite of 27,557 rows into roughly 76,000, a pivot in every consumer query, and three
  accepted revisions restated — which is why it is not taken here.
- **Whether `x_um`, `y_um` and `z_um` should be renamed.** They are slots, and their names imply a
  three-dimensional Cartesian frame that §2.4 measures 31% of coordinate rows not to have. A name
  saying which they are — `axis_0_value` and its fellows — would claim nothing, and would touch
  every row of both coordinate tables.
- **Where a probe model's geometry is looked up.** §5 measures that no artifact of a session
  states a shank's axes and that all three state the model. Turning a model into axes is a lookup
  someone must own — an adapter, an R17 §2 extension, or a nomenclature named the way R101 §3.6
  names one — and this part settles only that the packet may not guess.
- **What a `stereotaxic` frame would declare.** R19 §3 reserved the name and neither packet uses
  it. Such a frame is measured from an animal's own skull landmark, so two sessions' frames of that
  name differ by where bregma was, and §3.1's rows carry no origin to record that. The one artifact
  that could supply one declares nothing either: the AIND `rig.json` for `ecephys_786867` carries
  `rig_axes` and `origin` as **null**.
- **Whether `ccf` should name the atlas version.** R59 §2.2 makes the frame name the atlas, and
  `ccf` does not distinguish CCFv3 from a successor whose structure ids would differ. That is
  R59's question and it reaches `region_id` as much as the axes.

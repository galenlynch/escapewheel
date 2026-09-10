# R105 — A Coordinate Is a Value on a Declared Axis

| | |
|---|---|
| **Status** | **Accepted** 2026-09-09 |
| **Amends** | R19 §3 (the axis columns and the three reserved frame names), R28 §3 (the same columns on `core.unit_coordinates`), R59 §2.2 (the frame names a space; which published atlas it is becomes a declared fact); adds four tables and strikes six columns |
| **Depends on** | R3 §3.0 (a repeated value is a child table), R19 §3 (the coordinate table and its axes), R46 §2 (a reference is declared or nothing checks it), R56 §2.3 (a unit resolved one hop away), R58 §2.1 (a frame and a basis are two facts), R83 §2.3 (report unresolvable rather than resolve), R88 §2 (session scope), R101 §3.1 (every string column declares its vocabulary), R101 §3.4 (a value is spelled as its nomenclature spells it) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.electrode_coordinates` and `core.unit_coordinates` hold a position as `x_um`, `y_um` and
`z_um`, and R19 §3 names each of them the same way in every frame: *"their meaning is the
frame's."* Which way x points is therefore a fact about the frame, and a packet has nowhere to put
a fact about a frame — `coordinate_frame` is a bare string in two primary keys, resolving to
nothing.

Three columns is also not how many axes a frame has. This part gives a frame a row, each of its
axes a row, and each coordinate one value per axis, so a two-axis shank and a five-axis rendering
space are both sayable; `x_um`, `y_um` and `z_um` are struck, their names having claimed a
three-dimensional Cartesian frame that 31% of the rows do not have.

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

### 2.4 How many axes a frame has

**8,448 of 27,557 coordinate rows — 31% — carry a null `z_um`.** Those are the `probe` rows, whose
axes are `rel_x` and `rel_y` from the NWB: a contact's position on a shank is two numbers, and the
third column is a hole every one of them leaves. A frame is not three-dimensional because the
table has three columns.

It reaches the other way too. A Neuroglancer coordinate space is routinely five-dimensional, and
nothing about an atlas registration or a rig makes three the limit; three is what `02` happened to
declare, and `x`, `y` and `z` are what it happened to call them.

R3 §3.0 settles the shape for a repeated value: it is a child table, never a list, a delimited
string, or a column per occurrence. `core.array_dimensions` is what that looks like already —
keyed `(array_asset_id, axis_index)`, one row per axis, carrying each axis's name and unit — and
an array has as many axes as it has.

Nothing reads the three columns. `escapewheel-reader`, `escapewheel-validator` and `rules.json`
name none of them; the only mention outside the writer is `fixtures/build.py` filling them.

### 2.5 What a session's artifacts state about a frame

A Stage 1 survey of both frames found that the packet's own sources **name** the field each value
came from and say nothing about what it means. Neither what a shank's axes measure nor which way
they run nor which atlas a CCF coordinate is in appears anywhere.

For the shank: the NWB describes `rel_x` as **"rel_x from merged"**, Open Ephys offers
`<ELECTRODE_XPOS>` and `<ELECTRODE_YPOS>`, and the sorted asset's preprocessed record is a
SpikeInterface provenance object carrying none of ProbeInterface's `ndim`, `si_units`,
`contact_positions` or `contact_plane_axes`. Three artifacts, three spellings of x and y, and no
sentence saying which way either runs. The geometry shows it — 2 distinct `ELECTRODE_XPOS` values
against 192 `ELECTRODE_YPOS` over 2,865 µm — and a writer may not read it, because a probe with
equal counts on both axes would defeat the inference. What all three state is the model, `NP2000`
and "Neuropixels 2.0 - Single Shank", whose contact geometry imec's specification fixes.

For the atlas: `ccf_coordinate_transform` is **null** in `rig.json`, `session.json` and
`processing.json` alike, the NWB describes `ccf_ap` as "ccf_ap from merged", and no artifact names
a version, an annotation volume or a template. `ccf` is the adapter's own label.

## 3. Decision

### 3.1 `core.coordinate_frames`

| column | type | presence | role | vocabulary | description |
|---|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | — | The session, per R88 §2. |
| `coordinate_frame` | `string` | required | data | open | The session's own name for this space. |
| `atlas` | `string` | nullable | data | open | The published atlas this space is, where it is one. |
| `atlas_version` | `string` | nullable | data | open | That atlas's version, spelled as it spells it — `CCFv3`. |
| `description` | `string` | nullable | data | free | What the frame is, for a reader without the atlas. |

Primary key `(session_id, coordinate_frame)`; sorted by it (R10 §2); referencing `core.sessions`.

`core.electrode_coordinates.coordinate_frame` and `core.unit_coordinates.coordinate_frame`
**MUST** reference it on `(session_id, coordinate_frame)`, so a coordinate naming an undeclared
frame is an orphan Tier 1 reports.

The atlas is two columns rather than a spelling of the name. R59 §2.2 made the frame name the
atlas, and a name cannot carry a version without a rename on every row that holds it: two packets
both saying `ccf` may be in CCFv3 and in a successor whose structure ids differ, and comparing
labels cannot tell. Comparing `atlas` and `atlas_version` can, and **null against null reads as
unknown rather than as agreement** — which is what §2.5 measures both packets to be. A writer
**MUST NOT** fill either from a name: `ccf` is a label, not a version.

Session-scoped, because a frame's definition is a session's. R88 §2 scopes a table by whether it
reaches `core.sessions`, and R85 §1.3 measured why that is right for a table keyed by a name:
`headstage.slot3.port4` is `hardware_version` **1.8** in one session and **0.1** in the other, so
a name two sessions reuse names different things.

### 3.2 An axis row

| column | type | presence | role | vocabulary | description |
|---|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | — | The session, per R88 §2. |
| `coordinate_frame` | `string` | required | data | open | The frame these axes belong to. |
| `axis_index` | `int64` | required | structural_index | — | Which axis, 0-based (R3 §6). |
| `axis_name` | `string` | required | data | open | The source's own name for what this axis holds. |
| `axis_direction` | `string` | nullable | data | open | Which way its values increase. |
| `unit` | `string` | nullable | data | open | The axis's unit, as a UCUM code (R101 §3.6). |

`core.coordinate_frame_axes` is keyed `(session_id, coordinate_frame, axis_index)` and references
`core.coordinate_frames` and `core.sessions`. A frame declares **as many axis rows as it has
axes**, which is two for a shank and five for a rendering space.

`axis_name` says which quantity, in the source's own words: `ccf_ml` where the NWB's electrodes
table has a column of that name, `rel_x` where it has one of that. Two axes of one frame **MUST
NOT** carry the same name, which one Tier 2 rule checks. `axis_direction` says
which way its values increase — `right`, `anterior`, `superior` and the rest — and is a separate
column because it is a separate fact, which is what makes an anatomical code like `RAS` three axis
rows rather than a fourth column on the frame.

`axis_direction` is **nullable**, and that is what lets a frame record its axes without claiming
to interpret them. `axis_name` is not: a writer that put a value on an axis read it from
somewhere, and §3.4 makes recording where the requirement.

### 3.3 A coordinate's values

`core.electrode_coordinate_values` and `core.unit_coordinate_values` are added, one row per axis
per coordinate:

| column | type | presence | role | vocabulary | description |
|---|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | — | The session, per R88 §2. |
| `electrode_id` / `unit_id` | `int32` | required | identifier | — | The thing positioned. |
| `coordinate_frame` | `string` | required | data | open | The frame, with `coordinate_basis` completing the parent's key. |
| `coordinate_basis` | `string` | required | data | open | What the coordinate asserts (R58 §2.1). |
| `axis_index` | `int64` | required | structural_index | — | Which of the frame's axes this value is on. |
| `axis_value` | `float64` | required | data | — | The value, in the axis's `unit`. |

Each is keyed by its parent's key plus `axis_index`, and the two parents differ:
`core.electrode_coordinates` is keyed `(electrode_id, coordinate_frame, coordinate_basis)` and
`core.unit_coordinates` on `(session_id, unit_id, coordinate_frame, coordinate_basis)`, so the
child of each mirrors it rather than imposing a shape of its own. Each references its parent
coordinate row, `core.coordinate_frame_axes` on `(session_id, coordinate_frame, axis_index)`, and
`core.sessions`. `axis_value` declares
`unit_from: "core.coordinate_frame_axes.unit"`, which R56 §2.3's one-hop form resolves through
that reference — so no column name carries a unit and a frame in millimetres needs no second set
of columns.

`x_um`, `y_um` and `z_um` are **struck** from both parent tables, which keep `region_id`,
`region_label` and `processing_run_id`: those are facts about a coordinate rather than about an
axis, and moving them into the long form would repeat each of them once per axis, which R3 §3.0
forbids.

The reference to the axis row is what makes arity checkable. A coordinate carrying a value on an
axis its frame never declared is an orphan Tier 1 reports, so a frame's axis count and its
coordinates' shape cannot disagree.

A coordinate **MAY** carry values on fewer axes than its frame declares, where its source states
none on the rest, and a consumer **MUST NOT** read an absent axis row as a zero — it is a position
the source did not state on that axis. That is what a null in the struck columns said, in the form
the child table has. Neither packaged session omits one: 19,109 `ccf` coordinates on three axes and
8,448 `probe` coordinates on two come to exactly the 74,223 value rows §5 counts.

### 3.4 What a writer records about an axis

A writer **MUST** record, for each axis, what it read and where it put it. That is always
answerable, because a writer necessarily chose: `CCF_AXES = ("ccf_ml", "ccf_ap", "ccf_dv")` is the
adapter deciding that axis 0 takes `ccf_ml`'s values, and the packet has been losing that decision
rather than lacking it.

`axis_name` holds **whatever the source called the field the values came from, verbatim** — the
source's name becomes a value in the packet, not a column of it. An NWB whose electrodes table has
a column `ccf_ml` yields an axis row whose `axis_name` is the string `ccf_ml`.

This is R22 §3's rule for a scorer's label: recorded as the source emitted it, never rewritten. A
writer **MUST NOT** normalise it, translate it, strip part of it, or replace it with what the
quantity is conventionally taken to be. An axis named `rel_x` says the packet's axis 0 holds what
the NWB called `rel_x`, which is a fact; naming it `across_shank` would be a claim no source
supports, and naming it `x` would discard the only trace of where the value came from.

`unit` **MUST** be declared, and a writer knows it by construction: whatever unit it wrote the
values in, it wrote them. These packets' coordinates are micrometres, which R19 §3 declared in
naming the columns `x_um`, `y_um` and `z_um`, and which the adapter carries forward when those
names go.

`axis_direction` is the one an adapter may not supply. Which way an axis increases is an
interpretation of the source rather than a report of it, and §2.2 measures why the difference
matters: a swap between ML and AP is undetectable on the values, so an inference that is right on
the data at hand fixes the wrong convention for every packet built afterwards (R83 §2). A writer
**MUST** leave it null where its source does not state it, which is R67 §2.4's rule in a third
place.

### 3.5 A consumer meeting an undeclared axis

A consumer needing to know **which way** an axis runs, where its `axis_direction` is null, **MUST**
report the coordinate unusable for that purpose rather than assume a convention. An `axis_name` is
the source's word and not an interpretation: `rel_x` tells a consumer where the value came from and
not whether it runs across the shank. That is R83 §2.3's rule for a run
that declares no channels, and it holds here for the same reason: the packet is conforming, so
failing it would be wrong, and resolving against a default would produce a plausible number in the
wrong place.

## 4. What this does not change

- **No coordinate value changes.** §2.2 is about values being read wrongly, not written wrongly.
  Every number a packet holds it still holds, at the axis its frame declares, and nothing here
  re-bases or reorders one.
- **The frame stays in both coordinate tables' keys.** R58 §2.1 keys `core.electrode_coordinates`
  on `(electrode_id, coordinate_frame, coordinate_basis)` and R28 §3 keys `core.unit_coordinates`
  on `(session_id, unit_id, coordinate_frame, coordinate_basis)`, and the new reference replaces
  neither name with an identifier: a frame name is what the child rows join on.

## 5. Consequence

39 tables become **43**, 334 columns become **351** — 23 added and six struck — and 100 references
become **111**. Tier 1's not-null checks go from 149 to **167**, and Tier 2 rules from 76 to
**77**, the new one checking that two axes of one frame do not name the same quantity. Twelve of
the new columns are strings, so R101 §5's counts move with them: 39 open become **50** and 52 free
become **53**, over 115 string columns. The counts are measured against the registry as R104 left
it.

The 27,557 coordinate rows keep their annotation and provenance and give up their values to
**74,223 value rows**, 2.69 per coordinate. Nothing reads the struck columns (§2.4), so no consumer
breaks; `fixtures/build.py` is the only caller and writes the child rows instead.

Both packets declare two frames. `ccf` declares three axis rows named `ccf_ml`, `ccf_ap` and
`ccf_dv`, and `probe` two named `rel_x` and `rel_y` — the NWB columns the adapter read, verbatim. Both carry `unit` of `um`
and no direction, since no artifact of either session says which way any of the five increases,
and both leave `atlas` and `atlas_version` **null**, since none names the atlas either. Both
packets are rebuilt, which R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98, R99, R101 and R103 already
require.

`fixtures/build.py` gains the four tables and a `frame_without_axes` variant whose expected finding
is a coordinate value on an axis no frame declares, taking the corpus from 27 packets to **28**.

## 6. Open

- **When a probe's axes would be worth interpreting.** Not yet, and the condition is testable. The
  probe frame declares axes named `rel_x` and `rel_y` (§3.4), which say where each value came from
  and not which runs along the shank. Across all 22 probes of both packets those two axes carry **2
  distinct values against 192**, and on none of them are the counts equal — so a consumer sees
  which is the shank without being told, and the questions that use these coordinates mostly do not
  ask: a contact layout plots one axis against the other whichever is which, and inter-contact
  distance is the same either way. What an interpretation decides is which direction is depth, and
  2 against 192 decides that here.

  The trigger is a probe whose contact counts do not separate its axes — a square grid, or a
  multi-shank layout whose shank spacing and contact pitch give similar counts. Then §3.4 forbids
  the writer inferring and the consumer has nothing to count, and turning a model into axis names
  becomes a lookup someone must own: keyed on `core.probes.probe_type`, which already carries
  `NP2000`, and held in an adapter, an R17 §2 extension, or a nomenclature named the way R101 §3.6
  names one.
- **What a `stereotaxic` frame would declare.** R19 §3 reserved the name and neither packet uses
  it. Such a frame is measured from an animal's own skull landmark, so two sessions' frames of that
  name differ by where bregma was, and §3.1's row carries no origin to record that. The AIND
  `rig.json` for `ecephys_786867` carries `rig_axes` and `origin` as **null**, so the one artifact
  that could supply one declares nothing either.
- **Whether a frame should declare its extent.** §2.2's `z_um` of −1,607 µm falls outside the DV
  extent of the atlas it claims, and a frame declaring bounds would make that checkable in SQL
  rather than noticeable by eye. It would also be the first core column asserting what an external
  atlas contains, which R3 §3.0 argues against.

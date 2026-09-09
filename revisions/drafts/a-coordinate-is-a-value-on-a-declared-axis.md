# A Coordinate Is a Value on a Declared Axis

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R19 §3 (the axis columns and the three reserved frame names), R28 §2–4 (the same columns on `core.unit_coordinates`), R59 §2.2 (the frame names a space; which published atlas it is becomes a declared fact); adds four tables and strikes six columns |
| **Depends on** | R3 §3.0 (a repeated value is a child table), R19 §3 (the coordinate table and its axes), R46 §2 (a reference is declared or nothing checks it), R56 §2.3 (a unit resolved one hop away), R58 §2.1 (a frame and a basis are two facts), R83 §3 (report unresolvable rather than resolve), R88 §2 (session scope), R101 §3.1 (every string column declares its vocabulary), R101 §3.4 (a value is spelled as its nomenclature spells it) |
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

A Stage 1 survey of both frames found that the packet's own sources state neither what a shank's
axes are nor which atlas a CCF coordinate is in.

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
| `axis_name` | `string` | nullable | data | open | What this axis measures. |
| `axis_direction` | `string` | nullable | data | open | Which way its values increase. |
| `unit` | `string` | nullable | data | open | The axis's unit, as a UCUM code (R101 §3.6). |

`core.coordinate_frame_axes` is keyed `(session_id, coordinate_frame, axis_index)` and references
`core.coordinate_frames` and `core.sessions`. A frame declares **as many axis rows as it has
axes**, which is two for a shank and five for a rendering space.

`axis_name` says which quantity — `ml`, `ap`, `dv`, `along_shank`, a lab's own term. Two axes of
one frame **MUST NOT** name the same quantity, which one Tier 2 rule checks. `axis_direction` says
which way its values increase — `right`, `anterior`, `superior` and the rest — and is a separate
column because it is a separate fact, which is what makes an anatomical code like `RAS` three axis
rows rather than a fourth column on the frame.

Both are **nullable**, and that is what lets a frame state its arity without stating its meaning.
The probe frame declares two axis rows with null names: how many numbers a contact's position has
is knowable from the source (§2.5), and what they measure is not.

### 3.3 A coordinate's values

`core.electrode_coordinate_values` and `core.unit_coordinate_values` are added, one row per axis
per coordinate:

| column | type | presence | role | description |
|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | The session, per R88 §2. |
| `electrode_id` / `unit_id` | `int32` | required | identifier | The thing positioned. |
| `coordinate_frame` | `string` | required | data | The frame, with `coordinate_basis` completing the parent's key. |
| `coordinate_basis` | `string` | required | data | What the coordinate asserts (R58 §2.1). |
| `axis_index` | `int64` | required | structural_index | Which of the frame's axes this value is on. |
| `axis_value` | `float64` | required | data | The value. |

Each references its parent coordinate row, `core.coordinate_frame_axes` on `(session_id,
coordinate_frame, axis_index)`, and `core.sessions`. `axis_value` declares
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

### 3.4 Where an axis value comes from

A writer **MUST** fill `axis_name`, `axis_direction` and `unit` from what its source states. **A
source's own naming of a field is such a statement**: an NWB column called `ccf_ml` says its values
are ML, and reading it is reading the source rather than guessing.

A writer **MUST NOT** infer an axis from the packet's own column, from the values' range, or from
what a frame is conventionally taken to mean. `rel_x` names a relative position and not an
across-shank one, so a source stating only that states no axis name. This is R67 §2.4's rule in a
third place, and R83 §2 gives the reason: an inference that is right on the data at hand fixes the
wrong convention for every packet built afterwards, and a coordinate is where a wrong convention is
least visible.

Where the source states nothing, the column is null and the axis row still exists — the frame has
that axis whether or not anyone can say what it measures.

### 3.5 A consumer meeting an undeclared axis

A consumer needing to know which quantity an axis holds, where its `axis_name` is null, **MUST**
report the coordinate unusable rather than assume a convention. That is R83 §3's rule for a run
that declares no channels, and it holds here for the same reason: the packet is conforming, so
failing it would be wrong, and resolving against a default would produce a plausible number in the
wrong place.

## 4. What this does not change

- **No coordinate value changes.** §2.2 is about values being read wrongly, not written wrongly.
  Every number a packet holds it still holds, at the axis its frame declares, and nothing here
  re-bases or reorders one.
- **The frame stays in the coordinate tables' key.** R58 §2.1 keys them on `(electrode_id,
  coordinate_frame, coordinate_basis)`, and the new reference does not replace the name with an
  identifier: a frame name is what the child rows join on.

## 5. Consequence

39 tables become **43**, 334 columns become **351** — 23 added and six struck — and 100 references
become **111**. Tier 1's not-null checks go from 149 to **166**, and Tier 2 rules from 76 to
**77**, the new one checking that two axes of one frame do not name the same quantity. Twelve of
the new columns are strings, so R101 §5's counts move with them: 39 open become **50** and 52 free
become **53**, over 115 string columns. The counts are measured against the registry as R104 left
it.

The 27,557 coordinate rows keep their annotation and provenance and give up their values to
**74,223 value rows**, 2.69 per coordinate. Nothing reads the struck columns (§2.4), so no consumer
breaks; `fixtures/build.py` is the only caller and writes the child rows instead.

Both packets declare two frames. `ccf` declares three axis rows — `ml`, `ap` and `dv`, from the NWB
columns that name them — with `unit` of `um`, no direction, and both `atlas` and `atlas_version`
**null**, since no artifact of either session names the atlas. `probe` declares two axis rows with
`unit` of `um` and null names, since `rel_x` and `rel_y` state a count and not a meaning. Both
packets are rebuilt, which R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98, R99, R101 and R103 already
require.

`fixtures/build.py` gains the four tables and a `frame_without_axes` variant whose expected finding
is a coordinate value on an axis no frame declares, taking the corpus from 27 packets to **28**.

## 6. Open

- **Where a probe model's geometry is looked up.** §2.5 measures that no artifact of a session
  states a shank's axes and that all three state the model. Turning a model into axis names is a
  lookup someone must own — an adapter, an R17 §2 extension, or a nomenclature named the way R101
  §3.6 names one — and this part settles only that a packet may not guess.
- **What a `stereotaxic` frame would declare.** R19 §3 reserved the name and neither packet uses
  it. Such a frame is measured from an animal's own skull landmark, so two sessions' frames of that
  name differ by where bregma was, and §3.1's row carries no origin to record that. The AIND
  `rig.json` for `ecephys_786867` carries `rig_axes` and `origin` as **null**, so the one artifact
  that could supply one declares nothing either.
- **Whether a frame should declare its extent.** §2.2's `z_um` of −1,607 µm falls outside the DV
  extent of the atlas it claims, and a frame declaring bounds would make that checkable in SQL
  rather than noticeable by eye. It would also be the first core column asserting what an external
  atlas contains, which R3 §3.0 argues against.

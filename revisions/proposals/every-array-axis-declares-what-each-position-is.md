# Every array axis declares what each position is

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-28 |
| **Based on** | `8938863b52926f43ec71b26245ed45836ca08369` |
| **Decision domain** | specification |
| **Affects** | Part 02 §8.3, Part 02 §9.4 and Part 02 §11.6; Part 03 §6.3 and Part 03 §6.5; `core.array_dimensions`, `core.array_channels`, `core.unit_electrodes` and `analysis.array_dimensions`; a new core table and its analysis mirror holding the row each labelled position stands for; the registry meta-schema's `positions_in`; the reference writer, reader and validator; the `outside_array_floor` and `unresolved_externals` fixtures; both session packets |

## 1. Problem

A packet describes each axis of a dense array with one row of `core.array_dimensions`. Besides
naming the axis, the row says what each position along it stands for, in one of four forms that
R20 §2 introduced and Part 03 §6.3 now governs:

| form | columns | the position at index *k* stands for | example in the session packets |
|---|---|---|---|
| tick | `clock_id`, `origin_tick`, `step_tick_num`, `step_tick_den` | tick `origin_tick + k × step` on that clock | an LFP time axis |
| numeric | `origin_value`, `step_value`, `coordinate_unit` | the value `origin_value + k × step_value` in that unit | a waveform's sample axis: sample *k* − 60 |
| irregular | `coordinate_array_asset_id` | the value at index *k* of a 1-D array | none |
| labelled | `coordinate_resource`, `coordinate_position_column` | the row of the named table whose position column holds *k* | an LFP channel axis: the row of `core.array_channels` whose `channel_index` is *k* |

The mean-waveform array `core.waveform_mean` holds one template per unit, per channel, per sample.
The reference writer declares its three axes like this:

| `axis_index` | `dimension_name` | declared form |
|---|---|---|
| 0 | `unit` | none |
| 1 | `channel` | labelled: `core.unit_electrodes`, position column `channel_index` |
| 2 | `sample` | numeric: origin −60, step 1, unit `{sample}` |

Each of the three problems below is visible in those three rows.

### 1.1 No form can say which unit a position holds

The unit axis declares nothing, so a consumer has only the order to go on and reads the unit at
index *k* as `unit_id` *k*. Until commit `0ab4e89` the writer filled the axis in the order its
analyzer files list units, which differs from `unit_id` order, so templates were paired with the
wrong units (§2.1). Nothing reported the mismatch.

The writer could not have declared the unit axis correctly. A labelled axis needs a table with one
row per position of this array, holding the index and the unit it stands for, and no such table
exists.

### 1.2 Nothing declares that the channel axis depends on the unit axis

A unit's template covers only the contacts it was detected on, so channel index *j* holds a
different electrode for each unit. The electrode at channel index *j* of the unit at index *i* is
the `core.unit_electrodes` row whose `unit_id` is that unit's and whose `channel_index` is *j*.
Nothing in the packet says that the channel axis's rows depend on the unit axis, so a consumer
following the declaration reads every row whose `channel_index` is *j*: for *j* = 0 that is 4,505
rows in `ecephys_786867`, one per unit.

R20 §2.4 requires a coordinate table to be keyed by `array_asset_id`, so that its rows belong to
one array. `core.unit_electrodes` has no such column. R100 §2.3 recorded this case, and its §5 left
open "whether the tie belongs in the registry or stays the named resource's own business" until a
third case arose. The waveform unit axis is that third case.

### 1.3 Part 03 §6.3 and R20 §3 disagree about an axis that declares nothing

R20 §3 permits an axis to declare no form. Part 03 §6.3 requires every axis to declare one, as
Part 01 §3.17 does of every array asset. The ledger records R20 §3 as applied at Part 03 §6.3, but
commit `4ce6f09`, which compiled v0.2 from v0.1 and the first 64 revisions, wrote the requirement
there and dropped the permission. No rule checks either statement, so the waveform unit axis breaks
the current text and validates clean.

An axis that declares nothing is ambiguous. R20 §3 meant it to say that the positions carry only
their order. The waveform unit axis declares nothing for a different reason: its positions stand
for units, and no form could say so. A consumer cannot tell the two apart.

## 2. Evidence

The measurements use the two session packets built at the baseline with the fixed waveform source
(the `packet-wf` builds): `ecephys_786867`, ten probes and 4,505 sorted units, and
`ecephys_776259`, twelve probes and 6,781. Each has `core.waveform_mean`, of shape (4,505, 26,
150) and (6,781, 26, 150), and `ecephys_776259` also has `core.waveform_sd` with the same shape.
Each probe also contributes one LFP array of 96 channels. Both packets validate with no errors.
Section 2.1 alone uses the builds made before the fix.

### 2.1 The unit axis held the wrong unit at 3,971 and 6,781 indices

The waveform source stores each template on the unit's own contacts and zeroes the rest of the 26
channels. A template therefore has non-zero samples on at most as many channels as its unit has
rows in `core.unit_electrodes`, and a count above that proves the index holds a different unit.
Reading the unit at index *k* as `unit_id` *k*:

| indices | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| non-zero on more channels than that unit has contacts | 558 | 1,680 |
| non-zero on exactly as many channels as that unit has contacts | 3,354 | 3,368 |

The actual order was recovered by placing each sorting run's units, in `unit_id` order, as one
contiguous block, taking at each step the one run whose units fit. The blocks follow the analyzer's
run order: `sorting_run_id` 0, 2, 3, 4, 9, 1, 5, 6, 7, 8 in `ecephys_786867`, and 4 to 9, 11, 0 to
3, 10 in `ecephys_776259`. Under that recovered order, 3,971 of 4,505 indices in `ecephys_786867`
hold a unit other than `unit_id` *k*, and all 6,781 in `ecephys_776259` do.

### 2.2 The fixed order holds by a numbering convention that nothing declares

Since commit `0ab4e89`, the waveform source places units in `unit_id` order, and a unit with no
template keeps its index with no channels. In the rebuilt packets every index of
`core.waveform_mean` passes the §2.1 test exactly: 4,505 of 4,505 and 6,781 of 6,781. In
`core.waveform_sd`, 6,779 indices match and 2 are non-zero on fewer channels, where the deviation is
exactly zero on a contact. Every table matches the earlier build except the build's own run
timestamps.

Part 02 §12.1 numbers units by ascending `(sorting_run_id, curation_id, local_unit_label)` from
zero, so the unit at index *k* is `unit_id` *k* in both packets. The equality holds only because
each array holds every unit in its packet. An array holding one probe's units, or only the units a
curation kept, places `unit_id` *k* somewhere else, and a consumer reading the index as the
identifier relies on a convention no declaration states.

### 2.3 Only the waveform arrays are affected

| `core.array_dimensions` rows | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| all | 23 | 30 |
| declaring no form | 1 | 2 |
| naming `core.unit_electrodes` | 1 | 2 |

In both packets, the rows declaring no form are exactly the waveform unit axes, and the rows
naming `core.unit_electrodes` are exactly the waveform channel axes. Of the 64 fixture packets
under `fixtures/packets/`, two carry arrays, `outside_array_floor` and `unresolved_externals`. All
10 of their axes declare no form, because `fixtures/build.py` catalogues each array with a `unit`
and a `sample` axis and nothing else.

### 2.4 No rule or prose states R20 §2.4's keying rule

The ledger disposes of R20 §2.4 as `registry`, pointing at `core.array_dimensions` as a whole. No
registry declaration can express it: the registry can require a named position column to have the
role `structural_index`, as R100 §2.2 does, but not require the named table to carry
`array_asset_id`. No current part states the rule either. The two coordinate tables in use are tied
to their arrays in different ways:

| table | primary key | tied to one axis of one array by |
|---|---|---|
| `core.array_channels` | `array_asset_id`, `channel_index` | `array_asset_id` and `axis_index`, which reference `core.array_dimensions` |
| `core.unit_electrodes` | `session_id`, `unit_id`, `electrode_id` | the unit at the same array's unit-axis index, which nothing declares |

### 2.5 No key fixes a channel's index

Where a channel sits on an axis is a fact of how the array was assembled. On each LFP array,
exactly one of the 96 channels sits at the index its electrode would have if channels were ordered
by `electrode_id`: 10 of 960 rows in `ecephys_786867` and 12 of 1,152 in `ecephys_776259`. On the
waveform arrays, every `core.unit_electrodes.channel_index` equals the electrode's rank in its
sorting run's channel order, in 114,945 of 114,945 and 171,280 of 171,280 rows, while ordering by
`electrode_id` matches 102,112 and 151,280. The waveform order is this source's convention, and
the LFP order follows no key at all, so each labelled position needs its label stored.

### 2.6 The storage layer cannot hold the labels

The storage layer was examined as an owner of the labels, since a Zarr store can hold arrays of
coordinates beside the data.

- **Referenced arrays cannot be annotated.** Every LFP array in both packets is a Zarr v2 array
  inside the source NWB's store, which `packet.json` locates by an external `file://` URI and
  Part 03 §6.1 permits. A packet writes nothing there, so any fact about those axes lives in
  tables.
- **OME-Zarr 0.6 (released 2026-09-14) describes images.** A multiscale image needs two or three
  space axes, and its channel axis carries no identity per position.
- **The Zarr conventions describe space.** The `spatial`, `proj` and `multiscales` conventions
  under the `zarr-conventions` organisation describe spatial transforms, coordinate reference
  systems and pyramid levels; none references a row of an external table.
- **Coordinate arrays are values, not references.** A prototype stored `unit_id` as a 1-D Zarr
  array and `electrode_id` as a 2-D one, with −1 at an unlabelled index, in a group xarray opens
  unaided. It took 35,108 bytes for `ecephys_786867`, and a numpy check caught three injected
  defects in 22 ms. That check is code written for those two arrays: nothing declares that the
  values name units or electrodes, and it cannot reach a referenced array.

Other formats leave the dependent channel axis unstated. NWB's `Units.waveform_mean` does not say
which electrode each channel holds; `waveform_mean_index`, which would have, was merged into
nwb-schema by pull request 576 on 2024-04-25 and reverted by pull request 595 on 2024-11-15, and
issue 615 remains open. SpikeInterface pads a template to the most channels any unit has and
records a boolean mask per unit, so the slot at index *k* is the *k*-th channel the mask selects, in
ascending channel order.

### 2.7 One label table measured on both packets

The table §4.2 prefers was built from both `packet-wf` builds, with one row per labelled position:
each unit index of each waveform array, each channel index a unit's template covers, and each LFP
channel. The discriminator sits on the axis row, so a label row holds only the array, the axis, the
two indices and an integer identifier. Checks ran in DuckDB 1.5.5 over Parquet files, as the
median of 9 runs.

| | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| label rows | 120,410 | 357,274 |
| bytes, zstd-compressed Parquet | 107,273 | 282,937 |
| every label names a row, one anti-join per named resource | 8.4 ms | 13.9 ms |
| the same check as one join over every resource | 1,003 ms | 4,016 ms |
| primary key unique | 7.1 ms | 16.0 ms |
| waveform channel positions without a label | 2,185 of 117,130 | 10,052 of 352,612 |

Every check returns no rows, and no axis names one row twice. A position without a label is
padding: a unit with fewer than 26 contacts leaves the rest of its channel indices empty. A
generated existence check has to be one anti-join per named resource: the single join checks the
same thing 120 to 288 times more slowly.

An earlier prototype, which also carried the resource on every row, compared integer labels with
the name labels Part 02 §8.3 requires of a paired value today. Names cost 108,140 bytes against
106,507, and finding the units with a template on one electrode took 3.5 ms against 2.3 ms. It also
built an xarray `DataArray` with `unit_id` and a 2-D `electrode_id` as coordinates in 6.7 ms, against
6.1 ms from the Zarr coordinate arrays of §2.6.

## 3. Desired outcome and constraints

- A consumer can say what every position of every axis stands for from the packet's declarations,
  without knowing how the writer numbered identifiers or which tables need special handling.
- A packet with an axis that declares nothing is reported as non-conforming, so a defect like
  §2.1's surfaces at validation rather than in an analysis.
- A position standing for a row of a table is a checked reference, on a packet-owned array and on
  a referenced one alike.
- Arrays stay generic, as Part 01 §3.17 requires: an axis is declared per packet, not per kind of
  array, and no table is added per kind of array or per kind of row an axis can hold.
- `core.unit_electrodes` keeps its meaning: the contacts a unit was detected on, whether or not any
  array uses it.
- Each fact has one owner. Which electrode a channel index holds is stated once.
- The cost stays proportional to the positions labelled.

## 4. Options and tradeoffs

The preferred direction makes seven changes:

- Escapewheel owns the binding of positions to rows, and the Zarr layer carries only axis names
  (§4.1).
- One core table, `core.array_labels`, holds the row each labelled position stands for, as an
  integer identifier (§4.2).
- Part 02 §8.3 lets a paired value sit one declared reference away and be an integer identifier
  (§4.3).
- An axis row can name another axis its labels depend on (§4.4).
- Every axis declares a form, and an axis whose positions mean only their order declares the
  numeric form (§4.5).
- `core.array_channels.electrode_id` and `core.unit_electrodes.channel_index` are struck, since
  the labels state both (§4.6).
- The checks follow from the declarations (§4.7).

The names `core.array_labels`, `position_index`, `outer_position_index`, `label_id` and
`coordinate_depends_on` are tentative. With them, `core.waveform_mean` and an LFP array would be
declared like this:

| array | `axis_index` | `dimension_name` | declared form | `coordinate_depends_on` | label rows in `ecephys_786867` |
|---|---|---|---|---|---:|
| `core.waveform_mean` | 0 | `unit` | labelled: `core.units` | — | 4,505 |
| | 1 | `channel` | labelled: `core.electrodes` | 0 | 114,945 |
| | 2 | `sample` | numeric: origin −60, step 1, unit `{sample}` | — | 0 |
| an LFP array | 0 | `time` | tick | — | 0 |
| | 1 | `channel` | labelled: `core.electrodes` | — | 96 |

To find the electrode at unit index *i* and channel index *j*, a consumer reads the label row for
the first axis at index *i*, which holds a `unit_id`, and the label row for the second axis at outer
index *i* and index *j*, which holds an `electrode_id`. Both resolve through the resource the axis
row names.

### 4.1 Escapewheel owns the labels, and the Zarr layer names the axes

A position standing for a row of an Escapewheel table is a reference, and only the tables can
declare and check one. §2.6 found no storage convention that can reference a table row and no way
to annotate a referenced array, and Part 03 §6.5 already requires facts needed for validation to
live in tables. Clock time stays with the tick form for the same reason: the clock is a row of
`core.clocks`.

The Zarr layer keeps what it can state unaided. A packet-owned array would carry Zarr v3
`dimension_names` equal to the names its axis rows declare, so a Zarr tool that reads them, such as
xarray, names the axes without reading a table. The axis rows stay the owner of the names: a Zarr
v2 array cannot carry them, and Zarr.jl, as of ZarrCore 0.11.0, accepts the key and does not
expose it, which is Part 03 §6.5's reason. A multiscale pyramid is a set of arrays, each with its
own catalogue and axis rows, and no pyramid convention is adopted.

| alternative | why it falls short |
|---|---|
| adopt OME-Zarr | it models images with two or three space axes, and its channel axis has no identity per position (§2.6) |
| store coordinate arrays in the Zarr group, as CF and xarray do | an array value is not a reference, nothing declares what it names, and a referenced array cannot hold one (§2.6) |
| describe labels in Zarr attributes | the same as coordinate arrays, with no type |

### 4.2 One label table holds every labelled position

`core.array_labels` has one row per labelled position of any core array:

| column | type | role | holds |
|---|---|---|---|
| `session_id` | `int32` | identifier, assigned | the session, referencing `core.sessions` |
| `array_asset_id` | `int32` | identifier, assigned | the array |
| `axis_index` | `int64` | structural index | the axis; with `array_asset_id` it references `core.array_dimensions` |
| `outer_position_index` | `int64` | structural index | the index on the axis this one depends on, and 0 on an axis that depends on none |
| `position_index` | `int64` | structural index | the index on this axis |
| `label_id` | `int32` | identifier, assigned | the identifier of a row of the resource the axis row names |

The primary key is (`array_asset_id`, `axis_index`, `outer_position_index`, `position_index`). A
position with no row stands for no row of the resource, which is how padding is stated. The table
is keyed by the array, so R20 §2.4's keying rule holds by the key rather than by a rule no
declaration can express, and the ledger's `registry` disposition for R20 §2.4 is replaced when the
revision is accepted. `analysis.array_labels` mirrors it for analysis arrays, as R20 §5 mirrors the
other two array tables; its axis rows may name a core or an analysis resource.

`core.array_dimensions.coordinate_resource` keeps its name and changes its meaning. It names the
resource whose rows the axis's labels identify, and `coordinate_position_column` is struck. The
by-position shape then has no declaration left using it: `positions_in` appears only on the two
axis tables. Part 02 §8.3's by-position shape and the meta-schema's `positions_in` are therefore
retired. The rule `core.array_dimensions.coordinate_resource_is_core` stays, so a core axis names a
core resource, as R20 §5.1 requires.

| alternative | why it falls short |
|---|---|
| a table per kind of row, such as `core.array_units` | each new kind of labelled axis adds a core table, where Part 01 §3.17 keeps arrays generic |
| a coordinate table per array, stated from one template | the tables multiply with the arrays, and a generic consumer has to discover each |
| labels holding the target's `*_name`, as §8.3 requires today | one more join per lookup, for 1.5% more bytes and about 1 ms (§2.7), and the name repeats what the identifier already states |
| keep `core.array_channels` as the LFP channel axis's coordinate table and add a table for the waveform axes | two mechanisms for one question, and the by-position shape stays |

### 4.3 Part 02 §8.3 admits an integer paired value one reference away

Part 02 §8.3 lets a discriminator sit one declared reference away from the rows it specialises,
through `discriminates_via`, which `core.event_streams.detail_kind` uses with a shared key. A paired
value, however, has to be a string on the discriminator's own table, holding the target's key where
it is carried or its `*_name` where it is assigned. The preferred direction relaxes both:

- A paired value may sit on the table that `discriminates_via` reaches, so the discriminator on the
  axis row pairs with `label_id` on each of that axis's label rows. Presence then agrees by row: a
  label row exists only for an axis whose `coordinate_resource` is set.
- A paired value may be an integer identifier whose type and identity equal those of the named
  resource's single-column key. The writer numbers it in the named resource's numbering, as it
  numbers any reference to that resource.

Every resource an axis may name therefore has a primary key of one assigned `int32` identifier.
In core that admits `core.units`, `core.electrodes`, `core.devices`, `core.probes`, `core.clocks`,
`core.sorting_runs` and the other tables keyed by one assigned identifier. It excludes
`core.intervals`, whose key is (`session_id`, `interval_kind`, `interval_id`) and whose
`interval_id` is carried. A companion proposal, `an-interval-is-numbered-by-its-packet`, gives
intervals an assigned identifier, which is what a trial axis needs. `core.events`,
`core.media_frames` and `core.spike_events` have composite keys and no identity of their own; an
axis over them is a tick or irregular axis.

The two existing string paired values, `scope` on `core.preferred_runs` and on
`core.processing_runs`, keep their form. Relaxing the rule changes no existing declaration.

An integer label costs one thing a name does not: `label_id` 212 means nothing until the axis row
says which resource it is in. The axis row always says, and the generated check resolves it.

### 4.4 A dependent axis names the axis it depends on

`coordinate_depends_on`, a new nullable column of `core.array_dimensions`, holds the `axis_index`
of another axis of the same array. Where it is set, the axis's labels vary along that other axis,
and each label row's `outer_position_index` is the index on it. A dependent axis may depend only on
an axis that depends on none; a chain would make the labels vary along two axes, and nothing in
either packet needs it. Where it is null, `outer_position_index` is 0 in every row, the labels
standing for the whole array.

| alternative | why it falls short |
|---|---|
| keep R100 §2.3's view that the named table decides | a consumer has to know `core.unit_electrodes` by name, which §1.2 shows leads to 4,505 rows for one index |
| key a dependent label by the outer axis's label, such as `unit_id`, rather than its index | the outer axis would have to be labelled, and the key would describe the unit rather than the array |
| a nullable `outer_position_index` | a primary-key column is required (Part 02 §9.4), so 0 is the value an independent axis can hold |
| a second table for dependent labels | two tables answer one question, and each check is written twice |

### 4.5 Every axis declares a form

Part 03 §6.3's requirement stays, a rule at error level reports an axis that declares no form, and
R20 §3's permission is recorded as superseded. An omission is then reported, and an axis that no
form can describe fails its build instead of being published unlabelled. The rule catches an
omission but not a wrong form declared on purpose, and the omission is the failure observed. It
affects the 3 waveform unit axes, which §4.2 labels, and the 10 fixture axes.

An axis whose positions mean only their order, such as a principal-component axis, declares the
numeric form with step 1 and `coordinate_unit` `1`, UCUM's dimensionless unit. Its origin is the
number the source gives the first position, so components a source numbers 1 to 3 keep those
numbers, and it is 0 where the source numbers none. This needs no schema change.

| alternative | why it falls short |
|---|---|
| add a fifth, ordinal form | it says what the dimensionless numeric form says, at the cost of another column and another completeness rule |
| restore R20 §3's permission in Part 03 §6.3 | an axis declaring nothing stays ambiguous, and §2.1's defect stays conforming |

### 4.6 Each channel fact has one owner

`core.array_channels.electrode_id` states which electrode an LFP channel is, which the channel
axis's labels would state again. The column is struck, and `core.array_channels` keeps the
acquisition facts of each channel: `channel_label`, `inter_sample_shift`, `unit`, `offset` and
`conversion`. It stays keyed by (`array_asset_id`, `channel_index`) and references its axis row,
but is no longer that axis's coordinate table.

`core.unit_electrodes.channel_index` exists only to place an electrode on a waveform channel axis,
as its description says. The column is struck with its rule
`core.unit_electrodes.channel_index_contiguous`, and `is_primary` stays. `core.unit_electrodes`
then states which contacts a unit was detected on, and the labels state which electrode each
channel index of one array holds. These are different facts that coincide for this source, so no
rule compares them.

### 4.7 The checks follow from the declarations

| check | where | what it reports |
|---|---|---|
| every axis declares one form | declared rule on `core.array_dimensions` | an axis with none; `one_coordinate_form` already reports two |
| the named resource exists and has a single-column key of the label's type | generated, with each resource's key supplied by the registry | an axis naming a resource no label can identify |
| every label names a row | generated, one anti-join per named resource | a `label_id` absent from the resource its axis names |
| labels sit on labelled axes | generated | a label row whose axis names no resource |
| an independent axis's labels have outer index 0 | declared rule on `core.array_labels` | a nonzero `outer_position_index` where `coordinate_depends_on` is null |
| a dependent axis depends on an independent axis of its array | declared rule on `core.array_dimensions` | a chain, an axis naming itself, or an axis the array lacks |
| no axis names one row twice | declared rule on `core.array_labels` | two positions with one `label_id` at one outer index |
| indices lie within the array | physical, from the array's shape | a `position_index` or `outer_position_index` at or beyond its axis's length |
| a packet-owned array's `dimension_names` match | physical | a name differing from its axis row's |

The duplicate rules `core.array_dimensions.labelled_axis_complete` and
`core.array_dimensions.coordinate_pair_complete` go with `coordinate_position_column`.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose (Part 01) | unchanged; §3.17 already requires every axis to declare its coordinates |
| logical prose (Part 02) | affected: §8.3 admits the integer paired value one reference away and retires the by-position shape; §9.4's discriminator-shape invariant follows; §11.6 lists the new table and §11.8 its analysis mirror |
| registry declarations | affected: `core.array_labels` and `analysis.array_labels` are added; `coordinate_depends_on` is added to and `coordinate_position_column` struck from both axis tables; `core.array_channels.electrode_id` and `core.unit_electrodes.channel_index` are struck; the rules in §4.7 are added and three are struck |
| registry meta-schema | affected: `positions_in` is removed, and a paired value may be an integer identifier reached through `discriminates_via` |
| physical profile (Part 03) | affected: §6.3 states the labelled form, the dependency and the ordinal numeric form; §6.5 requires `dimension_names` on a packet-owned array and the extent check |
| packet manifest (Part 04) | unchanged; no resource-entry field changes |
| validation and import (Part 05) | unchanged prose; the generated checks are built by Tier 1's existing discriminator rules |
| extension registries | unchanged; no extension declares an array or uses `positions_in` |
| reference writer | affected: the waveform and LFP sources write label rows and `dimension_names`, and stop writing the struck columns |
| reference reader | affected: an axis resolves through the label table, and discriminator resolution learns the integer paired value |
| reference validator | affected: the generated and physical checks |
| adapters (Part 12) | unchanged; the protocol carries tables and arrays whatever their columns |
| existing packets | affected: both session packets are rebuilt, gaining 120,410 and 357,274 label rows |
| conformance fixtures | affected: `outside_array_floor` and `unresolved_externals` declare a form on each of their 10 axes; positive and negative fixtures for each check in §4.7 |
| revision tooling | unchanged |
| documentation | affected: Part 08's list of core tables gains the new table |

## 6. Open questions

1. **Whether a category axis may hold a label that is not a row.** A category axis whose categories
   are rows, such as one over probes, is labelled like any other. One whose categories are not,
   such as the statistic of a waveform, has no row to name; `core.waveform_mean` and
   `core.waveform_sd` already split that axis into two arrays. No array in either packet or the
   fixtures has such an axis. The preferred direction admits no free-text label: such an axis is
   split into arrays or declared ordinal.
2. **Whether `dimension_names` is required or recommended on a packet-owned array.** The reference
   writer writes none today, and the physical checker can compare them where present. The preferred
   direction requires them, since the writer controls them and a Zarr tool otherwise opens the
   array with unnamed axes.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

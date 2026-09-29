# Every array axis declares what each position is

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `b1fb70bfab14c19296aa03dea2429332a2731a71` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 02 §§1, 3, 8.3, 9.2, 9.4, 11.6 and 11.8; Part 03 §§6.3 and 6.5; Part 05 §5.3; Part 08 §§2 and 3; Part 10 §2.9; `registry/registry.schema.json`; the registry-contract descriptor; the core registry |
| **Depends on** | None |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6; §3.7; §3.8 |

Section 3 is normative. Sections 1, 2 and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

A packet describes each axis of a dense array with one row of the array's axes table,
`core.array_dimensions` for a core array. Besides naming the axis, the row says what each position
along it stands for, in one of four forms that Part 03 §6.3 governs:

| form | columns | the position at index *k* stands for |
|---|---|---|
| tick | `clock_id`, `origin_tick`, `step_tick_num`, `step_tick_den` | tick `origin_tick + k × step` on that clock |
| numeric | `origin_value`, `step_value`, `coordinate_unit` | the value `origin_value + k × step_value` in that unit |
| irregular | `coordinate_array_asset_id` | the value at index *k* of a 1-D array |
| labelled | `coordinate_resource`, `coordinate_position_column` | the row of the named table whose position column holds *k* |

The labelled form resolves by the by-position shape of Part 02 §8.3. The mean-waveform array
`core.waveform_mean` holds one template per unit, per channel, per sample, and shows three defects
in how the form works:

- **No form can say which unit a position holds.** The unit axis declares no form, because a
  labelled axis needs a table with one row per position of this array, holding the index and the
  unit, and none exists. The reference writer once filled the axis in an order other than
  `unit_id`, pairing templates with the wrong units, and nothing reported it (§2.1).
- **Nothing declares that the channel axis depends on the unit axis.** A unit's template covers
  only the contacts it was detected on, so channel index *j* holds a different electrode for each
  unit. The channel axis names `core.unit_electrodes` by `channel_index`, and a consumer following
  that declaration finds 4,505 rows for index 0 in one session packet, one per unit.
- **An axis declaring nothing is ambiguous.** Part 03 §6.3 requires every axis to declare a form,
  R20 §3 permitted an axis to declare none, and no rule checks either. The unit axis declares
  nothing because no form fits, where R20 §3 meant an axis declaring nothing to carry only its
  order, and a consumer cannot tell the two apart.

This revision gives each layer one table holding a row for every position of a labelled axis,
with the identifier of the row the position stands for, or null for padding. An axis row names
that identifier's resource and any other axis its labels depend on. A paired value of Part 02 §8.3
may then sit on the rows a discriminator specialises, be an integer identifier and be null there,
and the by-position shape retires. Every axis declares exactly one form, and one rule reports an
axis declaring none or several. Which electrode a channel holds is stated once, in the labels. A
packet-owned array carries its axis names in Zarr, and a validator checks the label rows against
the array's shape. The labels state which row each position stands for, and no check compares
them with the array's values (§4).

The change is structural because it revises rules inside Part 02 §§3, 8.3 and 9.4, Part 03 §§6.3
and 6.5, and Part 05 §5.3. Appended sections would leave Part 02 §8.3 describing a shape no
declaration uses and Part 03 §6.3 naming a position column that no longer exists.

### 1.1 Structural crosswalk

Every affected section carries a canonical anchor. The anchor bootstrap `0b98d31` added
`ew-climbing-integer-marks` to Part 10 §2.9, and no further bootstrap is needed. No section moves,
splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 02 §1, the incorporated descriptor file | revise in place | same section | the v0.6 descriptor is incorporated, in place of a v0.2 file the repository does not hold | §3.8 |
| Part 02 §3, the table row listing the discriminator attributes | revise in place | same section | `positions_in` is no longer a column attribute | §3.3 |
| Part 02 §8.3, "Which column carries it" | extend in place | same section | a paired value may sit on the specialised table | §3.3 |
| Part 02 §8.3, "Whether it must resolve", presence agreement | extend in place | same section | a paired value on the specialised table may be null, naming no row, and its discriminator is non-null for every specialised row | §3.3 |
| Part 02 §8.3, the paired-value shape | revise in place | same section | a paired value may be an identifier holding the named key's value | §3.3 |
| Part 02 §8.3, the by-position shape | retire | none | no discriminator resolves by position | §3.3 |
| Part 02 §8.3, "What is generated", the by-position check | replace in place | same section | a paired value that must resolve gains a key-shape, a value and a presence check | §3.3 |
| Part 02 §9.2, the meta-schema `$id` and core registry version | revise in place | same section | both advance to 0.9.0 | §3.8 |
| Part 02 §9.4, the descriptor ID and the discriminator-shape paragraph | revise in place | same section | the descriptor advances to v0.6; a discriminator selects one of two shapes and its companion follows §3.3 | §3.3, §3.8 |
| Part 02 §11.6, the rows for `core.array_channels` and the axes | revise and add | same section | `core.array_channels` holds scaling and shift; `core.array_labels` is listed | §3.1, §3.5 |
| Part 02 §11.8 | add a row | same section | `analysis.array_labels` is listed | §3.1 |
| Part 03 §6.3 | extend in place | same section | a labelled axis has a label row at every position, names the resource its labels identify and may depend on one other axis; a core axis names a core resource; an axis declares exactly one form, and an order-only axis is numeric | §3.2, §3.4 |
| Part 03 §6.5 | revise in place | same section | a packet-owned array carries `dimension_names`, and the axes table owns the names | §3.6 |
| Part 05 §5.3, the list of physical checks | extend in place | same section | label rows, their completeness, channel positions and `dimension_names` are checked against the array | §3.6 |
| Part 08 §§2 and 3, the generated layout and manifest excerpt | regenerate the informative example | same sections | none | none |
| Part 10 §2.9, the example of a mis-marked structural index | revise the informative example | same section | none | none |

## 2. Background

Section 2 is informative. The measurements use the two session packets the reference writer built
at this baseline with the fixed waveform source, the `packet-wf` builds: `ecephys_786867`, ten
probes and 4,505 sorted units, and `ecephys_776259`, twelve probes and 6,781 sorted units. Each has
`core.waveform_mean`, of shape (4,505, 26, 150) and (6,781, 26, 150), and `ecephys_776259` also has
`core.waveform_sd` of the same shape. Each probe contributes one LFP array of 96 channels, stored as
Zarr v2 inside the source NWB and referenced by an external URI. Both packets validate with no
errors. Section 2.1 alone uses the builds made before the fix.

### 2.1 The unit axis held the wrong unit at 3,971 and 6,781 indices

The waveform source stores each template on the unit's own contacts and zeroes the rest of the 26
channels. A template therefore has non-zero samples on at most as many channels as its unit has rows
in `core.unit_electrodes`, and a count above that proves the index holds a different unit. Reading
the unit at index *k* as `unit_id` *k*, the earlier builds had 558 and 1,680 indices non-zero on
more channels than that unit has contacts.

The actual order was recovered by placing each sorting run's units, in `unit_id` order, as one
contiguous block, taking at each step the one run whose units fit. The blocks follow the analyzer's
run order, `sorting_run_id` 0, 2, 3, 4, 9, 1, 5, 6, 7, 8 in `ecephys_786867`. Under that order,
3,971 of 4,505 indices in `ecephys_786867` held a unit other than `unit_id` *k*, and all 6,781 in
`ecephys_776259` did.

### 2.2 The fixed order holds by a numbering convention nothing declares

The rebuilt waveform source places units in `unit_id` order, and a unit with no template keeps its
index with no channels. Every index of `core.waveform_mean` then passes §2.1's test exactly, 4,505
of 4,505 and 6,781 of 6,781. The unit at index *k* is `unit_id` *k* only because Part 02 §12.1
numbers units from zero and each array holds every unit in its packet. An array holding one probe's
units, or the units one curation kept, places `unit_id` *k* elsewhere.

### 2.3 Only the waveform arrays are affected

| `core.array_dimensions` rows | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| all | 23 | 30 |
| declaring no form | 1 | 2 |
| naming `core.unit_electrodes` | 1 | 2 |

The rows declaring no form are exactly the waveform unit axes, and the rows naming
`core.unit_electrodes` exactly the waveform channel axes. Of the 64 fixture packets under
`fixtures/packets/`, `outside_array_floor` and `unresolved_externals` carry arrays, and all 10 of
their axes declare no form: `fixtures/build.py` catalogues each array with a `unit` and a `sample`
axis and nothing else.

### 2.4 Nothing states R20 §2.4's keying rule

R20 §2.4 requires a coordinate table to be keyed by `array_asset_id`, so that its rows belong to
one array, and the ledger records it as `registry`. No declaration can express it: the registry can
require a position column's role, which R100 §2.2 does, but not require the named table to carry
`array_asset_id`. `core.array_channels` is keyed (`array_asset_id`, `channel_index`) and references
its axis row. `core.unit_electrodes` is keyed (`session_id`, `unit_id`, `electrode_id`) and has no
tie to any array. R100 §5 left open whether that tie belongs in the registry until a third case
arose, and the waveform unit axis is the third.

### 2.5 No key fixes a channel's position

Where a channel sits on an axis is a fact of how the array was assembled. On each LFP array exactly
one of the 96 channels sits where ordering by `electrode_id` would put it: 10 of 960 rows in
`ecephys_786867` and 12 of 1,152 in `ecephys_776259`. On the waveform arrays, every
`core.unit_electrodes.channel_index` equals the electrode's rank in its sorting run's channel order,
in 114,945 of 114,945 and 171,280 of 171,280 rows. The waveform order is one source's convention
and the LFP order follows no key, so each labelled position needs its label stored.

### 2.6 The storage layer cannot hold the labels

- **A referenced array cannot be annotated.** Every LFP array is Zarr v2 inside the source NWB, and
  a packet writes nothing there, so any fact about those axes lives in tables.
- **OME-Zarr 0.6 describes images.** A multiscale image has two or three space axes, and its channel
  axis carries no identity per position.
- **The Zarr conventions describe space.** The `spatial`, `proj` and `multiscales` conventions of
  the `zarr-conventions` organisation describe spatial transforms, coordinate reference systems and
  pyramid levels, and none references a row of a table.
- **A coordinate array is a value, not a reference.** A prototype stored `unit_id` as a 1-D Zarr
  array and `electrode_id` as a 2-D one, with −1 at an unlabelled index, in a group xarray opens
  unaided. It took 35,108 bytes for `ecephys_786867`, and a numpy check written for those two arrays
  caught three injected defects in 22 ms. Nothing declares what the values name, and a referenced
  array cannot hold them.

NWB's `Units.waveform_mean` does not say which electrode each channel holds either:
`waveform_mean_index` was merged into nwb-schema by pull request 576 on 2024-04-25 and reverted by
pull request 595 on 2024-11-15, and issue 615 remains open. SpikeInterface pads a template to the
most channels any unit has and records a boolean mask per unit, so the slot at index *k* is the
*k*-th channel the mask selects.

Zarr v3 can still name the axes: `dimension_names` is part of the array metadata, and xarray reads
it. The axes table remains the owner of the names, because Zarr v2 cannot carry them.

### 2.7 One label table measured on both packets

The table §3.1 declares was built from both `packet-wf` builds, with one row per labelled position:
each unit index of each waveform array, each channel index of each unit's template, and each LFP
channel. Axis lengths came from each waveform array's Zarr metadata and from each LFP array's
`core.array_channels` rows. Checks ran in DuckDB 1.5.5 over Parquet files, as the median of 9 runs.

| | `ecephys_786867` | `ecephys_776259` |
|---|---:|---:|
| label rows | 122,595 | 367,326 |
| padding rows, holding a null label | 2,185 | 10,052 |
| labelled axes | 12 | 16 |
| bytes, zstd-compressed Parquet | 105,587 | 276,825 |
| every label names a row, one anti-join per named resource | 7.3 ms | 15.1 ms |
| the same check as one join over every resource | 879 ms | 3,462 ms |
| primary key unique | 6.2 ms | 16.4 ms |
| every position has a row, counted against the axis lengths | 4.5 ms | 8.6 ms |

Every check returns no rows, and no axis names one row twice. The padding sits on the waveform
channel axes: a unit with fewer than 26 contacts leaves the rest of its channel indices standing for
no electrode. The padding rows add 1.8% and 2.8% to the rows, and the table takes fewer bytes with
them than without, 105,587 against 107,273 and 276,825 against 282,937. Dropping one row draws the
completeness count. The reference validator checks a paired value today with one query over a union
of every named resource, cast to strings, which is the single join's form. It checks the same thing
120 and 229 times more slowly, so the generated check is one anti-join per named resource.

An earlier prototype compared integer labels with the `*_name` labels Part 02 §8.3 requires of a
paired value today. Names cost 108,140 bytes against 106,507, and finding the units with a template
on one electrode took 3.5 ms against 2.3 ms.

### 2.8 One-column keys make a generic table possible

R20 §2.4 chose a pointer to a coordinate table over a generic table because the things an axis
names had keys of different widths: one column for a channel, two for a trial, four for a unit. R81
§2.1 has since made `unit_id` the whole key of a unit. Every core table keyed by one column is keyed
by one assigned `int32` identifier: `core.units`, `core.electrodes`, `core.probes`, `core.devices`,
`core.clocks`, `core.sorting_runs` and nine others. One `int32` column can therefore label a
position in any of them. `core.intervals` is keyed (`session_id`, `interval_kind`, `interval_id`),
so no label can name a trial.

Part 02 §8.3 requires a string paired value, matching an assigned key's `*_name`, because a value
written before the build cannot hold a number the build has not assigned (R90 §3.7). A label is not
written before the build. An adapter hands over each identifier as its source's name (Part 12 §5),
and the build numbers a label as it numbers any reference to the resource.

### 2.9 Alternatives

| alternative | why it falls short |
|---|---|
| keep the current forms and let each writer order positions by identifier | §2.2's convention fails for any array holding a subset, and nothing checks it |
| adopt OME-Zarr, or store coordinate arrays in the Zarr group as CF and xarray do | neither references a table row, and a referenced array cannot hold one (§2.6) |
| a table per kind of row, such as `core.array_units` | each new kind of labelled axis adds a core table, where Part 01 §3.17 keeps arrays generic |
| a coordinate table per array, stated from one template | the tables multiply with the arrays, and a generic consumer has to discover each |
| labels holding the named row's `*_name` | one more join per lookup for 1.5% more bytes (§2.7), repeating what the identifier states |
| state padding by omitting a position's label row | a label a writer omits cannot be told from padding, so nothing can require an axis's labels to be complete; the padding rows cost no bytes (§2.7) |
| keep `core.array_channels` as the LFP axis's coordinate table and add a table for the waveform axes | two mechanisms answer one question, and the by-position shape stays |
| keep R100 §2.3's view that the named table decides how its rows narrow to one axis | a consumer has to know `core.unit_electrodes` by name, or it finds 4,505 rows for one index |
| key a dependent label by the label of the axis it depends on, such as `unit_id`, rather than by that axis's position | the axis depended on would have to be labelled, and the key would describe the unit rather than the array |
| a nullable `depends_on_position_index` | a primary-key column is required (Part 02 §9.4), so 0 is the value an independent axis holds |
| add a fifth, ordinal form | it would tell an axis carrying only order from a measured dimensionless one, which the numeric form leaves to `dimension_name`; no rule could check that a writer chose it, and it costs another column and another completeness rule |
| restore R20 §3's permission in Part 03 §6.3 | an axis declaring nothing stays ambiguous, and §2.1's defect stays conforming |
| let a label hold free text for a category that is not a row | a string label is unchecked, and an array whose categories are statistics already splits into one array per statistic, as `core.waveform_mean` and `core.waveform_sd` do |
| recommend `dimension_names` rather than require it | a Zarr tool opens an array without it with unnamed axes, and the writer always knows the names |

### 2.10 Feasibility and overlap

The five rules of §3.7, four new and one revised, pass the Part 11 static rule check against the
proposed declarations, and so do their analysis mirrors. Run on the prototype tables of §2.7, each
returns no rows. With one defect injected per rule, each flags that defect and no other rule fires;
the revised form rule flags an axis with no form and one with two. A chain of two dependent axes is
reported at both rows of the cycle it forms. The padding rows, up to 13 at one unit's position, draw
nothing from the rule forbidding one row at two positions.

The ledger records R20 §5.1, which kept a core axis to core resources, as superseded by R145, and
R145 §3.4 exempts a discriminator from the canonical-reference rule, since a discriminator names
without depending. The declared rule `core.array_dimensions.coordinate_resource_is_core` has had no
prose owner since; §3.2 states it with its reason.

The sections citing Part 02 §8.3 from other parts, Part 05 §13.4 and Part 09 §6.2, state the
resolution rule generally and stay true.

The reference validator reads an axis's length as the number of its coordinate table's rows and
reports an external array whose stored length differs. No part states that comparison. §3.6 states
it for label rows, which cover every position, so an external array rewritten with more positions
along a labelled axis draws the completeness check.

## 3. Decision

Eight subsections declare the label tables, the axis rows, the paired value they rely on, the form
every axis declares, the owner of each channel fact, the physical checks, the declared rules and
the registry identifiers. The crosswalk in §1.1 places each.

### 3.1 A label table holds the row each labelled position stands for

`core.array_labels` holds one row for each position of a labelled core array axis (§3.2). Its
`label_id` is the identifier of the row the position stands for, in the resource its axis row's
`coordinate_resource` names. A null `label_id` stands for no row, which is how a packet states
padding.

The incorporated core registry MUST declare `core.array_labels` with content class `core`, kind
`table`, singleton instances of optional presence, no `requires`, optional lineage, and primary key
(`array_asset_id`, `axis_index`, `depends_on_position_index`, `position_index`). Every column is
`required` except `label_id`, which is `nullable`:

| column | type | role | identity | description |
|---|---|---|---|---|
| `session_id` | `int32` | `identifier` | `assigned` | Session ID. |
| `array_asset_id` | `int32` | `identifier` | `assigned` | The array whose axis this position is on. |
| `axis_index` | `int64` | `structural_index` | — | The labelled axis, in stored order. |
| `depends_on_position_index` | `int64` | `structural_index` | — | The position on the axis this axis's labels depend on, and 0 where they depend on none. |
| `position_index` | `int64` | `structural_index` | — | The position on the labelled axis. |
| `label_id` | `int32` | `identifier` | `assigned` | The identifier of the row this position stands for, in the resource the axis row's `coordinate_resource` names; null where it stands for none. |

It MUST declare two references: `session_id` to `core.sessions.session_id`, and (`array_asset_id`,
`axis_index`) to `core.array_dimensions` (`array_asset_id`, `axis_index`). `label_id` references no
resource by declaration; §3.3 resolves it.

The incorporated core registry MUST declare `analysis.array_labels` with the same columns, key and
descriptions, content class `analysis`, required lineage, and references `session_id` to
`core.sessions.session_id` and (`array_asset_id`, `axis_index`) to `analysis.array_dimensions`
(`array_asset_id`, `axis_index`).

### 3.2 An axis row declares how its labels resolve

An axis is **labelled** where its row declares `coordinate_resource`, and each of its positions
then stands for the row its label names, or for none. The incorporated core registry MUST declare,
on `core.array_dimensions`:

| column | type | presence | role | declares | description |
|---|---|---|---|---|---|
| `coordinate_resource` | `string` | `nullable` | `discriminator` | `resolves: required`, `discriminates_via: core.array_labels.axis_index`, `discriminates: label_id` | The table whose rows this axis's positions stand for, as a dotted resource ID. Each position's row is named by its label in `core.array_labels`. |
| `depends_on_axis_index` | `int64` | `nullable` | `structural_index` | — | The axis of this array whose position, with this axis's own, decides each label. Null where this axis's position alone decides it. |

and MUST declare a reference from (`array_asset_id`, `depends_on_axis_index`) to
`core.array_dimensions` (`array_asset_id`, `axis_index`). `coordinate_position_column` is struck.
`analysis.array_dimensions` MUST declare the same, with `analysis.array_labels.axis_index` as the
`discriminates_via` target and `analysis.array_dimensions` as the reference target.

An axis is **dependent** where its row declares `depends_on_axis_index`: which row each of its
positions stands for changes along the axis `depends_on_axis_index` names, and each label row's
`depends_on_position_index` is the position on that axis. A packet MUST satisfy each of these:

- a labelled axis has one label row at each of its positions, and a dependent axis one at each of
  its positions for each position of the axis it depends on;
- a dependent axis is labelled;
- the axis a dependent axis names is not itself dependent, which excludes an axis naming itself;
- every label row of an axis that is not dependent has `depends_on_position_index` 0; and
- no two label rows of one axis at one `depends_on_position_index` hold one non-null `label_id`, so
  a row is at most one position.

A core axis MUST name a `core` resource, and the rule
`core.array_dimensions.coordinate_resource_is_core` reports one that does not. A label must
resolve, and an analysis resource may be deleted (Part 06 §2), which would leave a core array's
positions standing for nothing. A core axis has no need to name an extension resource: a kind of
interval an extension specialises is a row of `core.intervals`.

Part 03 §6.3 states the labelled form in these terms.

### 3.3 A paired value may sit on the specialised rows and be an identifier

This clause replaces Part 02 §8.3's paired-value and by-position shapes and the checks generated
for them. The shared-key shape and its reverse check are unchanged.

A paired-value discriminator declares `discriminates`, naming the column that holds the value.
Where the discriminator declares `discriminates_via`, that column belongs to the table
`discriminates_via` names, whose rows the discriminator specialises. Otherwise it belongs to the
discriminator's own table.

The named resource's primary key MUST be one column, and a paired value MUST take one of two forms:

- a `string` `data` column, whose value matches the named key where that key is `carried` and its
  `*_name` where the key is `assigned`; or
- an `identifier` column whose type and identity equal the named key's, holding that key's value.

A writer MUST fill an identifier paired value with the identifier it assigned the named row, as it
fills any reference to that resource (Part 05 §4.3).

A paired value on the discriminator's own table has the discriminator's `required` or `nullable`
presence, and each row declares both or neither. A paired value on the specialised table is
`required` or `nullable`. Its kind comes from the discriminator's row there, so a null value is not
undeterminable: the specialised row names no row of that kind. A packet MUST NOT hold a specialised
row whose discriminator is null, since that row would pair a value with no kind.

Where `resolves` is `required`, a validator MUST generate, in addition to the forward anti-join,
three checks for a paired-value discriminator, each at `error` and each built over the kinds the
packet's rows name:

- a check reporting a named resource whose primary key is not one column of the paired value's
  form, built from the registry's key declarations as literals;
- per named kind, an anti-join returning every row whose paired value is not null and matches no
  row of the named resource; and
- where the paired value is on the specialised table, a check returning every specialised row
  whose discriminator is null.

A discriminator resolves by a shared key or by a paired value, and MUST NOT declare `positions_in`.
Part 02 §3 lists `resolves`, `discriminates` and `discriminates_via` as the discriminator
attributes, and Part 02 §9.4 states that a discriminator selects the paired-value shape by declaring
`discriminates` and the shared-key shape by not declaring it.

### 3.4 Every axis declares exactly one coordinate form

Part 03 §6.3's requirements that every axis declare its coordinates in one of the declared forms,
and in no more than one, stand. The rule `core.array_dimensions.one_coordinate_form` reports an axis
declaring none or several (§3.7). R20 §3's permission to declare none is superseded.

A writer MUST declare an axis whose positions carry only their order in the numeric form, with
`step_value` 1, `coordinate_unit` `1` and `origin_value` the number its source gives the first
position, or 0 where the source numbers none. A principal-component axis is one. No rule can tell
an order-only axis from a measured one, so nothing checks this.

No form labels a position with text. An axis whose positions are categories that are not rows of a
resource is declared order-only, or the array is split along it into one array per category, each
naming its category in `semantic_type` (Part 01 §3.17). Only a core axis is limited to core
resources (§3.2), so an analysis array may instead label the axis with a resource whose rows are
the categories, such as an extension's table.

### 3.5 Each channel fact has one owner

The labels state which electrode each channel position holds, so no other column states it:

- `core.array_channels.electrode_id` is struck. `core.array_channels` keeps `channel_label`,
  `inter_sample_shift`, `unit`, `offset` and `conversion`, its key (`array_asset_id`,
  `channel_index`), and its reference to its axis row. It is no axis's coordinate table.
- `core.unit_electrodes.channel_index` is struck, with its rule
  `core.unit_electrodes.channel_index_contiguous`. `core.unit_electrodes` states which contacts a
  unit was detected on, whether or not any array holds that unit, and keeps `is_primary`.

Which contacts a unit was detected on and which electrode an array's channel position holds
coincide for one source and differ in general, so no rule compares them.

### 3.6 An array's shape and names agree with its axes and labels

A packet-owned array MUST carry Zarr v3 `dimension_names`, holding at each position the
`dimension_name` of the axes-table row with that `axis_index`. The axes table owns the names: a
referenced array may carry other names or none, and its axes-table rows govern. Part 03 §6.5 states
this.

For each dense array whose metadata it reads, a validator MUST report at `error`:

- a label row whose `position_index` is negative or not less than its axis's length;
- a label row whose `depends_on_position_index` is negative or not less than the length of the axis
  its axis row's `depends_on_axis_index` names;
- a position of a labelled axis with no label row, or, on a dependent axis, a pair of its position
  and a position of the axis it depends on with no label row;
- a `core.array_channels` row whose `channel_index` is negative or not less than the length of the
  axis its `axis_index` names; and
- for a packet-owned array, `dimension_names` that is absent or differs at any position from the
  axes table.

A validator finds an axis's label rows in the table that the `discriminates_via` of the axes
table's `coordinate_resource` names. Part 05 §5.3 lists these checks among the physical checks.

### 3.7 The registry declares the axis rules

The incorporated core registry MUST declare these rules, each at level `error`, with
`core.array_dimensions.one_coordinate_form` replacing that rule's current message and SQL:

| id | message | sql |
|---|---|---|
| `core.array_dimensions.one_coordinate_form` | `an axis declares no coordinate form, or more than one` | `SELECT array_asset_id, axis_index FROM core.array_dimensions WHERE (CASE WHEN origin_tick IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN origin_value IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN coordinate_array_asset_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN coordinate_resource IS NOT NULL THEN 1 ELSE 0 END) <> 1` |
| `core.array_dimensions.dependent_axis_labelled` | `an axis depends on another axis and has no labels` | `SELECT array_asset_id, axis_index, depends_on_axis_index FROM core.array_dimensions WHERE depends_on_axis_index IS NOT NULL AND coordinate_resource IS NULL` |
| `core.array_dimensions.dependency_not_chained` | `an axis depends on an axis that itself depends on another` | `SELECT d.array_asset_id, d.axis_index, d.depends_on_axis_index FROM core.array_dimensions AS d JOIN core.array_dimensions AS o ON o.array_asset_id = d.array_asset_id AND o.axis_index = d.depends_on_axis_index WHERE o.depends_on_axis_index IS NOT NULL` |
| `core.array_labels.independent_depends_on_position_zero` | `a label on an axis that depends on no other has a nonzero depends_on_position_index` | `SELECT l.array_asset_id, l.axis_index, l.depends_on_position_index, l.position_index FROM core.array_labels AS l JOIN core.array_dimensions AS d ON d.array_asset_id = l.array_asset_id AND d.axis_index = l.axis_index WHERE d.depends_on_axis_index IS NULL AND l.depends_on_position_index <> 0` |
| `core.array_labels.one_position_per_row` | `an axis names one row at two positions` | `SELECT array_asset_id, axis_index, depends_on_position_index, label_id, COUNT(*) AS n FROM core.array_labels WHERE label_id IS NOT NULL GROUP BY array_asset_id, axis_index, depends_on_position_index, label_id HAVING COUNT(*) > 1` |

`analysis.array_dimensions` MUST carry every rule `core.array_dimensions` carries except
`core.array_dimensions.coordinate_resource_is_core`, and `analysis.array_labels` every rule
`core.array_labels` carries, each with `analysis` in place of `core` in its ID and SQL. The core
registry MUST NOT carry `core.array_dimensions.labelled_axis_complete`,
`core.array_dimensions.coordinate_pair_complete`,
`analysis.array_dimensions.coordinate_pair_complete` or
`core.unit_electrodes.channel_index_contiguous`.

### 3.8 The registry identifiers advance

The registry meta-schema MUST NOT declare `positions_in`. The registry-contract invariant
`registry.discriminator.declaration` decides §3.3's companion rule: the column `discriminates`
names resolves on the table `discriminates_via` names where the discriminator declares it, and on
the discriminator's own table otherwise; it is one `string` `data` column or one `identifier`
column; and it has the discriminator's non-optional presence on the discriminator's own table and
`required` or `nullable` presence on another. The invariant inventory is otherwise unchanged.

These incorporated identifiers MUST advance:

| artifact | from | to |
|---|---|---|
| registry meta-schema `$id` | `https://escapewheel.org/schemas/registry/0.8.0` | `https://escapewheel.org/schemas/registry/0.9.0` |
| registry-contract descriptor ID | `escapewheel-registry-contract-v0.5` | `escapewheel-registry-contract-v0.6`, selecting meta-schema 0.9.0 with the same invariants |
| core registry `registry_version` | `0.8.0` | `0.9.0` |

Part 02 §1 incorporates the descriptor as
`registry/registry_contracts/escapewheel-registry-contract-v0.6.json`.

An extension registry migrated to meta-schema 0.9.0 MUST carry a `registry_version` different from
the one it carried under 0.8.0; the core specification does not assign it. No checker verifies
this.

## 4. What this does not change

The tick, numeric and irregular forms are unchanged, and so is Part 01 §3.17. The string paired
values `scope` on `core.preferred_runs` and on `core.processing_runs` keep their form, and every
discriminator declared today resolves as it does now. No multiscale convention is adopted: a
pyramid is a set of arrays, each with its own catalogue and axis rows.

A validator cannot compare a label with the array's values, so an array whose labels disagree with
its data conforms. The labels remove the unstated order a consumer had to assume, which is how
§2.1's defect arose, and leave a writer's own labelling beyond what validation detects.

## 5. Consequence

Every packet carrying a labelled axis, a waveform array or `core.array_channels` is rebuilt, and
every packet binds core registry 0.9.0, as after any meta-schema change. The two session packets
gain 122,595 and 367,326 label rows, 2,185 and 10,052 of them padding, lose
`core.array_channels.electrode_id` and `core.unit_electrodes.channel_index`, and their packet-owned
waveform arrays gain `dimension_names`; their other tables are unchanged. A packet built before this
revision fails selection under the new meta-schema, so no mixed reading arises.

The meta-schema change is incompatible, so the core registry and each of the four repository
extension registries name meta-schema 0.9.0. Core's `registry_version` becomes 0.9.0, and each
extension advances its own. No extension declares an array or a discriminator using `positions_in`,
so no extension declaration changes.

These accepted clauses are superseded: R20 §2.4 by §3.1, whose key ties each label to one array;
R20 §3 by §§3.4 and 3.7, which require exactly one form and revise its rule; R100 §2.1 by §3.2,
which restates `coordinate_resource`'s whole declaration; and R100 §§2.2 and 2.3 by §§3.2 and 3.3,
which strike the position column and `positions_in`. R90 §§3.5, 3.7 and 3.8 are narrowed by §3.3,
and their ledger entries gain a note: the by-position shape is retired, a paired value may be an
identifier on the specialised table and null there, and a paired value that must resolve gains three
generated checks. R100 §2.4 is unchanged. The ledger destinations naming Part 02 §8.3,
Part 02 §§11.6 and 11.8, or Part 03 §6.3 by number move to their anchors.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §3.17 already requires every axis to declare its coordinates, and a label is one way to. | None required. |
| logical prose and registry | Part 02 §8.3, §3 and §9.4 take §3.3; §§1, 9.2 and 9.4 take §3.8's identifiers; §§11.6 and 11.8 list the new tables. The core registry source declares §3.1's tables, §3.2's columns and references, §3.5's struck columns and §3.7's rules; `registry/build.py`, `registry/check.py` and `registry/assemble.py` follow the meta-schema and drop `positions_in`, and `check.py`'s naming exceptions for `coordinate_resource` stay. | `evidence/R<N>.json` names each anchor and registry pointer; `registry/check.py` passes. |
| physical profiles | Part 03 §6.3 takes §3.2's labelled form, dependency and resource rule and §3.4; Part 03 §6.5 takes §3.6's `dimension_names`. | `evidence/R<N>.json` names the anchors. |
| packet manifest and JSON Schemas | Unchanged. No manifest field names an axis, and the registry meta-schema changes under the row above. | None required. |
| validation and import | Part 05 §5.3 lists §3.6's physical checks. Part 05 §4.3 already has a writer assign identifiers packet-wide, which covers §3.3's identifier paired value. | The corpus variants below. |
| extensions | Each of the four repository extension registries names meta-schema 0.9.0 and advances its `registry_version`; no declaration changes. | `registry/check.py` over every extension registry. |
| reader, writer, validator, adapters | The validator generates §3.3's checks, replacing its single union with one anti-join per named kind, drops the by-position branch, runs §3.6's physical checks, whose completeness check replaces its comparison of an axis's length with its coordinate-table row count, adds the `analysis.array_dimensions` rules, and selects the v0.6 descriptor. The writer's waveform source labels the unit axis with `core.units` and the channel axis with `core.electrodes` depending on the unit axis, and writes `dimension_names`; its LFP source labels each channel axis with `core.electrodes`; both number `label_id` in the named resource's numbering and write a null `label_id` at each padding position, and neither writes the struck columns. The writer's encoding exception for `core.unit_electrodes.channel_index` goes with the column. The reader's discriminator resolution learns the identifier paired value on the specialised table and drops the by-position shape; its uncommitted axis sketch is rewritten against the label table or discarded. No adapter in `escapewheel-aind` writes an array. | The writer, reader and validator suites; both session packets rebuilt and validated with no error, and §2.1's template test passing on both. |
| conformance fixtures and tests | `fixtures/build.py` declares a numeric order-only form on the 10 fixture axes. New negative variants: an axis with no form, and one with two; a label naming a row that does not exist; a label row on an unlabelled axis; a labelled axis missing one position's row; a chain of dependent axes; a nonzero `depends_on_position_index` on an independent axis; one row at two positions; a label position beyond its axis; a packet-owned array without `dimension_names`. A positive variant holds two padding rows at one position of a dependent axis. Registry-checker cases reject `positions_in` and a paired value that is neither form. | `fixtures/corpus.py` and the registry-document tests. |
| revision process and tooling | The ordinary ledger and evidence records; the superseded and narrowed clauses above; `revisions/registry-targets.toml`'s targets for R20 §2.4 and R100 §§2.1 and 2.2 retire with those clauses. `facts.py`, `conformance/interval-kinds/probe.py`, `prototype/registry-codegen/` and the package tests naming meta-schema 0.8.0 or descriptor v0.5 follow the new identifiers. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | `registry/render.py` renders the new tables and columns in `registry/tables.md`; Part 08 §§2 and 3 regenerate from `integration/example.py`, listing `array_labels` and the new registry versions; the specification README's identifier table, `framework.py`'s expected values, the combined specification and the heading index follow. Part 10 §2.9's example of a structural index the declarations mis-mark names a struck column, and is replaced by a column the rebuilt packets show mis-marked, or dropped where none is. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `registry`, with targets in the declarations of `core.array_labels` and
`analysis.array_labels`. §3.2 is `applied` at Part 03 §6.3 and `registry` for its columns and
references. §3.3 is `applied` at Part 02 §8.3, with Part 02 §§3 and 9.4. §3.4 is `applied` at
Part 03 §6.3. §3.5 and §3.7 are `registry`. §3.6 is `applied` at Part 03 §6.5 and Part 05 §5.3. §3.8
is `applied` at Part 02 §§9.2 and 9.4. Each is placed by canonical anchor.

These cases distinguish the new rules from the current ones:

- a `core.waveform_mean` whose unit axis declares no form draws
  `core.array_dimensions.one_coordinate_form`, which the current rule passes;
- a label whose `label_id` names no `core.units` row draws the generated value check;
- a label row on an axis with no `coordinate_resource` draws the generated presence check;
- an axis naming `core.events`, whose key has three columns, draws the generated key-shape check;
- a unit axis declaring `depends_on_axis_index` 1 beside a channel axis declaring 0 draws
  `core.array_dimensions.dependency_not_chained` at both rows;
- a label with `depends_on_position_index` 3 on the unit axis draws
  `core.array_labels.independent_depends_on_position_zero`;
- two unit positions labelled with one `unit_id` draw `core.array_labels.one_position_per_row`;
- a label with `position_index` 4,505 on a unit axis of length 4,505 draws the physical extent
  check;
- a unit axis of length 4,505 with no label row at one position draws the physical completeness
  check, where the current validator counts no label rows;
- a packet-owned array without `dimension_names`, or with names out of order, draws the physical
  name check; and
- a registry declaring `positions_in`, or a paired value that is a `float64` data column, fails
  registry-document conformance under meta-schema 0.9.0.

The positive cases are the two rebuilt session packets and the valid corpus packet, whose waveform
unit axes are labelled with `core.units`, whose channel axes are labelled with `core.electrodes`,
and which draw none of these findings. A label row whose `label_id` is null draws no finding.

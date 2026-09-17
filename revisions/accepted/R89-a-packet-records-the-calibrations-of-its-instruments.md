# R89 — A Packet Records the Calibrations of Its Instruments

| | |
|---|---|
| **Status** | **Accepted** 2026-09-07 |
| **Amends** | Part 01 (adds Calibration as a semantic concept), Part 02 (adds three core resources) |
| **Depends on** | R55 (a discriminated reference), R56 (a column declares its context), R65 (an array names the instrument that made it), R88 (a session-scoped table names the session of every row) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

A **calibration** is what someone measured about an instrument so that its numbers can be
interpreted: how many microlitres a valve delivers when held open for 30 ms, how much light a fibre
emits at a given drive, where a manipulator's own coordinates sit in the rig, where a camera is
mounted. Nothing in this specification records one. Measured on the two packaged sessions,
**`ecephys_776259`** (twelve probes, 6,781 sorted units, recorded 2025-04-09) and
**`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25), whose AIND `rig.json` and
`session.json` documents hold ten calibration records between them.

## 1. Motivation

### 1.1 Two extensions record a calibrated quantity and neither can say what calibrated it

`dynamic_foraging.sessions` carries **`left_valve_open_time`** and **`reward_size_left`** — a
setting and the volume it delivers, which are the input and the output of one curve. The curve
itself sits in `rig.json` as seven paired points, `valve open time (s)` against
`water volume (ul)`, and the packet holds neither it nor anywhere to put it.

`aind_opto.emissions` has the same gap, and more rests on it. It carries **`power_mw`**, nullable and
declared in milliwatts, keyed on `(session_id, epoch_id, device_id)` and already referencing
`core.devices`. A rig that drives a laser by voltage or DAC counts produces that number only
through a calibration, so `power_mw` is either absent or a value someone computed from a curve the
packet does not hold — and an opto experiment is uninterpretable without knowing the power that
reached the tissue.

### 1.2 A calibration outlives the session that uses it

Both packets' `rig.json` documents carry **the same two water calibrations, both dated
2024-11-27** — **133 days** before `ecephys_776259` and **302 days** before `ecephys_786867`. One
measurement, cited by two sessions nearly six months apart.

A calibration is therefore not a `core.processing_runs` row. That table is R9 §2's provenance —
what ran over `core.source_files` to produce resources in *this* packet — and a curve measured in
November produced nothing in either. R88 §2.4 duplicates a run whose results reach several
sessions, and a calibration is not a run at all: it is a standing property of an instrument, and a
session reports it as in force rather than as having happened.

### 1.3 A source states a calibration four ways; only one is a curve

`session.json` records six of `ecephys_776259`'s probes as `ephys_modules`, each with
`calibration_date` `2025-04-09T10:00:00Z` and `coordinate_transform`
`behavior/calibration_info_np2_2025_04_09T10_00_00.npy` — a manipulator calibration whose content
is an array in a file, not a series of points. Camera intrinsics and extrinsics are the same
shape.

The same file records three `stick_microscopes` with `calibration_date` **null**,
`coordinate_transform` null, and `notes` reading *"Did not record arc or module angles, did not
calibrate"*. So a source states a calibration in at least four ways: as a curve, as an array, as a
date and nothing else, and as an assertion that none was made. Any design admitting only the first
would drop three of them.

### 1.4 One calibration covers many devices

Those six `ephys_modules` name **one file and one timestamp** between them: 6 modules, 1 distinct
`coordinate_transform`, 1 distinct `calibration_date`. One calibration of the rig's manipulators,
cited by six probes.

A `device_id` column on the calibration would therefore record six calibrations where the rig
performed one. R67 §3 found the same defect with its multiplicity reversed: four device rows
claiming four probes where the session had one physical object.

## 2. Decision

### 2.1 A new table records each calibration and the session it applied to

`core.calibrations` is added, keyed on `calibration_id` alone as R81 §2.1 keys a unit:

| column | type | presence | role | |
|---|---|---|---|---|
| `calibration_id` | `int32` | required | identifier | `assigned` (R53 §2.3) |
| `session_id` | `int32` | required | identifier | R88 §2.1; the session the calibration was in force for |
| `calibration_name` | `string` | required | data | R53 §2.3.1's name for an assigned identifier |
| `calibration_type` | `string` | required | data | **open** (R8 §4): `water_volume`, `light_power`, `manipulator_transform` |
| `calibrated_at` | `TIMESTAMP(MICROS, UTC)` | nullable | data | when it was measured |
| `description` | `string` | nullable | data | what the source said it was |
| `input_unit` | `string` | nullable | data | §2.3 |
| `output_unit` | `string` | nullable | data | §2.3 |
| `array_asset_id` | `int32` | nullable | identifier | §2.4 |
| `detail_kind` | `string` | nullable | discriminator | §2.5; `resolves: optional` |
| `metadata` | `json_string` | optional | data | §2.6 |

Two references are declared: `session_id` to `core.sessions` and `array_asset_id` to
`core.array_assets`.

The vocabulary is named `calibration_type` rather than `calibration_kind` because a `_kind` column
is a discriminator (R55 §2.1), which `registry/check.py` enforces both ways; this one holds a value
and resolves to no table, so it takes the suffix `event_type` and `activity_type` already use.

`session_id` says which session the calibration applied to and `calibrated_at` says when it was
measured, and the two **MUST NOT** be read as one fact: §1.2 measures 133 and 302 days between
them. A calibration in force for several sessions is recorded once per session, which is R88
§2.4's rule applied to a second table.

`calibrated_at` is nullable because a source states a calibration without one — three
`stick_microscopes` do — and R66 §2.1's discipline holds: what the source did not say is not
invented.

### 2.2 A calibration names the devices it covers

`core.calibration_devices` is added, keyed on `(calibration_id, device_id)`. The devices a
calibration covers are a repeated value, so they are a child table and not a column (R3 §3.0). That
is what keeps §1.4's manipulator calibration one row instead of six.

| column | type | presence | role | |
|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | R88 §2.1; references `core.sessions` |
| `calibration_id` | `int32` | required | identifier | references `core.calibrations` |
| `device_id` | `int32` | required | identifier | references `core.devices` |

A calibration covering a device the packet does not hold gets no row in that table, and its
absence is a fact rather than a defect (R49 §2.2): `core.devices` holds 20 rows in `ecephys_776259` and
`Lick spout Left` is not among them, because the writer builds devices from the probes and the
acquisition chain. No rule requires a calibration to name a device. Recording one costs a single
row, so a writer that records the calibration SHOULD record the device it names as well.

### 2.3 A calibration's paired series is a child table

`core.calibration_points` is added, keyed on `(calibration_id, point_index)`. Seven rows hold the
measured water curve, where `rig.json` holds two parallel JSON lists that R3 §3.0 forbids.

| column | type | presence | role | |
|---|---|---|---|---|
| `session_id` | `int32` | required | identifier | R88 §2.1; references `core.sessions` |
| `calibration_id` | `int32` | required | identifier | references `core.calibrations` |
| `point_index` | `int64` | required | structural_index | 0-based (R3 §6), as every other index is |
| `input_value` | `float64` | required | data | `unit_from: core.calibrations.input_unit` |
| `output_value` | `float64` | required | data | `unit_from: core.calibrations.output_unit` |

A point with one side missing states nothing, so both values are required and a calibration with no
points has no rows rather than empty ones.

The unit varies per calibration — seconds to microlitres for water, volts to milliwatts for opto —
so no literal `unit` can be declared on a value column. `input_value` declares
`unit_from: core.calibrations.input_unit` and `output_value` declares
`unit_from: core.calibrations.output_unit`, which is R56 §2.3's one-hop `resource.column` form and
the first use of it for a unit rather than a clock. `registry/check.py` already resolves that form
and requires the declared reference to exist.

`point_index` is a `structural_index`, and the key is not the input value even though the seven
inputs are distinct. R47 struck `interval_index` and keyed an interval on `start_tick` instead,
which works because a tick is an integer; an equality join on a `float64` is not safe, so the index
stays.

Two rules follow, both the shape of R49 §2.4's `scope_pair_complete`: a calibration declaring one
unit and not the other is a defect, and a calibration with points declaring no units is a defect.

### 2.4 A calibration that is an array names the asset holding it

A manipulator transform and a camera's intrinsics are arrays rather than curves, and a calibration
whose content is one declares `array_asset_id`, referencing `core.array_assets`. R65 §2 already
gave that table a `device_id`, so an array knows the instrument it came from; `array_asset_id` is
what says the array *is* that instrument's calibration.

A writer reading `calibration_info_np2_2025_04_09T10_00_00.npy` emits it as an owned array asset,
as the waveform adapter already does with a template. The `.npy` does not become a
`core.source_files` row: that table records what fed a processing run, and §1.2 settles that a
calibration is not one.

### 2.5 A calibration with no recorded content is still a calibration

A row of `core.calibrations` with no points, no `array_asset_id` and no `detail_kind` records that
the calibration was in force and that the packet holds nothing further. That is the state
`ecephys_776259`'s manipulator calibration would be in if its `.npy` could not be read, and a
consumer **MUST** read such a row as *unrecorded* rather than as *absent*.

`detail_kind` is the escape hatch, an R48 `discriminator` declaring `resolves: optional` and
holding the resource ID of a table carrying a shape core does not define. R55 §2 is what makes
this the right instrument: a discriminator **names without depending**, so an R17 extension may
carry a calibration core has never seen without core referencing an extension. `resolves:
optional` is what makes an unresolvable value a fact (R55 §2.2). R49 §2.2 made the same judgement
for a run scoped to a rig the packet does not hold.

`detail_kind` carries no paired value. R55 §2.3.1 admits one only for a resource with a
single-column key, and a detail table keyed by its calibration has a composite one, so a detail is
found by joining the calibration's own key — R55's shared-key shape, which `interval_kind` already
uses. That is also why §2.4's array route is an ordinary declared reference rather than a
discriminated one: Tier 1 generates an anti-join for `array_asset_id` and generates nothing for a
value reached through a discriminator, so the shape core defines gets the stronger check and the
shape it does not gets the escape hatch.

A source stating that no calibration was performed gets no row. The absence of a calibration is
not a calibration, and R66 §1.4 refuses a field that records nothing.

### 2.6 Only the calibration itself declares a free-form column

`core.calibrations` declares `metadata` and the two child tables **MUST NOT**. The rule that
decides it is identity: a table's key holds an identifier of its own, so the row is a thing
rather than a statement about other things, and `core.calibrations` is the only one of the three
whose key does. A source states more about a calibration than the ten typed columns above model —
the fit a curve was reduced to, the standard it was measured against, who performed it — and none
of that is sayable about one of its points.

A point's own unmodelled facts belong on the calibration, and a device's on `core.devices`, which
declares `metadata` already; §5 measures how much of it a packet fills.

## 3. What this does not change

- **No existing table, column or rule.** Three resources are added and nothing is amended;
  `aind_opto.emissions.power_mw` and `dynamic_foraging.sessions.left_valve_open_time` keep their
  definitions and gain something to resolve against.
- **No packet becomes invalid.** No existing table gains a column, so a packet carrying none of
  the three is conforming. Both measured packets are, and stay so until they are rebuilt.
- **A curve does not become a JSON string.** `core.devices.metadata` would hide the seven points
  from every rule, which is R66 §1.4's and R70 §2's argument, and two parallel lists are what R3
  §3.0 forbids by name. What does belong there is §2.6's remainder: what a source says about a
  device that no column models.
- **No calibration is required.** A packet holding none is conforming. Part 09's metadata minimalism
  makes core carry what is needed to interpret, and a session with no calibrated quantity needs
  none.

## 4. Consequence

35 tables become **38**, 316 columns become **335**, and 90 references become **97**. Two Tier 2
rules are added, both on `core.calibrations`. Tier 1 gains the checks those references and required
columns imply, none hand-written.

The two packets hold **ten calibration records** between them: two water curves each, and six
`ephys_modules` in `ecephys_776259` citing one manipulator calibration. Written out they are
**five** rows of `core.calibrations` — three and two — with **28** rows of
`core.calibration_points`, seven per curve. `core.calibration_devices` holds a row only for a
device the packet has, which today is the manipulator calibration's six probes and neither lick
spout.

The writer gains a `rig.json` and `session.json` reader for the calibration blocks; the AIND
session adapter already parses both files for other reasons, so no source is opened that was not
opened already. §2.2's device rows are the new work: a lick spout is not a device the writer
builds today.

Both packets are rebuilt to gain the tables. R61 §3 already settled what that costs: a correction
is a rebuild, and this one re-reads no external resource.

## 5. Open

- **Where a source's statement that it did not calibrate should go.** §2.5 writes no row, and
  `stick_microscopes` carries the note *"Did not record arc or module angles, did not calibrate"* —
  real information about a session that this revision drops. It is a fact about a device rather than
  about a calibration, so its home is `core.devices.metadata`, filled on 13 of 20 device rows in
  `ecephys_776259` and 20 of 21 in `ecephys_786867`. What stays open is whether an adapter should
  record a note that asserts no calibration, which is a question about the device adapter.
- **Whether a calibration should declare what it maps to what.** `calibration_type` says
  `water_volume` and the units say seconds to microlitres, and nothing says the input is a valve
  open time rather than a pressure. The source states it only in `description`, which is prose, and
  a typed answer would need a vocabulary of physical quantities this specification has no other use
  for.
- **Whether `power_mw` should be derived rather than stored.** `aind_opto.emissions.power_mw`
  becomes recomputable from a calibration and a drive setting, which the extension does not record.
  Storing the computed value and the curve that produced it is a denormalization of the kind
  `core.units.n_spikes` already is, and validating it needs the drive setting that no packet
  carries yet.

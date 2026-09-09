# A Device Declares What Kind of Thing It Is

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Adds `device_kind` to `core.devices`; adds a clause to `02` §8.3 |
| **Depends on** | R102 §3.3 (a camera is recorded as a device), R54 §2 (a kind in the key, with per-kind detail tables), R55 §2.1 (a discriminator names a table), R55 §2.2 (`resolves` says whether an unmatched value is a defect), R90 §3.5 (the shared-key resolution shape), R17 §2 (an extension is a registry document in the same format) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.devices` is one flat table for every instrument a session used: a Neuropixels probe, a
headstage, a basestation, a Harp sniff detector, a camera. Each carries the same eleven columns,
and a fact true of one kind has nowhere to go — a camera's target, an objective's magnification, a
thermistor's range.

Adding a column for each would give the other rows a field that does not apply to them. This part
declares instead which table holds a device's kind-specific facts, using the mechanism R54 §2 and
R90 §3.5 already established for intervals, and leaves the tables themselves to extensions.

Measured on **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25), whose
`core.devices` holds 21 rows.

## 2. Background

Informative.

### 2.1 Specialisation in the registry

R54 §2 gave `core.intervals` an `interval_kind` in its key and per-kind detail tables sharing it,
and R90 §3.5 named that the **shared key** — the class-table-inheritance mapping — and made
resolution generic: read the kind, take that resource's primary key from the registry, join.
`dynamic_foraging.trials` and `vr_foraging.sites` are the two that exist.

`core.devices` has no discriminator, and **no table in the registry is keyed on `device_id`**.
The two tables that look like specialisations are not. `core.probes` is keyed on `probe_id` and
references the device, because `01` §3.6 makes a probe "a device that carries electrodes" and R67
§3 measured four probes to one quad-base device — a different entity at a different cardinality,
which is why `core.electrodes`, `core.sorting_runs` and `core.units` reference it and not
`core.devices`. `core.calibration_devices` is a link table of `(calibration_id, device_id)`.

### 2.2 What a camera states

A camera is the first instrument to arrive whose facts `core.devices` cannot hold. `rig.json` for
`ecephys_786867` declares two assemblies, and beyond the manufacturer, model and serial that
`core.devices` already models, each states a `camera_target` — `Face side right`, `Face bottom` —
a sensor of 720×540, `Monochrome` chroma and a maximum frame rate of 522 Hz. Four facts that
apply to two of 21 rows.

`core.devices.metadata` is where they can go today, and it is not empty: **20 of 21** rows carry
one, holding prose such as `{"description":"Neuropixels 2.0 single shank probe with cap"}`. What
`metadata` cannot do is be read by a rule (R66 §1.4), which is the whole of the difference.

### 2.3 Which instruments core models

`01` §3.17 states the position: an array asset holds any sampled quantity, "this standard names
the concepts it defines … and it does not enumerate instruments", which R65 §1 rests on when it
answers *which signal* with the device rather than with a vocabulary.

`core.probes` is not a counter-example. `01` §3.6 defines a probe as a device that **carries
electrodes**, and an electrode is a concept the format is built on — `core.electrodes`,
`core.array_channels`, `core.unit_electrodes` and every spike hang off it. A probe is in core
because electrodes are, not because it is an instrument. A camera carries nothing core models.

## 3. Decision

### 3.1 `device_kind`

`core.devices` gains **`device_kind`**, a `string` with R48 role `discriminator`, nullable, and
`resolves: optional` (R55 §2.2): it holds the dotted resource ID of the table carrying this
device's kind-specific facts.

`optional` because most devices have none. A headstage that declares no `device_kind`, or one
whose value names a resource the packet does not carry, states a fact: the instrument had nothing
further to say, or the extension that would say it is absent. Neither is a defect (R55 §2.2).

The detail table shares `core.devices`' key: its primary key **MUST** begin `device_id`, so
resolution is R90 §3.5's shared-key join and needs no second column.

### 3.2 Where a detail table lives

Core **MUST NOT** declare a device detail table. `01` §3.17 makes this standard name no
instruments, and a `core.camera_devices` would name one; behind it would come tables for the
thermistor, the respiration sensor and the heart-rate monitor that `01` §3.17 lists by name.

An R17 §2 extension declares them instead, which is what a discriminator makes possible: R55 §2.6
records that core may name an extension's table without depending on it, because the value is a
name and not a reference. `aind_opto` already has that shape, holding a rig's own facts in a rig's
own registry.

### 3.3 What a writer sets

A writer **MUST** set `device_kind` where it writes a detail row, and **MUST NOT** set it
otherwise. A value naming a table the packet does not carry is permitted (§3.1) and is what a
packet built without an extension looks like; a value naming a table the packet carries and a row
it does not write is a dangling kind, which Tier 1's discriminator checks catch (R55 §2.4).

A fact that no detail table models stays in `metadata`, where 20 of 21 devices already keep one.
A detail table exists to promote a fact out of `metadata`; what justifies writing one is a rule or
a query that has to read the fact (R66 §1.4).

## 4. What this does not change

- **No table is added.** One column is added to `core.devices`; the tables it names are an
  extension's to declare.
- **`metadata` keeps its job.** R97 §3.3 puts what a source stated and the standard does not
  model, and §3.3 leaves it there until something needs to query it.

## 5. Consequence

330 columns become **331**, and no reference is added: a discriminator names without referencing
(R55 §2.6). Tier 1's discriminator checks go from 14 to **16**, the two a discriminator implies
(R55 §2.4) being that the value is a dotted resource ID and that it resolves where the packet
carries the resource. `02` §8.3 gains the clause §3.1 states. No packet is invalidated: the column
is nullable and both packets pass with it unset.

`check.py` gains the structural check that a table named by a `device_kind` value begins its
primary key with `device_id`.

## 6. Open

- **Whether a camera detail table is worth writing.** §3.2 leaves it to an extension and nothing
  declares one. The evidence is four filled facts on two rows of one session — `camera_target`,
  a sensor size, a chroma and a maximum frame rate — which is below what R66 §1.3 asks of a new
  column, and `metadata` holds them meanwhile. A second rig, or a query selecting videos by view,
  is what would settle it.
- **Whether a probe should carry a kind too.** `core.probes` is a separate entity (§2.3) and could
  itself specialise — a Neuropixels 1.0 and a tetrode drive state different things — which this
  part does not consider and which the same mechanism would serve.

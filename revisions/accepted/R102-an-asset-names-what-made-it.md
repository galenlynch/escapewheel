# R102 — An Asset Names What Made It

| | |
|---|---|
| **Status** | **Accepted** 2026-09-09 |
| **Amends** | Part 01 §3.5 (a camera is a device), Part 01 §3.17 (an array names the run that made it), Part 01 §3.18 (a media asset names the device that recorded it); adds `processing_run_id` to `core.array_assets` and `analysis.array_assets`, and `device_id` to `core.media_assets` |
| **Depends on** | R23 §1.1 (derivedness belongs in provenance, not a vocabulary), R41 §2.1 (currency is keyed on the producing run), R65 §1 (an array names the device that made it), R67 §2.2 (a device's identity is the serial the source states), R82 §2.1 (an undeclared currency is an error), R9 §4 (an output is recorded at resource granularity) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

A packet's assets are made by something — a run computes an array, an instrument records a video —
and neither asset table says what. `core.array_assets` cannot name the run that produced it, and
`core.media_assets` cannot name the device that recorded it, so the two questions a consumer asks
first about a derived array and about a video are both unanswerable in SQL.

This part adds the two references and states what a writer fills them from.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25),
which hold 25 array assets and 4 videos between them.

## 2. Background

Informative.

### 2.1 An array has no route to its run

`core.event_streams` has carried a `processing_run_id` since R23 §2, and `core.sorting_runs`,
`core.curation_versions`, `core.electrode_coordinates` and `core.unit_coordinates` have carried
one since R41 §2.1 and R60 §2.1. `core.array_assets` has none.

Those five are the tables whose rows name the run that produced them. Three more columns share the
name and answer something else: `core.processing_runs.processing_run_id` is the run's own key,
`core.processing_run_inputs` links a run to its inputs, and `core.preferred_runs` names the run a
packet prefers (R41 §2.2).

The manifest has the field — R9 §4 records an output at resource granularity, and
`registry/manifest.schema.json` gives every resource a `processing_run_id` — and **1 of 46**
resources in `ecephys_776259` fills it. What the manifest cannot do is be joined: R9 §4 puts
outputs there precisely so they are not per row, so no Tier 2 rule and no `Packet.duckdb()` query
reaches from an array to the run that produced it.

That is what makes it a defect rather than a preference. R41 §2.1 keys currency on the producing
run and R82 §2.1 made an undeclared currency a mandatory **error**, so a packet holding two waveform
arrays from two sortings must declare which is current and has no column to declare it through.
Neither packet holds that case, and R82 §2.1's rule is unenforceable for arrays the moment one does.

### 2.2 Media assets lack a device column

R65 §2.1 gave `core.array_assets` a `device_id` and gave `core.media_assets` none, so R65 §1's
rule — which signal an asset holds is answered by the device — reaches one asset table and not
the other.

`core.media_assets` declares `media_asset_name`, `uri`, `format`, `pts_rate_num`/`pts_rate_den`
and `clock_id`, and none of them separates a behaviour video from a miniscope movie, both of which
are `mp4` written by a camera.

### 2.3 What the rig states about its cameras

The packet's 21 devices are seven probes, a `SniffDetector` and the Open Ephys chain —
basestations, connect boards, headstages — and **no cameras**, while `ecephys_786867` holds four
videos.

The source states them. `rig.json` for that session declares two camera assemblies with distinct
serial numbers, `23022730` and `23022721`, both Teledyne FLIR Blackfly S BFS-U3-04S2M, which is
what R67 §2.2 makes identity; `sources/aind.py` already opens that file, for the rig's time zone
alone. `session.json` names three cameras where the rig declares two, and the packet holds a
fourth video, `clip`, that neither describes.

One camera is called five things across the artifacts — `Right Camera assembly`, `Right size of
face camera`, `Face side right`, `Face Side Right`, and the file stem `side_camera_right` — none
derivable from another by rule, and the packet carries only the last. Part 01 §3.5 already settles
what a consumer does with that: a name is unconstrained by this standard, and the reference is the
statement.

## 3. Decision

### 3.1 An array's producing run

`core.array_assets` and `analysis.array_assets` gain **`processing_run_id`**, `int32` nullable,
referencing `core.processing_runs`. An array a run produced **MUST** name it; an acquired array
declares none, which is the reading R23 §2 gives a stream.

A column rather than the manifest's field, which restates nothing it can reach. R9 §4 records an
output at resource granularity so that provenance is not per row, and the consequence is that the
link is invisible to SQL; R41 §2.1 keys currency on the producing run and R82 §2.1 makes an
undeclared one an error, so a rule must be able to join an array to its run. The manifest's field
keeps R9 §4's meaning, for resources that are not rows of a table.

### 3.2 A media asset's device

`core.media_assets` gains **`device_id`**, `int32` nullable, referencing `core.devices` — the
column R65 §2.1 gave the array table and not this one.

A writer **MUST** name the device where its source states one, and **MUST NOT** infer it from a
file name (Part 01 §3.5). Where the source states none the column is null, and a consumer **MUST**
report the instrument as unrecorded rather than read one out of the asset's name.

### 3.3 Which instruments get a device row

A writer **MUST** record an instrument its source declares as a `core.devices` row, whatever kind
of instrument it is, and identity is the serial the source states (R67 §2.2). Part 01 §3.5 defines a
device as "a physical instrument used during acquisition" and names no kinds, so a camera is one
on the same terms as a headstage.

This is a writer obligation and not a schema change: `core.devices` already models everything the
rig states about these two — a manufacturer, a model, a serial. What it does not model is where a
camera points, which §6 records.

## 4. What this does not change

- **`core.probes` is unaffected.** A probe is not a device subtype: Part 01 §3.6 makes it "a device
  that carries electrodes", R67 §3 measures four probes to one quad-base device, and three core
  tables reference it because electrodes do.

## 5. Consequence

330 columns become **333** and 97 references become **100**, measured against the registry as R101
left it — the other proposed changes to the asset tables move the same counts, and whichever lands
second is measured again. All three columns are nullable, so Tier 1's not-null checks are unchanged
at 154, and no Tier 2 rule changes.

Part 02's column tables are generated, so they follow from the registry. What is written is in Part 01:
Part 01 §3.17 gains §3.1's rule, Part 01 §3.18 gains §3.2's, and Part 01 §3.5 gains §3.3's, each beside the rules
R66, R67 and R85 already put there.

The registry change is the whole of what lands now, because every writer obligation §3 states is
blocked on something a source does not supply, and each blockage is worth recording.

The column is owed more widely than §2.1 suggested. **12 of 14** array URIs in `ecephys_776259`
and **10 of 11** in `ecephys_786867` sit under the NWB's `processing/` group rather than
`acquisition/` — `.../processing/ecephys/LFP/ElectricalSeries45883-1-LFP/data` — so nearly every
array in both packets was computed by a run neither packet records, and declares null until one
does.

`waveforms.py` names no run, and none of the twelve sortings produced its arrays: `waveform_mean`
spans all **6,781 units** of `ecephys_776259` across **12 sorting runs**, so what produced it is an
extraction over all of them that the packet does not record. `processing_run_id` is null on those
arrays until it does, which is the column exposing a gap in provenance rather than failing to
express one.

`sources/aind.py` can read `rig.json`'s two camera assemblies, and emitting them puts
`core.devices` in its `PRODUCES` and in both recipes' `contributes`, which R63 §2 makes a change to
the recipe rather than to the adapter.

`sources/video.py` cannot name a camera at all. The video directory holds four `.mp4` files and
their timing CSVs and nothing else, so the only link from `side_camera_right.mp4` to the Teledyne
FLIR with serial `23022730` is the file's name — which §3.2 forbids using, and rightly: `clip.mp4`
matches no assembly, and a rig that renamed its files would silently repoint every video at the
wrong instrument. `device_id` is null on all four videos until a source states the link.

Both packets are rebuilt for the columns, which R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98, R99
and R101 already require.

## 6. Open

- **Where a camera's view lives.** §3.3 gets the camera into `core.devices` as an object and says
  nothing about where it points, which is what separates `bottom_camera` from `side_camera_left`.
  The source states the view as a **label** — `camera_target` of `Face side right` and `Face
  bottom` — and leaves `position` **null** on both assemblies, with `rig_axes` and `origin` null
  beside them, so a pose column would be the principled shape and empty in every row this rig can
  produce (R66 §1.3). Adding a column to `core.devices` for it would give 21 rows a field that
  applies to two.
- **Whether a packet should record the run that extracted its waveforms.** §5 measures that
  `waveform_mean` spans twelve sortings, so the run that produced it is neither of them and is
  absent from `core.processing_runs`. Recording it would make §3.1's column fillable and would put
  the twelve sortings in `core.processing_run_inputs` beneath it, which is the shape R9 §4 already
  provides.
- **Whether `clip` has a source at all.** `ecephys_786867` holds a fourth video that neither
  `rig.json` nor `session.json` describes, so §3.2 leaves its `device_id` null. Whether that is an
  upstream omission or a file that should not be in the packet is a question for the recipe.

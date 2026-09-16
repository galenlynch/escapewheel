# Twelve of eighteen resources mix base NWB with one producer's columns

`escapewheel-writer`'s NWB adapter (`escapewheel-writer/src/escapewheel_writer/sources/nwb.py`)
is to be split: the reading base NWB defines stays in this distribution, and what one
institution's pipeline writes leaves with the AIND adapters. Deciding which methods move needs an
inventory of what the adapter actually reads, because the paths it walks — `units`,
`intervals/trials`, `general/extracellular_ephys/electrodes`, `acquisition` — are all base NWB and
say nothing about the columns inside them. Produced 2026-09-16, against
`ecephys_786867_2025-09-25_12-43-56_experiment1_recording1.nwb` in `/mnt/Data/ephys/`, 10 probes
and 4,608 electrodes. The second session, `ecephys_776259_2025-04-09`, is no longer on this disk;
where it differs, the difference is quoted from
[`nwb-core-schema-comparison.md`](nwb-core-schema-comparison.md).

## 1. The file carries the schema that settles the question

An NWB file caches the schema it was written against, so "does the standard define this name" is
answerable from the artifact rather than from memory: `specifications/core/2.9.0` inside this file
holds `nwb.file`, `nwb.misc`, `nwb.ecephys`, `nwb.epoch`, `nwb.device` and `nwb.base` as JSON. A
read is classified **base** where that schema names it, and **dialect** where nothing does.

Between the two sits a third class this inventory keeps separate, because it changes who else can
use the reader. A name the standard omits may still be one the sorting ecosystem agrees on:
SpikeInterface 0.104.1 (`~/Documents/Code/spikeinterface`, `0.104.0-43-g4e3f63c0c`) reads
`channel_name` and `unit_name` out of NWB files **it did not write**
(`src/spikeinterface/extractors/nwbextractors.py:674, 752, 1255`), and sets `inter_sample_shift`
as a recording property from Open Ephys, SpikeGLX and IBL alike. Those are conventions of the
tools, not of one rig. The names this adapter reads that appear nowhere in SpikeInterface —
`ks_unit_id`, `device_name`, `brain_region_id`, `ccf_ml` — are the producing pipeline's alone.

## 2. Base NWB defines 36 of the names the adapter reads

| Where | Names read | Defined by core 2.9.0 |
|---|---|---|
| `NWBFile` scalars | `session_description`, `identifier`, `session_start_time`, `timestamps_reference_time`, `file_create_date`, `nwb_version`, `general/session_id`, `general/lab`, `general/protocol`, `general/institution` | 10 |
| `Subject` | `subject_id`, `species`, `sex`, `genotype`, `date_of_birth`, `strain` | 6 |
| `Device` | the `general/devices` membership, `description`, `manufacturer` | 3 |
| `ElectrodeGroup` | the `general/extracellular_ephys` membership, `description`, `location`, the `device` link | 4 |
| `ElectrodesTable` | `group_name`, `imp`, `rel_x`, `rel_y`, `location` | 5 |
| `TimeSeries` | the `acquisition` membership, `timestamps`, `data`, `data/unit`, `description` | 5 |
| `TimeIntervals` | `start_time`, `stop_time`, `id` | 3 |

Two entries are worth naming for what they are, since both look like dialect and are not. The
`device` link on an ElectrodeGroup is base; `zarr_link` is only how `hdmf-zarr` serializes a link,
so `probes()` reading it is backend-specific rather than producer-specific. And `location` on the
electrodes table is base NWB's own region label, which is what lets `_annotation` fall back to it
when the atlas columns are absent — base NWB carries a region **name**, and it is the structure
**id** that R59 §2 found only in the dialect.

`general/subject` holds six members here and `strain` is not among them, so that read yields null;
`age`, which the schema defines and this adapter does not map, travels into
`core.subjects.metadata` uninterpreted.

## 3. The contact identifier rests on a name the standard does not define

`electrode_name(group_name, channel_name)` composes every contact's packet-wide identifier, and
only half of that pair is base NWB. `ElectrodesTable` defines `group_name`; `channel_name` appears
in no version of the schema. It is needed because neither column identifies a contact alone — the
shanks of a quad-base probe reuse one numbering, so `electrode_name` repeats across 1,920 distinct
values over 4,608 rows, and `channel_name` restarts per probe.

`_electrode_ids` subscripts `columns["channel_name"]` without a guard, so an NWB carrying only what
the standard defines raises `KeyError` rather than reporting what is missing. That the adapter has
never met such a file is a fact about which files it has read, not about the format. Naming a
contact from base NWB alone is an open question this inventory does not settle; what it settles is
that the question exists, and that it sits in the base half of the split rather than travelling
with the dialect.

## 4. One producer's dialect is 17 names and three conventions

| Where | Dialect names |
|---|---|
| `ElectrodesTable` | `electrode_name`, `ccf_ml`, `ccf_ap`, `ccf_dv`, `brain_region_id`, `ccf_id`, `ccf_acronym`, `ccf_name`, `ccf_structure_id_path` |
| `Units` | `ks_unit_id`, `device_name` (the CCF and atlas names repeat here) |
| `TimeIntervals` | `goCue_start_time`, `reward_outcome_time`, `delay_start_time`, `animal_response`, `rewarded_historyL`, `rewarded_historyR` |

The three conventions are not columns, which is why grepping the call sites misses them.

- **A device's model and serial are packed into its `description`**, matched by
  `DEVICE_DESCRIPTION`. §5 measures it.
- **An acquisition stream's instrument is named in prose**, matched by `SIGNAL_DEVICE`: "Sniff
  detector continuous signal imported from HARP SniffDetector__32.bin". One of the 8 streams
  carries such a sentence, and `general/devices` lists probes alone, so for that array the
  sentence is the only statement of what made it.
- **A stream's name ends in `_time`**, which `event_streams` strips to get `event_type`. Seven of
  the 8 streams here do. The strip degrades gracefully rather than breaking — a stream named
  `licks` yields `event_type` `licks` — so this seam costs a base file nothing.

The 60 remaining trial columns need no classification: `intervals()` splits them into what varies
per trial and what is constant across the session and carries both verbatim, interpreting neither.
That mechanism is generic; only the six names above are read for their meaning.

## 5. The device serial reaches the packet only through a parsed sentence

Core 2.9.0 defines `serial_number`, `model_number` and `model_name` as `Device` attributes. **No
device in this file sets any of them**: all 10 carry `description` and `manufacturer` and nothing
else. Every one of the 10 descriptions parses, yielding a serial in 10 of 10 and **a model in 0 of
10** — the model field is written empty, as in `Model:  - Serial number: 23176516323 -
Description: Neuropixels 2.0 single shank probe with cap`.

So `core.devices.model` and `core.probes.probe_type` are null for this session by construction, and
the serial that decides device identity — 7 distinct across 10 rows, which is what collapses the
four shanks of a quad-base probe into one device — exists nowhere a base reader would look. A base
NWB reader would emit 10 devices with no serial and no model, and the identity collapse would not
happen.

## 6. Two resources are wholly dialect and twelve mix

| Class | Resources | Count |
|---|---|---|
| Base throughout | `core.subjects`, `core.clocks`, `core.clock_anchors`, `core.array_dimensions` | 4 |
| Base reads with a dialect seam | `core.sessions`, `core.devices`, `core.probes`, `core.electrodes`, `core.coordinate_frames`, `core.coordinate_frame_axes`, `core.electrode_coordinates`, `core.electrode_coordinate_values`, `core.event_streams`, `core.events`, `core.intervals`, `core.array_assets` | 12 |
| Dialect throughout | `core.unit_coordinates`, `core.unit_coordinate_values` | 2 |

Each seam, named so the split has something to act on: `core.sessions` folds in the constant trial
parameters; `core.devices` and `core.probes` depend on the parsed description (§5);
`core.electrodes` takes its identifier from `channel_name` (§3), its `local_electrode_label` from
`electrode_name`, and two atlas strings into metadata; the four coordinate resources gain the `ccf`
entry of `FRAME_AXES` and the atlas annotation; `core.event_streams` and `core.events` gain the
three trial-event streams and their rows; `core.intervals` reads six named trial columns; and
`core.array_assets` gets its `device_id` from the HARP sentence.

The two dialect resources are dialect for one reason rather than two: `_unit_identity` joins an
array row to a unit on `(device_name, ks_unit_id)`, and with that pair unavailable there is no unit
to attach a coordinate to.

## 7. What this decides for the split

**Moving methods will not separate these.** Of the 18 resources this adapter produces, 2 could move
whole and 12 would have to be cut in half, which R108 §3.2 forbids: a row is composed by one source
or it is not composed at all. The seams are also mostly one line each — a column name, a dict
entry, a regex — so a split that moved them would leave two copies of the surrounding read.

That is what the decided shape handles, and this inventory is evidence for it rather than against:
the base reader stays here and reads what §2 lists, the dialect adapter calls it as a library, and
each resource is emitted whole by whichever of the two owns it. A recipe already arbitrates that
ownership (Part 05 §3.3). The refinement the dialect adapter performs on a base row — adding a
serial, an atlas annotation, a `ccf` frame — happens before it emits, so no packet row is composed
from two sources.

Four consequences worth carrying into the implementation:

1. **`core.electrodes` cannot move to the base reader unchanged** (§3). Its identifier needs
   `channel_name`, which the standard does not define.
2. **`core.devices` loses the serial when read as base NWB** (§5), and with it the quad-base
   collapse. The base reader emits one row per NWB Device; merging by serial is the dialect's.
3. **`FRAME_AXES` splits cleanly**: `probe` is `rel_x`/`rel_y`, both base; `ccf` is entirely
   dialect. The frame machinery — `_populated_frames`, `coordinate_frames`,
   `coordinate_frame_axes` — is generic over whatever the dict holds.
4. **`_unit_identity` moves whole**, and takes the two unit-coordinate resources with it.

# Core NWB schema versus the core registry

Read from the schema NWB embeds in its own files — `specifications/core/2.9.0` in
`ecephys_786867_2025-09-25_12-43-56_experiment1_recording1.nwb`. Produced 2026-08-26.

The question is not whether to imitate NWB. It is whether NWB's core schema names concepts
this specification lacks, since NWB has had two decades of contact with real recordings.

## 1. How much of an NWB file is schema at all

| Table | Columns in the file | Columns core NWB defines |
|---|---:|---:|
| `units` | 55 | 12 |
| `general/extracellular_ephys/electrodes` | 19 | ~7 |

The electrodes table's 19, read from `colnames`: `location`, `group`, `group_name`,
`channel_name`, `inter_sample_shift`, `gain_to_physical_unit`, `offset_to_physical_unit`,
`physical_unit`, `rel_x`, `rel_y`, `brain_region_id`, `ccf_ml`, `ccf_ap`, `ccf_dv`, `x`, `y`, `z`,
`imp`, `filtering`. Fifteen carry data; `x`, `y`, `z` and `imp` are NaN for all 3840 and
`filtering` is empty. `ecephys_776259_2025-04-04` carries 20 instead, differing in the atlas
annotation — `ccf_id`, `ccf_acronym`, `ccf_name`, `ccf_structure_id_path` where this session has
`brain_region_id` alone — and adding `electrode_name` while dropping the three scaling columns.

The remainder are `DynamicTable` columns added at runtime, conforming to nothing — not core,
not an `ndx-` extension. **Most columns in the file are unvalidated.** That is the facility
R17 answers with typed extension registries.

## 2. Concepts core NWB has that the registry lacked

### 2.1 `Units.obs_intervals` — when a unit was observable

Shaped `[num_intervals, start|end]`, indexed per unit, so a unit may have several disjoint
windows. Absent from this file, which does not populate it, but present in the schema
because units drift in and out of a recording.

The registry had no equivalent, which left `core.units.firing_rate_hz` with no stated
denominator. **R18.**

### 2.2 `NWBFile.timestamps_reference_time` — wall-clock zero

"Date and time corresponding to time zero of all timestamps." R6's `tick_zero_utc` is the
same concept, and better placed: NWB carries one per file, the registry carries one per
clock, and a session with a probe clock and a behaviour clock has two different zeros.

No change needed.

### 2.3 `Subject.age` — an alternative to date of birth

"Can be supplied instead of `date_of_birth`." R4 §3.4 struck `age_at_session` from Part 09 as a
reconciliation rather than a feature, noting the redaction argument and deferring. NWB
supports it explicitly for that reason. Worth revisiting; not urgent.

### 2.4 `ElectricalSeries.channel_conversion` — per-channel scaling

"Channel-specific conversion factor. Multiply the data by this." The registry has
`core.array_assets.conversion`, `offset`, and `unit` as **scalars for a whole array**.

The AIND file carries the per-channel form as electrode columns:

```text
gain_to_physical_unit    offset_to_physical_unit    physical_unit
```

So a Neuropixels array whose channels differ in gain cannot be converted correctly from a
packet. `core.array_channels` is the natural home, and this is a real representational gap.

### 2.5 `inter_sample_shift` — channels are not sampled simultaneously

An AIND electrode column, not core NWB, but it belongs in this list. Neuropixels ADC
multiplexing means channels within one sample index are acquired at slightly different times.
The registry's tick model treats a sample index as one instant across all channels.

For spike timing at 30 kHz the shift is a fraction of a sample and usually ignorable. For
anything comparing phase across channels it is not.

### 2.6 `ElectricalSeries.filtering` — what was applied

A free-text attribute. `core.array_assets.kind` implies it — `raw`, `ap`, `lfp` — but nothing
records the actual filter. Minor.

### 2.7 `TimeIntervals.timeseries` — an interval pointing into a series

A `DynamicTableRegion` linking a trial to a region of a TimeSeries. The registry expresses
this through ticks on a shared clock instead, which is more general and needs no link.

No change needed.

## 3. Where the registry is ahead

- **Per-clock wall-clock zero** rather than per-file (§2.2).
- **Normalized tags.** NWB's `TimeIntervals.tags` is a ragged column; `core.trial_tags` is a
  relation, queryable by equality (R3 §3.2).
- **Attributed quality labels.** NWB has no designated quality column and no way to say which
  of several labels it stands behind (R16).
- **Typed amplitude units.** NWB's `physical_unit` is a dynamic column; R11 §2 makes it a
  declared field on the sorting run.
- **A closed column set.** Every registry column has a type, a presence state, and a rule set.

## 4. Where NWB's deprecations are informative

`Device` marks `manufacturer`, `model_number`, and `model_name` **deprecated** in 2.9.0,
keeping only `description` and `serial_number` undeprecated. `core.devices` carries
`manufacturer`, `model`, and `serial_number` — mirroring two fields NWB is moving away from.

Worth watching what replaces them before following.

## 5. Two things checked and found not to warrant changes

**Phy export.** The pipeline also writes phy format — one TSV per property, keyed by
`cluster_id`. Structurally that is a column store and maps onto tables without difficulty.
Its contribution is evidential rather than structural: it carries a fourth quality label,
`cluster_group`, in phy's canonical curation slot, so one sorting appears in three
serializations with four label sources under three spellings. That strengthens R16 rather
than changing it.

**Drift correction.** `preprocessed/motion/` carries a displacement field of shape
`(2065 time bins, 10 depth bins)`, so probe position relative to the brain is time-varying in
principle. Measured, it is 19–31 µm peak-to-peak over 69 minutes — smaller than Neuropixels'
20 µm contact pitch and far smaller than CCF region boundaries. Static electrode coordinates
(R19 §3) are therefore adequate, and the motion field is a derived preprocessing artifact
belonging to an extension (R17).

Worth noting in passing: the motion estimate's temporal bins run from 14 425 742 s to
14 429 870 s. Those are neither session-relative nor Unix epoch, which is one more instance
of time origins in this data not being self-evident.

## 6. Outcome

| Finding | Disposition |
|---|---|
| `obs_intervals` | **R18** — `core.unit_observation_intervals` |
| Unvalidated dynamic columns | **R17** — extension registries |
| Per-channel conversion | **R19 §2** — `core.array_channels.conversion`, `offset`, `unit` |
| `inter_sample_shift` | **R19 §2** — `core.array_channels.inter_sample_shift` |
| Atlas structure id | **R59** — `region_id` on the coordinate row |
| `Subject.age` | open — R4 §3.4 deferred it |
| `filtering` | open, minor. Empty for all 3840 electrodes in this session |

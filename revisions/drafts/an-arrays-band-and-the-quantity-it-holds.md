# An Array's Band and the Quantity It Holds

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `01` §3.17 (`semantic_type` becomes nullable and is filled only where the facts cannot say it), R8 §4 (renames `raw`, strikes `waveform`, narrows what the column is for), the declarations of `kind` and `semantic_type` on the asset tables |
| **Depends on** | R102 §3.1 (an array names the run that produced it), R101 §3.1 (every string column declares `closed`, `open` or `free`), R101 §3.8 (records R8 §4's reserved set), R8 §4 (the four reserved kinds), R23 §1.1 (derivedness belongs in provenance, not a vocabulary), R50 §2 (a column is renamed where its name says less than its declaration), R65 §1 (an array names the device that made it) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.array_assets` carries two required, open, string columns describing what an array holds:
`semantic_type` and `kind`. Nothing says which answers what, their descriptions do not, and
nothing in the reader, the validator or `rules.json` reads either.

This part gives each its question and removes the pressure that filled both wrongly. `kind` states
which **band** of a sampled signal the array holds, so it is renamed `band` and becomes nullable;
`semantic_type` names the quantity, becomes nullable, and is for what the row's facts cannot say.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25),
which hold 25 array assets and 4 videos between them.

## 2. Background

Informative.

### 2.1 What the row already declares

What an array holds is already declared in facts. `device_id` names the instrument (R65 §2.1),
`clock_id` the time base, and `sample_rate_hz`, `unit`, `conversion` and `offset` the values;
`core.array_dimensions` gives the axes and their coordinates, and `core.array_channels` maps the
channels onto electrodes. Beside all of that sit two open strings, and searching `rules.json`,
`escapewheel-reader` and `escapewheel-validator` for either returns **nothing**.

Neither adds anything either. Grouped by every fact but the name and `semantic_type`, the arrays
come to **14 distinct tuples over 14** and **11 over 11**, so no two are told apart by a label.
On 22 arrays `semantic_type` holds `ElectricalSeries`, a class name for voltage per channel over
time — which `unit`, the channel map and the dimensions already give. On the three waveform arrays
it holds `waveform_mean` and `waveform_sd`, **the same strings as their `array_asset_name`**. `02`
§6 forbids exactly that: "A schema MUST NOT declare a column that duplicates what the data already
declares."

The columns came from `02`, where naming a class is how NWB says what a thing is. Every revision
since has moved the other way: R23 §1.1 replaced an acquired-versus-derived vocabulary with a run
pointer, R55 §2.1 made a discriminator name a table, R59 §2.1 put `region_id` beside
`region_label` because the id survives an atlas rename, R65 §1 answered which signal an array
holds with the device, and R83 §3 made an index resolve through a table rather than by guessing.
These two columns were not revisited.

The difference amounts to composition. NWB expresses "these series are the LFP" by wrapping them
in an `LFP` container, because HDF5 offers no other way to say it; a row carrying a device, a
unit, a rate and a channel map needs no wrapper. One thing the wrapper says and the row does not
is which **filter** produced the signal, and carrying that is the whole of what `kind` does.

### 2.2 R8 §4's reserved set

R8 §4 reserved four values with declared meanings:

```text
raw        unfiltered wideband extracellular voltage
ap         action-potential band
lfp        local field potential band
waveform   spike waveform snippets
```

`ap` and `lfp` name a part of a signal's spectrum. `raw` names a **processing stage** — what has
not been done to the signal — and describes the whole band by saying so. `waveform` names a thing
computed from spikes after sorting, which no filter produces and no acquisition system emits.

R23 §1.1 already ruled on the third: it rejected an acquired-versus-derived axis for `core`
outright — *"Acquired-ness is not a property of a fact but of how one came to know it, and it
belongs in provenance"* — and gave `core.event_streams` a `processing_run_id` instead of a
categorical value.

### 2.3 The values the writer emits

The three waveform arrays carry `kind` of `dense_array_asset`. That is one of the **manifest's**
six resource kinds — `table`, `materialized_table`, `dense_array_asset`, `media_asset`,
`document_asset`, `view` — which `registry/manifest.schema.json` declares and `writer.py:811`
writes into a manifest entry correctly. `waveforms.py:300` writes the same spelling into the
table row.

`semantic_type` shows the same pressure. The writer emits five values, of which one is an NWB
neurodata type (`ElectricalSeries`, `lfp.py:278`), two are **column names** of NWB's `Units` table
rather than types (`waveform_mean`, `waveform_sd`), and two are this implementation's own
(`signal` at `nwb.py:821`, `behavior_video` at `video.py:169`). A required column that `01` §3.17
says "carries no contract" is one a writer must fill with something, and inventing a label is what
filling it means.

### 2.4 What a source states about the filter

Expressing the band as a fact rather than a name would be two columns, a low and a high corner in
hertz, and it is not available. NWB models exactly this as `ElectricalSeries.filtering`, and the
Stage 1 inventory found it **empty for all 3,840 electrodes** of one session and **all 4,608** of
the other, recording that "nothing records the actual filter". That is R66 §1.3's control case: a
field a producer models and never fills is not evidence anyone needs it.

The sampling rate is not a substitute, and knowing it exactly does not help. It is declared: the
time axis of every LFP array carries `step_tick_num` 24 over `step_tick_den` 1 on a clock whose
tick rate is 30,000, so the rate is **30000 / 24 = 1250 Hz** as an exact rational (R20 §2.1) —
which is also why `core.array_assets.sample_rate_hz` is filled on 2 of 14 arrays and 1 of 11, a
column restating what the axis already declares (R3 §3.0). What 1250 Hz gives is a Nyquist bound
of 625 Hz and neither corner, so every lowpass below it is consistent with what the packet holds.
A signal can be decimated without being filtered and filtered without being decimated.

## 3. Decision

### 3.1 The band

`core.array_assets.kind` and `analysis.array_assets.kind` are renamed **`band`**, on R50 §2's
ground: a column is renamed where its name says less than its declaration, and `kind` is a
category noun for a thing that has a name. A manifest resource kind got into the column because
the name claimed more than the column delivers.

Three values are reserved:

```text
wideband   the unfiltered signal, spanning the whole band
ap         action-potential band
lfp        local field potential band
```

`raw` is renamed **`wideband`**. R8 §4 defined it as "unfiltered wideband extracellular voltage",
so the band was always what it meant; naming a processing stage instead is §2.2's mixture, one
level down inside the set. No packet writes `raw`.

`band` declares R48 role **`data`** and vocabulary **`open`**, neither of which follows from the
rename: R48 §2.2 gives a role no default and R101 §3.2 gives a vocabulary none, so a name nothing
classifies is a build error rather than a guess. The three values above are its `reserved_values`,
which R101 §3.4 permits only on an open column.

What a value holds is a conventional shorthand for **a filter the packet does not record**, and
the column's description says so (R101 §3.5). The vocabulary stays open (R8 §4): a rig whose
acquisition splits a signal differently names its own band and is conforming, and the three
reserved values are extracellular voltage's because that is the split this specification has seen,
not because the column is for ephys.

### 3.2 An array with no band

`band` is **nullable**. An array that was not split into bands declares none, and a consumer
meeting a null **MUST NOT** infer one from `semantic_type`, from the device or from the sample
rate. Each of those is evidence and none of them is the statement.

Requiring a value is what forced §2.3's. R65 §1 and `01` §3.17 make an array asset hold "**any**
sampled quantity, whatever instrument produced it", so a photometry trace, a respiration trace and
a spike-waveform template are all core-owned arrays with no band — and a column they must fill is
a column they will fill wrongly.

### 3.3 `waveform` is no longer a reserved value

R8 §4's fourth reserved value - `waveform` - is **struck**, and a writer **MUST
NOT** write it as a `band`. A waveform template is computed from sorted spikes
rather than split from a signal, so it names no band, and `semantic_type`
already carries `waveform_mean` and `waveform_sd` on exactly the arrays that
would have used it. The value was standing in for a run, and R102 §3.1 gives the
run a column of its own — which is R23 §1.1's disposal of a derived-ness
vocabulary, applied to the table R23 did not reach.

### 3.4 The quantity

`semantic_type` becomes **nullable** on all three asset tables, and a writer **MUST NOT** fill it
where the asset's declared facts already say what the asset holds. It is what the facts cannot
express, and null is the ordinary case.

`02` §6 settles the shape in one paragraph: a present nullable column is preferred to an absent
one, and a schema MUST NOT declare a column that duplicates what the data already declares.
Nullable satisfies both, where striking the column would honour the second by breaking the first.

Requiring it is what made it a duplicate. A column that `01` §3.17 says "carries no contract" and
that every row must fill is a column a writer invents a value for: `signal` and `behavior_video`
are two of the five values in use. `ElectricalSeries` is the other kind of filling, a class name
standing where the row already says voltage, per channel, over time.

Measured, the column goes from **29 of 29 assets filled to 7**. The 22 `ElectricalSeries` become
null, the three waveform arrays keep `waveform_mean` and `waveform_sd`, and the four videos keep
`behavior_video`. R102 §3.2 gave a media asset a `device_id` that would displace it, and R102 §5
measures that no source links a video file to a camera, so those four stay filled until one
does.

The waveform pair is the case that keeps the column. `waveforms.py` reads both from one analyzer
group, so a run pointer names one run for each; they share a session, a unit of `uV`, a sample
rate of 30,000 Hz and their dimensions, and `device_id` is null on both. Otherwise they are
separated by `conversion` alone, 0.06709875 against 0.06614436, which says that they differ and
not which is the mean. What separates them is a **statistic over one quantity**, and only this
column says it portably. Both arrays do carry the words in `array_asset_name`, which is `free`
(R101 §3.1): its spelling is this packet's, where an `open` value is meant to mean the same thing
in the next one.

Nothing checks it. Whether a fact is already declared elsewhere is a judgement no rule can make,
so this binds a writer and no validator, which is the shape R67 §2.4 has.

It stays `open` (R101 §3.1) and reserves nothing: the values in use are drawn from three
vocabularies, so no authority covers the column either (R101 §3.6).

## 4. What this does not change

- **The device still answers which signal.** Both name columns become nullable, so an array may
  carry neither. R65 §1 put the answer in `device_id` and this part leaves it there: a respiration
  trace is identified by the instrument that made it.

## 5. Consequence

`band` and `semantic_type` go from `required` to `nullable` on two and three tables, so Tier 1's
not-null checks go from 154 to **149**; the reserved set on `band` goes from four values to three,
with `raw` renamed `wideband`. `build.py` gains `band` in `ROLES` and in `VOCABULARY` (§3.1). No
column is added or struck, and no reference and no Tier 2 rule changes.

`02` names neither column and `01` §3.17 names `semantic_type`, so §3.4's rule lands there and
nothing else in the parts moves. The not-null figure is measured against the registry as R102 left
it: `a-coordinate-frame-declares-what-its-axes-mean` adds two required columns, so whichever of the
two lands second is measured again.

Both packets keep `band` of `lfp` on 22 arrays and declare it **null** on the three carrying
`dense_array_asset` today; `waveforms.py:300` stops setting the field, and `semantic_type` empties
to what §3.4 measures. Migration is
regeneration, as R53 §5 made it for identifiers: no packet carries `raw`, and both are rebuilt,
which R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98, R99 and R101 already require.

## 6. Open

- **Whether the band should be recorded as a filter.** §2.4 measures that no source on hand states
  one, so `band` stays a name for a filter the packet does not carry. Open Ephys writes the split
  in `settings.xml`, which the NWB adapter reads for one column already (R67 §2.3), so the fact is
  reachable and unclaimed. Two corners in hertz would make two rigs' splits comparable where two
  names are not.
- **Whether three bands are enough.** `wideband`, `ap` and `lfp` describe a Neuropixels 1.0 split,
  and a 2.0 probe emits wideband only. No packet on hand writes either of the first two, so the
  set is still R8 §4's examples rather than a survey.
- **Whether a statistic should be a column.** §3.4 leaves `waveform_mean` and `waveform_sd`
  distinguished by a label, where the difference is a statistic over one quantity. Two arrays in
  one packet pair is not evidence for a column (R66 §1.3), and a third statistic, or a consumer
  needing to select on one, would be.

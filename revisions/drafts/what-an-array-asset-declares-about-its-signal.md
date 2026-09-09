# What an Array Asset Declares About Its Signal

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R8 §4 (renames `raw`, strikes `waveform`, narrows what the column is for), the declarations of `kind` and `semantic_type` on the asset tables; adds `processing_run_id` to both array tables |
| **Depends on** | R101 §3.1 (every string column declares `closed`, `open` or `free`), R101 §3.8 (records R8 §4's reserved set), R8 §4 (the four reserved kinds), R23 §1.1 (derivedness belongs in provenance, not a vocabulary), R41 §2.1 (currency is keyed on the producing run), R50 §2 (a column is renamed where its name says less than its declaration), R65 §1 (an array names the device that made it), R82 §2 (an undeclared currency is an error) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.array_assets` carries two required, open, string columns describing what an array holds:
`semantic_type` and `kind`. Nothing says which answers what, their descriptions do not, and
nothing in the reader, the validator or `rules.json` reads either.

This part gives each column its question and removes the pressure that filled both wrongly. `kind`
states which **band** of a sampled signal the array holds, so it is renamed `band` and becomes
nullable; `semantic_type` names the quantity and becomes nullable; and the array gains the
`processing_run_id` that says what made it, which is where the value R8 §4 reserved for a derived
array belongs.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25),
which hold 25 array assets between them.

## 2. Background

Informative.

### 2.1 The table answers the question twice

What an array holds is already declared in facts. `device_id` names the instrument (R65 §2.1),
`clock_id` the time base, and `sample_rate_hz`, `unit`, `conversion` and `offset` the values;
`core.array_dimensions` gives the axes and their coordinates, and `core.array_channels` maps the
channels onto electrodes. Beside all of that sit two open strings, and **nothing reads either** —
no rule in `rules.json`, nothing in `escapewheel-reader`, nothing in `escapewheel-validator`.

The columns came from `02`, where naming a class is how NWB says what a thing is. Every revision
since has moved the other way: R23 §1.1 replaced an acquired-versus-derived vocabulary with a run
pointer, R55 §2.1 made a discriminator name a table, R59 §2.1 put `region_id` beside
`region_label` because the id survives an atlas rename, R65 §1 answered which signal an array
holds with the device, and R83 §3 made an index resolve through a table rather than by guessing.
These two columns were not revisited.

Composition is what the difference amounts to. NWB expresses "these series are the LFP" by
wrapping them in an `LFP` container, because HDF5 offers no other way to say it; a row carrying a
device, a unit, a rate and a channel map needs no wrapper. What the wrapper still says and the row
does not is which **filter** produced the signal, and that is the whole of what `kind` was
carrying.

### 2.2 The four reserved kinds name three different things

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

R23 §1.1 already ruled on the third. It rejected an acquired-versus-derived axis for `core`
outright — *"Acquired-ness is not a property of a fact but of how one came to know it, and it
belongs in provenance"* — and gave `core.event_streams` a `processing_run_id` instead of a
categorical value. `core.array_assets` got the categorical value and no run column.

### 2.3 A required column with nothing to hold is filled from elsewhere

The three waveform arrays carry `kind` of `dense_array_asset`. That is one of the **manifest's**
six resource kinds — `table`, `materialized_table`, `dense_array_asset`, `media_asset`,
`document_asset`, `view` — which `registry/manifest.schema.json` declares and `writer.py:811`
writes into a manifest entry correctly. `waveforms.py:300` writes the same spelling into the
table row.

`semantic_type` shows the same pressure. The writer emits five values, of which one is an NWB
neurodata type (`ElectricalSeries`, `lfp.py:278`), two are **column names** of NWB's `Units`
table rather than types (`waveform_mean`, `waveform_sd`), and two are this implementation's own
(`signal` at `nwb.py:821`, `behavior_video` at `video.py:169`). A required column that `01` §3.17
says "carries no contract" is a column a writer must fill with something, and inventing a label is
what filling it means.

### 2.4 The band is a label because no source records the filter

Expressing the band as a fact rather than a name would be two columns, a low and a high corner in
hertz, and it is not available. NWB models exactly this as `ElectricalSeries.filtering`, and the
Stage 1 inventory found it **empty for all 3,840 electrodes** of one session and **all 4,608** of
the other, recording that "nothing records the actual filter". That is R66 §1.4's control case:
a field a producer models and never fills is not evidence anyone needs it.

`sample_rate_hz` is not a substitute and is also absent — null on all 22 LFP arrays. A signal can
be decimated without being filtered and filtered without being decimated, so the rate is a proxy
for the band and not the band.

### 2.5 An array cannot reach the run that made it

`core.event_streams` has carried a `processing_run_id` since R23, and `core.sorting_runs`,
`core.curation_versions`, `core.electrode_coordinates` and `core.unit_coordinates` have carried
one since R41 §2.1 and R60 §2. `core.array_assets` has none.

The manifest has the field — R9 §4 records an output at resource granularity, and
`registry/manifest.schema.json` gives every resource a `processing_run_id` — and **1 of 46**
resources in `ecephys_776259` fills it. What the manifest cannot do is be joined: R9 §4 puts
outputs there precisely so they are not per row, so no SQL rule and no `Packet.duckdb()` query
reaches from an array to the run that produced it.

That is what makes the gap a defect rather than a preference. R41 §2.1 keys currency on the
producing run and R82 §2 made an undeclared currency a mandatory **error**, so a packet holding
two waveform arrays from two sortings must declare which is current and has no column to declare
it through. Neither packet holds that case today, and R82 §2's rule is unenforceable for arrays
the moment one does.

## 3. Decision

### 3.1 The band

`core.array_assets.kind` and `analysis.array_assets.kind` are renamed **`band`**, on R50 §2's
ground: a column is renamed where its name says less than its declaration, and `kind` is a
category noun for a thing that has a name. It also claimed more than the column delivers, which
is what let a manifest resource kind into it.

Three values are reserved:

```text
wideband   the unfiltered signal, spanning the whole band
ap         action-potential band
lfp        local field potential band
```

`raw` is renamed **`wideband`**. R8 §4 defined it as "unfiltered wideband extracellular voltage",
so the band was always what it meant, and `raw` said it by naming a processing stage instead —
the mixture §2.2 measures, one level down inside the set. No packet writes `raw`.

The value is a **conventional shorthand for a filter the packet does not record**, and the
column's description says so (R101 §3.5). Where a source states the filter, §6 is where that
lands; until one does, a consumer comparing `band` across packets is comparing two rigs' names for
their own splits, which is what an open vocabulary admits (R8 §4).

### 3.2 An array with no band declares none

`band` is **nullable**. An array that was not split into bands declares none, and a consumer
meeting a null **MUST NOT** infer one — not from `semantic_type`, not from the device, not from
the sample rate, each of which is evidence and none of which is the statement.

Required is what forced §2.3's value. A photometry trace, a respiration trace and a
spike-waveform template are all core-owned arrays with no band — R65 §1 and `01` §3.17 make an
array asset hold "**any** sampled quantity, whatever instrument produced it" — and a column they
must fill is a column they will fill wrongly.

### 3.3 `waveform` leaves the reserved set

R8 §4's fourth reserved value is **struck**, and a writer **MUST NOT** write it as a `band`. A
waveform template is computed from sorted spikes rather than split from a signal, so it names no
band; `semantic_type` already carries `waveform_mean` and `waveform_sd` on exactly the arrays
that would have used it; and §3.5 gives the fact it was standing in for a column of its own,
which is R23 §1.1's disposal of a derived-ness vocabulary applied where R23 did not reach.

### 3.4 The quantity

`semantic_type` states **what quantity** the asset holds, on every asset table, and becomes
**nullable**.

`01` §3.17 already fixes what an unrecognised value means: "A value this standard does not define
is a label and carries no contract, which is the honest state of affairs for a quantity whose
meaning lives in the device rather than in the format." A column that carries no contract and is
required is one a writer must invent a value for, which §2.3 measures at two of five. Nullable is
what lets a writer say the source named no type.

It stays `open` (R101 §3.1) and reserves nothing. The values a packet writes are drawn from three
vocabularies — an NWB neurodata type, two NWB `Units` column names, two labels invented here — so
no authority covers the column either (R101 §3.6).

### 3.5 The run that made it

`core.array_assets` and `analysis.array_assets` gain **`processing_run_id`**, `int32` nullable,
referencing `core.processing_runs`. An array a run produced **MUST** name it; an acquired array
declares none, which is the same reading R23 §2 gives a stream.

A column rather than the manifest's field, which restates nothing it can reach: R9 §4 records an
output at resource granularity so that provenance is not per row, and the consequence is that
the link is invisible to SQL. R41 §2.1 keys currency on the producing run and R82 §2 makes an
undeclared one an error, so a rule must be able to join an array to its run, and a manifest entry
is what a rule cannot read. The manifest's field stays as R9 §4 defined it, for resources that
are not rows of a table.

## 4. What this does not change

- **No table or reference is removed, and no Tier 2 rule.** One column is renamed and changes
  presence, one changes presence, one is added to each array table with its reference.
- **`band` stays open.** Three values are reserved where four were, and a validator still **MUST
  NOT** reject an unrecognised one.
- **The device still answers which signal.** R65 §2.1's `device_id` identifies a respiration
  trace, and §3.2 makes a null `band` say so rather than leaving a value to be invented.
- **No manifest field changes.** `writer.py:811` writes `dense_array_asset` into a manifest entry
  correctly, and the manifest's own `processing_run_id` keeps R9 §4's meaning.

## 5. Consequence

330 columns become **332** and 97 references become **99**. `band` and `semantic_type` go from
`required` to `nullable` on two and three tables, so Tier 1's not-null checks go from 154 to
**149**; the reserved set on `band` goes from four values to three, with `raw` renamed `wideband`.
`02` names neither column, so nothing in the frozen documents changes.

Both packets keep `band` of `lfp` on 22 arrays and declare it **null** on the three that carry
`dense_array_asset`, whose `semantic_type` of `waveform_mean` and `waveform_sd` is unchanged;
those three name the sorting run that produced them, which the packets already record.
`waveforms.py:300` stops setting the field. Migration is regeneration, as R53 §5 made it for
identifiers: no packet carries `raw`, and both are rebuilt, which R87 §2.1, R88 §2, R91 §5, R95,
R96, R97, R98, R99 and R101 already require.

## 6. Open

- **Whether the band should be recorded as a filter.** §2.4 measures that no source on hand
  states one, so `band` stays a name for a filter the packet does not carry. Open Ephys writes the
  split in `settings.xml`, which the NWB adapter reads for one column already (R67 §2.3), so the
  fact is reachable and unclaimed. Two corners in hertz would make two rigs' splits comparable
  where two names are not.
- **Whether three bands are enough.** `wideband`, `ap` and `lfp` describe a Neuropixels 1.0
  split, and a 2.0 probe emits wideband only. No packet on hand writes either of the first two, so
  the set is still R8 §4's examples rather than a survey.
- **Whether `semantic_type` earns its place.** Nothing reads it, its values come from three
  vocabularies, and §3.4 makes it nullable rather than striking it — because it is the only record
  of what a source called the array, which R62 struck a file for lacking. Whether that is worth a
  column is a question a second importer would answer.

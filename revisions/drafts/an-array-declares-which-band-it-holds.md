# An Array Declares Which Band It Holds

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R8 §4 (renames `raw`, strikes `waveform`, and narrows what the column is for), the declarations of `kind` and `semantic_type` on both array tables |
| **Depends on** | `a-column-declares-what-its-values-mean` (open draft: records R8 §4's reserved set and rewrites both descriptions), R8 §4 (the four reserved kinds), R23 §1.1 (derivedness belongs in provenance, not a vocabulary), R50 §2 (a column is renamed where its name says less than its declaration), R65 §1 (an array names the device that made it) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.array_assets` carries two required, open, string columns describing what an array holds:
`semantic_type` and `kind`. Nothing says which answers what, and their descriptions do not —
`semantic_type` reads "Semantic type, e.g. ElectricalSeries." and `kind` reads "`raw`, `ap`,
`lfp`, `waveform`, etc.", the construction R8 §4 was written to remove.

This part gives each column its question. The column called `kind` states which **band** of a
sampled signal the array holds, so it is renamed `band`, becomes nullable, and keeps three of its
four reserved values under one of the three renamed. `semantic_type` names the quantity, which
every asset has.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25),
which hold 25 array assets between them.

## 2. Background

Informative.

### 2.1 Both columns describe the array and neither says which does what

Across both packets the two columns stand in two different relationships:

| `semantic_type` | `kind` | arrays | relationship |
|---|---|---|---|
| `ElectricalSeries` | `lfp` | 22 | complementary: what kind of series, and which band |
| `waveform_mean`, `waveform_sd` | `dense_array_asset` | 3 | neither — see §2.3 |

The first is the pair working. The second is what happens where nothing states the division, and
a reader cannot tell from the registry which of the two was supposed to hold the answer.

One asymmetry does say something. `semantic_type` is declared on `core.array_assets`,
`analysis.array_assets` **and** `core.media_assets`; `kind` is declared on the two array tables
only. A behaviour video has a quantity and no band, which is the distinction the tables already
draw and no prose states.

### 2.2 The reserved four name three different things

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

That is R11 §4's failure in another column: its six mixed the instrument's vocabulary with the
experiment's, which is why no single test admitted them. Here three things are mixed rather than
two, and R23 §1.1 has already ruled on the third. It rejected an acquired-versus-derived axis for
`core` outright — *"Acquired-ness is not a property of a fact but of how one came to know it, and
it belongs in provenance"* — and gave `core.event_streams` a `processing_run_id` instead of a
categorical value. `core.array_assets` has no run column and a categorical value, which is the
arrangement R23 §1.1 declined.

The duplication the fourth value produces is visible on the three waveform arrays. Their
`semantic_type` is `waveform_mean` or `waveform_sd`, so a `kind` of `waveform` would state a
second time what the first column already states, which R3 §3.0 forbids.

### 2.3 A required column with nothing to hold is filled from elsewhere

The three waveform arrays carry `kind` of `dense_array_asset`. That is not a fifth kind; it is one
of the **manifest's** six resource kinds — `table`, `materialized_table`, `dense_array_asset`,
`media_asset`, `document_asset`, `view` — which `registry/manifest.schema.json` declares and
`writer.py:811` writes into a manifest entry correctly. `waveforms.py:300` writes the same
spelling into the table row.

R8 §4 forbids a value outside the reserved set "for data the reserved set describes", so both
packets breach it today. What the breach shows is not carelessness: the column is **required**,
the adapter had no correct value for a derived array, and the nearest field of the same name
supplied one.

The gap is wider than waveforms. R65 §1 and `01` §3.17 make an array asset hold "**any** sampled
quantity, whatever instrument produced it", naming a respiration sensor, a heart-rate monitor and
a thermistor as core-owned arrays that no clause of the specification mentions. None of them is
split into bands, and each must fill the column today.

## 3. Decision

### 3.1 The column states which part of a signal's spectrum the array holds

`core.array_assets.kind` and `analysis.array_assets.kind` are renamed **`band`**, on R50 §2's
ground: a column is renamed where its name says less than its declaration, and `kind` is a
category noun for a thing that has a name. It also claimed more than the column delivers, which is
what let a manifest resource kind into it.

Three values are reserved:

```text
wideband   the unfiltered signal, spanning the whole band
ap         action-potential band
lfp        local field potential band
```

`raw` is renamed **`wideband`**. R8 §4 defined it as "unfiltered wideband extracellular voltage",
so the band was always what it meant, and `raw` said it by naming a processing stage instead —
which is the mixture §2.2 measures, one level down inside the set. No packet writes `raw`, so the
rename costs nothing.

The vocabulary stays open (R8 §4). A signal split some other way names its own band and is
conforming; the three reserved values are extracellular voltage's because that is the split this
specification has seen, not because the column is for ephys.

### 3.2 An array with no band declares none

`band` is **nullable**. An array that was not split into bands declares none, and a consumer
meeting a null **MUST NOT** infer one — not from `semantic_type`, not from the device, not from
the sample rate, each of which is evidence and none of which is the statement.

Required is what forced §2.3's value. A photometry trace, a respiration trace and a spike-waveform
template are all core-owned arrays with no band, and a column they must fill is a column they will
fill wrongly.

A numeric band was the alternative — `band_low_hz` and `band_high_hz`, which would be
instrument-agnostic and need no vocabulary at all. It fails on what the sources state:
**`sample_rate_hz` is null on all 22 LFP arrays**, so a packet that does not record the sampling
rate will not record the filter corners, and a column nothing can fill is worse than a vocabulary
someone can read.

### 3.3 `waveform` leaves the reserved set

R8 §4's fourth reserved value is **struck**, and a writer **MUST NOT** write it as a `band`. A
waveform template is computed from sorted spikes rather than split from a signal, so it names no
band; `semantic_type` already carries `waveform_mean` and `waveform_sd` on exactly the arrays that
would have used it; and R23 §1.1 places derivedness in provenance rather than in a vocabulary.

The three arrays carrying `dense_array_asset` today declare `band` null and keep the
`semantic_type` they have, which is where a consumer looking for waveform templates was always
going to look.

### 3.4 `semantic_type` names the quantity, and carries no contract

`semantic_type` states **what quantity** the asset holds. It stays required on every asset table,
because every asset holds something, and open on R8 §4's terms.

`01` §3.17 already fixes what an unrecognised value means: "A value this standard does not define
is a label and carries no contract, which is the honest state of affairs for a quantity whose
meaning lives in the device rather than in the format."

Nothing is reserved and no authority is named, because the values in hand come from three
vocabularies at once. The writer emits five: `ElectricalSeries` is an NWB **neurodata type**
(`lfp.py:278`); `waveform_mean` and `waveform_sd` are **column names** of NWB's `Units` table,
which are not types; and `signal` (`nwb.py:821`) and `behavior_video` (`video.py:169`) are this
implementation's own. An authority names where a column's values are drawn from, and these are
drawn from three places, so naming one would be a claim about the other two.

## 4. What this does not change

- **No table, column or reference is added or removed.** One column is renamed and changes
  presence; one loses a reserved value; `semantic_type` gains a description.
- **`band` stays open.** Three values are reserved where four were, and a validator still **MUST
  NOT** reject an unrecognised one.
- **The device still answers which signal.** R65 §2.1's `device_id` identifies a respiration
  trace, and §3.2 makes a null `band` say so rather than leaving a value to be invented.
- **No manifest kind changes.** `writer.py:811` writes `dense_array_asset` into a manifest entry
  correctly, and §2.3's defect is one table row copying it.

## 5. Consequence

`kind` becomes `band` on `core.array_assets` and `analysis.array_assets`, going from `required` to
`nullable`, so Tier 1's not-null checks go from 154 to **152**. Its reserved set goes from four
values to **three**, with `raw` renamed `wideband`. No table, column, reference or Tier 2 rule
changes, and `02` names neither column, so nothing in the frozen documents does either.

Both packets keep `band` of `lfp` on 22 arrays and declare it **null** on the three that carry
`dense_array_asset`, whose `semantic_type` of `waveform_mean` and `waveform_sd` is unchanged.
`waveforms.py:300` stops setting the field. Migration is regeneration, as R53 §5 made it for
identifiers: no packet carries `raw`, and the rename reaches the two packets through the rebuild
that R87 §2.1, R88 §2, R91 §5, R95, R96, R97, R98 and R99 already require.

## 6. Open

- **Whether an array should name the run that produced it.** R23 §1.1 answered acquired-versus-
  derived for a stream with a `processing_run_id`, and `core.array_assets` has no such column, so
  §3.3 strikes a derived value without putting the fact anywhere. Nothing asks today — the three
  waveform arrays are produced by a sorting run the packet already records — but a derived array
  from an R17 extension would have nowhere to point.
- **Whether three bands are enough.** `wideband`, `ap` and `lfp` describe a Neuropixels 1.0 split,
  and a 2.0 probe emits wideband only. No packet on hand writes either of the first two, so the
  set is still R8 §4's examples rather than a survey — narrower now, and unmeasured either way.
- **Whether `semantic_type` should be one vocabulary.** §3.4 records that it holds three: an NWB
  neurodata type, two NWB `Units` column names, and two labels this implementation invented. NWB
  itself expresses the band by wrapping — `LFP` is a container of `ElectricalSeries`, not a series
  type — so a packet importing from NWB has the same fact in a type name and in `band`, and
  nothing says which the writer should keep. Settling that needs a survey of what an NWB actually
  offers per array, which `inventory/` is the place for and no revision has done.

# An Array's Kind Is Its Band

| | |
|---|---|
| **Status** | Draft |
| **Amends** | R8 §4 (strikes `waveform` from the reserved set and narrows `kind` to a band), the declarations of `kind` and `semantic_type` on both array tables |
| **Depends on** | `a-column-declares-what-its-values-mean` (open draft: which records R8 §4's reserved set and rewrites both descriptions), R8 §4 (the four reserved kinds), R65 §1 (an array names the device that made it), R3 §3.0 (a table does not restate what something else declares) |
| **Profile** | all |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

`core.array_assets` carries two required, open, string columns describing what an array holds:
`semantic_type` and `kind`. Nothing says which answers what, and their descriptions do not —
`semantic_type` reads "Semantic type, e.g. ElectricalSeries." and `kind` reads "`raw`, `ap`,
`lfp`, `waveform`, etc.", the construction R8 §4 was written to remove.

This part gives each column its question. `kind` is the **band** a sampled signal was filtered
into, which not every array has, so the column becomes nullable and loses one of its four reserved
values. `semantic_type` names the quantity, which every asset has.

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

The first is the column pair working. The second is what happens where nothing states the
division, and a reader cannot tell from the registry which of the two was supposed to hold the
answer.

One asymmetry does say something. `semantic_type` is declared on `core.array_assets`,
`analysis.array_assets` **and** `core.media_assets`; `kind` is declared on the two array tables
only. A behaviour video has a quantity and no band, which is the distinction the tables already
draw and no prose states.

### 2.2 The reserved four are three bands and a product

R8 §4 reserved four values with declared meanings:

```text
raw        unfiltered wideband extracellular voltage
ap         action-potential band
lfp        local field potential band
waveform   spike waveform snippets
```

Three name what a filter left in a signal. The fourth names a thing computed from spikes after
sorting, which no acquisition system emits and no filter produces. That is R11 §4's failure in
another column — its six mixed the instrument's vocabulary with the experiment's, which is why no
single test admitted them — and here the mixture is smaller and the same shape.

The duplication it produces is visible on the three waveform arrays. Their `semantic_type` is
`waveform_mean` or `waveform_sd`, so `kind` of `waveform` would state a second time what the
first column already states, which R3 §3.0 forbids.

### 2.3 A required column with nothing to hold is filled from elsewhere

The three waveform arrays carry `kind` of `dense_array_asset`. That is not a fifth kind; it is one
of the **manifest's** six resource kinds — `table`, `materialized_table`, `dense_array_asset`,
`media_asset`, `document_asset`, `view` — which `registry/manifest.schema.json` declares and
`writer.py:811` writes into a manifest entry correctly. `waveforms.py:300` writes the same
spelling into the table row.

R8 §4 forbids a value outside the reserved set "for data the reserved set describes", so both
packets breach it today. What the breach shows is not carelessness: `kind` is **required**, the
adapter had no correct value for a derived array, and the nearest field with the same name
supplied one.

The gap is wider than waveforms. R65 §1 and `01` §3.17 make an array asset hold "**any** sampled
quantity, whatever instrument produced it", naming a respiration sensor, a heart-rate monitor and
a thermistor as core-owned arrays that no clause of the specification mentions. None of them is
filtered into a band, and each must put something in `kind` today.

## 3. Decision

### 3.1 The band is a property of acquisition, and only a filtered signal has one

`core.array_assets.kind` and `analysis.array_assets.kind` state which **band** of a sampled signal
the array holds. A band is what acquisition and filtering left in the signal, which is why a
consumer comparing two packets learns something from the value alone: `kind = 'lfp'` selects
comparable arrays from packets built by different labs.

Three values are reserved, each carrying the meaning R8 §4 declares for it:

```text
raw        unfiltered wideband extracellular voltage
ap         action-potential band
lfp        local field potential band
```

The vocabulary stays open (R8 §4), so a rig whose acquisition splits a signal differently names
its own band and is conforming.

### 3.2 An array with no band declares none

`kind` becomes **nullable** on both array tables. An array that was not filtered into a band
declares none, and a consumer meeting a null `kind` **MUST NOT** infer one — not from
`semantic_type`, not from the device, and not from the sample rate, each of which is evidence and
none of which is the statement.

Required is what forced §2.3's value. A photometry trace, a respiration trace and a spike-waveform
template are all core-owned arrays with no band, and a column they must fill is a column they will
fill wrongly.

### 3.3 `waveform` leaves the reserved set

R8 §4's fourth reserved value is **struck**. A waveform template is computed from sorted spikes
rather than filtered from a signal, so it is not a band, and `semantic_type` already carries
`waveform_mean` and `waveform_sd` on exactly the arrays that would have used it.

A writer **MUST NOT** write `waveform` as a `kind`. The three arrays that carry
`dense_array_asset` today declare `kind` null and keep the `semantic_type` they already have,
which is where a consumer looking for waveform templates was always going to look.

### 3.4 `semantic_type` names the quantity, and carries no contract

`semantic_type` states **what quantity** the asset holds. It is required on every asset table,
because every asset holds something, and it is open on R8 §4's terms.

`01` §3.17 already fixes what an unrecognised value means: "A value this standard does not define
is a label and carries no contract, which is the honest state of affairs for a quantity whose
meaning lives in the device rather than in the format." This part adds no reserved set, because
the values a packet writes — `ElectricalSeries`, `waveform_mean`, `waveform_sd` — are NWB's
vocabulary and this specification defines none of them, which is §3.4 of
`a-column-declares-what-its-values-mean`'s test for a reservation failing.

## 4. What this does not change

- **No table, column or reference is added or removed.** `kind` changes presence and loses a
  reserved value; `semantic_type` gains a description and nothing else.
- **`kind` stays open.** Three values are reserved where four were; a rig naming its own band is
  conforming, and a validator still **MUST NOT** reject an unrecognised one.
- **The device still answers which signal.** R65 §2.1's `device_id` is what identifies a
  respiration trace, and §3.2 makes a null `kind` say so rather than leaving a value to be
  invented.
- **No manifest kind changes.** `writer.py:811` writes `dense_array_asset` into a manifest entry
  correctly, and §2.3's defect is one table row copying it.

## 5. Consequence

`02` names neither column, so nothing in the frozen documents changes: what this amends is R8 §4
and the registry. The reserved set on `kind` goes from four values to **three**, on both array
tables. `kind` goes
from `required` to `nullable`, so Tier 1's not-null checks go from 154 to **152**. No table,
column, reference or Tier 2 rule changes.

Both packets keep `kind = 'lfp'` on 22 arrays and declare it **null** on the three that carry
`dense_array_asset`, whose `semantic_type` of `waveform_mean` and `waveform_sd` is unchanged.
`waveforms.py:300` stops setting the field. Both packets are rebuilt, which R87 §2.1, R88 §2, R91
§5, R95, R96, R97, R98 and R99 already require.

## 6. Open

- **Whether three bands are enough.** `raw`, `ap` and `lfp` describe a Neuropixels 1.0 split, and
  a 2.0 probe emits wideband only. No packet on hand exercises `raw` or `ap`, so the set is still
  R8 §4's examples rather than a survey — narrower now, and unmeasured either way.
- **Whether `semantic_type` should reserve NWB's names.** `ElectricalSeries` is NWB's, and both
  packets write it. Reserving it would make this specification declare a meaning it takes from
  another standard, which is what an `authority` records instead — and the vocabulary draft's
  §3.6 permits one where a nomenclature covers the column, which NWB's neurodata types do not,
  covering only the arrays that came from an NWB.

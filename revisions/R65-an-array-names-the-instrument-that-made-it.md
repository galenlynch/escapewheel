# R65 — An Array Names The Instrument That Made It

| | |
|---|---|
| **Status** | **Accepted** 2026-09-04 |
| **Amends** | `01` §3.17 (what an array asset holds), `02` (`core.array_assets`), R19 §2 (what the array tables carry) |
| **Depends on** | R46 (references are declared), R53 (identifiers are assigned or carried) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`core.array_assets` is the generic dense-array registry: any array, on a declared clock, with
declared axes, a unit, and a conversion. It holds an LFP series, a waveform template and a sniff
trace alike.

It does not say what made any of them. Its only references are to `core.sessions` and
`core.clocks`.

### 1.1 What that costs, measured on one packet

`ecephys_786867` carries twelve array assets:

| asset | `semantic_type` | unit | what identifies the instrument |
|---|---|---|---|
| ten LFP series | `ElectricalSeries` | volts | the probe, through `core.array_channels` → `core.electrodes` |
| `waveform_mean` | `waveform_mean` | uV | the sorting run, through the units it indexes |
| `sniff_detector` | `signal` | a.u. | **nothing** |

The first two are reachable only because something *else* in core happens to link them. An
`ElectricalSeries` resolves to a probe through its channels; a waveform template resolves through
the units it is indexed by. Neither route is a statement about the asset, and neither exists for
an array that is not channel-mapped and not per-unit.

`core.probes` has declared `device_id` since `02`. An array asset is the only acquired thing in
core that does not name its instrument.

### 1.2 The gap is a reference, not a mechanism

The absence invites a larger answer than it needs. A discriminator naming an extension resource
that describes the asset (R55 §2.3) would work, and it would be the wrong instrument: a
discriminator earns its place where a row needs typed, queryable, per-row facts that core cannot
declare, which is what `dynamic_foraging.trials` needs and a single sniff trace does not.

Everything a signal is — values over time, a unit, a scale, a clock, and a producing instrument —
is already declared, four parts in `core.array_assets` and the fifth in `core.devices`. Only the
join between them is missing.

### 1.3 The standard should never have to name an instrument

The absence has a second cost, and it is the larger one. With no way to say what made an array,
the only thing distinguishing one acquired signal from another is `semantic_type` — so a rig
fitting a new instrument appears to need a new value in the standard, or an extension, or a
concept in `01`. None of that is true, and none of it should be.

`core.array_assets` is generic **by design**. An acquired signal belongs in it whatever produced
the signal, and *which* signal it is should be answered by the **device**, which is data, rather
than by the **type**, which is vocabulary. A packet names its own arrays; the standard names only
the concepts it defines.

This is the test the change has to pass: a rig fitted with an instrument nobody anticipated —
a respiration sensor, a heart-rate monitor, a thermistor — produces a core-owned array, and
**no clause of this specification mentions any of them.** A packet says what its instruments are;
the standard says how an array points at one.

The alternative — a namespace per instrument, each declaring its own array tables as `analysis`
does — fragments raw acquisition across extensions and buys nothing this column does not.

## 2. Decision

### 2.1 An array asset may name its device

`core.array_assets` and `analysis.array_assets` each gain `device_id`: `int32`, **nullable**, R48
role `identifier`, R53 identity `assigned`, with a declared reference (R46 §2) to
`core.devices.device_id`.

A writer that knows which instrument produced an array **SHOULD** record it. Nullable rather than
required, because a derived array has no instrument and a referenced one may come from a producer
the packet cannot attribute.

### 2.2 The standard does not enumerate instruments

`01` §3.17 is amended to state positively what it previously permitted by silence: an array asset
holds any sampled quantity, whatever instrument produced it, and this standard **MUST NOT**
enumerate instruments. A quantity whose meaning lives in the device is identified by its
`device_id`; a quantity the standard defines as a concept is identified by its `semantic_type`,
and `01` §3.16 is the only such concept today.

`semantic_type` stays open (R8 §4). A value the standard does not define is a label carrying no
contract, which is the honest state of affairs rather than a gap to be filled.

### 2.3 What a consumer may then do

A consumer **MAY** resolve any array asset to the device that produced it, without knowing what
kind of array it is and without the channel or unit tables that happen to serve two of the three
cases today.

A consumer **MUST NOT** infer an instrument from an asset's `semantic_type`, its name, or its
URI. Those are labels; this is a reference.

### 2.4 What stays where it is

Device-specific detail — calibration, what an arbitrary unit corresponds to, mounting, firmware —
belongs on `core.devices.metadata` or in an extension, by `09`'s tiering unchanged. This revision
adds a join and no vocabulary.

A quantity that becomes queryable earns a typed column then, argued from what a producer emits, as
`09` §7 already requires of any promotion.

## 3. What this does not change

- **No new table**, and no table is withdrawn. `core.array_assets` was already the table that
  describes signals.
- **No change to `semantic_type`.** It stays open, and `ElectricalSeries` keeps the contract `01`
  gives it.
- **No packet becomes invalid.** The column is nullable, so every existing packet stays conforming
  and gains the reference on its next rebuild.
- **No change to `core.array_channels`.** Where an array is channel-mapped, the electrode route
  stays and is more specific than the device route; the two answer different questions.

## 4. Open

- **Whether a device should name its session's rig.** `core.devices` is per session, so ten
  sessions on one rig carry ten rows for one instrument. That is the same shape `core.probes` has
  and no consumer has yet asked to deduplicate it.
- **Whether `waveform_mean` should name a device at all.** It is derived from a recording rather
  than acquired, so its `device_id` would be null and its provenance is the sorting run. That
  argues its instrument is the wrong question, not that the column is.

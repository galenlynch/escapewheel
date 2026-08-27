# R14 — Codec Floor and External Arrays

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `03_portable_physical_profile.md`, `04_packet_catalog_manifest.md`, R3 §7.2 |
| **Depends on** | R3 (codec floor, `required_codecs`) |
| **Blocks** | Phase 5 |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R3 §7.2 sets the reader floor at `none`, `gzip`, and `zstd`, permits `blosc` with
`cname=zstd, shuffle=shuffle` and `sharding_indexed` under a `required_codecs` declaration,
and forbids nothing else explicitly.

Discovery finds that the intended acquisition uses a codec outside that set
(`inventory/ecephys_776259_2025-04-09.md` §6). Every compressed stream, including the sync
stream, is WavPack:

```text
Neuropix-PXI-100.46110   <i2  [191_631_595, 384]  codec wavpack
NI-DAQmx-107.PXIe-6341   <i2  [191_652_096, 1]    codec wavpack
```

R3 §7.3 anticipated this without resolving it: "specialized audio-style codecs do far better
but are not portable." A 384-channel probe at 30 kHz for 1.77 h is ~147 GB uncompressed, and
this session has fourteen of them.

The specification therefore faces a choice it has not made: transcode, admit the codec, or
stop copying the arrays.

## 2. Decision

**All three, scoped.** They are not alternatives; each answers a different question.

### 2.1 The reader floor is unchanged

`none`, `gzip`, and `zstd` remain what every conforming reader MUST support. Widening the
floor to accommodate one acquisition system would make the floor mean nothing, and R3 §7.2's
reasoning — that the baseline must not be derived from what particular libraries happen to
support — applies with more force to a codec with one implementation.

### 2.2 Any codec may be used, and MUST be declared

R3 §7.2's `required_codecs` declaration is generalized from an enumerated opt-in list to an
open one. A writer MAY use any Zarr codec; the manifest MUST name it; a reader MUST check
before opening an array and fail naming what it lacks.

```json
{ "required_codecs": ["wavpack"] }
```

This is what the declaration mechanism was for. R3 §7.2 admitted `blosc` and
`sharding_indexed` by name because those were the cases measured; naming codecs individually
does not scale to acquisition systems the specification has not met.

A packet using a non-baseline codec is conforming and **not portable by default**, which the
manifest now states rather than implies.

### 2.3 Arrays may be referenced instead of copied

`03` permits absolute URIs for external assets but treats copying as the norm. For dense
arrays at acquisition scale, copying is often the wrong default: it duplicates hundreds of
gigabytes, and transcoding to a baseline codec discards compression the acquisition already
achieved.

A `core.array_assets` entry MAY reference an array outside the packet. Where it does, the
manifest resource entry MUST set:

| Field | Meaning |
|---|---|
| `external` | `true` |
| `uri` | absolute, resolvable without the packet |

An external array is outside the packet's immutability guarantee (`03`), and its resource
entry's `validation_state` records what was checked at validation time, not what is true now.

```sql
-- core.array_assets.external_declared  (error)
-- An absolute URI is a copy the packet does not own; the manifest must say so.
SELECT array_asset_id, uri FROM core_array_assets
WHERE uri LIKE '%://%'
  AND array_asset_id NOT IN (SELECT array_asset_id FROM manifest_external_arrays)
```

### 2.4 Transcoding is a writer's choice, not a rule

An importer MAY transcode to a baseline codec. Nothing requires it, and for ~147 GB per
probe the cost is real. The trade is recorded here so it is chosen rather than defaulted
into: transcode and the packet is portable but larger and slower to write; declare the codec
and it is smaller but opens in fewer readers; reference externally and it is neither copied
nor portable.

## 3. What this does not do

**No WavPack in the floor.** §2.1.

**No codec vocabulary.** `required_codecs` carries whatever the arrays use. A validator
checks that the manifest's declaration matches the arrays' actual codecs, not that the names
come from a list.

**No policy on which route to take.** §2.4 is deliberately a MAY. Phase 5 will have evidence
this revision does not.

## 4. Consequence

R3 §7.2's sentence naming `blosc` and `sharding_indexed` as the permitted opt-ins is
replaced by §2.2's open declaration. The measured evidence in R3 §7.3 stands as evidence
that those two are safe to use, not as the boundary of what may be used.

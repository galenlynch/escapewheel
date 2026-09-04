# R21 — Per-Resource Zarr Version and a Versioned Codec Floor

| | |
|---|---|
| **Status** | **Accepted** 2026-08-27 |
| **Amends** | R3 §7.1, §7.2, §7.3; R15 §2 |
| **Depends on** | R14 (external resources), R15 (per-resource codecs) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R3 §7.1 is one sentence:

> Arrays MUST be Zarr v3 with a regular chunk grid.

That was written when a packet owned every array in it. R14 §2.3 then made referencing the
expected form for large arrays, and the arrays a lab already has are not v3.

AIND writes NWB-Zarr for approximately all of its NWB output, and `hdmf-zarr` writes **Zarr
v2**. The session inventoried in `inventory/nwb-zarr-776259-2025-04-09.md` carries twelve LFP
arrays of 7,983,750 × 96 int16, blosc/zstd, v2. Under R3 §7.1 a packet cannot reference them
at all — not because anything cannot read them, but because the profile forbids the version
they are already in. The only conforming route is to transcode 18 GB the packet does not own,
which R14 exists to avoid.

The evidence for permitting v2 was already in R3 §7.3, which records `v2 zstd, v2
blosc-zstd-shuffle | reads` from Zarr.jl. Only the rule forbade it.

## 2. The codec floor is not version-independent

What R3 §7.3 did not measure is v2 with the baseline codecs. Measured now
(`conformance/zarr-probe/`, zarr-python 3.3.0, Zarr.jl 0.10.2, Julia 1.12.7):

| Configuration | zarr-python 3.3.0 | Zarr.jl 0.10.2 |
|---|---|---|
| v3 raw, gzip, zstd | reads | reads |
| v3 blosc-zstd-shuffle, `sharding_indexed` | reads | reads |
| v2 zstd, v2 blosc-zstd-shuffle | reads | reads |
| **v2 gzip** | reads | **`KeyError: "gzip"`** |
| v2 `vlen-bytes` | reads | **`KeyError: "vlen-bytes"`** |

`gzip` is in R3 §7.2's MUST-support baseline. Zarr.jl reads it in v3 and not in v2, because
the two versions name codecs differently and the library registers only the v3 spelling.

So a codec's readability is a property of the **pair** `(zarr_format, codec)`, not of the
codec. R3 §7.2's floor is a v3 floor and does not transfer. Admitting v2 while leaving the
floor unqualified would have silently broken the guarantee the floor exists to give.

## 3. Rule

### 3.1 Packet-owned arrays

An array the packet owns MUST be Zarr v3. R3 §7.1 is unchanged for these, and a writer has no
reason to emit anything else.

### 3.2 External arrays

A resource with `external: true` MAY be Zarr v2. It declares this in `physical_profile`,
whose vocabulary already carried the version:

```json
{
  "resource_id": "array.probe46110_lfp",
  "kind": "dense_array_asset",
  "physical_profile": "zarr_v2",
  "uri": "s3://…/ecephys_776259…nwb/processing/ecephys/LFP/ElectricalSeries46110-LFP/data",
  "external": true,
  "codecs": ["blosc"]
}
```

`physical_profile` gains `zarr_v2` beside the existing `zarr_v3`. **No new field is added.**
A separate `zarr_format` integer was considered and rejected: the version would then be
declared in two places that could contradict each other, which is exactly the duplication
R3 §3.0 forbids. A resource already says it is `zarr_v3`; saying `zarr_v2` instead is the
whole change.

`physical_profile: "zarr_v2"` MUST NOT appear on a resource that is not `external: true`.

A reader MUST check a resource's `physical_profile` together with its `codecs` before opening
it, and MUST fail for that resource naming whichever it lacks — the per-resource degradation
R15 §2 established, now over the pair.

### 3.3 The floor, per version

| `physical_profile` | Readers MUST support | Writers MAY also use |
|---|---|---|
| `zarr_v3` | `none`, `gzip`, `zstd` | `blosc` (cname=zstd, shuffle=shuffle), `sharding_indexed` |
| `zarr_v2` | `none`, `zstd`, `blosc` (cname=zstd) | — |

`gzip` is deliberately absent from the `zarr_v2` row: it is not readable in Julia, and a MUST
that one of the two target languages cannot honour is not a floor. A v2 resource compressed
with gzip is therefore outside the baseline and MUST be declared like any other non-baseline
codec, so a reader that lacks it declines that resource and no other.

This amends R3 §7.2's single unqualified baseline.

## 4. `required_codecs` and the summary

R15 §3 makes `required_codecs` the union over resources, for a whole-packet capability
answer. It stays a codec union and gains no version dimension: a reader that wants the
precise answer reads the resources, and a packet-level summary that tried to express
`(version, codec)` pairs would be answering a question no reader asks.

## 5. hdmf-zarr's consolidated metadata is unreadable, and that is not a v2 problem

zarr-python 3.3.0 cannot open an `hdmf-zarr` file through its consolidated metadata:

```text
TypeError: Invalid type: 0. Expected a string.     zarr/core/dtype/npy/bytes.py:1204
```

`.zmetadata` carries `fill_value: 0` on vlen-string arrays, which the stricter v2 parser
rejects. `zarr.open(..., use_consolidated=False)` then works, and every numeric array reads
correctly. Plain v2 arrays written by zarr-python itself open through the consolidated path
without complaint, so the fault is in the writer, not the version.

This specification takes no position on it. It is recorded because any importer reading AIND
NWB-Zarr needs the workaround, and because the failure looks like a v2 incompatibility and is
not one.

## 6. What this does not permit

- **Not a v2 write path.** Nothing in the profile emits v2. §3.1 stands.
- **Not v2 for tables.** Tables are Parquet; this concerns `dense_array_asset` only.
- **Not `vlen-bytes` or any object dtype.** R3 §2.1's primitive floor is unchanged, and the
  measurement above shows Zarr.jl cannot read it in any case. A v2 array a packet references
  MUST have a primitive dtype.
- **Not group-level referencing.** A resource names one array. Neither reader opens an
  `hdmf-zarr` file as a group (§5, and Zarr.jl fails on `vlen-bytes` in the hierarchy), so a
  packet that referenced the NWB root would be declaring something no conforming reader can
  open.

## 7. Consequence

Referencing AIND's LFP becomes possible without transcoding, which was R14's whole point, and
the one array kind that matters — a primitive-dtype, blosc/zstd, v2 `data` array — reads in
both target languages today. The arrays that do not read in Julia are the ones a packet has
no reason to reference: `timestamps`, which R20 §2 replaces with three integers, and
vlen-string columns, which become Parquet.

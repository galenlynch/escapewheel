# R15 — Per-Resource Codec Declaration

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | R3 §7.2, `04_packet_catalog_manifest.md` |
| **Depends on** | R14 (external resources) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R3 §7.2 declares codecs once per packet and makes the capability check all-or-nothing:

> Readers MUST check `required_codecs` before opening any array, and MUST fail with a
> message naming the unsupported codec rather than attempting the read.

That was written when every array in a packet was assumed to be owned by it and written by
the same writer. R14 §2.3 makes referencing external resources the expected form for large
arrays, and the consequence is immediate: a packet may carry arrays with different codecs,
written by different producers, some of which a given reader will never open.

The AIND case is the ordinary one, not a corner. Fourteen probe recordings are referenced
externally in WavPack (`inventory/ecephys_776259_2025-04-09.md` §6); any array the packet
derives and owns is written to the baseline. Under R3 §7.2 a reader without WavPack must
refuse the packet entirely — including the baseline arrays it could read, and including the
external arrays it was not going to open.

A capability contract that forces a reader to decline work it could do is worse than no
contract.

## 2. Rule

A manifest resource entry of kind `dense_array_asset` MUST declare the Zarr codecs its array
uses, in a `codecs` array. The mandatory `bytes` codec is excluded, as in R3 §7.2.

```json
{
  "resource_id": "array.probe0_ap",
  "kind": "dense_array_asset",
  "uri": "s3://aind-open-data/…/experiment1_Record Node 109#Neuropix-PXI-100.46110.zarr",
  "external": true,
  "codecs": ["wavpack"]
}
```

A reader MUST check a resource's own `codecs` before opening that resource, and MUST fail
for that resource naming the codec it lacks. A reader MUST NOT refuse a packet, or any other
resource in it, on account of a codec used only by resources it does not open.

## 3. `required_codecs` becomes a summary

The top-level `required_codecs` is retained and MUST equal the union of every resource's
`codecs`. Its purpose changes: it answers "can this reader use the whole packet", which is
worth knowing up front, rather than gating every read.

```sql
-- manifest.required_codecs_is_the_union  (error)
SELECT codec FROM manifest_resource_codecs
WHERE codec NOT IN (SELECT codec FROM manifest_required_codecs)
UNION ALL
SELECT codec FROM manifest_required_codecs
WHERE codec NOT IN (SELECT codec FROM manifest_resource_codecs)
```

A reader SHOULD report which resources it cannot open rather than only that it cannot open
everything.

## 4. What does not change

The baseline stays `none`, `gzip`, `zstd` (R3 §7.2). Writers SHOULD still use it for arrays
they own; a packet whose owned arrays are baseline stays fully readable regardless of what
it references.

R14 §2.2's open declaration stands — any codec may be used provided it is declared. This
revision changes only where the declaration lives and how coarsely a reader may act on it.

## 5. Consequence

`04`'s resource entry gains `codecs`, required for `dense_array_asset`. The manifest JSON
Schema gains it with that conditional.

`Packet.check_codecs()` in the reference reader is packet-level and implements exactly the
behaviour §2 forbids. It becomes a per-resource check, with a packet-level convenience that
reports which resources are unopenable rather than raising on the first missing codec.

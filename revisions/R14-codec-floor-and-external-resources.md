# R14 — Codec Floor and External Resources

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `03_portable_physical_profile.md`, `04_packet_catalog_manifest.md`, `05_validation_and_import.md`, R3 §7.2 |
| **Depends on** | R3 (codec floor, `required_codecs`) |
| **Blocks** | Phase 5 |
| **Profile** | `escapewheel-portable-v0.1` |

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

### 2.3 External resources, and the declaration Part 03 requires but never defined

`00:56` already admits the form: a packet may be "a local directory, an object-store prefix,
or **a release manifest that points to distributed assets**." Part 03 permits absolute URIs and
then requires that "external assets MUST be explicitly declared in the manifest" — but no
field for that declaration exists anywhere in Part 04. The mechanism has been mandatory and
absent since v0.1.

This revision defines it, and states the expectation Part 03 leaves ambiguous.

**Referencing is the expected form for large resources.** Part 03's preference for relative
URIs is scoped to "portable local packets" and is not a general default. For dense arrays,
media, and large tables, copying is usually wrong: it duplicates the bulk of a dataset for
no gain, and for arrays it additionally forces either a transcode that discards the
acquisition's compression (§2.4) or a codec declaration (§2.2).

This applies to any resource kind — `table`, `dense_array_asset`, `media_asset`,
`document_asset` — not to arrays alone.

A manifest resource entry that references data the packet does not own MUST set:

| Field | Type | Required | Meaning |
|---|---|:---:|---|
| `external` | bool | yes | `true`; its absence means the packet owns the bytes |
| `uri` | string | yes | absolute, resolvable without the packet |
| `sha256` | string | no | what was verified, if anything was |
| `size_bytes` | int64 | no | as verified |
| `verified_at` | timestamp | no | when `sha256` or `size_bytes` last held |

A resource whose `uri` is absolute MUST declare `external: true`. The converse does not
hold: a packet may declare a resource external and still resolve it relatively, which is how
a packet published beside its data records that it does not own it.

### 2.3.1 Immutability does not extend to external resources

Part 03 says a portable packet SHOULD be treated as immutable after validation, and that a
committed packet MUST have a validation report corresponding to its current bytes. That
guarantee covers **bytes the packet owns**. An external resource may change or vanish
without the packet changing at all.

`sha256` and `verified_at` are what a consumer has instead: a record of what was true when
validation ran, not a promise about now. A packet asserting integrity it cannot enforce
would be worse than one that says plainly where its guarantee stops.

### 2.3.2 Validation does not reach the network by default

Part 05's physical validators require that declared URIs resolve. Applied to external resources
that would make validity depend on network reachability, credentials, and whether the
validator is running offline — none of which is a property of the packet.

Structural validation MUST NOT require an external resource to be reachable. A validator
MUST offer a separate, explicitly requested mode that resolves external URIs and checks
`sha256` and `size_bytes` where declared; findings from that mode are reported against the
resource entry rather than the packet's structure.

**The cost is real for tables.** An unreachable external `table` resource cannot have its
Tier 1 or Tier 2 rules run at all, so a packet that externalizes core tables validates less
of itself than one that owns them. Arrays lose only rank and dtype checks; media and
documents lose only existence. Externalizing a core table is therefore a heavier trade than
externalizing an array, and a writer SHOULD prefer to own core tables where their size
permits — which, for everything except `core.spike_events` and `core.media_frames`, it
generally does.

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

**No resolution of external URIs at write time.** A writer records what it verified; it is
not required to have verified anything. A packet may reference an asset it has never read.

## 4. Consequence

R3 §7.2's sentence naming `blosc` and `sharding_indexed` as the permitted opt-ins is
replaced by §2.2's open declaration. The measured evidence in R3 §7.3 stands as evidence
that those two are safe to use, not as the boundary of what may be used.

Part 04's resource entry gains `external`, `sha256`, `size_bytes`, and `verified_at`. The
manifest JSON Schema gains them with `external` required wherever `uri` is absolute.

Part 05's physical validators are amended per §2.3.2: "declared URIs resolve" applies to
packet-owned resources, and external resolution is a separate mode.

This makes `00:56`'s third packet form — "a release manifest that points to distributed
assets" — actually expressible. It has been named in the architecture since v0.1 with no
mechanism behind it.

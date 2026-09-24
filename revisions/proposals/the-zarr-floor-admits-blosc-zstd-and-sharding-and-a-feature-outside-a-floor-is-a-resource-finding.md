# The Zarr floor admits Blosc-Zstd and sharding, and a feature outside a floor is a resource finding

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `cc6209e572d48f3b1e86a4895b64264fd7dc6d34` |
| **Decision domain** | specification |
| **Affects** | Part 03 §6.4; the physical-profile descriptor's `zarr.v3.reader_floor` and its schema; Part 05 §5.3; Part 10 §5; the reader's array codec reporting and `UnsupportedCodecError`; the validator's physical checks; the writer's residual codec-name helpers |

## 1. Problem

The portable profile states a reader floor for each interface: the physical features every
conforming reader supports. For Zarr v3,
[Part 03 §6.4](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-array-codecs)
fixes it at three ordered codec sequences: `bytes`; `bytes` then `gzip`; and `bytes` then `zstd`.
The floor is a reader minimum only, so a writer may use any valid codec, and a valid feature outside
it is outside the portability guarantee without being an error.

The reference writer emits no packet-owned array inside that floor. Its default pipeline is `bytes`
then Blosc, and its sharded arrays wrap that pipeline in `sharding_indexed`. The guarantee therefore
covers none of the arrays the reference build produces, and a portability finding raised on every
array would carry no information.

[R129 §3.8](../accepted/R129-a-portable-profile-declares-its-interfaces-and-reader-floor.md#38-physical-assessment-uses-available-resource-metadata)
obliges a validator to compare each available resource with the descriptor's floor and to
distinguish upstream invalidity from a valid feature outside the floor. It left finding IDs,
severity, and summaries to a later revision, and no implementation performs the comparison.

The reader cannot report missing support for one resource, which
[Part 03 §6.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-array-version)
requires. Its codec listing also discards the order and nesting a floor comparison needs.

The floor's current shape cannot admit either feature the writer uses. A floor entry is a list of
bare names, so it cannot state Blosc's `cname` or the pipeline nested inside a shard.

## 2. Evidence

All observations were made at the recorded baseline on 2026-09-24.

### 2.1 Every packet-owned array the writer emits is outside the v3 floor

Each row below was produced by calling the writer's `write_zarr` with a `StagedArray` shaped like
the named path, under the writer environment's zarr-python 3.3.0, and reading the resulting
`zarr.json`. Configuration members that no option below discriminates on are omitted.

| writer path | stored v3 pipeline | in the current floor | in the preferred floor |
|---|---|---|---|
| `StagedArray` default, `codecs=("blosc",)`, no shard | `bytes`, `blosc` (`cname: zstd`, `shuffle: shuffle`) | no | yes |
| waveform adapter, `shard=shard_for(...)` | `sharding_indexed` holding `bytes`, `blosc` (`cname: zstd`); index `bytes`, `crc32c`; `index_location: end` | no | yes |
| NWB adapter signals, `codecs=("numcodecs.delta", "blosc")` | `numcodecs.delta`, `bytes`, `blosc` (`cname: zstd`, `shuffle: bitshuffle`) | no | no |

The writer's only other array route stages an adapter-written array unchanged. The LFP adapter's
arrays are external Zarr v2, whose metadata the source defines.

### 2.2 Five implementations read Blosc-Zstd and sharding

The repository's Zarr probe, `conformance/zarr-probe/`, writes arrays with zarr-python and reads
them back with Zarr.jl, checking the int64 element sum.
[R3 §7.3](../accepted/R3-cross-language-physical-floor.md#73-evidence) recorded that both libraries
read Blosc-Zstd and sharding.
[R3 §8](../accepted/R3-cross-language-physical-floor.md#8-rejected-alternatives) then declined to
raise the floor, because two implementations were too few. Later,
[R14 §2.1](../accepted/R14-codec-floor-and-external-resources.md#21-the-reader-floor-is-unchanged)
kept that floor unchanged.

The probe's `write.py` and `read.jl` were rerun unchanged. The same element-sum check was then
applied with three further readers:

- TensorStore;
- zarrs, through zarrs-python with `codec_pipeline.strict` set, so that no read falls back to
  Python; and
- zarrita.

Further arrays covered Blosc shuffle modes, each floor pipeline inside a shard, both index
pipelines, both index locations, and the three writer paths of §2.1. These added scripts ran in a
scratch directory and are not committed.

Versions: zarr-python 3.4.0 with numcodecs 0.17.0; Zarr.jl 0.10.2 on Julia 1.12.7; TensorStore
0.1.85; zarrs-python 0.2.3; zarrita 0.7.5 on Node 22.22.2.

| stored v3 pipeline | zarr-python | Zarr.jl | TensorStore | zarrs | zarrita |
|---|---|---|---|---|---|
| each current floor sequence | reads | reads | reads | reads | reads |
| `bytes`, `blosc` (`zstd`), each of `noshuffle`, `shuffle`, `bitshuffle` | reads | reads | reads | reads | reads |
| `sharding_indexed` around each current floor sequence and around `bytes`, `blosc` (`zstd`); index `bytes`, `crc32c`; at `end` | reads | reads | reads | reads | reads |
| `sharding_indexed` with index `bytes` alone, at `end` | reads | reads | reads | reads | reads |
| `sharding_indexed` with index at `start` | reads | reads | reads | reads | fails |
| `bytes`, `blosc` (`lz4`) | reads | reads | reads | reads | reads |
| the writer's `numcodecs.delta` pipeline | reads | fails | fails | fails | reads |

Zarr v2 zstd and Blosc-Zstd, both already in the v2 floor, also read in all five. zarrita's failure
is `RangeError [ERR_OUT_OF_RANGE]` when reading the index at `start`. Zarr.jl reports that it "does
not support the delta codec", TensorStore that `"numcodecs.delta" is not registered`, and zarrs
raises `UnsupportedMetadataError`.

The five readers span Python, Julia, C++, Rust and JavaScript. It is an inference, not checked here,
that all five decode Blosc through the c-blosc library or a build of it. If so, R3 §8's cost stands:
a new implementation must bind that library or reimplement it to conform.

### 2.3 No implementation compares a resource with a floor

- The validator's `_check_one_array` reads the stored codec names only to reject `transpose`. No
  validator code reads either floor from the descriptor. The reader's profile module offers
  `parquet_floor()` and no Zarr floor accessor.
- The writer checks each packet-owned table's footer against the Parquet floor before committing.
  The validator reads Parquet footers only for statistics.
- An unresolved external resource yields one `info` finding, `external.physical_unassessed`, listing
  every such resource and attributed to the packet.
- PyArrow 25.0.1's footer API reports each column chunk's compression and encodings, but not its
  data-page types.

### 2.4 The reader cannot name missing support

- `UnsupportedCodecError` is exported and never raised.
- `ArrayResource.open` catches only `ImportError`. For a pipeline naming an unregistered codec,
  zarr-python 3.3.0 raises `zarr.errors.UnknownCodecError: Unknown codec: 'example.unknown'` when
  the array opens, so the caller receives a library exception that does not name the resource.
- `ArrayResource.codecs` and `resources._codec_names` drop `bytes` and flatten a shard's inner
  pipeline, but omit its index pipeline. For v2 they list the compressor before the filters, the
  reverse of the encoding order that the v3 listing follows. The property's docstring calls it
  comparable with "what the manifest claims", although
  [Part 04 §6](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-codecs) no longer
  lets a manifest carry codecs.
- The writer's `declared_codecs` and `written_codecs` still derive manifest-style name lists.
  Only tests call them. `ExternalArray` still carries `physical_profile` and `codecs`; the LFP
  adapter fills them, and the delivery serializer drops them.

## 3. Desired outcome and constraints

A successful resolution:

- makes the v3 floor cover the reference writer's default and sharded output, on the evidence of
  §2.2;
- states each floor entry so it compares exactly with Zarr metadata, including configuration
  discriminants and a shard's nested pipelines;
- has a validator report each available resource's floor membership as one standard finding per
  resource, which composes through the verdict rules of
  [Part 05 §9.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-verdict-composition)
  with no portability verdict of its own;
- reports a packet-owned table outside the Parquet writer floor as a warning.
  [Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes)
  bars reporting a packet non-conforming for an obligation that binds only a writer; and
- has a reader fail one selected resource by naming the codec it cannot decode, whatever the floor
  says.

It preserves the Parquet floor's writer ceiling and the Zarr floor's reader-only role, the Zarr
writer's open codec choice, the descriptor's refusal to enumerate optional features, the absence of
packet codec fields, and the rule that structural validation never reaches the network.

## 4. Options and tradeoffs

### 4.1 Floor membership

**Keep the current floor.** This retains R3 §8's reasoning, but every array the reference writer
emits would stay outside the guarantee and draw a finding. A finding present on every array would
not tell a reader anything.

**Admit Blosc with `cname: zstd`, and sharding over floor pipelines (preferred direction).** Both
read in all five implementations of §2.2. That is the same evidence standard R129 applied to the
Parquet floor, with five independent readers where R3 §8 had two. The cost R3 §8 named remains: a
new reader has to decode Blosc and parse shard indexes. With this change:

- a Blosc entry discriminates on `cname` alone. Shuffle is recorded in each Blosc frame, and all
  three modes read in all five implementations.
- a sharded pipeline matches when it consists of exactly one `sharding_indexed` codec whose inner
  pipeline matches an unsharded floor sequence, whose index pipeline is `bytes` or `bytes` then
  `crc32c`, and whose `index_location` is `end`.
- the floor admits no nested shard, and no codec outside a shard. Neither was measured, and an
  outer codec defeats the partial read that sharding exists for.

**Admit Blosc with any `cname`.** `lz4` also read in all five. It is rejected because the floor
already carries Zstd, and no writer needs a second Blosc compressor.

**Also admit `numcodecs.delta`.** Only two of the five read it. Arrays using it stay outside the
floor and draw the finding of §4.3.

### 4.2 Floor representation

**Enumerate every sharded sequence flat.** Four inner sequences and two index pipelines make eight
more entries, so the inner floor would be stated twice.

**Structured codec patterns, with one `sharding` member (preferred direction).** Each floor entry
becomes an ordered list of codec patterns, matched by the rule Part 03 §6.4 already states for v2
patterns: every stated member compares equal, and unmentioned members do not participate. A
`sharding` member states the index pipelines and location once and refers to `codec_sequences` for
the inner pipeline:

```json
"reader_floor": {
  "codec_sequences": [
    [{"name": "bytes"}],
    [{"name": "bytes"}, {"name": "gzip"}],
    [{"name": "bytes"}, {"name": "zstd"}],
    [{"name": "bytes"}, {"name": "blosc", "configuration": {"cname": "zstd"}}]
  ],
  "sharding": {
    "index_codec_sequences": [[{"name": "bytes"}], [{"name": "bytes"}, {"name": "crc32c"}]],
    "index_location": "end"
  }
}
```

The schema closes a pattern's `configuration` to the discriminants Part 03 gives floor semantics,
as R129 §3.5 requires. This changes the descriptor schema's v3 floor shape incompatibly.

### 4.3 Portability reporting

**A portability verdict beside the packet, core and extension verdicts.** Rejected. It would add
an axis that every consumer composes separately, although R129 §3.5 already states that floor
membership does not decide conformance.

**One standard per-resource finding (preferred direction).** The finding would have one check ID,
tentatively `physical.outside_reader_floor`. It would name:

- the resource;
- its interface and variant; and
- the observed features that matched no entry: each outside compression or encoding for Parquet,
  and the full observed pipeline for Zarr.

Its level is `warning` for a packet-owned table, whose writer floor it breaks, and `info` for any
other resource. It is never `error`, so no verdict changes. Part 05 §9.5 attributes the finding to
the registry that declares the resource. A consumer can derive "portable" as the absence of this
finding and of unassessed resources, without a verdict saying so.

Under this direction, a validator:

- reports malformed metadata, or an invalid configuration of a codec it recognizes, as upstream
  invalidity through the existing error findings;
- treats an unrecognized codec name as outside the floor, not invalid, because Zarr v3 admits
  extension codecs and a validator cannot judge one it does not know; and
- assesses packet-owned resources during structural validation, and external ones only in the
  requested resolution mode of
  [Part 04 §5.3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-external-resource-verification).

### 4.4 Reader reporting

**Keep the name tuple and fix it**, by retaining `bytes` and nesting. This still loses the
configuration that the preferred floor discriminates on.

**Expose the stored pipeline, and share one matcher (preferred direction).**

- `ArrayResource` returns the format-owned pipeline unchanged: v3 `codecs`, or v2 `filters` and
  `compressor`.
- The reader's profile module offers one floor matcher. The validator calls it, and so can any
  caller that wants to know floor membership.
- `open` raises `UnsupportedCodecError` naming the resource and the codec when the Zarr library
  cannot build the pipeline.
- The reader never refuses or warns over floor membership alone, because it may support more than
  the floor.

The writer's `declared_codecs`, `written_codecs`, and the `ExternalArray` fields of §2.4 have no
remaining consumer and can be removed.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | unchanged; the change concerns storage only |
| logical prose and registries | unchanged; logical kinds and the kind-to-interface mapping stay as they are |
| physical profiles | affected: Part 03 §6.4 states the new v3 entries, sharded matching, and default-valued members; the descriptor's v3 floor and the schema's v3 floor shape change. Part 03 §12 already cites the Blosc, CRC32C, and sharding-indexed codec specifications |
| packet manifest and schemas | unchanged; no packet field is added |
| validation and import | affected: Part 05 §5.3 names the finding and its levels; Part 05 §9.1, Part 05 §9.5 and Part 05 §10 are applied, not changed |
| extension registries | unchanged; extension resources derive interfaces through the same mapping |
| reader, writer, validator, adapters | reader and validator affected as §§4.3–4.4 describe; writer output unchanged, with its stale helpers removed; adapters unchanged |
| existing packets | no regeneration needed; arrays using the writer's default and sharded pipelines fall inside the floor, and arrays using `numcodecs.delta` draw an `info` finding |
| conformance fixtures and tests | affected: descriptor schema and checker cases for the new shape; matcher vectors from real v2 and v3 metadata, including every §2.2 pipeline; validator findings for each level and ownership; per-resource reader failure |
| revision tooling | unchanged |
| publications and documentation | affected: Part 10 §5's table gains the five-implementation measurement, and the added probe scripts are committed under `conformance/zarr-probe/`; the TODO defect entry closes |

The open build-order proposal changes Part 05 §10, Part 05 §11, and array delivery. This proposal cites
Part 05 §10 without changing it and leaves delivery alone, so the two do not conflict.

## 6. Open questions

1. **Shard index location.** Preferred: admit only `end`, the Zarr default, and compare an absent
   `index_location` at that default, since zarrita 0.7.5 cannot read an index at `start`.
2. **Blosc discriminants.** Preferred: `cname` alone, because every shuffle mode read in every
   implementation.
3. **Level of a valid feature outside a reader-only floor.** Preferred: `info`. Part 05 §9.1 defines
   `warning` as "likely not intended", and the writer's Zarr codec choice is deliberate and
   permitted.
4. **Unassessed external resources.** Preferred: one `info` finding per resource, attributed like
   the outside-floor finding, in place of the single packet-level list.
5. **Parquet page types.** Preferred: the validator compares compression and encodings from the
   footer, and reports page type as unassessed. The writer's obligation to configure the page type
   remains its enforcement, because PyArrow exposes no page type without reading page headers.
6. **Descriptor schema version.** Preferred: move the schema's `$id` to 0.2.0, since distributed
   copies validate against it and the v3 floor shape changes incompatibly.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [ ] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

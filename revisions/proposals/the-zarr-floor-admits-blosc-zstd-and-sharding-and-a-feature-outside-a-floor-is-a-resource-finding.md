# The Zarr floor admits Blosc-Zstd and sharding, and a feature outside a floor is a resource finding

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-09-24 |
| **Based on** | `cc6209e572d48f3b1e86a4895b64264fd7dc6d34` |
| **Decision domain** | specification |
| **Affects** | Part 03 §6.4; the physical-profile descriptor's `zarr.v3.reader_floor` and its schema; Part 05 §5.3; Part 10 §5; the reader's array codec reporting and `UnsupportedCodecError`; the validator's physical checks; the writer's residual codec-name helpers |

## 1. Problem

The portable physical profile declares, for each storage interface, a reader floor: the physical
features every conforming reader supports.
[Part 03 §6.4](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-array-codecs)
fixes the Zarr v3 floor at three ordered codec sequences: `bytes`; `bytes` then `gzip`; and `bytes`
then `zstd`. The Zarr floor binds readers only, so a writer may use any valid codec, and under
[Part 03 §2](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-portable-profile-technologies)
a valid feature outside it forfeits the portability guarantee without being an error.

The reference writer emits no packet-owned array inside that floor. Its default pipeline is `bytes`
then Blosc, and its sharded arrays wrap that pipeline in `sharding_indexed`. The guarantee covers
none of the arrays a reference build produces, so a finding raised for every array outside the
floor would distinguish nothing.

[Part 05 §5.3](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-validation-shim) has a
validator check each available resource's codecs, but no implementation compares them with a floor,
and [R129 §3.8](../accepted/R129-a-portable-profile-declares-its-interfaces-and-reader-floor.md#38-physical-assessment-uses-available-resource-metadata)
left the comparison's finding IDs and severity to a later revision.

[Part 03 §6.1](../../escapewheel_poc_docs_v0.2/03_portable_physical_profile.md#ew-array-version)
has a reader report missing support for the one resource it cannot decode, and the reference reader
lets a library exception escape instead. Its codec listing also discards the order and nesting a
floor comparison needs.

The floor cannot admit either feature the writer uses in its current shape. A floor entry is a list
of bare codec names, so it cannot state Blosc's `cname` or the pipeline nested inside a shard.

## 2. Evidence

All observations were made at the recorded baseline on 2026-09-24.

### 2.1 The reference writer emits no array inside the v3 floor

Each row below comes from calling the writer's `write_zarr` with a `StagedArray` shaped like the
named path, under the writer environment's zarr-python 3.3.0, and reading the resulting `zarr.json`.
The table omits configuration members that no option below discriminates on.

| writer path | stored v3 pipeline | in the current floor | in the preferred floor |
|---|---|---|---|
| `StagedArray` default, `codecs=("blosc",)`, no shard | `bytes`, `blosc` (`cname: zstd`, `shuffle: shuffle`) | no | yes |
| waveform adapter, `shard=shard_for(...)` | `sharding_indexed` holding `bytes`, `blosc` (`cname: zstd`); index `bytes`, `crc32c`; `index_location: end` | no | yes |
| NWB adapter signals, `codecs=("numcodecs.delta", "blosc")` | `numcodecs.delta`, `bytes`, `blosc` (`cname: zstd`, `shuffle: bitshuffle`) | no | no |

The writer's only other route stages an adapter-written array unchanged, and the LFP adapter's
arrays are external Zarr v2 whose metadata the source defines.

### 2.2 Five implementations read Blosc-Zstd and sharding

The repository's Zarr probe, `conformance/zarr-probe/`, writes arrays with zarr-python and reads
them back with Zarr.jl, checking the int64 element sum.
Both read Blosc-Zstd and sharding ([R3 §7.3](../accepted/R3-cross-language-physical-floor.md#73-evidence)),
yet [R3 §8](../accepted/R3-cross-language-physical-floor.md#8-rejected-alternatives) declined to
raise the floor on two implementations, and
[R14 §2.1](../accepted/R14-codec-floor-and-external-resources.md#21-the-reader-floor-is-unchanged)
kept it.

Rerun unchanged, the probe's `write.py` and `read.jl` reproduce R3's result. The same element-sum
check was extended to three further readers: TensorStore; zarrs, through zarrs-python with
`codec_pipeline.strict` set so that no read falls back to Python; and zarrita. Further arrays
covered each Blosc shuffle mode, each floor pipeline inside a shard, both index pipelines, both
index locations, and the three writer paths of §2.1. The scripts for those added arrays and readers
ran in a scratch directory and are not committed.

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

All five also read Zarr v2 zstd and Blosc-Zstd, which the v2 floor already admits. zarrita fails an
index at `start` with `RangeError [ERR_OUT_OF_RANGE]`. On the delta pipeline, Zarr.jl reports that
it "does not support the delta codec", TensorStore that `"numcodecs.delta" is not registered`, and
zarrs raises `UnsupportedMetadataError`.

The five readers are written in Python, Julia, C++, Rust, and JavaScript. That all five decode Blosc
through the c-blosc library or a build of it is an inference, not checked here. If it holds, R3 §8's
cost stands: a new implementation must bind that library or reimplement it to conform.

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

### 2.4 The reader's codec reporting drops the resource and the pipeline's shape

- `UnsupportedCodecError` is exported and never raised.
- `ArrayResource.open` catches only `ImportError`. For a pipeline naming an unregistered codec,
  zarr-python 3.3.0 raises `zarr.errors.UnknownCodecError: Unknown codec: 'example.unknown'` when
  the array opens, so the caller receives a library exception that does not name the resource.
- `ArrayResource.codecs` and `resources._codec_names` drop `bytes`, flatten a shard's inner
  pipeline, and omit its index pipeline. For v2 they list the compressor before the filters, the
  reverse of the encoding order the v3 listing follows. The property's docstring calls the listing
  comparable with "what the manifest claims", although
  [Part 04 §6](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-packet-codecs) no longer
  lets a manifest carry codecs.
- The writer's `declared_codecs` and `written_codecs` still derive manifest-style name lists, and
  only tests call them. `ExternalArray` still carries `physical_profile` and `codecs`; the LFP
  adapter fills them, and the delivery serializer drops them.

## 3. Desired outcome and constraints

A successful resolution:

- makes the v3 floor cover the reference writer's default and sharded output, on the evidence of
  §2.2;
- states each floor entry so it compares exactly with Zarr metadata, including configuration
  discriminants and a shard's nested pipelines;
- has a validator report each available resource's floor membership as one standard finding per
  resource, composed through the verdict rules of
  [Part 05 §9.5](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-verdict-composition)
  with no portability verdict of its own;
- has a validator report a packet-owned table outside the Parquet writer floor as a warning, since
  [Part 05 §10](../../escapewheel_poc_docs_v0.2/05_validation_and_import.md#ew-conformance-classes)
  bars reporting a packet non-conforming for an obligation that binds only a writer; and
- has a reader fail one selected resource by naming the codec it cannot decode, whatever the floor
  says.

A resolution also preserves:

- the Parquet floor's writer ceiling and the Zarr floor's reader-only role;
- the Zarr writer's open codec choice;
- the descriptor's refusal to enumerate optional features;
- the absence of packet codec fields; and
- the rule that structural validation never reaches the network.

## 4. Options and tradeoffs

### 4.1 Floor membership

**Keep the current floor.** Rejected: every array the reference writer emits would stay outside
the guarantee, and a finding on every array distinguishes nothing.

**Admit Blosc with `cname: zstd`, and sharding over floor pipelines (preferred direction).** All five
implementations of §2.2 read both, where R3 §8 had evidence from two, and R129 set the Parquet
floor on the same standard. The cost R3 §8 named remains: a new reader has to
decode Blosc and parse shard indexes. Under this direction:

- a Blosc entry discriminates on `cname` alone, since all three shuffle modes read in all five
  implementations;
- a sharded pipeline matches when it is exactly one `sharding_indexed` codec whose inner pipeline
  matches an unsharded floor sequence, whose index pipeline is `bytes` or `bytes` then `crc32c`, and
  whose `index_location` is `end`; and
- the floor admits no nested shard and no codec outside a shard. Neither was measured here. The
  writer's `arrays` module records that an outer codec over a shard disables the partial read
  sharding exists for, at 188 ms against 0.6 ms to reach one chunk.

**Admit Blosc with any `cname`.** Rejected: `lz4` also read in all five, but the floor already
carries Zstd and no writer needs a second Blosc compressor.

**Also admit `numcodecs.delta`.** Rejected: only two of the five read it, so arrays using it stay
outside the floor and draw the finding of §4.3.

### 4.2 Floor representation

**Enumerate every sharded sequence flat.** Rejected: four inner sequences and two index pipelines
add eight entries and state the inner floor twice.

**Structured codec patterns, with one `sharding` member (preferred direction).** Each floor entry
becomes an ordered list of codec patterns, matched by the rule Part 03 §6.4 already states for v2
patterns: every stated member compares equal, and unmentioned members do not participate. A
`sharding` member states the index pipelines and location once and takes the inner pipeline from
`codec_sequences`:

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
as [R129 §3.5](../accepted/R129-a-portable-profile-declares-its-interfaces-and-reader-floor.md#35-floor-role-is-declared-per-interface)
requires of a floor. The descriptor schema's v3 floor shape changes incompatibly.

### 4.3 Portability reporting

**A portability verdict beside the packet, core, and extension verdicts.** Rejected: floor
membership does not decide conformance (Part 03 §2), so the verdict would add an axis every consumer
composes separately for nothing a finding cannot carry.

**One standard per-resource finding (preferred direction).** The finding has one check ID,
tentatively `physical.outside_reader_floor`, and names:

- the resource;
- its interface and variant; and
- the observed features that matched no entry: each outside compression or encoding for Parquet,
  and the full observed pipeline for Zarr.

Its level is `warning` for a packet-owned table, whose writer floor it breaks, and `info` for any
other resource. It is never `error`, so no verdict changes. Part 05 §9.5 attributes it to the
registry that declares the resource. A consumer can read "portable" as the absence of this finding
and of unassessed resources.

Under this direction, a validator:

- reports malformed metadata, or an invalid configuration of a codec it recognizes, as upstream
  invalidity through the existing error findings;
- treats an unrecognized codec name as outside the floor rather than invalid, because Zarr v3 admits
  extension codecs and a validator cannot judge one it does not know; and
- assesses packet-owned resources during structural validation, and external ones only in the
  requested resolution mode of
  [Part 04 §5.3](../../escapewheel_poc_docs_v0.2/04_packet_catalog.md#ew-external-resource-verification).

### 4.4 Reader reporting

**Keep the name tuple and fix it** by retaining `bytes` and nesting. Rejected: the tuple would still
lose the configuration the preferred floor discriminates on.

**Expose the stored pipeline, and share one matcher (preferred direction).**

- `ArrayResource` returns the format-owned pipeline unchanged: v3 `codecs`, or v2 `filters` and
  `compressor`.
- The reader's profile module offers one floor matcher, which the validator and any other caller
  use.
- `open` raises `UnsupportedCodecError`, naming the resource and the codec, when the Zarr library
  cannot build the pipeline.
- The reader never refuses or warns over floor membership alone, since it may support more.

With the pipeline exposed, the writer's `declared_codecs`, `written_codecs`, and the `ExternalArray`
fields of §2.4 have no consumer left and can be removed.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged; the change concerns storage only. |
| logical prose and registries | Unchanged; logical kinds and the kind-to-interface mapping stay as they are. |
| physical profiles | Affected: Part 03 §6.4 states the new v3 entries, sharded matching, and default-valued members; the descriptor's v3 floor and the schema's v3 floor shape change. Part 03 §12 already cites the Blosc, CRC32C, and sharding-indexed codec specifications. |
| packet manifest and schemas | Unchanged; no packet field is added. |
| validation and import | Affected: Part 05 §5.3 names the finding and its levels. Part 05 §9.1, Part 05 §9.5, and Part 05 §10 are applied, not changed. |
| extension registries | Unchanged; extension resources derive interfaces through the same mapping. |
| reader, writer, validator, adapters | Affected: the reader and validator change as §§4.3–4.4 describe, and the writer loses its stale helpers. Writer output is unchanged, and adapters are unchanged because their codec choices stay valid. |
| existing packets | Unchanged; the writer's default and sharded arrays fall inside the new floor, and arrays using `numcodecs.delta` draw an `info` finding. |
| conformance fixtures and tests | Affected: descriptor-schema and checker cases for the new shape; matcher vectors from real v2 and v3 metadata, including every §2.2 pipeline; validator findings for each level and ownership; per-resource reader failure. |
| revision tooling | Unchanged; the ledger and evidence tools already cover a specification change to Part 03 and Part 05. |
| publications and documentation | Affected: Part 10 §5's table gains the five-implementation measurement, the added probe scripts are committed under `conformance/zarr-probe/`, and the TODO entry on reader codec reporting closes. |

Two open changes touch neighbouring text without conflict: the build-order draft retitles Part 05
§5, the parent of Part 05 §5.3, and the digest proposal rewrites the Part 04 §5.3 levels this
proposal cites only for when a validator may reach an external resource.

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
   footer and reports page type as unassessed. The writer's obligation to configure the page type
   remains its enforcement, because PyArrow exposes no page type without reading page headers.
6. **Descriptor schema version.** Preferred: move the schema's `$id` to 0.2.0, since distributed
   copies validate against it and the v3 floor shape changes incompatibly.

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [ ] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [ ] The exact proposal and its final appraisal state are tracked in the current commit.
- [ ] The proposal has explicit approval to advance to a revision draft.

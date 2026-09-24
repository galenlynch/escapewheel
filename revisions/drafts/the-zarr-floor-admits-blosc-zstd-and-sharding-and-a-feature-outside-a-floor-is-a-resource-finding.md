# The Zarr Floor Admits Blosc-Zstd and Sharding, and a Feature Outside a Floor Is a Resource Finding

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `06b11fb29285fe90890ae84054ca33807bf9abfb` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§5.5 and 6.4; Part 05 §5.3; Part 10 §5; `registry/physical_profile.schema.json`; `registry/physical_profiles/escapewheel-portable-v0.1.json` |
| **Depends on** | R129 §§3.4, 3.5, and 3.8 |
| **Profile** | `escapewheel-portable-v0.1` |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4; §3.5; §3.6 |

Section 3 is normative. Sections 1, 2, and 4–6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

The portable physical profile declares, for each storage interface, a reader floor: the physical
features every conforming reader supports. Part 03 §6.4 fixes the Zarr v3 floor at three ordered
codec sequences: `bytes`; `bytes` then `gzip`; and `bytes` then `zstd`. The Zarr floor binds
readers only, so a writer may use any valid codec, and under Part 03 §2 a valid feature outside it
forfeits the portability guarantee without being an error.

The reference writer emits no packet-owned array inside that floor. Its default pipeline is `bytes`
then Blosc, and its sharded arrays wrap that pipeline in `sharding_indexed`, so the guarantee covers
none of the arrays a reference build produces. A floor entry is a list of bare codec names, and it
cannot state Blosc's `cname` or the pipeline nested inside a shard. Part 05 §5.3 has a validator
check each available resource's codecs, but no rule says what the validator reports when a resource
falls outside a floor: R129 §3.8 left the finding IDs and levels to a later revision.

This revision admits Blosc-Zstd and sharding over floor pipelines to the v3 floor, restates each
floor entry as codec patterns that compare exactly with Zarr metadata, and advances the descriptor
schema for the new shape. It defines one per-resource finding for a resource outside its floor, and
one per-resource finding for an external resource left unassessed. It says which Parquet floor
features a validator compares.

The change is structural because it replaces rules inside existing sections: the second paragraph
of Part 03 §6.4, which fixes the v3 floor, and the Part 05 §5.3 sentences under which a resource
outside a floor or unavailable draws no stated finding. Appended sections would leave each stating a
narrower rule beside its replacement.

### 1.1 Structural crosswalk

Part 03 §§5.5 and 6.4 and Part 05 §5.3 carry the canonical anchors `ew-parquet-reader-floor`,
`ew-array-codecs`, and `ew-validation-shim`. Commit `06b11fb` added `ew-zarr-codec-floor-evidence`
to Part 10 §5 and changed nothing else. No section is added, moved, or retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §5.5, the Parquet floor and writer ceiling | extend in place with one paragraph after the descriptor paragraph | same section | a validator compares footer-reported compressions and encodings, and reports data-page types it does not compare as unassessed | §3.4 |
| Part 03 §6.4, the v3 floor is three name sequences, and the v2 matching rule | replace in place | same section | the v3 floor adds Blosc-Zstd and sharding over floor pipelines; entries are codec patterns; sharded matching, unrecognized codecs, and the schema's pattern shape are stated; the v2 floor and its rule are unchanged | §§3.1–3.3 |
| Part 05 §5.3, an unavailable external resource is physically unassessed, and a valid feature outside a reader-only floor is not by itself a profile error | replace those two sentences in place | same section | defines `physical.outside_reader_floor` and its levels, and makes `external.physical_unassessed` one `info` finding per resource | §§3.5, 3.6 |
| Part 10 §5, the two-implementation Zarr table | revise the informative table | same section | carries the five-implementation measurement of §2.2 | none |

## 2. Background

Section 2 is informative. The writer output of §2.1 was reproduced at the recorded baseline on
2026-09-24; the reader matrix of §2.2 was measured the same day against the same arrays.

### 2.1 The reference writer emits no array inside the v3 floor

Each row below comes from writing an array through the reference writer's array path with the
layout named, under the writer environment's zarr-python 3.3.0, and reading the stored `zarr.json`.
The table omits configuration members no alternative in §2.5 turns on.

| reference-writer output | stored v3 pipeline | current floor | this floor |
|---|---|---|---|
| a default array | `bytes`, `blosc` (`cname: zstd`, `shuffle: shuffle`) | outside | inside |
| a sharded array, as the waveform source writes | `sharding_indexed` holding `bytes`, `blosc` (`cname: zstd`, `shuffle: shuffle`); index `bytes`, `crc32c`; `index_location: end` | outside | inside |
| a delta-filtered array, as the NWB source writes a signal | `numcodecs.delta`, `bytes`, `blosc` (`cname: zstd`, `shuffle: bitshuffle`) | outside | outside |

The writer's only other route stages an adapter-written array unchanged, and the LFP source's arrays
are external Zarr v2 whose metadata the source defines.

### 2.2 Five implementations read Blosc-Zstd and sharding

The repository's Zarr probe, `conformance/zarr-probe/`, writes arrays with zarr-python and reads
them back with Zarr.jl, checking the int64 element sum. Both read Blosc-Zstd and sharding
(R3 §7.3), yet R3 §8 declined to raise the floor on two implementations, and R14 §2.1 kept it.

Rerun unchanged, the probe reproduces R3's result. The same element-sum check was extended to three
further readers: TensorStore; zarrs, through zarrs-python with a strict codec pipeline so that no
read falls back to Python; and zarrita. Further arrays covered each Blosc shuffle mode, each floor
pipeline inside a shard, both index pipelines, both index locations, and the three outputs of §2.1.
The scripts for those arrays and readers ran in a scratch directory and are committed under
`conformance/zarr-probe/` at incorporation.

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
zarrs that the metadata is unsupported.

The five readers are written in Python, Julia, C++, Rust, and JavaScript. That all five decode
Blosc through the c-blosc library or a build of it is an inference, not checked here. If it holds,
R3 §8's cost stands: a new implementation must bind that library or reimplement it to conform.

### 2.3 No validator compares a resource with a floor

The reference validator reads a packet-owned array's stored codec names only to reject `transpose`,
and reads neither floor from the descriptor. The reference writer checks each packet-owned table's
footer against the Parquet floor before committing, but the validator reads Parquet footers only
for statistics. An unresolved external resource yields one `info` finding,
`external.physical_unassessed`, attributed to the packet and counting every such resource.

The reference reader compares an array's Zarr metadata with the v3 or v2 floor of the descriptor
vendored in its package, and reports the verdict on the array's handle and in the error it raises
for a codec it cannot decode. Its matcher already accepts codec patterns with configuration members
and a `sharding` member with an absent `index_location` read as `end`, so it applies §3.2's rules
once the vendored descriptor carries §3.1's floor.

A Parquet footer reports each column chunk's compression and encodings. Data-page types are
recorded in page headers and optionally in the footer's encoding statistics, and PyArrow 25.0.1's
footer API exposes neither.

### 2.4 Levels

Part 05 §9.1 defines `warning` as conformant but likely not intended, and `info` as recorded, not
judged. A packet-owned table outside the Parquet floor breaks its writer's ceiling, which fits
`warning`; Part 05 §10 bars reporting a packet non-conforming for an obligation that binds only a
writer, so it cannot be `error`. A Zarr array outside the reader-only floor is a permitted,
deliberate writer choice, which fits `info`. A finding about one resource is attributed under
Part 05 §9.5 to the registry declaring it; a packet-level list of resources from several registries
has no one registry to belong to.

### 2.5 Alternatives

Keeping the current floor leaves every array the reference writer emits outside the guarantee, so a
finding on every array would distinguish nothing. Admitting Blosc with any `cname` adds a second
Blosc compressor no writer needs, although `lz4` read in all five. Admitting `numcodecs.delta` would
bind readers to a codec three of the five cannot read. Admitting an index at `start` gains the
writer nothing and excludes zarrita 0.7.5. Admitting a codec outside a shard would put the whole
shard through that codec before any chunk is reachable, which defeats the partial read sharding
exists for; nested shards were not measured. Enumerating every sharded pipeline flat adds eight
entries and states the inner floor twice.

A portability verdict beside the packet, core, and extension verdicts would add an axis every
consumer composes separately, for a fact that decides no conformance. Reading every page header
to compare Parquet page types costs a read of every page, where the writer already configures the
page type before writing. Keeping the schema's `$id` would let a distributed descriptor of the old
v3 shape claim the new schema.

### 2.6 Feasibility and overlap

The reference validator already reads each packet-owned array's `zarr.json` and each table's
footer, so both comparisons use metadata it holds. Every pipeline in the new floor read in all five
implementations of §2.2.

The digest draft, `every-packet-owned-resource-records-a-named-whole-object-digest.md`, rewrites
Part 03 §§1, 10, and 11.3, removes the RFC 1952 row from Part 03 §12, and replaces the Part 04 §5.3
verification levels. This revision cites Part 04 §5.3 only for when a validator may read an
external resource and changes no Part 03 §12 row, so either order works. R135 retitled Part 05 §5,
the parent of §5.3, and changed nothing this revision relies on.

## 3. Decision

Six subsections set the v3 floor, define how a pipeline matches it, fix the descriptor schema, say
what a validator compares for Parquet, and define the outside-floor and unassessed findings.

### 3.1 The Zarr v3 reader floor

The v3 variant's reader floor admits exactly these unsharded codec sequences, in pipeline order:

- `bytes`;
- `bytes` then `gzip`;
- `bytes` then `zstd`; and
- `bytes` then `blosc` with `cname` `zstd`.

It also admits a sharded pipeline whose shard holds one of those sequences, under §3.2. A
conforming reader MUST expose the logical values of every valid v3 array whose pipeline matches the
floor. The descriptor's `interfaces.zarr.variants.v3.reader_floor` is exactly:

```json
{
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

### 3.2 Matching a v3 pipeline

A reader or validator comparing a v3 array's metadata with the floor MUST apply these rules.

A codec matches a codec pattern when its `name` equals the pattern's and every configuration member
the pattern states compares equal. Members the pattern does not state do not participate, and a
codec stated by its name alone has no configuration members. An unsharded pipeline matches a floor
sequence when both have the same length and each codec matches the pattern at its position.

A sharded pipeline matches the floor when:

- the pipeline is exactly one `sharding_indexed` codec;
- that codec's `codecs` match an entry of `codec_sequences`;
- its `index_codecs` match an entry of `sharding.index_codec_sequences`; and
- its `index_location` equals `sharding.index_location`, an absent `index_location` comparing as
  `end`, the default the sharding-indexed codec specification gives it.

A floor without `sharding` admits no sharded pipeline, and a pipeline matching no entry is outside
the floor. Metadata the applicable Zarr specification makes invalid, including an invalid
configuration of a codec the validator implements, is upstream invalidity rather than a floor
observation. A validator MUST treat a codec name it does not recognize as valid metadata outside
the floor, because Zarr v3 admits extension codecs.

### 3.3 The descriptor schema

The physical-profile schema's `$id`, and the `$schema` value it requires of a descriptor, are
`https://escapewheel.org/schemas/physical-profile/0.2.0`, and the portable descriptor's `$schema`
names it. The schema declares the v3 floor with these definitions, and its Parquet and v2 floors are
unchanged:

| definition | shape |
|---|---|
| `codec_pattern` | closed object; requires `name`, a string; admits `configuration` only where `name` is `blosc`, and there `configuration` is a closed object requiring `cname`, a string |
| `codec_sequence` | array of one or more `codec_pattern` |
| `sharding_floor` | closed object; requires `index_codec_sequences`, an array of one or more distinct `codec_sequence`, and `index_location`, `start` or `end` |
| `zarr_v3_floor` | closed object; requires `codec_sequences`, an array of one or more distinct `codec_sequence`; admits `sharding`, a `sharding_floor` |

### 3.4 Parquet floor assessment

A validator assessing a Parquet resource MUST compare each column chunk's footer-reported
compression and encodings with the floor's `compressions` and `encodings`. It need not read page
headers or determine data-page types. A validator that does not compare data-page types MUST
state in its report that it did not assess them.

### 3.5 The outside-floor finding

A validator MUST assess floor membership for every packet-owned resource whose interface declares a
reader floor, and for every external one whose format-owned metadata it reads under Part 04 §5.3.
For each assessed resource using a feature outside its floor, it MUST report one finding under the
check ID `physical.outside_reader_floor`, naming:

- the resource;
- its interface and, for Zarr, its variant; and
- the observed features that matched no floor entry: each outside compression or encoding for
  Parquet, the whole observed pipeline for Zarr v3, and `filters` and `compressor` for Zarr v2.

The finding's level is `warning` for a packet-owned resource whose interface's floor role is
`reader_and_packet_writer`, and `info` for every other resource. A validator MUST NOT report it at
`error`. The finding concerns one resource, so Part 05 §9.5 attributes it to the registry whose
declaration the resource's entry names.

### 3.6 Unassessed external resources

A validator MUST report each external resource whose interface declares a reader floor and whose
format-owned metadata it did not read, one finding per resource, at `info` under the check ID
`external.physical_unassessed`, naming the resource. Part 05 §9.5 attributes it as it does §3.5's
finding.

## 4. What this does not change

The Zarr floor stays reader-only: a writer MAY still use any codec the applicable Zarr
specification permits, and an array outside the floor stays valid and its packet conforming. A
reader still fails only the resource it cannot decode, under Part 03 §6.1. An encrypted Parquet
footer or column that a validator cannot read leaves that table's evaluation incomplete under
Part 05 §9.4 and draws no outside-floor finding.

## 5. Consequence

Packet bytes and manifests are unchanged, and no packet is rebuilt. The reference writer's default
and sharded arrays fall inside the floor and draw no finding; its delta-filtered arrays draw
`physical.outside_reader_floor` at `info`, and an external LFP array draws it wherever its source's
metadata is outside the v2 floor. A report that listed unresolved external resources in one packet
finding now carries one finding per resource, attributed to each resource's registry.

Reader obligations grow. A reader conforming at the baseline may support only the three current
sequences; it must now decode Blosc-Zstd and parse shard indexes. zarr-python, which the reference
reader uses, already does, and the reference reader's floor verdict admits the reference writer's
default and sharded arrays once its vendored descriptor regenerates. The profile identifier stays
`escapewheel-portable-v0.1`, as it has through earlier candidate changes to the profile's floors.

The descriptor schema's v3 floor shape changes incompatibly, so its `$id` advances to 0.2.0, and a
descriptor naming 0.1.0 fails the checker's `$schema` comparison. The vendored descriptor and schema
in the reader package regenerate.

No accepted clause is superseded. R129 §3.4's exact list of three v3 name sequences is extended by
§3.1 and restated as patterns, and R129 §3.8's deferral of finding IDs and levels is answered by
§§3.5–3.6; both keep `applied` dispositions, with notes saying so. R3 §7.2 and R14 §2.1 keep
`applied`, with notes that the floor now includes Blosc-Zstd and sharding. The 16 ledger
destinations that name Part 03 §5.5 or §6.4 or Part 05 §5.3 by number move to
`ew-parquet-reader-floor`, `ew-array-codecs`, and `ew-validation-shim`: those of R3 §§2.1 and 7.2,
R14 §§2.1 and 2.2, R15 §2, R21 §3.3, R110 §§3.3 and 3.5, R111 §3.5, and R118 §§3.1–3.6.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. The change concerns storage only. | None required. |
| logical prose and registry | Unchanged. Logical kinds and the kind-to-interface mapping stay as they are. | None required. |
| physical profiles | Part 03 §6.4 takes §§3.1–3.3 and Part 03 §5.5 takes §3.4. The descriptor's v3 floor becomes §3.1's object and its `$schema` names 0.2.0; the schema takes §3.3's definitions and `$id`. Part 03 §12 already cites the Blosc, CRC32C, and sharding-indexed codec specifications. | `evidence/R<N>.json` names both anchors and the schema pointers; `registry/check.py` validates the descriptor. |
| packet manifest and JSON Schemas | Unchanged. No packet field is added. | None required. |
| validation and import | Part 05 §5.3 takes §§3.5 and 3.6. Part 05 §§9.1, 9.5, and 10 are applied, not changed. | The corpus variants below. |
| extensions | Unchanged. An extension's resources derive their interfaces through the same mapping and draw the same findings, attributed to the extension. | A validator test attributing the finding to an extension. |
| reader, writer, validator, adapters | The validator reads both floors from the descriptor, matches under §3.2, reports §§3.5 and 3.6, and states that data-page types were not assessed. The reader's code is unchanged: zarr-python reads the new floor, its floor matcher already applies §3.2, and Part 03 §6.1 already has a reader report a codec it cannot decode; its vendored descriptor and schema regenerate, and its test that places a sharded array with a `bytes`, `crc32c` index outside the floor is inverted. The writer and adapters are unchanged, since their codec choices stay valid; writer comments that say a manifest declares codecs or that Zarr.jl reads delta are corrected. | Validator and descriptor tests below. |
| conformance fixtures and tests | Descriptor-schema and checker cases accept §3.1's floor and reject a `configuration` on a non-Blosc pattern, an unknown pattern member, and a 0.1.0 `$schema`. Matcher vectors from real metadata cover every pipeline of §2.2, an absent `index_location`, an index at `start`, a codec after a shard, and an unrecognized codec. Corpus variants: a packet-owned array using `numcodecs.delta` draws the finding at `info`; a packet-owned table using an outside encoding draws it at `warning`; the valid packet draws none; two unresolved external resources draw two `external.physical_unassessed` findings. | `fixtures/corpus.py`, the validator suite, and the reader suite. |
| revision process and tooling | The ledger moves and notes above; otherwise the ordinary revision and evidence records. | `ledger.py` and `evidence.py`. |
| generated publications and developer documentation | Part 10 §5's table carries §2.2's measurement. The combined specification and heading index regenerate, and the extended probe scripts are committed under `conformance/zarr-probe/`. | `verify.py`. |

## 6. Conformance and implementation evidence

Each clause is `applied`, by canonical anchor: §§3.1–3.3 at Part 03 §6.4, §3.4 at Part 03 §5.5, and
§§3.5 and 3.6 at Part 05 §5.3. The descriptor and schema are evidence owners of §§3.1 and 3.3.

The negative cases distinguish the new rules from the current ones:

- a packet-owned array stored as `bytes`, `blosc` (`zstd`), or as that pipeline inside
  `sharding_indexed` with index `bytes`, `crc32c` at `end`, is inside the floor, where the current
  floor puts both outside;
- the same shard with `index_location: start`, or followed by a `zstd` codec, is outside;
- a pipeline with `blosc` (`lz4`) or `numcodecs.delta` draws `physical.outside_reader_floor` at
  `info`, where no finding is reported now;
- a packet-owned table with `PLAIN_DICTIONARY` draws the finding at `warning`;
- an unrecognized codec name draws the outside-floor finding and no invalid-metadata finding; and
- two unresolved external resources declared by different registries draw two
  `external.physical_unassessed` findings, each attributed to its registry, where one packet-level
  finding is reported now.

The positive case is the valid corpus packet, whose tables and arrays draw neither finding. The
extended Zarr probe is the feasibility evidence for §3.1; rerunning it against newer library
versions is what keeps Part 10 §5 current.

# The reader floor bounds an array's byte order

| | |
|---|---|
| **Status** | **Proposal** |
| **Opened** | 2026-10-01 |
| **Based on** | `f8d62ab0e79945a68d9aa8f7d3446cb60d956bca` |
| **Decision domain** | specification |
| **Affects** | R3 §7.1's requirements that an array be little-endian and set `fill_value`; Part 03 §6.4's Zarr v2 reader floor; Part 05 §5.3's list of the features a floor finding names; the incorporated physical-profile schema and the `escapewheel-portable-v0.1` descriptor |

## 1. Problem

R3 §7.1, an accepted revision, requires every array to be little-endian and to set `fill_value`
explicitly. The ledger records that clause as applied in Part 03 §6.1. Part 03 §6.1 states neither
requirement, and no other part mentions byte order or `fill_value`. The accepted record and the
parts therefore disagree, and the reference implementation follows the record: its validator
reports an array without `fill_value` as an error and cites Part 03 §6.1, which has no such rule.

Restoring the two sentences would make the parts agree with the record, and the measurements in §2
argue against restoring them. Every probed reader decodes a big-endian Zarr v3 array, and the v3
reader floor already obliges a conforming reader to decode one. The Zarr specifications themselves
require `fill_value`. The measurements show a different defect instead: the Zarr v2 reader floor says
nothing about byte order, so it obliges every conforming reader to decode a big-endian v2 array, and
two of the five probed libraries do not.

## 2. Evidence

Observed in the tracked files at the baseline commit, and in a run of the Zarr conformance probe
under `conformance/zarr-probe/` on 2026-10-01.

### 2.1 The parts state neither sentence of R3 §7.1

R3 §7.1 has three paragraphs. The first requires Zarr v3 with a regular chunk grid. The second
requires little-endian arrays, noting that in Zarr v3 byte order is the `bytes` codec's `endian`
configuration, and requires that `fill_value` be set explicitly. The third forbids `transpose`.

The ledger's entry for R3 §7.1 has the disposition `applied` and the destination Part 03 §6.1, with
the note that the clause was restored on 2026-09-04 because the regular chunk grid was absent.
Part 03 §6.1 states the version rule and the regular chunk grid, and Part 03 §6.2 forbids
`transpose`. A case-insensitive search of `spec/parts/` for `endian` and for `fill_value` finds no
occurrence in any part.

### 2.2 The v3 floor already admits either byte order

Part 03 §6.4 gives the v3 reader floor as codec patterns, each beginning with `{"name": "bytes"}`.
Its matching rule compares only the configuration members a pattern states, and a pattern stated by
name alone states none. A `bytes` codec configured `endian: big` therefore matches the floor, and
Part 03 §6.4 obliges a conforming reader to expose the logical values of every valid v3 array whose
pipeline matches the floor.

### 2.3 Every probed reader decodes a big-endian v3 array

`write_endian.py` writes one 2000 by 384 `int16` array five ways with zarr-python and records its
int64 element sum, -365,664. The sum of the same bytes read without swapping differs, so a reader
that ignores the declared byte order reports a wrong sum. Each reader's script compares its own sum
with the recorded one. The readers were zarr-python 3.4.0 with numcodecs 0.17.0, TensorStore 0.1.85,
zarrs-python 0.2.3, Zarr.jl 0.10.2 on Julia 1.12.7, and zarrita 0.7.5 on Node 22.22.2.

| stored array | zarr-python | TensorStore | zarrs | Zarr.jl | zarrita |
|---|---|---|---|---|---|
| v3, `bytes` big-endian, `int16` | reads | reads | reads | reads | reads |
| v3, `bytes` big-endian then `zstd`, `int16` | reads | reads | reads | reads | reads |
| v3, `sharding_indexed` around `bytes` big-endian then `zstd`, `int16` | reads | reads | reads | reads | reads |
| v3, `bytes` big-endian, `float32` | reads | reads | reads | reads | reads |
| v2, `dtype` `>i2`, compressor `zstd` | reads | reads | refuses | wrong values | reads |

### 2.4 Two of five probed readers do not decode a big-endian v2 array

The last row of §2.3's table is a v2 array inside the current floor. Part 03 §6.4 gives the v2 floor
as `filters: null` with one of three compressors, `zstd` among them, and compares no other member of
the array's metadata. zarrs-python refuses the array with "Non-native byte order not supported".
Zarr.jl returns a sum of -2,964,480 and raises no error, so its caller receives wrong values.

Part 03 §2 defines a reader floor as what every conforming reader supports for logical-value access.
Part 03 §6.1 permits Zarr v2 only for an array a packet references, and the descriptor gives the Zarr
interface the floor role `reader_only`, so the floor binds readers and no writer.

### 2.5 The Zarr specifications require `fill_value`

The Zarr v3 core specification lists `fill_value` among the members an array's metadata document
contains, and the Zarr v2 storage specification lists it among the keys of `.zarray`, where its value
may be null. Part 03 §12 already names both as normative references. Part 03 §6.4 classes metadata
the applicable Zarr specification makes invalid as upstream invalidity and not as a floor
observation. A v3 array without `fill_value` is therefore invalid before any rule of this
specification applies to it.

### 2.6 A floor change has kept the profile identifier twice

R137 changed the Zarr floor incompatibly, advanced the profile schema's identifier to 0.2.0, and kept
the profile identifier `escapewheel-portable-v0.1`. R154 added a descriptor member, advanced the
schema to 0.3.0, and kept the profile identifier again. A packet records `profile_id`, so keeping it
leaves every existing packet's identity and every amendment's identity unchanged.

## 3. Desired outcome and constraints

Every sentence of an accepted clause is either stated by the part the ledger names or recorded as
superseded. A conforming reader is obliged to decode only arrays that the probed libraries decode,
and a consumer learns from a validator's report when a referenced array falls outside that set. The
resolution preserves:

- the conformance of every existing packet, including one that references a big-endian array its
  writer did not produce;
- the v3 reader floor and its matching rule;
- the profile identifier `escapewheel-portable-v0.1`; and
- Part 03 §2's rule that a feature outside a reader-only floor leaves a packet conforming.

## 4. Options and tradeoffs

| option | effect |
|---|---|
| restore both sentences of R3 §7.1 to Part 03 §6.1 | the parts match the ledger; a packet referencing a big-endian array becomes non-conforming over external bytes its writer cannot change (Part 03 §8.2); the v3 rule excludes arrays every probed reader decodes; the `fill_value` sentence repeats the Zarr specifications |
| supersede both sentences and change nothing else | the parts and the record agree; the v2 floor still obliges every conforming reader to decode a big-endian v2 array, which zarrs-python refuses and Zarr.jl decodes wrongly |
| supersede both sentences and narrow the v2 floor to little-endian and single-byte data types (preferred direction) | the parts and the record agree; the floor obliges a reader only where all five probed libraries read correctly; a big-endian v2 array stays valid and conforming and draws a per-resource finding |
| also narrow the v3 floor to a little-endian `bytes` codec | no measurement supports it; it adds a configuration member to four codec patterns and takes arrays every probed reader decodes out of the floor |

Under the preferred direction a later revision supersedes R3 §7.1's requirements of byte order and
of `fill_value`, and the ledger records that those two sentences no longer bind. Part 03 §6.1 keeps
its text. Byte order becomes a property the reader floor bounds, and no packet is required to store
an array in either order.

Part 03 §6.4's v2 floor gains one condition beside its three metadata patterns: the array's `dtype`
declares little-endian byte order or a type that has none, which a v2 type string writes as the
prefix `<` or `|`. Where `dtype` is a structured type, the condition holds of each field's type
string. A v2 array of any other byte order is outside the floor. It remains valid Zarr, a packet
referencing it remains conforming, and Part 05 §5.3's finding `physical.outside_reader_floor`
reports it at `info`, as it reports any feature outside a reader-only floor. Part 05 §5.3 lists the
observed features that finding names, and for Zarr v2 the list gains `dtype`.

The descriptor states the condition in its v2 floor. The current floor is a list of patterns whose
members compare equal, and a prefix of a string is not an equal member, so the floor gains a member
naming the admitted byte orders. The schema declares that member and its identifier advances, as in
§2.6, and the profile identifier stays.

The `fill_value` requirement is dropped without a replacement. A validator that reports a metadata
document lacking `fill_value` is reporting upstream invalidity under Part 03 §6.4, and needs no rule
of Part 03 §6.1 to do so.

## 5. Impact sketch

| surface | effect |
|---|---|
| semantic prose | Unchanged. Part 01 states no storage property. |
| logical prose, registry meta-schema, declarations and rules | Unchanged. The registry declares no byte order and no rule reads array metadata. |
| physical profiles | Part 03 §6.4's v2 floor states the byte-order condition. The schema declares the new floor member and advances its identifier; the descriptor's v2 floor carries the member. Part 03 §6.1 is unchanged. The profile identifier is unchanged. |
| packet manifest and other JSON Schemas | Unchanged. No manifest member states a byte order or a fill value. |
| validation and import | Part 05 §5.3 adds `dtype` to the features a v2 floor finding names. A validator assesses a v2 array's byte order with the rest of the floor. No import rule changes, since a build writes v3 arrays and v2 is external only. |
| extension registries | Unchanged. An extension declares no storage property. |
| reader, writer, validator, adapters, code generation | The reader's floor test compares a v2 array's byte order, and its vendored descriptor and schema regenerate. The validator reports a big-endian v2 array under the floor finding, and its check of an absent `fill_value` stops citing Part 03 §6.1. The writer's documentation stops citing Part 03 §6.1 for byte order and `fill_value`; its output is unchanged. Adapters are unchanged. |
| existing packets | Unchanged in conformance. A packet referencing a big-endian v2 array gains one `info` finding; the conformance corpus references no v2 array. |
| conformance fixtures and implementation tests | The descriptor check gains cases for the new member. The corpus or the validator's tests gain a referenced v2 array of each byte order, expecting the floor finding for big-endian and none for little-endian. The probe's big-endian set stays as the evidence. |
| revision lifecycle, ledger, evidence and tooling | The ledger's entry for R3 §7.1 records which sentences the later revision superseded. No process rule changes. |
| generated publications and developer documentation | Part 03 §2's generated table is unchanged. Part 10 §5's reader matrix gains the big-endian rows. The combined rendering regenerates. |

## 7. Promotion criteria

- [x] The baseline commit is recorded and the problem is demonstrated against its generated v0.2 specification.
- [x] The current owner of each affected fact and the affected abstraction level are identified.
- [x] Every impact-sketch surface is marked affected, unchanged with a reason, or unknown.
- [x] Overlapping proposals, drafts, accepted revisions, and changed-section citers have been examined.
- [x] Material alternatives, compatibility effects, migration costs, and the option to keep the current rule have been considered.
- [x] The evidence needed to distinguish conforming from non-conforming behavior is identified.
- [x] Questions that would change the decision are resolved, or the proposal is split so they no longer block it.
- [x] The intended direction is clear enough to express as testable normative clauses and exact registry or schema declarations where applicable.
- [x] The exact proposal and its final appraisal state are tracked in the current commit.
- [x] The proposal has explicit approval to advance to a revision draft.

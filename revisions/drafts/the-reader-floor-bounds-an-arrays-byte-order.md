# The reader floor bounds an array's byte order

| | |
|---|---|
| **Status** | **Draft** |
| **Based on** | `5117217baf235beab19700e9b945b673b4bd41eb` |
| **Decision domain** | specification |
| **Change form** | structural |
| **Amends** | Part 03 §§1 and 6.4; Part 05 §5.3; Part 10 §5; the physical-profile schema; the `escapewheel-portable-v0.1` descriptor |
| **Depends on** | R3 §7.1 (the byte-order and `fill_value` requirements this supersedes); R129 §3.4 (the v2 floor this narrows); R137 §3.5 (the finding this extends); R154 §3.5 (the schema identifier this advances from) |
| **Profile** | `escapewheel-portable-v0.1` |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

## 1. Scope

R3 §7.1 requires every array to be little-endian and to set `fill_value` explicitly. The ledger
records that clause as applied at Part 03 §6.1, and no part states either requirement: a
case-insensitive search of the thirteen parts for `endian` and for `fill_value` finds no occurrence.
The accepted record and the parts disagree.

This revision resolves the disagreement by superseding the two sentences, not by restoring them.
Part 03 §6.4 already lets a writer use any codec the applicable Zarr specification permits, the v3
reader floor already admits a `bytes` codec of either byte order, and every probed reader decodes a
big-endian v3 array. The Zarr specifications themselves require `fill_value`.

The measurements show a different defect. The Zarr v2 reader floor compares only `filters` and
`compressor`, so it obliges every conforming reader to decode a big-endian v2 array, and two of the
five probed libraries do not. This revision narrows the v2 floor to arrays whose data type is
little-endian or has no byte order, declares that bound in the descriptor, and has the outside-floor
finding name `dtype`. The descriptor schema advances to 0.4.0, and the profile identifier is
unchanged.

The change is structural because it revises rules inside existing sections: Part 03 §6.4's sentence
fixing the v2 floor, Part 03 §1's schema identifier, and Part 05 §5.3's list of the features a
finding names. Appended sections would leave each stating a wider floor or an older identifier
beside its replacement.

### 1.1 Structural crosswalk

Part 03 §§1 and 6.4, Part 05 §5.3 and Part 10 §5 carry the canonical anchors
`ew-portable-profile-scope`, `ew-array-codecs`, `ew-validation-shim` and
`ew-zarr-codec-floor-evidence`, so no anchor bootstrap is needed. No section is added, moved, split
or retired.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| Part 03 §1, the schema's identifier | revise in place | same section | the identifier is 0.4.0 | §3.3 |
| Part 03 §6.4, a writer may use any permitted codec | extend in place | same section | a writer may store an array in either byte order; a metadata document lacking a member the Zarr specification requires is upstream invalidity | §3.1 |
| Part 03 §6.4, the v2 floor is three metadata patterns | revise in place | same section | a v2 array is inside the floor only where its data type is little-endian or has no byte order | §3.2 |
| Part 03 §6.4, the schema's floor definitions | extend the table | same section | the table gains `zarr_v2_floor` with its required `dtype_byte_orders` | §3.3 |
| Part 05 §5.3, the features an outside-floor finding names | revise in place | same section | a v2 finding names `dtype` where the byte order is outside the floor | §3.4 |
| Part 10 §5, the five-implementation table and the sentence on Zarr v2 | revise the informative table | same section | carries the big-endian rows of §2.2 | none |

## 2. Background

### 2.1 The v3 floor already admits either byte order

Part 03 §6.4's v3 floor is a list of codec patterns, each beginning with `{"name": "bytes"}`. Its
matching rule compares only the configuration members a pattern states, and a pattern stated by name
alone states none. A `bytes` codec configured `endian: big` therefore matches the floor, and the
same section obliges a conforming reader to expose the logical values of every valid v3 array whose
pipeline matches it. A rule that an array be little-endian would contradict a floor the parts already
state.

### 2.2 Two of five probed readers do not decode a big-endian v2 array

The Zarr conformance probe under `conformance/zarr-probe/` writes one 2000 by 384 `int16` array five
ways with zarr-python and records its int64 element sum, -365,664. The sum of the same bytes read
without swapping differs, so a reader that ignores the declared byte order reports a wrong sum. Each
reader's script compares its own sum with the recorded one. The run was made on 2026-10-01 with
zarr-python 3.4.0 and numcodecs 0.17.0, TensorStore 0.1.85, zarrs-python 0.2.3, Zarr.jl 0.10.2 on
Julia 1.12.7, and zarrita 0.7.5 on Node 22.22.2.

| stored array | zarr-python | TensorStore | zarrs | Zarr.jl | zarrita |
|---|---|---|---|---|---|
| v3, `bytes` big-endian, `int16` | reads | reads | reads | reads | reads |
| v3, `bytes` big-endian then `zstd`, `int16` | reads | reads | reads | reads | reads |
| v3, `sharding_indexed` around `bytes` big-endian then `zstd`, `int16` | reads | reads | reads | reads | reads |
| v3, `bytes` big-endian, `float32` | reads | reads | reads | reads | reads |
| v2, `dtype` `>i2`, compressor `zstd` | reads | reads | refuses | wrong values | reads |

The last row is inside the current v2 floor: its `filters` are null and its compressor is `zstd`.
zarrs-python refuses it with "Non-native byte order not supported". Zarr.jl returns a sum of
-2,964,480 and raises no error, so its caller receives wrong values.

### 2.3 The Zarr specifications require `fill_value`

The Zarr v3 core specification lists `fill_value` among the members an array's metadata document
contains, and the Zarr v2 storage specification lists it among the keys of `.zarray`, where its
value may be null. Part 03 §12 names both as normative references. Part 03 §6.4 classes metadata the
applicable Zarr specification makes invalid as upstream invalidity, and Part 03 §6.1 requires a
packet-owned array to be Zarr v3. A packet-owned array whose metadata lacks `fill_value` is
therefore not a Zarr v3 array, and R3 §7.1's sentence adds nothing to that.

### 2.4 Alternatives

Restoring both sentences to Part 03 §6.1 would make a packet that references a big-endian array
non-conforming over external bytes its writer cannot change (Part 03 §8.2), and would exclude v3
arrays every probed reader decodes. Superseding the sentences and leaving the v2 floor alone keeps
an obligation that zarrs-python refuses and Zarr.jl answers wrongly. Narrowing the v3 floor to a
little-endian `bytes` codec has no measurement behind it.

The byte-order bound is a member of the v2 floor and not a member of each metadata pattern. A
pattern's members compare equal with the metadata's, and a byte order is the first character of a
type string, which equality cannot state. The member lists that character as the Zarr v2 storage
specification writes it, so the comparison needs no translation between two vocabularies.

The member is required. A floor that could omit it would need a rule for what omission admits, and
the one descriptor that declares a v2 floor states the bound.

### 2.5 Feasibility

The schema of §3.3 was evaluated with a Draft 2020-12 validator against the descriptor at the
baseline commit. The descriptor of §3.2 passes. The schema refuses the current descriptor, a v2
floor without `dtype_byte_orders`, an empty list, a list naming `=`, and the member on the v3 floor.

R137 and R154 each advanced the schema identifier and kept the profile identifier, so a packet's
recorded `profile_id` has not changed with the floor before.

## 3. Decision

The subsections state what the profile leaves to the Zarr specifications, the v2 reader floor, the
descriptor schema, and the finding for an array outside the floor.

### 3.1 The profile fixes no byte order and adds no `fill_value` requirement

A writer MAY store an array in either byte order. In Zarr v3 the byte order is the `bytes` codec's
`endian` configuration, and in Zarr v2 it is the first character of each type string of `dtype`.

The applicable Zarr specification alone decides which members an array's metadata document requires.
A metadata document lacking a member that specification requires, `fill_value` among them, is
upstream invalidity under Part 03 §6.4, and this profile states no separate requirement of that
member.

R3 §7.1's requirements that an array be little-endian and that `fill_value` be set explicitly no
longer bind.

### 3.2 The v2 reader floor admits a data type that is little-endian or has no byte order

A **type string** of a Zarr v2 array is its `dtype` where that is a string. Where `dtype` is a
structured type, the array's type strings are those of each field's data type, taken recursively
where a field's data type is itself structured. The Zarr v2 storage specification makes the first
character of a type string its byte order: `<` for little-endian, `>` for big-endian, and `|` for a
type that has none.

A valid v2 array is inside the v2 reader floor when both of the following hold:

- its `filters` and `compressor` match one of the floor's `metadata_patterns`, under Part 03 §6.4's
  rule for a v2 pattern; and
- the first character of every one of its type strings is a member of the floor's
  `dtype_byte_orders`.

Any other valid v2 array is outside the floor. The descriptor's
`interfaces.zarr.variants.v2.reader_floor` is exactly:

```json
{
  "metadata_patterns": [
    {"filters": null, "compressor": null},
    {"filters": null, "compressor": {"id": "zstd"}},
    {"filters": null, "compressor": {"id": "blosc", "cname": "zstd"}}
  ],
  "dtype_byte_orders": ["<", "|"]
}
```

A reader or validator comparing a v2 array's metadata with the floor MUST apply these rules.

### 3.3 The descriptor schema

The physical-profile schema's `$id`, and the `$schema` value it requires of a descriptor, are
`https://escapewheel.org/schemas/physical-profile/0.4.0`, and the portable descriptor's `$schema`
names it. Part 03 §1 states the identifier. The profile identifier remains
`escapewheel-portable-v0.1`.

The schema's `zarr_v2_floor` is a closed object requiring `metadata_patterns`, unchanged, and
`dtype_byte_orders`, declared as:

```json
"dtype_byte_orders": {
  "type": "array",
  "minItems": 1,
  "uniqueItems": true,
  "items": {"enum": ["<", ">", "|"]}
}
```

### 3.4 The outside-floor finding names `dtype`

For a Zarr v2 array outside its floor, the observed features that the finding
`physical.outside_reader_floor` names under Part 05 §5.3 are:

- `filters` and `compressor`, where they match no metadata pattern; and
- `dtype`, where a type string's first character is not a member of `dtype_byte_orders`.

A validator MUST name both where both hold, in the one finding it reports for the resource. The
finding's level and attribution are those Part 05 §5.3 already gives it.

## 4. What this does not change

The Zarr floor stays reader-only, so an array outside it stays valid and its packet conforming. A
reader that cannot decode an array's byte order still fails that resource under Part 03 §6.1 and
returns no values for it. The v3 floor and its matching rule are unchanged, and no v3 array moves
into or out of the floor.

## 5. Consequence

Every existing packet conforms unchanged. No packet's bytes, manifest or `profile_id` changes, so no
amendment's identity changes. A packet that references a big-endian v2 array gains one `info`
finding, or one more named feature in the finding it already draws. The conformance corpus
references no v2 array.

Reader obligations shrink: a conforming reader need no longer decode a big-endian v2 array. Writer
obligations are unchanged, since a build writes v3 arrays and a v2 array is external only.

A descriptor naming schema 0.3.0 fails the checker's `$schema` comparison, as R154 §3.5 made a 0.2.0
descriptor fail, so every distributed copy regenerates with the schema.

R3 §7.1 keeps the disposition `applied` at Part 03 §6.1 for its version, chunk-grid and `transpose`
sentences, with a note that §3.1 supersedes its byte-order and `fill_value` sentences. R129 §3.4 and
R137 §3.3 gain notes that §§3.2 and 3.3 add the byte-order bound to the v2 floor. R137 §3.5 gains a
note that §3.4 extends the v2 feature list. R154 §3.5 gains a note that §3.3 supersedes its
identifier.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 states no storage property. | None required. |
| logical prose and registry | Unchanged. The registry declares no byte order, and no rule reads array metadata. | None required. |
| physical profiles | Part 03 §6.4 takes §§3.1 and 3.2 and the `zarr_v2_floor` row of §3.3; Part 03 §1 takes §3.3's identifier. The schema requires `dtype_byte_orders` at 0.4.0, and the portable descriptor's v2 floor declares it. Part 03 §6.1 is unchanged. | The registry checker over the descriptor; `evidence/R<N>.json` names the anchors and the schema and descriptor pointers. |
| packet manifest and JSON Schemas | Unchanged. No manifest member states a byte order or a fill value. | None required. |
| validation and import | Part 05 §5.3 takes §3.4. No import rule changes: a build writes v3 arrays. | `evidence/R<N>.json` names the anchor; the cases of §6. |
| extensions | Unchanged. An extension declares no storage property, and its referenced arrays are assessed as core's are. | None required. |
| reader, writer, validator, adapters | The reader's floor test compares a v2 array's type strings with `dtype_byte_orders`, and its vendored schema and descriptor regenerate. The validator reports a big-endian v2 array under the floor finding and names `dtype`; its finding for a packet-owned array without `fill_value` cites the Zarr v3 requirement of Part 03 §6.1 and no rule of this profile about `fill_value`. The writer's output is unchanged, and its documentation stops citing Part 03 §6.1 for byte order and `fill_value`. Adapters are unchanged. | The reader and validator suites; the writer suite unchanged. |
| conformance fixtures and tests | Descriptor-schema cases for §3.3. Matcher vectors for §3.2 from real `.zarray` documents. A referenced v2 array of each byte order in the corpus or the validator's suite. | `fixtures/corpus.py`, the reader and validator suites, and the registry checker. |
| revision process and tooling | The ordinary ledger and evidence records, and the notes on R3 §7.1, R129 §3.4, R137 §§3.3 and 3.5, and R154 §3.5. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | Part 10 §5's table carries §2.2's rows, and its sentence on Zarr v2 says which byte order was read. The combined specification regenerates. The probe's README names this revision beside R137. | `verify.py`. |

## 6. Conformance and implementation evidence

§§3.1 and 3.2 are `applied` at Part 03 §6.4, §3.3 at Part 03 §§1 and 6.4, and §3.4 at Part 05 §5.3,
each by canonical anchor. The descriptor and schema are evidence owners of §§3.2 and 3.3.

These cases distinguish the new rules from the current ones:

- the portable descriptor with `dtype_byte_orders` passes schema 0.4.0, where the current schema
  refuses the member;
- a descriptor naming schema 0.3.0, a v2 floor without the member, an empty list, and a list naming
  a character other than `<`, `>` and `|` are each refused;
- a v2 array with `dtype` `>i2` and compressor `zstd` is outside the floor and draws
  `physical.outside_reader_floor` at `info` naming `dtype`, where it is inside the floor now and
  draws nothing;
- the same array with `dtype` `<i2`, and one with `dtype` `|u1`, are inside the floor and draw
  nothing;
- a v2 array with a structured `dtype` holding one `>f4` field is outside the floor;
- a v2 array with `dtype` `>i2` and a `lz4` compressor draws one finding naming `filters`,
  `compressor` and `dtype`; and
- a v3 array whose `bytes` codec is configured `endian: big` is inside the floor, as it is now.

The probe's big-endian set under `conformance/zarr-probe/endian/` stays as the measurement of §2.2.

# R3 — Cross-Language Physical Floor

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02_core_logical_schemas.md`, `03_portable_physical_profile.md`, `04_packet_catalog_manifest.md`, `09_metadata_minimalism_and_extensions.md` |
| **Depends on** | R1 (single-session primary) |
| **Forces** | R5 (flat spike representation) — see §4 |
| **Defers** | Downstream edits to `04` §canonical_representations, `06`, `07` — to R5 |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

No migration path is required. Nothing implements this specification and no packets exist.

## 1. Motivation

`00_architecture.md:9` lists "not locked into Python" as a design goal. Nothing downstream
enforces it: no second language is named anywhere in the specification, and the physical
encoding rules amount to a single line — `03:104`, "Compression SHOULD be Zstd when
available."

This project targets Python and Julia as first-class analysis clients. That makes the
physical floor a conformance surface rather than an implementation detail: a packet that
one language cannot read is not portable, however well it conforms logically.

This revision defines that floor. It does not change any semantic concept.

## 2. Parquet type floor

### 2.1 Normative

Core and analysis tables MUST NOT use Parquet nested types. Every column MUST be a
primitive: string, int32, int64, float32, float64, bool, date, or timestamp. These
Arrow-compatible names are the vocabulary in which the schema registry states required
column types; NumPy dtype strings (`<i2`, `|b1`) MUST NOT be used, being Python-specific
and encoding endianness in-band.

Array data types are not specified here. A Zarr array declares its own
`data_type` and both target languages read it identically (§7.3), so the specification has
nothing to add: no table restates it (§3.0), and whether a given array is int16 or float32
is an acquisition choice, not a conformance question.

`struct`, `map`, and `list` MUST NOT appear in any column of any table in the portable
profile. The alternative permitted at `02:52` — choosing between nested types and JSON
strings per implementation — is withdrawn: it makes physical type an implementation
choice, so two conforming packets can require different reader code paths.

Semi-structured values MUST be UTF-8 JSON strings, and MUST be confined to optional
columns. A conforming reader MUST be able to satisfy every required column without a JSON
parser.

**Wall-clock columns only.** The rules in this subsection governing `timestamp` and `date`
apply exclusively to wall-clock and calendar columns — `session_start_time`, `started_at`,
`ended_at`, `created_at`, `modified_at`, `date_of_birth`. They do not apply to experimental
time. Every `*_tick` column is a plain `int64` on a declared `clock_id`, with no timezone,
epoch, or calendar semantics of any kind. The two systems are disjoint and MUST NOT be
mixed: nothing that aligns data uses a timestamp, and nothing administrative uses a tick.

Tick columns MUST be **signed** `int64`. Signed, because `05:131` contemplates negative
ticks ("spike ticks are nonnegative or justified by clock origin"), so `uint64` is wrong
despite its larger positive range. `int64` rather than a narrower width because `int32`
overflows inside a normal recording — 19.9 h at 30 kHz, 11.9 h at 50 kHz, 36 min at 1 MHz —
and does so without error, since a wrapped tick is still a valid integer. Measured, `int64`
tick columns are no larger than `int32` and are smaller in the case tested, because sorted
values leave leading zero bytes that compress (§7.3).

Writers SHOULD encode tick columns with `DELTA_BINARY_PACKED`, and SHOULD NOT
dictionary-encode them. On a high-cardinality tick column the writer builds a dictionary
nearly as large as the column, abandons it on reaching its size threshold, and emits a mix
of partial dictionary and plain pages larger than either encoding alone (§7.3).

Wall-clock timestamps MUST be stored as Parquet `TIMESTAMP` with `isAdjustedToUTC=true` and
`MICROS` precision. The legacy `INT96` representation MUST NOT be used. Dates MUST be
Parquet `DATE` (int32 days since the Unix epoch).

Readers MUST support the Parquet compressions uncompressed, Snappy, Gzip, and Zstd. Writers
MUST use one of those four, and SHOULD use Zstd. Dictionary, RLE, and delta encodings MAY
be used and MUST be supported by readers.

### 2.2 Columns affected

| Table | Column | Current | Becomes |
|---|---|---|---|
| `core.sessions` | `experimenter` | `list<string>` | `core.session_experimenters` (§3.1) |
| `core.trials` | `tags` | `list<string>` | `core.trial_tags` (§3.2) |
| `core.array_assets` | `shape` | `list<int64>` | removed (§3.0, §3.3) |
| `core.array_assets` | `dimension_names` | `list<string>` | `core.array_dimensions` (§3.3) |
| `core.array_assets` | `dtype` | `string` | removed (§3.0) |
| `core.clocks` | `transform_to_parent` | `struct/map/json` | typed columns (§3.4) |
| `core.unit_spike_chunks` | `spike_ticks` | `list<int64>` | *table withdrawn entirely* (§4) |
| `core.events` | `payload` | `struct/map/json` | `json_string` |
| `core.sorting_runs`, `core.processing_runs` | `parameters` | `struct/map/json` | `json_string` |
| all tables | `metadata` | `struct/map/json` | `json_string` |

### 2.3 Rationale

`map` support is uneven across language bindings, and a `struct` whose fields vary between
sessions produces incompatible Parquet schemas that break multi-file dataset reads. Both
risks are structural, not incidental.

`list` is core Parquet and supported in Arrow C++, pyarrow, and DuckDB. It is nonetheless
excluded. Measured (§7.3), Parquet2.jl — the only working native Julia Parquet reader —
cannot read a list column at any compression, while reading primitive columns from the same
writer. One list column therefore routes every Julia reader through DuckDB.

DuckDB is a supported Julia path, but requiring it for any table read narrows "readable
without a server", and a reader cannot determine the constraint before failing.

A uniform "every column is a primitive" rule is also a lower implementation floor than
"primitives, plus lists, except not maps or structs", and the columns that used lists are
modelled as relations (§3) or as a flat table (§4).

## 3. Table/array metadata boundary, and normalizations

### 3.0 Principles

Two rules govern §3. Both are stated here so that future fields are decided by rule rather
than case by case.

**Duplication test — a table MUST NOT restate what the data it describes already declares,
unless the duplication buys access that is otherwise unavailable.**

A duplicated value can disagree with its source. The test is whether reading the source
directly is already cheap. Where it is, the duplication adds a failure mode and no
capability. Where it is not, a validated denormalization is permitted; see §4.

**Multiplicity rule — a field whose semantic type is "zero or more X" MUST be a child
table, keyed on the parent's primary key plus the value. Never a list, never a delimited
string, never JSON.**

Delimited strings admit substring collisions and break on any delimiter occurring within a
value. JSON requires every client to carry a parser to evaluate a filter. Lists are not
readable by Parquet2.jl (§7.3). A child table has none of these properties, costs one
additional file, and makes the value an equality join.

The fields that would otherwise use nested types are relations, so §2.1's prohibition
removes little. R2 carries this rule forward for fields added later.

`03:180` currently requires that "scientific metadata required for packet validation MUST
also be represented in tables or the manifest," to prevent metadata being "trapped only
inside array-store attributes." This is broader than necessary. Measured against the
readers in §7.3:

| Field | Declared by Zarr? | Visible to Zarr.jl? | In a table? |
|---|---|---|---|
| `data_type` | yes | yes, identical string | **no** — redundant |
| `shape` | yes | yes (axis-reversed) | **no** — redundant |
| `dimension_names` | optional, absent by default | **no** | **yes** — nothing else carries it |
| channel → electrode mapping | no | n/a | yes |
| `clock_id`, `sample_rate_hz`, `unit`, `conversion`, `offset` | no | n/a | yes |

A duplicated value is a value that can disagree with the data it describes. Validating
declared dtype against actual dtype checks the table against itself; it cannot detect a
wrong array, only a stale row.

Accordingly `core.array_assets` loses `dtype` and `shape`. It retains `array_asset_id`,
`session_id`, `semantic_type`, `name`, `kind`, `uri`, `format`, `clock_id`,
`sample_rate_hz`, `unit`, `conversion`, and `offset` — none of which the array declares.

The accepted cost: catalog-scale questions ("what dtypes, how large") now require opening
each array's metadata rather than one Parquet scan. Acceptable under R1's single-session
primary case, where a packet holds few arrays.

`09` §4.5 is amended correspondingly: `dtype` and `shape` are struck from the MUST-include
list for array assets.

### 3.1 New table: `core.session_experimenters`

Replaces the `experimenter` list column on `core.sessions`.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session ID. |
| `experimenter` | string | yes | One experimenter. |

Primary key: `(session_id, experimenter)`.
References: `session_id` -> `core.sessions.session_id`.

A session has zero or more experimenters, so §3.0's multiplicity rule applies. A free-text
string is lossy: individuals cannot be recovered reliably from `"Alice Smith, Bob Jones"`,
and any delimiter chosen may occur within a name. Using the same shape as `core.trial_tags`
gives one pattern for repeated values rather than two.

### 3.2 New table: `core.trial_tags`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `session_id` | string | yes | Session ID. |
| `trial_id` | string | yes | Trial ID. |
| `tag` | string | yes | Tag value. |

Primary key: `(session_id, trial_id, tag)`.
References: `(session_id, trial_id)` -> `core.trials`.

A tag is a many-to-one relation and belongs in a table. Delimited strings admit substring
collisions (`good` matching `not_good`); JSON forces every client to carry a parser to
answer a routine filter.

### 3.3 New table: `core.array_dimensions`

Replaces `dimension_names` on `core.array_assets`.

| Field | Type | Required | Description |
|---|---|:---:|---|
| `array_asset_id` | string | yes | Array asset ID. |
| `axis_index` | int64 | yes | 0-based axis position in **stored order** (§5). |
| `dimension_name` | string | yes | Axis name, e.g. `time`, `channel`. |

Primary key: `(array_asset_id, axis_index)`.
References: `array_asset_id` -> `core.array_assets`.

Validation:

- `axis_index` MUST be contiguous from 0 for each array asset.
- Row count per asset MUST equal the rank of the stored array.

Axis lengths are absent per §3.0: the array declares them. Axis names it does not —
`dimension_names` is optional in Zarr v3, absent by default, and not exposed by Zarr.jl
(§7.3).

One row per axis also removes an unvalidated invariant in the base specification, where
`shape[i]` had to correspond to `dimension_names[i]` across two parallel lists with nothing
enforcing the correspondence. `core.array_channels` already normalizes the channel axis on
the same key shape.

### 3.4 `core.clocks.transform_to_parent`

Replaced by typed columns on `core.clocks`:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `transform_slope` | float64 | conditional | Parent ticks per this clock's tick, **as measured**. |
| `transform_offset` | float64 | conditional | Parent-clock tick at this clock's tick 0. |

Both MAY be present. If either is present, both MUST be present. Both MUST be absent when
`parent_clock_id` is absent.

They are NOT required merely because `parent_clock_id` is present: a packet may legitimately
know a clock's parent before any alignment has been measured, which is the state of every
packet imported before synchronization analysis runs.

`transform_slope` is the **measured** ratio, not the nominal one. The nominal ratio is
derivable from the two clocks' declared tick rates, so recording it would duplicate derivable
data, contrary to §3.0. A `transform_slope` differing from the nominal ratio records relative
drift.

Clock alignment is required to interpret a multi-clock session. In JSON it would be
unreachable without a parser, contrary to §2.1's rule that required interpretation not depend
on one.

**Open:** non-linear alignment (piecewise, anchor-point) needs a child table. This revision
does not define one; packets requiring it are out of scope for `nwb-lake-portable-v0.1`.

## 4. Consequence for spike representation

`core.unit_spike_chunks.spike_ticks` is a required `list<int64>` column and is therefore in
violation of §2.1. The rule cannot be adopted without replacing it.

**Decision:** `core.spike_events` — one row per spike, all primitives, sorted by unit —
becomes the sole canonical spike representation. `core.unit_spike_chunks` is withdrawn, and
no chunked form is retained in `core` or `analysis`.

The chunked table's stated justification is compactness (`00:110`). Measured with delta
encoding applied to both forms — for the chunked table via the Parquet child path
`spike_ticks.list.element` — the flat table is 17.45 MB and the chunked table 17.27 MB for
the same 9M spikes, a 1% difference (§7.3). Compactness does not distinguish them.

Access does. Across the three patterns measured the chunked table is slowest in each,
including single-unit retrieval (§7.3). Sort order, not table shape, is the effective lever:
the same flat table sorted by unit rather than by tick differs 10x on single-unit retrieval.
Sorted by unit the flat table is fastest at single-unit and multi-unit retrieval and within
7% of the tick-sorted layout at range selection, so no second representation is required for
the patterns measured. This is the ordering `03:120` already recommends —
`session_id, sorting_run_id, curation_id, unit_id, t_tick` — so that guidance is unchanged. A
packet requiring a tick-optimized access path should materialize a second flat table sorted
by tick, which is also faster than the chunked form on that pattern.

The remaining costs of chunking are structural: chunk size is a free parameter no document
specifies, so importers produce non-comparable packets; three derived columns can disagree
with the data; four validation rules exist only because of chunking; and the
dual-representation mechanism — the spike policy in `02`, `canonical_representations` in
`04`, `analysis.spike_events` in `06`, and the round-trip equivalence tests in `07` — exists
only to reconcile the two forms.

`core.units` SHOULD gain `n_spikes`, `first_spike_tick`, and `last_spike_tick`. These are
derived from `core.spike_events`, and so must satisfy §3.0's duplication test — which they
do: they turn a 9M-row aggregate into a 500-row scan, access a flat table cannot otherwise provide
cheaply. This is the legitimate case §3.0 admits, unlike `core.array_assets.dtype` (§3.0)
where reading the source was already cheap. R5 MUST state the consistency rule; under the
rules-as-data validator it is one anti-join:

```sql
SELECT u.unit_id FROM core_units u
LEFT JOIN (SELECT unit_id, COUNT(*) AS n FROM core_spike_events GROUP BY unit_id) s
  USING (unit_id)
WHERE u.n_spikes IS DISTINCT FROM s.n
```

The full schema surgery — table definitions, deletions, and the downstream edits to `04`,
`06`, and `07` — is deferred to **R5**. This revision records only the decision that §2.1
forces.

## 5. Array axis convention

### 5.1 Normative

`axis_index` in `core.array_dimensions` MUST enumerate axes in **stored order**:
slowest-varying first, matching the `shape` array in the Zarr metadata.

The Zarr v3 `transpose` codec MUST NOT be used in the portable profile, so that stored
order and declared order are always identical.

Readers MUST NOT assume that their language presents axes in declared order. Bindings that
present column-major order enumerate axes in reverse.

Array dimension names MUST be recorded in `core.array_dimensions`. Writers MAY also set
`dimension_names` in the Zarr metadata, but readers MUST NOT depend on it.

### 5.2 Rationale

Measured, not assumed (§7.3). An array written from zarr-python 3.3.0 with shape
`(2000, 384)` opens in Zarr.jl 0.10.2 with size `(384, 2000)`; element-checked, Julia
`a[2,1]` equals Python `data[0,1]`. Zarr.jl reverses axis order to preserve memory layout
without copying, which is correct behaviour for a column-major language.

The stored bytes are unambiguous and both libraries are correct; the divergence is at the
presentation layer and is resolved there. Each client applies its own convention, and a
validator compares its own view of the array's rank and extents against
`core.array_dimensions` accordingly.

Zarr.jl 0.10.2 does not expose `dimension_names` at all: its `MetadataV3` type carries
`zarr_format`, `node_type`, `shape`, `chunks`, `dtype`, `pipeline`, `fill_value`, and
`chunk_key_encoding`, and nothing else. Nor is the field written by default — zarr-python
emits `"dimension_names": null` unless asked. A Julia reader therefore sees a transposed
array with no metadata identifying the axes, which is the case for §3.3.

Clients SHOULD make named axis access the primary array API — `xarray` in Python,
`DimensionalData.jl` in Julia — so that axis position never surfaces to users.

## 6. Index base

No document in the base specification states an index base for any column.

Two kinds of column are currently both called "index":

**Structural indices** address positions in a stored resource. These MUST be 0-based
offsets. Clients converting to 1-based languages MUST convert at the boundary.

- `core.array_channels.channel_index` — position on the array's channel axis
- `core.array_dimensions.axis_index` — position in the array's axis order
- `core.media_frames.frame_index` — position in the media file

**Source labels** are integers copied verbatim from acquisition or sorting software. Their
base is whatever that software used, and some acquisition systems number channels from 1.
These MUST be documented as opaque source-provenance values with undefined base, and MUST
NOT be used as offsets into any packet resource.

- `core.electrodes.local_electrode_index`
- `core.electrodes.local_channel_index`
- `core.units.local_unit_index`

Renaming the source labels to `*_label` is preferable and SHOULD be considered in R5.

(`core.unit_spike_chunks.chunk_index` is withdrawn with its table under §4.)

### 6.1 Binding `core.array_channels` to an axis

`core.array_channels.channel_index` is defined in `02` as "Channel dimension index", but
nothing identifies *which* axis is the channel dimension. `dimension_name` is free text and
no controlled vocabulary requires the channel axis to be named `channel`.

`core.array_channels` MUST therefore gain:

| Field | Type | Required | Description |
|---|---|:---:|---|
| `axis_index` | int64 | yes | Axis that `channel_index` indexes, in stored order. |

References: `(array_asset_id, axis_index)` -> `core.array_dimensions`.

Validation: `channel_index` MUST be within the extent of that axis in the stored array.

## 7. Zarr profile

### 7.1 Version and chunk grid

Arrays MUST be Zarr v3 with a regular chunk grid.

Arrays MUST be little-endian — in Zarr v3 this is the `bytes` codec's `endian`
configuration, not part of the data type. `fill_value` MUST be set explicitly.

`transpose` MUST NOT be used (§5.1).

### 7.2 Codecs

The **baseline** is `none`, `gzip`, and `zstd`. Readers MUST support all three. These are
universally available across Zarr implementations. The baseline is not derived from what the
libraries tested in §7.3 happen to support.

Writers SHOULD use only baseline codecs. A packet written to the baseline opens in any
conforming reader, which is what portability means by default.

Writers MAY use `blosc` with `cname=zstd` and `shuffle=shuffle`, and MAY use the
`sharding_indexed` codec.

The packet manifest MUST declare every Zarr codec used by any array in the packet, in a
top-level `required_codecs` array. The mandatory `bytes` codec is excluded from this list.

```json
{ "required_codecs": ["zstd", "sharding_indexed"] }
```

Readers MUST check `required_codecs` before opening any array, and MUST fail with a message
naming the unsupported codec rather than attempting the read.

This is a declared capability contract. A reader determines from the manifest, before
opening any array, whether it can proceed — the same mechanism as `profile_id`. Under the
withdrawn `02:52` rule a reader could determine a packet's physical encoding only by
inspecting the data.

This amends `04`'s required top-level manifest fields.

### 7.3 Evidence

Produced by [`conformance/zarr-probe/`](../conformance/zarr-probe/); re-run it against
newer library versions before trusting this section. Recorded run: zarr-python 3.3.0,
numcodecs 0.16.5, Zarr.jl 0.10.2, Julia 1.12.0.

Read-back from Zarr.jl, arrays written by zarr-python, all verified by element sum:

| Configuration | Zarr.jl |
|---|---|
| v3 raw, gzip, zstd | reads |
| v3 blosc-zstd-byteshuffle | reads |
| v3 `sharding_indexed` + zstd | reads |
| v2 zstd, v2 blosc-zstd-shuffle | reads |

Sharding and blosc were both initially proposed for exclusion on suspected lack of Julia
support. That suspicion was wrong, and §7.2 permits both.

Datatype surface, same array viewed three ways:

```text
on disk        "data_type": "int16"
Zarr.jl        metadata.dtype = "int16"   (String)
endianness     bytes codec {"endian": "little"}
```

### Parquet, spike tables

9,001,407 spikes, 500 units, 1 h at 30 kHz, zstd throughout. Encoding choice, `t_tick`:

| encoding | total | `t_tick` column |
|---|---:|---:|
| pyarrow default (dictionary on) | 22.83 MB | 2.64 MB |
| dictionary off | 20.50 MB | 2.38 MB |
| **`DELTA_BINARY_PACKED`** | **17.34 MB** | **2.01 MB** |

The default is the worst of the three. `DELTA_BINARY_PACKED` is supported but never chosen
automatically; on a nested column it must be addressed by child path
(`spike_ticks.list.element`), and naming the column alone is silently ignored.

Width, same column: `int32` 33.56 MB against `int64` 20.48 MB — the wider type is smaller,
both `PLAIN`, the difference being zstd on leading zero bytes.

Representation, delta applied to both: flat 17.45 MB, chunked 17.27 MB. Access, via DuckDB:

| access pattern | flat by unit | flat by time | chunked |
|---|---:|---:|---:|
| retrieve 1 unit's train | **4.7 ms** | 46.7 ms | 12.0 ms |
| retrieve 10 units' trains | **24.1 ms** | 31.0 ms | 63.7 ms |
| 100 s window, all units | 28.7 ms | **26.9 ms** | 71.3 ms |

Measured on one synthetic session with uniform firing, through DuckDB only. Bursty real
data and direct pyarrow access were not tested.

### Parquet, nested type portability

The same two-column table written by pyarrow 25.0.1, read by each Julia Parquet path.
A primitives-only control isolates the nested type from the codec:

| file | Parquet2.jl 0.2.34 | DuckDB.jl |
|---|---|---|
| primitives, zstd / snappy / uncompressed | reads | reads |
| `list<int64>`, zstd / snappy / uncompressed | **fails, all three** | reads |

Parquet2.jl raises `FieldError: type Nothing has no field meta_data` on every list file and
on none of the primitive files, so the failure is the nested type rather than compression.
DuckDB.jl returns the lists correctly and `UNNEST` works in SQL.

These are single library versions and may change upstream. §2.1 rests partly on this result;
re-run `conformance/parquet-probe/lists.jl` before relaxing that rule.

### Zarr, array compression

Compression measured on realistic data — 30000×384 int16, correlated Gaussian noise with
sparse spike waveforms:

| Codec | Size | Ratio |
|---|---:|---:|
| uncompressed | 23.04 MB | 1.00x |
| gzip-5 | 17.26 MB | 1.33x |
| zstd-3 | 17.29 MB | 1.33x |
| zstd-9 | 16.76 MB | 1.37x |
| **blosc-zstd-byteshuffle** | **15.55 MB** | **1.48x** |
| blosc-zstd-bitshuffle | 23.02 MB | 1.00x |

Byte-shuffle gives roughly 11% over plain zstd on arrays; bitshuffle gives nothing on this
data and SHOULD NOT be used. Extracellular recordings are predominantly noise and compress
poorly; approximately 1.5x is the expected ceiling for any portable codec.

## 8. Rejected alternatives

**Raising the reader baseline to include blosc and `sharding_indexed`.** Would guarantee
every packet opens in every conforming reader, but bases the standard on n=2 — what the two
libraries tested here happen to support. A third implementation would then have to
implement shard-index parsing and link c-blosc merely to conform. §7.2's declaration
mechanism produces a defined failure without raising the floor.

**Retaining an advisory `core.array_assets.dtype`.** Rejected under §3.0. A value that can
disagree with the data it describes buys nothing that opening the array does not.

**Enumerating permitted array data types.** An earlier draft restricted core arrays to a
fixed list and banned `float16`, complex, and raw types. Withdrawn as over-specification:
it prescribes acquisition choices the specification has no stake in, on speculation about
reader support, and `07` explicitly warns against this kind of early over-building. Should
a data type prove a genuine portability risk, it is the same shape of problem as a codec
and gets §7.2's declaration mechanism, not a ban.

**Per-array `storage_order` field.** Recreates the fork this revision removes: every reader
would have to handle both orders. Zarr v3 already fixes storage as C-order, so the
convention can be a constant.

**Flat spike values in a Zarr array with offsets in the table** (the NWB
`spike_times` / `spike_times_index` pattern). Eliminates nested types without a long table,
but splits canonical spike data across two stores that must be kept consistent,
complicating validation and atomic commit. Available later as an analysis-layer
materialization if a hot path needs contiguity; core stays flat.

**Keeping `list<int64>` for `spike_ticks` only.** Defensible on portability grounds — the
type is well supported — but retains chunking's costs (§4) for a compactness gain Parquet's
encoders already provide.

## 9. Open questions

- Zarr.jl against object-store backends. Only local filesystem stores were tested.
- Julia as a *writer* of Zarr v3. Untested; only read paths were exercised.
- Data types other than int16. Untested; if one proves unportable, extend §7.2's
  declaration rather than enumerating permitted types.
- Whether bursty real firing, larger sessions, or direct pyarrow access change §7.3's
  ranking. The flat-sorted-by-unit decision rests on one synthetic session through DuckDB.
  Re-run `conformance/parquet-probe/access.py` against real data before treating it as
  settled for AIND-scale packets. Should a chunked form ever earn its place, it belongs in
  `analysis` with declared lineage per `06`, never in `core`, which would reinstate the
  dual-canonical machinery §4 removes.
- Non-linear clock alignment (§3.4).

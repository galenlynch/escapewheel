# A null identifier says only that a row names nothing

| | |
|---|---|
| **Status** | **Open** |
| **Opened** | 2026-10-02 |
| **Based on** | `c0f9214b88a2b134bf130a37abde0c396fb0b932` |
| **Affects** | a new subsection of Part 02 §6, which gives each presence state and no meaning to a null; Part 01 §§3.12 and 3.17, which give that meaning for one column family; Part 03 §§5.6 and 6.3; the descriptions of `core.devices.parent_device_id`, `core.sessions.source_session_id` and `core.processing_runs.supersedes_run_id`; the core registry version |

## 1. Problem

Core declares 40 nullable columns whose role is `identifier` or `discriminator`, and
`dynamic_foraging` declares one more. Each names something: a row of a packet table, or an entity
outside the packet, such as an atlas structure. Part 02 §6 lets such a column be null and says
nothing of what a null in it means. Part 03 §5.6 says why no part can leave that to the encoding:
a value that is inapplicable, one never recorded and one recorded as unknown all arrive as the same
null.

Some nulls have a stated meaning, and the rest have none:

- Part 01 §§3.12 and 3.17 give the seven `processing_run_id` columns the reading that the packet
  names no producing run, and forbid a consumer to conclude more from it.
- Part 03 §6.3 makes a null `label_id` padding: the position stands for no row. The same section
  selects an axis's coordinate form by which of its form columns are null.
- Part 02 §8.3 calls a row holding neither discriminator value undeterminable, and Part 01 §2.6
  calls a run declaring no scope undeterminable.
- Part 01 §3.18 tells a consumer to report a media asset with no device as unrecorded.
- `core.calibrations.array_asset_id` and four discriminators (`detail_kind` on
  `core.calibrations` and `core.event_streams`, `core.devices.device_kind` and
  `core.processing_runs.scope_kind`) state their nulls in their descriptions or in Part 02 §§8.3
  and 12.3.
- The other 19 columns rely on their descriptions. Three of those descriptions give a null a
  reading that a writer cannot honour, and sixteen give it none or only a hint.

A consumer meeting a null `parent_device_id` cannot tell a device at the root of an attachment
chain from one whose source never stated a parent. Its description claims both readings: "Null at
the root of a chain, or where no source states it." A consumer grouping probes by headstage then
has nothing to act on.

## 2. Evidence

Observed at the baseline commit. Null counts were taken by reading each table's Parquet footer and
column with PyArrow. The population was the 135-packet conformance corpus built at that commit, and
the two session packets for 786867 and 776259. Those two were built at an earlier core version and
have not been rebuilt.

### 2.1 Three descriptions give a null a reading no writer can honour

| column | description | what a writer writes null for |
|---|---|---|
| `core.devices.parent_device_id` | "Null at the root of a chain, or where no source states it." | both cases; the NWB source path writes whatever its attachment map holds, the Open Ephys path a named parent or none |
| `core.sessions.source_session_id` | "Source-system session ID if different." | `session_id` is an assigned `int32`, so "if different" compares a source's identifier with a number the writer chose |
| `core.processing_runs.supersedes_run_id` | "The run this one replaces, if any." | a run the packet does not hold, which a reference cannot name, as well as no run |

Nulls in these columns are common:

| column | 786867 | 776259 | corpus |
|---|---|---|---|
| `parent_device_id` | 4 of 21 | 5 of 20 | 134 of 134 |
| `source_session_id` | 1 of 1 | 1 of 1 | 147 of 147 |

The packet cannot show which reading any of these nulls had.

### 2.2 Sixteen descriptions say little or nothing of a null

Fifteen core descriptions name the referent and nothing more:

- `device_id` on `core.array_assets`, `analysis.array_assets` and `core.probes`;
- `clock_id` on `core.array_assets`, `analysis.array_assets` and `core.media_assets`;
- `core.clocks.parent_clock_id`;
- `core.curation_versions.parent_curation_id`;
- `region_id` on `core.electrode_coordinates` and `core.unit_coordinates`;
- `probe_id` on `core.electrodes`, `core.sorting_runs` and `core.units`;
- `core.sorting_runs.input_array_asset_id`;
- `core.sessions.reference_clock_id`.

`core.event_streams.device_id` says only "where one is identified". The extension's
`dynamic_foraging.trials.block_id` also names its referent and nothing more.

Several of these columns hold many nulls. `region_id` is null on 3,840 of 7,680 electrode
coordinates of 786867 and 4,608 of 8,832 of 776259. It is null on every unit coordinate of both.
The AIND adapter writes a null `region_id` for a position in a frame that is not an atlas. It also
writes one for a position in an atlas frame whose source has no region column. A consumer filtering
units by structure has to treat those two nulls alike, and nothing tells it so.

### 2.3 One null reading already stands, and it is not "none exists"

R161 settled the producing-run case. Part 01 §3.17 now says that an array asset naming no
producing run "states only that the packet names no run that produced the array". It also says
that a consumer must not conclude from it that the array was acquired. Part 01 §3.12 says the same
of an event stream.

That reading is agnostic. A null says that the row names nothing, and it says neither that the
thing does not exist nor that it exists and went unrecorded. Part 01 §3.18's unrecorded media
device and Part 02 §12.3's unrecorded calibration agree with it.

### 2.4 Comparable standards keep one null

BIDS codes missing and non-applicable values as one marker, `n/a`. Arrow and Parquet carry one
validity bit. ISO SQL has one NULL; Codd's two-mark proposal for applicable and inapplicable
absence was never adopted. HL7 FHIR adds a companion `data-absent-reason` code instead of a second
null, and that is the pattern Part 03 §5.6 already rejects in favour of recording the specific
distinguishing fact.

### 2.5 Alternatives

- **Keep the current design.** Three descriptions keep claiming readings no writer honours, and
  every new nullable column is a new chance to omit one.
- **"None exists" as the default.** This is the literal reading of a null as no such thing. It
  contradicts R161's consumer clauses and Part 01 §3.18. It would also oblige a writer to refuse
  whenever a source is silent, so a packet from an NWB file stating no device attachment could not
  be built. The reviewer confirmed it is not the reading meant (§4).
- **A `null_means` attribute on each column.** It would put a meaning into the registry
  meta-schema that Part 00 §2.2 assigns to prose. It would cost a meta-schema version and a version
  of every extension, and it still could not separate an ambiguous column's two cases.
- **A companion reason column.** This is FHIR's `data-absent-reason` pattern. It doubles the
  column set with values adapters mostly cannot fill, and Part 03 §5.6 asks for the specific
  distinguishing fact instead.
- **A writer refuses every null it cannot classify.** This makes silent sources unbuildable, as in
  the "none exists" alternative.
- **Sentinel values or sentinel rows.** Part 03 §5.6 forbids a sentinel value, and a sentinel row
  would be a referent that does not exist.

## 3. Preferred direction

A consumer reading any nullable naming column can tell what its null says without reading the
writer's code. The outcome must:

- keep one null, as Part 03 §5.6 requires;
- agree with the readings R161, Part 03 §6.3 and Part 02 §8.3 already give;
- stay buildable from a source that is silent about a referent; and
- change no row of an existing packet.

### 3.1 A default reading in Part 02, with named exceptions

Part 02 §6 gains a rule for every nullable column whose role is `identifier` or `discriminator`. A
null in such a column says only that the row names nothing in that column. It does not say that
nothing exists to name, nor that something exists and went unrecorded. A consumer must not
conclude either. A consumer that reports the referent reports, for a null, that the packet names
none. This generalises R161's reading, and no checker could verify either obligation, so each is
stated as unchecked.

The default yields where a numbered part gives a column's null another reading. Two exceptions
exist today, and both give the null a positive meaning:

- `label_id` on `core.array_labels` and `analysis.array_labels`: a null states padding (Part 03
  §6.3).
- The coordinate-form columns of `core.array_dimensions` and `analysis.array_dimensions`
  (`clock_id`, `coordinate_array_asset_id` and `coordinate_resource`): a null says the axis does
  not take that form (Part 03 §6.3). Their `depends_on_axis_index` has the role
  `structural_index`, so the rule does not reach it, and its description states its null.

For `label_id` a writer that could not determine which row a position stands for would, by writing
null, assert padding. The preferred direction adds that a writer must refuse the build rather than
do so. The packet cannot show the difference, so this is unchecked too. The waveform builder, the
only writer path producing a null `label_id`, already writes one only for padding. For the form
columns, Part 03 §6.3's form rules already bind the writer and a checker enforces them, so nothing
is added.

Part 02 §8.3's undeterminable discriminator row, Part 01 §2.6's undeterminable run scope and Part
01 §3.18's unrecorded device are not exceptions. Each one names the consequence of a row that names
nothing, and stays where it is.

Three descriptions change because each contradicts the default:

- `parent_device_id` drops "Null at the root of a chain, or where no source states it".
- `source_session_id` becomes the session's identifier in its source system, dropping "if
  different".
- `supersedes_run_id` drops "if any".

The descriptions of the sixteen silent columns stay as they are, since Part 02 §6 then owns their
null. The seven `processing_run_id` descriptions R161 wrote agree with the default and stay too.
Core takes a minor version.

`region_id` takes the default. Whether a frame is an atlas already separates the not-applicable
case, through the frame's own declaration under Part 01 §3.24. Where a consumer needs to separate
"no structure" from "not annotated" within an atlas frame, Part 03 §5.6 says to record the
distinguishing fact. None is proposed here, since no measured source states it.

`dynamic_foraging.trials.block_id` takes the default unless the extension's maintainers state
otherwise in its description. The default needs no extension change. The corpus holds 269 null
`block_id` values in 269 trial rows, and both session packets hold none.

### 3.2 Placement

The reading is a logical fact about a column's values, so it belongs in Part 02 beside presence,
not in Part 03's encoding section or in each Part 01 concept. An ordinary change appends it as a
subsection at the end of Part 02 §6, which takes its own anchor when created. Part 01 §§3.12 and 3.17 keep their concept-specific conclusions
("came off a device as recorded", "was acquired"), which the general rule does not state.

R166 §3.1 added a subsection at the end of Part 02 §6 on a column a table's declaration does not
declare. This rule's subsection follows it. Neither depends on the other's content.

## 4. Questions

1. **Which reading does the default take?** **Answered 2026-10-02: the agnostic one,** that a null
   says only that the row names nothing (§3.1). The reviewer's earlier approval of "null means no
   such thing" was given on a description of it as the reading R161 gave the null producing run,
   which §2.3 shows is the agnostic reading; this answer replaces it.
2. **Do the sixteen silent descriptions restate the default?** **Answered 2026-10-02: no.** Part 02
   owns the rule once, and a reader of the registry alone does not find it there. R161's seven
   descriptions, which already agree with it, stay.
3. **Does the default cover every nullable column, or only naming ones?** **Answered 2026-10-02:
   naming ones only,** the `identifier` and `discriminator` columns. For a data column Part 03 §5.6
   already implies that a null records no value.

No question that would change the decision is open.

## 5. Consequence

| surface | effect |
|---|---|
| semantic prose | Part 01 unchanged: §§3.12, 3.17 and 3.18 agree with the default and keep their concept-specific clauses |
| logical prose and declarations | Part 02 §6 gains the default reading and its exceptions; three core descriptions change; core takes a minor version |
| physical profiles | Part 03 §6.3 gains the writer's refusal for an undetermined `label_id`, or the Part 02 rule names it; §5.6 unchanged |
| packet manifest and JSON Schemas | unchanged: no structure changes |
| validation and import | unchanged: no new check, since no packet distinguishes the readings |
| extension registries | unchanged unless `dynamic_foraging` states a different reading for `block_id` |
| reader, writer, validator, adapters | unchanged: every current writer path already complies; the waveform builder writes a null `label_id` only for padding |
| existing packets | no row changes; packets keep binding their old core version |
| conformance fixtures and tests | corpus regenerates under the new core version; a registry test pins the three new descriptions |
| revision tooling | unchanged |
| documentation | generated column tables pick up the three descriptions |

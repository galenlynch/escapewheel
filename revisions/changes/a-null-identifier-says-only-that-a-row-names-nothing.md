# A null identifier says only that a row names nothing

| | |
|---|---|
| **Status** | **Ready** |
| **Opened** | 2026-10-02 |
| **Based on** | `04da4ef50a6e4066520778be78eaeedce41e7804` |
| **Change form** | structural |
| **Amends** | Part 02 §6, by a new subsection at its end; Part 02 §9.2; Part 03 §6.3; Part 08 §§2 and 3; the core registry |
| **Depends on** | R161 §3.1 and R161 §3.2 (the readings of a null producing run this generalises); R166 §3.1 (the subsection of Part 02 §6 the new one follows); R164 §3.5 (the core registry version at the baseline) |
| **Profile** | all |
| **Decision clauses** | §3.1; §3.2; §3.3; §3.4 |

Section 3 is normative. Sections 1, 2, 4, 5 and 6 are informative.

Normative keywords follow BCP 14.

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
- The other 19 core columns rely on their descriptions. Three of those descriptions give a null a
  reading that a writer cannot honour, and sixteen give it none or only a hint.

A consumer meeting a null `parent_device_id` cannot tell a device at the root of an attachment
chain from one whose source never stated a parent. Its description claims both readings: "Null at
the root of a chain, or where no source states it." A consumer grouping probes by headstage then
has nothing to act on.

This change has Part 02 state what a null in any naming column says, names the readings Part 03
gives instead, adds the writer's side of the padding reading, corrects the three descriptions that
contradict the rule, and advances the core registry version, since the registry's bytes change.

The change is structural because it revises existing sections in place. Part 03 §6.3 gains the
writer's obligation beside the sentence that makes a null `label_id` padding, which is where a
reader of the padding rule looks for it. Part 02 §9.2 restates the core version, and the example
packet of Part 08 §§2 and 3 binds it. The default reading itself is appended as a new subsection.

### 1.1 Structural crosswalk

Every amended section already carries a canonical anchor, so no bootstrap is needed. No section
moves, splits, merges or retires.

| old location or statement | disposition | current or new owner | semantic effect | Decision clause |
|---|---|---|---|---|
| none | add a subsection at the end of Part 02 §6, after §6.1, with its own anchor | the new subsection | a null in a naming column says only that the row names nothing, unless a numbered part gives it another reading | §3.1 |
| Part 03 §6.3, "a null `label_id` stands for no row, which is how a packet states padding" | extend in place | same section | a writer does not write a null `label_id` for a position whose row it could not determine | §3.2 |
| core registry, the descriptions of three columns | revise in place | same declarations | each description stops giving a null a reading of its own | §3.3 |
| Part 02 §9.2, the core registry version | revise in place | same section | the version advances by one minor version | §3.4 |
| Part 08 §§2 and 3, the example packet's core registry version | revise the informative example in place | same sections | none | none |

## 2. Evidence

Observed at the baseline commit. Declarations were read with `escapewheel-dev`. Null counts were
read from each table with the reference reader, over two populations: the 137-packet conformance
corpus that `fixtures/build.py` writes at the baseline, and the session packets for 786867 and
776259, built by the reference writer at core 0.18.0, the version the baseline incorporates.

### 2.1 Three descriptions give a null a reading no writer can honour

| column | description | what a writer writes null for |
|---|---|---|
| `core.devices.parent_device_id` | "Null at the root of a chain, or where no source states it." | both cases; the NWB source path writes whatever its attachment map holds, the Open Ephys path a named parent or none |
| `core.sessions.source_session_id` | "Source-system session ID if different." | every session; no writer path fills the column, and "if different" compares a source's identifier with the `session_id` the writer chose |
| `core.processing_runs.supersedes_run_id` | "The run this one replaces, if any." | a run the packet does not hold, which a reference cannot name, as well as no run |

Nulls in these columns are common:

| column | 786867 | 776259 | corpus |
|---|---|---|---|
| `parent_device_id` | 4 of 21 | 5 of 20 | 136 of 136 |
| `source_session_id` | 1 of 1 | 1 of 1 | 149 of 149 |
| `supersedes_run_id` | 22 of 22 | 26 of 26 | 157 of 157 |

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

`core.event_streams.device_id` says only "where one is identified". Outside core,
`dynamic_foraging.trials.block_id` says how blocks are derived and nothing of a null.

Several of these columns hold many nulls. `region_id` is null on 3,840 of 7,680 electrode
coordinates of 786867 and 4,608 of 8,832 of 776259. It is null on every unit coordinate of both,
4,505 and 6,540 rows. The AIND adapter writes a null `region_id` for a position in a frame that is
not an atlas. It also writes one for a position in an atlas frame whose source holds no region
value. A consumer filtering units by structure has to treat those two nulls alike, and nothing tells
it so. `block_id` is null in all 274 corpus trial rows and in none of the 1,158 trial rows of the
two session packets.

### 2.3 One null reading already stands, and it is not "none exists"

R161 settled the producing-run case. Part 01 §3.17 says that an array asset naming no producing run
"states only that the packet names no run that produced the array". It also says that a consumer
must not conclude from it that the array was acquired. Part 01 §3.12 says the same of an event
stream.

That reading is agnostic. A null says that the row names nothing, and it says neither that the
thing does not exist nor that it exists. Part 01 §3.18's unrecorded media device, Part 02 §12.3's
unrecorded calibration and Part 02 §8.3's specialised row with a null paired value, which "names no
row of that kind", agree with it.

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

### 2.6 Placement and order

The reading is a logical fact about a column's values, so it belongs in Part 02 beside presence,
not in Part 03's encoding section or in each Part 01 concept. Part 01 §§3.12 and 3.17 keep their
concept-specific conclusions ("came off a device as recorded", "was acquired"), which the general
rule does not state. R166 §3.1 added Part 02 §6.1 on a column a declaration does not declare; the
new subsection follows it, and neither depends on the other's content.

R168 also advances the core registry version and touches no section this change amends. §3.4
names no value, so the Decision stands whichever version the incorporated registry carries.

## 3. Decision

The subsections state the reading of a null in a naming column, the writer's side of the padding
reading Part 03 gives instead, the three descriptions that contradicted the reading, and the
registry version. The crosswalk in §1.1 places each.

### 3.1 A null in a naming column says only that the row names nothing

A null in a column whose role is `identifier` or `discriminator` states only that the row names
nothing in that column. It states neither that nothing exists to name nor that something exists
that the row does not name, and a consumer MUST NOT conclude either from the null. A consumer that
reports what such a column names MUST report, for a null, that the packet names nothing there. A
consumer that does not report what the column names owes only the first of these. No checker
verifies either.

This reading holds for such a column whatever registry declares it, except where a numbered part
gives a null in that column another reading. At the baseline Part 03 §6.3 gives the only other
readings: a null `label_id` on `core.array_labels` or `analysis.array_labels` states padding, and a
null `coordinate_resource`, `coordinate_array_asset_id` or `clock_id` on `core.array_dimensions` or
`analysis.array_dimensions` says the axis does not take that coordinate form. A consequence a
numbered part attaches to a row that names nothing, such as an undeterminable discriminator row
(Part 02 §8.3), an undeterminable run scope (Part 01 §2.6) or an unrecorded media device
(Part 01 §3.18), is not another reading and stands.

### 3.2 A writer writes a null `label_id` only for padding

A writer MUST NOT write a null `label_id` for a position of a labelled axis whose row it could not
determine. No checker verifies this, since a packet holds nothing that separates such a position
from padding.

### 3.3 Three descriptions stop giving a null a reading

The core registry declares these three columns with these descriptions. Every other field of each
column stands: type `int32`, presence `nullable`, role `identifier` and identity `assigned`.
`parent_device_id` and `supersedes_run_id` keep their references to their own tables' keys, and
`source_session_id` declares none.

| column | description |
|---|---|
| `core.devices.parent_device_id` | The device this one was attached to -- a probe's headstage, a headstage's connect board. |
| `core.sessions.source_session_id` | Source-system session ID. |
| `core.processing_runs.supersedes_run_id` | The run this one replaces. |

### 3.4 The core registry version advances

The core registry's `registry_version` MUST advance by one minor version from the version the
incorporated registry carries when this change is incorporated. At the baseline that version is
`0.18.0`, which R164 §3.5 assigns. Other open work advances the same identifier, so this change
fixes no order among them. This change alters neither the registry meta-schema, the
registry-contract descriptor nor the rule language.

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

## 5. Consequence

No row of any packet changes, and no packet changes verdict. A packet bound to core 0.18.0 keeps
it until it is rebuilt or amended, and §3.1 governs how a consumer reads it, since the reading is
prose and no declaration it relies on changes. A packet built afterwards binds the new version. The
three descriptions in a packet's embedded registry are the only bytes that differ.

A consumer that read a null `parent_device_id` as a chain's root, a null `source_session_id` as a
source identifier equal to `session_id`, or a null `supersedes_run_id` as a run that replaces none
now has no basis for it. The reference reader draws none of these conclusions.

Every current writer path complies with §3.2: the waveform builder writes a null `label_id` only
for a channel position past a unit's contacts, and the LFP builder writes none. An independent
writer that wrote null for an unresolved position now conforms only by resolving it, declaring the
axis in another form, or not writing the array.

A citation of Part 02 §6 or Part 03 §6.3 keeps resolving: no heading changes, and the incorporation
sweep reads the 77 citers `impact.py` lists for the two sections. An extension declaring a naming
column takes §3.1 with no change to its registry; a different reading for `block_id` or any other
extension column would need a numbered part to state it (Part 00 §2.2), and none is proposed.

R164 §3.5 states the version together with the meta-schema and descriptor, which remain, so its
ledger entry stays as it is. Where a change incorporated before this one advances the version
in a clause that states only the version, that clause's entry becomes `superseded` naming this
change's revision. R161's clauses stay `applied`.

`core.sessions.source_session_id` keeps a contradiction this change does not resolve: its
description names a source system's identifier, which Part 01 §2.1 calls `carried`, while it
declares identity `assigned`, and `session_name` already holds the identifier a source used for the session.
No writer fills it. Retyping or removing the column changes a declaration and is left to a change
of its own.

| surface | required change or reason unchanged | evidence after incorporation |
|---|---|---|
| semantic prose | Unchanged. Part 01 §§3.12, 3.17 and 3.18 agree with §3.1 and keep their concept-specific clauses. | None required. |
| logical prose and registry | A new subsection at the end of Part 02 §6 takes §3.1. The core registry source takes §3.3's descriptions, and Part 02 §9.2 states §3.4's version. The meta-schema, the descriptor and every rule are unchanged. | `evidence/R<N>.json` names the new anchor, `ew-registry-self-description` and the three registry pointers. |
| physical profiles | Part 03 §6.3 takes §3.2. §5.6 is unchanged. | `evidence/R<N>.json` names `ew-array-axis-coordinates`. |
| packet manifest and JSON Schemas | Unchanged. The manifest schema constrains a registry entry's `version` by a pattern and fixes no value. | None required. |
| validation and import | Unchanged. No packet separates the readings §3.1 rules out, and no check can see an undetermined label. | None required. |
| extensions | Unchanged. §3.1 reaches `dynamic_foraging.trials.block_id` with no declaration change, and no extension pins a core version. | `extensions/registries.py check` passes. |
| reader, writer, validator, adapters | The writer's tests and sources that pin core 0.18.0 take the new version. No behaviour changes: every writer path already complies with §3.2, and the reader concludes nothing from a null. | The writer suite; `test_attachments.py`'s padding case. |
| conformance fixtures and tests | The corpus regenerates under the new version with no change of finding. A registry test pins the three descriptions. | `fixtures/corpus.py`; the registry test. |
| revision process and tooling | A ledger entry for each Decision clause and the ordinary evidence record; no existing entry changes unless §5's version case applies. No tool changes. | `ledger.py`, `evidence.py` and `verify.py`. |
| generated publications and developer documentation | The combined specification, the column tables and Part 08's example regenerate. | `verify.py`. |

## 6. Conformance and implementation evidence

§3.1 is `applied` at the new subsection of Part 02 §6, §3.2 at Part 03 §6.3, §3.3 `registry` at the
three column declarations, and §3.4 `applied` at Part 02 §9.2, each by canonical anchor or pointer.

No packet fixture distinguishes §3.1 or §3.2 from the baseline rule: both bind a consumer's or a
writer's conclusion about a null, and a packet holds the same null under either. The distinguishing
evidence is:

- a registry test asserting the three descriptions of §3.3 and that no other field of the three
  columns changed;
- the existing writer test that a label beyond a unit's contacts is null and every other label
  names a row, which §3.2 now requires;
- the core version tests of the writer suite, asserting the new version; and
- `spec/tools/check.py` and `extensions/registries.py check`, passing with no change of column
  count.

# Part 02 — Core Logical Schemas

Normative.

## 1. Scope

This part defines how a logical schema is declared, what a declaration must contain, and which resources the core layer comprises.

The column-level definitions themselves are not written here. They are data (§9), carried in a registry document that a packet embeds and that generates the checks of Part 05. This part is the rules the registry obeys; the registry is the schema.

Two renderings of that registry accompany this specification and are **generated, never edited**: `registry/logical_schemas.json`, which is normative and is what a packet embeds, and `registry/tables.md`, a human-readable listing of every table and column with the revision that introduced each (§9.4). Where this part and a rendering disagree, this part states the rule and the rendering states the current content.

## 2. Table resource requirements

Every table resource MUST declare:

- a schema identifier;
- an ordered list of columns, each conforming to §3;
- a primary key, or `null` with a stated reason (R7 §2);
- its references to other tables (§7);
- its Tier 2 validation rules, if any (§10.2).

## 3. Column declaration

Every column MUST declare a name, a type, a presence, and a role. It MAY declare an identity, a vocabulary, a unit, a clock, and the revision that introduced it.

| attribute | required | clause |
|---|---|---|
| `name` | yes | §4 |
| `type` | yes | §5 |
| `presence` | yes | §6 |
| `role` | yes | §8.1 |
| `identity` | for identifiers | §8.2 |
| `enum` | for closed vocabularies | §9.3 |
| `resolves`, `discriminates` | for discriminators | §8.3 |
| `unit`, `unit_from`, `clock_from` | where applicable | §8.4 |
| `since` | recommended | §9.4 |

## 4. Naming

Column names MUST be lowercase snake case.

| suffix | use |
|---|---|
| `_id` | a stable identifier |
| `_name` | the name an assigned identifier was assigned from |
| `_tick` | a tick coordinate on a declared clock |
| `_uri`, or bare `uri` | a URI |
| `_index` | a zero-based offset into a sequence |

A name is a property of the registry rather than of any packet's rows, so naming is checked against the declaration and not by a validation rule (R48 §4). An exception MUST be declared with a reason.

A source-provenance label — `local_electrode_label`, `local_channel_label`, `local_unit_label` — is a `string` carrying whatever base the producing software used, and MUST NOT be used as an offset into any packet resource (R5 §5, R8 §2).

## 5. Type system

### 5.1 Permitted types

A column's type MUST be one of:

```text
string  int32  int64  float32  float64  bool  timestamp  date  json_string
```

### 5.2 No nested types

`list`, `struct`, and `map` MUST NOT be used (R3 §2.1). A repeated value becomes a child table; a semi-structured value becomes a `json_string` in an optional column.

This keeps a conforming reader able to satisfy every required column without a JSON parser, and keeps a native reader viable in a language without an embedded SQL engine.

A writer SHOULD NOT fill a `json_string` column routinely. Doing so defeats that guarantee in practice: a column present on every row forces a parse on every row, in exactly the table where a consumer works. A value that varies per row and is queried belongs in a typed column of a specialising resource; a value constant across the table belongs once, on the table that owns the whole.

### 5.3 Fixed representations

A writer MUST NOT use wraparound, truncating or saturating semantics for a value whose role is `identifier`, `coordinate`, `structural_index` or `sequence_position`, nor for arithmetic over interval bounds. A conversion whose result would fall outside the declared type MUST fail before the value is written, naming the column and the value (R76 §2.1). A validator is not required to re-derive this: a wrapped value is a valid value of its type and the evidence is gone by the time rules run.

Tick columns MUST be `int64`. Wall-clock columns MUST be `timestamp` with microsecond precision in UTC, and MUST NOT use INT96. Identifier columns MUST be `int32` (R53 §2.1), except where the number of distinct values may exceed `int32`, where the column MUST be `int64` (R53 §2.4). No core table is near that bound; an extension declaring an identifier over more than 2^31 rows declares `int64` for it.

## 6. Presence

A column is `required`, `nullable` or `optional` (R2 §5):

| state | the column | its values |
|---|---|---|
| `required` | MUST be present | MUST be non-null in every row |
| `nullable` | MUST be present | MAY be null |
| `optional` | MAY be absent | MAY be null where present |

The third state is what R3 §2.1 confines a `json_string` to: a conforming reader must be able to
satisfy every required column without a JSON parser, so a column holding JSON is never required.

A present nullable column is preferred to an absent one, because a stable column set simplifies query code. A schema MUST NOT declare a column that duplicates what the data already declares: `core.array_assets` carries no dtype or shape, because the array declares them (R3 §3.0).

Duplication is permitted only where it buys otherwise-unavailable access. Axis names are carried in `core.array_dimensions` because a Zarr binding in another language cannot see them.

## 7. References

A table declares each foreign key as a reference naming the target resource, this table's columns, and the target's columns. A reference MAY be composite, nullable, or self-referencing (R46 §2).

A reference MUST relate columns of the same role, and of the same identity where both are identifiers. Relating an assigned identifier to a carried one resolves to nothing.

### 7.1 Session scope

A table is **session-scoped** where it reaches `core.sessions` through its declared references, directly or transitively (R86 §2.1). That is a property of the registry, computable with no packet in hand.

A session-scoped table MUST carry a `session_id` column — `int32`, required, role `identifier`, identity `assigned` — and MUST declare the reference `session_id` → `core.sessions.session_id` (R88 §2.1, §2.2). A table that does not reach `core.sessions` MUST NOT carry one; `core.subjects` and `core.source_files` are the two, which `core.sessions` references rather than the reverse.

Carrying the column without the reference is what the rule forbids: Tier 1 generates one anti-join per declared reference and nothing from a column's name, so an undeclared `session_id` is a foreign key no rule can see.

## 8. Column semantics

### 8.1 Role

Every column MUST declare exactly one role, from a closed vocabulary with no default (R48 §2.1, R90 §3.1):

| role | meaning |
|---|---|
| `data` | a value to be read |
| `identifier` | a stable identity, per §8.2 |
| `coordinate` | a position on an axis, such as a tick |
| `structural_index` | a zero-based offset into a stored sequence |
| `sequence_position` | an ordinal within an ordered set |
| `discriminator` | a value naming the resource another column resolves against |

The role is what makes index-base conversion derivable from a packet rather than hard-coded in each one-based client (R3 §6). A `structural_index` converts at the client boundary; a `coordinate` does not.

### 8.1.1 Index base

A **structural index** addresses a position in a stored resource and MUST be a **0-based offset**. A client converting to a 1-based language MUST convert at the boundary (R3 §6); the format picks one base and clients adapt, because an offset whose base changes per reader is not an offset.

A **source label** is copied verbatim from acquisition or sorting software. Its base is whatever that software used, and it MUST NOT be used as an offset into any packet resource.

A **coordinate** is neither: copied verbatim like a source label, but used arithmetically, which a source label MUST NOT be (R45 §2.5). Its zero is where its clock's origin says it is.

Because a reference relates columns of the same role (§7), converting every structural index at a boundary is join-preserving by construction.

### 8.2 Identity

An `identifier` column MUST declare `carried` or `assigned` (R53 §2.3). A table owning an assigned identifier MUST carry the corresponding `*_name` column.

A `carried` identifier gets no name column and MUST NOT be given one: the value is already the source's own, so a name beside it would be a second identity for one thing.

An assigned identifier's `*_name` MUST be unique within its packet (R85 §2.2) — the 16 name columns in core and analysis that pair with one, not the 6 that name a kind of thing and are expected to repeat, such as `core.sorting_runs.sorter_name`. `registry/check.py` sorts them and requires the second kind to be declared. No rule can check it: a writer numbering an assigned identifier per distinct name emits one row per name, so two things wrongly sharing one are already merged by the time the packet exists — and that merge is indistinguishable from the correct one R67 §2.2 requires, where four streams naming one serial become one device. The obligation falls on whatever composes the name.

### 8.3 Discriminator

A `discriminator` column MUST be a `string` holding a dotted resource identifier — a namespace and
a table name, each lowercase snake_case — naming a table in the packet's registry or in one of its
extensions (R90 §3.1).

**Which column carries it.** A discriminator MAY be declared on the table whose rows it
specialises, or on a table those rows reach through one declared reference. Where it is not on the
specialised table it MUST declare `discriminates_via`, holding the referencing column as a dotted
`resource.column`; one reference and no more (R90 §3.2).

A column carrying a discriminator's value as part of a shared key is **not** a discriminator and
MUST NOT declare the role: it resolves nothing a consumer of that row does not already know. Such a
column is `data`, and a reference relating it to the discriminator it copies is the one role
mismatch a reference may carry (R90 §3.3).

**Whether it must resolve.** A discriminator MUST declare `resolves`, required and with no default:

| `resolves` | an unresolvable value is |
|---|---|
| `required` | a defect: the row is uninterpretable |
| `optional` | a fact: the packet does not hold that resource |

Where a discriminator is paired with a value column, both are nullable and the two MUST agree — a
row declares both or neither (R49 §2.4). A row declaring neither is **undeterminable**, which a
consumer MUST report apart from a row whose value resolves to nothing: the fix for one is to record
the missing half, and for the other to correct what it names.

**How it resolves.** A reader SHOULD offer the resolution: read the kind, take that resource's key
from the registry, join. A discriminator nothing reads is a free-form name with extra steps, which
is the observed fate of the mechanism this one replaces. Three shapes exist (R90 §3.5):

- **Shared key.** The discriminated row and the named resource share a key, so the join is on that
  key. A resource a shared-key discriminator may name MUST declare a reference back to the
  discriminated table, and that reference MUST cover the discriminated table's **whole key**. A
  reference on part of it targets a set that is not unique — it identifies a row of some kind,
  which is not a foreign key, and the generated anti-join passes while resolving to several rows.
  A detail table therefore carries the discriminator's value as a constant column, restating in
  every row what its own identity implies; a column holding one value costs almost nothing once
  encoded, and what it buys is a reference that identifies a row. The reference runs extension →
  core, so a discriminator names downward while the integrity constraint points upward.
- **Paired value.** A separate column holds an identifier in the named resource's key space, and
  the discriminator MUST declare `discriminates` naming that column. A paired value holds one
  identifier, so the named resource's primary key MUST be a single column, and the value MUST be a
  `string` matching that key where it is `carried` or its `*_name` where it is `assigned`.
- **By position.** The named resource's rows are the positions the discriminated column indexes,
  located by a column that resource declares. Resolution is neither a key join nor a value-to-key
  join, so the joinability rules above do not apply and MUST NOT be read as applying.

**What is generated.** Where `resolves` is `required`, two checks follow from the structure: a
forward anti-join against the resources the manifest declares, and a reverse check per named kind
returning every row of the discriminating table whose key has no counterpart in the resource its
discriminator names, both at **error**. The reverse check is generated over the kinds a packet's
rows actually name, and applies to the shared-key shape alone. Where `resolves` is `optional`,
neither is generated and an unresolvable value is reported as `info` (R90 §3.8).

Every generated check MUST be built over **every resource the packet declares, extensions
included**. Building them over core alone is the defect R55 was written for: an extension kind
matched no branch and passed in silence, which is the one case the mechanism exists to cover.

Core MAY name an extension's resource through a discriminator. It MUST NOT reference one: naming
does not create a dependency, so core stays checkable alone, an absent target is a reportable fact,
and no integrity constraint couples the versions (R90 §3.9).

### 8.4 Unit and clock

A `data` column carrying a physical quantity SHOULD declare its `unit`, or `unit_from` naming a column that carries it (R77 §2.2). A `coordinate` column MUST declare `clock_from` where the clock its ticks are on is not the one that row's `clock_id` names, and MUST declare it where the table has no `clock_id` at all (R77 §2.1). Measured across the registry, 6 of 20 coordinates declare one and the other 14 resolve to their own row's clock; none has neither.

`clock_from` names a column of the same table or a one-hop `resource.column`. A consumer resolves it rather than guessing, because converting on the wrong clock fails silently.

A consumer MAY label a quantity with its declared unit, and MUST NOT silently compare or combine two columns whose declared units differ (R56 §2.5).

## 9. The registry

### 9.1 The schema is one document

Table structure and validation rules are carried in one JSON document (R2 §2). It declares the semantic and logical standard versions, its own registry version, and its tables.

### 9.2 Self-description

A packet MUST record the registry version it was written against and SHOULD embed the registry itself, so the packet stays readable as the reference registry moves on (R2 §8). A packet whose embedded registry disagrees with its recorded version is invalid.

A registry document SHOULD carry a top-level `$schema` naming its meta-schema (R57 §2.1). A
validator MUST NOT dereference it and MUST NOT require it.

Where `$schema` is present it MUST equal the `$id` of a meta-schema the consumer holds, or the
document MUST be reported as governed by a schema this consumer does not have — an **`info`**
finding, not an error (R57 §2.2). R17 §4 already says a core validator is not required to hold an
extension's schema, and the same reasoning applies one level up.

### 9.3 Vocabularies

A vocabulary is open unless the column declares `enum`. A validator MUST reject a value outside a declared `enum`, and MUST NOT reject an unrecognized value from an open one (R8 §4).

Three columns are closed:

| column | values |
|---|---|
| `core.processing_runs.status` | `succeeded`, `failed`, `partial` |
| `core.units.quality_label` | `sua`, `mua`, `noise` |
| `core.unit_quality_labels.normalized_label` | `sua`, `mua`, `noise` |

A scorer's own `label` is open, because aggregating over scorers is incompatible with one closed set (R22 §1).

### 9.4 Provenance of a declaration

A table and a column SHOULD each carry `since`, naming the revision that introduced or last changed it (R77 §2.3). The registry stamps both: 15 tables and 172 columns carry one.

A column whose role is declared SHOULD NOT restate its base in its description (R48 §2.5). The role carries it, and prose repeating it is a second statement that can disagree with the first.

## 10. Validation rules

### 10.1 Tier 1: generated from structure

A validator MUST generate, from the declaration alone: required-column non-null checks, primary-key uniqueness, foreign-key anti-joins, and closed-vocabulary membership. A nullable foreign key is guarded with a null test.

Uniqueness need not be checked by query where a table's physical sort begins with its primary key, since duplicates are then adjacent and the ordering scan settles it.

### 10.2 Tier 2: declared

A rule the structure cannot imply is declared as SQL returning offending rows, or as a named template the registry build expands (R24 §2).

The execution contract is the whole protocol: **a check's query returns offending rows; empty is a pass, non-empty is a failure, and the returned rows are the finding.**

A rule declares a level of `error`, `warning`, or `info`. A rule MAY be `advisory`, in which case
it is off by default and MUST NOT be `error`, so that enabling it cannot change whether a packet
previously passed. Stated as the guarantee it is: **running with advisory rules enabled MUST NOT
change whether a packet passed** (R26 §4). A validator MUST expose the choice, and a report MUST state whether
advisory rules were run: two reports over one packet may legitimately differ, and one that does
not say which mode produced it cannot be compared with the other.

### 10.3 What is not a rule

Physical order, file presence, Parquet types, Zarr rank and codecs, and checksums MUST NOT be expressed as SQL (R12 §4). A query cannot observe them, so a storage-layer check written as SQL fails silently rather than loudly. These are checked by the shim of Part 05 §5.3.

## 11. Core resource index

The core layer comprises the following resources. Column definitions are in the registry.

### 11.1 Session and subject

| resource | contents |
|---|---|
| `core.sessions` | one row per session; declares the reference clock and time origin |
| `core.subjects` | one row per subject |
| `core.session_experimenters` | experimenters, one row each |

### 11.2 Instruments

| resource | contents |
|---|---|
| `core.devices` | instruments used, each with the hardware revision and firmware version it ran |
| `core.probes` | devices carrying electrodes |
| `core.electrodes` | recording contacts |
| `core.electrode_coordinates` | a contact's position per frame and basis |
| `core.calibrations` | what was measured about an instrument so its numbers can be read |
| `core.calibration_devices` | the devices each calibration covers |
| `core.calibration_points` | the paired series of a calibration that is a curve |

### 11.3 Time

| resource | contents |
|---|---|
| `core.clocks` | declared counters, their rates, origins, and parents |
| `core.clock_anchors` | anchor pairs mapping a clock onto its parent |
| `core.clock_observation_intervals` | when each clock was observing |

### 11.4 Structure

| resource | contents |
|---|---|
| `core.intervals` | bounded spans, discriminated by kind |
| `core.events` | timestamped observations, one per tick per stream |
| `core.event_streams` | what produced a set of events, and on what clock |
| `core.event_stream_observation_intervals` | a stream's refinement of its clock's window |

### 11.5 Sorting

| resource | contents |
|---|---|
| `core.sorting_runs` | what sorted what, on which clock |
| `core.sorting_run_channels` | the channels a run used, in the order it counted them |
| `core.curation_versions` | named states of a sorting's unit set |
| `core.units` | one row per unit per sorting and curation |
| `core.spike_events` | one row per spike |
| `core.unit_quality_labels` | one row per unit per scorer |
| `core.unit_electrodes` | the contacts a unit sits on |
| `core.unit_coordinates` | a unit's position per frame and basis |
| `core.unit_observation_intervals` | a unit's refinement of its clock's window |

### 11.6 Arrays and media

| resource | contents |
|---|---|
| `core.array_assets` | dense arrays, owned or referenced, each naming the device that made it |
| `core.array_dimensions` | one row per axis, with its coordinates |
| `core.array_channels` | per-channel scaling, shift, and electrode |
| `core.media_assets` | images and video |
| `core.media_frames` | frame timing |

### 11.7 Provenance

| resource | contents |
|---|---|
| `core.source_files` | inputs the packet was built from |
| `core.processing_runs` | activities that produced resources |
| `core.processing_run_inputs` | which files fed which run |
| `core.preferred_runs` | which of several coexisting results to use |

### 11.8 Analysis

| resource | contents |
|---|---|
| `analysis.spike_events` | core spikes on the reference clock, bucketed by time |
| `analysis.array_assets` | derived dense arrays |
| `analysis.array_dimensions` | their axes |

## 12. Rules for particular resources

Sections 2 through 10 bind every table. What follows binds three of them, where identifying a row,
resolving a value, or reading an absence takes more than the generic rules give.

### 12.1 Unit identity

`unit_id` identifies a unit on its own (R81 §2.1). The packet assigns it, numbering units by
ascending `(sorting_run_id, curation_id, local_unit_label)` so a rebuild reproduces the same
numbers (R81 §2.2); `core.units` records the run and the curation as ordinary columns, and
`local_unit_label` records what the sorter called it.

A table keyed on a unit carries `unit_id` and not the run or the curation (R81 §2.3), and a
consumer relating a unit to anything outside the packet uses `(sorting_run_id, local_unit_label)`
(R81 §2.5).

### 12.2 Channel indices in a sorting run

A sorting drops bad channels before it runs, so a channel index a source emits counts the channels
it kept and not the probe's contacts. `core.sorting_run_channels` records that list in the run's
own order (R83 §2.1).

A writer that can read it SHOULD emit the table, MUST NOT derive it from `core.unit_electrodes` or
from a bad-channel list, and SHOULD emit nothing where it cannot read it (R83 §2.2).

A consumer holding such an index MUST resolve it through that table and MUST NOT read it as a
position in `core.electrodes`; where the run declares no channels the index is unresolvable, and
the consumer MUST report that rather than resolve it against the contact list (R83 §2.3).

Where a run declares its channels, every `core.unit_electrodes` row for one of its units MUST name
an electrode among them (R83 §2.4).

### 12.3 Calibration

A calibration is a standing property of an instrument rather than an activity of this packet, so
`core.calibrations` records the session it was **in force** for and, separately, when it was
measured; a consumer MUST NOT read the two as one fact (R89 §2.1). A calibration in force for
several sessions is recorded once per session, as R88 §2.4 requires of any row whose results reach
more than one.

The devices a calibration covers are a child table, since one calibration of the rig's manipulators
is cited by six probes (R89 §2.2); a calibration covering a device the packet does not hold gets no
row there, which is a fact rather than a defect, and a writer that records the calibration SHOULD
record the devices it names.

A paired series is carried as `core.calibration_points`, whose two value columns take their units
of measure from the calibration, since the unit varies per calibration and so cannot be a literal
on either column (R89 §2.3). Content that is an array rather than a curve names the array asset
holding it (R89 §2.4).

A row with no points, no array asset and no detail kind records that the calibration was in force
and that the packet holds nothing further, which a consumer MUST read as **unrecorded** rather than
as absent (R89 §2.5). A source stating that no calibration was performed gets no row at all.

`core.calibrations` declares `metadata` and the two child tables MUST NOT, because its key holds an
identifier of its own where theirs are keyed by other tables' identifiers (R89 §2.6).

## 13. Stored layout

### 13.1 Ordering

A writer SHOULD sort every table by its primary key (R10 §2). No core table overrides this: R81
§2.4 removed the spike table's override by numbering `unit_id` run-major, and R91 §3.2 removed
`core.events`' by keying the table on the order it is stored in. `analysis.spike_events` overrides
it under a MUST, specified in `03` §5.4.

### 13.2 Partitioning

A large table SHOULD be partitioned by `session_id`. A table MUST NOT be partitioned by `unit_id`.

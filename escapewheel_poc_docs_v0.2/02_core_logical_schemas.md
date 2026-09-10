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

A value that varies per row and is queried belongs in a typed column of a specialising resource; a value constant across the table belongs once, on the table that owns the whole. What may go in the two `json_string` columns core declares is §8.6 for `metadata` and §12.6 for `core.processing_runs.parameters`.

### 5.3 Fixed representations

A writer MUST NOT use wraparound, truncating or saturating semantics for a value whose role is `identifier`, `coordinate`, `structural_index` or `sequence_position`, nor for arithmetic over interval bounds. A conversion whose result would fall outside the declared type MUST fail before the value is written, naming the column and the value (R76 §2.1). A validator is not required to re-derive this: a wrapped value is a valid value of its type and the evidence is gone by the time rules run.

Tick columns MUST be `int64`. Wall-clock columns MUST be `timestamp` with microsecond precision in UTC. Identifier columns MUST be `int32` (R53 §2.1), except where the number of distinct values may exceed `int32`, where the column MUST be `int64` (R53 §2.4). No core table is near that bound; an extension declaring an identifier over more than 2^31 rows declares `int64` for it.

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

An `identifier` column MUST declare `carried` or `assigned` (R53 §2.3). A table owning an assigned identifier MUST carry the corresponding `*_name` column, and MUST NOT carry a second column naming the same thing (R95 §3.1). Seven tables carried both a generated `*_name` and a `name` declared by `02`, equal on every row of every packet that wrote them; the `*_name` survives, taking the presence the declared column had.

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
  join, so the joinability rules above do not apply and MUST NOT be read as applying. The
  discriminator MUST declare `positions_in`, naming the column of its own table whose value is that
  position column, and MUST NOT declare it beside `discriminates` (R100 §2.3). Without the
  declaration this shape and the shared key are indistinguishable, and the exclusion above binds a
  reader while a generator reads every discriminator without a paired value as shared-key.

**What is generated.** Where `resolves` is `required`, two checks follow from the structure: a
forward anti-join against the resources the manifest declares, and a reverse check per named kind
returning every row of the discriminating table whose key has no counterpart in the resource its
discriminator names, both at **error**. The reverse check is generated over the kinds a packet's
rows actually name, and applies to the shared-key shape alone. Where `resolves` is `optional`,
neither is generated and an unresolvable value is reported as `info` (R90 §3.8).

A by-position discriminator gets a third instead of the reverse one: the column `positions_in`
names MUST hold a column of the named resource whose role is `structural_index`, and the registry
supplies each named resource's such columns as literals (R100 §2.2). A role is invisible to a
query and visible to whatever writes one.

Every generated check MUST be built over **every resource the packet declares, extensions
included**. Building them over core alone is the defect R55 was written for: an extension kind
matched no branch and passed in silence, which is the one case the mechanism exists to cover.

Core MAY name an extension's resource through a discriminator. It MUST NOT reference one: naming
does not create a dependency, so core stays checkable alone, an absent target is a reportable fact,
and no integrity constraint couples the versions (R90 §3.9).

A row's kind-specific facts live in a table sharing that row's key, which is R54 §2's shape and
R90 §3.5's shared-key join: the detail table's primary key MUST begin with the discriminated
table's own identifier (R104 §3.1). `core.devices` names such a table through `device_kind`, and
core MUST NOT declare one — `01` §3.17 makes this standard name no instruments, so a camera's
target or a thermistor's range belongs to an R17 §2 extension (R104 §3.2). A fact no detail table
models stays in `metadata` (R97 §3.3), and what justifies promoting one out of it is a rule or a
query that has to read it.

### 8.4 Unit and clock

A `data` column carrying a physical quantity SHOULD declare its `unit`, or `unit_from` naming a column that carries it (R77 §2.2). A `coordinate` column MUST declare `clock_from` where the clock its ticks are on is not the one that row's `clock_id` names, and MUST declare it where the table has no `clock_id` at all (R77 §2.1). Measured across the registry, 6 of 20 coordinates declare one and the other 14 resolve to their own row's clock; none has neither.

`clock_from` names a column of the same table or a one-hop `resource.column`. A consumer resolves it rather than guessing, because converting on the wrong clock fails silently.

A column holding a physical unit MUST hold a UCUM code, and a column declaring one MUST declare a UCUM code — an annotation in curly braces is one, and is dimensionless, which is what a quantity normalised by something the packet measured is (R101 §3.6).

A consumer MAY label a quantity with its declared unit, and MUST NOT silently compare or combine two columns whose declared units differ (R56 §2.5). One vocabulary is what makes that rule run: `volts` and `V` differ while naming one unit, so without it the rule refuses a legitimate comparison exactly as readily as it catches a wrong one.

### 8.5 Functional dependence

A column MAY declare `determined_by`, naming the columns whose values fix its own: two rows agreeing on every column named agree on this one, and an empty list declares a constant (R92 §2.2). The declaration is structural, decidable from the registry with no packet in hand.

It is a statement about values and holds under any profile. What a profile does with it is the profile's: `03` §5.3 uses it to decide whether a table's stored order settles its primary key, and requires the scan establishing that order to verify the declaration against rows (R92 §2.3), because a wrong one waives a check rather than failing one.

### 8.6 Free-form metadata

A column named `metadata` is a `json_string` holding what a source stated about a row that this standard does not model, carried in the source's own vocabulary and read by no rule (R97 §3.4). Every declaration carries that description and no other.

A table's registry entry MUST declare `metadata` where its primary key includes an `identifier` column that is not part of a declared reference, MUST NOT declare one where every key column is part of a declared reference, and MAY declare one otherwise (R97 §3.1). An identifier of the table's own is what makes a row a thing rather than a statement about other things; a key made entirely of other tables' identifiers makes it a relationship, and nothing can be said about a relationship that is not a fact about one of its ends. Seventeen core tables fall in the first band and three in the second. Both bounds are decidable from the registry with no packet in hand, and `registry/check.py` enforces both against core and against every extension.

A `metadata` column MUST be declared `optional`, which is what makes R94 §3's prohibition sound: that check matches the bare column name, and so holds only while every column called `metadata` may be absent from the file.

A validator SHOULD report, at `info`, a declared `metadata` column that no row of the packet fills. Where the key neither requires the column nor forbids it, declaring one is a judgement, and this is the evidence against which it is revisited: `core.spike_events` carried the column on 286,896,563 rows that no adapter ever filled.

A writer MAY fill `metadata` on every row of a table that declares it (R97 §3.2). Parquet reads the columns a query projects and no others, so the column costs a consumer who does not ask for it 1.9 kB of extra footer over 5,000,000 rows, and one who does 394.6 ms against 29.6 ms.

A writer MUST NOT emit a `metadata` key holding a fact that a column of the logical schema holds, unless the duplication buys access that is otherwise unavailable, and MUST NOT emit one that contradicts such a column under any circumstance (R97 §3.3). The exception is R3 §3.0's, on the same terms, so the bag is exactly as strict as the schema around it; a contradiction takes no exception, since it buys nothing by definition. A fact required to interpret the data belongs in a column, never in a key.

No rule checks either half and none is added. The content is schemaless by design, so a constraint on it is unenforceable in principle rather than merely in practice, and an adapter names a key in the source's vocabulary where core names a column in its own — across both packaged sessions, zero of the 20 distinct keys share a name with any column in the registry. The obligation binds the writer, which is the only party that knows what it put in the bag.

A writer SHOULD put prose in a prose column where the table has one, and not in `metadata`. A human-readable string has no structure to preserve, so a JSON envelope costs a serialisation, puts the value where no rule reads it and no filter uses it, and buys none of the otherwise-unavailable access the exception above requires.

### 8.7 Coded values

A writer that can decode a source's code MUST store the decoded value, declaring the vocabulary it decodes onto as §9.3 requires of any other (R106 §3.1). A code is a token standing for something the emitting system names elsewhere, and a packet holding one without the key leaves no rule, query or reader able to tell one value from another.

A writer that cannot decode one stores the code itself, verbatim, in a `string` column declaring an open vocabulary, whose description names where the key lives. An undecoded code is a label carrying no contract, and an open vocabulary is how this standard declares one (`01` §3.17); an integer column declares nothing of the sort, since §9.3 permits a vocabulary on no other type and a code stored as an integer is indistinguishable from a count.

Recording the token rather than dropping it is R22 §3's rule for a scorer's label and §4's for a source-provenance label: a source's own token is a string, kept as the source emitted it, and MUST NOT be used as an offset.

No rule checks either half, and none is added. Nothing structural tells a code from a count, so the obligation binds the writer, which is the party that knows whether it had a key.

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

Every `string` column declares a `vocabulary`, whatever its role, except a discriminator, whose value space R55 §2.1 fixes; a column of any other type declares none (R101 §3.1). There is no default, so an absent declaration is a defect rather than a claim of openness.

| value | what it says |
|---|---|
| `closed` | the column also declares `enum`, and a validator MUST reject a value outside it |
| `open` | the values name kinds of thing, comparable between packets; a validator MUST NOT reject an unrecognized one, and the column MAY declare `reserved_values` |
| `free` | not a vocabulary — a name, a description, a URI, a digest, a version string, a person; nothing may be reserved and no report is due |

Four columns are closed:

| column | values |
|---|---|
| `core.processing_runs.status` | `succeeded`, `failed`, `partial` |
| `core.units.quality_label` | `sua`, `mua`, `noise` |
| `core.unit_quality_labels.normalized_label` | `sua`, `mua`, `noise` |
| `core.subjects.sex` | `male`, `female`, `hermaphrodite`, `other` |

A scorer's own `label` is open, because aggregating over scorers is incompatible with one closed set (R22 §1).

A value MAY be reserved only where it is read **whole**: where a consumer comparing two packets learns something from the value alone, without knowing what either packet was doing (R101 §3.4). Where an external nomenclature defines the values instead, the registry names it rather than copying it, which R3 §3.0 requires of any set the standard does not itself define. A validator SHOULD report a value outside a reserved set at `info`, and MUST NOT fail on one.

An `open` column MUST carry a description stating the form its values take, and that description MUST name the nomenclature where one fixes the spelling (R101 §3.5). The column MAY also declare `authority`, naming that nomenclature as an absolute URI — identity, not a fetch instruction: a validator MUST NOT dereference one and MUST NOT reject a value for being absent from it (R101 §3.6). A writer MUST spell a value as the named nomenclature does.

### 9.4 Provenance of a declaration

A table and a column SHOULD each carry `since`, naming the revision that introduced or last changed it (R77 §2.3). The registry stamps both: 19 tables and 213 columns carry one.

A column whose role is declared SHOULD NOT restate its base in its description (R48 §2.5). The role carries it, and prose repeating it is a second statement that can disagree with the first.

## 10. Validation rules

### 10.1 Tier 1: generated from structure

A validator MUST generate, from the declaration alone: required-column non-null checks, foreign-key anti-joins, and closed-vocabulary membership. A nullable foreign key is guarded with a null test.

A validator MUST establish that a table's primary key is unique, by query or by any means a physical profile defines as establishing it (R92 §2.1). That a key is unique holds under any profile and is this part's; how a validator may establish it depends on how rows are stored, and is the profile's.

### 10.2 Tier 2: declared

A rule the structure cannot imply is declared as SQL returning offending rows, or as a named template the registry build expands (R24 §2).

A rule's SQL MUST NOT reference a column whose presence is `optional` (R94 §3). A rule is executed against the file, and `optional` permits the column to be absent from it (§6), so a rule naming one does not miss a check — the query fails to parse, and the run meant to find defects reports an error of its own. A constraint that wants an optional column either makes it `nullable`, which declares it always present and sometimes empty, or moves to the shim of §10.3.

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
| `core.electrode_coordinate_values` | one row per axis of that position |
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
| `core.unit_coordinate_values` | one row per axis of that position |
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

### 11.9 Space

Frames stand to a coordinate as §11.3's clocks stand to a tick: the declared reference the value is stated against.

| resource | contents |
|---|---|
| `core.coordinate_frames` | the spaces coordinates are positions in, and which published atlas each one is |
| `core.coordinate_frame_axes` | one row per axis of a frame, with its name, direction, and unit |

## 12. Rules for particular resources

Sections 2 through 10 bind every table. What follows binds particular ones, where identifying a
row, resolving a value, or reading an absence takes more than the generic rules give.

### 12.1 Unit identity

`unit_id` identifies a unit on its own (R81 §2.1). The packet assigns it, numbering units by
ascending `(sorting_run_id, curation_id, local_unit_label)` so a rebuild reproduces the same
numbers (R81 §2.2); `core.units` records the run and the curation as ordinary columns, and
`local_unit_label` records what the sorter called it.

A table keyed on a unit carries `unit_id` and not the run or the curation (R81 §2.3), and a
consumer relating a unit to anything outside the packet uses `(sorting_run_id, local_unit_label)`
(R81 §2.5).

`core.units` also declares what its spikes are counted on and measured in: `clock_id`, required,
and `amplitude_unit`, nullable and open (R96 §3.1, §3.2). Both are facts of the sorting run, and a
spike cannot reach the run — §8.4 admits one hop and spike → unit → run is two — so they live on
the table a spike references directly. `core.spike_events.t_tick` therefore declares
`clock_from: core.units.clock_id` and `amplitude` declares `unit_from: core.units.amplitude_unit`
(R96 §3.3), and neither `core.spike_events` nor `core.unit_observation_intervals` carries a
`clock_id` of its own (R96 §3.4). The run still determines both values, since a unit names its run
in a reference it MUST carry.

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

### 12.4 A clock's rate

A clock MUST NOT declare both `tick_rate_hz` and a rational rate (R95 §3.2); `core.clocks.tick_rate_declared` already requires at least one, so exactly one is present. The float is for a source that measured its rate rather than stating an exact one, and forcing a rational on it would make a writer invent a denominator — a rounding decision this specification does not make on a source's behalf (R66 §2.1).

### 12.5 A clock's observation window

A packet MUST declare at least one row of `core.clock_observation_intervals` for every clock any of its rows is timestamped on (R98 §3.1). More than one is permitted, for an acquisition paused and resumed (R38 §2.1). A clock that exists only as a parent declares none: R27 §3 requires the chain to be well founded, so such a clock is declared, and nothing is observed on it for R38 §2.3's inheritance to reach.

`core.clocks.observation_declared` checks the part of that a query can see — a clock that has anchors, or that a session names as its `reference_clock_id`, and declares no interval. A clock aligned by `transform_slope` alone carries data and has no anchors, so the obligation reaches it and the rule does not; the obligation binds the writer, which knows what it timestamped.

### 12.6 A clock's alignment record

Three facts about how a packet's clocks were aligned are columns, because a consumer needs them to place a tick and `02` §8.6's line puts such a fact in a column and never in a key (R99 §3).

`core.sessions.alignment_bound` holds how far past its anchors the writer mapped, in median anchor intervals. A writer establishing a bound wider than R27 §5.3's default MUST record it; a consumer reading a null MUST map at that default, which is a fact and not a defect. It is on the session because the bound is a property of the times the packet states, as `t_zero_tick` is (R39 §2.1), so one session declares one bound and no rule is needed to say which run wins. A value below one is refused.

`core.clocks.withheld_first_anchor` and `withheld_last_anchor` record R37 §3.2's terminal-anchor test on that clock, and a writer running it MUST record both. Three states carry what R40 §2.3 asks for: null is a clock the test did not run on, false is a terminal it kept, true is one it withheld — so a silent zero and an untested clock differ structurally rather than by a rule nothing can observe. A clock with no anchors MUST NOT declare either.

`core.clock_phase_steps` holds one row per step in a clock's alignment to its parent, a clock having possibly several (§5.2). A writer detecting a step MUST record it, and a step is reported and never corrected: R13's map is exact at every anchor, so it carries the step faithfully, and subtracting it would need to know whether the step also moved the devices timestamped on that parent, which the packet does not record. A clock whose `parent_clock_id` is null MUST NOT have rows here.

`core.processing_runs.parameters` keeps the evidence behind each decision and none of the three facts themselves. A writer SHOULD record there what R40 §2.2 requires of a measurement — median, p95 and maximum error, with the distance and the tolerance it judged them against. A consumer needs the bound to place a tick and not the residual that justified it.

### 12.7 A frame's axes

A frame declares one row of `core.coordinate_frame_axes` per axis it has, and two axes of one frame MUST NOT carry the same `axis_name` (R105 §3.2), which `core.coordinate_frame_axes.axis_names_distinct` checks. An axis name is the source's own word for the field the values came from, so two axes sharing one means a writer put two quantities under one name and the packet cannot say which value is on which axis.

A coordinate's values reference the axis rows of their own frame on `(session_id, coordinate_frame, axis_index)`, so a value on an axis the frame never declared is an orphan Tier 1 reports, and a frame's axis count cannot disagree with the shape of its coordinates (R105 §3.3).

A coordinate MAY carry values on fewer axes than its frame declares, where its source states none on the rest, and a consumer MUST NOT read an absent axis row as a zero: it is a position the source did not state on that axis (R105 §3.3). That is what a null in the struck `x_um`, `y_um` and `z_um` said, in the form the child table has.

`axis_value` declares `unit_from` of `core.coordinate_frame_axes.unit`, resolved one hop through that reference (§8.4): the unit is the axis's, so a frame stated in millimetres needs no second set of columns and no column name carries a unit.

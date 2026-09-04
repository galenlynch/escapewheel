# Part 02 — Core Logical Schemas

Normative.

## 1. Scope

This part defines how a logical schema is declared, what a declaration must contain, and which resources the core layer comprises.

The column-level definitions themselves are not written here. They are data (§9), carried in a registry document that a packet embeds and that generates the checks of Part 05. This part is the rules the registry obeys; the registry is the schema.

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

## 5. Type system

### 5.1 Permitted types

A column's type MUST be one of:

```text
string  int32  int64  float32  float64  bool  timestamp  date  json_string
```

### 5.2 No nested types

`list`, `struct`, and `map` MUST NOT be used (R3 §2.1). A repeated value becomes a child table; a semi-structured value becomes a `json_string` in an optional column.

This keeps a conforming reader able to satisfy every required column without a JSON parser, and keeps a native reader viable in a language without an embedded SQL engine.

### 5.3 Fixed representations

Tick columns MUST be `int64`. Wall-clock columns MUST be `timestamp` with microsecond precision in UTC, and MUST NOT use INT96. Identifier columns MUST be `int32` (R53 §2.1).

## 6. Presence

A column is `required` or `nullable`. A required column MUST be present and non-null in every row.

A present nullable column is preferred to an absent one, because a stable column set simplifies query code. A schema MUST NOT declare a column that duplicates what the data already declares: `core.array_assets` carries no dtype or shape, because the array declares them (R3 §3.0).

Duplication is permitted only where it buys otherwise-unavailable access. Axis names are carried in `core.array_dimensions` because a Zarr binding in another language cannot see them.

## 7. References

A table declares each foreign key as a reference naming the target resource, this table's columns, and the target's columns. A reference MAY be composite, nullable, or self-referencing (R46 §2).

A reference MUST relate columns of the same role, and of the same identity where both are identifiers. Relating an assigned identifier to a carried one resolves to nothing.

## 8. Column semantics

### 8.1 Role

Every column MUST declare exactly one role, from a closed vocabulary with no default (R48 §2.1, R55 §2.1):

| role | meaning |
|---|---|
| `data` | a value to be read |
| `identifier` | a stable identity, per §8.2 |
| `coordinate` | a position on an axis, such as a tick |
| `structural_index` | a zero-based offset into a stored sequence |
| `sequence_position` | an ordinal within an ordered set |
| `discriminator` | a value naming the resource another column resolves against |

The role is what makes index-base conversion derivable from a packet rather than hard-coded in each one-based client (R3 §6). A `structural_index` converts at the client boundary; a `coordinate` does not.

### 8.2 Identity

An `identifier` column MUST declare `carried` or `assigned` (R53 §2.3). A table owning an assigned identifier MUST carry the corresponding `*_name` column.

### 8.3 Discriminator

A `discriminator` column MUST hold a dotted resource identifier, and MUST declare `resolves` as `required` or `optional` (R55 §2.2):

| `resolves` | an unresolvable value is |
|---|---|
| `required` | a defect: the row is uninterpretable |
| `optional` | a fact: the packet does not hold that resource |

A discriminator paired with a value column MUST declare `discriminates`, naming that column. A paired value holds one identifier and so can only name a resource with a single-column primary key.

Core MAY name an extension's resource through a discriminator. It MUST NOT reference one (R55 §5): naming does not create a dependency.

### 8.4 Unit and clock

A `data` column carrying a physical quantity SHOULD declare its `unit`, or `unit_from` naming a column that carries it. A `coordinate` column MUST declare `clock_from` where the clock is not that row's `clock_id` (R56 §2).

`clock_from` names a column of the same table or a one-hop `resource.column`. A consumer resolves it rather than guessing, because converting on the wrong clock fails silently.

## 9. The registry

### 9.1 The schema is one document

Table structure and validation rules are carried in one JSON document (R2 §2). It declares the semantic and logical standard versions, its own registry version, and its tables.

### 9.2 Self-description

A packet MUST record the registry version it was written against and SHOULD embed the registry itself, so the packet stays readable as the reference registry moves on (R2 §8). A packet whose embedded registry disagrees with its recorded version is invalid.

A registry document SHOULD carry a top-level `$schema` naming its meta-schema (R57 §2). A validator MUST NOT dereference it and MUST NOT require it.

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

A column SHOULD carry `since`, naming the revision that introduced or last changed it (R29 §2), so that the generated schema reference answers both what a table is and why.

## 10. Validation rules

### 10.1 Tier 1: generated from structure

A validator MUST generate, from the declaration alone: required-column non-null checks, primary-key uniqueness, foreign-key anti-joins, and closed-vocabulary membership. A nullable foreign key is guarded with a null test.

Uniqueness need not be checked by query where a table's physical sort begins with its primary key, since duplicates are then adjacent and the ordering scan settles it.

### 10.2 Tier 2: declared

A rule the structure cannot imply is declared as SQL returning offending rows, or as a named template the registry build expands (R24 §2).

The execution contract is the whole protocol: **a check's query returns offending rows; empty is a pass, non-empty is a failure, and the returned rows are the finding.**

A rule declares a level of `error`, `warning`, or `info`. A rule MAY be `advisory`, in which case it is off by default and MUST NOT be `error`, so that enabling it cannot change whether a packet previously passed (R26 §2).

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
| `core.devices` | instruments used |
| `core.probes` | devices carrying electrodes |
| `core.electrodes` | recording contacts |
| `core.electrode_coordinates` | a contact's position per frame and basis |

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
| `core.events` | timestamped observations |
| `core.event_streams` | what produced a set of events, and on what clock |
| `core.event_stream_observation_intervals` | a stream's refinement of its clock's window |

### 11.5 Sorting

| resource | contents |
|---|---|
| `core.sorting_runs` | what sorted what, on which clock |
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
| `core.array_assets` | dense arrays, owned or referenced |
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

## 12. Ordering

A writer SHOULD sort every table by its primary key (R10 §2). Two tables override this:

| resource | order |
|---|---|
| `core.spike_events` | `session_id, sorting_run_id, curation_id, unit_id, t_tick` |
| `core.events` | `session_id, clock_id, t_tick, event_type` |

A large table SHOULD be partitioned by `session_id`. A table MUST NOT be partitioned by `unit_id`.

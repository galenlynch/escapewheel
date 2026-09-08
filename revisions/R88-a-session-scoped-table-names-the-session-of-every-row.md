# R88 — A Session-Scoped Table Names the Session of Every Row

| | |
|---|---|
| **Status** | **Accepted** 2026-09-07 |
| **Amends** | `02` (`core.devices.session_id`, `core.processing_runs.session_id`, and the eight tables that carry no session column), R86 §2.1 (its count of undeclared `session_id` columns) |
| **Depends on** | R46 (the references the registry never declared), R86 (session scope is derivable) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

`core.sessions` holds one row per session, and `session_id` is the column by which a row of any
other table names the session it belongs to. A table is **session-scoped** where it reaches
`core.sessions` through its declared references, directly or transitively (R86 §2.1), which 33 of
core and analysis's 35 tables do. Measured on the two packaged sessions, **`ecephys_776259`**
(twelve probes, 6,781 sorted units) and **`ecephys_786867`** (ten probes, 4,505).

## 1. Motivation

### 1.1 Thirty-three session-scoped tables use four conventions between them

Sixteen of the thirty-two that are not `core.sessions` itself hold `session_id` as a required
column and declare its reference to `core.sessions`. The other sixteen each depart from that in
one of three ways.

| what the table has | tables | |
|---|---:|---|
| a required `session_id`, and the reference declared | 16 | the intended shape |
| a nullable `session_id`, and the reference declared | 2 | `core.devices`, `core.processing_runs` |
| a `session_id`, and no reference declared | 6 | `analysis.spike_events`, `core.sorting_run_channels`, `core.unit_coordinates`, `core.unit_electrodes`, `core.unit_observation_intervals`, `core.unit_quality_labels` |
| no session column at all | 8 | `analysis.array_dimensions`, `core.array_channels`, `core.array_dimensions`, `core.clock_anchors`, `core.electrode_coordinates`, `core.event_stream_observation_intervals`, `core.media_frames`, `core.processing_run_inputs` |

Nothing chose the split, and each of the three departures costs something different.

### 1.2 Six `session_id` columns are foreign keys no rule checks

A Tier 1 anti-join is generated from a table's declared `references` and from nothing else
(`escapewheel_validator/generate.py:292`), so a column naming another table's key without
declaring it gets no check at all. Six `session_id` columns are in that state, so a row of
`core.unit_electrodes` naming a session that is not in `core.sessions` validates clean.

R86 §2.1 states the opposite, and its count is wrong: *"zero tables carry a `session_id` column
without also declaring the reference"*. Measured against the current registry, **25 tables carry
the column and 7 declare no reference** — `core.sessions` itself, which owns the key, and these
six. R86's conclusion is unharmed and better supported than it was: all six reach `core.sessions`
transitively, so the reference graph finds them where a declared-reference test does not, which is
what R86 §2.1 calls the stricter test.

The rows are not a rounding error. Across the two packets **418,618,218 rows hold a `session_id`
nothing validates**, of which 286,876,859 are `analysis.spike_events` in `ecephys_776259` alone —
the largest table either packet holds. R46 declared sixteen foreign keys that had never been
written, for exactly this reason, and these six survived that sweep.

### 1.3 Eight tables cannot say which session a row is from

R86 §2.2 requires a reader presenting one or more packets to carry a session discriminator on
every session-scoped table. Eight of the thirty-three hold no column to derive one from, so the
only route is a join to the parent that does — which R86 §2.4 measures at **2.22x** against a
projected literal's 1.02x, and which R86 specifies nowhere. The reference reader refuses, raising
`MultiSessionUnresolved` and naming the table rather than guessing.

Nothing has met that refusal, because R1 §1 makes a single-session packet primary and none of
the other kind exists: where a packet holds one session, that session answers for every row in it.
The first multi-session packet meets the refusal on eight tables at once.

### 1.4 Two `session_id` columns are nullable for a question the registry now answers

`core.devices.session_id` and `core.processing_runs.session_id` are nullable, and `02` describes
them as *"Session if device record is session-scoped"* and *"Session ID if session-scoped"*. Both
hedges were written before anything could compute scope; R86 §2.1 now does, and both tables reach
`core.sessions`, so both are session-scoped and the condition the hedge waits on is settled.

A null in either would leave R86 §2.2's discriminator undefined for the row, and would also degrade
a rule that already exists: R82 §2.1's currency check groups by `session_id, activity_type, scope`,
and SQL collects every null into one group, so two runs recording no session would be reported as
competing alternatives whether or not they are. Neither column is ever null — **0 of 41 device rows
and 0 of 48 processing-run rows** across the two packets. R85 §3 settles the first of them
independently: `core.devices` is session-scoped because 11 device names appear in both packets with
different hardware behind them.

## 2. Decision

### 2.1 Exactly the session-scoped tables have a `session_id`

A table reaching `core.sessions` through its declared references **MUST** have a `session_id`
column: `int32`, presence **required**, R48 role `identifier`, R53 identity `assigned`. The
eight tables holding no session column gain one, and `core.devices.session_id` and
`core.processing_runs.session_id` become required.

A table that does not reach `core.sessions` **MUST NOT** have one. Two do not —
`core.subjects` and `core.source_files`, which `core.sessions` references rather than the reverse —
and neither carries one today, so the prohibition costs nothing and states what a later table may
not do.

### 2.2 A `session_id` declares its reference to `core.sessions`

A table with a `session_id` **MUST** declare the reference `session_id` →
`core.sessions.session_id`. Carrying the column without it is the state §1.2 measures, and the
reference is the whole of what a rule can see: Tier 1 generates one anti-join per declared
reference, so the column is checked or unchecked according to whether the reference is written.

### 2.3 A writer fills the column from the parent it already read

Every one of the eight is **exactly one hop** from a parent that holds `session_id` —
`core.media_frames` from `core.media_assets`, `core.clock_anchors` from `core.clocks`,
`core.electrode_coordinates` from `core.electrodes`, and so on. An adapter is also constructed
with the session it is building, which is where the value actually comes from.

So the column costs no new read. A writer **MUST NOT** infer the session from a name — a file path
and a packet directory both spell one, and neither is a statement this specification constrains.
R67 §2.4 forbids the same inference to a consumer reading a device's name, so this is that rule's
shape turned on the other actor: the reference is the statement, whoever is reading it.

### 2.4 A run covering several sessions is recorded once per session

`processing_run_id` is `assigned` (R53 §2.3) and `core.processing_runs` is keyed on it alone, so
the packet mints the number and nothing obliges one computation to be one row. A run whose results
reach several sessions is recorded **once per session**, and every dependent row — a sorting run, a
curation version, a coordinate, a run input — references the copy for its own session.

R85 §1.3 measures the same shape one level down: `core.devices` holds a row per session for
hardware that is one physical object, because two sessions record different firmware behind one
name. Here duplication costs a handful of columns on a table holding 26 and 22 rows.

Currency is unaffected, because the machinery is already partitioned by session: R82 §2.1's rule
groups by `session_id, activity_type, scope` and `core.preferred_runs` is keyed
`(session_id, activity_type, scope_kind, scope)`, so two copies in different sessions never
compete. The copies **MUST NOT** share a `processing_run_name`, which R85 §2.2 requires to be
unique within a packet.

## 3. What this does not change

- **R3 §3.0 stands.** It forbids restating what the data declares *unless the duplication buys
  otherwise-unavailable access*, and this buys two things that are otherwise unavailable:
  attribution without a join, and a foreign key a rule can see. Its own worked example is the same
  shape — `core.array_dimensions` carries axis names because Zarr.jl cannot see them at all.
- **No table is added and no rule is hand-written.** The fourteen new checks are Tier 1, generated
  from the references §2.2 declares.
- **R86 is unamended.** Its §2.2 already requires the discriminator on every session-scoped table;
  this makes that requirement satisfiable for a multi-session packet, where today it is only
  refusable.
- **No primary key changes.** `session_id` sits beside the key rather than in it, which is what the
  sixteen tables already doing this do: `core.units` is keyed on `unit_id` alone since R81 §2.3 and
  holds the session as an ordinary column. Uniqueness is unaffected on the eight tables that gain
  one, since adding a column cannot make an existing key less unique.
- **No packet's information changes.** Every value the new columns will hold is already in the
  packet, one declared reference away. What changes is where it sits and whether a rule can reach
  it.

## 4. Consequence

The registry goes from 308 columns to **316** and from 76 references to **90**, so Tier 1's
not-null checks go from 130 to **140** and its anti-joins, one per reference, from 76 to **90**.

Nothing fails. The six columns that already exist have **0 orphans across both packets**, so the
six references declared over them turn on checks that already pass — R46's own result on its
sixteen. The other eight cannot orphan by construction: §2.3 fills each from the parent row whose
own reference to `core.sessions` is already checked.

Storage is free. On `core.media_frames`, the largest of the eight at **7,570,450 rows**, adding the
column costs **1.0005x** — 0.013 bits per row — because one distinct value under a clustered sort
compresses away. R81 measured the same shape at no cost over 286,896,563 spikes.

**Both packets must be rebuilt.** The column is required and eight tables lack it, so every packet
built before this is non-conforming. R61 §3 makes a correction a rebuild, and this one re-reads no
external resource; `ecephys_776259` was already owed one for its subject.

The reference reader drops `MultiSessionUnresolved` with the case that produced it, and R86 §2.4's
projection covers all 33 session-scoped tables rather than 25.

## 5. Open

- **Whether a run about no session at all should be recordable.** §2.4 answers the run that spans
  sessions and not the run that belongs to none. The candidate case turned out not to be one: both
  packets' `rig.json` carries the same water calibration dated 2024-11-27, **133 days** before one
  session and **302 days** before the other, and a calibration produced no resource in either
  packet, so it was never a `core.processing_runs` row to begin with. R89 gives it `core.calibrations`
  instead. What remains open is a genuine processing run owned by a rig rather than a session, which
  R49 §2.2 anticipates one field over and no packet holds.
- **Whether `analysis.array_dimensions.coordinate_array_asset_id` is a seventeenth missing
  reference.** Settled by R93 §2.4, which declares it. Unpacking it found a second defect in the
  same two columns that this revision's scope would have hidden: `coordinate_resource` holds a
  dotted resource ID in **25 rows across the two packets** and carries R48 role `data`, so nothing
  checks the value R55 §2.1 added a role for.
- **Whether `registry/check.py` should enforce §2.1 both ways.** It already computes scope and
  reports the 33 and the 2, so both halves of §2.1 are checkable there rather than left to review.
  Doing it is implementation and needs no clause; recording that it was the intent does.

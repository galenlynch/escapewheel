# R88 — A Session-Scoped Table Carries `session_id`

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `02` (`core.devices.session_id`, `core.processing_runs.session_id`, and the eight tables that carry no session column) |
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

Sixteen of the thirty-two that are not `core.sessions` itself carry `session_id` as a required
column and declare the reference to `core.sessions`. The other sixteen each do one of three other
things.

| what the table does | tables | |
|---|---:|---|
| carries a required `session_id`, declares the reference | 16 | the intended shape |
| carries a nullable `session_id`, declares the reference | 2 | `core.devices`, `core.processing_runs` |
| carries `session_id`, declares no reference | 6 | `analysis.spike_events`, `core.sorting_run_channels`, `core.unit_coordinates`, `core.unit_electrodes`, `core.unit_observation_intervals`, `core.unit_quality_labels` |
| carries no session column at all | 8 | `analysis.array_dimensions`, `core.array_channels`, `core.array_dimensions`, `core.clock_anchors`, `core.electrode_coordinates`, `core.event_stream_observation_intervals`, `core.media_frames`, `core.processing_run_inputs` |

Nothing chose the split. Each of the three departures has its own consequence, and the three are
described below in the order they cost something.

### 1.2 Six `session_id` columns are foreign keys no rule checks

A Tier 1 anti-join is generated from a table's declared `references` and from nothing else
(`escapewheel_validator/generate.py:292`), so a column naming another table's key without
declaring it gets no check at all. Six `session_id` columns are in that state, and a row of
`core.unit_electrodes` naming a session that is not in `core.sessions` therefore validates clean.

The rows are not a rounding error. Across the two packets **418,618,218 rows carry a `session_id`
nothing validates**, of which 286,876,859 are `analysis.spike_events` in `ecephys_776259` alone —
the largest table either packet holds. R46 declared sixteen foreign keys that had never been
written, for exactly this reason, and these six survived that sweep.

### 1.3 Eight tables cannot say which session a row is from

R86 §2.2 requires a reader presenting one or more packets to carry a session discriminator on
every session-scoped table. Eight of the thirty-three hold no column to derive one from, so the
only route is a join to the parent that does — which R86 §2.4 measures at **2.22x** against a
projected literal's 1.02x, and which R86 specifies nowhere. The reference reader refuses, raising
`MultiSessionUnresolved` and naming the table rather than guessing.

Nothing has met that refusal, because R1 §1 makes a single-session packet primary and no
multi-session packet exists: where a packet holds one session, that session answers for every row
it holds. The first multi-session packet meets it on eight tables at once.

### 1.4 Two `session_id` columns are nullable for a question the registry now answers

`core.devices.session_id` and `core.processing_runs.session_id` are nullable, and `02` describes
them as *"Session if device record is session-scoped"* and *"Session ID if session-scoped"*. Both
hedges were written before anything could compute scope; R86 §2.1 now does, and both tables reach
`core.sessions`, so both are session-scoped and the condition the hedge waits on is settled.

A null in either would leave R86 §2.2's discriminator undefined for the row. Neither is ever null:
**0 of 41 device rows and 0 of 48 processing-run rows** across the two packets. R85 §3 settles the
first of them independently — `core.devices` is session-scoped because 11 device names appear in
both packets with different hardware behind them.

## 2. Decision

### 2.1 A session-scoped table carries `session_id`, and a table that is not MUST NOT

A table reaching `core.sessions` through its declared references **MUST** carry `session_id`:
`int32`, presence **required**, R48 role `identifier`, R53 identity `assigned`. The eight tables
that carry no session column gain one, and `core.devices.session_id` and
`core.processing_runs.session_id` become required.

A table that does not reach `core.sessions` **MUST NOT** carry a `session_id`. Two do not —
`core.subjects` and `core.source_files`, which `core.sessions` references rather than the reverse —
and neither carries one today, so the prohibition costs nothing and states what a later table may
not do.

### 2.2 A `session_id` declares its reference to `core.sessions`

A table carrying `session_id` **MUST** declare the reference `session_id` →
`core.sessions.session_id`. Carrying the column without it is the state §1.2 measures, and the
reference is the whole of what a rule can see: Tier 1 generates one anti-join per declared
reference, so the column is checked or unchecked according to whether the reference is written.

### 2.3 A writer fills the column from the parent it already read

Every one of the eight is **exactly one hop** from a parent that carries `session_id` —
`core.media_frames` from `core.media_assets`, `core.clock_anchors` from `core.clocks`,
`core.electrode_coordinates` from `core.electrodes`, and so on. An adapter is also constructed
with the session it is building, which is where the value actually comes from.

So the column costs no new read. A writer **MUST NOT** infer the session from a name — a file path
and a packet directory both spell one, and neither is a statement this specification constrains,
which is R67 §2.1's rule about attachment applied to the same shape of question.

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
- **No primary key changes.** `session_id` is carried and not keyed, which is what the sixteen
  tables already doing this do: `core.units` is keyed on `unit_id` alone since R81 §2.3 and carries
  the session beside it. Uniqueness is unaffected on the eight tables that gain a column.
- **No packet's information changes.** Every value the new columns will hold is already in the
  packet, one declared reference away. What changes is where it sits and whether a rule can reach
  it.

## 4. Consequence

The registry goes from 308 columns to **316** and from 76 references to **90**, so Tier 1's
not-null checks go from 130 to **140** and its anti-joins, one per reference, from 76 to **90**.

Nothing fails. The six columns that already exist have **0 orphans across both packets**, so
declaring their references turns on fourteen checks that all pass — R46's own result on its
sixteen.

Storage is free. On `core.media_frames`, the largest of the eight at **7,570,450 rows**, adding the
column costs **1.0005x** — 0.013 bits per row — because one distinct value under a clustered sort
compresses away. R81 measured the same shape at no cost over 286,896,563 spikes.

**Both packets MUST be rebuilt.** The column is required and eight tables lack it, so every packet
built before this is non-conforming. R61 §5 makes a correction a rebuild, and this one re-reads no
external resource; `ecephys_776259` was already owed one for its subject.

The reference reader drops `MultiSessionUnresolved` with the case that produced it. R86 §2.4's
projection then covers all 33 session-scoped tables rather than 25, and no reader needs the join
R86 declined to specify.

## 5. Open

- **Whether a processing run is always a session's.** §2.1 makes `core.processing_runs.session_id`
  required on the evidence that it is never null, and R44 §2 gives a run a `scope` that may name a
  rig or a camera rather than a session. A run about something no session owns would need the
  column nullable again and would make R86 §2.2's discriminator genuinely undefined for that row
  rather than accidentally so. No packet holds one, and that is the condition on which this clause
  should be reopened.
- **Whether `analysis.array_dimensions.coordinate_array_asset_id` is a seventeenth missing
  reference.** `core.array_dimensions` declares the analogous column against `core.array_assets`
  and the analysis copy declares nothing, so the two disagree about one column. It is the same
  defect class as §1.2 and is left out because one column is a case rather than a class, and
  because it is not about sessions.
- **Whether `registry/check.py` should enforce §2.1 both ways.** It already computes scope and
  reports the 33 and the 2, so both halves of §2.1 are checkable there rather than left to review.
  Doing it is implementation and needs no clause; recording that it was the intent does.

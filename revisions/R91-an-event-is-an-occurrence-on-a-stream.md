# R91 — An Event Is an Occurrence on a Stream

| | |
|---|---|
| **Status** | **Accepted** 2026-09-08 |
| **Amends** | `02` (`core.events`' columns and key, `core.event_streams`' columns), R23 §2 (what a stream declares), R11 §4 (which table declares `event_type`) |
| **Depends on** | R23 (an event stream is the context events lacked), R53 (an identifier is an integer, and an assigned one carries a name), R55 (a discriminated reference), R56 (a column declares its context) |
| **Profile** | `escapewheel-portable-v0.1` |

Normative, except §2 and §6, which are informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R23 added `core.event_streams` as the context an event needed: what produced these events, on what
clock, and — through `core.event_stream_observation_intervals` — when it was watching. The event
kept carrying that context anyway, on every row, and gained a surrogate identifier and a generated
name to explain it.

This part moves what belongs to the stream onto the stream, strikes what nothing reads, and leaves
an event as what it is: a tick, a stream, and what was measured.

Measured on the two packaged sessions, **`ecephys_776259`** (twelve probes, 6,781 sorted units,
recorded 2025-04-09) and **`ecephys_786867`** (ten probes, 4,505 units, recorded 2025-09-25), which
hold 5,485 and 6,256 events across ten declared streams, seven of them carrying events.

## 2. What the table holds

Informative.

### 2.1 Three columns are the stream's

| column | what it copies | measured |
|---|---|---|
| `clock_id` | `core.event_streams.clock_id` | differs on **0** of 5,485 and **0** of 6,256 rows |
| `event_type` | `core.event_streams.name`, minus a suffix | each stream carries one type, each type one stream |
| `event_name` | that same name, plus an ordinal | 5,485 of 5,485 filled, all distinct |

`event_type` is not merely correlated with the stream, it is **derived** from it: the only adapter
that writes an event computes `name.removesuffix("_time")` from the stream's own name
(`sources/nwb.py:958`), so `left_lick_time` becomes `left_lick`. `event_name` is that same name
plus a running ordinal, `left_lick_time:0`, which is R53 §2.3.1's generated explanation for an
assigned identifier and carries nothing the stream does not.

### 2.2 The surrogate costs more than the measurement

Nothing in the registry references `core.events`. Its one consumer is
`escapewheel_reader.alignment`, which returns `event_id` as the label of the event a spike was
aligned to and picks the nearest with `argmin(e.event_id, …)`.

`event_id` and `event_name` together are **41,164 of the table's 56,115 compressed bytes** in
`ecephys_776259` — 73% — against 12,140 for `t_tick`, the only column recording an observation, and
1,345 for `event_type`. The identifier alone is 21,010, or 37%.

### 2.3 What is left identifies the row

`(session_id, stream_id, t_tick)` is unique in both packets: **5,485 of 5,485** and **6,256 of
6,256**. `(session_id, t_tick)` is not — 5,480 in `ecephys_776259` — so the stream is doing work in
the key rather than riding along.

### 2.4 A mark has nowhere typed to go

An event may carry marks: a marked point process is events with marks, and core has one already in
`core.spike_events`, where `amplitude` sits beside the tick. `core.events` has `payload`, an
optional `json_string` the NWB adapter fills as `{"value": …}` — one number inside a JSON envelope
no rule can read and no filter can use (`sources/nwb.py:963`). It is absent from both packets, the
marker being constant on every stream there.

A typed column in core would only move the problem. How many marks an event carries, and of what
type, is a property of what produced it: a spike has an amplitude and a width, a lick a force and a
duration, a stimulus an identity that is not a number at all. One column of one type guesses at
both, and guesses wrong for every source but the one measured.

## 3. Decision

### 3.1 What the stream declares

`core.event_streams` gains two columns:

| column | type | presence | |
|---|---|---|---|
| `event_type` | `string` | required | data; what kind of event this stream emits, open (R8 §4) |
| `detail_kind` | `string` | nullable | discriminator, `resolves: optional`; §3.4 |

A stream emits **one kind of event**, which is why `event_type` is required: a writer **MUST**
write a source emitting several kinds on one channel as several streams. That is what the only
adapter already does, and what `core.event_streams.name` — the source's own field name — makes
natural.

### 3.2 What an event is

`core.events.event_id`, `event_name`, `event_type` and `clock_id` are **struck**. The primary key
becomes `(session_id, stream_id, t_tick)`.

`clock_id` goes because §2.1 measures it as the stream's and R56 §2.3 resolves `t_tick` in one hop:
`core.events.t_tick` **MUST** declare `clock_from: "core.event_streams.clock_id"`, through the
reference the table already declares on `stream_id`.

A consumer naming the event a spike was aligned to takes the event's `t_tick`:
`escapewheel_reader.alignment` selects `e.t_tick` where it selected `e.event_id`, unique within the
`(session_id, stream_id)` scope its queries already impose.

### 3.3 Where a mark goes

Core adds no column for a mark. A stream whose events carry marks **MUST** name the table holding
them through §3.4's `detail_kind`, and **that table declares how many there are and what type each
is**. A writer **MUST NOT** put a mark in `core.events.metadata`, which no rule reads and no filter
can use.

Core cannot declare it. §2.4 is why: cardinality and type are properties of what produced the
event, and a column in `core.events` would fix both for every source. An extension table fixes
neither — it carries one row per event with whatever columns that source's marks need, typed, and a
consumer filters on them without parsing anything.

`core.events.payload` is **not struck here**. It is the only home a per-event value has today and
`sources/nwb.py:963` fills it, so removing it before any extension declares a mark table would take
a capability away and leave §3.4's route existing but unused. What one event carries is also a
different subject from this part's: everything above is about facts constant across a stream.
`the-free-form-metadata-column` §5 strikes `payload` on its own ground — a second free-form column
on a table entitled to one — and that argument needs nothing from here.

### 3.4 Where structured detail lives

`core.event_streams.detail_kind` names a table that specialises the events of that stream, as a
dotted resource ID. It **MUST** declare `resolves: optional`, so a kind naming a table the packet
does not carry records that the detail is elsewhere rather than that the stream is wrong (R90
§3.4) — which is R89 §2.5's judgement, not R54 §2.1's, because an event with no detail is still an
event.

Resolution is R90 §3.5's shared key: the named table carries `(session_id, stream_id, t_tick)` and
declares a reference to `core.events` on those three columns, so Tier 1 generates the anti-join
(R46) and a detail row naming no event fails. `dynamic_foraging.trials` already resolves against
`core.intervals` on a three-column key this way.

The discriminator sits on the **stream** rather than on the event, which
R90 §3.2 is what admits — every discriminator until now has
sat on the row it specialises. It therefore declares
`discriminates_via: "core.events.stream_id"`, naming the reference a consumer follows from an
event to the stream carrying its kind.

## 4. What this does not change

- **`event_type` stays open.** R8 §4's terms are unaltered and a validator still MUST NOT reject an
  unrecognized value; the column changes table, not vocabulary.
- **No tick moves and no event is lost.** Every row keeps its tick and its stream. Four columns
  stop being written on the event and two start on the stream; nothing is added to `core.events`.
- **`core.event_stream_observation_intervals` is untouched.** R25 §2's refinement of a clock's
  window is a property of the stream and was already there.
- **A task's shape stays out of core.** Which spout a lick was on is one experiment's distinction,
  and R43 §3 and R54 §2.3 send it to an extension — reached here by §3.4 rather than by a column.
- **`core.events.metadata` stays.** Its key is not made entirely of other tables' identifiers, so
  the free-form column has somewhere to be under `the-free-form-metadata-column` §3.1.
- **`core.event_streams.metadata` stays, and is where a per-stream fact already goes.** It is
  written on 10 of 10 streams in both packets, holding the source's own description of the signal.
  With §3.1 and §3.4 the stream now carries three tiers: typed columns for what the standard models,
  `detail_kind` for what an extension does, and `metadata` for what nobody does.
- **`core.events.payload` stays.** §3.3 says why, and `the-free-form-metadata-column` §5 is where
  it is struck.

## 5. Consequence

`core.events` loses `event_id`, `event_name`, `event_type` and `clock_id`, going from nine columns
to five: `session_id`, `stream_id`, `t_tick`, `payload` and `metadata`. `core.event_streams` gains
two, going from eight to ten. One reference is struck, `core.events.clock_id` to `core.clocks`. So
335 columns become **333** and 97 references **96**.

Two Tier 2 rules on `core.events` are touched. `clock_matches_stream` becomes vacuous and is
**struck**: it compared an event's clock with its stream's, which is now one column.
`within_observation` stands and is rewritten, its projection selecting `(session_id, stream_id,
t_tick)` where it selected `event_id` — the rule is unchanged, the rows it returns are named by the
new key. Rules go from 70 to **69**.

Two other drafts touch what this one moves. `what-a-reserved-value-is-for` names
`core.events.event_type` five times, including a section heading, and after this part that column
is `core.event_streams.event_type`; `columns-that-hold-one-value` strikes the stream's generated
name and renames the other, so the stream ends at nine columns rather than ten if both are
accepted. Whichever lands second re-measures and repoints, as the pre-acceptance checks require of
every count.

**Both packets must be rebuilt.** The table's key, its columns and its stream's columns all change.
R87 §2.1 and R88 §2 already require that rebuild, so this adds none of its own. R61 §3 makes a
correction a rebuild, and this one re-reads no external resource.

`escapewheel_reader.alignment` selects the event's tick in `_events`, `aligned_spikes` and the
`argmin` that picks the nearest, and reads the kind and the clock from `core.event_streams` —
selecting one kind of event becomes a join rather than a predicate on the event row.
`Packet.events` resolves the type to a set of streams and pushes those keys down, which needs
membership as a predicate alongside equality and range. The NWB adapter writes `event_type` once
per stream instead of once per event and stops composing `f"{name}:{offset}"`; its `{"value": …}`
payload is untouched and keeps working.

One conformance variant is retired with the rule it exercised. `stream_clock_mismatch` put an
event on a clock its stream did not declare, and after §3.2 an event has no clock to put anywhere:
the defect is unconstructible, not merely unchecked. The corpus goes from 27 packets to 26.

## 6. Open

- **Whether an extension will declare a mark table.** §3.4 gives marks a typed route and nothing
  uses it, which is the shape `core.trial_tags` had: R3 §3.2 added it as the child-table example,
  no packet ever populated it, and R54 §2.3 withdrew it. §3.3 leaves `payload` in place so this
  part creates no gap while that plays out, but a route nobody takes is a route that gets withdrawn,
  and whether one appears decides whether `payload` is ever safely struck.
- **Whether `event_type` and the stream's name should differ at all.** They hold `left_lick` and
  `left_lick_time` here, one derived from the other by the adapter, and this part states no
  relationship between them — deliberately, because R67 §2.4 and R85 §2.2 forbid reading semantics
  out of a name, and asserting a derivation would make the name load-bearing. Both earn their
  place: the name is the source's own identifier and R53 §2.5's bridge between packets, the type is
  the vocabulary a consumer filters on across them. What is unmeasured is how often a source names
  a stream something a type cannot be derived from at all, which is the case that would prove the
  two columns independent rather than merely declared so.

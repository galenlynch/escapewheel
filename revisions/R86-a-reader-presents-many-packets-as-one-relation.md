# R86 — A Reader Presents Many Packets as One Relation

| | |
|---|---|
| **Status** | Proposed |
| **Amends** | `07` (the reference reader's surface), R1 §2 (multi-session packets) |
| **Depends on** | R46 (a reference is declared), R53 §2.5 (an assigned identifier is not stable across packets), R81 (unit IDs are assigned by the packet) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

R53 §2.5 settled what an assigned identifier means: *"not stable across packets… §2.3.1's
`*_name` is what recovers the correspondence."* This revision is about the consumer that has to
act on it — a reader holding more than one packet, or one packet holding more than one session.
Measured on the two packaged sessions, **`ecephys_776259`** and **`ecephys_786867`**.

## 1. Motivation

### 1.1 The analysis that meets this is ordinary

Every unit in one brain region, across twenty sessions, with their spike trains. Nothing about it
is exotic, and it is the reason people build multi-session summary tables in the first place.

Escapewheel removes the usual excuse for materialising one. Reading the two packets as a union
costs **274.8 ms** against **136.9 ms** for the same query on a single merged table, and both
return the same 549 units. Over an object store the fixed cost is requests rather than rows, and
the endpoint plateaus at **~120 per second** whatever the concurrency, so twenty sessions is about
a second of metadata. Materialising a packet per grouping of animals buys a factor of two and
costs a combinatorial number of artifacts, each stale the moment a session is re-sorted.

### 1.2 What the reader does not do today

`open_packet` opens one packet and registers its tables under their own names. There is no second
entry point, so a consumer wanting twenty sessions writes the union itself — and R53 §2.5's
warning is the only thing standing between it and joining `unit_id` across packets, which returns
a number rather than an error.

`core.units` holds `unit_id` 0–6,780 in one packet and 0–4,504 in the other, so **4,505 values
name a unit in both** and no two of those pairs are the same unit. Both sessions are additionally
`session_id = 0`, so the obvious repair does not work either.

### 1.3 A packet is not the unit that varies

R1 §2 makes a multi-session packet a graceful extension, so a consumer of **one** packet may
already face several sessions. The problem is therefore not a property of holding many packets,
and a reader that changed behaviour above one packet would draw the line in the wrong place.

## 2. Decision

### 2.1 A table is session-scoped where it reaches `core.sessions`

A table is **session-scoped** if it reaches `core.sessions` through its declared references,
directly or transitively. That is a property of the registry, computable with no packet in hand,
and `registry/check.py` reports it.

Of 34 core and analysis tables, **32 are session-scoped and 2 are not** — `core.subjects` and
`core.source_files`, which fall out unscoped because `core.sessions` references *them*. No
declaration is needed and none is added: **zero tables carry a `session_id` column without also
declaring the reference**, while **8 reach `core.sessions` without carrying the column**, so the
reference graph is both the stricter test and the simpler one. R46 is what made it available, by
declaring the sixteen foreign keys that were missing.

### 2.2 A reader discriminates by what it knows, not by what a name claims

A reader presenting one or more packets **MUST** carry a session discriminator on every
session-scoped table and **MUST NOT** carry one on a table that is not.

**The discriminator is the packet the row came from, together with the row's `session_id`.** Both
are known for certain: the reader opened the file, and the identifier is unique within it by
R53 §2.5. Their pair is unique by construction, so nothing has to be assumed about the world and
nothing can be wrong. A reader **SHOULD** number those pairs as it opens them and expose an
integer, which §2.4 measures as the cheap form.

A reader **MUST NOT** derive the discriminator from a `*_name`. R53 §2.3.1 says a name records
what a number stands for, and R53 §2.5 offers it as what "recovers the correspondence" across
packets — but a name is a **label**, and half of them are labels of a kind rather than of a
thing. Measured across these two packets, which share no session, no animal and no probe, **6 of
12 name columns collide**: `device_name` on 11 rig positions, `event_stream_name` on 10 stream
kinds, and `clock_name`, `array_asset_name` and `processing_run_name` on one each. `harp` and
`waveform_mean` are correct names in both packets and denote different things in each.

A reader **SHOULD** carry `session_name` beside the discriminator, as a label for reading and
grouping. It promises nothing: whether two packets' matching labels denote one thing is a fact
about the world, and an analyst asserting it is doing so knowingly.

**None of this depends on how many packets are open.** §1.3 is why there is no defensible
boundary, and the cost of drawing one is worse than the boundary itself: an analysis written
against one session and later pointed at twenty would meet a differently shaped relation without
meeting an error, which is the failure arriving exactly when the work scales.

### 2.3 Identity is carried, not joined on

Session identity **MUST NOT** become part of a join key where the assigned identifier is already
unique. Within one packet `unit_id` identifies a unit by itself, which is R81 §2.1's purpose, and
widening the join to `(session_id, unit_id)` costs **2.93x** — 310.7 ms against 106.2 ms over
286,896,563 spikes. That is more than R81 bought by narrowing, given back for nothing: the second
column discriminates only across packets, where the identifier is genuinely ambiguous and the cost
buys correctness. R53 §2.5 says the same thing in different words — the correspondence is
recovered *"through a join on the dimension table rather than on the fact table."*

### 2.4 A reader projects the identity rather than joining for it

`core.sessions` holds a handful of rows, so a reader that has opened a packet already knows every
session's discriminator and label, and **SHOULD** emit them as literal expressions over
`session_id`:

```sql
SELECT *, CASE session_id WHEN 0 THEN 'ecephys_776259_2025-04-09' END AS session_name
FROM 'spike_events.parquet'
```

rather than as a view joining `core.sessions`, which is what a reader writes first. The two differ
by an order of magnitude in what they cost a query that never uses the column:

| how the identity is added | unused | grouped on |
|---|---:|---:|
| projected as a literal | **1.02x** | 1.95x |
| joined from `core.sessions` | 2.22x | — |

A projection is a scalar expression over a column already being scanned, so a query not selecting
it has the expression pruned and reads nothing extra. A join cannot be pruned, because the planner
cannot show it neither filters nor duplicates rows, so it runs whether its output is read or not.

That 1.02x is what makes §2.2 affordable. Carrying identity only above one session would buy back
two percent and pay for it with the shape change §2.2 exists to prevent.

## 3. What this does not change

- **No table, column or rule.** Every fact this relies on — the names, the references, the graph —
  is already in the registry, and R53 §2.3.1 already requires the names.
- **No packet becomes invalid.** Both measured packets are conforming and remain so; this is about
  what a reader does with two of them.
- **R53 §2.5 is unamended.** It states what an assigned identifier means and that a `*_name`
  recovers the correspondence. This says what a reader must therefore do, which R53 left to the
  consumer.
- **R81 stands.** Narrowing `core.units` to one column is correct within a packet, which is the
  only scope a declared reference has ever had, and §2.3 is what keeps that win.

## 4. Consequence

Nothing to rebuild and nothing to migrate.

The reader gains a multi-packet open that walks the reference graph once, projects session
identity into the 32 session-scoped tables and leaves the 2 that are not alone. Its cost is §1.1's
union — 2x a merged table locally, about a second of requests for twenty sessions over an object
store — and 1.02x on a query that ignores the column.

`registry/check.py` gains the scope computation, so the 32 and the 2 are reported rather than
rediscovered by whoever next needs them.

## 5. Open

- **Whether anything should declare a cross-packet identity.** §2.2 needs none, because the
  discriminator comes from provenance the reader holds. Unifying two packets — the same animal,
  the same probe — is a different question, and a registry declaration naming the column that
  identifies a thing outside its packet would be asserting global uniqueness the format cannot
  check. `subject_name` is unique within one institution's numbering and means nothing against
  another's. Left to the analyst, explicitly, until a consumer needs the format to take the risk.
- **Whether the reader should renumber instead.** Offsetting each packet's identifiers would keep
  every join single-column and preserve R81's win in full, at the cost of showing a consumer
  numbers that are in no packet. Rejected here because an identifier a user reads should be the one
  the file holds, but it is the cheaper implementation and the choice deserves stating.
- **Whether combining packets deserves a tool.** Concatenating two packets is already refused
  without a clause: both hold `unit_id = 0`, so Tier 1's uniqueness check rejects the result. The
  sound version — renumbering every assigned identifier through one assignment — measured **34 s
  for 28 tables and 844,651,251 rows**, against **652 s** to rebuild both packets from sources. No
  multi-session packet exists yet, so what such a tool should promise is a question without a case.

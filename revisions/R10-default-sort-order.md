# R10 — Default Sort Order

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `03_portable_physical_profile.md` |
| **Depends on** | R7 (every table declares a key) |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`03` recommends a physical ordering for three tables — `core.unit_spike_chunks`,
`core.spike_events`, and `core.events` — and says nothing about the rest. The first of those
is withdrawn by R5, leaving two orderings declared out of 22 tables.

The omission has no principled basis. `03` scoped its recommendation to "large spike tables",
but ordering costs a writer one sort and benefits any table that is filtered, compressed, or
checksummed. Enumerating an ordering per table would add twenty entries of normative surface
for what a single rule expresses.

## 2. Rule

A writer SHOULD sort every table by its primary key, in the order the key declares, unless a
different ordering is specified for that table.

A table declaring `primary_key: null` (R7 §2) has no default ordering.

This is a physical property. Row order carries no meaning, and a conforming reader MUST NOT
depend on it — query results are unordered without an explicit `ORDER BY`. A writer that
ignores this rule produces a conforming packet, only a slower one.

## 3. The two specified orderings are overrides

Neither ordering `03` specifies is primary-key order. Both are retained, and both override
§2 for their table.

| Table | Primary key | Specified ordering |
|---|---|---|
| `core.spike_events` | `session_id, unit_id, sorting_run_id, curation_id, t_tick` | `session_id, sorting_run_id, curation_id, unit_id, t_tick` |
| `core.events` | `session_id, event_id` | `session_id, clock_id, t_tick, event_type` |

`core.spike_events` groups by sorting run and curation before unit, which keeps one
sorting/curation context contiguous. R3 §7.3 measures this ordering as the best all-around
layout for the access patterns tested.

`core.events` sorts by time rather than by identity, because events are queried by when they
occurred and `event_id` carries no ordering.

That both are overrides rather than restatements is why §2 needs an exception mechanism at
all.

## 4. What the rule buys

Sorting does not accelerate a full scan; row order is irrelevant there. It applies to three
other things, all of which hold at any table size:

- **Compression.** Sorted repeated values yield run-length and delta-encodable sequences.
- **Page-level pruning.** Parquet page indexes let an engine skip pages within a row group,
  so a filtered read benefits even where a table is too small to span row groups.
- **Deterministic output.** The same input produces a byte-identical file, which is what
  makes the checksums `03` recommends meaningful and what makes two packets diffable.

The third is the reason to apply the rule to small tables. Pruning and compression gains on a
few-hundred-row table are negligible; reproducible bytes are not, and cost the same nothing.

## 5. Consequence for validation

R2 §7.1's generated ordering check applies to every table with a declared `sort` rather than
to two. That is 22 window-function queries where there were 2, at `warning` level, over
tables that are mostly small.

This is the rule's entire cost.

## 6. Registry representation

The registry records the effective ordering per table: primary-key order by default, the
§3 orderings where they override. Recording the resolved value rather than a default-plus-
exception keeps a generator from having to implement the rule.

`core.media_frames` requires no special handling: §2 gives it its key order,
`(media_asset_id, frame_index)`.

Whether this is also time order depends on a convention `02` leaves unstated: it defines
`frame_index` only as "Frame index", without saying whether frames are counted in decode or
presentation order. Presentation order is the near-certain intent — it is the only reading
under which a frame-timing table is monotonic in `t_tick`, and it is what frame counters in
common decoding libraries produce — but an unstated convention two implementers read
differently misaligns media against neural data silently, without failing any check.

Until it is stated, a consumer aligning media to neural data SHOULD order by `t_tick` rather
than rely on `frame_index`.

Whether `core.media_frames` should override §2 to sort by `(media_asset_id, t_tick)` —
following `core.events`, which sorts by time rather than identity for the same reason —
depends on access patterns no packet has yet exercised. Deferred.

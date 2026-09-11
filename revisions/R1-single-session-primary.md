# R1 — Single-Session Primary

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | Parts 01, 03 and 04 |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

The base specification never says whether a packet normally holds one session or many, and
its documents assume different answers:

- `01:51` — a packet is "a concrete representation of a dataset or dataset subset",
  permitting both.
- Part 03 — tables SHOULD be partitioned by `session_id`, and array and media paths are laid out
  as `session_id=<id>/`, assuming many.
- Parts 07 and 08 — every example and CLI invocation is `session_001.nwbpkt`, assuming one.

The ambiguity has to be resolved before a fixture packet can be built, because it decides the
fixture's shape, the manifest's resource entries, and whether partitioning is exercised at all.

## 2. Decision

**A packet normally represents one session. Multi-session packets are a conforming extension,
not the primary case.**

The portable profile is optimized for the single-session packet: one file per table, no
partitioning, relative URIs, readable without a server.

## 3. Impact on the schemas

The base schemas already support both cases. This decision changes no column and no key.

- `session_id` is a column on every session-scoped core table, present in single-session
  packets exactly as in multi-session ones. Cardinality differs; the schema does not.
- Primary keys are already session-scoped composites — `(session_id, trial_id)`,
  `(session_id, event_id)`, `(session_id, unit_id, sorting_run_id, curation_id)`. Adding
  sessions requires no key migration.
- Part 03 already makes partitioning a MAY: "Implementations MAY use partitioned Parquet datasets
  instead of single Parquet files for large tables." Single-file-per-table is therefore already
  conforming, and partitioning is the extension.
- The manifest already records which layout is in use, through `physical_profile` (`parquet`
  versus `parquet_dataset`) and the `partitioning` field. Readers resolve through the manifest,
  so the extension is invisible to client code.
- Part 08's single-session example already writes arrays to `arrays/session_id=s001/`, so
  directory conventions do not change either.
- `core.subjects` is keyed on `subject_id` alone and `core.devices.session_id` is optional.
  Both already span sessions.
- `core.source_files` and the three provenance tables are packet-scoped, not session-scoped,
  and are unaffected.

The only absent piece is §4.

## 4. Manifest session inventory

Part 04's required top-level fields include no list of sessions, so a reader must open Parquet to
learn what a packet contains.

The manifest MUST include a top-level `sessions` array naming every session in the packet:

```json
{ "sessions": ["s001"] }
```

Validation: the set MUST equal the distinct `session_id` values in `core.sessions`.

```sql
-- manifest.sessions_match_core  (error)
SELECT session_id FROM core_sessions
WHERE session_id NOT IN (SELECT unnest FROM manifest_sessions)
UNION ALL
SELECT unnest FROM manifest_sessions
WHERE unnest NOT IN (SELECT session_id FROM core_sessions)
```

For a single-session packet this is one string, and it lets a reader answer "what is in here"
from a small JSON file. For the multi-session extension it permits a catalog of packets to be
queried without opening any table.

## 5. Multi-session as an extension

A conforming multi-session packet:

- lists every session in `sessions` (§4);
- SHOULD partition large tables by `session_id`, declaring `physical_profile:
  parquet_dataset` and `partitioning: ["session_id"]` in the resource entry;
- keeps every schema, key, and validation rule unchanged.

Cross-session clock alignment is out of scope. Sessions relate to one another through
`core.sessions.session_start_time`, and through `tick_zero_utc` where R6 is adopted. Clocks
remain session-scoped, as Part 01 requires; `parent_clock_id` carries no same-session restriction,
so a packet requiring a shared reference clock may point at one, but no validation rule
requires or checks this.

## 6. Consequences for the fixture

Phase 0's fixture (Part 07) is a single-session packet: one session, one subject, one clock, two
trials, two units, and their spikes as `core.spike_events` (R5). It uses one Parquet file per
table and exercises no partitioning.

A second, small multi-session fixture SHOULD exist in the conformance corpus to exercise the
extension. It is not required for Phases 0–2.

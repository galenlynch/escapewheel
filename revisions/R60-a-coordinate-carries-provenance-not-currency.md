# R60 — A Coordinate Carries Provenance, Not Currency

| | |
|---|---|
| **Status** | **Proposed** |
| **Amends** | R58 §2.3 (currency within a basis) |
| **Depends on** | R9 (provenance is optional), R41 (currency), R58 (a coordinate declares its basis) |
| **Profile** | `nwb-lake-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

R58 §2.3 states that two histology registrations of one probe are alternatives, that both
coordinate tables gain a nullable `processing_run_id`, and that "R41 applies unchanged within one
`(frame, basis)`". Implementing it shows the last clause cannot hold.

R58 §2.1 keys `core.electrode_coordinates` on `(electrode_id, coordinate_frame,
coordinate_basis)`. Two registrations of one electrode in the CCF frame are both `measured`, so
they collide on that key and the second cannot be stored. R41 arbitrates between alternatives that
coexist; where the schema admits one row, there is nothing to arbitrate.

### 1.1 Two layers were conflated

Core already has a table where alternatives coexist, and it is keyed differently:

| | |
|---|---|
| `core.units` | key `(session_id, unit_id, sorting_run_id, curation_id)` — both run columns `required` |
| `core.sorting_runs` | `processing_run_id`, **nullable** |

The id that separates alternatives is a **domain** id, required and in the key. The link to
provenance is a separate column and is nullable, which is what keeps R9's promise that a packet
carrying no provenance is conforming.

R58 §2.3 asked one column to be both. A `processing_run_id` in the key would have to be required,
so every coordinate in every packet would need a `core.processing_runs` row — provenance as a MUST,
which R9 §5 declines.

## 2. Decision

### 2.1 The column is provenance

`core.electrode_coordinates.processing_run_id` and `core.unit_coordinates.processing_run_id` record
**which run produced this row**. They stay nullable and stay out of the primary key. A writer
**SHOULD** record one where it knows it, as R9 §3 asks of provenance generally.

### 2.2 Currency does not apply

R58 §2.3's claim that R41 applies within a `(frame, basis)` is **struck**. One coordinate exists per
electrode, frame and basis; re-registering a probe replaces it, and R32 §2 versions the packet that
holds the replacement. A consumer never chooses between two coordinates of one basis, because a
packet never offers two.

R58 §2.3's decomposition survives the strike and is what remains true: `coordinate_basis` separates
different questions and is never superseded, while a later registration answers the same question
and replaces its predecessor rather than joining it.

### 2.3 What admitting alternatives would cost

Recorded so a future revision prices it rather than rediscovering it. Coexisting registrations need
a domain id in the key, on `core.units`' precedent — a `registration_id`, required, referencing a
new `core.registrations` table that R7 would require a key for and R46 a reference to. That is one
table and one column per coordinate row, and it is not built here because no measured session has a
second registration: both sessions in R58 §1.1 carry exactly one CCF estimate per electrode.

R43's test applies. Machinery for a case no data exhibits is machinery built to make something safe
rather than useful, and R42 records what happens to it.

## 3. What this does not change

- **No column is added or removed.** `processing_run_id` stays exactly as R58 §2.3 defined it;
  what changes is the claim about what it enables.
- **No key changes.** R58 §2.1's keys stand.
- **No change to `coordinate_basis`.** R58 §2.1 and §2.2 are untouched, including the rule that an
  unrecognised basis MUST NOT be read as `measured`.

## 4. Open

- **Whether a replaced coordinate should be traceable.** R32 §2 retains the manifest of every
  version, so an earlier registration is recoverable from an earlier version of the packet, but
  nothing links the two rows. `core.curation_versions.parent_curation_id` is the shape that would
  do it. Left until someone needs the lineage rather than the current value.

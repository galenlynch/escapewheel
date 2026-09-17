# R7 — Table Uniqueness Rules

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `02_core_logical_schemas.md` |
| **Blocks** | R2 content generation |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`02:13` requires that every core table declare "a primary key or uniqueness rule". Seven of
the 22 tables it defines declare neither. R5 §2 supplies one for `core.spike_events`; the
remaining six are resolved here.

A registry entry (R2 §6) cannot omit the field, and Tier 1 generation (R2 §7.1) emits a
uniqueness check per declared key, so an undeclared key silently removes a check rather than
producing an error.

## 2. Rule

Every core table MUST declare either a primary key or, explicitly, that it has none.

`primary_key` is an array of column names. A table that admits duplicate rows declares
`primary_key: null` and MUST state the reason in its description. Omitting the field is not
permitted.

No table defined by this specification declares `primary_key: null`. The representation
exists so that a future table admitting duplicates is distinguishable from one whose key was
forgotten.

## 3. Resolutions

### 3.1 Single-column keys

Five tables carry an explicit identifier column, already required and already named as a
stable ID by Part 01:

| Table | Primary key |
|---|---|
| `core.media_assets` | `media_asset_id` |
| `core.processing_runs` | `processing_run_id` |
| `core.source_files` | `source_file_id` |
| `core.provenance_activities` | `activity_id` — withdrawn by R9 |
| `core.provenance_entities` | `entity_id` — withdrawn by R9 |

These match the pattern Part 02 already uses for `core.devices`, `core.probes`,
`core.electrodes`, `core.clocks`, `core.sorting_runs`, and `core.curation_versions`.

`core.source_files` deserves one note: the key is `source_file_id`, not `uri`. The same URI
may be imported more than once — at different times, or with different checksums after the
source was modified — and each import is a distinct source file record. `uri` is therefore
not unique and MUST NOT be treated as a key.

### 3.2 `core.provenance_edges` (withdrawn by R9)

R9 withdraws this table. The analysis is retained because it applies to any edge table a
later revision reintroduces.


| Table | Primary key |
|---|---|
| `core.provenance_edges` | `(source_entity_id, activity_id, target_entity_id, relationship_type)` |

This is the full set of required columns; the only other column is `metadata`.

An edge asserts that one entity stood in a stated relationship to another through a given
activity. That assertion is fully described by its endpoints, its activity, and its
relationship type. A repeated quadruple carries no information the first does not, so
provenance is a graph rather than a multigraph and the quadruple is unique.

Any information that would distinguish two otherwise identical edges belongs in a column, not
in `metadata`, and would require a schema revision that extends the key accordingly.

## 4. Consequences

Tier 1 generation (R2 §7.1) gains a uniqueness check per table, one for every core table.
R9 withdraws three of the tables keyed here and adds `core.processing_run_inputs`, keyed
`(processing_run_id, source_file_id)`.

Uniqueness checks are `error` level. A duplicate primary key indicates either a writer defect
or a merge that combined records from different contexts, and neither yields interpretable
data.

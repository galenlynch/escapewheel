# R9 — Provenance Simplification

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `01`, `02`, `04`, `05`, `09` |
| **Supersedes** | R7 §3.1 (in part), R7 §3.2 |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

The provenance layer has five tables and four defects.

**`core.provenance_activities` restates `core.processing_runs`.** Its non-key columns —
`activity_type`, `started_at`, `ended_at`, `status` — all exist on `core.processing_runs`,
and `processing_run_id` is a foreign key to the table being restated. `05` Stage 6 confirms
they are written in pairs. This is the failure R3 §3.0 rules out: duplication where reading
the source is a join.

**`core.provenance_entities` restates `core.source_files`.** An entity with
`entity_type: source_file` duplicates `uri` and `sha256` from a `source_files` row. `01`
lists "source NWB file" as a ProvenanceEntity example, so this is the expected case.

**The edge vocabulary does not match the edge shape.** `relationship_type` offers "used,
generated, derived_from, validated, etc.", but `used` and `generated` are entity-to-activity
relations, while `core.provenance_edges` is entity-to-entity through an activity. Only
`derived_from` fits the table it is declared on.

**The requirement level is contradictory.** `01:25` and `09` §4.7 say a packet MUST record
enough provenance to trace; `05` Stage 6 — the only place stating what to write — says
SHOULD. The MUSTs have no mechanism.

Underlying all four: no importer exists, so nothing has exercised this layer. Every other
decision in R1–R8 rests on measurement; this one cannot yet.

## 2. Decision

The generic entity/activity/edge graph is withdrawn. Provenance is recorded as what came in,
what ran, and which run produced each resource.

| Table | Disposition |
|---|---|
| `core.source_files` | kept — the inputs |
| `core.processing_runs` | kept — what ran, with software, version, parameters, status |
| `core.processing_run_inputs` | **new** — which source files fed which run |
| `core.provenance_entities` | **withdrawn** |
| `core.provenance_activities` | **withdrawn** |
| `core.provenance_edges` | **withdrawn** |

Five tables become three. The full ledger for R2 content generation, superseding R4 §7's
count, which was accurate before this revision:

```text
02 as written                                     22
R5 §3   − core.unit_spike_chunks                  21
R3 §3.1 + core.session_experimenters              22
R3 §3.2 + core.trial_tags                         23
R3 §3.3 + core.array_dimensions                   24
R9 §2   − core.provenance_entities                23
R9 §2   − core.provenance_activities              22
R9 §2   − core.provenance_edges                   21
R9 §3   + core.processing_run_inputs              22
                                                  --
registry content                                  22
```

The return to 22 is coincidental. This revision is a net removal of two tables, not a
no-op: `02`'s 22 and the registry's 22 name different sets.

Reproduce with `python3 conformance/spec-sweep/tables.py`.

The semantic concepts in `01` survive; only the generic encoding is withdrawn. A
ProvenanceActivity is a `core.processing_runs` row. A ProvenanceEntity is a
`core.source_files` row or a packet resource. Nothing needs a node table to be one of those.

## 3. New table: `core.processing_run_inputs`

| Field | Type | Required | Description |
|---|---|:---:|---|
| `processing_run_id` | string | yes | The run. |
| `source_file_id` | string | yes | A source file the run consumed. |

Primary key: `(processing_run_id, source_file_id)`.

References: `processing_run_id` -> `core.processing_runs`; `source_file_id` ->
`core.source_files`.

A run consumes zero or more source files, so this is R3 §3.0's multiplicity rule.

## 4. Outputs are recorded in the manifest

Which resources a run produced is resource-level, not row-level, and `04` already carries it:
resource entries have `derived_from` and `activity_id`.

`activity_id` is renamed `processing_run_id` and references `core.processing_runs`.
`04`'s provenance block field `import_activity_id` becomes `import_processing_run_id`.
The block's `entities_resource`, `activities_resource`, and `edges_resource` fields are
struck along with the tables they name.

Resource-level granularity is the right one. Nothing in the specification asks which
individual row came from which input, and no consumer has been identified that would.

## 5. Requirement level

`01:25` is amended from MUST to SHOULD:

> Every imported core resource SHOULD be traceable to source data or source activities.

`09` §4.7 is amended to match. `05` Stage 6 already says SHOULD and is unchanged.

**Consequence, stated plainly: a packet carrying no provenance is conforming.** This is a
deliberate weakening. Provenance is valuable for reproducibility, but requiring it makes
import fail on packets that are otherwise complete and usable, and the specification's
stated priority (`09` §4.7) is reproducibility over process modelling — not process
modelling as a precondition.

Where provenance is recorded, the rules in §3 and §6 apply. Optional does not mean
unvalidated.

## 6. `activity_type`

`core.processing_runs.activity_type` is required and declares "import, validation, sorting,
curation, materialization, etc."

Declared open on R8 §4's terms: a validator MUST NOT reject an unrecognized value, and the
five listed values are reserved with those meanings. Closing it would require knowing the
processing steps real pipelines perform, which Phase 3 will establish.

`entity_type` and `relationship_type` are withdrawn with their tables and need no
resolution.

## 7. What this gives up

Recorded so the trade is explicit rather than discovered later.

- **Multi-hop lineage within tables.** A → B → C chains are expressible only through the
  manifest's `derived_from`, at resource granularity.
- **Row-level lineage.** Which spike came from which file is not recoverable. Nothing in
  the specification requested it.
- **Arbitrary relationship types.** Only "this run consumed this file" and "this run produced
  this resource" are expressible.
- **PROV interoperability.** A packet no longer maps mechanically onto a PROV graph.

## 8. Reversibility

Restoring the general model is additive: three tables and a manifest field, breaking no
existing packet, on the same grounds R3 §3.1 records for adding child tables.

Carrying the general model is not free — every implementation writes and validates five
tables, two of which duplicate others, against a shape no importer has exercised. The
asymmetry is why the simplification is the safer default for the proof of principle.

If Phase 3 shows a real pipeline needs a general graph, R9 is reverted with better evidence
than exists now.

## 9. Effect on R7

R7 §3.1 assigns primary keys to `core.provenance_activities` and `core.provenance_entities`,
and R7 §3.2 to `core.provenance_edges`. All three tables are withdrawn here, so those
assignments lapse. R7's remaining assignments — `core.media_assets`,
`core.processing_runs`, `core.source_files` — stand, joined by
`core.processing_run_inputs` (§3).

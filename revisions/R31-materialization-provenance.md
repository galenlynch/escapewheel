# R31 — Materialization Provenance Has a Vehicle

| | |
|---|---|
| **Status** | **Accepted** 2026-08-28 |
| **Amends** | `06_analysis_layer.md` §13, §171 |
| **Depends on** | R9 (provenance simplification), R12 (what belongs in the shim), R14 (external resources) |
| **Forces** | R30 §3.1, which requires a bucket width to be declared as a transform parameter |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`06` §13 requires every analysis resource to declare its transform parameters and software
version, and §171 says where:

> A materialization activity MUST record:
> `activity_id`, source resources, source validation state or source packet release,
> code version, `parameters`, `created_at`, output `resource_id`, output validation status.

**R9 withdrew the activity graph.** "A materialization activity" names a thing the format no
longer has, so `06` §171 mandates a record with no vehicle, and §13's MUST cannot be satisfied
by any conforming packet. This was found by implementation: the reference writer records only
the manifest's `derived_from`, because there was nowhere else to put anything.

Nothing new is needed to fix it. Every field §171 lists already exists, split across the two
places R9 left provenance in — `core.processing_runs` for what ran, and the manifest for what
it produced. This revision says so.

## 2. Replacement

**Strike** `06` §171's list and the sentence introducing it, and replace with:

> A materialization is recorded as a row in `core.processing_runs` with `activity_type` set to
> `materialization`, named by the produced resource's `processing_run_id` in the manifest.
> `activity_type` is an open vocabulary (R9 §6), so a writer MAY use a narrower value.

The mapping from what `06` asked for to what a packet carries:

| `06` §171 | Where it lives |
|---|---|
| `activity_id` | `core.processing_runs.processing_run_id` |
| source resources | the resource entry's `derived_from` |
| source validation state or source packet release | each source's `validation_state` in the same manifest; for an external source, R14's `sha256` and `verified_at` |
| code version | `software_name`, `software_version`, `code_uri` |
| `parameters` | `core.processing_runs.parameters` |
| `created_at` | `started_at` and `ended_at` |
| output `resource_id` | the resource entry carrying this `processing_run_id` |
| output validation status | that entry's `validation_state` |

`processing_run_id` is already a manifest resource field; `04` defines it and nothing was
writing it. R31 gives it its first required use.

## 3. What an analysis resource MUST carry

An analysis resource MUST set `processing_run_id`, and the run it names MUST exist in
`core.processing_runs`. That run MUST carry `software_name` and `software_version`, and MUST
carry `parameters` unless the transformation takes none.

`parameters` is a `json_string` column, which R3 §2.1 confines to optional columns — satisfied,
since a reader that cannot parse JSON can still read every required column of the table. The
parameters are not queryable and are not meant to be: they are a record of what was run, and a
packet that wants one of them queryable should promote it to a column through a schema
revision, as `06` already requires of any analysis fact.

A transformation "takes no parameters" is a strong claim and usually false. R30's bucket width
is the example: it is not recoverable from the data, because a table whose buckets all happen
to be non-empty looks the same at 300 s as at 299 s.

## 4. MUST and SHOULD are about different claims

R9 made provenance SHOULD, and `06` §13 makes it MUST. Both stand, because they are not the
same requirement.

- R9's SHOULD covers **acquisition**: what files came in, what ran over them. A packet that
  says nothing about where its raw data came from is conforming.
- `06` §13's MUST covers **derivation**: how a resource in this packet was computed from
  another resource in this packet. A packet that carries a derived resource and does not say
  how it was derived is not conforming, because the resource is disposable and regenerating it
  is the recovery path — and a recipe you cannot read is not a recipe.

So a packet with no analysis resources needs no `core.processing_runs` at all, and a packet
with one needs a row per derived resource. Nothing requires the two kinds of run to be
distinguishable beyond `activity_type`.

## 5. Validation

The claim is manifest-to-table and therefore **not** SQL. A Tier 1 foreign key runs between two
tables; `processing_run_id` lives in the manifest, which no query sees. R12 §4 puts exactly
this case in the shim: a validator MUST check that every analysis resource declares a
`processing_run_id`, and that the value appears in `core.processing_runs.processing_run_id`.

A rule written in SQL here would pass silently on a packet whose manifest names a run that does
not exist, which is the failure mode R12 was written about.

## 6. What this does not do

- **No new column, table, or manifest field.** Everything named already exists.
- **No change to `06` §11's lineage rule.** `derived_from` remains where source resources are
  declared; §2's table records what §171 asked for on top of that.
- **No requirement that a materialization be reproducible in practice.** `06` says analysis
  resources SHOULD be reproducible from core, and recording the parameters is what makes that
  possible, not what makes it true. A run whose `code_uri` has since disappeared is still a
  conforming record of what happened.
- **No treatment of stale derivations.** `06` says a dependent analysis resource SHOULD be
  invalidated when its sources change, and nothing here detects that.

## 7. Open

- **Whether `parameters` should have a declared shape.** It is free-form JSON, so two writers
  can record a bucket width under two different keys and neither is wrong. A convention would
  make materializations comparable across packets; a schema for it would be an extension
  registry under R17, and nothing needs it yet.
- **Whether the run should record what it dropped.** R30 §4 lets a materialization omit rows
  it cannot place, and the count is a quality signal with no home. `parameters` is the wrong
  place — it is what went in, not what came out — and a `results` column does not exist.

# R2 — Schema Registry Format

| | |
|---|---|
| **Status** | **Accepted** 2026-08-26 |
| **Amends** | `03_portable_physical_profile.md`, `04_packet_catalog_manifest.md` |
| **Depends on** | R3 (type floor, §3.0 principles), R4 (reconciled column set) |
| **Scope** | Format only. The registry *content* is a separate artifact; R9 §2 has the table ledger. |
| **Profile** | `escapewheel-portable-v0.1` |

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Motivation

`03:76` lists `schemas/logical_schemas.json` in the packet layout and never defines it.
`03:75` does the same for `semantic_version.txt`. This revision defines both.

Two problems make the definition necessary rather than tidy:

**Schemas are prose.** Part 02 expresses its table schemas as markdown tables. No program reads
them, so each implementation transcribes them by hand.

**Validation rules are prose and scattered.** They appear in Part 02's per-table Validation
sections, Part 05's validator taxonomy, Part 08's checklist, and Part 09's ordering. Independent
implementations derive checks from English text and diverge, after which conformance is
defined by whichever validator was run.

R4 records the cost of the same failure at schema level: five fields named in one document
and absent from another, undetected until a mechanical sweep.

## 2. Two artifacts

This revision defines the **format**. The **content** — the registry for the tables in R9
§2's ledger — is generated against that format and versioned as its own artifact.

The format is normative and changes rarely; the content changes whenever a schema does.
Embedding the content in a revision document would make every schema edit a specification
amendment.

## 3. Registry document

The registry is a single JSON document. Structure:

```json
{
  "registry_version": "0.1.0",
  "semantic_standard_version": "escapewheel-semantic-v0.1",
  "logical_standard_version": "escapewheel-logical-v0.1",
  "tables": {
    "core.trials": {
      "schema_id": "core.trials.v0.1",
      "layer": "core",
      "semantic_type": "Trial",
      "description": "One row per trial.",
      "columns": [
        {"name": "session_id",   "type": "string", "presence": "required",
         "description": "Session ID."},
        {"name": "trial_id",     "type": "string", "presence": "required",
         "description": "Stable trial ID."},
        {"name": "start_tick",   "type": "int64",  "presence": "required",
         "description": "Trial start tick."},
        {"name": "stop_tick",    "type": "int64",  "presence": "required",
         "description": "Trial stop tick."},
        {"name": "clock_id",     "type": "string", "presence": "required",
         "description": "Clock for start/stop ticks."},
        {"name": "condition_id", "type": "string", "presence": "nullable",
         "description": "Experimental condition."},
        {"name": "metadata",     "type": "json_string", "presence": "optional",
         "description": "Additional trial metadata."}
      ],
      "primary_key": ["session_id", "trial_id"],
      "references": [
        {"columns": ["session_id"], "resource": "core.sessions",
         "resource_columns": ["session_id"]},
        {"columns": ["clock_id"], "resource": "core.clocks",
         "resource_columns": ["clock_id"]}
      ],
      "sort": ["session_id", "trial_id"],
      "rules": [
        {"id": "core.trials.interval_valid", "level": "error",
         "message": "trial stop_tick precedes start_tick",
         "sql": "SELECT session_id, trial_id FROM core_trials WHERE stop_tick < start_tick"}
      ]
    }
  }
}
```

`columns` MUST be an array, not an object. Column order is meaningful for generated DDL and
for human reading, and JSON object key order is not guaranteed across parsers.

`tables` is keyed by resource ID (dotted). SQL identifiers substitute underscores, as Part 08
already does — `core.trials` is queried as `core_trials`.

## 4. Column types

The `type` vocabulary is exactly R3 §2.1's Arrow-compatible primitive set:

```text
string   int32   int64   float32   float64   bool   date   timestamp   json_string
```

`json_string` is a `string` at the physical layer, distinguished so a generator can emit a
parsed type where a language has one, and so validation can require the column be optional
per R3 §2.1. No other type is permitted; nested types are forbidden by R3 §2.1 and repeated
values are child tables by R3 §3.0.

Array data types are NOT expressed here. A Zarr array declares its own `data_type` and both
target languages read it identically (R3 §3.0, §7.3).

## 5. Presence — three states

Part 02 says "prefer present nullable columns over absent columns," which implies three states,
not two. A boolean `required` flag cannot carry them.

| `presence` | Column present? | Values null? |
|---|---|---|
| `required` | MUST be | MUST NOT be |
| `nullable` | MUST be | MAY be |
| `optional` | MAY be absent | MAY be |

A reader MUST tolerate an absent `optional` column. A writer SHOULD emit `nullable` columns
even when every value is null, so that query code need not branch on column existence.

## 6. Keys, references, ordering

`primary_key` is an array of column names, composite where Part 02 declares a composite. The
generated uniqueness check follows from it. A table admitting duplicate rows declares
`primary_key: null` with the reason in its description; omitting the field is not permitted
(R7 §2).

`references` express foreign keys. Composite references are supported because Part 02 uses
them — `core.spike_events` references `core.units` on four columns.

`sort` records the physical ordering a writer SHOULD apply, from Part 03. It is a performance
property, not correctness, and generates a warning-level check rather than an error.

## 7. Validation rules

### 7.1 Tier 1 — generated from structure

Not written by hand, for any table. A generator emits, from §3's structure alone:

- required column present; type matches
- `required` columns contain no nulls
- `primary_key` is unique
- every `references` entry resolves (anti-join)
- physical order matches `sort` (warning)

That is most of Part 05's check taxonomy, across every table, with no per-table authoring.

### 7.2 Tier 2 — SQL for what structure cannot imply

Written once, in the registry, as SQL. Examples already established: R5 §7's spike ordering
and resolution checks, R5 §4's `core.units` summary consistency, R6 §3's clock plausibility
bounds, R1 §4's manifest session inventory.

### 7.3 Execution contract

**A rule's query returns the offending rows. An empty result is a pass; a non-empty result
is a failure, and the returned rows are the finding.**

That is the entire contract. It requires no expression language, no per-language rule
interpreter, and no custom result protocol.

`level` is `error`, `warning`, or `info`, matching Part 05's error policy.

### 7.4 Why SQL

DuckDB reads Parquet natively and has bindings in Python, Julia, R, Rust, C++, and JS, so one
rule set executes in each with no FFI and no compiled dependency. R3's decisions make this
practical: with no nested types every check is relational SQL, and with a flat spike table
(R5) tick ordering is a window function rather than a list traversal.

DuckDB is required for validation. It is not required for reading: R3 §2.1's prohibition on
nested types keeps Parquet2.jl a working native Julia read path (R3 §7.3). The two
requirements MUST remain separable.

## 8. Versioning

The registry carries one `registry_version`. Per-table `schema_id` values are derived from
it, not managed independently: at registry version `0.1.0`, `core.trials` has `schema_id`
`core.trials.v0.1`. This matches the IDs Part 04 already uses in resource entries.

A packet MUST record the registry version it was written against, and SHOULD embed the
registry itself at `schemas/logical_schemas.json` so the packet is self-describing. A packet
whose embedded registry disagrees with its recorded version is invalid.

`schemas/semantic_version.txt` (`03:75`) contains the semantic standard version string and
nothing else.

## 9. The registry's own schema

The registry document MUST itself validate against a JSON Schema — a meta-schema — published
alongside it. This lets any JSON Schema tooling check a registry before anything consumes it,
and gives generators a contract to code against.

This is a different job from the packet manifest's JSON Schema (§10), and the two MUST NOT
be conflated: one describes the shape of a registry, the other the shape of
`packet.json`.

## 10. Manifest JSON Schema

`packet.json` is a JSON document whose contract Part 04 gives only by example. This
revision requires a JSON Schema for it, covering Part 04's required and recommended fields plus
those added by accepted revisions — `required_codecs` (R3 §7.2) and `sessions` (R1 §4), and
minus `canonical_representations` (R5 §6).

JSON Schema's own type system is too coarse for column types — it has `integer`, not `int32`
versus `int64`, and no timestamp precision. Column types are therefore values inside the
registry with a pinned enum (§4), never JSON Schema types. JSON Schema validates document
*shape*; the registry supplies column *semantics*.

## 11. Generation targets

The format is a flat map of table to `{columns, primary_key, references, sort, rules}`, with
columns as an ordered array of uniform records, so that emitters require no special-case
handling.

The registry's function does not depend on generation. Its primary purpose is to be the
single machine-readable statement of what a conforming table is, so that independent
validators cannot diverge. Generation is a secondary consequence.

Generation targets are not specified by this revision. Their value differs by an order of
magnitude and is recorded here so that effort is directed accordingly:

| Target | Volume | Note |
|---|---|---|
| Tier 1 rule SQL | ~230 checks | §7.1; the case for generation |
| SQL DDL (`CREATE TABLE`) | one per table | builds the DuckDB validation environment |
| Arrow/Parquet write schemas | one per table | enforces types and presence at write time rather than at validation time |
| Python types | ~250 lines | convenience; the tables are primitives and hand-writing is cheap |
| Julia types | ~250 lines | as above |
| Per-table JSON Schema | one per table | for languages with no first-party client |
| Markdown schema tables | one per table | regenerates Part 02-style documentation |

The ~230 figure is 196 column presence and type checks, 15 primary-key uniqueness checks, and
19 foreign-key anti-joins, counted from Part 02. Seven Tier 2 rules have been written by hand so
far. Generating language types saves little; generating the rules avoids maintaining ~230
checks per implementation with nothing detecting divergence between them.

Generating the markdown schema tables would prevent the drift R4 corrects, rather than
correcting it once. `nwb_lake_poc_docs/` is frozen, so this applies to a future specification
version rather than to Part 02.

Field naming follows Frictionless Table Schema where the concepts coincide (`primary_key`,
foreign key `resource`/`fields`, per-field constraints). This revision does not claim
conformance to that standard: its type system lacks the width distinctions R3 §2.1 requires,
and it has no representation for SQL rules.

## 12. Deliberately excluded

- **A rule expression language.** SQL is the expression language.
- **Codegen output specifications.** §11 lists targets; emitters are implementation.
- **Analysis-layer schemas.** Part 06's tables are derived and their shapes depend on
  materialization parameters. Core first.
- **Extension schemas.** Part 09 §5 requires only that declared extension files exist.

## 13. Open

- Whether Tier 2 rules should be inline in `rules` as shown, or in a sibling document
  referenced by ID. Inline keeps a table's contract in one place; separate keeps the registry
  readable as pure structure. Decide when the content artifact is generated.
- Where the generated registry artifact is versioned — alongside the revisions, or in its own
  repository beside the reference implementation.
- Expressing R4 §4's conditional requirement (`tick_rate_hz` XOR `tick_rate_num` +
  `tick_rate_den`). It is a cross-column predicate that `presence` cannot carry, so it must
  be a named Tier 2 rule; whether the registry should also mark the columns as
  conditionally-required for documentation purposes is unsettled.

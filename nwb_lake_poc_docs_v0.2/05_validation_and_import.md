# Part 05 — Validation and Import

Normative.

## 1. Core principle

**Validation is importation.** Copying bytes into a packet directory is staging, not import.

A resource is imported when it has been discovered, extracted to staging, normalized to the logical schemas, validated, committed, and recorded in the catalog with its provenance.

A staged resource MUST NOT appear in the catalog as a committed canonical resource. Nothing becomes core data before it has passed the validators that apply to it.

## 2. Pipeline

| stage | action |
|---|---|
| 1 | discover what each source offers |
| 2 | extract candidate resources to staging |
| 3 | normalize to the logical schemas |
| 4 | validate the staged resources |
| 5 | commit |
| 6 | record provenance |
| 7 | materialize analysis resources |

An importer MUST NOT combine parsing, normalization, validation, and writing into one opaque step. A source adapter returns records; it MUST NOT write files.

## 3. The session recipe

### 3.1 Purpose

One source is rarely sufficient: integer sample indices come from a sorter, task structure and registration from an exported file, and session identity from acquisition metadata. The unit of work is therefore a **recipe** naming several sources, not a single input file.

A recipe declares, for one packet:

- each source: its kind, its root, and its options;
- which resources each source supplies;
- the clocks the packet declares, and their parents;
- what to materialize;
- session and subject facts no source carries.

### 3.2 The recipe is the provenance record

A recipe MUST be recorded in the import run's parameters, and its digest MUST be recorded as the run's `code_uri`. A committed packet therefore states what produced it.

### 3.3 Ownership

Each source declares its resources as `owns` or `contributes`.

| declaration | meaning |
|---|---|
| `owns` | this source is solely responsible; records another source emits for the resource are discarded |
| `contributes` | this source adds rows alongside others |

`contributes` exists because some resources genuinely have several suppliers. Without the distinction, the last adapter to run wins silently.

### 3.4 What a source can produce

Every source adapter MUST declare `PRODUCES`, the set of resource identifiers it can supply (R63 §2.1). It is static: a property of the adapter, readable with nothing open, and distinct from what a particular source root happens to hold.

A source entry that declares no `owns` MUST be read as owning every resource in its adapter's `PRODUCES` that no other source owns (R63 §2.2). **A recipe states what it narrows; silence means the whole.**

Where two sources default to the same resource and no preference is declared, the recipe MUST be refused naming both.

### 3.5 Checking a recipe

A recipe MUST be checked against the registry before any source is opened. The check MUST refuse:

- a resource owned by more than one source;
- an owned resource the registry does not define;
- an owned table whose **required** foreign key targets a table nothing supplies;
- a clock declared twice, referenced but absent, or parented to nothing;
- a required source option that is not set.

The check MUST report as a **warning**:

- an owned table whose **nullable** foreign key targets a table nothing supplies;
- a resource some listed source declares in `PRODUCES` that no source claims (R63 §2.3).

A warning is not an error because narrowing is legitimate, and only the recipe's author knows whether this one was meant.

## 4. Stages 1 to 3

### 4.1 Discover

For each source, report what it offers per resource, and how many rows. Discovery MUST NOT write to the packet.

### 4.2 Extract

Copy or stream candidate resources into a staging area under the packet root. A table whose row count is large MUST be streamed rather than materialized as host objects.

### 4.3 Normalize

Map source objects onto the logical schemas: assign identifiers packet-wide before any table is written (R53 §2.5), apply the declared sort, and coerce types to the registry's.

Normalization MUST be deterministic in the recipe. Two runs of the same recipe over the same sources produce the same packet.

An interval is closed (01 §2.3). A source whose intervals are half-open — `[start, stop)` — MUST be converted, which is a subtraction on the stop bound. A writer MUST NOT carry a half-open bound through unchanged.

An adapter compensating for a known defect in its source MUST declare the compensation, and every compensation applied MUST be recorded in the import run's parameters. Choosing not to correct a known defect is equally a compensation and is declared as a pass-through.

## 5. Stage 4: Validate

### 5.1 Tier 1

Generated from structure (Part 02 §10.1): required-column non-null, primary-key uniqueness, foreign-key anti-joins, closed-vocabulary membership.

### 5.2 Tier 2

Declared per table as SQL returning offending rows, or as an expanded template (Part 02 §10.2).

### 5.3 The shim

Physical order, file presence, Parquet types, Zarr rank and codecs, and checksums MUST be checked outside SQL (R12 §4). A query cannot observe them, so such a check written as SQL fails silently rather than loudly.

### 5.4 Extensions

Each extension registry present is validated on the same terms as core, and its verdict is reported separately (R17 §4). A core failure MUST NOT be attributed to an extension, and an extension failure MUST NOT invalidate core.

## 6. Stage 5: Commit

Commit MUST be atomic with respect to a concurrent reader:

1. write the staged resources;
2. validate them;
3. write a **candidate** manifest;
4. move resources into their final paths;
5. rename the candidate to `nwb.packet.json` **last**.

A commit that finds an error MUST NOT write a manifest at the packet root, and SHOULD leave staging in place for inspection.

## 7. Stage 6: Provenance

Record `core.source_files` for the inputs, one `core.processing_runs` row for the import, and `core.processing_run_inputs` linking them. The run declares its `scope` and `scope_kind` (R44 §2, R49 §2).

## 8. Stage 7: Materialize

Materialization runs inside the import: core is staged, the staged packet is opened, derived resources are computed from it, and everything is validated together before anything is promoted.

Deriving into an already-committed packet is an amendment (03 §9.1), not part of an import.

## 9. Reporting

### 9.1 Findings

A finding declares a level, the check that produced it, and a message. Where a check is a query, the offending rows are the finding.

| level | meaning |
|---|---|
| `error` | the packet does not conform |
| `warning` | conformant, but likely not intended |
| `info` | recorded, not judged |

### 9.2 Error policy

An import MUST refuse to commit on any error.

A validator MUST NOT downgrade an error to make a packet pass. An advisory rule MUST NOT be an error (Part 02 §10.2), so enabling advisory checks cannot change whether a packet previously passed.

### 9.3 Comparison against a prior packet

Where an import replaces an existing packet, it SHOULD report every resource the prior catalog declared that the new one does not. This is a warning: narrowing is legitimate, and no other check sees a resource that is simply absent.

## 10. Minimum acceptance criteria

An importer conforms when it:

1. refuses a recipe that cannot produce a valid packet, before opening any source;
2. produces a packet that passes Tier 1, Tier 2, and the shim;
3. records provenance for what it read and what it ran;
4. leaves no manifest at the packet root when it refuses;
5. produces byte-identical output from two runs over the same sources.

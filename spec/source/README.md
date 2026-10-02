# Schema registry

`../artifacts/logical_schemas.json` is the incorporated core registry: the machine-readable
declaration of core and analysis resources under [Part 02](../parts/02_core_logical_schemas.md).
This directory holds its source, `core/`, and this guide to it. A packet binds the registry as
registry `core`, stored at `registries/core/<version>.json.gz` (Part 04 §8, Part 03 §3.3).

<!-- BEGIN generated: counts -->
```
51 resources, 47 tables, 367 columns, 117 references, 91 Tier 2 rules
```
<!-- END generated: counts -->

`../informative/tables.md` is the same content as Markdown, rendered by `tools/render.py` at build
time. Read it to see the exact declarations; read Part 02 for their current meaning. Accepted
revisions preserve history and rationale but are not current normative owners.

The tree's other artifacts lie beside the registry in `../artifacts/`, and the example documents
the tools validate against them lie in `../informative/`:

| File | Contents |
|---|---|
| `logical_schemas.json` | The registry. Bound by packets as `core` at `registries/core/<version>.json.gz`. |
| `registry.schema.json` | Incorporated local-shape schema for core and extension registry documents. |
| `registry_result.schema.json` | Closed portable representation of a complete registry-document result. |
| `registry_contract.schema.json` | Incorporated closed shape of a registry-contract descriptor. |
| `registry_contracts/escapewheel-registry-contract-v0.9.json` | Incorporated phase, invariant, applicability, and prose-owner index. |
| `rule_language.schema.json` | Closed schema for a rule-language profile. |
| `rule_languages/escapewheel-rule-sql-v0.2.json` | Exact incorporated portable Tier 2 language profile. |
| `manifest.schema.json` | Incorporated closed schema for `packet.json` (Part 04). |
| `physical_profile.schema.json` | Incorporated closed shape of a physical-profile descriptor (Part 03 §1). |
| `physical_profiles/escapewheel-portable-v0.1.json` | The portable profile's descriptor: its interfaces, reader floors, and the table interface's `overriding_orders` (Part 03 §5.4). |
| `resources.schema.json` | Incorporated delivery schema (Part 12 §5). **Generated** by `tools/build.py` from the manifest's resource entry. |
| `adapter.schema.json` | Incorporated schema for an adapter's declaration document (Part 12 §7). |
| `sources.schema.json` | Incorporated schema for a source resolution document (Part 04 §5.5). |
| `recipe.schema.json` | Incorporated schema for a session recipe's decoded TOML (Part 05 §3.1). |

Each of `../informative/resources.example.json`, `adapter.example.json`, `sources.example.json` and
`recipe.example.toml` is a document that `tools/check.py` validates against its schema.

A package copies the artifacts and checkers it uses from the tree, since a wheel cannot read a file
from another distribution, and checks that each copy agrees with its source. The monorepo's
contributing guide describes the copies; edit the tree's file and never a copy.

## Where the registry comes from

`logical_schemas.json` is **generated. Do not edit it.** `tools/assemble.py` writes it from a
directory of TOML, and an extension outside the tree is assembled from its own directory by the
same module:

```
core/registry.toml + core/<resource_id>.toml   ──assemble.py──> ../artifacts/logical_schemas.json
```

`registry.toml` holds the document's own fields and each other file declares one resource, in the
published format's keys. A file differs from the document only in spelling, so reading one needs
nothing beyond Part 02: a table's fields sit at the top of its file rather than under `table`, a
single-column reference is written on its column, and a rule may invoke the `interval` template,
which `assemble.py` expands into plain SQL. `canonical.py` fixes the document's key and reference
order, so how a file orders them changes nothing, and `tools/check.py` refuses a table whose
`session_id` does not lead or whose `metadata` does not close it.

Why a declaration is as it is lives in the accepted revisions and in Git, not in the source:
`revisions/registry-targets.toml` locates each accepted clause in the generated document. Before
the source existed, `build.py` generated the core registry by replaying the accepted revisions
over the frozen Part 02, and `git show 0c8fa3e:registry/build.py` recovers that replay.

Within the tree, `uv run --project tools python tools/build.py` rebuilds the registry and
`uv run --project tools python tools/check.py` checks it. From the monorepo root,
`uv run --project escapewheel-writer python verify.py --quick` also checks the extensions and the
packages' copies; without `--quick` it runs the package tests as well.

`tools/check.py` verifies that the document is what its source assembles to, and statically checks
every Tier 2 rule against the selected profile.

`tools/render.py` writes `tables.md` and fills this file's generated regions. Every count below is
one of those: a number stated in prose is a number that goes stale, which this file
demonstrated by claiming 33 tables and 51 rules against a registry holding 34 and 61.

## What `tools/check.py` verifies

`tools/check.py` requires the core registry to return the one complete result defined by Part 02
§9.4. It then checks authoring conventions and generation invariants that are intentionally not
packet-conformance rules, including source-to-document agreement, column order, naming
exceptions, each artifact's schema, and current development identities. Tier 2 rules pass the
Part 11 static contract here; executing them against empty typed relations needs an engine the
tree does not declare, so the monorepo does that outside it.

## What it produces

Tier 1 checks are generated from structure, with no per-table authoring. What the registry
declares, and therefore what a generator has to work with:

<!-- BEGIN generated: structure -->
```
179 required column, not null
117 reference, resolves
47  primary key, unique
4   closed vocabulary, member of
26  finite column, no NaN or infinity
9   discriminator, resolvable
```
<!-- END generated: structure -->

How many checks that becomes is the **validator's** answer, not this file's: a table whose sort
begins with its primary key has its uniqueness settled by the shim's ordering scan instead, so
the count is fewer than the keys (R12 §4). `escapewheel_validator.generate` decides it, and
restating the total here is what let this section claim 122 against a registry producing 236.

A reference may be composite or conditional, where a `nullable` foreign key gets an `IS NOT NULL`
guard so legitimately absent values do not report as violations. Unit references are deliberately
not composite: `core.spike_events` references `core.units` on packet-assigned `unit_id` alone. A
discriminator yields two checks, not one: that the value is a dotted resource ID at all, and that
it names a resource the packet declares (R55 §2.4).

## Tier 2 rules

Authored as `[[rules]]` entries in each table's source file and carried inline in its `rules`
array. The whole registry
selects `escapewheel-rule-sql-v0.2`; individual rules cannot override it. Inline rules keep a
table's whole logical contract readable in one declaration.

<!-- BEGIN generated: rules -->
91 rules over 29 tables: 82 error, 7 warning, 2 info — the 2 at `info` being the advisory ones (Part 02 §10.2), off unless asked for.

| Table | Rules |
|---|---:|
| `core.clocks` | 12 |
| `core.array_dimensions` | 8 |
| `analysis.array_dimensions` | 7 |
| `core.processing_runs` | 7 |
| `core.units` | 6 |
| `core.clock_anchors` | 4 |
| `core.preferred_runs` | 4 |
| `core.sessions` | 4 |
| `analysis.spike_events` | 3 |
| `core.intervals` | 3 |
| `core.media_assets` | 3 |
| `analysis.array_labels` | 2 |
| `core.array_assets` | 2 |
| `core.array_labels` | 2 |
| `core.calibrations` | 2 |
| `core.clock_observation_intervals` | 2 |
| `core.devices` | 2 |
| `core.event_stream_observation_intervals` | 2 |
| `core.media_frames` | 2 |
| `core.sorting_run_channels` | 2 |
| `core.spike_events` | 2 |
| `core.unit_electrodes` | 2 |
| `core.unit_observation_intervals` | 2 |
| `core.array_channels` | 1 |
| `core.clock_phase_steps` | 1 |
| `core.coordinate_frame_axes` | 1 |
| `core.event_streams` | 1 |
| `core.events` | 1 |
| `core.unit_quality_labels` | 1 |
<!-- END generated: rules -->

`tables.md` lists them by ID with the message each reports. The manifest-to-`core.sessions`
comparison is a Part 05 shim check because the manifest is not a SQL relation.

## Amendment groups

Every table's source file declares `amendment_groups`, the group lists of Part 02 §2.8. An amendment
may add a row to a table only where the version it supersedes lacks the row's group under at least
one list, so `[]` admits no added row and `[["unit_id"]]` admits a row of any new unit. A list names
required columns of its own table, and no two lists of a table name the same set. Only a core or
extension table declares a list other than `[]`. `check.py` and the validator report a list breaking
either rule as `registry.amendment_groups.resolves`, and `tables.md` shows each table's lists.

## Specialising references

A reference may declare `specialises`, naming the shared-key discriminator whose rows its table
specialises (Part 02 §8.3). `dynamic_foraging.trials` and `vr_foraging.sites` declare
`core.intervals.interval_kind`, written in the column's reference table:

```toml
references = { resource = "core.intervals", column = "interval_id", specialises = "core.intervals.interval_kind" }
```

The validator generates a check on each detail table that its rows' intervals name that table, and
finds a reverse check's counterpart through the declaration. `check.py` and the validator report a
declaration breaking Part 02 §8.3 as `registry.discriminator.specialisation`. The core registry
declares none, and `tables.md` shows each declaration on its reference.

## Identifier quoting

Tier 2 rules name canonical qualified resources such as `core.array_assets`. Identifiers use the
exact lowercase spelling declared by the registry; delimiters do not create alternate names.

## Not yet present

- **`sort` on every table.** Some tables deliberately declare no ordering rather than inventing
  one; Part 03 owns the physical consequences.
- **Array and manifest checks** belonging to the shim rather than SQL: Zarr rank against
  `core.array_dimensions`, `channel_index` within its axis extent, checksums,
  format-owned physical metadata only when a selected resource is accessed or assessed.

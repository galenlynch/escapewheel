# Schema registry

`logical_schemas.json` is the incorporated core registry: the machine-readable declaration of
core and analysis resources under [Part 02](../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md).
A packet binds it as registry `core`, stored at `registries/core/<version>.json.gz` (Part 04 §8,
Part 03 §3.3).

<!-- BEGIN generated: counts -->
```
48 resources, 45 tables, 360 columns, 116 references, 91 Tier 2 rules
```
<!-- END generated: counts -->

`tables.md` is the same content as Markdown, rendered by `render.py` at build time. Read it to see
the exact declarations; read Part 02 for their current meaning. Accepted revisions preserve
history and rationale but are not current normative owners.

| File | Contents |
|---|---|
| `logical_schemas.json` | The registry. Bound by packets as `core` at `registries/core/<version>.json.gz`. |
| `registry.schema.json` | Incorporated local-shape schema for core and extension registry documents. |
| `registry_result.schema.json` | Closed portable representation of a complete registry-document result. |
| `registry_contract.schema.json` | Incorporated closed shape of a registry-contract descriptor. |
| `registry_contracts/escapewheel-registry-contract-v0.8.json` | Incorporated phase, invariant, applicability, and prose-owner index. |
| `rule_language.schema.json` | Closed schema for a rule-language profile. |
| `rule_languages/escapewheel-rule-sql-v0.2.json` | Exact incorporated portable Tier 2 language profile. |
| `manifest.schema.json` | Incorporated closed schema for `packet.json` (Part 04). |
| `resources.schema.json` | Incorporated delivery schema (Part 12 §5). **Generated** by `build.py` from the manifest's resource entry. |
| `resources.example.json` | A delivery document that `check.py` validates against it. |
| `adapter.schema.json` | Incorporated schema for an adapter's declaration document (Part 12 §7). |
| `adapter.example.json` | A declaration document that `check.py` validates against it. |
| `sources.schema.json` | Incorporated schema for a source resolution document (Part 04 §5.5). |
| `sources.example.json` | A resolution document that `check.py` validates against it. |
| `recipe.schema.json` | Incorporated schema for a session recipe's decoded TOML (Part 05 §3.1). |
| `recipe.example.toml` | A recipe using every top-level block, which `check.py` validates against it. |

The schemas and language profile are hand-written here and **vendored** by the distributions that use them — a
wheel cannot read a file from another distribution. Those copies are *build artifacts*, written by
`build.py` and compared by `check.py`, not files to maintain:

```
registry.schema.json  ──build.py──>  escapewheel-validator/src/escapewheel_validator/schemas/
registry_result.schema.json ──build.py──> escapewheel-validator/src/escapewheel_validator/schemas/
registry_contract.schema.json ─┐
registry_contracts/*.json ────├─build.py─> escapewheel-validator/src/escapewheel_validator/schemas/
rule_language.schema.json ──build.py──> escapewheel-validator/src/escapewheel_validator/schemas/
rule_languages/escapewheel-rule-sql-v0.2.json ──build.py──> escapewheel-validator/src/escapewheel_validator/schemas/
manifest.schema.json  ──build.py──>  escapewheel-validator/src/escapewheel_validator/schemas/
sources.schema.json   ──build.py──>  escapewheel-reader/src/escapewheel_reader/schemas/
resources.schema.json ──build.py──>  escapewheel-writer/src/escapewheel_writer/schemas/
adapter.schema.json   ──build.py──>  escapewheel-writer/src/escapewheel_writer/schemas/
recipe.schema.json    ──build.py──>  escapewheel-writer/src/escapewheel_writer/schemas/
```

Edit the copy here, run `build.py`, and commit both repositories. A stale copy has broken every
packet three times — R48, R53 and R56 — each time surfacing as a hundred findings about the data
rather than one about the copy, which is why it is now a build output and a check rather than
a thing to remember.

## Where the registry comes from

`logical_schemas.json` and the extension documents are **generated. Do not edit them.**
`assemble.py` writes each from a directory of TOML:

```
core/registry.toml + core/<resource_id>.toml   ──assemble.py──> logical_schemas.json
extensions/<id>/registry.toml + <resource_id>.toml ─assemble.py──> extensions/<id>.json
```

`registry.toml` holds the document's own fields and each other file declares one resource, in the
published format's keys. A file differs from the document only in spelling, so reading one needs
nothing beyond Part 02: a table's fields sit at the top of its file rather than under `table`, a
single-column reference is written on its column, and a rule may invoke the `interval` template,
which `assemble.py` expands into plain SQL. `canonical.py` fixes the document's key and reference
order, so how a file orders them changes nothing, and `check.py` refuses a table whose
`session_id` does not lead or whose `metadata` does not close it.

Why a declaration is as it is lives in the accepted revisions and in Git, not in the source:
`revisions/registry-targets.toml` locates each accepted clause in the generated document. Before
the source existed, `build.py` generated the core registry by replaying the accepted revisions
over the frozen Part 02, and `git show 0c8fa3e:registry/build.py` recovers that replay.

From the monorepo root, `uv run --project escapewheel-writer python verify.py --quick` rebuilds
the registry and runs its complete checks. Use the same command without `--quick` for package
tests as well.

`check.py` verifies that each document is what its source assembles to. The rule-language
conformance suite statically checks every Tier 2 rule against the selected profile, binds it
against qualified relations built from the registry, and exercises typed semantic vectors.

`render.py` writes `tables.md` and fills this file's generated regions. Every count below is
one of those: a number stated in prose is a number that goes stale, which this file
demonstrated by claiming 33 tables and 51 rules against a registry holding 34 and 61.

## What `check.py` verifies

`check.py` requires the core registry and every repository extension example to return the one
complete result defined by Part 02 §9.4. It then checks repository authoring conventions and
generation invariants that are intentionally not packet-conformance rules, including the table
ledger, source-to-document agreement, column order, naming exceptions, generated copies, and current development
identities. Tier 2 rules also pass the Part 11 static contract and execute against empty typed
relations; semantic vectors separately test their data behavior.

## What it produces

Tier 1 checks are generated from structure, with no per-table authoring. What the registry
declares, and therefore what a generator has to work with:

<!-- BEGIN generated: structure -->
```
175 required column, not null
116 reference, resolves
45  primary key, unique
4   closed vocabulary, member of
26  finite column, no NaN or infinity
8   discriminator, resolvable
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

## Identifier quoting

Tier 2 rules name canonical qualified resources such as `core.array_assets`. Identifiers use the
exact lowercase spelling declared by the registry; delimiters do not create alternate names.

## Not yet present

- **`sort` on every table.** Some tables deliberately declare no ordering rather than inventing
  one; Part 03 owns the physical consequences.
- **Array and manifest checks** belonging to the shim rather than SQL: Zarr rank against
  `core.array_dimensions`, `channel_index` within its axis extent, checksums,
  format-owned physical metadata only when a selected resource is accessed or assessed.

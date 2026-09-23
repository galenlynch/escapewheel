# Schema registry

`logical_schemas.json` is the incorporated core registry: the machine-readable declaration of
core and analysis resources under [Part 02](../escapewheel_poc_docs_v0.2/02_core_logical_schemas.md).
It is the file a packet embeds at `schemas/logical_schemas.json` (Part 02 §9.2).

<!-- BEGIN generated: counts -->
```
46 resources, 43 tables, 348 columns, 111 references, 76 Tier 2 rules
```
<!-- END generated: counts -->

`tables.md` is the same content as Markdown, rendered by `render.py` at build time. Read it to see
the exact declarations; read Part 02 for their current meaning. Accepted revisions preserve
history and rationale but are not current normative owners.

| File | Contents |
|---|---|
| `logical_schemas.json` | The registry. Embedded in packets at `schemas/logical_schemas.json`. |
| `registry.schema.json` | Incorporated local-shape schema for core and extension registry documents. |
| `registry_result.schema.json` | Closed portable representation of a complete registry-document result. |
| `registry_contract.schema.json` | Incorporated closed shape of a registry-contract descriptor. |
| `registry_contracts/escapewheel-registry-contract-v0.2.json` | Incorporated phase, invariant, applicability, and prose-owner index. |
| `rule_language.schema.json` | Closed schema for a rule-language profile. |
| `rule_languages/escapewheel-rule-sql-v0.1.json` | Exact incorporated portable Tier 2 language profile. |
| `manifest.schema.json` | JSON Schema for `packet.json` (Part 04). |

The schemas and language profile are hand-written here and **vendored** by the distributions that use them — a
wheel cannot read a file from another distribution. Those copies are *build artifacts*, written by
`build.py` and compared by `check.py`, not files to maintain:

```
registry.schema.json  ──build.py──>  escapewheel-validator/src/escapewheel_validator/schemas/
registry_result.schema.json ──build.py──> escapewheel-validator/src/escapewheel_validator/schemas/
registry_contract.schema.json ─┐
registry_contracts/*.json ────├─build.py─> escapewheel-validator/src/escapewheel_validator/schemas/
rule_language.schema.json ──build.py──> escapewheel-validator/src/escapewheel_validator/schemas/
rule_languages/escapewheel-rule-sql-v0.1.json ──build.py──> escapewheel-validator/src/escapewheel_validator/schemas/
manifest.schema.json  ──build.py──>  escapewheel-reader/src/escapewheel_reader/schemas/
```

Edit the copy here, run `build.py`, and commit both repositories. A stale copy has broken every
packet three times — R48, R53 and R56 — each time surfacing as a hundred findings about the data
rather than one about the copy, which is why it is now a build output and a check rather than
a thing to remember.

## Provenance of this file

`logical_schemas.json` is **generated. Do not edit it.** Its inputs are maintained separately:

```
nwb_lake_poc_docs/02_*.md ──parse02.py──┐
registry/build.py (reviewed transformations) ─┼──> logical_schemas.json
rules.json (hand-authored) ──────────────────┘
```

**Structure** — columns, keys, references, and ordering — is derived. Historical labels in
`build.py` preserve why a transformation exists; current conformance comes from the incorporated
registry and its Part 02 meanings. Contract changes use the specification-change lifecycle and
then rebuild the generated document.

**Tier 2 rules** are hand-authored in `rules.json`, because nothing derives a check the
structure cannot imply. Keeping them out of the generated file means the registry can be
rebuilt without losing hand-written work, and a diff shows at a glance whether a change was
to a schema or to a rule.

From the monorepo root, `uv run --project escapewheel-writer python verify.py --quick` rebuilds
the registry and runs its complete checks. Use the same command without `--quick` for package
tests as well.

`build.py` rejects a `rules.json` entry naming a table the registry does not define;
`check.py` verifies the merge round-trips. The rule-language conformance suite statically checks
every Tier 2 rule against the selected profile, binds it against qualified relations built from
the registry, and exercises typed semantic vectors.

`render.py` writes `tables.md` and fills this file's generated regions. Every count below is
one of those: a number stated in prose is a number that goes stale, which this file
demonstrated by claiming 33 tables and 51 rules against a registry holding 34 and 61.

## What `check.py` verifies

`check.py` requires the core registry and every repository extension example to return the one
complete result defined by Part 02 §9.4. It then checks repository authoring conventions and
generation invariants that are intentionally not packet-conformance rules, including the table
ledger, source-rule merge, naming exceptions, generated copies, and current development
identities. Tier 2 rules also pass the Part 11 static contract and execute against empty typed
relations; semantic vectors separately test their data behavior.

## What it produces

Tier 1 checks are generated from structure, with no per-table authoring. What the registry
declares, and therefore what a generator has to work with:

<!-- BEGIN generated: structure -->
```
164 required column, not null
111 reference, resolves
43  primary key, unique
4   closed vocabulary, member of
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

Authored in `rules.json` and merged inline into each table's `rules` array. The whole registry
selects `escapewheel-rule-sql-v0.1`; individual rules cannot override it. Inline rules keep a
table's whole logical contract readable in one declaration.

<!-- BEGIN generated: rules -->
76 rules over 27 tables: 67 error, 7 warning, 2 info — the 2 at `info` being the advisory ones (Part 02 §10.2), off unless asked for.

| Table | Rules |
|---|---:|
| `core.clocks` | 11 |
| `core.array_dimensions` | 8 |
| `core.processing_runs` | 7 |
| `core.units` | 5 |
| `core.clock_anchors` | 4 |
| `core.sessions` | 4 |
| `core.media_assets` | 3 |
| `core.preferred_runs` | 3 |
| `core.unit_electrodes` | 3 |
| `analysis.spike_events` | 2 |
| `core.array_assets` | 2 |
| `core.calibrations` | 2 |
| `core.clock_observation_intervals` | 2 |
| `core.devices` | 2 |
| `core.event_stream_observation_intervals` | 2 |
| `core.media_frames` | 2 |
| `core.sorting_run_channels` | 2 |
| `core.spike_events` | 2 |
| `core.unit_observation_intervals` | 2 |
| `analysis.array_dimensions` | 1 |
| `core.array_channels` | 1 |
| `core.clock_phase_steps` | 1 |
| `core.coordinate_frame_axes` | 1 |
| `core.event_streams` | 1 |
| `core.events` | 1 |
| `core.intervals` | 1 |
| `core.unit_quality_labels` | 1 |
<!-- END generated: rules -->

`tables.md` lists them by ID with the message each reports. The catalog-to-`core.sessions`
comparison is a Part 05 shim check because the catalog is not a SQL relation.

## Identifier quoting

Tier 2 rules name canonical qualified resources such as `core.array_assets`. Identifiers use the
exact lowercase spelling declared by the registry; delimiters do not create alternate names.

## Not yet present

- **`sort` on every table.** Some tables deliberately declare no ordering rather than inventing
  one; Part 03 owns the physical consequences.
- **Array and manifest checks** belonging to the shim rather than SQL: Zarr rank against
  `core.array_dimensions`, `channel_index` within its axis extent, checksums,
  `required_codecs` against reader capability.

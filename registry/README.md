# Schema registry

`logical_schemas.json` is the registry content: the machine-readable statement of what a
conforming table is, in the format [R2](../revisions/R2-schema-registry-format.md) defines.
It is the file a packet embeds at `schemas/logical_schemas.json` (R2 §8).

```
33 tables, 276 columns, 46 references, 51 Tier 2 rules
```

`tables.md` is the same content as markdown, rendered by `render.py` at build time. Read it
to see what a table looks like now; read `02` plus the revisions to see why.

| File | Contents |
|---|---|
| `logical_schemas.json` | The registry. Embedded in packets at `schemas/logical_schemas.json`. |
| `registry.schema.json` | Meta-schema; the registry validates against it (R2 §9). |
| `manifest.schema.json` | JSON Schema for `nwb.packet.json` (R2 §10). |

The two schemas are hand-written here and **vendored** by the distributions that use them — a
wheel cannot read a file from another repository. Those copies are *build artifacts*, written by
`build.py` and compared by `check.py`, not files to maintain:

```
registry.schema.json  ──build.py──>  nwb-lake-validator/src/nwb_lake_validator/schemas/
manifest.schema.json  ──build.py──>  nwb-lake-reader/src/nwb_lake_reader/schemas/
```

Edit the copy here, run `build.py`, and commit both repositories. A stale copy has broken every
packet three times — R48, R53 and R56 — each time surfacing as a hundred findings about the data
rather than one about the copy, which is why it is now a build output and a check rather than
a thing to remember.

## Provenance of this file

`logical_schemas.json` is **generated. Do not edit it.** It is built from two sources kept
apart because they are maintained differently:

```
02_core_logical_schemas.md ──parse02.py──┐
revisions R3-R11 ──────────(build.py)────┼──> logical_schemas.json
rules.json (hand-authored) ──────────────┘
```

**Structure** — columns, keys, references, ordering — is derived. `build.py` labels every
transformation with the revision that mandates it, so a column's type or presence traces to
the decision that set it. Changing structure means changing a revision and rebuilding.

**Tier 2 rules** are hand-authored in `rules.json`, because nothing derives a check the
structure cannot imply. Keeping them out of the generated file means the registry can be
rebuilt without losing hand-written work, and a diff shows at a glance whether a change was
to a schema or to a rule.

```bash
python3 build.py      # merges both sources, writes logical_schemas.json
python3 check.py      # 20 invariants; exit 1 on any failure
```

`build.py` rejects a `rules.json` entry naming a table the registry does not define;
`check.py` verifies the merge round-trips and that every rule executes as SQL against
tables built from the registry, which is what catches a rule referencing a column that a
revision has since removed.

## What `check.py` verifies

| Invariant | Source |
|---|---|
| Table set matches the ledger | R9 §2 |
| Every table declares a primary key | R7 §2 |
| Every column type is in the vocabulary | R2 §4 |
| No required column is `json_string` | R2 §5, R3 §2.1 |
| No nested type spellings survived | R3 §2.1 |
| Primary key columns exist and are `required` | R2 §6 |
| References resolve at both ends, arities match | R2 §6 |
| `*_label` columns are `string` | R5 §5, R8 §2 |
| Withdrawn tables absent | R5 §3, R9 §2 |

## What it produces

Fed to `prototype/registry-codegen/generate.py`, the registry yields **122 Tier 1 checks**
with no per-table authoring:

```
74  required column not null
26  foreign key resolves
22  primary key unique
```

Twenty-six references include composite keys (`core.spike_events` → `core.units` on four
columns) and conditional ones, where a `nullable` foreign key gets an `IS NOT NULL` guard so
legitimately absent values do not report as violations.

## Tier 2 rules

Twelve, inline in each table's `rules` array. R2 §13 left inline-versus-sibling open,
to be decided when the content was generated; inline was chosen, so a table's whole
contract is readable in one place.

| Rule | Level | Source |
|---|---|---|
| `core.trials.interval_valid` | error | `02` |
| `core.clocks.tick_rate_declared` | error | R4 §4 |
| `core.clocks.tick_rate_positive` | error | `02` |
| `core.clocks.transform_pair_complete` | error | R3 §3.4 |
| `core.clocks.transform_requires_parent` | error | R3 §3.4 |
| `core.clocks.tick_zero_plausible` | warning | R6 §3 |
| `core.units.spike_summary_consistent` | error | R5 §4 |
| `core.spike_events.ticks_sorted_within_unit` | warning | R5 §7 |
| `core.spike_events.ticks_within_clock_span` | warning | R6 §3 |
| `core.processing_runs.no_failed_runs` | error | R8 §3 |
| `core.array_dimensions.axis_index_contiguous` | error | R3 §3.3 |
| `core.sessions.manifest_sessions_match` | error | R1 §4 |

The last requires the shim to register the manifest's `sessions` array as a
`manifest_sessions` relation before running rules.

## Identifier quoting

Emitted SQL quotes every column identifier. `core.array_assets.offset` is reserved in
DuckDB, and each engine reserves a different set, so quoting is unconditional rather than
conditional on a word list. `check.py` builds DDL from the registry and executes all 12
rules against empty tables, which is what surfaced the collision.

## Not yet present

- **`sort` beyond `03`'s two tables.** Only `core.spike_events` and `core.events` have a
  specified ordering; the rest are null rather than invented.
- **Analysis-layer tables.** Excluded by R2 §12.
- **Array and manifest checks** belonging to the shim rather than SQL: Zarr rank against
  `core.array_dimensions`, `channel_index` within its axis extent, checksums,
  `required_codecs` against reader capability.

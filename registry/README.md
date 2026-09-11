# Schema registry

`logical_schemas.json` is the registry content: the machine-readable statement of what a
conforming table is, in the format [R2](../revisions/R2-schema-registry-format.md) defines.
It is the file a packet embeds at `schemas/logical_schemas.json` (R2 §8).

<!-- BEGIN generated: counts -->
```
43 tables, 351 columns, 111 references, 77 Tier 2 rules
```
<!-- END generated: counts -->

`tables.md` is the same content as markdown, rendered by `render.py` at build time. Read it
to see what a table looks like now; read Part 02 plus the revisions to see why.

| File | Contents |
|---|---|
| `logical_schemas.json` | The registry. Embedded in packets at `schemas/logical_schemas.json`. |
| `registry.schema.json` | Meta-schema; the registry validates against it (R2 §9). |
| `manifest.schema.json` | JSON Schema for `packet.json` (R2 §10). |

The two schemas are hand-written here and **vendored** by the distributions that use them — a
wheel cannot read a file from another repository. Those copies are *build artifacts*, written by
`build.py` and compared by `check.py`, not files to maintain:

```
registry.schema.json  ──build.py──>  escapewheel-validator/src/escapewheel_validator/schemas/
manifest.schema.json  ──build.py──>  escapewheel-reader/src/escapewheel_reader/schemas/
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
python3 check.py      # structural invariants; exit 1 on any failure
```

`build.py` rejects a `rules.json` entry naming a table the registry does not define;
`check.py` verifies the merge round-trips and that every rule executes as SQL against
tables built from the registry, which is what catches a rule referencing a column that a
revision has since removed.

`render.py` writes `tables.md` and fills this file's generated regions. Every count below is
one of those: a number stated in prose is a number that goes stale, which this file
demonstrated by claiming 33 tables and 51 rules against a registry holding 34 and 61.

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

Tier 1 checks are generated from structure, with no per-table authoring. What the registry
declares, and therefore what a generator has to work with:

<!-- BEGIN generated: structure -->
```
167 required column, not null
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

A reference may be composite (`core.spike_events` → `core.units` on four columns) or
conditional, where a `nullable` foreign key gets an `IS NOT NULL` guard so legitimately absent
values do not report as violations. A discriminator yields two checks, not one: that the value
is a dotted resource ID at all, and that it names a resource the packet declares (R55 §2.4).

## Tier 2 rules

Authored in `rules.json` and merged inline into each table's `rules` array. R2 §13 left
inline-versus-sibling open, to be decided when the content was generated; inline was chosen, so
a table's whole contract is readable in one place.

<!-- BEGIN generated: rules -->
77 rules over 27 tables: 68 error, 7 warning, 2 info — the 2 at `info` being the advisory ones (Part 02 §10.2), off unless asked for.

| Table | Rules |
|---|---:|
| `core.clocks` | 11 |
| `core.array_dimensions` | 8 |
| `core.processing_runs` | 7 |
| `core.sessions` | 5 |
| `core.units` | 5 |
| `core.clock_anchors` | 4 |
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

`tables.md` lists them by id with the message each reports. `core.sessions` requires the shim to
register the manifest's `sessions` array as a `manifest_sessions` relation before rules run,
which is the one rule that reads something no table holds.

## Identifier quoting

Emitted SQL quotes every column identifier. `core.array_assets.offset` is reserved in
DuckDB, and each engine reserves a different set, so quoting is unconditional rather than
conditional on a word list. `check.py` builds DDL from the registry and executes every rule
against empty tables, which is what surfaced the collision.

## Not yet present

- **`sort` on every table.** R10 §2 gives 21 of 34 an ordering, primary-key by default with
  Part 03's two overrides; the rest are null rather than invented.
- **Array and manifest checks** belonging to the shim rather than SQL: Zarr rank against
  `core.array_dimensions`, `channel_index` within its axis extent, checksums,
  `required_codecs` against reader capability.

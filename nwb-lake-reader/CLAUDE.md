# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The reference **reader** for NWB-Lake packets. A packet is an ecephys dataset bundle under a
declared physical profile: Parquet tables, Zarr arrays, and a JSON manifest binding them,
with no runtime dependency on NWB, HDMF, or PyNWB.

This package opens a packet and provides tabular access. It does not write packets, import
source data, or validate packet contents beyond the manifest's own shape.

### Where the specification lives

This repository implements a specification maintained in sibling repositories under
`../` — it does not define one. When behaviour here seems arbitrary, the reason is there.

| Sibling | Contents |
|---|---|
| `nwb_lake_poc_docs/` | The frozen specification. Never edited. |
| `revisions/` | R1–R12, all accepted. Where they disagree with the frozen docs, the revision binds. |
| `registry/` | `logical_schemas.json` (22 tables), its meta-schema, and the manifest JSON Schema. |
| `fixtures/` | Phase 0 packets and the conformance corpus — 13 packets with expected findings as data. |
| `conformance/` | Probes producing the measured evidence the revisions cite. |

`src/nwb_lake_reader/schemas/manifest.schema.json` is a **vendored copy** from `registry/`.
Re-copy it when the manifest schema changes there; it is not generated at build time.

## Scope

`07_reference_api_and_implementation_plan.md` sets the phase plan. This package is Phase 1.

**Delivered.** `open_packet`; manifest parsing and JSON Schema validation; resource listing
and URI resolution; `TableResource` for reading, lazy `dataset()` access, DuckDB
registration, and an optional Polars scan; convenience accessors `trials()`, `units()`,
`events()`, `spike_times()`; and the `nwb-lake ls` and `nwb-lake sql` subcommands.

**Also delivered (Phase 2).** `nwb_lake_reader.validation` — Tier 1 checks generated from
the registry's structure, Tier 2 rules carried in it, and the schema and ordering layers SQL
cannot express. `nwb-lake validate` runs them. It lives behind the `validate` extra so that
DuckDB stays optional.

**Not yet.** Zarr array access (Phase 5). Writing, importing, and analysis materialization
are separate concerns and probably separate packages; this one stays a reader and a
validator.

## Architecture

```
Packet                 opened packet; resolves resources, accessors, DuckDB registration
Manifest               parsed nwb.packet.json, validated against its JSON Schema
Resource               one manifest entry: id, layer, kind, uri, plus the raw entry
TableResource          a Resource bound to a root; reads, opens lazily, registers, scans
validation.generate    registry -> Tier 1 checks, plus its Tier 2 rules
validation.validate    four layers over a packet, returning a Report
```

`Resource` records what the manifest *says*; `TableResource` reads it. `ArrayResource`
arrives at Phase 5 and should mirror `TableResource`'s shape. `Packet.table()` and
`Packet.duckdb()` delegate to `TableResource` rather than touching the filesystem
themselves.

Errors derive from `PacketError` so callers can catch the family.

### Design decisions carried from the specification

These are not local preferences; changing them breaks conformance.

- **Resources resolve through the manifest, never by filename convention.** A packet that
  partitions a table or relocates a file stays readable. `Packet.path()` is the only place
  that touches the filesystem layout.
- **Resource IDs are dotted; SQL identifiers are not.** `core.trials` registers as
  `core_trials` (`_sql.sql_name`). Column identifiers in emitted SQL are quoted
  unconditionally — `core.array_assets.offset` is a DuckDB reserved word, and every engine
  reserves a different set.
- **The packet's embedded registry is preferred over any bundled copy** (R2 §8). A packet
  written against registry 0.1.0 stays readable when the reference registry moves on.
  Reading does not require the registry at all; validation does.
- **`required_codecs` must be checked before opening any array** (R3 §7.2), failing with the
  codec named rather than attempting the read. `Packet.check_codecs()` does this; it matters
  from Phase 5.
- **DuckDB is required for validation and deliberately not for reading.** The ban on nested
  Parquet types (R3 §2.1) is what keeps Parquet2.jl a working native Julia read path —
  measured, in `conformance/parquet-probe/`. So DuckDB is an *optional extra*, the accessors
  filter through PyArrow, and `tests/test_accessors.py` asserts that reading never imports
  it. Do not introduce a read path that requires it.
- **Validation splits by what a query can see** (R12 §4). SQL covers what the data *says* —
  values, keys, references, vocabularies. The Python layers cover how it is *stored* —
  column presence, Parquet types, physical order. A storage-layer check written as SQL fails
  silently rather than loudly, which is how R12 came to exist.
- **No registry is bundled.** `validate()` uses the packet's embedded copy (R2 §8) or one
  passed explicitly. Bundling a reference copy would let it go stale against `../registry/`.
- **Tables are flat primitives.** No `struct`, `map`, or `list` columns exist anywhere in the
  registry. Repeated values are child tables (`core.trial_tags`, `core.array_dimensions`,
  `core.session_experimenters`); JSON strings appear only in optional columns.
- **Ticks and timestamps are disjoint.** `*_tick` columns are signed `int64` on a declared
  clock, with no timezone or epoch semantics. Wall-clock columns are `TIMESTAMP(MICROS, UTC)`.
  Nothing that aligns data uses a timestamp.
- **Array axes are in stored order**, slowest-varying first (R3 §5). Column-major bindings
  enumerate them in reverse; clients adapt, the format does not. Relevant from Phase 5.

### Deviations from 07's API

`07`'s example reads `core.unit_spike_chunks` and sums an `n_spikes` list column. R5
withdrew that table, so `spike_times()` filters the flat `core.spike_events` instead, and
returns `clock_id` alongside `t_tick` — a tick has no meaning without its clock.

`07` names the CLI `nwb-lake`, which this package claims. Later packages add subcommands by
depending on this one rather than registering a competing entry point.

## Testing

Tests build their own minimal packet in `tmp_path` (see `tests/conftest.py`) rather than
depending on `../fixtures/`, whose output is gitignored and lives in another repository. Keep
it that way — this package must be testable standalone.

For an end-to-end check against a real packet, `../fixtures/packets/valid` is a
17-table single-session packet; `../fixtures/corpus.py` runs the full conformance corpus.

## Commands

```bash
uv sync                                   # install
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
uv run pytest                             # tests
uv run pytest -k "test_name"              # one test
uv run ruff format
uv run ruff check --fix
uv run mypy
uv run sphinx-build -b html docs/source/ docs/build/html
```

Always use `uv run` to execute commands, `uv add` to add dependencies, and `uv sync` to set up
the environment. Never use bare `pip` or `python`.

## Conventions

`src/` layout, package in `src/nwb_lake_reader/`, tests in `tests/`. Hatchling build, ruff at
120 columns with numpy docstrings, mypy strict, pytest with coverage, commitizen for
versioning, Sphinx with furo for docs. CLI entry points go in `[project.scripts]` and are
implemented in `src/nwb_lake_reader/scripts/`.

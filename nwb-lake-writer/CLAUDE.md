# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The reference **writer** for NWB-Lake packets: the thing that turns normalized records into a
validated packet on disk, and the source adapters that produce those records.

**Nothing is implemented yet.** This repository is a template plus this file. What follows is
the design it is being built to, settled in conversation and grounded in `05` and
`inventory/`.

## Scope

`07_reference_api_and_implementation_plan.md` sets the phase plan. This package is Phase 3.

### The importer is not one step

`05` is explicit: *"Do not combine source parsing, normalization, validation, and writing
into one opaque step."* The decomposition it names is the module layout —

```
source adapter   reads source-specific objects
normalizer       maps source objects to logical records
writer           writes staged Parquet/Zarr resources
validator        validates staged resources        <- nwb-lake-validator, not reimplemented
committer        finalizes resources and manifest
```

The rule that makes this real rather than aspirational: **an adapter never writes a file.**
Its return type is records, not a path. That is what lets adapters be tested without a
filesystem, and what stops normalization decisions leaking into I/O code.

### The first packet needs three sources, not one

Measured in `../inventory/nwb-zarr-776259-2025-04-09.md`:

| Source | What only it has |
|---|---|
| Sorter output (SpikeInterface) | integer sample indices, so `t_tick` is exact; `amplitude_unit` |
| Ephys + behaviour NWB (NWB-Zarr) | trials, behaviour events, CCF registration |
| aind-data-schema JSONs | subject, rig, procedures, session identity |

So there is no `nwb-lake import <file>`. The unit of work is a **session recipe** naming
several sources, and the recipe doubles as the parameters `05` Stage 3 requires normalization
to be deterministic in — which is what gets recorded in `core.processing_runs`.

```bash
nwb-lake-import inspect <source>            # 05 Stage 1, per source, one inventory
nwb-lake import session.toml --out packet   # 05 Stages 2-6
```

### Two things about the sources that will bite

- **AIND writes NWB-Zarr, not NWB-HDF5** — roughly all of it. Target `hdmf_zarr.NWBZarrIO`
  first. zarr-python 3 cannot open those files through consolidated metadata
  (`fill_value: 0` on vlen-string arrays), so `use_consolidated=False` is mandatory.
- **`session.json` carries a 7-hour timezone error** on this dataset —
  `2025-04-09T17:25:12+00:00` for a Pacific wall clock. The NWB gets it right. Identity comes
  from the JSONs, so the importer must not trust that offset.

## Architecture, when it exists

```
PacketWriter    normalized Arrow tables + array assets -> a staged, validated, committed packet
adapters/       one module per source; returns records, touches no filesystem
recipe          the parsed session spec; also the provenance record
```

`PacketWriter` is the product; the adapters are thin. It owns sort order (R10), the physical
floor (R3 — primitive columns only), staging layout, and `05` Stage 5's atomic commit:
write staged resources, validate them, write a *candidate* manifest, move resources into
final paths, rename the candidate to `nwb.packet.json` **last**.

Heavy source dependencies (`hdmf-zarr`, `spikeinterface`) go behind extras, the way
`nwb-lake-reader` keeps DuckDB behind `sql`.

### Design decisions carried from the specification

- **Validation is importation** (`05`). Copying bytes is staging. Staged resources MUST NOT
  appear as committed canonical resources in the manifest.
- **Time is integer ticks on a declared clock.** Every event, interval, spike time and dense
  time axis carries `clock_id` and an integer `*_tick`. Float seconds are derived only. This
  is the reason the sorter is the tick source: the NWB has already baked a per-probe
  alignment into float seconds and thrown the sample index away.
- **Clock alignment may be piecewise** (R13). A clock declares linear alignment, anchor
  points, or neither — never both. Real AIND data needs the anchor form.
- **Referencing is expected for large resources** (R14, R15). A resource the packet does not
  own sets `external: true` with an absolute URI, and declares its own codecs.
- **Sort every table by its primary key** (R10) except `core.spike_events` and `core.events`,
  whose orderings `03` overrides.

## The CLI

`07` names one command, `nwb-lake`. `nwb-lake-reader` owns the console script; this package
registers under the `nwb_lake.commands` entry-point group, as `nwb-lake-validator` does. Two
distributions declaring the same `[project.scripts]` name is a conflict in which the last one
installed wins silently.

```toml
[project.entry-points."nwb_lake.commands"]
import = "nwb_lake_writer.scripts.cli:register"
```

## Where the specification lives

| Sibling | Contents |
|---|---|
| `nwb_lake_poc_docs/` | The frozen specification. Never edited. `05` is the import pipeline. |
| `revisions/` | R1–R20, all accepted. Where they disagree with the frozen docs, the revision binds. |
| `registry/` | `logical_schemas.json` (28 tables) — what a written table must look like. |
| `inventory/` | `05` Stage 1 inventories of the real datasets this will import. |
| `nwb-lake-reader/` | The read path. |
| `nwb-lake-validator/` | Phase 2. The committer calls this; it is not reimplemented here. |

## Commands

```bash
uv sync
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
uv run pytest
uv run ruff format
uv run ruff check --fix
uv run mypy
```

Always use `uv run` to execute commands, `uv add` to add dependencies, and `uv sync` to set up
the environment. Never use bare `pip` or `python`.

## Conventions

`src/` layout, package in `src/nwb_lake_writer/`, tests in `tests/`. Hatchling build, ruff at
120 columns with numpy docstrings, mypy strict, pytest with coverage, commitizen for
versioning, Sphinx with furo for docs.

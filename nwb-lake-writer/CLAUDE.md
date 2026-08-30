# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The reference **writer** for NWB-Lake packets: the thing that turns normalized records into a
validated packet on disk, and the source adapters that produce those records.

**Delivered.** `PacketWriter` — records in, validated packet out. It stages under
`staging/`, validates there, moves resources into place, and renames the manifest **last**
(`05` Stage 5), so a reader never finds a partial import claiming to be valid. Schema, column
order and physical sort all come from the registry, which is embedded in the packet (R2 §8).
Wall-clock values without a UTC offset are refused rather than assumed (`arrow.NaiveTimestamp`).

**Also delivered.** Four source adapters, the session recipe, the `nwb-lake` subcommands
(`inspect`, `init`, `import`), and dense array staging. Two real AIND sessions commit clean
from a recipe, 248 M and 287 M spikes.

**Not yet.** External resources (R14/R15 level 3): LFP referenced rather than owned, and
`core.array_channels` with R19 per-channel gain, offset and `inter_sample_shift`. The NWB
adapter already prints a note it cannot clear until that lands.

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
to be deterministic in — which is what `core.processing_runs.parameters` now carries, so a
committed packet says what produced it and `code_uri` names the recipe by digest.

See **The CLI** below for the commands. A recipe is checked against the registry before any
source is opened, so the problems that cost a four-minute build are reported in milliseconds.

### Two things about the sources that will bite

- **AIND writes NWB-Zarr, not NWB-HDF5** — roughly all of it. Target `hdmf_zarr.NWBZarrIO`
  first. zarr-python 3 cannot open those files through consolidated metadata
  (`fill_value: 0` on vlen-string arrays), so `use_consolidated=False` is mandatory.
- **`session.json` carries a 7-hour timezone error** on this dataset —
  `2025-04-09T17:25:12+00:00` for a Pacific wall clock. The NWB gets it right. Identity comes
  from the JSONs, so the importer must not trust that offset.

## Architecture

```
sources/        one adapter per source; returns records, touches no filesystem
recipe          parse and check a session recipe; opens nothing
session         order the sources, run them, keep what each one owns
arrow           registry column types -> Arrow schema; records -> a sorted table
arrays          Zarr v3 layout: chunk for the question, shard for the object
PacketWriter    records in, staged/validated/committed packet out
```

`PacketWriter.add(resource_id, records)` accumulates; `commit(root)` does the rest and
returns the validator's `Report`. A commit that finds errors raises `CommitRefused` and leaves
`staging/` in place for inspection, with no manifest at the root at all.

`PacketWriter` is the product; the adapters are thin. It owns sort order (R10), the physical
floor (R3 — primitive columns only), staging layout, and `05` Stage 5's atomic commit:
write staged resources, validate them, write a *candidate* manifest, move resources into
final paths, rename the candidate to `nwb.packet.json` **last**.

Heavy source dependencies (`hdmf-zarr`, `spikeinterface`, `zarr`) go behind extras, the way
`nwb-lake-reader` keeps DuckDB behind `sql`.

### Ownership, and why it is declared

A recipe gives each source an `owns` list and an optional `contributes` list. `owns` is
exclusive; `contributes` is additive, and exists because `core.clocks` genuinely has two
suppliers — the sorter declares one clock per probe stream, the sync source declares the rig
clock they are anchored to. Without the distinction the last adapter to run wins silently,
which is how a `probe_id` collapse once matched 0 of 6,781 units and how two adapters emitting
`core.unit_electrodes` collided on its primary key.

`Recipe.check(registry)` is what makes the declaration pay. Before a byte is read it refuses a
resource owned twice, an owned resource the registry does not define, and an owned table whose
**required** foreign key points at a table nothing supplies — a packet that cannot validate,
known from two documents with no data in hand. A nullable one is a warning, because
`generate(only=...)` silently skips a foreign-key check whose target is absent.

### Ordering comes from the adapters, not the registry

A foreign key constrains validity, not write order: Parquet files are independent and nothing
stops `core.spike_events` being written before `core.units`. What sequences a build is
data-flow between adapters — `NWBSource` needs the sorter's units before it can attach a unit
to an electrode — so `session.CONSUMES` states it, and it is short because there is little of
it. Table-level parallelism would not pay in any case: `core.spike_events` is 99.9% of a
session's rows.

### Never leave Arrow inside a per-batch path

Every performance defect found in this package has been the same one: a column turned into
Python objects inside a loop that runs once per batch. If a line converts a column to a Python
`list` and its surrounding code runs per batch, it is wrong — `pc.unique`, `pc.equal`,
`pc.is_in`, `Array.take` and `np.flatnonzero` cover nearly every case and release the GIL.

String identifiers are not the cause and replacing them makes things worse: Parquet
dictionary-encodes them, so the four-column contextual key is 2.7 MB per million rows against
195 MB as uncompressed Arrow.

`docs/source/performance.md` carries the measurements, the layout decisions and what they cost
— read it before changing an encoding, a row-group size or the spill format, each of which has
already been changed and reverted on evidence.

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

```bash
nwb-lake inspect sorter /data/sorted    # 05 Stage 1: what one source offers
nwb-lake init --session-id s001 \       # a recipe draft, contested resources flagged
  --source sorter=/data/sorted --source nwb=/data/session.nwb
nwb-lake import session.toml --check    # every problem, before any I/O
nwb-lake import session.toml            # 05 Stages 2-6
```

Progress is stamped and flushed. An import is minutes long and its stages cost very
differently — on a 287 M-spike session, sources then staging then validation — so the log has
to say where the time went rather than leaving a caller to guess.

## Where the specification lives

| Sibling | Contents |
|---|---|
| `nwb_lake_poc_docs/` | The frozen specification. Never edited. `05` is the import pipeline. |
| `revisions/` | R1–R32, all accepted. Where they disagree with the frozen docs, the revision binds. |
| `registry/` | `logical_schemas.json` (33 tables) — what a written table must look like. |
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

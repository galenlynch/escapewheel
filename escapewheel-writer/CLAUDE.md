# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The reference **writer** for Escapewheel packets: the thing that turns normalized records into a
validated packet on disk, and the source adapters that produce those records.

**Delivered.** `PacketWriter` — records in, validated packet out. It stages under
`staging/`, validates there, moves resources into place, and renames the manifest **last**
(Part 05 Stage 5), so a reader never finds a partial import claiming to be valid. Schema, column
order and physical sort all come from the registry, which is embedded in the packet (R2 §8).
Wall-clock values without a UTC offset are refused rather than assumed (`arrow.NaiveTimestamp`).

**Also delivered.** Four source adapters, the session recipe, the `escapewheel` subcommands
(`inspect`, `init`, `import`), and dense array staging. Two real AIND sessions commit clean
from a recipe, 248 M and 287 M spikes.

**Also delivered.** LFP, referenced rather than owned (R14 §2.3, R21 §3.2): twelve Zarr v2
arrays, 6.8 GB the packet points at and does not copy, with `core.array_channels` carrying
R19's per-channel `inter_sample_shift` and the electrode behind each position.

**Not yet.** Media assets, and an external mode that resolves anything but a `file://` URI.

## Scope

Part 07 sets the phase plan. This package is Phase 3.

### The importer is not one step

Part 05 is explicit: *"Do not combine source parsing, normalization, validation, and writing
into one opaque step."* The decomposition it names is the module layout —

```
source adapter   reads source-specific objects
normalizer       maps source objects to logical records
writer           writes staged Parquet/Zarr resources
validator        validates staged resources        <- escapewheel-validator, not reimplemented
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

So there is no `escapewheel import <file>`. The unit of work is a **session recipe** naming
several sources, and the recipe doubles as the parameters Part 05 Stage 3 requires normalization
to be deterministic in — which is what `core.processing_runs.parameters` now carries, so a
committed packet says what produced it and `code_uri` names the recipe by digest.

See **The CLI** below for the commands. A recipe is checked against the registry before any
source is opened, so the problems that cost a four-minute build are reported in milliseconds.

### LFP: referenced, and timed by its probe rather than by its timestamps

The NWB stores 7,983,750 float64 timestamps per series -- 767 MB across twelve -- on a
regenerated nominal grid, with the sign of `t0` flipped so the array reads as 268 days before
the spikes. The packet stores none of them. Measured across four probes, LFP sample 0 lands
within 0.2 ms of the probe's own sample 0 and advances exactly 24 AP ticks a sample, so R20's
regular-tick axis states the whole time base in three integers on the clock the spikes are
already on. Both upstream defects disappear rather than being carried forward, and the
per-probe drift the grid would have introduced -- up to 70 ms over a session -- goes with them.

**In production the arrays are on S3, and `uri_base` is how the recipe says so.** Set it and
the manifest points at `s3://.../ElectricalSeries<probe>-LFP/data`; leave it and the packet
records a `file://` URI that resolves only on the machine that built it. A remote base also
suppresses `size_bytes` and `verified_at`, because R14 §2.3.1 lets a packet report only what
was actually looked at and a local copy says nothing about what a remote URI resolves to. The
consequence is worth knowing: **a production packet currently carries no verified fact about
its LFP at all.** Closing that needs the writer to reach the real URI, which is the same
capability `validate(external=True)` needs and neither has yet.

`LFPSource` derives the step from the *interval* between the first two timestamps rather than
their values: the sign fault ruins the values and leaves the spacing alone. A ratio that is not
a whole number of probe ticks is refused, because then this is not a decimation of that stream.

`conversion` is one value per series here, so it stays on `core.array_assets`; repeating it
down 96 channel rows would buy nothing (R3 §3.0). `inter_sample_shift` genuinely varies -- eight
distinct values within a series -- which is what R19 added the column for.

### Two things about the sources that will bite

- **AIND writes NWB-Zarr, not NWB-HDF5** — roughly all of it. Target `hdmf_zarr.NWBZarrIO`
  first. zarr-python 3 cannot open those files through consolidated metadata
  (`fill_value: 0` on vlen-string arrays), so `use_consolidated=False` is mandatory.
- **`session.json` carries a 7-hour timezone error** on this dataset —
  `2025-04-09T17:25:12+00:00` for a Pacific wall clock. The NWB gets it right. Identity comes
  from the JSONs, so the importer must not trust that offset.

## Developer guidance

**`CONTRIBUTING.md` is the canonical statement** of what belongs in this package and why. Read it
before adding a source adapter, a compensation, or anything in a per-batch path. The rules with
the sharpest failure modes: ownership is declared and checked before a byte is read; a
compensation is declared with evidence into `../inventory/`, and so is a knowing pass-through;
and never leave Arrow inside a per-batch path, which is what every performance defect here has
been.

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
floor (R3 — primitive columns only), staging layout, and Part 05 Stage 5's atomic commit:
write staged resources, validate them, write a *candidate* manifest, move resources into
final paths, rename the candidate to `packet.json` **last**.

Heavy source dependencies (`hdmf-zarr`, `spikeinterface`, `zarr`) go behind extras, the way
`escapewheel-reader` keeps DuckDB behind `sql`.

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

### One source is read once

Three adapters in a real recipe open the same `.nwb`, and two of them read the electrode
table; `WaveformSource` read its six `units/` arrays twice within itself. `SourceStore` holds
one memoized reader per resolved root and `Context` shares it. The saving is small; the point
is that two readers of the same bytes can no longer disagree. An adapter built on its own gets
a private store, so nothing about sharing leaks into how one is written or tested.

`NWBSource._table` stays outside the store because it produces notes, and a note about a
skipped column belongs to the adapter that asked rather than to whichever asked first.

### The importer records what it assumed about its sources

Every adapter works around something known to be wrong upstream — `inventory/` carries eight
measured defects. A correction is silent by construction, which is fine until the fault is
fixed: an importer still compensating for a defect its source no longer has produces a packet
wrong in the opposite direction, and nothing in it says so.

So a compensation is declared, registered in `sources/compensations.py` with its evidence, and
every one an import applied lands in `core.processing_runs.parameters`. A knowing pass-through
is registered too — choosing not to correct is as much an assumption as choosing to. Adding one
without a citation into `inventory/` is refused by the tests.

`--strict` refuses a build on any adapter note. A note is a place the packet says less than the
source could have; working around them is the point of an adapter, so it is off by default and
on in CI, where a new one is news.

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

Storing a low-cardinality string is not the cause — Parquet dictionary-encodes it, and a
column holding a handful of values costs a hundredth of a bit a row. **Converting one is.**
Carry the codes: `read_dictionary=` on the way in, `store_schema=False` so the file still
advertises the registry's type, and never a `pc.less` on a dictionary, which decodes both
sides.

`docs/source/performance.md` carries the measurements, the dictionary rules, the layout
decisions and what they cost — read it before changing an encoding, a row-group size or the
spill format, each of which has already been changed and reverted on evidence.

### Design decisions carried from the specification

- **Validation is importation** (Part 05). Copying bytes is staging. Staged resources MUST NOT
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
  whose orderings Part 03 overrides.

## The CLI

Part 07 names one command, `escapewheel`. `escapewheel-reader` owns the console script; this package
registers under the `escapewheel.commands` entry-point group, as `escapewheel-validator` does. Two
distributions declaring the same `[project.scripts]` name is a conflict in which the last one
installed wins silently.

```bash
escapewheel inspect sorter /data/sorted    # 05 Stage 1: what one source offers
escapewheel init --session-id s001 \       # a recipe draft, contested resources flagged
  --source sorter=/data/sorted --source nwb=/data/session.nwb
escapewheel import session.toml --check    # every problem, before any I/O
escapewheel import session.toml --strict   # refuse anything the adapters worked around
escapewheel import session.toml            # 05 Stages 2-6
```

Progress is stamped and flushed. An import is minutes long and its stages cost very
differently — on a 287 M-spike session, sources then staging then validation — so the log has
to say where the time went rather than leaving a caller to guess.

## Where the specification lives

| Directory | Contents |
|---|---|
| `nwb_lake_poc_docs/` | The frozen v0.1 specification. Never edited. |
| `escapewheel_poc_docs_v0.2/` | The editable parts, which are what bind. Part 05 is the import pipeline. |
| `revisions/` | One file per accepted change. Where a revision and the frozen docs disagree, the revision binds. |
| `registry/` | `logical_schemas.json` — what a written table must look like. |
| `inventory/` | Part 05 Stage 1 inventories of the real datasets this will import. |
| `escapewheel-reader/` | The read path. |
| `escapewheel-validator/` | Phase 2. The committer calls this; it is not reimplemented here. |

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R118 accepted. R42 and R73 withdrawn. No draft is open.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
43 tables, 351 columns, 111 references, 77 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
28 conformance packets
<!-- END facts: corpus -->


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

`src/` layout, package in `src/escapewheel_writer/`, tests in `tests/`. Hatchling build, ruff at
120 columns with numpy docstrings, mypy strict, pytest with coverage, commitizen for
versioning, Sphinx with furo for docs.

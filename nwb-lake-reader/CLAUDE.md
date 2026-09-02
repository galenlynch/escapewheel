# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The reference **reader** for NWB-Lake packets. A packet is an ecephys dataset bundle under a
declared physical profile: Parquet tables, Zarr arrays, and a JSON manifest binding them,
with no runtime dependency on NWB, HDMF, or PyNWB.

This package opens a packet and provides tabular access. It does not write packets, import
source data, or validate packet contents beyond the manifest's own shape.

#### An external array is addressed by URI, not by path

`ArrayResource.path` is the local answer and refuses a scheme it cannot reach; `store` is what
to hand a Zarr store, and for a remote array that is the URI itself — resolving it to a `Path`
first is exactly what would make it unopenable. In production an LFP array is an S3 object, so
this is the normal case and not the exotic one.

A remote array takes its Zarr version from the manifest's `physical_profile`, which is the only
statement available. That is not the circularity R15 §4's level 2 avoids: level 2 covers
packet-owned arrays, where a local document exists to compare against, while R14 §2.3.1 already
frames an external resource's declaration as a claim. Its `metadata()` is read through Zarr
rather than from a JSON document, so shape, dtype and codecs need the `arrays` extra *and* a
backend for the scheme (`s3fs` for `s3://`) — neither of which this package depends on.

## Where the specification lives

This repository implements a specification maintained in sibling repositories under
`../` — it does not define one. When behaviour here seems arbitrary, the reason is there.

| Sibling | Contents |
|---|---|
| `nwb_lake_poc_docs/` | The frozen specification. Never edited. |
| `revisions/` | R1–R36, all accepted. Where they disagree with the frozen docs, the revision binds. |
| `registry/` | `logical_schemas.json` (33 tables), its meta-schema, and the manifest JSON Schema. |
| `fixtures/` | Phase 0 packets and the conformance corpus — 16 packets with expected findings as data. |
| `conformance/` | Probes producing the measured evidence the revisions cite. |
| `nwb-lake-validator/` | Phase 2. Depends on this package; adds `nwb-lake validate`. |
| `nwb-lake-writer/` | Phase 3. Depends on the validator; adds `nwb-lake import`. |

`src/nwb_lake_reader/schemas/manifest.schema.json` is a **vendored copy** from `registry/`.
Re-copy it when the manifest schema changes there; it is not generated at build time.

## Scope

`07_reference_api_and_implementation_plan.md` sets the phase plan. This package is Phase 1.

**Delivered.** `open_packet`; manifest parsing and JSON Schema validation; resource listing
and URI resolution; `TableResource` for reading, lazy `dataset()` access, DuckDB
registration, and an optional Polars scan; convenience accessors `trials()`, `units()`,
`events()`, `spike_times()`; and the `nwb-lake ls` and `nwb-lake sql` subcommands.

**Elsewhere.** Validation is `nwb-lake-validator`, a separate package that depends on this
one. It was split out because its correctness is pinned to a *registry* version while this
package's API is not — every new table or rule would otherwise force a reader release for
code that had not changed.

**Also delivered.** Dense array access (Phase 5) — `ArrayResource`, `Packet.array_resource()`
and `Packet.array_resources()`. Metadata needs no Zarr: an array declares its shape, dtype,
chunk grid, fill value and codecs in a JSON document in the store, so what an array *is* costs
nothing. Only `read()` needs Zarr, behind the `arrays` extra.

**Not yet.** Writing, importing, and analysis materialization belong to `nwb-lake-writer` and
its successors; this one stays a reader.

## Architecture

```
Packet                 opened packet; resolves resources, accessors, DuckDB registration
Manifest               parsed nwb.packet.json, validated against its JSON Schema
Resource               one manifest entry: id, layer, kind, uri, plus the raw entry
TableResource          a Resource bound to a root; reads, opens lazily, registers, scans
sql                    resource ID -> SQL identifier; public because the validator emits SQL
                       against the names this package registers, and the two must agree
```

`Resource` records what the manifest *says*; `TableResource` and `ArrayResource` read it.
`Packet.table()` and `Packet.duckdb()` delegate to `TableResource` rather than touching the
filesystem themselves, and `Packet.array_resource()` to `ArrayResource`.

The two handles split their dependencies the same way and for the same reason. A table needs
PyArrow to read and DuckDB only to query; an array needs nothing to describe and Zarr only to
read. That is what lets the validator check R15 §4 level 2 — declared codecs against the
store's own metadata — without depending on Zarr at all.

Errors derive from `PacketError` so callers can catch the family.

### The shape of the API, and what belongs in it

**`CONTRIBUTING.md` is the canonical statement.** Read it before adding a function, a module or
a `Packet` method. The binding parts, in short:

- **Free functions in three layers** — kernels over raw arrays, `(packet, table)` semantics,
  `(packet, ...)` access — with thin one-line `Packet` delegates. The function is the
  implementation and carries the docstring; the delegate carries no behaviour. The reason is
  structural: our currency is `pa.Table`, which is PyArrow's and has no `.pipe()`, so the method
  form was never available.
- **`Packet` is manifest, resolution, IO and DuckDB registration.** Nothing may be added to it
  that would work as a free function instead.
- **The test for whether a transformation is ours at all:** the reader owns it when doing it
  yourself from the documented schema would be *silently* wrong. Everything else is a query.
  `CONTRIBUTING.md` carries the table of hazards that bounds the set, one row per revision.
- **Refuse rather than choose**, naming the revision. An accepted revision's rule raises; one a
  proposed revision would catch warns, so a non-binding revision cannot make a readable packet
  unreadable.
- **A semantic operation added to the SQL path is added to the PyArrow path too**, with a test
  asserting the two agree. DuckDB is the optional `sql` extra by design.

### Design decisions carried from the specification

These are not local preferences; changing them breaks conformance.

- **Resources resolve through the manifest, never by filename convention.** A packet that
  partitions a table or relocates a file stays readable. `Packet.path()` is the only place
  that touches the filesystem layout.
- **Resource IDs are dotted; SQL identifiers are not.** `core.trials` registers as
  `core_trials` (`sql.sql_name`). Column identifiers in emitted SQL are quoted
  unconditionally — `core.array_assets.offset` is a DuckDB reserved word, and every engine
  reserves a different set. `sql` is public rather than private precisely because
  `nwb-lake-validator` must produce the same names; one implementation, so they cannot drift.
- **The packet's embedded registry is preferred over any bundled copy** (R2 §8). A packet
  written against registry 0.1.0 stays readable when the reference registry moves on.
  Reading does not require the registry at all; validation does.
- **`required_codecs` must be checked before opening any array** (R3 §7.2), failing with the
  codec named rather than attempting the read. `Packet.check_codecs()` does this, and
  `ArrayResource.codecs` reports what a store actually uses, which is the other side of the
  same comparison.
- **A complete read path exists without a SQL engine.** `table()`, the accessors, and
  `TableResource` go through PyArrow; `Packet.duckdb()` and `Packet.sql()` are read paths
  too, and they do need DuckDB. The point is that they are not the *only* ones, so a minimal
  reader stays possible in a language lacking an embedded SQL engine — which is what the ban
  on nested Parquet types (R3 §2.1) exists to preserve, measured in
  `conformance/parquet-probe/`. DuckDB is therefore the `sql` extra, and
  `tests/test_accessors.py` asserts the PyArrow path never imports it.

  The PyArrow path is **not faster** — on 9M spikes selecting one unit it is 4.4 ms against
  DuckDB's 3.2 ms, and DuckDB adds only ~57 MB to an install PyArrow already dominates at
  152 MB. Its whole justification is that it works with the extra absent. Keeping DuckDB
  optional is what *enforces* that: as a hard dependency, nothing would stop a read path
  growing to require it and the format's portability claim eroding silently.

- **The discoverable call is the efficient one.** `table(resource_id, columns=..., **where)`
  pushes constraints into the Parquet reader — a scalar means equality, a two-item tuple a
  closed range — so row groups that cannot match are never decompressed. 4.4 ms against
  24.8 ms selecting one unit from nine million spikes. The named accessors are typed sugar
  over it. `scan()` returns a lazy dataset for what constraints cannot express.

  This shape was chosen over adding a second, faster name for users to discover. Five of the
  30 tables grow large — `spike_events`, `events`, `media_frames`, `trials`, `trial_tags` —
  and under R1's multi-session extension every table scales with session count, so a
  read-everything default would be wrong in the general case rather than in a corner.
- **No registry is bundled.** Reading never needs one; `Packet` exposes the copy a packet
  embeds (R2 §8) and `nwb-lake-validator` validates against that. Bundling a reference copy
  here would let it go stale against `../registry/`.
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

`07` names the CLI `nwb-lake`, which this package claims under `[project.scripts]`. Later
packages **cannot** also claim it — two distributions declaring the same console script is a
conflict, and the last one installed wins silently. So they register a callable under the
`nwb_lake.commands` entry-point group instead, and `cli._extend` loads them at parse time.
`cli.EXTENSIONS` names the subcommands that live elsewhere, so an uninstalled one reports
which package provides it rather than failing as an argparse "invalid choice".

## Testing

Tests build their own minimal packet in `tmp_path` (see `tests/conftest.py`) rather than
depending on `../fixtures/`, whose output is gitignored and lives in another repository. Keep
it that way — this package must be testable standalone.

For an end-to-end check against a real packet, `../fixtures/packets/valid` is a
17-table single-session packet; `../fixtures/corpus.py` runs the full conformance corpus.

## Commands

```bash
uv sync                                   # install
uv sync --extra sql                       # install with DuckDB, for Packet.duckdb()
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

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The reference **reader** for Escapewheel packets. A packet is an ecephys dataset bundle under a
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

This package implements a specification kept in sibling **directories** of the same repository,
under `../` — it does not define one. When behaviour here seems arbitrary, the reason is there.
Version control has been one repository at the root since 2026-09-04; it was ten, coupled by
relative paths git could not see.

| Directory | Contents |
|---|---|
| `nwb_lake_poc_docs/` | The frozen v0.1 specification. Never edited. |
| `escapewheel_poc_docs_v0.2/` | The editable parts, which are what bind. |
| `revisions/` | One file per accepted change. Where a revision and the frozen docs disagree, the revision binds. |
| `registry/` | `logical_schemas.json`, its meta-schema, and the manifest JSON Schema. |
| `fixtures/` | Phase 0 packets and the conformance corpus, each with its expected findings as data. |
| `conformance/` | Probes producing the measured evidence the revisions cite. |
| `escapewheel-validator/` | Phase 2. Depends on this package; adds `escapewheel validate`. |
| `escapewheel-writer/` | Phase 3. Depends on the validator; adds `escapewheel import`. |

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R119 accepted. R42 and R73 withdrawn. No draft is open.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
43 tables, 351 columns, 111 references, 77 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
28 conformance packets
<!-- END facts: corpus -->

`src/escapewheel_reader/schemas/manifest.schema.json` is a copy of `registry/manifest.schema.json`,
and `registry/build.py` writes it: a wheel cannot read a file from another distribution, so the copy
is an output of that build rather than something to re-copy by hand. `verify.py` regenerates and
then demands a clean tree, so a stale copy fails.

## Scope

Part 07 sets the phase plan. This package is Phase 1.

**Delivered.** `open_packet`; manifest parsing and JSON Schema validation; resource listing
and URI resolution; `TableResource` for reading, lazy `dataset()` access, DuckDB
registration, and an optional Polars scan; convenience accessors `trials()`, `units()`,
`events()`, `spike_times()`; and the `escapewheel ls` and `escapewheel sql` subcommands.

**Elsewhere.** Validation is `escapewheel-validator`, a separate package that depends on this
one. It was split out because its correctness is pinned to a *registry* version while this
package's API is not — every new table or rule would otherwise force a reader release for
code that had not changed.

**Also delivered.** Dense array access (Phase 5) — `ArrayResource`, `Packet.array_resource()`
and `Packet.array_resources()`. Metadata needs no Zarr: an array declares its shape, dtype,
chunk grid, fill value and codecs in a JSON document in the store, so what an array *is* costs
nothing. Only `read()` needs Zarr, behind the `arrays` extra.

**Not yet.** Writing, importing, and analysis materialization belong to `escapewheel-writer` and
its successors; this one stays a reader.

## Architecture

```
Packet                 opened packet; resolves resources, accessors, DuckDB registration
Dataset                several packets as one relation per resource, with session identity
Manifest               parsed packet.json, validated against its JSON Schema
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
- **Resource IDs are dotted; SQL identifiers are not.** `core.intervals` registers as
  `core_intervals` (`sql.sql_name`). Column identifiers in emitted SQL are quoted
  unconditionally — `core.array_assets.offset` is a DuckDB reserved word, and every engine
  reserves a different set. `sql` is public rather than private precisely because
  `escapewheel-validator` must produce the same names; one implementation, so they cannot drift.
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

  This shape was chosen over adding a second, faster name for users to discover. A handful of
  tables grow large — `core.spike_events`, `core.events`, `core.media_frames`, `core.intervals` —
  and under R1's multi-session extension every table scales with session count, so a
  read-everything default would be wrong in the general case rather than in a corner.
- **No registry is bundled.** Reading never needs one; `Packet` exposes the copy a packet
  embeds (R2 §8) and `escapewheel-validator` validates against that. Bundling a reference copy
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

Part 07's example reads `core.unit_spike_chunks` and sums an `n_spikes` list column. R5
withdrew that table, so `spike_times()` filters the flat `core.spike_events` instead, and
returns `clock_id` alongside `t_tick` — a tick has no meaning without its clock.

Part 07 Phase 5 wants `core.array_assets` validated "against actual Zarr dtype/shape". **Both
columns were struck** — R3 §3.3 lists `shape` and `dtype` as `removed`, because the Zarr array
declares them and R3 §3.0 forbids restating what the data declares. What survives is the
agreement that is *not* recoverable from the array alone, and the validator checks it: rank
against `core.array_dimensions`, declared `codecs` against the store, `zarr_format`, and R3 §5's
transpose ban.

### This package acquires no transport of its own

`stores` moved to **escapewheel-validator**, because what needs a store *client* is R36's
verification -- list a prefix, hash its members -- and that is the validator's job, so the
`remote` and `s3` extras live there.

Everything a read path reaches remotely, it reaches through an engine already depended on.
`pyarrow.fs` opens a Parquet file or a JSON document, DuckDB reaches an object store through
its own C++ client, and `zarr` opens an array URI with its own backend. `Location` is where the
choice between a path and a store URI is made, once, so no caller repeats it.

Keep it that way. A read path here may need a remote byte -- an object store is where a shared
dataset lives -- but the engine that reads it brings its transport; this package adds no
dependency to get one.

### A packet root may be a store prefix

Part 00 §2.4 admits three forms -- a local directory, an object-store prefix, or a release manifest
pointing at distributed assets -- and `open_packet` takes any of them. `Location` resolves a
declared URI against the root: relative under it, absolute where it says, and `file:` as the
spelling of a path it is. `Packet.root` is the local answer and refuses a store; `Packet.location`
is the one to pass on.

`open_packet(..., rewrite=...)` substitutes a declared-URI prefix before resolution, longest
prefix first. R14 §2.3 makes reachability the reader's situation and a committed packet records
the writer's, so this is how the same bytes are reached from a mirror without editing bytes
R14 §2.3 makes immutable. It is a reader convenience and not a format change: what a packet says
is untouched. `git config url.<base>.insteadOf` is the same mechanism.

### A dataset is the entry point for more than one packet (R86)

`open_packet` gives one packet's tables under their own names, and R53 §2.5 makes those unsafe to
concatenate: an assigned identifier is unique within its packet and means nothing outside it, so
two packets both hold `unit_id` 0 and neither value names the other's unit. Measured on the two
packaged sessions, **4,505 `unit_id` values name a unit in both** and both sessions are
`session_id = 0`.

`open_dataset` is the second entry point. It numbers every session it opens and projects
`session_key` and `session_name` onto every **session-scoped** table -- one reaching
`core.sessions` through its declared references, which `dataset.session_scoped` computes from the
registry a packet embeds, 41 of 43. The two that are not, `core.subjects` and `core.source_files`,
get no key, because R86 §2.2 forbids one where the row is not a session's.

The discriminator comes from **provenance, never from a label**: the packet a row came from plus
its own `session_id`. A `*_name` is not usable for it -- 6 of 13 name columns hold a value
appearing in both packets, `event_name` on 4,223 trial-numbered events.

Identity is **projected, not joined for** (R86 §2.4): a scalar `CASE` over `session_id`, which a
query not selecting it has pruned, at 1.02x against the 2.22x of the `core.sessions` join a reader
writes first. And it is **carried, not joined on** (R86 §2.3) -- a query over one session still
joins on `unit_id` alone, because widening the key costs 2.93x over 286,896,563 spikes.

The shape does not depend on how many packets are open, so an analysis written against one session
and later pointed at twenty meets the same relation rather than a differently shaped one.

**What R86 requires and does not specify.** A scoped table that reaches `core.sessions` without
carrying `session_id` leaves a multi-session packet with only a join to answer with, which R86 §2.4
declines to specify, so `Dataset` raises `MultiSessionUnresolved` naming the table rather than
guessing. R88 §2.1 then made the column required on every scoped table, so **no table in the
current registry reaches that branch** — it guards a packet built against an older one, and
`tests/test_dataset.py` exercises it against a registry that omits the column.

### A discriminator is resolved here, not by every caller (Part 02 §8.3)

`discriminators.py` offers what Part 02 §8.3 asks a reader to offer: read the kind, take that
resource's key from the registry, join. The reason it names is that a discriminator nothing reads
is a free-form name with extra steps, and the join is not obvious — it takes **three shapes**, and
reading one as another is what that section's exclusion exists to stop.

`declared` reports what the packet's **own** registries declare, core and extensions together,
because a kind naming an extension table is the case the mechanism exists for and building over
core alone is the defect R55 was written for. `kinds` counts what the rows name, `resolved` joins
one of them, and `unresolved` reports what a packet names and does not hold — at the level the
section assigns, a defect where `resolves` is `required` and a fact where it is `optional`, and
apart from a row declaring no kind at all, which is **undeterminable** and wants the missing half
recorded rather than the value corrected.

Two details are easy to get wrong and are why this lives here. A shared-key join goes against the
**discriminated** table, which `discriminates_via` moves away from the one carrying the column:
`core.event_streams.detail_kind` specialises `core.events`. And a paired value is a `string` where
the named key is an `int32` a packet mints, so it matches that resource's `*_name` and not its key
(Part 02 §8.2).

### A channel index is resolved through the list its run kept (Part 02 §12.2)

A sorting drops bad channels before it runs, so a channel index it emits afterwards counts what it
kept and not the probe's contacts. `channels.py` is where that is settled: `kept_channels` reads
`core.sorting_run_channels`, `electrode_at` performs the lookup, and `runs_without_channels` names
the runs no index can be resolved for.

A wrong reading still returns a contact, so nothing about the answer says it is wrong. Measured on
the two packaged sessions, **3,375 of 4,510** channel indices in `ecephys_776259` and **1,651 of
3,813** in `ecephys_786867` name a different contact than the full contact list would, because
eleven of twelve runs and seven of ten dropped channels — one diverging as early as index 2. Where
a run dropped only from the tail, nothing shifts at all, which is how the convention stayed
invisible.

A run that declares no channels is reported and never resolved against `core.electrodes`
(R83 §2.3): such a packet is conforming, so the gap is a fact about what it carries and the answer
a consumer owes its caller is which run it cannot resolve. `UnresolvableChannelIndex` carries
`channels_declared` to separate that from an index outside a list the run *did* declare, since one
wants the list recorded and the other wants the index corrected.

Two checks are repeated here rather than assumed, because this package validates nothing: a table
missing a required column is refused rather than read as a run declaring nothing, and indices that
are not `0` to `n-1` are refused rather than indexed by position, which would return a wrong
electrode in silence.

A unit's own peak contact needs none of this — `core.unit_electrodes.is_primary` carries it, and
resolving an index to reach the same electrode repeats the writer's work.

### Registration is not free over a store

DuckDB binds a view when it is created, and binding a Parquet view reads that file's footer.
Locally that is nothing; against S3 it is a round trip per table, measured at 3.5 s of the 3.9 s
a one-table question cost on a 28-table packet. So `Packet.duckdb()` **registers nothing by
default**. Name what you need with `tables=`, pass the query as `for_query=` and let it read the
names out, or ask for `tables="all"` -- which is what the validator does, because it runs every
rule. `Packet.sql()` is unchanged for callers: it registers what the query names.

Registration is idempotent and re-entrant: `_register` asks the connection what it already holds
and re-runs `register_views` afterwards, so a view skipped for want of an input gains it when
that input is registered by a later query.

Part 07 names the CLI `escapewheel`, which this package claims under `[project.scripts]`. Later
packages **cannot** also claim it — two distributions declaring the same console script is a
conflict, and the last one installed wins silently. So they register a callable under the
`escapewheel.commands` entry-point group instead, and `cli._extend` loads them at parse time.
`cli.EXTENSIONS` names the subcommands that live elsewhere, so an uninstalled one reports
which package provides it rather than failing as an argparse "invalid choice".

## Testing

Tests build their own minimal packet in `tmp_path` (see `tests/conftest.py`) rather than
depending on `../fixtures/`, whose built packets are gitignored. Keep it that way — this package
must be testable with nothing else built.

For an end-to-end check against a real packet, `python ../fixtures/build.py` writes
`../fixtures/packets/valid`, a single-session packet holding every core table;
`../fixtures/corpus.py` runs the full conformance corpus.

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

`src/` layout, package in `src/escapewheel_reader/`, tests in `tests/`. Hatchling build, ruff at
120 columns with numpy docstrings, mypy strict, pytest with coverage, commitizen for
versioning, Sphinx with furo for docs. CLI entry points go in `[project.scripts]` and are
implemented in `src/escapewheel_reader/scripts/`.

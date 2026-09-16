# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The reference **validator** for Escapewheel packets. It answers one question — does this packet
conform? — and returns a machine-readable `Report` whose findings are the offending rows.

It depends on `escapewheel-reader` and adds `escapewheel validate`. It does not read packets for
any other purpose, and it does not write them.

### Why this is not part of the reader

Its correctness is pinned to a **registry version**; the reader's API is not. Twenty
revisions in, every new table or rule would otherwise force a reader release for code that
had not changed. The split also keeps DuckDB out of the read path's dependency closure by
construction rather than by discipline.

### Where the specification lives

This package implements a specification kept in sibling **directories** of the same repository,
under `../`. Version control has been one repository at the root since 2026-09-04. When behaviour
here seems arbitrary, the reason is there.

| Directory | Contents |
|---|---|
| `nwb_lake_poc_docs/` | The frozen v0.1 specification. Never edited. |
| `escapewheel_poc_docs_v0.2/` | The editable parts, which are what bind. Part 05 is the import and validation pipeline. |
| `revisions/` | One file per accepted change. Where a revision and the frozen docs disagree, the revision binds. |
| `registry/` | `logical_schemas.json`, its meta-schema, and the manifest JSON Schema. |
| `fixtures/` | The conformance corpus, each packet with its expected findings as data. |
| `escapewheel-reader/` | The read path. This package's only runtime dependency of substance. |

<!-- BEGIN facts: revisions -->
R1–R41, R43–R72 and R74–R119 accepted. R42 and R73 withdrawn. No draft is open.
<!-- END facts: revisions -->
<!-- BEGIN facts: registry -->
43 tables, 351 columns, 111 references, 77 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: corpus -->
28 conformance packets
<!-- END facts: corpus -->

`stores.py` lives here rather than in the reader because **no read path uses it**: a table
resolves to a local path or is refused, a Zarr array is handed its URI and `zarr` opens it with
its own backend, and DuckDB reaches an object store through its own C++ client. What needs a
store client is R36's verification -- list a prefix, hash its members. Both users are on that
side: this package checks what a manifest claims, and `escapewheel-writer` establishes it through
its `verify` setting, depending on this package already. Hence the `remote` and `s3` extras.

The contract it needs is two operations, `list(prefix)` and a ranged `get(key)`, not a
filesystem. Measured against a real bucket, every client lands within 26% of every other once
reads are concurrent, so the choice is dependency weight and scheme coverage rather than speed.

`src/escapewheel_validator/schemas/registry.schema.json` is a **vendored copy** from
`registry/`. Re-copy it when the meta-schema changes there; it is not generated at build time.

`registry_document.py` holds the invariants any registry document is held to — a reference relating
columns of the same type, role and identity; a namespace prefixing its own tables; a discriminator
declaring what it resolves to. They live here because they are checks, and because an author outside
this repository has the same document and the same question: `escapewheel extension check` runs
them, and `registry/check.py` imports the same functions, so core is held to exactly what an
extension is. What stays in that script is what is true of this repository's *build* rather than of
a document — the R9 §2 ledger, `derived_from`, the rule-expansion round trip.

## Scope

Part 07 sets the phase plan. This package is Phase 2.

**Delivered.** Tier 1 checks generated from each table's structure, Tier 2 rules read from
the registry the packet embeds, the schema and physical-ordering layers SQL cannot express,
and the `escapewheel validate` subcommand with an optional JSON report.

**Also delivered.** Advisory rules (R26) — `validate(packet, advisory=True)` and
`escapewheel validate --advisory`. They are never `error`, so enabling them cannot change whether
a packet passed, and the report records whether they ran.

**Also delivered.** Level 2 (R15 §4) — every packet-owned array against the metadata document
in its own store: codecs, Zarr version, chunk grid, fill value, and rank against
`core.array_dimensions`. The shim, not SQL (R12 §4), and it needs no Zarr, because the metadata
is JSON. It caught a real defect on its first run: a sharded array whose manifest declared only
the inner codec.

**Not yet.** The external mode (R15 §4, level 3): nothing resolves an external URI or checks
its `sha256`, `size_bytes`, or actual codecs. Needed for the LFP arrays.

## Developer guidance

**`CONTRIBUTING.md` is the canonical statement**, and its first section matters most: most new
checks belong in `../registry/rules.json`, not in this package. Tier 1 is generated from
structure and Tier 2 is authored as data; Python lands here only for what a query cannot see at
all. Decide SQL-or-shim before writing (R12 §4) — a storage-layer check written as SQL reports
success on a broken packet.

## Architecture

```
generate    registry structure -> Tier 1 Check objects, plus the Tier 2 rules it carries
validator   four layers over a packet, returning a Report
Finding     one failure: level, check id, message, and the rows that caused it
```

### The ordering scan reads strings as codes

`_check_ordering` compares a table's sort columns row by row, so how they are held decides its
cost wherever one is a string: `core.events` sorts on `event_type` and
`core.session_experimenters` on `experimenter`. It reads them with `read_dictionary` and
`_ranked` compares the *rank* of each dictionary value as int32 — never the codes, which are
unordered, and never the dictionary itself, which `pc.less` decodes on both sides every call.
A column that is not dictionary-encoded passes through `_ranked` untouched, which is every
identifier (R53 §2.1). `_breaks`
makes one pass where `_descents` and `_repeats` each made their own: a descent needs a
column's `less` mask and a duplicate needs its `same` mask, and one comparison yields both.

Together those took a full validation of a 287 M-row packet from 66.3 s to 37.1 s.
`escapewheel-writer/docs/source/performance.md` carries the measurements and the dictionary
rules; they apply on both sides of the boundary.

### Design decisions carried from the specification

These are not local preferences; changing them breaks conformance.

- **Rules are data, not code** (R2 §7). Tier 1 is *generated* from required-column presence,
  primary keys, foreign keys, and closed vocabularies — never hand-written per table. A rule
  that has to be hand-written is Tier 2 and belongs in `registry/rules.json`, not here.
- **A check's query returns offending rows.** Empty is a pass; non-empty is a failure and the
  rows *are* the finding. This is the whole execution contract — a rule that returns a count,
  or a boolean, cannot report what went wrong and does not belong.
- **Validation splits by what a query can see** (R12 §4). SQL covers what the data *says* —
  values, keys, references, vocabularies. Python covers how it is *stored* — column presence,
  Parquet types, physical order, file existence. A storage-layer check written as SQL fails
  silently rather than loudly, which is how R12 came to exist. When adding a check, decide
  which side of that line it falls on before writing it.
- **No registry is bundled.** `validate()` uses the copy the packet embeds (R2 §8) or one
  passed explicitly. A packet written against registry 0.1.0 must keep validating against
  0.1.0 when the reference registry moves on. Bundling a reference copy would let this
  package's idea of the schema silently overrule the packet's own.
- **A nullable foreign key needs an `IS NOT NULL` guard.** Six of the registry's references
  are nullable; without the guard every null row reports as an unresolved reference.
- **An amendment re-runs only the rules its own resources implicate** (R35 §5). `validate`
  takes `recheck`, the resources just written; a check survives when it is attached to one or
  when its SQL *names* one. The name test is syntactic over R2 §7's flattened form, which is
  what makes it sound without the registry promising that no existing rule references a
  resource added later — amending `core.processing_runs` re-runs foreign-key checks declared
  on `core.event_streams` and `core.processing_run_inputs`. It is deliberately over-inclusive:
  a match in a comment costs time, a missed one costs correctness. `None` runs everything,
  which is what a first commit and an unknown packet both need.
- **Validation does not reach the network by default** (R14 §2.3.2, R15 §4). Three levels:
  manifest-internal codec consistency always; a packet-owned array's actual Zarr metadata
  always; an external resource's URI, `size_bytes` and `codecs` only under `external=True`.
  Whether an external resource is reachable is a property of the reader's situation, not of
  the packet, so unreachable is a `warning` and a claim that resolved and disagrees is an
  `error`. Exactly one of `external.unverified` and `external.verified` is reported, so a
  passing run always says which mode produced it.
- **Level 3 is two levels, because they cost differently** (R36 §2.3). `external=True` lists
  the store and checks `size_bytes` and codecs — 65 ms over a session's twelve LFP arrays.
  `checksums=True` also recomputes `sha256`, which reads every byte: 47 s over 6.83 GB here,
  and a bill as well as a wait against an object store. Never one flag.
- **The codec floor is per Zarr version** (R21 §3.3), in `FLOOR`. `gzip` is in R3 §7.2's
  baseline and Zarr.jl reads it in v3 and not in v2, so a codec's readability belongs to the
  `(version, codec)` pair. Outside the floor is `info`, not an error: such a packet conforms
  and is simply not portable by default (R14 §2.2).
- **What the manifest JSON Schema already refuses is not re-checked here.** R14 §2.3's
  "absolute URI implies external" and R21 §3.2's "zarr_v2 implies external" are conditionals
  in `manifest.schema.json`, and a packet breaking either cannot be opened at all. A second
  copy in Python would never run.
- **Identifiers come from `escapewheel_reader.sql`.** The reader registers tables under
  flattened names and this package emits SQL against them; they must agree exactly, so there
  is one implementation and it lives there.

## Testing

Tests build their own minimal packet in `tmp_path` (`tests/conftest.py`) rather than
depending on `../fixtures/`, whose built packets are gitignored. That conftest is a near-copy of the reader's — deliberate duplication, so both suites run
standalone. `tests/test_cli.py` goes through `escapewheel_reader.scripts.cli.main`, so a pass
proves the entry-point wiring rather than just the handler.

For an end-to-end check, `../fixtures/corpus.py` runs the whole corpus, each packet's expected
findings recorded as data. Run it after changing the registry, the generator, or any rule.

```bash
cd ../fixtures && uv run --no-cache --with ../escapewheel-validator --with duckdb python corpus.py
```

## The CLI

Part 07 names one command, `escapewheel`. `escapewheel-reader` owns the console script; this package
registers under the `escapewheel.commands` entry-point group instead, because two distributions
declaring the same `[project.scripts]` name is a conflict in which the last one installed
wins silently.

```toml
[project.entry-points."escapewheel.commands"]
validate = "escapewheel_validator.scripts.cli:register"
```

`register(subcommands)` adds parsers and nothing else. Any future package adds its
subcommands the same way.

## Commands

```bash
uv sync                                   # install, including the reader from ../
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
uv run pytest
uv run pytest -k "test_name"              # one test
uv run ruff format
uv run ruff check --fix
uv run mypy
```

Always use `uv run` to execute commands, `uv add` to add dependencies, and `uv sync` to set up
the environment. Never use bare `pip` or `python`.

## Conventions

`src/` layout, package in `src/escapewheel_validator/`, tests in `tests/`. Hatchling build, ruff
at 120 columns with numpy docstrings, mypy strict, pytest with coverage, commitizen for
versioning, Sphinx with furo for docs.

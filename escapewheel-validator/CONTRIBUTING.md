# Contributing to escapewheel-validator

This package checks a packet against the registry it embeds. `README.md` covers running it; this
covers changing it.

## Where the rules come from

Use the monorepo's [authority model](../README.md#authority). The registry embedded in a packet
governs that packet's declared tables and rules; the current core registry in
`../spec/artifacts/` is generated source data for new packets.

The schemas under `src/escapewheel_validator/schemas/`, and `registry_document.py` and
`rule_language.py`, are copies of files in the specification's tree, listed in `pyproject.toml`'s
`[tool.escapewheel.copies]`. Change the tree's file, run `tools/copies.py` from the monorepo root, and
commit both; never edit a copy directly. `tests/test_copies.py` fails where a copy disagrees.

`registry_document.py` returns the complete ordered Part 02 §9.4 result. Do not add a second
registry checker at a caller boundary: invoke that result. The descriptor enumerates invariant
IDs and applicability, while Parts 02 and 09—not Python labels—own their meaning. Literal-unit
checks use the exact offline UCUM 2.2 data dated 2024-06-17; a printable-character approximation
is not a substitute.

The registry result is computed at a trust boundary, not on every ordinary packet read. Part 02
defines the result but deliberately leaves mandatory invocation and cache identity to the next
specification decision. Do not add an implicit reader-open hook while changing the checker.

**Read the next section before writing any code here.** The most common contribution to this
package belongs in the registry, and the design is what makes that true.

---

## Most new checks do not go here

**Rules are data, not code** (R2 §7).

- **Tier 1 is generated** from structure — required-column presence, primary keys, foreign keys,
  closed vocabularies, finite values, none of them hand-written. If your check is one of
  those five shapes, it already exists the moment the registry declares the column.
- **Tier 2 is hand-written portable-profile SQL**, and it lives in the registry, **not here**:
  each is a `[[rules]]` entry in its table's file under `../spec/source/core/`. Adding one is editing
  that file and running `build.py`. Nothing in this package needs to change.

So before writing Python, ask which of these your check is. Code lands here only for something a
query cannot see at all — see *SQL or shim* below.

A rule may also be a **template invocation** rather than SQL (R24). `interval` is the only one;
`assemble.py` expands it, so the registry a packet embeds still carries plain SQL and no validator
has to learn a vocabulary.

## The execution contract

**A check's query returns offending rows. Empty is a pass; non-empty is a failure and the rows
*are* the finding.**

That is the whole protocol. A rule that returns a count, or a boolean, cannot report *what* went
wrong and does not belong. If you find yourself writing `SELECT COUNT(*)`, the rule is wrong,
not the contract.

## SQL or shim — decide before you write

R12 §4 splits validation by what a query can see:

| | |
|---|---|
| **SQL** | what the data *says* — values, keys, references, vocabularies, cross-table agreement |
| **Python shim** | how it is *stored* — column presence, Parquet types, physical order, file existence, Zarr rank and codecs, checksums |

One value check lives in the shim: unit-column values are parsed as UCUM codes (Part 05 §5.3),
because the rule language has no UCUM grammar and adding one would make a nomenclature part of
the SQL profile.

**A storage-layer check written as SQL fails silently rather than loudly.** R12 exists because
one did. Physical order is the example: a query sees a set of rows and cannot see the order they
were written in, so a rule asserting it passes on a file that violates it.

Getting this wrong is not a style error — it produces a check that reports success on a broken
packet, which is worse than having no check.

## Rules that hold here

- **No registry is bundled or supplied.** `validate()` uses the registries the packet binds (Part 04
  §8), and Part 05 §14.5 forbids a caller-supplied one. A packet must keep validating against its
  bound registries when the reference registry moves on. A bundled or supplied copy would let
  this package's idea of the schema silently overrule the packet's own.
- **A foreign key that may be null needs an `IS NOT NULL` guard**, nullable or optional alike.
  Without it every null row reports as an unresolved reference.
- **A generated check reading an `optional` column declares it in `optional_columns`.** A table may
  omit the column (Part 02 §6), and the query would then fail to bind rather than find nothing.
- **An amendment re-runs only the rules its resources implicate** (R35 §5). `validate` takes
  `recheck`; Tier 1 inputs come from declarations, Tier 2 inputs from the parsed base-resource
  set, and shim inputs from their explicit contracts.
- **Validation does not reach the network by default** (R14 §2.3.2, R15 §4). A packet-owned
  resource's own metadata is read always; an external resource's URI, size and Zarr metadata only
  under `external=True`. Unreachable is a `warning`, since reachability is a property of the
  reader's situation and not of the packet; a URI that resolves and disagrees is an `error`.
- **`external` and `checksums` are never one flag** (R36 §2.3). Listing a store and checking sizes
  is 65 ms over a session's twelve LFP arrays. Computing a digest reads every byte: 47 s over
  6.83 GB, and a bill as well as a wait against an object store. A store's full-object checksums
  cost one request per object instead, and a composite one never counts (Part 04 §5.3).
- **Reader floors come from the descriptor, never from a constant here** (R137). Zarr metadata is
  matched with the reader's `zarr_floor_admits` against the variant its `zarr_format` selects, and
  a Parquet footer's compressions and encodings against `parquet_floor()`, so a restated floor needs
  no validator change. `physical.outside_reader_floor` is one finding per resource: `warning` for a
  packet-owned table, whose writer the Parquet floor also binds, and `info` otherwise, since a
  reader-only floor leaves a packet conforming and only less portable. An unrecognized codec is
  valid metadata outside the floor, not invalid metadata. Each external resource with a floor whose
  metadata no check read draws its own `external.physical_unassessed`, attributed like any
  resource finding, and `physical.page_types_unassessed` states that page headers were not read.
- **What the manifest JSON Schema already refuses is not re-checked here.** A packet breaking
  R14 §2.3's "absolute URI implies external" cannot be opened at all, so a second copy in Python
  would never run.
- **Tier 2 relation names are canonical resource IDs.** Use qualified names such as `core.units`;
  the validator installs exact packet-local schemas and rejects flattened aliases.
- **Every exception raised on purpose is defined in `errors.py` under `ValidatorError`.** It carries
  as attributes what a caller would otherwise read from its message, and keeps a built-in second
  base only where a caller already catches that built-in. A test asserts the class and those
  attributes, never the wording. `tests/test_errors.py` holds the rule; `RegistryRejected` and
  `RuleProfileError` stand outside it, being defined in the copied checkers.
- **A level, a verdict, an evaluation status and a registry state are members of the enumerations
  in `vocabulary.py`, never string literals.** Each member equals the string a report's JSON
  carries, so a caller holding that string compares against the member. `tests/test_vocabulary.py`
  holds the rule.
- **A check ID is written once, in `check_table.py`.** A new check adds an entry there with its
  default level, its scope and whether a numbered part names it: a constant for a fixed ID, a
  template and a function for a family built from a resource or a column. `Report.add` takes the
  entry and reports at its level; `entry.at(level)` is for a check whose level depends on what was
  found. No other module writes an ID as a string. `tests/test_check_table.py` holds the rule.

## An advisory rule is not a compromise

A rule may be `advisory` (R26): off by default, never `error`, so enabling it cannot change
whether a packet passed.

Use it when the requirement binds the **consumer** rather than the packet. R41 §2.4 forbids a
*consumer* silently choosing between runs, so a packet with two runs and no declared preference is
*conforming* — an `error` there would fail a valid packet, and silence would hide a real hazard.
`core.processing_runs.undeclared_currency` is the worked example.

## Testing

Tests build their own minimal packet in `tmp_path` (`tests/conftest.py`) rather than depending on
`../fixtures/`, whose built packets are gitignored. That conftest is a
near-copy of the reader's — **deliberate duplication, so both suites run standalone.** Keep it
that way.

`tests/test_cli.py` goes through `escapewheel_reader.scripts.cli.main`, so a pass proves the
entry-point wiring rather than just the handler.

**The conformance corpus is the acceptance test.** One conforming packet and its variants, each
with its expected finding recorded as data, so any implementation can be checked against the same
evidence rather than against a prose description:

```bash
cd ../fixtures && uv run --no-cache --with ../escapewheel-validator --with duckdb python corpus.py
```

Run it after changing the registry, the generator, or any rule. A new rule should arrive with a
variant that trips it — a rule nothing exercises is a rule nobody knows works. `conformance/registries/check.py`
statically checks every Tier 2 rule and executes it against typed empty tables, which proves a rule *binds* but not that it can
*report*: one bound cleanly for weeks and failed only once it had a finding to return.

## Before you push

```bash
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
```

Commits are conventional (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`). The title is
imperative; the body says **what changed and why**, not how.

## Conventions

`src/` layout, package in `src/escapewheel_validator/`, tests in `tests/`. Hatchling, ruff at 120
columns with numpy docstrings, mypy strict, pytest with coverage, Sphinx with furo. This package
registers its CLI under the `escapewheel.commands` entry-point group rather than
`[project.scripts]`: two distributions claiming the same console script is a conflict in which
the last installed wins silently.

Docstrings are terse and say what is not obvious from the code: why this way, what breaks
otherwise, the constraint that is not visible locally. No history, no ticket numbers, no dataset
names.

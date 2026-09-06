# Contributing to escapewheel-validator

This package checks a packet against the registry it embeds. `README.md` covers running it; this
covers changing it.

**Read the next section before writing any code here.** The most common contribution to this
package belongs in a different repository, and the design is what makes that true.

---

## Most new checks do not go here

**Rules are data, not code** (R2 §7).

- **Tier 1 is generated** from structure — required-column presence, primary keys, foreign keys,
  closed vocabularies. 211 checks over 35 tables, none hand-written. If your check is one of
  those four shapes, it already exists the moment the registry declares the column.
- **Tier 2 is hand-written SQL**, and it lives in `../registry/rules.json`, **not here**. Adding
  one is editing a JSON file in the registry and running `build.py`. Nothing in this package
  needs to change.

So before writing Python, ask which of these your check is. Code lands here only for something a
query cannot see at all — see *SQL or shim* below.

A rule may also be a **template invocation** rather than SQL (R24). `interval` is the only one;
`build.py` expands it, so the registry a packet embeds still carries plain SQL and no validator
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

**A storage-layer check written as SQL fails silently rather than loudly.** R12 exists because
one did. Physical order is the example: a query sees a set of rows and cannot see the order they
were written in, so a rule asserting it passes on a file that violates it.

Getting this wrong is not a style error — it produces a check that reports success on a broken
packet, which is worse than having no check.

## Rules that hold here

- **No registry is bundled.** `validate()` uses the copy the packet embeds (R2 §8), or one passed
  explicitly. A packet written against registry 0.1.0 must keep validating against 0.1.0 when the
  reference registry moves on. Bundling a reference copy would let this package's idea of the
  schema silently overrule the packet's own.
- **A nullable foreign key needs an `IS NOT NULL` guard.** Without it every null row reports as an
  unresolved reference.
- **An amendment re-runs only the rules its resources implicate** (R35 §5). `validate` takes
  `recheck`; a check survives when it is attached to a named resource or when its SQL *names* one.
  The name test is syntactic and deliberately over-inclusive: a match in a comment costs time, a
  missed one costs correctness.
- **Validation does not reach the network by default** (R14 §2.3.2, R15 §4). Three levels:
  manifest-internal codec consistency always; a packet-owned array's actual Zarr metadata always;
  an external resource's URI, size and codecs only under `external=True`. Unreachable is a
  `warning`, since reachability is a property of the reader's situation and not of the packet; a
  URI that resolves and disagrees is an `error`.
- **`external` and `checksums` are never one flag** (R36 §2.3). Listing a store and checking sizes
  is 65 ms over a session's twelve LFP arrays. Recomputing `sha256` reads every byte: 47 s over
  6.83 GB, and a bill as well as a wait against an object store.
- **The codec floor is per Zarr version** (R21 §3.3), in `FLOOR`. `gzip` is in R3 §7.2's baseline
  and Zarr.jl reads it in v3 but not in v2, so readability belongs to the `(version, codec)` pair.
  Outside the floor is `info`, not an error — such a packet conforms and is simply not portable
  by default.
- **What the manifest JSON Schema already refuses is not re-checked here.** A packet breaking
  R14 §2.3's "absolute URI implies external" cannot be opened at all, so a second copy in Python
  would never run.
- **Identifiers come from `escapewheel_reader.sql`.** The reader registers tables under flattened
  names and this package emits SQL against them. One implementation, so they cannot drift.

## An advisory rule is not a compromise

A rule may be `advisory` (R26): off by default, never `error`, so enabling it cannot change
whether a packet passed.

Use it when the requirement binds the **consumer** rather than the packet. R41 §2.4 forbids a
*consumer* silently choosing between runs, so a packet with two runs and no declared preference is
*conforming* — an `error` there would fail a valid packet, and silence would hide a real hazard.
`core.processing_runs.undeclared_currency` is the worked example.

## Testing

Tests build their own minimal packet in `tmp_path` (`tests/conftest.py`) rather than depending on
`../fixtures/`, whose output is gitignored and lives in another repository. That conftest is a
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
variant that trips it — a rule nothing exercises is a rule nobody knows works. `registry/check.py`
executes every Tier 2 rule against empty tables, which proves a rule *binds* but not that it can
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

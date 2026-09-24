# Escapewheel Validator

![CI](https://github.com/AllenNeuralDynamics/escapewheel-validator/actions/workflows/ci-call.yml/badge.svg)
[![PyPI - Version](https://img.shields.io/pypi/v/escapewheel-validator)](https://pypi.org/project/escapewheel-validator/)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border.json)](https://github.com/copier-org/copier)

Validate an Escapewheel packet against the registries it binds.

Registry documents have their own ordered conformance result before packet rows are considered.
The incorporated descriptor enumerates seven phases and 20 stable invariant IDs; the validator
uses the same result for core and extensions. Local JSON shape comes from the registry
meta-schema, cross-declaration meaning from Parts 02 and 09, Tier 2 static checks from Part 11,
and literal units from an offline case-sensitive UCUM 2.2 parser.

Validation first runs Part 04 §10's manifest phases: the manifest's JSON and shape, the checks
that need only the manifest, then registry binding. Binding acquires each registry through its
descriptor, verifies the digest over the decompressed bytes, obtains the registry's complete
result, and compares its identity, role, version, and standards with the descriptor. The report
retains every acquired registry's result, labelled by registry ID. Only a bound registry that
passed binding and is valid directs packet checks; no caller-supplied registry can stand in for
one. An extension that fails binding withholds only its own entries.

Rules are **data, not code**. `registry/logical_schemas.json` carries every table's structure
and its Tier 2 rules, and the checks are generated from it rather than written per table. The
execution contract is the whole protocol: **a check's query returns offending rows — empty is
a pass, non-empty is a failure and the rows are the finding.**

```bash
escapewheel validate packet/              # exits non-zero on any error
escapewheel validate packet/ --advisory   # include rules that are off by default (R26)
```

```python
from escapewheel_reader import open_packet
from escapewheel_validator import validate

report = validate(open_packet("packet/"))
report.passed, report.errors, report.warnings
report.registries  # complete, role-labelled registry-document results
```

## What runs

Most of what runs is generated rather than written. The registry the packet embeds decides how
much, so the counts below are the current reference registry's and a packet carrying an older one
gets its own.

<!-- BEGIN facts: registry -->
43 tables, 348 columns, 111 references, 76 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: tier1 -->
164 not-null, 111 foreign-key, 4 closed-vocabulary and 16 discriminator checks, plus one uniqueness check per table whose sort does not begin with its primary key
<!-- END facts: tier1 -->

| | Comes from |
|---|---|
| required-column non-null | `presence: required` |
| foreign-key anti-join | `references`, with a null guard where the column is nullable |
| primary-key uniqueness | `primary_key`, and only where a streaming scan does not already settle it |
| closed vocabulary | `enum` |
| discriminator | `role: discriminator`, two checks each (R55 §2.4) |
| Tier 2 | statically checked `escapewheel-rule-sql-v0.1` queries the structure cannot imply, authored in `registry/rules.json` |

## SQL and the shim

`R12 §4` draws the line: **SQL for what the data says, the shim for how it is stored.** A
relation has no row order, no file layout, no Parquet physical type and no Zarr chunk grid, so
a storage check written as SQL agrees with itself rather than failing. The shim covers physical
order (R10), column presence and physical type, manifest-internal consistency, and every
packet-owned array against its own Zarr metadata (R15 §4 level 2) — the last needing no Zarr,
because that metadata is JSON. It also parses every unit-column value as a UCUM code (Part 05
§5.3): a value check, but one SQL could express only through a UCUM function the rule language
does not have.

Tier 2 SQL is not DuckDB's full dialect. The validator parses each rule against the versioned
portable profile before execution, derives its base-resource dependencies from that parse, exposes
canonical schema-qualified relations, and reports unsupported, invalid, or incomplete evaluation
separately from packet findings.

The two halves cooperate: the ordering scan compares neighbours, so where a table's sort begins
with its primary key, duplicates must be adjacent and the same pass settles uniqueness. On 287
million spikes that replaced a `GROUP BY` which spilled 26 GB.

## Installation

If you choose to clone the repository, you can install the package by running the following command from the root directory of the repository:

```bash
pip install .
```

Otherwise, you can use pip:

```bash
pip install escapewheel-validator
```



To develop the code, run:
```bash
uv sync
```

## Development

**Changing this package?** Read [CONTRIBUTING.md](CONTRIBUTING.md) first — it carries the rules
that decide what belongs here, and the process for a specification defect found while
implementing.


Please test your changes using the full linting and testing suite:

```bash
./scripts/run_linters_and_checks.sh -c
```

Or run individual commands:
```bash
uv run --frozen ruff format          # Code formatting
uv run --frozen ruff check           # Linting
uv run --frozen mypy                 # Type checking
uv run --frozen interrogate -v src   # Documentation coverage
uv run --frozen codespell --check-filenames  # Spell checking
uv run --frozen pytest --cov escapewheel_validator # Tests with coverage
```


### Documentation
```bash
sphinx-build -b html docs/source/ docs/build/html
```


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
The packaged [third-party notices](src/escapewheel_validator/licenses/THIRD_PARTY_NOTICES.md)
cover the offline UCUM parser and its UCUM 2.2 data.

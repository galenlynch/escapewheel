# NWB Lake Validator

![CI](https://github.com/AllenNeuralDynamics/nwb-lake-validator/actions/workflows/ci-call.yml/badge.svg)
[![PyPI - Version](https://img.shields.io/pypi/v/nwb-lake-validator)](https://pypi.org/project/nwb-lake-validator/)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border.json)](https://github.com/copier-org/copier)

Validate an NWB-Lake packet against the registry it embeds.

Rules are **data, not code**. `registry/logical_schemas.json` carries every table's structure
and its Tier 2 rules, and the checks are generated from it rather than written per table. The
execution contract is the whole protocol: **a check's query returns offending rows — empty is
a pass, non-empty is a failure and the rows are the finding.**

```bash
nwb-lake validate packet/              # exits non-zero on any error
nwb-lake validate packet/ --advisory   # include rules that are off by default (R26)
```

```python
from nwb_lake_reader import open_packet
from nwb_lake_validator import validate

report = validate(open_packet("packet/"))
report.passed, report.errors, report.warnings
```

## What runs

241 checks over 33 tables, of which **192 are generated and 49 hand-written**:

| | Count | Comes from |
|---|---|---|
| required-column non-null | 130 | `presence: required` |
| foreign-key anti-join | 46 | `references`, with a null guard where the column is nullable |
| primary-key uniqueness | 13 | `primary_key` — the other 20 tables are settled by a streaming scan |
| closed vocabulary | 3 | `enum` |
| Tier 2 | 49 | SQL the structure cannot imply, authored in `registry/rules.json` |

## SQL and the shim

`R12 §4` draws the line: **SQL for what the data says, the shim for how it is stored.** A
relation has no row order, no file layout, no Parquet physical type and no Zarr chunk grid, so
a storage check written as SQL agrees with itself rather than failing. The shim covers physical
order (R10), column presence and physical type, manifest-internal consistency, and every
packet-owned array against its own Zarr metadata (R15 §4 level 2) — the last needing no Zarr,
because that metadata is JSON.

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
pip install nwb-lake-validator
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
uv run --frozen pytest --cov nwb_lake_validator # Tests with coverage
```


### Documentation
```bash
sphinx-build -b html docs/source/ docs/build/html
```


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

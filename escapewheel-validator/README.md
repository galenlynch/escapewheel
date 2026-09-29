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

An extension's resources receive every storage check core's do: column types, physical order,
duplication, unfilled `metadata`, reserved values, and unit codes (Part 05 §5.4). Each finding
belongs to the packet or to one bound registry, and the report gives the packet, core, and each
bound extension a verdict of `passed`, `failed`, or `incomplete` (Part 05 §9.5). The packet's
verdict is the worst of them, so a failing extension fails the packet and leaves core `passed`.
The JSON report's `status` is the packet verdict, `verdicts` maps each registry ID to its own, and
each finding's `registry` names its subject, `null` for the packet.

Rules are **data, not code**. `registry/logical_schemas.json` carries every table's structure
and its Tier 2 rules, and the checks are generated from it rather than written per table. The
execution contract is the whole protocol: **a check's query returns offending rows — empty is
a pass, non-empty is a failure and the rows are the finding.**

```bash
escapewheel validate packet/              # exits non-zero unless the packet verdict is passed
escapewheel validate packet/ --advisory   # include rules that are off by default (R26)
```

```python
from escapewheel_reader import open_packet
from escapewheel_validator import validate

report = validate(open_packet("packet/"))
report.passed, report.errors, report.warnings  # passed: the packet verdict is `passed`
report.verdict(), report.verdict("core")       # "passed", "failed", or "incomplete"
report.registries  # complete, role-labelled registry-document results
```

## Resource digests

Every resource the packet owns records a `digest` naming its algorithm: `sha256`, `crc64nvme`,
`crc32c`, or `crc32` (Part 04 §4.3). An entry without one is `packet.resource.digest_missing`,
an `entries` finding that withholds the declaration phases, as is a `uri` neither absolute nor a
relative reference in Part 03 §4's one form (`packet.resource.uri_form`). A prefix's value is the
SHA-256 of its member listing under every algorithm, each key its names in UTF-8 as they are.

```bash
escapewheel validate packet/ --checksums                       # establish every recorded digest
escapewheel validate packet/ --checksums --no-store-checksums  # and read every byte to do it
```

`--checksums` checks packet-owned digests and, since it implies `--external`, referenced ones.
Where an object store reports a full-object checksum in the digest's algorithm, the validator
takes it in place of reading the object (Part 04 §5.3). It never takes a composite value, and it
reads any object the store reports nothing for. `owned.verified` and `external.verified` name each
digest's route: `computed`, `store`, or `combined`. The CRCs use `awscrt` and `google-crc32c`
where they are installed and a pure-Python implementation otherwise.

## What runs

Most of what runs is generated rather than written. The registry the packet embeds decides how
much, so the counts below are the current reference registry's and a packet carrying an older one
gets its own.

<!-- BEGIN facts: registry -->
45 tables, 360 columns, 116 references, 89 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: tier1 -->
175 not-null, 116 foreign-key, 4 closed-vocabulary, 26 finite-value and 16 discriminator checks, plus one uniqueness check per table whose sort does not begin with its primary key
<!-- END facts: tier1 -->

| | Comes from |
|---|---|
| required-column non-null | `presence: required` |
| foreign-key anti-join | `references`, with a null guard where a column is not required |
| primary-key uniqueness | `primary_key`, and only where a streaming scan does not already settle it |
| closed vocabulary | `enum` |
| finite value | `finite: true` |
| discriminator | `role: discriminator`, two checks each (R55 §2.4) |
| Tier 2 | statically checked `escapewheel-rule-sql-v0.2` queries the structure cannot imply, authored as `[[rules]]` in the registry's TOML source |

A generated check reading an `optional` column is skipped where a table omits that column, which
leaves it nothing to test (Part 02 §6).

## SQL and the shim

`R12 §4` draws the line: **SQL for what the data says, the shim for how it is stored.** A
relation has no row order, no file layout, no Parquet physical type and no Zarr chunk grid, so
a storage check written as SQL agrees with itself rather than failing. The shim covers physical
order (R10), column presence and physical type, manifest-internal consistency, and every
packet-owned array against its own Zarr metadata (R15 §4 level 2) — the last needing no Zarr,
because that metadata is JSON. It compares each array's pipeline and each Parquet footer's
compressions and encodings with the portable profile's reader floors (Part 03 §§5.5 and 6.4), and
reports a resource outside one as `physical.outside_reader_floor`: `warning` for a packet-owned
table, `info` for everything else, never an error. Parquet data-page types are not assessed, and the
report says so. An external resource whose metadata was not read is reported, one finding each, as
`external.physical_unassessed`. A packet-owned opaque payload's names, and the decoded segments of
its `uri`, draw `physical.opaque_name_portability` at `warning` for each set a filesystem folding
case or normalization would merge and each name Windows cannot hold (Part 05 §5.3); the packet
still conforms. It also parses every unit-column value as a UCUM code (Part 05 §5.3): a value
check, but one SQL could express only through a UCUM function the rule language does not have.

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

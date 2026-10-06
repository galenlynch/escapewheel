# Escapewheel Validator

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

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
each finding's `registry` names its subject, `null` for the packet. A finding's `resource` and
`column` name the resource and the one column it concerns, `null` where it concerns none or several,
and its `counts` gives by name what its message counted. Its `rows` holds the first five rows
found, where a count is of them all.

Rules are **data, not code**. `spec/artifacts/logical_schemas.json` carries every table's structure
and its Tier 2 rules, and the checks are generated from it rather than written per table. The
execution contract is the whole protocol: **a check's query returns offending rows — empty is
a pass, non-empty is a failure and the rows are the finding.**

```bash
escapewheel validate packet/              # exits non-zero unless the packet verdict is passed
escapewheel validate packet/ --advisory   # include rules that are off by default (R26)
escapewheel validate packet/ --replaced old/  # compare a replaces item with the packet it names
```

`--replaced` may be given once per packet the manifest's `replaces` names, as a packet root or a
manifest file. The validator pairs each with an item, confirms the item's `sha256` against every
manifest the packet publishes or retains, and reports a difference as `packet.replaces.mismatch` at
`warning`, since it cannot tell which side is wrong (Part 04 §3). Given no packet, it reports
nothing about the link.

```python
from escapewheel_reader import open_packet
from escapewheel_validator import validate

report = validate(open_packet("packet/"))
report.passed, report.errors, report.warnings  # passed: the packet verdict is `passed`
report.verdict(), report.verdict("core")       # "passed", "failed", or "incomplete"
report.registries  # complete, role-labelled registry-document results
```

A verdict is a `Verdict`, a finding's level a `Level`, an evaluation's status an `EvaluationStatus`,
and a registry result's state a `RegistryState`. Each is a string enumeration whose members equal
the strings the JSON report carries, so `report.verdict() == Verdict.PASSED` and
`report.verdict() == "passed"` are one test.

Every check ID the validator declares is an entry of `escapewheel_validator.check_table`, which
gives its default level, its scope (`packet`, `registry`, `resource` or `column`) and whether a
numbered part of the specification names it. A fixed ID is a constant named after it, and an ID
built from a resource or a column comes from its family's function, so
`finding.check == check_table.OWNED_DIGEST.id` and
`finding.check == check_table.physical_order("core.intervals").id` compare against the table instead
of a string. A Tier 2 rule's ID is the registry's and a registry result's outcome's is the registry
contract's, and neither is in the table.

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

From Python the modes are one `Verification`, which resolves external resources where a mode needs
them, as the flags do:

```python
from escapewheel_validator import Verification, validate

validate(packet, verification=Verification(checksums=True))                  # as --checksums
validate(packet, verification=Verification(checksums=True, external=False))  # packet-owned digests alone
```

## What runs

Most of what runs is generated rather than written. The registry the packet embeds decides how
much, so the counts below are the current reference registry's and a packet carrying an older one
gets its own.

<!-- BEGIN facts: registry -->
47 tables, 367 columns, 117 references, 92 Tier 2 rules (2 advisory)
<!-- END facts: registry -->
<!-- BEGIN facts: tier1 -->
188 not-null, 117 foreign-key, 4 closed-vocabulary, 26 finite-value, 17 name-uniqueness and 18 discriminator checks, plus one uniqueness check per table whose sort does not begin with its primary key
<!-- END facts: tier1 -->

| | Comes from |
|---|---|
| required-column non-null | `presence: required` |
| foreign-key anti-join | `references`, with a null guard where a column is not required |
| primary-key uniqueness | `primary_key`, and only where a streaming scan does not already settle it |
| closed vocabulary | `enum` |
| finite value | `finite: true` |
| name uniqueness | the `*_name` of each assigned identifier a table owns (Part 02 §8.2) |
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
because that metadata is JSON. It compares each Zarr v3 array's pipeline, each Zarr v2 array's
filters, compressor and byte order, and each Parquet footer's compressions and encodings with the
portable profile's reader floors (Part 03 §§5.5 and 6.3), and reports a resource outside one as
`physical.outside_reader_floor`: `warning` for a packet-owned table, `info` for everything else,
never an error. Parquet data-page types are not assessed, and the report says so. An external
resource whose metadata was not read is reported, one finding each, as
`external.physical_unassessed`. A packet-owned opaque payload's names, and the decoded segments of
its `uri`, draw `physical.opaque_name_portability` at `warning` for each set a filesystem folding
case or normalization would merge and each name Windows cannot hold (Part 05 §5.3); the packet
still conforms. It also parses every unit-column value as a UCUM code (Part 05 §5.3): a value
check, but one SQL could express only through a UCUM function the rule language does not have.

Tier 2 SQL is not DuckDB's full dialect. The validator parses each rule against the versioned
portable profile before execution, derives its base-resource dependencies from that parse, exposes
canonical schema-qualified relations, and reports unsupported, invalid, or incomplete evaluation
separately from packet findings. A rule runs as authored except where DuckDB's semantics differ
from Part 11's. `PERCENTILE_CONT`'s ordering value is cast to `DOUBLE PRECISION`, since DuckDB
otherwise interpolates a `DECIMAL` or `REAL` value in its own domain (Part 11 §5). A `DECIMAL`
value, a decimal literal, or an integer literal beyond `BIGINT` that converts to `REAL` or
`DOUBLE PRECISION` is converted through its text, since DuckDB's own conversion does not always
round to nearest, ties to even (Part 11 §4). DuckDB gives every operand of a `BETWEEN` one
common type, so a `BETWEEN` whose two comparisons would take different domains is written as the
two comparisons; and it gives an `IN` list's members and its left operand one common type, so an
exact member of a `REAL` list compared with a `DOUBLE PRECISION` operand is converted to `REAL`
first (Part 11 §4). Where the validator cannot place such a conversion
in a rule's text, it reports the rule's evaluation as incomplete and does not run it (Part 11 §8).
A `USING` join whose columns convert reaches it, as does a set operation whose exact result
converts where a `UNION` sits under a `UNION ALL` or a member selects `*`. A registry's author
learns of such a rule from `conformance/registries/check.py`, before any packet binds it.

The two halves cooperate: the ordering scan compares neighbours, so where a table's sort begins
with its primary key, duplicates must be adjacent and the same pass settles uniqueness. On 287
million spikes that replaced a `GROUP BY` which spilled 26 GB.

## Installation

Nothing is published to an index; install from a clone of the monorepo. `uv sync` in this
directory sets up the development environment:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-validator
uv sync
```

The root [README](../README.md#building-and-reading-a-packet) describes building and reading a
packet.

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
uv run --frozen --group docs sphinx-build -b html docs/source/ docs/build/html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
The packaged [third-party notices](src/escapewheel_validator/licenses/THIRD_PARTY_NOTICES.md)
cover the offline UCUM parser and its UCUM 2.2 data.

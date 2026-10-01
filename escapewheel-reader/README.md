# Escapewheel Reader

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Read Escapewheel packets: Parquet tables, Zarr v3 arrays, and the JSON manifest binding them.

A packet is a directory. This package opens one, resolves its resources by dotted ID rather
than by path, and hands back Arrow tables and Zarr arrays. It does not write packets and does
not validate them — that is [escapewheel-validator](../escapewheel-validator). It checks only what
reading needs (Part 04 §10): the manifest decodes, repeats no member or resource ID, and has the
members it reads at their JSON types; and a bound registry, acquired only when a declaration is
needed, matches its descriptor's digest.

A relative `uri` is percent-decoded and its names appended to the packet root, or to its source's
location, in any spelling RFC 3986 admits (Part 03 §4). One that is neither absolute nor a relative
reference leaves the packet open and that resource unreadable, the error naming its ID.

Reading is deliberately not a validation boundary. Opening a packet, resolving references and
discriminators, correlating sessions, and extension-aware analysis require neither a validation
receipt nor the validator package. These operations interpret declarations without claiming that
the registry or packet conforms; applications invoke validation separately when they need that
claim.

```python
from escapewheel_reader import open_packet

packet = open_packet("session_packet/")
packet.manifest.sessions  # external session names from packet.json
trials = packet.intervals(session_id=1, interval_kind="task.trials")  # a pyarrow.Table
spikes = packet.spike_times(unit_id=17)  # packet-assigned integer ID; pushed down, not scanned
good_spikes = packet.spike_times(units=packet.units(quality_label="sua"))

array = packet.array_resource("core.waveform_mean")
array.shape, array.dtype, array.chunks, array.codecs  # no Zarr needed for any of this
array.read((slice(0, 1),))  # this needs Zarr
```

## What it costs to install

The mandatory dependency closure is **jsonschema and pyarrow**, and that is the point rather
than an accident. A complete read path exists without a SQL engine, which is what keeps a
native reader viable in a language that has no embedded one — the reason Part 03 bans nested
Parquet types. Everything heavier is an extra:

| Extra | Brings | Needed for |
|---|---|---|
| `sql` | DuckDB | `Packet.sql()`, `Packet.duckdb()`, and all validation |
| `arrays` | Zarr | `ArrayResource.read()` only — shape, dtype, chunking and codecs are read from the store's own JSON |
| `polars` | Polars | `TableResource.scan_polars()` |

## Two handles

`Resource` records what the manifest *says*. `TableResource` and `ArrayResource` read it.
`Packet.table()` and `Packet.duckdb()` delegate to the first, `Packet.array_resource()` to the
second; neither touches the filesystem itself. Both split their dependencies the same way: a
table needs PyArrow to read and DuckDB only to query, an array needs nothing to describe and
Zarr only to read.

## Installation

Nothing is published to an index; install from a clone of the monorepo. `uv sync` in this
directory sets up the development environment:

```bash
git clone https://github.com/galenlynch/escapewheel.git
cd escapewheel/escapewheel-reader
uv sync
```

The root [README](../README.md#building-and-reading-a-packet) describes building and reading a
packet.

## Development

**Changing this package?** Read [CONTRIBUTING.md](CONTRIBUTING.md) first — it carries the two
rules that decide what belongs here and what shape it takes, and the process for a specification
defect found while implementing.

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
uv run --frozen pytest --cov escapewheel_reader # Tests with coverage
```

### Documentation

```bash
sphinx-build -b html docs/source/ docs/build/html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

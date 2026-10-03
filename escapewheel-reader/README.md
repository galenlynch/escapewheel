# Escapewheel Reader

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Read Escapewheel packets: Parquet tables, Zarr v3 arrays, and the JSON manifest binding them.

A packet is a directory or an object-store prefix. This package opens one, resolves its resources
by dotted ID rather than by path, and returns Arrow tables and Zarr arrays. Writing a packet is
`escapewheel-writer`'s job and validating one is [escapewheel-validator](../escapewheel-validator)'s.

## Reading a packet

`open_packet` opens one packet. Functions taking the packet as their first argument then read it:

```python
from escapewheel_reader import open_packet, spike_times, units

packet = open_packet("session_packet/")  # or "s3://bucket/prefix"
good = units(packet, quality_label="sua")
spikes = spike_times(packet, units=good)  # pyarrow.Table of unit_id, t_tick and clock_id
```

`Packet` itself only resolves, reads and registers, and has no method doing what one of those
functions does:

```python
packet.manifest.sessions  # the sessions the manifest declares
packet.table("core.events", stream_id=1)  # any table, constraints pushed into the Parquet reader
packet.sql("SELECT count(*) FROM core_units")  # DuckDB over the tables the query names
packet.array_resource("core.waveform_mean").shape  # no Zarr needed to describe an array
```

The functions fall into three layers, by what they take:

| layer | shape | examples |
|---|---|---|
| kernels | arrays → arrays | `align(ticks, anchor_t, anchor_p, *, bound)` |
| semantics | `(packet, table) → table` | `on_clock(packet, table)`, `seconds(packet, table)` |
| access | `(packet, ...) → table` | `spike_times(packet, ...)`, `unit_windows(packet)`, `aligned_spikes(packet, ...)` |

Every table is a `pyarrow.Table`, so an access function's result feeds a semantics function, and
either feeds Polars, pandas or DuckDB unchanged. These three lines are what
`spike_times(packet, units=good, seconds=True)` does in one:

```python
from escapewheel_reader import STORED, on_clock, seconds

stored = spike_times(packet, units=good, clock=STORED)  # ticks as recorded, each with its clock_id
aligned = on_clock(packet, stored)  # the same rows on the packet's reference clock
timed = seconds(packet, aligned)  # with t_second from the session's time origin
```

Any table resource, an extension's included, gets the same treatment from its declaration.
`attach_clocks(packet, resource_id, table)` adds the clock each coordinate column is counted on,
following `clock_from` through the reference the table declares. `on_clock` and `seconds` take the
same `resource_id` and then convert every coordinate. `Packet.table` does all three in one read:

```python
trials = packet.table("dynamic_foraging.trials", on_clock=True, seconds=True)
trials["go_cue_start_second"]  # one seconds column per *_tick coordinate, on the reference clock
```

Where a table has several coordinates, a tick the anchors cannot place becomes a null cell and the
row stays. Where it has one, as spikes and events do, the row is dropped. The
[design notes](docs/source/design.md#clocks) give the naming rule for the added clock columns.

The functions are free rather than methods because the table belongs to PyArrow and cannot carry
methods of ours. `rate_of(packet, table)` is the one that returns a number: the rows' rate over
the span they were observed for.

Each exists because doing it by hand from the schema gives a plausible wrong answer: ticks from two
clocks compared directly, a rate divided by the wrong span, or two sortings of one probe counted as
one. The [design notes](docs/source/design.md) explain each.

## Reading many packets

`open_dataset` opens several packets and presents each table as one relation over all of them.
An identifier is assigned within its packet, so every row of a session-scoped table carries a
`session_key` saying which session it came from:

```python
from escapewheel_reader import open_dataset

dataset = open_dataset(["packet_a/", "packet_b/"])
every_unit = dataset.table("core.units")  # rows of both, with session_key and session_name
dataset.duckdb(tables=["core.units"]).sql("SELECT session_key, count(*) FROM core_units GROUP BY 1")
```

## Reading checks only what reading needs

Opening a packet checks that the manifest decodes, repeats no member or resource ID, and has the
members the reader uses at their JSON types (Part 04 §10). A registry the packet binds is read
only when a declaration is needed, and refused unless it matches its descriptor's digest. A
resource whose `uri` is malformed stays unreadable while the rest of the packet opens, and the
error names its ID.

Nothing else is checked, so reading needs neither a validation receipt nor the validator. Run
`escapewheel-validator` where you need the claim that a packet conforms.

## Extras

Without extras the package reads every table and describes every array, so a packet is fully
readable with no SQL engine. Each extra adds a capability:

| extra | provides |
|---|---|
| `sql` | SQL over a packet or dataset (`Packet.sql`, `Packet.duckdb`, `Dataset.duckdb`), and spike-to-event alignment |
| `arrays` | an array's values; its shape, dtype, chunking and codecs need no extra |
| `polars` | a table as a lazy Polars frame (`TableResource.scan_polars`) |

## Resources and their handles

`Resource` records what the manifest says about one resource. `TableResource` and `ArrayResource`
read it: `Packet.table` and `Packet.duckdb` go through the first, and `Packet.array_resource`
returns the second.

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

Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing this package. It gives the two rules that
decide what belongs here and what shape it takes, and the process for a specification defect found
while implementing.

Run the full linting and testing suite:

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
uv run --frozen --group docs sphinx-build -b html docs/source/ docs/build/html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

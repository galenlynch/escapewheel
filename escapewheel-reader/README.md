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
packet.contents()  # every resource, with each table's columns and types
packet.contents(stored=False)  # the same from the registries, reading no table
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
`attach_clocks(packet, table, resource_id)` adds the clock each coordinate column is counted on,
following `clock_from` through the reference the table declares. `on_clock` and `seconds` take the
same `resource_id` and then convert every coordinate. `Packet.table` does all three in one read:

```python
trials = packet.table("dynamic_foraging.trials", on_clock=True, seconds=True)
trials["go_cue_start_second"]  # one seconds column per *_tick coordinate, on the reference clock
```

Where a table has several coordinates, a tick the anchors cannot place becomes a null cell and the
row stays. Where it has one, as spikes and events do, the row is dropped. The
[design notes](docs/source/design.md#clocks) give the naming rule for the added clock columns.

A tick reaches the reference by climbing its clock's parent chain, through each clock's anchors or
linear transform. A clock that is not on that chain is refused rather than reached some other way.
Where mapping is refused, or a synchronization looks wrong, read the ticks as stored:
`clock=STORED` on an accessor, or `on_clock` left unset on `Packet.table`. Each row keeps the
`clock_id` it was counted on, so ticks from different clocks are never mistaken for one another.

The functions are free rather than methods because the table belongs to PyArrow and cannot carry
methods of ours. `rate_of(packet, table)` is the one that returns a number: the rows' rate over
the span they were observed for.

Each exists because doing it by hand from the schema gives a plausible wrong answer: ticks from two
clocks compared directly, a rate divided by the wrong span, or two sortings of one probe counted as
one. The [design notes](docs/source/design.md) explain each.

## Reading many packets

`open_packets` opens several packets and presents each table as one relation over all of them.
An identifier is assigned within its packet, so every row of a session-scoped table carries a
`session_key` saying which session it came from:

```python
from escapewheel_reader import open_packets

packets = open_packets(["packet_a/", "packet_b/"])
every_unit = packets.table("core.units")  # rows of both, with session_key and session_name
packets.duckdb(tables=["core.units"]).sql("SELECT session_key, count(*) FROM core_units GROUP BY 1")
```

Each such row also carries the `packet_key` of the packet it was read from, which with its
`session_id` names the same session; `packets.session_table()` lists every pair with its
`session_key` and `session_name`.

## Reading lazily

The accessors return a `pyarrow.Table`. A read too large to hold, or one handed to another
library, stays lazy as a `pyarrow.dataset` Dataset or Scanner, which the same predicates narrow
and the same transforms convert:

```python
from escapewheel_reader import on_clock, seconds, tick_range, where

scanner = packet.scanner(
    "core.events",
    filter=where(stream_id=3) & tick_range(packet, "core.events", (lo, hi)),
)
timed = seconds(packet, on_clock(packet, scanner, resource_id="core.events"))  # a RecordBatchReader
```

`tick_range` matches exactly the rows whose coordinate lands in `(lo, hi)` on the reference clock,
or on the clock named, yet it tests the ticks as stored, so row-group statistics prune before
anything is mapped. `tick_bounds` gives the same intervals as a table, for a filter written in SQL
or Polars. `attach_clocks`, `on_clock` and `seconds` take a Table, RecordBatch, RecordBatchReader,
Scanner or Dataset, and return a stream for any of the last three. A stream maps batch by batch and
takes no further pushdown, so narrow it first. Rows already on the reference clock, as in
`analysis.spike_events`, can take seconds inside the scan through `seconds_expression(packet)`.

A packet set reads the same way. `PacketSet.scan` makes each packet's files fragments of one
dataset with `packet_key` as their partition field, so a filter on it opens no other packet's
files. `PacketSet.scanner` adds `session_key` and `session_name` to each row, and turns a
constraint on either into one on `packet_key` and `session_id`. `tick_range` and the transforms
take the packet set in place of a packet, and resolve each row's clocks in the packet its
`packet_key` names.

No accessor promises an order. `spike_times` on the reference clock reads `analysis.spike_events`,
stored by time, where `clock=STORED` reads `core.spike_events`, stored by unit. Sort or group the
result as the analysis needs.

A table is stored with each key's rows together, so `ragged` groups them without a sort. It returns
one row per key, with every other column a list of that key's values:

```python
from escapewheel_reader import ragged

columns = ["session_id", "unit_id", "t_tick"]
trains = ragged(packet, packet.table("core.spike_events", columns=columns), "core.spike_events")
trains["t_tick"]  # one list of ticks per unit, sharing the read's buffers
```

The key is the table's stored order without its last column. For `analysis.spike_events` that
gives one row per unit per time bucket. `ragged` checks that the keys ascend and raises `Unordered`
otherwise, so it gives no wrong result on rows sorted or concatenated another way. A scanner is
grouped batch by batch, and a run that crosses a batch boundary is joined back together. On
`core.spike_events`, 287 million spikes became 6,781 trains in 0.60 s after a 0.57 s read.

## Joining spikes to events in SQL

`analysis.spike_events` holds every spike already on the reference clock, so a query comparing
spikes with behavioural events starts there rather than mapping `core.spike_events` itself.
`aligned_spikes` and `assigned_spikes` answer the common questions. Written by hand, a window join
is fastest as a hash join on **bins as wide as the window**. A window then spans at most two
adjacent bins, so each event is entered under both, and the `BETWEEN` keeps the exact window.
Counting 287 million spikes within −1 s to +2 s of 708 go cues took 0.40 s and peaked at 314 MiB
this way. The ASOF join, which sorts every spike first, took 6.1 s and peaked at 21 GiB, and a plain
range join took 46 s. All three gave identical counts:

```python
packet.sql("""
    SELECT s.unit_id, count(*) AS spikes, sum(s.t_tick - t.go_cue_start_tick) AS ticks_from_cue
    FROM analysis_spike_events s
    JOIN (SELECT go_cue_start_tick, (go_cue_start_tick - 31250) // 93750 + k AS bin  -- 1 s before, 3 s wide
          FROM dynamic_foraging_trials, (VALUES (0), (1)) AS shift(k)) t
      ON s.t_tick // 93750 = t.bin
     AND s.t_tick BETWEEN t.go_cue_start_tick - 31250 AND t.go_cue_start_tick + 62500
    GROUP BY s.unit_id
""")
```

The bin join is exact whether or not windows overlap. An ASOF join is exact only where they do not:
it pairs a spike with the latest window to have opened, so a spike in two windows keeps only the
later one. `windows_disjoint(packet, event_type, half_window)` says which case holds.

`aligned_spikes` and `assigned_spikes` take `t_tick=(lo, hi)` to read only the spikes in a closed
range of ticks, with every event still eligible. Adjacent ranges are `(lo, next_lo - 1)`.
`assigned_spikes(to="preceding")` is an ASOF join and sorts the spikes it reads, so looping over
ranges bounds its memory.

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
| `sql` | SQL over a packet or packet set (`Packet.sql`, `Packet.duckdb`, `PacketSet.duckdb`), and spike-to-event alignment |
| `arrays` | an array's values, locally or from an object store, reached as its packet's tables are; its shape, dtype, chunking and codecs need no extra |
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

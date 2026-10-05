# Writing an extension and its adapter

This guide is for someone bringing their own experiment's data into Escapewheel packets. It covers
the two things they write: an **extension**, the registry declaring the tables their data needs
beyond core, and an **adapter**, the program reading their files and delivering rows to a build.
The specification owns every rule cited here; `escapewheel-dev` reads any cited section from a
checkout, as `escapewheel-dev section 9 5.7`.

The fastest start is the copier template, which generates a project holding both halves with tests
that build a real packet:

```bash
uvx copier copy --trust gh:galenlynch/escapewheel-copier-template my-task
```

The generated project's `CONTRIBUTING.md` covers its commands; this guide covers the decisions.
`examples/` in the escapewheel repository holds worked adapters for what the template's does not
use: event streams, a sampled signal on a clock of its own, a source on an object store, and the
routes a build reaches an adapter by.

## Where a fact belongs

Part 09 §2 places each fact by what a reader needs it for. A fact needed to interpret, join or
reproduce the data belongs in a core table: a session, a clock, an interval's bounds, an event's
tick. A fact specific to one task or lab belongs in an extension's table: a trial's outcome, a
reward volume, a block's reward probabilities. A fact stated about one row in the source's own
vocabulary, which no reader queries by name, goes in that row's `metadata` column.

So an extension extends core rather than replacing it. A trial is a `core.intervals` row carrying
its start and stop ticks, and the extension's `<namespace>.trials` row carries what the task knows
about it, joined on the interval's identifier. A reader that has never heard of the extension still
sees every trial on the session's timeline.

## The extension

An extension is a registry document in Part 02's format, namespaced by its `extension_id`
(Part 09 §5.1–5.2). Its source is a directory: `registry.toml` holds the document's own fields and
each `<resource_id>.toml` declares one table, in the same form as core's source
(`spec/source/README.md`). `escapewheel extension build <directory>` writes `<id>.json` beside each
source directory, and `escapewheel extension check <directory>` holds each document to the
registry contract under the core registry, to its source, and to the naming conventions.

Every column declares a name, a type, a presence and a role (Part 02 §3, §6, §8.1):

- **Presence** says whether a column must be there. A `nullable` column is preferred to an
  `optional` one, since a stable column set simplifies queries (Part 02 §6).
- **Role** says what the column is: `identifier`, `coordinate` for a tick, `discriminator`, or
  `data`. A role has no default, so a forgotten classification cannot pass for a decision.
- **Identity**, on an identifier, says whether the value is `carried` from the source unchanged or
  `assigned` by the writer, which numbers it packet-wide (Part 02 §8.2).

A table reachable from `core.sessions` leads with the required int32 assigned `session_id`
(Part 02 §7.1). A trial table specialises `core.intervals` by declaring its key as a reference
with `specialises = "core.intervals.interval_kind"` (Part 02 §8.3), which is what lets the build
check that every trial names an interval of its kind.

Declare the union of what the pipeline may emit, as `nullable` where a run may not compute it. An
adapter delivers the columns its run computed, and a column it leaves out then says this run did
not compute it rather than that the extension lacks it.

A packet embeds the registry document it was built against (Part 09 §5.3), so a reader needs
nothing installed, and a change to a declaration is a new `registry_version`. Never derive the
document from the rows a build delivers: a declaration read off one packet's data cannot disagree
with that data, so it declares nothing (Part 09 §5.7).

`escapewheel extension draft` reads an existing Parquet file's columns into a draft. The draft
fails the meta-schema until every role is chosen, which is deliberate.

## The adapter

An adapter is a Python class that opens one session's source and hands back rows, written against
`escapewheel_writer.adapter` and registered under the `escapewheel.sources` entry point by the kind
a recipe names it by:

```toml
[project.entry-points."escapewheel.sources"]
my_task = "my_task.source:MyTaskSource"
```

The class states its **declarations** as attributes, which a build reads before it opens anything
(Part 05 §3.4, Part 12 §7): `PRODUCES`, the tables it can supply; `CONTRIBUTES`, those it supplies
only in part beside other sources; `STATES`, the recipe fields it can state; `NEEDS` and
`ACCEPTS`, the terms and options it is constructed with; and `PROTOCOLS`, how a build may reach it.
Its constructor takes the source's root and each name it needs, and `records()` returns each table's
rows by resource ID. `examples/lick-wheel/` is a complete one, with a test building it into a
validated packet.

`escapewheel declare <kind> --out declaration.json` writes the declarations as the document Part
12 §7 specifies, for a build that does not install the adapter and so cannot read its class. Never
write that document by hand: it is generated, and one written separately can disagree with the
class.

What crosses has five rules, all in Part 12 §5:

- **Identifiers are names.** An adapter delivers the source's own names, such as `"s001"` for a
  session and `"s001/<namespace>.trials/3"` for a trial, and the build numbers them. A trial's name
  joins its session, kind and number, since a bare `3` would name a trial of every session.
- **Every wanted table arrives.** A table with no rows is left out of `records()`, and the build
  delivers it empty; one that does not arrive says the run failed.
- **An absent key means no value.** A key no row carries says the source has nothing for that
  column.
- **Types, order and sort are the build's.** It holds the registry and settles them on arrival.
- **Arrays do not cross as rows.** A dense array is a `StagedArray`, below.

A source the adapter cannot read raises `SourceDefect` with a code of the adapter's own, and the
build stops on it. What the adapter worked around and carried on past is a note instead, below.

### Times are ticks on a declared clock

Every time in a packet is an integer tick on a clock the packet declares (Part 01 §2.2). The recipe
declares the rig's clock with its exact rational rate, and an adapter naming `reference_clock` in
`NEEDS` receives that clock's `core.clocks` row. `Clock.ticks` converts seconds on it to ticks, and
refuses any time that is not on the clock's grid rather than rounding it, since a time off the grid
says the clock is the wrong one:

```python
harp = Clock(clock_id=row["clock_id"], session_id=session_id, name=row["clock_id"],
             tick_rate_num=row["tick_rate_num"], tick_rate_den=row.get("tick_rate_den") or 1,
             origin=row["origin"])
ticks = harp.ticks(seconds)
```

The adapter that knows the rig contributes the reference clock's row to `core.clocks`, and the span
it recorded over as a `core.clock_observation_intervals` row. Every clock a row is timed on needs an
observation window (Part 02 §12.5), and validation refuses a reference clock without one.

### Events belong to streams

An event is a `core.events` row: a tick, the stream it belongs to, and an optional JSON `payload`
carrying what the event states beyond its moment, such as a reward's volume. A stream is a
`core.event_streams` row naming the one kind of event it emits, the device emitting it and the
clock its ticks are on; a source logging licks and rewards on one channel is two streams.

Each stream also needs a `core.event_stream_observation_intervals` row for each span it was
watched over. Without one, a stretch with no licks cannot be told from a stretch nobody recorded,
and no rate over the stream has a denominator. A stream inherits its clock's window and may narrow
it, but never to a window derived from its own events (Part 01 §2.3).

### A sampled signal is an array

A signal sampled at a regular rate, such as a wheel's position, does not cross as rows. The adapter
returns it from `staged_arrays()` as a `StagedArray`, which the packet owns as a Zarr array
(Part 03 §6). Two rows describe it: a `core.array_assets` row naming its `resource_id`, device,
clock, rate and UCUM unit, and a `core.array_dimensions` row for each axis. A time axis is
regular on a clock: position k is at `origin_tick + k * step_tick_num` ticks.

An adapter delivered out of process states each axis's `dimension_names` on the `StagedArray`
itself. That process writes the array before any build reads the axes rows.

### A device's own clock is anchored to the rig's

A device sampling on its own oscillator keeps even spacing on that oscillator and not on the rig's,
since two oscillators drift parts per million apart. Its samples are therefore regular on a clock of
its own, declared with `parent_clock_id` naming the rig clock, and the drift goes in
`core.clock_anchors`: pairs of a tick on the device's clock and the rig tick it fell at, one every
second or so and the last sample always included. A reader interpolates between anchors to place a
sample on the rig's clock (Part 01 §3.9). An adapter never converts the device's times
itself, because doing so would bake one interpolation into the data.

### The root may be a store

A build hands an adapter its `root` as an absolute local path or a URI (Part 12 §4). Opening it
with `source_root(root, cache=source_cache)` gives a path that reads an object store as it reads a
disk, anonymously for a public bucket unless the recipe's `storage_options` say otherwise. Read
every file through that path, never through the working directory, and accept `source_cache` so a
store's objects are fetched once across builds (Part 12 §10).

### A run reports what no table shows

An adapter's `notes` say what it worked around and why a table is legitimately short: a session
recorded without a wheel delivers no wheel array, and a note says so. `STATES` maps each recipe
field the source states to the attribute holding it, such as `{"subject.subject_id":
"subject_id"}`. A build compares that value with the recipe's and refuses a recipe naming another
animal (Part 05 §3.6). Run out of process, `escapewheel deliver` writes both into the report the
recipe names at `[source.delivery].report_path` (Part 12 §9).

An adapter may validate its own tables before delivering them, but a build validates every staged
resource whatever produced it, so a test that builds a real packet checks more than any
self-validation can.

### A build reaches an adapter in process or over a protocol

A recipe entry with `in_process = true` constructs the adapter in the build's own process. That
needs the adapter installed beside the writer, which is a fact about one machine, so only the
recipe says it (Part 05 §3.9). Otherwise the entry carries a `[source.delivery]` table naming the
command a build runs:

```toml
[source.delivery]
command = ["escapewheel", "deliver", "my_task"]
report_path = "report.json"
```

`escapewheel deliver` constructs the registered class and serves its rows by whichever protocol
the build reached it over. `stream-v0.1` writes Arrow IPC streams to standard output, `files-v0.1`
writes one Parquet file per table into a directory, and `flight-v0.1` serves Arrow Flight on a
socket (Part 12 §3). Where the recipe names no protocol, the build uses the first the class lists in
`PROTOCOLS`. The command is an argument list, never a shell line (Part 05 §3.7), so `uv run`, a
pinned interpreter and a container are all commands, and an adapter isolates its dependencies
however it likes.

A program not written in Python can be an adapter too, by speaking a protocol itself: under
`files-v0.1` it reads one JSON object of terms from standard input to its end and writes
`<resource_id>.parquet` per table into the `delivery_root` those terms name. Its recipe names its
declaration document under `[source.delivery].declaration`.

### The command is a function of its inputs

A build may run an adapter again, and two runs over the same inputs must produce the same rows: no
wall-clock time, unfixed random seed or iteration over an unordered collection may reach a value it
writes (Part 09 §5.7). An adapter that cannot meet that delivers a file produced beforehand.

## The recipe

A recipe is one session's (Part 05 §3): the packet, the session and subject facts, the clocks, and
each source with the command reaching it. A lab with many sessions generates its recipes from each
session's own metadata, which the template's `<kind>-recipe` command does.

The recipe names the core registry by path; `escapewheel registry --out core.json` writes the one
the installed release carries. An installed extension is named by the ID its
`escapewheel.extensions` entry point registers, and an uninstalled one by the path of its document.
A column whose values defeat the default Parquet encoding names its own in the recipe's
`[encoding]`, with a reason (Part 05 §3.8).

```bash
escapewheel registry --out core.json
my-task-recipe /data/s001 > s001.toml
escapewheel import s001.toml --check   # everything wrong, before any I/O
escapewheel import s001.toml           # stage, validate, commit
escapewheel ls packet/                 # what the packet holds
```

## Using escapewheel-dev

`escapewheel-dev` reads the specification, registries and schemas from an escapewheel checkout,
and an extension of one's own when it is named:

```bash
uv run --project <checkout>/escapewheel-dev escapewheel-dev section 12 5           # a section
uv run --project <checkout>/escapewheel-dev escapewheel-dev requirements 12        # a part's rules
uv run --project <checkout>/escapewheel-dev escapewheel-dev schema adapter         # a schema
uv run --project <checkout>/escapewheel-dev escapewheel-dev table core.intervals   # a declaration
uv run --project <checkout>/escapewheel-dev escapewheel-dev \
  --extension src/my_task/extensions tables my_task                                # one's own tables
```

`--extension` takes a document or a directory of them and repeats; the environment variable
`ESCAPEWHEEL_DEV_EXTENSIONS` does the same. Its `README.md` documents the Python API.

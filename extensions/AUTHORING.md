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

An adapter is a command a build runs once per session over the `files-v0.1` protocol
(Part 12 §3). The build writes one JSON object of terms to its standard input and closes it; the
adapter reads to the end, then writes one `<resource_id>.parquet` per table into the
`delivery_root` the terms name, and exits non-zero with its reason on standard error when it
cannot. Its **declaration document** (Part 12 §7) states what it produces and needs, and a build
checks it against the registries and the recipe before opening anything.

What crosses has five rules, all in Part 12 §5:

- **Identifiers are names.** An adapter delivers the source's own names, such as `"s001"` for a
  session and `"s001/<namespace>.trials/3"` for a trial, and the build numbers them. A trial's name
  joins its session, kind and number, since a bare `3` would name a trial of every session.
- **Every wanted table arrives.** A table with no rows arrives empty; one that does not arrive
  says the run failed.
- **An absent column means no value.** A column no row carries says the source has nothing for it.
  Build each table from the union of its rows' keys: `pa.Table.from_pylist` takes its columns from
  the first row alone.
- **Types, order and sort are the build's.** It holds the registry and settles them on arrival.
- **Arrays do not cross as rows.** A dense array is written as Zarr under the `array_location` the
  build supplies.

### Times are ticks on a declared clock

Every time in a packet is an integer tick on a clock the packet declares (Part 01 §2.2). The recipe
declares the rig's clock with its exact rational rate, and an adapter naming `reference_clock` in
`needs` receives that clock's row. It converts each source time to a tick from the rational rate,
parsing the source's text rather than a float so the same text lands on the same tick on every
machine:

```python
rate = Fraction(clock["tick_rate_num"], clock["tick_rate_den"])
tick = round(Fraction(Decimal(seconds_text)) * rate)
```

The adapter that knows the rig contributes the clock's `core.clocks` row and the span it recorded
over as a `core.clock_observation_intervals` row, since every clock a row is timestamped on needs
an observation window (Part 02 §12.5) and validation refuses a reference clock without one. A rig with several clocks declares each, and an adapter aligning one to another
delivers `core.clock_anchors` rather than converting the times itself (Part 02 §12.6).

### The command is a function of its inputs

A build may run an adapter again, and two runs over the same inputs must produce the same rows: no
wall-clock time, unfixed random seed or iteration over an unordered collection may reach a value it
writes (Part 09 §5.7). An adapter that cannot meet that delivers a file produced beforehand.

The command is an argument list, never a shell line (Part 05 §3.7), and runs wherever the build
runs it, so it opens what the terms name rather than relying on its working directory. Because it is a
list, `uv run`, a pinned interpreter and a container are all commands, so an adapter isolates its
dependencies however it likes.

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

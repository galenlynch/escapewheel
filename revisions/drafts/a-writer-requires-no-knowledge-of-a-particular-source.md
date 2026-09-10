# A Writer Requires No Knowledge of a Particular Source

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `05` §3 (a recipe declares a preference between two sources); `05` §3.4 (what an adapter declares); `07` §4 (what a build supplies an adapter, and how a registered one reaches it) |
| **Depends on** | R63 §2.1 (an adapter declares `PRODUCES` before any I/O), R63 §2.2 (silence means the whole), R87 §2.2 (an adapter declares which recipe fields it states), R109 §3.1 (a writer requires no code of an extension), R110 §3.4 (a choice about one packet's values belongs in its recipe) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R63 §2.1 has a source adapter declare `PRODUCES` and R87 §2.2 has it declare `STATES`, both read
before any I/O. Everything else a build needs to know about an adapter is written down centrally
instead: which resource it wins when two sources offer one, whether it is handed an object store,
whether it may be sampled, and which recipe options it cannot be constructed without.

Measured across the writer, **72 occurrences name a particular source kind**, 51 of them in the
module that drives a build. This part moves each piece to where it can be stated by whoever knows
it, and says how an adapter nobody in this project wrote reaches a build.

## 2. Background

Informative.

### 2.1 Four tables name a kind, and each holds one adapter's own property

`_SHARED_SOURCES` names the three kinds handed an object store. `SAMPLED` names the one kind a
`--sample` build may read partially. `REQUIRED_OPTIONS` names the two kinds that cannot be
constructed without a `zone`. Each is a fact about one adapter, recorded where that adapter is not.

`PRODUCES` and `STATES` are the same kind of fact and are declared on the class, which is what lets
a build read them with nothing open (R63 §2.1). Nothing distinguishes the four tables from those two
except where they were written.

### 2.2 A registered adapter cannot be given what a built-in is given

An adapter may already come from another distribution: `escapewheel.sources` is an entry-point group
and a build consults it after its own ten kinds. What it does with one is call
`build(root, session_id=…, **options)` — and nothing else. A built-in kind is constructed by name,
so `video` receives the reference clock, `sync` receives first samples, and three kinds receive an
object store; a registered kind receives none of them, because the branches that supply them test
for a literal name.

So a registered adapter can produce a resource and cannot read from an object store, which is the
case R80 makes ordinary.

### 2.3 A preference is a claim about a pair, and two of them exist

`PREFERRED` gives a contested resource to the source that knows most about it: the NWB knows a
probe's type and manufacturer where the sorter knows only the stream. That is a claim about a pair
of adapters over one dataset, not a property either one has, so no adapter can declare it.

Measured over all ten kinds: **35 resources are produced, 8 are contested by two or more adapters,
and 2 need arbitrating** once the shared ones and the recipe-supplied ones are set aside —
`core.probes`, between `nwb` and `sorter`, and `core.subjects`, between `nwb` and `session`. A
recipe cannot declare either; the table is the only place a preference can be written.

R110 §3.4 settled the same shape for an encoding, which is a fact about one packet's values and so
belongs in the recipe rather than the schema. A preference is a fact about one packet's sources.

### 2.4 An adapter's closure is what rots, and authorship does not protect it

R109 §2.3 refuses an in-process extension because its dependency closure becomes the writer's, and
two extensions pinning incompatible versions make that environment unsolvable. An adapter for a
scientific format is where the heavy libraries are, so the argument reaches an adapter with more
force, not less.

The writer's own adapters look exempt and are not. Their closure today is `escapewheel-validator`,
`numpy`, `pyarrow`, `s3fs` and `universal-pathlib`, with `numcodecs` as the NWB adapter's only
extra — it decodes Zarr v2 chunks directly rather than through `pynwb`, `hdmf-zarr` or `zarr`, so
there is no `h5py`, no `PyAV` and no `spikeinterface` anywhere in it. That was built for rather than
inherited, and it is a measurement of one moment. Python resolves one environment per process, so
every adapter that runs in the writer resolves against every other; an adapter that needs one more
library next year makes that resolution harder whoever wrote it. **Nothing about being shipped with
the writer keeps a closure small.**

So the property that makes in-process safe is not authorship but the closure itself, which is
checkable: an adapter adding no requirement the writer does not already have cannot make the
environment harder to solve. The writer's ten qualify today by that test, and would stop qualifying
the day one of them needed `pynwb` — which is the rot, handled by a rule rather than by revisiting
a permission.

Volume is the one thing that argues for keeping an in-process route at all: of the ten kinds, **one
produces bulk** — `sorter`, at 674.2 MB for `core.spike_events` — and every other produces under
0.25 MB, `nwb` included at 0.2 MB across 18 resources. The adapter with the most resources moves the
least data, so the exception is narrow and it is about a table's size rather than about who wrote
the code that makes it.

### 2.5 The ten adapters are three groups, and only two are this format's

What an adapter reads says whose it is. `aind.py` reads `rig.json`, `session.json` and
`subject.json` — one institute's metadata schema. `sorter` reads `si_folder.json` and
`curation.json`, SpikeInterface's layout. `openephys` reads `settings.xml` and `sync` reads
`sample_numbers.npy` and `sync_messages.txt`, both Open Ephys artifacts, and `harp` reads
`device.yml`.

Two read neither an institute's files nor a tool's. `tables` reads whatever the recipe names, which
is R109 §3.2's route. `nwb` reads NWB, which is the format this specification exists to interoperate
with and whose importer is `07` §5's Phase 3; its AIND mentions are a dialect it accommodates —
`aind-data-schema`'s device string, `ccf_acronym` beside core NWB's `location` — rather than a
schema it depends on.

The dependency work is the evidence. The NWB adapter decodes Zarr v2 chunks with `numcodecs`
directly rather than importing `pynwb`, `hdmf-zarr` or `zarr`, which is effort nobody spends on an
adapter that could live in another distribution and pull what it likes. It was spent because that
adapter belongs to the writer.

## 3. Decision

### 3.1 An adapter declares what a build must supply it

An adapter **MUST** declare what a build supplies it beyond its root and the session identifier, as
a static declaration read with nothing open, in the shape `PRODUCES` and `STATES` already take. A
build **MUST** supply exactly what an adapter declares and **MUST NOT** decide it from the kind's
name.

A build **MUST** refuse a recipe naming an adapter that declares something the build cannot supply,
before any source is opened, which is where R63 §2.2 already refuses a recipe it cannot satisfy.

What may be declared is closed, because a build can only hand over what it holds: an object store
for the root, the session's reference clock, the first sample of each stream, and the recipe options
the adapter cannot be constructed without. A profile adding to that list amends this section.

### 3.2 A recipe declares a preference between two sources

A recipe **MAY** declare which source owns a resource that more than one of its sources produces, in
a table keyed by resource, each entry naming a source and the reason it knows more. A build
**MUST** apply a declared preference and **MUST NOT** hold a preference of its own for any resource
a recipe does not name.

Where two sources produce one resource and the recipe declares neither the preference nor an
explicit `owns`, a build **MUST** refuse the recipe naming both sources and the resource. That is
R63 §2.2's rule unchanged — a contradiction is refused before a byte is read — and it replaces a
built-in winner that no recipe could see.

### 3.3 An adapter delivers its rows out of process

Every adapter **MUST** be able to deliver its rows without being imported into the writer, and an
adapter author **SHOULD** support that route whatever else they support. A writer **MUST NOT**
require any adapter to be importable in its own environment, and **MUST** provide the route for
every adapter it ships.

The transport is not fixed to a file. A build **MUST** accept rows as **files the recipe names**,
which is R109 §3.2's route for an extension, and **SHOULD** accept them as an **Arrow IPC stream**
read from the command it ran. A writer **MAY** offer another transport and **MUST NOT** require one.

The stream matters where the file does not fit. A packet's largest table is `core.spike_events` at
674.2 MB, and an intermediate file for it is a write and a read the build did not otherwise need,
where a stream is the batches the staging path already consumes. Every other adapter produces under
0.25 MB (§2.4), so the file route costs them nothing and the stream is what keeps the boundary
usable for the one that matters.

### 3.4 A recipe opts a source into the writer's process

A build **MUST** deliver a source out of process unless the recipe declares that it runs in the
writer's, and a writer **MUST NOT** run one in process where the recipe does not say so.

**The recipe declares it because the recipe author chose the environment.** Python resolves one
environment per process, so whether a given set of adapters installs together is a fact about one
machine on one day rather than a property of any adapter — and the person assembling the recipe is
the only party who can find out, and the one who carries it when the answer changes. A writer
deciding for them would assert what it cannot know, and §2.4 measures how fast that goes stale: its
own closure is five packages today and nothing about shipping with the writer keeps it that way.

What the opt-in buys is efficiency, and what it costs is a solvable environment. A build that cannot
import an adapter the recipe opted in **MUST** refuse, naming the source and the import that failed,
before any source is opened.

### 3.5 An identifier crosses the boundary as a name

An adapter reaching a build through files hands over identifiers as the **names** its source used,
never as numbers, because a writer mints every assigned identifier packet-wide (R53 §2.5) and the
numbers do not exist until it has. That is R109 §3.2's rule for an extension and it binds an adapter
identically.

A writer **SHOULD** report what resolving those names cost where it exceeds what staging the table
directly would have, which is the measurement §6 leaves open.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This binds
  where a build learns about a source, so what changes is who may add one.
- **`PRODUCES` and `STATES` are untouched.** R63 §2.1 and R87 §2.2 stand; §3.1 says the rest of what
  an adapter needs is declared the same way, not that those two change shape.

## 5. Consequence

`05` §3 gains a preference table and an in-process declaration, `05` §3.4 gains what an adapter
declares, and `07` §4 gains what a build supplies an adapter and the transports it accepts rows
over.

The reference implementation loses four tables that name a kind — `_SHARED_SOURCES`, `SAMPLED`,
`REQUIRED_OPTIONS` and `PREFERRED` — and gains one declaration per adapter. It also gains a command
it does not have: `escapewheel` runs `inspect`, `init`, `extension`, `verify`, `prune` and `import`,
and none of them runs one adapter and hands over its rows, which is what §3.3 requires of the ten it
ships. That command is also the `command` a `tables` source names, so a built-in adapter reaches a
build through the same door an extension does (R109 §3.2) rather than through a second mechanism
built for it — and it is where the Arrow IPC transport lands, since a command already has a
standard output and the staging path already consumes batches.

Both packaged recipes gain two preference lines — `core.probes` to `nwb`, `core.subjects` to
`session` — which is what §2.3 measures the whole preference table to be, and an opt-in for whichever
sources their author finds installable together. Neither packet's rows change: the same source wins
each contest, declared where a reader of the recipe can see it.

The `Amends` line understates one thing deliberately. Nothing here forces the ten adapters apart, and
§2.5's grouping is why the option is worth having: an adapter reading one institute's metadata schema
or one tool's directory layout can move to that institute or that tool once it can reach a build
without being imported, which is what §3.3 establishes and what nothing before it did.

What §3.3 buys is that the ten adapters this project ships stop being a privileged class. A
registered adapter today produces resources and cannot reach an object store; after this every
adapter has the same two routes, and which one a build takes is the recipe's to say.

It also makes §2.5's grouping actionable rather than an observation. An adapter reading one
institute's metadata schema or one tool's directory layout can live with that institute or that
tool, reaching a build the way any other source does, and the writer keeps the two that are this
format's own: `tables`, which is the route itself, and `nwb`, which is the format this
specification interoperates with. Nothing here requires that split, and nothing after it blocks
one.

## 6. Open

- **Whether the stream removes the reason to opt in at all.** §3.3 offers it for the case a file
  does not fit and §3.4 leaves the choice to a recipe author, neither with a number. What it would
  take: stage `core.spike_events` three ways — in process, through a Parquet intermediate, and over
  an Arrow IPC stream — remembering that the out-of-process rows carry `local_unit_label` rather
  than the `unit_id` a writer assigns, and that R86 §2.3 puts a widened join key at 2.93x over
  286,896,563 spikes without measuring it as an intermediate. If the stream costs little, §3.4's
  opt-in is a convenience rather than a necessity, and saying so is worth more than permitting it.

- **Whether a build should report what an opt-in bought.** §3.3 makes running an adapter in process
  the recipe author's call, and gives them nothing to judge it by: a build knows what the file route
  would have written and what the in-process one did, so the difference is measurable and is not
  reported. Whether that belongs beside the encoding report (R110 §3.5) or nowhere is unsettled.

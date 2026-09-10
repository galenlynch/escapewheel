# A Writer Requires No Knowledge of a Particular Source

| | |
|---|---|
| **Status** | Draft |
| **Amends** | `05` §3 (a recipe declares a preference between two sources, and whether a source runs in process); `05` §3.4 (what an adapter declares); `07` §4 (what a build supplies an adapter, and the transports it accepts rows over); `05` §3.7 (what a build captures where a command's output carries rows); `09` §5.7 (an extension's rows cross the same boundary by the same transports, and a command is carried as a list) |
| **Depends on** | R63 §2.1 (an adapter declares `PRODUCES` before any I/O), R63 §2.2 (silence means the whole), R87 §2.2 (an adapter declares which recipe fields it states), R109 §3.1 (a writer requires no code of an extension), R110 §3.4 (a choice about one packet's values belongs in its recipe) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R63 §2.1 has a source adapter declare `PRODUCES` and R87 §2.2 has it declare `STATES`, both read
before any I/O. Everything else a build needs to know about an adapter is written down centrally
instead: which resource it wins when two sources offer one, whether it is handed an object store,
whether it may be sampled, and which recipe options it cannot be constructed without.

Measured across the writer package, **102 occurrences name a particular source kind**. Fifteen are
sound — `sources/__init__.py` maps the ten built-in kinds to their classes, which is core's registry
of its own adapters, and three modules name themselves — leaving **87 in the modules that decide
behaviour**, 51 of them in the one that drives a build. This part moves each piece to where it can be stated by whoever knows
it, and says how an adapter reaches a build without being imported — which is a process boundary
rather than a file, and so generalises what R109 §3.2 gave an extension.

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

One reads neither an institute's files nor a tool's: `tables` reads whatever the recipe names, which
is R109 §3.2's route.

`nwb` is the interesting case and it does not divide at the module. It reads NWB, the format this
specification exists to interoperate with and whose importer is `07` §5's Phase 3 — and **15 of the
columns it reads are ones base NWB does not define**: eight for a CCF position (`ccf_ap`, `ccf_ml`,
`ccf_dv`, `ccf_id`, `ccf_acronym`, `ccf_name`, `ccf_structure_id_path`, `brain_region_id`), five for
a dynamic-foraging trial (`go_cue`, `reward_outcome`, `reward_outcome_time`, `delay_start`,
`delay_start_time`), plus `ks_unit_id` and `channel_name`. A `DynamicTable` admits any column, so
reading those is reading one producer's dialect, not the standard.

So the boundary runs **inside** the 1,291-line module rather than around it: the machinery that opens
an NWB and walks its tables is this format's, and the knowledge of which extra columns a particular
exporter writes is not. The dependency work says the same thing about the first half — the adapter
decodes Zarr v2 chunks with `numcodecs` rather than importing `pynwb`, `hdmf-zarr` or `zarr`, which
is effort nobody spends on an adapter free to pull what it likes.

### 2.6 One adapter's kind and its module disagree about whose it is

The kind a recipe names is `session`, and the module behind it is `aind.py`, which reads
`rig.json`, `session.json` and `subject.json` — one institute's metadata schema. A recipe author sees
a generic word for a specific reader, and R85 §2.3 is the rule that makes that a defect rather than
untidiness: a name this specification does not constrain must not be doing load-bearing work, and
this one names what a build constructs.

The mismatch is why §2.5's grouping is hard to see from a recipe: `[[source]] kind = "session"` reads
as a session's metadata generally, where it means AIND's. Nothing in this part turns on the fix, and
recording it is what keeps a rename from being invented later as a new idea.

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

A writer **MUST NOT** require any adapter to be importable in its own environment, and **MUST**
provide a route by which every adapter it ships delivers its rows without being imported. An adapter
author **SHOULD** provide that route for an adapter the writer does not ship, whatever else they
provide.

The obligation is the writer's and the author's rather than the adapter's, which is R109's
allocation: R109 §3.1 binds a writer to build from a document and rows, and describes what an
extension delivers without requiring it of the extension. An adapter is a class and cannot run
itself out of process; whoever ships it can.

**What matters is the process boundary; the transport is a choice with a default.** A build **MUST**
accept rows as an **Arrow IPC stream** on the command's standard output, and **MUST** accept them as
**files the recipe names**. Absent a declaration the stream is what a build uses. A writer **MAY**
offer another transport and **MUST NOT** require one.

The stream is the default because it leaves nothing behind. A file is an artifact the build did not
ask for and does not own: it outlives the build, goes stale against the source it came from, and is
the shape three copies of one extraction already took in this project. A stream lasts as long as the
build and is the batches the staging path already consumes, so the largest table costs no write and
no read.

A recipe declares files where persistence is the point — an extraction expensive enough to reuse
across builds, or one whose output should still be there to inspect after a failure. That is not a
lesser route: it is the one R109 §3.2 requires of an extension, and both packaged sessions use it
today, re-reading a `tables/` directory across several rebuilds without running the extraction again.

Where the stream is used, standard output carries rows and cannot also carry a diagnosis. **`05`
§3.7 is amended to match**: a build **MUST** capture standard error and report it with a failure, and
**MUST NOT** report standard output where the recipe put rows on it. R109 §3.4's reason survives
intact, since the diagnosis a command prints was always the thing worth keeping and stderr is where
a command that also emits data must print it.

The same holds for an extension's rows, and R109 §3.2 is narrower than its own reason: it has an
extension deliver Parquet and names a subprocess for converting a raw source, where the argument it
rests on — a dependency closure that must not become the writer's — is answered by the boundary
rather than by the file. An extension **MAY** therefore deliver over any transport this section
allows an adapter. Nothing R109 permitted is withdrawn: a file the recipe names remains the route
every implementation must support, and the stream is added beside it.

The default settles the case that would otherwise need an exception. `core.spike_events` is 674.2 MB
and every other adapter produces under 0.25 MB (§2.4), so a file costs the small ones nothing and the
large one a write and a read; defaulting to the stream means no adapter needs permission to avoid
that, and a recipe that wants the file says so.

### 3.4 A command is an argument list, and a stream is bytes

`09` §5.7 says a command is an argument list run in the source's own root and not a shell line. A
recipe **MUST** carry it as a list, and a build **MUST NOT** derive one by splitting a string.

A build given a string must parse it, and a parse is a quoting convention the recipe never declared.
`shlex.split` applies POSIX rules on every host and tests nothing about which one, so it eats a
backslash everywhere: `C:\Python\python.exe` becomes `C:Pythonpython.exe`. The parse is
unconditional and the failure is not — harmless where paths use forward slashes, fatal where they do
not — so the defect is the string and not the host.

A list needs no convention, because `subprocess` already has one per host: `list2cmdline` on Windows,
`execv` elsewhere. A list keeps that adaptation where it is already written.

Where rows travel on standard output, they are **bytes**. An adapter **MUST** write the stream to a
binary handle, and a build **MUST** read one. A platform translating a line ending in text mode
corrupts the stream, and it fails as malformed data rather than as an encoding error.

A build **MUST** consume standard output and standard error concurrently. A pipe holds tens of
kilobytes, so reading one to completion first deadlocks on any adapter whose diagnosis outruns that
buffer. How a build does it is `07` §7's, being a technique that changes with the implementation
(R93 §3.5).

### 3.5 A recipe opts a source into the writer's process

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

### 3.6 An adapter returns records, and a transport is not the return type

`07` §4 states that an adapter's return type is records and not a path, because that is what lets an
adapter be tested without a filesystem and keeps normalization decisions out of I/O code. That
sentence **stands and is not enough**, because it answers what an adapter returns and this part asks
how rows reach a build.

An adapter's interface **MUST** remain records whichever route delivers them. Out of process, the
transport carries them and the receiving end returns records again — which is not a hope: a `tables`
source reads files and yields batches today, so the interface is re-established on this side of the
boundary by machinery that already exists.

What the out-of-process route gives up is the property `07` §4 names. Testing an adapter that
delivers over a transport means running it, so the filesystem or the pipe is back, and an in-process
adapter is the only one testable without either. **That is the trade** — a solvable environment
against a test that needs no I/O — and §3.5 puts it where the person who bears it can make it, rather
than settling it here for every recipe.

### 3.7 An identifier crosses the boundary as a name

An adapter reaching a build through files hands over identifiers as the **names** its source used,
never as numbers, because a writer mints every assigned identifier packet-wide (R53 §2.5) and the
numbers do not exist until it has. That is R109 §3.2's rule for an extension and it binds an adapter
identically.

A writer **SHOULD** report what resolving those names cost, as a figure of its own rather than as a
comparison: a build that received rows out of process never staged them the other way and has no
baseline to subtract. What the two routes cost against each other is §6's measurement, not a report
a build can make.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This binds
  where a build learns about a source, so what changes is who may add one.
- **`PRODUCES` and `STATES` are untouched.** R63 §2.1 and R87 §2.2 stand; §3.1 says the rest of what
  an adapter needs is declared the same way, not that those two change shape.

## 5. Consequence

`05` §3 gains a preference table and an in-process declaration, `05` §3.4 gains what an adapter
declares, `05` §3.7 gains what a build captures where rows are on standard output, `07` §4 gains what a build supplies an adapter and the transports it accepts rows
over, `09` §5.7 gains that an extension may use them too, and `07` §4's sentence about a return type gains
what it does not cover.

The reference implementation carries the defect §3.4 forbids: `TablesSource` takes `command` as a
string and splits it with `shlex`, which the module's own docstring calls "a plain argument list …
**not** a shell". Both packaged recipes say `command = "python extract.py"`, which survives the parse
because it contains no backslash. One naming an interpreter by an absolute Windows path would not,
and would fail as a missing executable rather than as a malformed command. The fix is a TOML array
and the deletion of the split.

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
  286,896,563 spikes without measuring it as an intermediate. If the stream costs little, §3.5's
  opt-in is a convenience rather than a necessity, and saying so is worth more than permitting it.

- **Whether a build should report what an opt-in bought.** §3.3 makes running an adapter in process
  the recipe author's call, and gives them nothing to judge it by: a build knows what the file route
  would have written and what the in-process one did, so the difference is measurable and is not
  reported. Whether that belongs beside the encoding report (R110 §3.5) or nowhere is unsettled.

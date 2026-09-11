# An Adapter's Rows Cross a Process Boundary

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 05 §3 (a recipe declares whether a source runs in the writer's process); Part 05 §3.7 (what a build captures where a command's output carries rows); Part 07 §4 (an adapter's return type, the transports a build accepts rows over, and how an array crosses); Part 09 §5.7 (an extension's rows cross the same boundary by the same transports, and a command is carried as a list) |
| **Depends on** | R109 §2.3 (a shared process is a shared dependency closure), R109 §3.1 (a writer requires no code of an extension), R109 §3.2 (an extension delivers a registry document and rows as files), R109 §3.4 (a build keeps what a command wrote to its streams), R53 §2.5 (a writer mints every assigned identifier), R93 §3.5 (a number that would change with the implementation belongs to Part 07 §7) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

R109 §2.3 refuses an in-process extension because its dependency closure becomes the writer's, and
two extensions pinning incompatible versions make that environment unsolvable. R109 §3.2 answers it
with files and a subprocess, for an extension.

A source adapter is where the heavy libraries of a scientific format live, so the argument reaches
one with more force and nothing states it. This part says how an adapter's rows reach a build without
the adapter being imported, which transport carries them, and who decides — and states the rule once,
because R109 §3.2 named files where its own reason was the boundary.

What a build learns *about* an adapter is
`a-writer-requires-no-knowledge-of-a-particular-source`'s, and neither part depends on the other.

## 2. Background

Informative.

### 2.1 An adapter's closure is what rots, and authorship does not protect it

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

### 2.2 What an adapter reads says whose it is, and one boundary runs inside a module

What an adapter reads says whose it is. `aind.py` reads `rig.json`, `session.json` and
`subject.json` — one institute's metadata schema. `sorter` reads `si_folder.json` and
`curation.json`, SpikeInterface's layout. `openephys` reads `settings.xml` and `sync` reads
`sample_numbers.npy` and `sync_messages.txt`, both Open Ephys artifacts, and `harp` reads
`device.yml`.

One reads neither an institute's files nor a tool's: `tables` reads whatever the recipe names, which
is R109 §3.2's route.

`nwb` is the interesting case and it does not divide at the module. It reads NWB, the format this
specification exists to interoperate with and whose importer is Part 07 §5's Phase 3 — and **15 of the
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

### 2.3 One adapter's kind and its module disagree about whose it is

The kind a recipe names is `session`, and the module behind it is `aind.py`, which reads
`rig.json`, `session.json` and `subject.json` — one institute's metadata schema. A recipe author sees
a generic word for a specific reader, and R85 §2.3 is the rule that makes that a defect rather than
untidiness: a name this specification does not constrain must not be doing load-bearing work, and
this one names what a build constructs.

The mismatch is why §2.2's grouping is hard to see from a recipe: `[[source]] kind = "session"` reads
as a session's metadata generally, where it means AIND's. Nothing in this part turns on the fix, and
recording it is what keeps a rename from being invented later as a new idea.

## 3. Decision

### 3.1 An adapter delivers its rows out of process

A writer **MUST NOT** require any adapter to be importable in its own environment, and **MUST**
provide a route by which every adapter it ships delivers its rows without being imported. An adapter
author **SHOULD** provide that route for an adapter the writer does not ship, whatever else they
provide.

The obligation is the writer's and the author's rather than the adapter's, which is R109's
allocation: R109 §3.1 binds a writer to build from a document and rows, and describes what an
extension delivers without requiring it of the extension. An adapter is a class and cannot run
itself out of process; whoever ships it can.

**What matters is the process boundary; a transport is a protocol, and protocols come in groups.** A
profile names a group for each way an adapter reaches a build, and the protocols in it. An adapter
**MUST** declare and support **at least one** protocol in a group; a build **MUST** support **every**
protocol in every group its profile names.

**A protocol carries its version in its name**, semantically versioned and starting at `v0.1`, which
is the form every other identifier this specification hands out takes —
`escapewheel-portable-v0.1`, `escapewheel-logical-v0.1`. A profile **MUST NOT** change what a named
protocol means; a protocol that changes how rows cross is a **new member of the group**, not a new
reading of an old one.

`escapewheel-portable-v0.1` names one group, **out of process**, holding two:

| protocol | rows cross as |
|---|---|
| `files-v0.1` | Parquet the recipe names, one per resource |
| `stream-v0.1` | a sequence of Arrow IPC streams on standard output, each schema naming its resource |
| `flight-v0.1` | Arrow Flight over a Unix socket the build names, one descriptor per resource |

**A build supports the members a profile names, and MUST NOT infer one version from another.**
Semantic versioning says what a change was, which is what an author needs to decide a number; it
does not say what a build can read, which is decided by the group. Reading `stream-v0.2` is not
being able to read `stream-v0.1`, and a build that assumed otherwise would be guessing at a framing
rather than declaring it.

**The asymmetry is the point.** There is one build and there will be many adapters, so the build
carries breadth once and an adapter author implements whichever protocol suits the source in hand —
`files` where an extraction is worth keeping, `stream` where it should leave nothing behind — and
never both. Neither is a floor the other is measured against, and no negotiation can fail, because
a build already supports everything a conforming adapter may choose. A build meeting an adapter
that declares no protocol of the group **MUST** refuse it, naming the group: that adapter does not
conform, and refusing before any source is opened is where R63 §2.2 puts a recipe a build cannot
satisfy.

It is also how the contract grows. Adding a protocol to a group costs every build work and costs no
adapter anything, since one declaring what it declared before still declares something a build
supports; a revised protocol is added the same way, as `stream-v0.2` beside `stream-v0.1`. Adding a
**group** — an in-process protocol, or one reaching an adapter the build did not launch — leaves
every existing adapter and build alone.

Retiring a protocol is the one change that costs an adapter author anything, and it is a **profile**
change: the group is the profile's, so dropping `stream-v0.1` from `escapewheel-portable-v0.1` is not
something a build decides. An adapter declaring a protocol no group of the profile names is refused
as one declaring none.

`stream` earns its place by leaving nothing behind, and by never touching a disk: a pipe is memory,
so the largest table costs no write and no read. A file is an artifact the build did not ask for and
does not own — it outlives the build, goes stale against the source it came from, and is the shape
three copies of one extraction already took in this project — which is also why a recipe may want
one, and why neither protocol is the other's replacement.

**An Arrow IPC stream carries one schema, and an adapter returns many resources.** They concatenate:
a stream ends with the format's own end-of-stream marker — the continuation `0xFFFFFFFF` followed by
a zero length — so a reader opens one, reads to it, and opens the next on what is left. The resource
identifier rides in the schema's key-value metadata, which is a field the format defines.
`conformance/adapter-boundary/` sends three resources with three schemas over a real pipe and reads
all three back, which is the measurement this clause rests on.

**What each protocol invents, and nothing more.** `files-v0.1` invents a mapping from resource to
path, which a recipe already carries for a `tables` source. `stream-v0.1` invents **one metadata
key**, `resource_id`. Everything else is Arrow: the container, the schema, the batching, the
terminator that separates one resource from the next, and the metadata field the key lives in. A
protocol that owned more would be a format to maintain; these are a spelling of two.

**`flight-v0.1` gives, for free, two things the others need protocol to get.** Part 05 §4.1 has a
build report per source what it offers per resource and how many rows, without writing to the
packet, and Part 05 §3.3 lets a recipe narrow a source to some of what it produces. Flight answers
both from its own vocabulary: `ListFlights` returns a descriptor per resource with its schema and
row count before any data moves, and `DoGet` fetches one descriptor, so a build asks for what the
recipe named and no more.

Neither is out of reach of the others; each costs surface we would have to own. `files-v0.1` answers
discovery from a Parquet footer and selection by which files the recipe names, so it needs nothing.
`stream-v0.1` would need a way to be asked — an invocation that reports rather than emits, and a way
to say which resources are wanted — and both are ours to specify, name and version. **That is the
trade: own more protocol, or need gRPC bindings.**

**Which to reach for follows from that.** Where an extraction is worth keeping, `files-v0.1` is
both the cheapest to write and the one that already answers everything: a footer holds the row
count and the recipe's paths are the selection, which is why `TablesSource.offers` reads
`num_rows` from metadata and never opens the data. Where nothing should be left behind and the
source is small enough that extracting to discover costs little, `stream-v0.1` is a hundred lines.
Where it is not — a source whose extraction is expensive, or one a recipe narrows — `flight-v0.1`
is what asks before fetching.

The line is worth naming: **the moment a stream needs to be asked, it is becoming Flight.** A
reporting invocation, a way to name what is wanted, a schema for the answer — each is a thing Flight
already has a name for, and re-spelling them under our own names is how a protocol that owned one
metadata key grows into a format to maintain.

Flight also owns the least of the three. A descriptor is the format's, so the `resource_id` key is
unnecessary, and what a build supplies is the **socket path**, which it already passes in an
argument list. Measured in `conformance/adapter-boundary/`, a server over a **Unix socket** — no
port, no network exposure, shipped in the standard pyarrow wheel — serves three resources by
descriptor in **119 ms including the process start**.

`stream-v0.1` is not the lesser protocol for it. It is the one implementable wherever there is an
Arrow binding at all, which is R3 §2.1's argument from the beginning: Flight needs gRPC bindings for
that language too, and the Arrow implementations carrying Flight are a subset of those carrying IPC.
An adapter that emits everything it has and lets the build discard is paying a cost R63 §1.2
measures at one resource in five, and an adapter whose discovery costs an extraction is paying what
the NWB adapter's `offers` pays in process today, counting rows by computing them. Both are costs a
working adapter can carry.

A recipe declares files where persistence is the point — an extraction expensive enough to reuse
across builds, or one whose output should still be there to inspect after a failure. That is not a
lesser route: it is the one R109 §3.2 requires of an extension, and both packaged sessions use it
today, re-reading a `tables/` directory across several rebuilds without running the extraction again.

Where the stream is used, standard output carries rows and cannot also carry a diagnosis. **Part 05
§3.5 is amended to match**: a build **MUST** capture standard error and report it with a failure, and
**MUST NOT** report standard output where the recipe put rows on it. R109 §3.2's reason survives
intact, since the diagnosis a command prints was always the thing worth keeping and stderr is where
a command that also emits data must print it.

**An adapter MAY report the way an extension does.** Part 09 §5.8 already has an extension write a
JSON report at a path the recipe names, carrying a `problems` array whose entries each have a
`level` of `error`, `warning` or `info`, a message, and optionally the resource the finding is
about. An adapter **MAY** write the same report on the same terms, and a build treats it the same
way: reporting what it contains, requiring none, failing on none it cannot parse, and ignoring what
it can derive for itself.

Standard error stays what a failure carries. What the report adds is a finding a build can file
beside its own — Part 05 §9's levels are the ones §5.8 already uses — where a diagnosis on stderr
is a string a build can only repeat. An adapter and an extension reach a build by the same
protocols, and having them describe a problem two different ways is a difference with no argument
behind it.

The same holds for an extension's rows, and R109 §3.2 is narrower than its own reason: it has an
extension deliver Parquet and names a subprocess for converting a raw source, where the argument it
rests on — a dependency closure that must not become the writer's — is answered by the boundary
rather than by the file. An extension **MAY** therefore deliver over any transport this section
allows an adapter. Nothing R109 permitted is withdrawn: a file the recipe names remains the route
every implementation must support, and the stream is added beside it.

The default settles the case that would otherwise need an exception. `core.spike_events` is 674.2 MB
and every other adapter produces under 0.25 MB (§2.1), so a file costs the small ones nothing and the
large one a write and a read; defaulting to the stream means no adapter needs permission to avoid
that, and a recipe that wants the file says so.

### 3.2 A command is an argument list, and a stream is bytes

Part 09 §5.7 says a command is an argument list run in the source's own root and not a shell line. A
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
buffer. How a build does it is Part 07 §7's, being a technique that changes with the implementation
(R93 §3.3).

### 3.3 A recipe opts a source into the writer's process

A build **MUST** deliver a source out of process unless the recipe declares that it runs in the
writer's, and a writer **MUST NOT** run one in process where the recipe does not say so.

**The recipe declares it because the recipe author chose the environment.** Python resolves one
environment per process, so whether a given set of adapters installs together is a fact about one
machine on one day rather than a property of any adapter — and the person assembling the recipe is
the only party who can find out, and the one who carries it when the answer changes. A writer
deciding for them would assert what it cannot know, and §2.1 measures how fast that goes stale: its
own closure is five packages today and nothing about shipping with the writer keeps it that way.

What the opt-in buys is efficiency, and what it costs is a solvable environment. A build that cannot
import an adapter the recipe opted in **MUST** refuse, naming the source and the import that failed,
before any source is opened.

### 3.4 An adapter returns records, and a transport is not the return type

Part 07 §4 states that an adapter's return type is records and not a path, because that is what lets an
adapter be tested without a filesystem and keeps normalization decisions out of I/O code. That
sentence **stands and is not enough**, because it answers what an adapter returns and this part asks
how rows reach a build.

An adapter's interface **MUST** remain records whichever route delivers them. Out of process, the
transport carries them and the receiving end returns records again — which is not a hope: a `tables`
source reads files and yields batches today, so the interface is re-established on this side of the
boundary by machinery that already exists.

What the out-of-process route gives up is the property Part 07 §4 names. Testing an adapter that
delivers over a transport means running it, so the filesystem or the pipe is back, and an in-process
adapter is the only one testable without either. **That is the trade** — a solvable environment
against a test that needs no I/O — and §3.3 puts it where the person who bears it can make it, rather
than settling it here for every recipe.

### 3.5 An identifier crosses the boundary as a name

An adapter reaching a build through files hands over identifiers as the **names** its source used,
never as numbers, because a writer mints every assigned identifier packet-wide (R53 §2.2) and the
numbers do not exist until it has. That is R109 §3.2's rule for an extension and it binds an adapter
identically.

A writer **SHOULD** report what resolving those names cost, as a figure of its own rather than as a
comparison: a build that received rows out of process never staged them the other way and has no
baseline to subtract. What the two routes cost against each other is §6's measurement, not a report
a build can make.

### 3.6 A dense array crosses as a reference

An adapter's rows cross as records and its arrays **MUST NOT**. A dense array crosses as a
**reference**: the array_asset_id, the layout an adapter chose for it — chunking, sharding, codecs,
fill value — and a location.

**The build names the location, and it is in staging.** Where the packet will own the array, a build
**MUST** supply a location under the staging area Part 05 §1 already requires, and an adapter
**MUST** write the array there and return the reference rather than the measurement, whether it is
an adapter the writer ships, one it does not, or an extension. Writing it
anywhere else costs a copy: staging is where the array has to be before it is validated, and commit
moves it to its final path by the rename Part 05 §6 already performs. Told where, an adapter writes
the array once and nothing moves it again but that rename.

Measured on the waveform adapter, this is what the crossing already almost is.
`conformance/adapter-boundary/` reports `StagedArray`'s six fields — `values`, `array_asset_id`,
`chunks`, `shard`, `codecs` and `fill_value` — and **five of the six cross**; the sixth is the
array. Returning the five beside a location is the whole of the change.

**An array is not rows and no transport makes it rows.** §3.1 has an adapter deliver records as an
Arrow IPC stream, and a stream that carried a dense array would carry it whole, through the build's
memory, into a file the build then writes — the copy the staging path exists to avoid. The
`lfp` adapter is the one of three array-reading adapters that never takes this route: its
`external_arrays` returns references today, which is R14 §2.3.1's external resource, and the shape
this section gives every adapter.

Where the array is external — bytes the packet references rather than owns (Part 03 §6.1) — a
build supplies no location and the producer returns the URI its source already has.

**This binds whoever produces an array, which includes an extension.** An extension declares tables
and no arrays, because core already models any dense array generically: `core.array_assets` holds a
sampled quantity of any kind and the device it names says what kind (R65 §2.1), and
`core.array_dimensions` carries its axes. So an extension needing one does not describe a new sort
of array — it fills in core's, supplying those rows like any other source, and this section is what
lets the bytes travel with them. Without it an extension could declare an array asset and have no
way to deliver what it asserts.

### 3.7 A writer ships each protocol so an adapter need not write one

A writer **SHOULD** ship an implementation of each protocol its profile names, covering both ends,
and **whoever speaks one MAY use it** rather than write their own — an adapter, and an extension
delivering its rows over the same protocols (§3.1). Nobody should hand-roll a framing that is
already specified and already implemented, and the side that does is where the two ends drift apart
first.

Using it **MUST NOT** be a condition of conformance. §3.1 specifies each protocol so either can
speak one with nothing of the writer's installed, in any language, which is what R109 §3.1 asks and
what a shipped implementation would otherwise quietly undo — the point is to spare an author the
work, not to decide what they may build against. An extension is the case that makes this sharp:
R109 §3.1 requires no code of one at all, so an implementation it *must* import would contradict
the clause this part rests on.

**An adapter out of process may import whatever version it was written against.** §2.1's coupling is
a *shared* environment, and the boundary is what unshares it: an adapter depending on the writer at
one version, in its own closure, resolves against nothing the build resolves. So importing the
writer to speak a protocol is a cost rather than a coupling, and the cost is measurable — the
writer's environment resolves **57 distributions**, duckdb through the validator, s3fs and botocore
for an object store, zarr and numcodecs for arrays, where `pyarrow`, which both protocols need and
neither exceeds, **requires nothing**.

Where that implementation is published is not this part's business. It may ship inside the writer
and be split out later if its closure starts to matter to authors; what this part requires is that
it exist and that using it be optional.

**A protocol's name is importable with it.** An adapter declares a protocol by naming it, and the
name is a constant the implementation exports rather than a string the adapter spells. Pinning is
then what keeps an old adapter working, and it needs no shim to maintain: the adapter resolves the
version it was written against in its own environment, and that version exports `stream-v0.1` and
speaks it. A profile **MUST NOT** change what a named protocol means (§3.1), so the build at a
later version still names `stream-v0.1` in its group and still reads it.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This binds
  how rows reach a build, so what changes is what an adapter must be able to do and who chooses.
- **Nothing R109 permitted is withdrawn.** A file the recipe names remains a route every
  implementation supports; §3.1 adds the stream beside it and makes it the default, and §3.3 leaves
  the in-process route available where a recipe asks for it.

## 5. Consequence

Part 05 §3 gains an in-process declaration, Part 05 §3.7 gains what a build captures where rows are
on standard output, Part 03 §1 gains the protocol group the portable profile names, Part 07 §4
gains that an adapter declares a protocol and that an array crosses as a reference, and Part 09
§5.7 gains that an extension may use any protocol of the group and that a command is carried as a
list.

**What the reference implementation owes is both protocols, once, and a fourth distribution.** A
build supports every protocol in the group, so it reads Parquet the recipe names — which
`tables.py` does today, as `{resource: path}` with a batch iterator each — and reads a sequence of
Arrow IPC streams, which is new. Each of the ten adapters it ships then declares one.

§3.7's implementation is the rest: both ends of both protocols, and the names as constants an
adapter imports rather than spells. It can live in the writer to begin with. Splitting it into its
own distribution is a later question and a measurable one — the writer's environment resolves 57
distributions where `pyarrow`, which both protocols need and neither exceeds, requires nothing — but
an adapter out of process resolves its own environment, so that is a convenience for authors rather
than anything conformance turns on.

The array is the smaller half of the implementation. `StagedArray` already carries the four layout
fields and the identifier; what changes is that the adapter writes the values and returns the
location, where today it hands the values over and the writer writes them. `LFPSource` needs
nothing: `external_arrays` is already the shape, and `add_array` keeps its signature for an
in-process adapter that has not been converted.

The reference implementation owes a command it does not have: `escapewheel` runs `inspect`, `init`,
`extension`, `verify`, `prune` and `import`, and none of them runs one adapter and hands over its
rows, which is what §3.1 requires of the ten it ships. That command is also the `command` a `tables`
source names, so a built-in adapter reaches a build through the same door an extension does
(R109 §3.2) rather than through a second mechanism built for it — and it is where the Arrow IPC
transport lands, since a command already has a standard output and the staging path already consumes
batches.

It also carries the defect §3.2 forbids: `TablesSource` takes `command` as a string and splits it with
`shlex`, which the module's own docstring calls "a plain argument list … **not** a shell". Both
packaged recipes say `command = "python extract.py"`, which survives the parse because it contains no
backslash. One naming an interpreter by an absolute Windows path would not, and would fail as a
missing executable rather than as a malformed command. The fix is a TOML array and the deletion of
the split.

Both packaged recipes gain an opt-in for whichever sources their author finds installable together,
and nothing else: neither packet's rows change.

Nothing here forces the ten adapters apart, and §2.2's grouping is why the option is worth having.
An adapter reading one institute's metadata schema or one tool's directory layout can move to that
institute or that tool once it can reach a build without being imported, which is what §3.1
establishes and what nothing before it did.

## 6. Open

- **Whether the stream removes the reason to opt in at all.** §3.1 offers it for the case a file does
  not fit and §3.3 leaves the choice to a recipe author, neither with a number. What it would take:
  stage `core.spike_events` three ways — in process, through a Parquet intermediate, and over an
  Arrow IPC stream — remembering that the out-of-process rows carry `local_unit_label` rather than
  the `unit_id` a writer assigns, and that R86 §2.3 puts a widened join key at 2.93x over
  286,896,563 spikes without measuring it as an intermediate. If the stream costs little, §3.3's
  opt-in is a convenience rather than a necessity, and saying so is worth more than permitting it.

- **Whether a build should report what an opt-in bought.** §3.3 makes running an adapter in process
  the recipe author's call, and gives them nothing to judge it by: a build knows what it staged and
  not what the other route would have cost. Whether that belongs beside the encoding report
  (R110 §3.5) or nowhere is unsettled.

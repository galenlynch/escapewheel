# A Build Reaches a Source Through Declarations

| | |
|---|---|
| **Status** | Draft |
| **Amends** | Part 03 §1 (the protocol group the portable profile names); Part 05 §3 (a recipe declares a preference between two sources, and whether a source runs in the writer's process); Part 05 §3.4 (what an adapter declares); Part 05 §3.5 (what a build captures where a command's output carries rows); Part 05 §3.7 (the same, where a recipe names a command); Part 07 §4 (what a build supplies an adapter, an adapter's return type, the protocol it declares, and how an array crosses); Part 09 §5.7 (an extension's rows cross by the same protocols, and a command is carried as a list); Part 09 §5.8 (the connection as a carrier beside the file, and when a report is this run's) |
| **Depends on** | R63 §2.1 (an adapter declares `PRODUCES` before any I/O), R63 §2.2 (silence means the whole, and a contradiction is refused), R87 §2.2 (an adapter declares which recipe fields it states), R109 §2.3 (a shared process is a shared dependency closure), R109 §3.1 (a writer requires no code of an extension), R109 §3.2 (an extension delivers a registry document and rows as files), R110 §3.4 (a choice about one packet's values belongs in its recipe) |
| **Profile** | all |

Normative, except §2, which is informative.

MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense, as in the base specification.

## 1. Scope

Everything a build knows about a source is written down somewhere central. R63 §2.1 has an adapter
declare `PRODUCES` and R87 §2.2 has it declare `STATES`, both read before any I/O; the rest is a
table keyed by the adapter's kind — which resource it wins when two sources offer one, whether it
is handed an object store, whether it may be sampled, which recipe options it cannot be constructed
without, and whose output it reads. Measured across the writer package, 102 string literals match
one of the ten built-in kind names and **80 of them name a kind**: ten are `sources/__init__.py`
mapping each kind to its class, which is the registry of adapters, and **70 are in the modules that
decide behaviour**, 50 of them in the one that drives a build.

How an adapter's rows reach a build is written down nowhere. R109 §2.3 refuses an in-process
extension because its dependency closure becomes the writer's, and two extensions pinning
incompatible versions make that environment unsolvable; R109 §3.2 answers that with files and a
subprocess, **for an extension**. A source adapter is where the heavy libraries of a scientific
format live, so the argument reaches one with more force and nothing states it.

This part states both, and they are one interface rather than two. What a build supplies an adapter
is declared by the adapter and passed as values; how the adapter's rows come back is a protocol the
adapter declares from a group the profile names. Each half decides the other: a build cannot supply
a live object to an adapter in another process, and an adapter cannot be told what to produce
unless a build has something to tell it with.

## 2. Background

Informative.

### 2.1 An adapter's closure is what rots, and authorship does not protect it

R109 §2.3 refuses an in-process extension because its dependency closure becomes the writer's, and
two extensions pinning incompatible versions make that environment unsolvable. An adapter for a
scientific format is where the heavy libraries are, so the argument reaches an adapter with more
force, not less.

The writer's own adapters look exempt and are not. Their environment resolves **57 distributions**
today from five declared dependencies — `escapewheel-validator`, `numpy`, `pyarrow`, `s3fs` and
`universal-pathlib`, with `numcodecs` as the NWB adapter's only
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

### 2.2 An adapter's files say whose it is

`aind.py` reads `rig.json`, `session.json` and `subject.json` — one institute's metadata schema. `sorter` reads `si_folder.json` and
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

### 2.4 Five tables name a kind, and four hold one adapter's own property

`_SHARED_SOURCES` names the three kinds handed an object store. `SAMPLED` names the one kind a
`--sample` build may read partially. `REQUIRED_OPTIONS` names the two kinds that cannot be
constructed without a `zone`. `CONSUMES` names, for each of five kinds, the kinds whose output it
reads, which is what orders a build. Each is a fact about one adapter, recorded where that adapter
is not.

`PRODUCES` and `STATES` are the same kind of fact and are declared on the class, which is what lets
a build read them with nothing open (R63 §2.1). Nothing distinguishes those four from these two
except where they were written. The fifth, `PREFERRED`, is not an adapter's own property at all,
and §2.6 is about where it goes instead.

### 2.5 A registered adapter is given less than a built-in

An adapter may already come from another distribution: `escapewheel.sources` is an entry-point group
and a build consults it after its own ten kinds. What it does with one is call
`build(root, session_id=…, **options)` — and nothing else. A built-in kind is constructed by name,
so `video` receives the reference clock, `sync` receives first samples, and three kinds receive an
object store; a registered kind receives none of them, because the branches that supply them test
for a literal name.

So a registered adapter can produce a resource and cannot be told where to read it from, which is
the case R80 makes ordinary by putting a resource's bytes wherever a resolution document says.

### 2.6 A preference is a claim about a pair, not a property of either

`PREFERRED` gives a contested resource to the source that knows most about it: the NWB knows a
probe's type and manufacturer where the sorter knows only the stream. That is a claim about a pair
of adapters over one dataset, not a property either one has, so no adapter can declare it.

Measured over all ten kinds: **35 resources are produced, 8 are contested by two or more adapters,
and 2 need arbitrating** once the shared ones and the recipe-supplied ones are set aside —
`core.probes`, between `nwb` and `sorter`, and `core.subjects`, between `nwb` and `session`. A
recipe cannot declare either; the table is the only place a preference can be written.

R110 §3.4 settled the same shape for an encoding, which is a fact about one packet's values and so
belongs in the recipe rather than the schema. A preference is a fact about one packet's sources.

## 3. Decision

### 3.1 An adapter declares what a build must supply it

An adapter **MUST** declare what a build supplies it beyond its root and the session identifier, as
a static declaration read with nothing open, in the shape `PRODUCES` and `STATES` already take. A
build **MUST** supply exactly what an adapter declares and **MUST NOT** decide it from the kind's
name.

The reference spelling is `NEEDS`, a set of names beside `PRODUCES` and `STATES` on the class, and
it lives in Part 07 §4 with them rather than here: what a conforming build must do is read a
declaration, and what this implementation calls it is the reference implementation's business
(R87 §2.2 places `STATES` the same way).

A build **MUST** refuse a recipe naming an adapter that declares something the build cannot supply,
before any source is opened, which is where R63 §2.2 already refuses a recipe it cannot satisfy.

**Everything a build supplies is data.** An adapter need not run in the writer's process. Across a
process boundary a build passes an argument list, and an argument list holds strings. So a build
**MUST NOT** require an adapter to accept a live handle — an open store, a connection, an object of
the writer's own — and what may be declared is closed for the same reason: a build can pass only
what survives the crossing.

| an adapter declares it needs | a build passes |
|---|---|
| the root as a location | the URI, which the adapter opens for itself |
| the session's reference clock | its identifier and its rational tick rate |
| the first sample of each stream | one integer per stream name |
| the clocks declared before it runs | each identifier with its rate |
| the units a prior source produced | a row each: the source's names for it, and the identifiers assigned |
| which resources are wanted | the resource IDs the recipe leaves it owning, so it produces no more |
| somewhere to write an array | a location under the staging area, where the adapter produces one |
| a recipe option, named | the value the recipe carries under that name |

A profile adding to that list amends this section. An adapter names the options it accepts among
what it declares, rather than accepting whatever a recipe sets: a build that does not know which
options reach an adapter cannot refuse a recipe setting one the adapter will ignore, which is
R63 §2.2's refusal applied to an option instead of a resource.

**The wanted set is a term a build supplies and an adapter MAY act on.** A build settles ownership
before any source is opened (R63 §2.2), so it knows which of a source's resources it will keep, and
an adapter told that may extract no more — where one that is not told produces everything and a
build discards, which R63 §1.2 measures at one resource in five. Acting on it is permitted rather
than required, because for some sources there is nothing to save: an NWB reaches its eighteen
resources through one open file, so producing three of them costs what producing all eighteen does,
and the adapter filters at the end. A build cannot tell the two apart either, since an adapter that
extracted three and one that extracted eighteen and discarded fifteen return the same rows. It is a
value a build computes, so it belongs here rather than in a transport: telling an adapter what is
wanted is the same act whether its rows travel as files, as a stream, or over a connection.

**A mapping is not what a build passes; rows are.** A build **MUST** pass a collection as records
carrying its key as columns, because a mapping's keys are a type the crossing does not keep:
`conformance/adapter-boundary/` measures the units a build hands the waveform adapter, keyed by a
pair, refused outright, and the electrodes beside them, keyed by an integer, accepted and returned
with **string** keys. The second is the one to fear — a lookup that silently misses, and only where
an adapter runs elsewhere.

A build **MUST NOT** offer one of its own objects as an alternative to what an adapter declared. An
adapter that accepts a `Clock` *and* can read a clock's row has two ways in, and which one a build
takes becomes a property of where the adapter is running — the coupling this part exists to remove,
reintroduced as a fast path.

Sharing survives without being passed. `store_for` already keys its cache on the **resolved root**,
so three adapters pointed at one root open it once because they ask for the same thing, not because
one object reached all three. What moves is where that cache lives.

Separately, an adapter **MUST** declare the kinds whose output it reads, which orders a build rather
than being passed to it. `CONSUMES` records that the NWB adapter reads the sorter's clocks, which is
a fact about the NWB adapter held where the NWB adapter is not.

### 3.2 A recipe declares a preference between two sources

A recipe **MAY** declare which source owns a resource that more than one of its sources produces, in
a table keyed by resource, each entry naming a source and the reason it knows more. A build
**MUST** apply a declared preference and **MUST NOT** hold a preference of its own for any resource
a recipe does not name.

Where two sources produce one resource and the recipe declares neither the preference nor an
explicit `owns`, a build **MUST** refuse the recipe naming both sources and the resource. That is
R63 §2.2's rule unchanged — a contradiction is refused before a byte is read — and it replaces a
built-in winner that no recipe could see.

The refusal is also what answers R63 §1.4, which moved arbitration out of the scaffolder because
"the draft freezes into a document that no longer knows what the scaffolder knew, so a recipe
written before an adapter gained a table never learns of it". A recipe carrying a preference table
freezes the same way. What differs is the failure: a recipe that has not heard of a new contest is
refused naming both sources, where a built-in winner applied one silently.

### 3.3 An adapter delivers its rows out of process

A writer **MUST NOT** require any adapter to be importable in its own environment, and **MUST**
provide a route by which every adapter it ships delivers its rows without being imported. An adapter
author **SHOULD** provide that route for an adapter the writer does not ship, whatever else they
provide.

The obligation is the writer's and the author's rather than the adapter's, which is R109's
allocation: R109 §3.1 binds a writer to build from a document and rows, and describes what an
extension delivers without requiring it of the extension. An adapter is a class and cannot run
itself out of process; whoever ships it can.

**What matters is the process boundary; a transport is a protocol, and protocols come in groups.** A
profile names a group for each way rows cross that boundary, and the protocols in it. An adapter
**MUST** declare and support **at least one** protocol in a group; a build **MUST** support **every**
protocol in every group its profile names.

Running in the writer's process is not one of them, and §3.5 says why: whether a set of adapters
installs together is a fact about one machine on one day, so it is the recipe author's to declare
and not the adapter's. A protocol is what an adapter can promise about itself.

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

**None of this saves an adapter work, and that is a different question.** A Parquet footer answers
cheaply only once the file exists, so `files-v0.1` saves nothing where a command had to produce it;
`DoGet` fetches one descriptor but an adapter that computed everything to list them has already
done the work. What saves an adapter work is being **told what is wanted before it starts**, and a
build knows: R63 §2.2 settles ownership from `owns` and `PRODUCES` before any I/O, which is why
R63 §2.3 can report an unclaimed resource before a byte is read. So the wanted set is something a
build **supplies**, over any protocol, and §3.1 carries it as one more thing an adapter may declare
it needs.

**Which to reach for, then, is about what a source is, not about saving it work.** Where an
extraction already exists or is worth keeping, `files-v0.1` is the cheapest to write and answers
discovery from a footer. Where nothing should be left behind, `stream-v0.1` is a hundred lines.
Where a build wants to ask rather than be told — a source whose shape it does not know until it
looks — `flight-v0.1` is the one with the vocabulary for it.

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
working adapter can carry. What the stream costs on the failing path is larger and is §3.11's: a
build learns that a run failed and not which resource, where Flight names the one it asked for.

A recipe declares files where persistence is the point — an extraction expensive enough to reuse
across builds, or one whose output should still be there to inspect after a failure. That is not a
lesser route: it is the one R109 §3.2 requires of an extension, and both packaged sessions use it
today, re-reading a `tables/` directory across several rebuilds without running the extraction again.

Whether a run succeeded is §3.10's and is the same question under every protocol; how much a build
learns about why it did not is §3.11's, and is not.

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

### 3.4 A command is an argument list, and a stream is bytes

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

### 3.5 A recipe opts a source into the writer's process

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

### 3.6 An adapter returns records, and a transport is not the return type

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
against a test that needs no I/O — and §3.5 puts it where the person who bears it can make it, rather
than settling it here for every recipe.

### 3.7 An identifier crosses the boundary as a name

An adapter reaching a build through files hands over identifiers as the **names** its source used,
never as numbers, because a writer mints every assigned identifier packet-wide (R53 §2.2) and the
numbers do not exist until it has. That is R109 §3.2's rule for an extension and it binds an adapter
identically.

A writer **SHOULD** report what resolving those names cost, as a figure of its own rather than as a
comparison: a build that received rows out of process never staged them the other way and has no
baseline to subtract. What the two routes cost against each other is §6's measurement, not a report
a build can make.

### 3.8 A dense array crosses as a reference

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

**An array is not rows and no transport makes it rows.** §3.3 has an adapter deliver records as an
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

### 3.9 A writer ships each protocol so an adapter need not write one

A writer **SHOULD** ship an implementation of each protocol its profile names, covering both ends,
and **whoever speaks one MAY use it** rather than write their own — an adapter, and an extension
delivering its rows over the same protocols (§3.3). Nobody should hand-roll a framing that is
already specified and already implemented, and the side that does is where the two ends drift apart
first.

Using it **MUST NOT** be a condition of conformance. §3.3 specifies each protocol so either can
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

**A build knows an adapter is serving before it asks.** Where a protocol needs the adapter running
— `flight-v0.1` does, `files-v0.1` and `stream-v0.1` do not — the protocol **MUST** say how a build
establishes that. `flight-v0.1` says it by **connection**: a build retries the socket until it
connects or the adapter's process exits, and reports the exit — measured at **114 ms** to detect an
adapter that failed before binding, against a build that would have waited on that socket forever. A readiness line on standard output
is the obvious alternative and is weaker, because a build waiting for a line that never comes
cannot tell *not yet* from *never* unless it watches the process as well, which is the whole of
what retrying the socket already does.

**A protocol's name is importable with it.** An adapter declares a protocol by naming it, and the
name is a constant the implementation exports rather than a string the adapter spells. Pinning is
then what keeps an old adapter working, and it needs no shim to maintain: the adapter resolves the
version it was written against in its own environment, and that version exports `stream-v0.1` and
speaks it. A profile **MUST NOT** change what a named protocol means (§3.3), so the build at a
later version still names `stream-v0.1` in its group and still reads it.

### 3.10 A build knows a run succeeded from what arrived

R63 §2.2 settles which resources each source owns before any source is opened, which is what lets a
contradictory recipe be refused. A build therefore already holds the set it is waiting for when an
adapter starts: no adapter declares it, no protocol carries it, and it is the same set whether or
not §3.1's wanted term was supplied. A run succeeded when every resource in that set arrived. A
build **MUST** refuse where one did not, naming the source by the name the recipe gave it rather
than by its adapter, since two sources may run the same one.

**A source with no rows for a resource delivers it empty.** An adapter **MUST** deliver every
resource it was asked for, empty where the source has nothing for it, rather than omitting it. The
rule costs an adapter a schema it already holds and buys the only unambiguous reading of absence:
without it a missing resource is a crash under every protocol and *also* a source with nothing to
say under two of them, and no build can tell which. An empty table says the adapter looked. It does
not say the source is empty — an extraction that silently produced nothing delivers the same rows —
and a build wanting that difference reads §3.11's report.

**The data does not say whether a delivery finished.** Measured in
`conformance/adapter-boundary/stream_failures.py`, a command killed after writing four rows and
before the end-of-stream marker delivers **4 of 4 rows that parse clean**, because a reader treats
end of file as end of stream; a finished run, a run that died between two resources and that one all
end with the same parse error. Over `flight-v0.1` a transfer failing partway delivers **0 rows**,
the client discarding what it holds rather than returning a short table. The two protocols leave a
build holding different things and neither says so in the data, which is why the test is the set and
not the bytes.

**A non-zero exit is a failure whatever arrived.** A build **MUST** report one as a failure even
where every resource is present, because an adapter saying it failed is not overruled by its own
output, and a command dying between two resources delivers the first one complete and valid. A build
**MUST** also report a stream it cannot parse as a failure where the command exited zero, which is
the one case the bytes do carry: a stream stopped inside a message fails naming how many bytes short
it was, where every clean end reports a null schema message instead.

**What nothing catches is a short table from a run that exits zero.** An adapter that swallows its
own exception and reports success delivers a table with some rows where more were meant, and no
protocol defends against an adapter that misreports — one that will swallow an exception will as
readily declare a count it does not meet. Where an adapter declares one anyway a build **MUST**
check it: `flight-v0.1` carries a row count per resource in Stage 1, and an adapter that cannot know
its size before it sends declares none, which a build **MUST** read as unknown rather than as zero.
`stream-v0.1` has nowhere to put a count and this section adds nowhere, since a metadata key an
adapter can only fill after materialising its rows is a count bought by giving up the streaming that
named the protocol.

### 3.11 A build reports what the protocol carries

A build that captures standard error and nothing else reports nothing at all for a failure over
`flight-v0.1`. Measured in `conformance/adapter-boundary/failures.py`, an adapter failing inside
that protocol writes **0 bytes** to standard error, because the diagnosis travels on the connection
it was asked over; a build looking where a command would have printed one finds an empty string and
reports a failure with no reason attached. A build **MUST** report everything the protocol it used
carries about a failure, which is standard error for `files-v0.1` and `stream-v0.1`, and the error's
message together with its `extra_info` for `flight-v0.1`.

**Part 05 §3.7 is amended to match.** A build **MUST** capture standard error and report it with a
failure, and **MUST NOT** report standard output as a diagnosis where the recipe put rows on it.
R109 §3.2's reason survives intact: the diagnosis a command prints was always the thing worth
keeping, and standard error is where a command that also emits data must print it.

**A failing adapter is still serving.** Measured, after one resource's call raised, Stage 1 answered
unchanged, another resource delivered its rows, and the run's report came back carrying an `error`
for the resource that failed beside a `warning` from one that had not. A build **SHOULD** therefore
try every resource it was waiting for and report every failure together rather than stopping at the
first, which is what §3.10's set makes worth doing: the answer a person wants is which resources did
not arrive, not which one did not arrive first.

**The report is one shape on three carriers.** Part 09 §5.8 has an extension write a JSON report
carrying a `problems` array whose entries each have a `level` of `error`, `warning` or `info`, a
`message`, and optionally the `resource` the finding is about. An adapter **MAY** write the same
report on the same terms, and a build **MUST** ask for it after a failure as it does after a
success. What differs per protocol is only where it is handed over: a file at a path the recipe
names under `files-v0.1` and `stream-v0.1`, where rows have taken standard output and a file is the
channel left, and `DoAction("report")` under `flight-v0.1`, where the connection is that channel and
no file outlives the run. An adapter with a report **MUST** name `report` among its actions and a
build **MUST NOT** ask one that did not, since an adapter implementing no action lists none and
raises on being asked anyway.

A build owns the adapter's process and terminates it once it has the rows and the report, so an
adapter **MUST NOT** rely on running code after its last response.

**An adapter MAY attach one finding to the failing call.** A plain exception is what an adapter gets
for doing nothing and it does cross — as a **1,108-character** string with the adapter's Python
traceback and gRPC's own debug context pasted inside the message, which a build can repeat and
cannot read. The same failure raised as a Flight error carrying one `problems` entry in `extra_info`
is **125 bytes** a build parses, and saves the round trip the report costs. It is a **MAY** because
the report carries that finding and more: requiring it would tax every raise in every adapter for a
convenience. A build **MUST NOT** refuse a failure whose `extra_info` it cannot parse, and reports
the message alone.

**A report file says nothing about which run wrote it.** Part 09 §5.8 has a build report what a
report contains where one is present, and a file at a path the recipe names is present after any run
that ever wrote one, so last week's findings are reported as this build's and nothing distinguishes
them. The protocol that carries a report on the connection cannot have the defect, since what comes
back was asked for by this run. A build **MUST** remove the path before it runs the command, and
**MUST** treat a report it did not see appear as absent. Nothing reads one yet — R109 §3.6 is
specified and unimplemented — so the correction costs a clause and no rebuild.

**A finding does not ride Stage 1.** `FlightInfo` carries an `app_metadata` field and this protocol
names no meaning for it. A build asks Stage 1 before an adapter has extracted anything, so a finding
put there is one the adapter must know before doing the work, and what a build wants from Stage 1 —
which resources are offered, their schemas and their row counts — is in the `FlightInfo` already. A
build **MUST** ignore `app_metadata`, which leaves the field to a later version of the protocol.

What a build learns about *why* is the one thing a protocol does decide. With `stream-v0.1` a build
learns that the run failed and not which resource, where a Flight failure is an error on the call
and names the resource it was asked for. Getting that from the stream means a build reading the
end-of-stream marker itself rather than handing the bytes to a reader, which is the ownership §3.3
declines — so it stands as what the stream costs, not as something to repair.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This binds
  what a build tells a source and how a source answers, so what changes is who may add one.
- **Nothing R109 permitted is withdrawn.** A file the recipe names remains a route every
  implementation supports, and it is `files-v0.1`: §3.3 adds two protocols beside it and makes none
  of them a default, and §3.5 leaves the in-process route available where a recipe asks for it.
- **`PRODUCES` and `STATES` are untouched.** R63 §2.1 and R87 §2.2 stand; §3.1 says the rest of what
  an adapter needs is declared the same way, not that those two change shape.
- **An extension declares nothing of its own here.** An extension reaches a build as a source
  (R109 §3.2), so the adapter delivering its rows is what declares `NEEDS` and a protocol, and for
  the `tables` kind that is a root and the resources the recipe names. What an extension owes is its
  registry document, which this part does not touch.

## 5. Consequence

Part 03 §1 gains the protocol group the portable profile names. Part 05 §3 gains a preference table,
an in-process declaration and when a source's delivery is complete; Part 05 §3.4 gains what an
adapter declares; and Part 05 §3.5 and §3.7 gain what a build captures from a failure and what an
adapter may report about a run. Part 09 §5.8's report gains the connection as a carrier beside the
file, and the rule that a build clears the path before the run that writes it. Part 07 §4 gains
`NEEDS`, `CONSUMES`, the protocol an adapter declares and how an array crosses — its sentence
reads "two static declarations" today and becomes four. Part 09 §5.7 gains that an extension may
use any
protocol of the group and that a command is carried as a list.

**What a build tells a source.** `session.py` constructs an adapter in **56 lines carrying ten
`spec.kind` branches**, one per built-in, each passing a different set of extras. That becomes one
construction that reads `NEEDS` and passes the values it names. The five tables that name a kind go
with it — `_SHARED_SOURCES`, `SAMPLED`, `REQUIRED_OPTIONS`, `CONSUMES` and `PREFERRED` — against one
`NEEDS` and one `CONSUMES` per adapter, ten of each.

What that costs is three adapters, a cache and a conversion. `nwb`, `waveforms` and `lfp` are handed
an open store today and must open the root themselves; `store_for` already takes a root and keys on
the resolved one, so what moves is where its cache lives — out of the build's context and under
`store_for`, where an adapter asking for a root already opened gets that store without anyone
passing one. The conversion is the NWB adapter's: it calls `Clock.ticks` to turn a source's seconds
into ticks, and `Clock` is a `core.clocks` row with methods on it, so the arithmetic moves to the
rate that row carries. The writer's class stays available to an adapter that has it and stops being
what the interface names, which is §3.1 applied to the adapter that receives the most.

Both packaged recipes gain two lines, `core.probes` to `nwb` and `core.subjects` to `session`, which
is the whole of what §2.6 measures needing arbitration, and an opt-in for whichever sources their
author finds installable together. Neither packet's rows change: the same source wins each contest,
declared where a reader of the recipe can see it.

A registered adapter gains what §2.5 measures it lacking. One can produce a resource today and never
reach a root it must open for itself, because the branches that pass one test for a literal kind;
after this it declares what it needs and a build either passes it or refuses the recipe.

**How a source answers.** A build supports every protocol in the group, so it reads Parquet the
recipe names — which `tables.py` does today, as `{resource: path}` with a batch iterator each — and
gains a reader for a sequence of Arrow IPC streams and a Flight client. Each of the ten adapters it
ships then declares one protocol.

§3.9's implementation is the rest: every end of every protocol, and the names as constants an
adapter imports rather than spells. It can live in the writer to begin with. Splitting it into its
own distribution is a later question and a measurable one — §2.1's 57 against `pyarrow`, which the
protocols need and none exceeds, and which requires nothing — but an adapter out of process resolves
its own environment, so that is a convenience for authors rather than anything conformance turns
on.

The array is the smaller half. `StagedArray` already carries the four layout fields and the
identifier; what changes is that the producer writes the values and returns the location, where
today it hands the values over and the writer writes them. `LFPSource` needs nothing —
`external_arrays` is already the shape — and `add_array` keeps its signature for an in-process
adapter that has not been converted.

The reference implementation owes a command it does not have: `escapewheel` runs `inspect`, `init`,
`extension`, `verify`, `prune` and `import`, and none of them runs one adapter and hands over its
rows, which is what §3.3 requires of the ten it ships. That command is also the `command` a `tables`
source names, so a built-in adapter reaches a build through the same door an extension does
(R109 §3.2) rather than through a second mechanism built for it.

It also carries the defect §3.4 forbids: `TablesSource` takes `command` as a string and splits it
with `shlex`, which the module's own docstring calls "a plain argument list … **not** a shell". Both
packaged recipes say `command = "python extract.py"`, which survives the parse because it contains
no backslash. One naming an interpreter by an absolute Windows path would not, and would fail as a
missing executable rather than as a malformed command. The fix is a TOML array and the deletion of
the split.

§3.10's completeness test costs the ten adapters one habit each. An adapter that has nothing for a
resource returns nothing for it today, and must return it empty instead, which is a schema each
already holds and no extraction it does not already do. It buys the check a build has never had:
`records()` is trusted whole, so a source that quietly produced fewer resources than it owns has
been reaching a packet since R63 §2.3 reduced that case to a warning.

Nothing here forces the ten adapters apart, and §2.2's grouping is why the option is worth having.
An adapter reading one institute's metadata schema or one tool's directory layout can move to that
institute or that tool once it can reach a build without being imported, which is what §3.3
establishes and what nothing before it did.

## 6. Open

- **Whether any out-of-process protocol removes the reason to opt in at all.** §3.3 names three and
  ranks none, and §3.5 leaves the choice to a recipe author; no number stands behind either. What it
  would take:
  stage `core.spike_events` three ways — in process, through a Parquet intermediate, and over an
  Arrow IPC stream — remembering that the out-of-process rows carry `local_unit_label` rather than
  the `unit_id` a writer assigns, and that R86 §2.3 puts a widened join key at 2.93x over
  286,896,563 spikes without measuring it as an intermediate. If the stream costs little, §3.5's
  opt-in is a convenience rather than a necessity, and saying so is worth more than permitting it.

- **Whether a structured failure crosses between two languages.** Every measurement behind §3.10
  and §3.11 is Python answering Python: `extra_info`, `DoAction` and the Stage 1 row count are
  read from the same Arrow build that wrote them. The protocols exist so an adapter need not share
  the writer's closure, and a closure in another language is the case that most needs them. What it
  would take: one adapter in Go or Java serving `flight-v0.1`, failing once, and a Python build
  reading what came back — which also settles whether `extra_info` is carried by every Flight
  implementation or by this one.

- **Whether a build should report what an opt-in bought.** §3.5 makes running an adapter in process
  the recipe author's call, and gives them nothing to judge it by: a build knows what it staged and
  not what the other route would have cost. Whether that belongs beside the encoding report
  (R110 §3.5) or nowhere is unsettled.

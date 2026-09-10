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

### 3.3 An adapter reaches a build through files

Every adapter **MUST** be able to reach a build through files and, where a raw source needs
converting, a command, on the terms R109 §3.2 gives an extension. That is the baseline and it does
not depend on who wrote the adapter: a writer **MUST NOT** require any adapter to be importable in
its own environment.

An adapter **MAY** run in the writer's process where it **adds no requirement the writer does not
already declare**, and a writer **MAY** refuse to run one in process where it cannot establish that.
The condition is the closure and not the authorship, because Python resolves one environment per
process and an adapter that needs one more library makes that resolution harder whoever shipped it
(§2.4). A writer's own adapters satisfy it today and are not exempt from it.

A writer **MAY** additionally run in process an adapter whose declared output exceeds a size the
writer states, for which the intermediate file would cost more than the coupling; `core.spike_events`
at 674.2 MB is the case, and **§6 leaves that threshold unmeasured** rather than naming one this part
cannot support.

### 3.4 An identifier crosses the boundary as a name

An adapter reaching a build through files hands over identifiers as the **names** its source used,
never as numbers, because a writer mints every assigned identifier packet-wide (R53 §2.5) and the
numbers do not exist until it has. That is R109 §3.2's rule for an extension and it binds an adapter
identically.

A writer **SHOULD** report what a file-delivered adapter cost it in identifier resolution where that
exceeds a table it staged directly, which is the measurement §6 leaves open.

## 4. What this does not change

- **No table, column, reference, rule or vocabulary changes, and no packet is rebuilt.** This binds
  where a build learns about a source, so what changes is who may add one.
- **`PRODUCES` and `STATES` are untouched.** R63 §2.1 and R87 §2.2 stand; §3.1 says the rest of what
  an adapter needs is declared the same way, not that those two change shape.

## 5. Consequence

`05` §3 gains a preference table and §3.4 gains what an adapter declares; `07` §4 gains what a build
supplies and how a registered adapter reaches it.

The reference implementation loses four tables that name a kind — `_SHARED_SOURCES`, `SAMPLED`,
`REQUIRED_OPTIONS` and `PREFERRED` — and gains one declaration per adapter. Both packaged recipes
gain two lines, `core.probes` to `nwb` and `core.subjects` to `session`, which is what §2.3 measures
the whole preference table to be. Neither packet's rows change: the same source wins each contest,
declared where a reader of the recipe can see it.

What §3.3 buys is that the ten adapters this project ships stop being a privileged class. A
registered adapter today produces resources and cannot reach an object store; after this every
adapter has the same two routes, and which one it may take turns on whether it adds a requirement
rather than on who wrote it.

## 6. Open

- **The size at which a file boundary costs more than the coupling.** §3.3 permits an in-process
  adapter on that ground and names no number, because none has been measured. What it would take:
  stage `core.spike_events` through a Parquet intermediate and compare, remembering that the rows
  would carry `local_unit_label` rather than the `unit_id` a writer assigns, and that R86 §2.3 puts
  a widened join key at 2.93x over 286,896,563 spikes without measuring it as an intermediate. Until
  then the second permission in §3.3 rests on an estimate, and the first — an adapter adding no
  requirement — is the one carrying the weight.

- **How a writer establishes that an adapter adds no requirement.** §3.3 makes that the condition
  for running one in process and leaves the mechanism open. A distribution's requirements are
  readable from its metadata, so the comparison is available; whether a writer must perform it, or
  may take an adapter's own declaration, is the choice, and it is the difference between a check and
  a promise.

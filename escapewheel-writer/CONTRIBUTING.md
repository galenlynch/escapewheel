# Contributing to escapewheel-writer

This package builds Escapewheel packets: the writer, the source adapters, and the session recipe
that drives them. `README.md` covers running it; this covers changing it.

An import is not a translation. It is a set of adapters reading sources that each disagree with
their own documentation in known ways, into a format whose rules are written down elsewhere. Most
of what follows exists because one of those disagreements was silent once.

---

## Where the rules come from

Use the monorepo's [authority model](../README.md#authority). Packet construction uses the current
v0.2 parts and the generated declarations in `../spec/artifacts/logical_schemas.json`.
`../inventory/` records measured defects in real sources; every compensation cites one.

**A defect found while implementing starts as a proposal or revision draft, never as a silent
workaround here.** The current v0.2 text continues to govern until the change is accepted and
incorporated. Cite the current specification section for behavior; add an accepted-revision
citation where the code also needs to preserve why the rule exists.

## Ownership is declared before a byte is read

Each source in a recipe gets an `owns` list and an optional `contributes` list. `owns` is
exclusive; `contributes` is additive, and exists because `core.clocks` genuinely has two
suppliers — the sorter declares one clock per probe stream, the sync source the rig clock they
are anchored to.

`Recipe.check(registry)` is what makes the declaration pay. Before anything is read it refuses:

- a resource owned twice;
- an owned resource the registry does not define;
- an owned table whose **required** foreign key points at a table nothing supplies — a packet
  that cannot validate, known from two documents with no data in hand.

A nullable foreign key is a warning instead, because `generate(only=...)` silently skips a
foreign-key check whose target is absent, so the packet would pass while meaning less.

Without the distinction the last adapter to run wins silently. That is how a `probe_id` collapse
once matched **0 of 6,781 units**, and how two adapters emitting `core.unit_electrodes` collided
on its primary key.

## A compensation is declared, with evidence

Every adapter works around something known to be wrong upstream; `../inventory/` carries eight
measured defects. **A correction is silent by construction**, which is fine until the fault is
fixed — at which point the importer is still compensating, the packet is wrong in the opposite
direction, and nothing in it says so.

So a compensation is registered in `sources/compensations.py` with its evidence, and every one an
import applied lands in `core.processing_runs.parameters`. **A knowing pass-through is registered
too**: choosing not to correct something is as much an assumption as choosing to. The tests refuse
a compensation with no citation into `../inventory/`.

`--strict` fails a build on any adapter note. A note marks a place the packet says less than the
source could have; working around them is the job, so it is off by default and on in CI, where a
new one is news.

## Never leave Arrow inside a per-batch path

**Every performance defect found in this package has been the same one:** a column turned into
Python objects inside a loop that runs once per batch.

If a line converts a column to a Python `list` and its surrounding code runs per batch, it is
wrong. `pc.unique`, `pc.equal`, `pc.is_in`, `Array.take` and `np.flatnonzero` cover nearly every
case and release the GIL.

Storing a string identifier is not the cause — Parquet dictionary-encodes them, and all five
identity columns of `core.spike_events` are 1.4% of the file. **Converting one is.** Carry the
codes: `read_dictionary=` on the way in, `store_schema=False` so the file still advertises the
registry's type, and never a `pc.less` on a dictionary, which decodes both sides.

`docs/source/performance.md` carries the measurements and what each layout cost. Read it before
changing an encoding, a row-group size or the spill format — each has already been changed and
reverted on evidence.

## Adding a source adapter

An adapter returns records and leaves packet layout and I/O to the build. A packet-owned dense
array is handed over as values by `staged_arrays` and written by the build; run out of process,
`escapewheel deliver` writes it into the `array_location` the build supplies under staging, in a
directory named by its `core.array_assets` row's `resource_id`, which is all the build binds it by
— so that row must carry the `resource_id`. A referenced array is not copied; the adapter returns
its resource declaration. An adapter never chooses final packet paths or commits resources.

`escapewheel_writer.adapter` holds every name an adapter in another distribution imports from this
package, and nothing else here is its to import. Its protocols state what a build asks of an
adapter. Every adapter satisfies
`SourceAdapter`: `records`, `offers`, `notes` and the class's declaration. Each thing only some
adapters have is one capability protocol, which a build tests for and an adapter satisfies by
having its members: `Streams`, `StagesArrays`, `ReferencesArrays`, `ReferencesMedia`,
`StagesPayloads`, `DeclaresCompensations`, `WithholdsAnchors` and `Located`. A table with no rows
is omitted from `records`, `batches` and `offers` alike, and `offers` is the row counts of the
first two; an adapter whose rows need what only a build supplies counts them from the source
instead, as `LFPSource` does.

An adapter this package ships declares no `PROTOCOLS`; one registered by another distribution
declares the protocols it supports, since it is released apart from the writer (Part 12 §3).
`Recipe.check` checks every adapter class as the document `escapewheel declare` would generate.

1. **Declare what it owns** in the recipe, and `contributes` only where a resource genuinely has
   more than one supplier. `Recipe.check` is your first test and it needs no data.
2. **Read through `Context`**, so `SourceStore` can hand you the memoised reader for a root
   another adapter already opened. Two readers of the same bytes can then not disagree. An
   adapter built standalone gets a private store, so nothing about sharing leaks into how you
   write or test one.
3. **Register every compensation and every knowing pass-through**, each citing `../inventory/`.
4. **Emit ticks, never seconds.** Time is an integer on a declared clock; float seconds are
   derived downstream. This is why the sorter is the tick authority — the NWB has already baked a
   per-probe alignment into float seconds and thrown the sample index away.
5. **Declare a `scope` on any `core.processing_runs` row** (R44 §2.1). A run whose subject is
   unrecorded is *undeterminable* rather than unique, and a consumer cannot tell whether two runs
   of an activity compete.
6. **State ordering in `session.CONSUMES`** if another adapter needs your output. A foreign key
   constrains validity, not write order — Parquet files are independent, and nothing stops
   `core.spike_events` being written before `core.units`.

### From another distribution

An adapter need not live here. Register one under the `escapewheel.sources` entry-point group and a
recipe may name its kind like any built-in:

```toml
[project.entry-points."escapewheel.sources"]
tasklog = "your_package.sources:TaskLogSource"
```

The callable takes `(root, *, session_id, **options)` and returns something with the same surface
a built-in has — `offers()`, `records()`, `notes`. Built-in kinds are consulted **first**, so a
plugin cannot shadow `sorter`, and a kind whose import fails is skipped with a warning rather than
raised: one broken package must not make every other source unavailable.

This is R17's problem one layer down. R17 makes an extension's *schema* data, so no code is needed
to validate it; this is what keeps its *adapter* from being a patch to this package. Both exist
for the same reason — declaring an extension has to be easier than adding a column to core, or it
goes the way of NWB's multiple `TimeIntervals`, which the format permits and nobody uses.

## An extension declares; it never ships code on the read path

The invariant, and the one NWB's own extensions break. An `ndx-` extension is a schema **plus a
Python package**: reading a file needs the package installed, the package pins a library version,
and an extension whose author moved on rots. That is why they are a misery, and it is a choice
rather than a necessity.

Here an extension is data the packet carries. `pkt.table("vrf.sites")` needs nothing installed —
no package, no plugin, no registration — because the packet binds the registry that describes it.
A validator generates its checks from the same document with no per-extension code.

The **only** code an extension may require is a source adapter, and only to *write*. That is the
import boundary, where reading a raw format genuinely needs code, and it is never on the read
path. If a capability ever seems to need extension code to *read*, that is the signal to declare
it instead — which is what R56's `clock_from` did for tick conversion and R55's declared reference
does for the join.

### Emit files. Register code only if you must.

The least coupled way to supply a resource, and what an extension should reach for:

```toml
[packet]
extensions = ["vrf.json"]        # a document beside the recipe — no package at all

[[source]]
kind = "vrf_sites"
root = "/data/…/export"
owns = ["vrf.sites"]

[source.delivery]
declaration = "declarations/vrf_sites.json"   # what it produces and which terms it needs
command = ["python", "/opt/vrf/export.py"]
protocol = "files-v0.1"
```

**An extension supplied this way needs no Python of ours, and ships none.** A registry document,
a declaration and a script that writes Parquet: nothing to install, so nothing to rot. That is the
same failure `ndx-` extensions demonstrate on the read path, avoided one step earlier.

Under `files-v0.1` the command reads the build's terms as one JSON object on standard input (Part
12 §4) and writes `<resource_id>.parquet` for each resource into the `delivery_root` that
object names. The declaration document satisfies `spec/artifacts/adapter.schema.json`, and a build reads
it before it launches anything, so a term the script needs is one it declares.

`command` is an argument list — **not a shell**, and with no opinion about how the environment is
arranged. It does not run in `root`, so a script it names is an absolute path.
`uv run /opt/vrf/export.py`, `python -m package.export` and `/opt/venv/bin/python -m
package.export` are all just commands, so isolating an adapter's dependencies is your choice
rather than a tool this package makes you adopt. A non-zero exit is a failure, and so is a wanted
resource that never arrives.

Rows arrive as **names, not numbers**: R53 §2.5 assigns identifiers packet-wide before staging, so
a process outside this one cannot know them and does not need to. Write `session_id` as
`"ecephys_776259"`; the writer turns it into an `int32`.

Reach for an in-process adapter only when you need `Context` — the memoised `SourceStore` so two
readers of the same bytes cannot disagree, or the electrode and clock maps another source built.
That is real, and it is why the built-in adapters are in-process. It is also a shared interpreter
and shared pins, which is the thing to avoid where you can.

### Shipping one from another distribution

Two entry points, both **write-time only**:

```toml
[project.entry-points."escapewheel.extensions"]
vr_foraging = "aind_vr_foraging:REGISTRY"          # the document, or a path to it

[project.entry-points."escapewheel.sources"]
vr_sites = "aind_vr_foraging.sources:SiteSource"   # only if a raw format needs parsing
```

A recipe then names extensions by **id** where a distribution provides them, or by **path** where
one is still being drafted, and several at once is the same as one:

```toml
[packet]
extensions = ["vr_foraging", "opto_tagging", "unit_qc", "draft/my_task.json"]

[[source]]
kind = "vr_sites"
root = "/data/…/behavior"
owns = ["vr_foraging.sites", "vr_foraging.patches"]
```

Nothing about carrying one extension is special-cased, so carrying three is carrying one thrice.
They cannot collide: R17 §2 namespaces every table by its `extension_id`, and the writer refuses a
document that defines a table outside its own namespace or redefines a core one. A packet binds
one registry per extension, so `Recipe.check` refuses two entries resolving to one `extension_id`,
and `PacketWriter` two documents carrying one, rather than keeping the later (Part 05 §3.1).

Reading the resulting packet needs **none of those packages installed**.

### Drafting one

`escapewheel extension draft <id> --table name=path.parquet` reads what the data shows — column names,
their types in R2 §4's vocabulary, and whether a column is ever null — and reports everything it
cannot know. It writes **no role**, so the draft does not validate until a human supplies them:
R48 §2.2 refuses a default because a forgotten classification looks deliberate, and a generated
file is where a forgotten one hides best.

## Writing is not committing

Copying bytes is staging (Part 05). Staged resources MUST NOT appear as committed canonical
resources in the manifest, and a commit writes a candidate manifest and renames it to
`packet.json` **last**. If you are adding a path that produces files, make sure a failure
part-way leaves a packet that is absent rather than one that is half-declared.

## Two tiers of public names

Every module declares `__all__`.

- **User tier**: what `__init__` exports. `docs/source/api.rst` documents it by subject.
- **Adapter tier**: `escapewheel_writer.adapter.__all__`, for a source adapter in another
  distribution. That module defines nothing: each name is one another module exports, and
  `api.rst` lists it as `adapter.<name>`.

Any other module's `__all__` holds the names this package's own modules and tests import from it,
and no other package imports them. A module but `adapter` exports only names it defines, so an
adapter class is imported from the module defining it and not from `sources`. An underscore name
is for its own module and for the test module named after it. `tests/test_surface.py` holds all
of this, and the two tiers against `api.rst` in both directions.

Before taking a name out of a tier, search the other packages for it.

## Testing

Tests build their own inputs rather than depending on real data or on `../fixtures/`. Size a
fixture so the expected numbers can be read off by hand and say in the docstring what makes them
what they are; a test whose expectation you cannot derive on paper is one that will be *adjusted*
when it fails.

Prefer a test that would have caught the bug over one that covers the line. Several here exist
because a measurement contradicted an assumption — they assert the surprising half.

An end-to-end build against real sources is the only check for adapter behaviour, and it is not
in this suite. Run one before claiming an adapter change works, and run the conformance corpus
after anything that changes what is written:

```bash
cd ../fixtures && uv run --no-cache --with ../escapewheel-validator --with duckdb python corpus.py
```

## Before you push

```bash
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
```

Commits are conventional (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`). The title is
imperative; the body says **what changed and why**, not how. Where a change is driven by a
measurement, put the number in the body — it is the part that will not be re-derivable later.

## Conventions

`src/` layout, package in `src/escapewheel_writer/`, tests in `tests/`. Hatchling, ruff at 120
columns with numpy docstrings, mypy strict, pytest with coverage, Sphinx with furo. This package
registers its CLI under the `escapewheel.commands` entry-point group rather than
`[project.scripts]`: two distributions claiming the same console script is a conflict in which
the last installed wins silently.

Docstrings are terse and say what is not obvious from the code: why this way, what breaks
otherwise, the constraint that is not visible locally. No history, no ticket numbers, no dataset
names — state the rule that holds now and let the commit message carry the change.

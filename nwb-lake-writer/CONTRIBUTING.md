# Contributing to nwb-lake-writer

This package builds NWB-Lake packets: the writer, the source adapters, and the session recipe
that drives them. `README.md` covers running it; this covers changing it.

An import is not a translation. It is a set of adapters reading sources that each disagree with
their own documentation in known ways, into a format whose rules are written down elsewhere. Most
of what follows exists because one of those disagreements was silent once.

---

## Where the rules come from

The format is a frozen specification plus a numbered series of revisions, in the parent monorepo:

| | |
|---|---|
| `../nwb_lake_poc_docs/` | the specification. **Frozen** — never edit it, including to fix an error. |
| `../revisions/` | `R<N>-kebab-summary.md`. Where an **accepted** revision and the spec disagree, the revision wins. |
| `../registry/` | `logical_schemas.json`, generated. Tables, columns and rules as data. |
| `../inventory/` | measured defects in real sources. Every compensation cites one. |

**A defect found while implementing goes into a revision, never into the specification and never
into a silent workaround here.** Cite the revision in the code — `R38 §2.2`, not "the observation
window rule" — so a reader is one grep from the argument.

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

An adapter need not live here. Register one under the `nwb_lake.sources` entry-point group and a
recipe may name its kind like any built-in:

```toml
[project.entry-points."nwb_lake.sources"]
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

## Writing is not committing

Copying bytes is staging (`05`). Staged resources MUST NOT appear as committed canonical
resources in the manifest, and a commit writes a candidate manifest and renames it to
`nwb.packet.json` **last**. If you are adding a path that produces files, make sure a failure
part-way leaves a packet that is absent rather than one that is half-declared.

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
cd ../fixtures && uv run --no-cache --with ../nwb-lake-validator --with duckdb python corpus.py
```

## Before you push

```bash
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
```

Commits are conventional (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`). The title is
imperative; the body says **what changed and why**, not how. Where a change is driven by a
measurement, put the number in the body — it is the part that will not be re-derivable later.

## Conventions

`src/` layout, package in `src/nwb_lake_writer/`, tests in `tests/`. Hatchling, ruff at 120
columns with numpy docstrings, mypy strict, pytest with coverage, Sphinx with furo. This package
registers its CLI under the `nwb_lake.commands` entry-point group rather than
`[project.scripts]`: two distributions claiming the same console script is a conflict in which
the last installed wins silently.

Docstrings are terse and say what is not obvious from the code: why this way, what breaks
otherwise, the constraint that is not visible locally. No history, no ticket numbers, no dataset
names — state the rule that holds now and let the commit message carry the change.

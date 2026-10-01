# Contributing to escapewheel-reader

This is the reference reader for the **Escapewheel POC v0.2** format: it opens a packet, resolves
resources through the manifest, and gives tabular access. `README.md` covers installing and
using it; this covers changing it.

Two rules carry most of the weight. Read them before adding anything:

1. [What belongs in the reader](#what-belongs-in-the-reader) — the test for whether a
   transformation is ours at all.
2. [The shape of the API](#the-shape-of-the-api) — free functions in three layers.

---

## Where the rules come from

Use the monorepo's [authority model](../README.md#authority). Reader behavior comes from the
current v0.2 parts, while `../spec/artifacts/logical_schemas.json` supplies the exact generated table,
column, and validation declarations incorporated by Part 02. The portable profile's exact facts
come from the physical-profile descriptor copied from the specification's tree into
`schemas/physical_profiles/`: `profile.py` checks it once, with the copied `descriptor.py`, and `ordering.py` takes Part 03 §5.4's
overriding orders from its table interface for the writer and validator.

**A defect found while implementing starts as a proposal or revision draft, never as a silent
workaround here.** The current v0.2 text continues to govern until the change is accepted and
incorporated. Several revisions exist only because an implementation attempt exposed something —
that is the process working, not a detour.

Cite the current specification section for a behavioral rule, once, at the definition that rule
fixes. Code and tests cite no revision: why a rule exists is the specification's to say, and this
guide and the design notes may name the revision where the reasoning helps a contributor.

## What belongs in the reader

> The reader owns a transformation when doing it yourself from the documented schema would be
> **silently** wrong. Everything else is a query.

Not "tedious", not "slow". *Silently wrong* — producing a plausible number with nothing to
indicate it is not the right one.

"Good units", "trials in condition X", "spikes in a window" all fail the test: a user writes them
correctly unaided, and a wrong answer announces itself. They belong in user code or in SQL.

**The set that passes is bounded, because the hazards are enumerable from the accepted
revisions.** Almost all of them are about time:

| hazard | revision | what we own |
|---|---|---|
| a tick means nothing beside another clock's | R13, R27, R37 | `clocks.align`, `clocks.on_clock` |
| seconds need a declared origin, not a guessed one | R39 | `clocks.seconds`, `clocks.origin` |
| a count needs the span it was observed over | R38 | `observation.unit_windows`, `observation.rate` |
| several runs may have produced the same thing | R41, R44 | `runs.ambiguities`, `runs.preferred_run` |
| an ASOF and a range join differ where windows overlap | R43 | `alignment.aligned_spikes` |
| a channel index counts the channels a run kept, not contacts | R83 | `channels.electrode_at`, `channels.runs_without_channels` |
| an array position names a row only through its own array's labels, which vary along the axis they depend on | R147 | `axes.describe` |

That table is the justification for the module list. If you are adding something, either it
extends a row or it adds one — and adding one means naming the revision that makes it a hazard.

## The shape of the API

**Free functions in three layers, and a `Packet` that mirrors none of them.**

```
kernels      align(ticks, anchor_t, anchor_p, *, bound)       raw arrays, no packet
semantics    on_clock(packet, table), seconds(packet, table)  (packet, table) -> table
access       spike_times(packet, ...), unit_windows(packet)   (packet, ...) -> table
```

**Why free rather than methods: we do not own our data type.** polars, pandas and xarray can put
transformations on the object because they own `DataFrame` and `Dataset`. Our currency is
`pa.Table`, which is PyArrow's, and `pa.Table` has no `.pipe()`. So `table.on_clock()` and
`table.pipe(on_clock)` are both unavailable, and `packet.on_clock(table)` would be a method on
the *packet* operating on a *table*, owned by neither. Free functions are what is left once that
is faced, not a stylistic preference.

A function has one spelling. `Packet` is manifest, resolution, IO and DuckDB registration —
**nothing may be added to it that would work as a free function instead**, and it carries no
method that delegates to one: a delegate is a second name for the same call, and nothing decides
which functions get one. `tests/test_surface.py` checks that no `Packet` method shares a name with
an exported function.

A function taking a packet is typed against `protocols.PacketLike`, so it also runs on a stand-in
that resolves and reads the same way. An answer it must not read twice goes in `packet.memo`, a
`protocols.Memo` with one field per function, reached through `Memo.of(packet)` so that a stand-in
keeping no memo is read each time instead. Nothing in a memo is invalidated: keep there only an
answer that is a property of the packet's bytes, and add no cache attribute to `Packet`.

### Two tiers of public names

Every module declares `__all__`, and a name is public only through one.

- **User tier**: what `__init__` exports. `docs/source/api.rst` documents it by subject.
- **Support tier**: a name in a module's `__all__` that `__init__` does not export. The validator,
  the writer and an adapter package import it from that module, and `api.rst` lists it under
  "Support tier".

A bare name left out of `__all__` is for the reader's own modules, and an underscore name for its
own module; another package imports neither. A module exports only names it defines, so no module
passes on another's. `tests/test_surface.py` holds the tiers against `api.rst` in both directions:
adding a name to an `__all__` means documenting it, and the reverse.

Before taking a name out of a tier, search the other packages for it.

### Two shapes worth copying

**Refuse rather than choose.** Where the packet does not determine an answer, raise and name the
revision. `NoTimeOrigin`, `NotAligned`, `AmbiguousRun`, `StaleSupport` and `UnresolvableChannelIndex` are all this.

A rule from an **accepted** revision raises. Something only a **proposed** revision would catch
warns instead — a non-binding revision must not turn a readable packet into an unreadable one.
`runs.check` does both and is the worked example.

**The convenience accessor is guarded; the general one is not.** `units()` promises *the units*
and refuses when two sortings coexist with no declared preference. `table("core.units")` promises
rows and returns them. Keep that split: it is where the escape hatch lives, and it is why the
guard can afford to be strict.

## A note on Part 07

Part 07 is informative and may lag the normative parts. Implement the current normative v0.2 parts
and registry declarations. If its API sketch contradicts them, treat that as a documentation defect
to repair through the revision process, not as a package-local precedence rule.

## Both paths, or neither

Validation needs DuckDB because the rules are SQL. **Reading must not.** A complete read path
goes through PyArrow, `duckdb` is the optional `sql` extra, and a packet must stay fully readable
without it. That is what R3 §2.1's ban on nested Parquet types exists to protect, and it is why
the validator is a separate distribution.

The consequence is a real tax: a few semantic operations exist twice, once as SQL and once over
PyArrow. Three or four, not thirty. When you add one, **add both, and add a test asserting they
agree on the same packet** — `test_observation.py` has the pattern. Two implementations of one
rule agree only if something checks.

Do not resolve this by having the SQL path call the Python one, or by making a rule depend on a
view this package registers. A registry rule must be runnable by any implementation from
`logical_schemas.json` alone (R2 §7.4).

## Testing

Tests build their own minimal packet in `tmp_path` (`tests/conftest.py`) rather than depending on
`../fixtures/`, whose output is gitignored and belongs to the monorepo-level conformance corpus.
**Keep it that way — this package must be testable standalone.**

Size a fixture so the expected numbers can be read off by hand, and say in the docstring what
makes them what they are. `test_alignment.py` uses two events and five spikes for exactly this
reason; a test whose expectation you cannot derive on paper is a test that will be *adjusted*
when it fails.

Prefer a test that would have caught the bug over a test that covers the line. Several tests here
exist because a measurement contradicted an assumption — they assert the surprising half.

For an end-to-end check against a real packet:

```bash
uv run --no-cache --with ../escapewheel-validator --with duckdb python ../fixtures/corpus.py
```

## Before you push

```bash
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
```

Known noise: `mypy` reports a handful of pyarrow-stub errors in `discriminators.py` and
`profile.py`, and `codespell` flags "sortings", which is correct usage here.

Commits are conventional (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`). The title is
imperative; the body says **what changed and why**, not how — the diff already says how. Where a
change is driven by a measurement, put the number in the body: it is the part that will not be
re-derivable later.

## Conventions

`src/` layout, package in `src/escapewheel_reader/`, tests in `tests/`. Hatchling, ruff at 120
columns with numpy docstrings, mypy strict, pytest with coverage, Sphinx with furo. CLI entry
points go in `[project.scripts]` and are implemented in `src/escapewheel_reader/scripts/`.

Docstrings are terse and say what is not obvious from the code: why this way, what breaks
otherwise, the constraint that is not visible locally. No history, no ticket numbers, no dataset
names — state the rule that holds now, and let the commit message carry the change.

# Escapewheel AIND

Source adapters for the Allen Institute for Neural Dynamics' own formats, for building
[escapewheel](../README.md) packets.

Escapewheel's writer ships adapters for standards — SpikeInterface, Open Ephys, Harp, NWB — because
many institutions read them. An adapter serving one institution belongs outside that set, and this
is where those live: AIND's `session.json` metadata schema, the behaviour videos with their
headerless three-column CSV, the dialect columns an AIND pipeline writes into an otherwise
ordinary NWB, and the unit quality metrics its sorting analyzer computes.

## It is built as though it were already external

The package sits in the monorepo beside `escapewheel-writer` and depends on it, one direction only.
Nothing in the writer imports this package.

Its kinds register through the `escapewheel.sources` entry-point group, which
`escapewheel_writer.sources.discovered()` loads, rather than by being listed in that package's
built-in table. A registered kind is constructed exactly as a built-in one is, so nothing here is a
lesser source — the one difference a recipe sees is that a build will not reach a kind it neither
ships nor is told how to run, so a recipe naming one of these sets `in_process = true` or gives it
a `[source.delivery]` command (Part 05 §3.9). Each class declares the protocols `escapewheel
deliver` serves it over (Part 12 §3), so a delivery need not name one.

Writing it this way is what makes moving it to its own repository a packaging change rather than a
rewrite.

## Commands

```bash
uv sync
uv run pytest
./scripts/run_linters_and_checks.sh -c
```

`python verify.py` at the repository root runs this suite with the other three.

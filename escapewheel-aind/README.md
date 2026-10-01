# Escapewheel AIND

Source adapters for the Allen Institute for Neural Dynamics' own formats, for building
[escapewheel](../README.md) packets.

Escapewheel's writer ships adapters for standards — SpikeInterface, Open Ephys, Harp, NWB — because
many institutions read them. An adapter serving one institution belongs outside that set, and this
is where those live: AIND's `session.json` metadata schema, the behaviour videos with their
headerless three-column CSV, the dialect columns an AIND pipeline writes into an otherwise
ordinary NWB, and the unit quality metrics its sorting analyzer computes.

## Source kinds

A recipe names one of these as a `[[source]]`'s `kind`:

| kind | reads |
|---|---|
| `session` | `session.json` and `subject.json`: each stream's observation window, and where tick zero sits |
| `video` | a behaviour video and its CSV: one row per frame on the rig clock |
| `aind_nwb` | an NWB written by an AIND pipeline, with the columns that pipeline adds |
| `aind_unit_qc` | a sorting analyzer's unit quality metrics, as the `aind_unit_qc` extension |

[DESIGN.md](DESIGN.md) explains why each reads its source the way it does.

## It is built as though it were already external

The package sits in the monorepo beside `escapewheel-writer` and depends on it, one direction only.
Nothing in the writer imports this package, and it has no importable tier: `escapewheel_aind`
exports no name, and a build reaches each kind by the entry point that registers it.

Its kinds register through the `escapewheel.sources` entry-point group, which
`escapewheel_writer.adapter.discovered()` loads, rather than by being listed in that package's
built-in table. A registered kind is constructed exactly as a built-in one is, so nothing here is a
lesser source — the one difference a recipe sees is that a build will not reach a kind it neither
ships nor is told how to run, so a recipe naming one of these sets `in_process = true` or gives it
a `[source.delivery]` command (Part 05 §3.9). Each class declares the protocols `escapewheel
deliver` serves it over (Part 12 §3), so a delivery need not name one.

Writing it this way is what makes moving it to its own repository a packaging change rather than a
rewrite.

## Its extension registries

`extensions/` holds the `aind_opto` and `aind_unit_qc` registries these adapters fill, beside them
rather than in the specification. They are not in the wheel, so a recipe binds one by the path of
its document. `../extensions/README.md` describes how they are assembled and checked.

## Commands

```bash
uv sync
uv run pytest
./scripts/run_linters_and_checks.sh -c
```

`python verify.py` at the repository root runs this suite with the other three.

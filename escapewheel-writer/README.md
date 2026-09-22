# Escapewheel Writer

![CI](https://github.com/AllenNeuralDynamics/escapewheel-writer/actions/workflows/ci-call.yml/badge.svg)
[![PyPI - Version](https://img.shields.io/pypi/v/escapewheel-writer)](https://pypi.org/project/escapewheel-writer/)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border.json)](https://github.com/copier-org/copier)

Write Escapewheel packets, and the source adapters that feed them.

The unit of work is a **session recipe**: one TOML file naming every source, which resources
each is responsible for, and the clocks they share. It is also the provenance record — the
recipe lands in `core.processing_runs.parameters`, so a committed packet says what produced it.

```bash
escapewheel inspect sorter /data/session_sorted        # what a source offers (05 Stage 1)
escapewheel init --session-id s001 \
  --source sorter=/data/session_sorted \
  --source nwb=/data/session.nwb > session.toml     # a draft, contested resources flagged
escapewheel import session.toml --check                # everything wrong, before any I/O
escapewheel import session.toml                        # stage, validate, commit
```

## The recipe

```toml
[packet]
id = "ecephys_776259_2025-04-09"
registry = "../registry/logical_schemas.json"

[session]
session_id = "ecephys_776259_2025-04-09"
reference_clock_id = "harp"

[[clock]]
clock_id = "harp"; name = "HARP"; tick_rate_num = 31250; origin = "HARP epoch"

[[source]]
kind = "sorter"
root = "/data/session_sorted"
owns        = ["core.units", "core.spike_events", "core.sorting_runs"]
contributes = ["core.clocks"]        # one clock per probe stream

[[source]]
kind = "sync"
root = "/data/session_raw/ecephys/ecephys_clipped"
owns        = ["core.clock_anchors"]
contributes = ["core.clocks"]        # the rig clock the streams anchor to
```

`owns` is exclusive and `contributes` is additive. That distinction is load-bearing: several
adapters can produce `core.probes`, and without a declared owner the last one to run wins
silently. `escapewheel import --check` refuses a recipe where two sources own one resource, or
where an owned table's required foreign key points at a table nothing produces — both knowable
from the recipe and the registry, with no data in hand.

Before recipe checking or source I/O, the importer checks the exact core registry bytes and binds
the complete result to an in-process checked context. Extension registries are checked against
that same core context. A non-valid result stops the build before an adapter opens or staging
begins; `--registry-result PATH` writes the portable core result for automation. The public
`PacketWriter` constructor provides the same boundary for callers supplying mappings.

## An importer is not one step

Part 05 is explicit: *"do not combine source parsing, normalization, validation, and writing into
one opaque step."* The modules are that decomposition, and the rule that keeps it honest is
that **an adapter never writes a file** — its return type is records, not a path.

| Module | Job |
|---|---|
| `sources/` | One adapter per source. Returns records; touches no filesystem. |
| `recipe` | Parse and check the recipe. Opens nothing. |
| `session` | Order the sources, run them, keep what each owns. |
| `writer` | Stage, validate, commit. |
| `arrays` | Zarr v3 layout: chunk for the question, shard for the object. |

Ordering comes from the adapters, not the registry: a foreign key constrains validity, not
write order, and what actually sequences a build is data-flow — the NWB source needs the
sorter's units before it can attach a unit to an electrode.

## Commit is atomic

Part 05 Stage 5: write staged resources, validate them where they stand, move them into place, and
rename the manifest **last**. Until that rename the root holds no manifest at all, so a reader
finds nothing rather than a partial import claiming to be valid. A commit that finds errors
raises `CommitRefused` and leaves `staging/` for inspection.

## Installation

If you choose to clone the repository, you can install the package by running the following command from the root directory of the repository:

```bash
pip install .
```

Otherwise, you can use pip:

```bash
pip install escapewheel-writer
```



To develop the code, run:
```bash
uv sync
```

## Development

**Changing this package?** Read [CONTRIBUTING.md](CONTRIBUTING.md) first — it carries the rules
that decide what belongs here, and the process for a specification defect found while
implementing.


Please test your changes using the full linting and testing suite:

```bash
./scripts/run_linters_and_checks.sh -c
```

Or run individual commands:
```bash
uv run --frozen ruff format          # Code formatting
uv run --frozen ruff check           # Linting
uv run --frozen mypy                 # Type checking
uv run --frozen interrogate -v src   # Documentation coverage
uv run --frozen codespell --check-filenames  # Spell checking
uv run --frozen pytest --cov escapewheel_writer # Tests with coverage
```


### Documentation
```bash
sphinx-build -b html docs/source/ docs/build/html
```


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

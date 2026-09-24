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
escapewheel inspect sorter /data/session_sorted        # what a source offers (Part 05 §4.1)
escapewheel init --session-id s001 \
  --source sorter=/data/session_sorted \
  --source nwb=/data/session.nwb > session.toml     # a draft; contested resources await a [preference]
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

[[source]]
kind = "nwb"
root = "/data/session.nwb"
zone = "UTC"

[preference."core.probes"]
source = "nwb"
reason = "the NWB states a probe's type and manufacturer; the sorter knows only the stream"
```

A recipe is TOML 1.0 whose decoded form satisfies `schemas/recipe.schema.json`, vendored from
`registry/recipe.schema.json` (Part 05 §3.1). Its top-level blocks are closed, so a misspelled
block is refused on load rather than dropped; `registry/recipe.example.toml` uses every one. A
source kind appears once, and every report names a source by its kind. An extension appears once
too: `[packet].extensions` entries whose documents carry one `extension_id`, whether a repeated
entry, a path and an installed id, or two versions, are refused, since a packet binds one registry
per extension.

`owns` is exclusive and `contributes` is additive. That distinction is load-bearing: several
adapters can produce `core.probes`, and without a declared owner the last one to run wins
silently. An entry without `owns` owns what its adapter can supply and no other entry owns,
except the resources the adapter declares under `CONTRIBUTES` — the clocks of its own streams,
its own devices and arrays — which it contributes. Where two such entries would own one
resource, the recipe names the winner in `[preference]`, with the reason it knows more; the
writer holds no winner of its own (Part 05 §3.3).

`escapewheel import --check` refuses a recipe where two sources own one resource, where a
preference names a source that is not listed, cannot supply the resource or contradicts another
entry's `owns`, or where an owned table's required foreign key points at a table nothing
produces — all knowable from the recipe and the registry, with no data in hand. `escapewheel
init` leaves each contested resource to no source and writes a commented-out `[preference]`
naming the candidates, so its draft is refused until one is chosen.

Before recipe checking or source I/O, the importer checks the exact core registry bytes and binds
the complete result to an in-process checked context. Extension registries are checked against
that same core context. A non-valid result stops the build before an adapter opens or staging
begins; `--registry-result PATH` writes the portable core result for automation. The public
`PacketWriter` constructor provides the same boundary for callers supplying mappings.

## An importer is not one step

Part 05 is explicit: *"do not combine source parsing, normalization, validation, and writing into
one opaque step."* The modules are that decomposition, and the rule that keeps it honest is
that **an adapter writes only where the build points it** — its return type is records, not a
path, and what crosses a process boundary as files lands in a location the build supplies empty.

| Module | Job |
|---|---|
| `sources/` | One adapter per source. Returns records; writes only where the build points it. |
| `recipe` | Parse and check the recipe. Opens nothing. |
| `session` | Order the sources, run them, keep what each owns. |
| `writer` | Stage, validate, commit. |
| `arrays` | Zarr v3 layout: chunk for the question, shard for the object. |

Ordering comes from the adapters, not the registry: a foreign key constrains validity, not
write order, and what actually sequences a build is data-flow — the NWB source needs the
sorter's units before it can attach a unit to an electrode.

## Store sources are read through a cache

A source root on an object store is opened through fsspec's `simplecache`, so each object is
fetched once and read locally. The cache lives in `.escapewheel-source-cache/` in the packet's
parent directory, on the filesystem that will hold the packet, and a rebuild into a new directory
reuses what the last one fetched. Setting `ESCAPEWHEEL_SOURCE_CACHE` names another directory; the
variable is also how the location reaches an adapter run out of process. The specification governs
none of this: bytes in the cache never reach a delivery.

## Commit is atomic

Part 05: write staged resources, derive the requested analysis resources from the staged packet,
validate the whole of it where it stands, move it into place, and rename the manifest **last**. Until that rename the root holds no manifest at all, so a reader
finds nothing rather than a partial import claiming to be valid. A commit or amendment whose packet
verdict is not `passed` raises `CommitRefused` and leaves `staging/` for inspection, so a failing
extension or an incomplete evaluation publishes nothing (Part 05 §9.2).

Before its first write outside `staging/`, a commit or amendment records in `staging/promotion.json`
every path it will create. A retry after an interruption removes those paths and publishes; a
promoted directory with no record, or a record it cannot read, is refused and nothing is removed
(Part 05 §6). `escapewheel prune` reports `staging/` and those paths apart from strays.

## Digests, and `escapewheel verify`

Every resource the packet owns records a SHA-256 `digest`, `{"algorithm": "sha256", "value": …}`,
as Part 04 §4.3 requires; a Zarr prefix's value is the SHA-256 of its member listing. A build
records nothing it could not reach about a referenced resource (Part 04 §5.2), so
`escapewheel verify` records it once the bytes have landed, as a new packet version:

```bash
escapewheel verify packet/                   # sizes, and each prefix member with its entity tag
escapewheel verify packet/ --level sha256    # also a digest, and each member's beside it
```

A store's entity tag is recorded verbatim under `etag`, a multipart one included, and is compared
only with itself; it never stands in for a digest. The LFP source's `verify` setting records the
same levels at build time.

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

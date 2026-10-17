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
| `dynamic_foraging` | the foraging GUI's behavior JSON: the task's trials, blocks and session parameters |

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

## Drafting a session's recipe

`escapewheel-aind-recipe` drafts the recipe for one ecephys session from its raw asset's name:

```bash
uv sync --extra recipe
CODEOCEAN_API_TOKEN=... uv run escapewheel-aind-recipe ecephys_786867_2025-09-25_12-43-56 \
  --registry ../spec/artifacts/logical_schemas.json \
  --extension extensions/aind_unit_qc.json --extension ../extensions/dynamic_foraging.json \
  --out recipe.toml
uv run escapewheel import --check recipe.toml
```

The drafter takes its inputs from three places:

- **DocDB v2** supplies the session's facts, from the raw asset's record, and the assets derived
  from that asset.
- **Code Ocean** supplies more of those assets. Its app parameters also record which sorted asset
  an NWB was built from.
- **S3** listings of known prefixes, one level each, show what each chosen asset holds.

It reads only assets in a public bucket, so it refuses an asset stored inside Code Ocean and names
the asset in the recipe's header. `--mirror` names a readable copy of such an asset instead, as a
CSV of `asset_name` and `destination`. It takes the newest public sorted asset, or the one `--sorted`
names. It takes the newest public NWB built from that sorting, or the one `--nwb` names. Where no
such NWB is public, it reads the sorted asset's own ephys-only NWB, which carries probes and
electrodes but no behaviour. `--no-codeocean` drafts from DocDB alone.

The sources and their ownership are those an AIND ecephys session needs, so a resource that two
sources can supply is already settled. Values that no catalogue states are marked `GUESS`. The
recipe's footer lists each source it left out, with the reason. `video` is added only with
`--videos`, a local copy of the behaviour videos, because the adapter's `ffprobe` reads a local
file. The task's trials, blocks and session parameters come from the foraging GUI's behavior
JSON, and the sniff voltage from the HARP folder holding its register.

`acquisition_start_time` in the raw asset's record is a Pacific wall-clock reading stamped `+00:00`.
The drafter keeps a `+00:00` stamp only where a stream boundary with a non-zero offset states the
same instant. It reads any other `+00:00` stamp as local time, and the recipe says so.

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

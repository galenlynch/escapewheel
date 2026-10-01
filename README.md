# Escapewheel

A data-lake format built on **Parquet, Zarr v3 and a JSON manifest**, whose core vocabulary
targets extracellular electrophysiology, with no runtime dependency on NWB, HDMF or PyNWB. A packet is a directory you can
open with any Parquet reader; the format's meaning lives in the files and in a machine-readable
schema registry, never in a reader library.

This is a proof of principle.

## Authority

For v0.2, authority is assigned by concern in
[Part 00](spec/parts/00_architecture.md#ew-specification-authority):

- The numbered parts own meanings, processing semantics, obligations, conformance, artifact roles,
  and the subject boundaries assigned there.
- A machine-readable artifact owns exact structures or assignments only where a numbered part
  expressly incorporates it. Part 02 incorporates the registry and registry-contract schemas,
  the initial contract descriptor, and `spec/artifacts/logical_schemas.json` for their stated extents.
- `spec/README.md` is an informational entry point, and
  `Escapewheel_POC_v0.2_Implementation_Spec.md` is a generated convenience rendering. Neither is a
  separately edited normative owner.
- `nwb_lake_poc_docs/` and `revisions/` preserve the starting point, decisions, and rationale.
  Implementations, tests, examples, and developer documentation provide behavior or evidence but
  acquire no independent authority.

A disagreement among owning artifacts makes the specification candidate internally inconsistent;
no general prose-wins or data-wins rule chooses one silently.

## Why

NWB stores an ecephys session as one HDF5 or Zarr hierarchy whose semantics are recoverable
mainly through PyNWB. That makes columnar analytics awkward, cross-language reading hard, and
partial reads expensive. Escapewheel keeps the science and changes the substrate:

- **Tables are Parquet**, every column a primitive — no nested types, so a native reader stays
  viable in a language with no embedded SQL engine.
- **Arrays are Zarr v3**, chunked for the question and sharded for the object store.
- **Time is integer ticks on a declared clock.** Float seconds are derived, never stored.
- **Validation is data.** Most checks are generated from the registry's
  own structure.

## Layout

| Directory | What it is |
|---|---|
| `spec/` | The specification's tree: the README and style guide, the numbered parts in `parts/`, the incorporated artifacts in `artifacts/`, the core registry's source in `source/`, the rendered listing, single-file rendering and examples in `informative/`, and the tools producing and checking them in `tools/`. See [Authority](#authority). |
| `nwb_lake_poc_docs/` | The frozen v0.1 specification it was compiled from. Never edited. |
| [`revisions/`](revisions/) | The specification-change lifecycle, including proposals, drafts, and accepted decision records. |
| `extensions/` | The dynamic-foraging and VR-foraging extension registries, generated from TOML sources and checked where they sit by the tree's checker. |
| `escapewheel-reader/` | The reference reader. Opens a packet, resolves resources, gives tabular and array access. |
| `escapewheel-validator/` | The reference validator. SQL rules generated from the registry, plus the shim for what SQL cannot see. |
| `escapewheel-writer/` | The writer, the source adapters, and the session recipe that drives them. |
| `escapewheel-aind/` | AIND's source adapters and its two extension registries, `aind_opto` and `aind_unit_qc`, in `extensions/`. |
| `fixtures/` | The conformance corpus: one valid packet and its variants, each with its expected finding recorded as data. |
| `integration/` | The writer, reader, and validator run against one another, and the generator of Part 08's example packet. |
| `conformance/` | Mechanical probes producing the measured evidence revisions cite, and the registry checks needing more than the tree holds. |
| `inventory/` | Source inventories from discovery (Part 05 §4.1), and the upstream defects found while writing adapters. |

## A packet

```
packet.json                      the manifest: every resource, its location, and each bound registry's digest
registries/<id>/<version>.json.gz    the registries that declare the packet's resources
tables/core/*.parquet                canonical normalized facts
arrays/core/*.zarr                   dense arrays
```

Resources are addressed by dotted ID (`core.intervals`), never by path. Nothing in the format
uses file layout as identity.

## Three levels

- **Semantic** (Part 01) — what a Trial, Unit, Clock or ElectricalSeries *means*. Storage-agnostic.
- **Logical** (Parts 02 and 06) — those concepts as computable resources: tables, dense arrays and opaque payloads.
- **Physical** (Parts 03 and 12) — `escapewheel-portable-v0.1`: Parquet + Zarr v3 + JSON, readable with no server.

## Building and reading a packet

Build from a checkout: no package is published to an index. Run `uv sync` in `escapewheel-writer/`
for the standard sources, or in `escapewheel-aind/` to add AIND's, and run the commands below there
with `uv run`. A recipe's paths resolve against the recipe's own directory. It names the core
registry at `spec/artifacts/logical_schemas.json` and each extension by the path of its document:
`dynamic_foraging` and `vr_foraging` lie in `extensions/`, and `aind_opto` and `aind_unit_qc` in
`escapewheel-aind/extensions/`.

```bash

escapewheel inspect sorter /data/session_sorted  # what a source offers (Part 05 §4.1)
escapewheel init --session-id s001 \
  --source sorter=/data/session_sorted \
  --source nwb=/data/session.nwb > session.toml
escapewheel import session.toml                  # stage, validate, commit (Part 05 §2)
escapewheel validate packet/                     # re-validate any time
escapewheel ls packet/                           # what is in it
```

```python
from escapewheel_reader import open_packet

packet = open_packet("packet/")
trials = packet.trials(session_id="s001")  # a pyarrow.Table
spikes = packet.spike_times(units=["unit_0001"])  # predicate pushdown, no full scan
waveform = packet.array_resource("core.waveform_mean").read((slice(0, 1),))
```

A **session recipe** is the unit of import: one TOML file naming every source, which resources
each is responsible for, and the clocks they share. It is also the provenance record — the
recipe lands in `core.processing_runs.parameters`, so a packet says what produced it.

## Reporting a problem

Report problems as issues on the [repository](https://github.com/galenlynch/escapewheel/issues),
with the recipe, the command, and its output. A defect in a part, a registry or an incorporated
schema is a specification change and follows `revisions/README.md`; a defect in a package is
fixed in the package.

## Status

Current phase status, packet measurements, and generated repository counts are maintained in
[STATUS.md](STATUS.md). Run the monorepo verification command below to check the working tree rather
than copying those values into another document.
## Development

This is one Git repository with separate uv projects for its Python packages. From a package
directory:

```bash
uv sync --all-extras
./scripts/run_linters_and_checks.sh -c    # format, lint, mypy, interrogate, codespell, pytest
```

Python 3.12 or newer. Always `uv`, never bare `pip` or `python`.

For the registry and generation pipeline, see `CONTRIBUTING.md`. The specification style guide is
`spec/CONTRIBUTING.md`. For specification changes, start at
`revisions/README.md`; uncertain changes begin as proposals rather than normative drafts.

Run the monorepo verification from the repository root:

```bash
uv run --project escapewheel-writer python verify.py
```

After changing the registry, the check generator, or any rule, re-run the corpus:

```bash
cd fixtures && uv run --project ../escapewheel-validator python build.py && \
               uv run --project ../escapewheel-validator python corpus.py
```

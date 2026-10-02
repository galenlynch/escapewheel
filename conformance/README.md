# Conformance

Each directory answers one question about the specification or its registries that the
specification's own tree cannot answer alone. Its directories are of two kinds.

**Checks** run on every `verify.py`, and a failure fails the build:

| directory | checks |
|---|---|
| `registries/` | the registries against the v0.1 Part 02 table ledger in `spec-sweep/tables.py`, every Tier 2 rule executed by an engine, and every valid rule lowered for it |
| `rule-language/` | the Tier 2 rule language against its vectors, and every shipped rule against the language's static profile |
| `unit-identity/` | packet-local unit identity across the core and extension registries |
| `specification-framework/` | that the framework checks reject conflicting declarations and projections |
| `registry-contract/` | R126's registry migration against its frozen pre-migration side |
| `history-cleanup/` | R121's cleanup against its frozen pre-cleanup declarations |

**Probes** produce the measured evidence a revision or part cites. They run by hand, each from its
own README, and are rerun when a library version or the question changes:

| directory | measures |
|---|---|
| `parquet-probe/` | Parquet encodings, spike-table layouts, and which readers in which languages decode them |
| `zarr-probe/` | the Zarr reader floor across five readers, codec sizes, and waveform chunking |
| `adapter-boundary/` | what crosses between a build and an adapter, in-process and over IPC |
| `interval-kinds/` | one interval base table against one table per kind |
| `spec-sweep/` | the frozen v0.1 parts against each other and against R3 |

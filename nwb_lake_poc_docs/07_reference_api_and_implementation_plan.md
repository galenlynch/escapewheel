# 07 - Reference API and Implementation Plan

## Goal

The first reference implementation should be small, boring, and useful. It should prove that a packet can be created, validated, and queried without HDMF/PyNWB in the hot path.

PyNWB MAY be used as an import adapter for source NWB files.

## Suggested package layout

```text
nwb_lake/
  __init__.py
  packet.py
  manifest.py
  schemas.py
  validate.py
  importers/
    nwb.py
    spike_sorting.py
    behavior.py
  writers/
    parquet.py
    zarr.py
  materialize/
    spike_events.py
    spikes_by_trial.py
    trials_wide.py
  access/
    duckdb.py
    polars.py
    arrays.py
  cli.py
```

## User-facing API

Minimum API:

```python
import nwb_lake as nwl

pkt = nwl.open_packet("/path/to/session_001.nwbpkt")

pkt.validate()

trials = pkt.table("core.trials")
units = pkt.table("core.units")
spike_chunks = pkt.table("core.unit_spike_chunks")
lfp = pkt.array("probe0_lfp")
```

SQL access:

```python
con = pkt.duckdb()

con.sql("""
    SELECT unit_id, COUNT(*) AS n_chunks, SUM(n_spikes) AS n_spikes
    FROM core_unit_spike_chunks
    GROUP BY unit_id
""").df()
```

Convenience accessors:

```python
pkt.trials()
pkt.units()
pkt.spike_times(unit_id="unit_001")
pkt.events(event_type="reward")
pkt.array_asset("probe0_lfp")
```

Analysis materialization:

```python
pkt.materialize("analysis.spike_events")
pkt.materialize("analysis.spikes_by_trial", alignment_event="trial_start")
pkt.materialize("analysis.trials_wide")
```

## Command-line API

Suggested commands:

```bash
nwb-lake inspect-source source.nwb --out source_inventory.json
nwb-lake import source.nwb --packet session_001.nwbpkt
nwb-lake validate session_001.nwbpkt
nwb-lake ls session_001.nwbpkt
nwb-lake sql session_001.nwbpkt "SELECT COUNT(*) FROM core_trials"
nwb-lake materialize session_001.nwbpkt analysis.spike_events
```

## Internal object model

Do not create a large custom object hierarchy. Use a thin wrapper around standard backends.

Suggested objects:

### `Packet`

Responsibilities:

- load manifest;
- resolve resource URIs;
- list resources;
- validate manifest;
- provide table/array access;
- provide SQL registration;
- update manifest during controlled writes.

### `Resource`

Responsibilities:

- expose resource metadata;
- resolve URI;
- know layer/kind/schema/profile;
- know validation state;
- know lineage.

### `TableResource`

Responsibilities:

- open as PyArrow table/dataset;
- register with DuckDB;
- optionally expose Polars scan.

### `ArrayResource`

Responsibilities:

- open Zarr array/group;
- expose xarray adapter when dimensions/coords are available.

### `Validator`

Responsibilities:

- run schema checks;
- run resource existence checks;
- run cross-reference checks;
- produce machine-readable validation report.

## Implementation phases

### Phase 0: Spec fixtures

Create a tiny synthetic packet by hand.

Requirements:

- one session;
- one subject;
- one clock;
- two trials;
- two units;
- spike chunks;
- validation report.

This packet is the first test fixture.

### Phase 1: Manifest and table reader

Implement:

- `open_packet`;
- manifest parsing;
- resource listing;
- Parquet table loading;
- DuckDB registration.

Success criterion:

```python
pkt = open_packet("example_packet")
pkt.table("core.trials")
pkt.duckdb().sql("SELECT COUNT(*) FROM core_trials")
```

### Phase 2: Validator

Implement checks for:

- required resources;
- required columns;
- type compatibility;
- primary key uniqueness;
- reference integrity;
- trial interval validity;
- spike chunk validity.

Success criterion:

- Valid fixture passes.
- Deliberately broken fixtures fail with clear errors.

### Phase 3: NWB source importer

Use PyNWB only at the boundary if source is NWB.

Implement extraction for:

- session/subject metadata;
- trials;
- units/spike times;
- electrodes when possible;
- clocks/time basis as best effort.

Success criterion:

- Import one real source into a valid packet.

### Phase 4: Analysis materializations

Implement:

- `analysis.spike_events` from `core.unit_spike_chunks`;
- `analysis.spikes_by_trial`;
- `analysis.trials_wide`.

Success criterion:

- Run a simple PSTH-like query from packet data.

### Phase 5: Dense arrays

Add Zarr array assets for one dense time series such as LFP.

Success criterion:

- `core.array_assets` validates against actual Zarr dtype/shape.
- `pkt.array("...")` opens the array.

### Phase 6: Release/version discipline

Add:

- immutable packet release IDs;
- checksums;
- provenance completeness;
- dependency invalidation for analysis resources.

### Phase 7: Iceberg experiment

Only after the portable profile is useful, implement the same logical schemas as Iceberg tables.

Success criterion:

- same queries work against portable Parquet and Iceberg table resources through the same high-level API.

## Testing strategy

Tests should include:

- schema tests;
- manifest tests;
- validation pass/fail fixtures;
- import golden-data tests;
- round-trip tests for spike chunk -> spike event -> chunk equivalence;
- query tests using DuckDB;
- array asset validation tests.

## Do not overbuild early

Avoid in the first proof-of-principle:

- a custom storage engine;
- a full PyNWB-compatible object model;
- a full NWB exporter;
- distributed compute;
- Iceberg-first design;
- complicated extension registries;
- generalized ontology machinery.

The first goal is simple:

```text
Can I validate, open, query, and analyze my own ecephys data from this packet layout?
```

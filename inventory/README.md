# Source inventories

`05` Stage 1 requires discovery to produce a source inventory before anything is staged:
what source objects exist, what format they are, and which core resources they are
candidates for. Nothing is committed on the strength of an inventory — it is what the
normalization and validation stages are written against.

These are prose inventories of specific datasets. The machine-readable form is
`nwb-lake inspect-source --out source_inventory.json` (`07`), which does not exist yet.

| File | Dataset |
|---|---|
| [`ecephys_776259_2025-04-09.md`](ecephys_776259_2025-04-09.md) | AIND Neuropixels + behaviour, `aind-open-data` |
| [`nwb-zarr-776259-2025-04-09.md`](nwb-zarr-776259-2025-04-09.md) | The same session packaged as ephys + behaviour NWB-Zarr |
| [`nwb-core-schema-comparison.md`](nwb-core-schema-comparison.md) | Core NWB schema versus the core registry |

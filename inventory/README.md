# Source inventories

Part 05 §4.1 requires discovery to produce a source inventory before anything is staged:
what source objects exist, what format they are, and which core resources they are
candidates for. Nothing is committed on the strength of an inventory — it is what the
normalization and validation stages are written against.

These are prose inventories of specific datasets. The machine-readable form is
`escapewheel inspect-source --out source_inventory.json` (Part 07), which does not exist yet.

| File | Dataset |
|---|---|
| [`ecephys_776259_2025-04-09.md`](ecephys_776259_2025-04-09.md) | AIND Neuropixels + behaviour, `aind-open-data` |
| [`nwb-zarr-776259-2025-04-09.md`](nwb-zarr-776259-2025-04-09.md) | The same session packaged as ephys + behaviour NWB-Zarr |
| [`nwb-core-schema-comparison.md`](nwb-core-schema-comparison.md) | Core NWB schema versus the core registry |
| [`nwb-adapter-base-and-dialect.md`](nwb-adapter-base-and-dialect.md) | Each read of the NWB adapter, classified against the schema the file caches |
| [`behavior-video-cameras.md`](behavior-video-cameras.md) | What `rig.json` and `session.json` state about the cameras behind a packet's videos |
| [`probe-shank-axes.md`](probe-shank-axes.md) | What states which way a shank's axes run, across the NWB, `settings.xml` and the sorted asset |

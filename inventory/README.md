# Source inventories

Part 05 §4.1 requires discovery to produce a source inventory before anything is staged:
what source objects exist, what format they are, and which core resources they are
candidates for. Nothing is committed on the strength of an inventory — it is what the
normalization and validation stages are written against.

These are prose inventories of specific datasets and pipelines. For one source on disk,
`escapewheel inspect KIND ROOT` reports the core resources it offers and their row counts.

| File | Dataset |
|---|---|
| [`ecephys_776259_2025-04-09.md`](ecephys_776259_2025-04-09.md) | AIND Neuropixels + behaviour, `aind-open-data` |
| [`nwb-zarr-776259-2025-04-09.md`](nwb-zarr-776259-2025-04-09.md) | The same session packaged as ephys + behaviour NWB-Zarr |
| [`nwb-core-schema-comparison.md`](nwb-core-schema-comparison.md) | Core NWB schema versus the core registry |
| [`nwb-adapter-base-and-dialect.md`](nwb-adapter-base-and-dialect.md) | Each read of the NWB adapter, classified against the schema the file caches |
| [`behavior-video-cameras.md`](behavior-video-cameras.md) | What `rig.json` and `session.json` state about the cameras behind a packet's videos |
| [`probe-shank-axes.md`](probe-shank-axes.md) | What states which way a shank's axes run, across the NWB, `settings.xml` and the sorted asset |
| [`nwb-fidelity-786867.md`](nwb-fidelity-786867.md) | Whether the NWB of `ecephys_786867_2025-09-25_12-43-56` carries its raw asset's measurements faithfully |
| [`vr-foraging-packaging.md`](vr-foraging-packaging.md) | What the VR-foraging packaging pipeline emits, the import surface for most AIND behaviour data |
| [`upstream-defects.md`](upstream-defects.md) | Defects in producing pipelines, each worked around in `escapewheel-writer` |

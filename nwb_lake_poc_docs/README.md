# NWB-Lake POC v0.1 Implementation Kit

This package is a standalone implementation basis for a proof-of-principle ecephys data lake inspired by NWB semantics but not dependent on NWB, HDMF, or PyNWB as runtime storage abstractions.

The project name **NWB-Lake** is a placeholder. The design goal is to test whether neurophysiology data can be represented as a small semantic/logical standard over commodity storage formats:

- **Tables:** Parquet first; Iceberg later when table versioning/cataloging becomes necessary.
- **Dense arrays:** Zarr v3 first.
- **Media:** standard media files such as MP4, with frame timing in tables.
- **Packet catalog:** a JSON manifest that binds resources together.
- **Access:** DuckDB/Polars/PyArrow for tables, Zarr/xarray for arrays, and a small reference Python package over the packet.

The current focus is **not** the NWB compatibility projection. That can come later. The primary implementation focus is:

1. The semantic standard.
2. The logical core schemas.
3. The portable physical profile.
4. Validation-driven import.
5. Optional analysis-layer materializations.

## Design commitments

### 1. Validation is importation

A source object is not "imported" merely because bytes were copied into a packet. Importation means:

1. Source data were discovered.
2. Candidate resources were extracted into staging.
3. Candidate resources were normalized to the logical schemas.
4. Candidate resources passed validation.
5. Validated resources were committed into `core` and recorded in the packet catalog.
6. The import activity and source lineage were recorded as provenance.

Nothing should become `core` data until it has passed the relevant validators.

### 2. Core owns truth

The `core` layer contains canonical normalized facts. Derived products in `analysis` are reproducible from `core` and may be deleted/recomputed. A later `nwb` projection can be built from `core`, but it is not a requirement for the first proof-of-principle.

### 3. Stable IDs, not object paths

Resources and rows reference each other with stable IDs. Do not rely on HDF5 object references, Zarr hierarchy paths, Python object identity, or implicit file layout as the primary identity system.

### 4. Time is integer ticks on declared clocks

Ecephys data should not use floating-point seconds as the sole canonical time representation. Event and interval times use integer ticks plus a `clock_id`. Derived seconds may be provided for convenience.

### 5. Physical profiles are replaceable

The logical schemas should work whether tables are stored as plain Parquet, Iceberg tables, a relational database, or another compatible table system. The first implementation should use the portable Parquet/Zarr profile. Iceberg is a future scale/versioning profile, not a requirement for the first import pipeline.

## Document map

- `00_architecture.md`: Concepts, layers, packet/profile model, and implementation stance.
- `01_semantic_standard.md`: Domain meanings and invariants for ecephys concepts.
- `02_core_logical_schemas.md`: Core table/asset schemas and constraints.
- `03_portable_physical_profile.md`: Parquet/Zarr packet layout and file conventions.
- `04_packet_catalog_manifest.md`: Manifest/catalog fields and examples.
- `05_validation_and_import.md`: Validation-first import pipeline.
- `06_analysis_layer.md`: Optional derived analysis products and lineage rules.
- `07_reference_api_and_implementation_plan.md`: Suggested package/API and phased implementation plan.
- `08_example_packet.md`: Minimal packet layout and example manifest snippets.
- `09_metadata_minimalism_and_extensions.md`: Minimal core metadata requirements, extension policy, and sidecar guidance.

A consolidated single-file version is also provided as `NWB_Lake_POC_v0.1_Implementation_Spec.md`.

## Normative language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, and OPTIONAL are used in the RFC 2119 sense.

## External technology references

These references are not the standard. They are the intended commodity substrates for the first implementation profiles.

- RFC 2119 normative keywords: https://www.rfc-editor.org/info/rfc2119
- Apache Parquet overview: https://parquet.apache.org/docs/overview/
- Apache Arrow documentation: https://arrow.apache.org/docs/
- Zarr v3 core specification: https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html
- Apache Iceberg specification: https://iceberg.apache.org/spec/

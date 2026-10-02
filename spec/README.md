# Escapewheel Portable Data Packet Specification, v0.2

Informational entry point.

## 1. Orientation

This document set describes a proof-of-principle portable data packet: a small semantic and logical
standard over commodity storage formats, whose packet mechanism confines no packet to a recording
modality and whose core vocabulary targets extracellular electrophysiology.
[Part 00 §1](parts/00_architecture.md#ew-architecture-scope) defines its scope, and
[Part 00 §8](parts/00_architecture.md#ew-numbered-part-ownership) assigns the subject and status of
every numbered part.

The design tests whether recorded data can be represented over commodity substrates:
Parquet for tables, Zarr for dense arrays, standard media containers for media, and JSON for the
manifest. **Escapewheel** is a placeholder name. The project does not require an NWB, HDMF, or PyNWB
runtime; Part 00 defines the exact scope and exclusions.

## 2. Authority and conformance

The numbered parts and the machine-readable artifacts they expressly incorporate form the current
authoritative specification candidate. Part 00 defines
[candidate and release status](parts/00_architecture.md#ew-specification-candidate),
[authority by concern](parts/00_architecture.md#ew-authority-by-concern), and
[internal consistency](parts/00_architecture.md#ew-candidate-consistency).

The five conformance actors are summarized in
[Part 00 §2.4](parts/00_architecture.md#ew-specification-actors). Packet and writer conformance are
defined in [Part 05 §10](parts/05_validation_and_import.md#ew-conformance-classes), and verdict
composition in [Part 05 §9.5](parts/05_validation_and_import.md#ew-verdict-composition). Reader
resolution is defined by Parts 03 and 04, and extension independence by Part 09.

## 3. Numbered parts

This table is an informative projection of
[Part 00 §8](parts/00_architecture.md#ew-numbered-part-ownership).

| part | title | status |
|---|---|---|
| 00 | Architecture | normative |
| 01 | Semantic standard | normative |
| 02 | Core logical schemas | normative |
| 03 | Portable physical profile | normative |
| 04 | Packet manifest | normative |
| 05 | Validation, import, and reader operations | normative |
| 06 | Analysis layer | informative except §§2, 4, and 5, which are normative |
| 07 | Reference implementation | informative |
| 08 | Example packet | informative |
| 09 | Metadata minimalism and extensions | normative |
| 10 | Performance notes | informative |
| 11 | Tier 2 rule language | normative |
| 12 | Adapter interface | normative |

A consolidated convenience rendering is provided as
`informative/Escapewheel_POC_v0.2_Implementation_Spec.md`. It is generated from this entry point and
the numbered parts and is not edited separately.

This directory is the specification's tree
([Part 00 §2.1](parts/00_architecture.md#ew-specification-candidate)). The numbered parts are in
`parts/` and the artifacts they incorporate in `artifacts/`. `source/` holds the TOML the core
registry is assembled from, `informative/` the rendered table listing, the combined rendering and
the example documents, and `tools/` the tools that generate and check the tree, with the environment
they run in.

## 4. Packet-recorded identifiers

This table is an informative projection of the identifier-owning parts. The v0.2 specification
candidate is versioned independently of the identifiers a packet records.

| field | value | owner |
|---|---|---|
| `profile_id` | `escapewheel-portable-v0.1` | [Part 03 §1](parts/03_portable_physical_profile.md#ew-portable-profile-scope) |
| `semantic_standard_version` | `escapewheel-semantic-v0.1` | [Part 01 §1](parts/01_semantic_standard.md#ew-semantic-standard-scope) |
| `logical_standard_version` | `escapewheel-logical-v0.1` | [Part 02 §1](parts/02_core_logical_schemas.md#ew-core-logical-schema-scope) |
| `registry_id` | `core` | [Part 02 §9.2](parts/02_core_logical_schemas.md#ew-registry-self-description), core registry only |
| `registry_version` | `0.17.0` | [Part 02 §9.2](parts/02_core_logical_schemas.md#ew-registry-self-description), core registry only |

Part 02 §9.2 defines registry self-description and compatibility. A manifest records the core
registry's `registry_id` and `registry_version` as the member name and `version` of its descriptor
in `registries` (Part 04 §8). Current development packets use core registry `0.17.0` and are
regenerated rather than treated as compatible with the earlier development shape. Each extension registry carries and advances its own `registry_version` under
the generic mechanism in Part 09; the core specification does not assign extension versions.
Part 04 §§3 and 8 define the manifest fields that record these identifiers.

## 5. Informative references

- [Apache Iceberg table specification](https://iceberg.apache.org/spec/), for the deferred
  lakehouse profile discussed in Part 00.

[Part 00 §9](parts/00_architecture.md#ew-normative-references) defines normative-reference policy and
lists shared external authorities, among them RFC 1952, which the portable profile and the packet
manifest both invoke, and Parquet, which the portable profile and its adapter interface both invoke.
The Arrow authorities invoked by the adapter interface are in
[Part 12 §11](parts/12_adapter_interface.md#ew-adapter-interface-normative-references). The other
references invoked only by the portable profile are in
[Part 03 §12](parts/03_portable_physical_profile.md#ew-portable-profile-normative-references), and the
SHA-256, CRC64NVME, and CRC32C authorities invoked by the packet manifest are in
[Part 04 §11](parts/04_packet_catalog.md#ew-packet-catalog-normative-references).
The SQL and IEEE authorities invoked by the portable Tier 2 language are in
[Part 11 §9](parts/11_tier_2_rule_language.md#ew-rule-language-normative-references).
The UCUM, NCBI Taxonomy, MGI, and RGD authorities invoked by logical registry declarations are in
[Part 02 §13](parts/02_core_logical_schemas.md#ew-logical-schema-normative-references).

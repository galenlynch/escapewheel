# Escapewheel Portable Data Packet Specification, v0.2

Informational entry point.

## 1. Orientation

This document set describes a proof-of-principle portable representation of extracellular
electrophysiology data as a small semantic and logical standard over commodity storage formats.
[Part 00 §1](00_architecture.md#ew-architecture-scope) defines its scope, and
[Part 00 §9](00_architecture.md#ew-numbered-part-ownership) assigns the subject and status of
every numbered part.

The design tests whether neurophysiology data can be represented over commodity substrates:
Parquet for tables, Zarr for dense arrays, standard media containers for media, and JSON for the
manifest. **Escapewheel** is a placeholder name. The project does not require an NWB, HDMF, or PyNWB
runtime; Part 00 defines the exact scope and exclusions.

## 2. Authority and conformance

The numbered parts and the machine-readable artifacts they expressly incorporate form the current
authoritative specification candidate. Part 00 defines
[candidate and release status](00_architecture.md#ew-specification-candidate),
[authority by concern](00_architecture.md#ew-authority-by-concern), and
[internal consistency](00_architecture.md#ew-candidate-consistency).

The four conformance actors are summarized in
[Part 00 §2.4](00_architecture.md#ew-specification-actors). Packet and writer conformance are
defined in [Part 05 §10](05_validation_and_import.md#ew-conformance-classes), and verdict
composition in [Part 05 §9.5](05_validation_and_import.md#ew-verdict-composition). Reader
resolution is defined by Parts 03 and 04, and extension independence by Part 09.

## 3. Numbered parts

This table is an informative projection of
[Part 00 §9](00_architecture.md#ew-numbered-part-ownership).

| part | title | status |
|---|---|---|
| 00 | Architecture | normative |
| 01 | Semantic standard | normative |
| 02 | Core logical schemas | normative |
| 03 | Portable physical profile | normative |
| 04 | Packet manifest | normative |
| 05 | Validation, import, and reader operations | normative |
| 06 | Analysis layer | informative except §§2 and 5, which are normative |
| 07 | Reference implementation and plan | informative |
| 08 | Example packet | informative |
| 09 | Metadata minimalism and extensions | normative |
| 10 | Performance notes | informative |
| 11 | Tier 2 rule language | normative |

A consolidated convenience rendering is provided as
`Escapewheel_POC_v0.2_Implementation_Spec.md`. It is generated from this entry point and the
numbered parts and is not edited separately.

## 4. Packet-recorded identifiers

This table is an informative projection of the identifier-owning parts. The v0.2 specification
candidate is versioned independently of the identifiers a packet records.

| field | value | owner |
|---|---|---|
| `profile_id` | `escapewheel-portable-v0.1` | [Part 03 §1](03_portable_physical_profile.md#ew-portable-profile-scope) |
| `semantic_standard_version` | `escapewheel-semantic-v0.1` | [Part 01 §1](01_semantic_standard.md#ew-semantic-standard-scope) |
| `logical_standard_version` | `escapewheel-logical-v0.1` | [Part 02 §1](02_core_logical_schemas.md#ew-core-logical-schema-scope) |
| `registry_id` | `core` | [Part 02 §9.2](02_core_logical_schemas.md#ew-registry-self-description), core registry only |
| `registry_version` | `0.6.0` | [Part 02 §9.2](02_core_logical_schemas.md#ew-registry-self-description), core registry only |

Part 02 §9.2 defines registry self-description and compatibility. A manifest records the core
registry's `registry_id` and `registry_version` as the member name and `version` of its descriptor
in `registries` (Part 04 §8). Current development packets use core registry `0.6.0` and are
regenerated rather than treated as compatible with the earlier development shape. Each extension registry carries and advances its own `registry_version` under
the generic mechanism in Part 09; the core specification does not assign extension versions.
Part 04 §§3 and 8 define the manifest fields that record these identifiers.

## 5. Informative references

- [Apache Iceberg table specification](https://iceberg.apache.org/spec/), for the deferred
  lakehouse profile discussed in Part 00.

[Part 00 §10](00_architecture.md#ew-normative-references) defines normative-reference policy and
lists shared external authorities, among them RFC 1952, which the portable profile and the packet
manifest both invoke. References invoked only by the portable profile are in
[Part 03 §12](03_portable_physical_profile.md#ew-portable-profile-normative-references), and the
SHA-256, CRC64NVME, and CRC32C authorities invoked by the packet manifest are in
[Part 04 §11](04_packet_catalog.md#ew-packet-catalog-normative-references).
The SQL and IEEE authorities invoked by the portable Tier 2 language are in
[Part 11 §9](11_tier_2_rule_language.md#ew-rule-language-normative-references).
The UCUM and URI authorities invoked by logical registry declarations are in
[Part 02 §13](02_core_logical_schemas.md#ew-logical-schema-normative-references).

# Escapewheel Portable Data Packet Specification, v0.2

## Status of this document

This document set specifies the Escapewheel v0.2 proof-of-principle data packet. The generated v0.2
parts and the machine-readable artifacts they incorporate state the current contract.

The specification is versioned independently of the identifiers a packet records. See §5.

## 1. Scope

### 1.1 Purpose

This specification defines a portable representation of extracellular electrophysiology data as a small semantic and logical standard over commodity storage formats. It defines:

- a semantic standard: the meaning of the concepts represented (Part 01);
- a logical standard: those concepts as computable resources (Part 02);
- a physical profile: how those resources are stored (Part 03);
- a packet catalog binding the resources of one bundle (Part 04);
- a validation-first import procedure (Part 05).

### 1.2 Out of scope

This specification does not define a storage engine, an object model compatible with PyNWB, an NWB exporter, a distributed compute model, or ontology machinery. It has no runtime dependency on NWB, HDMF, or PyNWB.

A compatibility projection into NWB is deferred and is not required for conformance.

### 1.3 Applicability

The design goal is to test whether neurophysiology data can be represented over commodity substrates: Parquet for tables, Zarr for dense arrays, standard media containers for media, and JSON for the catalog. **Escapewheel** is a placeholder name.

## 2. Conformance

### 2.1 Conformance targets

Requirements in this specification apply to four classes of implementation. Each requirement states or implies which.

| target | definition |
|---|---|
| **writer** | produces a packet from source data |
| **reader** | opens a packet and resolves its resources |
| **validator** | decides whether a packet conforms |
| **consumer** | interprets values a reader returns |

### 2.2 Conforming packet

A packet conforms to this specification when it declares a profile defined here, carries every resource that profile requires, satisfies every structural requirement of Part 02, and produces no error-level finding from the checks of Part 05.

A conforming packet MAY omit any resource this specification does not require. A validator MUST NOT reject a packet for carrying a resource this specification does not define.

### 2.3 Conforming reader

A conforming reader resolves a packet's resources through its catalog rather than through file layout, checks a resource's declared codecs before opening it, and fails naming what it lacks rather than silently returning partial data.

A reader MUST NOT require an extension schema in order to read core resources (Part 09).

### 2.4 Extension

An extension is a registry document in the format of Part 02, in its own namespace. Core resources never reference an extension's. A validator MUST NOT require an extension's schema in order to validate core, and MUST NOT fail an import because optional extension metadata is absent.

## 3. Normative language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in RFC 2119.

Requirements are stated in clauses numbered within each part. A citation such as `Part 03 §5.4`
refers to clause 5.4 of Part 03.

## 4. Document organization

This specification is published as eleven parts. Parts 00 to 05 and 09 are normative. Parts 06 to 08 are informative except where a clause states otherwise.

| part | title | status |
|---|---|---|
| 00 | Architecture | normative |
| 01 | Semantic standard | normative |
| 02 | Core logical schemas | normative |
| 03 | Portable physical profile | normative |
| 04 | Packet catalog | normative |
| 05 | Validation and import | normative |
| 06 | Analysis layer | informative |
| 07 | Reference API and implementation plan | informative |
| 08 | Example packet | informative |
| 09 | Metadata minimalism and extensions | normative |

A consolidated single-file rendering is provided as `Escapewheel_POC_v0.2_Implementation_Spec.md`.

## 5. Version identifiers

### 5.1 Identifiers a packet records

This document set is v0.2. The **identifier strings** a packet records are unchanged by it:

| field | value |
|---|---|
| `profile_id` | `escapewheel-portable-v0.1` |
| `semantic_standard_version` | `escapewheel-semantic-v0.1` |
| `logical_standard_version` | `escapewheel-logical-v0.1` |
| `registry_version` | `0.2.0` |

A packet built against an earlier schema does **not** remain conforming merely because the semantic,
logical, and profile identifiers are unchanged. Those identifiers state which standards a packet
uses; they do not guarantee that an older physical shape validates against the current registry.

A packet remains conforming across v0.1 and v0.2 only where it was rebuilt against the current registry. Migration is regeneration: every packet is reproducible from its sources through the recipe recorded in `core.processing_runs.parameters`, so a conversion tool would be a second implementation of the writer that ran once.

### 5.2 Recording the registry version

Part 02 §9.2 defines registry self-description and the exact current registry and meta-schema
identities. Current development packets use core registry `0.2.0` and are regenerated rather than
treated as compatible with the earlier development shape.

## 6. Normative references

- RFC 2119, *Key words for use in RFCs to Indicate Requirement Levels*. https://www.rfc-editor.org/info/rfc2119
- Zarr v3 core specification. https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html
- Apache Parquet format. https://parquet.apache.org/docs/
- Apache Arrow columnar format. https://arrow.apache.org/docs/format/Columnar.html

## 7. Informative references

- Apache Iceberg table specification. https://iceberg.apache.org/spec/
- Zarr v2 specification, referenced only where a packet points at externally written v2 arrays (03 §6.4).

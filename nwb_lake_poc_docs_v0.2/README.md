# NWB-Lake Portable Data Packet Specification, v0.2

## Status of this document

This document set specifies the NWB-Lake proof-of-principle data packet. It is v0.1 with revisions R1–R41 and R43–R70 applied. R42 was withdrawn.

The revision documents in `revisions/` remain the record of why each requirement holds. This specification states only what holds. A requirement introduced or changed by a revision cites it as `(R<N> §<clause>)`; an uncited requirement is unchanged from v0.1.

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

The design goal is to test whether neurophysiology data can be represented over commodity substrates: Parquet for tables, Zarr for dense arrays, standard media containers for media, and JSON for the catalog. **NWB-Lake** is a placeholder name.

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

A conforming reader resolves a packet's resources through its catalog rather than through file layout, checks a resource's declared codecs before opening it, and fails naming what it lacks rather than silently returning partial data (R15 §2).

A reader MUST NOT require an extension schema in order to read core resources (Part 09).

### 2.4 Extension

An extension is a registry document in the format of Part 02, in its own namespace (R17 §2). Core resources never reference an extension's. A validator MUST NOT require an extension's schema in order to validate core, and MUST NOT fail an import because optional extension metadata is absent.

## 3. Normative language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL are to be interpreted as described in RFC 2119.

Requirements are stated in clauses numbered within each part. A citation of the form `03 §4.2` refers to clause 4.2 of Part 03. A citation of the form `(R53 §2)` refers to a revision document and is provenance, not a requirement.

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

A consolidated single-file rendering is provided as `NWB_Lake_POC_v0.2_Implementation_Spec.md`.

## 5. Version identifiers

### 5.1 Identifiers a packet records

This document set is v0.2. The identifiers a packet records are unchanged by it, and a packet written against v0.1 remains conforming:

| field | value |
|---|---|
| `profile_id` | `nwb-lake-portable-v0.1` |
| `semantic_standard_version` | `nwb-lake-semantic-v0.1` |
| `logical_standard_version` | `nwb-lake-logical-v0.1` |
| `registry_version` | `0.1.0` |

### 5.2 Recording the registry version

A packet MUST record the registry version it was written against, and SHOULD embed that registry so the packet is self-describing (R2 §8). A packet whose embedded registry disagrees with its recorded version is invalid.

`registry_version` states **compatibility**, and follows semantic versioning: a removed, renamed or retyped column is a major change; an added nullable column is a minor one; a corrected description is a patch.

It is **deliberately held at `0.1.0` while the schema iterates**, so amendments that would otherwise have incremented it — several of them major — have not. A consumer MUST therefore treat the embedded registry as authoritative and MUST NOT use `registry_version` alone to decide compatibility until the hold is lifted. Lifting it is a decision about the schema's stability, not a defect to be fixed.

## 6. Normative references

- RFC 2119, *Key words for use in RFCs to Indicate Requirement Levels*. https://www.rfc-editor.org/info/rfc2119
- Zarr v3 core specification. https://zarr-specs.readthedocs.io/en/latest/v3/core/index.html
- Apache Parquet format. https://parquet.apache.org/docs/
- Apache Arrow columnar format. https://arrow.apache.org/docs/format/Columnar.html

## 7. Informative references

- Apache Iceberg table specification. https://iceberg.apache.org/spec/
- Zarr v2 specification, referenced only where a packet points at externally written v2 arrays (03 §6.4).

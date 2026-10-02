"""What the framework checker expects the specification to state.

Each value restates a decision a numbered part owns, so a part and this module change together.
"""

#: The numbered parts Part 00's ownership table names.
EXPECTED_PARTS = {f"{number:02d}" for number in range(13)}

#: Each packet-recorded identifier's value, owning part, and the anchor of its owning section.
IDENTIFIERS = {
    "profile_id": (
        "escapewheel-portable-v0.1",
        "03",
        "ew-portable-profile-scope",
    ),
    "semantic_standard_version": (
        "escapewheel-semantic-v0.1",
        "01",
        "ew-semantic-standard-scope",
    ),
    "logical_standard_version": (
        "escapewheel-logical-v0.1",
        "02",
        "ew-core-logical-schema-scope",
    ),
    "registry_id": ("core", "02", "ew-registry-self-description"),
    "registry_version": ("0.15.0", "02", "ew-registry-self-description"),
}

#: Text found in the normative-reference entry of each external authority.
REFERENCE_MARKERS = {
    "BCP 14": "https://www.rfc-editor.org/info/bcp14",
    "RFC 8259": "https://www.rfc-editor.org/info/rfc8259",
    "RFC 3986": "https://www.rfc-editor.org/info/rfc3986",
    "JSON Schema Core": "json-schema.org/draft/2020-12/json-schema-core",
    "JSON Schema Validation": "json-schema.org/draft/2020-12/json-schema-validation",
    "Parquet": "[Apache Parquet format](https://github.com/apache/parquet-format)",
    "Parquet logical types": "LogicalTypes.md",
    "Arrow columnar": "arrow.apache.org/docs/format/Columnar.html",
    "Arrow IPC": "#serialization-and-interprocess-communication-ipc",
    "Arrow Flight": "arrow.apache.org/docs/format/Flight.html",
    "Zarr v3 core": "zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html",
    "Zarr data types": "zarr-specs.readthedocs.io/en/latest/v3/data-types/",
    "Zarr regular chunk grid": "zarr-specs.readthedocs.io/en/latest/v3/chunk-grids/regular-grid/",
    "Zarr default chunk keys": "zarr-specs.readthedocs.io/en/latest/v3/chunk-key-encodings/default/",
    "Zarr Bytes": "zarr-specs.readthedocs.io/en/latest/v3/codecs/bytes/",
    "Zarr Gzip": "zarr-specs.readthedocs.io/en/latest/v3/codecs/gzip/",
    "Zarr Blosc": "zarr-specs.readthedocs.io/en/latest/v3/codecs/blosc/",
    "Zarr CRC32C": "zarr-specs.readthedocs.io/en/latest/v3/codecs/crc32c/",
    "Zarr transpose": "zarr-specs.readthedocs.io/en/latest/v3/codecs/transpose/",
    "Zarr sharding": "zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/",
    "Zarr Zstandard": "zarr-specs.readthedocs.io/en/latest/v3/codecs/zstd/",
    "Zarr v2": "zarr-specs.readthedocs.io/en/latest/v2/v2.0.html",
    "RFC 8878": "https://www.rfc-editor.org/info/rfc8878",
    "RFC 1952": "https://www.rfc-editor.org/info/rfc1952",
    "RFC 1951": "https://www.rfc-editor.org/info/rfc1951",
    "FIPS 180-4": "csrc.nist.gov/pubs/fips/180-4",
    "NVM Command Set": "NVM Express NVM Command Set Specification, Revision 1.2",
    "RFC 9260": "https://www.rfc-editor.org/info/rfc9260",
    "RFC 8785": "https://www.rfc-editor.org/info/rfc8785",
    "Unicode 15.0.0": "https://www.unicode.org/versions/Unicode15.0.0/",
    "ISO/IEC 9075-1:2023": "https://www.iso.org/standard/76583.html",
    "ISO/IEC 9075-1:2023/Cor 1:2026": "https://www.iso.org/standard/93690.html",
    "ISO/IEC 9075-2:2023": "https://www.iso.org/standard/76584.html",
    "ISO/IEC 9075-2:2023/Cor 1:2026": "https://www.iso.org/standard/93691.html",
    "IEEE 754-2019": "https://standards.ieee.org/ieee/754/6210/",
    "UCUM": "https://ucum.org/ucum",
    "NCBI Taxonomy": "https://www.ncbi.nlm.nih.gov/taxonomy",
    "MGI": "https://www.informatics.jax.org/",
    "RGD": "https://rgd.mcw.edu/",
    "IANA Media Types": "https://www.iana.org/assignments/media-types/",
}

#: The one part whose normative-reference section holds each authority.
REFERENCE_OWNERS = {
    "BCP 14": "00",
    "RFC 8259": "00",
    "RFC 3986": "00",
    "JSON Schema Core": "00",
    "JSON Schema Validation": "00",
    "Parquet": "00",
    "Parquet logical types": "00",
    "Arrow columnar": "12",
    "Arrow IPC": "12",
    "Arrow Flight": "12",
    "Zarr v3 core": "03",
    "Zarr data types": "03",
    "Zarr regular chunk grid": "03",
    "Zarr default chunk keys": "03",
    "Zarr Bytes": "03",
    "Zarr Gzip": "03",
    "Zarr Blosc": "03",
    "Zarr CRC32C": "03",
    "Zarr transpose": "03",
    "Zarr sharding": "03",
    "Zarr Zstandard": "03",
    "Zarr v2": "03",
    "RFC 8878": "03",
    "RFC 1952": "00",
    "RFC 1951": "03",
    "FIPS 180-4": "04",
    "NVM Command Set": "04",
    "RFC 9260": "04",
    "RFC 8785": "04",
    "Unicode 15.0.0": "05",
    "ISO/IEC 9075-1:2023": "11",
    "ISO/IEC 9075-1:2023/Cor 1:2026": "11",
    "ISO/IEC 9075-2:2023": "11",
    "ISO/IEC 9075-2:2023/Cor 1:2026": "11",
    "IEEE 754-2019": "11",
    "UCUM": "02",
    "NCBI Taxonomy": "02",
    "MGI": "02",
    "RGD": "02",
    "IANA Media Types": "02",
}

#: The anchor of each part's normative-reference section that has approved rows.
REFERENCE_ANCHORS = {
    "00": "ew-normative-references",
    "02": "ew-logical-schema-normative-references",
    "03": "ew-portable-profile-normative-references",
    "04": "ew-packet-catalog-normative-references",
    "11": "ew-rule-language-normative-references",
    "12": "ew-adapter-interface-normative-references",
}

#: The approved rows of each part's normative-reference table, in order.
REFERENCE_ROWS = {
    "00": (
        (
            "[BCP 14](https://www.rfc-editor.org/info/bcp14), comprising RFC 2119 and RFC 8174",
            "exact RFC editions",
            "normative keywords",
        ),
        (
            "[RFC 8259](https://www.rfc-editor.org/info/rfc8259)",
            "exact",
            "JSON",
        ),
        (
            "[RFC 3986](https://www.rfc-editor.org/info/rfc3986)",
            "exact",
            "URI syntax",
        ),
        (
            "[JSON Schema Core](https://json-schema.org/draft/2020-12/json-schema-core) and [Validation](https://json-schema.org/draft/2020-12/json-schema-validation)",
            "Draft 2020-12",
            "incorporated JSON Schemas",
        ),
        (
            "[RFC 1952](https://www.rfc-editor.org/info/rfc1952)",
            "exact",
            "gzip member format of a bound registry (Part 03 §3.3) and CRC-32 (Part 04 §4.3)",
        ),
        (
            "[Apache Parquet format](https://github.com/apache/parquet-format), including [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md)",
            "unversioned",
            "Parquet files and logical types of stored tables (Part 03 §5) and of `files-v0.1` deliveries (Part 12 §3)",
        ),
    ),
    "02": (
        (
            "[The Unified Code for Units of Measure](https://ucum.org/ucum)",
            "version 2.2, revision date 2024-06-17",
            "unit codes (§8.4) and the spelling of values in open columns naming it (§9.3)",
        ),
        (
            "[NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/taxonomy)",
            "living registry",
            "the spelling of the names it registers, in open columns naming it (§9.3)",
        ),
        (
            "[Mouse Genome Informatics (MGI)](https://www.informatics.jax.org/)",
            "living registry",
            "the spelling of the names it registers, in open columns naming it (§9.3)",
        ),
        (
            "[Rat Genome Database (RGD)](https://rgd.mcw.edu/)",
            "living registry",
            "the spelling of the names it registers, in open columns naming it (§9.3)",
        ),
        (
            "[IANA Media Types](https://www.iana.org/assignments/media-types/)",
            "living registry",
            "the spelling of the names it registers, in open columns naming it (§9.3)",
        ),
    ),
    "03": (
        (
            "[Zarr v3 core](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html), "
            "[data types](https://zarr-specs.readthedocs.io/en/latest/v3/data-types/index.html), "
            "[regular chunk grid](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-grids/regular-grid/index.html), "
            "and "
            "[default chunk-key encoding](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-key-encodings/default/index.html)",
            "core v3.0; other entries unversioned",
            "Zarr v3 arrays",
        ),
        (
            "Zarr v3 [Bytes](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/bytes/), "
            "[Gzip](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/gzip/), "
            "[Blosc](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/blosc/), "
            "[CRC32C](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/crc32c/), "
            "[transpose](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/transpose/), and "
            "[sharding-indexed](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/) "
            "codec specifications",
            "unversioned",
            "permitted Zarr v3 codec pipeline components",
        ),
        (
            "[Zarr v3 Zstandard codec specification](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/zstd/)",
            "unversioned",
            "`zstd` codec metadata object and configuration",
        ),
        (
            "[Zarr v2 storage specification](https://zarr-specs.readthedocs.io/en/latest/v2/v2.0.html)",
            "2.0",
            "permitted external Zarr v2 arrays",
        ),
        (
            "[RFC 8878](https://www.rfc-editor.org/info/rfc8878)",
            "exact",
            "Zstandard framing",
        ),
        (
            "[RFC 1951](https://www.rfc-editor.org/info/rfc1951)",
            "exact",
            "DEFLATE compression of a bound registry (§3.3)",
        ),
    ),
    "04": (
        (
            "[NIST FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)",
            "exact",
            "SHA-256",
        ),
        (
            "[NVM Express NVM Command Set Specification, Revision 1.2](https://nvmexpress.org/specifications/)",
            "exact",
            "CRC64NVME (§5.3.1.3)",
        ),
        (
            "[RFC 9260](https://www.rfc-editor.org/info/rfc9260)",
            "exact",
            "CRC32C (Appendix A)",
        ),
        (
            "[RFC 8785](https://www.rfc-editor.org/info/rfc8785)",
            "exact",
            "the serialization of a prefix listing's keys (§4.3), Section 3.2.2.2",
        ),
    ),
    "11": (
        (
            "[ISO/IEC 9075-1:2023](https://www.iso.org/standard/76583.html)",
            "exact",
            "SQL framework, terminology, and feature identification",
        ),
        (
            "[ISO/IEC 9075-1:2023/Cor 1:2026](https://www.iso.org/standard/93690.html)",
            "exact",
            "corrections to the SQL framework edition",
        ),
        (
            "[ISO/IEC 9075-2:2023](https://www.iso.org/standard/76584.html)",
            "exact",
            "SQL/Foundation grammar and semantics selected by the profile",
        ),
        (
            "[ISO/IEC 9075-2:2023/Cor 1:2026](https://www.iso.org/standard/93691.html)",
            "exact",
            "corrections to the SQL/Foundation edition",
        ),
        (
            "[IEEE 754-2019](https://standards.ieee.org/ieee/754/6210/)",
            "exact",
            "binary32, binary64, rounding, exceptional values, and approximate arithmetic",
        ),
    ),
    "12": (
        (
            "[Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html), "
            "[IPC](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc), "  # noqa: E501
            "and "
            "[Flight](https://arrow.apache.org/docs/format/Flight.html)",
            "unversioned",
            "Arrow data, IPC, and Flight",
        ),
    ),
}

#: Prose by which each part invokes the authorities it relies on.
REFERENCE_INVOCATIONS = {
    "00": "Normative prose invokes an external authority **directly**",
    "03": "Its requirements directly invoke the shared JSON, URI, JSON Schema, Parquet, and RFC 1952",
    "04": "Its requirements directly invoke the shared JSON, URI, JSON Schema, and RFC 1952",
    "11": "SQL/Foundation editions, corrigenda, and IEEE floating-point edition identified in §9",
    "12": "Its requirements directly invoke the shared JSON, URI, JSON Schema, and Parquet",
}

#: Implementations, which no normative-reference section may name as an authority.
IMPLEMENTATIONS = ("DuckDB", "zarr-python", "Numcodecs")

#: How the informative entry point opens.
README_OPENING = "# Escapewheel Portable Data Packet Specification, v0.2\n\nInformational entry point."

#: Phrases of Part 00's candidate framework.
CANDIDATE_PHRASES = (
    "current generated v0.2 numbered parts",
    "every artifact that a numbered part expressly",
    "specification candidate",
    "specification release",
)

"""Check the specification framework and its informative projections.

Part 00 owns artifact roles, numbered-part subjects and statuses, identifier ownership, and the
normative-reference policy. Subject-owning parts own their local bibliographies. This checker verifies the representations that can be compared
mechanically, including that Part 02 §13 links every authority an open column of the core registry
names. It does not decide whether prose is well placed or semantically complete.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

import combine

HERE = Path(__file__).resolve().parent
CORE_REGISTRY = HERE.parent / "registry" / "logical_schemas.json"

PARTS = {path.name[:2]: path.name for path in sorted(HERE.glob("[0-9][0-9]_*.md"))}
EXPECTED_PARTS = {f"{number:02d}" for number in range(12)}

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
    "registry_version": ("0.7.0", "02", "ew-registry-self-description"),
}

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
    "ISO/IEC 9075-1:2023": "https://www.iso.org/standard/76583.html",
    "ISO/IEC 9075-1:2023/Cor 1:2026": "https://www.iso.org/standard/93690.html",
    "ISO/IEC 9075-2:2023": "https://www.iso.org/standard/76584.html",
    "ISO/IEC 9075-2:2023/Cor 1:2026": "https://www.iso.org/standard/93691.html",
    "IEEE 754-2019": "https://standards.ieee.org/ieee/754/6210/",
    "UCUM": "https://ucum.org/ucum",
    "NCBI Taxonomy": "https://www.ncbi.nlm.nih.gov/taxonomy",
    "MGI": "https://www.informatics.jax.org/",
    "RGD": "https://rgd.mcw.edu/",
}

REFERENCE_OWNERS = {
    "BCP 14": "00",
    "RFC 8259": "00",
    "RFC 3986": "00",
    "JSON Schema Core": "00",
    "JSON Schema Validation": "00",
    "Parquet": "03",
    "Parquet logical types": "03",
    "Arrow columnar": "03",
    "Arrow IPC": "03",
    "Arrow Flight": "03",
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
    "ISO/IEC 9075-1:2023": "11",
    "ISO/IEC 9075-1:2023/Cor 1:2026": "11",
    "ISO/IEC 9075-2:2023": "11",
    "ISO/IEC 9075-2:2023/Cor 1:2026": "11",
    "IEEE 754-2019": "11",
    "UCUM": "02",
    "NCBI Taxonomy": "02",
    "MGI": "02",
    "RGD": "02",
}

REFERENCE_ANCHORS = {
    "00": "ew-normative-references",
    "02": "ew-logical-schema-normative-references",
    "03": "ew-portable-profile-normative-references",
    "04": "ew-packet-catalog-normative-references",
    "11": "ew-rule-language-normative-references",
}

REFERENCE_SECTION_ANCHOR = re.compile(r'id="(ew-[a-z-]*normative-references)"')
LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")

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
    ),
    "03": (
        (
            "[Apache Parquet format](https://github.com/apache/parquet-format), including [logical types](https://github.com/apache/parquet-format/blob/master/LogicalTypes.md)",
            "unversioned",
            "Parquet files and logical types",
        ),
        (
            "[Apache Arrow columnar format](https://arrow.apache.org/docs/format/Columnar.html), [IPC](https://arrow.apache.org/docs/format/Columnar.html#serialization-and-interprocess-communication-ipc), and [Flight](https://arrow.apache.org/docs/format/Flight.html)",
            "unversioned",
            "Arrow data, IPC, and Flight",
        ),
        (
            "[Zarr v3 core](https://zarr-specs.readthedocs.io/en/latest/v3/core/v3.0.html), [data types](https://zarr-specs.readthedocs.io/en/latest/v3/data-types/index.html), [regular chunk grid](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-grids/regular-grid/index.html), and [default chunk-key encoding](https://zarr-specs.readthedocs.io/en/latest/v3/chunk-key-encodings/default/index.html)",
            "core v3.0; other entries unversioned",
            "Zarr v3 arrays",
        ),
        (
            "Zarr v3 [Bytes](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/bytes/), [Gzip](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/gzip/), [Blosc](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/blosc/), [CRC32C](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/crc32c/), [transpose](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/transpose/), and [sharding-indexed](https://zarr-specs.readthedocs.io/en/latest/v3/codecs/sharding-indexed/) codec specifications",
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
}

REFERENCE_INVOCATIONS = {
    "00": "Normative prose invokes an external authority **directly**",
    "03": "Its requirements directly invoke the shared JSON, URI, and RFC 1952",
    "04": "Its requirements directly invoke the shared JSON, URI, JSON Schema, and RFC 1952",
    "11": "SQL/Foundation editions, corrigenda, and IEEE floating-point edition identified in §9",
}

NORMATIVE_KEYWORD = re.compile(
    r"\b(?:MUST|REQUIRED|SHALL|SHOULD|RECOMMENDED|MAY|OPTIONAL)\b"
)


def _documents(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Read framework inputs, replacing named files with optional mutation text."""
    names = {
        "README.md",
        "Escapewheel_POC_v0.2_Implementation_Spec.md",
        *PARTS.values(),
    }
    documents = {
        name: (HERE / name).read_text() if (HERE / name).is_file() else ""
        for name in names
    }
    if overrides:
        documents.update(overrides)
    return documents


def _table_after(
    text: str, marker: str, header: tuple[str, ...]
) -> list[tuple[str, ...]]:
    """Return rows of the first Markdown table with ``header`` following ``marker``."""
    start = text.find(marker)
    if start < 0:
        return []
    lines = text[start:].splitlines()
    wanted = tuple(cell.strip() for cell in header)
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if cells != wanted:
            continue
        rows = []
        for row in lines[index + 2 :]:
            if not row.startswith("|"):
                break
            values = tuple(cell.strip() for cell in row.strip().strip("|").split("|"))
            if len(values) == len(header):
                rows.append(values)
        return rows
    return []


def _anchored_section(text: str, anchor: str) -> str:
    """Return one top-level numbered section selected by its canonical anchor."""
    start = text.find(f'id="{anchor}"')
    if start < 0:
        return ""
    heading = text.find("\n## ", start)
    if heading < 0:
        return ""
    end = text.find("\n## ", heading + 4)
    return text[start:] if end < 0 else text[start:end]


def _status(value: str) -> tuple[str, tuple[str, ...]]:
    """Normalize a local or tabular status to its class and mixed-section exceptions."""
    lowered = value.lower().strip().rstrip(".")
    if lowered.startswith("normative"):
        return ("normative", ())
    if not lowered.startswith("informative"):
        return ("unknown", ())
    if "except" not in lowered:
        return ("informative", ())
    exceptions = tuple(re.findall(r"\d+(?:\.\d+)?", lowered.split("except", 1)[1]))
    return ("mixed", exceptions)


def _local_status(text: str) -> str:
    """Return the first non-empty line after a part's title."""
    lines = text.splitlines()
    for line in lines[1:]:
        if line.strip():
            return line.strip()
    return ""


def _part_title(text: str) -> str:
    """Return the title following the em dash in a numbered part's H1."""
    first = text.splitlines()[0] if text else ""
    return first.split("—", 1)[1].strip() if "—" in first else ""


def _open_authorities(registry: Mapping) -> list[tuple[str, str]]:
    """Return each (column, URI) naming an authority on an open column of a registry document."""
    return [
        (f"{resource_id}.{column['name']}", entry["uri"])
        for resource_id, resource in registry.get("resources", {}).items()
        for column in resource.get("table", {}).get("columns", [])
        if column.get("vocabulary") == "open"
        for entry in column.get("authority", [])
    ]


def _render(documents: Mapping[str, str]) -> str:
    """Render the combined document from possibly mutated source documents."""
    blocks = [combine.HEADER]
    for name in combine.ORDER:
        body = documents[name].rstrip("\n")
        blocks.append(f"<!-- BEGIN {name} -->\n\n{body}\n\n<!-- END {name} -->\n")
    return "\n".join(blocks)


def defects(
    overrides: Mapping[str, str] | None = None, registry: Mapping | None = None
) -> list[str]:
    """Return each mechanically observable framework disagreement.

    ``registry`` replaces the core registry document read from ``CORE_REGISTRY``.
    """
    documents = _documents(overrides)
    if registry is None:
        registry = json.loads(CORE_REGISTRY.read_text())
    found: list[str] = []
    architecture = documents[PARTS["00"]]
    readme = documents["README.md"]

    owner_rows = _table_after(
        architecture,
        'id="ew-numbered-part-ownership"',
        ("part", "subject", "status"),
    )
    owner_parts = [row[0] for row in owner_rows]
    missing = sorted(EXPECTED_PARTS - set(owner_parts))
    unknown = sorted(set(owner_parts) - EXPECTED_PARTS)
    duplicate = sorted({part for part in owner_parts if owner_parts.count(part) > 1})
    if missing:
        found.append("Part 00 part table missing: " + ", ".join(missing))
    if unknown:
        found.append("Part 00 part table has unknown: " + ", ".join(unknown))
    if duplicate:
        found.append("Part 00 part table duplicates: " + ", ".join(duplicate))

    owner_status = {row[0]: row[2] for row in owner_rows if row[0] in EXPECTED_PARTS}
    for number, name in PARTS.items():
        expected = owner_status.get(number)
        if expected is None:
            continue
        local = _local_status(documents[name])
        if _status(local) != _status(expected):
            found.append(
                f"Part {number} local status disagrees: {local!r} != {expected!r}"
            )

    readme_rows = _table_after(
        readme, "## 3. Numbered parts", ("part", "title", "status")
    )
    readme_parts = [row[0] for row in readme_rows]
    if readme_parts != sorted(EXPECTED_PARTS):
        found.append("README part projection does not contain Parts 00–11 exactly once")
    for number, title, status in readme_rows:
        if number not in PARTS:
            continue
        if title.casefold() != _part_title(documents[PARTS[number]]).casefold():
            found.append(f"README title projection disagrees for Part {number}")
        if number in owner_status and _status(status) != _status(owner_status[number]):
            found.append(f"README status projection disagrees for Part {number}")

    numbered_texts = {number: documents[name] for number, name in PARTS.items()}
    for field, (value, owner, _anchor) in IDENTIFIERS.items():
        if field in {"registry_id", "registry_version"}:
            declaration = f"`{field}: {value}`"
            if declaration not in numbered_texts[owner]:
                found.append(f"{field} owner declaration is missing from Part {owner}")
        else:
            pattern = re.compile(rf"is identified by\s+`{re.escape(value)}`")
            owners = [
                number
                for number, text in numbered_texts.items()
                if pattern.search(text)
            ]
            if owners != [owner]:
                found.append(
                    f"{field} owner declarations are {owners or 'missing'}, expected Part {owner}"
                )

    identifier_rows = _table_after(
        readme, "## 4. Packet-recorded identifiers", ("field", "value", "owner")
    )
    projected = {row[0].strip("`"): row for row in identifier_rows}
    if set(projected) != set(IDENTIFIERS):
        found.append("README identifier projection has missing or unknown fields")
    for field, (value, owner, anchor) in IDENTIFIERS.items():
        row = projected.get(field)
        if row is None:
            continue
        if row[1] != f"`{value}`":
            found.append(f"README identifier projection disagrees for {field}")
        if PARTS[owner] not in row[2] or f"#{anchor}" not in row[2]:
            found.append(f"README identifier owner link disagrees for {field}")

    if not readme.startswith(
        "# Escapewheel Portable Data Packet Specification, v0.2\n\nInformational entry point."
    ):
        found.append("README is not explicitly informational")
    if re.search(
        r"^#{1,6}\s+.*normative references", readme, re.IGNORECASE | re.MULTILINE
    ):
        found.append("README contains a normative-reference section")
    if match := NORMATIVE_KEYWORD.search(readme):
        found.append(f"README contains normative keyword {match.group(0)}")

    reference_sections = {
        number: _anchored_section(numbered_texts[number], anchor)
        for number, anchor in REFERENCE_ANCHORS.items()
    }
    # Every part's section, including those with no approved row allocation, so an authority
    # copied into one of them is still found out of place.
    every_reference_section = {
        number: _anchored_section(text, match.group(1))
        for number, text in numbered_texts.items()
        if (match := REFERENCE_SECTION_ANCHOR.search(text))
    } | reference_sections
    reference_rows: dict[str, list[tuple[str, ...]]] = {}
    for number, references in reference_sections.items():
        if not references:
            found.append(f"Part {number} normative-reference section is missing")
            continue
        rows = reference_rows[number] = _table_after(
            references,
            REFERENCE_ANCHORS[number],
            ("reference", "candidate edition", "application"),
        )
        if tuple(rows) != REFERENCE_ROWS[number]:
            found.append(
                f"Part {number} normative-reference rows disagree with the approved allocation"
            )
    for name, marker in REFERENCE_MARKERS.items():
        expected = REFERENCE_OWNERS[name]
        owners = [
            number
            for number, references in sorted(every_reference_section.items())
            if marker in references
        ]
        if owners == [expected]:
            continue
        if not owners:
            found.append(f"Part {expected} normative references are missing {name}")
        elif expected not in owners and len(owners) == 1:
            found.append(
                f"{name} normative reference is in Part {owners[0]}, expected Part {expected}"
            )
        else:
            found.append(
                f"{name} normative reference appears in Parts {', '.join(owners)}, expected only Part {expected}"
            )
    # Part 02 §13's consistency condition with the core registry: an exact URI match on an entry's
    # link, with no dereference.
    part_02_links = {
        target
        for row in reference_rows.get("02", [])
        for target in LINK_TARGET.findall(row[0])
    }
    for column, uri in _open_authorities(registry):
        if uri not in part_02_links:
            found.append(
                f"open core column {column} names authority {uri}, which no Part 02 §13 entry links"
            )
    for number, marker in REFERENCE_INVOCATIONS.items():
        if marker not in numbered_texts[number]:
            found.append(f"Part {number} external-reference invocation is missing")
    for implementation in ("DuckDB", "zarr-python", "Numcodecs"):
        if any(
            implementation in references
            for references in every_reference_section.values()
        ):
            found.append(
                f"normative references promote implementation {implementation}"
            )

    combined = documents["Escapewheel_POC_v0.2_Implementation_Spec.md"]
    if combined != _render(documents):
        found.append("combined specification is stale")
    if "<!-- BEGIN 00_architecture.md -->" not in combined:
        found.append("combined specification omits Part 00")

    required_candidate_phrases = (
        "current generated v0.2 numbered parts",
        "every artifact that a numbered part expressly",
        "specification candidate",
        "specification release",
    )
    for phrase in required_candidate_phrases:
        if phrase not in architecture:
            found.append(f"Part 00 candidate framework is missing {phrase!r}")

    return found


def main() -> int:
    """Report framework consistency."""
    found = defects()
    if found:
        for defect in found:
            print(f"FAIL  {defect}")
        return 1
    print("ok    specification framework declarations agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

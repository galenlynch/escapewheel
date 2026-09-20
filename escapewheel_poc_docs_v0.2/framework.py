"""Check the specification framework and its informative projections.

Part 00 owns artifact roles, numbered-part subjects and statuses, identifier ownership, and the
normative bibliography. This checker verifies the representations that can be compared
mechanically. It does not decide whether prose is well placed or semantically complete.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import combine

HERE = Path(__file__).resolve().parent

PARTS = {path.name[:2]: path.name for path in sorted(HERE.glob("[0-9][0-9]_*.md"))}
EXPECTED_PARTS = {f"{number:02d}" for number in range(11)}

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
    "registry_version": ("0.2.0", "02", "ew-registry-self-description"),
}

REFERENCE_MARKERS = {
    "BCP 14": "https://www.rfc-editor.org/info/bcp14",
    "RFC 8259": "https://www.rfc-editor.org/info/rfc8259",
    "RFC 3986": "https://www.rfc-editor.org/info/rfc3986",
    "JSON Schema Core": "json-schema.org/draft/2020-12/json-schema-core",
    "JSON Schema Validation": "json-schema.org/draft/2020-12/json-schema-validation",
    "Parquet": "github.com/apache/parquet-format",
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
    "Zarr v2": "zarr-specs.readthedocs.io/en/latest/v2/v2.0.html",
    "RFC 8878": "https://www.rfc-editor.org/info/rfc8878",
    "FIPS 180-4": "csrc.nist.gov/pubs/fips/180-4",
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


def _render(documents: Mapping[str, str]) -> str:
    """Render the combined document from possibly mutated source documents."""
    blocks = [combine.HEADER]
    for name in combine.ORDER:
        body = documents[name].rstrip("\n")
        blocks.append(f"<!-- BEGIN {name} -->\n\n{body}\n\n<!-- END {name} -->\n")
    return "\n".join(blocks)


def defects(overrides: Mapping[str, str] | None = None) -> list[str]:
    """Return each mechanically observable framework disagreement."""
    documents = _documents(overrides)
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
        found.append("README part projection does not contain Parts 00–10 exactly once")
    for number, title, status in readme_rows:
        if number not in PARTS:
            continue
        if title.casefold() != _part_title(documents[PARTS[number]]).casefold():
            found.append(f"README title projection disagrees for Part {number}")
        if number in owner_status and _status(status) != _status(owner_status[number]):
            found.append(f"README status projection disagrees for Part {number}")

    numbered_texts = {number: documents[name] for number, name in PARTS.items()}
    for field, (value, owner, _anchor) in IDENTIFIERS.items():
        if field == "registry_version":
            declaration = (
                "The core registry's `registry_version` MUST be exactly `0.2.0`."
            )
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

    reference_start = architecture.find('id="ew-normative-references"')
    references = architecture[reference_start:] if reference_start >= 0 else ""
    if reference_start < 0:
        found.append("Part 00 normative bibliography is missing")
    for name, marker in REFERENCE_MARKERS.items():
        if marker not in references:
            found.append(f"Part 00 normative bibliography is missing {name}")
    for implementation in ("DuckDB", "zarr-python", "Numcodecs"):
        if implementation in references:
            found.append(
                f"Part 00 normative bibliography promotes implementation {implementation}"
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

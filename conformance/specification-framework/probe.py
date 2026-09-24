"""Prove that framework checks reject conflicting declarations and projections."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "escapewheel_poc_docs_v0.2"
sys.path.insert(0, str(SPEC))

import framework


def _text(name: str) -> str:
    """Read one framework input."""
    return (SPEC / name).read_text()


def _replace(name: str, old: str, new: str) -> dict[str, str]:
    """Return a one-file mutation, refusing an ambiguous selector."""
    text = _text(name)
    count = text.count(old)
    if count != 1:
        raise AssertionError(
            f"mutation selector occurs {count} times in {name}: {old!r}"
        )
    return {name: text.replace(old, new)}


def _assert_rejected(label: str, mutation: dict[str, str], expected: str) -> None:
    """Require a mutation to produce its intended framework defect."""
    found = framework.defects(mutation)
    if not any(expected in defect for defect in found):
        raise AssertionError(f"{label} was not rejected as {expected!r}: {found}")


def main() -> int:
    """Exercise every conflict class promised by R122."""
    current = framework.defects()
    if current:
        raise AssertionError(f"positive framework case is not clean: {current}")

    part_row = "| 10 | performance measurements and rationale | informative |"
    _assert_rejected(
        "missing part",
        _replace("00_architecture.md", part_row + "\n", ""),
        "part table missing: 10",
    )
    _assert_rejected(
        "duplicate part",
        _replace("00_architecture.md", part_row, part_row + "\n" + part_row),
        "part table duplicates: 10",
    )
    _assert_rejected(
        "unknown part",
        _replace(
            "00_architecture.md",
            part_row,
            part_row + "\n| 12 | unknown | informative |",
        ),
        "part table has unknown: 12",
    )
    _assert_rejected(
        "conflicting local status",
        _replace(
            "03_portable_physical_profile.md",
            "Normative. Profile identifier:",
            "Informative. Profile identifier:",
        ),
        "Part 03 local status disagrees",
    )
    _assert_rejected(
        "missing mixed exception",
        _replace(
            "00_architecture.md",
            "informative except §§2 and 5, which are normative",
            "informative",
        ),
        "Part 06 local status disagrees",
    )
    _assert_rejected(
        "conflicting mixed exception",
        _replace(
            "06_analysis_layer.md",
            "Informative, except §2 and §5, which are normative.",
            "Informative, except §2 and §4, which are normative.",
        ),
        "Part 06 local status disagrees",
    )
    _assert_rejected(
        "missing identifier owner",
        _replace(
            "01_semantic_standard.md",
            "is identified by `escapewheel-semantic-v0.1`",
            "has identifier `escapewheel-semantic-v0.1`",
        ),
        "semantic_standard_version owner declarations are missing",
    )
    duplicate_owner = _text("04_packet_catalog.md") + (
        "\nThe semantic standard is identified by `escapewheel-semantic-v0.1`.\n"
    )
    _assert_rejected(
        "duplicate identifier owner",
        {"04_packet_catalog.md": duplicate_owner},
        "semantic_standard_version owner declarations are",
    )
    _assert_rejected(
        "README normative-reference section",
        {"README.md": _text("README.md") + "\n## Normative references\n"},
        "README contains a normative-reference section",
    )
    _assert_rejected(
        "README normative keyword",
        {"README.md": _text("README.md") + "\nA reader MUST infer nothing.\n"},
        "README contains normative keyword MUST",
    )
    _assert_rejected(
        "stale README projection",
        _replace(
            "README.md",
            "| 10 | Performance notes | informative |",
            "| 10 | Performance notes | normative |",
        ),
        "README status projection disagrees for Part 10",
    )
    _assert_rejected(
        "missing bibliography entry",
        _replace(
            "00_architecture.md",
            "https://www.rfc-editor.org/info/bcp14",
            "https://example.invalid/missing-bcp14",
        ),
        "Part 00 normative references are missing BCP 14",
    )
    _assert_rejected(
        "missing Part 03 reference",
        _replace(
            "03_portable_physical_profile.md",
            "[Apache Parquet format](https://github.com/apache/parquet-format)",
            "[Apache Parquet format](https://example.invalid/missing-parquet)",
        ),
        "Part 03 normative references are missing Parquet",
    )
    _assert_rejected(
        "missing Part 04 reference",
        _replace(
            "04_packet_catalog.md",
            "https://csrc.nist.gov/pubs/fips/180-4/upd1/final",
            "https://example.invalid/missing-fips-180-4",
        ),
        "Part 04 normative references are missing FIPS 180-4",
    )
    _assert_rejected(
        "missing Part 11 reference",
        _replace(
            "11_tier_2_rule_language.md",
            "https://standards.ieee.org/ieee/754/6210/",
            "https://example.invalid/missing-ieee-754",
        ),
        "Part 11 normative references are missing IEEE 754-2019",
    )
    parquet_marker = framework.REFERENCE_MARKERS["Parquet"]
    misplaced_part_03 = _text("03_portable_physical_profile.md").replace(
        parquet_marker, "example.invalid/misplaced-parquet"
    )
    misplaced_part_04 = _text("04_packet_catalog.md") + f"\n{parquet_marker}\n"
    _assert_rejected(
        "misplaced reference",
        {
            "03_portable_physical_profile.md": misplaced_part_03,
            "04_packet_catalog.md": misplaced_part_04,
        },
        "Parquet normative reference is in Part 04, expected Part 03",
    )
    _assert_rejected(
        "duplicate reference",
        {
            "04_packet_catalog.md": _text("04_packet_catalog.md")
            + f"\n{parquet_marker}\n"
        },
        "Parquet normative reference appears in Parts 03, 04",
    )
    _assert_rejected(
        "reference copied into an untabled section",
        _replace(
            "02_core_logical_schemas.md",
            "## 13. Normative references\n",
            "## 13. Normative references\n\n- [RFC 3986](https://www.rfc-editor.org/info/rfc3986)\n",
        ),
        "RFC 3986 normative reference appears in Parts 00, 02",
    )
    _assert_rejected(
        "changed reference row",
        _replace(
            "03_portable_physical_profile.md",
            "| [RFC 8878](https://www.rfc-editor.org/info/rfc8878) | exact | Zstandard framing |",
            "| [RFC 8878](https://www.rfc-editor.org/info/rfc8878) | unversioned | Zstandard framing |",
        ),
        "Part 03 normative-reference rows disagree with the approved allocation",
    )
    _assert_rejected(
        "missing Part 03 invocation",
        _replace(
            "03_portable_physical_profile.md",
            "Its requirements directly invoke the shared JSON and URI authorities",
            "Its requirements use the shared JSON and URI authorities",
        ),
        "Part 03 external-reference invocation is missing",
    )
    _assert_rejected(
        "missing Part 04 invocation",
        _replace(
            "04_packet_catalog.md",
            "Its requirements directly invoke the shared JSON, URI, and JSON Schema authorities",
            "Its requirements use the shared JSON, URI, and JSON Schema authorities",
        ),
        "Part 04 external-reference invocation is missing",
    )
    _assert_rejected(
        "missing Part 11 invocation",
        _replace(
            "11_tier_2_rule_language.md",
            "SQL/Foundation editions, corrigenda, and IEEE floating-point edition identified in §9",
            "SQL and floating-point references identified in §9",
        ),
        "Part 11 external-reference invocation is missing",
    )
    _assert_rejected(
        "implementation used as authority",
        _replace(
            "00_architecture.md",
            "| [RFC 8259]",
            "| DuckDB behavior and [RFC 8259]",
        ),
        "normative references promote implementation DuckDB",
    )
    _assert_rejected(
        "zarr-python used as authority",
        _replace(
            "03_portable_physical_profile.md",
            "| [Zarr v3 core]",
            "| zarr-python behavior and [Zarr v3 core]",
        ),
        "normative references promote implementation zarr-python",
    )
    _assert_rejected(
        "Numcodecs used as authority",
        _replace(
            "03_portable_physical_profile.md",
            "| Zarr v3 [Bytes]",
            "| Numcodecs behavior and Zarr v3 [Bytes]",
        ),
        "normative references promote implementation Numcodecs",
    )
    _assert_rejected(
        "stale combined rendering",
        {
            "Escapewheel_POC_v0.2_Implementation_Spec.md": _text(
                "Escapewheel_POC_v0.2_Implementation_Spec.md"
            )
            + "\n"
        },
        "combined specification is stale",
    )
    _assert_rejected(
        "combined rendering omits Part 00",
        _replace(
            "Escapewheel_POC_v0.2_Implementation_Spec.md",
            "<!-- BEGIN 00_architecture.md -->",
            "<!-- OMITTED 00_architecture.md -->",
        ),
        "combined specification omits Part 00",
    )

    print("ok    specification framework rejects conflicting projections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

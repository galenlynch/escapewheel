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
            part_row + "\n| 11 | unknown | informative |",
        ),
        "part table has unknown: 11",
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
        "normative bibliography is missing BCP 14",
    )
    _assert_rejected(
        "implementation used as authority",
        _replace(
            "00_architecture.md",
            "| [RFC 8259]",
            "| DuckDB behavior and [RFC 8259]",
        ),
        "normative bibliography promotes implementation DuckDB",
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

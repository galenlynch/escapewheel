"""Check the specification framework and its informative projections.

Part 00 owns artifact roles, numbered-part subjects and statuses, identifier ownership, and the
normative-reference policy. Subject-owning parts own their local bibliographies. This checker
verifies the representations that can be compared mechanically, including that Part 02 §13 links
every authority an open column of the core registry names. It does not decide whether prose is well
placed or semantically complete.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

import combine
from framework_data import (
    CANDIDATE_PHRASES,
    EXPECTED_PARTS,
    IDENTIFIERS,
    IMPLEMENTATIONS,
    README_OPENING,
    REFERENCE_ANCHORS,
    REFERENCE_INVOCATIONS,
    REFERENCE_MARKERS,
    REFERENCE_OWNERS,
    REFERENCE_ROWS,
)

HERE = Path(__file__).resolve().parent
TREE = HERE.parent
ARTIFACTS = TREE / "artifacts"
CORE_REGISTRY = ARTIFACTS / "logical_schemas.json"

PARTS = {path.name[:2]: path.name for path in sorted((HERE.parent / "parts").glob("[0-9][0-9]_*.md"))}

REFERENCE_SECTION_ANCHOR = re.compile(r'id="(ew-[a-z-]*normative-references)"')
LINK_TARGET = re.compile(r"\]\(([^)\s]+)\)")
NORMATIVE_KEYWORD = re.compile(r"\b(?:MUST|REQUIRED|SHALL|SHOULD|RECOMMENDED|MAY|OPTIONAL)\b")


def _documents(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Read framework inputs, replacing named files with optional mutation text."""
    paths = {
        **combine.SOURCES,
        combine.OUT.name: combine.OUT,
    }
    documents = {name: path.read_text() if path.is_file() else "" for name, path in paths.items()}
    if overrides:
        documents.update(overrides)
    return documents


def _table_after(text: str, marker: str, header: tuple[str, ...]) -> list[tuple[str, ...]]:
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
    return combine.render_documents(dict(documents))


def _artifacts() -> dict[str, str]:
    return {
        path.relative_to(TREE).as_posix(): path.read_text() for path in sorted(ARTIFACTS.rglob("*")) if path.is_file()
    }


def path_defects(
    documents: Mapping[str, str],
    artifacts: Mapping[str, str] | None = None,
    outside: Iterable[str] = (),
) -> list[str]:
    """Report each path leaving the tree or naming nothing in it, and each unincorporated artifact.

    Part 00 §2.1 requires a part or incorporated artifact to give a path relative to the tree's
    root and naming a file within it, other than a path within a packet or a link between parts.
    A path within a packet begins with no entry of the tree's root, so only a path beginning with
    `../`, with one of those entries, or with an ``outside`` entry of an enclosing repository is
    judged. ``artifacts`` maps a path relative to the tree to the artifact's text.
    """
    if artifacts is None:
        artifacts = _artifacts()
    roots = sorted({path.name for path in TREE.iterdir() if path.is_dir()} - {".venv"})
    leaving = sorted(set(outside) - set(roots))
    pattern = re.compile(r"(?<![\w./:-])((?:\.\.|" + "|".join(map(re.escape, roots + leaving)) + r")/[\w./<>*-]*)")
    link = re.compile(r"\]\(([^)\s#]*)[^)\s]*\)")
    parts = {name: text for name, text in documents.items() if name in PARTS.values()}
    found: list[str] = []
    for name, text in [*parts.items(), *artifacts.items()]:
        for path in sorted(set(pattern.findall(text))):
            path = path.rstrip(".")
            first = path.split("/", 1)[0]
            if first == ".." or first in leaving:
                found.append(f"{name} gives {path}, outside the tree")
            elif "<" not in path and "*" not in path and not (TREE / path).exists():
                found.append(f"{name} gives {path}, which names nothing in the tree")
    for name, text in parts.items():
        for target in link.findall(text):
            if target and not re.match(r"[a-z]+:", target) and target not in PARTS.values():
                found.append(f"{name} links to {target}, which is not a numbered part")
    cited = "\n".join(parts.values())
    found += [f"{path} is incorporated by no numbered part" for path in artifacts if path not in cited]
    return found


def _part_table_defects(owner_rows: list[tuple[str, ...]]) -> list[str]:
    """Report a numbered part Part 00's ownership table omits, invents or repeats."""
    found = []
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
    return found


def _local_status_defects(documents: Mapping[str, str], owner_status: Mapping[str, str]) -> list[str]:
    """Report each part whose own status line disagrees with Part 00's table."""
    found = []
    for number, name in PARTS.items():
        expected = owner_status.get(number)
        if expected is None:
            continue
        local = _local_status(documents[name])
        if _status(local) != _status(expected):
            found.append(f"Part {number} local status disagrees: {local!r} != {expected!r}")
    return found


def _readme_part_defects(documents: Mapping[str, str], owner_status: Mapping[str, str]) -> list[str]:
    """Report where the README's part table disagrees with the parts or with Part 00."""
    found = []
    readme_rows = _table_after(documents["README.md"], "## 3. Numbered parts", ("part", "title", "status"))
    readme_parts = [row[0] for row in readme_rows]
    if readme_parts != sorted(EXPECTED_PARTS):
        found.append("README part projection does not contain Parts 00–12 exactly once")
    for number, title, status in readme_rows:
        if number not in PARTS:
            continue
        if title.casefold() != _part_title(documents[PARTS[number]]).casefold():
            found.append(f"README title projection disagrees for Part {number}")
        if number in owner_status and _status(status) != _status(owner_status[number]):
            found.append(f"README status projection disagrees for Part {number}")
    return found


def _identifier_owner_defects(numbered_texts: Mapping[str, str]) -> list[str]:
    """Report each packet-recorded identifier its owning part does not alone declare."""
    found = []
    for field, (value, owner, _anchor) in IDENTIFIERS.items():
        if field in {"registry_id", "registry_version"}:
            declaration = f"`{field}: {value}`"
            if declaration not in numbered_texts[owner]:
                found.append(f"{field} owner declaration is missing from Part {owner}")
        else:
            pattern = re.compile(rf"is identified by\s+`{re.escape(value)}`")
            owners = [number for number, text in numbered_texts.items() if pattern.search(text)]
            if owners != [owner]:
                found.append(f"{field} owner declarations are {owners or 'missing'}, expected Part {owner}")
    return found


def _identifier_projection_defects(readme: str) -> list[str]:
    """Report where the README's identifier table disagrees with the owning parts."""
    found = []
    identifier_rows = _table_after(readme, "## 4. Packet-recorded identifiers", ("field", "value", "owner"))
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
    return found


def _readme_informational_defects(readme: str) -> list[str]:
    """Report anything by which the README would read as normative."""
    found = []
    if not readme.startswith(README_OPENING):
        found.append("README is not explicitly informational")
    if re.search(r"^#{1,6}\s+.*normative references", readme, re.IGNORECASE | re.MULTILINE):
        found.append("README contains a normative-reference section")
    if match := NORMATIVE_KEYWORD.search(readme):
        found.append(f"README contains normative keyword {match.group(0)}")
    return found


def _reference_rows(reference_sections: Mapping[str, str]) -> dict[str, list[tuple[str, ...]]]:
    """Return the reference table's rows in each normative-reference section that is present."""
    return {
        number: _table_after(references, REFERENCE_ANCHORS[number], ("reference", "candidate edition", "application"))
        for number, references in reference_sections.items()
        if references
    }


def _reference_row_defects(
    reference_sections: Mapping[str, str], reference_rows: Mapping[str, list[tuple[str, ...]]]
) -> list[str]:
    """Report each normative-reference section that is absent or departs from its approved rows."""
    found = []
    for number, references in reference_sections.items():
        if not references:
            found.append(f"Part {number} normative-reference section is missing")
        elif tuple(reference_rows[number]) != REFERENCE_ROWS[number]:
            found.append(f"Part {number} normative-reference rows disagree with the approved allocation")
    return found


def _reference_owner_defects(every_reference_section: Mapping[str, str]) -> list[str]:
    """Report each external authority that is not referenced by its owning part alone."""
    found = []
    for name, marker in REFERENCE_MARKERS.items():
        expected = REFERENCE_OWNERS[name]
        owners = [number for number, references in sorted(every_reference_section.items()) if marker in references]
        if owners == [expected]:
            continue
        if not owners:
            found.append(f"Part {expected} normative references are missing {name}")
        elif expected not in owners and len(owners) == 1:
            found.append(f"{name} normative reference is in Part {owners[0]}, expected Part {expected}")
        else:
            found.append(
                f"{name} normative reference appears in Parts {', '.join(owners)}, expected only Part {expected}"
            )
    return found


def _authority_link_defects(part_02_rows: list[tuple[str, ...]], registry: Mapping) -> list[str]:
    """Report each authority of an open core column that no Part 02 §13 entry links.

    Part 02 §13's consistency condition is an exact URI match on an entry's link, with no
    dereference.
    """
    part_02_links = {target for row in part_02_rows for target in LINK_TARGET.findall(row[0])}
    return [
        f"open core column {column} names authority {uri}, which no Part 02 §13 entry links"
        for column, uri in _open_authorities(registry)
        if uri not in part_02_links
    ]


def _invocation_defects(numbered_texts: Mapping[str, str]) -> list[str]:
    """Report each part that no longer invokes its external authorities in prose."""
    return [
        f"Part {number} external-reference invocation is missing"
        for number, marker in REFERENCE_INVOCATIONS.items()
        if marker not in numbered_texts[number]
    ]


def _implementation_defects(every_reference_section: Mapping[str, str]) -> list[str]:
    """Report each implementation a normative-reference section names."""
    return [
        f"normative references promote implementation {implementation}"
        for implementation in IMPLEMENTATIONS
        if any(implementation in references for references in every_reference_section.values())
    ]


def _combined_defects(documents: Mapping[str, str]) -> list[str]:
    """Report a single-file rendering that is stale or incomplete."""
    found = []
    combined = documents["Escapewheel_POC_v0.2_Implementation_Spec.md"]
    if combined != _render(documents):
        found.append("combined specification is stale")
    if "<!-- BEGIN 00_architecture.md -->" not in combined:
        found.append("combined specification omits Part 00")
    return found


def _candidate_defects(architecture: str) -> list[str]:
    """Report each phrase of the candidate framework Part 00 no longer states."""
    return [
        f"Part 00 candidate framework is missing {phrase!r}"
        for phrase in CANDIDATE_PHRASES
        if phrase not in architecture
    ]


def defects(overrides: Mapping[str, str] | None = None, registry: Mapping | None = None) -> list[str]:
    """Return each mechanically observable framework disagreement.

    ``registry`` replaces the core registry document read from ``CORE_REGISTRY``.
    """
    documents = _documents(overrides)
    if registry is None:
        registry = json.loads(CORE_REGISTRY.read_text())
    architecture = documents[PARTS["00"]]
    readme = documents["README.md"]
    numbered_texts = {number: documents[name] for number, name in PARTS.items()}

    owner_rows = _table_after(architecture, 'id="ew-numbered-part-ownership"', ("part", "subject", "status"))
    owner_status = {row[0]: row[2] for row in owner_rows if row[0] in EXPECTED_PARTS}

    reference_sections = {
        number: _anchored_section(numbered_texts[number], anchor) for number, anchor in REFERENCE_ANCHORS.items()
    }
    # Every part's section, including those with no approved row allocation, so an authority
    # copied into one of them is still found out of place.
    every_reference_section = {
        number: _anchored_section(text, match.group(1))
        for number, text in numbered_texts.items()
        if (match := REFERENCE_SECTION_ANCHOR.search(text))
    } | reference_sections
    reference_rows = _reference_rows(reference_sections)

    return [
        *_part_table_defects(owner_rows),
        *_local_status_defects(documents, owner_status),
        *_readme_part_defects(documents, owner_status),
        *_identifier_owner_defects(numbered_texts),
        *_identifier_projection_defects(readme),
        *_readme_informational_defects(readme),
        *_reference_row_defects(reference_sections, reference_rows),
        *_reference_owner_defects(every_reference_section),
        *_authority_link_defects(reference_rows.get("02", []), registry),
        *_invocation_defects(numbered_texts),
        *_implementation_defects(every_reference_section),
        *_combined_defects(documents),
        *_candidate_defects(architecture),
        *path_defects(documents),
    ]


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

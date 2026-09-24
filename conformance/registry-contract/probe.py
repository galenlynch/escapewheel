"""Preserve the migration and external-domain evidence for R126.

Before R126 is committed, the incorporated side is the candidate working tree. Afterward it is
the first commit that added the accepted R126 record. This makes the comparison reproducible
without freezing future registry development at R126's declarations.
"""

from __future__ import annotations

import importlib.metadata
import json
import re
import subprocess
from importlib.resources import files
from pathlib import Path
from typing import Any
from unittest.mock import patch
from xml.etree import ElementTree

from escapewheel_validator.registry_document import check_registry
from ucumvert import get_ucum_parser, parse_ucum

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "8b22b501cec6d2b76a1f286d84d2c082055f62f6"
ACCEPTED = "revisions/accepted/R126-a-registry-document-has-one-complete-conformance-contract.md"
CORE = "registry/logical_schemas.json"
EXTENSIONS = (
    "registry/extensions/aind_opto.json",
    "registry/extensions/aind_unit_qc.json",
    "registry/extensions/dynamic_foraging.json",
    "registry/extensions/vr_foraging.json",
)


def _git(*arguments: str) -> str:
    """Run one read-only Git query from the repository root."""
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _incorporation_commit() -> str | None:
    """Return the first commit that added R126, if acceptance is already committed."""
    commits = _git(
        "log", "--diff-filter=A", "--format=%H", "--reverse", "--", ACCEPTED
    ).splitlines()
    return commits[0] if commits else None


def _document(path: str, revision: str | None) -> Any:
    """Load JSON from a commit or, for the candidate incorporation, the working tree."""
    text = _git("show", f"{revision}:{path}") if revision else (ROOT / path).read_text()
    return json.loads(text)


def _tables(document: dict[str, Any]) -> dict[str, Any]:
    """Project table contracts from either side of the R128 shape transition."""
    if "tables" in document:
        return document["tables"]
    return {
        name: declaration["table"]
        for name, declaration in document["resources"].items()
        if declaration["kind"] == "table"
    }


def _declarations(document: dict[str, Any]) -> dict[str, Any]:
    """Remove the one reviewed declaration-local spelling transition."""
    tables = json.loads(json.dumps(_tables(document)))
    for table in tables.values():
        for column in table["columns"]:
            for authority in column.get("authority", []):
                if authority == {"name": "UCUM", "uri": "https://ucum.org/ucum.html"}:
                    authority["uri"] = "https://ucum.org/ucum"
    return tables


def _rules(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        rule
        for document in documents
        for table in _tables(document).values()
        for rule in table["rules"]
    ]


def _references(documents: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (resource, reference)
        for document in documents
        for resource, table in _tables(document).items()
        for reference in table["references"]
    ]


def _columns(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {column["name"]: column for column in table["columns"]}


def _session_edge(
    source: dict[str, Any], target: dict[str, Any], reference: dict[str, Any]
) -> bool:
    """Apply the four Part 02 session-preserving edge conditions."""
    source_columns = _columns(source)
    target_columns = _columns(target)
    pairs = list(zip(reference["columns"], reference["resource_columns"], strict=True))
    return (
        pairs.count(("session_id", "session_id")) == 1
        and all(source_columns[name]["presence"] == "required" for name, _ in pairs)
        and reference["resource_columns"] == target["primary_key"]
        and all(
            source_columns[left]["type"] == target_columns[right]["type"]
            and (
                source_columns[left]["role"] == target_columns[right]["role"]
                or (source_columns[left]["role"], target_columns[right]["role"])
                == ("data", "discriminator")
            )
            and source_columns[left].get("identity")
            == target_columns[right].get("identity")
            for left, right in pairs
        )
    )


def _has_session_path(resource: str, tables: dict[str, Any]) -> bool:
    """Return whether a resource reaches core.sessions by session-preserving references."""
    frontier = [resource]
    seen: set[str] = set()
    while frontier:
        current = frontier.pop()
        if current == "core.sessions":
            return True
        if current in seen:
            continue
        seen.add(current)
        table = tables[current]
        frontier.extend(
            reference["resource"]
            for reference in table["references"]
            if reference["resource"] in tables
            and _session_edge(table, tables[reference["resource"]], reference)
        )
    return False


def _assert_migration(
    before: list[dict[str, Any]], after: list[dict[str, Any]]
) -> None:
    """Check declaration preservation and the exact measured populations."""
    assert sum(len(_tables(document)) for document in before) == 54
    assert sum(len(_tables(document)) for document in after) == 54
    assert all(
        _declarations(old) == _declarations(new)
        for old, new in zip(before, after, strict=True)
    )
    print("ok    R126 migration preserves 54 table declarations")

    rules = _rules(after)
    references = _references(after)
    assert len(rules) == 121
    assert len(references) == 128
    rule_ids = [rule["id"] for rule in rules]
    assert len(rule_ids) == len(set(rule_ids))
    assert all(
        rule["id"].startswith(f"{resource}.")
        for document in after
        for resource, table in _tables(document).items()
        for rule in table["rules"]
    )
    tables = {
        resource: table
        for document in after
        for resource, table in _tables(document).items()
    }
    assert all(
        reference["resource_columns"] == tables[reference["resource"]]["primary_key"]
        for _, reference in references
    )
    print("ok    R126 migration preserves 121 rules and 128 complete references")

    indirect = {
        "aind_opto.emissions",
        "dynamic_foraging.trials",
        "vr_foraging.sites",
        "vr_foraging.site_odors",
    }
    assert all(_has_session_path(resource, tables) for resource in indirect)
    assert all(
        _has_session_path(resource, tables) == ("session_id" in _columns(table))
        for resource, table in tables.items()
    )
    print("ok    R126 session-preserving paths are valid")


def _assert_ucum(documents: list[dict[str, Any]]) -> None:
    """Exercise the exact offline parser and verify its bundled data and notices."""
    essence = files("ucumvert").joinpath("vendor/ucum-essence.xml").read_text()
    root = ElementTree.fromstring(essence)
    assert root.attrib["version"] == "2.2"
    assert root.attrib["revision-date"] == "2024-06-17"
    units = [
        column["unit"]
        for document in documents
        for table in _tables(document).values()
        for column in table["columns"]
        if "unit" in column
    ]
    assert len(units) == 65
    with patch(
        "socket.socket", side_effect=AssertionError("network access is forbidden")
    ):
        parser = get_ucum_parser()
        for unit in units:
            parse_ucum(unit, parser=parser)
    print("ok    R126 parses 65 literal UCUM units offline")

    distribution = importlib.metadata.distribution("ucumvert")
    assert distribution.version == "0.3.2"
    assert distribution.metadata["License-Expression"] == "MIT"
    package = files("escapewheel_validator")
    mit = package.joinpath("licenses/UCUMVERT-LICENSE.txt").read_text()
    notices = package.joinpath("licenses/THIRD_PARTY_NOTICES.md").read_text()
    assert "MIT License" in mit and "Copyright (c) 2024 David Linke" in mit
    assert re.search(r"UCUM Copyright Notice and\s+License, Version 1\.1", notices)
    assert re.search(r"https://ucum\.org/license", notices)
    print("ok    R126 UCUM parser and license evidence is distributable")


def main() -> int:
    """Run the frozen migration comparison and live offline capability checks."""
    incorporated = _incorporation_commit()
    before = [_document(path, BASELINE) for path in (CORE, *EXTENSIONS)]
    after = [_document(path, incorporated) for path in (CORE, *EXTENSIONS)]
    _assert_migration(before, after)
    current = [_document(path, None) for path in (CORE, *EXTENSIONS)]
    core = current[0]
    assert check_registry(core).state == "valid"
    assert all(
        check_registry(extension, core).state == "valid" for extension in current[1:]
    )
    _assert_ucum(current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Pure checks shared by revision-process conformance tests."""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "spec" / "tools"))

import specdoc


def _canonical(line: str) -> str | None:
    """Return the identifier where `line` is a canonical anchor's own line."""
    match = specdoc.ANCHOR.fullmatch(line)
    return match.group(1) if match and match.group(2) == "canonical" else None


def canonical_anchor_occurrences(text: str) -> list[str]:
    """Return canonical raw-HTML anchors outside fenced code blocks, in source order."""
    return [
        anchor
        for _, line in specdoc.outside_fences(text)
        if line is not None and (anchor := _canonical(line)) is not None
    ]


def canonical_anchors(text: str) -> set[str]:
    """Return canonical raw-HTML anchor identities outside fenced code blocks."""
    return set(canonical_anchor_occurrences(text))


def anchor_bootstrap_only(before: str, after: str) -> bool:
    """Whether a change inserts only canonical anchors immediately before existing headings."""
    old = before.splitlines()
    new = after.splitlines()
    insertions = []
    for tag, _, _, start, end in difflib.SequenceMatcher(a=old, b=new).get_opcodes():
        if tag in {"delete", "replace"}:
            return False
        if tag == "insert":
            inserted = new[start:end]
            if (
                len(inserted) != 1
                or _canonical(inserted[0]) is None
                or end >= len(new)
                or specdoc.HEADING.match(new[end]) is None
            ):
                return False
            insertions.append(inserted[0])
    return bool(insertions)

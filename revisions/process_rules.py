"""Pure checks shared by revision-process conformance tests."""

from __future__ import annotations

import difflib
import re

CANONICAL_LINE = re.compile(r'^<a id="([a-z0-9]+(?:-[a-z0-9]+)*)" data-spec-anchor="canonical"></a>$')
HEADING_LINE = re.compile(r"^#{1,4} \d+(?:\.\d+)*\.?(?:\s|$)")


def canonical_anchor_occurrences(text: str) -> list[str]:
    """Return canonical raw-HTML anchors outside fenced code blocks, in source order."""
    found = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and (match := CANONICAL_LINE.fullmatch(line)):
            found.append(match.group(1))
    return found


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
                or CANONICAL_LINE.fullmatch(inserted[0]) is None
                or end >= len(new)
                or HEADING_LINE.match(new[end]) is None
            ):
                return False
            insertions.append(inserted[0])
    return bool(insertions)

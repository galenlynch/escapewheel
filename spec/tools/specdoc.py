"""What the specification's tools share.

Only the standard library is imported, so a tool outside the tree's environment can import this.
"""

import re
from collections.abc import Iterator
from pathlib import Path

#: A numbered part's file name: two digits, an underscore, then its subject.
PART_GLOB = "[0-9][0-9]_*.md"

#: A section number: `3`, `3.1`, `10.2.4`.
SECTION = r"\d+(?:\.\d+)*"
#: A numbered heading up to four deep, capturing its number, which a title need not follow.
HEADING = re.compile(rf"^#{{1,4}} ({SECTION})\.?(?:\s|$)", re.MULTILINE)
#: `§5.4`, capturing the section.
SECTION_CITATION = re.compile(rf"§({SECTION})")
#: A revision's clause, `R<N> §<section>`, capturing the revision's number and the section.
REVISION_CITATION = re.compile(rf"\bR(\d+) §({SECTION})")
#: A stable anchor on a line of its own, capturing its identifier and `canonical` or `alias`.
ANCHOR = re.compile(r'^<a id="([a-z0-9]+(?:-[a-z0-9]+)*)" data-spec-anchor="(canonical|alias)"></a>$')


class GenerationError(Exception):
    """A source a generator cannot produce its output from; the message names it and says why."""


def part_paths(directory: Path) -> list[Path]:
    """Return every numbered part in `directory`, in number order."""
    return sorted(directory.glob(PART_GLOB))


def part_path(directory: Path, number: str) -> Path | None:
    """Return the part in `directory` numbered `number`, the first by name where several are.

    `number` is matched as a glob, so it is two digits wherever it was read from a citation.
    """
    found = sorted(directory.glob(f"{number}_*.md"))
    return found[0] if found else None


def titled_heading(shallowest: int) -> re.Pattern[str]:
    """Match a numbered heading from `shallowest` to four deep, capturing its number and title."""
    return re.compile(rf"^#{{{shallowest},4}} ({SECTION})\.? +(.+)$", re.MULTILINE)


def part_citation(gap: str) -> re.Pattern[str]:
    """Match `Part 03 §5.4` and the bare `03` form of it, capturing either number, then the section.

    `gap` is the pattern for what separates the part from the section sign.
    """
    return re.compile(rf"(?:`(\d\d)`|Part (\d\d)){gap}§({SECTION})")


def outside_fences(text: str) -> Iterator[tuple[int, str | None]]:
    """Yield each line outside a fenced code block with its position, the first line being 1.

    A fence's own line is yielded as None, since it ends whatever the lines before it began.
    """
    fenced = False
    for position, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
            yield position, None
        elif not fenced:
            yield position, line

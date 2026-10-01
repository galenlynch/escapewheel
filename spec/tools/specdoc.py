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
#: How many leading characters of a stage document or record its metadata table is read from.
METADATA_HEAD = 2000


class GenerationError(Exception):
    """A source a generator cannot produce its output from; the message names it and says why."""


class ScalarError(TypeError):
    """A JSON Pointer token that addresses into a value holding nothing; `token` is that token."""

    def __init__(self, token: str) -> None:
        super().__init__(f"{token!r} follows a scalar")
        self.token = token


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


def _metadata_row(name: str) -> re.Pattern[str]:
    """Match `| **Name** | value |` on a line of its own, where `name` is the pattern for the name."""
    return re.compile(rf"^\|\s*\*\*{name}\*\*\s*\|\s*(.*?)\s*\|$", re.MULTILINE)


#: A row of a two-column metadata table, capturing its name and its value.
METADATA_ROW = _metadata_row("(.+?)")


def metadata(text: str) -> dict[str, str]:
    """Return the metadata table at the head of `text`, the last row winning where a name repeats."""
    return dict(METADATA_ROW.findall(text[:METADATA_HEAD]))


def metadata_value(text: str, name: str) -> str | None:
    """Return what the first metadata row named `name` holds, or None where no row is.

    An empty cell is the empty string, so test the result against None.
    """
    match = _metadata_row(re.escape(name)).search(text[:METADATA_HEAD])
    return match.group(1) if match else None


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


def resolve_pointer(document: object, pointer: object) -> object:
    """Return what an RFC 6901 JSON Pointer addresses in `document`.

    Raises ValueError for anything but a string beginning with `/`, KeyError for a member an object
    lacks, IndexError for a token that is no index of an array, and ScalarError for a token that
    follows a scalar; the last three carry the token.
    """
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("pointer must be a nonempty RFC 6901 string beginning with `/`")
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(token)
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise IndexError(token)
            current = current[int(token)]
        else:
            raise ScalarError(token)
    return current

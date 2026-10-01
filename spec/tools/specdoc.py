"""What the specification's tools share.

Only the standard library is imported, so a tool outside the tree's environment can import this.
"""

from pathlib import Path

#: A numbered part's file name: two digits, an underscore, then its subject.
PART_GLOB = "[0-9][0-9]_*.md"


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

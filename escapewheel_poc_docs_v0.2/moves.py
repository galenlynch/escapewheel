"""Where a section that has moved lives now.

`applied.toml` says where a clause landed and is never rewritten; `moves.toml` says what has moved
since. Everything that resolves a section number composes the two, so a citation written before a
move keeps working and the compliance record keeps saying what was true at acceptance.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def table(path: Path | None = None) -> dict[tuple[str, str], str]:
    """Each move as (part, from) -> to."""
    source = path or HERE / "moves.toml"
    if not source.exists():
        return {}
    loaded = tomllib.loads(source.read_text()).get("move", [])
    return {(str(m["part"]), str(m["from"])): str(m["to"]) for m in loaded}


def resolve(part: str, section: str, moves: dict[tuple[str, str], str] | None = None) -> str:
    """The section this one became, following a chain of moves.

    Returns the input where nothing moved. A cycle would loop, so the walk is bounded by the
    number of moves: a move table that cycles is a defect this refuses to hang on.
    """
    known = table() if moves is None else moves
    seen = section
    for _ in range(len(known) + 1):
        nxt = known.get((part, seen))
        if nxt is None:
            return seen
        seen = nxt
    raise ValueError(f"moves.toml cycles at `{part}` §{section}")


__all__ = ["resolve", "table"]

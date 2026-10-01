"""The record that declares one packet of the corpus."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

#: Writes one packet at the directory it is given.
Build = Callable[[Path], None]


@dataclass(frozen=True)
class Expected:
    """The finding a packet is built to draw."""

    level: str
    check: str
    #: How often it fires, for a finding drawn once per resource (Part 05 §5.3); at least once where None.
    count: int | None = None
    #: The extension it is filed under (Part 05 §9.5), which fails with the packet while core passes.
    registry: str | None = None
    #: The packet still passes, its finding being a warning that leaves it conformant.
    conforming: bool = False


@dataclass(frozen=True)
class Packet:
    """One packet of the corpus: how it is written, and what a validator must report of it."""

    name: str
    build: Build
    #: None for a packet that must pass without a warning.
    expected: Expected | None = None
    #: Checks it must not draw at any level.
    absent: frozenset[str] = frozenset()
    #: Validated with checksums, which establishes every packet-owned digest (Part 04 §5.3, level 2).
    checksums: bool = False
    #: Validated with advisory rules on (Part 02 §10.2), which never changes whether a packet passed.
    advisory: bool = False

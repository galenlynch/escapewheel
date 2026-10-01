"""What a build asks of a source adapter (Part 05 §3.4, Part 12 §5).

- :class:`SourceAdapter` -- what every adapter has.
- :class:`Streams` -- tables too large to hold as records, as batches.
- :class:`StagesArrays` -- dense arrays the packet will own.
- :class:`ReferencesArrays`, :class:`ReferencesMedia` -- arrays and media the packet references.
- :class:`StagesPayloads` -- opaque payloads the packet will own.
- :class:`DeclaresCompensations` -- the source defects the adapter worked around.
- :class:`WithholdsAnchors` -- the terminal anchors a clock's fit left out.
- :class:`Located` -- the path the adapter reads, for a message.

An adapter satisfies a protocol by having its members; it subclasses nothing. A build asks an
adapter for a capability by testing for the capability's protocol.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

import pyarrow as pa

from .opaque import Payload
from .writer import ExternalArray, ExternalMedia, StagedArray


class SourceAdapter(Protocol):
    """One source, opened, with the rows it produces.

    The class also carries the adapter's declaration (Part 05 §3.4), which a recipe check reads
    with nothing open: `PRODUCES`, the resources it can supply, and `STATES`, required; and
    `CONTRIBUTES`, `NEEDS`, `ACCEPTS`, `CONSUMES` and `PROTOCOLS`, each read as empty where the
    class omits it, except that `NEEDS` is then `("root", "session_id")`.

    A table with no rows is omitted, by `records` and by `offers` alike.
    """

    #: Notes about this run, which a build reports and may append to.
    notes: list[str]

    def __init__(self, root: Any, **supplied: Any) -> None:
        """Open the source at `root`, given each name the class declares it needs or accepts."""

    @property
    def STATES(self) -> Mapping[str, str]:
        """Each `block.field` the source states, to the attribute holding its value (Part 05 §3.6)."""

    def records(self) -> Mapping[str, list[dict[str, Any]]]:
        """Return each table held as records, by resource ID."""

    def offers(self) -> Mapping[str, int]:
        """Return the rows of each table `records` and :meth:`Streams.batches` supply (Part 05 §4.1)."""


@runtime_checkable
class Streams(Protocol):
    """An adapter with tables too large to hold as records."""

    def batches(self) -> Mapping[str, Iterator[pa.RecordBatch]]:
        """Return each streamed table as batches in its declared order, by resource ID.

        A batch becomes one row group.
        """

    def stream_rows(self) -> Mapping[str, int]:
        """Return the rows of each table of `batches`, counted without reading them."""


@runtime_checkable
class StagesArrays(Protocol):
    """An adapter with dense arrays the packet will own."""

    def staged_arrays(self) -> Sequence[StagedArray]:
        """Return each array to stage."""


@runtime_checkable
class ReferencesArrays(Protocol):
    """An adapter with arrays the packet references where they lie (Part 04 §5.1)."""

    def external_arrays(self) -> Mapping[str, ExternalArray]:
        """Return each referenced array, by resource ID."""


@runtime_checkable
class ReferencesMedia(Protocol):
    """An adapter with media the packet references where they lie (Part 04 §5.1)."""

    def external_media(self) -> Mapping[str, ExternalMedia]:
        """Return each referenced media asset, by resource ID."""


@runtime_checkable
class StagesPayloads(Protocol):
    """An adapter with opaque payloads the packet will own (Part 12 §5)."""

    def staged_payloads(self) -> Iterable[Payload]:
        """Return each payload to write."""


@runtime_checkable
class DeclaresCompensations(Protocol):
    """An adapter that works around known defects of its source (Part 05 §4.3)."""

    #: The ID of each registered compensation this run applied.
    compensations: list[str]


@runtime_checkable
class WithholdsAnchors(Protocol):
    """An adapter that tests each clock's terminal anchors (Part 02 §12.6)."""

    #: Each clock the test examined, to an entry whose `anchors` lists `first`, `last` or neither and
    #: whose `n_withheld` counts them.
    withheld: Mapping[str, Mapping[str, Any]]


@runtime_checkable
class Located(Protocol):
    """An adapter that names the path it reads, which a message about its facts then names."""

    path: Any


__all__ = [
    "DeclaresCompensations",
    "Located",
    "ReferencesArrays",
    "ReferencesMedia",
    "SourceAdapter",
    "StagesArrays",
    "StagesPayloads",
    "Streams",
    "WithholdsAnchors",
]

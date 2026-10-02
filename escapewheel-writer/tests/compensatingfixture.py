"""An adapter applying one registered compensation as it reads, for a build to reach by any route."""

from typing import Any, ClassVar

from escapewheel_writer.sources.compensations import Compensates

#: The registered compensation `Keeping` applies.
APPLIED = "nwb.stored_offset_kept"


class Keeping(Compensates):
    """Own `core.media_assets`, deliver no row of it, and apply `APPLIED` while reading."""

    PROTOCOLS = ("files-v0.1", "stream-v0.1", "flight-v0.1")
    PRODUCES = frozenset({"core.media_assets"})
    CONTRIBUTES: frozenset[str] = frozenset()
    STATES: ClassVar[dict[str, str]] = {}
    NEEDS = ("root", "session_id")
    ACCEPTS: tuple[str, ...] = ()
    CONSUMES: tuple[str, ...] = ()

    def __init__(self, root: Any, *, session_id: str) -> None:
        super().__init__()
        self.notes: list[str] = []

    def records(self) -> dict[str, list[dict[str, Any]]]:
        self.compensate(APPLIED)
        return {}

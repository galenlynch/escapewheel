"""Which claims about stored bytes a validation establishes beyond structure.

- :class:`Verification` -- the verification modes of one validation, and whether they resolve
  external resources.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Verification:
    """The verification modes of one validation (Part 04 §5.3).

    The default establishes nothing beyond structure: structural validation reaches for no resource
    the packet does not own, since whether one is reachable is a property of the reader's situation
    and not of the packet.

    Attributes
    ----------
    checksums : bool
        Establish every recorded `digest`: each packet-owned resource (level 2) and each external
        one resolved (level 3c). Separate because reading costs every byte, and a packet may
        reference far more than it owns. The report names each digest's route.
    store_digests : bool
        Compare each external member's recorded `store_digest` against what the store reports
        now. It costs the listing resolving already performs, and it answers "has anything
        changed in place" rather than "are these the bytes". A member with nothing recorded, or a
        store offering nothing, is not checked, and the report says how many were skipped.
    store_checksums : bool
        With `checksums`, take a store's full-object checksums in the digest's algorithm in place of
        reading those objects. A composite value is never taken, an object the store reports nothing
        for is read, and a local packet has no store checksums to take.
    external : bool or None
        Resolve external URIs and check the `digest`, `size_bytes` and `members` claimed for them
        (level 3). An unreachable resource is a warning; one that resolves and disagrees with its
        claim is an error. None, the default, resolves them where `checksums` or `store_digests`
        asks for a comparison that needs it; False establishes packet-owned digests alone.
    """

    checksums: bool = False
    store_digests: bool = False
    store_checksums: bool = True
    external: bool | None = None

    @property
    def resolves_external(self) -> bool:
        """Whether this validation resolves external resources."""
        return (self.checksums or self.store_digests) if self.external is None else self.external


__all__ = ["Verification"]

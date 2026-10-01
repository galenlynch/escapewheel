"""Assign an integer to each thing a packet names (Part 05 §4.3).

- :class:`Keys` -- the numbers one packet assigns, per kind, and the name each stands for.

Numbers start at 0 in first-seen order, and every adapter of a build shares one `Keys`. An
amending build first holds every number the packet assigned, so a held name keeps its number and
a new name takes the number after the largest held.
"""

from __future__ import annotations


class Keys:
    """Integer identifiers for the things one packet names, and what each stands for.

    Examples
    --------
    >>> keys = Keys()
    >>> keys.of("probe", "Neuropix-PXI-100.46110")
    0
    >>> keys.of("probe", "Neuropix-PXI-100.46113")
    1
    >>> keys.of("probe", "Neuropix-PXI-100.46110")  # the same thing keeps its number
    0
    >>> keys.names("probe")
    {0: 'Neuropix-PXI-100.46110', 1: 'Neuropix-PXI-100.46113'}
    """

    def __init__(self) -> None:
        self._assigned: dict[str, dict[str, int]] = {}
        self._named: dict[str, dict[int, str]] = {}
        self._next: dict[str, int] = {}

    def of(self, kind: str, name: str) -> int:
        """Return the number for one named thing, assigning it if this is the first sight.

        Parameters
        ----------
        kind : str
            What sort of thing is being numbered -- `probe`, `clock`, `sorting_run`. Numbers
            restart per kind, since an identifier is only ever compared within its own column.
        name : str
            What the thing is called, which is what its `*_name` column will hold.
        """
        within = self._assigned.setdefault(kind, {})
        if name not in within:
            self.hold(kind, name, self._next.get(kind, 0))
        return within[name]

    def hold(self, kind: str, name: str, number: int) -> None:
        """Record a number already assigned to a name, so later names are numbered after it.

        Raises
        ------
        ValueError
            If the name already holds another number, or the number already names another thing.
        """
        within = self._assigned.setdefault(kind, {})
        named = self._named.setdefault(kind, {})
        if within.get(name, number) != number or named.get(number, name) != name:
            raise ValueError(f"{kind} {name!r} and {number} each already name something else")
        within[name] = number
        named[number] = name
        self._next[kind] = max(self._next.get(kind, 0), number + 1)

    def names(self, kind: str) -> dict[int, str]:
        """Return every number assigned for one kind, and what it stands for."""
        return dict(self._named.get(kind, {}))

    def name_of(self, kind: str, number: int) -> str | None:
        """Return what one number stands for, or None if this kind never assigned it."""
        return self._named.get(kind, {}).get(number)

    def __len__(self) -> int:
        """How many things have been numbered, across every kind."""
        return sum(len(within) for within in self._assigned.values())


__all__ = ["Keys"]

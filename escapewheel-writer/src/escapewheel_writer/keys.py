"""Assign an integer to each thing a packet names (Part 05 §4.3).

An identifier is `int32` and, where R53 §2.3 calls it **assigned**, this is what chooses the
number. Shared across adapters on purpose: the recipe exists because four sources can each
produce `core.probes`, and two of them numbering the same probe differently would be a defect no
foreign key could see -- both values resolve, to different rows.

A **carried** identifier does not come through here at all. `core.intervals.interval_id` is the
NWB's own `id`, so the writer passes it through rather than choosing. `core.units.unit_id` was
one until R81 §2.1: a sorter numbers from zero within each run, so its label named several units
and only the packet can say which is which.

Numbers are assigned in first-seen order and start at 0. Nothing depends on the order -- Part 05 §4.3
requires only that a key not move once committed -- but a deterministic one makes two builds of
the same sources produce the same packet, which is what lets a rebuild be compared to what it
replaced.
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
            within[name] = len(within)
        return within[name]

    def names(self, kind: str) -> dict[int, str]:
        """Return every number assigned for one kind, and what it stands for."""
        return {number: name for name, number in self._assigned.get(kind, {}).items()}

    def name_of(self, kind: str, number: int) -> str | None:
        """Return what one number stands for, or None if this kind never assigned it."""
        return self.names(kind).get(number)

    def __len__(self) -> int:
        """How many things have been numbered, across every kind."""
        return sum(len(within) for within in self._assigned.values())


__all__ = ["Keys"]

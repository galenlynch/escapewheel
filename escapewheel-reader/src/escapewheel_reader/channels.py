"""The electrode a sorter's channel index names (Part 02 §12.2).

- :func:`electrode_at` -- the electrode one index names, counting the channels its run kept.
- :func:`kept_channels` -- each run's kept channels, in the order the run counted them.
- :func:`runs_without_channels` -- the runs whose indices cannot be resolved.
- :class:`ChannelsUndeclared` -- a run whose kept channels the packet does not record.

An index counts the channels a sorter kept, not the probe's contacts, so reading it as a position
in `core.electrodes` names the wrong electrode.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .errors import PacketError, UnresolvableChannelIndex
from .protocols import PacketLike
from .resource_ids import CORE_SORTING_RUN_CHANNELS, CORE_SORTING_RUNS


@dataclass(frozen=True)
class ChannelsUndeclared:
    """A sorting run whose kept channels the packet does not record."""

    sorting_run_id: int
    session_id: int | None = None

    def __str__(self) -> str:
        """One line naming the run and what a caller cannot do with it."""
        where = f" in session {self.session_id}" if self.session_id is not None else ""
        return (
            f"sorting run {self.sorting_run_id}{where} declares no channels, so a channel "
            f"index into it names no electrode"
        )


def _rows(packet: PacketLike, resource_id: str, columns: list[str], *, required: bool = False) -> list[dict[str, Any]]:
    """Read named columns from a resource, or nothing where the packet holds it not at all.

    `core.sorting_run_channels` is optional, so a packet may carry no such resource and
    absence is ordinary rather than an error. A column is another matter where
    `required` says the registry requires it: a table missing one is not a run declaring no
    channels, and reading it as one is the silent wrong answer this module exists to prevent.
    """
    if resource_id not in {r.resource_id for r in packet.resources()}:
        return []
    held = set(packet.table_resource(resource_id).schema().names)
    if required and (absent := [c for c in columns if c not in held]):
        raise PacketError(f"{resource_id} carries no {', '.join(absent)}, which every row must")
    present = [c for c in columns if c in held]
    if not present:
        return []
    return [{c: row.get(c) for c in columns} for row in packet.table(resource_id, columns=present).to_pylist()]


def kept_channels(packet: PacketLike, *, sorting_run_id: int | None = None) -> dict[int, tuple[int, ...]]:
    """Return each run's kept electrodes, in the order the run counted them.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    sorting_run_id : int, optional
        One run. Every run the table records is the default.

    Returns
    -------
    dict
        `sorting_run_id` to its electrodes, position *n* holding what channel index *n* names.
        A run the packet records no channels for is **absent** rather than empty, since an empty
        list would say the run kept nothing.

    Raises
    ------
    PacketError
        Where the table carries none of a required column, or where a run's indices are not `0`
        to `n-1`, which `core.sorting_run_channels`'s own `index_contiguous` check refuses at
        error level. A tuple whose positions disagree with the indices they came from returns a
        wrong electrode and says nothing, so it is refused here too rather than assumed away in
        a packet this reader did not validate.
    """
    rows = _rows(packet, CORE_SORTING_RUN_CHANNELS, ["sorting_run_id", "channel_index", "electrode_id"], required=True)
    by_run: dict[int, list[tuple[int, int]]] = {}
    for row in rows:
        run = row["sorting_run_id"]
        if sorting_run_id is not None and run != sorting_run_id:
            continue
        by_run.setdefault(int(run), []).append((int(row["channel_index"]), int(row["electrode_id"])))
    kept = {}
    for run, pairs in by_run.items():
        pairs.sort()
        if [index for index, _ in pairs] != list(range(len(pairs))):
            raise PacketError(
                f"sorting run {run}: channel indices are not 0 to {len(pairs) - 1}, so a position "
                f"in this list is not the index it was recorded under "
                f"(core.sorting_run_channels.index_contiguous)"
            )
        kept[run] = tuple(electrode for _, electrode in pairs)
    return kept


def electrode_at(
    packet: PacketLike,
    sorting_run_id: int,
    channel_index: int | NDArray[np.integer[Any]] | list[int],
) -> int | NDArray[np.int32]:
    """Return the electrode a channel index names, counting the channels the run kept.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    sorting_run_id : int
        The run the index counts within. An index means nothing without it, because two runs on
        one probe may keep different channels.
    channel_index : int or array of int
        0-based, in the run's own order. An array resolves in one pass, which is what 6,781 units'
        peak channels need.

    Returns
    -------
    int or ndarray of int32
        The electrode, or one per index where several were asked for.

    Raises
    ------
    UnresolvableChannelIndex
        Where the run declares no channels, which is reported rather than resolved against
        `core.electrodes`, or where an index falls outside the list it declares.
        The exception's `channels_declared` tells the two apart.
    """
    kept = kept_channels(packet, sorting_run_id=sorting_run_id).get(sorting_run_id)
    asked = np.atleast_1d(np.asarray(channel_index, dtype=np.int64))
    if kept is None:
        raise UnresolvableChannelIndex(
            f"sorting run {sorting_run_id} declares no channels, so channel index "
            f"{asked[0] if asked.size == 1 else f'{asked.size} indices'} resolves to no electrode"
        )
    electrodes = np.asarray(kept, dtype=np.int32)
    outside = (asked < 0) | (asked >= electrodes.size)
    if outside.any():
        raise UnresolvableChannelIndex(
            f"sorting run {sorting_run_id} kept {electrodes.size} channels and "
            f"{int(outside.sum())} of the {asked.size} index(es) asked for fall outside them, "
            f"the first being {int(asked[outside][0])}",
            channels_declared=int(electrodes.size),
        )
    found = electrodes[asked]
    return int(found[0]) if np.ndim(channel_index) == 0 else found


def runs_without_channels(packet: PacketLike) -> tuple[ChannelsUndeclared, ...]:
    """Return every sorting run the packet records no channel list for.

    Reports rather than raises: a packet whose runs declare no channels is conforming, so the
    answer a consumer owes its caller is which indices it cannot resolve, not a failed read.

    Parameters
    ----------
    packet : Packet
        The packet to read.

    Returns
    -------
    tuple of ChannelsUndeclared
        One per run, ordered by run. Empty where every run declares its channels, and also where
        the packet declares no sorting runs at all.
    """
    declared = set(kept_channels(packet))
    runs = _rows(packet, CORE_SORTING_RUNS, ["sorting_run_id", "session_id"])
    return tuple(
        ChannelsUndeclared(sorting_run_id=int(row["sorting_run_id"]), session_id=row["session_id"])
        for row in sorted(runs, key=lambda r: int(r["sorting_run_id"]))
        if int(row["sorting_run_id"]) not in declared
    )


__all__ = [
    "ChannelsUndeclared",
    "electrode_at",
    "kept_channels",
    "runs_without_channels",
]

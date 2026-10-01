"""Which of several coexisting sortings, curations or models to read (Part 01 §2.6).

- :func:`ambiguities` -- the purposes with several runs and no preference, or no recorded scope.
- :func:`preferred_run` -- the run to read for one purpose.
- :func:`preferences` -- the preferences the packet declares.
- :func:`check` -- raise where a purpose is unresolved, and warn where it cannot be judged.
- :class:`Ambiguity` -- one unresolved purpose.

A purpose is `(session_id, activity_type, scope)`; an `import` run is in none.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .errors import AmbiguousRun, NotDeclared
from .protocols import PacketLike
from .resource_ids import CORE_PREFERRED_RUNS, CORE_PROCESSING_RUNS

#: The activity whose runs are never alternatives to one another (Part 05 §12).
IMPORT = "import"


@dataclass(frozen=True)
class Ambiguity:
    """Several runs share a purpose and the packet does not say which to read."""

    session_id: int | None
    activity_type: str
    scope_kind: str | None
    scope: str | None
    run_ids: tuple[int, ...]

    @property
    def determinable(self) -> bool:
        """Whether the packet said what these runs are about.

        False means the runs may be alternatives or may be complementary and nothing in the
        packet distinguishes them, which calls for a different fix than a missing preference:
        record the scopes, rather than choose between the runs.
        """
        return self.scope is not None

    def __str__(self) -> str:
        """One line naming the purpose and the runs competing for it.

        The run list is truncated because a re-sorted session has one ambiguity per probe and
        each names a dozen runs; the full list is on `run_ids` for a caller that wants it.
        """
        about = f"{self.scope} in {self.scope_kind}" if self.determinable else "an unrecorded scope"
        listed = sorted(self.run_ids)
        shown = ", ".join(str(run_id) for run_id in listed[:3]) + (
            f", +{len(listed) - 3} more" if len(listed) > 3 else ""
        )
        return f"{self.activity_type} for {about}: {len(self.run_ids)} runs ({shown})"


def _rows(packet: PacketLike, resource_id: str, columns: list[str]) -> list[dict[str, Any]]:
    """Read named columns from a resource, or nothing when the packet lacks it or them.

    Every column here arrived in a revision and all of them are optional, so absence is the
    normal case rather than an error: a packet predating R41 declares no runs at all, and one
    predating R44 declares runs without scopes.
    """
    if resource_id not in {r.resource_id for r in packet.resources()}:
        return []
    present = [c for c in columns if c in packet.table_resource(resource_id).schema().names]
    if not present:
        return []
    rows = packet.table(resource_id, columns=present).to_pylist()
    return [{c: row.get(c) for c in columns} for row in rows]


def preferences(packet: PacketLike) -> dict[tuple[int | None, str, str, str], int]:
    """Return the declared preferences, keyed by purpose (Part 01 §2.6).

    Parameters
    ----------
    packet : Packet
        The packet to read.

    Returns
    -------
    dict
        ``(session_id, activity_type, scope_kind, scope)`` to the preferred
        ``processing_run_id``. Empty
        when the packet declares no preferences, which is most of them.
    """
    columns = ["session_id", "activity_type", "scope_kind", "scope", "processing_run_id"]
    rows = _rows(packet, CORE_PREFERRED_RUNS, columns)
    return {
        (row["session_id"], row["activity_type"], row["scope_kind"], row["scope"]): row["processing_run_id"]
        for row in rows
        if row["processing_run_id"] is not None
    }


def ambiguities(packet: PacketLike) -> tuple[Ambiguity, ...]:
    """Return the purposes this packet has more than one run for and does not choose between.

    Runs are grouped by ``(session_id, activity_type, scope)``, which is the key
    `core.preferred_runs` is filed under. **Grouping without the scope is the way to get this
    wrong**: twelve probes sorted once each share an activity and are complementary, and a
    grouping that ignores scope reports twelve alternatives where there are none.

    A run whose `scope` is null is grouped alone and reported as undeterminable if its activity
    has other runs, rather than assumed unique (Part 01 §2.6). An `import` run is skipped, since
    imports are not alternatives to one another (Part 05 §12).

    Parameters
    ----------
    packet : Packet
        The packet to read.

    Returns
    -------
    tuple of Ambiguity
        Unresolved purposes, ordered by activity then scope. Empty means every purpose has one
        run or a declared preference.

    Notes
    -----
    Reads the run log once and memoises on the packet, which owns the cache because the answer
    is a property of the packet's bytes. Costs 0.8 ms otherwise, against 6 ms for the accessor
    it guards, and `spike_times` is called once per unit.
    """
    cached = getattr(packet, "_ambiguity_cache", None)
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    rows = _rows(
        packet, CORE_PROCESSING_RUNS, ["processing_run_id", "session_id", "activity_type", "scope_kind", "scope"]
    )
    declared = preferences(packet) if rows else {}

    grouped: dict[tuple[int | None, str, str | None, str | None], list[int]] = {}
    unscoped: dict[tuple[int | None, str], list[int]] = {}
    for row in rows:
        if row["activity_type"] in (None, IMPORT) or row["processing_run_id"] is None:
            continue
        key = (row["session_id"], row["activity_type"], row["scope_kind"], row["scope"])
        grouped.setdefault(key, []).append(row["processing_run_id"])
        if row["scope"] is None:
            unscoped.setdefault((row["session_id"], row["activity_type"]), []).append(row["processing_run_id"])

    found = []
    for (session_id, activity_type, scope_kind, scope), run_ids in grouped.items():
        if scope is None:
            # Every unscoped run of an activity landed in one group by accident of them all
            # being keyed None, so the group size says nothing. What matters is whether the
            # activity has more than one run at all: if it does, the packet cannot say whether
            # they compete.
            if len(unscoped[(session_id, activity_type)]) > 1:
                found.append(Ambiguity(session_id, activity_type, None, None, tuple(run_ids)))
            continue
        if len(run_ids) > 1 and (session_id, activity_type, scope_kind, scope) not in declared:
            found.append(Ambiguity(session_id, activity_type, scope_kind, scope, tuple(run_ids)))
    out = tuple(sorted(found, key=lambda a: (a.activity_type, a.scope or "")))
    if hasattr(packet, "_ambiguity_cache"):
        packet._ambiguity_cache = out
    return out


def preferred_run(
    packet: PacketLike,
    activity_type: str,
    scope_kind: str,
    scope: str,
    *,
    session_id: int | None = None,
) -> int:
    """Return the run to read for one purpose.

    Parameters
    ----------
    packet : Packet
        The packet to read.
    activity_type : str
        Which kind of output, e.g. ``spike_sorting``. Open (Part 02 §9.3).
    scope_kind : str
        The resource whose primary key `scope` holds, as a dotted resource ID (R49 §2.2) --
        ``core.probes``, ``core.sorting_runs``, ``core.sessions``.
    scope : str
        The thing the run is about: the scoped row's key where that key is carried, and its
        `*_name` where it is assigned, as `core.processing_runs.scope` names it.
    session_id : int, optional
        Which session. Required only for a multi-session packet.

    Returns
    -------
    int
        The preferred ``processing_run_id``.

    Raises
    ------
    AmbiguousRun
        If several runs share the purpose and none is preferred (Part 01 §2.6).
    NotDeclared
        If no run matches the purpose at all.
    """
    rows = _rows(
        packet, CORE_PROCESSING_RUNS, ["processing_run_id", "session_id", "activity_type", "scope_kind", "scope"]
    )
    matching = [
        row
        for row in rows
        if row["activity_type"] == activity_type
        and row["scope_kind"] == scope_kind
        and row["scope"] == scope
        and (session_id is None or row["session_id"] == session_id)
    ]
    if not matching:
        raise NotDeclared(f"no {activity_type!r} run for scope {scope!r} in {scope_kind!r}")

    sessions = {row["session_id"] for row in matching}
    for candidate in sessions:
        declared = preferences(packet).get((candidate, activity_type, scope_kind, scope))
        if declared is not None:
            return int(declared)
    if len(matching) == 1:
        # Part 01 §2.6: exactly one run is the preference by construction.
        return int(matching[0]["processing_run_id"])
    raise AmbiguousRun(
        f"{len(matching)} runs produced {activity_type!r} for {scope!r} and none is preferred; "
        f"declare one in {CORE_PREFERRED_RUNS} (Part 01 §2.6)"
    )


def check(packet: PacketLike, activities: Iterable[str] | None = None) -> None:
    """Raise if the packet leaves a purpose unresolved, warn if it cannot tell.

    Called by the accessors that would otherwise concatenate alternatives. Reports every
    unresolved purpose at once rather than the first, because a re-sorted session has one per
    probe and fixing them one error at a time is twelve round trips.

    **The two states are treated differently on purpose.** A packet that records scopes and
    still has two runs for one of them is unresolved, and Part 01 §2.6 forbids choosing, so it
    raises. A packet that records no scopes cannot be judged either way, and Part 01 §2.6 asks for
    that to be *reported* distinctly rather than refused -- the two call for different fixes,
    declare a preference against record the scopes, and an exception for both would send a
    writer to the wrong one.

    Parameters
    ----------
    packet : Packet
        The packet to check.
    activities : iterable of str, optional
        Restrict to these activity types. An accessor passes the activities that produce what
        it returns, so a second pose-estimation run does not stop anyone reading units. This
        is not the core-table mapping R44 §2.4 rejects: an accessor already names one
        resource, and this names what produces it. Checking everything is the default.

    Raises
    ------
    AmbiguousRun
        If any purpose has several runs, a declared scope, and no preference.

    Warns
    -----
    UserWarning
        If an activity has several runs whose scopes are unrecorded.
    """
    found = ambiguities(packet)
    if activities is not None:
        wanted = set(activities)
        found = tuple(a for a in found if a.activity_type in wanted)
    if not found:
        return
    unresolved = [a for a in found if a.determinable]
    unknown = [a for a in found if not a.determinable]
    if unknown:
        lines = "\n  ".join(str(a) for a in unknown)
        warnings.warn(
            f"cannot tell whether these runs are alternatives or complementary:\n  {lines}\n"
            f"record each run's scope in {CORE_PROCESSING_RUNS} (R44 §2.1)",
            stacklevel=2,
        )
    if unresolved:
        lines = "\n  ".join(str(a) for a in unresolved)
        raise AmbiguousRun(
            f"the packet does not say which run to read:\n  {lines}\n"
            f"declare a preference in {CORE_PREFERRED_RUNS} (Part 01 §2.6)"
        )


__all__ = ["Ambiguity", "ambiguities", "preferred_run"]

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

import pyarrow as pa
import pyarrow.compute as pc

from .dictionaries import plain
from .errors import AmbiguousRun, NotDeclared
from .optional import read_optional
from .protocols import Memo, PacketLike
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


#: A purpose's columns, the key `core.preferred_runs` is filed under.
_PURPOSE = ["session_id", "activity_type", "scope_kind", "scope"]


def _runs(packet: PacketLike) -> pa.Table:
    """Read the run log; a packet may declare no runs at all, or runs without scopes."""
    return read_optional(packet, CORE_PROCESSING_RUNS, ["processing_run_id", *_PURPOSE])


def preferences(packet: PacketLike) -> dict[tuple[int | None, str, str, str], int]:
    """Return the declared preferences, keyed by purpose.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.

    Returns
    -------
    dict
        ``(session_id, activity_type, scope_kind, scope)`` to the preferred
        ``processing_run_id``. Empty
        when the packet declares no preferences, which is most of them.
    """
    table = read_optional(packet, CORE_PREFERRED_RUNS, [*_PURPOSE, "processing_run_id"])
    table = table.filter(pc.is_valid(table.column("processing_run_id")))
    return {tuple(row[c] for c in _PURPOSE): row["processing_run_id"] for row in table.to_pylist()}


def ambiguities(packet: PacketLike) -> tuple[Ambiguity, ...]:
    """Return the purposes this packet has more than one run for and does not choose between.

    Runs are grouped by ``(session_id, activity_type, scope)``, which is the key
    `core.preferred_runs` is filed under. **Grouping without the scope is the way to get this
    wrong**: twelve probes sorted once each share an activity and are complementary, and a
    grouping that ignores scope reports twelve alternatives where there are none.

    A run whose `scope` is null is grouped alone and reported as undeterminable if its activity
    has other runs, rather than assumed unique. An `import` run is skipped, since imports are
    not alternatives to one another.

    Parameters
    ----------
    packet : PacketLike
        The packet to read.

    Returns
    -------
    tuple of Ambiguity
        Unresolved purposes, ordered by activity then scope. Empty means every purpose has one
        run or a declared preference.

    Notes
    -----
    Reads the run log once and keeps the answer in the packet's memo, because `spike_times`
    checks it once per unit.
    """
    memo = Memo.of(packet)
    if memo.ambiguities is not None:
        return memo.ambiguities

    runs = _runs(packet)
    if not runs.num_rows:
        memo.ambiguities = ()
        return ()
    activity = plain(runs.column("activity_type"))
    alternatives = pc.and_(
        pc.is_valid(runs.column("processing_run_id")),
        pc.invert(pc.fill_null(pc.equal(activity, pa.scalar(IMPORT, activity.type)), True)),
    )
    runs = runs.filter(alternatives)
    declared = preferences(packet) if runs.num_rows else {}
    scoped = pc.is_valid(runs.column("scope"))

    found = [
        Ambiguity(group["session_id"], group["activity_type"], group["scope_kind"], group["scope"], tuple(ids))
        for group in _grouped(runs.filter(scoped), _PURPOSE)
        if len(ids := group["processing_run_id_list"]) > 1 and tuple(group[c] for c in _PURPOSE) not in declared
    ]
    # Unscoped runs cannot be told apart, so an activity with more than one cannot say whether
    # they compete.
    found += [
        Ambiguity(group["session_id"], group["activity_type"], None, None, tuple(ids))
        for group in _grouped(runs.filter(pc.invert(scoped)), ["session_id", "activity_type"])
        if len(ids := group["processing_run_id_list"]) > 1
    ]
    out = tuple(sorted(found, key=lambda a: (a.activity_type, a.scope or "")))
    memo.ambiguities = out
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
    packet : PacketLike
        The packet to read.
    activity_type : str
        Which kind of output, e.g. ``spike_sorting``. An open vocabulary.
    scope_kind : str
        The resource whose primary key `scope` holds, as a dotted resource ID --
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
        If several runs share the purpose and none is preferred.
    NotDeclared
        If no run matches the purpose at all.
    """
    runs = _runs(packet)
    asked: dict[str, Any] = {"activity_type": activity_type, "scope_kind": scope_kind, "scope": scope}
    if session_id is not None:
        asked["session_id"] = session_id
    for name, value in asked.items():
        column = plain(runs.column(name))
        if pa.types.is_null(column.type):
            runs = runs.slice(0, 0)
            break
        runs = runs.filter(pc.fill_null(pc.equal(column, pa.scalar(value, column.type)), False))
    matching = runs.to_pylist()
    if not matching:
        raise NotDeclared(f"no {activity_type!r} run for scope {scope!r} in {scope_kind!r}")

    sessions = {row["session_id"] for row in matching}
    for candidate in sessions:
        declared = preferences(packet).get((candidate, activity_type, scope_kind, scope))
        if declared is not None:
            return int(declared)
    if len(matching) == 1:
        # Exactly one run is the preference by construction.
        return int(matching[0]["processing_run_id"])
    raise AmbiguousRun(
        f"{len(matching)} runs produced {activity_type!r} for {scope!r} and none is preferred; "
        f"declare one in {CORE_PREFERRED_RUNS} (Part 05 §12)"
    )


def _grouped(runs: pa.Table, keys: list[str]) -> list[dict[str, Any]]:
    """Group runs by `keys`, each group's run IDs listed in log order."""
    return runs.group_by(keys, use_threads=False).aggregate([("processing_run_id", "list")]).to_pylist()


def check(packet: PacketLike, activities: Iterable[str] | None = None) -> None:
    """Raise if the packet leaves a purpose unresolved, warn if it cannot tell.

    Called by the accessors that would otherwise concatenate alternatives. Reports every
    unresolved purpose at once rather than the first, because a re-sorted session has one per
    probe and fixing them one error at a time is twelve round trips.

    **The two states are treated differently on purpose.** A packet that records scopes and
    still has two runs for one of them is unresolved, and a consumer may not choose, so it
    raises. A packet that records no scopes cannot be judged either way, which is *reported*
    distinctly rather than refused -- the two call for different fixes, declare a preference
    against record the scopes, and an exception for both would send a writer to the wrong one.

    Parameters
    ----------
    packet : PacketLike
        The packet to check.
    activities : iterable of str, optional
        Restrict to these activity types. An accessor passes the activities that produce what
        it returns, so a second pose-estimation run does not stop anyone reading units. This
        is no general map from an activity to its tables: an accessor already names one
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
            f"record each run's scope in {CORE_PROCESSING_RUNS} (Part 05 §12)",
            stacklevel=2,
        )
    if unresolved:
        lines = "\n  ".join(str(a) for a in unresolved)
        raise AmbiguousRun(
            f"the packet does not say which run to read:\n  {lines}\n"
            f"declare a preference in {CORE_PREFERRED_RUNS} (Part 05 §12)"
        )


__all__ = ["Ambiguity", "ambiguities", "preferred_run"]

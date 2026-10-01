"""Compare an amendment with the version it supersedes (Part 05 §15.6).

- :func:`compare` -- the changes an amendment made that Part 05 §15.6 forbids, each as a
  :class:`Finding`.
- :func:`predecessor` -- the retained manifest whose version immediately precedes the current one.
- :class:`Version` -- one version's canonical tables as DuckDB views, and the SQL saying whether
  it holds a row's group.
- :func:`group_lists`, :func:`chain_reaches` -- a table's group lists, and the first of some
  resources a `derived_from` chain reaches.
- :func:`semver`, :func:`quoted`, :func:`literal`, :func:`absent` -- a `packet_version` as a sort
  key, and the SQL for an identifier, a string, and a column a file omits.
- :data:`PREFERENCES`, :data:`DERIVED` -- the one table whose held row an amendment may replace,
  and the content classes whose lineage can go stale.

A writer settling delivered rows against the packet it amends uses :class:`Version`'s group test
too (Part 02 §2.8), so the two cannot disagree about which groups a version holds.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from escapewheel_reader.manifest import MANIFESTS_DIRNAME
from escapewheel_reader.resource_ids import (
    CORE_PREFERRED_RUNS,
    CORE_PROCESSING_RUN_INPUTS,
    CORE_PROCESSING_RUNS,
    CORE_SOURCE_FILES,
)

from . import check_table
from .check_table import CheckEntry

#: Tables whose rows record what ran rather than what was measured, so writing one leaves no derived
#: resource stale (Part 05 §15.2).
PROVENANCE = frozenset({CORE_PROCESSING_RUNS, CORE_SOURCE_FILES, CORE_PROCESSING_RUN_INPUTS})

#: The one table whose held row an amendment may replace (Part 05 §15.2).
PREFERENCES = CORE_PREFERRED_RUNS

#: Content classes an amendment may remove or replace, and whose lineage can go stale.
DERIVED = frozenset({"analysis", "compatibility_projection"})

#: The packet-level fields no amendment changes (Part 05 §15.2).
IDENTITY = ("packet_id", "profile_id", "semantic_standard_version", "logical_standard_version")

#: Rows kept per finding, as `Report.add` keeps.
SHOWN = 5


def semver(text: str) -> tuple[int, ...]:
    """Order a `packet_version` (Part 05 §15.1); a part that is not a number sorts first."""
    return tuple(int(part) if part.isdigit() else -1 for part in str(text).split("."))


def quoted(name: str) -> str:
    """Quote an SQL identifier."""
    return '"' + name.replace('"', '""') + '"'


def literal(text: str) -> str:
    """Quote an SQL string literal."""
    return "'" + text.replace("'", "''") + "'"


def predecessor(root: Path, current: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return the retained manifest whose `packet_version` immediately precedes the current one.

    None where the packet retains none that precedes it, which leaves nothing to compare.

    Raises
    ------
    OSError or ValueError
        If a retained manifest cannot be read, since it might be the predecessor.
    """
    folder = root / MANIFESTS_DIRNAME
    if not folder.is_dir():
        return None
    here = semver(str(current.get("packet_version", "")))
    best: Mapping[str, Any] | None = None
    for path in sorted(folder.glob("*.json")):
        document = json.loads(path.read_text())
        version = semver(str(document.get("packet_version", "")))
        if version < here and (best is None or version > semver(str(best["packet_version"]))):
            best = document
    return best


def absent(column: Mapping[str, Any]) -> str:
    """Return SQL selecting a column a file omits, as a null of its declared type (Part 05 §15.6)."""
    from .validator import DDL

    return f"CAST(NULL AS {DDL.get(str(column.get('type')), 'VARCHAR')}) AS {quoted(column['name'])}"


def group_lists(spec: Mapping[str, Any]) -> list[list[str]]:
    """Return a table's group lists, empty where it declares `[]` or none."""
    return [list(members) for members in spec.get("amendment_groups") or ()]


class Version:
    """One packet version's canonical tables, registered as DuckDB views over their files.

    Parameters
    ----------
    connection : duckdb.DuckDBPyConnection
        Where the views go.
    name : str
        Prefix for this version's views, unique on the connection.
    tables : Mapping
        Resource ID to table declaration, from the registries the amended manifest binds: every
        comparison reads columns by those declarations (Part 05 §15.6).
    path_of : callable
        Resource ID to the file this version names for it, or None where it names none.
    """

    def __init__(
        self,
        connection: Any,
        name: str,
        tables: Mapping[str, Mapping[str, Any]],
        path_of: Callable[[str], Path | None],
    ) -> None:
        self.connection = connection
        self.name = name
        self.tables = tables
        self.path_of = path_of
        self._views: dict[str, str] = {}
        self._groups: dict[tuple[str, tuple[str, ...]], str] = {}

    def columns(self, resource_id: str) -> list[str]:
        """Return the declared columns of one table."""
        return [c["name"] for c in self.tables[resource_id]["columns"]]

    def view(self, resource_id: str) -> str:
        """Return a view of the table's rows over every declared column, empty where not named.

        An `optional` column the file omits reads as null (Part 05 §15.6), as does a canonical
        table the manifest does not name, which holds no rows (Part 02 §2.8).
        """
        if resource_id in self._views:
            return self._views[resource_id]
        view = quoted(f"{self.name}__{resource_id}")
        columns = self.tables[resource_id]["columns"]
        path = self.path_of(resource_id)
        if path is None:
            select = ", ".join(absent(c) for c in columns)
            body = f"SELECT {select} WHERE false"
        else:
            present = set(pq.read_schema(path).names)
            select = ", ".join(quoted(c["name"]) if c["name"] in present else absent(c) for c in columns)
            body = f"SELECT {select} FROM read_parquet({literal(str(path))})"
        self.connection.execute(f"CREATE OR REPLACE TEMP VIEW {view} AS {body}")
        self._views[resource_id] = view
        return view

    def _distinct(self, resource_id: str, members: Sequence[str]) -> str:
        """Return a table of the distinct values this version's rows hold under `members`."""
        key = (resource_id, tuple(members))
        if key not in self._groups:
            table = quoted(f"{self.name}__{resource_id}__{len(self._groups)}")
            listed = ", ".join(quoted(m) for m in members)
            self.connection.execute(
                f"CREATE OR REPLACE TEMP TABLE {table} AS SELECT DISTINCT {listed} FROM {self.view(resource_id)}"
            )
            self._groups[key] = table
        return self._groups[key]

    def holds(self, resource_id: str, members: Sequence[str], alias: str) -> str:
        """Return SQL true where this version holds the group of `alias`'s row under `members`.

        Part 02 §2.8: a version holds a group where it holds one of the group's rows, or where the
        list carries a reference to a table not declaring `[]` and every such reference resolves,
        on the group's values, to a row the version holds.
        """
        match = " AND ".join(f"g.{quoted(m)} IS NOT DISTINCT FROM {alias}.{quoted(m)}" for m in members)
        clauses = [f"EXISTS (SELECT 1 FROM {self._distinct(resource_id, members)} AS g WHERE {match})"]
        carried = []
        for reference in self.tables[resource_id].get("references", ()):
            target = self.tables.get(reference["resource"])
            if target is None or not group_lists(target) or not set(reference["columns"]) <= set(members):
                continue
            others = [m for m in members if m not in reference["columns"]]
            if not set(others) <= {c["name"] for c in target["columns"]}:
                continue
            on = [
                f"r.{quoted(theirs)} = {alias}.{quoted(ours)}"
                for ours, theirs in zip(reference["columns"], reference["resource_columns"], strict=True)
            ] + [f"r.{quoted(m)} IS NOT DISTINCT FROM {alias}.{quoted(m)}" for m in others]
            carried.append(f"EXISTS (SELECT 1 FROM {self.view(reference['resource'])} AS r WHERE {' AND '.join(on)})")
        if carried:
            clauses.append("(" + " AND ".join(carried) + ")")
        return "(" + " OR ".join(clauses) + ")"

    def grows(self, resource_id: str, alias: str) -> str:
        """Return SQL true where `alias`'s row forms, under no group list, a group this version lacks."""
        lists = group_lists(self.tables[resource_id])
        if not lists:
            return "true"
        return "(" + " AND ".join(self.holds(resource_id, members, alias) for members in lists) + ")"


def _key_match(spec: Mapping[str, Any], left: str, right: str) -> str:
    """Return SQL matching two aliases' rows on the table's primary key."""
    return " AND ".join(
        f"{left}.{quoted(k)} IS NOT DISTINCT FROM {right}.{quoted(k)}" for k in spec.get("primary_key") or ()
    )


def _rows(connection: Any, query: str) -> tuple[int, list[tuple[Any, ...]]]:
    """Return how many rows a query yields and the first few."""
    count = connection.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]
    shown = connection.execute(f"SELECT * FROM ({query}) LIMIT {SHOWN}").fetchall() if count else []
    return int(count), shown


def chain_reaches(entries: Mapping[str, Mapping[str, Any]], start: str, targets: Collection[str]) -> str | None:
    """Return the first of `targets` a resource's `derived_from` chain reaches, or None."""
    seen: set[str] = set()
    pending = list(entries.get(start, {}).get("derived_from", ()))
    while pending:
        resource = pending.pop()
        if resource in targets:
            return resource
        if resource in seen:
            continue
        seen.add(resource)
        pending.extend(entries.get(resource, {}).get("derived_from", ()))
    return None


@dataclass(frozen=True)
class Finding:
    """One comparison finding, about a resource or, where `resource` is None, the packet."""

    check: CheckEntry
    resource: str | None
    message: str
    rows: Sequence[Sequence[Any]] = ()


def compare(
    connection: Any,
    current: Mapping[str, Any],
    superseded: Mapping[str, Any],
    *,
    tables: Mapping[str, Mapping[str, Any]],
    classes: Mapping[str, str | None],
    kinds: Mapping[str, str | None],
    current_path: Callable[[str], Path | None],
    superseded_path: Callable[[str], Path | None],
) -> list[Finding]:
    """Compare two manifests and their tables as Part 05 §15.6 requires.

    Parameters
    ----------
    connection : duckdb.DuckDBPyConnection
        Where the comparison runs, already bounded by the caller's limits.
    current, superseded : Mapping
        The amended manifest and the one it supersedes.
    tables : Mapping
        Resource ID to table declaration, from the registries the amended manifest binds.
    classes, kinds : Mapping
        Resource ID to its declaration's content class and kind, for every resource either
        manifest names.
    current_path, superseded_path : callable
        Resource ID to the file each version names for a table, or None.

    Raises
    ------
    OSError or pyarrow.ArrowException or duckdb.Error
        If a file either version names cannot be read, which leaves the comparison incomplete
        rather than reporting a finding.
    """
    found: list[Finding] = []
    changed = [(f, superseded.get(f), current.get(f)) for f in IDENTITY if current.get(f) != superseded.get(f)]
    before_version, version = (str(m.get("packet_version", "")) for m in (superseded, current))
    if before_version.split(".", 1)[0] != version.split(".", 1)[0]:
        changed.append(("the major version of packet_version", before_version, version))
    # An absent member differs from any present one, and two arrays by their items in order.
    if current.get("replaces") != superseded.get("replaces"):
        changed.append(("replaces", json.dumps(superseded.get("replaces")), json.dumps(current.get("replaces"))))
    if changed:
        found.append(
            Finding(
                check_table.AMENDMENT_IDENTITY_CHANGED,
                None,
                f"the amendment changes {', '.join(f for f, _, _ in changed)}, which no amendment changes "
                "(Part 05 §15.2)",
                changed,
            )
        )

    now = {e["resource_id"]: e for e in current.get("resources", ())}
    before = {e["resource_id"]: e for e in superseded.get("resources", ())}
    canonical = {r for r, c in classes.items() if c in {"core", "extension"}}
    for resource in sorted(set(before) & canonical):
        if resource not in now:
            found.append(
                Finding(
                    check_table.AMENDMENT_RESOURCE_CHANGED, resource, f"{resource} is removed; no amendment removes one"
                )
            )
        elif now[resource].get("uri") != before[resource].get("uri") and kinds.get(resource) != "table":
            found.append(
                Finding(
                    check_table.AMENDMENT_RESOURCE_CHANGED,
                    resource,
                    f"{resource} is named at another uri; no amendment changes a canonical resource but a table",
                    [(before[resource].get("uri"), now[resource].get("uri"))],
                )
            )

    written = {r for r, e in now.items() if r not in before or before[r].get("uri") != e.get("uri")}
    old = Version(connection, "superseded", tables, superseded_path)
    new = Version(connection, "current", tables, current_path)
    for resource in sorted(written & canonical):
        if kinds.get(resource) != "table" or resource not in tables:
            continue
        found.extend(_compare_table(connection, resource, tables[resource], old, new, resource in before))

    stale_sources = (written & canonical) - PROVENANCE
    for resource in sorted(set(now) & set(before)):
        if classes.get(resource) not in DERIVED or now[resource].get("uri") != before[resource].get("uri"):
            continue
        reached = chain_reaches(now, resource, stale_sources) or chain_reaches(before, resource, stale_sources)
        if reached is not None:
            found.append(
                Finding(
                    check_table.AMENDMENT_DERIVED_RESOURCE_STALE,
                    resource,
                    f"{resource} is kept at its uri, and its derived_from chain reaches {reached}, which the "
                    "amendment writes; derive it again or remove it (Part 05 §15.2)",
                )
            )
    return found


def _compare_table(
    connection: Any, resource: str, spec: Mapping[str, Any], old: Version, new: Version, named_before: bool
) -> list[Finding]:
    """Report one written table's changed rows and grown groups."""
    found = []
    columns = ", ".join(quoted(c) for c in new.columns(resource))
    before, after = old.view(resource), new.view(resource)
    if resource == PREFERENCES:
        # A preference replaced by one of the same key changes no row a run produced.
        same = _key_match(spec, "o", "n")
        kept = f"SELECT {columns} FROM {before} AS o WHERE NOT EXISTS (SELECT 1 FROM {after} AS n WHERE {same})"
        fresh = f"SELECT {columns} FROM {after} AS n WHERE NOT EXISTS (SELECT 1 FROM {before} AS o WHERE {same})"
    else:
        kept = f"SELECT {columns} FROM {before}"
        fresh = f"SELECT {columns} FROM {after}"
    if named_before:
        count, shown = _rows(connection, f"{kept} EXCEPT ALL SELECT {columns} FROM {after}")
        if count:
            found.append(
                Finding(
                    check_table.AMENDMENT_ROW_CHANGED,
                    resource,
                    f"{resource}: {count:,} superseded row(s) the amendment does not hold unchanged; an amendment "
                    "changes and removes no canonical row (Part 05 §15.2)",
                    shown,
                )
            )
    added = f"{fresh} EXCEPT ALL SELECT {columns} FROM {before}"
    members = list(dict.fromkeys(m for group in group_lists(spec) for m in group))
    listed = ", ".join(quoted(m) for m in members)
    if members:
        grouped = f"SELECT {listed}, COUNT(*) AS n_rows FROM ({added}) GROUP BY ALL"
        query = f"SELECT a.* FROM ({grouped}) AS a WHERE {old.grows(resource, 'a')}"
        total = connection.execute(f"SELECT COALESCE(SUM(n_rows), 0) FROM ({query})").fetchone()[0]
        shown = connection.execute(f"SELECT * FROM ({query}) LIMIT {SHOWN}").fetchall() if total else []
    else:
        total, shown = _rows(connection, added)
    if total:
        why = (
            "the table declares no group list"
            if not members
            else "the superseded version holds each row's group under every group list"
        )
        found.append(
            Finding(
                check_table.AMENDMENT_GROUP_GROWN,
                resource,
                f"{resource}: {int(total):,} added row(s) join groups the superseded version holds: {why} "
                "(Part 05 §15.2)",
                shown,
            )
        )
    return found


__all__ = [
    "DERIVED",
    "IDENTITY",
    "PREFERENCES",
    "PROVENANCE",
    "Finding",
    "Version",
    "absent",
    "chain_reaches",
    "compare",
    "group_lists",
    "predecessor",
    "quoted",
    "semver",
]

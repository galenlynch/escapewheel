"""Generate Tier 1 validation checks from a registry.

Tier 1 follows from structure alone (R2 §7.1): required columns, primary keys, foreign
keys, closed vocabularies. Nothing here is written per table. Tier 2 rules carried in the
registry are passed through unchanged.

Every check is SQL returning offending rows; an empty result is a pass (R2 §7.3).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from nwb_lake_reader import quote, sql_name


@dataclass(frozen=True)
class Check:
    """One validation check.

    Attributes
    ----------
    id : str
        Stable identifier, e.g. ``core.trials.primary_key_unique``.
    level : str
        ``error``, ``warning``, or ``info``.
    message : str
        What a non-empty result means.
    sql : str
        A query returning offending rows.
    resource : str
        The resource the check is declared on. Not necessarily the only one its query reads.
    """

    id: str
    level: str
    message: str
    sql: str
    resource: str


def concerns(check: Check, written: Collection[str]) -> bool:
    """Whether R35 §5 obliges `check` to run when `written` are the resources just written.

    A check must run when it is attached to one of them, or when its query names one. Anything
    else reads only files an amendment may not modify (R32 §3) and R14 §2.3 declares immutable,
    so it can only reach the verdict it reached before.

    The test is syntactic, over the flattened name a query must use (R2 §7), because that is
    what makes it sound without the registry having to promise that no existing rule references
    a resource added later. It is deliberately over-inclusive: a match inside a string literal
    or a comment re-runs a check that did not need it, which costs time, where missing one costs
    correctness.
    """
    if check.resource in written:
        return True
    return any(sql_name(resource) in check.sql for resource in written)


def adjacency_settles_uniqueness(table: Mapping[str, Any]) -> bool:
    """Whether a table's sort order puts duplicate primary keys next to each other.

    Two rows sharing a key are neighbours when nothing in the sort can order between them. That
    holds when every sort column up to and including the last key column is either a key column
    itself, or one the registry declares `determined_by` a subset of the key: a column that is a
    function of the key takes the same value in both rows, so it cannot separate them.

    `analysis.spike_events` is the case that needs the second clause. R30 §3.2 sorts it by
    `(session_id, clock_id, time_bucket_tick, …)` so a time filter and a unit filter both prune,
    which puts two non-key columns ahead of the key — but `clock_id` is the session's reference
    clock and `time_bucket_tick` is a function of `t_tick`, so neither varies between rows that
    share a key. Without the declaration a 287 M-row `GROUP BY` runs and spills 27 GB to settle
    what one comparison per row already answers.

    False where a sort column genuinely varies within a key: a sort of `(a, x, b)` with key
    `(a, b)` lets `x` order duplicates apart, so neighbours are not enough and the aggregate is
    the only correct check.
    """
    key = table.get("primary_key")
    sort = table.get("sort")
    if not key or not sort:
        return False
    determined = {c["name"]: set(c["determined_by"]) for c in table.get("columns", []) if "determined_by" in c}
    positions = [sort.index(k) for k in key if k in sort]
    if len(positions) != len(key):
        return False
    return all(column in key or determined.get(column, {object()}) <= set(key) for column in sort[: max(positions) + 1])


def generate(
    registry: Mapping[str, Any],
    *,
    only: set[str] | None = None,
    advisory: bool = False,
    aggregate: set[str] | None = None,
    resolvable: set[str] | None = None,
) -> list[Check]:
    """Build every check a registry implies.

    Parameters
    ----------
    registry : Mapping
        A parsed registry document.
    advisory : bool, default False
        Include rules marked ``advisory`` (R26 §3). They never carry ``error``, so
        enabling them cannot change whether a packet passed.
    only : set of str, optional
        Restrict to these resources. Checks referring to a resource outside the set are
        still generated if their own table is inside it; a packet need not carry every
        table, and a foreign key into an absent one cannot be evaluated.
    resolvable : set of str, optional
        Resources a reference may resolve against, beyond this registry's own tables. An
        extension registry needs core's tables here, since it declares none of them and R17 §2
        lets it reference them.

    Returns
    -------
    list of Check
        Generated Tier 1 checks followed by the registry's Tier 2 rules.
    """
    checks: list[Check] = []
    tables: Mapping[str, Any] = registry["tables"]
    included = set(tables) if only is None else set(only)
    # What a reference may point at, which is not the same as what gets checks. An extension
    # declares its own tables and references core's (R17 §2), so without this its foreign keys
    # generate nothing and an orphan validates clean -- the gap R46 closed for core.
    reachable = included if resolvable is None else set(resolvable) | included

    for resource, table in tables.items():
        if resource not in included:
            continue
        name = sql_name(resource)
        presence = {c["name"]: c["presence"] for c in table["columns"]}

        for column in table["columns"]:
            if column["presence"] == "required":
                checks.append(
                    Check(
                        f"{resource}.{column['name']}.not_null",
                        "error",
                        f"required column {column['name']} contains nulls",
                        f"SELECT * FROM {name} WHERE {quote(column['name'])} IS NULL",
                        resource,
                    )
                )
            if values := column.get("enum"):
                allowed = ", ".join(f"'{v}'" for v in values)
                col = quote(column["name"])
                checks.append(
                    Check(
                        f"{resource}.{column['name']}.in_vocabulary",
                        "error",
                        f"{column['name']} carries a value outside its closed vocabulary",
                        f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND {col} NOT IN ({allowed})",
                        resource,
                    )
                )

        by_scan = adjacency_settles_uniqueness(table) and resource not in (aggregate or set())
        if (key := table.get("primary_key")) and not by_scan:
            columns = ", ".join(quote(k) for k in key)
            checks.append(
                Check(
                    f"{resource}.primary_key_unique",
                    "error",
                    "duplicate primary key",
                    f"SELECT {columns}, COUNT(*) AS n FROM {name} GROUP BY {columns} HAVING COUNT(*) > 1",
                    resource,
                )
            )

        for ref in table.get("references", []):
            if ref["resource"] not in reachable:
                continue
            parent = sql_name(ref["resource"])
            on = " AND ".join(f"c.{quote(a)} = p.{quote(b)}" for a, b in zip(ref["columns"], ref["resource_columns"]))
            # A nullable foreign key constrains only its non-null values; without this
            # guard every legitimately absent value reports as a violation.
            guards = [f"c.{quote(a)} IS NOT NULL" for a in ref["columns"] if presence.get(a) == "nullable"]
            where = " AND ".join([f"p.{quote(ref['resource_columns'][0])} IS NULL", *guards])
            selected = ", ".join("c." + quote(a) for a in ref["columns"])
            checks.append(
                Check(
                    f"{resource}.{'_'.join(ref['columns'])}_resolves",
                    "error",
                    f"{', '.join(ref['columns'])} does not resolve to {ref['resource']}",
                    f"SELECT DISTINCT {selected} FROM {name} c LEFT JOIN {parent} p ON {on} WHERE {where}",
                    resource,
                )
            )

        for rule in table.get("rules", []):
            if rule.get("advisory") and not advisory:
                continue
            checks.append(Check(rule["id"], rule["level"], rule["message"], rule["sql"], resource))

    return checks

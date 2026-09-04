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


#: A dotted resource ID: two lowercase snake_case names. R55 §2.1 makes this checkable without
#: knowing which resources exist, which is what nothing did -- `scope_kind` could hold an empty
#: string and no rule would see it.
RESOURCE_ID = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


def _discriminator(
    resource: str,
    name: str,
    table: Mapping[str, Any],
    column: Mapping[str, Any],
    kinds: Mapping[str, str | None] | None,
    included: Collection[str],
) -> list[Check]:
    """Build the checks one discriminator column implies (R55 §2.4).

    Three, and they fail for different reasons: the value is not a resource ID at all, it names a
    resource the packet does not declare, or it names one that exists and holds no such row. Only
    the second is what `resolves` governs -- R49's scope may legitimately name a rig the packet
    does not hold, where R54's interval kind naming nothing leaves the row uninterpretable.
    """
    col = quote(column["name"])
    checks = [
        Check(
            f"{resource}.{column['name']}.is_a_resource_id",
            "error",
            f"{column['name']} holds a value that is not a dotted resource ID",
            f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND NOT regexp_matches({col}, '{RESOURCE_ID}')",
            resource,
        )
    ]
    if not kinds:
        return checks

    declared = ", ".join(f"'{k}'" for k in sorted(kinds))
    checks.append(
        Check(
            f"{resource}.{column['name']}.kind_declared",
            # R55 §2.2. Where an unresolvable kind is a fact rather than a defect it is still
            # reported: R49 §2.5's union passed it in silence, which is what let an extension
            # kind go unchecked without anything saying so.
            "error" if column.get("resolves") == "required" else "info",
            f"{column['name']} names a resource this packet does not declare",
            f"SELECT DISTINCT {col} FROM {name} WHERE {col} IS NOT NULL AND {col} NOT IN ({declared})",
            resource,
        )
    )

    # A paired value lives in the named table's key space (R55 §2.3), so it resolves value-to-key.
    # A shared-key discriminator needs no such check: the reference R55 §2.3.1 requires of the
    # named table already generates the anti-join, pointing the other way.
    paired = column.get("discriminates")
    if paired is None:
        return checks
    # Only a resource a paired value can actually name: one with a single-column key, which is
    # what `_resolve_column` returns a column for (R55 §2.3.3).
    joinable = {k: key for k, key in kinds.items() if k in included and key is not None}
    if not joinable:
        return checks
    # CAST both sides. A paired value is a string, because one column resolves against several
    # kinds and a carried key is a number where an assigned one's name is not -- so the union
    # mixes types by construction. Uncast, DuckDB coerces the string and *raises* on one that is
    # not a number, turning a finding into a check that could not run.
    union = " UNION ALL ".join(
        f"SELECT '{k}' AS kind, CAST({quote(key)} AS VARCHAR) AS id FROM {sql_name(k)}"
        for k, key in sorted(joinable.items())
    )
    val = quote(paired)
    return checks + [
        Check(
            f"{resource}.{column['name']}.resolves",
            "error",
            f"{paired} names no row of the resource {column['name']} declares",
            f"WITH known AS ({union}) SELECT DISTINCT r.{col}, r.{val} FROM {name} r "
            f"WHERE r.{col} IN (SELECT DISTINCT kind FROM known) AND NOT EXISTS "
            f"(SELECT 1 FROM known k WHERE k.kind = r.{col} AND k.id = CAST(r.{val} AS VARCHAR))",
            resource,
        )
    ]


def generate(
    registry: Mapping[str, Any],
    *,
    only: set[str] | None = None,
    advisory: bool = False,
    aggregate: set[str] | None = None,
    resolvable: set[str] | None = None,
    kinds: Mapping[str, str | None] | None = None,
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
    kinds : Mapping, optional
        Every resource a discriminator may name (R55 §2.1), mapped to the column a paired value
        joins to -- the `*_name` where the key is assigned, the key where it is carried (R55
        §2.3.3). Supplied by the caller rather than read from this registry, because R55 §2.5
        requires the resolution to reach the packet's *extension* kinds -- the case R49 §2.4
        designed the mechanism for and whose hand-written union quietly matched no branch.

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

        for column in table["columns"]:
            if column.get("role") != "discriminator":
                continue
            checks.extend(_discriminator(resource, name, table, column, kinds, included))

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

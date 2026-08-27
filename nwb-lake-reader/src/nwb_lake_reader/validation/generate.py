"""Generate Tier 1 validation checks from a registry.

Tier 1 follows from structure alone (R2 §7.1): required columns, primary keys, foreign
keys, closed vocabularies. Nothing here is written per table. Tier 2 rules carried in the
registry are passed through unchanged.

Every check is SQL returning offending rows; an empty result is a pass (R2 §7.3).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .._sql import quote, sql_name


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
    """

    id: str
    level: str
    message: str
    sql: str


def generate(registry: Mapping[str, Any], *, only: set[str] | None = None) -> list[Check]:
    """Build every check a registry implies.

    Parameters
    ----------
    registry : Mapping
        A parsed registry document.
    only : set of str, optional
        Restrict to these resources. Checks referring to a resource outside the set are
        still generated if their own table is inside it; a packet need not carry every
        table, and a foreign key into an absent one cannot be evaluated.

    Returns
    -------
    list of Check
        Generated Tier 1 checks followed by the registry's Tier 2 rules.
    """
    checks: list[Check] = []
    tables: Mapping[str, Any] = registry["tables"]
    included = set(tables) if only is None else set(only)

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
                    )
                )

        if key := table.get("primary_key"):
            columns = ", ".join(quote(k) for k in key)
            checks.append(
                Check(
                    f"{resource}.primary_key_unique",
                    "error",
                    "duplicate primary key",
                    f"SELECT {columns}, COUNT(*) AS n FROM {name} GROUP BY {columns} HAVING COUNT(*) > 1",
                )
            )

        for ref in table.get("references", []):
            if ref["resource"] not in included:
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
                )
            )

        for rule in table.get("rules", []):
            checks.append(Check(rule["id"], rule["level"], rule["message"], rule["sql"]))

    return checks

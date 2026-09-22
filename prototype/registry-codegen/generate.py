"""Emit validation checks from a schema registry.

Tier 1 checks are derived from structure alone (R2 §7.1); Tier 2 rules carried in the
registry are passed through unchanged. Every check is SQL returning offending rows —
empty result is a pass (R2 §7.3).
"""

import json
from pathlib import Path


def q(column: str) -> str:
    """Quote a column identifier. `offset` is reserved in DuckDB, and every engine
    reserves a different set, so emitted SQL quotes unconditionally."""
    return f'"{column}"'


def generate(registry: dict) -> list[dict]:
    checks = []

    def add(cid, level, message, sql):
        checks.append({"id": cid, "level": level, "message": message, "sql": sql})

    for resource, table in registry["tables"].items():
        t = resource
        presence = {c["name"]: c["presence"] for c in table["columns"]}

        for column in table["columns"]:
            if column["presence"] == "required":
                add(
                    f"{resource}.{column['name']}.not_null",
                    "error",
                    f"required column {column['name']} contains nulls",
                    f"SELECT * FROM {t} WHERE {q(column['name'])} IS NULL",
                )

        for column in table["columns"]:
            if values := column.get("enum"):
                allowed = ", ".join(f"'{v}'" for v in values)
                add(
                    f"{resource}.{column['name']}.in_vocabulary",
                    "error",
                    f"{column['name']} carries a value outside its closed vocabulary",
                    f"SELECT DISTINCT {q(column['name'])} FROM {t} "
                    f"WHERE {q(column['name'])} IS NOT NULL "
                    f"AND {q(column['name'])} NOT IN ({allowed})",
                )

        if table.get("primary_key"):
            key = ", ".join(q(k) for k in table["primary_key"])
            add(
                f"{resource}.primary_key_unique",
                "error",
                "duplicate primary key",
                f"SELECT {key}, COUNT(*) AS n FROM {t} GROUP BY {key} HAVING COUNT(*) > 1",
            )

        for ref in table.get("references", []):
            parent = ref["resource"]
            on = " AND ".join(
                f"c.{q(a)} = p.{q(b)}"
                for a, b in zip(ref["columns"], ref["resource_columns"])
            )
            # A nullable foreign key constrains only its non-null values; without this
            # guard every legitimately absent value reports as a violation.
            guards = [
                f"c.{q(a)} IS NOT NULL"
                for a in ref["columns"]
                if presence.get(a) == "nullable"
            ]
            where = " AND ".join(
                [f"p.{q(ref['resource_columns'][0])} IS NULL", *guards]
            )
            add(
                f"{resource}.{'_'.join(ref['columns'])}_resolves",
                "error",
                f"{', '.join(ref['columns'])} does not resolve to {ref['resource']}",
                f"SELECT DISTINCT {', '.join('c.' + q(a) for a in ref['columns'])} "
                f"FROM {t} c LEFT JOIN {parent} p ON {on} WHERE {where}",
            )

        for rule in table.get("rules", []):
            add(rule["id"], rule["level"], rule["message"], rule["sql"])

    return checks


def load(path="registry.json") -> dict:
    return json.loads(Path(path).read_text())


if __name__ == "__main__":
    registry = load(Path(__file__).parent / "registry.json")
    checks = generate(registry)
    tier2 = sum(len(t.get("rules", [])) for t in registry["tables"].values())
    print(
        f"{len(checks)} checks from {len(registry['tables'])} tables "
        f"({len(checks) - tier2} generated, {tier2} hand-written)\n"
    )
    for c in checks:
        print(f"  {c['id']}")
        print(f"      {c['sql']}")

"""Run the machine-readable Part 11 conformance vectors and shipped-rule checks."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "escapewheel-validator/src"))

from escapewheel_validator.rule_language import (
    PROFILE_ID,
    RuleProfileError,
    check_rule,
)

HERE = Path(__file__).resolve().parent
DDL = {
    "string": "VARCHAR",
    "int32": "INTEGER",
    "int64": "BIGINT",
    "float32": "FLOAT",
    "float64": "DOUBLE",
    "bool": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMPTZ",
    "json_string": "VARCHAR",
}


def registry(inputs: dict[str, Any]) -> dict[str, Any]:
    """Build the logical declarations one vector supplies."""
    return {
        "rule_language": PROFILE_ID,
        "resources": {
            name: {
                "kind": "table",
                "table": {
                    "columns": spec["columns"],
                    "primary_key": spec.get("primary_key"),
                    "references": [],
                    "rules": [],
                },
            }
            for name, spec in inputs.items()
        },
    }


def normalized(value: Any) -> str | None:
    """Render result scalars without losing exceptional or timestamp identity."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, datetime):
        return str(value)
    return str(value)


def execute(vector: dict[str, Any], host_zone: str = "UTC") -> list[list[str]]:
    """Execute one checked vector under the deterministic session settings."""
    connection = duckdb.connect()
    connection.sql(f"SET TimeZone = '{host_zone}'")
    # Rule evaluation is required to override, rather than inherit, this setting.
    connection.sql("SET TimeZone = 'UTC'")
    try:
        for resource, spec in vector["inputs"].items():
            namespace, _ = resource.split(".", 1)
            connection.sql(f"CREATE SCHEMA IF NOT EXISTS {namespace}")
            columns = ", ".join(
                f'"{c["name"]}" {DDL[c["type"]]}' for c in spec["columns"]
            )
            connection.sql(f"CREATE TABLE {resource} ({columns})")
            rows = spec.get("rows", [])
            if rows:
                marks = ", ".join("?" for _ in spec["columns"])
                connection.executemany(f"INSERT INTO {resource} VALUES ({marks})", rows)
        result = connection.sql(vector["query"]).arrow().read_all()
        return [
            [
                normalized(result.column(column)[row].as_py())
                for column in range(result.num_columns)
            ]
            for row in range(result.num_rows)
        ]
    finally:
        connection.close()


def vector_defects() -> list[str]:
    """Return every explicit-vector disagreement."""
    document = json.loads((HERE / "vectors.json").read_text())
    defects: list[str] = []
    if document.get("profile") != PROFILE_ID:
        defects.append("vector-set profile identity disagrees")
    for vector in document["vectors"]:
        name = vector["id"]
        declaration = registry(vector["inputs"])
        try:
            checked = check_rule(vector["query"], declaration)
        except RuleProfileError as exc:
            if vector["mode"] != "reject":
                defects.append(f"{name}: unexpectedly rejected: {exc}")
            continue
        if vector["mode"] == "reject":
            defects.append(f"{name}: unexpectedly accepted")
            continue
        if sorted(checked.resources) != vector["expected_resources"]:
            defects.append(f"{name}: resource set {sorted(checked.resources)!r}")
        if list(checked.result_names) != vector["expected_result_names"]:
            defects.append(f"{name}: result names {checked.result_names!r}")
        if vector["mode"].startswith("execute"):
            zones = (
                ("UTC", "America/Los_Angeles")
                if vector["mode"] == "execute-time-zones"
                else ("UTC",)
            )
            # The evaluator fixes UTC; changing an inherited session zone must not change the result.
            for zone in zones:
                actual = execute(vector, zone)
                if Counter(map(tuple, actual)) != Counter(
                    map(tuple, vector["expected_rows"])
                ):
                    defects.append(f"{name}: result bag {actual!r}")
    return defects


def profile_defects() -> list[str]:
    """Validate the incorporated descriptor and its contract-anchor references."""
    schema = json.loads((ROOT / "registry/rule_language.schema.json").read_text())
    profile = json.loads(
        (ROOT / "registry/rule_languages/escapewheel-rule-sql-v0.2.json").read_text()
    )
    defects = [
        error.message
        for error in jsonschema.Draft202012Validator(schema).iter_errors(profile)
    ]
    if profile.get("id") != PROFILE_ID:
        defects.append("profile id disagrees")
    part = (ROOT / "escapewheel_poc_docs_v0.2/11_tier_2_rule_language.md").read_text()
    for anchor in profile.get("contract_clauses", []):
        if f'id="{anchor}"' not in part:
            defects.append(f"contract anchor #{anchor} does not resolve")
    return defects


def shipped_rule_defects() -> list[str]:
    """Check and execute every shipped rule against typed empty relations."""
    core = json.loads((ROOT / "registry/logical_schemas.json").read_text())
    documents = [
        core,
        *[
            json.loads(path.read_text())
            for path in sorted((ROOT / "registry/extensions").glob("*.json"))
        ],
    ]
    connection = duckdb.connect()
    defects: list[str] = []
    tables = [
        {
            name: declaration["table"]
            for name, declaration in document["resources"].items()
            if declaration["kind"] == "table"
        }
        for document in documents
    ]
    try:
        for namespace in sorted(
            {name.split(".", 1)[0] for document in tables for name in document}
        ):
            connection.sql(f"CREATE SCHEMA {namespace}")
        for document in tables:
            for resource, table in document.items():
                columns = ", ".join(
                    f'"{c["name"]}" {DDL[c["type"]]}' for c in table["columns"]
                )
                connection.sql(f"CREATE TABLE {resource} ({columns})")
        count = 0
        for source, document in zip(documents, tables, strict=True):
            for table in document.values():
                for rule in table["rules"]:
                    count += 1
                    try:
                        check_rule(rule["sql"], source, core_resources=core)
                        connection.sql(rule["sql"]).fetchall()
                    except Exception as exc:  # noqa: BLE001 - each defect is reported together
                        defects.append(f"{rule['id']}: {str(exc).splitlines()[0]}")
        if count != 137:
            defects.append(f"shipped rule count is {count}, expected 137")
    finally:
        connection.close()
    return defects


def main() -> int:
    """Print each evidence group and fail on any disagreement."""
    groups = {
        "incorporated profile and anchors": profile_defects(),
        "machine-readable rule-language vectors": vector_defects(),
        "137 shipped rules statically check, bind, and execute empty": shipped_rule_defects(),
    }
    for label, defects in groups.items():
        print(
            f"{'FAIL' if defects else 'ok  '}  {label}"
            + (f" ({len(defects)})" if defects else "")
        )
        for defect in defects[:8]:
            print(f"          {defect}")
    return int(any(groups.values()))


if __name__ == "__main__":
    raise SystemExit(main())

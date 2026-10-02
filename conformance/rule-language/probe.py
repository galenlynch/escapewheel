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

from escapewheel_validator.errors import LoweringFailed
from escapewheel_validator.lowering import lower
from escapewheel_validator.rule_language import (
    PROFILE_ID,
    RuleProfileError,
    check_rule,
)

HERE = Path(__file__).resolve().parent
#: The engine's name for a result type -> Part 11 §4's SQL domain, where the two differ.
DOMAINS = {
    "FLOAT": "REAL",
    "DOUBLE": "DOUBLE PRECISION",
    "VARCHAR": "CHARACTER VARYING",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMP(6) WITH TIME ZONE",
}
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


def execute(vector: dict[str, Any], host_zone: str = "UTC") -> tuple[list[str], list[list[str | None]]]:
    """Execute one checked vector as the validator does, and return its result's domains and rows."""
    connection = duckdb.connect()
    connection.sql(f"SET TimeZone = '{host_zone}'")
    # Rule evaluation is required to override, rather than inherit, this setting.
    connection.sql("SET TimeZone = 'UTC'")
    try:
        for resource, spec in vector["inputs"].items():
            namespace, _ = resource.split(".", 1)
            connection.sql(f"CREATE SCHEMA IF NOT EXISTS {namespace}")
            columns = ", ".join(f'"{c["name"]}" {DDL[c["type"]]}' for c in spec["columns"])
            connection.sql(f"CREATE TABLE {resource} ({columns})")
            rows = spec.get("rows", [])
            if rows:
                marks = ", ".join("?" for _ in spec["columns"])
                connection.executemany(f"INSERT INTO {resource} VALUES ({marks})", rows)
        relation = connection.sql(lower(vector["query"], vector["inputs"]))
        domains = [DOMAINS.get(str(engine_type), str(engine_type)) for engine_type in relation.types]
        result = relation.arrow().read_all()
        return domains, [
            [normalized(result.column(column)[row].as_py()) for column in range(result.num_columns)]
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
            zones = ("UTC", "America/Los_Angeles") if vector["mode"] == "execute-time-zones" else ("UTC",)
            # The evaluator fixes UTC; changing an inherited session zone must not change the result.
            for zone in zones:
                try:
                    domains, actual = execute(vector, zone)
                except LoweringFailed:
                    # Part 11 §8 admits an incomplete evaluation where the stated result is not reached.
                    if vector["mode"] != "execute-or-incomplete":
                        defects.append(f"{name}: unexpectedly incomplete")
                    continue
                if Counter(map(tuple, actual)) != Counter(map(tuple, vector["expected_rows"])):
                    defects.append(f"{name}: result bag {actual!r}")
                if domains != vector.get("expected_result_domains", domains):
                    defects.append(f"{name}: result domains {domains!r}")
    return defects


def profile_defects() -> list[str]:
    """Validate the incorporated descriptor and its contract-anchor references."""
    schema = json.loads((ROOT / "spec/artifacts/rule_language.schema.json").read_text())
    profile = json.loads((ROOT / "spec/artifacts/rule_languages/escapewheel-rule-sql-v0.2.json").read_text())
    defects = [error.message for error in jsonschema.Draft202012Validator(schema).iter_errors(profile)]
    if profile.get("id") != PROFILE_ID:
        defects.append("profile id disagrees")
    part = (ROOT / "spec/parts/11_tier_2_rule_language.md").read_text()
    for anchor in profile.get("contract_clauses", []):
        if f'id="{anchor}"' not in part:
            defects.append(f"contract anchor #{anchor} does not resolve")
    return defects


def shipped_rule_defects() -> list[str]:
    """Check every shipped rule against the profile and the declarations it may name.

    Executing a shipped rule exercises no vector, so `conformance/registries/check.py` does it.
    """
    core = json.loads((ROOT / "spec/artifacts/logical_schemas.json").read_text())
    documents = [
        core,
        *[
            json.loads(path.read_text())
            for directory in ("extensions", "escapewheel-aind/extensions")
            for path in sorted((ROOT / directory).glob("*.json"))
        ],
    ]
    defects: list[str] = []
    count = 0
    for document in documents:
        for declaration in document["resources"].values():
            if declaration["kind"] != "table":
                continue
            for rule in declaration["table"]["rules"]:
                count += 1
                try:
                    check_rule(rule["sql"], document, core_resources=core)
                except Exception as exc:
                    defects.append(f"{rule['id']}: {str(exc).splitlines()[0]}")
    if count != 140:
        defects.append(f"shipped rule count is {count}, expected 140")
    return defects


def main() -> int:
    """Print each evidence group and fail on any disagreement."""
    groups = {
        "incorporated profile and anchors": profile_defects(),
        "machine-readable rule-language vectors": vector_defects(),
        "140 shipped rules statically check and bind": shipped_rule_defects(),
    }
    for label, defects in groups.items():
        print(f"{'FAIL' if defects else 'ok  '}  {label}" + (f" ({len(defects)})" if defects else ""))
        for defect in defects[:8]:
            print(f"          {defect}")
    return int(any(groups.values()))


if __name__ == "__main__":
    raise SystemExit(main())

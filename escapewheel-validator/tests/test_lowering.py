"""A Tier 2 query as the engine is given it (Part 11 §4)."""

import json
import struct
from pathlib import Path

import duckdb
import pytest

from escapewheel_validator.lowering import lower

ROOT = Path(__file__).resolve().parents[2]
MEDIAN = "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {value}) AS median_value FROM core.measurements"
CAST = "CAST({} AS DOUBLE PRECISION)"


def _binary32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


@pytest.mark.parametrize(
    ("domain", "value", "rows", "median"),
    [
        ("INTEGER", "value", [1, 2, 3, 5], 2.5),
        ("BIGINT", "value", [1, 2, 3, 5], 2.5),
        ("BIGINT", "CAST(value AS DECIMAL(38,0))", [1, 2, 3, 5], 2.5),
        ("REAL", "value", [0.1, 0.2], (_binary32(0.1) + _binary32(0.2)) / 2),
        ("DOUBLE PRECISION", "value", [0.1, 0.2], (0.1 + 0.2) / 2),
    ],
    ids=["integer", "bigint", "decimal", "real", "double"],
)
def test_a_median_is_interpolated_in_binary64_over_every_ordering_domain(domain, value, rows, median):
    """Part 11 §5: the ordering value converts to binary64 before interpolation, whatever its domain."""
    connection = duckdb.connect()
    connection.sql("CREATE SCHEMA core")
    connection.sql(f"CREATE TABLE core.measurements (value {domain})")
    connection.executemany("INSERT INTO core.measurements VALUES (?)", [(row,) for row in rows])
    result = connection.sql(lower(MEDIAN.format(value=value)))
    assert [str(returned) for returned in result.types] == ["DOUBLE"]
    assert result.fetchall() == [(median,)]


@pytest.mark.parametrize(
    ("query", "values"),
    [
        ("SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {}) FILTER (WHERE v > 0) AS m FROM a.b", ["ABS(v) + (w)"]),
        ("select percentile_cont(0.5) within group (order by {} -- the value\n) as m from a.b", ["v"]),
        ("SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {} ASC) AS m FROM a.b", ["v"]),
        ("SELECT '😀' AS s, " + ", ".join(["PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {}) AS m"] * 2), ["v", "w"]),
    ],
    ids=["expression-and-filter", "lower-case-and-comment", "explicit-asc", "two-calls"],
)
def test_the_whole_ordering_value_is_cast_and_nothing_else_changes(query, values):
    assert lower(query.format(*values)) == query.format(*(CAST.format(value) for value in values))


def test_a_median_ordered_by_a_median_is_cast_at_both_depths():
    inner = "(SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {}) FROM a.b)"
    outer = "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {}) AS m FROM a.b"
    assert lower(outer.format(inner.format("w"))) == outer.format(CAST.format(inner.format(CAST.format("w"))))


@pytest.mark.parametrize(
    "authored",
    [
        "SELECT 'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v)' AS label FROM a.b",
        "SELECT v FROM a.b -- PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v)",
        "SELECT percentile_cont FROM a.b",
    ],
    ids=["string", "comment", "column"],
)
def test_text_that_only_spells_the_routine_runs_as_authored(authored):
    assert lower(authored) == authored


def test_only_a_shipped_rule_taking_a_median_is_changed():
    """Every other rule reaches the engine byte for byte as the registry carries it."""
    core = json.loads((ROOT / "spec/artifacts/logical_schemas.json").read_text())
    rules = [
        rule
        for declaration in core["resources"].values()
        if declaration["kind"] == "table"
        for rule in declaration["table"]["rules"]
    ]
    assert {rule["id"] for rule in rules if lower(rule["sql"]) != rule["sql"]} == {
        rule["id"] for rule in rules if "PERCENTILE_CONT" in rule["sql"]
    }

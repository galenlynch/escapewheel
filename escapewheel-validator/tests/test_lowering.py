"""A Tier 2 query as the engine is given it (Part 11 §4)."""

import json
import re
import struct
from pathlib import Path

import duckdb
import pytest

from escapewheel_validator import LoweringFailed
from escapewheel_validator.lowering import lower

ROOT = Path(__file__).resolve().parents[2]
MEDIAN = "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {value}) AS median_value FROM core.measurements"
CAST = "CAST({} AS DOUBLE PRECISION)"
THROUGH_TEXT = "CAST(CAST({} AS VARCHAR) AS {})"
#: The tables the queries below name, by resource ID.
TABLES = {
    "a.b": {"columns": [{"name": "v", "type": "float32"}, {"name": "w", "type": "int64"}]},
    "core.products": {
        "columns": [
            {"name": "left_factor", "type": "int64"},
            {"name": "right_factor", "type": "int64"},
            {"name": "stored", "type": "float64"},
            {"name": "narrow", "type": "float32"},
        ]
    },
}
#: Two factors whose product exceeds 2^64, where the engine's own conversion does not round to nearest.
LEFT, RIGHT = 7353365817, 4496161461
NEAREST = float(LEFT * RIGHT)
PRODUCT = "CAST(left_factor AS DECIMAL(38,0)) * CAST(right_factor AS DECIMAL(38,0))"


def _binary32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


def _measurements(domain):
    return {"core.measurements": {"columns": [{"name": "value", "type": domain}]}}


def _products():
    connection = duckdb.connect()
    connection.sql("CREATE SCHEMA core")
    connection.sql("CREATE TABLE core.products (left_factor BIGINT, right_factor BIGINT, stored DOUBLE, narrow FLOAT)")
    connection.execute("INSERT INTO core.products VALUES (?, ?, ?, ?)", [LEFT, RIGHT, NEAREST, NEAREST])
    return connection


@pytest.mark.parametrize(
    ("declared", "domain", "value", "rows", "median"),
    [
        ("int32", "INTEGER", "value", [1, 2, 3, 5], 2.5),
        ("int64", "BIGINT", "value", [1, 2, 3, 5], 2.5),
        ("int64", "BIGINT", "CAST(value AS DECIMAL(38,0))", [1, 2, 3, 5], 2.5),
        ("float32", "REAL", "value", [0.1, 0.2], (_binary32(0.1) + _binary32(0.2)) / 2),
        ("float64", "DOUBLE PRECISION", "value", [0.1, 0.2], (0.1 + 0.2) / 2),
    ],
    ids=["integer", "bigint", "decimal", "real", "double"],
)
def test_a_median_is_interpolated_in_binary64_over_every_ordering_domain(declared, domain, value, rows, median):
    """Part 11 §5: the ordering value converts to binary64 before interpolation, whatever its domain."""
    connection = duckdb.connect()
    connection.sql("CREATE SCHEMA core")
    connection.sql(f"CREATE TABLE core.measurements (value {domain})")
    connection.executemany("INSERT INTO core.measurements VALUES (?)", [(row,) for row in rows])
    result = connection.sql(lower(MEDIAN.format(value=value), _measurements(declared)))
    assert [str(returned) for returned in result.types] == ["DOUBLE"]
    assert result.fetchall() == [(median,)]


@pytest.mark.parametrize(
    ("query", "values"),
    [
        ("SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {}) FILTER (WHERE v > 0) AS m FROM a.b", ["ABS(v) + (w)"]),
        ("select percentile_cont(0.5) within group (order by {} -- the value\n) as m from a.b", ["v"]),
        ("SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {} ASC) AS m FROM a.b", ["v"]),
        (
            "SELECT '😀' AS s, "
            + ", ".join(f"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {{}}) AS {name}" for name in "mn")
            + " FROM a.b",
            ["v", "w"],
        ),
    ],
    ids=["expression-and-filter", "lower-case-and-comment", "explicit-asc", "two-calls"],
)
def test_the_whole_ordering_value_is_cast_and_nothing_else_changes(query, values):
    assert lower(query.format(*values), TABLES) == query.format(*(CAST.format(value) for value in values))


def test_a_median_ordered_by_a_median_is_cast_at_both_depths():
    inner = "(SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {}) FROM a.b)"
    outer = "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {}) AS m FROM a.b"
    lowered = outer.format(CAST.format(inner.format(CAST.format("w"))))
    assert lower(outer.format(inner.format("w")), TABLES) == lowered


@pytest.mark.parametrize(
    "authored",
    [
        "SELECT 'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v)' AS label, 'v > 0.5' AS other FROM a.b",
        "SELECT v FROM a.b -- PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY v), v > 0.5",
        "SELECT percentile_cont FROM a.b",
    ],
    ids=["string", "comment", "column"],
)
def test_text_that_only_spells_a_lowered_form_runs_as_authored(authored):
    assert lower(authored, TABLES) == authored


@pytest.mark.parametrize(
    ("query", "returned"),
    [
        (f"SELECT left_factor FROM core.products WHERE {PRODUCT} = stored", [(LEFT,)]),
        (f"SELECT left_factor FROM core.products WHERE {PRODUCT} IS DISTINCT FROM stored", []),
        (f"SELECT left_factor FROM core.products WHERE stored BETWEEN {PRODUCT} AND {PRODUCT}", [(LEFT,)]),
        (f"SELECT left_factor FROM core.products WHERE stored IN ({PRODUCT}, 0)", [(LEFT,)]),
        (f"SELECT left_factor FROM core.products WHERE stored IN (SELECT {PRODUCT} FROM core.products)", [(LEFT,)]),
        (
            f"SELECT left_factor FROM core.products WHERE (SELECT MAX({PRODUCT}) AS top FROM core.products) = stored",
            [(LEFT,)],
        ),
        (
            (
                "SELECT p.left_factor FROM core.products AS p "
                f"INNER JOIN (SELECT {PRODUCT} AS wide FROM core.products) AS q ON q.wide = p.stored"
            ),
            [(LEFT,)],
        ),
        (
            (
                f"WITH wide AS (SELECT {PRODUCT} AS product, stored FROM core.products), "
                "every AS (SELECT * FROM wide) SELECT stored FROM every WHERE product = stored"
            ),
            [(NEAREST,)],
        ),
        (
            (
                f"SELECT left_factor, MAX({PRODUCT}) AS top FROM core.products "
                "GROUP BY left_factor, stored HAVING top <> stored"
            ),
            [],
        ),
        (f"SELECT {PRODUCT} * CAST(1 AS DOUBLE PRECISION) AS converted FROM core.products", [(NEAREST,)]),
        (f"SELECT {PRODUCT} / CAST(1 AS DOUBLE PRECISION) AS converted FROM core.products", [(NEAREST,)]),
        (f"SELECT CAST({PRODUCT} AS DOUBLE PRECISION) AS converted FROM core.products", [(NEAREST,)]),
        (f"SELECT COALESCE({PRODUCT}, stored) AS converted FROM core.products", [(NEAREST,)]),
        (
            f"SELECT CASE WHEN left_factor > 0 THEN {PRODUCT} ELSE stored END AS converted FROM core.products",
            [(NEAREST,)],
        ),
        (
            f"SELECT {PRODUCT} AS converted FROM core.products UNION ALL SELECT stored FROM core.products",
            [(NEAREST,), (NEAREST,)],
        ),
        (
            (
                f"SELECT {PRODUCT} AS converted FROM core.products UNION ALL SELECT {PRODUCT} FROM core.products "
                "UNION ALL SELECT stored FROM core.products"
            ),
            [(NEAREST,)] * 3,
        ),
        (MEDIAN.format(value=PRODUCT).replace("core.measurements", "core.products"), [(NEAREST,)]),
    ],
    ids=[
        "comparison",
        "is-distinct-from",
        "between",
        "in-list",
        "in-subquery",
        "scalar-subquery",
        "derived-table",
        "common-table-and-star",
        "result-name",
        "multiplication",
        "division",
        "cast",
        "coalesce",
        "case",
        "set-operation",
        "nested-set-operation",
        "ordering-value",
    ],
)
def test_an_exact_value_beyond_64_bits_converts_to_the_nearest_binary64_wherever_it_converts(query, returned):
    """Part 11 §4: every exact-to-approximate conversion rounds to nearest, ties to even."""
    assert _products().sql(lower(query, TABLES)).fetchall() == returned


@pytest.mark.parametrize(
    ("literal", "nearest"),
    [
        ("9.761848053491069", float("9.761848053491069")),
        ("9185068664893501.9", float("9185068664893501.9")),
        ("12.28551346553040255", float("12.28551346553040255")),
        ("-9185068664893501.9", float("-9185068664893501.9")),
        ("21249824117375502558", float(21249824117375502558)),
        ("0.5", 0.5),
    ],
    ids=["16-digits", "17-digits", "19-digits", "negated", "integer-beyond-bigint", "2-digits"],
)
def test_an_exact_literal_converts_to_the_nearest_binary64(literal, nearest):
    """Part 11 §4: a literal meeting an approximate value rounds to nearest as every conversion does."""
    query = f"SELECT CAST(1 AS DOUBLE PRECISION) * {literal} AS converted FROM core.products"
    assert _products().sql(lower(query, TABLES)).fetchall() == [(nearest,)]


@pytest.mark.parametrize(
    ("literal", "nearest"),
    [("7.6034944", 7.603494167327881), ("32138961.3", 32138962.0)],
    ids=["8-digits", "9-digits"],
)
def test_an_exact_value_meeting_a_real_converts_to_the_nearest_binary32(literal, nearest):
    """Part 11 §4: an exact with a `REAL` yields `REAL`, so the conversion rounds once, to binary32."""
    query = "SELECT narrow - narrow + {} AS converted FROM core.products"
    assert lower(query.format(literal), TABLES) == query.format(THROUGH_TEXT.format(literal, "REAL"))
    result = _products().sql(lower(query.format(literal), TABLES))
    assert [str(returned) for returned in result.types] == ["FLOAT"]
    assert result.fetchall() == [(nearest,)]


@pytest.mark.parametrize(
    "authored",
    [
        f"SELECT left_factor FROM core.products WHERE {PRODUCT} = 33061919995030178637",
        "SELECT left_factor FROM core.products WHERE left_factor < 2.5",
        f"SELECT COALESCE({PRODUCT}, left_factor) AS exact FROM core.products",
        "SELECT left_factor FROM core.products WHERE left_factor > stored AND right_factor < narrow AND stored > 1",
        "SELECT left_factor FROM core.products WHERE stored > 1.5E0 AND narrow > stored",
    ],
    ids=["decimal-with-integer-literal", "integer-with-decimal-literal", "exact-coalesce", "integer", "approximate"],
)
def test_a_query_converting_no_decimal_to_an_approximate_domain_runs_as_authored(authored):
    """Part 11 §4 compares exact values exactly, and the engine converts `INTEGER` and `BIGINT` to nearest."""
    assert lower(authored, TABLES) == authored


@pytest.mark.parametrize(
    ("query", "expression"),
    [
        ("SELECT v FROM a.c WHERE v > 0.5", None),
        (
            (
                "SELECT stored FROM core.products "
                f"INNER JOIN (SELECT {PRODUCT} AS stored FROM core.products) AS q USING (stored)"
            ),
            "q.stored",
        ),
        (
            (
                f"SELECT {PRODUCT} AS converted FROM core.products UNION SELECT {PRODUCT} FROM core.products "
                "UNION ALL SELECT stored FROM core.products"
            ),
            None,
        ),
        (
            (
                f"SELECT q.v FROM (SELECT * FROM (SELECT {PRODUCT} AS v FROM core.products) AS s "
                "UNION ALL SELECT stored FROM core.products) AS q"
            ),
            "s.v",
        ),
        ("SELECT v FROM a.b WHERE", None),
    ],
    ids=["undeclared-table", "using", "set-operation-removing-duplicates", "set-operation-member-star", "unparsed"],
)
def test_a_conversion_that_cannot_be_lowered_is_refused(query, expression):
    """A query is never run with a conversion left to the engine: Part 11 §8 makes the rule incomplete."""
    with pytest.raises(LoweringFailed) as refused:
        lower(query, TABLES)
    assert refused.value.expression == expression


def test_a_shipped_rule_is_changed_only_where_it_takes_a_median_or_converts_a_decimal():
    """Every other rule reaches the engine byte for byte as the registry carries it."""
    core = json.loads((ROOT / "spec/artifacts/logical_schemas.json").read_text())
    tables = {name: d["table"] for name, d in core["resources"].items() if d["kind"] == "table"}
    rules = [rule for table in tables.values() for rule in table["rules"]]
    changed = {rule["id"] for rule in rules if lower(rule["sql"], tables) != rule["sql"]}
    exact = re.compile(r"DECIMAL|\d\.\d+(?![\dEe])")
    assert {rule["id"] for rule in rules if "PERCENTILE_CONT" in rule["sql"]} <= changed
    assert changed <= {rule["id"] for rule in rules if "PERCENTILE_CONT" in rule["sql"] or exact.search(rule["sql"])}


#: Operands whose two `BETWEEN` comparisons would take different domains under one common domain.
MIXED = {
    "core.mixed": {
        "columns": [
            {"name": "x", "type": "int64"},
            {"name": "y", "type": "int64"},
            {"name": "z", "type": "float64"},
            {"name": "r", "type": "float32"},
            {"name": "i", "type": "int32"},
        ]
    }
}


def _mixed():
    connection = duckdb.connect()
    connection.sql("CREATE SCHEMA core")
    connection.sql("CREATE TABLE core.mixed (x BIGINT, y BIGINT, z DOUBLE, r FLOAT, i INTEGER)")
    connection.execute("INSERT INTO core.mixed VALUES (?, ?, ?, ?, ?)", [2**53, 2**53 + 1, 1e300, 0.0, 2])
    return connection


@pytest.mark.parametrize(
    ("predicate", "lowered", "holds"),
    [
        ("x BETWEEN y AND z", "(x >= y AND x <= z)", False),
        ("x NOT BETWEEN y AND z", "NOT (x >= y AND x <= z)", True),
        ("NOT x BETWEEN y AND z", "NOT (x >= y AND x <= z)", True),
        ("x BETWEEN 9007199254740992.5 AND 1e300", "(x >= 9007199254740992.5 AND x <= 1e300)", False),
        ("x + 1 BETWEEN y AND z", "((x + 1) >= y AND (x + 1) <= z)", True),
        (
            "CASE WHEN x BETWEEN y AND z THEN 1 ELSE 0 END BETWEEN 0 AND z",
            (
                "(CASE WHEN (x >= y AND x <= z) THEN 1 ELSE 0 END >= 0"
                " AND CASE WHEN (x >= y AND x <= z) THEN 1 ELSE 0 END <= z)"
            ),
            True,
        ),
    ],
    ids=["exact-pair", "not-between", "not-before", "decimal-literal", "expression", "nested"],
)
def test_a_between_whose_comparisons_take_different_domains_is_written_as_both(predicate, lowered, holds):
    """Part 11 §4: each comparison converts only its own operands, so two exact operands stay exact."""
    query = "SELECT x FROM core.mixed WHERE {}"
    assert lower(query.format(predicate), MIXED) == query.format(lowered)
    assert _mixed().sql(lower(query.format(predicate), MIXED)).fetchall() == ([(2**53,)] if holds else [])


def test_a_between_whose_operands_share_one_domain_runs_as_authored():
    query = "SELECT x FROM core.mixed WHERE x BETWEEN 0 AND 2 * y"
    assert lower(query, MIXED) == query


@pytest.mark.parametrize(
    ("predicate", "lowered", "holds"),
    [
        ("z - z + 16777217 IN (16777217, r)", "z - z + 16777217 IN (CAST(16777217 AS REAL), r)", False),
        ("z - z + 16777217 NOT IN (16777217, r)", "z - z + 16777217 NOT IN (CAST(16777217 AS REAL), r)", True),
        ("x IN (9007199254740993, 1e300)", "x IN (9007199254740993, 1e300)", True),
        ("i IN (2.5)", "i IN (2.5)", False),
        ("i IN (1, 2.5)", "i IN (1, 2.5)", False),
        ("i IN (2.0, 3)", "i IN (2.0, 3)", True),
    ],
    ids=["real-list", "real-list-negated", "double-list", "decimal", "integer-and-decimal", "decimal-equal"],
)
def test_an_in_list_takes_its_members_domain_before_its_left_operand_meets_it(predicate, lowered, holds):
    """Part 11 §4: the list is typed first, and a list of exact members compares by mathematical value."""
    query = "SELECT x FROM core.mixed WHERE {}"
    assert lower(query.format(predicate), MIXED) == query.format(lowered)
    assert _mixed().sql(lower(query.format(predicate), MIXED)).fetchall() == ([(2**53,)] if holds else [])

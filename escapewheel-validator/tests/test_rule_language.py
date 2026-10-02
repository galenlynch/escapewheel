import copy
import json
from pathlib import Path

import pytest
from escapewheel_reader import open_packet
from packet_fixture import install_registry, read_registry

from escapewheel_validator import validate

ROOT = Path(__file__).resolve().parents[2]


def _rule(registry, sql, *, rule_id="core.intervals.profile_test"):
    changed = copy.deepcopy(registry)
    changed["resources"]["core.intervals"]["table"]["rules"].append(
        {"id": rule_id, "level": "error", "message": "profile test", "sql": sql}
    )
    return changed


def test_the_transform_slope_rule_flags_every_slope_that_is_not_positive():
    """Part 11 §5 orders NaN above infinity, so NaN and +inf pass here and draw the finiteness check."""
    import duckdb

    core = json.loads((ROOT / "spec/artifacts/logical_schemas.json").read_text())
    rule = next(
        r
        for r in core["resources"]["core.clocks"]["table"]["rules"]
        if r["id"] == "core.clocks.transform_slope_positive"
    )
    slopes = [0.0, -0.0, -1.0, float("-inf"), 1.0, None, float("nan"), float("inf")]
    connection = duckdb.connect()
    connection.sql("CREATE SCHEMA core")
    connection.sql("CREATE TABLE core.clocks (clock_id INTEGER, transform_slope DOUBLE)")
    connection.executemany("INSERT INTO core.clocks VALUES (?, ?)", list(enumerate(slopes)))
    assert sorted(row[0] for row in connection.sql(rule["sql"]).fetchall()) == [0, 1, 2, 3]


def test_invalid_rule_is_not_executed_or_reported_as_a_packet_finding(packet_root):
    install_registry(packet_root, _rule(read_registry(packet_root), "DELETE FROM core.intervals"))
    report = validate(open_packet(packet_root))
    assert (report.verdict(), report.verdict("core")) == ("failed", "failed")
    assert report.registries[0].result.state == "invalid"
    assert not any(f.check == "core.intervals.profile_test" for f in report.findings)


def test_unsupported_language_is_distinct_from_a_finding(packet_root):
    registry = read_registry(packet_root)
    registry["rule_language"] = "another-rule-language-v1.0"
    install_registry(packet_root, registry)
    report = validate(open_packet(packet_root))
    assert (report.verdict(), report.verdict("core")) == ("incomplete", "incomplete")
    assert report.registries[0].result.state == "unsupported"
    assert not any(f.check == "rule_language.unsupported" for f in report.findings)


def test_engine_failure_is_incomplete_not_a_packet_finding(packet_root):
    sql = (
        "SELECT CAST(start_tick AS DECIMAL(38,0)) * 99999999999999999999999999999999999999 AS exploded "
        "FROM core.intervals"
    )
    install_registry(packet_root, _rule(read_registry(packet_root), sql))
    report = validate(open_packet(packet_root))
    assert (report.verdict(), report.verdict("core")) == ("incomplete", "incomplete")
    assert any(e.status == "incomplete" and e.rule == "core.intervals.profile_test" for e in report.evaluations)
    assert not any(f.check == "core.intervals.profile_test" for f in report.findings)


def test_a_median_over_an_exact_value_is_evaluated_in_binary64(packet_root):
    """Part 11 §5: the engine alone returns the median of 0 and 1 in the ordering value's exact domain."""
    sql = (
        "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CAST(interval_id AS DECIMAL(38,0))) AS median_id "
        "FROM core.intervals"
    )
    install_registry(packet_root, _rule(read_registry(packet_root), sql))
    report = validate(open_packet(packet_root))
    assert [f.rows for f in report.findings if f.check == "core.intervals.profile_test"] == [(("0.5",),)]


def test_an_exact_value_converts_to_the_nearest_binary64(packet_root):
    """Part 11 §4: the engine alone converts this product, which exceeds 2^64, to a binary64 one place off."""
    sql = (
        "SELECT interval_id FROM core.intervals "
        "WHERE CAST(7353365817 AS DECIMAL(38,0)) * CAST(4496161461 AS DECIMAL(38,0)) = 3.306191999503018E19"
    )
    assert float(7353365817 * 4496161461) == 3.306191999503018e19
    install_registry(packet_root, _rule(read_registry(packet_root), sql))
    report = validate(open_packet(packet_root))
    assert [bool(f.rows) for f in report.findings if f.check == "core.intervals.profile_test"] == [True]


def test_a_conversion_the_validator_cannot_round_is_incomplete_not_a_packet_finding(packet_root):
    """Part 11 §8: a `USING` join converts its exact column where no authored expression stands."""
    sql = (
        "WITH wide AS (SELECT CAST(start_tick AS DECIMAL(38,0)) AS tick FROM core.intervals), "
        "narrow AS (SELECT CAST(start_tick AS DOUBLE PRECISION) AS tick FROM core.intervals) "
        "SELECT wide.tick FROM wide INNER JOIN narrow USING (tick)"
    )
    install_registry(packet_root, _rule(read_registry(packet_root), sql))
    report = validate(open_packet(packet_root))
    assert (report.verdict(), report.verdict("core")) == ("incomplete", "incomplete")
    assert any(e.status == "incomplete" and e.rule == "core.intervals.profile_test" for e in report.evaluations)
    assert not any(f.check == "core.intervals.profile_test" for f in report.findings)


@pytest.mark.parametrize(
    ("units", "conforming"),
    [
        ([(0, 0, 0, "2"), (1, 0, 0, "10")], True),
        ([(0, 0, 0, "10"), (1, 0, 0, "2")], False),
        ([(1, 0, 0, "1"), (2, 0, 0, "2")], False),
        ([(0, 1, 0, "1"), (1, 1, 0, "2"), (2, 0, 0, "1")], True),
        ([(0, 0, 0, "1"), (1, 0, 1, "1"), (2, 0, 0, "2")], False),
        ([(0, 0, 0, "7"), (1, 0, 0, "007")], True),
        ([(0, 0, 0, "007"), (1, 0, 0, "7")], False),
        ([(0, 0, 0, "3"), (1, 0, 0, None), (2, 0, 0, None)], True),
        ([(0, 0, 0, None), (1, 0, 0, "3")], False),
    ],
    ids=[
        "2-before-10",
        "10-before-2",
        "from-one",
        "later-run-first",
        "curation-interleaved",
        "7-before-007",
        "007-before-7",
        "nulls-last",
        "null-first",
    ],
)
def test_units_are_numbered_densely_and_by_label_within_a_curation(units, conforming):
    """A label sorts by its length first, so "2" precedes "10" and "7" precedes "007"; null sorts last."""
    import duckdb

    core = json.loads((ROOT / "spec/artifacts/logical_schemas.json").read_text())
    rule = next(
        r for r in core["resources"]["core.units"]["table"]["rules"] if r["id"] == "core.units.numbered_in_order"
    )
    connection = duckdb.connect()
    connection.sql("CREATE SCHEMA core")
    connection.sql(
        "CREATE TABLE core.units "
        "(unit_id INTEGER, sorting_run_id INTEGER, curation_id INTEGER, local_unit_label VARCHAR)"
    )
    connection.executemany("INSERT INTO core.units VALUES (?, ?, ?, ?)", units)
    assert (not connection.sql(rule["sql"]).fetchall()) == conforming

"""Shipped core Tier 2 rules, run on hand-built rows of the tables they read."""

import json
from pathlib import Path

import duckdb
import pytest

from escapewheel_validator.rule_language import check_rule
from escapewheel_validator.validator import DDL

ROOT = Path(__file__).resolve().parents[2]
CORE = json.loads((ROOT / "spec/artifacts/logical_schemas.json").read_text())


def _flagged(rule_id, rows):
    table_id = rule_id.rsplit(".", 1)[0]
    rule = next(r for r in CORE["resources"][table_id]["table"]["rules"] if r["id"] == rule_id)
    connection = duckdb.connect()
    connection.sql("CREATE SCHEMA core")
    for resource_id in {table for table, _ in rows}:
        columns = ", ".join(
            f'"{c["name"]}" {DDL[c["type"]]}' for c in CORE["resources"][resource_id]["table"]["columns"]
        )
        connection.sql(f"CREATE TABLE {resource_id} ({columns})")
    for resource_id, row in rows:
        names = ", ".join(f'"{name}"' for name in row)
        values = ", ".join("?" * len(row))
        connection.execute(f"INSERT INTO {resource_id} ({names}) VALUES ({values})", list(row.values()))
    return len(connection.sql(check_rule(rule["sql"], CORE).sql).fetchall())


RATE_FORMS = {
    "hz": {"tick_rate_hz": 30000.0},
    "fraction": {"tick_rate_num": 30000, "tick_rate_den": 1},
    "unreduced": {"tick_rate_num": 60000, "tick_rate_den": 2},
}


def _array(sample_rate_hz, clock, step_tick_num, step_tick_den):
    return [
        ("core.clocks", {"session_id": 1, "clock_id": 1, "clock_name": "c", "origin": "o", **clock}),
        ("core.array_assets", {"session_id": 1, "array_asset_id": 1, "sample_rate_hz": sample_rate_hz}),
        (
            "core.array_dimensions",
            {
                "session_id": 1,
                "array_asset_id": 1,
                "axis_index": 0,
                "clock_id": 1,
                "origin_tick": 0,
                "step_tick_num": step_tick_num,
                "step_tick_den": step_tick_den,
            },
        ),
    ]


# A sample advances num/den ticks, so a 30 kHz clock implies 30000 * den / num samples per second.
@pytest.mark.parametrize("form", RATE_FORMS)
@pytest.mark.parametrize(
    ("num", "den", "implied"), [(1, 1, 30000.0), (24, 1, 1250.0), (3, 2, 20000.0), (3, 4, 40000.0)]
)
def test_the_rate_an_axis_implies_passes(form, num, den, implied):
    assert _flagged("core.array_assets.sample_rate_matches_axis", _array(implied, RATE_FORMS[form], num, den)) == 0


@pytest.mark.parametrize("form", RATE_FORMS)
@pytest.mark.parametrize(("num", "den", "wrong"), [(3, 2, 5000.0), (3, 4, 2500.0), (1, 1, 1.0)])
def test_any_other_rate_is_flagged(form, num, den, wrong):
    assert _flagged("core.array_assets.sample_rate_matches_axis", _array(wrong, RATE_FORMS[form], num, den)) == 1


def test_a_nan_sample_rate_is_flagged():
    assert _flagged("core.array_assets.sample_rate_matches_axis", _array(float("nan"), RATE_FORMS["hz"], 1, 1)) == 1

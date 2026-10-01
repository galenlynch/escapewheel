"""Running a rule and reading back its offending rows."""

import sys

import duckdb
import pytest

from escapewheel_validator.rules import _offending


def test_a_finding_that_projects_a_timestamp_is_reported_without_pytz(monkeypatch):
    """A rule that projects a wall-clock column must report its rows, not an engine error.

    DuckDB's own Python conversion imports `pytz` to render a ``TIMESTAMP WITH TIME ZONE``.
    An empty result converts nothing, so such a rule ran fine until it had something to say
    and then failed -- and whether that happened depended on whether an unrelated package had
    pulled `pytz` in.
    """
    connection = duckdb.connect()
    connection.sql("CREATE TABLE core_clocks (clock_id VARCHAR, tick_zero_utc TIMESTAMP WITH TIME ZONE)")
    connection.sql("INSERT INTO core_clocks VALUES ('harp', '2024-11-27T00:51:12+00:00')")
    query = "SELECT clock_id, tick_zero_utc FROM core_clocks"

    monkeypatch.setitem(sys.modules, "pytz", None)  # makes `import pytz` raise, as an absent one does
    with pytest.raises(duckdb.InvalidInputException):
        connection.sql(query).fetchall()
    assert _offending(connection, query)[0][0] == "harp"
    assert _offending(connection, "SELECT clock_id, tick_zero_utc FROM core_clocks WHERE FALSE") == []

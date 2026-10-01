"""The validator module's own helpers, exercised without a packet around them."""

import sys
from types import SimpleNamespace

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_validator import EvaluationStatus, Report
from escapewheel_validator.validator import _check_column, _offending, _scan_one_ordering, report_unassessed


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


def test_a_dictionary_column_satisfies_a_string_declaration():
    """A dictionary is an encoding, not a type: Parquet stores BYTE_ARRAY/String either way."""
    report = Report()
    column = {"name": "session_id", "type": "string", "presence": "required"}
    schema = pa.schema([pa.field("session_id", pa.dictionary(pa.int32(), pa.string()))])
    _check_column("core.units", column, schema, report)
    assert not report.findings


def test_a_dictionary_over_the_wrong_value_type_is_still_refused():
    """Unwrapping the encoding must not unwrap the check."""
    report = Report()
    column = {"name": "session_id", "type": "string", "presence": "required"}
    schema = pa.schema([pa.field("session_id", pa.dictionary(pa.int32(), pa.int64()))])
    _check_column("core.units", column, schema, report)
    assert [f.check for f in report.findings] == ["schema.column_type"]


def test_each_unassessed_external_is_its_own_registrys_finding():
    """Part 05 §5.3: one finding per resource, attributed as Part 05 §9.5 attributes a resource's."""
    resources = [
        SimpleNamespace(
            resource_id="core.lfp", declaration_id="core.array_asset_instances", is_external=True, interface="zarr"
        ),
        SimpleNamespace(resource_id="task.lfp", declaration_id="task.arrays", is_external=True, interface="zarr"),
        SimpleNamespace(resource_id="task.table", declaration_id="task.tables", is_external=True, interface="parquet"),
        SimpleNamespace(resource_id="core.video", declaration_id="core.media", is_external=True, interface=None),
        SimpleNamespace(resource_id="core.owned", declaration_id="core.media", is_external=False, interface="zarr"),
    ]
    report = Report(bound=("core", "task"))
    report.attribute(
        {"core.array_asset_instances": "core", "core.media": "core", "task.arrays": "task", "task.tables": "task"},
        resources,
    )
    report_unassessed(SimpleNamespace(resources=lambda: resources), {"task.table"}, report)
    assert [(f.level, f.check, f.registry, f.rows) for f in report.findings] == [
        ("info", "external.physical_unassessed", "core", (("core.lfp",),)),
        ("info", "external.physical_unassessed", "task", (("task.lfp",),)),
    ]


def test_a_row_breaking_a_determined_by_declaration_is_named_by_position(tmp_path):
    """Part 03 §5.3: the third row shares the second's key and differs in both columns the key determines."""
    path = tmp_path / "spike_events.parquet"
    pq.write_table(
        pa.table(
            {
                "session_id": pa.array([1, 1, 1, 1], type=pa.int32()),
                "clock_id": pa.array([1, 1, 2, 2], type=pa.int32()),
                "time_bucket_tick": pa.array([0, 0, 1, 1], type=pa.int64()),
                "unit_id": pa.array([1, 1, 1, 2], type=pa.int32()),
                "t_tick": pa.array([5, 6, 6, 9], type=pa.int64()),
            }
        ),
        path,
    )
    spec = {
        "columns": [
            {"name": "session_id"},
            {"name": "unit_id"},
            {"name": "t_tick"},
            {"name": "clock_id", "determined_by": ["session_id"]},
            {"name": "time_bucket_tick", "determined_by": ["t_tick"]},
        ],
        "primary_key": ["session_id", "unit_id", "t_tick"],
    }
    report = Report()
    handle = SimpleNamespace(path=path, schema=lambda: pq.read_schema(path))
    _scan_one_ordering("analysis.spike_events", handle, spec, report)
    assert [(f.check, f.rows) for f in report.findings] == [
        (
            "analysis.spike_events.determined_by",
            (("row 3", "clock_id", "1 != 2"), ("row 3", "time_bucket_tick", "0 != 1")),
        ),
        ("analysis.spike_events.primary_key_unique", (("row 3", "(1, 6)"),)),
    ]


def test_a_bound_registry_lacking_an_overrides_column_departs_from_its_order():
    """Part 03 §5.4: without `time_bucket_tick` the table cannot take the descriptor's order."""
    report = Report()
    spec = {
        "columns": [
            {"name": "session_id"},
            {"name": "unit_id"},
            {"name": "t_tick"},
            {"name": "clock_id", "determined_by": ["session_id"]},
        ],
        "primary_key": ["session_id", "unit_id", "t_tick"],
    }
    _scan_one_ordering("analysis.spike_events", None, spec, report)
    (finding,) = report.findings
    assert (finding.check, finding.level) == ("analysis.spike_events.physical_order", "error")
    assert "declares no time_bucket_tick" in finding.message


#: `analysis.spike_events` as a registry declares it: two sort columns ahead of the key, each
#: declared a function of it.
_SPIKE_EVENTS = {
    "columns": [
        {"name": "session_id"},
        {"name": "unit_id"},
        {"name": "t_tick"},
        {"name": "clock_id", "determined_by": ["session_id"]},
        {"name": "time_bucket_tick", "determined_by": ["t_tick"]},
    ],
    "primary_key": ["session_id", "unit_id", "t_tick"],
}


def _scanned_spike_events(tmp_path, *, clock_id, unit_id=(1, 1, 2), t_tick=(5, 5, 9)):
    """The ordering scan's findings over one session's spikes, as (check, rows) pairs."""
    path = tmp_path / "spike_events.parquet"
    rows = len(clock_id)
    pq.write_table(
        pa.table(
            {
                "session_id": pa.array([1] * rows, type=pa.int32()),
                "clock_id": pa.array(clock_id, type=pa.int32()),
                "time_bucket_tick": pa.array([0] * rows, type=pa.int64()),
                "unit_id": pa.array(unit_id, type=pa.int32()),
                "t_tick": pa.array(t_tick, type=pa.int64()),
            }
        ),
        path,
    )
    report = Report()
    handle = SimpleNamespace(path=path, schema=lambda: pq.read_schema(path))
    _scan_one_ordering("analysis.spike_events", handle, _SPIKE_EVENTS, report)
    return [(f.check, f.rows) for f in report.findings]


def test_a_repeated_key_under_a_constant_determined_column_is_only_a_duplicate(tmp_path):
    """Part 03 §5.3: a column the file holds as one value agrees with itself at every repeated key."""
    assert _scanned_spike_events(tmp_path, clock_id=[1, 1, 1]) == [
        ("analysis.spike_events.primary_key_unique", (("row 2", "(1, 5)"),)),
    ]


def test_a_repeated_key_under_a_varying_determined_column_is_also_a_false_declaration(tmp_path):
    assert _scanned_spike_events(tmp_path, clock_id=[1, 2, 2]) == [
        ("analysis.spike_events.determined_by", (("row 2", "clock_id", "1 != 2"),)),
        ("analysis.spike_events.primary_key_unique", (("row 2", "(1, 5)"),)),
    ]


def test_a_table_of_one_repeated_row_keeps_every_key_and_reports_the_duplicate(tmp_path):
    """Every key is constant, so the scan drops none of them and reads the determined columns."""
    assert _scanned_spike_events(tmp_path, clock_id=[1, 1], unit_id=[1, 1], t_tick=[5, 5]) == [
        ("analysis.spike_events.primary_key_unique", (("row 2", "(1, 1, 5)"),)),
    ]


def test_completing_an_evaluation_records_it_complete():
    """Part 05 §9.5: a registry passes only once its evaluation is recorded complete."""
    report = Report(bound=("core",))
    assert report.verdict("core") == "incomplete"
    report.complete("core")
    assert [(e.registry, e.status) for e in report.evaluations] == [("core", "complete")]


def test_completing_leaves_an_evaluation_that_ended_otherwise():
    report = Report(bound=("core", "task"))
    report.record_evaluation("core", EvaluationStatus.INCOMPLETE, rule="core.rule", detail="unreadable")
    report.complete("core")
    report.complete("task")
    assert [(e.registry, e.status) for e in report.evaluations] == [("core", "incomplete"), ("task", "complete")]

"""Generated checks and Tier 2 rules over a packet's tables, and a rule's offending rows read back."""

import json
import sys

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import validate
from escapewheel_validator.rules import _offending

from .builders import add_extension, rewrite_table, verdicts_of
from .conftest import install_registry, read_registry


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


def test_duplicate_primary_key(packet_root):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    rewrite_table(packet_root, "intervals", pa.concat_tables([intervals, intervals.slice(0, 1)]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.intervals.primary_key_unique" for f in report.findings)


def test_unresolved_foreign_key(packet_root):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    broken = intervals.set_column(0, "session_id", pa.array([999, 999], type=pa.int32()))
    rewrite_table(packet_root, "intervals", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.intervals.session_id_resolves" for f in report.findings)


def test_closed_vocabulary(packet_root):
    units = pq.read_table(packet_root / "tables" / "core" / "units.parquet")
    broken = units.set_column(4, "quality_label", pa.array(["good", "mua"]))
    rewrite_table(packet_root, "units", broken)
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "core.units.quality_label.in_vocabulary")
    assert finding.rows == (("good",),)


def test_open_vocabulary_accepts_anything(packet_root):
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    renamed = events.set_column(2, "event_type", pa.array(["whatever", "reward", "lick"]))
    rewrite_table(packet_root, "events", renamed)
    assert validate(open_packet(packet_root)).passed


def _validate_tick_rates(packet_root, values, *, presence="nullable"):
    """Declare a finite `core.clocks.tick_rate_hz` (Part 02 §5.4), write `values` unless None, validate."""
    registry = read_registry(packet_root)
    registry["resources"]["core.clocks"]["table"]["columns"].append(
        {
            "name": "tick_rate_hz",
            "type": "float64",
            "presence": presence,
            "role": "data",
            "description": "ticks per second",
            "finite": True,
        }
    )
    install_registry(packet_root, registry)
    if values is not None:
        clocks = pq.read_table(packet_root / "tables" / "core" / "clocks.parquet")
        rewrite_table(packet_root, "clocks", clocks.append_column("tick_rate_hz", pa.array(values, type=pa.float64())))
    return validate(open_packet(packet_root))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_value_in_a_finite_column_fails(packet_root, value):
    """Part 02 §10.1: each non-finite value is an error; the null beside it is presence's concern alone."""
    report = _validate_tick_rates(packet_root, [value, None])
    finding = next(f for f in report.findings if f.check == "core.clocks.tick_rate_hz.finite")
    assert not report.passed
    assert finding.level == "error" and finding.registry == "core"
    assert [row[0] for row in finding.rows] == ["1"]


def test_finite_values_and_nulls_pass_a_finite_column(packet_root):
    report = _validate_tick_rates(packet_root, [30_000.0, None])
    assert report.passed
    assert not any(f.check.endswith(".finite") for f in report.findings)


def test_an_absent_optional_finite_column_reports_nothing(packet_root):
    report = _validate_tick_rates(packet_root, None, presence="optional")
    assert report.passed
    assert not any(f.check.endswith(".finite") for f in report.findings)


def _validate_optional_event_column(packet_root, column, reference, values):
    """Declare `column` optional on `core.events` with `reference`, write `values` unless None, validate."""
    registry = read_registry(packet_root)
    table = registry["resources"]["core.events"]["table"]
    table["columns"].append(column)
    if reference is not None:
        table["references"].append(reference)
    install_registry(packet_root, registry)
    if values is not None:
        events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
        rewrite_table(packet_root, "events", events.append_column(column["name"], values))
    return validate(open_packet(packet_root))


CUE_SIDE = {
    "name": "cue_side",
    "type": "string",
    "presence": "optional",
    "role": "data",
    "description": "side the cue came from",
    "vocabulary": "closed",
    "enum": ["left", "right"],
}


INTERVAL_ID = {
    "name": "interval_id",
    "type": "int32",
    "presence": "optional",
    "role": "identifier",
    "identity": "assigned",
    "description": "the interval an event fell in",
}


IN_INTERVAL = {
    "columns": ["session_id", "interval_id"],
    "resource": "core.intervals",
    "resource_columns": ["session_id", "interval_id"],
}


def test_an_absent_optional_closed_vocabulary_column_reports_nothing(packet_root):
    """Part 02 §6 lets a table omit an optional column, which leaves no value to test."""
    report = _validate_optional_event_column(packet_root, CUE_SIDE, None, None)
    assert report.passed, [(f.check, f.message) for f in report.findings]


def test_a_present_optional_closed_vocabulary_column_is_checked(packet_root):
    report = _validate_optional_event_column(packet_root, CUE_SIDE, None, pa.array(["left", None, "up"]))
    finding = next(f for f in report.findings if f.check == "core.events.cue_side.in_vocabulary")
    assert finding.rows == (("up",),)


def test_an_absent_optional_foreign_key_column_reports_nothing(packet_root):
    report = _validate_optional_event_column(packet_root, INTERVAL_ID, IN_INTERVAL, None)
    assert report.passed, [(f.check, f.message) for f in report.findings]


def test_a_present_optional_foreign_key_column_is_checked(packet_root):
    """An optional column may be null where present (Part 02 §6), so only the 9 fails to resolve."""
    report = _validate_optional_event_column(packet_root, INTERVAL_ID, IN_INTERVAL, pa.array([1, None, 9], pa.int32()))
    finding = next(f for f in report.findings if f.check == "core.events.session_id_interval_id_resolves")
    assert finding.rows == (("1", "9"),)


def test_tier_two_rule(packet_root):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    broken = intervals.set_column(3, "stop_tick", pa.array([0, 10000], type=pa.int64()))
    rewrite_table(packet_root, "intervals", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.intervals.interval_valid" for f in report.findings)


def test_absent_tables_are_not_required(packet_root):
    """A packet need not carry every table the registry defines."""
    import json as _json

    path = packet_root / "packet.json"
    entry = _json.loads(path.read_text())
    entry["resources"] = [r for r in entry["resources"] if r["resource_id"] != "core.spike_events"]
    path.write_text(_json.dumps(entry))
    assert validate(open_packet(packet_root)).passed


def test_advisory_rules_are_off_by_default(packet_root):
    """An advisory rule does not run unless asked (Part 02 §10.2)."""
    registry = read_registry(packet_root)
    registry["resources"]["core.intervals"]["table"]["rules"].append(
        {
            "id": "core.intervals.advice",
            "level": "info",
            "advisory": True,
            "message": "advice",
            "sql": "SELECT session_id, interval_id FROM core.intervals",
        }
    )
    install_registry(packet_root, registry)
    quiet = validate(open_packet(packet_root))
    assert not any(f.check == "core.intervals.advice" for f in quiet.findings)

    loud = validate(open_packet(packet_root), advisory=True)
    assert any(f.check == "core.intervals.advice" for f in loud.findings)


def test_advisory_cannot_change_the_verdict(packet_root):
    """`passed` is invariant under the flag, because advisory rules are never errors."""
    registry = read_registry(packet_root)
    registry["resources"]["core.intervals"]["table"]["rules"].append(
        {
            "id": "core.intervals.advice",
            "level": "info",
            "advisory": True,
            "message": "advice",
            "sql": "SELECT session_id, interval_id FROM core.intervals",
        }
    )
    install_registry(packet_root, registry)
    quiet = validate(open_packet(packet_root))
    loud = validate(open_packet(packet_root), advisory=True)
    assert quiet.passed is loud.passed is True
    assert loud.errors == quiet.errors == 0


def test_validation_leaves_nothing_in_the_packet(packet_root):
    """The spill goes beside the packet, not inside it: a packet's bytes are settled, and one
    on read-only media must still be validatable."""
    before = {p.name for p in packet_root.iterdir()}
    validate(open_packet(packet_root))
    assert {p.name for p in packet_root.iterdir()} == before


def test_recheck_still_catches_a_break_in_what_was_written(packet_root):
    """Narrowing must not narrow away the resource the amendment actually wrote."""
    duplicated = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    rewrite_table(packet_root, "intervals", pa.concat_tables([duplicated, duplicated.slice(0, 1)]))
    report = validate(open_packet(packet_root), recheck={"core.intervals"})
    assert not report.passed


def test_an_extension_is_validated_by_the_same_machinery(packet_root):
    """R17 §3: nothing per-extension. `generate` produces its checks from its structure."""
    report = validate(open_packet(add_extension(packet_root)))
    assert report.passed
    assert "extension.validated" in {f.check for f in report.findings}


def test_an_extensions_closed_vocabulary_is_enforced(packet_root):
    root = add_extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "sideways"))
    report = validate(open_packet(root))
    assert "task.trials.choice.in_vocabulary" in {f.check for f in report.findings}


def test_an_extension_reference_into_core_resolves(packet_root):
    """Part 09 §6.1 lets an extension reference core. Without the cross-registry link the anti-join is
    never generated and an orphan validates clean -- the gap R46 closed for core."""
    root = add_extension(packet_root, mutate=lambda r: r["interval_id"].__setitem__(0, 999))
    report = validate(open_packet(root))
    assert any(f.check.endswith("_resolves") and f.registry == "task" for f in report.findings)


def test_an_extension_non_finite_value_is_attributed_to_it(packet_root):
    """Part 05 §5.4 applies the finiteness check to an extension's columns, filed under it (§9.5)."""
    root = add_extension(packet_root)
    document = read_registry(root, "task")
    document["resources"]["task.trials"]["table"]["columns"].append(
        {
            "name": "reward_volume",
            "type": "float64",
            "presence": "nullable",
            "role": "data",
            "description": "Reward volume.",
            "finite": True,
        }
    )
    install_registry(root, document)
    table = pq.read_table(root / "tables" / "task" / "trials.parquet")
    pq.write_table(
        table.append_column("reward_volume", pa.array([float("nan"), 2.0])), root / "tables" / "task" / "trials.parquet"
    )
    report = validate(open_packet(root))
    finding = next(f for f in report.findings if f.check == "task.trials.reward_volume.finite")
    assert finding.registry == "task" and finding.level == "error"
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")


def test_an_extension_the_packet_does_not_carry_is_reported_not_run(packet_root):
    root = add_extension(packet_root)
    (root / "tables" / "task" / "trials.parquet").unlink()
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"] = [r for r in manifest["resources"] if r["resource_id"] != "task.trials"]
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    assert "extension.table_absent" in {f.check for f in report.findings}

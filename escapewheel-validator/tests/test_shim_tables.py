"""A table's physical schema, and the values a registry constrains without a rule."""

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader import open_packet
from packet_fixture import install_registry, read_registry

from escapewheel_validator import Report, validate
from escapewheel_validator.shim.tables import _check_column

from .builders import add_extension, read_table, rewrite_table, verdicts_of, with_column


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


def test_equal_varying_columns_are_reported_at_info_only(packet_root):
    intervals = read_table(packet_root, "intervals")
    rewrite_table(packet_root, "intervals", with_column(intervals, "stop_tick", intervals["start_tick"]))
    report = validate(open_packet(packet_root))
    duplicated = [f for f in report.findings if f.check == "core.intervals.columns_duplicated"]
    assert [f.level for f in duplicated] == ["info"]
    assert "start_tick" in duplicated[0].message and "stop_tick" in duplicated[0].message
    assert report.passed


def test_equal_constant_columns_are_not_reported(packet_root):
    """Both units then hold one value in `sorting_run_id` and the same value in `curation_id`."""
    units = read_table(packet_root, "units")
    rewrite_table(packet_root, "units", with_column(units, "curation_id", units["sorting_run_id"]))
    report = validate(open_packet(packet_root))
    assert not any(f.check.endswith(".columns_duplicated") for f in report.findings)


def _validate_amplitude_units(packet_root, values):
    """Declare `core.units.amplitude_unit` a unit column (Part 02 §8.4), write `values`, validate."""
    registry = read_registry(packet_root)
    registry["resources"]["core.units"]["table"]["columns"].append(
        {
            "name": "amplitude_unit",
            "type": "string",
            "presence": "nullable",
            "role": "data",
            "description": "the UCUM code amplitudes are in",
            "vocabulary": "open",
            "authority": [{"name": "UCUM", "uri": "https://ucum.org/ucum"}],
        }
    )
    install_registry(packet_root, registry)
    units = pq.read_table(packet_root / "tables" / "core" / "units.parquet")
    rewrite_table(packet_root, "units", units.append_column("amplitude_unit", pa.array(values, type=pa.string())))
    return validate(open_packet(packet_root))


def test_ucum_codes_and_annotations_pass(packet_root):
    report = _validate_amplitude_units(packet_root, ["V", "{sample}"])
    assert report.passed
    assert not any(f.check.endswith(".ucum_code") for f in report.findings)


def test_a_null_unit_is_not_checked_as_a_code(packet_root):
    report = _validate_amplitude_units(packet_root, [None, "uV"])
    assert not any(f.check.endswith(".ucum_code") for f in report.findings)


def test_a_unit_that_is_not_a_ucum_code_fails_once_per_value(packet_root):
    """Part 05 §5.3: `volts` names the unit whose code is `V`, and is not itself a code."""
    report = _validate_amplitude_units(packet_root, ["volts", "volts"])
    finding = next(f for f in report.findings if f.check == "core.units.amplitude_unit.ucum_code")
    assert not report.passed
    assert finding.level == "error"
    assert finding.rows == (("volts",),)


def test_wrong_column_type_is_caught_before_any_query(packet_root):
    intervals = read_table(packet_root, "intervals")
    narrowed = with_column(intervals, "start_tick", intervals.column("start_tick").cast(pa.int32()))
    rewrite_table(packet_root, "intervals", narrowed)
    report = validate(open_packet(packet_root))
    assert any(f.check == "schema.column_type" for f in report.findings)


def test_a_declared_metadata_column_no_row_fills_is_reported(packet_root):
    """Part 05 §5.3, at `info`. The column may be absent from the file, so this can never fail."""
    report = validate(open_packet(packet_root))
    assert report.passed
    finding = next(f for f in report.findings if f.check == "core.intervals.metadata_unfilled")
    assert finding.level == "info"
    # Part 05 §9.5: a finding about one resource belongs to the registry declaring it.
    assert finding.registry == "core"


def test_a_filled_metadata_column_is_not_reported(packet_root):
    """The other side: one non-null value in the packet is enough, so the report cannot nag."""
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    filled = intervals.append_column("metadata", pa.array(['{"a": 1}', None]))
    rewrite_table(packet_root, "intervals", filled)
    report = validate(open_packet(packet_root))
    assert not [f for f in report.findings if f.check == "core.intervals.metadata_unfilled"]


def test_an_extension_table_receives_the_storage_checks(packet_root):
    """Part 05 §5.4: a column type an extension declares is checked as core's are, and filed under it."""
    root = add_extension(packet_root)
    table = pq.read_table(root / "tables" / "task" / "trials.parquet")
    widened = table.set_column(0, "session_id", table["session_id"].cast(pa.int64()))
    pq.write_table(widened, root / "tables" / "task" / "trials.parquet")
    report = validate(open_packet(root))
    finding = next(f for f in report.findings if f.check == "schema.column_type")
    assert finding.registry == "task" and finding.message.startswith("task.trials.session_id")
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")


def test_an_extension_unit_column_is_checked_against_ucum(packet_root):
    """Part 05 §5.3's unit-code check covers every directing registry's tables."""
    root = add_extension(packet_root)
    document = read_registry(root, "task")
    choice = document["resources"]["task.trials"]["table"]["columns"][2]
    choice.pop("enum")
    choice |= {"vocabulary": "open", "authority": [{"name": "UCUM", "uri": "https://ucum.org/ucum"}]}
    install_registry(root, document)
    table = pq.read_table(root / "tables" / "task" / "trials.parquet")
    pq.write_table(
        table.set_column(2, "choice", pa.array(["mV", "volts"])), root / "tables" / "task" / "trials.parquet"
    )
    report = validate(open_packet(root))
    finding = next(f for f in report.findings if f.check == "task.trials.choice.ucum_code")
    assert finding.registry == "task" and finding.rows == (("volts",),)
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")

"""A table's physical schema, and the values a registry constrains without a rule."""

from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import open_packet
from packet_fixture import install_registry, read_registry

from escapewheel_validator import Report, validate
from escapewheel_validator.registry_types import PARQUET_TYPES
from escapewheel_validator.shim.tables import _check_types, parquet_type

from .builders import add_extension, read_table, rewrite_table, verdicts_of, with_column


def _types_of(tmp_path, declared, values, *, external=False):
    """Write one column of `values`, declared `declared`, and return the findings its footer draws."""
    path = tmp_path / "t.parquet"
    pq.write_table(pa.table({"c": values}), path)
    report = Report()
    resource = SimpleNamespace(resource_id="core.t", is_external=external)
    _check_types(resource, [{"name": "c", "type": declared}], pq.read_metadata(path), report)
    return [(f.check, f.level) for f in report.findings]


def test_a_dictionary_column_satisfies_a_string_declaration(tmp_path):
    """A dictionary is an encoding, not a type: Parquet stores BYTE_ARRAY/String either way."""
    assert _types_of(tmp_path, "string", pa.array(["a", "a"]).dictionary_encode()) == []


def test_a_dictionary_over_the_wrong_value_type_is_still_refused(tmp_path):
    """Unwrapping the encoding must not unwrap the check."""
    found = _types_of(tmp_path, "string", pa.array([1, 1], pa.int64()).dictionary_encode())
    assert found == [("schema.column_type", "error")]


@pytest.mark.parametrize(
    ("declared", "values"),
    [
        ("int64", pa.array([1], pa.uint64())),
        ("json_string", pa.array(["{}"], pa.json_(pa.string()))),
        ("timestamp", pa.array([1], pa.timestamp("ms", tz="UTC"))),
    ],
    ids=["unsigned-int64", "json-annotated", "millis-timestamp"],
)
def test_a_packet_owned_column_off_the_type_table_is_at_the_wrong_type(tmp_path, declared, values):
    """Part 03 §5.1 gives a packet-owned column of each logical type one Parquet type."""
    assert _types_of(tmp_path, declared, values) == [("schema.column_type", "error")]


@pytest.mark.parametrize(
    ("declared", "values"),
    [
        ("timestamp", pa.array([1], pa.timestamp("ms", tz="UTC"))),
        ("int64", pa.array([1], pa.uint32())),
        ("float32", pa.array([1.0])),
        ("json_string", pa.array(["{}"], pa.json_(pa.string()))),
    ],
    ids=["millis-timestamp", "unsigned-int32", "double-for-float32", "json-annotated"],
)
def test_an_external_column_elsewhere_in_its_family_is_reported_at_info_only(tmp_path, declared, values):
    """Part 05 §5.3: outside the portability guarantee, and never also `schema.column_type`."""
    found = _types_of(tmp_path, declared, values, external=True)
    assert found == [("physical.outside_type_mapping", "info")]


@pytest.mark.parametrize(
    ("declared", "values"),
    [
        ("int64", pa.array(["1"])),
        ("timestamp", pa.array([1], pa.timestamp("us"))),
        ("date", pa.array([1], pa.int32())),
    ],
    ids=["text-for-int64", "local-time-timestamp", "integer-for-date"],
)
def test_an_external_column_outside_its_family_is_at_the_wrong_type(tmp_path, declared, values):
    assert _types_of(tmp_path, declared, values, external=True) == [("schema.column_type", "error")]


def test_every_column_of_the_valid_packet_is_at_its_type_tables_type(packet_root):
    """Part 03 §5.1, read from each table's footer rather than through the validator's findings."""
    packet = open_packet(packet_root)
    registry = read_registry(packet_root)["resources"]
    checked = 0
    for resource in packet.resources():
        declaration = registry.get(resource.declaration_id, {}).get("table")
        if declaration is None:
            continue
        footer = pq.read_metadata(packet.table_resource(resource.resource_id).path)
        leaves = {footer.schema.column(i).path: footer.schema.column(i) for i in range(footer.num_columns)}
        for column in declaration["columns"]:
            if column["name"] in leaves:
                assert parquet_type(leaves[column["name"]]) in PARQUET_TYPES[column["type"]], (
                    resource.resource_id,
                    column["name"],
                )
                checked += 1
    assert checked


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


def test_a_column_the_declaration_does_not_declare_fails_whatever_its_values(packet_root):
    """Part 02 §6.1: an all-null column is undeclared too, and Part 05 §9.5 files it under core."""
    intervals = read_table(packet_root, "intervals")
    rewrite_table(packet_root, "intervals", intervals.append_column("extra", pa.nulls(intervals.num_rows, pa.string())))
    report = validate(open_packet(packet_root))
    found = [f for f in report.findings if f.check == "schema.column_undeclared"]
    assert [(f.level, f.registry, f.resource, f.column) for f in found] == [
        ("error", "core", "core.intervals", "extra")
    ]
    assert not report.passed


def test_an_extension_table_undeclared_column_is_filed_under_the_extension(packet_root):
    root = add_extension(packet_root)
    table = pq.read_table(root / "tables" / "task" / "trials.parquet")
    pq.write_table(
        table.append_column("extra", pa.array([1, 2], type=pa.int64())), root / "tables" / "task" / "trials.parquet"
    )
    report = validate(open_packet(root))
    finding = next(f for f in report.findings if f.check == "schema.column_undeclared")
    assert finding.registry == "task" and finding.column == "extra"
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")


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

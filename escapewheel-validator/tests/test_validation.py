import inspect
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import RegistryFault, RegistryUnavailable, open_packet

from escapewheel_validator import Verification, validate
from escapewheel_validator.validator import check_packet_manifest

from .conftest import UNREAD_DIGEST, install_registry, owned_digest, read_registry


def _rewrite(root, name, table):
    pq.write_table(table, root / "tables" / "core" / f"{name}.parquet", compression="zstd")


def test_conforming_packet_passes(packet_root):
    report = validate(open_packet(packet_root))
    assert report.passed
    assert report.errors == 0 and report.warnings == 0


def test_duplicate_primary_key(packet_root):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    _rewrite(packet_root, "intervals", pa.concat_tables([intervals, intervals.slice(0, 1)]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.intervals.primary_key_unique" for f in report.findings)


def test_unresolved_foreign_key(packet_root):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    broken = intervals.set_column(0, "session_id", pa.array([999, 999], type=pa.int32()))
    _rewrite(packet_root, "intervals", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.intervals.session_id_resolves" for f in report.findings)


def test_closed_vocabulary(packet_root):
    units = pq.read_table(packet_root / "tables" / "core" / "units.parquet")
    broken = units.set_column(4, "quality_label", pa.array(["good", "mua"]))
    _rewrite(packet_root, "units", broken)
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "core.units.quality_label.in_vocabulary")
    assert finding.rows == (("good",),)


def test_equal_varying_columns_are_reported_at_info_only(packet_root):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    index = intervals.schema.get_field_index("clock_id")
    _rewrite(packet_root, "intervals", intervals.set_column(index, "clock_id", pa.array([1, 2], type=pa.int32())))
    report = validate(open_packet(packet_root))
    duplicated = [f for f in report.findings if f.check == "core.intervals.columns_duplicated"]
    assert [f.level for f in duplicated] == ["info"]
    assert "interval_id" in duplicated[0].message and "clock_id" in duplicated[0].message
    assert report.passed


def test_equal_constant_columns_are_not_reported(packet_root):
    """The fixture's `session_id` and `clock_id` both hold 1 in every interval."""
    report = validate(open_packet(packet_root))
    assert not any(f.check.endswith(".columns_duplicated") for f in report.findings)


def test_open_vocabulary_accepts_anything(packet_root):
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    renamed = events.set_column(2, "event_type", pa.array(["whatever", "reward", "lick"]))
    _rewrite(packet_root, "events", renamed)
    assert validate(open_packet(packet_root)).passed


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
    _rewrite(packet_root, "units", units.append_column("amplitude_unit", pa.array(values, type=pa.string())))
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
        _rewrite(packet_root, "clocks", clocks.append_column("tick_rate_hz", pa.array(values, type=pa.float64())))
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
        _rewrite(packet_root, "events", events.append_column(column["name"], values))
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
    _rewrite(packet_root, "intervals", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.intervals.interval_valid" for f in report.findings)


def test_wrong_column_type_is_caught_before_any_query(packet_root):
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    narrowed = intervals.set_column(2, "start_tick", intervals.column("start_tick").cast(pa.int32()))
    _rewrite(packet_root, "intervals", narrowed)
    report = validate(open_packet(packet_root))
    assert any(f.check == "schema.column_type" for f in report.findings)


def test_physical_order_is_an_error(packet_root):
    """Part 03 §5.3. A waiver may not rest on a property nothing requires.

    Part 02 §10.1 skips the uniqueness query for a table whose order settles its key, so the order
    is what a correctness check is discharged by and a departure fails the packet.
    """
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    _rewrite(packet_root, "events", events.take([2, 0, 1]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    (finding,) = [f for f in report.findings if f.check == "core.events.physical_order"]
    assert finding.level == "error"
    # The second row sorts before the first: a finding names a row by its position.
    assert [row[0] for row in finding.rows] == ["row 2"]


def test_registry_version_must_match_its_descriptor(packet_root):
    registry = read_registry(packet_root)
    registry["registry_version"] = "0.2.0"
    install_registry(packet_root, registry)
    manifest = json.loads((packet_root / "packet.json").read_text())
    manifest["registries"]["core"]["version"] = "0.1.0"
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert "packet.registry.version" in {f.check for f in report.findings}


def test_a_missing_bound_registry_fails_the_packet(packet_root):
    manifest = json.loads((packet_root / "packet.json").read_text())
    (packet_root / manifest["registries"]["core"]["path"]).unlink()
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert [f.check for f in report.findings] == ["packet.registry.missing"]
    assert report.registries == [] and report.evaluations == []


def test_no_caller_supplied_registry_can_stand_in_for_a_bound_one(packet_root):
    """Part 05 §14.5: the packet's bound registries direct its checks, so there is no override."""
    assert "registry" not in inspect.signature(validate).parameters
    manifest = json.loads((packet_root / "packet.json").read_text())
    manifest["registries"]["core"]["sha256"] = "0" * 64
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert {f.check for f in report.findings} == {"packet.registry.digest"}


def test_unsupported_registry_result_is_preserved_and_dependent_checks_are_skipped(packet_root):
    registry = read_registry(packet_root)
    registry["$schema"] = "https://example.org/unknown"
    install_registry(packet_root, registry)
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert report.registries[0].result.state == "unsupported"
    assert not report.registries[0].directs_checks
    assert not any(f.check.startswith("core.intervals.") for f in report.findings)


def test_invalid_json_registry_is_a_complete_result_not_a_crash(packet_root):
    install_registry(packet_root, read_registry(packet_root), body=b"{not json")
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert report.registries[0].result.state == "invalid"
    assert "registry.json.invalid_syntax" in {finding.check for finding in report.findings}


def test_absent_tables_are_not_required(packet_root):
    """A packet need not carry every table the registry defines."""
    import json as _json

    path = packet_root / "packet.json"
    entry = _json.loads(path.read_text())
    entry["resources"] = [r for r in entry["resources"] if r["resource_id"] != "core.spike_events"]
    path.write_text(_json.dumps(entry))
    assert validate(open_packet(packet_root)).passed


def test_a_populated_foreign_key_requires_its_target_resource(packet_root):
    path = packet_root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"] = [resource for resource in manifest["resources"] if resource["resource_id"] != "core.clocks"]
    path.write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert "packet.resource.reference_target_missing" in {finding.check for finding in report.findings}


def test_an_unknown_resource_declaration_is_rejected(packet_root):
    path = packet_root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"][0]["declaration_id"] = "core.not_declared"
    path.write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert "packet.resource.declaration_unknown" in {finding.check for finding in report.findings}


def test_report_renders_as_json(packet_root):
    report = validate(open_packet(packet_root))
    rendered = report.to_dict("session_001")
    assert rendered["status"] == "passed"
    assert rendered["summary"] == {"errors": 0, "warnings": 0}
    assert rendered["registries"][0]["subject"] == "core"
    assert rendered["registries"][0]["result"]["state"] == "valid"


def _add_family_declaration(root, declaration_id, *, content_class="core"):
    """Add an opaque family for tests concerned with generic manifest behavior."""
    registry = read_registry(root)
    registry["resources"][declaration_id] = {
        "content_class": content_class,
        "kind": "opaque",
        "instances": {"mode": "family"},
        "requires": [],
        "lineage": "forbidden" if content_class == "documentation" else "optional",
    }
    install_registry(root, registry)


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
    _rewrite(packet_root, "intervals", filled)
    report = validate(open_packet(packet_root))
    assert not [f for f in report.findings if f.check == "core.intervals.metadata_unfilled"]


def test_retired_codec_summary_is_rejected_by_the_manifest_schema(packet_root):
    _add_family_declaration(packet_root, "core.test_payloads")
    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "core.probe0",
            "declaration_id": "core.test_payloads",
            "uri": "s3://example/p.zarr",
            "external": True,
            "validation_state": "not_run",
        }
    )
    entry["required_codecs"] = ["wavpack"]
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert {f.check for f in report.findings} == {"packet.manifest.schema"}


def test_an_external_resource_with_no_floor_is_not_reported_unassessed(packet_root):
    """Part 05 §5.3: an opaque resource has no reader floor, so there is nothing left unassessed."""
    _add_family_declaration(packet_root, "core.test_payloads")
    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "core.probe0",
            "declaration_id": "core.test_payloads",
            "uri": "s3://example/p.zarr",
            "external": True,
            "validation_state": "not_run",
        }
    )
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    assert report.passed  # unreachable externals do not invalidate
    assert "external.physical_unassessed" not in {f.check for f in report.findings}


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


def test_report_records_whether_advisories_ran(packet_root):
    """An empty advisory result is ambiguous unless the report says (R26 §5)."""
    assert validate(open_packet(packet_root)).to_dict("p")["advisory"] is False
    assert validate(open_packet(packet_root), advisory=True).to_dict("p")["advisory"] is True


# -- resource lineage (Part 04 §7) -----------------------------------------------------------


def _declare(root, **overrides):
    """Add an analysis resource to the manifest, pointing at a table that already exists."""
    registry = read_registry(root)
    registry["resources"]["analysis.test_output"] = {
        "content_class": "analysis",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "required",
        "table": {**registry["resources"]["core.intervals"]["table"], "rules": [], "amendment_groups": []},
    }
    install_registry(root, registry)
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    entry = {
        "resource_id": "analysis.test_output",
        "declaration_id": "analysis.test_output",
        "uri": "tables/core/intervals.parquet",
        "digest": owned_digest(root, "tables/core/intervals.parquet"),
        "validation_state": "passed",
        "derived_from": ["core.intervals"],
        **overrides,
    }
    manifest["resources"].append({key: value for key, value in entry.items() if value is not None})
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def test_an_analysis_resource_names_its_lineage_and_no_run(packet_root):
    """Part 06 §5: a materialization's run is optional provenance the manifest does not carry."""
    _declare(packet_root)
    report = validate(open_packet(packet_root))
    assert report.passed, [f for f in report.findings if f.level == "error"]


def test_an_analysis_resource_without_lineage_is_an_error(packet_root):
    _declare(packet_root, derived_from=None)
    report = validate(open_packet(packet_root))
    assert "packet.resource.derived_from_required" in {f.check for f in report.findings}


def test_a_manifest_entry_naming_a_run_is_refused_by_its_schema(packet_root):
    _declare(packet_root, processing_run_id="ghost")
    report = validate(open_packet(packet_root))
    assert not report.passed
    finding = next(f for f in report.findings if f.check == "packet.manifest.schema")
    assert finding.rows[0][1].endswith("/additionalProperties")


def test_a_duplicate_beside_its_twin_is_caught_by_the_scan(packet_root):
    """core.intervals is sorted by its key, so duplicates are neighbours and no GROUP BY runs."""
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    _rewrite(packet_root, "intervals", intervals.take([0, 0, 1]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    (finding,) = [f for f in report.findings if f.check == "core.intervals.primary_key_unique"]
    assert [row[0] for row in finding.rows] == ["row 2"]  # the second row repeats the first


def test_a_duplicate_out_of_order_still_fails(packet_root):
    """Adjacency is unsound on an unordered file, so uniqueness falls back to the aggregate.

    Ordering stays a warning -- a packet in the wrong order still conforms -- so the fallback
    is what keeps the check from passing by omission.
    """
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    _rewrite(packet_root, "intervals", intervals.take([1, 0, 0]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.intervals.primary_key_unique" for f in report.findings)


def test_validation_leaves_nothing_in_the_packet(packet_root):
    """The spill goes beside the packet, not inside it: a packet's bytes are settled, and one
    on read-only media must still be validatable."""
    before = {p.name for p in packet_root.iterdir()}
    validate(open_packet(packet_root))
    assert {p.name for p in packet_root.iterdir()} == before


# -- packet-owned arrays (Part 04 §5.3, level 2) ------------------------------------------------
#
# These are shim checks, not SQL (R12 §4): a query cannot see a chunk grid. The store below
# is a real Zarr v3 array with no chunk files, which is valid -- every chunk reads as
# `fill_value` -- so the metadata under test is the whole array.


def _zarr_v3(*, sharded=True, fill_value=0, grid="regular"):
    codecs = [{"name": "bytes"}, {"name": "blosc"}]
    document = {
        "zarr_format": 3,
        "node_type": "array",
        "shape": [4, 2, 3],
        "data_type": "int16",
        "chunk_grid": {"name": grid, "configuration": {"chunk_shape": [4, 2, 3] if sharded else [1, 2, 3]}},
        "chunk_key_encoding": {"name": "default"},
        "codecs": (
            [{"name": "sharding_indexed", "configuration": {"chunk_shape": [1, 2, 3], "codecs": codecs}}]
            if sharded
            else codecs
        ),
        "dimension_names": ["unit", "channel", "sample"],
    }
    if fill_value is not None:
        document["fill_value"] = fill_value
    return document


def _add_array(root, *, declared, document=None, axes=3, external=False):
    """Bolt an array onto a packet, with whatever the manifest should claim about it."""
    manifest = json.loads((root / "packet.json").read_text())
    uri = "arrays/core/wf.zarr"
    store = root / uri
    store.mkdir(parents=True)
    (store / "zarr.json").write_text(json.dumps(document or _zarr_v3()))

    registry = read_registry(root)
    common = {
        "content_class": "core",
        "requires": [],
        "lineage": "optional",
    }
    registry["resources"]["core.array_assets"] = {
        **common,
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "Array row identity.",
                },
                {
                    "name": "array_asset_name",
                    "type": "string",
                    "presence": "optional",
                    "role": "data",
                    "vocabulary": "free",
                    "description": "Source array label.",
                },
                {
                    "name": "resource_id",
                    "type": "string",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "carried",
                    "vocabulary": "free",
                    "description": "Packet resource identity.",
                },
                {
                    "name": "metadata",
                    "type": "json_string",
                    "presence": "optional",
                    "role": "data",
                    "description": (
                        "What the source stated about this row that the standard does not model, "
                        "carried in the source's own vocabulary and read by no rule."
                    ),
                },
            ],
            "primary_key": ["array_asset_id"],
            "amendment_groups": [["array_asset_id"]],
            "references": [],
            "rules": [],
        },
    }
    registry["resources"]["core.array_dimensions"] = {
        **common,
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "Array row identity.",
                },
                {
                    "name": "axis_index",
                    "type": "int64",
                    "presence": "required",
                    "role": "structural_index",
                    "description": "Zero-based axis index.",
                },
                {
                    "name": "dimension_name",
                    "type": "string",
                    "presence": "required",
                    "role": "data",
                    "vocabulary": "free",
                    "description": "Axis name.",
                },
                {
                    "name": "coordinate_resource",
                    "type": "string",
                    "presence": "optional",
                    "role": "data",
                    "vocabulary": "free",
                    "description": "Optional coordinate resource.",
                },
            ],
            "primary_key": ["array_asset_id", "axis_index"],
            "amendment_groups": [["array_asset_id", "axis_index"]],
            "references": [
                {
                    "columns": ["array_asset_id"],
                    "resource": "core.array_assets",
                    "resource_columns": ["array_asset_id"],
                }
            ],
            "rules": [],
        },
    }
    registry["resources"]["core.array_asset_instances"] = {
        **common,
        "kind": "dense_array",
        "instances": {
            "mode": "catalog",
            "catalog_resource": "core.array_assets",
            "resource_id_column": "resource_id",
        },
        "array": {"axes_resource": "core.array_dimensions"},
    }
    install_registry(root, registry)
    manifest["registries"] = json.loads((root / "packet.json").read_text())["registries"]

    assets = pa.table(
        {
            "array_asset_id": pa.array([1], type=pa.int32()),
            "array_asset_name": pa.array(["wf"]),
            "resource_id": pa.array(["core.waveform_mean"]),
        }
    )
    pq.write_table(assets, root / "tables" / "core" / "array_assets.parquet")
    manifest["resources"].append(
        {
            "resource_id": "core.array_assets",
            "declaration_id": "core.array_assets",
            "uri": "tables/core/array_assets.parquet",
            "digest": owned_digest(root, "tables/core/array_assets.parquet"),
            "validation_state": "passed",
        }
    )

    if axes is not None:
        dimensions = pa.table(
            {
                "array_asset_id": pa.array([1] * axes, type=pa.int32()),
                "axis_index": pa.array(list(range(axes)), type=pa.int64()),
                "dimension_name": pa.array(["unit", "channel", "sample"][:axes]),
            }
        )
        (root / "tables" / "core").mkdir(parents=True, exist_ok=True)
        pq.write_table(dimensions, root / "tables" / "core" / "array_dimensions.parquet")
        manifest["resources"].append(
            {
                "resource_id": "core.array_dimensions",
                "declaration_id": "core.array_dimensions",
                "uri": "tables/core/array_dimensions.parquet",
                "digest": owned_digest(root, "tables/core/array_dimensions.parquet"),
                "validation_state": "passed",
            }
        )

    entry = {
        "resource_id": "core.waveform_mean",
        "declaration_id": "core.array_asset_instances",
        "uri": uri,
        "validation_state": "passed",
    }
    if external:
        entry |= {"external": True, "uri": f"file://{store}"}
    else:
        entry["digest"] = owned_digest(root, uri)
    manifest["resources"].append(entry)
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return root


def _checks(report, prefix="array."):
    return {f.check for f in report.findings if f.check.startswith(prefix)}


def test_an_array_declaring_its_codecs_correctly_is_clean(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"])
    assert _checks(validate(open_packet(packet_root))) == set()


def test_a_catalog_row_requires_its_declared_resource(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"])
    path = packet_root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"] = [
        resource for resource in manifest["resources"] if resource["resource_id"] != "core.waveform_mean"
    ]
    path.write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert "packet.resource.catalog_row_binding" in {finding.check for finding in report.findings}


def test_a_packet_owned_array_must_be_zarr_v3(packet_root):
    """Part 03 §6.1 allows v2 only for an array the packet references."""
    v2 = {"zarr_format": 2, "shape": [4, 2, 3], "chunks": [1, 2, 3], "dtype": "<i2", "fill_value": 0}
    store = packet_root / "arrays" / "core" / "wf.zarr"
    _add_array(packet_root, declared=[])
    (store / "zarr.json").unlink()
    (store / ".zarray").write_text(json.dumps(v2))
    assert "array.not_zarr_v3" in _checks(validate(open_packet(packet_root)))


def test_an_array_without_a_fill_value_is_caught(packet_root):
    """Part 03 §6.1 requires one: without it an unwritten chunk has no defined value."""
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=_zarr_v3(fill_value=None))
    assert "array.no_fill_value" in _checks(validate(open_packet(packet_root)))


def test_an_irregular_chunk_grid_is_caught(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=_zarr_v3(grid="rectilinear"))
    assert "array.irregular_chunk_grid" in _checks(validate(open_packet(packet_root)))


def test_a_transpose_inside_a_shard_is_caught(packet_root):
    """Part 03 §6.2 bans `transpose` from the whole chain, a shard's own pipeline included."""
    document = _zarr_v3()
    document["codecs"][0]["configuration"]["codecs"].insert(0, {"name": "transpose"})
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=document)
    assert "array.transpose_codec" in _checks(validate(open_packet(packet_root)))


def test_a_rank_the_dimensions_do_not_cover_is_caught(packet_root):
    """Part 03 §6.3: axis_index enumerates every stored axis, so two rows cannot describe rank 3."""
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=2)
    assert "array.rank_disagrees_with_dimensions" in _checks(validate(open_packet(packet_root)))


def test_no_array_dimensions_at_all_is_caught(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=None)
    assert "array.no_array_dimensions_table" in _checks(validate(open_packet(packet_root)))


def test_an_external_array_is_left_to_the_external_mode(packet_root):
    """Level 3, not level 2: reaching it is the reader's situation, not the packet's defect."""
    _add_array(packet_root, declared=["blosc"], external=True)
    assert _checks(validate(open_packet(packet_root))) == set()


def test_scanning_nothing_leaves_the_ordering_unchecked(packet_root):
    """What `commit` relies on: a caller that established the order elsewhere skips the read."""
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    _rewrite(packet_root, "intervals", intervals.sort_by([("interval_id", "descending")]))
    assert any(f.check == "core.intervals.physical_order" for f in validate(open_packet(packet_root)).findings)
    assert not any(
        f.check == "core.intervals.physical_order" for f in validate(open_packet(packet_root), scan=set()).findings
    )


# -- Part 05 §15.4: an amendment re-runs only the rules its own resources implicate ---------------


def test_recheck_still_catches_a_break_in_what_was_written(packet_root):
    """Narrowing must not narrow away the resource the amendment actually wrote."""
    duplicated = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    _rewrite(packet_root, "intervals", pa.concat_tables([duplicated, duplicated.slice(0, 1)]))
    report = validate(open_packet(packet_root), recheck={"core.intervals"})
    assert not report.passed


# -- R14/R15/R21: external resources -------------------------------------------------------


def _external(root, **overrides):
    """Point a packet at a Zarr v2 array beside it, the way an LFP reference does."""
    array = root.parent / "external.zarr"
    array.mkdir(exist_ok=True)
    (array / ".zarray").write_text(
        json.dumps(
            {
                "shape": [4, 2],
                "chunks": [4, 2],
                "dtype": "<i2",
                "zarr_format": 2,
                "compressor": {"id": "blosc"},
                "filters": None,
                "order": "C",
                "fill_value": 0,
            }
        )
    )
    (array / "0.0").write_bytes(b"x" * 100)
    total = sum(f.stat().st_size for f in array.rglob("*") if f.is_file())
    _add_array(root, declared=["blosc"], axes=2, external=True)
    manifest = json.loads((root / "packet.json").read_text())
    entry = next(resource for resource in manifest["resources"] if resource["resource_id"] == "core.waveform_mean")
    entry.update(
        {
            "uri": array.resolve().as_uri(),
            "external": True,
            "size_bytes": total,
            **overrides,
        }
    )
    for key, value in tuple(entry.items()):
        if value is None:
            entry.pop(key)
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_an_external_resource_is_reported_as_unverified_by_default(packet_root):
    """Part 04 §5.3: structural validation must not reach for bytes the packet does not own."""
    report = validate(open_packet(_external(packet_root)))
    assert report.passed
    [finding] = [f for f in report.findings if f.check == "external.physical_unassessed"]
    assert (finding.level, finding.rows, finding.registry) == ("info", (("core.waveform_mean",),), "core")
    assert "physical.outside_reader_floor" not in {f.check for f in report.findings}


def test_the_requested_mode_resolves_it(packet_root):
    report = validate(open_packet(_external(packet_root)), verification=Verification(external=True))
    assert report.passed
    checks = {f.check for f in report.findings}
    assert "external.verified" in checks
    assert "external.physical_unassessed" not in checks, "the two modes must not both speak"


def test_size_bytes_counts_the_whole_prefix_including_its_metadata(packet_root):
    """A dense array asset is a prefix of many objects, so its size is a list, not a stat.
    Excluding the metadata document would make the writer and the validator disagree."""
    assert validate(open_packet(_external(packet_root)), verification=Verification(external=True)).passed


def test_a_size_that_disagrees_is_an_error_only_in_that_mode(packet_root):
    root = _external(packet_root, size_bytes=999)
    assert validate(open_packet(root)).passed
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed
    assert "external.size_bytes" in {f.check for f in report.findings}


def test_an_unreachable_resource_is_a_warning_not_an_error(packet_root):
    """Reachability is a property of the reader's situation, not of the packet."""
    root = _external(packet_root, uri="file:///nowhere/at/all.zarr")
    report = validate(open_packet(root), verification=Verification(external=True))
    assert report.passed
    assert "external.unreachable" in {f.check for f in report.findings}


def test_a_requested_digest_with_nothing_recorded_says_so(packet_root):
    """Part 04 §4.3: an external resource need not record a digest.
    Asking for checksums and finding nothing to compare must not report a clean verification."""
    report = validate(open_packet(_external(packet_root)), verification=Verification(checksums=True, external=True))
    assert report.passed, "a claim the packet never made is not a failure"
    assert "external.no_checksum" in {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert "digest" not in verified.message, "it compared none, so it must not claim any"


@pytest.mark.parametrize("algorithm", ["sha256", "crc64nvme", "crc32c", "crc32"])
def test_a_recorded_digest_is_compared(packet_root, algorithm):
    from escapewheel_validator.stores import digest

    root = _external(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r.get("external"))
    entry["digest"] = {"algorithm": algorithm, "value": digest(entry["uri"], algorithm)}
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root), verification=Verification(checksums=True, external=True))
    assert report.passed
    assert "external.no_checksum" not in {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert "1 digest" in verified.message and "route: computed for all 1" in verified.message
    assert verified.rows == (("core.waveform_mean", algorithm, "computed"),)


def test_a_digest_that_disagrees_is_an_error(packet_root):
    root = _external(packet_root, digest={"algorithm": "sha256", "value": "0" * 64})
    assert validate(open_packet(root), verification=Verification(external=True)).passed, "not read without checksums"
    report = validate(open_packet(root), verification=Verification(checksums=True, external=True))
    assert not report.passed
    assert "external.digest" in {f.check for f in report.findings}


def test_the_summary_names_what_it_compared(packet_root):
    """ "Resolved and checked" said nothing about which claims were actually tested."""
    report = validate(open_packet(_external(packet_root)), verification=Verification(external=True))
    message = next(f for f in report.findings if f.check == "external.verified").message
    assert "1 rank" in message and "1 size_bytes" in message


def _with_members(root, *, mutate=None):
    """Declare Part 04 §5.4 members for the external resource, as a writer at verify="members" would."""
    from escapewheel_validator.stores import listing

    manifest = json.loads((root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r.get("external"))
    entry["members"] = [{"key": m.key, "size_bytes": m.size_bytes} for m in listing(entry["uri"]).members]
    if mutate is not None:
        mutate(entry)
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_declared_members_are_checked_against_the_store(packet_root):
    report = validate(open_packet(_with_members(_external(packet_root))), verification=Verification(external=True))
    assert report.passed
    assert "1 members" in next(f for f in report.findings if f.check == "external.verified").message


def test_a_member_the_store_does_not_hold_is_an_error(packet_root):
    def add(entry):
        entry["members"].append({"key": "9.9", "size_bytes": 1})
        entry["size_bytes"] += 1  # so the entry stays self-consistent and only the store disagrees

    root = _with_members(_external(packet_root), mutate=add)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed
    assert "external.members" in {f.check for f in report.findings}


def test_a_member_size_that_disagrees_is_caught_where_the_total_would_not(packet_root):
    """Two members changing in opposite directions leave `size_bytes` correct. Part 04 §5.4."""

    def swap(entry):
        entry["members"][0]["size_bytes"] += 10
        entry["members"][1]["size_bytes"] -= 10

    root = _with_members(_external(packet_root), mutate=swap)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed, "the total still agrees, so only a per-member check sees this"
    assert "external.members" in {f.check for f in report.findings}


def test_store_digests_report_what_they_could_not_check(packet_root):
    """A local filesystem offers no content hash, so every member is skipped, not passed."""
    report = validate(
        open_packet(_with_members(_external(packet_root))), verification=Verification(store_digests=True, external=True)
    )
    assert report.passed
    assert "external.no_store_digest" in {f.check for f in report.findings}
    assert "store_digest" not in next(f for f in report.findings if f.check == "external.verified").message


def test_a_store_digest_that_changed_in_place_is_an_error(packet_root, monkeypatch):
    """Neither the size nor a recorded digest need change for this to fire, and a multipart tag compares."""
    from escapewheel_validator import stores as module
    from escapewheel_validator.stores import Listing, Member, StoreDigest, listing

    def stamped(uri, **kwargs):
        found = listing(uri, **kwargs)
        return Listing(
            tuple(
                Member(m.key, m.size_bytes, StoreDigest("etag", f'"{index:032x}-2"'))
                for index, m in enumerate(found.members)
            ),
            found.size_bytes,
        )

    root = _with_members(_external(packet_root))
    monkeypatch.setattr(module, "listing", stamped)
    passing = validate(
        open_packet(
            _with_members(
                root,
                mutate=lambda e: [
                    m.update(store_digest={"algorithm": "etag", "value": f'"{i:032x}-2"'})
                    for i, m in enumerate(e["members"])
                ],
            )
        ),
        verification=Verification(store_digests=True, external=True),
    )
    assert passing.passed
    assert "1 store_digest" in next(f for f in passing.findings if f.check == "external.verified").message

    changed = validate(
        open_packet(
            _with_members(
                root,
                mutate=lambda e: [
                    m.update(store_digest={"algorithm": "etag", "value": '"' + "f" * 32 + '"'}) for m in e["members"]
                ],
            )
        ),
        verification=Verification(store_digests=True, external=True),
    )
    assert not changed.passed
    assert "external.store_digest" in {f.check for f in changed.findings}


# -- Part 05 §5.3: an external array's shape against what the packet's tables assert ----------


def test_an_external_arrays_rank_is_checked_against_the_dimensions(packet_root):
    """The check `_check_one_array` does for a packet-owned array, for an external one."""
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=2)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed
    assert "external.array_rank" in {f.check for f in report.findings}


def test_a_matching_rank_passes_and_is_counted(packet_root):
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=3)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert "external.array_rank" not in {f.check for f in report.findings}
    assert "1 rank" in next(f for f in report.findings if f.check == "external.verified").message


def _manifest_table(root, manifest, name, table):
    """Write a core table and declare it in `manifest`, once."""
    path = f"tables/core/{name.removeprefix('core.')}.parquet"
    pq.write_table(table, root / path)
    manifest["resources"] = [r for r in manifest["resources"] if r["resource_id"] != name]
    manifest["resources"].append(
        {
            "resource_id": name,
            "declaration_id": name,
            "uri": path,
            "digest": owned_digest(root, path),
            "validation_state": "passed",
        }
    )


def _index(name, **extra):
    return {
        "name": name,
        "type": "int64",
        "presence": "required",
        "role": "structural_index",
        "description": "d",
        **extra,
    }


def _label_axis(root, labels, *, depends_on=None, kind="core.sessions"):
    """Label axis 1 of the test array by `kind`'s rows (Part 03 §6.3).

    `labels` holds (`depends_on_position_index`, `position_index`, `label_id`) rows; `depends_on`
    makes axis 1 depend on that axis.
    """
    registry = read_registry(root)
    dimensions = registry["resources"]["core.array_dimensions"]["table"]
    replaced = {"coordinate_resource", "depends_on_axis_index"}
    dimensions["columns"] = [c for c in dimensions["columns"] if c["name"] not in replaced] + [
        {
            "name": "coordinate_resource",
            "type": "string",
            "presence": "nullable",
            "role": "discriminator",
            "resolves": "required",
            "discriminates_via": "core.array_labels.axis_index",
            "discriminates": "label_id",
            "description": "d",
        },
        _index("depends_on_axis_index", presence="nullable"),
    ]
    registry["resources"]["core.array_labels"] = {
        "content_class": "core",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "d",
                },
                _index("axis_index"),
                _index("depends_on_position_index"),
                _index("position_index"),
                {
                    "name": "label_id",
                    "type": "int32",
                    "presence": "nullable",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "d",
                },
            ],
            "primary_key": ["array_asset_id", "axis_index", "depends_on_position_index", "position_index"],
            "amendment_groups": [["array_asset_id", "axis_index", "depends_on_position_index", "position_index"]],
            "references": [
                {
                    "columns": ["array_asset_id", "axis_index"],
                    "resource": "core.array_dimensions",
                    "resource_columns": ["array_asset_id", "axis_index"],
                }
            ],
            "rules": [],
        },
    }
    install_registry(root, registry)
    manifest = json.loads((root / "packet.json").read_text())
    current = pq.read_table(root / "tables" / "core" / "array_dimensions.parquet").to_pydict()
    rank = len(current["axis_index"])
    _manifest_table(
        root,
        manifest,
        "core.array_dimensions",
        pa.table(
            {
                "array_asset_id": pa.array(current["array_asset_id"], type=pa.int32()),
                "axis_index": pa.array(current["axis_index"], type=pa.int64()),
                "dimension_name": pa.array(current["dimension_name"]),
                "coordinate_resource": pa.array([kind if axis == 1 else None for axis in range(rank)]),
                "depends_on_axis_index": pa.array(
                    [depends_on if axis == 1 else None for axis in range(rank)], type=pa.int64()
                ),
            }
        ),
    )
    _manifest_table(
        root,
        manifest,
        "core.array_labels",
        pa.table(
            {
                "array_asset_id": pa.array([1] * len(labels), type=pa.int32()),
                "axis_index": pa.array([1] * len(labels), type=pa.int64()),
                "depends_on_position_index": pa.array([row[0] for row in labels], type=pa.int64()),
                "position_index": pa.array([row[1] for row in labels], type=pa.int64()),
                "label_id": pa.array([row[2] for row in labels], type=pa.int32()),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_an_external_axis_is_checked_against_its_labels(packet_root):
    """A re-generated array with a different channel count leaves its labels naming positions that
    are not there, or positions with none (Part 03 §6.3)."""
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 1)])  # axis 1 is 2 long in _zarr_v3's [4, 2, 3]
    report = validate(open_packet(root), verification=Verification(external=True))
    assert report.passed, [f for f in report.findings if f.level == "error"]
    assert "1 labels" in next(f for f in report.findings if f.check == "external.verified").message

    _label_axis(root, [(0, 0, 1), (0, 1, 1), (0, 2, 1)])
    assert "external.array_label_position_out_of_range" in _checks(
        validate(open_packet(root), verification=Verification(external=True)), ""
    )

    _label_axis(root, [(0, 0, 1)])
    assert "external.array_label_missing" in _checks(
        validate(open_packet(root), verification=Verification(external=True)), ""
    )


def test_a_packet_owned_axis_is_checked_against_its_labels(packet_root):
    """Checked without asking, unlike an external array, since the owned array's shape is in hand."""
    root = _add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 1)])
    assert validate(open_packet(root)).passed

    _label_axis(root, [(0, 0, 1), (0, 1, 1), (0, -1, 1)])
    assert "array.label_position_out_of_range" in _checks(validate(open_packet(root)))


def test_a_dependent_axis_is_labelled_at_every_pair_of_positions(packet_root):
    """Axis 1 depends on axis 0, which is 4 long, so its 2 positions need 8 rows; padding is a row."""
    root = _add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    full = [(outer, position, 1 if position == 0 else None) for outer in range(4) for position in range(2)]
    _label_axis(root, full, depends_on=0)
    assert validate(open_packet(root)).passed

    _label_axis(root, full[:-1], depends_on=0)
    missing = next(f for f in validate(open_packet(root)).findings if f.check == "array.label_missing")
    assert missing.rows == (("axis_index 1", "depends_on_position_index 3, position_index 1", "1 missing"),)

    _label_axis(root, [*full, (4, 0, 1)], depends_on=0)
    assert "array.depends_on_position_out_of_range" in _checks(validate(open_packet(root)))


def test_a_label_naming_no_row_is_caught(packet_root):
    """Part 02 §8.3: the paired value on the specialised table resolves in the kind its axis names."""
    root = _add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 7)])
    checks = {f.check for f in validate(open_packet(root)).findings if f.level == "error"}
    assert checks == {"core.array_dimensions.coordinate_resource.core_sessions_resolves"}


def test_a_label_on_an_unlabelled_axis_is_caught(packet_root):
    """A label row whose axis names no kind has a value nothing can resolve (Part 02 §8.3)."""
    root = _add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    _label_axis(root, [(0, 0, 1), (0, 1, 1)], kind=None)
    checks = {f.check for f in validate(open_packet(root)).findings if f.level == "error"}
    assert "core.array_dimensions.coordinate_resource.specialised_row_has_kind" in checks


def test_a_packet_owned_array_carries_its_axes_names(packet_root):
    """Part 03 §6.5: the axes table owns the names, and a packet-owned array repeats them."""
    document = _zarr_v3()
    document["dimension_names"] = ["unit", "sample", "channel"]
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=document)
    assert "array.dimension_names" in _checks(validate(open_packet(packet_root)))


def test_a_packet_owned_array_without_dimension_names_is_caught(packet_root):
    document = _zarr_v3()
    del document["dimension_names"]
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=document)
    assert "array.dimension_names" in _checks(validate(open_packet(packet_root)))


def test_a_referenced_array_may_name_its_axes_otherwise(packet_root):
    """The axes table governs an external array's names, which its producer chose (Part 03 §6.5)."""
    document = _zarr_v3()
    del document["dimension_names"]
    root = _add_array(packet_root, declared=["blosc", "sharding_indexed"], document=document, external=True)
    assert validate(open_packet(root), verification=Verification(external=True)).passed


def _channels(root, *, rows):
    """Give axis 1 of the test array `rows` channels in `core.array_channels`."""
    registry = read_registry(root)
    registry["resources"]["core.array_channels"] = {
        "content_class": "core",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "optional",
        "table": {
            "columns": [
                {
                    "name": "array_asset_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                    "description": "d",
                },
                _index("axis_index"),
                _index("channel_index"),
            ],
            "primary_key": ["array_asset_id", "channel_index"],
            "amendment_groups": [["array_asset_id", "channel_index"]],
            "references": [
                {
                    "columns": ["array_asset_id", "axis_index"],
                    "resource": "core.array_dimensions",
                    "resource_columns": ["array_asset_id", "axis_index"],
                }
            ],
            "rules": [],
        },
    }
    install_registry(root, registry)
    manifest = json.loads((root / "packet.json").read_text())
    _manifest_table(
        root,
        manifest,
        "core.array_channels",
        pa.table(
            {
                "array_asset_id": pa.array([1] * rows, type=pa.int32()),
                "axis_index": pa.array([1] * rows, type=pa.int64()),
                "channel_index": pa.array(list(range(rows)), type=pa.int64()),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_a_channel_index_beyond_its_axis_is_caught(packet_root):
    """`core.array_channels` describes positions of an axis, so each must be one (Part 05 §5.3)."""
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=3)
    _channels(root, rows=2)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert report.passed
    assert "1 channels" in next(f for f in report.findings if f.check == "external.verified").message

    _channels(root, rows=3)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert "external.array_channel_index_out_of_range" in _checks(report, "")


# -- Part 04 §4.3 and §5.3: a packet-owned resource's digest ----------------------------------


def _record_owned_digests(root, *, algorithm="sha256", corrupt=None):
    """Record every packet-owned resource's digest under `algorithm`, one wrong where `corrupt` names it."""
    manifest = json.loads((root / "packet.json").read_text())
    for entry in manifest["resources"]:
        if not entry.get("external"):
            entry["digest"] = owned_digest(root, entry["uri"], algorithm)
    if corrupt is not None:
        target = next(e for e in manifest["resources"] if e["resource_id"] == corrupt)
        target["digest"]["value"] = "0" * len(target["digest"]["value"])
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


@pytest.mark.parametrize("algorithm", ["sha256", "crc64nvme", "crc32c", "crc32"])
def test_packet_owned_digests_are_checked(packet_root, algorithm):
    report = validate(
        open_packet(_record_owned_digests(packet_root, algorithm=algorithm)),
        verification=Verification(checksums=True, external=False),
    )
    assert report.passed
    verified = next(f for f in report.findings if f.check == "owned.verified")
    assert verified.message.startswith("6 of 6") and verified.message.endswith("route: computed for all 6")
    assert {row[1:] for row in verified.rows} == {(algorithm, "computed")}, "each digest names its route"


@pytest.mark.parametrize("algorithm", ["sha256", "crc64nvme", "crc32c", "crc32"])
def test_a_packet_owned_file_one_byte_off_is_an_error(packet_root, algorithm):
    """Part 05 §15.4 bounds revalidation on immutability. This is what checks the premise.

    The recorded value is of the file with one byte flipped, so the file itself stays readable.
    """
    from escapewheel_validator.stores import hasher

    root = _record_owned_digests(packet_root, algorithm=algorithm)
    body = bytearray((root / "tables" / "core" / "intervals.parquet").read_bytes())
    body[len(body) // 2] ^= 0x01
    function = hasher(algorithm)
    function.update(bytes(body))
    manifest = json.loads((root / "packet.json").read_text())
    intervals = next(e for e in manifest["resources"] if e["resource_id"] == "core.intervals")
    intervals["digest"]["value"] = function.hexdigest()
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root), verification=Verification(checksums=True, external=False))
    assert not report.passed
    assert [f.message.split(":")[0] for f in report.findings if f.check == "owned.digest"] == ["core.intervals"]


def test_a_recorded_digest_is_not_read_without_checksums(packet_root):
    root = _record_owned_digests(packet_root, corrupt="core.intervals")
    assert validate(open_packet(root)).passed, "not read without checksums"
    assert "owned.digest" in {
        f.check for f in validate(open_packet(root), verification=Verification(checksums=True, external=False)).findings
    }


def test_a_packet_owned_resource_without_a_digest_fails_the_manifest(packet_root):
    """Part 04 §4.3: a writer records one for every resource the packet owns."""
    manifest = json.loads((packet_root / "packet.json").read_text())
    del manifest["resources"][1]["digest"]
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert [(f.level, f.check) for f in report.findings] == [("error", "packet.resource.digest_missing")]


def test_a_crc_prefix_digest_is_the_sha256_of_its_listing(packet_root):
    """Part 04 §4.3: under a CRC the members' values are CRCs and the prefix value is 64 digits."""
    from escapewheel_validator.stores import digest, listing, listing_digest

    root = _add_array(packet_root, declared=["zstd"], axes=3)
    (root / "arrays/core/wf.zarr/c/0/0/0").parent.mkdir(parents=True)
    (root / "arrays/core/wf.zarr/c/0/0/0").write_bytes(b"chunk")
    uri = str(root / "arrays/core/wf.zarr")
    rows = [(m.key, m.size_bytes, digest(f"{uri}/{m.key}", "crc32c")) for m in listing(uri).members]
    assert [len(value) for _, _, value in rows] == [8, 8]
    assert digest(uri, "crc32c") == listing_digest(rows)
    _record_owned_digests(root, algorithm="crc32c")
    report = validate(open_packet(root), verification=Verification(checksums=True, external=False))
    assert "owned.digest" not in {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "owned.verified")
    assert verified.message.startswith("9 of 9") and verified.message.endswith("route: computed for all 9")


def test_an_empty_packet_owned_prefix_is_missing(packet_root):
    """Part 04 §4.3: a prefix holding no object does not exist."""
    root = _add_array(packet_root, declared=["zstd"], axes=3)
    (root / "arrays/core/wf.zarr/zarr.json").unlink()
    report = validate(open_packet(root))
    assert ("error", "resource.missing") in {(f.level, f.check) for f in report.findings}
    assert "array.unreadable" not in {f.check for f in report.findings}


# -- R17: an extension is a registry, validated by the same machinery ----------------------


def _extension(root, *, tables=None, mutate=None):
    """Give the packet an extension registry and a table conforming to it."""
    document = {
        "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
        "registry_id": "task",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.2",
        "extension_id": "task",
        "resources": {
            "task.trials": {
                "content_class": "extension",
                "kind": "table",
                "instances": {"mode": "singleton", "presence": "optional"},
                "requires": [],
                "lineage": "optional",
                "table": {
                    "columns": [
                        {
                            "name": "session_id",
                            "type": "int32",
                            "presence": "required",
                            "role": "identifier",
                            "identity": "assigned",
                            "description": "Session identity.",
                        },
                        {
                            "name": "interval_id",
                            "type": "int32",
                            "presence": "required",
                            "role": "identifier",
                            "identity": "assigned",
                            "description": "Interval identity.",
                        },
                        {
                            "name": "choice",
                            "type": "string",
                            "presence": "nullable",
                            "role": "data",
                            "vocabulary": "closed",
                            "enum": ["left", "right"],
                            "description": "Choice.",
                        },
                    ],
                    "primary_key": ["session_id", "interval_id"],
                    "amendment_groups": [["session_id", "interval_id"]],
                    "references": [
                        {
                            "columns": ["session_id", "interval_id"],
                            "resource": "core.intervals",
                            "resource_columns": ["session_id", "interval_id"],
                        }
                    ],
                    "rules": [],
                },
            }
        },
    }
    intervals = pq.read_table(root / "tables" / "core" / "intervals.parquet")
    rows = {
        "session_id": intervals["session_id"].to_pylist(),
        "interval_id": intervals["interval_id"].to_pylist(),
        "choice": ["left"] * intervals.num_rows,
    }
    if mutate is not None:
        mutate(rows)
    (root / "tables" / "task").mkdir(parents=True, exist_ok=True)
    types = {"session_id": pa.int32(), "interval_id": pa.int32(), "choice": pa.string()}
    table = pa.table({name: pa.array(values, type=types.get(name)) for name, values in rows.items()})
    pq.write_table(table, root / "tables" / "task" / "trials.parquet")
    install_registry(root, document)

    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "task.trials",
            "declaration_id": "task.trials",
            "uri": "tables/task/trials.parquet",
            "digest": owned_digest(root, "tables/task/trials.parquet"),
            "validation_state": "passed",
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_an_extension_is_validated_by_the_same_machinery(packet_root):
    """R17 §3: nothing per-extension. `generate` produces its checks from its structure."""
    report = validate(open_packet(_extension(packet_root)))
    assert report.passed
    assert "extension.validated" in {f.check for f in report.findings}


def test_an_extensions_closed_vocabulary_is_enforced(packet_root):
    root = _extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "sideways"))
    report = validate(open_packet(root))
    assert "task.trials.choice.in_vocabulary" in {f.check for f in report.findings}


def test_an_extension_reference_into_core_resolves(packet_root):
    """Part 09 §6.1 lets an extension reference core. Without the cross-registry link the anti-join is
    never generated and an orphan validates clean -- the gap R46 closed for core."""
    root = _extension(packet_root, mutate=lambda r: r["interval_id"].__setitem__(0, 999))
    report = validate(open_packet(root))
    assert any(f.check.endswith("_resolves") and f.registry == "task" for f in report.findings)


def test_an_extension_non_finite_value_is_attributed_to_it(packet_root):
    """Part 05 §5.4 applies the finiteness check to an extension's columns, filed under it (§9.5)."""
    root = _extension(packet_root)
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
    assert _verdicts(report, "core", "task") == ("failed", "passed", "failed")


def _verdicts(report, *registries):
    return report.verdict(), *(report.verdict(name) for name in registries)


def test_an_extension_finding_fails_the_packet_and_not_core(packet_root):
    """Part 05 §9.5: an extension's resources are the packet's, so its failure is the packet's too."""
    root = _extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "sideways"))
    report = validate(open_packet(root))
    assert _verdicts(report, "core", "task") == ("failed", "passed", "failed")
    assert not report.passed
    assert report.bound == ("core", "task")


def test_one_extension_failing_leaves_another_passed(packet_root):
    root = _required_extension(_extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "?")), "cue")
    report = validate(open_packet(root))
    assert _verdicts(report, "core", "task", "cue") == ("failed", "passed", "failed", "passed")


def test_an_extension_table_receives_the_storage_checks(packet_root):
    """Part 05 §5.4: a column type an extension declares is checked as core's are, and filed under it."""
    root = _extension(packet_root)
    table = pq.read_table(root / "tables" / "task" / "trials.parquet")
    widened = table.set_column(0, "session_id", table["session_id"].cast(pa.int64()))
    pq.write_table(widened, root / "tables" / "task" / "trials.parquet")
    report = validate(open_packet(root))
    finding = next(f for f in report.findings if f.check == "schema.column_type")
    assert finding.registry == "task" and finding.message.startswith("task.trials.session_id")
    assert _verdicts(report, "core", "task") == ("failed", "passed", "failed")


def test_an_extension_unit_column_is_checked_against_ucum(packet_root):
    """Part 05 §5.3's unit-code check covers every directing registry's tables."""
    root = _extension(packet_root)
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
    assert _verdicts(report, "core", "task") == ("failed", "passed", "failed")


def test_an_extension_array_defect_fails_the_extension_and_not_core(packet_root):
    """Part 05 §9.5: an array finding belongs to the registry declaring the array, not to core."""
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], document=_zarr_v3(fill_value=None))
    core = read_registry(packet_root)
    declaration = core["resources"].pop("core.array_asset_instances") | {"content_class": "extension"}
    install_registry(packet_root, core)
    install_registry(
        packet_root,
        {
            "$schema": core["$schema"],
            "registry_id": "probe",
            "registry_version": "0.1.0",
            "logical_standard_version": core["logical_standard_version"],
            "rule_language": core["rule_language"],
            "extension_id": "probe",
            "resources": {"probe.waveforms": declaration},
        },
    )
    manifest = json.loads((packet_root / "packet.json").read_text())
    for entry in manifest["resources"]:
        if entry["resource_id"] == "core.waveform_mean":
            entry |= {"resource_id": "probe.waveform_mean", "declaration_id": "probe.waveforms"}
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    assets = pq.read_table(packet_root / "tables" / "core" / "array_assets.parquet")
    _rewrite(packet_root, "array_assets", assets.set_column(2, "resource_id", pa.array(["probe.waveform_mean"])))
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "array.no_fill_value")
    assert finding.registry == "probe"
    assert _verdicts(report, "core", "probe") == ("failed", "passed", "failed")


def test_a_shape_finding_leaves_every_registry_incomplete(packet_root):
    """Part 05 §9.5: an early-phase finding withholds every registry's evaluation."""
    root = _extension(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    manifest["created_at"] = "yesterday"
    (root / "packet.json").write_text(json.dumps(manifest))
    report, _ = check_packet_manifest(root)
    assert [(f.check, f.registry) for f in report.findings] == [("packet.manifest.schema", None)]
    assert _verdicts(report, "core", "task") == ("failed", "incomplete", "incomplete")


def test_the_json_report_states_every_verdict_and_subject(packet_root):
    """Part 05 §9.5: a report states the packet's verdict, each registry's, and each finding's subject."""
    root = _extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "sideways"))
    document = validate(open_packet(root)).to_dict("p")
    assert document["status"] == "failed"
    assert document["verdicts"] == {"core": "passed", "task": "failed"}
    errors = [f for f in document["findings"] if f["level"] == "error"]
    assert [(f["check"], f["registry"]) for f in errors] == [("task.trials.choice.in_vocabulary", "task")]
    assert json.loads(json.dumps(document)) == document


def test_an_extension_the_packet_does_not_carry_is_reported_not_run(packet_root):
    root = _extension(packet_root)
    (root / "tables" / "task" / "trials.parquet").unlink()
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"] = [r for r in manifest["resources"] if r["resource_id"] != "task.trials"]
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    assert "extension.table_absent" in {f.check for f in report.findings}


def _unparseable_extension(root):
    """Bind the extension to bytes that match their digest and are not JSON."""
    install_registry(root, read_registry(root, "task"), body=b"{not json")
    return root


def test_an_unparseable_extension_fails_only_what_needs_it(packet_root):
    """Part 04 §10: a reader fails the operation that needs the registry, naming it."""
    packet = open_packet(_unparseable_extension(_extension(packet_root)))
    assert packet.table("core.intervals").num_rows == 2
    with pytest.raises(RegistryUnavailable) as refused:
        packet.extensions()
    assert (refused.value.registry_id, refused.value.reason) == ("task", RegistryFault.INVALID)


def test_validator_preserves_an_available_unparseable_extension_result(packet_root):
    root = _unparseable_extension(_extension(packet_root))
    report = validate(open_packet(root))
    task = next(item for item in report.registries if item.subject == "task")
    assert task.result.state == "invalid"
    assert _verdicts(report, "core", "task") == ("failed", "passed", "failed")
    assert not any(f.check == "extension.validated" for f in report.findings)


def test_an_extension_that_fails_binding_withholds_only_its_entries(packet_root):
    """Part 04 §10: core's declaration phase still runs, and the extension's entries are not judged."""
    root = _extension(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    manifest["registries"]["task"]["version"] = "0.9.0"
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    binding = next(f for f in report.findings if f.check == "packet.registry.version")
    assert binding.registry == "task"
    assert _verdicts(report, "core", "task") == ("failed", "passed", "failed")
    assert not [f for f in report.findings if f.check.startswith("packet.resource.") and "task." in f.message]
    assert any(e.registry == "core" for e in report.evaluations)


def _required_extension(root, extension_id):
    """Bind a second extension whose only declaration is a required singleton, and carry it."""
    table = {
        "columns": [
            {
                "name": "session_id",
                "type": "int32",
                "presence": "required",
                "role": "identifier",
                "identity": "assigned",
                "description": "Session identity.",
            }
        ],
        "primary_key": ["session_id"],
        "amendment_groups": [["session_id"]],
        "references": [{"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}],
        "rules": [],
    }
    install_registry(
        root,
        {
            "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
            "registry_id": extension_id,
            "registry_version": "0.1.0",
            "logical_standard_version": "escapewheel-logical-v0.1",
            "rule_language": "escapewheel-rule-sql-v0.2",
            "extension_id": extension_id,
            "resources": {
                f"{extension_id}.marks": {
                    "content_class": "extension",
                    "kind": "table",
                    "instances": {"mode": "singleton", "presence": "required"},
                    "requires": [],
                    "lineage": "optional",
                    "table": table,
                }
            },
        },
    )
    (root / "tables" / extension_id).mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table({"session_id": pa.array([1], type=pa.int32())}), root / "tables" / extension_id / "marks.parquet"
    )
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": f"{extension_id}.marks",
            "declaration_id": f"{extension_id}.marks",
            "uri": f"tables/{extension_id}/marks.parquet",
            "digest": owned_digest(root, f"tables/{extension_id}/marks.parquet"),
            "validation_state": "passed",
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_two_bound_extensions_pass_and_activate_their_required_singletons(packet_root):
    """Part 02 §2.5: binding an extension activates its required declarations."""
    root = _required_extension(_required_extension(packet_root, "cue"), "lick")
    report = validate(open_packet(root))
    assert _verdicts(report, "core", "cue", "lick") == ("passed", "passed", "passed", "passed")

    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"] = [r for r in manifest["resources"] if r["resource_id"] != "lick.marks"]
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    missing = [f for f in report.findings if f.check == "packet.resource.required_missing"]
    assert [f.message for f in missing] == ["required singleton lick.marks is absent"]


def _reference(root, **overrides):
    """Append an external array entry to a packet's manifest and return the path."""
    _add_family_declaration(root, "core.test_payloads")
    path = root / "packet.json"
    entry = json.loads(path.read_text())
    resource = {
        "resource_id": "core.probe0",
        "declaration_id": "core.test_payloads",
        "uri": "processing/ecephys/LFP/data",
        "external": True,
        "source": "raw_nwb",
        "validation_state": "not_run",
    }
    resource.update(overrides)
    entry["resources"].append(resource)
    path.write_text(json.dumps(entry))
    return path


def test_a_named_source_no_document_locates_is_reported_not_failed(packet_root):
    """Part 04 §5.5: which mirrors a reader can reach is the reader's situation, not a defect."""
    _reference(packet_root)
    report = validate(open_packet(packet_root))
    assert report.passed
    info = next(f for f in report.findings if f.check == "sources.unresolved")
    assert info.level == "info"
    assert info.rows[0][0] == "raw_nwb"


def test_a_located_source_is_counted_as_located(packet_root):
    """Part 04 §5.5: the packet root's own document is consulted, and says which are reachable."""
    _reference(packet_root)
    (packet_root / "sources.json").write_text(
        json.dumps(
            {
                "sources_standard_version": "escapewheel-sources-v0.1",
                "sources": {"raw_nwb": {"uri": "s3://bucket/session.nwb"}},
            }
        )
    )
    report = validate(open_packet(packet_root))
    assert report.passed
    assert not [f for f in report.findings if f.check == "sources.unresolved"]


def test_a_source_with_an_absolute_uri_is_refused(packet_root):
    """Part 04 §5.5: naming a source and an absolute URI means the source would do nothing."""
    _reference(packet_root, uri="s3://elsewhere/data")
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "sources.absolute_uri" and f.level == "error" for f in report.findings)


def test_a_source_on_a_packet_owned_resource_is_refused(packet_root):
    """Part 04 §5.5: a source locates bytes the packet does not own, which the schema enforces."""
    _reference(packet_root, external=False)
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert {f.check for f in report.findings} == {"packet.manifest.schema"}


def test_declaring_the_resolution_document_as_a_resource_is_refused(packet_root):
    """Part 04 §5.5: inside the manifest, immutability would freeze the file that must stay editable."""
    _add_family_declaration(packet_root, "core.test_docs", content_class="documentation")
    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "core.sources_document",
            "declaration_id": "core.test_docs",
            "uri": "sources.json",
            "digest": UNREAD_DIGEST,
            "validation_state": "passed",
        }
    )
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "sources.declared" and f.level == "error" for f in report.findings)


# -- R137: the reader floor, assessed per resource (Part 05 §5.3) --------------------------------


def _outside(report):
    return [f for f in report.findings if f.check == "physical.outside_reader_floor"]


_BLOSC_ZSTD = {"name": "blosc", "configuration": {"cname": "zstd", "shuffle": "shuffle", "typesize": 2}}
_BYTES = {"name": "bytes", "configuration": {"endian": "little"}}
_CRC = {"name": "crc32c"}


def _shard(codecs, *, index=(_BYTES, _CRC), location="end"):
    configuration = {"chunk_shape": [1, 2, 3], "codecs": codecs, "index_codecs": list(index)}
    if location is not None:
        configuration["index_location"] = location
    return [{"name": "sharding_indexed", "configuration": configuration}]


@pytest.mark.parametrize(
    ("codecs", "inside"),
    [
        ([_BYTES, _BLOSC_ZSTD], True),
        (_shard([_BYTES, _BLOSC_ZSTD]), True),
        (_shard([_BYTES, {"name": "zstd"}], location=None), True),
        (_shard([_BYTES, {"name": "zstd"}], location="start"), False),
        ([*_shard([_BYTES, _BLOSC_ZSTD]), {"name": "zstd"}], False),
        ([_BYTES, {"name": "blosc", "configuration": {"cname": "lz4"}}], False),
        ([{"name": "numcodecs.delta", "configuration": {"dtype": "int16"}}, _BYTES, _BLOSC_ZSTD], False),
    ],
    ids=["blosc_zstd", "sharded", "absent_location", "index_at_start", "codec_after_shard", "lz4", "delta"],
)
def test_a_packet_owned_array_is_compared_with_the_v3_floor(packet_root, codecs, inside):
    """Part 03 §6.4 matched under its rules; outside a reader-only floor is `info`, never a failure."""
    document = _zarr_v3()
    document["codecs"] = codecs
    _add_array(packet_root, declared=[], document=document)
    report = validate(open_packet(packet_root))
    assert report.passed
    findings = _outside(report)
    assert findings == [] if inside else [(f.level, f.registry) for f in findings] == [("info", "core")]
    if not inside:
        assert findings[0].rows == (("codecs", json.dumps(codecs, separators=(",", ":"))),)
        assert "core.waveform_mean: zarr v3" in findings[0].message


def test_an_unrecognized_codec_is_outside_the_floor_and_not_invalid(packet_root):
    """Part 03 §6.4: Zarr v3 admits extension codecs, so an unknown name is valid metadata."""
    document = _zarr_v3(sharded=False)
    document["codecs"] = [_BYTES, {"name": "example.unknown"}]
    _add_array(packet_root, declared=[], document=document)
    report = validate(open_packet(packet_root))
    assert report.passed and report.errors == 0 and report.warnings == 0
    assert [f.level for f in _outside(report)] == ["info"]
    assert _checks(report) == set()


def test_a_packet_owned_table_outside_the_parquet_floor_is_a_warning(packet_root):
    """Part 05 §5.3: the Parquet floor binds the packet's writer too, so exceeding it is `warning`."""
    intervals = pq.read_table(packet_root / "tables" / "core" / "intervals.parquet")
    pq.write_table(intervals, packet_root / "tables" / "core" / "intervals.parquet", compression="zstd", version="1.0")
    report = validate(open_packet(packet_root))
    assert report.passed
    [finding] = _outside(report)
    assert (finding.level, finding.registry) == ("warning", "core")
    assert finding.rows == (("encoding", "PLAIN_DICTIONARY"),)
    assert finding.message.startswith("core.intervals: parquet encoding PLAIN_DICTIONARY")


def test_an_extension_table_outside_the_floor_is_the_extensions_finding(packet_root):
    """Part 05 §9.5: the finding concerns one resource, so the registry declaring it owns it."""
    root = _extension(packet_root)
    path = root / "tables" / "task" / "trials.parquet"
    pq.write_table(pq.read_table(path), path, compression="brotli")
    report = validate(open_packet(root))
    [finding] = _outside(report)
    assert (finding.level, finding.registry, finding.rows) == ("warning", "task", (("compression", "BROTLI"),))
    assert _verdicts(report, "core", "task") == ("passed", "passed", "passed")


def test_a_validator_states_that_it_did_not_assess_page_types(packet_root):
    """Part 03 §5.5: footers are compared, page headers are not, and the report says so."""
    report = validate(open_packet(packet_root))
    [finding] = [f for f in report.findings if f.check == "physical.page_types_unassessed"]
    assert finding.level == "info" and "data-page types were not assessed" in finding.message
    assert _outside(report) == []


def test_a_resolved_external_array_is_assessed_against_its_variant(packet_root):
    """Part 05 §5.3: metadata read in the requested mode is compared, and the resource is not unassessed."""
    report = validate(open_packet(_external(packet_root)), verification=Verification(external=True))
    assert report.passed
    [finding] = _outside(report)
    assert (finding.level, finding.registry) == ("info", "core")
    assert "zarr v2" in finding.message
    assert [row[0] for row in finding.rows] == ["filters", "compressor"]
    assert "external.physical_unassessed" not in {f.check for f in report.findings}

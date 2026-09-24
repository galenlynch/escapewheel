import inspect
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import RegistryUnavailable, open_packet

from escapewheel_validator import validate
from escapewheel_validator.generate import Check, concerns
from escapewheel_validator.generate import _generate as generate

from .conftest import install_registry, read_registry


def _rewrite(root, name, table):
    pq.write_table(table, root / "tables" / "core" / f"{name}.parquet", compression="zstd")


def test_conforming_packet_passes(packet_root):
    report = validate(open_packet(packet_root))
    assert report.passed
    assert report.errors == 0 and report.warnings == 0


def test_duplicate_primary_key(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", pa.concat_tables([trials, trials.slice(0, 1)]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.trials.primary_key_unique" for f in report.findings)


def test_unresolved_foreign_key(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    broken = trials.set_column(0, "session_id", pa.array([999, 999], type=pa.int32()))
    _rewrite(packet_root, "trials", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.trials.session_id_resolves" for f in report.findings)


def test_closed_vocabulary(packet_root):
    units = pq.read_table(packet_root / "tables" / "core" / "units.parquet")
    broken = units.set_column(4, "quality_label", pa.array(["good", "mua"]))
    _rewrite(packet_root, "units", broken)
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "core.units.quality_label.in_vocabulary")
    assert finding.rows == (("good",),)


def test_open_vocabulary_accepts_anything(packet_root):
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    renamed = events.set_column(2, "event_type", pa.array(["whatever", "reward", "lick"]))
    _rewrite(packet_root, "events", renamed)
    assert validate(open_packet(packet_root)).passed


def test_tier_two_rule(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    broken = trials.set_column(3, "stop_tick", pa.array([0, 10000], type=pa.int64()))
    _rewrite(packet_root, "trials", broken)
    report = validate(open_packet(packet_root))
    assert any(f.check == "core.trials.interval_valid" for f in report.findings)


def test_wrong_column_type_is_caught_before_any_query(packet_root):
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    narrowed = trials.set_column(2, "start_tick", trials.column("start_tick").cast(pa.int32()))
    _rewrite(packet_root, "trials", narrowed)
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
    assert any(f.check == "core.events.physical_order" and f.level == "error" for f in report.findings)


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
    assert not any(f.check.startswith("core.trials.") for f in report.findings)


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


def test_generator_emits_nothing_for_an_empty_registry():
    assert generate({"resources": {}}) == []


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


def test_nullable_foreign_keys_are_guarded(packet_root):
    """Without an IS NOT NULL guard, every absent optional key reports as a violation."""
    registry = read_registry(packet_root)
    registry["resources"]["core.trials"]["table"]["columns"].append(
        {"name": "probe_id", "type": "string", "presence": "nullable", "description": "probe"}
    )
    registry["resources"]["core.trials"]["table"]["references"].append(
        {"columns": ["probe_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
    )
    check = next(c for c in generate(registry) if c.id == "core.trials.probe_id_resolves")
    assert "IS NOT NULL" in check.sql


def test_a_declared_metadata_column_no_row_fills_is_reported(packet_root):
    """Part 02 §8.6, at `info`. The column may be absent from the file, so this can never fail."""
    report = validate(open_packet(packet_root))
    assert report.passed
    finding = next(f for f in report.findings if f.check == "core.trials.metadata_unfilled")
    assert finding.level == "info"


def test_a_filled_metadata_column_is_not_reported(packet_root):
    """The other side: one non-null value in the packet is enough, so the report cannot nag."""
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    filled = trials.append_column("metadata", pa.array(['{"a": 1}', None]))
    _rewrite(packet_root, "trials", filled)
    report = validate(open_packet(packet_root))
    assert not [f for f in report.findings if f.check == "core.trials.metadata_unfilled"]


def test_a_by_position_discriminator_gets_no_reverse_check(packet_root):
    """Part 02 §8.3. Part 02 §8.3 excludes the third shape, and `positions_in` is what says it is one."""
    registry = read_registry(packet_root)
    trials = registry["resources"]["core.trials"]["table"]
    trials["columns"].append(
        {
            "name": "axis_of",
            "type": "string",
            "presence": "nullable",
            "role": "discriminator",
            "resolves": "required",
            "positions_in": "axis_column",
            "description": "d",
        }
    )
    trials["columns"].append(
        {"name": "axis_column", "type": "string", "presence": "nullable", "role": "data", "description": "d"}
    )
    ids = {c.id for c in generate(registry, kinds={"core.units": None})}
    assert "core.trials.axis_of.is_a_resource_id" in ids
    assert "core.trials.axis_of.kind_declared" in ids
    assert not [i for i in ids if i.startswith("core.trials.axis_of.") and "is_specialised" in i]


def test_the_position_column_is_checked_against_the_registrys_roles(packet_root):
    """R100 §2.2. A role is invisible to a query and visible to whatever writes one."""
    registry = read_registry(packet_root)
    trials = registry["resources"]["core.trials"]["table"]
    trials["columns"] += [
        {
            "name": "axis_of",
            "type": "string",
            "presence": "nullable",
            "role": "discriminator",
            "resolves": "required",
            "positions_in": "axis_column",
            "description": "d",
        },
        {"name": "axis_column", "type": "string", "presence": "nullable", "role": "data", "description": "d"},
    ]
    registry["resources"]["core.units"]["table"]["columns"].append(
        {"name": "seat_index", "type": "int64", "presence": "nullable", "role": "structural_index", "description": "d"}
    )
    check = next(
        c
        for c in generate(registry, kinds={"core.units": None})
        if c.id == "core.trials.axis_of.position_column_indexes"
    )
    assert "'seat_index'" in check.sql and "core.units" in check.sql


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


def test_external_resources_are_reported_as_unverified(packet_root):
    """A default-mode pass must not imply external claims were checked."""
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
    info = next(f for f in report.findings if f.check == "external.physical_unassessed")
    assert info.level == "info"
    assert info.rows == (("core.probe0",),)


def test_advisory_rules_are_off_by_default(packet_root):
    """An advisory rule does not run unless asked (Part 02 §10.2)."""
    registry = read_registry(packet_root)
    registry["resources"]["core.trials"]["table"]["rules"].append(
        {
            "id": "core.trials.advice",
            "level": "info",
            "advisory": True,
            "message": "advice",
            "sql": "SELECT session_id, trial_id FROM core.trials",
        }
    )
    install_registry(packet_root, registry)
    quiet = validate(open_packet(packet_root))
    assert not any(f.check == "core.trials.advice" for f in quiet.findings)

    loud = validate(open_packet(packet_root), advisory=True)
    assert any(f.check == "core.trials.advice" for f in loud.findings)


def test_advisory_cannot_change_the_verdict(packet_root):
    """`passed` is invariant under the flag, because advisory rules are never errors."""
    registry = read_registry(packet_root)
    registry["resources"]["core.trials"]["table"]["rules"].append(
        {
            "id": "core.trials.advice",
            "level": "info",
            "advisory": True,
            "message": "advice",
            "sql": "SELECT session_id, trial_id FROM core.trials",
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


def test_a_finding_that_projects_a_timestamp_is_reported_without_pytz(monkeypatch):
    """A rule that projects a wall-clock column must report its rows, not an engine error.

    DuckDB's own Python conversion imports `pytz` to render a ``TIMESTAMP WITH TIME ZONE``.
    An empty result converts nothing, so such a rule ran fine until it had something to say
    and then failed -- and whether that happened depended on whether an unrelated package had
    pulled `pytz` in.
    """
    import sys

    import duckdb

    from escapewheel_validator.validator import _offending

    connection = duckdb.connect()
    connection.sql("CREATE TABLE core_clocks (clock_id VARCHAR, tick_zero_utc TIMESTAMP WITH TIME ZONE)")
    connection.sql("INSERT INTO core_clocks VALUES ('harp', '2024-11-27T00:51:12+00:00')")
    query = "SELECT clock_id, tick_zero_utc FROM core_clocks"

    monkeypatch.setitem(sys.modules, "pytz", None)  # makes `import pytz` raise, as an absent one does
    with pytest.raises(duckdb.InvalidInputException):
        connection.sql(query).fetchall()
    assert _offending(connection, query)[0][0] == "harp"
    assert _offending(connection, "SELECT clock_id, tick_zero_utc FROM core_clocks WHERE FALSE") == []


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
        "table": {**registry["resources"]["core.trials"]["table"], "rules": []},
    }
    install_registry(root, registry)
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    entry = {
        "resource_id": "analysis.test_output",
        "declaration_id": "analysis.test_output",
        "uri": "tables/core/trials.parquet",
        "validation_state": "passed",
        "derived_from": ["core.trials"],
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
    """core.trials is sorted by its key, so duplicates are neighbours and no GROUP BY runs."""
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", trials.take([0, 0, 1]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.trials.primary_key_unique" for f in report.findings)


def test_a_duplicate_out_of_order_still_fails(packet_root):
    """Adjacency is unsound on an unordered file, so uniqueness falls back to the aggregate.

    Ordering stays a warning -- a packet in the wrong order still conforms -- so the fallback
    is what keeps the check from passing by omission.
    """
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", trials.take([1, 0, 0]))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "core.trials.primary_key_unique" for f in report.findings)


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


def test_a_rank_the_dimensions_do_not_cover_is_caught(packet_root):
    """Part 03 §6.2: axis_index enumerates every stored axis, so two rows cannot describe rank 3."""
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=2)
    assert "array.rank_disagrees_with_dimensions" in _checks(validate(open_packet(packet_root)))


def test_no_array_dimensions_at_all_is_caught(packet_root):
    _add_array(packet_root, declared=["sharding_indexed", "blosc"], axes=None)
    assert "array.no_array_dimensions_table" in _checks(validate(open_packet(packet_root)))


def test_an_external_array_is_left_to_the_external_mode(packet_root):
    """Level 3, not level 2: reaching it is the reader's situation, not the packet's defect."""
    _add_array(packet_root, declared=["blosc"], external=True)
    assert _checks(validate(open_packet(packet_root))) == set()


# -- verify_order: the same comparison, made on the way in ---------------------------------


def _batch(first_tick, n=5, unit="u1"):
    return pa.record_batch(
        {
            "unit_id": pa.array([unit] * n),
            "t_tick": pa.array(range(first_tick, first_tick + n), type=pa.int64()),
        }
    )


KEYS = ["unit_id", "t_tick"]


def test_ordered_batches_pass_through_unchanged():
    from escapewheel_validator import verify_order

    batches = [_batch(0), _batch(5), _batch(10)]
    assert [b.num_rows for b in verify_order(iter(batches), KEYS)] == [5, 5, 5]


def test_a_descent_inside_a_batch_is_caught():
    from escapewheel_validator import OrderViolation, verify_order

    bad = pa.record_batch({"unit_id": pa.array(["u1"] * 3), "t_tick": pa.array([0, 5, 2], type=pa.int64())})
    with pytest.raises(OrderViolation, match="row 2 sorts before"):
        list(verify_order(iter([bad]), KEYS))


def test_a_descent_on_a_batch_seam_is_caught():
    """The case a per-batch check misses: each batch is ordered, the pair is not."""
    from escapewheel_validator import OrderViolation, verify_order

    with pytest.raises(OrderViolation, match="row 5 sorts before"):
        list(verify_order(iter([_batch(10), _batch(0)]), KEYS))


def test_a_duplicate_on_a_batch_seam_is_caught():
    from escapewheel_validator import OrderViolation, verify_order

    tail = pa.record_batch({"unit_id": pa.array(["u1"]), "t_tick": pa.array([4], type=pa.int64())})
    with pytest.raises(OrderViolation, match="row 5 repeats"):
        list(verify_order(iter([_batch(0), tail]), KEYS, unique=KEYS))


def test_an_empty_batch_does_not_break_the_seam():
    from escapewheel_validator import verify_order

    empty = _batch(0, n=0)
    assert [b.num_rows for b in verify_order(iter([_batch(0), empty, _batch(5)]), KEYS)] == [5, 0, 5]


def test_scanning_nothing_leaves_the_ordering_unchecked(packet_root):
    """What `commit` relies on: a caller that established the order elsewhere skips the read."""
    trials = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", trials.sort_by([("trial_id", "descending")]))
    assert any(f.check == "core.trials.physical_order" for f in validate(open_packet(packet_root)).findings)
    assert not any(
        f.check == "core.trials.physical_order" for f in validate(open_packet(packet_root), scan=set()).findings
    )


def test_a_column_determined_by_the_key_cannot_separate_duplicates():
    """R30 sorts `analysis.spike_events` by two columns that precede its key.

    `clock_id` is the session's reference clock and `time_bucket_tick` is a function of
    `t_tick`, so neither varies between rows sharing a key, and duplicates stay neighbours.
    """
    from escapewheel_validator.generate import adjacency_settles_uniqueness

    # R93 §3.3 took the order out of the registry, so the resource names it: Part 03 §5.4's entry
    # for this one is what puts two non-key columns ahead of the key.
    table = {
        "primary_key": ["session_id", "unit_id", "t_tick"],
        "columns": [
            {"name": "clock_id", "type": "int32", "presence": "required", "determined_by": ["session_id"]},
            {"name": "time_bucket_tick", "type": "int64", "presence": "required", "determined_by": ["t_tick"]},
        ],
    }
    assert adjacency_settles_uniqueness("analysis.spike_events", table)


def test_a_column_determined_by_a_non_key_still_refuses():
    """The dependency must be on the key: anything else can order duplicates apart."""
    from unittest.mock import patch

    from escapewheel_reader.ordering import OVERRIDES

    from escapewheel_validator.generate import adjacency_settles_uniqueness

    table = {
        "primary_key": ["a", "b"],
        "columns": [{"name": "x", "type": "string", "presence": "required", "determined_by": ["c"]}],
    }
    with patch.dict(OVERRIDES, {"x.y": ("a", "x", "b")}):
        assert not adjacency_settles_uniqueness("x.y", table)


def test_an_undeclared_column_ahead_of_the_key_refuses():
    from unittest.mock import patch

    from escapewheel_reader.ordering import OVERRIDES

    from escapewheel_validator.generate import adjacency_settles_uniqueness

    table = {"primary_key": ["a", "b"], "columns": [{"name": "x"}]}
    with patch.dict(OVERRIDES, {"x.y": ("a", "x", "b")}):
        assert not adjacency_settles_uniqueness("x.y", table)


def test_a_dictionary_column_satisfies_a_string_declaration():
    """A dictionary is an encoding, not a type: Parquet stores BYTE_ARRAY/String either way."""
    from escapewheel_validator import Report
    from escapewheel_validator.validator import _check_column

    report = Report()
    column = {"name": "session_id", "type": "string", "presence": "required"}
    schema = pa.schema([pa.field("session_id", pa.dictionary(pa.int32(), pa.string()))])
    _check_column("core.units", column, schema, report)
    assert not report.findings


def test_a_dictionary_over_the_wrong_value_type_is_still_refused():
    """Unwrapping the encoding must not unwrap the check."""
    from escapewheel_validator import Report
    from escapewheel_validator.validator import _check_column

    report = Report()
    column = {"name": "session_id", "type": "string", "presence": "required"}
    schema = pa.schema([pa.field("session_id", pa.dictionary(pa.int32(), pa.int64()))])
    _check_column("core.units", column, schema, report)
    assert [f.check for f in report.findings] == ["schema.column_type"]


# -- Part 03 §9.4: an amendment re-runs only the rules its own resources implicate ---------------


def _check(sql, resource="core.units", dependencies=()):
    return Check(
        f"{resource}.rule",
        "error",
        "message",
        sql,
        resource,
        dependencies=frozenset(dependencies or {resource}),
    )


def test_a_rule_attached_to_a_written_resource_runs():
    assert concerns(_check("SELECT * FROM core_units"), {"core.units"})


def test_a_rule_whose_query_names_a_written_resource_runs():
    """Parsed base relations are authoritative dependencies for Tier 2."""
    sql = "SELECT c.unit_id FROM core_units c LEFT JOIN analysis_spike_events p ON c.unit_id = p.unit_id"
    assert concerns(_check(sql, dependencies={"core.units", "analysis.spike_events"}), {"analysis.spike_events"})


def test_a_rule_reading_only_untouched_resources_may_be_skipped():
    assert not concerns(_check("SELECT * FROM core_units"), {"analysis.spike_events"})


def test_resource_text_in_a_comment_is_not_a_dependency():
    """Part 03 §9.4: comments do not create Tier 2 dependencies."""
    sql = "SELECT * FROM core_units -- nothing to do with analysis_spike_events"
    assert not concerns(_check(sql), {"analysis.spike_events"})


def test_recheck_narrows_the_rules_that_run(packet_root):
    """A packet that passes still passes, over fewer checks."""
    packet = open_packet(packet_root)
    registry = packet.registry
    every = generate(
        registry,
        only={name for name, declaration in registry["resources"].items() if declaration["kind"] == "table"},
    )
    narrowed = [c for c in every if concerns(c, {"core.trials"})]
    assert 0 < len(narrowed) < len(every)
    assert validate(open_packet(packet_root), recheck={"core.trials"}).passed


def test_recheck_still_catches_a_break_in_what_was_written(packet_root):
    """Narrowing must not narrow away the resource the amendment actually wrote."""
    duplicated = pq.read_table(packet_root / "tables" / "core" / "trials.parquet")
    _rewrite(packet_root, "trials", pa.concat_tables([duplicated, duplicated.slice(0, 1)]))
    report = validate(open_packet(packet_root), recheck={"core.trials"})
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
    assert "external.physical_unassessed" in [f.check for f in report.findings if f.level == "info"]


def test_the_requested_mode_resolves_it(packet_root):
    report = validate(open_packet(_external(packet_root)), external=True)
    assert report.passed
    checks = {f.check for f in report.findings}
    assert "external.verified" in checks
    assert "external.physical_unassessed" not in checks, "the two modes must not both speak"


def test_size_bytes_counts_the_whole_prefix_including_its_metadata(packet_root):
    """A dense array asset is a prefix of many objects, so its size is a list, not a stat.
    Excluding the metadata document would make the writer and the validator disagree."""
    assert validate(open_packet(_external(packet_root)), external=True).passed


def test_a_size_that_disagrees_is_an_error_only_in_that_mode(packet_root):
    root = _external(packet_root, size_bytes=999)
    assert validate(open_packet(root)).passed
    report = validate(open_packet(root), external=True)
    assert not report.passed
    assert "external.size_bytes" in {f.check for f in report.findings}


def test_an_unreachable_resource_is_a_warning_not_an_error(packet_root):
    """Reachability is a property of the reader's situation, not of the packet."""
    root = _external(packet_root, uri="file:///nowhere/at/all.zarr")
    report = validate(open_packet(root), external=True)
    assert report.passed
    assert "external.unreachable" in {f.check for f in report.findings}


def test_a_requested_digest_with_nothing_recorded_says_so(packet_root):
    """Part 04 §5.2: a packet need not record a sha256, and every packet built so far records none.
    Asking for checksums and finding nothing to compare must not report a clean verification."""
    report = validate(open_packet(_external(packet_root)), external=True, checksums=True)
    assert report.passed, "a claim the packet never made is not a failure"
    assert "external.no_checksum" in {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert "sha256" not in verified.message, "it compared none, so it must not claim any"


def test_a_recorded_digest_is_compared(packet_root):
    from escapewheel_validator.stores import digest

    root = _external(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r.get("external"))
    entry["sha256"] = digest(entry["uri"])
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root), external=True, checksums=True)
    assert report.passed
    assert "external.no_checksum" not in {f.check for f in report.findings}
    assert "1 sha256" in next(f for f in report.findings if f.check == "external.verified").message


def test_a_digest_that_disagrees_is_an_error(packet_root):
    root = _external(packet_root, sha256="0" * 64)
    assert validate(open_packet(root), external=True).passed, "not read without checksums"
    report = validate(open_packet(root), external=True, checksums=True)
    assert not report.passed
    assert "external.sha256" in {f.check for f in report.findings}


def test_the_summary_names_what_it_compared(packet_root):
    """ "Resolved and checked" said nothing about which claims were actually tested."""
    report = validate(open_packet(_external(packet_root)), external=True)
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
    report = validate(open_packet(_with_members(_external(packet_root))), external=True)
    assert report.passed
    assert "1 members" in next(f for f in report.findings if f.check == "external.verified").message


def test_a_member_the_store_does_not_hold_is_an_error(packet_root):
    def add(entry):
        entry["members"].append({"key": "9.9", "size_bytes": 1})
        entry["size_bytes"] += 1  # so the entry stays self-consistent and only the store disagrees

    root = _with_members(_external(packet_root), mutate=add)
    report = validate(open_packet(root), external=True)
    assert not report.passed
    assert "external.members" in {f.check for f in report.findings}


def test_a_member_size_that_disagrees_is_caught_where_the_total_would_not(packet_root):
    """Two members changing in opposite directions leave `size_bytes` correct. Part 04 §5.4."""

    def swap(entry):
        entry["members"][0]["size_bytes"] += 10
        entry["members"][1]["size_bytes"] -= 10

    root = _with_members(_external(packet_root), mutate=swap)
    report = validate(open_packet(root), external=True)
    assert not report.passed, "the total still agrees, so only a per-member check sees this"
    assert "external.members" in {f.check for f in report.findings}


def test_store_digests_report_what_they_could_not_check(packet_root):
    """A local filesystem offers no content hash, so every member is skipped, not passed."""
    report = validate(open_packet(_with_members(_external(packet_root))), external=True, store_digests=True)
    assert report.passed
    assert "external.no_store_digest" in {f.check for f in report.findings}
    assert "store_digest" not in next(f for f in report.findings if f.check == "external.verified").message


def test_a_store_digest_that_changed_in_place_is_an_error(packet_root, monkeypatch):
    """Neither the size nor a recorded sha256 need change for this to fire."""
    from escapewheel_validator import validator as module
    from escapewheel_validator.stores import Listing, Member, StoreDigest, listing

    def stamped(uri, **kwargs):
        found = listing(uri, **kwargs)
        return Listing(
            tuple(
                Member(m.key, m.size_bytes, StoreDigest("md5", f"{index:032x}"))
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
                    m.update(store_digest={"algorithm": "md5", "value": f"{i:032x}"})
                    for i, m in enumerate(e["members"])
                ],
            )
        ),
        external=True,
        store_digests=True,
    )
    assert passing.passed
    assert "1 store_digest" in next(f for f in passing.findings if f.check == "external.verified").message

    changed = validate(
        open_packet(
            _with_members(
                root,
                mutate=lambda e: [m.update(store_digest={"algorithm": "md5", "value": "f" * 32}) for m in e["members"]],
            )
        ),
        external=True,
        store_digests=True,
    )
    assert not changed.passed
    assert "external.store_digest" in {f.check for f in changed.findings}


# -- Part 02 §6: an external array's shape against what the packet's tables assert ------------


def test_an_external_arrays_rank_is_checked_against_the_dimensions(packet_root):
    """The check `_check_one_array` does for a packet-owned array, for an external one."""
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=2)
    report = validate(open_packet(root), external=True)
    assert not report.passed
    assert "external.array_rank" in {f.check for f in report.findings}


def test_a_matching_rank_passes_and_is_counted(packet_root):
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=3)
    report = validate(open_packet(root), external=True)
    assert "external.array_rank" not in {f.check for f in report.findings}
    assert "1 rank" in next(f for f in report.findings if f.check == "external.verified").message


def test_an_axis_length_is_taken_from_its_coordinate_table(packet_root):
    """An axis whose coordinates are a table has one row per position, so the row count is the
    length. This is what catches a re-generated array with a different channel count."""
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=3)
    _coordinate_table(root, rows=2)  # axis 1 is 2 long in _zarr_v3's [4, 2, 3]
    assert validate(open_packet(root), external=True).passed

    _coordinate_table(root, rows=5)
    report = validate(open_packet(root), external=True)
    assert not report.passed
    assert "external.array_shape" in {f.check for f in report.findings}


def test_a_coordinate_table_not_keyed_by_axis_says_nothing_about_length(packet_root):
    """`core.unit_electrodes` is a coordinate resource whose rows are a subset of an axis, not
    an enumeration of it, so counting them would invent a disagreement."""
    root = _add_array(packet_root, declared=["blosc"], external=True, axes=3)
    _coordinate_table(root, rows=5, keyed=False)
    assert validate(open_packet(root), external=True).passed


def _coordinate_table(root, *, rows, keyed=True):
    """Point axis 1 at a coordinate table and give that table `rows` positions."""
    manifest = json.loads((root / "packet.json").read_text())
    dimensions = pq.read_table(root / "tables" / "core" / "array_dimensions.parquet").to_pydict()
    dimensions["coordinate_resource"] = [None, "core.array_channels", None]
    pq.write_table(
        pa.table(
            {
                "array_asset_id": pa.array(dimensions["array_asset_id"], type=pa.int32()),
                "axis_index": pa.array(dimensions["axis_index"], type=pa.int64()),
                "dimension_name": pa.array(dimensions["dimension_name"]),
                "coordinate_resource": pa.array(dimensions["coordinate_resource"]),
            }
        ),
        root / "tables" / "core" / "array_dimensions.parquet",
    )
    columns = {"channel_label": pa.array([f"c{i}" for i in range(rows)])}
    if keyed:
        columns = {
            "array_asset_id": pa.array([1] * rows, type=pa.int32()),
            "axis_index": pa.array([1] * rows, type=pa.int64()),
            "channel_index": pa.array(list(range(rows)), type=pa.int64()),
            **columns,
        }
    pq.write_table(pa.table(columns), root / "tables" / "core" / "array_channels.parquet")
    if not any(r["resource_id"] == "core.array_channels" for r in manifest["resources"]):
        manifest["resources"].append(
            {
                "resource_id": "core.array_channels",
                "declaration_id": "core.array_channels",
                "uri": "tables/core/array_channels.parquet",
                "validation_state": "passed",
            }
        )
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
                        "description": "Array row identity.",
                    },
                    {
                        "name": "axis_index",
                        "type": "int64",
                        "presence": "required",
                        "role": "structural_index",
                        "description": "Axis index.",
                    },
                    {
                        "name": "channel_label",
                        "type": "string",
                        "presence": "required",
                        "role": "data",
                        "vocabulary": "free",
                        "description": "Channel label.",
                    },
                    {
                        "name": "channel_index",
                        "type": "int64",
                        "presence": "required",
                        "role": "structural_index",
                        "description": "Channel index.",
                    },
                ]
                if keyed
                else [
                    {
                        "name": "channel_label",
                        "type": "string",
                        "presence": "required",
                        "role": "data",
                        "vocabulary": "free",
                        "description": "Channel label.",
                    }
                ],
                "primary_key": ["array_asset_id", "axis_index", "channel_index"] if keyed else None,
                "references": (
                    [
                        {
                            "columns": ["array_asset_id"],
                            "resource": "core.array_assets",
                            "resource_columns": ["array_asset_id"],
                        }
                    ]
                    if keyed
                    else []
                ),
                "rules": [],
            },
        }
        (root / "packet.json").write_text(json.dumps(manifest))
        install_registry(root, registry)


def test_a_packet_owned_arrays_axis_length_is_checked_too(packet_root):
    """The external path checked axis lengths and the packet-owned one only checked rank, though
    the owned array's shape is already in hand. The two now derive extent the same way."""
    root = _add_array(packet_root, declared=["blosc", "sharding_indexed"], external=False, axes=3)
    _coordinate_table(root, rows=2)  # _zarr_v3 is [4, 2, 3], so axis 1 is 2
    assert validate(open_packet(root)).passed

    _coordinate_table(root, rows=5)
    report = validate(open_packet(root))
    assert not report.passed, "an owned array is checked without asking, unlike an external one"
    assert "array.shape_disagrees_with_coordinates" in {f.check for f in report.findings}


# -- R52: a packet-owned resource's digest -------------------------------------------------


def _record_owned_digests(root, *, corrupt=None):
    """Record a sha256 per packet-owned resource, as a writer does since R52."""
    from escapewheel_validator.stores import digest

    manifest = json.loads((root / "packet.json").read_text())
    for entry in manifest["resources"]:
        if not entry.get("external"):
            entry["sha256"] = digest(str(root / entry["uri"]))
    if corrupt is not None:
        next(e for e in manifest["resources"] if e["resource_id"] == corrupt)["sha256"] = "0" * 64
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_packet_owned_digests_are_checked(packet_root):
    report = validate(open_packet(_record_owned_digests(packet_root)), checksums=True)
    assert report.passed
    assert "owned.verified" in {f.check for f in report.findings}
    assert "owned.no_checksum" not in {f.check for f in report.findings}


def test_a_packet_owned_file_that_changed_is_an_error(packet_root):
    """Part 03 §9.4 bounds revalidation on immutability. This is what checks the premise."""
    root = _record_owned_digests(packet_root, corrupt="core.trials")
    assert validate(open_packet(root)).passed, "not read without checksums"
    report = validate(open_packet(root), checksums=True)
    assert not report.passed
    assert "owned.sha256" in {f.check for f in report.findings}


def test_a_packet_recording_no_owned_digest_says_so(packet_root):
    """Every packet built before R52 records none; that is a warning, not a silent pass."""
    report = validate(open_packet(packet_root), checksums=True)
    assert report.passed
    assert "owned.no_checksum" in {f.check for f in report.findings}


# -- R17: an extension is a registry, validated by the same machinery ----------------------


def _extension(root, *, tables=None, mutate=None):
    """Give the packet an extension registry and a table conforming to it."""
    document = {
        "$schema": "https://escapewheel.org/schemas/registry/0.6.0",
        "registry_id": "task",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.1",
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
                            "name": "trial_id",
                            "type": "int32",
                            "presence": "required",
                            "role": "identifier",
                            "identity": "assigned",
                            "description": "Trial identity.",
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
                    "primary_key": ["session_id", "trial_id"],
                    "references": [
                        {
                            "columns": ["session_id", "trial_id"],
                            "resource": "core.trials",
                            "resource_columns": ["session_id", "trial_id"],
                        }
                    ],
                    "rules": [],
                },
            }
        },
    }
    trials = pq.read_table(root / "tables" / "core" / "trials.parquet")
    rows = {
        "session_id": trials["session_id"].to_pylist(),
        "trial_id": trials["trial_id"].to_pylist(),
        "choice": ["left"] * trials.num_rows,
    }
    if mutate is not None:
        mutate(rows)
    (root / "tables" / "task").mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(rows), root / "tables" / "task" / "trials.parquet")
    install_registry(root, document)

    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "task.trials",
            "declaration_id": "task.trials",
            "uri": "tables/task/trials.parquet",
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
    """Part 09 §2 lets an extension reference core. Without the cross-registry link the anti-join is
    never generated and an orphan validates clean -- the gap R46 closed for core."""
    root = _extension(packet_root, mutate=lambda r: r["trial_id"].__setitem__(0, 999))
    report = validate(open_packet(root))
    assert any(f.check.endswith("_resolves") and f.extension == "task" for f in report.findings)


def test_an_extension_finding_does_not_fail_core(packet_root):
    """Part 05 §5.4. A core validator need not hold the schema at all, so holding it must not be able
    to fail a packet that passes without it."""
    root = _extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "sideways"))
    report = validate(open_packet(root))
    assert report.passed, "core conformance is unchanged"
    assert not report.extension_passed("task")
    assert report.extensions == ("task",)


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
    assert packet.table("core.trials").num_rows == 2
    with pytest.raises(RegistryUnavailable, match="'task'"):
        packet.extensions()


def test_validator_preserves_an_available_unparseable_extension_result(packet_root):
    root = _unparseable_extension(_extension(packet_root))
    report = validate(open_packet(root))
    task = next(item for item in report.registries if item.subject == "task")
    assert task.result.state == "invalid"
    assert report.passed
    assert not report.extension_passed("task")
    assert "task" in report.extensions
    assert not any(f.check == "extension.validated" for f in report.findings)


def test_an_extension_that_fails_binding_withholds_only_its_entries(packet_root):
    """Part 04 §10: core's declaration phase still runs, and the extension's entries are not judged."""
    root = _extension(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    manifest["registries"]["task"]["version"] = "0.9.0"
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    binding = next(f for f in report.findings if f.check == "packet.registry.version")
    assert binding.extension == "task"
    assert report.passed
    assert not report.extension_passed("task")
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
        "references": [{"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}],
        "rules": [],
    }
    install_registry(
        root,
        {
            "$schema": "https://escapewheel.org/schemas/registry/0.6.0",
            "registry_id": extension_id,
            "registry_version": "0.1.0",
            "logical_standard_version": "escapewheel-logical-v0.1",
            "rule_language": "escapewheel-rule-sql-v0.1",
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
            "validation_state": "passed",
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_two_bound_extensions_pass_and_activate_their_required_singletons(packet_root):
    """Part 02 §2.5: binding an extension activates its required declarations."""
    root = _required_extension(_required_extension(packet_root, "cue"), "lick")
    report = validate(open_packet(root))
    assert report.passed and report.extension_passed("cue") and report.extension_passed("lick")

    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"] = [r for r in manifest["resources"] if r["resource_id"] != "lick.marks"]
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    missing = [f for f in report.findings if f.check == "packet.resource.required_missing"]
    assert [f.message for f in missing] == ["required singleton lick.marks is absent"]


def _discriminated(role="discriminator", **extra):
    """A one-table registry whose `k_kind` discriminates `k` (Part 02 §8.3)."""
    column = {"name": "k_kind", "type": "string", "presence": "nullable", "role": role, **extra}
    return {
        "resources": {
            "core.runs": {
                "kind": "table",
                "table": {
                    "columns": [
                        {"name": "run_id", "type": "int32", "presence": "required", "role": "identifier"},
                        column,
                        {"name": "k", "type": "string", "presence": "nullable", "role": "data"},
                    ],
                    "primary_key": ["run_id"],
                    "references": [],
                    "rules": [],
                },
            }
        }
    }


def test_a_discriminator_is_checked_for_being_a_resource_id():
    """Part 02 §8.3. Nothing checked this: `scope_kind` could hold an empty string and no rule saw it."""
    checks = generate(_discriminated(resolves="optional", discriminates="k"))
    ids = {c.id for c in checks}
    assert "core.runs.k_kind.is_a_resource_id" in ids


def test_a_data_column_generates_no_discriminator_checks():
    """The role is what turns it on, which is R55 §1.1's point: `data` said only 'may be read'."""
    checks = generate(_discriminated(role="data"))
    assert not [c for c in checks if "k_kind" in c.id]


def test_resolves_decides_the_level_not_whether_the_check_exists():
    """Part 02 §8.3. An optional kind naming nothing is a fact, and reported; R49 §2.5 passed it in silence."""
    kinds = {"core.sessions": "session_id"}
    optional = generate(_discriminated(resolves="optional", discriminates="k"), kinds=kinds)
    required = generate(_discriminated(resolves="required", discriminates="k"), kinds=kinds)
    levels = {c.id: c.level for c in optional + required}
    assert levels["core.runs.k_kind.kind_declared"] in ("info", "error")
    assert {c.level for c in optional if c.id.endswith("kind_declared")} == {"info"}
    assert {c.level for c in required if c.id.endswith("kind_declared")} == {"error"}


def test_a_shared_key_discriminator_generates_no_value_resolution():
    """Part 02 §8.3: the named table's own reference carries that integrity, pointing the other way."""
    checks = generate(_discriminated(resolves="required"), kinds={"core.sessions": "session_id"})
    assert not [c for c in checks if c.id.endswith("k_kind.resolves")]


def test_the_paired_value_comparison_is_cast_on_both_sides():
    """R53 §2.1 made keys int32 while the paired value stayed a string (R55 §4).

    Without the cast DuckDB coerces the string to an integer and *raises* on one that is not a
    number, which turns a finding into a check that could not run.
    """
    checks = generate(
        _discriminated(resolves="optional", discriminates="k"),
        only={"core.runs"},
        kinds={"core.runs": "run_id"},
    )
    sql = next(c.sql for c in checks if c.id == "core.runs.k_kind.resolves")
    assert sql.count("CAST") == 2


def test_a_kind_the_packet_does_not_declare_is_not_joined():
    """Only a resource the packet carries can appear in the union; the rest are the declared-kind check."""
    checks = generate(
        _discriminated(resolves="optional", discriminates="k"),
        only={"core.runs"},
        kinds={"core.runs": "run_id", "ext.absent": "absent_id"},
    )
    sql = next(c.sql for c in checks if c.id == "core.runs.k_kind.resolves")
    assert "ext_absent" not in sql
    declared = next(c.sql for c in checks if c.id == "core.runs.k_kind.kind_declared")
    assert "'ext.absent'" in declared


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
    assert any(f.check == "source.absolute_uri" and f.level == "error" for f in report.findings)


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
            "validation_state": "passed",
        }
    )
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert any(f.check == "sources.declared" and f.level == "error" for f in report.findings)

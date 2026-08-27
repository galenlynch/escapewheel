import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from nwb_lake_reader import PacketError, open_packet
from nwb_lake_reader.validation import generate, validate


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
    broken = trials.set_column(0, "session_id", pa.array(["s999", "s999"]))
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


def test_physical_order_is_a_warning_not_an_error(packet_root):
    """Ordering is a performance property; a packet in the wrong order still conforms."""
    events = pq.read_table(packet_root / "tables" / "core" / "events.parquet")
    _rewrite(packet_root, "events", events.take([2, 0, 1]))
    report = validate(open_packet(packet_root))
    assert report.passed
    assert any(f.check == "core.events.physical_order" and f.level == "warning" for f in report.findings)


def test_registry_version_must_match_the_manifest(packet_root):
    path = packet_root / "schemas" / "logical_schemas.json"
    registry = json.loads(path.read_text())
    registry["registry_version"] = "0.2.0"
    path.write_text(json.dumps(registry))
    report = validate(open_packet(packet_root))
    assert any(f.check == "registry.version_mismatch" for f in report.findings)


def test_no_registry_anywhere_is_an_error(packet_root):
    (packet_root / "schemas" / "logical_schemas.json").unlink()
    with pytest.raises(PacketError, match="embeds no registry"):
        validate(open_packet(packet_root))


def test_supplied_registry_overrides_the_absent_one(packet_root):
    path = packet_root / "schemas" / "logical_schemas.json"
    registry = json.loads(path.read_text())
    path.unlink()
    assert validate(open_packet(packet_root), registry=registry).passed


def test_absent_tables_are_not_required(packet_root):
    """A packet need not carry every table the registry defines."""
    import json as _json

    path = packet_root / "nwb.packet.json"
    entry = _json.loads(path.read_text())
    entry["resources"] = [r for r in entry["resources"] if r["resource_id"] != "core.spike_events"]
    path.write_text(_json.dumps(entry))
    assert validate(open_packet(packet_root)).passed


def test_report_renders_as_json(packet_root):
    report = validate(open_packet(packet_root))
    rendered = report.to_dict("session_001")
    assert rendered["status"] == "passed"
    assert rendered["summary"] == {"errors": 0, "warnings": 0}


def test_generator_emits_nothing_for_an_empty_registry():
    assert generate({"tables": {}}) == []


def test_nullable_foreign_keys_are_guarded(packet_root):
    """Without an IS NOT NULL guard, every absent optional key reports as a violation."""
    registry = json.loads((packet_root / "schemas" / "logical_schemas.json").read_text())
    registry["tables"]["core.trials"]["columns"].append(
        {"name": "probe_id", "type": "string", "presence": "nullable", "description": "probe"}
    )
    registry["tables"]["core.trials"]["references"].append(
        {"columns": ["probe_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
    )
    check = next(c for c in generate(registry) if c.id == "core.trials.probe_id_resolves")
    assert "IS NOT NULL" in check.sql


def test_required_codecs_must_equal_the_union(packet_root):
    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "array.probe0",
            "layer": "core",
            "kind": "dense_array_asset",
            "uri": "s3://example/p.zarr",
            "external": True,
            "codecs": ["wavpack"],
        }
    )
    entry["required_codecs"] = []  # the union says wavpack
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "manifest.required_codecs_is_the_union")
    assert "wavpack" in finding.message


def test_external_resources_are_reported_as_unverified(packet_root):
    """A default-mode pass must not imply external claims were checked."""
    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "array.probe0",
            "layer": "core",
            "kind": "dense_array_asset",
            "uri": "s3://example/p.zarr",
            "external": True,
            "codecs": ["wavpack"],
        }
    )
    entry["required_codecs"] = ["wavpack"]
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    assert report.passed  # unreachable externals do not invalidate
    info = next(f for f in report.findings if f.check == "external.unverified")
    assert info.level == "info"
    assert info.rows == (("array.probe0",),)

"""An amended packet compared with the version it supersedes (Part 05 §15.6)."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader import open_packet
from packet_fixture import CLOCK_BEHAVIOUR, SESSION, STREAMS, UNITS, install_registry, read_registry

from escapewheel_validator import validate

from .builders import with_column
from .conftest import owned_digest

TABLES = "tables/core"


def _retain(root):
    """Keep the current manifest as a superseded version and return the one that amends it."""
    manifest = json.loads((root / "packet.json").read_text())
    (root / "manifests").mkdir(exist_ok=True)
    (root / "manifests" / f"{manifest['packet_version']}.json").write_text(json.dumps(manifest, indent=2))
    return {**manifest, "packet_version": "0.1.1"}


def _write_version(root, manifest, name, table):
    """Write a table at a new uri, as an amendment writes one, and point the manifest at it."""
    uri = f"{TABLES}/{name}.0.1.1.parquet"
    pq.write_table(table, root / uri, compression="zstd")
    for entry in manifest["resources"]:
        if entry["resource_id"] == f"core.{name}":
            entry.update(uri=uri, digest=owned_digest(root, uri))
    return manifest


def _amended(root, name, extend):
    """Amend `core.<name>` with the rows `extend` returns for the held table."""
    held = pq.read_table(root / TABLES / f"{name}.parquet")
    manifest = _write_version(root, _retain(root), name, extend(held))
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return validate(open_packet(root))


def _checks(report):
    return {f.check for f in report.findings if f.check.startswith("amendment.")}


def _rows(held, **columns):
    return pa.concat_tables([held, pa.table(columns, schema=held.schema)])


def _new_stream(held):
    """A stream is its own amendment group, so a new one joins none that is held."""
    return _rows(
        held,
        event_stream_id=pa.array([len(STREAMS)], type=pa.int32()),
        session_id=pa.array([SESSION], type=pa.int32()),
        event_stream_name=pa.array(["lick"]),
        event_type=pa.array(["lick"]),
        clock_id=pa.array([CLOCK_BEHAVIOUR], type=pa.int32()),
    )


def test_an_amendment_adding_a_new_group_passes(packet_root):
    report = _amended(packet_root, "event_streams", _new_stream)
    assert report.passed, [f"{f.check}: {f.message}" for f in report.findings if f.level == "error"]
    assert not [e for e in report.evaluations if e.rule == "amendment"]


def test_changing_a_held_row_is_row_changed(packet_root):
    def shifted(held):
        return with_column(held, "start_tick", pa.array([1001, 6000], type=pa.int64()))

    report = _amended(packet_root, "intervals", shifted)
    assert _checks(report) == {"amendment.row_changed", "amendment.group_grown"}


def test_removing_a_held_row_is_row_changed(packet_root):
    assert _checks(_amended(packet_root, "intervals", lambda held: held.slice(0, 1))) == {"amendment.row_changed"}


def test_a_row_joining_a_held_group_is_group_grown(packet_root):
    """Part 02 §2.8: a unit's spikes are one group, so an amendment adds a unit's spikes or none of them."""

    def one_more_spike(held):
        return _rows(
            held,
            session_id=pa.array([SESSION], type=pa.int32()),
            unit_id=pa.array([UNITS[0]], type=pa.int32()),
            t_tick=pa.array([90000], type=pa.int64()),
        )

    report = _amended(packet_root, "spike_events", one_more_spike)
    assert _checks(report) == {"amendment.group_grown"}
    (finding,) = [f for f in report.findings if f.check == "amendment.group_grown"]
    assert finding.rows == ((str(SESSION), str(UNITS[0]), "1"),)  # session_id, unit_id, rows added to the group


def test_a_table_declaring_no_group_list_takes_no_added_row(packet_root):
    registry = read_registry(packet_root)
    registry["resources"]["core.events"]["table"]["amendment_groups"] = []
    install_registry(packet_root, registry)
    report = _amended(
        packet_root,
        "events",
        lambda held: _rows(
            held,
            session_id=pa.array([SESSION], type=pa.int32()),
            stream_id=pa.array([STREAMS[1]], type=pa.int32()),
            t_tick=pa.array([7000], type=pa.int64()),
        ),
    )
    assert _checks(report) == {"amendment.group_grown"}


def test_changing_the_packet_id_is_identity_changed(packet_root):
    manifest = _retain(packet_root)
    manifest["packet_id"] = "session_002"
    (packet_root / "packet.json").write_text(json.dumps(manifest, indent=2))
    assert _checks(validate(open_packet(packet_root))) == {"amendment.identity_changed"}


def test_removing_a_canonical_resource_is_resource_changed(packet_root):
    manifest = _retain(packet_root)
    manifest["resources"] = [e for e in manifest["resources"] if e["resource_id"] != "core.events"]
    (packet_root / "packet.json").write_text(json.dumps(manifest, indent=2))
    report = validate(open_packet(packet_root))
    assert "amendment.resource_changed" in _checks(report)


def _analysis(root):
    """Declare a derived table over `core.event_streams`, stored apart from it."""
    registry = read_registry(root)
    registry["resources"]["analysis.stream_summary"] = {
        "content_class": "analysis",
        "kind": "table",
        "instances": {"mode": "singleton", "presence": "optional"},
        "requires": [],
        "lineage": "required",
        "table": {**registry["resources"]["core.event_streams"]["table"], "rules": [], "amendment_groups": []},
    }
    install_registry(root, registry)
    uri = f"{TABLES}/stream_summary.parquet"
    pq.write_table(pq.read_table(root / TABLES / "event_streams.parquet"), root / uri)
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "analysis.stream_summary",
            "declaration_id": "analysis.stream_summary",
            "uri": uri,
            "digest": owned_digest(root, uri),
            "validation_state": "passed",
            "derived_from": ["core.event_streams"],
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))


def test_a_derived_resource_kept_over_a_written_source_is_stale(packet_root):
    _analysis(packet_root)
    report = _amended(packet_root, "event_streams", _new_stream)
    assert _checks(report) == {"amendment.derived_resource_stale"}


def test_removing_the_stale_derived_resource_passes(packet_root):
    """Part 05 §15.2: an amendment may remove an analysis resource it does not derive again."""
    _analysis(packet_root)
    held = pq.read_table(packet_root / TABLES / "event_streams.parquet")
    manifest = _write_version(packet_root, _retain(packet_root), "event_streams", _new_stream(held))
    manifest["resources"] = [e for e in manifest["resources"] if e["resource_id"] != "analysis.stream_summary"]
    (packet_root / "packet.json").write_text(json.dumps(manifest, indent=2))
    report = validate(open_packet(packet_root))
    assert report.passed, [f"{f.check}: {f.message}" for f in report.findings if f.level == "error"]


def test_an_unreadable_retained_manifest_leaves_the_comparison_incomplete(packet_root):
    """Part 05 §9.4: the validator could not compare, which is not a finding about the packet."""
    manifest = _retain(packet_root)
    (packet_root / "manifests" / "0.0.9.json").write_text("{")
    (packet_root / "packet.json").write_text(json.dumps(manifest, indent=2))
    report = validate(open_packet(packet_root))
    assert not _checks(report)
    assert [(e.registry, e.status) for e in report.evaluations if e.rule == "amendment"] == [("core", "incomplete")]


def test_a_superseded_version_whose_files_were_removed_leaves_the_comparison_incomplete(packet_root):
    held = pq.read_table(packet_root / TABLES / "event_streams.parquet")
    manifest = _write_version(packet_root, _retain(packet_root), "event_streams", _new_stream(held))
    (packet_root / "packet.json").write_text(json.dumps(manifest, indent=2))
    (packet_root / TABLES / "event_streams.parquet").unlink()
    report = validate(open_packet(packet_root))
    assert not _checks(report)
    assert [(e.registry, e.status) for e in report.evaluations if e.rule == "amendment"] == [("core", "incomplete")]

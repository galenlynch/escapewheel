"""The reader floor: what a validation finds outside it, and what it reports it did not assess."""

import json
from types import SimpleNamespace

import pyarrow.parquet as pq
import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import Report, Verification, validate
from escapewheel_validator.shim.floors import report_unassessed

from .builders import (
    add_array,
    add_extension,
    add_family_declaration,
    checks_under,
    external_array,
    verdicts_of,
    zarr_v3_metadata,
)


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


def test_an_external_resource_with_no_floor_is_not_reported_unassessed(packet_root):
    """Part 05 §5.3: an opaque resource has no reader floor, so there is nothing left unassessed."""
    add_family_declaration(packet_root, "core.test_payloads")
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
    document = zarr_v3_metadata()
    document["codecs"] = codecs
    add_array(packet_root, declared=[], document=document)
    report = validate(open_packet(packet_root))
    assert report.passed
    findings = _outside(report)
    assert findings == [] if inside else [(f.level, f.registry) for f in findings] == [("info", "core")]
    if not inside:
        assert findings[0].rows == (("codecs", json.dumps(codecs, separators=(",", ":"))),)
        assert "core.waveform_mean: zarr v3" in findings[0].message


def test_an_unrecognized_codec_is_outside_the_floor_and_not_invalid(packet_root):
    """Part 03 §6.4: Zarr v3 admits extension codecs, so an unknown name is valid metadata."""
    document = zarr_v3_metadata(sharded=False)
    document["codecs"] = [_BYTES, {"name": "example.unknown"}]
    add_array(packet_root, declared=[], document=document)
    report = validate(open_packet(packet_root))
    assert report.passed and report.errors == 0 and report.warnings == 0
    assert [f.level for f in _outside(report)] == ["info"]
    assert checks_under(report) == set()


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
    root = add_extension(packet_root)
    path = root / "tables" / "task" / "trials.parquet"
    pq.write_table(pq.read_table(path), path, compression="brotli")
    report = validate(open_packet(root))
    [finding] = _outside(report)
    assert (finding.level, finding.registry, finding.rows) == ("warning", "task", (("compression", "BROTLI"),))
    assert verdicts_of(report, "core", "task") == ("passed", "passed", "passed")


def test_a_validator_states_that_it_did_not_assess_page_types(packet_root):
    """Part 03 §5.5: footers are compared, page headers are not, and the report says so."""
    report = validate(open_packet(packet_root))
    [finding] = [f for f in report.findings if f.check == "physical.page_types_unassessed"]
    assert finding.level == "info" and "data-page types were not assessed" in finding.message
    assert _outside(report) == []


def test_a_resolved_external_array_is_assessed_against_its_variant(packet_root):
    """Part 05 §5.3: metadata read in the requested mode is compared, and the resource is not unassessed."""
    report = validate(open_packet(external_array(packet_root)), verification=Verification(external=True))
    assert report.passed
    [finding] = _outside(report)
    assert (finding.level, finding.registry) == ("info", "core")
    assert "zarr v2" in finding.message
    assert [row[0] for row in finding.rows] == ["filters", "compressor"]
    assert "external.physical_unassessed" not in {f.check for f in report.findings}

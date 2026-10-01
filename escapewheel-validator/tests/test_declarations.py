"""The manifest's entries against the declarations, lineage and sources they name."""

import json

from escapewheel_reader import open_packet

from escapewheel_validator import validate

from .builders import add_array, add_family_declaration, declare_analysis
from .conftest import UNREAD_DIGEST


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


def test_an_analysis_resource_names_its_lineage_and_no_run(packet_root):
    """Part 06 §5: a materialization's run is optional provenance the manifest does not carry."""
    declare_analysis(packet_root)
    report = validate(open_packet(packet_root))
    assert report.passed, [f for f in report.findings if f.level == "error"]


def test_an_analysis_resource_without_lineage_is_an_error(packet_root):
    declare_analysis(packet_root, derived_from=None)
    report = validate(open_packet(packet_root))
    assert "packet.resource.derived_from_required" in {f.check for f in report.findings}


def test_a_catalog_row_requires_its_declared_resource(packet_root):
    add_array(packet_root, declared=["sharding_indexed", "blosc"])
    path = packet_root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"] = [
        resource for resource in manifest["resources"] if resource["resource_id"] != "core.waveform_mean"
    ]
    path.write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert "packet.resource.catalog_row_binding" in {finding.check for finding in report.findings}


def _reference(root, **overrides):
    """Append an external array entry to a packet's manifest and return the path."""
    add_family_declaration(root, "core.test_payloads")
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
    add_family_declaration(packet_root, "core.test_docs", content_class="documentation")
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

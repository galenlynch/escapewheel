"""`validate` over a packet: the registries that direct it, its verdicts, and its verification modes."""

import inspect
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from escapewheel_reader import RegistryFault, RegistryUnavailable, open_packet
from packet_fixture import install_registry, read_registry

from escapewheel_validator import Verification, validate
from escapewheel_validator.validator import check_packet_manifest

from .builders import add_array, add_extension, external_array, rewrite_table, verdicts_of, zarr_v3_metadata
from .conftest import owned_digest


def _checks(report):
    return {finding.check for finding in report.findings}


def test_a_mode_that_needs_external_resources_resolves_them():
    assert not Verification().resolves_external
    assert Verification(checksums=True).resolves_external
    assert Verification(store_digests=True).resolves_external
    assert Verification(external=True).resolves_external


def test_external_resolution_can_be_refused_beside_checksums():
    assert not Verification(checksums=True, external=False).resolves_external


def test_checksums_through_the_object_reach_external_resources(packet_root):
    """Part 04 §5.3: a digest of an external resource is level 3c, which resolving comes before."""
    root = external_array(packet_root)
    assert "external.verified" not in _checks(validate(open_packet(root)))
    assert "external.verified" in _checks(validate(open_packet(root), verification=Verification(checksums=True)))
    owned_only = validate(open_packet(root), verification=Verification(checksums=True, external=False))
    assert "owned.verified" in _checks(owned_only) and "external.verified" not in _checks(owned_only)


def test_the_separate_keywords_keep_their_meaning(packet_root):
    """`external` is off unless given, so `checksums` alone establishes packet-owned digests only."""
    root = external_array(packet_root)
    by_keyword = validate(open_packet(root), checksums=True)
    by_object = validate(open_packet(root), verification=Verification(checksums=True, external=False))
    assert by_keyword.findings == by_object.findings
    assert "external.verified" in _checks(validate(open_packet(root), external=True))


def test_a_mode_keyword_beside_the_object_is_refused(packet_root):
    with pytest.raises(TypeError, match="verification or checksums"):
        validate(open_packet(packet_root), verification=Verification(), checksums=True)


def test_conforming_packet_passes(packet_root):
    report = validate(open_packet(packet_root))
    assert report.passed
    assert report.errors == 0 and report.warnings == 0


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


def test_an_extension_finding_fails_the_packet_and_not_core(packet_root):
    """Part 05 §9.5: an extension's resources are the packet's, so its failure is the packet's too."""
    root = add_extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "sideways"))
    report = validate(open_packet(root))
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")
    assert not report.passed
    assert report.bound == ("core", "task")


def test_one_extension_failing_leaves_another_passed(packet_root):
    root = _required_extension(add_extension(packet_root, mutate=lambda r: r["choice"].__setitem__(0, "?")), "cue")
    report = validate(open_packet(root))
    assert verdicts_of(report, "core", "task", "cue") == ("failed", "passed", "failed", "passed")


def test_an_extension_array_defect_fails_the_extension_and_not_core(packet_root):
    """Part 05 §9.5: an array finding belongs to the registry declaring the array, not to core."""
    add_array(packet_root, declared=["sharding_indexed", "blosc"], document=zarr_v3_metadata(fill_value=None))
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
    rewrite_table(packet_root, "array_assets", assets.set_column(2, "resource_id", pa.array(["probe.waveform_mean"])))
    report = validate(open_packet(packet_root))
    finding = next(f for f in report.findings if f.check == "array.no_fill_value")
    assert finding.registry == "probe"
    assert verdicts_of(report, "core", "probe") == ("failed", "passed", "failed")


def test_a_shape_finding_leaves_every_registry_incomplete(packet_root):
    """Part 05 §9.5: an early-phase finding withholds every registry's evaluation."""
    root = add_extension(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    manifest["created_at"] = "yesterday"
    (root / "packet.json").write_text(json.dumps(manifest))
    report, _ = check_packet_manifest(root)
    assert [(f.check, f.registry) for f in report.findings] == [("packet.manifest.schema", None)]
    assert verdicts_of(report, "core", "task") == ("failed", "incomplete", "incomplete")


def _unparseable_extension(root):
    """Bind the extension to bytes that match their digest and are not JSON."""
    install_registry(root, read_registry(root, "task"), body=b"{not json")
    return root


def test_an_unparseable_extension_fails_only_what_needs_it(packet_root):
    """Part 04 §10: a reader fails the operation that needs the registry, naming it."""
    packet = open_packet(_unparseable_extension(add_extension(packet_root)))
    assert packet.table("core.intervals").num_rows == 2
    with pytest.raises(RegistryUnavailable) as refused:
        packet.extensions()
    assert (refused.value.registry_id, refused.value.reason) == ("task", RegistryFault.INVALID)


def test_validator_preserves_an_available_unparseable_extension_result(packet_root):
    root = _unparseable_extension(add_extension(packet_root))
    report = validate(open_packet(root))
    task = next(item for item in report.registries if item.subject == "task")
    assert task.result.state == "invalid"
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")
    assert not any(f.check == "extension.validated" for f in report.findings)


def test_an_extension_that_fails_binding_withholds_only_its_entries(packet_root):
    """Part 04 §10: core's declaration phase still runs, and the extension's entries are not judged."""
    root = add_extension(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    manifest["registries"]["task"]["version"] = "0.9.0"
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    binding = next(f for f in report.findings if f.check == "packet.registry.version")
    assert binding.registry == "task"
    assert verdicts_of(report, "core", "task") == ("failed", "passed", "failed")
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
    assert verdicts_of(report, "core", "cue", "lick") == ("passed", "passed", "passed", "passed")

    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"] = [r for r in manifest["resources"] if r["resource_id"] != "lick.marks"]
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root))
    missing = [f for f in report.findings if f.check == "packet.resource.required_missing"]
    assert [f.message for f in missing] == ["required singleton lick.marks is absent"]

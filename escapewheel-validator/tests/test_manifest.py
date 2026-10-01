"""Part 04 §10's manifest phases, from the manifest's bytes through registry binding."""

import gzip
import json

import jsonschema
import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import FormatCheckUnavailable, check_packet_manifest, validate
from escapewheel_validator.manifest import format_checker, prefix_digest

from .builders import add_family_declaration, declare_analysis
from .conftest import install_registry, read_registry


def _edit(root, change):
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    change(manifest)
    path.write_text(json.dumps(manifest))


def _checks(root):
    report, _ = check_packet_manifest(root)
    return [finding.check for finding in report.findings]


def test_a_conforming_manifest_binds_its_core_registry(packet_root):
    report, bound = check_packet_manifest(packet_root)
    assert report.findings == []
    assert bound.core is not None and bound.directs("core")
    assert [(item.subject, item.core, item.directs_checks) for item in report.registries] == [("core", True, True)]


@pytest.mark.parametrize("raw", [b"{not json", b'{"a": "\xff"}'])
def test_bytes_that_are_not_utf8_json_are_refused(packet_root, raw):
    (packet_root / "packet.json").write_bytes(raw)
    assert _checks(packet_root) == ["packet.manifest.invalid_json"]


def test_a_repeated_member_inside_an_entry_is_named_where_it_repeats(packet_root):
    text = (packet_root / "packet.json").read_text()
    repeated = text.replace(
        '"resource_id": "core.intervals"', '"resource_id": "core.intervals", "resource_id": "core.x"'
    )
    (packet_root / "packet.json").write_text(repeated)
    report, _ = check_packet_manifest(packet_root)
    assert [f.check for f in report.findings] == ["packet.manifest.duplicate_member"]
    assert report.findings[0].rows == (("/resources/1", "resource_id"),)


def test_a_repeated_member_is_refused_before_the_schema_runs(packet_root):
    text = (packet_root / "packet.json").read_text()
    (packet_root / "packet.json").write_text(
        text.replace('"packet_id": "session_001"', '"packet_id": "a", "packet_id": "b"')
    )
    report, bound = check_packet_manifest(packet_root)
    assert [f.check for f in report.findings] == ["packet.manifest.duplicate_member"]
    assert report.findings[0].rows == (("", "packet_id"),)
    assert bound is None


@pytest.mark.parametrize(
    "change",
    [
        *[
            pytest.param(lambda m, name=name: m.update({name: "x"}), id=f"root_{name}")
            for name in (
                "registry_version",
                "extensions",
                "provenance",
                "creators",
                "dataset_id",
                "keywords",
                "license",
                "release_id",
                "source_summary",
                "unknown",
            )
        ],
        pytest.param(lambda m: m["resources"][0].update(processing_run_id="run"), id="entry_processing_run_id"),
        pytest.param(lambda m: m["resources"][0].update(semantic_type="x"), id="entry_semantic_type"),
        pytest.param(lambda m: m["resources"][0].update(kind="table"), id="entry_unknown"),
        pytest.param(lambda m: m["validation"].update(report_uri="r.json"), id="validation_report_uri"),
        pytest.param(lambda m: m["registries"]["core"].update(extra=True), id="descriptor_unknown"),
        pytest.param(lambda m: m.update(retention={"keep_versions": 1, "extra": 1}), id="retention_unknown"),
        pytest.param(
            lambda m: _members(m, [{"key": "a", "size_bytes": 1, "extra": 1}]),
            id="member_unknown",
        ),
        pytest.param(
            lambda m: _members(
                m, [{"key": "a", "size_bytes": 1, "store_digest": {"algorithm": "etag", "value": "x", "extra": 1}}]
            ),
            id="store_digest_unknown",
        ),
        pytest.param(lambda m: m["resources"][0].update(resource_id="sessions"), id="resource_id_without_namespace"),
        pytest.param(lambda m: m["resources"][0].update(derived_from=["core.a", "core.a"]), id="derived_from_repeated"),
        pytest.param(lambda m: m["resources"][0].pop("validation_state"), id="validation_state_missing"),
        pytest.param(lambda m: m["resources"][0].update(derived_from=[]), id="derived_from_empty"),
        pytest.param(lambda m: m["resources"][0].update(uri="s3://b/k"), id="absolute_uri_not_external"),
        pytest.param(lambda m: m["resources"][0].update(source="raw"), id="source_not_external"),
        pytest.param(lambda m: m.update(registries={}), id="no_registries"),
        pytest.param(lambda m: m["resources"][0].update(sha256="0" * 64), id="sha256_in_place_of_digest"),
        pytest.param(lambda m: m["resources"][0]["digest"].update(algorithm="md5"), id="digest_algorithm_unknown"),
        pytest.param(lambda m: m["resources"][0]["digest"].update(value="0" * 16), id="digest_sha256_width"),
        pytest.param(
            lambda m: m["resources"][0].update(digest={"algorithm": "crc32c", "value": "0" * 16}),
            id="digest_crc32c_width",
        ),
        pytest.param(lambda m: m["resources"][0]["digest"].update(extra=1), id="digest_unknown"),
        pytest.param(lambda m: _members(m, []), id="members_empty"),
        pytest.param(
            lambda m: _members(m, [{"key": "a", "size_bytes": 1, "digest": "1" * 8}]), id="member_digest_without_entry"
        ),
        pytest.param(
            lambda m: _members(
                m,
                [{"key": "a", "size_bytes": 1, "digest": "1" * 64}, {"key": "b", "size_bytes": 1}],
                digest={"algorithm": "sha256", "value": "0" * 64},
            ),
            id="member_digest_partial",
        ),
        pytest.param(
            lambda m: _members(
                m,
                [{"key": "a", "size_bytes": 1, "digest": "1" * 64}],
                digest={"algorithm": "crc64nvme", "value": "0" * 64},
            ),
            id="member_digest_width",
        ),
    ],
)
def test_the_schema_refuses_what_it_does_not_define(packet_root, change):
    _edit(packet_root, change)
    assert set(_checks(packet_root)) == {"packet.manifest.schema"}


@pytest.mark.parametrize("value", ["yesterday", "2026-08-26", "2026-08-26T00:00:00"])
def test_a_malformed_date_time_is_a_shape_finding(packet_root, value):
    _edit(packet_root, lambda m: m.update(created_at=value))
    report, _ = check_packet_manifest(packet_root)
    finding = report.findings[0]
    assert finding.check == "packet.manifest.schema"
    assert finding.rows == (("/created_at", "#/properties/created_at/format"),)


def test_every_date_time_member_is_asserted(packet_root):
    def change(manifest):
        manifest["validation"]["validated_at"] = "yesterday"
        manifest["resources"][0]["verified_at"] = "yesterday"

    _edit(packet_root, change)
    report, _ = check_packet_manifest(packet_root)
    assert {row[0] for f in report.findings for row in f.rows} == {
        "/validation/validated_at",
        "/resources/0/verified_at",
    }
    assert {f.check for f in report.findings} == {"packet.manifest.schema"}


def test_a_manifest_the_reader_opens_still_fails_its_schema(packet_root):
    """R130 §6: reading proceeds past closure and formats, and validation reports both."""
    from escapewheel_reader import open_packet

    from escapewheel_validator import validate

    _edit(packet_root, lambda m: m.update(created_at="2026-09-04 04:22:45", unknown=True))
    report = validate(open_packet(packet_root))
    assert {row[0] for f in report.findings for row in f.rows} == {"/created_at", ""}
    assert {f.check for f in report.findings} == {"packet.manifest.schema"}


@pytest.mark.parametrize(
    "path",
    [
        "/registries/core.json.gz",
        "../core.json.gz",
        "./core.json.gz",
        "a/../b.json.gz",
        "a/./b.json.gz",
        "a\\b",
        "s3://b/k",
        "a//b",
        "",
    ],
)
def test_a_descriptor_path_stays_inside_the_packet(packet_root, path):
    _edit(packet_root, lambda m: m["registries"]["core"].update(path=path))
    assert set(_checks(packet_root)) == {"packet.manifest.schema"}


def test_a_repeated_resource_id_is_an_entries_finding(packet_root):
    _edit(packet_root, lambda m: m["resources"].append(m["resources"][0]))
    assert _checks(packet_root) == ["packet.resource.id_unique"]


def _members(manifest, members, **entry):
    manifest["resources"].append(
        {
            "resource_id": "core.external",
            "declaration_id": "core.external",
            "uri": "s3://bucket/prefix",
            "external": True,
            "validation_state": "not_run",
            "members": members,
            **entry,
        }
    )


def test_member_keys_are_unique(packet_root):
    _edit(packet_root, lambda m: _members(m, [{"key": "a", "size_bytes": 1}, {"key": "a", "size_bytes": 1}]))
    assert _checks(packet_root) == ["packet.resource.member_unique"]


def test_size_bytes_is_the_sum_of_the_members(packet_root):
    _edit(packet_root, lambda m: _members(m, [{"key": "a", "size_bytes": 1}], size_bytes=2))
    assert _checks(packet_root) == ["packet.resource.member_size"]


@pytest.mark.parametrize(("algorithm", "width"), [("sha256", 64), ("crc64nvme", 16), ("crc32c", 8), ("crc32", 8)])
def test_digest_is_the_value_of_its_member_list(packet_root, algorithm, width):
    """Part 04 §4.3: the members carry values under the entry's algorithm, and the entry the listing's SHA-256."""
    members = [
        {"key": "b", "size_bytes": 1, "digest": "1" * width},
        {"key": "a", "size_bytes": 2, "digest": "2" * width},
    ]
    listed = {"algorithm": algorithm, "value": prefix_digest(members)}
    _edit(packet_root, lambda m: _members(m, members, digest=listed))
    assert _checks(packet_root) == []
    _edit(packet_root, lambda m: m["resources"][-1].update(digest={"algorithm": algorithm, "value": "0" * 64}))
    assert _checks(packet_root) == ["packet.resource.member_digest"]


def test_a_packet_owned_entry_records_a_digest(packet_root):
    _edit(packet_root, lambda m: m["resources"][0].pop("digest"))
    assert _checks(packet_root) == ["packet.resource.digest_missing"]


def test_an_external_entry_need_not_record_a_digest(packet_root):
    _edit(packet_root, lambda m: _members(m, [{"key": "a", "size_bytes": 1}]))
    assert _checks(packet_root) == []


@pytest.mark.parametrize(
    "uri",
    [
        pytest.param("tables/core/intervals%20one.parquet", id="encoded_space"),
        pytest.param("opaque/core.qc_report/QC%20report%20%C3%A9.pdf", id="encoded_utf8"),
        pytest.param("s3://bucket/QC report é.pdf", id="absolute"),
    ],
)
def test_a_uri_in_the_one_form_passes(packet_root, uri):
    """Part 03 §4: absolute, or a relative reference with only unreserved characters left bare."""
    _edit(packet_root, lambda m: m["resources"][1].update(uri=uri, external=True))
    assert _checks(packet_root) == []


@pytest.mark.parametrize(
    "uri",
    [
        pytest.param("tables/core/intervals one.parquet", id="raw_space"),
        pytest.param("tables/core/r%c3%a9sum%c3%a9.parquet", id="lowercase_hex"),
        pytest.param("tables/core/%41.parquet", id="encoded_unreserved"),
        pytest.param("tables/../tables/core/intervals.parquet", id="dot_dot_segment"),
        pytest.param("tables/./core/intervals.parquet", id="dot_segment"),
        pytest.param("/tables/core/intervals.parquet", id="leading_slash"),
        pytest.param("tables//core/intervals.parquet", id="empty_segment"),
        pytest.param("tables/a%2Fb.parquet", id="encoded_slash"),
        pytest.param("tables/%FF.parquet", id="not_utf8"),
        pytest.param("c:/tables/core/intervals.parquet", id="windows_drive"),
    ],
)
def test_a_uri_not_in_the_one_form_is_an_entries_finding(packet_root, uri):
    """Part 04 §10: `packet.resource.uri_form` at `error`, naming the entry, and nothing later runs."""
    _edit(packet_root, lambda m: m["resources"][1].update(uri=uri))
    report, bound = check_packet_manifest(packet_root)
    assert [(f.level, f.check) for f in report.findings] == [("error", "packet.resource.uri_form")]
    assert report.findings[0].rows == (("core.intervals", uri),)
    assert report.findings[0].message.startswith("core.intervals: ")
    assert bound is None


def test_exactly_one_core_descriptor(packet_root):
    _edit(packet_root, lambda m: m["registries"]["core"].update(role="extension"))
    assert _checks(packet_root) == ["packet.registry.core_count"]
    _edit(
        packet_root, lambda m: m["registries"].update(base={**m["registries"]["core"], "role": "core", "path": "x.gz"})
    )
    _edit(packet_root, lambda m: m["registries"]["core"].update(role="core"))
    assert _checks(packet_root) == ["packet.registry.core_count"]


def test_two_descriptors_do_not_share_a_path(packet_root):
    _edit(packet_root, lambda m: m["registries"].update(task={**m["registries"]["core"], "role": "extension"}))
    assert _checks(packet_root) == ["packet.registry.path_unique"]


def _stored(root, registry_id="core"):
    manifest = json.loads((root / "packet.json").read_text())
    return root / manifest["registries"][registry_id]["path"]


def test_a_missing_registry_is_named(packet_root):
    _stored(packet_root).unlink()
    report, bound = check_packet_manifest(packet_root)
    assert [f.check for f in report.findings] == ["packet.registry.missing"]
    assert report.findings[0].rows[0][0] == "core"
    assert bound.core is None and report.registries == []


def test_a_registry_that_is_not_gzip_is_unreadable(packet_root):
    stored = _stored(packet_root)
    stored.write_bytes(gzip.decompress(stored.read_bytes()))
    assert _checks(packet_root) == ["packet.registry.unreadable"]


def test_a_registry_of_two_gzip_members_is_unreadable(packet_root):
    """Part 03 §3.3: one member, so the digest covers exactly one decompressed stream."""
    stored = _stored(packet_root)
    body = gzip.decompress(stored.read_bytes())
    half = len(body) // 2
    stored.write_bytes(gzip.compress(body[:half]) + gzip.compress(body[half:]))
    assert _checks(packet_root) == ["packet.registry.unreadable"]


def test_trailing_bytes_after_the_gzip_member_are_unreadable(packet_root):
    stored = _stored(packet_root)
    stored.write_bytes(stored.read_bytes() + b"\0")
    assert _checks(packet_root) == ["packet.registry.unreadable"]


def test_a_digest_mismatch_obtains_no_registry_result(packet_root):
    _edit(packet_root, lambda m: m["registries"]["core"].update(sha256="0" * 64))
    report, bound = check_packet_manifest(packet_root)
    assert [f.check for f in report.findings] == ["packet.registry.digest"]
    assert report.registries == [] and bound.core is None


def test_the_document_identity_matches_its_descriptor_name(packet_root):
    install_registry(packet_root, read_registry(packet_root), name="base", role="core")
    _edit(packet_root, lambda m: m["registries"].pop("core"))
    report, bound = check_packet_manifest(packet_root)
    assert [f.check for f in report.findings] == ["packet.registry.identity"]
    assert bound.core is None
    assert report.registries[0].result.state == "valid" and not report.registries[0].directs_checks


def test_the_document_class_matches_its_descriptor_role(packet_root, extension_document):
    install_registry(packet_root, extension_document, role="core")
    _edit(packet_root, lambda m: m["registries"]["core"].update(role="extension"))
    checks = _checks(packet_root)
    assert checks.count("packet.registry.role") == 2


def test_the_document_version_matches_its_descriptor(packet_root):
    _edit(packet_root, lambda m: m["registries"]["core"].update(version="9.9.9"))
    assert _checks(packet_root) == ["packet.registry.version"]


@pytest.mark.parametrize("member", ["semantic_standard_version", "logical_standard_version"])
def test_a_core_registry_matches_the_manifest_standards(packet_root, member):
    _edit(packet_root, lambda m: m.update({member: "escapewheel-other-v9"}))
    assert _checks(packet_root) == ["packet.registry.standard"]


def test_an_extension_matches_only_the_logical_standard(packet_root, extension_document):
    install_registry(packet_root, extension_document)
    _edit(packet_root, lambda m: m.update(logical_standard_version="escapewheel-other-v9"))
    report, _ = check_packet_manifest(packet_root)
    standard = [f for f in report.findings if f.check == "packet.registry.standard"]
    assert {f.registry for f in standard} == {"core", "task"}


def test_an_extension_binding_finding_is_attributed_to_it(packet_root, extension_document):
    install_registry(packet_root, extension_document)
    _edit(packet_root, lambda m: m["registries"]["task"].update(version="9.9.9"))
    report, bound = check_packet_manifest(packet_root)
    assert [(f.check, f.registry) for f in report.findings] == [("packet.registry.version", "task")]
    assert report.verdict("task") == "failed" and not report.passed
    assert bound.core is not None and bound.extensions == {}


@pytest.fixture
def extension_document():
    return {
        "$schema": "https://escapewheel.org/schemas/registry/0.11.0",
        "registry_id": "task",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.2",
        "extension_id": "task",
        "resources": {
            "task.notes": {
                "content_class": "extension",
                "kind": "opaque",
                "instances": {"mode": "family"},
                "requires": [],
                "lineage": "optional",
            }
        },
    }


def test_an_installation_that_cannot_assert_date_time_is_refused(monkeypatch):
    """Part 04 §10: a shape check that annotates `date-time` without asserting it is no shape check."""
    known = {name: check for name, check in jsonschema.FormatChecker.checkers.items() if name != "date-time"}
    monkeypatch.setattr(jsonschema.FormatChecker, "checkers", known)
    with pytest.raises(FormatCheckUnavailable):
        format_checker()


def test_retired_codec_summary_is_rejected_by_the_manifest_schema(packet_root):
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
    entry["required_codecs"] = ["wavpack"]
    path.write_text(json.dumps(entry))
    report = validate(open_packet(packet_root))
    assert not report.passed
    assert {f.check for f in report.findings} == {"packet.manifest.schema"}


def test_a_manifest_entry_naming_a_run_is_refused_by_its_schema(packet_root):
    declare_analysis(packet_root, processing_run_id="ghost")
    report = validate(open_packet(packet_root))
    assert not report.passed
    finding = next(f for f in report.findings if f.check == "packet.manifest.schema")
    assert finding.rows[0][1].endswith("/additionalProperties")


def test_a_packet_owned_resource_without_a_digest_fails_the_manifest(packet_root):
    """Part 04 §4.3: a writer records one for every resource the packet owns."""
    manifest = json.loads((packet_root / "packet.json").read_text())
    del manifest["resources"][1]["digest"]
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(packet_root))
    assert [(f.level, f.check) for f in report.findings] == [("error", "packet.resource.digest_missing")]

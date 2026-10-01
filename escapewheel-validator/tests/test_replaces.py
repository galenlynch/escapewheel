"""A manifest naming the packets it replaces (Part 04 §3), and an amendment keeping that link."""

import hashlib
import json
import shutil

import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import ReplacedPacketUnreadable, check_packet_manifest, validate

OTHER_SHA = "0" * 64


def _manifest(root):
    return json.loads((root / "packet.json").read_text())


def _write(root, manifest):
    (root / "packet.json").write_text(json.dumps(manifest, indent=2) + "\n")


def _replacing(root, version, *items):
    manifest = _manifest(root)
    manifest["packet_version"] = version
    manifest["replaces"] = list(items)
    _write(root, manifest)


def _item(packet_id="session_001", packet_version="0.1.0", sha256=OTHER_SHA, **extra):
    return {"packet_id": packet_id, "packet_version": packet_version, "sha256": sha256, **extra}


def _checks(root):
    report, _ = check_packet_manifest(root)
    return [finding.check for finding in report.findings]


def test_a_replacement_at_a_greater_major_version_conforms(packet_root):
    _replacing(packet_root, "1.0.0", _item())
    assert _checks(packet_root) == []


@pytest.mark.parametrize(("version", "named"), [("0.1.0", "0.1.0"), ("1.0.0", "1.2.0"), ("1.0.0", "2.0.0")])
def test_naming_its_own_packet_id_below_a_greater_major_version_is_required(packet_root, version, named):
    """Itself included: a manifest at 0.1.0 naming 0.1.0 of its own packet_id."""
    _replacing(packet_root, version, _item(packet_version=named))
    report, _ = check_packet_manifest(packet_root)
    assert [(f.check, f.rows) for f in report.findings] == [
        ("packet.replaces.major_version", (("1", "session_001", named),))
    ]


def test_a_packet_of_another_packet_id_may_be_named_at_any_version(packet_root):
    _replacing(packet_root, "0.1.0", _item(packet_id="session_000", packet_version="3.0.0"))
    assert _checks(packet_root) == []


@pytest.mark.parametrize(
    "item",
    [_item(uri="../old"), {"packet_id": "session_001", "packet_version": "0.1.0"}],
    ids=["location", "no-digest"],
)
def test_an_item_carrying_a_location_or_lacking_its_digest_fails_the_schema(packet_root, item):
    _replacing(packet_root, "1.0.0", item)
    assert _checks(packet_root) == ["packet.manifest.schema"]


def _predecessor(tmp_path, packet_root):
    """Copy the packet as the version a replacement names, returning its root and item."""
    old = tmp_path / "old"
    shutil.copytree(packet_root, old)
    body = (old / "packet.json").read_bytes()
    return old, _item(sha256=hashlib.sha256(body).hexdigest())


def _mismatches(report):
    return [(f.level, f.rows) for f in report.findings if f.check == "packet.replaces.mismatch"]


def test_a_supplied_packet_matching_its_item_is_confirmed(tmp_path, packet_root):
    old, item = _predecessor(tmp_path, packet_root)
    _replacing(packet_root, "1.0.0", item)
    report = validate(open_packet(packet_root), replaced=[old])
    assert report.passed and _mismatches(report) == []


def test_a_supplied_packet_differing_from_its_item_is_a_warning(tmp_path, packet_root):
    """The validator cannot tell which is wrong, so the packet passes and both values are named."""
    old, item = _predecessor(tmp_path, packet_root)
    _replacing(packet_root, "1.0.0", {**item, "sha256": OTHER_SHA})
    report = validate(open_packet(packet_root), replaced=[old])
    assert report.passed
    assert _mismatches(report) == [("warning", (("1", "sha256", OTHER_SHA, item["sha256"]),))]


def test_no_supplied_packet_reports_nothing_about_the_link(packet_root):
    _replacing(packet_root, "1.0.0", _item())
    report = validate(open_packet(packet_root))
    assert report.passed and _mismatches(report) == []


def test_an_item_naming_a_version_later_amended_is_confirmed_from_the_retained_manifest(tmp_path, packet_root):
    old, item = _predecessor(tmp_path, packet_root)
    (old / "manifests").mkdir()
    shutil.copyfile(old / "packet.json", old / "manifests" / "0.1.0.json")
    amended = _manifest(old)
    _write(old, {**amended, "packet_version": "0.1.1"})
    _replacing(packet_root, "1.0.0", item)
    report = validate(open_packet(packet_root), replaced=[old])
    assert _mismatches(report) == []


@pytest.mark.parametrize("body", [None, "not json"], ids=["absent", "unparsable"])
def test_a_supplied_path_holding_no_readable_manifest_is_refused(tmp_path, packet_root, body):
    _replacing(packet_root, "1.0.0", _item())
    supplied = tmp_path / "supplied"
    if body is not None:
        supplied.mkdir()
        (supplied / "packet.json").write_text(body)
    with pytest.raises(ReplacedPacketUnreadable) as refused:
        validate(open_packet(packet_root), replaced=[supplied])
    assert refused.value.path == supplied


def _amended_replacement(root, change):
    """Make the packet a replacement at 1.0.0, retain it, and amend it to 1.0.1 with `change`."""
    _replacing(root, "1.0.0", _item())
    (root / "manifests").mkdir()
    shutil.copyfile(root / "packet.json", root / "manifests" / "1.0.0.json")
    manifest = {**_manifest(root), "packet_version": "1.0.1"}
    change(manifest)
    _write(root, manifest)
    return validate(open_packet(root))


def _identity(report):
    return [f.rows for f in report.findings if f.check == "amendment.identity_changed"]


def test_an_amendment_keeping_the_major_version_and_the_link_passes(packet_root):
    report = _amended_replacement(packet_root, lambda manifest: None)
    assert report.passed, [f"{f.check}: {f.message}" for f in report.findings if f.level == "error"]


@pytest.mark.parametrize(
    ("change", "member"),
    [
        (lambda m: m.pop("replaces"), "replaces"),
        (lambda m: m.update(replaces=[_item(packet_version="0.2.0")]), "replaces"),
        (lambda m: m.update(packet_version="2.0.0"), "the major version of packet_version"),
    ],
    ids=["dropped", "altered", "major"],
)
def test_an_amendment_changing_the_major_version_or_the_link_is_identity_changed(packet_root, change, member):
    (rows,) = _identity(_amended_replacement(packet_root, change))
    assert [row[0] for row in rows] == [member]

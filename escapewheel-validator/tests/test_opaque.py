"""A packet-owned opaque payload: presence, digest, and names (Part 03 §§4, 10, 11.3; Part 05 §5.3)."""

import hashlib
import json

import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import validate
from escapewheel_validator.opaque import colliding, findings, payload_directories, unportable_to_windows

from .conftest import install_registry, read_registry

PORTABILITY = "physical.opaque_name_portability"


def _declare(root, declaration_id="core.test_payloads", *, registry=None):
    """Declare an opaque family in core, or an opaque singleton in the given extension document."""
    if registry is None:
        document = read_registry(root)
        document["resources"][declaration_id] = {
            "content_class": "core",
            "kind": "opaque",
            "instances": {"mode": "family"},
            "requires": [],
            "lineage": "optional",
        }
    else:
        document = registry
    install_registry(root, document)


def _own(root, resource_id, uri, files, *, declaration_id="core.test_payloads", digest=None):
    """Write a payload under the names `files` gives, relative to the root, and add its entry at `uri`.

    The recorded digest is the single object's where one file is written and otherwise the prefix
    value, each computed here from the bytes; `digest` overrides it.
    """
    for relative, body in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes(body)
    if digest is None:
        if len(files) == 1:
            digest = hashlib.sha256(next(iter(files.values()))).hexdigest()
        else:
            prefix = min(files, key=len).rsplit("/", 1)[0]
            rows = sorted(
                (
                    [key.removeprefix(f"{prefix}/"), len(body), hashlib.sha256(body).hexdigest()]
                    for key, body in files.items()
                ),
                key=lambda row: row[0].encode(),
            )
            listing = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()
            digest = hashlib.sha256(listing).hexdigest()
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": resource_id,
            "declaration_id": declaration_id,
            "uri": uri,
            "validation_state": "not_run",
            "digest": {"algorithm": "sha256", "value": digest},
            "size_bytes": sum(len(body) for body in files.values()),
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest))


def _validate(root, **options):
    return validate(open_packet(root), **options)


def _portability(report):
    return [f for f in report.findings if f.check == PORTABILITY]


# -- presence and digest: the existing rules, over a kind that is neither table nor array ---------


def test_an_owned_opaque_file_is_present_and_its_digest_holds(packet_root):
    """Part 03 §10: a payload that is one file is a single object."""
    _declare(packet_root)
    _own(packet_root, "core.clip", "opaque/core.clip/clip.mp4", {"opaque/core.clip/clip.mp4": b"\x00\x00\x00\x18ftyp"})
    report = _validate(packet_root, checksums=True)
    assert report.passed and report.warnings == 0
    verified = next(f for f in report.findings if f.check == "owned.verified")
    assert verified.message.startswith("7 of 7")


def test_an_owned_opaque_directory_is_digested_as_a_prefix(packet_root):
    """Part 04 §5.4: its keys are paths relative to the payload, `0.png` and `1.png`, not the resource."""
    _declare(packet_root)
    files = {"opaque/core.frames/frames/0.png": b"123456789", "opaque/core.frames/frames/1.png": b"frame one"}
    listing = (
        b'[["0.png",9,"15e2b0d3c33891ebb0f1ef609ec419420c20e320ce94c65fbc8c3312448eb225"],'
        b'["1.png",9,"' + hashlib.sha256(b"frame one").hexdigest().encode() + b'"]]'
    )
    _own(packet_root, "core.frames", "opaque/core.frames/frames", files, digest=hashlib.sha256(listing).hexdigest())
    report = _validate(packet_root, checksums=True)
    assert report.passed and report.warnings == 0
    assert "owned.digest" not in {f.check for f in report.findings}


def test_an_owned_opaque_digest_that_disagrees_is_an_error(packet_root):
    _declare(packet_root)
    _own(packet_root, "core.clip", "opaque/core.clip/clip.mp4", {"opaque/core.clip/clip.mp4": b"clip"}, digest="0" * 64)
    report = _validate(packet_root, checksums=True)
    assert [(f.level, f.registry) for f in report.findings if f.check == "owned.digest"] == [("error", "core")]
    assert not report.passed


def test_an_absent_owned_opaque_payload_is_missing_without_checksums(packet_root):
    """Part 05 §5.3's file presence, as a packet-owned array's is checked, with no byte read."""
    _declare(packet_root)
    _own(packet_root, "core.clip", "opaque/core.clip/clip.mp4", {"opaque/core.clip/clip.mp4": b"clip"})
    (packet_root / "opaque/core.clip/clip.mp4").unlink()
    report = _validate(packet_root)
    assert [(f.level, f.check) for f in report.findings if f.level == "error"] == [("error", "resource.missing")]


def test_a_payload_whose_name_needs_encoding_is_found_by_its_decoded_name(packet_root):
    """Part 03 §4: the URI is percent-encoded, the file keeps `QC report é.pdf`, and its digest holds."""
    _declare(packet_root)
    _own(
        packet_root,
        "core.qc_report",
        "opaque/core.qc_report/QC%20report%20%C3%A9.pdf",
        {"opaque/core.qc_report/QC report é.pdf": b"%PDF-1.7"},
    )
    report = _validate(packet_root, checksums=True)
    assert report.passed and report.warnings == 0
    assert next(f for f in report.findings if f.check == "owned.verified").message.startswith("7 of 7")


# -- names that would not survive a copy (Part 05 §5.3) ---------------------------------------------


def test_colliding_and_windows_names_warn_once_each_and_the_packet_passes(packet_root):
    """`é` in NFC beside `É` in NFD is one set; `12:00:00.png` is one name; two findings in all."""
    _declare(packet_root)
    base = "opaque/core.frames/frames"
    files = {f"{base}/é.png": b"a", f"{base}/E\u0301.png": b"b", f"{base}/12:00:00.png": b"c"}
    _own(packet_root, "core.frames", base, files)
    report = _validate(packet_root, checksums=True)
    warned = _portability(report)
    assert [(f.level, f.registry, f.rows) for f in warned] == [
        ("warning", "core", (("core.frames", base, "E\u0301.png", "é.png"),)),
        ("warning", "core", (("core.frames", base, "12:00:00.png"),)),
    ]
    assert all(f.message.startswith("core.frames: in 'opaque/core.frames/frames'") for f in warned)
    assert "'E\\u0301.png', '\\xe9.png' are one name" in warned[0].message, "escaped, as they print alike"
    assert report.passed and report.warnings == 2
    assert "owned.digest" not in {f.check for f in report.findings}


def test_a_uri_segment_windows_cannot_hold_is_named_in_its_own_directory(packet_root):
    """A decoded segment of the payload's `uri` counts, and the payload's own name once."""
    _declare(packet_root)
    _own(packet_root, "core.clip", "media/CON/clip.", {"media/CON/clip.": b"clip"})
    report = _validate(packet_root)
    assert [f.rows[0] for f in _portability(report)] == [
        ("core.clip", "media", "CON"),
        ("core.clip", "media/CON", "clip."),
    ]
    assert report.passed


def test_a_warning_on_an_extensions_payload_is_that_extensions(packet_root):
    """Part 05 §9.5: attributed to the registry whose declaration the entry names."""
    extension = {
        "$schema": "https://escapewheel.org/schemas/registry/0.9.0",
        "registry_id": "task",
        "registry_version": "0.1.0",
        "logical_standard_version": "escapewheel-logical-v0.1",
        "rule_language": "escapewheel-rule-sql-v0.1",
        "extension_id": "task",
        "resources": {
            "task.report": {
                "content_class": "extension",
                "kind": "opaque",
                "instances": {"mode": "singleton", "presence": "optional"},
                "requires": [],
                "lineage": "optional",
            }
        },
    }
    _declare(packet_root, registry=extension)
    _own(
        packet_root,
        "task.report",
        "opaque/task.report/report",
        {"opaque/task.report/report/A.txt": b"1", "opaque/task.report/report/a.txt": b"2"},
        declaration_id="task.report",
    )
    report = _validate(packet_root, checksums=True)
    assert [(f.registry, f.rows[0]) for f in _portability(report)] == [
        ("task", ("task.report", "opaque/task.report/report", "A.txt", "a.txt"))
    ]
    assert report.verdict("task") == "passed" and report.passed


def test_an_external_payload_is_not_assessed(packet_root):
    """Only a packet-owned payload keeps its names under the packet root."""
    _declare(packet_root)
    (packet_root / "media").mkdir()
    (packet_root / "media/a:b.png").write_bytes(b"x")
    manifest = json.loads((packet_root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "core.clip",
            "declaration_id": "core.test_payloads",
            "uri": "media/a%3Ab.png",
            "external": True,
            "validation_state": "not_run",
        }
    )
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    assert _portability(_validate(packet_root)) == []


@pytest.mark.parametrize(
    "name",
    [
        "a\x01b",
        "a\x1fb",
        *(f"a{character}b" for character in '"*:<>?\\|'),
        "clip.",
        "clip ",
        "CON",
        "con",
        "Nul.txt",
        "aux.tar.gz",
        "PRN.",
        "COM1",
        "lpt9.log",
        "COM¹",
        "lpt³.x",
    ],
)
def test_a_name_windows_cannot_hold(name):
    assert unportable_to_windows(name)


@pytest.mark.parametrize(
    "name",
    [
        "clip.mp4",
        "a\x7fb",
        "é.png",
        "COM0",
        "COM10",
        "LPT",
        "CONSOLE",
        "xCON",
        "CON-1",
        "COM\u2074",
        "\u212aON",
        ".hidden",
    ],
)
def test_a_name_windows_holds(name):
    """`\\u212a` is the Kelvin sign, which only Unicode case-insensitivity would read as `K`."""
    assert not unportable_to_windows(name)


def test_names_collide_differing_in_case_normalization_or_both():
    """Unicode D145, and only distinct names: a name does not collide with itself."""
    assert colliding(["a", "A", "é", "E\u0301", "e\u0301", "b", "Straße", "STRASSE"]) == [
        ("A", "a"),
        ("E\u0301", "e\u0301", "é"),
        ("STRASSE", "Straße"),
    ]
    assert colliding(["x", "y"]) == []


def test_each_directory_holds_its_own_names():
    directories = payload_directories(("opaque", "core.frames", "frames"), ["0.png", "sub/A.png", "sub/a.png"])
    assert directories == {
        ".": {"opaque"},
        "opaque": {"core.frames"},
        "opaque/core.frames": {"frames"},
        "opaque/core.frames/frames": {"0.png", "sub"},
        "opaque/core.frames/frames/sub": {"A.png", "a.png"},
    }


def test_collisions_are_sought_only_within_the_payload_and_its_directory():
    """Above the payload each directory holds one name the `uri` gives, so only Windows applies there."""
    found = findings(("opaque", "core.frames", "frames"), ["sub/A.png", "sub/a.png", "b:c"])
    assert found == [
        ("opaque/core.frames/frames", ("b:c",), "windows"),
        ("opaque/core.frames/frames/sub", ("A.png", "a.png"), "collide"),
    ]


# -- Part 03 §4: an external relative reference resolves under the packet root, or its source ------


def _referenced(root, uri, body, **extra):
    _declare(root)
    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "core.clip",
            "declaration_id": "core.test_payloads",
            "uri": uri,
            "external": True,
            "validation_state": "not_run",
            "size_bytes": len(body),
            "digest": {"algorithm": "sha256", "value": hashlib.sha256(body).hexdigest()},
            **extra,
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest))


def test_an_external_relative_reference_is_decoded_under_the_packet_root(packet_root):
    (packet_root / "media").mkdir()
    (packet_root / "media/cam 1.mp4").write_bytes(b"camera one")
    _referenced(packet_root, "media/cam%201.mp4", b"camera one")
    report = _validate(packet_root, external=True, checksums=True)
    assert report.passed
    assert not {"external.unreachable", "external.size_bytes", "external.digest"} & {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert verified.message.startswith("1 external resource(s) resolved; compared 1 digest, 1 size_bytes")


def test_a_source_relative_reference_is_decoded_under_the_sources_location(packet_root, tmp_path):
    """Part 04 §5.5: appended to the source's location, which keeps its last segment."""
    source = tmp_path / "session.nwb"
    (source / "videos").mkdir(parents=True)
    (source / "videos/cam 1.mp4").write_bytes(b"camera one")
    (packet_root / "sources.json").write_text(
        json.dumps({"sources_standard_version": "escapewheel-sources-v0.1", "sources": {"raw": {"uri": str(source)}}})
    )
    _referenced(packet_root, "videos/cam%201.mp4", b"camera one", source="raw")
    report = _validate(packet_root, external=True, checksums=True)
    assert report.passed
    assert not {"external.unreachable", "external.size_bytes", "external.digest"} & {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert verified.message.startswith("1 external resource(s) resolved; compared 1 digest, 1 size_bytes")


def test_an_unresolved_source_is_unreachable_not_wrong(packet_root):
    _referenced(packet_root, "videos/cam%201.mp4", b"camera one", source="raw")
    report = _validate(packet_root, external=True)
    assert report.passed
    assert [(f.level, f.check) for f in report.findings if f.check.startswith("external.")] == [
        ("warning", "external.unreachable")
    ]

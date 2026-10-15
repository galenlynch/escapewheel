"""A packet-owned resource's recorded digest, where a mode asks for it."""

import json

import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import Verification, validate

from .builders import add_array
from .conftest import owned_digest


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
    assert verified.counts == {"checked": 7, "matched": 7}
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


def test_a_crc_prefix_digest_is_the_sha256_of_its_listing(packet_root):
    """Part 04 §4.3: under a CRC the members' values are CRCs and the prefix value is 64 digits."""
    from escapewheel_validator.stores import digest, listing, listing_digest

    root = add_array(packet_root, declared=["zstd"], axes=3)
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
    assert verified.counts == {"checked": 10, "matched": 10}
    assert {row[2] for row in verified.rows} == {"computed"}


def test_an_empty_packet_owned_prefix_is_missing(packet_root):
    """Part 04 §4.3: a prefix holding no object does not exist."""
    root = add_array(packet_root, declared=["zstd"], axes=3)
    (root / "arrays/core/wf.zarr/zarr.json").unlink()
    report = validate(open_packet(root))
    assert ("error", "resource.missing") in {(f.level, f.check) for f in report.findings}
    assert "array.unreadable" not in {f.check for f in report.findings}


def _record_sizes(root, *, off_by=None):
    """Record every packet-owned resource's size, one byte short where `off_by` names it."""
    from escapewheel_validator.stores import listing

    manifest = json.loads((root / "packet.json").read_text())
    for entry in manifest["resources"]:
        entry["size_bytes"] = listing(str(root / entry["uri"])).size_bytes - (entry["resource_id"] == off_by)
    (root / "packet.json").write_text(json.dumps(manifest))
    return root


def test_recorded_sizes_that_hold_draw_no_finding(packet_root):
    root = _record_sizes(add_array(packet_root, declared=["zstd"], axes=3))
    assert "owned.size_bytes" not in {f.check for f in validate(open_packet(root)).findings}


def test_a_wrong_recorded_size_is_an_error_without_checksums(packet_root):
    """A reader takes a remote table's size from the entry, so this is checked on every validation."""
    report = validate(open_packet(_record_sizes(packet_root, off_by="core.intervals")))
    assert not report.passed
    found = [f for f in report.findings if f.check == "owned.size_bytes"]
    assert [(f.level, f.message.split(":")[0]) for f in found] == [("error", "core.intervals")]

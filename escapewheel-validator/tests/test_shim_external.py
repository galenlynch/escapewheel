"""An external resource against what the manifest claims of it, where a mode asks."""

import json

import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import Verification, validate

from .builders import external_array


def test_an_external_resource_is_reported_as_unverified_by_default(packet_root):
    """Part 04 §5.3: structural validation must not reach for bytes the packet does not own."""
    report = validate(open_packet(external_array(packet_root)))
    assert report.passed
    [finding] = [f for f in report.findings if f.check == "external.physical_unassessed"]
    assert (finding.level, finding.rows, finding.registry) == ("info", (("core.waveform_mean",),), "core")
    assert "physical.outside_reader_floor" not in {f.check for f in report.findings}


def test_the_requested_mode_resolves_it(packet_root):
    report = validate(open_packet(external_array(packet_root)), verification=Verification(external=True))
    assert report.passed
    checks = {f.check for f in report.findings}
    assert "external.verified" in checks
    assert "external.physical_unassessed" not in checks, "the two modes must not both speak"


def test_size_bytes_counts_the_whole_prefix_including_its_metadata(packet_root):
    """A dense array asset is a prefix of many objects, so its size is a list, not a stat.
    Excluding the metadata document would make the writer and the validator disagree."""
    assert validate(open_packet(external_array(packet_root)), verification=Verification(external=True)).passed


def test_a_size_that_disagrees_is_an_error_only_in_that_mode(packet_root):
    root = external_array(packet_root, size_bytes=999)
    assert validate(open_packet(root)).passed
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed
    assert "external.size_bytes" in {f.check for f in report.findings}


def test_an_unreachable_resource_is_a_warning_not_an_error(packet_root):
    """Reachability is a property of the reader's situation, not of the packet."""
    root = external_array(packet_root, uri="file:///nowhere/at/all.zarr")
    report = validate(open_packet(root), verification=Verification(external=True))
    assert report.passed
    assert "external.unreachable" in {f.check for f in report.findings}


def test_a_requested_digest_with_nothing_recorded_says_so(packet_root):
    """Part 04 §4.3: an external resource need not record a digest.
    Asking for checksums and finding nothing to compare must not report a clean verification."""
    report = validate(
        open_packet(external_array(packet_root)), verification=Verification(checksums=True, external=True)
    )
    assert report.passed, "a claim the packet never made is not a failure"
    assert "external.no_checksum" in {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert "digest" not in verified.message, "it compared none, so it must not claim any"


@pytest.mark.parametrize("algorithm", ["sha256", "crc64nvme", "crc32c", "crc32"])
def test_a_recorded_digest_is_compared(packet_root, algorithm):
    from escapewheel_validator.stores import digest

    root = external_array(packet_root)
    manifest = json.loads((root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r.get("external"))
    entry["digest"] = {"algorithm": algorithm, "value": digest(entry["uri"], algorithm)}
    (root / "packet.json").write_text(json.dumps(manifest))
    report = validate(open_packet(root), verification=Verification(checksums=True, external=True))
    assert report.passed
    assert "external.no_checksum" not in {f.check for f in report.findings}
    verified = next(f for f in report.findings if f.check == "external.verified")
    assert "1 digest" in verified.message and "route: computed for all 1" in verified.message
    assert verified.rows == (("core.waveform_mean", algorithm, "computed"),)


def test_a_digest_that_disagrees_is_an_error(packet_root):
    root = external_array(packet_root, digest={"algorithm": "sha256", "value": "0" * 64})
    assert validate(open_packet(root), verification=Verification(external=True)).passed, "not read without checksums"
    report = validate(open_packet(root), verification=Verification(checksums=True, external=True))
    assert not report.passed
    assert "external.digest" in {f.check for f in report.findings}


def test_the_summary_names_what_it_compared(packet_root):
    """ "Resolved and checked" said nothing about which claims were actually tested."""
    report = validate(open_packet(external_array(packet_root)), verification=Verification(external=True))
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
    report = validate(open_packet(_with_members(external_array(packet_root))), verification=Verification(external=True))
    assert report.passed
    assert "1 members" in next(f for f in report.findings if f.check == "external.verified").message


def test_a_member_the_store_does_not_hold_is_an_error(packet_root):
    def add(entry):
        entry["members"].append({"key": "9.9", "size_bytes": 1})
        entry["size_bytes"] += 1  # so the entry stays self-consistent and only the store disagrees

    root = _with_members(external_array(packet_root), mutate=add)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed
    assert "external.members" in {f.check for f in report.findings}


def test_a_member_size_that_disagrees_is_caught_where_the_total_would_not(packet_root):
    """Two members changing in opposite directions leave `size_bytes` correct. Part 04 §5.4."""

    def swap(entry):
        entry["members"][0]["size_bytes"] += 10
        entry["members"][1]["size_bytes"] -= 10

    root = _with_members(external_array(packet_root), mutate=swap)
    report = validate(open_packet(root), verification=Verification(external=True))
    assert not report.passed, "the total still agrees, so only a per-member check sees this"
    assert "external.members" in {f.check for f in report.findings}


def test_store_digests_report_what_they_could_not_check(packet_root):
    """A local filesystem offers no content hash, so every member is skipped, not passed."""
    report = validate(
        open_packet(_with_members(external_array(packet_root))),
        verification=Verification(store_digests=True, external=True),
    )
    assert report.passed
    assert "external.no_store_digest" in {f.check for f in report.findings}
    assert "store_digest" not in next(f for f in report.findings if f.check == "external.verified").message


def test_a_store_digest_that_changed_in_place_is_an_error(packet_root, monkeypatch):
    """Neither the size nor a recorded digest need change for this to fire, and a multipart tag compares."""
    from escapewheel_validator import stores as module
    from escapewheel_validator.stores import Listing, Member, StoreDigest, listing

    def stamped(uri, **kwargs):
        found = listing(uri, **kwargs)
        return Listing(
            tuple(
                Member(m.key, m.size_bytes, StoreDigest("etag", f'"{index:032x}-2"'))
                for index, m in enumerate(found.members)
            ),
            found.size_bytes,
        )

    root = _with_members(external_array(packet_root))
    monkeypatch.setattr(module, "listing", stamped)
    passing = validate(
        open_packet(
            _with_members(
                root,
                mutate=lambda e: [
                    m.update(store_digest={"algorithm": "etag", "value": f'"{i:032x}-2"'})
                    for i, m in enumerate(e["members"])
                ],
            )
        ),
        verification=Verification(store_digests=True, external=True),
    )
    assert passing.passed
    assert "1 store_digest" in next(f for f in passing.findings if f.check == "external.verified").message

    changed = validate(
        open_packet(
            _with_members(
                root,
                mutate=lambda e: [
                    m.update(store_digest={"algorithm": "etag", "value": '"' + "f" * 32 + '"'}) for m in e["members"]
                ],
            )
        ),
        verification=Verification(store_digests=True, external=True),
    )
    assert not changed.passed
    assert "external.store_digest" in {f.check for f in changed.findings}


# -- Part 04 §§5.3, 5.4: located as a reader locates, and a redirected store digest is not compared --


def _stamped(monkeypatch):
    """Have the store report an entity tag per member, as an object store would."""
    from escapewheel_validator import stores as module
    from escapewheel_validator.stores import Listing, Member, StoreDigest, listing

    def stamped(uri, **kwargs):
        found = listing(uri, **kwargs)
        members = (Member(m.key, m.size_bytes, StoreDigest("etag", f'"{i:032x}"')) for i, m in enumerate(found.members))
        return Listing(tuple(members), found.size_bytes)

    monkeypatch.setattr(module, "listing", stamped)


def _recorded(root):
    """Record the tags `_stamped` reports, so a comparison that runs agrees."""

    def record(entry):
        for i, member in enumerate(entry["members"]):
            member["store_digest"] = {"algorithm": "etag", "value": f'"{i:032x}"'}

    return _with_members(root, mutate=record)


def _document(path, sources=None, mirrors=None):
    body = {"sources_standard_version": "escapewheel-sources-v0.2"}
    if sources is not None:
        body["sources"] = {name: {"uri": uri} for name, uri in sources.items()}
    if mirrors is not None:
        body["mirrors"] = {prefix: {"uri": uri} for prefix, uri in mirrors.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))
    return path


def _mirrored(packet_root, tmp_path):
    """Move the external array to a copy, and return a document mirroring its old place to the copy."""
    import shutil

    original = packet_root.parent / "external.zarr"
    copy = tmp_path / "copy"
    copy.mkdir()
    shutil.move(original, copy / "external.zarr")
    return _document(tmp_path / "machine.json", mirrors={original.parent.resolve().as_uri(): str(copy)})


def test_a_mirrored_resource_is_read_at_the_mirror_and_its_document_named(packet_root, tmp_path):
    root = _with_members(external_array(packet_root))
    machine = _mirrored(packet_root, tmp_path)
    report = validate(open_packet(root, sources=[machine]), verification=Verification(external=True))
    assert report.passed
    assert "external.unreachable" not in {f.check for f in report.findings}
    [located] = [f for f in report.findings if f.check == "external.located"]
    assert located.rows == (("core.waveform_mean", "", str(machine)),)


def test_verifying_without_reading_checks_no_member_of_a_mirrored_resource(packet_root, tmp_path, monkeypatch):
    root = _recorded(external_array(packet_root))
    machine = _mirrored(packet_root, tmp_path)
    _stamped(monkeypatch)
    report = validate(
        open_packet(root, sources=[machine]), verification=Verification(store_digests=True, external=True)
    )
    [unchecked] = [f for f in report.findings if f.check == "external.no_store_digest"]
    assert "redirected" in unchecked.message
    assert unchecked.counts["unchecked"] == unchecked.counts["declared"] == 2
    assert "store_digest" not in next(f for f in report.findings if f.check == "external.verified").message


@pytest.mark.parametrize("through", ["default", "configured"])
def test_store_digests_are_compared_only_for_a_source_the_default_resolves(packet_root, tmp_path, monkeypatch, through):
    root = _recorded(external_array(packet_root))
    manifest = json.loads((root / "packet.json").read_text())
    next(r for r in manifest["resources"] if r.get("external")).update(uri="external.zarr", source="raw")
    (root / "packet.json").write_text(json.dumps(manifest))

    located = {"raw": str(packet_root.parent.resolve())}
    if through == "default":
        _document(packet_root / "sources.json", located)
    else:
        monkeypatch.setenv("ESCAPEWHEEL_SOURCES", str(_document(tmp_path / "machine.json", located)))
    _stamped(monkeypatch)
    report = validate(open_packet(root), verification=Verification(store_digests=True, external=True))
    assert report.passed
    compared = "store_digest" in next(f for f in report.findings if f.check == "external.verified").message
    assert compared is (through == "default")
    assert ("external.no_store_digest" in {f.check for f in report.findings}) is (through == "configured")

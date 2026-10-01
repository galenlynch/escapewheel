"""`validate`'s verification modes, through the options object and the keywords it replaces."""

import pytest
from escapewheel_reader import open_packet

from escapewheel_validator import Verification, validate

from .test_validation import _external


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
    root = _external(packet_root)
    assert "external.verified" not in _checks(validate(open_packet(root)))
    assert "external.verified" in _checks(validate(open_packet(root), verification=Verification(checksums=True)))
    owned_only = validate(open_packet(root), verification=Verification(checksums=True, external=False))
    assert "owned.verified" in _checks(owned_only) and "external.verified" not in _checks(owned_only)


def test_the_separate_keywords_keep_their_meaning(packet_root):
    """`external` is off unless given, so `checksums` alone establishes packet-owned digests only."""
    root = _external(packet_root)
    by_keyword = validate(open_packet(root), checksums=True)
    by_object = validate(open_packet(root), verification=Verification(checksums=True, external=False))
    assert by_keyword.findings == by_object.findings
    assert "external.verified" in _checks(validate(open_packet(root), external=True))


def test_a_mode_keyword_beside_the_object_is_refused(packet_root):
    with pytest.raises(TypeError, match="verification or checksums"):
        validate(open_packet(packet_root), verification=Verification(), checksums=True)

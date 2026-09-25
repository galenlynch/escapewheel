"""A manifest `uri`'s two forms, and the one spelling of a relative reference (Part 03 §4)."""

import pytest

from escapewheel_reader.uri import canonical, decode, encode, in_one_form, is_absolute, representable


@pytest.mark.parametrize("uri", ["s3://bucket/key", "file:///data/x", "gs://b/o", "a+b.c-d://x"])
def test_a_scheme_followed_by_two_slashes_is_absolute(uri):
    assert is_absolute(uri)
    assert in_one_form(uri)


@pytest.mark.parametrize("uri", ["tables/core/units.parquet", "file:/data/x", "mailto:x", "/data/x", "1s3://x"])
def test_anything_else_is_not_absolute(uri):
    assert not is_absolute(uri)


@pytest.mark.parametrize("name", ["a", "QC report é.pdf", "12:00:00.png", "e\u0301", "A", "...", "\x7f", "a\nb"])
def test_a_representable_name_may_be_anything_but_the_five_exclusions(name):
    assert representable(name)


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "a\0b", "caf\udce9"])
def test_empty_dot_dotdot_slash_nul_and_non_utf8_are_not_representable(name):
    """Part 03 §11; `\\udce9` is what `os.fsdecode` makes of a byte that is not UTF-8."""
    assert not representable(name)


def test_encode_writes_unreserved_as_itself_and_every_other_octet_in_uppercase_hex():
    """Part 03 §4's one form, spelled out for the name the corpus carries."""
    assert encode(["opaque", "core.qc_report", "QC report é.pdf"]) == "opaque/core.qc_report/QC%20report%20%C3%A9.pdf"
    assert encode(["AZaz09-._~"]) == "AZaz09-._~"
    assert encode(["12:00:00.png"]) == "12%3A00%3A00.png"
    assert encode(["\U0001f600"]) == "%F0%9F%98%80"


@pytest.mark.parametrize("names", [[], ["a", ""], [".."], ["a/b"]])
def test_encode_refuses_what_no_relative_reference_can_name(names):
    with pytest.raises(ValueError):
        encode(names)


def test_decode_reads_any_spelling_rfc_3986_admits():
    assert decode("opaque/core.qc_report/QC%20report%20%C3%A9.pdf") == ("opaque", "core.qc_report", "QC report é.pdf")
    assert decode("videos/r%c3%a9sum%c3%a9.pdf") == ("videos", "résumé.pdf")
    assert decode("%41/b:c@d") == ("A", "b:c@d")


def test_decoding_keeps_normalization_distinct():
    """No normalization: NFC and NFD `é` are two names (Part 03 §11)."""
    assert decode("%C3%A9") != decode("e%CC%81")


@pytest.mark.parametrize(
    "reference",
    [
        "",
        "/data/x",
        "a//b",
        "a/",
        "cam 1.mp4",
        "a%2Fb.mp4",
        "../b.mp4",
        "a/./b",
        "a/%2E%2E/b",
        "%00",
        "%FF",
        "a%2",
        "c:/x",
        "s3://bucket/x",
        "a?b",
        "a#b",
    ],
)
def test_decode_refuses_what_is_not_a_relative_reference(reference):
    with pytest.raises(ValueError):
        decode(reference)


@pytest.mark.parametrize(
    ("uri", "passes"),
    [
        ("tables/core/units.parquet", True),
        ("opaque/core.qc_report/QC%20report%20%C3%A9.pdf", True),
        ("opaque/core.clip/cam 1.mp4", False),  # a raw space
        ("opaque/core.clip/r%c3%a9sum%c3%a9.pdf", False),  # lowercase hexadecimal digits
        ("opaque/core.clip/%41.mp4", False),  # an encoded unreserved character
        ("opaque/core.clip/../core.clip/clip.mp4", False),  # a `..` segment
        ("opaque/core.clip/12:00.png", False),  # `:` is reserved, so the one form encodes it
        ("opaque/core.clip/é.png", False),  # a raw non-ASCII character
        ("s3://bucket/QC report.pdf", True),  # an absolute URI is not this rule's business
    ],
)
def test_in_one_form_is_the_uri_form_check(uri, passes):
    """Part 03 §4 and Part 04 §10's `packet.resource.uri_form`."""
    assert in_one_form(uri) is passes


def test_canonical_rewrites_a_reference_into_the_one_form():
    assert canonical("videos/r%c3%a9sum%c3%a9.pdf") == "videos/r%C3%A9sum%C3%A9.pdf"
    assert canonical("%41/12:00.png") == "A/12%3A00.png"
    with pytest.raises(ValueError):
        canonical("videos/cam 1.mp4")

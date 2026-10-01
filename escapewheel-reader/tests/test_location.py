"""A packet root may be a store prefix, and a declared URI may be redirected."""

from pathlib import Path

import pytest

from escapewheel_reader import Location, ResourceUnreadableError


def test_a_local_root_resolves_a_relative_uri_under_itself():
    """What made a packet portable in the first place, stated once."""
    assert Location.of("/data/packet").resolve("tables/core/units.parquet") == Location(
        "/data/packet/tables/core/units.parquet"
    )


def test_a_store_root_resolves_the_same_uri_in_the_store():
    """The same manifest, unchanged, reaching a bucket instead of a disk."""
    where = Location.of("s3://bucket/prefix/").resolve("tables/core/units.parquet")
    assert where.uri == "s3://bucket/prefix/tables/core/units.parquet"
    assert not where.is_local


def test_a_file_uri_is_a_local_path_and_a_store_uri_is_not():
    """`file:` is a spelling of a path; anything longer than one letter is a store."""
    assert Location.of("file:///data/packet").is_local
    assert Location.of("/data/packet").is_local
    assert not Location.of("s3://bucket/prefix").is_local
    # A single-letter scheme is a Windows drive rather than a URI.
    assert Location.of("C:/data/packet").is_local


def test_a_store_location_has_no_path():
    """A caller reaching for `path` on a bucket is told where to go instead."""
    with pytest.raises(ResourceUnreadableError, match="no local path"):
        _ = Location.of("s3://bucket/prefix").path


def test_a_rewrite_redirects_an_absolute_uri():
    """Part 04 §5.1 makes reachability the caller's situation; this is how the caller says so."""
    root = Location.of("/data/packet", {"file:///mnt/Data/ephys/": "s3://bucket/ephys/"})
    assert root.resolve("file:///mnt/Data/ephys/session.nwb/lfp").uri == "s3://bucket/ephys/session.nwb/lfp"


def test_the_longest_matching_prefix_wins():
    """So a specific redirect may sit inside a general one without being shadowed."""
    root = Location.of(
        "/data/packet",
        {"file:///mnt/": "s3://everything/", "file:///mnt/Data/ephys/": "s3://just-ephys/"},
    )
    assert root.resolve("file:///mnt/Data/ephys/x").uri == "s3://just-ephys/x"
    assert root.resolve("file:///mnt/other/x").uri == "s3://everything/other/x"


def test_a_rewrite_that_matches_nothing_changes_nothing():
    """A redirect is not a requirement; a URI it does not name resolves as before."""
    root = Location.of("/data/packet", {"s3://elsewhere/": "s3://here/"})
    assert root.resolve("tables/core/units.parquet").path == Path("/data/packet/tables/core/units.parquet")


def test_a_relative_uri_is_rewritten_too(tmp_path):
    """Substitution precedes resolution, so a packet-owned resource can be redirected as well."""
    root = Location.of(tmp_path, {"tables/": "s3://mirror/tables/"})
    assert root.resolve("tables/core/units.parquet").uri == "s3://mirror/tables/core/units.parquet"


def test_a_rewrite_survives_joining(tmp_path):
    """The rules travel with the root, so a resource handle needs nothing else passed to it."""
    root = Location.of(tmp_path, {"a": "b"})
    assert root.join("schemas").rewrite == root.rewrite


def test_a_local_location_reads_its_own_bytes(tmp_path):
    """The one path both stores share, so a manifest is read the same way in each."""
    (tmp_path / "thing.json").write_text('{"a": 1}')
    assert Location.of(tmp_path).join("thing.json").read_bytes() == b'{"a": 1}'
    assert Location.of(tmp_path).join("thing.json").exists()
    assert not Location.of(tmp_path).join("absent.json").exists()


def test_a_source_resolves_through_a_document(tmp_path):
    """Part 04 §5.5: the entry names a body of data, the document says where that is."""
    root = Location.of(tmp_path, sources={"raw_nwb": "s3://bucket/session.nwb"})
    where = root.resolve("processing/ecephys/LFP/data", "raw_nwb")
    assert where.uri == "s3://bucket/session.nwb/processing/ecephys/LFP/data"


def test_a_source_no_document_locates_is_refused(tmp_path):
    """Part 04 §5.5: a fact about the reader's situation, raised where the bytes are asked for."""
    from escapewheel_reader import UnresolvedSource

    with pytest.raises(UnresolvedSource) as refused:
        Location.of(tmp_path).resolve("processing/data", "raw_nwb")
    assert refused.value.source == "raw_nwb"


def test_an_entry_naming_no_source_is_unchanged(tmp_path):
    """Part 04 §5.5: silence keeps today's meaning, so every existing packet still resolves."""
    root = Location.of(tmp_path, sources={"raw_nwb": "s3://bucket/x"})
    assert root.resolve("tables/core/units.parquet").path == Path(tmp_path) / "tables/core/units.parquet"


# -- a relative reference is decoded and its names appended (Part 03 §4) ------------------------


def test_a_relative_reference_is_decoded_before_it_is_appended():
    where = Location.of("/data/packet").resolve("opaque/core.qc_report/QC%20report%20%C3%A9.pdf")
    assert where.path == Path("/data/packet/opaque/core.qc_report/QC report é.pdf")


def test_a_store_root_takes_the_decoded_names_as_key_segments(monkeypatch):
    """Object-key segments, not a URI: a `?` or `#` a name holds stays in the key."""
    from escapewheel_reader import location

    monkeypatch.setattr(location, "_filesystem", lambda store: (store, ""))
    where = Location.of("s3://bucket/prefix").resolve("opaque/core.x/a%3Fb%23c%20%C3%A9.png")
    assert where.uri == "s3://bucket/prefix/opaque/core.x/a?b#c é.png"
    assert where.store() == ("bucket/prefix/opaque/core.x/a?b#c é.png", "s3://bucket")


def test_a_source_relative_reference_is_decoded_too():
    """Part 04 §5.5: appended to the source's location, so its last segment is kept."""
    root = Location.of("/data/packet", sources={"raw": "s3://bucket/session.nwb"})
    assert root.resolve("videos/cam%201.mp4", "raw").uri == "s3://bucket/session.nwb/videos/cam 1.mp4"


def test_lowercase_hex_resolves_where_uppercase_does():
    """A reader decodes any spelling; only a checker insists on one (Part 03 §4)."""
    root = Location.of("/data/packet")
    assert root.resolve("r%c3%a9sum%c3%a9.pdf") == root.resolve("r%C3%A9sum%C3%A9.pdf")


@pytest.mark.parametrize("declared", ["/mnt/elsewhere/x.parquet", "../x.parquet", "a//b", "cam 1.mp4", "a%2Fb"])
def test_a_uri_neither_absolute_nor_a_relative_reference_is_unreadable(declared):
    """A leading `/` or a `..` segment would reach outside the root, so it resolves nowhere."""
    with pytest.raises(ResourceUnreadableError, match="neither absolute nor a relative reference"):
        Location.of("/data/packet").resolve(declared)


def test_a_substituted_uri_is_taken_as_the_caller_wrote_it():
    """A rewrite is the caller's location, not the packet's reference, so it is not decoded."""
    root = Location.of("/data/packet", {"s3://old/": "/mnt/mirror dir/"})
    assert root.resolve("s3://old/a%20b").uri == "/mnt/mirror dir/a%20b"

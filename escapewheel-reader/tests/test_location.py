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
    """`04` §5.1 makes reachability the caller's situation; this is how the caller says so."""
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
    """R80 §2.1: the entry names a body of data, the document says where that is."""
    root = Location.of(tmp_path, sources={"raw_nwb": "s3://bucket/session.nwb"})
    where = root.resolve("processing/ecephys/LFP/data", "raw_nwb")
    assert where.uri == "s3://bucket/session.nwb/processing/ecephys/LFP/data"


def test_a_source_no_document_locates_is_refused(tmp_path):
    """`04` §5.5: a fact about the reader's situation, raised where the bytes are asked for."""
    from escapewheel_reader import UnresolvedSource

    with pytest.raises(UnresolvedSource, match="raw_nwb"):
        Location.of(tmp_path).resolve("processing/data", "raw_nwb")


def test_an_entry_naming_no_source_is_unchanged(tmp_path):
    """R80 §2.1: silence keeps today's meaning, so every existing packet still resolves."""
    root = Location.of(tmp_path, sources={"raw_nwb": "s3://bucket/x"})
    assert root.resolve("tables/core/units.parquet").path == Path(tmp_path) / "tables/core/units.parquet"

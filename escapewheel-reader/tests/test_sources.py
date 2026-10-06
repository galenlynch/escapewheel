"""Ranking resolution documents and applying their mirrors (Part 04 §5.5, §5.5.1, §5.5.2)."""

import json

import pytest

from escapewheel_reader import Location, Resolution, SourcesDocument, SourcesError, UnresolvedSource, open_packet
from escapewheel_reader import location as location_module
from escapewheel_reader.location import check_sources, resolve_sources


def _document(path, sources=None, mirrors=None, version="escapewheel-sources-v0.2"):
    body = {"sources_standard_version": version}
    if sources is not None:
        body["sources"] = {name: {"uri": uri} for name, uri in sources.items()}
    if mirrors is not None:
        body["mirrors"] = {prefix: {"uri": uri} for prefix, uri in mirrors.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body))
    return path


def _ranked(root, *documents):
    return Location.of(root, Resolution(tuple(documents)))


def _mirrors(where, base=None, **_):
    return lambda mirrors: SourcesDocument.of(where, base, mirrors=mirrors)


# -- ranking --------------------------------------------------------------------------------------


def test_a_configured_copy_outranks_the_default_and_a_caller_outranks_both(packet_root, tmp_path):
    _document(packet_root / "sources.json", {"raw": "s3://bucket/raw"})
    configured = _document(tmp_path / "machine.json", {"raw": "/mnt/copy/raw"})
    root = Location.of(packet_root)
    assert Location.of(root, resolve_sources(root, configured=[str(configured)])).resolve("x", "raw").uri == (
        "/mnt/copy/raw/x"
    )
    caller = _document(tmp_path / "caller.json", {"raw": "/scratch/raw"})
    ranked = resolve_sources(root, [caller], configured=[str(configured)])
    assert Location.of(root, ranked).resolve("x", "raw").uri == "/scratch/raw/x"


def test_the_environment_and_the_user_file_configure_documents(packet_root, tmp_path, monkeypatch):
    listed = _document(tmp_path / "listed.json", {"raw": "/listed/raw"})
    user = _document(tmp_path / "config" / "escapewheel" / "sources.json", {"raw": "/user/raw", "more": "/user/more"})
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("ESCAPEWHEEL_SOURCES", str(listed))
    packet = open_packet(packet_root)
    assert [d.where for d in packet.resolution.documents] == [str(listed), str(user)]
    assert packet.location.resolve("x", "raw").uri == "/listed/raw/x"
    assert packet.location.resolve("x", "more").uri == "/user/more/x"


def test_a_document_above_the_packet_root_is_not_read(tmp_path):
    root = tmp_path / "bundle" / "packet"
    root.mkdir(parents=True)
    _document(tmp_path / "bundle" / "sources.json", {"raw": "/above/raw"})
    ranked = resolve_sources(Location.of(root), configured=[])
    assert ranked.documents == ()


def test_a_configured_pattern_names_no_document(tmp_path):
    _document(tmp_path / "a.json", {"raw": "/a"})
    ranked = resolve_sources(Location.of(tmp_path / "packet"), configured=[str(tmp_path / "*.json")])
    assert ranked.documents == ()


@pytest.mark.parametrize(
    "body",
    ['{"sources_standard_version": "escapewheel-sources-v9", "sources": {}}', "{not json"],
    ids=["unknown-version", "unparsable"],
)
def test_an_unusable_configured_document_is_reported_and_the_next_place_tried(packet_root, tmp_path, body):
    (tmp_path / "bad.json").write_text(body)
    _document(packet_root / "sources.json", {"raw": "s3://bucket/raw"})
    ranked = resolve_sources(Location.of(packet_root), configured=[str(tmp_path / "bad.json")])
    assert [where for where, _ in ranked.unused] == [str(tmp_path / "bad.json")]
    assert Location.of(packet_root, ranked).resolve("x", "raw").uri == "s3://bucket/raw/x"


def test_a_caller_document_that_is_absent_is_refused(packet_root, tmp_path):
    with pytest.raises(SourcesError, match="no source resolution document"):
        open_packet(packet_root, sources=[tmp_path / "absent.json"])


# -- mirrors --------------------------------------------------------------------------------------


def test_a_mirror_only_document_redirects_absolute_and_default_resolved_locations(packet_root, tmp_path):
    _document(packet_root / "sources.json", {"raw": "s3://bucket/raw"})
    machine = _document(tmp_path / "machine.json", mirrors={"s3://bucket/": "/mnt/bucket/"})
    root = Location.of(packet_root)
    ranked = Location.of(root, resolve_sources(root, configured=[str(machine)]))
    via_source = ranked.locate("x.nwb", "raw")
    assert via_source.location.uri == "/mnt/bucket/raw/x.nwb"
    assert (via_source.source_document, via_source.mirror_document) == (str(packet_root / "sources.json"), str(machine))
    assert ranked.resolve("s3://bucket/y").uri == "/mnt/bucket/y"
    assert ranked.resolve("s3://other/y").uri == "s3://other/y"


def test_the_longest_prefix_in_the_first_document_applies_once():
    first = SourcesDocument.of("first", mirrors={"s3://b/": "s3://general/", "s3://b/a/": "s3://specific/"})
    second = SourcesDocument.of("second", mirrors={"s3://b/a/x/": "s3://lower/"})
    again = SourcesDocument.of("again", mirrors={"s3://specific/": "s3://twice/"})
    root = _ranked("/p", first, second, again)
    located = root.locate("s3://b/a/x/y")
    assert located.location.uri == "s3://specific/x/y"
    assert located.mirror_document == "first"


def test_names_are_compared_decoded_and_whole():
    mirror = SourcesDocument.of("m", mirrors={"S3://bucket/a%2a": "s3://copy"})
    root = _ranked("/p", mirror)
    assert root.resolve("s3://bucket/a%2A/x").uri == "s3://copy/x"
    partial = _ranked("/p", SourcesDocument.of("m", mirrors={"s3://bucket/a": "s3://copy"}))
    assert partial.resolve("s3://bucket/ab/x").uri == "s3://bucket/ab/x"


@pytest.mark.parametrize(
    "prefixes", [("s3://bucket/a/", "s3://bucket/a"), ("/allen/", "file:///allen/")], ids=["slash", "file"]
)
def test_a_document_with_equal_prefixes_is_not_used(tmp_path, prefixes):
    doc = _document(tmp_path / "equal.json", mirrors={p: "/copy" for p in prefixes})
    ranked = resolve_sources(Location.of(tmp_path / "packet"), configured=[str(doc)])
    assert ranked.documents == ()
    assert "equal mirror prefixes" in ranked.unused[0][1]


@pytest.mark.parametrize(
    ("prefix", "location"),
    [
        ("/allen/programs/", "file:///allen/programs/x"),
        ("d:\\data", "file:///D:/data/x"),
        ("\\\\server\\share", "file://SERVER/share/x"),
    ],
    ids=["posix", "drive", "unc"],
)
def test_a_file_uri_is_compared_as_the_path_it_names(prefix, location):
    root = _ranked("/p", SourcesDocument.of("m", mirrors={prefix: "s3://copy/"}))
    assert root.resolve(location).uri == "s3://copy/x"


@pytest.mark.parametrize("path", ["\\\\?\\D:\\data", "\\\\.\\pipe\\x"], ids=["verbatim", "device"])
def test_a_device_path_names_no_location(path):
    assert location_module._key(path) is None
    assert SourcesDocument.of("m", Location.of("/bundle")).place(path) == (None, None)


def test_a_bundle_mirror_with_an_empty_uri_is_the_bundle_folder(packet_root, tmp_path):
    bundle = _document(tmp_path / "bundle" / "sources.json", mirrors={"s3://bucket/": ""})
    packet = open_packet(packet_root, sources=[bundle])
    assert packet.location.resolve("s3://bucket/session/x.nwb").uri == str(tmp_path / "bundle" / "session" / "x.nwb")


def test_a_bundle_mirrors_one_asset_and_another_falls_to_the_configured_mirror(packet_root, tmp_path):
    bundle = _document(tmp_path / "bundle" / "sources.json", mirrors={"s3://bucket/held/": "copies/held"})
    machine = _document(tmp_path / "machine.json", mirrors={"s3://bucket/": "/mnt/bucket"})
    root = Location.of(packet_root)
    ranked = Location.of(root, resolve_sources(root, [bundle], configured=[str(machine)]))
    assert ranked.resolve("s3://bucket/held/x").uri == str(tmp_path / "bundle" / "copies" / "held" / "x")
    assert ranked.resolve("s3://bucket/other/x").uri == "/mnt/bucket/other/x"


@pytest.mark.parametrize("uri", ["copies/raw", "D:\\copies\\raw"], ids=["unstored", "other-platform"])
def test_an_unusable_mirror_is_passed_over_and_reported(uri):
    unusable = SourcesDocument.of("caller", None, mirrors={"s3://bucket/": uri})
    usable = SourcesDocument.of("next", mirrors={"s3://bucket/": "/mnt/bucket"})
    located = _ranked("/p", unusable, usable).locate("s3://bucket/x")
    assert located.location.uri == "/mnt/bucket/x"
    assert located.unusable == (("caller", "s3://bucket/"),)
    assert located.mirror_document == "next"


def test_a_relative_source_in_a_document_stored_nowhere_is_unresolved():
    root = _ranked("/p", SourcesDocument.of("caller", None, sources={"raw": "copies/raw"}))
    with pytest.raises(UnresolvedSource, match="names no location"):
        root.resolve("x", "raw")


def test_a_relative_source_resolves_against_its_document(packet_root, tmp_path):
    doc = _document(tmp_path / "bundle" / "sources.json", {"raw": "copies/raw%20data"})
    packet = open_packet(packet_root, sources=[doc])
    assert packet.location.resolve("x", "raw").uri == str(tmp_path / "bundle" / "copies" / "raw data" / "x")


def test_a_mirror_to_a_missing_directory_does_not_fall_back(tmp_path):
    original = tmp_path / "original"
    original.mkdir()
    (original / "x").write_text("bytes")
    root = _ranked(tmp_path, SourcesDocument.of("m", mirrors={str(original): str(tmp_path / "missing")}))
    where = root.resolve(original.as_uri() + "/x")
    assert where.uri == str(tmp_path / "missing" / "x")
    with pytest.raises(FileNotFoundError):
        where.read_bytes()


# -- Windows paths --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "uri", ["D:\\data\\raw", "D:/data/raw", "\\\\server\\share\\raw"], ids=["backslash", "slash", "unc"]
)
def test_a_windows_location_satisfies_v0_2_only(uri):
    for version, valid in (("escapewheel-sources-v0.2", True), ("escapewheel-sources-v0.1", False)):
        document = {"sources_standard_version": version, "sources": {"raw": {"uri": uri}}}
        assert (check_sources(document) == ()) is valid


def test_a_windows_location_names_none_elsewhere(monkeypatch):
    monkeypatch.setattr(location_module, "_WINDOWS", False)
    root = _ranked("/p", SourcesDocument.of("m", sources={"raw": "D:\\data\\raw"}))
    with pytest.raises(UnresolvedSource, match="names no location"):
        root.resolve("x", "raw")


@pytest.mark.parametrize("uri", ["D:\\data\\raw", "D:/data/raw"], ids=["backslash", "slash"])
def test_a_windows_reader_resolves_either_separator(monkeypatch, uri):
    monkeypatch.setattr(location_module, "_WINDOWS", True)
    root = _ranked("/p", SourcesDocument.of("m", sources={"raw": uri}))
    assert root.locate("x", "raw").location.uri.replace("\\", "/") == "D:/data/raw/x"


def test_a_linux_entry_reaches_a_windows_reader_through_a_unc_mirror(monkeypatch):
    monkeypatch.setattr(location_module, "_WINDOWS", True)
    root = _ranked("/p", SourcesDocument.of("m", mirrors={"/allen/programs/": "\\\\allen\\programs"}))
    assert root.resolve("file:///allen/programs/x").uri.replace("/", "\\") == "\\\\allen\\programs\\x"


# -- versions -------------------------------------------------------------------------------------


def test_a_v0_1_document_resolves_and_cannot_state_v0_2_forms(packet_root, tmp_path):
    doc = _document(tmp_path / "old.json", {"raw": "s3://bucket/raw"}, version="escapewheel-sources-v0.1")
    assert open_packet(packet_root, sources=[doc]).location.resolve("x", "raw").uri == "s3://bucket/raw/x"
    for body in (
        {"sources": {"raw": {"uri": "copies/raw"}}},
        {"sources": {}, "mirrors": {"s3://bucket/": {"uri": "/mnt"}}},
    ):
        assert check_sources({"sources_standard_version": "escapewheel-sources-v0.1", **body})

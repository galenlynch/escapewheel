import json

import pytest

from escapewheel_reader import (
    ManifestError,
    ResourceNotFoundError,
    ResourceUnreadableError,
    UnsupportedCodecError,
    open_packet,
)

from .conftest import SESSION_NAME, SUBJECT


def test_success_criterion(packet_root):
    """07's Phase 1 success criterion, verbatim."""
    pkt = open_packet(packet_root)
    assert pkt.table("core.intervals").num_rows == 2
    query = "SELECT COUNT(*) FROM core_intervals"
    assert pkt.duckdb(for_query=query).sql(query).fetchone() == (2,)


def test_resource_listing_and_filtering(packet_root):
    pkt = open_packet(packet_root)
    assert len(pkt.resources()) == 6
    assert len(pkt.resources(layer="core")) == 6
    assert len(pkt.resources(layer="analysis")) == 0
    assert len(pkt.resources(kind="table")) == 6
    assert all(r.is_table for r in pkt.resources())


def test_resource_facts_are_resolved_from_the_registry(packet_root):
    resource = open_packet(packet_root).resource("core.sessions")
    assert resource.declaration_id == "core.sessions"
    assert resource.content_class == "core"
    assert resource.kind == "table"
    assert resource.canonical is True
    assert resource.instances == {"mode": "singleton", "presence": "required"}


def test_manifest_rejects_legacy_logical_classification(packet_root):
    path = packet_root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["resources"][0]["kind"] = "table"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ManifestError, match="does not conform"):
        open_packet(packet_root)


def test_resources_resolve_through_the_manifest(packet_root, tmp_path):
    """A relocated file stays readable because the manifest, not convention, locates it."""
    moved = packet_root / "elsewhere"
    moved.mkdir()
    (packet_root / "tables" / "core" / "intervals.parquet").rename(moved / "t.parquet")
    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    entry["resources"][1]["uri"] = "elsewhere/t.parquet"
    path.write_text(json.dumps(entry))

    assert open_packet(packet_root).table("core.intervals").num_rows == 2


def test_unknown_resource_names_what_is_available(packet_root):
    pkt = open_packet(packet_root)
    with pytest.raises(ResourceNotFoundError, match="core.intervals"):
        pkt.resource("core.probes")


def test_declared_but_absent_resource(packet_root):
    (packet_root / "tables" / "core" / "intervals.parquet").unlink()
    with pytest.raises(ResourceUnreadableError, match="does not resolve"):
        open_packet(packet_root).path("core.intervals")


def test_duckdb_skips_unreadable_resources(packet_root):
    """One missing file must not prevent the rest of the packet being queried."""
    (packet_root / "tables" / "core" / "intervals.parquet").unlink()
    con = open_packet(packet_root).duckdb(tables="all")
    assert con.sql("SELECT COUNT(*) FROM core_sessions").fetchone() == (1,)


def test_sql_across_resources(packet_root):
    pkt = open_packet(packet_root)
    result = pkt.sql(
        "SELECT s.subject_id, COUNT(*) AS n "
        "FROM core_intervals t JOIN core_sessions s USING (session_id) "
        "GROUP BY s.subject_id"
    )
    assert result.to_pydict() == {"subject_id": [SUBJECT], "n": [2]}


def test_embedded_registry_is_exposed(packet_root):
    registry = open_packet(packet_root).registry
    assert registry["registry_version"] == "0.1.0"
    assert {
        name
        for name, declaration in registry["resources"].items()
        if declaration["kind"] == "table" and name.startswith("core.")
    } == {
        "core.sessions",
        "core.clocks",
        "core.processing_runs",
        "core.intervals",
        "core.units",
        "core.event_streams",
        "core.events",
        "core.spike_events",
    }


def test_registry_is_optional(packet_root):
    (packet_root / "schemas" / "logical_schemas.json").unlink()
    assert open_packet(packet_root).registry is None


def _with_array(packet_root, codecs, profile=None):
    """Add an external array resource declaring `codecs`."""
    import json

    path = packet_root / "packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "core.probe0_ap",
            "declaration_id": "core.test_arrays",
            "uri": "s3://example/probe0.zarr",
            "external": True,
            "codecs": codecs,
            **({"physical_profile": profile} if profile else {}),
        }
    )
    entry["required_codecs"] = codecs
    path.write_text(json.dumps(entry))
    registry_path = packet_root / "schemas" / "logical_schemas.json"
    registry = json.loads(registry_path.read_text())
    registry["resources"]["core.test_arrays"] = {
        "content_class": "core",
        "kind": "dense_array",
        "instances": {"mode": "family"},
        "requires": [],
        "lineage": "optional",
        "producing_run": "optional",
        "array": {"axes_resource": "core.intervals"},
    }
    registry_path.write_text(json.dumps(registry, indent=2))
    return open_packet(packet_root)


def test_codec_check_passes_on_the_baseline(packet_root):
    _with_array(packet_root, ["zstd"]).check_codecs("core.probe0_ap")


def test_codec_check_names_what_is_missing(packet_root):
    pkt = _with_array(packet_root, ["wavpack"])
    with pytest.raises(UnsupportedCodecError, match="wavpack"):
        pkt.check_codecs("core.probe0_ap")


def test_a_missing_codec_disqualifies_only_that_resource(packet_root):
    """Part 03 §6.4: a reader must not refuse a packet over a codec it will never need."""
    pkt = _with_array(packet_root, ["wavpack"])
    assert pkt.unopenable() == {"core.probe0_ap": ("wavpack",)}
    assert pkt.table("core.intervals").num_rows == 2  # tables stay readable
    pkt.check_codecs("core.intervals")  # and declare no codecs at all


def test_unopenable_is_empty_when_everything_reads(packet_root):
    assert _with_array(packet_root, ["gzip"]).unopenable() == {}


def test_the_floor_is_read_for_the_version_the_resource_declares(packet_root):
    """Part 03 §6.4 states the floor per Zarr version, and `blosc` is in v2's.

    A single set is the v3 row applied to both, which refuses a conforming v2 array the reader
    can in fact open -- and Part 03 §6.1 asks for the pair precisely because readability differs
    between the versions.
    """
    pkt = _with_array(packet_root, ["blosc"], profile="zarr_v2")
    pkt.check_codecs("core.probe0_ap")
    assert pkt.unopenable() == {}


def test_an_unsupported_codec_names_the_version_it_was_judged_against(packet_root):
    pkt = _with_array(packet_root, ["wavpack"], profile="zarr_v2")
    with pytest.raises(UnsupportedCodecError, match="zarr_v2 codecs"):
        pkt.check_codecs("core.probe0_ap")


def test_sessions_and_repr(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.sessions == (SESSION_NAME,)
    assert "session_001" in repr(pkt)
    assert pkt.root == packet_root


def _views(connection):
    """The views this packet registered, without DuckDB's own catalog views."""
    return {r[0] for r in connection.sql("SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()}


def test_duckdb_registers_nothing_until_asked(packet_root):
    """Binding a view reads a footer, which over a store is a round trip per table."""
    con = open_packet(packet_root).duckdb()
    assert _views(con) == set()


def test_a_query_registers_only_the_tables_it_names(packet_root):
    """So asking about one table does not pay for the packet's other twenty-seven."""
    packet = open_packet(packet_root)
    con = packet.duckdb(for_query="SELECT count(*) FROM core_intervals")
    assert _views(con) == {"core_intervals"}


def test_registering_twice_is_not_two_reads(packet_root):
    """A second query naming the same table finds it registered rather than re-binding it."""
    packet = open_packet(packet_root)
    con = packet.duckdb(for_query="SELECT count(*) FROM core_intervals")
    join = "SELECT count(*) FROM core_intervals JOIN core_sessions USING (session_id)"
    packet.duckdb(connection=con, for_query=join)
    assert _views(con) == {"core_intervals", "core_sessions"}


def test_a_packet_in_a_store_resolves_its_tables_there(packet_root):
    """The same manifest, unchanged, addressing a bucket instead of a directory."""
    import pytest

    from escapewheel_reader import Manifest, Packet, ResourceUnreadableError

    packet = Packet("s3://bucket/prefix", Manifest.load(packet_root))
    handle = packet.table_resource("core.intervals")
    assert not handle.is_local
    assert handle.location.uri == "s3://bucket/prefix/tables/core/intervals.parquet"
    with pytest.raises(ResourceUnreadableError, match="no local path"):
        _ = packet.root


def test_a_rewrite_reaches_bytes_the_manifest_names_elsewhere(packet_root, tmp_path):
    """Part 04 §5.1 makes reachability the reader's situation, and a committed packet records the
    writer's -- so a caller redirects rather than editing bytes Part 04 §5.1 makes immutable."""
    import json
    import shutil

    moved = tmp_path / "moved"
    moved.mkdir()
    shutil.copy(packet_root / "tables" / "core" / "intervals.parquet", moved / "intervals.parquet")
    manifest_path = packet_root / "packet.json"
    entry = json.loads(manifest_path.read_text())
    for resource in entry["resources"]:
        if resource["resource_id"] == "core.intervals":
            resource["uri"] = "file:///gone/intervals.parquet"
            resource["external"] = True
    manifest_path.write_text(json.dumps(entry))

    packet = open_packet(packet_root, rewrite={"file:///gone/": f"{moved}/"})
    assert packet.table("core.intervals").num_rows == 2


def test_the_packet_roots_default_document_is_read(packet_root):
    """Part 04 §5.5: under the root so a copy carries it, outside the manifest so it may be edited."""
    import json

    (packet_root / "sources.json").write_text(
        json.dumps(
            {"sources_standard_version": "escapewheel-sources-v0.1", "sources": {"raw": {"uri": "s3://bucket/raw"}}}
        )
    )
    packet = open_packet(packet_root)
    assert dict(packet.location.sources) == {"raw": "s3://bucket/raw"}


def test_a_caller_document_wins_over_the_packets_own(packet_root):
    """Part 04 §5.5's order: the caller's first, so a mirror is named without editing the packet."""
    import json

    (packet_root / "sources.json").write_text(
        json.dumps(
            {"sources_standard_version": "escapewheel-sources-v0.1", "sources": {"raw": {"uri": "s3://stale/raw"}}}
        )
    )
    packet = open_packet(packet_root, sources=[{"raw": "/scratch/staged"}])
    assert dict(packet.location.sources)["raw"] == "/scratch/staged"


def test_a_document_of_an_unknown_version_is_refused(packet_root, tmp_path):
    """Part 04 §5.5: reading it as if it were this version is how a location silently goes wrong."""
    import json

    import pytest

    from escapewheel_reader import ManifestError

    doc = tmp_path / "future.json"
    doc.write_text(json.dumps({"sources_standard_version": "escapewheel-sources-v9", "sources": {}}))
    with pytest.raises(ManifestError, match="escapewheel-sources-v0.1"):
        open_packet(packet_root, sources=[doc])

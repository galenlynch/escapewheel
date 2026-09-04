import pytest

from nwb_lake_reader import (
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
    assert pkt.duckdb().sql("SELECT COUNT(*) FROM core_intervals").fetchone() == (2,)


def test_resource_listing_and_filtering(packet_root):
    pkt = open_packet(packet_root)
    assert len(pkt.resources()) == 5
    assert len(pkt.resources(layer="core")) == 5
    assert len(pkt.resources(layer="analysis")) == 0
    assert len(pkt.resources(kind="table")) == 5
    assert all(r.is_table for r in pkt.resources())


def test_resources_resolve_through_the_manifest(packet_root, tmp_path):
    """A relocated file stays readable because the manifest, not convention, locates it."""
    import json

    moved = packet_root / "elsewhere"
    moved.mkdir()
    (packet_root / "tables" / "core" / "intervals.parquet").rename(moved / "t.parquet")
    path = packet_root / "nwb.packet.json"
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
    con = open_packet(packet_root).duckdb()
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
    assert set(registry["tables"]) == {
        "core.sessions",
        "core.intervals",
        "core.units",
        "core.events",
        "core.spike_events",
    }


def test_registry_is_optional(packet_root):
    (packet_root / "schemas" / "logical_schemas.json").unlink()
    assert open_packet(packet_root).registry is None


def _with_array(packet_root, codecs):
    """Add an external array resource declaring `codecs`."""
    import json

    path = packet_root / "nwb.packet.json"
    entry = json.loads(path.read_text())
    entry["resources"].append(
        {
            "resource_id": "array.probe0_ap",
            "layer": "core",
            "kind": "dense_array_asset",
            "uri": "s3://example/probe0.zarr",
            "external": True,
            "codecs": codecs,
        }
    )
    entry["required_codecs"] = codecs
    path.write_text(json.dumps(entry))
    return open_packet(packet_root)


def test_codec_check_passes_on_the_baseline(packet_root):
    _with_array(packet_root, ["zstd"]).check_codecs("array.probe0_ap")


def test_codec_check_names_what_is_missing(packet_root):
    pkt = _with_array(packet_root, ["wavpack"])
    with pytest.raises(UnsupportedCodecError, match="wavpack"):
        pkt.check_codecs("array.probe0_ap")


def test_a_missing_codec_disqualifies_only_that_resource(packet_root):
    """R15 §2: a reader must not refuse a packet over a codec it will never need."""
    pkt = _with_array(packet_root, ["wavpack"])
    assert pkt.unopenable() == {"array.probe0_ap": ("wavpack",)}
    assert pkt.table("core.intervals").num_rows == 2  # tables stay readable
    pkt.check_codecs("core.intervals")  # and declare no codecs at all


def test_unopenable_is_empty_when_everything_reads(packet_root):
    assert _with_array(packet_root, ["gzip"]).unopenable() == {}


def test_sessions_and_repr(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.sessions == (SESSION_NAME,)
    assert "session_001" in repr(pkt)
    assert pkt.root == packet_root

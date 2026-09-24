import pytest

from escapewheel_reader import ResourceNotFoundError, ResourceUnreadableError, open_packet

from .conftest import TRIALS, install_registry, read_registry


def test_handle_reads_and_describes(packet_root):
    handle = open_packet(packet_root).table_resource("core.intervals")
    assert handle.resource_id == "core.intervals"
    assert handle.sql_name == "core_intervals"
    assert handle.to_arrow().num_rows == 2
    assert "core.intervals" in repr(handle)


def test_schema_without_reading_data(packet_root):
    schema = open_packet(packet_root).table_resource("core.intervals").schema()
    assert schema.names == ["session_id", "interval_kind", "interval_id", "start_tick", "stop_tick", "clock_id"]
    assert str(schema.field("start_tick").type) == "int64"


def test_dataset_is_lazy_and_filterable(packet_root):
    import pyarrow.dataset as pads

    dataset = open_packet(packet_root).table_resource("core.intervals").dataset()
    filtered = dataset.to_table(filter=pads.field("interval_id") == TRIALS[1])
    assert filtered.num_rows == 1


def test_register_returns_the_view_name(packet_root):
    import duckdb

    con = duckdb.connect()
    name = open_packet(packet_root).table_resource("core.intervals").register(con)
    assert name == "core_intervals"
    assert con.sql("SELECT COUNT(*) FROM core_intervals").fetchone() == (2,)


def test_register_accepts_an_explicit_name(packet_root):
    import duckdb

    con = duckdb.connect()
    open_packet(packet_root).table_resource("core.intervals").register(con, name="t")
    assert con.sql("SELECT COUNT(*) FROM t").fetchone() == (2,)


def test_missing_file_raises_on_access_not_construction(packet_root):
    handle = open_packet(packet_root).table_resource("core.intervals")
    (packet_root / "tables" / "core" / "intervals.parquet").unlink()
    with pytest.raises(ResourceUnreadableError):
        _ = handle.path


# -- one type, whichever way a read was routed -------------------------------------------


def test_reads_return_plain_strings(packet_root):
    """A read decodes. Parquet stores a low-cardinality column as codes into a dictionary,
    and a caller gets the values, so nothing downstream has to know how the file was written.
    """
    table = open_packet(packet_root).table("core.intervals")
    assert all(str(table.schema.field(n).type) == "string" for n in handle_strings(table))


def test_the_schema_does_not_depend_on_whether_you_filtered(packet_root):
    """The read strategy differs between a whole read and a filtered one; the type must not.

    A caller should not have to know which branch its arguments took, and code that checks a
    column's type, concatenates two results, or converts to pandas must not change behaviour
    because a constraint was passed.
    """
    packet = open_packet(packet_root)
    whole = packet.table("core.intervals")
    first = whole.column("interval_id").to_pylist()[0]
    filtered = packet.table("core.intervals", interval_id=first)
    assert whole.schema.types == filtered.schema.types
    assert filtered.num_rows == 1


def test_results_from_both_paths_concatenate(packet_root):
    """The point of one type: two reads compose."""
    import pyarrow as pa

    packet = open_packet(packet_root)
    whole = packet.table("core.intervals")
    first = whole.column("interval_id").to_pylist()[0]
    filtered = packet.table("core.intervals", interval_id=first)
    assert pa.concat_tables([whole, filtered]).num_rows == whole.num_rows + 1


def test_a_pushed_predicate_still_matches(packet_root):
    """A filter compares against the values, so a dictionary-encoded column pushes down."""
    every = open_packet(packet_root).table("core.intervals")
    first = every.column("interval_id").to_pylist()[0]
    picked = open_packet(packet_root).table("core.intervals", interval_id=first)
    assert picked.num_rows == 1
    assert picked.column("interval_id").to_pylist() == [first]


def handle_strings(table):
    """String-ish column names, whichever encoding they came back in."""
    return [n for n in table.schema.names if str(table.schema.field(n).type).startswith(("string", "dictionary"))]


# -- Part 04 §5.1: external arrays, which in production live on an object store -----------------


def _external_entry(uri):
    from escapewheel_reader.manifest import Resource

    entry = {
        "resource_id": "core.probe.lfp",
        "declaration_id": "core.test_arrays",
        "uri": uri,
        "external": True,
    }
    declaration = {
        "content_class": "core",
        "kind": "dense_array",
        "instances": {"mode": "family"},
    }
    return Resource("core.probe.lfp", "core.test_arrays", uri, entry, declaration)


def _array_resource(uri, root=None):
    from pathlib import Path

    from escapewheel_reader.resources import ArrayResource

    root = root or Path("/nonexistent")

    return ArrayResource(_external_entry(uri), root)


def test_a_file_uri_resolves_to_its_path(tmp_path):
    """A packet built locally writes file://, which is a URI and not a path."""
    (tmp_path / "a.zarr").mkdir()
    handle = _array_resource((tmp_path / "a.zarr").resolve().as_uri(), tmp_path)

    assert handle.path == tmp_path / "a.zarr"
    assert handle.store == str(tmp_path / "a.zarr")


def test_a_remote_uri_is_handed_over_verbatim():
    """Resolving it to a Path first is the thing that would make it unopenable."""
    uri = "s3://bucket/session.nwb/processing/ecephys/LFP/ElectricalSeries1-LFP/data"
    assert _array_resource(uri).store == uri


def test_a_remote_uri_has_no_local_path():
    from escapewheel_reader import ResourceUnreadableError

    with pytest.raises(ResourceUnreadableError, match="s3:, which has no local path"):
        assert _array_resource("s3://bucket/lfp").path


def test_an_unreachable_external_array_has_no_inferred_zarr_version():
    """The packet and URI cannot substitute for unavailable format metadata."""
    from escapewheel_reader import ResourceUnreadableError

    with pytest.raises(ResourceUnreadableError, match="cannot reach"):
        _ = _array_resource("example://bucket/lfp").zarr_format


def test_a_windows_drive_is_not_a_scheme(tmp_path):
    """A single letter before a colon is a drive letter, not a URI scheme.

    It is treated as a path, so it fails for not existing rather than for being remote.
    """
    from escapewheel_reader import ResourceUnreadableError

    with pytest.raises(ResourceUnreadableError, match="does not resolve under"):
        assert _array_resource("C:/data/lfp.zarr").store


@pytest.fixture
def array_packet(tmp_path, packet_root):
    """The fixture packet plus one small packet-owned Zarr v3 array."""
    zarr = pytest.importorskip("zarr")
    import json
    import shutil

    import numpy as np

    root = tmp_path / "with_array"
    shutil.copytree(packet_root, root)
    store = root / "arrays" / "lfp.zarr"
    array = zarr.create_array(store=str(store), shape=(4, 3), chunks=(2, 3), dtype="int16")
    array[:] = np.arange(12, dtype="int16").reshape(4, 3)

    manifest = json.loads((root / "packet.json").read_text())
    manifest["resources"].append(
        {
            "resource_id": "core.lfp",
            "declaration_id": "core.test_arrays",
            "uri": "arrays/lfp.zarr",
            "validation_state": "passed",
        }
    )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    registry = read_registry(root)
    registry["resources"]["core.test_arrays"] = {
        "content_class": "core",
        "kind": "dense_array",
        "instances": {"mode": "family"},
        "requires": [],
        "lineage": "optional",
        "array": {"axes_resource": "core.intervals"},
    }
    install_registry(root, registry)
    return root


def test_array_opens_a_declared_array(array_packet):
    """Part 07 Phase 5 names this call; it is the counterpart of `table` and does the same job."""
    packet = open_packet(array_packet)
    opened = packet.array("core.lfp")
    assert opened.shape == (4, 3)
    assert opened[0, 0] == 0
    assert opened[3, 2] == 11


def test_array_agrees_with_the_handle(array_packet):
    """Sugar, so it must return what the two-step form returns."""
    packet = open_packet(array_packet)
    assert packet.array("core.lfp").shape == packet.array_resource("core.lfp").shape


def test_array_reports_an_undeclared_resource(array_packet):
    """Same failure as `table`, so the two behave alike where they can."""
    with pytest.raises(ResourceNotFoundError):
        open_packet(array_packet).array("core.not_declared")


def test_a_store_uri_pyarrow_cannot_open_is_reported(packet_root):
    """Part 04 §5.1: reachability is the reader's situation, so an unreachable store is a readable
    error and not a traceback from inside pyarrow."""
    import json

    from escapewheel_reader import open_packet
    from escapewheel_reader.errors import ResourceUnreadableError

    manifest = json.loads((packet_root / "packet.json").read_text())
    entry = next(r for r in manifest["resources"] if r["declaration_id"] == "core.units")
    entry["uri"] = "wat://nowhere/units.parquet"
    entry["external"] = True
    (packet_root / "packet.json").write_text(json.dumps(manifest))
    resource = open_packet(packet_root).table_resource(entry["resource_id"])
    assert not resource.is_local
    with pytest.raises(ResourceUnreadableError, match="cannot reach"):
        resource.schema()


# -- Part 03 §§6.1 and 6.4: the reader floor, and a codec this reader cannot decode ---------------


def _zarr_json(store):
    import json

    return json.loads((store / "zarr.json").read_text())


def _v3_array(tmp_path, name, **layout):
    """A two-chunk int16 array written by zarr-python, bound as an external resource."""
    zarr = pytest.importorskip("zarr")
    import numpy as np

    store = tmp_path / name
    array = zarr.create_array(store=str(store), shape=(4, 3), dtype="int16", **{"chunks": (2, 3), **layout})
    array[:] = np.arange(12, dtype="int16").reshape(4, 3)
    return store, _array_resource(store.resolve().as_uri(), tmp_path)


def test_the_pipeline_keeps_bytes_and_an_array_inside_the_floor_opens(array_packet):
    """zarr-python's default int16 pipeline, `bytes` then `zstd`, is a floor sequence verbatim."""
    handle = open_packet(array_packet).array_resource("core.lfp")
    assert handle.codecs == ("bytes", "zstd")
    assert handle.within_reader_floor
    assert handle.read((slice(3, 4), slice(2, 3)))[0, 0] == 11


def test_a_sharded_pipeline_is_the_sharding_codec_alone(tmp_path):
    """The shard's `bytes`, `zstd` with index `bytes`, `crc32c` at `end` is inside the floor."""
    _, handle = _v3_array(tmp_path, "sharded.zarr", shards=(4, 3))
    assert handle.codecs == ("sharding_indexed",)
    assert handle.within_reader_floor
    assert handle.read()[3, 2] == 11


def _shard(inner=(), index=None, location="end"):
    from zarr.codecs import BytesCodec, Crc32cCodec, ShardingCodec

    index = [BytesCodec(), Crc32cCodec()] if index is None else index
    codec = ShardingCodec(
        chunk_shape=(2, 3), codecs=[BytesCodec(), *inner], index_codecs=index, index_location=location
    )
    # Without `compressors=None` zarr-python wraps the whole shard in its default compressor.
    return {"serializer": codec, "chunks": (4, 3), "compressors": None}


def _floor_vectors():
    pytest.importorskip("zarr")
    from zarr.codecs import BloscCodec, BytesCodec, GzipCodec, ZstdCodec
    from zarr.codecs.numcodecs import Delta

    blosc = BloscCodec(cname="zstd", shuffle="shuffle")
    return {
        "bytes": ({"compressors": None}, True),
        "bytes_gzip": ({"compressors": GzipCodec()}, True),
        "bytes_zstd": ({"compressors": ZstdCodec()}, True),
        **{
            f"blosc_zstd_{mode}": ({"compressors": BloscCodec(cname="zstd", shuffle=mode)}, True)
            for mode in ("noshuffle", "shuffle", "bitshuffle")
        },
        "shard_bytes": (_shard(), True),
        "shard_gzip": (_shard([GzipCodec()]), True),
        "shard_zstd": (_shard([ZstdCodec()]), True),
        "shard_blosc_zstd": (_shard([blosc]), True),
        "shard_index_bytes": (_shard([ZstdCodec()], index=[BytesCodec()]), True),
        "shard_index_start": (_shard([ZstdCodec()], location="start"), False),
        "blosc_lz4": ({"compressors": BloscCodec(cname="lz4", shuffle="shuffle")}, False),
        "delta_blosc_zstd": ({"filters": Delta(dtype="int16"), "compressors": blosc}, False),
    }


@pytest.mark.parametrize(
    "name",
    [
        "bytes",
        "bytes_gzip",
        "bytes_zstd",
        "blosc_zstd_noshuffle",
        "blosc_zstd_shuffle",
        "blosc_zstd_bitshuffle",
        "shard_bytes",
        "shard_gzip",
        "shard_zstd",
        "shard_blosc_zstd",
        "shard_index_bytes",
        "shard_index_start",
        "blosc_lz4",
        "delta_blosc_zstd",
    ],
)
def test_the_descriptor_floor_classifies_written_v3_metadata(tmp_path, name):
    """Part 03 §6.4 against zarr-python's own `zarr.json` for each pipeline Part 10 §5 measured."""
    from escapewheel_reader.profile import variant_for_zarr_format, zarr_floor_admits

    layout, admitted = _floor_vectors()[name]
    store, _ = _v3_array(tmp_path, f"{name}.zarr", **layout)
    assert zarr_floor_admits(_zarr_json(store), variant_for_zarr_format(3)["reader_floor"]) is admitted


def test_the_descriptor_floor_reads_an_absent_index_location_as_end_and_nothing_after_a_shard(tmp_path):
    """Part 03 §6.4: `end` is the sharding codec's default; a codec after the shard leaves the floor."""
    from escapewheel_reader.profile import variant_for_zarr_format, zarr_floor_admits

    floor = variant_for_zarr_format(3)["reader_floor"]
    store, _ = _v3_array(tmp_path, "sharded.zarr", **_shard([pytest.importorskip("zarr").codecs.ZstdCodec()]))
    metadata = _zarr_json(store)
    del metadata["codecs"][0]["configuration"]["index_location"]
    assert zarr_floor_admits(metadata, floor)
    metadata["codecs"].append({"name": "zstd"})
    assert not zarr_floor_admits(metadata, floor)
    unrecognized = _zarr_json(store)
    unrecognized["codecs"] = [{"name": "bytes"}, {"name": "example.unknown"}]
    assert not zarr_floor_admits(unrecognized, floor)
    bare_blosc = _zarr_json(store)
    bare_blosc["codecs"] = [{"name": "bytes"}, {"name": "blosc"}]
    assert not zarr_floor_admits(bare_blosc, floor)


def test_a_floor_admitting_sharding_compares_the_shard_as_a_pipeline(tmp_path):
    """The descriptor decides; the same comparison reads a floor stated as patterns with sharding."""
    from escapewheel_reader.profile import zarr_floor_admits

    store, _ = _v3_array(tmp_path, "sharded.zarr", shards=(4, 3))
    metadata = _zarr_json(store)
    floor = {
        "codec_sequences": [[{"name": "bytes"}], [{"name": "bytes"}, {"name": "zstd"}]],
        "sharding": {"index_codec_sequences": [[{"name": "bytes"}, {"name": "crc32c"}]], "index_location": "end"},
    }
    assert zarr_floor_admits(metadata, floor)
    del metadata["codecs"][0]["configuration"]["index_location"]
    assert zarr_floor_admits(metadata, floor)
    metadata["codecs"].append({"name": "zstd"})
    assert not zarr_floor_admits(metadata, floor)
    assert not zarr_floor_admits(_zarr_json(store), {"codec_sequences": floor["codec_sequences"]})


def test_a_decodable_array_outside_the_floor_still_reads(tmp_path):
    """Outside the floor is beyond the portability guarantee, not an error (Part 03 §2)."""
    from zarr.codecs import BloscCodec

    _, handle = _v3_array(tmp_path, "blosc.zarr", compressors=BloscCodec(cname="lz4"))
    assert handle.codecs == ("bytes", "blosc")
    assert not handle.within_reader_floor
    assert handle.read()[3, 2] == 11


def test_a_codec_this_reader_lacks_fails_that_array_alone(array_packet):
    """Part 03 §6.1: the packet opens, the array describes itself, and only its values refuse."""
    import json

    from escapewheel_reader import UnsupportedCodecError

    store = array_packet / "arrays" / "lfp.zarr"
    metadata = _zarr_json(store)
    metadata["codecs"].append({"name": "example.unimplemented"})
    (store / "zarr.json").write_text(json.dumps(metadata))

    packet = open_packet(array_packet)
    handle = packet.array_resource("core.lfp")
    assert handle.codecs == ("bytes", "zstd", "example.unimplemented")
    assert not handle.within_reader_floor
    with pytest.raises(UnsupportedCodecError, match="example.unimplemented") as raised:
        packet.array("core.lfp")
    assert raised.value.resource_id == "core.lfp"
    assert raised.value.outside_floor
    assert packet.table("core.intervals").num_rows == 2


def test_a_v2_compressor_this_reader_lacks_fails_that_array(tmp_path):
    import json

    from escapewheel_reader import UnsupportedCodecError

    zarr = pytest.importorskip("zarr")
    store = tmp_path / "v2.zarr"
    zarr.create_array(store=str(store), shape=(4,), chunks=(2,), dtype="int16", zarr_format=2)[:] = 1
    metadata = json.loads((store / ".zarray").read_text())
    metadata["compressor"] = {"id": "example_unimplemented"}
    (store / ".zarray").write_text(json.dumps(metadata))

    handle = _array_resource(store.resolve().as_uri(), tmp_path)
    assert handle.codecs == ("example_unimplemented",)
    with pytest.raises(UnsupportedCodecError) as raised:
        handle.read()
    assert raised.value.outside_floor


def test_a_floor_codec_this_installation_lacks_is_marked_within_the_floor(array_packet, monkeypatch):
    """The packet is portable here, so the installation is what a user must repair."""
    zarr = pytest.importorskip("zarr")
    from zarr.errors import UnknownCodecError

    from escapewheel_reader import UnsupportedCodecError

    def unimplemented(*args, **kwargs):
        raise UnknownCodecError("zstd")

    monkeypatch.setattr(zarr, "open_array", unimplemented)
    with pytest.raises(UnsupportedCodecError, match="reader floor: within it") as raised:
        open_packet(array_packet).array("core.lfp")
    assert not raised.value.outside_floor


@pytest.mark.parametrize(
    ("filters", "compressor", "admitted"),
    [
        (None, None, True),
        (None, {"id": "zstd", "level": 5}, True),
        (None, {"id": "blosc", "cname": "zstd", "clevel": 5, "shuffle": 1}, True),
        (None, {"id": "blosc", "cname": "lz4"}, False),
        ([], {"id": "zstd"}, False),
        ([{"id": "delta", "dtype": "<i2"}], {"id": "zstd"}, False),
    ],
)
def test_the_v2_floor_compares_only_the_members_a_pattern_states(filters, compressor, admitted):
    """Part 03 §6.4: null matches only null, and unmentioned configuration does not participate."""
    from escapewheel_reader.profile import variant_for_zarr_format, zarr_floor_admits

    metadata = {"zarr_format": 2, "shape": [4], "filters": filters, "compressor": compressor}
    assert zarr_floor_admits(metadata, variant_for_zarr_format(2)["reader_floor"]) is admitted


def test_a_store_only_zarr_can_reach_leaves_the_floor_unassessed(array_packet, monkeypatch):
    """The metadata cannot be compared when the one reader of it is the one that failed."""
    zarr = pytest.importorskip("zarr")
    from zarr.errors import UnknownCodecError

    from escapewheel_reader import UnsupportedCodecError
    from escapewheel_reader.resources import ArrayResource

    def unimplemented(*args, **kwargs):
        raise UnknownCodecError("example.unimplemented")

    monkeypatch.setattr(zarr, "open_array", unimplemented)
    monkeypatch.setattr(ArrayResource, "_read_document", lambda self: None)
    handle = open_packet(array_packet).array_resource("core.lfp")
    with pytest.raises(UnsupportedCodecError, match="reader floor: unassessed") as raised:
        handle.metadata()
    assert raised.value.outside_floor is None

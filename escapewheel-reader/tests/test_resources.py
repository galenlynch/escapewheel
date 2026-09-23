import pytest

from escapewheel_reader import ResourceNotFoundError, ResourceUnreadableError, open_packet

from .conftest import TRIALS


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
    registry_path = root / "schemas" / "logical_schemas.json"
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

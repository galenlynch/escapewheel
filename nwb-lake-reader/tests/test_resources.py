import pytest

from nwb_lake_reader import ResourceUnreadableError, open_packet


def test_handle_reads_and_describes(packet_root):
    handle = open_packet(packet_root).table_resource("core.trials")
    assert handle.resource_id == "core.trials"
    assert handle.sql_name == "core_trials"
    assert handle.to_arrow().num_rows == 2
    assert "core.trials" in repr(handle)


def test_schema_without_reading_data(packet_root):
    schema = open_packet(packet_root).table_resource("core.trials").schema()
    assert schema.names == ["session_id", "trial_id", "start_tick", "stop_tick", "clock_id"]
    assert str(schema.field("start_tick").type) == "int64"


def test_dataset_is_lazy_and_filterable(packet_root):
    import pyarrow.dataset as pads

    dataset = open_packet(packet_root).table_resource("core.trials").dataset()
    filtered = dataset.to_table(filter=pads.field("trial_id") == "trial_0002")
    assert filtered.num_rows == 1


def test_register_returns_the_view_name(packet_root):
    import duckdb

    con = duckdb.connect()
    name = open_packet(packet_root).table_resource("core.trials").register(con)
    assert name == "core_trials"
    assert con.sql("SELECT COUNT(*) FROM core_trials").fetchone() == (2,)


def test_register_accepts_an_explicit_name(packet_root):
    import duckdb

    con = duckdb.connect()
    open_packet(packet_root).table_resource("core.trials").register(con, name="t")
    assert con.sql("SELECT COUNT(*) FROM t").fetchone() == (2,)


def test_missing_file_raises_on_access_not_construction(packet_root):
    handle = open_packet(packet_root).table_resource("core.trials")
    (packet_root / "tables" / "core" / "trials.parquet").unlink()
    with pytest.raises(ResourceUnreadableError):
        _ = handle.path


# -- dictionary-encoded identity columns -------------------------------------------------


def test_dictionary_columns_names_what_the_file_encoded(packet_root):
    """Only columns the writer dictionary-encoded, and only ones a dictionary helps."""
    handle = open_packet(packet_root).table_resource("core.trials")
    named = handle.dictionary_columns()
    schema = handle.schema()
    assert named, "the fixture writes low-cardinality strings, which pyarrow dictionary-encodes"
    assert all(str(schema.field(n).type) == "string" for n in named)
    assert "start_tick" not in named


def test_reads_return_plain_strings(packet_root):
    """The default is the predictable type. Keeping the file's own encoding is opt-in,
    because the case it helps -- reading a whole identity column -- is not one an analysis
    performs, and changing what every read returns to serve it is not a trade worth making.
    """
    table = open_packet(packet_root).table("core.trials")
    assert all(str(table.schema.field(n).type) == "string" for n in handle_strings(table))


def test_the_schema_does_not_depend_on_whether_you_filtered(packet_root):
    """The read strategy differs between a whole read and a filtered one; the type must not.

    A caller should not have to know which branch its arguments took, and code that checks a
    column's type, concatenates two results, or converts to pandas must not change behaviour
    because a constraint was passed.
    """
    packet = open_packet(packet_root)
    whole = packet.table("core.trials")
    first = whole.column("trial_id").to_pylist()[0]
    filtered = packet.table("core.trials", trial_id=first)
    assert whole.schema.types == filtered.schema.types
    assert filtered.num_rows == 1


def test_results_from_both_paths_concatenate(packet_root):
    """The point of one type: two reads compose."""
    import pyarrow as pa

    packet = open_packet(packet_root)
    whole = packet.table("core.trials")
    first = whole.column("trial_id").to_pylist()[0]
    filtered = packet.table("core.trials", trial_id=first)
    assert pa.concat_tables([whole, filtered]).num_rows == whole.num_rows + 1


def test_keeping_the_dictionary_is_uniform_too(packet_root):
    """Whichever is asked for applies to both paths, so the schema never depends on the
    arguments -- which is the whole reason `decode` is a promise about the type rather than
    about how the file is read."""
    packet = open_packet(packet_root)
    whole = packet.table("core.trials", decode=False)
    first = whole.column("trial_id").to_pylist()[0]
    filtered = packet.table("core.trials", trial_id=first, decode=False)
    assert whole.schema.types == filtered.schema.types
    assert all(str(whole.schema.field(n).type).startswith("dictionary") for n in handle_strings(whole))


def test_decode_can_be_forced_either_way(packet_root):
    packet = open_packet(packet_root)
    kept = packet.table("core.trials", columns=["trial_id"], decode=False)
    assert str(kept.schema.field("trial_id").type).startswith("dictionary")
    table = open_packet(packet_root).table("core.trials", decode=True)
    assert all(str(table.schema.field(n).type) == "string" for n in handle_strings(table))


def test_values_are_the_same_either_way(packet_root):
    """A dictionary is an encoding, not a different answer."""
    encoded = open_packet(packet_root).table("core.trials")
    decoded = open_packet(packet_root).table("core.trials", decode=True)
    assert encoded.num_rows == decoded.num_rows
    for name in handle_strings(decoded):
        assert encoded.column(name).to_pylist() == decoded.column(name).to_pylist()


def test_a_pushed_predicate_still_matches(packet_root):
    """Filters compare against dictionary values, so pushdown is unaffected."""
    every = open_packet(packet_root).table("core.trials")
    first = every.column("trial_id").to_pylist()[0]
    picked = open_packet(packet_root).table("core.trials", trial_id=first)
    assert picked.num_rows == 1
    assert picked.column("trial_id").to_pylist() == [first]


def handle_strings(table):
    """String-ish column names, whichever encoding they came back in."""
    return [n for n in table.schema.names if str(table.schema.field(n).type).startswith(("string", "dictionary"))]


# -- R14 §2.3: external arrays, which in production live on an object store -----------------


def _external_entry(uri):
    from nwb_lake_reader.manifest import Resource

    entry = {
        "resource_id": "core.probe.lfp",
        "layer": "core",
        "kind": "dense_array_asset",
        "physical_profile": "zarr_v2",
        "uri": uri,
        "external": True,
        "codecs": ["blosc"],
    }
    return Resource("core.probe.lfp", "core", "dense_array_asset", uri, entry)


def _array_resource(uri, root=None):
    from pathlib import Path

    from nwb_lake_reader.resources import ArrayResource

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
    from nwb_lake_reader import ResourceUnreadableError

    with pytest.raises(ResourceUnreadableError, match="s3:, which has no local path"):
        assert _array_resource("s3://bucket/lfp").path


def test_a_remote_array_takes_its_zarr_version_from_the_manifest():
    """Nothing local exists to read it from, and R14 §2.3.1 already makes it a claim."""
    assert _array_resource("s3://bucket/lfp").zarr_format == 2


def test_a_windows_drive_is_not_a_scheme(tmp_path):
    """A single letter before a colon is a drive letter, not a URI scheme.

    It is treated as a path, so it fails for not existing rather than for being remote.
    """
    from nwb_lake_reader import ResourceUnreadableError

    with pytest.raises(ResourceUnreadableError, match="does not resolve under"):
        assert _array_resource("C:/data/lfp.zarr").store

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

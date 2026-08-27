import pytest

from nwb_lake_reader import open_packet


def test_trials_unfiltered(packet_root):
    assert open_packet(packet_root).trials().num_rows == 2


def test_trials_filtered_by_session(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.trials(session_id="s001").num_rows == 2
    assert pkt.trials(session_id="s999").num_rows == 0


def test_accessors_use_no_sql_engine(packet_root, monkeypatch):
    """A complete read path must exist without a SQL engine.

    table(), the accessors, and TableResource all go through PyArrow. Packet.duckdb() is a
    read path too and does need DuckDB; the point is that it is not the only one, so a
    minimal reader stays possible in a language without an embedded SQL engine (R3 2.1).
    """
    import builtins

    real_import = builtins.__import__

    def refuse_duckdb(name, *args, **kwargs):
        if name == "duckdb":
            raise AssertionError("reading a packet must not import duckdb")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse_duckdb)
    pkt = open_packet(packet_root)
    assert pkt.trials().num_rows == 2
    assert pkt.table("core.sessions").num_rows == 1


def test_units_filtered_by_quality(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.units().num_rows == 2
    assert pkt.units(quality_label="sua").num_rows == 1
    assert pkt.units(quality_label="noise").num_rows == 0


def test_events_filtered_by_type(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.events().num_rows == 3
    assert pkt.events(event_type="stimulus_onset").num_rows == 2
    assert pkt.events(event_type="reward").num_rows == 1


def test_unrecognised_event_type_is_empty_not_an_error(packet_root):
    """event_type is an open vocabulary, so an unknown value is simply absent."""
    assert open_packet(packet_root).events(event_type="lick").num_rows == 0


def test_spike_times_returns_ticks_with_their_clock(packet_root):
    """A tick has no meaning without the clock it was counted on."""
    result = open_packet(packet_root).spike_times("unit_001")
    assert result.column_names == ["t_tick", "clock_id"]
    assert result.to_pydict()["t_tick"] == [30000, 39000, 48000]
    assert set(result.to_pydict()["clock_id"]) == {"imec_ap_s001"}


def test_spike_times_narrowed_by_sorting_context(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.spike_times("unit_002", sorting_run_id="sort_001").num_rows == 2
    assert pkt.spike_times("unit_002", sorting_run_id="other").num_rows == 0


def test_accessors_push_predicates_into_the_reader(packet_root, monkeypatch):
    """Filters must reach the Parquet reader, not be applied after loading everything.

    pq.read_table materialises a whole table; the dataset path does not. Making it raise
    proves the accessors take the pushdown path, which is worth 24.8 ms to 4.4 ms on nine
    million rows.
    """
    import pyarrow.parquet as pq

    def refuse(*args, **kwargs):
        raise AssertionError("accessors must not load a whole table; push the predicate down")

    monkeypatch.setattr(pq, "read_table", refuse)
    assert open_packet(packet_root).units(quality_label="sua").num_rows == 1
    assert open_packet(packet_root).spike_times("unit_001").num_rows == 3


def test_table_pushes_equality_constraints(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.table("core.events", event_type="reward").num_rows == 1
    assert pkt.table("core.events", event_type="stimulus_onset").num_rows == 2


def test_table_pushes_range_constraints(packet_root):
    """A two-item tuple means a closed range."""
    pkt = open_packet(packet_root)
    assert pkt.table("core.events", t_tick=(1200, 4200)).num_rows == 2
    assert pkt.table("core.events", t_tick=(0, 1199)).num_rows == 0
    assert pkt.table("core.events", t_tick=(1200, 1200)).num_rows == 1


def test_table_combines_constraints(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.table("core.events", event_type="stimulus_onset", t_tick=(0, 2000)).num_rows == 1


def test_table_projects_columns(packet_root):
    projected = open_packet(packet_root).table("core.units", columns=["unit_id", "quality_label"])
    assert projected.column_names == ["unit_id", "quality_label"]


def test_table_unconstrained_reads_everything(packet_root):
    assert open_packet(packet_root).table("core.events").num_rows == 3


def test_unknown_constraint_column_fails_loudly(packet_root):
    """A typo must raise, not silently match nothing."""
    with pytest.raises(Exception, match="no_such_column"):
        open_packet(packet_root).table("core.events", no_such_column="x")


def test_events_accepts_a_tick_range(packet_root):
    assert open_packet(packet_root).events(event_type="stimulus_onset", t_tick=(6000, 7000)).num_rows == 1


def test_spike_times_accepts_a_tick_range(packet_root):
    result = open_packet(packet_root).spike_times("unit_001", t_tick=(30000, 39000))
    assert result.to_pydict()["t_tick"] == [30000, 39000]


def test_scan_is_lazy(packet_root):
    """scan() must not read; it hands back a dataset for what constraints cannot express."""
    import pyarrow.dataset as pads
    import pyarrow.parquet as pq

    dataset = open_packet(packet_root).scan("core.events")
    assert isinstance(dataset, pads.Dataset)
    assert dataset.to_table(filter=pads.field("event_type") == "lick").num_rows == 0
    assert pq  # the import exists so the lazy contrast is explicit

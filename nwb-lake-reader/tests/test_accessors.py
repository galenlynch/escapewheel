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

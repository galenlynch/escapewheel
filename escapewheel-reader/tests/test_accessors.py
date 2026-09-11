import pyarrow as pa
import pytest

from escapewheel_reader import STORED, NotAligned, NoTimeOrigin, open_packet
from tests.conftest import CLOCK_BEHAVIOUR, CLOCK_PROBE, SESSION, SORTING_RUN, UNITS, _resource, _write


def test_trials_unfiltered(packet_root):
    assert open_packet(packet_root).intervals().num_rows == 2


def test_trials_filtered_by_session(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.intervals(session_id=SESSION).num_rows == 2
    assert pkt.intervals(session_id=SESSION + 999).num_rows == 0


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
    assert pkt.intervals().num_rows == 2
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
    result = open_packet(packet_root).spike_times(UNITS[0])
    assert result.column_names == ["t_tick", "clock_id"]
    assert result.to_pydict()["t_tick"] == [30000, 39000, 48000]
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_PROBE}


def test_spike_times_narrowed_by_sorting_context(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.spike_times(UNITS[1], sorting_run_id=SORTING_RUN).num_rows == 2
    assert pkt.spike_times(UNITS[1], sorting_run_id=SORTING_RUN + 1).num_rows == 0


def test_accessors_push_predicates_into_the_reader(packet_root, monkeypatch):
    """Filters must reach the Parquet reader, not be applied after loading everything.

    pq.read_table materialises a whole table; the dataset path does not. Making it raise
    proves the accessors take the pushdown path, which is worth 24.8 ms to 4.4 ms on nine
    million rows.
    """
    import pyarrow.parquet as pq

    real = pq.read_table

    def refuse(source, *args, **kwargs):
        # Only the spike table. Reading `core.sessions` or `core.clock_anchors` whole is what
        # returning ticks on a declared clock takes, and both are one row per session or per
        # sync pulse -- the cost this guards against is per spike.
        if "spike" in str(source):
            raise AssertionError("accessors must not load a whole table; push the predicate down")
        return real(source, *args, **kwargs)

    monkeypatch.setattr(pq, "read_table", refuse)
    assert open_packet(packet_root).units(quality_label="sua").num_rows == 1
    assert open_packet(packet_root).spike_times(UNITS[0]).num_rows == 3


def test_table_pushes_equality_constraints(packet_root):
    """R91 §3.2 leaves `stream_id` as the event's only equality column; the type is the
    stream's, which `events()` resolves and `table()` does not."""
    pkt = open_packet(packet_root)
    assert pkt.table("core.events", stream_id=1).num_rows == 1
    assert pkt.table("core.events", stream_id=0).num_rows == 2


def test_table_pushes_range_constraints(packet_root):
    """A two-item tuple means a closed range."""
    pkt = open_packet(packet_root)
    assert pkt.table("core.events", t_tick=(1200, 4200)).num_rows == 2
    assert pkt.table("core.events", t_tick=(0, 1199)).num_rows == 0
    assert pkt.table("core.events", t_tick=(1200, 1200)).num_rows == 1


def test_table_combines_constraints(packet_root):
    pkt = open_packet(packet_root)
    assert pkt.table("core.events", stream_id=0, t_tick=(0, 2000)).num_rows == 1


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
    result = open_packet(packet_root).spike_times(UNITS[0], t_tick=(30000, 39000))
    assert result.to_pydict()["t_tick"] == [30000, 39000]


def test_scan_is_lazy(packet_root):
    """scan() must not read; it hands back a dataset for what constraints cannot express."""
    import pyarrow.dataset as pads
    import pyarrow.parquet as pq

    dataset = open_packet(packet_root).scan("core.events")
    assert isinstance(dataset, pads.Dataset)
    assert dataset.to_table(filter=pads.field("stream_id") == 99).num_rows == 0
    assert pq  # the import exists so the lazy contrast is explicit


# -- the packet's default clock (R27 §2) --------------------------------------------------


def test_spike_times_come_back_on_the_reference_clock(two_clock_packet):
    """A spike is counted on its probe; a caller comparing that to behaviour needs the map."""
    pkt = open_packet(two_clock_packet)
    assert pkt.reference_clock() == CLOCK_BEHAVIOUR
    result = pkt.spike_times(UNITS[0])
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_BEHAVIOUR}
    assert result.to_pydict()["t_tick"] == [1_031_250, 1_062_500]


def test_stored_ticks_take_saying_so(two_clock_packet):
    """The unsynchronized answer is still reachable -- it just cannot be reached by accident."""
    result = open_packet(two_clock_packet).spike_times(UNITS[0], clock=STORED)
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_PROBE}
    assert result.to_pydict()["t_tick"] == [30_000, 60_000]


def test_events_come_back_on_the_reference_clock(two_clock_packet):
    result = open_packet(two_clock_packet).events(event_type="go_cue")
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_BEHAVIOUR}


def test_a_packet_with_one_clock_needs_no_declaration(packet_root):
    """Nothing to reconcile, so nothing to declare; the fixture packet declares none."""
    pkt = open_packet(packet_root)
    with pytest.raises(NotAligned, match="reference_clock_id"):
        pkt.reference_clock()
    assert set(pkt.spike_times(UNITS[0]).to_pydict()["clock_id"]) == {CLOCK_PROBE}


def test_rows_spanning_clocks_with_no_reference_are_refused(two_clock_packet, monkeypatch):
    """Returning these as stored would invite a comparison that means nothing."""
    pkt = open_packet(two_clock_packet)
    spanning = pkt.table("core.spike_events")
    monkeypatch.setattr(pkt, "reference_clock", _raise_unaligned)
    assert sorted(set(spanning.to_pydict()["clock_id"])) == [CLOCK_BEHAVIOUR, CLOCK_PROBE]
    with pytest.raises(NotAligned):
        pkt.on_clock(spanning)


def _raise_unaligned(**kwargs):
    raise NotAligned("no reference declared")


def test_a_tick_range_is_stated_on_the_clock_the_result_uses(two_clock_packet):
    """The range and the ticks it selects must be in one space, or the caller is comparing
    a reference tick against a probe tick without being told."""
    pkt = open_packet(two_clock_packet)
    whole = pkt.spike_times(UNITS[0]).to_pydict()["t_tick"]
    assert whole == [1_031_250, 1_062_500]
    # A range around the first spike, on the reference clock, must not select the second.
    narrowed = pkt.spike_times(UNITS[0], t_tick=(1_031_000, 1_031_500)).to_pydict()["t_tick"]
    assert narrowed == [1_031_250]
    # The same numbers read as stored probe ticks select nothing, and say so rather than
    # quietly returning the whole train.
    assert pkt.spike_times(UNITS[0], t_tick=(1_031_000, 1_031_500), clock=STORED).num_rows == 0


def test_a_stored_range_still_selects_stored_ticks(two_clock_packet):
    result = open_packet(two_clock_packet).spike_times(UNITS[0], t_tick=(29_000, 31_000), clock=STORED)
    assert result.to_pydict()["t_tick"] == [30_000]


def test_an_event_range_is_on_the_reference_clock(two_clock_packet):
    pkt = open_packet(two_clock_packet)
    assert pkt.events(t_tick=(1_100_000, 1_300_000)).num_rows == 1
    assert pkt.events(t_tick=(1_300_000, 1_400_000)).num_rows == 0


# -- seconds (Part 01 §2.1) ----------------------------------------------------------------


def test_the_origin_is_read_not_recomputed(two_clock_packet):
    """The writer took the minimum across clocks through R13's map; a reader repeats none of it."""
    assert open_packet(two_clock_packet).t_zero() == 1_000_000


def test_seconds_run_from_the_declared_origin(two_clock_packet):
    """A spike at probe tick 30,000 is harp tick 1,031,250, one harp second past the origin."""
    found = open_packet(two_clock_packet).spike_times(UNITS[0], seconds=True)
    assert found.column("t_tick").to_pylist() == [1_031_250, 1_062_500]
    assert found.column("t_second").to_pylist() == [1.0, 2.0]


def test_seconds_are_derived_beside_the_tick_not_instead_of_it(two_clock_packet):
    found = open_packet(two_clock_packet).events(seconds=True)
    assert "t_tick" in found.column_names
    assert found.column("t_second").to_pylist() == [pytest.approx(6.4)]


def test_seconds_may_be_negative(two_clock_packet):
    """Part 01 §2.1: data outside its window is reported, not clamped away."""
    before = pa.table({"t_tick": pa.array([968_750], type=pa.int64()), "clock_id": pa.array([CLOCK_BEHAVIOUR])})
    assert open_packet(two_clock_packet).seconds(before).column("t_second").to_pylist() == [-1.0]


def test_a_packet_with_no_origin_refuses_rather_than_inventing_one(packet_root):
    """Part 01 §2.1: tick zero, the wall clock and the first datum are all available and all wrong."""
    with pytest.raises(NoTimeOrigin):
        open_packet(packet_root).t_zero()


def test_seconds_refuse_ticks_that_are_not_on_the_reference(two_clock_packet):
    """Seconds from a probe tick would be a different quantity wearing the same name."""
    packet = open_packet(two_clock_packet)
    with pytest.raises(NotAligned):
        packet.seconds(packet.spike_times(UNITS[0], clock=STORED))


def test_mapping_uses_the_bound_the_writer_established(two_clock_packet, tmp_path):
    """Part 01 §3.9: a reader mapping at a narrower bound drops rows the packet's own derived
    table kept, and the two then disagree about which spikes exist."""
    import json
    import shutil

    root = tmp_path / "wide"
    shutil.copytree(two_clock_packet, root)
    manifest = json.loads((root / "packet.json").read_text())
    # R99 §3.1 puts the bound on the session, so this widens the packet's own session row
    # rather than standing a new table beside it.
    import pyarrow.parquet as pq

    entry = next(r for r in manifest["resources"] if r["resource_id"] == "core.sessions")
    sessions = pq.read_table(root / entry["uri"])
    sessions = sessions.append_column("alignment_bound", pa.array([3.0] * sessions.num_rows, pa.float64()))
    pq.write_table(sessions, root / entry["uri"])
    (root / "packet.json").write_text(json.dumps(manifest))

    # Two anchor intervals before the first anchor: outside Part 01 §3.9's default, inside the
    # bound this packet says its writer measured.
    far = pa.table({"t_tick": pa.array([-60_000], type=pa.int64()), "clock_id": pa.array([CLOCK_PROBE])})
    packet = open_packet(root)
    assert packet.on_clock(far).num_rows == 1
    assert packet.on_clock(far, bound=1.0).num_rows == 0

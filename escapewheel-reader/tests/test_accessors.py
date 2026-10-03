import json
import shutil

import pyarrow as pa
import pytest
from packet_fixture import (
    CLOCK_BEHAVIOUR,
    CLOCK_PROBE,
    CURATION,
    SESSION,
    SESSION_NAME,
    SORTING_RUN,
    UNITS,
    resource_entry,
    write_table,
)

from escapewheel_reader import STORED, NotAligned, NoTimeOrigin, access, clocks, open_packet
from escapewheel_reader.observation import support_of


def test_trials_unfiltered(packet_root):
    assert access.intervals(open_packet(packet_root)).num_rows == 2


def test_trials_filtered_by_session(packet_root):
    pkt = open_packet(packet_root)
    assert access.intervals(pkt, session_id=SESSION).num_rows == 2
    assert access.intervals(pkt, session_id=SESSION + 999).num_rows == 0


def test_accessors_use_no_sql_engine(packet_root, monkeypatch):
    """A complete read path must exist without a SQL engine.

    table(), the accessors, and TableResource all go through PyArrow. Packet.duckdb() is a
    read path too and does need DuckDB; the point is that it is not the only one, so a
    minimal reader stays possible in a language without an embedded SQL engine (Part 02 §5.2).
    """
    import builtins

    real_import = builtins.__import__

    def refuse_duckdb(name, *args, **kwargs):
        if name == "duckdb":
            raise AssertionError("reading a packet must not import duckdb")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse_duckdb)
    pkt = open_packet(packet_root)
    assert access.intervals(pkt).num_rows == 2
    assert pkt.table("core.sessions").num_rows == 1


def test_units_filtered_by_quality(packet_root):
    pkt = open_packet(packet_root)
    assert access.units(pkt).num_rows == 2
    assert access.units(pkt, quality_label="sua").num_rows == 1
    assert access.units(pkt, quality_label="noise").num_rows == 0


def test_events_filtered_by_type(packet_root):
    pkt = open_packet(packet_root)
    assert access.events(pkt).num_rows == 3
    assert access.events(pkt, event_type="stimulus_onset").num_rows == 2
    assert access.events(pkt, event_type="reward").num_rows == 1


def test_unrecognised_event_type_is_empty_not_an_error(packet_root):
    """event_type is an open vocabulary, so an unknown value is simply absent."""
    assert access.events(open_packet(packet_root), event_type="lick").num_rows == 0


def test_spike_times_returns_ticks_with_their_clock(packet_root):
    """A tick has no meaning without the clock it was counted on."""
    result = access.spike_times(open_packet(packet_root), UNITS[0])
    assert result.column_names == ["unit_id", "t_tick", "clock_id"]
    assert result.to_pydict()["t_tick"] == [30000, 39000, 48000]
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_PROBE}


def test_spike_times_rejects_removed_identity_arguments(packet_root):
    """Run and curation are unit facts, not redundant spike-selection arguments."""
    with pytest.raises(TypeError, match="sorting_run_id"):
        access.spike_times(open_packet(packet_root), UNITS[1], sorting_run_id=1)


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
    assert access.units(open_packet(packet_root), quality_label="sua").num_rows == 1
    assert access.spike_times(open_packet(packet_root), UNITS[0]).num_rows == 3


def test_table_pushes_equality_constraints(packet_root):
    """`stream_id` is the event's only equality column; the type is the stream's
    (Part 01 §3.11), which `events()` resolves and `table()` does not."""
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
    assert access.events(open_packet(packet_root), event_type="stimulus_onset", t_tick=(6000, 7000)).num_rows == 1


def test_spike_times_accepts_a_tick_range(packet_root):
    result = access.spike_times(open_packet(packet_root), UNITS[0], t_tick=(30000, 39000))
    assert result.to_pydict()["t_tick"] == [30000, 39000]


def test_session_scope_reaches_spikes_time_conversion_and_support(tmp_path, packet_root):
    """One session restriction governs rows, unit clocks, origins, and attached support."""
    root = tmp_path / "two_sessions"
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())
    by_id = {resource["resource_id"]: resource for resource in manifest["resources"]}
    other = SESSION + 1
    i32 = pa.int32()

    sessions = pa.table(
        {
            "session_id": pa.array([SESSION, other], type=i32),
            "session_name": pa.array([SESSION_NAME, "s002"]),
            "subject_id": pa.array([7, 8], type=i32),
            "session_start_time": pa.array(
                [1_756_000_000_000_000, 1_756_000_100_000_000],
                type=pa.timestamp("us", tz="UTC"),
            ),
            "reference_clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], type=i32),
            "t_zero_tick": pa.array([0, 100], type=pa.int64()),
        }
    )
    units = pa.table(
        {
            "session_id": pa.array([SESSION, other], type=i32),
            "unit_id": pa.array([UNITS[0], UNITS[2]], type=i32),
            "sorting_run_id": pa.array([SORTING_RUN, SORTING_RUN + 1], type=i32),
            "curation_id": pa.array([CURATION, CURATION + 1], type=i32),
            "quality_label": pa.array(["sua", "mua"]),
            "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], type=i32),
        }
    )
    spikes = pa.table(
        {
            "session_id": pa.array([SESSION, other, other], type=i32),
            "unit_id": pa.array([UNITS[0], UNITS[2], UNITS[2]], type=i32),
            "t_tick": pa.array([50, 150, 200], type=pa.int64()),
        }
    )
    clock_rows = pa.table(
        {
            "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], type=i32),
            "session_id": pa.array([SESSION, other], type=i32),
            "tick_rate_num": pa.array([100, 100], type=pa.int64()),
            "tick_rate_den": pa.array([1, 1], type=pa.int64()),
        }
    )
    windows = pa.table(
        {
            "session_id": pa.array([SESSION, other], type=i32),
            "clock_id": pa.array([CLOCK_BEHAVIOUR, CLOCK_PROBE], type=i32),
            "start_tick": pa.array([0, 100], type=pa.int64()),
            "stop_tick": pa.array([99, 299], type=pa.int64()),
        }
    )
    for resource_id, name, table in (
        ("core.sessions", "sessions", sessions),
        ("core.units", "units", units),
        ("core.spike_events", "spike_events", spikes),
    ):
        by_id[resource_id]["uri"] = write_table(root, name, table)
    manifest["resources"].extend(
        [
            resource_entry("core.clocks", write_table(root, "clocks", clock_rows)),
            resource_entry(
                "core.clock_observation_intervals", write_table(root, "clock_observation_intervals", windows)
            ),
        ]
    )
    manifest["sessions"] = [SESSION_NAME, "s002"]
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))

    packet = open_packet(root)
    single = access.spike_times(packet, UNITS[2], session_id=other, seconds=True)
    assert single.column("t_tick").to_pylist() == [150, 200]
    assert single.column("t_second").to_pylist() == [0.5, 1.0]
    assert support_of(single).to_pylist() == [{"clock_id": CLOCK_PROBE, "start_tick": 100, "stop_tick": 299}]
    assert clocks.reference_clock(packet, session_id=other) == CLOCK_PROBE
    assert clocks.origin(packet, other)[0] == 100

    explicit = access.spike_times(packet, units=access.units(packet), session_id=other, clock=STORED)
    assert explicit.column("t_tick").to_pylist() == [150, 200]
    mismatched = access.spike_times(packet, UNITS[0], session_id=other, clock=STORED)
    assert mismatched.num_rows == 0
    assert support_of(mismatched) is None


def test_scan_is_lazy(packet_root):
    """scan() must not read; it hands back a dataset for what constraints cannot express."""
    import pyarrow.dataset as pads
    import pyarrow.parquet as pq

    dataset = open_packet(packet_root).scan("core.events")
    assert isinstance(dataset, pads.Dataset)
    assert dataset.to_table(filter=pads.field("stream_id") == 99).num_rows == 0
    assert pq  # the import exists so the lazy contrast is explicit


def test_a_scanner_reads_what_table_reads(packet_root):
    import pyarrow.dataset as pads

    from escapewheel_reader.resources import read_pool

    packet = open_packet(packet_root)
    scanner = packet.scanner("core.events", columns=["stream_id"], stream_id=99)
    assert isinstance(scanner, pads.Scanner)
    assert scanner.to_table().equals(packet.table("core.events", columns=["stream_id"], stream_id=99))
    before = read_pool().bytes_allocated()
    held = packet.scanner("core.events").to_table()
    assert held.num_rows and read_pool().bytes_allocated() > before


# -- the packet's default clock ------------------------------------------------------------


def test_spike_times_come_back_on_the_reference_clock(two_clock_packet):
    """A spike is counted on its probe; a caller comparing that to behaviour needs the map."""
    pkt = open_packet(two_clock_packet)
    assert clocks.reference_clock(pkt) == CLOCK_BEHAVIOUR
    result = access.spike_times(pkt, UNITS[0])
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_BEHAVIOUR}
    assert result.to_pydict()["t_tick"] == [1_031_250, 1_062_500]


def test_stored_ticks_take_saying_so(two_clock_packet):
    """The unsynchronized answer is still reachable -- it just cannot be reached by accident."""
    result = access.spike_times(open_packet(two_clock_packet), UNITS[0], clock=STORED)
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_PROBE}
    assert result.to_pydict()["t_tick"] == [30_000, 60_000]


def test_events_come_back_on_the_reference_clock(two_clock_packet):
    result = access.events(open_packet(two_clock_packet), event_type="go_cue")
    assert set(result.to_pydict()["clock_id"]) == {CLOCK_BEHAVIOUR}


def test_a_packet_with_one_clock_needs_no_declaration(packet_root):
    """Nothing to reconcile, so nothing to declare; the fixture packet declares none."""
    pkt = open_packet(packet_root)
    with pytest.raises(NotAligned, match="reference_clock_id"):
        clocks.reference_clock(pkt)
    assert set(access.spike_times(pkt, UNITS[0]).to_pydict()["clock_id"]) == {CLOCK_PROBE}


def test_rows_spanning_clocks_with_no_reference_are_refused(two_clock_packet, monkeypatch):
    """Returning these as stored would invite a comparison that means nothing."""
    pkt = open_packet(two_clock_packet)
    spanning = access.spike_times(pkt, units=access.units(pkt), clock=STORED)
    monkeypatch.setattr(clocks, "reference_clock", _raise_unaligned)
    assert sorted(set(spanning.to_pydict()["clock_id"])) == [CLOCK_BEHAVIOUR, CLOCK_PROBE]
    with pytest.raises(NotAligned):
        clocks.on_clock(pkt, spanning)


def _raise_unaligned(*args, **kwargs):
    raise NotAligned("no reference declared")


def test_a_tick_range_is_stated_on_the_clock_the_result_uses(two_clock_packet):
    """The range and the ticks it selects must be in one space, or the caller is comparing
    a reference tick against a probe tick without being told."""
    pkt = open_packet(two_clock_packet)
    whole = access.spike_times(pkt, UNITS[0]).to_pydict()["t_tick"]
    assert whole == [1_031_250, 1_062_500]
    # A range around the first spike, on the reference clock, must not select the second.
    narrowed = access.spike_times(pkt, UNITS[0], t_tick=(1_031_000, 1_031_500)).to_pydict()["t_tick"]
    assert narrowed == [1_031_250]
    # The same numbers read as stored probe ticks select nothing, and say so rather than
    # quietly returning the whole train.
    assert access.spike_times(pkt, UNITS[0], t_tick=(1_031_000, 1_031_500), clock=STORED).num_rows == 0


def test_a_stored_range_still_selects_stored_ticks(two_clock_packet):
    result = access.spike_times(open_packet(two_clock_packet), UNITS[0], t_tick=(29_000, 31_000), clock=STORED)
    assert result.to_pydict()["t_tick"] == [30_000]


def test_an_event_range_is_on_the_reference_clock(two_clock_packet):
    pkt = open_packet(two_clock_packet)
    assert access.events(pkt, t_tick=(1_100_000, 1_300_000)).num_rows == 1
    assert access.events(pkt, t_tick=(1_300_000, 1_400_000)).num_rows == 0


# -- seconds (Part 01 §2.2) ----------------------------------------------------------------


def test_the_origin_is_read_not_recomputed(two_clock_packet):
    """The writer took the minimum across clocks through the anchor map; a reader repeats none of it."""
    assert clocks.origin(open_packet(two_clock_packet))[0] == 1_000_000


def test_seconds_run_from_the_declared_origin(two_clock_packet):
    """A spike at probe tick 30,000 is harp tick 1,031,250, one harp second past the origin."""
    found = access.spike_times(open_packet(two_clock_packet), UNITS[0], seconds=True)
    assert found.column("t_tick").to_pylist() == [1_031_250, 1_062_500]
    assert found.column("t_second").to_pylist() == [1.0, 2.0]


def test_seconds_are_derived_beside_the_tick_not_instead_of_it(two_clock_packet):
    found = access.events(open_packet(two_clock_packet), seconds=True)
    assert "t_tick" in found.column_names
    assert found.column("t_second").to_pylist() == [pytest.approx(6.4)]


def test_seconds_may_be_negative(two_clock_packet):
    """Part 01 §2.2: data outside its window is reported, not clamped away."""
    before = pa.table({"t_tick": pa.array([968_750], type=pa.int64()), "clock_id": pa.array([CLOCK_BEHAVIOUR])})
    assert clocks.seconds(open_packet(two_clock_packet), before).column("t_second").to_pylist() == [-1.0]


def test_a_packet_with_no_origin_refuses_rather_than_inventing_one(packet_root):
    """Part 01 §2.2: tick zero, the wall clock and the first datum are all available and all wrong."""
    with pytest.raises(NoTimeOrigin):
        clocks.origin(open_packet(packet_root))[0]


def test_seconds_refuse_ticks_that_are_not_on_the_reference(two_clock_packet):
    """Seconds from a probe tick would be a different quantity wearing the same name."""
    packet = open_packet(two_clock_packet)
    with pytest.raises(NotAligned):
        clocks.seconds(packet, access.spike_times(packet, UNITS[0], clock=STORED))


def test_mapping_uses_the_bound_the_writer_established(two_clock_packet, tmp_path):
    """Part 01 §3.9: a reader mapping at a narrower bound drops rows the packet's own derived
    table kept, and the two then disagree about which spikes exist."""
    import json
    import shutil

    root = tmp_path / "wide"
    shutil.copytree(two_clock_packet, root)
    manifest = json.loads((root / "packet.json").read_text())
    # The bound is on the session (Part 02 §12.6), so this widens the packet's own session row
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
    assert clocks.on_clock(packet, far).num_rows == 1
    assert clocks.on_clock(packet, far, bound=1.0).num_rows == 0

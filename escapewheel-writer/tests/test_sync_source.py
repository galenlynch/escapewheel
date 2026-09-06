"""The sync adapter turns shared pulses into anchors, and refuses the unaligned stubs."""

from datetime import datetime, timezone
from itertools import pairwise

import numpy as np
import pytest

from escapewheel_writer.clock import HARP_TICK_RATE_HZ
from escapewheel_writer.sources import SourceDefect, SyncSource
from escapewheel_writer.sources.sync import phase_discontinuities, suspect_terminals
from tests import syncfixture
from tests.syncfixture import AP_HZ, FIRST_SAMPLE, HARP_START, N_PULSES

SESSION = "ecephys_837772_2026-06-27_14-08-21"


@pytest.fixture
def tree(tmp_path):
    return syncfixture.build(tmp_path)


@pytest.fixture
def source(tree):
    return SyncSource(tree, session_id=SESSION, first_samples={f"experiment1.{k}": v for k, v in FIRST_SAMPLE.items()})


#: Real usage names a clock only for streams that carry ticks; the NI-DAQ does not.
def probes_only(stream):
    return f"{stream.key}.samples" if "probe" in stream.stream else None


def anchors_of(source, **kwargs):
    kwargs.setdefault("clock_id_for", probes_only)
    rows = source.anchors(**kwargs)
    by_clock = {}
    for r in rows:
        by_clock.setdefault(r["clock_id"], []).append((r["t_tick"], r["parent_tick"]))
    return by_clock


# -- which streams are usable ---------------------------------------------------------


def test_a_tree_without_record_nodes_is_a_defect(tmp_path):
    with pytest.raises(SourceDefect, match="no Record Node"):
        SyncSource(tmp_path, session_id=SESSION)


def test_it_finds_every_stream_both_nodes_saw(source):
    """Each node lists all four; only its own are aligned."""
    assert len(source.streams()) == 8


def test_only_the_owned_streams_are_aligned(source):
    """The archive rig-qc leaves is the only signal, so ownership is detected."""
    aligned = {(s.node, s.stream) for s in source.aligned()}
    assert aligned == {
        ("109", "Neuropix-PXI-100.probeA"),
        ("109", "Neuropix-PXI-100.probeB"),
        ("109", "NI-DAQmx-107"),  # 111's is the same device recorded twice; see below
        ("111", "Neuropix-PXI-100.probeC"),
    }


def test_a_stub_is_skipped_and_reported(source):
    """Its seconds are acquisition-local; taken at face value they are 17.7 Ms out."""
    source.aligned()
    assert any("Neuropix-PXI-100.probeC" in n and "acquisition-local" in n for n in source.notes)
    assert sum("skipped" in n for n in source.notes) == 3


def test_a_tree_with_nothing_aligned_is_a_defect(tmp_path):
    events = tmp_path / "Record Node 109" / "experiment1" / "recording1" / "events"
    syncfixture.stream(events, "Neuropix-PXI-100.probeA", first_sample=1000, aligned=False)
    with pytest.raises(SourceDefect, match="no stream .* carries HARP-aligned"):
        SyncSource(tmp_path, session_id=SESSION).aligned()


def test_an_absent_experiment_is_a_defect(tree):
    with pytest.raises(SourceDefect, match="no TTL events"):
        SyncSource(tree, session_id=SESSION, experiment="experiment9").streams()


# -- the anchors -----------------------------------------------------------------------


def test_ticks_are_recording_relative(source):
    """`spikes.npy` indexes the recording, so a raw counter must lose its acquisition base."""
    by_clock = anchors_of(source)
    ticks = [t for t, _ in by_clock["experiment1.Neuropix-PXI-100.probeA.samples"]]
    assert ticks == [1000 + i * AP_HZ for i in range(N_PULSES)]


def test_parent_ticks_are_harp(source):
    by_clock = anchors_of(source)
    parents = [p for _, p in by_clock["experiment1.Neuropix-PXI-100.probeB.samples"]]
    assert parents[0] == round(HARP_START * HARP_TICK_RATE_HZ)
    assert np.allclose(np.diff(parents), HARP_TICK_RATE_HZ)


def test_the_same_pulse_lands_on_the_same_parent_tick(source):
    """Two streams, one physical pulse: the anchor into HARP must agree."""
    by_clock = anchors_of(source)
    a = [p for _, p in by_clock["experiment1.Neuropix-PXI-100.probeA.samples"]]
    b = [p for _, p in by_clock["experiment1.Neuropix-PXI-100.probeB.samples"]]
    assert a == b


def test_anchor_index_is_contiguous_from_zero(source):
    rows = source.anchors(clock_id_for=probes_only)
    for clock in {r["clock_id"] for r in rows}:
        indices = [r["anchor_index"] for r in rows if r["clock_id"] == clock]
        assert indices == list(range(len(indices)))


def test_both_sequences_increase_together(source):
    """R13 §3: interpolation is only defined if they do."""
    for pairs in anchors_of(source).values():
        ticks, parents = zip(*pairs, strict=True)
        assert all(b > a for a, b in pairwise(ticks))
        assert all(b > a for a, b in pairwise(parents))


def test_a_stream_may_decline_a_clock(source):
    """The NI-DAQ records the pulse and carries no ticks, so it anchors to nothing."""
    rows = source.anchors(clock_id_for=lambda s: None if "NI-DAQ" in s.stream else f"{s.key}.samples")
    assert not [r for r in rows if "NI-DAQ" in r["clock_id"]]
    assert any("anchored to nothing" in n for n in source.notes)


def test_a_counter_that_goes_backwards_is_refused(tmp_path):
    """R27 §6: a reset mid-recording is two clocks, and this is not one of them."""
    events = tmp_path / "Record Node 109" / "experiment1" / "recording1" / "events"
    ttl = syncfixture.stream(events, "Neuropix-PXI-100.probeA", first_sample=1000, aligned=True)
    ts = np.load(ttl / "timestamps.npy")
    ts[6:] -= 500.0  # the counter reset
    np.save(ttl / "timestamps.npy", ts)
    source = SyncSource(tmp_path, session_id=SESSION, first_samples={"experiment1.Neuropix-PXI-100.probeA": 1000})
    with pytest.raises(SourceDefect, match="do not increase on both clocks"):
        source.anchors(clock_id_for=probes_only)


def test_a_line_with_no_edges_is_a_defect(source):
    with pytest.raises(SourceDefect, match="no rising edge on line 7"):
        SyncSource(
            source.root,
            session_id=SESSION,
            sync_line=7,
            first_samples={f"experiment1.{k}": v for k, v in FIRST_SAMPLE.items()},
        ).anchors(clock_id_for=probes_only)


# -- the first sample ------------------------------------------------------------------


def test_the_first_sample_is_read_from_disk_when_not_supplied(tmp_path):
    """Element 0 of a 1.3 GB array, memory-mapped, so the file is never touched."""
    syncfixture.build(tmp_path, with_continuous=True)
    source = SyncSource(tmp_path, session_id=SESSION)
    rows = source.anchors(clock_id_for=lambda s: f"{s.key}.samples" if "probe" in s.stream else None)
    first = min(r["t_tick"] for r in rows if r["clock_id"] == "experiment1.Neuropix-PXI-100.probeA.samples")
    assert first == 1000


def test_without_it_the_counter_cannot_be_made_relative(tree):
    with pytest.raises(SourceDefect, match="no first sample supplied"):
        SyncSource(tree, session_id=SESSION).anchors(clock_id_for=probes_only)


# -- the reference clock ----------------------------------------------------------------


def test_the_reference_clock_is_harp_and_claims_no_epoch(source):
    """HARP free-runs from power-on and an events tree does not record when that was."""
    clock = source.clock()
    assert (clock.clock_id, clock.tick_rate_num) == ("harp", HARP_TICK_RATE_HZ)
    assert clock.record().get("tick_zero_utc") is None
    assert clock.record().get("parent_clock_id") is None


def test_a_prefix_reaches_the_clock_and_the_anchors(tree):
    source = SyncSource(
        tree, session_id=SESSION, prefix="A_", first_samples={f"experiment1.{k}": v for k, v in FIRST_SAMPLE.items()}
    )
    assert source.clock().clock_id == "A_harp"
    rows = source.anchors(clock_id_for=lambda st: f"A_{st.key}.samples" if "probe" in st.stream else None)
    assert all(r["clock_id"].startswith("A_") for r in rows)


def test_one_device_recorded_by_two_nodes_is_kept_once(source):
    """Real rigs do this: 776259 has Record Nodes 109 and 111 subscribed to one NI-DAQ, with
    identical events and HARP seconds that disagree by 70 us. One device is one clock."""
    daq = [s for s in source.aligned() if s.stream == "NI-DAQmx-107"]
    assert [s.node for s in daq] == ["109"]
    assert any("records the same" in note and "disagree by up to" in note for note in source.notes)


def test_uid_stays_unique_where_key_does_not(source):
    """`key` matches what a sorted folder calls the data and omits the node, so it cannot
    identify a stream on a two-node rig; `uid` can."""
    every = source.streams()
    daq = [s for s in every if s.stream == "NI-DAQmx-107"]
    assert len(daq) == 2
    assert len({s.key for s in daq}) == 1
    assert len({s.uid for s in daq}) == 2


def test_a_node_qualified_first_sample_wins(source, tmp_path):
    """A caller that distinguishes the nodes must not have its value ignored."""
    stream = next(s for s in source.aligned() if s.stream == "NI-DAQmx-107")
    source.first_samples = {stream.key: 111, stream.uid: 222}
    assert source._first_sample(stream) == 222


# -- the terminal-anchor test (R37 §3.2) -----------------------------------------------

#: Enough anchors for `suspect_terminals` to have an interior to judge against.
LONG = 200


def _train(displacement=0):
    """A clean anchor train at 30 kHz against 31,250, with the first anchor displaced."""
    ticks = np.arange(LONG, dtype=np.int64) * AP_HZ + 1000
    parents = np.rint(ticks * (HARP_TICK_RATE_HZ / AP_HZ)).astype(np.int64) + 553_191_712_312
    parents[0] += displacement
    return ticks, parents


def test_a_clean_train_withholds_nothing():
    first, last, _ = suspect_terminals(*_train())
    assert (first, last) == (False, False)


def test_a_displaced_first_anchor_is_withheld():
    """The upstream defect R37 §5 traces: only the first anchor of a stream is misplaced."""
    first, last, residuals = suspect_terminals(*_train(displacement=200))
    assert (first, last) == (True, False)
    assert residuals["first"] == pytest.approx(200, abs=2)
    assert residuals["threshold"] < 200


def test_too_short_a_train_is_not_judged():
    """Two anchors define no interior, so there is no distribution to be an outlier of."""
    ticks, parents = _train()
    assert suspect_terminals(ticks[:5], parents[:5]) == (False, False, {})


# -- the reference clock's window (R38 §2.1) -------------------------------------------


def test_the_harp_window_spans_the_sync_train(source):
    """HARP-native, so the window needs no conversion -- which is the shape's whole point."""
    source.anchors(clock_id_for=probes_only)
    (window,) = source.observation_intervals()
    assert window["clock_id"] == "harp"
    assert window["start_tick"] == round(HARP_START * HARP_TICK_RATE_HZ)
    assert window["stop_tick"] == round((HARP_START + N_PULSES - 1) * HARP_TICK_RATE_HZ)


def test_no_window_before_the_anchors_are_read(source):
    """The span is what reading the pulses saw, so there is nothing to say before that."""
    assert source.observation_intervals() == []


def test_reading_the_anchors_twice_reads_the_pulses_once(source):
    """`build` asks for them once to locate tick 0 and once to write them."""
    source.anchors(clock_id_for=probes_only)
    before = len(source.notes)
    source.anchors(clock_id_for=probes_only)
    assert len(source.notes) == before
    assert len(source.observation_intervals()) == 1


# -- what the record node itself says ---------------------------------------------------


def test_a_node_states_when_it_began_and_where_every_counter_stood(tmp_path):
    """`sync_messages.txt` is the one file in an ecephys asset carrying a real UTC instant."""
    tree = syncfixture.build(tmp_path, with_sync_messages=True)
    source = SyncSource(tree, session_id=SESSION)
    stream = next(s for s in source.aligned() if s.node == "109")
    started = source.started(stream)
    assert started.started == datetime(2025, 4, 10, 0, 25, 12, 90_000, tzinfo=timezone.utc)
    assert started.samples["Neuropix-PXI-100.probeA"] == FIRST_SAMPLE["Neuropix-PXI-100.probeA"]
    # It lists every stream the node saw, owned or not, as the TTL directories do.
    assert set(FIRST_SAMPLE) <= set(started.samples)


def test_the_node_supplies_the_first_sample_nobody_else_did(tmp_path):
    """Which is where a hand-made first_samples.json got its numbers anyway."""
    tree = syncfixture.build(tmp_path, with_sync_messages=True)
    told = anchors_of(
        SyncSource(tree, session_id=SESSION, first_samples={f"experiment1.{k}": v for k, v in FIRST_SAMPLE.items()})
    )
    found = anchors_of(SyncSource(tree, session_id=SESSION))
    assert found == told


def test_a_supplied_first_sample_still_wins(tmp_path):
    """A caller that states one has a reason, and the node cannot know it."""
    tree = syncfixture.build(tmp_path, with_sync_messages=True)
    key = "experiment1.Neuropix-PXI-100.probeA"
    shifted = anchors_of(
        SyncSource(tree, session_id=SESSION, first_samples={key: FIRST_SAMPLE[key.split(".", 1)[1]] + 7})
    )
    # probeA's first pulse is 1000 samples into the recording, so overstating where the
    # recording began by seven puts that pulse seven ticks earlier.
    assert shifted["experiment1.Neuropix-PXI-100.probeA.samples"][0][0] == 1000 - 7


def test_without_the_file_the_older_routes_still_apply(tree):
    """A tree with neither the file nor the counter array refuses rather than guessing."""
    source = SyncSource(tree, session_id=SESSION)
    with pytest.raises(SourceDefect, match="sync_messages"):
        source.anchors(clock_id_for=probes_only)
    assert any("no sync_messages.txt" in note for note in source.notes)


# -- phase discontinuities in the parent's alignment ------------------------------------


def _straight(n=200, ratio=HARP_TICK_RATE_HZ / AP_HZ):
    ticks = np.arange(n, dtype=np.int64) * AP_HZ + 1000
    return ticks, np.rint(ticks * ratio).astype(np.int64) + 553_191_712_312


def test_a_clean_alignment_reports_nothing():
    assert phase_discontinuities(*_straight(), HARP_TICK_RATE_HZ) == []


def test_a_phase_step_is_found_and_sized():
    """A permanent step: the parent falls behind and stays behind."""
    ticks, parents = _straight()
    parents[100:] -= 50  # 50 harp ticks = 1.6 ms, the size measured upstream
    (found,) = phase_discontinuities(ticks, parents, HARP_TICK_RATE_HZ)
    assert found["seconds"] == pytest.approx(-50 / HARP_TICK_RATE_HZ)
    assert found["t_tick"] == ticks[99]


def test_a_step_spread_over_two_intervals_is_one_event(source):
    """Upstream it arrives as a ramp, because the alignment absorbs it across a dropped anchor."""
    ticks, parents = _straight()
    parents[100] -= 25
    parents[101:] -= 50
    (found,) = phase_discontinuities(ticks, parents, HARP_TICK_RATE_HZ)
    assert found["anchor_intervals"] == 2
    assert found["seconds"] == pytest.approx(-50 / HARP_TICK_RATE_HZ)


def test_ordinary_quantisation_is_not_a_discontinuity():
    """Half a parent tick of rounding on every anchor must not be reported."""
    ticks, parents = _straight()
    rng = np.random.default_rng(0)
    parents += rng.integers(-2, 3, parents.size)
    assert phase_discontinuities(ticks, parents, HARP_TICK_RATE_HZ) == []


def test_the_limit_is_a_duration(source):
    ticks, parents = _straight()
    parents[100:] -= 20  # 640 µs
    assert phase_discontinuities(ticks, parents, HARP_TICK_RATE_HZ, limit=1e-3) == []
    assert phase_discontinuities(ticks, parents, HARP_TICK_RATE_HZ, limit=1e-4)

"""When something was observing, and what a rate is divided by (R38).

The fixture uses a 1 kHz clock observing ticks 0 to 999, so a window's length in ticks and in
milliseconds are the same number and every expectation can be read off by hand. `unit_002`
refines that to 100..599; `unit_001` declares nothing and inherits.
"""

import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from escapewheel_reader import open_packet
from escapewheel_reader.observation import (
    DECLARED,
    INHERITED,
    StaleSupport,
    attach_support,
    clock_windows,
    observed_seconds,
    observed_ticks,
    rate,
    rate_of,
    register_views,
    stream_windows,
    support_of,
    unit_windows,
)

from .conftest import CLOCK_BEHAVIOUR, CURATION, SESSION, SORTING_RUN, UNITS, _resource, _write

CLOCK = CLOCK_BEHAVIOUR
LICKS, CUES = 30, 31


def _extend(root, manifest, **tables):
    """Write extra core tables into a copied packet and declare them."""
    for name, table in tables.items():
        manifest["resources"].append(_resource(f"core.{name}", _write(root, name, table)))
    return manifest


@pytest.fixture
def observed_packet(tmp_path, packet_root):
    """A packet whose clock observes 0..999, with one unit refining and one inheriting."""
    root = tmp_path / "observed"
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())
    _extend(
        root,
        manifest,
        clocks=pa.table(
            {
                "clock_id": pa.array([CLOCK]),
                "session_id": pa.array([SESSION]),
                "tick_rate_hz": pa.array([1000.0]),
                "tick_rate_num": pa.array([1000], type=pa.int64()),
                "tick_rate_den": pa.array([1], type=pa.int64()),
            }
        ),
        sorting_runs=pa.table(
            {
                "sorting_run_id": pa.array([SORTING_RUN]),
                "session_id": pa.array([SESSION]),
            }
        ),
        units=pa.table(
            {
                "session_id": pa.array([SESSION] * 2, type=pa.int32()),
                "unit_id": pa.array(list(UNITS[:2]), type=pa.int32()),
                "sorting_run_id": pa.array([SORTING_RUN] * 2, type=pa.int32()),
                "curation_id": pa.array([CURATION] * 2, type=pa.int32()),
                "quality_label": pa.array(["sua", "mua"]),
                # R96 §3.2: the unit names the clock, so this fixture's units name CLOCK.
                "clock_id": pa.array([CLOCK] * 2, type=pa.int32()),
            }
        ),
        clock_observation_intervals=pa.table(
            {
                "session_id": pa.array([SESSION]),
                "clock_id": pa.array([CLOCK]),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([0], type=pa.int64()),
                "stop_tick": pa.array([999], type=pa.int64()),
            }
        ),
        unit_observation_intervals=pa.table(
            {
                "session_id": pa.array([SESSION]),
                "unit_id": pa.array([UNITS[1]]),
                "sorting_run_id": pa.array([SORTING_RUN]),
                "curation_id": pa.array([CURATION]),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([100], type=pa.int64()),
                "stop_tick": pa.array([599], type=pa.int64()),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


def test_a_unit_without_its_own_window_inherits_its_clocks(observed_packet):
    """R38 §2.2: the clock is where observation lives, and a unit reaches it via its run."""
    rows = {r["unit_id"]: r for r in unit_windows(observed_packet).to_pylist()}
    assert rows[UNITS[0]]["source"] == INHERITED
    assert (rows[UNITS[0]]["start_tick"], rows[UNITS[0]]["stop_tick"]) == (0, 999)
    assert rows[UNITS[0]]["clock_id"] == CLOCK


def test_a_refinement_replaces_the_inherited_window(observed_packet):
    """Not adds. Keeping both would widen the span the refinement narrowed."""
    rows = [r for r in unit_windows(observed_packet).to_pylist() if r["unit_id"] == UNITS[1]]
    assert len(rows) == 1
    assert rows[0]["source"] == DECLARED
    assert (rows[0]["start_tick"], rows[0]["stop_tick"]) == (100, 599)


def test_both_ends_are_observed(observed_packet):
    """R18 §2 and R38 §2.2 make the interval closed, so 0..999 is 1000 ticks and not 999."""
    rows = unit_windows(observed_packet)
    first = rows.filter(pa.compute.equal(rows.column("unit_id"), UNITS[0]))
    assert observed_ticks(first) == 1000
    second = rows.filter(pa.compute.equal(rows.column("unit_id"), UNITS[1]))
    assert observed_ticks(second) == 500


def test_seconds_come_from_the_clocks_declared_rate(observed_packet):
    """A 1 kHz clock makes 1000 ticks one second, which is what a rate divides by."""
    rows = unit_windows(observed_packet)
    first = rows.filter(pa.compute.equal(rows.column("unit_id"), UNITS[0]))
    assert observed_seconds(observed_packet, first) == pytest.approx(1.0)
    assert rate(3, observed_seconds(observed_packet, first)) == pytest.approx(3.0)


def test_the_two_units_do_not_share_a_denominator(observed_packet):
    """The whole point: the same count over the two windows is two different rates."""
    rows = unit_windows(observed_packet)
    one = rows.filter(pa.compute.equal(rows.column("unit_id"), UNITS[0]))
    two = rows.filter(pa.compute.equal(rows.column("unit_id"), UNITS[1]))
    assert rate(10, observed_seconds(observed_packet, one)) == pytest.approx(10.0)
    assert rate(10, observed_seconds(observed_packet, two)) == pytest.approx(20.0)


def test_a_rate_over_nothing_is_refused(observed_packet):
    """Undefined, not zero. Dividing by an unobserved span is the error this exists to stop."""
    with pytest.raises(ValueError, match="undefined, not zero"):
        rate(5, 0.0)


def test_a_clock_without_a_rate_is_refused(tmp_path, observed_packet):
    """Skipping it would silently shorten the denominator, which is the wrong direction."""
    path = observed_packet.root / "tables" / "core" / "clocks.parquet"
    clocks = pq.read_table(path)
    blank = pa.table(
        {
            "clock_id": clocks.column("clock_id"),
            "session_id": clocks.column("session_id"),
            "tick_rate_hz": pa.array([None], type=pa.float64()),
            "tick_rate_num": pa.array([None], type=pa.int64()),
            "tick_rate_den": pa.array([None], type=pa.int64()),
        }
    )
    pq.write_table(blank, path, compression="zstd")
    packet = open_packet(observed_packet.root)
    with pytest.raises(KeyError, match="declares no tick rate"):
        observed_seconds(packet, unit_windows(packet))


def test_a_packet_without_observation_tables_invents_nothing(packet_root):
    """Conforming under R9 §5, so this is empty rather than an error or a guessed extent."""
    packet = open_packet(packet_root)
    assert clock_windows(packet).num_rows == 0
    assert unit_windows(packet).num_rows == 0
    assert stream_windows(packet).num_rows == 0


def test_the_sql_view_agrees_with_the_function(observed_packet):
    """Drift protection. Two implementations of one rule agree only if something checks."""
    con = observed_packet.duckdb(tables="all")
    columns = [
        "session_id",
        "unit_id",
        "clock_id",
        "start_tick",
        "stop_tick",
        "source",
    ]
    from_sql = sorted(con.sql(f"SELECT {', '.join(columns)} FROM unit_observation").fetchall())
    from_arrow = sorted(tuple(r[c] for c in columns) for r in unit_windows(observed_packet).to_pylist())
    assert from_sql == from_arrow


def test_the_view_survives_a_packet_with_no_refinements(tmp_path, packet_root):
    """The common shape: units inherit, so the refinement table is never written.

    DuckDB binds a view at creation, so a single statement naming that table would fail to
    register on exactly the packets the view is most useful for.
    """
    root = tmp_path / "unrefined"
    shutil.copytree(packet_root, root)
    manifest = json.loads((root / "packet.json").read_text())
    _extend(
        root,
        manifest,
        clocks=pa.table(
            {
                "clock_id": pa.array([CLOCK]),
                "session_id": pa.array([SESSION]),
                "tick_rate_hz": pa.array([1000.0]),
                "tick_rate_num": pa.array([1000], type=pa.int64()),
                "tick_rate_den": pa.array([1], type=pa.int64()),
            }
        ),
        sorting_runs=pa.table(
            {
                "sorting_run_id": pa.array([SORTING_RUN]),
                "session_id": pa.array([SESSION]),
            }
        ),
        units=pa.table(
            {
                "session_id": pa.array([SESSION] * 2, type=pa.int32()),
                "unit_id": pa.array(list(UNITS[:2]), type=pa.int32()),
                "sorting_run_id": pa.array([SORTING_RUN] * 2, type=pa.int32()),
                "curation_id": pa.array([CURATION] * 2, type=pa.int32()),
                "quality_label": pa.array(["sua", "mua"]),
                # R96 §3.2: the unit names the clock, so this fixture's units name CLOCK.
                "clock_id": pa.array([CLOCK] * 2, type=pa.int32()),
            }
        ),
        clock_observation_intervals=pa.table(
            {
                "session_id": pa.array([SESSION]),
                "clock_id": pa.array([CLOCK]),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([0], type=pa.int64()),
                "stop_tick": pa.array([999], type=pa.int64()),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    packet = open_packet(root)
    con = packet.duckdb(tables="all")
    assert con.sql("SELECT count(*) FROM unit_observation").fetchone()[0] == 2
    assert {r[0] for r in con.sql("SELECT DISTINCT source FROM unit_observation").fetchall()} == {INHERITED}


def test_no_observation_tables_registers_no_view(packet_root):
    """A view over nothing would look answered. Absent is the honest state."""
    packet = open_packet(packet_root)
    assert register_views(packet.duckdb(tables="all")) == []


@pytest.fixture
def stream_packet(tmp_path, observed_packet):
    """Two event streams on the observed clock, one of them refining its window."""
    root = observed_packet.root
    manifest = json.loads((root / "packet.json").read_text())
    _extend(
        root,
        manifest,
        event_streams=pa.table(
            {
                "event_stream_id": pa.array([LICKS, CUES], type=pa.int32()),
                "session_id": pa.array([SESSION, SESSION]),
                "name": pa.array(["licks", "cues"]),
                "clock_id": pa.array([CLOCK, CLOCK]),
            }
        ),
        event_stream_observation_intervals=pa.table(
            {
                "event_stream_id": pa.array([LICKS], type=pa.int32()),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([200], type=pa.int64()),
                "stop_tick": pa.array([899], type=pa.int64()),
            }
        ),
    )
    (root / "packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


def test_a_stream_refines_or_inherits_like_a_unit(stream_packet):
    """R38 §2.2 gives streams the same inheritance, which is why they share a resolution."""
    rows = {r["event_stream_id"]: r for r in stream_windows(stream_packet).to_pylist()}
    assert rows[LICKS]["source"] == DECLARED
    assert (rows[LICKS]["start_tick"], rows[LICKS]["stop_tick"]) == (200, 899)
    assert rows[CUES]["source"] == INHERITED
    assert (rows[CUES]["start_tick"], rows[CUES]["stop_tick"]) == (0, 999)


def test_a_streams_denominator_is_its_own(stream_packet):
    """700 ticks against 1000, so the same count is not the same rate."""
    rows = stream_windows(stream_packet)
    licks = rows.filter(pa.compute.equal(rows.column("event_stream_id"), LICKS))
    assert observed_ticks(licks) == 700
    assert observed_seconds(stream_packet, licks) == pytest.approx(0.7)


def test_the_stream_view_agrees_with_the_function(stream_packet):
    """Drift protection for the second view, as for the first."""
    con = stream_packet.duckdb(tables="all")
    columns = ["event_stream_id", "clock_id", "start_tick", "stop_tick", "source"]
    from_sql = sorted(con.sql(f"SELECT {', '.join(columns)} FROM stream_observation").fetchall())
    from_arrow = sorted(tuple(r[c] for c in columns) for r in stream_windows(stream_packet).to_pylist())
    assert from_sql == from_arrow


# -- support carried on the result (option B, guarded by a fingerprint) ------------------


def test_a_single_unit_read_carries_its_support(observed_packet):
    """So a rate needs no second lookup on the path where the answer is unambiguous."""
    spikes = observed_packet.spike_times(UNITS[0])
    carried = support_of(spikes)
    assert carried is not None
    assert carried.to_pylist() == [{"clock_id": CLOCK, "start_tick": 0, "stop_tick": 999}]
    assert rate_of(observed_packet, spikes) == pytest.approx(spikes.num_rows / 1.0)


def test_a_refined_unit_carries_its_own_window(observed_packet):
    """The attachment follows the resolution, so a refinement reaches the denominator."""
    carried = support_of(observed_packet.spike_times(UNITS[1]))
    assert carried.to_pylist() == [{"clock_id": CLOCK, "start_tick": 100, "stop_tick": 599}]


def test_filtering_invalidates_the_support_loudly(observed_packet):
    """Arrow keeps metadata through a filter, so without the fingerprint this would silently
    divide by a window the remaining rows no longer span."""
    spikes = observed_packet.spike_times(UNITS[0])
    fewer = spikes.slice(0, 1)
    with pytest.raises(StaleSupport, match="read it again"):
        support_of(fewer)
    with pytest.raises(StaleSupport):
        rate_of(observed_packet, fewer)


def test_concatenation_is_caught_too(observed_packet):
    """The other direction: more rows over the same window would read as a doubled rate."""
    spikes = observed_packet.spike_times(UNITS[0])
    with pytest.raises(StaleSupport):
        support_of(pa.concat_tables([spikes, spikes]))


def test_reordering_and_projection_stay_valid(observed_packet):
    """Neither changes which rows the support describes, so neither should be refused."""
    spikes = observed_packet.spike_times(UNITS[0])
    expected = rate_of(observed_packet, spikes)
    assert rate_of(observed_packet, spikes.sort_by("t_tick")) == pytest.approx(expected)
    assert rate_of(observed_packet, spikes.select(["t_tick"])) == pytest.approx(expected)


def test_a_range_narrowed_read_carries_no_support(observed_packet):
    """The span is the caller's choice, so the observation window is no denominator for it."""
    narrowed = observed_packet.spike_times(UNITS[0], t_tick=(0, 100))
    assert support_of(narrowed) is None
    with pytest.raises(LookupError, match="no support"):
        rate_of(observed_packet, narrowed)


def test_a_many_unit_read_carries_no_support(observed_packet):
    """Two units with different windows have no single denominator, so none is attached."""
    spikes = observed_packet.spike_times(units=observed_packet.units())
    assert support_of(spikes) is None


def test_attaching_an_empty_support_attaches_nothing(observed_packet):
    """Absent, not empty: an empty attachment would read as a declared zero-length window."""
    bare = observed_packet.table("core.spike_events", columns=["t_tick"])
    assert support_of(bare) is None
    assert support_of(attach_support(bare, unit_windows(observed_packet).slice(0, 0))) is None


def test_a_view_is_skipped_while_its_refinements_table_is_unregistered(observed_packet):
    """The hazard lazy registration introduces: a partial connection answering instead of not.

    Without `core_unit_observation_intervals` registered, the guard that drops an inherited
    window for a unit that declares its own is omitted, and the view would return a wider span
    for every refined unit. Refusing to build it is what keeps a subset from being wrong.
    """
    con = observed_packet.duckdb(tables=["core.units", "core.sorting_runs", "core.clock_observation_intervals"])
    assert "unit_observation" not in {
        r[0] for r in con.sql("SELECT view_name FROM duckdb_views() WHERE NOT internal").fetchall()
    }
    observed_packet.duckdb(connection=con, tables=["core.unit_observation_intervals"])
    from_sql = con.sql("SELECT count(*) FROM unit_observation").fetchone()
    assert from_sql == (unit_windows(observed_packet).num_rows,)

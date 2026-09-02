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

from nwb_lake_reader import open_packet
from nwb_lake_reader.observation import (
    DECLARED,
    INHERITED,
    clock_windows,
    observed_seconds,
    observed_ticks,
    rate,
    register_views,
    stream_windows,
    unit_windows,
)

from .conftest import _resource, _write

CLOCK = "behavior_s001"


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
    manifest = json.loads((root / "nwb.packet.json").read_text())
    _extend(
        root,
        manifest,
        clocks=pa.table(
            {
                "clock_id": pa.array([CLOCK]),
                "session_id": pa.array(["s001"]),
                "tick_rate_hz": pa.array([1000.0]),
                "tick_rate_num": pa.array([1000], type=pa.int64()),
                "tick_rate_den": pa.array([1], type=pa.int64()),
            }
        ),
        sorting_runs=pa.table(
            {
                "sorting_run_id": pa.array(["sort_001"]),
                "session_id": pa.array(["s001"]),
                "clock_id": pa.array([CLOCK]),
            }
        ),
        clock_observation_intervals=pa.table(
            {
                "session_id": pa.array(["s001"]),
                "clock_id": pa.array([CLOCK]),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([0], type=pa.int64()),
                "stop_tick": pa.array([999], type=pa.int64()),
            }
        ),
        unit_observation_intervals=pa.table(
            {
                "session_id": pa.array(["s001"]),
                "unit_id": pa.array(["unit_002"]),
                "sorting_run_id": pa.array(["sort_001"]),
                "curation_id": pa.array(["cur_001"]),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([100], type=pa.int64()),
                "stop_tick": pa.array([599], type=pa.int64()),
            }
        ),
    )
    (root / "nwb.packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


def test_a_unit_without_its_own_window_inherits_its_clocks(observed_packet):
    """R38 §2.2: the clock is where observation lives, and a unit reaches it via its run."""
    rows = {r["unit_id"]: r for r in unit_windows(observed_packet).to_pylist()}
    assert rows["unit_001"]["source"] == INHERITED
    assert (rows["unit_001"]["start_tick"], rows["unit_001"]["stop_tick"]) == (0, 999)
    assert rows["unit_001"]["clock_id"] == CLOCK


def test_a_refinement_replaces_the_inherited_window(observed_packet):
    """Not adds. Keeping both would widen the span the refinement narrowed."""
    rows = [r for r in unit_windows(observed_packet).to_pylist() if r["unit_id"] == "unit_002"]
    assert len(rows) == 1
    assert rows[0]["source"] == DECLARED
    assert (rows[0]["start_tick"], rows[0]["stop_tick"]) == (100, 599)


def test_both_ends_are_observed(observed_packet):
    """R18 §2 and R38 §2.2 make the interval closed, so 0..999 is 1000 ticks and not 999."""
    rows = unit_windows(observed_packet)
    first = rows.filter(pa.compute.equal(rows.column("unit_id"), "unit_001"))
    assert observed_ticks(first) == 1000
    second = rows.filter(pa.compute.equal(rows.column("unit_id"), "unit_002"))
    assert observed_ticks(second) == 500


def test_seconds_come_from_the_clocks_declared_rate(observed_packet):
    """A 1 kHz clock makes 1000 ticks one second, which is what a rate divides by."""
    rows = unit_windows(observed_packet)
    first = rows.filter(pa.compute.equal(rows.column("unit_id"), "unit_001"))
    assert observed_seconds(observed_packet, first) == pytest.approx(1.0)
    assert rate(3, observed_seconds(observed_packet, first)) == pytest.approx(3.0)


def test_the_two_units_do_not_share_a_denominator(observed_packet):
    """The whole point: the same count over the two windows is two different rates."""
    rows = unit_windows(observed_packet)
    one = rows.filter(pa.compute.equal(rows.column("unit_id"), "unit_001"))
    two = rows.filter(pa.compute.equal(rows.column("unit_id"), "unit_002"))
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
    con = observed_packet.duckdb()
    columns = [
        "session_id",
        "unit_id",
        "sorting_run_id",
        "curation_id",
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
    manifest = json.loads((root / "nwb.packet.json").read_text())
    _extend(
        root,
        manifest,
        clocks=pa.table(
            {
                "clock_id": pa.array([CLOCK]),
                "session_id": pa.array(["s001"]),
                "tick_rate_hz": pa.array([1000.0]),
                "tick_rate_num": pa.array([1000], type=pa.int64()),
                "tick_rate_den": pa.array([1], type=pa.int64()),
            }
        ),
        sorting_runs=pa.table(
            {"sorting_run_id": pa.array(["sort_001"]), "session_id": pa.array(["s001"]), "clock_id": pa.array([CLOCK])}
        ),
        clock_observation_intervals=pa.table(
            {
                "session_id": pa.array(["s001"]),
                "clock_id": pa.array([CLOCK]),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([0], type=pa.int64()),
                "stop_tick": pa.array([999], type=pa.int64()),
            }
        ),
    )
    (root / "nwb.packet.json").write_text(json.dumps(manifest, indent=2))
    packet = open_packet(root)
    con = packet.duckdb()
    assert con.sql("SELECT count(*) FROM unit_observation").fetchone()[0] == 2
    assert {r[0] for r in con.sql("SELECT DISTINCT source FROM unit_observation").fetchall()} == {INHERITED}


def test_no_observation_tables_registers_no_view(packet_root):
    """A view over nothing would look answered. Absent is the honest state."""
    packet = open_packet(packet_root)
    assert register_views(packet.duckdb()) == []


@pytest.fixture
def stream_packet(tmp_path, observed_packet):
    """Two event streams on the observed clock, one of them refining its window."""
    root = observed_packet.root
    manifest = json.loads((root / "nwb.packet.json").read_text())
    _extend(
        root,
        manifest,
        event_streams=pa.table(
            {
                "event_stream_id": pa.array(["licks", "cues"]),
                "session_id": pa.array(["s001", "s001"]),
                "name": pa.array(["licks", "cues"]),
                "clock_id": pa.array([CLOCK, CLOCK]),
            }
        ),
        event_stream_observation_intervals=pa.table(
            {
                "event_stream_id": pa.array(["licks"]),
                "interval_index": pa.array([0], type=pa.int64()),
                "start_tick": pa.array([200], type=pa.int64()),
                "stop_tick": pa.array([899], type=pa.int64()),
            }
        ),
    )
    (root / "nwb.packet.json").write_text(json.dumps(manifest, indent=2))
    return open_packet(root)


def test_a_stream_refines_or_inherits_like_a_unit(stream_packet):
    """R38 §2.2 gives streams the same inheritance, which is why they share a resolution."""
    rows = {r["event_stream_id"]: r for r in stream_windows(stream_packet).to_pylist()}
    assert rows["licks"]["source"] == DECLARED
    assert (rows["licks"]["start_tick"], rows["licks"]["stop_tick"]) == (200, 899)
    assert rows["cues"]["source"] == INHERITED
    assert (rows["cues"]["start_tick"], rows["cues"]["stop_tick"]) == (0, 999)


def test_a_streams_denominator_is_its_own(stream_packet):
    """700 ticks against 1000, so the same count is not the same rate."""
    rows = stream_windows(stream_packet)
    licks = rows.filter(pa.compute.equal(rows.column("event_stream_id"), "licks"))
    assert observed_ticks(licks) == 700
    assert observed_seconds(stream_packet, licks) == pytest.approx(0.7)


def test_the_stream_view_agrees_with_the_function(stream_packet):
    """Drift protection for the second view, as for the first."""
    con = stream_packet.duckdb()
    columns = ["event_stream_id", "clock_id", "start_tick", "stop_tick", "source"]
    from_sql = sorted(con.sql(f"SELECT {', '.join(columns)} FROM stream_observation").fetchall())
    from_arrow = sorted(tuple(r[c] for c in columns) for r in stream_windows(stream_packet).to_pylist())
    assert from_sql == from_arrow

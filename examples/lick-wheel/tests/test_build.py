"""A build reads the session through the adapter into a packet, by each route a recipe can name."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from escapewheel_reader import open_packet
from escapewheel_reader.clocks import align
from escapewheel_validator.registry_types import core_registry_bytes

from session import EVENTS, WHEEL_SAMPLES, wheel_ticks, write

RECIPE = Path(__file__).parents[1] / "recipe.toml"
ESCAPEWHEEL = str(Path(sys.executable).with_name("escapewheel"))

#: How each route changes the committed recipe, which delivers over `stream-v0.1`.
ROUTES = {
    "stream-v0.1": lambda text: text,
    "files-v0.1": lambda text: text + 'protocol = "files-v0.1"\n',
    # Constructed in the build's own process, which this machine can do because it installs the
    # adapter beside the writer (Part 05 §3.9).
    "in-process": lambda text: text[: text.index("# Run in a process")] + "in_process = true\n",
}


def build(tmp_path, route="stream-v0.1", **session):
    """Lay out what the committed recipe names beside it, then run `escapewheel import`."""
    write(tmp_path / "s001", **session)
    (tmp_path / "core.json").write_bytes(core_registry_bytes())
    (tmp_path / "recipe.toml").write_text(ROUTES[route](RECIPE.read_text()))
    return subprocess.run(
        [ESCAPEWHEEL, "import", str(tmp_path / "recipe.toml")], capture_output=True, text=True, check=False
    )


@pytest.fixture(scope="module")
def packets(tmp_path_factory):
    built = {}
    for route in ROUTES:
        root = tmp_path_factory.mktemp(route)
        done = build(root, route)
        assert done.returncode == 0, done.stderr
        built[route] = open_packet(str(root / "packet"))
    return built


@pytest.mark.parametrize("route", ROUTES)
def test_every_route_commits_the_same_events(packets, route):
    events = (
        packets[route]
        .sql(
            "SELECT s.event_type, e.t_tick, e.payload FROM core_events e"
            " JOIN core_event_streams s ON s.event_stream_id = e.stream_id ORDER BY e.t_tick"
        )
        .to_pylist()
    )
    assert [(e["event_type"], e["t_tick"]) for e in events] == [(kind, tick) for tick, kind, _ in EVENTS]
    assert [json.loads(e["payload"])["volume_ul"] for e in events if e["payload"]] == [2.5, 3.0]


@pytest.mark.parametrize("route", ROUTES)
def test_every_route_commits_the_wheel_array(packets, route):
    assert packets[route].array_resource("core.wheel_position").shape == (WHEEL_SAMPLES,)


def test_a_wheel_sample_reaches_harp_through_its_anchors(packets):
    """Sample k is tick k on the wheel's clock; the anchors place it on HARP to within a tick."""
    packet = packets["stream-v0.1"]
    clocks = {row["clock_name"]: row["clock_id"] for row in packet.table("core.clocks").to_pylist()}
    anchors = packet.table("core.clock_anchors", clock_id=clocks["wheel"]).sort_by("anchor_index")
    samples = np.arange(WHEEL_SAMPLES, dtype=np.int64)
    on_harp, defined = align(samples, anchors["t_tick"].to_numpy(), anchors["parent_tick"].to_numpy())
    assert defined.all()
    assert np.abs(on_harp - wheel_ticks()).max() <= 1


def test_a_delivered_adapter_reports_what_it_states(tmp_path):
    """Out of process, `escapewheel deliver` writes the report the recipe names (Part 12 §9)."""
    done = build(tmp_path, wheel=False)
    assert done.returncode == 0, done.stderr
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["stated"] == {"subject.subject_id": "m001"}
    assert any("wheel.csv" in problem["message"] for problem in report["problems"])


@pytest.mark.parametrize("route", ["stream-v0.1", "in-process"])
def test_a_source_naming_another_subject_is_refused(tmp_path, route):
    """The subject identifies an animal across packets, so a disagreement stops the build (Part 05 §3.6)."""
    done = build(tmp_path, route, subject_id="m002")
    assert done.returncode != 0
    assert "m002" in done.stderr
    assert not (tmp_path / "packet" / "packet.json").exists()


def test_the_committed_recipe_checks_clean(tmp_path):
    write(tmp_path / "s001")
    (tmp_path / "core.json").write_bytes(core_registry_bytes())
    shutil.copy(RECIPE, tmp_path / "recipe.toml")
    done = subprocess.run(
        [ESCAPEWHEEL, "import", str(tmp_path / "recipe.toml"), "--check"], capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr

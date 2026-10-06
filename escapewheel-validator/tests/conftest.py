import pytest
from packet_fixture import write_packet

from escapewheel_validator.stores import digest

#: What the fixture packet declares of core: each table's key and the columns a test reads.
COLUMNS = {
    "core.sessions": ("session_id", "session_name", "subject_id", "session_start_time", "metadata"),
    "core.clocks": ("session_id", "clock_id", "clock_name", "metadata"),
    "core.intervals": ("session_id", "interval_id", "interval_name", "start_tick", "stop_tick", "clock_id", "metadata"),
    "core.units": (
        "session_id",
        "unit_id",
        "unit_name",
        "sorting_run_id",
        "curation_id",
        "quality_label",
        "clock_id",
        "metadata",
    ),
    "core.event_streams": ("event_stream_id", "session_id", "event_stream_name", "event_type", "clock_id", "metadata"),
    "core.events": ("session_id", "stream_id", "t_tick", "metadata"),
    "core.spike_events": ("session_id", "unit_id", "t_tick"),
}
RULES = ("core.intervals.interval_valid",)


def owned_digest(root, uri, algorithm="sha256"):
    """The `digest` a writer records for a packet-owned resource under `root` (Part 04 §4.3)."""
    return {"algorithm": algorithm, "value": digest(str(root / uri), algorithm)}


@pytest.fixture
def packet_root(tmp_path):
    """The shared packet with a digest on every entry."""
    return write_packet(tmp_path / "session_001", COLUMNS, rules=RULES, digest=owned_digest)


@pytest.fixture(autouse=True)
def _no_configured_sources(monkeypatch, tmp_path_factory):
    """Keep a developer's own resolution documents (Part 04 §5.5's second rank) out of every test."""
    monkeypatch.delenv("ESCAPEWHEEL_SOURCES", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path_factory.mktemp("config")))

"""Public logical identifier types follow the registry rather than their spelling."""

import sys
from inspect import signature
from typing import Any, Literal, get_type_hints

import duckdb

from escapewheel_reader import (
    Discriminator,
    Manifest,
    Packet,
    Resource,
    Session,
    aligned_spikes,
    assigned_spikes,
    clock_windows,
    electrode_at,
    kept_channels,
    on_clock,
    open_packet,
    origin,
    preferred_run,
    seconds,
    stream_windows,
    unit_windows,
    windows_disjoint,
)


def _column_type(registry: dict[str, Any], resource: str, column: str) -> type[Any]:
    """Map the logical scalar named by a checked symbol to its public host scalar."""
    declaration = next(c for c in registry["resources"][resource]["table"]["columns"] if c["name"] == column)
    return {"int32": int, "int64": int, "string": str}[declaration["type"]]


def _hints(symbol: Any) -> dict[str, Any]:
    """Resolve postponed annotations, including optional DuckDB annotations."""
    namespace = dict(vars(sys.modules[symbol.__module__]))
    namespace.update({"duckdb": duckdb, "DuckDBPyConnection": duckdb.DuckDBPyConnection})
    return get_type_hints(symbol, globalns=namespace)


def test_public_logical_identifier_annotations_follow_the_registry(packet_root):
    """Each mapping explicitly names the API symbol and the declaration it projects."""
    registry = open_packet(packet_root).registry
    assert registry is not None

    # (symbol, parameter, logical owner, column). A None default admits None; a required
    # parameter does not. The mapping is bounded and reviewed, not inferred from `_id`.
    mapped = [
        (Packet.intervals, "session_id", "core.sessions", "session_id"),
        (Packet.units, "session_id", "core.sessions", "session_id"),
        (Packet.events, "session_id", "core.sessions", "session_id"),
        (Packet.spike_times, "unit_id", "core.units", "unit_id"),
        (Packet.spike_times, "session_id", "core.sessions", "session_id"),
        (Packet.reference_clock, "session_id", "core.sessions", "session_id"),
        (Packet.t_zero, "session_id", "core.sessions", "session_id"),
        (Packet.seconds, "session_id", "core.sessions", "session_id"),
        (Packet.on_clock, "clock", "core.clocks", "clock_id"),
        (aligned_spikes, "session_id", "core.sessions", "session_id"),
        (assigned_spikes, "session_id", "core.sessions", "session_id"),
        (windows_disjoint, "session_id", "core.sessions", "session_id"),
        (clock_windows, "session_id", "core.sessions", "session_id"),
        (clock_windows, "clock_id", "core.clocks", "clock_id"),
        (unit_windows, "session_id", "core.sessions", "session_id"),
        (stream_windows, "session_id", "core.sessions", "session_id"),
        (origin, "session_id", "core.sessions", "session_id"),
        (on_clock, "clock", "core.clocks", "clock_id"),
        (seconds, "session_id", "core.sessions", "session_id"),
        (preferred_run, "session_id", "core.sessions", "session_id"),
        (kept_channels, "sorting_run_id", "core.units", "sorting_run_id"),
        (electrode_at, "sorting_run_id", "core.units", "sorting_run_id"),
    ]
    for symbol, parameter, resource, column in mapped:
        scalar = _column_type(registry, resource, column)
        default = signature(symbol).parameters[parameter].default
        expected = scalar | None if default is None else scalar
        assert _hints(symbol)[parameter] == expected, f"{symbol.__qualname__}.{parameter}"

    clock_type = _column_type(registry, "core.clocks", "clock_id")
    assert _hints(Packet.events)["clock"] == clock_type | Literal["stored"] | None
    assert _hints(Packet.spike_times)["clock"] == clock_type | Literal["stored"] | None

    assert _hints(Packet.reference_clock)["return"] is clock_type
    assert _hints(preferred_run)["return"] is _column_type(registry, "core.processing_runs", "processing_run_id")


def test_nonlogical_names_remain_strings():
    """Catalog IDs, manifest session names, resources, and discriminator scopes are not table IDs."""
    assert _hints(Manifest)["packet_id"] is str
    assert _hints(Manifest)["sessions"] == tuple[str, ...]
    assert _hints(Resource)["resource_id"] is str
    assert _hints(Session)["packet_id"] is str
    assert _hints(Discriminator)["resource"] is str
    assert _hints(preferred_run)["scope"] is str

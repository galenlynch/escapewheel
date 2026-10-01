"""Every column an adapter emits is one the registry declares.

`PacketWriter.add` and `add_batches` refuse a key no loaded registry declares, so a column a
revision removed from a table and an adapter kept emitting fails only when a build reaches that
adapter. Each built-in kind runs here on its own test fixture, records and batches alike, and every
column is resolved against core or the extension registry owning the resource's namespace.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from escapewheel_writer.clock import HARP_TICK_RATE_HZ, Clock
from escapewheel_writer.sources import ADAPTERS
from escapewheel_writer.sources.harp import HarpSource
from escapewheel_writer.sources.lfp import LFPSource
from escapewheel_writer.sources.nwb import NWBSource
from escapewheel_writer.sources.openephys import OpenEphysSource
from escapewheel_writer.sources.sorter import SorterSource
from escapewheel_writer.sources.sync import SyncSource
from escapewheel_writer.sources.waveforms import WaveformSource
from tests import nwbfixture, sorterfixture, syncfixture
from tests.conftest import REGISTRY
from tests.test_harp_source import SCHEMA as HARP_SCHEMA
from tests.test_lfp import CLOCK_ROW, _contacts, _series
from tests.test_openephys_source import SETTINGS
from tests.test_sync_source import FIRST_SAMPLES, PROBE_CLOCKS
from tests.test_waveforms import build as analyzer

EXTENSIONS = {
    document["extension_id"]: document
    for document in (
        json.loads(path.read_text())
        for directory in ("extensions", "escapewheel-aind/extensions")
        for path in sorted((Path(__file__).resolve().parents[2] / directory).glob("*.json"))
    )
}


def declared(resource_id: str) -> set[str] | None:
    """Columns core or the resource's own extension declares for a table, or None if neither does."""
    namespace = resource_id.split(".", 1)[0]
    document = REGISTRY if resource_id in REGISTRY["resources"] else EXTENSIONS.get(namespace)
    declaration = (document or {}).get("resources", {}).get(resource_id)
    if declaration is None or declaration.get("kind") != "table":
        return None
    return {column["name"] for column in declaration["table"]["columns"]}


def emitted(source: Any) -> dict[str, set[str]]:
    """Every column a source hands a build, by resource, over each path the build stages from."""
    found: dict[str, set[str]] = {}
    for resource_id, rows in source.records().items():
        found.setdefault(resource_id, set()).update(key for row in rows for key in row)
    for resource_id, batches in getattr(source, "batches", dict)().items():
        for batch in batches:
            found.setdefault(resource_id, set()).update(batch.schema.names)
    if hasattr(source, "spike_batches"):
        for batch in source.spike_batches(batch_rows=4):
            found.setdefault("core.spike_events", set()).update(batch.schema.names)
    return found


def undeclared(source: Any) -> dict[str, list[str]]:
    """What of `emitted` no registry declares: a whole resource as `['*']`, else its stray columns."""
    wrong = {}
    for resource_id, columns in emitted(source).items():
        known = declared(resource_id)
        if known is None:
            wrong[resource_id] = ["*"]
        elif extra := sorted(columns - known):
            wrong[resource_id] = extra
    return wrong


# -- one fixture per kind ----------------------------------------------------------------

SESSION = "s001"


def _harp(root: Path) -> Any:
    (root / "SniffDetector.harp").mkdir()
    (root / "SniffDetector.harp" / "device.yml").write_text(HARP_SCHEMA)
    return HarpSource(root, session_id=SESSION)


def _openephys(root: Path) -> Any:
    (root / "Record Node 109").mkdir()
    (root / "Record Node 109" / "settings.xml").write_text(SETTINGS)
    return OpenEphysSource(root, session_id=SESSION)


def _sorter(root: Path) -> Any:
    return SorterSource(sorterfixture.build(root), session_id=SESSION)


def _sync(root: Path) -> Any:
    return SyncSource(syncfixture.build(root), session_id=SESSION, clocks=PROBE_CLOCKS, first_samples=FIRST_SAMPLES)


def _nwb(root: Path) -> Any:
    """The base fixture plus one acquisition signal, the only route to `core.array_assets` rows."""
    nwb = nwbfixture.build(root)
    sniff = nwbfixture.group(nwb / "acquisition/sniff", neurodata_type="TimeSeries", description="sniff")
    nwbfixture.array(sniff / "timestamps", np.array([1.0, 2.0]))
    nwbfixture.array(sniff / "data", np.array([0.1, 0.2]))
    # The fixture's own session, which a reference clock must belong to.
    harp = Clock("harp", session_id="mini_2025-04-09", name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="epoch")
    zone = ZoneInfo("America/Los_Angeles")
    return NWBSource(nwb, reference_clock=harp.record(), zone=zone, signals=("sniff",), interval_kind="task.trials")


def _waveforms(root: Path) -> Any:
    units = [{"device_name": "probeA", "local_unit_label": str(u), "unit_id": u} for u in range(3)]
    return WaveformSource(analyzer(root), session_id=SESSION, units=units, sd=True)


def _lfp(root: Path) -> Any:
    nwb = root / "s.nwb"
    _series(nwb)
    _contacts(nwb)
    return LFPSource(nwb, session_id=SESSION, clocks=[CLOCK_ROW])


BUILDERS: dict[str, Callable[[Path], Any]] = {
    "harp": _harp,
    "openephys": _openephys,
    "sorter": _sorter,
    "sync": _sync,
    "nwb": _nwb,
    "waveforms": _waveforms,
    "lfp": _lfp,
}


def test_every_built_in_kind_is_checked():
    """A kind without a builder here is one whose columns nothing compares with the registry."""
    assert set(BUILDERS) == set(ADAPTERS)


@pytest.mark.parametrize("kind", sorted(BUILDERS))
def test_an_adapter_emits_only_declared_columns(kind, tmp_path):
    source = BUILDERS[kind](tmp_path)
    assert emitted(source), f"{kind}'s fixture emits nothing, so the check below would pass vacuously"
    assert undeclared(source) == {}

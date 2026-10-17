"""Every column an adapter emits is one the registry declares.

`PacketWriter.add` and `add_batches` refuse a key no loaded registry declares, so a column a
revision removed from a table and an adapter kept emitting fails only when a build reaches that
adapter. Each built-in kind runs here on its own test fixture, records and batches alike, and every
column is resolved against core or the extension registry owning the resource's namespace.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import nwbfixture
import pytest
from adapter_columns import emitted, undeclared

from escapewheel_writer.clock import HARP_TICK_RATE_HZ, Clock
from escapewheel_writer.sources import ADAPTERS
from escapewheel_writer.sources.harp import HarpSource
from escapewheel_writer.sources.lfp import LFPSource
from escapewheel_writer.sources.nwb.source import NWBSource
from escapewheel_writer.sources.openephys import OpenEphysSource
from escapewheel_writer.sources.sidecars import SidecarSource
from escapewheel_writer.sources.sorter import SorterSource
from escapewheel_writer.sources.sync import SyncSource
from escapewheel_writer.sources.waveforms import WaveformSource
from tests import lfpfixture, sorterfixture, syncfixture
from tests.test_harp_source import acquisition as harp_acquisition
from tests.test_openephys_source import SETTINGS
from tests.test_sync_source import FIRST_SAMPLES, PROBE_CLOCKS
from tests.test_waveforms import build as analyzer

# -- one fixture per kind ----------------------------------------------------------------

SESSION = "s001"


def _harp(root: Path) -> Any:
    harp_acquisition(root)
    harp = Clock("harp", session_id=SESSION, name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="epoch")
    return HarpSource(root, session_id=SESSION, reference_clock=harp.record(), signals=["RawVoltage"])


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
    lfpfixture.series(nwb)
    lfpfixture.contacts(nwb)
    return LFPSource(nwb, session_id=SESSION, clocks=[lfpfixture.CLOCK_ROW])


def _sidecars(root: Path) -> Any:
    (root / "README.md").write_text("# s001\n")
    listed = [
        {
            "resource_id": "core.readme",
            "path": "README.md",
            "media_type": "text/markdown",
            "scopes": [{"scope_kind": "core.sessions", "scope": SESSION}],
        }
    ]
    return SidecarSource(root, sidecars=listed)


BUILDERS: dict[str, Callable[[Path], Any]] = {
    "harp": _harp,
    "openephys": _openephys,
    "sorter": _sorter,
    "sync": _sync,
    "nwb": _nwb,
    "waveforms": _waveforms,
    "lfp": _lfp,
    "sidecars": _sidecars,
}


def test_every_built_in_kind_is_checked():
    """A kind without a builder here is one whose columns nothing compares with the registry."""
    assert set(BUILDERS) == set(ADAPTERS)


@pytest.mark.parametrize("kind", sorted(BUILDERS))
def test_an_adapter_emits_only_declared_columns(kind, tmp_path):
    source = BUILDERS[kind](tmp_path)
    assert emitted(source), f"{kind}'s fixture emits nothing, so the check below would pass vacuously"
    assert undeclared(source) == {}

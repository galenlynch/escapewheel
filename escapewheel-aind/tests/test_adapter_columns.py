"""Every column this distribution's adapters emit is one the registry declares.

The writer refuses a key no loaded registry declares, so a column a revision removed and an adapter
kept emitting fails only when a build reaches that adapter. Each kind registered here runs on its
own test fixture, records and batches alike, and every column is resolved against core or the
extension registry owning the resource's namespace.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from adapter_columns import emitted, undeclared
from escapewheel_writer.adapter import HARP_TICK_RATE_HZ, SOURCE_GROUP, Clock

from escapewheel_aind.nwb import AindNWBSource
from escapewheel_aind.unit_qc import UnitQCSource
from escapewheel_aind.video import VideoSource
from tests import nwbfixture
from tests.builders import session_asset, session_source
from tests.test_dynamic_foraging import source as foraging
from tests.test_unit_qc import UNITS as QC_UNITS
from tests.test_unit_qc import stream as analyzer
from tests.test_video_source import HARP_ROW, camera

# -- one fixture per kind ----------------------------------------------------------------


def _session_source(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    return session_source(session_asset(root))


def _video(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    return VideoSource(camera(root, monkeypatch), session_id="s001", reference_clock=HARP_ROW)


def _nwb(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The fixture with its units table and one acquisition signal, the route to array rows."""
    nwb = nwbfixture.build(root)
    units = nwbfixture.units(nwb)
    sniff = nwbfixture.group(nwb / "acquisition/sniff", neurodata_type="TimeSeries", description="sniff")
    nwbfixture.array(sniff / "timestamps", np.array([1.0, 2.0]))
    nwbfixture.array(sniff / "data", np.array([0.1, 0.2]))
    # The fixture's own session, which a reference clock must belong to.
    harp = Clock("harp", session_id="mini_2025-04-09", name="HARP", tick_rate_num=HARP_TICK_RATE_HZ, origin="epoch")
    return AindNWBSource(
        nwb,
        reference_clock=harp.record(),
        zone=ZoneInfo("America/Los_Angeles"),
        units=units,
        signals=("sniff",),
        interval_kind="task.trials",
    )


def _unit_qc(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    asset = analyzer(root / "sorted", "experiment1_Record Node 109#Neuropix-PXI-100.A_recording1")
    return UnitQCSource(asset, session_id="s1", units=QC_UNITS)


def _dynamic_foraging(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    return foraging(root)


BUILDERS: dict[str, Callable[[Path, pytest.MonkeyPatch], Any]] = {
    "session": _session_source,
    "dynamic_foraging": _dynamic_foraging,
    "video": _video,
    "aind_nwb": _nwb,
    "aind_unit_qc": _unit_qc,
}


def test_every_registered_kind_is_checked():
    """A kind without a builder here is one whose columns nothing compares with the registry."""
    registered = {e.name for e in entry_points(group=SOURCE_GROUP) if e.dist and e.dist.name == "escapewheel-aind"}
    assert set(BUILDERS) == registered


@pytest.mark.parametrize("kind", sorted(BUILDERS))
def test_an_adapter_emits_only_declared_columns(kind, tmp_path, monkeypatch):
    source = BUILDERS[kind](tmp_path, monkeypatch)
    assert emitted(source), f"{kind}'s fixture emits nothing, so the check below would pass vacuously"
    assert undeclared(source) == {}

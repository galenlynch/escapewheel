"""Every column this distribution's adapters emit is one the registry declares.

The writer refuses a key no loaded registry declares, so a column a revision removed and an adapter
kept emitting fails only when a build reaches that adapter. Each kind registered here runs on its
own test fixture, records and batches alike, and every column is resolved against core or the
extension registry owning the resource's namespace.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from escapewheel_writer import Clock
from escapewheel_writer.clock import HARP_TICK_RATE_HZ
from escapewheel_writer.sources import SOURCE_GROUP

from escapewheel_aind import video
from escapewheel_aind.nwb import AindNWBSource
from escapewheel_aind.unit_qc import UnitQCSource
from escapewheel_aind.video import VideoSource
from tests import nwbfixture
from tests.test_session_source import _session
from tests.test_session_source import build as session_json
from tests.test_unit_qc import UNITS as QC_UNITS
from tests.test_unit_qc import stream as analyzer
from tests.test_video_source import HARP_ROW, TIMING

ROOT = Path(__file__).resolve().parents[2]
CORE = json.loads((ROOT / "spec/artifacts/logical_schemas.json").read_text())
EXTENSIONS = {
    document["extension_id"]: document
    for document in (
        json.loads(path.read_text())
        for directory in ("extensions", "escapewheel-aind/extensions")
        for path in sorted((ROOT / directory).glob("*.json"))
    )
}


def declared(resource_id: str) -> set[str] | None:
    """Columns core or the resource's own extension declares for a table, or None if neither does."""
    namespace = resource_id.split(".", 1)[0]
    document = CORE if resource_id in CORE["resources"] else EXTENSIONS.get(namespace)
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


def _session_source(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    return _session(session_json(root))


def _video(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    (root / "bottom_camera.mp4").write_bytes(b"")
    (root / "bottom_camera.csv").write_text(TIMING)
    answers = {"stream=time_base": "1/90000\n", "packet=pts": "0\n3000\n6000\n"}
    monkeypatch.setattr(video, "_ffprobe", lambda path, entries: answers[entries])
    return VideoSource(root, session_id="s001", reference_clock=HARP_ROW)


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


BUILDERS: dict[str, Callable[[Path, pytest.MonkeyPatch], Any]] = {
    "session": _session_source,
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

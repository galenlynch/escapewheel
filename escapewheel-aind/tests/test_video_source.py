"""Behaviour videos: the assets referenced and the frames timed on the rig clock."""

import json
from pathlib import Path

import pyarrow as pa
import pytest
from escapewheel_writer.writer import PacketWriter

from escapewheel_aind import video
from escapewheel_aind.video import VideoSource

HARP_ROW = {"clock_id": "harp", "session_id": "s001", "tick_rate_num": 31250, "origin": "HARP epoch"}

#: Three frames on the rig clock, the counter skipping the third exposure's predecessor.
TIMING = "1.0,100,0\n1.002,101,2000000\n1.006,103,6000000\n"


@pytest.fixture
def root(tmp_path, monkeypatch):
    """One camera with its timing CSV, and ffprobe answered from here rather than run."""
    (tmp_path / "bottom_camera.mp4").write_bytes(b"")
    (tmp_path / "bottom_camera.csv").write_text(TIMING)
    answers = {"stream=time_base": "1/90000\n", "packet=pts": "0\n3000\n6000\n"}
    monkeypatch.setattr(video, "_ffprobe", lambda path, entries: answers[entries])
    return tmp_path


def _source(root, **options):
    return VideoSource(root, session_id="s001", reference_clock=HARP_ROW, **options)


def _frames(source):
    return pa.Table.from_batches(list(source.batches()["core.media_frames"])).to_pylist()


def test_an_unprefixed_asset_is_named_by_its_video(root):
    (row,) = _source(root).media_assets()
    assert (row["media_asset_id"], row["media_asset_name"], row["resource_id"]) == (
        "bottom_camera",
        "bottom_camera",
        "core.bottom_camera",
    )
    assert set(_source(root).external_media()) == {"core.bottom_camera"}


def test_a_prefix_reaches_every_asset_id_its_name_and_its_resource(root):
    """R53 §2.5: every ID this source mints, and its name, carries the prefix; the clock is given."""
    source = _source(root, prefix="A_")
    (row,) = source.media_assets()
    assert (row["media_asset_id"], row["media_asset_name"], row["resource_id"]) == (
        "A_bottom_camera",
        "A_bottom_camera",
        "core.A_bottom_camera",
    )
    assert row["clock_id"] == "harp"
    ((resource_id, media),) = source.external_media().items()
    assert (resource_id, media.media_asset_id) == ("core.A_bottom_camera", "A_bottom_camera")
    frames = _frames(source)
    assert {f["media_asset_id"] for f in frames} == {"A_bottom_camera"}
    assert {f["clock_id"] for f in frames} == {"harp"}


def test_a_prefixed_video_binds_to_its_own_asset_row(root):
    """A build binds a referenced resource to the catalog row by asset ID, so both must carry the prefix."""
    registry = json.loads((Path(__file__).parents[2] / "registry/logical_schemas.json").read_text())
    source = _source(root, prefix="A_")
    rows = source.media_assets()
    writer = PacketWriter(registry, packet_id="p", session="s001")
    writer.add("core.media_assets", rows)
    for resource_id, media in source.external_media().items():
        writer.reference_media(resource_id, media)
    assert {f["media_asset_id"] for f in _frames(source)} <= {r["media_asset_id"] for r in rows}

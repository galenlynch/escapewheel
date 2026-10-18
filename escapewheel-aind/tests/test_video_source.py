"""Behaviour videos: the assets referenced and the frames timed on the rig clock."""

import json
import re
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest
from escapewheel_writer import PacketWriter
from escapewheel_writer.adapter import SourceDefect, codes

from escapewheel_aind import video
from escapewheel_aind.errors import AindFault
from escapewheel_aind.notes import AindNote
from escapewheel_aind.video import VideoSource

HARP_ROW = {"clock_id": "harp", "session_id": "s001", "tick_rate_num": 31250, "origin": "HARP epoch"}

#: Three frames on the rig clock, the counter skipping the third exposure's predecessor.
TIMING = "1.0,100,0\n1.002,101,2000000\n1.006,103,6000000\n"


def probe(monkeypatch, *pts):
    """Answer the MP4 index with the presented timestamps given, in a 1/90000 time base."""
    monkeypatch.setattr(video, "presentation", lambda handle: (1, 90000, np.sort(np.array(pts, dtype=np.int64))))


def ffprobe(monkeypatch, *pts, discarded=()):
    """Leave the index unread and answer ffprobe with packets in the order given, `discarded` flagged `D`."""

    def unindexed(handle):
        raise SourceDefect("fragmented", code=AindFault.VIDEO_UNINDEXED)

    packets = "".join(f"{p},{'_D_' if p in discarded else '___'}\n" for p in pts)
    answers = {"stream=time_base": "1/90000\n", "packet=pts,flags": packets}
    monkeypatch.setattr(video, "presentation", unindexed)
    monkeypatch.setattr(video, "_ffprobe", lambda path, entries: answers[entries])


def camera(root, monkeypatch):
    """Write one camera with its timing CSV under `root`, and answer its index from here."""
    (root / "bottom_camera.mp4").write_bytes(b"")
    (root / "bottom_camera.csv").write_text(TIMING)
    probe(monkeypatch, 0, 3000, 6000)
    return root


@pytest.fixture
def root(tmp_path, monkeypatch):
    return camera(tmp_path, monkeypatch)


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
    """Every ID this source mints, and its name, carries the prefix; the clock is given."""
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
    registry = json.loads((Path(__file__).parents[2] / "spec/artifacts/logical_schemas.json").read_text())
    source = _source(root, prefix="A_")
    rows = source.media_assets()
    writer = PacketWriter(registry, packet_id="p", session="s001")
    writer.add("core.media_assets", rows)
    for resource_id, media in source.external_media().items():
        writer.reference_media(resource_id, media)
    assert {f["media_asset_id"] for f in _frames(source)} <= {r["media_asset_id"] for r in rows}


def test_a_complete_video_is_read_in_order_across_a_timestamp_skip(root, monkeypatch):
    """A stitched transcode skips timestamps without losing a picture."""
    probe(monkeypatch, 0, 3000, 12000)
    frames = _frames(_source(root))
    assert [f["frame_index"] for f in frames] == [0, 1, 2]
    assert [f["t_tick"] for f in frames] == [31250, 31312, 31532]


def test_a_short_video_places_each_frame_by_its_timestamp(root, monkeypatch):
    """A transcode that drops a picture keeps the timeline, so the survivors keep their rows."""
    (root / "bottom_camera.csv").write_text("".join(f"{1 + 0.002 * i},{100 + i},0\n" for i in range(5)))
    probe(monkeypatch, 0, 3000, 6000, 12000)
    source = _source(root)
    assert [f["t_tick"] for f in _frames(source)] == [31250, 31312, 31375, 31500]
    assert AindNote.FRAME_ABSENT in codes(source.notes)


def test_a_complete_video_flags_a_skip_in_the_frame_counter(root):
    """The counter skipping 102 is a known loss; nothing precedes the timing file's first exposure."""
    assert [f["dropped"] for f in _frames(_source(root))] == [False, False, True]


def test_a_short_video_cannot_tell_what_preceded_its_first_frame(root, monkeypatch):
    """A transcode may have lost the leading frames, so the first flag is null rather than false."""
    (root / "bottom_camera.csv").write_text("".join(f"{1 + 0.002 * i},{100 + i},0\n" for i in range(5)))
    probe(monkeypatch, 0, 3000, 9000)
    assert [f["dropped"] for f in _frames(_source(root))] == [None, False, True]


def test_frames_are_numbered_in_presentation_order_whatever_order_they_are_stored_in(root, monkeypatch):
    """Packets arrive in decode order; a frame's index and tick follow the order it is presented."""
    probe(monkeypatch, 0, 6000, 3000)
    frames = _frames(_source(root))
    assert [f["pts"] for f in frames] == [0, 3000, 6000]
    assert [f["t_tick"] for f in frames] == [31250, 31312, 31532]


def test_an_unindexed_video_is_listed_by_ffprobe_less_the_packets_it_discards(root, monkeypatch):
    """The excluded packet is stored and never presented, so it has no row and the rest stay complete."""
    ffprobe(monkeypatch, -3000, 6000, 0, 3000, discarded=(-3000,))
    source = _source(root)
    (row,) = source.media_assets()
    assert (row["pts_rate_num"], row["pts_rate_den"]) == (90000, 1)
    frames = _frames(source)
    assert [f["pts"] for f in frames] == [0, 3000, 6000]
    assert frames[0]["dropped"] is False
    assert AindNote.INDEX_UNREAD in codes(source.notes)


def test_the_columns_an_older_workflow_appends_are_not_read(root):
    (root / "bottom_camera.csv").write_text("".join(f"{line},8.59,996\n" for line in TIMING.splitlines()))
    assert [f["t_tick"] for f in _frames(_source(root))] == [31250, 31312, 31532]


def test_a_trigger_time_out_of_order_with_both_neighbours_takes_their_midpoint(root, monkeypatch):
    """A time a second early between two in order is replaced; the frames stay timed in order."""
    (root / "bottom_camera.csv").write_text("1.0,100,0\n0.002,101,0\n1.004,102,0\n")
    source = _source(root)
    source.media_assets()
    assert [f["t_tick"] for f in _frames(source)] == [31250, 31312, 31375]
    assert "video.trigger_time_out_of_line" in source.compensations
    assert AindNote.TRIGGER_REPAIRED in codes(source.notes)


def test_disorder_beyond_one_time_is_left_for_validation():
    """Two neighbouring times out of order leave no in-order pair around either, so neither is guessed at."""
    triggers = np.array([10, 20, 5, 6, 50, 60])
    assert video.in_line(triggers.copy()).size == 0


#: Part 04 §4.1's resource-ID pattern.
RESOURCE_ID = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_.-]+$")


def _camera(root, stem, suffix=".mp4", timing=".csv"):
    (root / f"{stem}{suffix}").write_bytes(b"")
    (root / f"{stem}{timing}").write_text(TIMING)


def test_a_file_name_is_accepted_however_it_is_spelled(root):
    """A stem Part 04 §4.1 would not admit is folded for the ID and kept as it came for the name."""
    (root / "bottom_camera.mp4").unlink()
    _camera(root, "Side Caméra (Left)", suffix=".MP4", timing=".CSV")
    source = _source(root, uri_base="s3://bucket/videos")
    (row,) = source.media_assets()
    assert (row["media_asset_id"], row["media_asset_name"], row["resource_id"]) == (
        "side_camera_left",
        "Side Caméra (Left)",
        "core.side_camera_left",
    )
    assert row["clock_id"] == "harp"
    ((resource_id, media),) = source.external_media().items()
    assert (resource_id, media.media_asset_id) == ("core.side_camera_left", "side_camera_left")
    assert media.uri == "s3://bucket/videos/Side%20Cam%C3%A9ra%20%28Left%29.MP4"
    assert {f["media_asset_id"] for f in _frames(source)} == {"side_camera_left"}


def test_stems_that_fold_alike_stay_distinct(root):
    """Each takes its own digest, so adding a camera never renames another."""
    _camera(root, "Bottom Camera")
    _camera(root, "日本")
    rows = _source(root).media_assets()
    ids = [r["resource_id"] for r in rows]
    assert len(set(ids)) == 3
    assert all(RESOURCE_ID.match(i) for i in ids)
    folded = sorted(i for i in ids if i.startswith("core.bottom_camera"))
    assert len(folded) == 2 and all(i.startswith("core.bottom_camera-") for i in folded)
    assert {r["media_asset_name"] for r in rows} == {"bottom_camera", "Bottom Camera", "日本"}

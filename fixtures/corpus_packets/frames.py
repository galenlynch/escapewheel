"""Packets about the frames of a media asset."""

from .record import Expected, Packet
from .session import variant

#: The behavior clock's ticks of a camera's frames in presentation order, one repeated.
TICKS = [100, 140, 180, 180, 220, 260]
#: Their presentation timestamps, two steps of 32 apart as a 1/16000 time base gives at 250 Hz.
PTS = [0, 64, 128, 192, 256, 320]


def frames(asset: str, ticks, pts, clocks=None, indices=None) -> list[dict]:
    clocks = clocks or ["behavior_s001"] * len(ticks)
    indices = indices or range(len(ticks))
    return [
        {
            "session_id": "s001",
            "media_asset_id": asset,
            "frame_index": index,
            "t_tick": tick,
            "clock_id": clock,
            "pts": stamp,
            "dropped": index == 3,
        }
        for index, tick, stamp, clock in zip(indices, ticks, pts, clocks, strict=True)
    ]


def asset(name: str) -> dict:
    return {
        "session_id": "s001",
        "media_asset_id": name,
        "resource_id": f"core.{name}",
        "media_asset_name": name,
        "pts_rate_num": 16000,
        "pts_rate_den": 1,
        "clock_id": "behavior_s001",
    }


def media(*framed: tuple[str, list[dict]]):
    """The valid session cataloguing each asset as a referenced video, and carrying its frames.

    A validator times frames without opening the media, so nothing reads the URI.
    """

    def mutate(c):
        c["core.media_assets"] = [asset(name) for name, _ in framed]
        c["core.media_frames"] = [row for _, rows in framed for row in rows]

    def reference(manifest):
        manifest["resources"] += [
            {
                "resource_id": f"core.{name}",
                "declaration_id": "core.media_asset_instances",
                "uri": f"s3://example-bucket/session/{name}.mp4",
                "external": True,
                "validation_state": "not_run",
            }
            for name, _ in framed
        ]

    return variant(mutate, edit=reference)


#: An asset whose frames lie on both clocks, its ticks falling only from a frame on one clock to
#: the next frame, which is on the other.
TWO_CLOCKS = (
    "cam_two_clocks",
    frames(
        "cam_two_clocks",
        [100, 5000, 140, 6000, 180],
        PTS[:5],
        clocks=["behavior_s001", "imec_ap_s001", "behavior_s001", "imec_ap_s001", "behavior_s001"],
    ),
)

#: Part 01 §3.18's frames: numbered and timed in presentation order on each clock.
FRAME_PACKETS = (
    Packet("media_frames", media(("cam_front", frames("cam_front", TICKS, PTS)), TWO_CLOCKS)),
    Packet(
        # Timed in decode order, the order a stream with bidirectional frames stores them in.
        "frames_timed_in_decode_order",
        media(("cam_front", frames("cam_front", [100, 180, 140, 260, 180, 220], PTS))),
        Expected("error", "core.media_frames.t_tick_nondecreasing_with_frame_index"),
        absent=frozenset({"core.media_frames.pts_increases_with_frame_index"}),
    ),
    Packet(
        "frames_fall_behind_another_clock",
        media(
            (
                TWO_CLOCKS[0],
                frames(
                    TWO_CLOCKS[0],
                    [140, 5000, 100, 6000, 180],
                    PTS[:5],
                    clocks=["behavior_s001", "imec_ap_s001", "behavior_s001", "imec_ap_s001", "behavior_s001"],
                ),
            )
        ),
        Expected("error", "core.media_frames.t_tick_nondecreasing_with_frame_index"),
    ),
    Packet(
        "frames_pts_out_of_order",
        media(("cam_front", frames("cam_front", TICKS, [0, 128, 64, 192, 256, 320]))),
        Expected("error", "core.media_frames.pts_increases_with_frame_index"),
    ),
    Packet(
        "frames_index_skips",
        media(("cam_front", frames("cam_front", TICKS, PTS, indices=[0, 1, 2, 3, 4, 6]))),
        Expected("error", "core.media_frames.frame_index_contiguous"),
    ),
)

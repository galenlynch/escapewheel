"""An MP4 video track's presentation timestamps, read from its index alone."""

import io
import struct

import pytest
from escapewheel_writer.adapter import SourceDefect

from escapewheel_aind.errors import AindFault
from escapewheel_aind.mp4 import presentation


def box(kind, *children):
    payload = b"".join(children)
    return struct.pack(">I4s", 8 + len(payload), kind.encode()) + payload


def full(kind, payload, version=0):
    return box(kind, bytes([version, 0, 0, 0]) + payload)


def table(kind, rows, signed=False):
    fmt = ">Ii" if signed else ">II"
    return full(kind, struct.pack(">I", len(rows)) + b"".join(struct.pack(fmt, *r) for r in rows), int(signed))


def track(handler, deltas, offsets=None, edits=None, scale=16000):
    """A `trak` of one sample per delta, with `ctts` offsets and `elst` edits of (duration, media_time)."""
    stbl = [table("stts", [(1, d) for d in deltas])]
    if offsets is not None:
        stbl.append(table("ctts", [(1, o) for o in offsets], signed=any(o < 0 for o in offsets)))
    parts = []
    if edits is not None:
        rows = b"".join(struct.pack(">Iii", d, t, 1 << 16) for d, t in edits)
        parts.append(box("edts", full("elst", struct.pack(">I", len(edits)) + rows)))
    mdhd = full("mdhd", struct.pack(">IIII", 0, 0, scale, sum(deltas)) + b"\0" * 4)
    hdlr = full("hdlr", b"\0" * 4 + handler.encode() + b"\0" * 12)
    parts.append(box("mdia", mdhd, hdlr, box("minf", box("stbl", *stbl))))
    return box("trak", *parts)


def mp4(*tracks, movie_scale=1000, moov_last=False, extra=b""):
    moov = box("moov", full("mvhd", struct.pack(">IIII", 0, 0, movie_scale, 0) + b"\0" * 80), *tracks)
    parts = [box("ftyp", b"isom\0\0\0\0"), box("mdat", b"\0" * 64), moov]
    if not moov_last:
        parts[1], parts[2] = parts[2], parts[1]
    return io.BytesIO(b"".join(parts) + extra)


def test_frames_are_presented_in_order_after_the_edit_lists_shift():
    """B-frames store a frame ahead of where it shows; the edit list moves the first shown to zero."""
    handle = mp4(track("vide", [1000] * 4, offsets=[2000, 4000, 1000, 1000], edits=[(250, 2000)]))
    num, den, pts = presentation(handle)
    assert (num, den) == (1, 16000)
    assert pts.tolist() == [0, 1000, 2000, 3000]


def test_a_sample_before_the_edit_is_no_frame():
    pts = presentation(mp4(track("vide", [1000] * 3, edits=[(0, 1000)])))[2]
    assert pts.tolist() == [0, 1000]


def test_a_leading_empty_edit_delays_every_frame():
    """The empty edit is in the movie's timescale and the samples in the media's."""
    pts = presentation(mp4(track("vide", [1000] * 2, edits=[(500, -1), (0, 0)]), movie_scale=1000))[2]
    assert pts.tolist() == [8000, 9000]


def test_the_video_track_is_read_wherever_it_is_and_wherever_the_index_lies():
    handle = mp4(track("soun", [1024] * 5), track("vide", [512] * 3), moov_last=True)
    assert presentation(handle)[2].tolist() == [0, 512, 1024]


@pytest.mark.parametrize(
    "handle",
    [
        mp4(track("vide", [1000]), extra=box("moof")),
        mp4(track("vide", [1000] * 2, edits=[(1, 0), (1, 1000)])),
        mp4(track("soun", [1000])),
    ],
    ids=["fragmented", "two-segment edit", "no video"],
)
def test_an_index_this_reader_does_not_take_is_refused(handle):
    with pytest.raises(SourceDefect) as refused:
        presentation(handle)
    assert refused.value.code == AindFault.VIDEO_UNINDEXED

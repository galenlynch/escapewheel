"""A video track's presentation timestamps, read from an MP4's index without its media.

- :func:`presentation` -- the time base and presented timestamps of an MP4's first video track.

An MP4 keeps every sample's timing in its `moov` box, a few MB against gigabytes of `mdat`, so a
remote video is timed by a few range reads rather than a download. The result is what
`ffprobe -show_entries packet=pts,flags` reports, less the packets it flags discarded.
"""

from __future__ import annotations

import struct
from collections.abc import Iterator
from typing import BinaryIO

import numpy as np
from escapewheel_writer.adapter import SourceDefect
from numpy.typing import NDArray

from .errors import AindFault


def _unindexed(reason: str) -> SourceDefect:
    """Return the refusal for an MP4 with no index this reader takes."""
    return SourceDefect(reason, code=AindFault.VIDEO_UNINDEXED, where="moov")


def _boxes(buf: bytes, start: int, end: int) -> Iterator[tuple[str, int, int]]:
    """Yield each child box between `start` and `end` as its type, payload start and end."""
    while start + 8 <= end:
        size, kind = struct.unpack_from(">I4s", buf, start)
        header = 8
        if size == 1:
            (size,) = struct.unpack_from(">Q", buf, start + 8)
            header = 16
        elif size == 0:
            size = end - start
        yield kind.decode("latin-1"), start + header, start + size
        start += size


def _top_level(handle: BinaryIO) -> dict[str, tuple[int, int]]:
    """Return each top-level box's offset and size, read from its header alone."""
    handle.seek(0, 2)
    end = handle.tell()
    found: dict[str, tuple[int, int]] = {}
    offset = 0
    while offset + 8 <= end:
        handle.seek(offset)
        head = handle.read(16)
        size, kind = struct.unpack_from(">I4s", head)
        if size == 1:
            (size,) = struct.unpack_from(">Q", head, 8)
        elif size == 0:
            size = end - offset
        if size < 8:
            break
        found.setdefault(kind.decode("latin-1"), (offset, size))
        offset += size
    return found


def _table(payload: bytes, fields: str) -> NDArray[np.int64]:
    """Return a full box's entry table as rows of big-endian 32-bit fields, `fields` naming each one's sign."""
    (count,) = struct.unpack_from(">I", payload, 4)
    dtype = np.dtype([(str(i), ">i4" if sign == "i" else ">u4") for i, sign in enumerate(fields)])
    rows = np.frombuffer(payload, dtype=dtype, count=count, offset=8)
    return np.stack([rows[str(i)].astype(np.int64) for i in range(len(fields))], axis=1)


def _edit(payload: bytes, media_scale: int, movie_scale: int) -> tuple[int, int, int | None]:
    """Return an edit list's shift as the leading empty duration, the media start and its length.

    Lengths are in the media's timescale; a length of None runs to the end.
    """
    version = payload[0]
    (count,) = struct.unpack_from(">I", payload, 4)
    wide = version == 1
    step = 20 if wide else 12
    empty, kept = 0, []
    for i in range(count):
        at = 8 + i * step
        if wide:
            duration, media_time = struct.unpack_from(">Qq", payload, at)
        else:
            duration, media_time = struct.unpack_from(">Ii", payload, at)
        (rate,) = struct.unpack_from(">i", payload, at + step - 4)
        if media_time == -1 and not kept:
            empty += duration * media_scale // movie_scale
        else:
            kept.append((duration, media_time, rate))
    if len(kept) != 1 or kept[0][2] != 1 << 16:
        raise _unindexed(f"edit list of {count} entries, which this reader does not take")
    duration, media_time, _ = kept[0]
    return empty, media_time, duration * media_scale // movie_scale or None


def presentation(handle: BinaryIO) -> tuple[int, int, NDArray[np.int64]]:
    """Return the first video track's time base, as numerator and denominator, and presented timestamps.

    Timestamps are sorted, in time-base units, and shifted by the edit list as ffprobe shifts them; a
    sample the edit list leaves out is no frame of the video and is not returned.
    """
    boxes = _top_level(handle)
    if "moof" in boxes or "moov" not in boxes:
        raise _unindexed("fragmented, or no moov box")
    offset, size = boxes["moov"]
    handle.seek(offset)
    moov = handle.read(size)
    movie_scale = 1
    for kind, start, end in _boxes(moov, 8, len(moov)):
        if kind == "mvhd":
            movie_scale = struct.unpack_from(">I", moov, start + (20 if moov[start] == 1 else 12))[0]
        if kind == "mvex":
            raise _unindexed("fragmented")
    for kind, start, end in _boxes(moov, 8, len(moov)):
        if kind != "trak":
            continue
        track = {k: (s, e) for k, s, e in _boxes(moov, start, end)}
        media = {k: (s, e) for k, s, e in _boxes(moov, *track["mdia"])}
        handler = moov[media["hdlr"][0] + 8 : media["hdlr"][0] + 12]
        if handler != b"vide":
            continue
        mdhd = media["mdhd"][0]
        media_scale = struct.unpack_from(">I", moov, mdhd + (20 if moov[mdhd] == 1 else 12))[0]
        minf = {k: (s, e) for k, s, e in _boxes(moov, *media["minf"])}
        stbl = {k: moov[s:e] for k, s, e in _boxes(moov, *minf["stbl"])}
        stts = _table(stbl["stts"], "uu")
        deltas = np.repeat(stts[:, 1], stts[:, 0])
        decode = np.concatenate([[0], np.cumsum(deltas[:-1])]) if deltas.size else deltas
        pts = decode.copy()
        if "ctts" in stbl:
            ctts = _table(stbl["ctts"], "ui" if stbl["ctts"][0] == 1 else "uu")
            pts += np.repeat(ctts[:, 1], ctts[:, 0])[: pts.size]
        empty, start_at, length = 0, 0, None
        length: int | None
        if "edts" in track:
            edits = {k: moov[s:e] for k, s, e in _boxes(moov, *track["edts"])}
            if "elst" in edits:
                empty, start_at, length = _edit(edits["elst"], media_scale, movie_scale)
        kept = pts >= start_at
        if length is not None:
            kept &= pts < start_at + length
        pts = np.sort(pts[kept] - start_at + empty)
        return 1, media_scale, pts
    raise _unindexed("no video track")


__all__ = ["presentation"]

"""What more than one test module builds: a session asset and the source over it."""

import json
from zoneinfo import ZoneInfo

from escapewheel_writer.adapter import HARP_TICK_RATE_HZ

from escapewheel_aind.session import SessionSource

PACIFIC = ZoneInfo("America/Los_Angeles")
SESSION = "ecephys_776259_2025-04-09_17-25-12"

#: The ephys stream's start, stamped `+00:00` on a Pacific reading -- the real defect.
EPHYS_START = "2025-04-09T17:25:12+00:00"
EPHYS_STOP = "2025-04-09T19:11:39+00:00"
#: The behaviour stream's, stamped correctly.
BEHAVIOR_START = "2025-04-09T17:27:55.339024-07:00"
BEHAVIOR_STOP = "2025-04-09T19:38:44.147959-07:00"


def session_asset(root, *, streams=None):
    """Write a minimal `session.json` into an asset directory."""
    asset = root / SESSION
    asset.mkdir(parents=True, exist_ok=True)
    if streams is None:
        streams = [
            {
                "stream_start_time": EPHYS_START,
                "stream_end_time": EPHYS_STOP,
                "ephys_modules": [{"assembly_name": "46100"}],
            },
            {
                "stream_start_time": BEHAVIOR_START,
                "stream_end_time": BEHAVIOR_STOP,
                "ephys_modules": [],
                "stream_modalities": [{"abbreviation": "behavior-videos"}],
            },
        ]
    (asset / "session.json").write_text(
        json.dumps({"session_start_time": EPHYS_START, "subject_id": "776259", "data_streams": streams})
    )
    return asset


#: The reference clock's row, which a build supplies and this source emits as given.
HARP_ROW = {
    "clock_id": "harp",
    "session_id": SESSION,
    "origin": "HARP device power-on",
    "tick_rate_num": HARP_TICK_RATE_HZ,
    "tick_rate_den": 1,
}


def session_source(root, **kwargs):
    """The session adapter over `root`, supplied the HARP row and the Pacific zone unless told otherwise."""
    kwargs.setdefault("reference_clock", HARP_ROW)
    kwargs.setdefault("zone", PACIFIC)
    return SessionSource(root, **kwargs)

"""Write one session's source tree, on a local disk or a store, as the rig would have.

python tests/session.py s001
"""

import json
import sys
from pathlib import Path

import numpy as np

HARP_HZ = 31250
#: The rig starts recording an hour into HARP's count, as a free-running clock does.
START_TICK = 3600 * HARP_HZ
#: Ten seconds recorded; the wheel ran for all but the last.
STOP_TICK = START_TICK + 10 * HARP_HZ
WHEEL_SAMPLES = 9 * 250
#: HARP ticks per wheel sample: 125 nominally, and 40 ppm more on this encoder's oscillator.
DRIFT = 125 * (1 + 40e-6)

#: (HARP tick, event, reward volume), as the rig logged them.
EVENTS = [
    (START_TICK + 37500, "lick", ""),
    (START_TICK + 42188, "lick", ""),
    (START_TICK + 90625, "reward", "2.5"),
    (START_TICK + 93750, "lick", ""),
    (START_TICK + 200000, "reward", "3.0"),
    (START_TICK + 203125, "lick", ""),
]


def wheel_ticks():
    """Each wheel sample's arrival on HARP, drifting against the encoder's own count."""
    return START_TICK + np.rint(np.arange(WHEEL_SAMPLES) * DRIFT).astype(np.int64)


def write(root, *, wheel=True, subject_id="m001"):
    """Write the session under `root`, any path with `/` and `write_text`."""
    root.mkdir(parents=True, exist_ok=True)
    seconds = lambda tick: repr(tick / HARP_HZ)  # noqa: E731 -- Bonsai writes a float's shortest repr
    stated = {
        "subject_id": subject_id,
        "harp_start_seconds": START_TICK / HARP_HZ,
        "harp_stop_seconds": STOP_TICK / HARP_HZ,
    }
    (root / "session.json").write_text(json.dumps(stated))
    (root / "events.csv").write_text(
        "harp_seconds,event,volume_ul\n" + "".join(f"{seconds(t)},{e},{v}\n" for t, e, v in EVENTS)
    )
    if wheel:
        position = np.cumsum(np.sin(np.arange(WHEEL_SAMPLES) / 50.0)).astype(np.float32)
        (root / "wheel.csv").write_text(
            "harp_seconds,position_deg\n"
            + "".join(f"{seconds(int(t))},{float(p)!r}\n" for t, p in zip(wheel_ticks(), position, strict=True))
        )
    return root


if __name__ == "__main__":
    write(Path(sys.argv[1]))

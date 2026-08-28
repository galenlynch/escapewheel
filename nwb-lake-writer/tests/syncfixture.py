"""Build a miniature Open Ephys clipped tree, with the trap the real one carries.

The trap is the unaligned stub: a record node's directory lists every stream it saw, and only
the ones it owns were aligned. A stub's `timestamps.npy` is acquisition-local seconds with
nothing but the absent `original_timestamps.npy` to say so, and taking one at face value puts
a probe's pulses 17.7 million seconds from where they belong.
"""

import json
from pathlib import Path

import numpy as np

AP_HZ, HARP_HZ = 30000, 31250

#: Where this rig's HARP counter had got to, so a local value is unmistakable beside it.
HARP_START = 17_702_134.0

#: One rising edge per second, as the shared sync line gives.
N_PULSES = 8


def stream(
    events: Path,
    name: str,
    *,
    first_sample: int,
    aligned: bool = True,
    pulse_offset: int = 0,
    continuous: Path | None = None,
    line: int = 1,
) -> Path:
    """Write one stream's TTL events, aligned or a local-only stub.

    Parameters
    ----------
    first_sample : int
        The recording's first raw sample, which is what makes a raw counter relative.
    pulse_offset : int
        Samples between the recording's start and the first pulse, so a fixture can put
        spikes outside the anchor span the way a real recording does.
    continuous : Path, optional
        Write `continuous/<name>/sample_numbers.npy` too, so the adapter can read element 0
        rather than being told.
    """
    ttl = events / name / "TTL"
    ttl.mkdir(parents=True, exist_ok=True)

    samples = first_sample + pulse_offset + np.arange(N_PULSES, dtype=np.int64) * AP_HZ
    # Both edges of each pulse, so `states` has something to filter.
    both = np.empty(N_PULSES * 2, dtype=np.int64)
    both[0::2], both[1::2] = samples, samples + 100
    states = np.empty(N_PULSES * 2, dtype=np.int64)
    states[0::2], states[1::2] = line, -line

    np.save(ttl / "sample_numbers.npy", both)
    np.save(ttl / "states.npy", states)
    local = (both - first_sample) / AP_HZ
    if aligned:
        # One physical pulse per second, so every stream that saw it reports the same HARP
        # time however far into its own recording the pulse fell.
        shared = np.repeat(np.arange(N_PULSES, dtype=np.float64), 2)
        shared[1::2] += 100 / AP_HZ
        np.save(ttl / "timestamps.npy", HARP_START + shared)
        np.save(ttl / "original_timestamps.npy", 1475.0 + local)
        np.save(ttl / "local_timestamps.npy", local)
    else:
        np.save(ttl / "timestamps.npy", 1475.0 + local)

    if continuous is not None:
        target = continuous / name
        target.mkdir(parents=True, exist_ok=True)
        np.save(target / "sample_numbers.npy", first_sample + np.arange(1000, dtype=np.int64))
    return ttl


#: Node 109 owns probeA and probeB; node 111 owns probeC and carries stubs of the others.
OWNED = {"109": ("probeA", "probeB"), "111": ("probeC",)}
FIRST_SAMPLE = {"probeA": 44_259_994, "probeB": 44_251_369, "probeC": 44_255_501}


def build(root: Path, *, experiment: str = "experiment1", with_continuous: bool = False) -> Path:
    """Write two record nodes, each owning some streams and stubbing the rest."""
    for node, owns in OWNED.items():
        recording = root / f"Record Node {node}" / experiment / "recording1"
        events = recording / "events"
        for name, first in FIRST_SAMPLE.items():
            stream(
                events,
                name,
                first_sample=first,
                aligned=name in owns,
                pulse_offset=1000 if name == "probeA" else 0,
                continuous=(recording / "continuous") if (with_continuous and name in owns) else None,
            )
        # The NI-DAQ is aligned and carries no ticks of its own.
        stream(events, "NI-DAQmx-107", first_sample=44_000_000, aligned=True)
    (root / "structure.json").write_text(json.dumps({"note": "fixture"}))
    return root

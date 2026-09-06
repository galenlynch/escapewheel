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


#: Node 109 owns probeA and probeB; node 111 owns probeC and carries stubs of the others. The
#: names are the shape Open Ephys writes, `<processor>-<id>.<stream>`, because that is what a
#: node's own `sync_messages.txt` composes to and what a lookup there has to match.
OWNED = {"109": ("Neuropix-PXI-100.probeA", "Neuropix-PXI-100.probeB"), "111": ("Neuropix-PXI-100.probeC",)}
FIRST_SAMPLE = {
    "Neuropix-PXI-100.probeA": 44_259_994,
    "Neuropix-PXI-100.probeB": 44_251_369,
    "Neuropix-PXI-100.probeC": 44_255_501,
}


#: When each node says it began, milliseconds since the epoch. They differ, as two nodes
#: starting independently do, and the difference is what bounds an epoch derived from them.
STARTED_MS = {"109": 1_744_244_712_090, "111": 1_744_244_712_153}


def sync_messages(recording: Path, node: str) -> Path:
    """Write a record node's `sync_messages.txt`, as Open Ephys does.

    It lists every stream the node *saw*, owned or not, which is the same asymmetry the TTL
    directories carry: a value here does not mean the node's timestamps are HARP.
    """
    lines = [f"Software Time (milliseconds since midnight Jan 1st 1970 UTC): {STARTED_MS[node]}"]
    lines += [
        # The node names the processor and the stream separately; the directory beside the
        # data is what the two compose to, which is what a lookup has to reconstruct.
        f"Start Time for Neuropix-PXI (100) - {name.rsplit('.', 1)[-1]} @ {AP_HZ} Hz: {first}"
        for name, first in FIRST_SAMPLE.items()
    ]
    lines.append(f"Start Time for NI-DAQmx (107) - PXIe-6341 @ {AP_HZ} Hz: 44000000")
    path = recording / "sync_messages.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path


def build(
    root: Path, *, experiment: str = "experiment1", with_continuous: bool = False, with_sync_messages: bool = False
) -> Path:
    """Write two record nodes, each owning some streams and stubbing the rest."""
    for node, owns in OWNED.items():
        recording = root / f"Record Node {node}" / experiment / "recording1"
        events = recording / "events"
        if with_sync_messages:
            sync_messages(recording, node)
        for name, first in FIRST_SAMPLE.items():
            stream(
                events,
                name,
                first_sample=first,
                aligned=name in owns,
                pulse_offset=1000 if name == "Neuropix-PXI-100.probeA" else 0,
                continuous=(recording / "continuous") if (with_continuous and name in owns) else None,
            )
        # The NI-DAQ is aligned and carries no ticks of its own.
        stream(events, "NI-DAQmx-107", first_sample=44_000_000, aligned=True)
    (root / "structure.json").write_text(json.dumps({"note": "fixture"}))
    return root

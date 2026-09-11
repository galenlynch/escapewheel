"""What actually crosses between a build and the NWB adapter, measured rather than argued.

Two drafts propose that an adapter declare what a build supplies it and deliver its rows out of
process. Both were written against the shape of the code rather than against a run of it. This
constructs the NWB adapter twice -- once as `session.py` builds it today, once from values that
survive a JSON round trip -- and compares what comes back, so the closed list is tested against the
adapter that receives the most.

    uv run --project ../../escapewheel-writer python probe.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

import numpy

HERE = Path(__file__).resolve().parent
#  imports `tests.nwbfixture`, so the package root goes on the path too.
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer"))
sys.path.insert(0, str(HERE.parent.parent / "escapewheel-writer/tests"))

import nwbfixture
from escapewheel_writer.clock import Clock
from escapewheel_writer.sources.nwb import NWBSource
from escapewheel_writer.sources.waveforms import WaveformSource

SESSION = "mini_2025-04-09"
KIND = "task.trials"
ZONE = "America/Los_Angeles"


def today(root: Path) -> NWBSource:
    """The adapter as `session.py` constructs it: a Clock object and a ZoneInfo."""
    clock = Clock(
        "harp",
        session_id=SESSION,
        name="HARP",
        tick_rate_num=31_250,
        origin="HARP epoch",
    )
    return NWBSource(root, clock=clock, zone=ZoneInfo(ZONE), interval_kind=KIND)


def across(root: Path) -> tuple[NWBSource, str]:
    """The adapter built from what a build could pass across a process boundary.

    Everything goes through `json.dumps` first, so anything that cannot be written down fails here
    rather than in review. The far side rebuilds the writer's classes from the values -- which an
    adapter holding the writer may do, and one that does not replaces with its own.
    """
    supplied = {
        "root": str(root),
        "reference_clock": {
            "clock_id": "harp",
            "session_id": SESSION,
            "name": "HARP",
            "tick_rate_num": 31_250,
            "tick_rate_den": 1,
            "origin": "HARP epoch",
        },
        "zone": ZONE,
        "options": {"interval_kind": KIND},
    }
    wire = json.dumps(supplied)
    got = json.loads(wire)
    clock = Clock(**got["reference_clock"])
    return NWBSource(
        got["root"], clock=clock, zone=ZoneInfo(got["zone"]), **got["options"]
    ), wire


def main() -> int:
    """Report what crossed, what did not, and whether the rows agree."""
    with TemporaryDirectory() as tmp:
        root = nwbfixture.build(Path(tmp))
        here, wire = today(root), None
        there, wire = across(root)

        mine, theirs = here.records(), there.records()
        same = mine == theirs
        rows = sum(len(v) for v in mine.values())
        print(f"inputs crossed as {len(wire)} bytes of JSON")
        print(
            f"records: {len(mine)} resources, {rows} rows, identical across the boundary: {same}"
        )
        if not same:
            for key in sorted(set(mine) | set(theirs)):
                if mine.get(key) != theirs.get(key):
                    print(f"    differs: {key}")

        # The other half. `records` is rows; an array is not, and neither draft says how one
        # crosses. The waveform adapter is where to look: it stages arrays, and its two build-
        # supplied inputs are mappings keyed by a tuple and by an integer.
        waveforms(Path(tmp))
    streams()
    return 0


def waveforms(tmp: Path) -> None:
    """What the waveform adapter is passed and hands back, on the same test."""
    import test_waveforms as fixture

    root = tmp / "session.nwb"
    units = fixture.group(root / "units")
    fixture._wide(units / "waveform_mean", fixture._dense(fixture.SUPPORT))
    fixture.array(
        units / "device_name", ["probeA"] * fixture.UNITS, filter_id="vlen-utf8"
    )
    fixture.array(units / "ks_unit_id", numpy.arange(fixture.UNITS, dtype="<i8"))
    fixture.array(
        units / "electrodes",
        numpy.arange(fixture.UNITS * fixture.CHANNELS, dtype="<i8"),
    )
    fixture.array(
        units / "electrodes_index",
        numpy.arange(1, fixture.UNITS + 1, dtype="<i8") * fixture.CHANNELS,
    )
    fixture.array(
        units / "extremum_channel_index", numpy.array(fixture.EXTREMUM, dtype="<i8")
    )
    (root / ".zgroup").write_text(json.dumps({"zarr_format": 2}))

    supplied = {
        "units": {
            ("probeA", str(u)): {"unit_id": u, "sorting_run_id": 1, "curation_id": 1}
            for u in range(fixture.UNITS)
        },
        "electrodes": {
            row: 100 + row for row in range(fixture.UNITS * fixture.CHANNELS)
        },
    }
    print("\nwaveform adapter, what a build supplies:")
    for name, value in supplied.items():
        key = next(iter(value))
        wrote = _dumps(value)
        # A mapping that writes down is not a mapping that comes back: JSON has string keys, so
        # an integer one returns as a string and the adapter looks a row up with the wrong type.
        survives = (
            wrote == "yes"
            and list(json.loads(json.dumps(value))) == [str(k) for k in value]
            and list(json.loads(json.dumps(value))) != list(value)
        )
        note = "; keys return as strings" if survives else ""
        print(f"    {name}: keyed by {type(key).__name__}, json.dumps: {wrote}{note}")

    source = WaveformSource(root, session_id="s1", **supplied)
    staged = source.staged_arrays()
    print(
        f"\nstaged_arrays: {len(staged)} object(s), type {type(staged[0]).__name__ if staged else '—'}"
    )
    for item in staged:
        values = getattr(item, "values", None)
        print(f"    {item.array_asset_id}: fields {[f.name for f in fields(item)]}")
        print(
            f"      values is {type(values).__name__}, "
            f"{getattr(values, 'nbytes', '?')} bytes, shape {getattr(values, 'shape', '?')}"
        )
        print(f"      json.dumps: {_dumps(item.__dict__)}")


def _dumps(value: object) -> str:
    """Whether a value can be written down, which is what crossing a boundary takes."""
    try:
        json.dumps(value)
    except TypeError as exc:
        return f"refused — {exc}"
    return "yes"


def streams() -> None:
    """Whether many resources cross one pipe as Arrow, and how.

    An IPC stream carries one schema by construction, and an adapter returns thirteen resources on
    the NWB fixture. Streams concatenate, though: each ends with an end-of-stream marker, so a
    reader opens one, reads to it, and opens the next on what is left. The resource identifier
    rides in the schema's own key-value metadata, so nothing is framed that Arrow does not frame.
    """
    import subprocess

    import pyarrow as pa

    script = HERE / "emit.py"
    child = subprocess.Popen([sys.executable, str(script)], stdout=subprocess.PIPE)
    got: dict[str, int] = {}
    try:
        while True:
            reader = pa.ipc.open_stream(child.stdout)
            got[reader.schema.metadata[b"resource_id"].decode()] = (
                reader.read_all().num_rows
            )
    except pa.ArrowInvalid:
        pass
    child.wait()
    print(
        f"\nthree resources over one pipe, three schemas: {got}, exit {child.returncode}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

"""Fail unless the runtime can exercise facilities used by the full package suites.

The local restricted agent sandbox cannot wake Zarr's synchronous asyncio bridge or bind the
Unix-domain socket used by Arrow Flight. Those are environment failures, but silently skipping the
tests would leave the monorepo without conformance evidence. The full verifier runs these isolated
probes before generation or package tests so its environment contract is explicit and a blocked
primitive fails quickly. CI reaches them through that same verifier entry point.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path


def async_bridge() -> None:
    """Exercise the event-loop-to-worker wakeup on which Zarr's sync API depends."""

    async def run() -> None:
        result = await asyncio.wait_for(asyncio.to_thread(lambda: 42), timeout=5)
        if result != 42:
            raise RuntimeError(f"async worker returned {result!r}")

    asyncio.run(run())


def zarr_array() -> None:
    """Create and round-trip the smallest Zarr v3 array used by reader and writer tests."""
    import zarr

    with tempfile.TemporaryDirectory(prefix="escapewheel-zarr-") as temporary:
        array = zarr.create_array(
            store=str(Path(temporary) / "array.zarr"),
            shape=(2,),
            chunks=(2,),
            dtype="int16",
        )
        array[:] = [3, 5]
        if array[:].tolist() != [3, 5]:
            raise RuntimeError("Zarr round trip changed values")


def flight_socket() -> None:
    """Bind and release the Unix-domain socket used by the Flight delivery protocol."""
    from pyarrow import flight

    with tempfile.TemporaryDirectory(prefix="escapewheel-flight-") as temporary:
        server = flight.FlightServerBase(
            flight.Location.for_grpc_unix(str(Path(temporary) / "adapter.sock"))
        )
        server.shutdown()


PROBES = {
    "async-bridge": async_bridge,
    "zarr-array": zarr_array,
    "flight-socket": flight_socket,
}

# A healthy probe completes in well under a second. This outer bound is deliberately
# longer than async_bridge's five-second diagnostic bound because it also includes interpreter
# startup and imports. It exists for runtimes where the event loop itself cannot wake, so the
# in-process asyncio timeout cannot fire.
PROBE_TIMEOUT = 10


def main() -> int:
    """Run one child probe or supervise every probe with a short hard timeout."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--probe", choices=sorted(PROBES))
    args = parser.parse_args()
    if args.probe:
        PROBES[args.probe]()
        return 0

    for name in PROBES:
        print(f"run  {name}", flush=True)
        try:
            done = subprocess.run(
                [sys.executable, __file__, "--probe", name],
                capture_output=True,
                text=True,
                check=False,
                timeout=PROBE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            print(f"FAIL {name}: timed out after {PROBE_TIMEOUT} seconds")
            return 1
        if done.returncode:
            output = (done.stdout + done.stderr).strip().splitlines()
            detail = output[-1] if output else "failed without output"
            print(f"FAIL {name}: {detail}")
            return 1
        print(f"ok   {name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

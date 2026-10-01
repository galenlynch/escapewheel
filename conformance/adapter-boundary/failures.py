"""What a failure carries across the adapter boundary, measured over `flight-v0.1`.

`build_side.py` measures the path where everything works. This measures the four ways it does not,
and the one where an adapter has something to say about a run that succeeded. The table is
synthetic and tiny: what is being measured is what crosses a process boundary, not what an adapter
extracts.

    uv run --project ../../escapewheel-writer python failures.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.flight as fl

HERE = Path(__file__).resolve().parent
ROWS = pa.table({"electrode_id": [1, 2, 3, 4], "session_id": [0, 0, 0, 0]})

#: One finding in the shape Part 12 §9 gives an extension's report.
FINDING = {
    "level": "warning",
    "resource": "core.electrodes",
    "message": "3 of 4 contacts carry no CCF position; the source states none",
}


class Adapter(fl.FlightServerBase):
    """A server whose failure mode is chosen by the build that started it."""

    def __init__(self, location: str, mode: str) -> None:
        super().__init__(fl.Location.for_grpc_unix(location))
        self.mode = mode

    def list_flights(self, context, criteria):
        """Discovery (Part 05 §4.1), carrying a per-resource finding where the mode has one."""
        meta = json.dumps(FINDING).encode() if self.mode == "findings" else b""
        yield fl.FlightInfo(
            ROWS.schema,
            fl.FlightDescriptor.for_path("core.electrodes"),
            [],
            ROWS.num_rows,
            ROWS.nbytes,
            app_metadata=meta,
        )

    def do_get(self, context, ticket):
        """One resource, or whichever failure this adapter was started to produce."""
        if self.mode == "raises":
            raise ValueError("no CCF frame in /general/extracellular_ephys/electrodes")
        if self.mode == "structured":
            raise fl.FlightServerError(
                "core.electrodes could not be extracted",
                extra_info=json.dumps({**FINDING, "level": "error"}).encode(),
            )
        if self.mode == "midstream":
            return fl.GeneratorStream(ROWS.schema, self._half())
        return fl.RecordBatchStream(ROWS)

    def _half(self):
        """Two batches, then the failure a long extraction meets partway through."""
        yield ROWS.slice(0, 2).to_batches()[0]
        raise fl.FlightServerError("the source file ended at row 2")

    def list_actions(self, context):
        """The one action `flight-v0.1` would name, absent from an adapter with nothing to say."""
        return [] if self.mode == "silent" else [("report", "what this run says about itself")]

    def do_action(self, context, action):
        """The whole run's report, asked for once, after the rows (Part 12 §9's shape)."""
        if self.mode == "silent":
            raise NotImplementedError(action.type)
        if action.type == "report":
            body = {"problems": [FINDING], "read": ["sub-mini_ecephys.nwb"]}
            yield fl.Result(json.dumps(body).encode())


def serve(mode: str, socket: str) -> None:
    """The adapter side: `dies` never binds, every other mode serves."""
    if mode == "dies":
        raise SystemExit("NWBSource: /mnt/Data/no-such-session holds no NWB file")
    Adapter(socket, mode).serve()


def start(mode: str, socket: str) -> subprocess.Popen:
    """Launch the adapter, capturing standard error as Part 05 §3.7 requires."""
    return subprocess.Popen(
        [sys.executable, str(HERE / "failures.py"), "serve", mode, socket],
        stderr=subprocess.PIPE,
        text=True,
    )


def connect(socket: str, child: subprocess.Popen) -> fl.FlightClient:
    """`flight-v0.1`'s rendezvous: retry until the socket answers or the adapter exits."""
    while True:
        try:
            client = fl.connect(fl.Location.for_grpc_unix(socket))
            client.wait_for_available(timeout=0.05)
            return client
        except (fl.FlightUnavailableError, fl.FlightTimedOutError):
            if child.poll() is not None:
                raise SystemExit(f"the adapter exited {child.returncode} before serving")
            time.sleep(0.01)


def run(mode: str, tmp: str):
    """One adapter, started and read the way a build would, returning what reached this side."""
    socket = str(Path(tmp) / f"{mode}.sock")
    child = start(mode, socket)
    started = time.perf_counter()
    try:
        client = connect(socket, child)
    except SystemExit as exit_:
        elapsed = 1000 * (time.perf_counter() - started)
        return {
            "detected_ms": elapsed,
            "exit": str(exit_),
            "stderr": child.stderr.read(),
        }
    offered = list(client.list_flights())
    result = {"app_metadata": offered[0].app_metadata}
    try:
        got = client.do_get(fl.Ticket(b"core.electrodes")).read_all()
        result["rows"] = got.num_rows
    except pa.ArrowException as err:
        result["error"] = type(err).__name__
        result["message"] = str(err)
        result["extra_info"] = getattr(err, "extra_info", b"")
    if mode in ("findings", "silent"):
        result["actions"] = [a.type for a in client.list_actions()]
        try:
            answer = next(client.do_action(fl.Action("report", b"")))
            result["report"] = json.loads(answer.body.to_pybytes())
        except pa.ArrowException as err:
            result["report_error"] = type(err).__name__
    client.close()
    child.terminate()
    child.wait()
    result["stderr"] = child.stderr.read()
    return result


def main() -> int:
    """Measure every mode and print what a build is left holding."""
    with tempfile.TemporaryDirectory() as tmp:
        died = run("dies", tmp)
        print("**The adapter never binds.** A build retrying the socket sees the exit rather than")
        print(f"waiting on it: detected in {died['detected_ms']:.0f} ms, and standard error carries")
        print(f"  {died['stderr'].strip().splitlines()[-1]!r}\n")

        raised = run("raises", tmp)
        print("**A plain exception in `do_get`.** What crosses is a string:")
        print(
            f"  {raised['error']}, message {len(raised['message'])} chars, extra_info {len(raised['extra_info'])} bytes"
        )
        print(f"  {raised['message'].strip().splitlines()[0][:96]!r}")
        print(f"  standard error: {len(raised['stderr'])} bytes\n")

        structured = run("structured", tmp)
        info = json.loads(structured["extra_info"])
        print("**A structured failure.** The same call, with the finding attached to it:")
        print(
            f"  {structured['error']}, message {len(structured['message'])} chars, "
            f"extra_info {len(structured['extra_info'])} bytes of JSON"
        )
        print(f"  parsed: level={info['level']!r} resource={info['resource']!r}")
        print(f"  standard error: {len(structured['stderr'])} bytes\n")

        mid = run("midstream", tmp)
        print("**A failure partway through a stream.** Two batches had already crossed:")
        print(f"  {mid['error']}, rows delivered to the build: {mid.get('rows', 0)}\n")

        found = run("findings", tmp)
        meta = json.loads(found["app_metadata"])
        print("**A run that succeeded and has something to say.** Two places carry it in band:")
        print(f"  discovery `app_metadata`, per resource: {len(found['app_metadata'])} bytes, level={meta['level']!r}")
        print(
            f"  `DoAction('report')`, per run, after the rows: "
            f"{len(found['report']['problems'])} problem(s), read {found['report']['read']}"
        )
        print(f"  rows still delivered: {found['rows']}")

        silent = run("silent", tmp)
        print("\n**An adapter with nothing to say.** Asking costs a build one refused call:")
        print(f"  ListActions: {silent['actions']}, DoAction: {silent.get('report_error')}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(main())

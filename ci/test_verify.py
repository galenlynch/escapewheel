"""Regression tests for the root verifier's runtime gate."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from unittest import mock

import verify
from ci import runtime_capabilities


class VerifierRuntimeGateTests(unittest.TestCase):
    """Keep an unsuitable runtime from reaching slow repository work."""

    def test_full_run_stops_when_the_runtime_gate_fails(self) -> None:
        with (
            mock.patch.object(sys, "argv", ["verify.py"]),
            mock.patch.object(verify, "STAGES", [("must not run", verify.ROOT, [])]),
            mock.patch.object(verify, "SUITES", ()),
            mock.patch.object(verify, "GENERATED", ()),
            mock.patch.object(verify, "run", return_value=(False, "blocked")) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = verify.main()

        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], "runtime: full-suite capabilities")

    def test_quick_run_bypasses_the_runtime_gate(self) -> None:
        with (
            mock.patch.object(sys, "argv", ["verify.py", "--quick"]),
            mock.patch.object(verify, "STAGES", []),
            mock.patch.object(verify, "SUITES", ()),
            mock.patch.object(verify, "GENERATED", ()),
            mock.patch.object(verify, "run") as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = verify.main()

        self.assertEqual(result, 0)
        run.assert_not_called()

    def test_successful_runtime_gate_precedes_repository_stages(self) -> None:
        stage = ("ordinary stage", verify.ROOT, ["ordinary"])
        with (
            mock.patch.object(sys, "argv", ["verify.py"]),
            mock.patch.object(verify, "STAGES", [stage]),
            mock.patch.object(verify, "SUITES", ()),
            mock.patch.object(verify, "GENERATED", ()),
            mock.patch.object(verify, "run", side_effect=[(True, "capable"), (True, "ordinary")]) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = verify.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            ["runtime: full-suite capabilities", "ordinary stage"],
        )


class CapabilitySupervisorTests(unittest.TestCase):
    """Keep an unresponsive primitive bounded by the supervisor."""

    def test_first_timeout_stops_later_probes(self) -> None:
        timeout = subprocess.TimeoutExpired("probe", runtime_capabilities.PROBE_TIMEOUT)
        with (
            mock.patch.object(sys, "argv", ["runtime_capabilities.py"]),
            mock.patch.object(runtime_capabilities.subprocess, "run", side_effect=timeout) as run,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = runtime_capabilities.main()

        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()

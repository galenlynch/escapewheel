"""Regression tests for the root verifier's runtime gate."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from unittest import mock

import verify
from tools import runtime_capabilities


class VerifierRuntimeGateTests(unittest.TestCase):
    """Keep an unsuitable runtime from reaching slow repository work."""

    def test_full_run_stops_when_the_runtime_gate_fails(self) -> None:
        with (
            mock.patch.object(sys, "argv", ["verify.py"]),
            mock.patch.object(verify, "STAGES", [verify.Stage("must not run", verify.ROOT, verify.ROOT, ())]),
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
        stage = verify.Stage("ordinary stage", verify.ROOT, verify.ROOT, ("ordinary",))
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


class StageOrderTests(unittest.TestCase):
    """Keep a stage that reads the tree from running before one that writes it."""

    def _run(
        self, stages: list[verify.Stage], outcomes: dict[str, bool], *arguments: str
    ) -> tuple[int, list[str], str]:
        started: list[str] = []

        def run(name: str, *_: object) -> tuple[bool, str]:
            started.append(name)
            return outcomes.get(name, True), name

        printed = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["verify.py", "--quick", *arguments]),
            mock.patch.object(verify, "STAGES", stages),
            mock.patch.object(verify, "GENERATED", ()),
            mock.patch.object(verify, "run", side_effect=run),
            contextlib.redirect_stdout(printed),
        ):
            return verify.main(), started, printed.getvalue()

    def test_writers_run_first_in_declared_order(self) -> None:
        stages = [
            verify.Stage("reads", verify.ROOT, verify.ROOT, ()),
            verify.Stage("writes first", verify.ROOT, verify.ROOT, (), writes=True),
            verify.Stage("writes second", verify.ROOT, verify.ROOT, (), writes=True),
        ]
        result, started, _ = self._run(stages, {})

        self.assertEqual(result, 0)
        self.assertEqual(started, ["writes first", "writes second", "reads"])

    def test_one_job_runs_the_readers_in_declared_order(self) -> None:
        stages = [verify.Stage(name, verify.ROOT, verify.ROOT, ()) for name in ("a", "b", "c", "d")]
        _, started, _ = self._run(stages, {}, "--jobs", "1")

        self.assertEqual(started, ["a", "b", "c", "d"])

    def test_a_failure_among_stages_run_together_fails_the_run_and_stops_no_other(self) -> None:
        stages = [verify.Stage(name, verify.ROOT, verify.ROOT, ()) for name in ("a", "b", "c")]
        result, started, printed = self._run(stages, {"b": False})

        self.assertEqual(result, 1)
        self.assertEqual(sorted(started), ["a", "b", "c"])
        self.assertIn("1 stage(s) failed:\n  b\n", printed)

    def test_only_the_generators_write(self) -> None:
        self.assertEqual(
            [stage.name for stage in [*verify.STAGES, *verify.SUITES] if stage.writes],
            [
                "spec: generate",
                "extensions: generate",
                "root: the documents' counts are current",
                "corpus: write every packet",
            ],
        )


class StageTableTests(unittest.TestCase):
    """Keep the stage table uniform, since other tools read its names and commands."""

    def test_every_stage_names_its_environment_and_runs_python_or_pytest(self) -> None:
        for stage in [verify.RUNTIME_CAPABILITY_STAGE, *verify.STAGES, *verify.SUITES]:
            with self.subTest(stage=stage.name):
                self.assertEqual(stage.argv[:4], ["uv", "run", "--project", str(stage.project)])
                self.assertIn(stage.command[0], {"python", "pytest"})
                self.assertTrue((stage.project / "pyproject.toml").is_file())

    def test_stage_names_are_unique(self) -> None:
        names = [stage.name for stage in [*verify.STAGES, *verify.SUITES]]
        self.assertEqual(len(names), len(set(names)))


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

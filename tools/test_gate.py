"""Tests for the gate's choice of package suites."""

from __future__ import annotations

import unittest

import verify
from tools import gate

ROOT = gate.ROOT


def _names(paths: list[str]) -> set[str]:
    return {stage.name for stage in gate.suites_for([ROOT / path for path in paths])}


class SuiteSelectionTests(unittest.TestCase):
    def test_every_suite_depends_on_its_own_directory(self) -> None:
        dependencies = gate.suite_dependencies()
        for stage in verify.SUITES:
            self.assertIn(stage.cwd, dependencies[stage.cwd])

    def test_a_reader_change_selects_every_suite_built_on_the_reader(self) -> None:
        selected = _names(["escapewheel-reader/src/escapewheel_reader/__init__.py"])
        self.assertIn("escapewheel-reader: tests", selected)
        self.assertIn("escapewheel-writer: tests", selected)
        self.assertIn("escapewheel-aind: tests", selected)
        self.assertIn("examples/lick-wheel: tests", selected)
        self.assertIn("integration: tests", selected)

    def test_an_aind_change_selects_only_the_aind_suite(self) -> None:
        self.assertEqual(_names(["escapewheel-aind/src/escapewheel_aind/video.py"]), {"escapewheel-aind: tests"})

    def test_a_change_outside_every_package_selects_no_suite(self) -> None:
        self.assertEqual(_names(["TODO.md", "spec/parts/02_core_logical_schemas.md"]), set())


if __name__ == "__main__":
    unittest.main()

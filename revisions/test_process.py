"""Focused conformance checks for the revision lifecycle established by R120."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spec" / "tools"))

import combine
from revisions import check_citations, impact, ledger, process_rules, stages


def metadata(**values: str) -> str:
    """Render the metadata rows needed by the stage validator."""
    return "\n".join(f"| **{name}** | {value} |" for name, value in values.items())


class ProcessSemanticsTests(unittest.TestCase):
    """Exercise each stable R120 process-check identifier."""

    def test_decision_domain_legacy_cutoff(self) -> None:
        self.assertEqual(stages.accepted(Path("R119-legacy.md")), [])
        self.assertEqual(
            stages.accepted(ROOT / "revisions/accepted/R120-allow-controlled-specification-reorganization.md"),
            [],
        )

    def test_decision_domain_required_prospectively(self) -> None:
        errors = stages.lifecycle_metadata(Path("future.md"), "", proposal_stage=True)
        self.assertTrue(any("Decision domain" in error for error in errors))

    def test_change_form_required_prospectively(self) -> None:
        proposal = metadata(**{"Decision domain": "specification"})
        draft = metadata(**{"Decision domain": "specification"})
        self.assertEqual(
            stages.lifecycle_metadata(Path("proposal.md"), proposal, proposal_stage=True),
            [],
        )
        self.assertTrue(
            any(
                "Change form" in error
                for error in stages.lifecycle_metadata(Path("draft.md"), draft, proposal_stage=False)
            )
        )

    def test_process_amends_requires_path_anchor(self) -> None:
        text = metadata(
            **{
                "Decision domain": "process",
                "Change form": "ordinary",
                "Profile": "not applicable",
                "Amends": "Part NN §x",
            }
        )
        errors = stages.lifecycle_metadata(Path("draft.md"), text, proposal_stage=False)
        self.assertTrue(any("path#anchor" in error for error in errors))

    def test_ledger_process_owner_resolves(self) -> None:
        dangling, malformed = ledger.unresolved(ledger.recorded())
        self.assertFalse([item for item in dangling if item[0].startswith("R120 ")])
        self.assertFalse([item for item in malformed if item[0].startswith("R120 ")])
        invalid = {
            "R120 §3.1": {
                "disposition": "applied",
                "where": [{"part": "00", "section": "1"}],
            }
        }
        self.assertTrue(ledger.unresolved(invalid)[0])

    def test_owner_backlink_not_required(self) -> None:
        self.assertFalse(hasattr(ledger, "uncorroborated"))
        self.assertFalse(hasattr(ledger, "corroboration_exception_defects"))

    def test_canonical_anchor_shape_and_identity(self) -> None:
        text = (ROOT / "revisions/CONTRIBUTING.md").read_text()
        identifiers = process_rules.canonical_anchor_occurrences(text)
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(len(identifiers), 7)

    def test_anchor_bootstrap_is_metadata_only(self) -> None:
        before = "## 1. Subject\nBody\n"
        after = '<a id="ew-subject" data-spec-anchor="canonical"></a>\n## 1. Subject\nBody\n'
        self.assertTrue(process_rules.anchor_bootstrap_only(before, after))
        self.assertFalse(process_rules.anchor_bootstrap_only(before, after.replace("Body", "Changed")))

    def test_linked_part_number_matches_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "spec"
            parts.mkdir()
            (parts / "02_subject.md").write_text(
                '<a id="ew-subject" data-spec-anchor="canonical"></a>\n\n## 7.1 Subject\n'
            )
            source = root / "guide.md"
            with (
                mock.patch.object(check_citations, "HERE", root / "revisions"),
                mock.patch.object(check_citations, "PARTS", parts),
            ):
                target = "spec/02_subject.md" + "#ew-subject"
                self.assertEqual(
                    check_citations.anchored(
                        source,
                        "[Part " + "02 §7.1](" + target + ")",
                    ),
                    [],
                )
                self.assertTrue(
                    check_citations.anchored(
                        source,
                        "[Part " + "02 §7.2](" + target + ")",
                    )
                )

    def test_anchor_impact_reports_live_citers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parts = Path(directory)
            (parts / "02_subject.md").write_text(
                '<a id="ew-subject" data-spec-anchor="canonical"></a>\n\n## 7.1 Subject\n'
            )
            with mock.patch.object(impact, "PARTS", parts):
                self.assertEqual(impact.anchor_location("ew-subject"), ("02", "7.1", "Subject"))

    def test_combined_rendering_preserves_unique_anchors(self) -> None:
        self.assertEqual(combine.duplicate_ids('<a id="one"></a>'), [])
        self.assertEqual(combine.duplicate_ids('<a id="one"></a>\n<a id="one"></a>'), ["one"])

    def test_part00_process_citations_are_repointed(self) -> None:
        sites = [site for section in ("10.1", "10.2", "10.3", "10.4") for site in impact.citers("00", section)]
        self.assertEqual([site for site in sites if not site.startswith("spec/parts/07_")], [])


class LedgerErrorTests(unittest.TestCase):
    """An unreadable ledger raises the ledger's own error, which an importer can catch."""

    def test_malformed_ledger_names_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "applied.toml"
            path.write_text("[clause\n")
            with mock.patch.object(ledger, "LEDGER", path), self.assertRaises(ledger.LedgerError) as raised:
                ledger.recorded()
        self.assertTrue(str(raised.exception).startswith("applied.toml: "))


ACCEPTED_RECORD = "# Subject\n\n| **Status** | **Accepted** |\n\n## 1. Motivation\n\nWhy.\n\n## 2. Decision\n\nWhat.\n"
RATIONALE = '[clause."R{} §2"]\ndisposition = "rationale"\n\n'
OTHER_ENTRIES = RATIONALE.format(1) + RATIONALE.format(3)


def superseded(fields: str) -> str:
    """Render a ledger whose entry for the second revision's clause is superseded."""
    return f'[clause."R2 §2"]\ndisposition = "superseded"\n{fields}\n{OTHER_ENTRIES}'


class LedgerCheckTests(unittest.TestCase):
    """The ledger check resolves each successor, admits no undisposed clause, and writes no file."""

    def check(self, entries: str, *arguments: str) -> tuple[int, str]:
        """Check `entries` against accepted revisions 1 to 3, each deciding one clause, §2."""
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "accepted").mkdir()
            for number in (1, 2, 3):
                (root / "accepted" / f"R{number}-subject.md").write_text(ACCEPTED_RECORD)
            (root / "applied.toml").write_text(entries)
            (root / "registry-targets.toml").write_text("")
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            report = io.StringIO()
            with (
                mock.patch.object(ledger, "REVISIONS", root / "accepted"),
                mock.patch.object(ledger, "LEDGER", root / "applied.toml"),
                mock.patch.object(ledger, "REGISTRY_TARGETS", root / "registry-targets.toml"),
                contextlib.redirect_stdout(report),
            ):
                status = ledger.main(list(arguments))
            self.assertEqual({path: path.read_bytes() for path in root.rglob("*") if path.is_file()}, before)
        return status, report.getvalue()

    def assert_names(self, report: str, label: str, clause: str = "R2 §2") -> None:
        """Assert that a line of the report carries `label` and names `clause`."""
        self.assertTrue(
            any(line.split()[:3] == [label, *clause.split()] for line in report.splitlines()),
            report,
        )

    def test_superseded_by_later_accepted_revision_passes(self) -> None:
        for fields in ('by = "R3"', 'by = "R3"\nnote = "R3 §2 restates the rule"'):
            with self.subTest(fields=fields):
                status, report = self.check(superseded(fields))
                self.assertEqual(status, 0, report)
                self.assertNotIn("SUCCESSOR", report)

    def test_superseded_without_by_fails(self) -> None:
        status, report = self.check(superseded('note = "replaced"'))
        self.assertEqual(status, 1)
        self.assert_names(report, "SUCCESSOR")

    def test_superseded_by_not_one_revision_string_fails(self) -> None:
        for by in ('["R3"]', '"R3 §2"', '"3"', '"R3, R4"', "3"):
            with self.subTest(by=by):
                status, report = self.check(superseded(f"by = {by}"))
                self.assertEqual(status, 1)
                self.assert_names(report, "SUCCESSOR")

    def test_superseded_by_unaccepted_revision_fails(self) -> None:
        status, report = self.check(superseded('by = "R9"'))
        self.assertEqual(status, 1)
        self.assert_names(report, "SUCCESSOR")

    def test_superseded_by_own_or_earlier_revision_fails(self) -> None:
        for by in ("R2", "R1"):
            with self.subTest(by=by):
                status, report = self.check(superseded(f'by = "{by}"'))
                self.assertEqual(status, 1)
                self.assert_names(report, "SUCCESSOR")

    def test_superseded_carrying_where_fails(self) -> None:
        for where in ('[{ part = "02", section = "2" }]', '"Part 02 §2"'):
            with self.subTest(where=where):
                status, report = self.check(superseded(f'by = "R3"\nwhere = {where}'))
                self.assertEqual(status, 1)
                self.assert_names(report, "SUCCESSOR")

    def test_clause_without_entry_fails(self) -> None:
        for arguments in ((), ("--summary",)):
            with self.subTest(arguments=arguments):
                status, report = self.check(OTHER_ENTRIES, *arguments)
                self.assertEqual(status, 1)
                self.assert_names(report, "UNDISPOSED")

    def test_ledger_keeps_no_undisposed_count(self) -> None:
        self.assertEqual(set(tomllib.loads(ledger.LEDGER.read_text())), {"clause"})
        status, report = self.check("[baseline]\nundisposed = 1\n\n" + OTHER_ENTRIES)
        self.assertEqual(status, 1)
        self.assert_names(report, "UNDISPOSED")

    def test_check_writes_no_file(self) -> None:
        # `check` compares every file under its scratch tree before and after the run.
        self.assertEqual(self.check(superseded('by = "R3"'))[0], 0)
        self.assertEqual(self.check(superseded('by = "R1"'))[0], 1)
        self.assertEqual(self.check(OTHER_ENTRIES)[0], 1)
        before = ledger.LEDGER.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            ledger.main(["--summary"])
        self.assertEqual(ledger.LEDGER.read_bytes(), before)

    def test_incorporated_ledger_resolves_every_superseded_entry(self) -> None:
        recorded = ledger.recorded()
        self.assertTrue([key for key, entry in recorded.items() if entry.get("disposition") == "superseded"])
        self.assertEqual(ledger.successor_defects(recorded, ledger.accepted_revisions()), [])
        report = io.StringIO()
        with contextlib.redirect_stdout(report):
            self.assertEqual(ledger.main(["--summary"]), 0, report.getvalue())


if __name__ == "__main__":
    unittest.main()

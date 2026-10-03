"""Focused conformance checks for the revision lifecycle and its process tools."""

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
        errors = stages.lifecycle_metadata(Path("R130-subject.md"), "")
        self.assertTrue(any("Decision domain" in error for error in errors))

    def test_change_form_required_prospectively(self) -> None:
        record = metadata(**{"Decision domain": "specification"})
        self.assertTrue(
            any("Change form" in error for error in stages.lifecycle_metadata(Path("R130-subject.md"), record))
        )
        record += "\n" + metadata(**{"Change form": "ordinary"})
        self.assertEqual(stages.lifecycle_metadata(Path("R130-subject.md"), record), [])

    def test_process_amends_requires_path_anchor(self) -> None:
        text = metadata(
            **{
                "Decision domain": "process",
                "Change form": "ordinary",
                "Profile": "not applicable",
                "Amends": "Part NN §x",
            }
        )
        errors = stages.lifecycle_metadata(Path("R130-subject.md"), text)
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
        self.assertEqual(len(identifiers), 17)

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


#: A commit this repository holds, standing in for a document's baseline.
BASELINE = "`9462b393a00e9e681b7a38528112483b6a5aa206`"
OPEN_DOCUMENT = (
    "# Subject\n\n| | |\n|---|---|\n"
    + metadata(Status="**Open**", Opened="2026-10-02", **{"Based on": BASELINE}, Affects="Part 02 §6")
    + "\n\n## 1. Problem\n\nWhy.\n\n## 2. Evidence\n\nSeen.\n\n## 3. Preferred direction\n\nThis way.\n\n"
    "## 4. Questions\n\n1. **Which way?** **Answered 2026-10-02: this one.**\n2. **How far?**\n\n"
    "## 5. Consequence\n\nNone.\n"
)
READY_DOCUMENT = (
    "# Subject\n\n| | |\n|---|---|\n"
    + metadata(
        Status="**Ready**",
        Opened="2026-10-02",
        **{
            "Based on": BASELINE,
            "Change form": "ordinary",
            "Amends": "Part 02 §6",
            "Depends on": "none",
            "Profile": "all",
            "Decision clauses": "§3.1",
        },
    )
    + "\n\n## 1. Problem\n\nWhy.\n\n## 2. Evidence\n\nSeen.\n\n## 3. Decision\n\n### 3.1 Rule\n\n"
    "A writer MUST do it.\n\n## 4. Questions\n\n1. **Which way?** **Answered 2026-10-02: this one.**\n"
    "2. **How far?**\n   **Answered 2026-10-02: far.**\n\n## 5. Consequence\n\nNone.\n\n"
    "## 6. Conformance and implementation evidence\n\nA test.\n"
)
#: An accepted record numbered after R167, which declares no decision domain.
LATER_RECORD = READY_DOCUMENT.replace("**Ready**", "**Accepted** 2026-10-02")


class ChangeDocumentTests(unittest.TestCase):
    """The stage check reads a change document at the status it declares."""

    def errors(self, text: str, name: str = "subject.md") -> list[str]:
        """Return the stage defects of `text` written as a change document named `name`."""
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / name
            path.write_text(text)
            return stages.change(path)

    def test_open_document_with_unanswered_questions_passes(self) -> None:
        self.assertEqual(self.errors(OPEN_DOCUMENT), [])

    def test_ready_document_with_every_answer_passes(self) -> None:
        self.assertEqual(self.errors(READY_DOCUMENT), [])

    def test_accepted_record_without_domain_passes(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "R168-subject.md"
            path.write_text(LATER_RECORD)
            self.assertEqual(stages.accepted(path), [])
            path = Path(scratch) / "R166-subject.md"
            path.write_text(LATER_RECORD)
            self.assertTrue(any("Decision domain" in error for error in stages.accepted(path)))
        for name in (
            "R120-allow-controlled-specification-reorganization.md",
            "R158-the-ledger-resolves-a-superseded-entrys-successor-and-keeps-no-ratchet.md",
        ):
            with self.subTest(record=name):
                record = ROOT / "revisions/accepted" / name
                self.assertTrue(record.is_file())
                self.assertEqual(stages.accepted(record), [])

    def test_ready_question_without_answer_fails(self) -> None:
        text = READY_DOCUMENT.replace("   **Answered 2026-10-02: far.**\n", "")
        self.assertIn("question 2 has no recorded answer", self.errors(text))

    def test_open_document_with_bcp14_fails(self) -> None:
        text = OPEN_DOCUMENT.replace("This way.", "A writer MUST do it.")
        self.assertTrue(any("BCP 14" in error for error in self.errors(text)))

    def test_change_document_with_domain_number_or_status_fails(self) -> None:
        domain = OPEN_DOCUMENT.replace("| **Opened**", "| **Decision domain** | specification |\n| **Opened**")
        self.assertTrue(any("Decision domain" in error for error in self.errors(domain)))
        numbered = self.errors(OPEN_DOCUMENT, "R168-subject.md")
        self.assertTrue(any("revision number" in error for error in numbered))
        for status in ("**Proposal**", "**Draft**", "**Accepted** 2026-10-02"):
            with self.subTest(status=status):
                text = OPEN_DOCUMENT.replace("**Open**", status)
                self.assertTrue(any("status is" in error for error in self.errors(text)))

    def test_document_under_retired_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            proposals, drafts = Path(scratch) / "proposals", Path(scratch) / "drafts"
            drafts.mkdir()
            (drafts / "subject.md").write_text(READY_DOCUMENT)
            with mock.patch.object(stages, "RETIRED", (proposals, drafts)):
                self.assertEqual(stages.retired(), [drafts / "subject.md"])
        self.assertEqual(stages.retired(), [])

    def test_accepted_record_citing_change_document_fails(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            accepted = Path(scratch)
            changes = accepted / "changes"
            changes.mkdir()
            (changes / "subject.md").write_text(OPEN_DOCUMENT)
            later, earlier = accepted / "R168-later.md", accepted / "R166-earlier.md"
            for path in (later, earlier):
                path.write_text("As `subject.md` and `revisions/drafts/old.md` say.\n")
            with (
                mock.patch.object(check_citations, "ACCEPTED", accepted),
                mock.patch.object(check_citations, "CHANGES", changes),
            ):
                self.assertEqual(len(check_citations.unaccepted_citations(later)), 2)
                self.assertEqual(check_citations.unaccepted_citations(earlier), [])


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

    def test_noted_entry_from_r167_fails(self) -> None:
        later = {
            "entry": '[clause."R3 §2"]\ndisposition = "rationale"\nnote = "why"\n\n',
            "destination": '[clause."R3 §2"]\ndisposition = "applied"\n'
            'where = [{ path = "revisions/CONTRIBUTING.md", anchor = "ew-acceptance", note = "where" }]\n\n',
        }
        earlier = '[clause."R1 §2"]\ndisposition = "rationale"\nnote = "kept"\n\n' + RATIONALE.format(2)
        # The scratch revisions are numbered 1 to 3, so the third stands for R167.
        with mock.patch.object(ledger, "NOTELESS_FROM", 3):
            for case, entry in later.items():
                with self.subTest(case=case):
                    status, report = self.check(earlier + entry)
                    self.assertEqual(status, 1)
                    self.assert_names(report, "NOTED", "R3 §2")
            status, report = self.check(earlier + RATIONALE.format(3))
            self.assertEqual(status, 0, report)

    def test_incorporated_ledger_carries_no_new_note(self) -> None:
        recorded = ledger.recorded()
        self.assertTrue([key for key in recorded if key.startswith("R167 ")])
        self.assertEqual(ledger.noted(recorded), [])

    def test_incorporated_ledger_resolves_every_superseded_entry(self) -> None:
        recorded = ledger.recorded()
        self.assertTrue([key for key, entry in recorded.items() if entry.get("disposition") == "superseded"])
        self.assertEqual(ledger.successor_defects(recorded, ledger.accepted_revisions()), [])
        report = io.StringIO()
        with contextlib.redirect_stdout(report):
            self.assertEqual(ledger.main(["--summary"]), 0, report.getvalue())


if __name__ == "__main__":
    unittest.main()

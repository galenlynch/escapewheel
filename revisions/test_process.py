"""Focused conformance checks for the revision lifecycle established by R120."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "escapewheel_poc_docs_v0.2"))

import combine

import release
from revisions import check_citations, impact, ledger, process_rules, stages


def metadata(**values: str) -> str:
    """Render the metadata rows needed by the stage validator."""
    return "\n".join(f"| **{name}** | {value} |" for name, value in values.items())


class ProcessSemanticsTests(unittest.TestCase):
    """Exercise each stable R120 process-check identifier."""

    def test_decision_domain_legacy_cutoff(self) -> None:
        self.assertEqual(stages.accepted(Path("R119-legacy.md")), [])
        derived = json.loads((ROOT / "registry/logical_schemas.json").read_text())[
            "derived_from"
        ]["revisions"]
        self.assertIn("R119", derived)
        self.assertNotIn("R120", derived)

    def test_decision_domain_required_prospectively(self) -> None:
        errors = stages.lifecycle_metadata(Path("future.md"), "", proposal_stage=True)
        self.assertTrue(any("Decision domain" in error for error in errors))

    def test_change_form_required_prospectively(self) -> None:
        proposal = metadata(**{"Decision domain": "specification"})
        draft = metadata(**{"Decision domain": "specification"})
        self.assertEqual(
            stages.lifecycle_metadata(
                Path("proposal.md"), proposal, proposal_stage=True
            ),
            [],
        )
        self.assertTrue(
            any(
                "Change form" in error
                for error in stages.lifecycle_metadata(
                    Path("draft.md"), draft, proposal_stage=False
                )
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
        after = (
            '<a id="ew-subject" data-spec-anchor="canonical"></a>\n'
            "## 1. Subject\nBody\n"
        )
        self.assertTrue(process_rules.anchor_bootstrap_only(before, after))
        self.assertFalse(
            process_rules.anchor_bootstrap_only(
                before, after.replace("Body", "Changed")
            )
        )

    def test_linked_part_number_matches_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parts = root / "spec"
            parts.mkdir()
            (parts / "02_subject.md").write_text(
                '<a id="ew-subject" data-spec-anchor="canonical"></a>\n\n'
                "## 7.1 Subject\n"
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
                '<a id="ew-subject" data-spec-anchor="canonical"></a>\n\n'
                "## 7.1 Subject\n"
            )
            with mock.patch.object(impact, "PARTS", parts):
                self.assertEqual(
                    impact.anchor_location("ew-subject"), ("02", "7.1", "Subject")
                )

    def test_combined_rendering_preserves_unique_anchors(self) -> None:
        self.assertEqual(combine.duplicate_ids('<a id="one"></a>'), [])
        self.assertEqual(
            combine.duplicate_ids('<a id="one"></a>\n<a id="one"></a>'), ["one"]
        )

    def test_part00_process_citations_are_repointed(self) -> None:
        sites = [
            site
            for section in ("10.1", "10.2", "10.3", "10.4")
            for site in impact.citers("00", section)
        ]
        live_process = [
            site
            for site in sites
            if not site.startswith("revisions/accepted/")
            and not site.startswith("escapewheel_poc_docs_v0.2/07_")
        ]
        self.assertEqual(live_process, [])
        self.assertEqual(len(sites), 5)

    def test_release_generator_selects_moved_ledger(self) -> None:
        self.assertEqual(release.PARTS["provenance"], ("revisions/applied.toml",))
        self.assertEqual(
            release.digest(ROOT / release.PARTS["provenance"][0]),
            release.digest(ROOT / "revisions/applied.toml"),
        )


if __name__ == "__main__":
    unittest.main()

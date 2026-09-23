"""Focused regression tests for the revision evidence closure checker."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from revisions import evidence


class EvidenceTests(unittest.TestCase):
    """Exercise every evidence kind and a complete no-code clause manifest."""

    def test_owner_targets_resolve_by_anchor_and_pointer(self) -> None:
        self.assertEqual(
            evidence.owner_defects(
                {
                    "path": "revisions/CONTRIBUTING.md",
                    "anchor": "ew-decision-domains",
                }
            ),
            [],
        )
        self.assertEqual(
            evidence.owner_defects(
                {
                    "path": "registry/logical_schemas.json",
                    "pointer": "/resources/core.units/table",
                }
            ),
            [],
        )

    def test_fixture_and_verifier_stage_are_collected(self) -> None:
        queued: list[tuple[str, str]] = []
        self.assertEqual(
            evidence.evidence_defects(
                {
                    "evidence": [
                        {
                            "kind": "fixture",
                            "packet": "dup_pk",
                            "finding": "core.intervals.primary_key_unique",
                        },
                        {
                            "kind": "check",
                            "stage": "registry: structural checks",
                            "id": "every Tier 2 rule conforms and executes against empty tables",
                        },
                    ]
                },
                queued,
            ),
            [],
        )

    def test_complete_manifest_with_nonexecutable_clause(self) -> None:
        revision = "R" + "999"
        clause = revision + " §3.1"
        baseline = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=evidence.ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        document = {
            "version": 1,
            "revision": revision,
            "based_on": baseline,
            "clauses": {
                clause: {
                    "owners": [
                        {
                            "path": "revisions/CONTRIBUTING.md",
                            "anchor": "ew-decision-domains",
                        }
                    ],
                    "projections": {
                        "paths": [
                            "escapewheel_poc_docs_v0.2/Escapewheel_POC_v0.2_Implementation_Spec.md"
                        ]
                    },
                    "conformance": {
                        "not_applicable": "publication ownership has no executable packet case"
                    },
                    "implementations": {
                        "unchanged": "the clause assigns publication ownership, not behavior"
                    },
                    "documentation": {"paths": ["escapewheel_poc_docs_v0.2/README.md"]},
                }
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / f"{revision}.json"
            path.write_text(json.dumps(document))
            queued: list[tuple[str, str]] = []
            self.assertEqual(
                evidence.manifest_defects(path, revision, {clause}, queued), []
            )
            self.assertEqual(queued, [])


if __name__ == "__main__":
    unittest.main()

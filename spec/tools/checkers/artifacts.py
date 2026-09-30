"""Where the checkers find the incorporated artifacts: the tree's `artifacts/` directory."""

from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"

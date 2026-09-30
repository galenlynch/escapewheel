"""Where the copied checkers find this package's copies of the incorporated artifacts."""

from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parent / "schemas"

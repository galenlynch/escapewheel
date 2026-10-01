"""Where the copied checkers find this package's copies of the incorporated artifacts.

- :data:`ARTIFACTS` -- the directory holding them.
"""

from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parent / "schemas"

__all__: list[str] = []

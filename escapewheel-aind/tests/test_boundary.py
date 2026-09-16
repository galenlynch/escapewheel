"""What this distribution may rely on from the writer, asserted rather than assumed.

Every kind here reaches a build through an entry point rather than through the writer's own table,
so the two names that have to agree are the group this package publishes under and the group the
writer loads. They are in different distributions and nothing else compares them: a typo in either
registers a kind no build ever sees, and the failure is silence rather than an error.
"""

from __future__ import annotations

import ast
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

from escapewheel_writer.sources import SOURCE_GROUP

PYPROJECT = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())

#: The import name, which is what a dependency is spelled as. The distribution name differs by a
#: hyphen, and `entry_points` reports that one.
PACKAGE = "escapewheel_aind"


def test_the_group_this_package_publishes_under_is_the_one_the_writer_loads():
    """A kind registered under any other name is loaded by nothing and reported by nothing."""
    published = PYPROJECT["project"]["entry-points"]
    assert SOURCE_GROUP in published, f"pyproject registers {sorted(published)}, and the writer loads {SOURCE_GROUP}"


def test_every_registered_kind_loads():
    """`discovered()` skips a kind whose entry point raises, so a broken one is a warning there.

    Here it is a failure: this package's own kinds are not third-party plugins to be tolerated.
    """
    failed = {}
    for entry in entry_points(group=SOURCE_GROUP):
        if entry.dist is not None and entry.dist.name != "escapewheel-aind":
            continue
        try:
            entry.load()
        except Exception as exc:  # noqa: BLE001 - the point is to report every one, not the first
            failed[entry.name] = f"{type(exc).__name__}: {exc}"
    assert failed == {}


def test_the_writer_does_not_import_this_package():
    """One direction only, or the boundary is a cycle and moving this out stops being packaging.

    Read as imports rather than as text. The writer may **name** this package and may not depend on
    it: `clock.py` points a reader at the adapter that moved, which is worth keeping and is not a
    dependency, where matching the name anywhere would forbid the two together.
    """
    writer = Path(__file__).resolve().parents[2] / "escapewheel-writer" / "src"
    offending = []
    for path in sorted(writer.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                # A relative import has no module name and cannot reach another distribution.
                imported = [node.module or ""]
            else:
                continue
            if any(name == PACKAGE or name.startswith(f"{PACKAGE}.") for name in imported):
                offending.append(f"{path.relative_to(writer)}:{node.lineno}")
    assert offending == []

"""This package's copies agree with the specification's tree they come from."""

from pathlib import Path

import pytest
import tomllib

PACKAGE = Path(__file__).resolve().parents[1]
TREE = PACKAGE.parent / "spec"
COPIES = tomllib.loads((PACKAGE / "pyproject.toml").read_text())["tool"]["escapewheel"]["copies"]


@pytest.mark.skipif(not TREE.is_dir(), reason="the specification's tree is not beside this package")
@pytest.mark.parametrize(("copy", "source"), COPIES.items(), ids=list(COPIES))
def test_a_copy_matches_its_source(copy, source):
    assert (PACKAGE / copy).read_bytes() == (TREE / source).read_bytes(), "run copies.py at the monorepo root"

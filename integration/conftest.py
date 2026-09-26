import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import example


@pytest.fixture(scope="session")
def packet_root(tmp_path_factory):
    """The example packet, committed once and shared by every test that only reads it."""
    root = tmp_path_factory.mktemp("example") / example.SESSION
    example.build(root)
    return root

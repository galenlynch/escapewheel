import pytest
from corpus_packets import VALID


@pytest.fixture(scope="session")
def valid(tmp_path_factory):
    """The conformance corpus's valid packet, built once; a test that changes it restores it."""
    root = tmp_path_factory.mktemp("corpus") / VALID.name
    VALID.build(root)
    return root

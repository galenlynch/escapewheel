"""Example test module."""

import nwb_lake_writer


def test_version():
    """Test that version is defined."""
    assert nwb_lake_writer.__version__ is not None
    assert isinstance(nwb_lake_writer.__version__, str)

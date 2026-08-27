"""Example test module."""

import nwb_lake_validator


def test_version():
    """Test that version is defined."""
    assert nwb_lake_validator.__version__ is not None
    assert isinstance(nwb_lake_validator.__version__, str)

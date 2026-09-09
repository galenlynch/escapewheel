import json
from pathlib import Path

import pytest

REGISTRY = json.loads((Path(__file__).resolve().parents[2] / "registry" / "logical_schemas.json").read_text())


@pytest.fixture
def registry():
    """The reference registry, read from the sibling repository."""
    return REGISTRY


@pytest.fixture
def minimal():
    """The smallest set of records that validates: one session, one subject, one clock."""
    return {
        "core.subjects": [{"subject_id": "m001", "species": "Mus musculus", "sex": "male"}],
        "core.sessions": [
            {
                "session_id": "s001",
                "subject_id": "m001",
                "session_start_time": "2026-08-27T00:00:00Z",
            }
        ],
        "core.clocks": [
            {
                "clock_id": "harp_s001",
                "session_id": "s001",
                "clock_name": "harp",
                "tick_rate_num": 31250,
                "tick_rate_den": 1,
                "origin": "harp_epoch",
            }
        ],
    }

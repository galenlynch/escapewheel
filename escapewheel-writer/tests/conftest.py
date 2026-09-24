import gzip
import hashlib
import json
from pathlib import Path

import pytest
from escapewheel_validator import check_registry_context

REGISTRY = json.loads((Path(__file__).resolve().parents[2] / "registry" / "logical_schemas.json").read_text())
REGISTRY_CONTEXT = check_registry_context(REGISTRY)


@pytest.fixture
def registry():
    """The reference registry, read from the sibling repository."""
    return REGISTRY_CONTEXT


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


def read_registry(root, registry_id="core"):
    """The registry a committed packet binds under `registry_id`, decoded."""
    manifest = json.loads((root / "packet.json").read_text())
    return json.loads(gzip.decompress((root / manifest["registries"][registry_id]["path"]).read_bytes()))


def rebind_registry(root, document):
    """Store an edited registry at its own versioned path and bind it, as a test's shortcut past a writer."""
    body = json.dumps(document, indent=2).encode()
    registry_id = document["registry_id"]
    relative = f"registries/{registry_id}/{document['registry_version']}.json.gz"
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_bytes(gzip.compress(body, mtime=0))
    path = root / "packet.json"
    manifest = json.loads(path.read_text())
    manifest["registries"][registry_id] |= {"path": relative, "sha256": hashlib.sha256(body).hexdigest()}
    path.write_text(json.dumps(manifest))

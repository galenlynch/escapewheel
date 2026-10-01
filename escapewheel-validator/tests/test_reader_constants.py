"""A core resource ID or a packet file name is the reader's constant, spelled in no module here."""

import ast
from pathlib import Path

from escapewheel_reader import resource_ids
from escapewheel_reader.location import SOURCES_FILENAME, SOURCES_VERSION
from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME
from escapewheel_reader.profile import PROFILE_ID
from escapewheel_reader.resources import ZARR_METADATA_FILENAMES

import escapewheel_validator

from .copies import COPIED_FILES as COPIED

SOURCE = Path(escapewheel_validator.__file__).resolve().parent

RESOURCE_IDS = {getattr(resource_ids, name) for name in resource_ids.__all__}
NAMES = {
    MANIFEST_FILENAME,
    MANIFESTS_DIRNAME,
    SOURCES_FILENAME,
    SOURCES_VERSION,
    PROFILE_ID,
    *ZARR_METADATA_FILENAMES.values(),
}


def _spelled(values):
    """Each string literal in a module of the package's own that is exactly one of `values`."""
    return [
        f"{path.relative_to(SOURCE)}:{node.lineno}: {node.value}"
        for path in sorted(SOURCE.rglob("*.py"))
        if path not in COPIED
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in values
    ]


def test_the_scan_reads_the_package_and_skips_the_copies():
    scanned = {path.name for path in SOURCE.rglob("*.py") if path not in COPIED}
    assert {"validator.py", "amendment.py", "manifest.py"} <= scanned
    assert not {path.name for path in COPIED} & scanned


def test_no_module_spells_a_named_resource_id():
    """A whole literal; an ID inside a message, a query or a check ID's template is not one."""
    assert _spelled(RESOURCE_IDS) == []


def test_no_module_spells_a_packet_file_name_or_identifier():
    assert _spelled(NAMES) == []

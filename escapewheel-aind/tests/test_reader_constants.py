"""A resource ID or a packet file name is a constant, spelled in no module here.

A core ID and a packet's file names are the reader's; an ID of an extension this package carries is
its own, in `resource_ids`.
"""

import ast
import json
from pathlib import Path

from escapewheel_reader import resource_ids as core_ids
from escapewheel_reader.location import SOURCES_FILENAME, SOURCES_VERSION
from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME
from escapewheel_reader.profile import PROFILE_ID
from escapewheel_reader.resources import ZARR_METADATA_FILENAMES

import escapewheel_aind
from escapewheel_aind import resource_ids

SOURCE = Path(escapewheel_aind.__file__).resolve().parent
EXTENSIONS = Path(__file__).resolve().parents[1] / "extensions"

CORE_IDS = {getattr(core_ids, name) for name in core_ids.__all__}
OWN = {name: getattr(resource_ids, name) for name in resource_ids.__all__}
NAMES = {
    MANIFEST_FILENAME,
    MANIFESTS_DIRNAME,
    SOURCES_FILENAME,
    SOURCES_VERSION,
    PROFILE_ID,
    *ZARR_METADATA_FILENAMES.values(),
}


def _spelled(values):
    """Each string literal, outside the constants module, that is exactly one of `values`."""
    return [
        f"{path.relative_to(SOURCE)}:{node.lineno}: {node.value}"
        for path in sorted(SOURCE.rglob("*.py"))
        if path != Path(resource_ids.__file__).resolve()
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in values
    ]


def test_the_scan_reads_the_package():
    scanned = {path.name for path in SOURCE.rglob("*.py")}
    assert {"session.py", "video.py", "nwb.py", "unit_qc.py"} <= scanned


def test_no_module_spells_a_named_resource_id():
    """A whole literal; an ID inside a message or a query is not one."""
    assert _spelled(CORE_IDS | set(OWN.values())) == []


def test_no_module_spells_a_packet_file_name_or_identifier():
    assert _spelled(NAMES) == []


def test_all_lists_every_constant_of_the_package_once():
    defined = {name for name, value in vars(resource_ids).items() if name.isupper() and isinstance(value, str)}
    assert sorted(defined) == sorted(resource_ids.__all__)


def test_a_constant_of_the_package_is_named_for_its_id():
    for name, value in OWN.items():
        assert name == value.replace(".", "_").upper()


def test_every_constant_of_the_package_names_a_resource_an_extension_declares():
    declared = {
        resource_id
        for document in sorted(EXTENSIONS.glob("*.json"))
        for resource_id in json.loads(document.read_text())["resources"]
    }
    assert sorted(value for value in OWN.values() if value not in declared) == []

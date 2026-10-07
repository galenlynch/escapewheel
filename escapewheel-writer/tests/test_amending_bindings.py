"""Which extensions an amendment binds: a held one it does not use is left out (Part 05 §15.1)."""

import copy
import gzip
import json

from escapewheel_reader import open_packet

from escapewheel_writer import PacketWriter
from escapewheel_writer.amending import Held
from escapewheel_writer.registries import Declarations
from tests.builders import import_runs
from tests.test_extensions import EXTENSION, TRIALS

#: An extension whose one table is an analysis resource, so an amendment may remove it (Part 05 §15.2).
DERIVED = {
    **{key: EXTENSION[key] for key in ("$schema", "registry_version", "logical_standard_version", "rule_language")},
    "registry_id": "derived",
    "extension_id": "derived",
    "resources": {
        "derived.device_counts": {
            "content_class": "analysis",
            "kind": "table",
            "instances": {"mode": "singleton", "presence": "optional"},
            "requires": [],
            "lineage": "required",
            "table": {
                "columns": [
                    {
                        "name": "session_id",
                        "type": "int32",
                        "presence": "required",
                        "role": "identifier",
                        "identity": "assigned",
                        "description": "Session identity.",
                    },
                    {
                        "name": "devices",
                        "type": "int64",
                        "presence": "required",
                        "role": "data",
                        "description": "How many devices the session declares.",
                    },
                ],
                "primary_key": ["session_id"],
                "amendment_groups": [],
                "references": [
                    {"columns": ["session_id"], "resource": "core.sessions", "resource_columns": ["session_id"]}
                ],
                "rules": [],
            },
        }
    },
}


def _device(name):
    return {"session_id": "s001", "device_id": name, "device_name": name}


def _trials():
    return [{"session_id": r["session_id"], "trial_id": r["interval_id"], "choice": "left"} for r in TRIALS]


def _commit(root, registry, tables, extensions, derived=None):
    writer = PacketWriter(registry, packet_id=root.name, extensions=extensions)
    for resource_id, records in tables.items():
        writer.add(resource_id, records)
    for resource_id, sources in (derived or {}).items():
        writer.derives(resource_id, sources)
    assert writer.commit(root).passed


def _amend(root, registry, extensions, *, unnamed, tables=None):
    """Amend `root` with `tables`, an import run by default, binding `unnamed` only because it binds them."""
    said: list[str] = []
    writer = PacketWriter(registry, packet_id=root.name, extensions=extensions)
    writer.amending(Held.open(root), unnamed=unnamed)
    for resource_id, records in (tables or {"core.processing_runs": import_runs()}).items():
        writer.add(resource_id, records)
    report = writer.amend(root, say=said.append)
    assert report.passed
    return report, said


def _bound(root):
    return set(json.loads((root / "packet.json").read_text())["registries"])


def test_an_amendment_leaves_out_a_held_extension_the_packet_does_not_use(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal, [EXTENSION])
    report, said = _amend(root, registry, [EXTENSION], unnamed={"task"})
    assert _bound(root) == {"core"}
    assert "  registry: task is left out, since the amended packet uses none of it" in said
    assert "packet.registry.unused" not in {f.check for f in report.findings}
    # The retained manifest that binds it still names a readable copy.
    retained = json.loads((root / "manifests" / "0.1.0.json").read_text())
    stored = root / retained["registries"]["task"]["path"]
    assert json.loads(gzip.decompress(stored.read_bytes()))["registry_id"] == "task"


def test_an_amendment_keeps_a_held_extension_the_packet_uses(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, {**minimal, "core.intervals": TRIALS, "task.trials": _trials()}, [EXTENSION])
    _, said = _amend(root, registry, [EXTENSION], unnamed={"task"})
    assert _bound(root) == {"core", "task"}
    assert not [line for line in said if line.startswith("  registry:")]


def test_an_amendment_binds_an_unused_extension_its_caller_names(tmp_path, registry, minimal):
    """Part 05 §3.1 binds what a recipe names, and validation warns of it (Part 04 §8)."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal, [EXTENSION])
    report, said = _amend(root, registry, [EXTENSION], unnamed=())
    assert _bound(root) == {"core", "task"}
    assert "  registry: task is bound and declares none of the packet's resources" in said
    assert [f.message.split(":")[0] for f in report.findings if f.check == "packet.registry.unused"] == ["task"]


def test_an_amendment_removing_an_extension_s_last_resource_leaves_it_out(tmp_path, registry, minimal):
    """Part 05 §15.2: the counts were derived from the devices the amendment adds to, so they go."""
    root = tmp_path / "s001"
    counts = [{"session_id": "s001", "devices": 1}]
    _commit(
        root,
        registry,
        {**minimal, "core.devices": [_device("d1")], "derived.device_counts": counts},
        [DERIVED],
        derived={"derived.device_counts": ["core.devices"]},
    )
    assert _bound(root) == {"core", "derived"}
    added = {"core.devices": [_device("d2")]}
    _, said = _amend(root, registry, [DERIVED], unnamed={"derived"}, tables=added)
    assert "derived.device_counts" not in [r.resource_id for r in open_packet(root).resources()]
    assert _bound(root) == {"core"}
    assert "  registry: derived is left out, since the amended packet uses none of it" in said


def test_an_extension_with_a_required_singleton_is_never_left_out(registry):
    required = copy.deepcopy(EXTENSION)
    required["resources"]["task.trials"]["instances"]["presence"] = "required"
    assert Declarations(registry, [required]).left_out(["task"], []) == []
    assert Declarations(registry, [EXTENSION]).left_out(["task"], []) == ["task"]
    assert Declarations(registry, [EXTENSION]).left_out([], []) == []

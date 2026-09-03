"""A packet carries an extension's table the same way it carries a core one (R17)."""

import json

import pytest
from nwb_lake_reader import open_packet
from nwb_lake_validator import validate

from nwb_lake_writer import PacketWriter

EXTENSION = {
    "registry_version": "0.1.0",
    "logical_standard_version": "0.1",
    "extension_id": "task",
    "extends": "nwb-lake-logical-v0.1",
    "tables": {
        "task.trials": {
            "columns": [
                {
                    "name": "session_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "assigned",
                },
                {
                    "name": "trial_id",
                    "type": "int32",
                    "presence": "required",
                    "role": "identifier",
                    "identity": "carried",
                },
                {"name": "choice", "type": "string", "presence": "nullable", "role": "data", "enum": ["left", "right"]},
            ],
            "primary_key": ["session_id", "trial_id"],
            "references": [
                {
                    "columns": ["session_id", "trial_id"],
                    "resource": "core.trials",
                    "resource_columns": ["session_id", "trial_id"],
                }
            ],
            "sort": ["session_id", "trial_id"],
            "rules": [],
        }
    },
}


TRIALS = [
    {"session_id": "s001", "trial_id": 0, "clock_id": "harp_s001", "start_tick": 0, "stop_tick": 99},
    {"session_id": "s001", "trial_id": 1, "clock_id": "harp_s001", "start_tick": 200, "stop_tick": 299},
]


def _commit(root, registry, minimal, *, choice="left"):
    writer = PacketWriter(registry, packet_id=root.name, extensions=[EXTENSION])
    for resource_id, records in minimal.items():
        writer.add(resource_id, records)
    writer.add("core.trials", TRIALS)
    writer.add(
        "task.trials", [{"session_id": t["session_id"], "trial_id": t["trial_id"], "choice": choice} for t in TRIALS]
    )
    return writer.commit(root)


def test_an_extension_table_is_written_and_validates(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    report = _commit(root, registry, minimal)
    assert report.passed, [f.check for f in report.findings]
    assert (root / "tables" / "task" / "trials.parquet").is_file()


def test_the_packet_declares_the_extension_and_carries_its_registry(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    manifest = json.loads((root / "nwb.packet.json").read_text())
    assert manifest["extensions"] == {"task": {"version": "0.1.0", "registry": "extensions/task.json"}}
    assert (root / "extensions" / "task.json").is_file()
    assert open_packet(root).extensions()["task"]["extension_id"] == "task"


def test_the_entry_says_which_extension_owns_it(tmp_path, registry, minimal):
    """R17 §4: a reader knows what it holds without parsing the extension's registry."""
    root = tmp_path / "s001"
    _commit(root, registry, minimal)
    entry = next(
        r for r in json.loads((root / "nwb.packet.json").read_text())["resources"] if r["resource_id"] == "task.trials"
    )
    assert (entry["layer"], entry["extension_id"]) == ("extension", "task")


def test_the_extension_is_validated_and_reported_apart(tmp_path, registry, minimal):
    root = tmp_path / "s001"
    _commit(root, registry, minimal, choice="sideways")
    report = validate(open_packet(root))
    assert report.passed, "core conformance is unchanged by an extension's finding (R17 §4)"
    assert not report.extension_passed("task")
    assert "task.trials.choice.in_vocabulary" in {f.check for f in report.findings}


def test_a_core_table_cannot_be_redefined(registry):
    stray = {**EXTENSION, "tables": {"core.trials": EXTENSION["tables"]["task.trials"]}}
    with pytest.raises(ValueError, match="not namespaced"):
        PacketWriter(registry, packet_id="s001", extensions=[stray])


def test_an_unnamespaced_table_is_refused(registry):
    stray = {**EXTENSION, "tables": {"elsewhere.trials": EXTENSION["tables"]["task.trials"]}}
    with pytest.raises(ValueError, match="not namespaced"):
        PacketWriter(registry, packet_id="s001", extensions=[stray])

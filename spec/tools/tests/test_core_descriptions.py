"""What the core registry's descriptions say, where a part gives the reading they must not contradict."""

import json

from checkers.artifacts import ARTIFACTS

CORE = json.loads((ARTIFACTS / "logical_schemas.json").read_text())
TABLES = (ARTIFACTS.parent / "informative" / "tables.md").read_text()
UNNAMED_RUN = "Null says only that the packet names no producing run."


def test_a_null_processing_run_says_only_that_the_packet_names_none():
    # Part 01 §§3.12 and 3.17: a null names no recorded run, and is not a statement of acquisition.
    nullable = {
        name
        for name, resource in CORE["resources"].items()
        for column in resource.get("table", {}).get("columns", [])
        if column["name"] == "processing_run_id" and column["presence"] == "nullable"
    }
    assert nullable == {
        "core.array_assets",
        "analysis.array_assets",
        "core.event_streams",
        "core.sorting_runs",
        "core.curation_versions",
        "core.electrode_coordinates",
        "core.unit_coordinates",
    }
    for name in nullable:
        (column,) = [c for c in CORE["resources"][name]["table"]["columns"] if c["name"] == "processing_run_id"]
        assert column["description"].endswith(", where the packet records it. " + UNNAMED_RUN), name
    assert "acquired rather than computed" not in json.dumps(CORE)
    assert "acquired rather than computed" not in TABLES

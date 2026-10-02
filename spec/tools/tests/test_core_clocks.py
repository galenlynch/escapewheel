"""How the core registry declares a clock's alignment, which Part 01 §3.9 gives two typed models."""

import json

from checkers.artifacts import ARTIFACTS

CORE = json.loads((ARTIFACTS / "logical_schemas.json").read_text())


def test_a_clock_states_its_transform_in_typed_columns_alone():
    columns = CORE["resources"]["core.clocks"]["table"]["columns"]
    names = [c["name"] for c in columns]
    assert len(names) == 14
    assert "transform_to_parent" not in names
    after = names.index("transform_slope")
    assert names[after : after + 3] == ["transform_slope", "transform_offset", "withheld_first_anchor"]
    assert [c["name"] for c in columns if c["type"] == "json_string"] == ["metadata"]

"""The build reports a generated file that no longer reproduces its source."""

import build
import render

DESCRIPTOR = {
    "kind_interfaces": {"table": "columnar", "opaque": None},
    "interfaces": {"columnar": {"overriding_orders": {"core.a": ["x", "y"]}}},
}
PART = (
    "before\n"
    "<!-- BEGIN GENERATED PHYSICAL PROFILE -->\nhand edit\n<!-- END GENERATED PHYSICAL PROFILE -->\n"
    "between\n"
    "<!-- BEGIN GENERATED OVERRIDING ORDERS -->\n<!-- END GENERATED OVERRIDING ORDERS -->\n"
    "after\n"
)


def test_part_03_regions_are_refilled_from_the_descriptor():
    filled = build.fill_physical_profile(PART, DESCRIPTOR)

    assert "hand edit" not in filled
    assert "| `table` | `columnar` |\n| `opaque` | none |" in filled
    assert "| `core.a` | `x, y` |" in filled
    assert filled.startswith("before\n") and "\nbetween\n" in filled and filled.endswith("after\n")
    assert build.fill_physical_profile(filled, DESCRIPTOR) == filled


def test_the_committed_tree_has_no_stale_output():
    assert build.stale() == []


def test_an_edited_part_03_region_is_stale(tmp_path, monkeypatch):
    edited = tmp_path / build.PART_03.name
    edited.write_text(build.PART_03.read_text().replace("| logical kind | generic interface |", "| kind | interface |"))
    monkeypatch.setattr(build, "PART_03", edited)

    assert build.stale() == [edited]


def test_an_edited_listing_is_stale(tmp_path, monkeypatch):
    edited = tmp_path / render.OUT.name
    edited.write_text(render.OUT.read_text() + "\nan added line\n")
    monkeypatch.setattr(render, "OUT", edited)

    assert build.stale() == [edited]


def test_a_missing_listing_is_stale(tmp_path, monkeypatch):
    missing = tmp_path / render.OUT.name
    monkeypatch.setattr(render, "OUT", missing)

    assert build.stale() == [missing]

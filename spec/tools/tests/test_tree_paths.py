"""A part gives only paths within the tree, and every artifact in `artifacts/` is incorporated."""

import framework

PART = framework.PARTS["02"]


def _parts(extra: str = "") -> dict[str, str]:
    documents = framework._documents()
    return {**documents, PART: documents[PART] + extra}


def test_the_tree_gives_only_paths_within_it():
    assert framework.path_defects(framework._documents()) == []


def test_a_path_leaving_the_tree_fails():
    found = framework.path_defects(_parts("\nSee `../conformance/probe.py`.\n"))
    assert found == [f"{PART} gives ../conformance/probe.py, outside the tree"]


def test_a_path_under_an_enclosing_repository_entry_fails():
    found = framework.path_defects(_parts("\nSee `registry/logical_schemas.json`.\n"), outside=["registry"])
    assert found == [f"{PART} gives registry/logical_schemas.json, outside the tree"]


def test_a_path_under_a_tree_entry_must_name_a_file():
    found = framework.path_defects(_parts("\nSee `artifacts/absent.schema.json`.\n"))
    assert found == [f"{PART} gives artifacts/absent.schema.json, which names nothing in the tree"]


def test_a_path_within_a_packet_is_not_judged():
    assert framework.path_defects(_parts("\nRead `schemas/semantic_version.txt`.\n")) == []


def test_a_link_to_anything_but_a_part_fails():
    found = framework.path_defects(_parts("\nSee [the guide](../source/README.md).\n"))
    assert f"{PART} links to ../source/README.md, which is not a numbered part" in found


def test_an_artifact_no_part_incorporates_fails():
    artifacts = {**framework._artifacts(), "artifacts/stray.json": "{}"}
    found = framework.path_defects(framework._documents(), artifacts)
    assert found == ["artifacts/stray.json is incorporated by no numbered part"]


def test_an_artifact_giving_a_path_outside_the_tree_fails():
    artifacts = {**framework._artifacts(), "artifacts/stray.json": '{"description": "see ../tools/build.py"}'}
    found = framework.path_defects(_parts("\n`artifacts/stray.json`\n"), artifacts)
    assert "artifacts/stray.json gives ../tools/build.py, outside the tree" in found

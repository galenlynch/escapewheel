"""The helpers the specification's tools share."""

import specdoc


def _parts(directory, *names):
    for name in names:
        (directory / name).write_text("")
    return directory


def test_parts_are_listed_in_number_order_and_nothing_else_is(tmp_path):
    _parts(tmp_path, "10_rules.md", "02_schema.md", "README.md", "2_short.md", "03_profile.txt")

    assert [path.name for path in specdoc.part_paths(tmp_path)] == ["02_schema.md", "10_rules.md"]


def test_a_part_is_found_by_its_number(tmp_path):
    _parts(tmp_path, "02_schema.md", "10_rules.md")

    assert specdoc.part_path(tmp_path, "10") == tmp_path / "10_rules.md"
    assert specdoc.part_path(tmp_path, "11") is None


def test_the_first_by_name_is_the_part_where_two_share_a_number(tmp_path):
    _parts(tmp_path, "02_schema.md", "02_another.md")

    assert specdoc.part_path(tmp_path, "02") == tmp_path / "02_another.md"

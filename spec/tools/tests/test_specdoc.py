"""The helpers the specification's tools share."""

import pytest

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


def test_lines_inside_a_fence_are_skipped_and_the_fence_is_marked():
    text = "one\n```text\n## 3. Fenced\n```\nfive\n"

    assert list(specdoc.outside_fences(text)) == [(1, "one"), (2, None), (4, None), (5, "five")]


def test_an_unclosed_fence_hides_the_rest():
    assert list(specdoc.outside_fences("one\n```\ntwo\nthree")) == [(1, "one"), (2, None)]


@pytest.mark.parametrize(
    ("line", "number"),
    [("# 1 Scope", "1"), ("## 3. Concepts", "3"), ("#### 10.2.4 Deep", "10.2.4"), ("### 3.1", "3.1")],
)
def test_a_numbered_heading_gives_its_number(line, number):
    assert specdoc.HEADING.match(line).group(1) == number


@pytest.mark.parametrize("line", ["##### 3.1 Too deep", "## Concepts", "##3. Unspaced", "## 3.1x Suffixed"])
def test_other_lines_are_not_numbered_headings(line):
    assert specdoc.HEADING.match(line) is None


def test_a_titled_heading_needs_a_title_and_respects_its_shallowest_depth():
    assert specdoc.titled_heading(1).fullmatch("# 1 Scope").groups() == ("1", "Scope")
    assert specdoc.titled_heading(2).fullmatch("### 3.1. Dataset  ").groups() == ("3.1", "Dataset  ")
    assert specdoc.titled_heading(2).fullmatch("# 1 Scope") is None
    assert specdoc.titled_heading(1).fullmatch("### 3.1") is None


def test_headings_are_found_across_a_document():
    text = "# 1 Scope\n\nprose\n\n## 1.1 Terms\n"

    assert specdoc.HEADING.findall(text) == ["1", "1.1"]
    assert specdoc.titled_heading(1).findall(text) == [("1", "Scope"), ("1.1", "Terms")]


def test_an_anchor_line_gives_its_identifier_and_kind():
    assert specdoc.ANCHOR.fullmatch('<a id="ew-scope" data-spec-anchor="canonical"></a>').groups() == (
        "ew-scope",
        "canonical",
    )
    assert specdoc.ANCHOR.fullmatch('<a id="ew-old-scope" data-spec-anchor="alias"></a>').group(2) == "alias"
    assert specdoc.ANCHOR.fullmatch('<a id="EW-scope" data-spec-anchor="canonical"></a>') is None
    assert specdoc.ANCHOR.fullmatch('<a id="ew-scope"></a>') is None

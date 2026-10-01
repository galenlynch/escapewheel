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


def test_a_part_citation_reads_both_spellings_of_the_part():
    pattern = specdoc.part_citation(" ")

    assert pattern.search("see Part 03 §5.4.").groups() == (None, "03", "5.4")
    assert pattern.search("see `03` §5").groups() == ("03", None, "5")
    assert pattern.search("see Part 3 §5.4") is None


def test_the_gap_decides_which_separations_a_part_citation_admits():
    assert specdoc.part_citation(" ").search("Part 03  §5.4") is None
    assert specdoc.part_citation(r"\s+").search("Part 03  §5.4").group(3) == "5.4"
    assert specdoc.part_citation(r"\s+").search("Part 03\t§5.4").group(3) == "5.4"


def test_a_revision_citation_gives_the_revision_and_the_section():
    # Assembled, so that no tool reading this file for citations finds one to resolve.
    first, second = 92, 7
    text = f"R{first} §2.2 and R{second} §3, not PR{first} §1."

    assert specdoc.REVISION_CITATION.findall(text) == [("92", "2.2"), ("7", "3")]


def test_a_section_citation_drops_a_sentence_ending_dot():
    assert specdoc.SECTION_CITATION.findall("§3.1, §4. Then §10.2.4") == ["3.1", "4", "10.2.4"]


RECORD = """# A record

| Field | Value |
|---|---|
| **Status** | Draft |
| **Decision clauses** |  §3.1, §3.2  |
| **Empty** | |
| **Status** | Accepted |

Prose with | **Not a row** | in it.
"""


def test_the_metadata_table_is_read_with_the_last_of_a_repeated_name():
    assert specdoc.metadata(RECORD) == {"Status": "Accepted", "Decision clauses": "§3.1, §3.2", "Empty": ""}


def test_one_metadata_value_is_the_first_row_of_its_name():
    assert specdoc.metadata_value(RECORD, "Status") == "Draft"
    assert specdoc.metadata_value(RECORD, "Decision clauses") == "§3.1, §3.2"


def test_an_empty_metadata_cell_is_told_from_an_absent_row():
    assert specdoc.metadata_value(RECORD, "Empty") == ""
    assert specdoc.metadata_value(RECORD, "Baseline") is None


def test_a_metadata_name_is_read_literally():
    assert specdoc.metadata_value("| **A.B** | dotted |\n", "A.B") == "dotted"
    assert specdoc.metadata_value("| **AxB** | other |\n", "A.B") is None


def test_metadata_past_the_head_of_the_document_is_not_read():
    late = "x" * specdoc.METADATA_HEAD + "\n| **Status** | Late |\n"

    assert specdoc.metadata(late) == {}
    assert specdoc.metadata_value(late, "Status") is None


DOCUMENT = {"resources": {"core.units": {"table": "units", "key": ["unit_id"]}}, "a/b": {"m~n": 1}, "": 0}


@pytest.mark.parametrize(
    ("pointer", "addressed"),
    [
        ("/resources/core.units/table", "units"),
        ("/resources/core.units/key/0", "unit_id"),
        ("/a~1b/m~0n", 1),
        ("/", 0),
    ],
)
def test_a_pointer_resolves_members_indices_and_escapes(pointer, addressed):
    assert specdoc.resolve_pointer(DOCUMENT, pointer) == addressed


@pytest.mark.parametrize("pointer", ["", "resources", None, 3])
def test_a_pointer_is_a_string_beginning_with_a_slash(pointer):
    with pytest.raises(ValueError, match="RFC 6901"):
        specdoc.resolve_pointer(DOCUMENT, pointer)


def test_a_missing_member_raises_with_its_token():
    with pytest.raises(KeyError) as raised:
        specdoc.resolve_pointer(DOCUMENT, "/resources/absent")

    assert raised.value.args == ("absent",)


@pytest.mark.parametrize("token", ["1", "first", "-1"])
def test_a_token_that_is_no_index_of_an_array_raises_with_it(token):
    with pytest.raises(IndexError) as raised:
        specdoc.resolve_pointer(DOCUMENT, f"/resources/core.units/key/{token}")

    assert raised.value.args == (token,)


def test_a_token_after_a_scalar_raises_with_it():
    with pytest.raises(specdoc.ScalarError, match="'deeper' follows a scalar") as raised:
        specdoc.resolve_pointer(DOCUMENT, "/resources/core.units/table/deeper")

    assert raised.value.token == "deeper"
    assert isinstance(raised.value, TypeError)

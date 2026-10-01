"""The helpers the specification's tools share."""

import subprocess

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


@pytest.fixture
def repository(tmp_path):
    """A repository with a committed-to-be file, a new one, an ignored one and a spaced name."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name in ("staged.md", "new.py", "ignored.log", "two words.md", "nested/deep.md"):
        (tmp_path / name).parent.mkdir(exist_ok=True)
        (tmp_path / name).write_text("")
    (tmp_path / ".gitignore").write_text("*.log\n")
    subprocess.run(["git", "add", "staged.md"], cwd=tmp_path, check=True)
    return tmp_path


def test_tracked_files_are_the_staged_and_the_new_but_not_the_ignored(repository):
    assert sorted(specdoc.tracked_files(repository)) == [
        ".gitignore",
        "nested/deep.md",
        "new.py",
        "staged.md",
        "two words.md",
    ]


def test_pathspecs_narrow_the_tracked_files(repository):
    assert sorted(specdoc.tracked_files(repository, "*.py")) == ["new.py"]
    assert sorted(specdoc.tracked_files(repository, "nested", "*.py")) == ["nested/deep.md", "new.py"]


def test_a_listing_split_on_whitespace_breaks_a_spaced_name(repository):
    assert sorted(specdoc.tracked_files(repository, "*.md", whole_names=False)) == [
        "nested/deep.md",
        "staged.md",
        "two",
        "words.md",
    ]


def test_a_registry_gives_its_tables_and_not_its_other_resources():
    registry = {
        "resources": {
            "core.units": {"kind": "table", "table": {"columns": ["unit_id"]}},
            "core.spike_times": {"kind": "array"},
            "core.sessions": {"kind": "table", "table": {"columns": []}},
        }
    }

    assert specdoc.registry_tables(registry) == {
        "core.units": {"columns": ["unit_id"]},
        "core.sessions": {"columns": []},
    }
    assert list(specdoc.registry_tables(registry)) == ["core.units", "core.sessions"]


@pytest.mark.parametrize("resource", [{}, {"kind": "table"}])
def test_a_resource_missing_what_a_valid_registry_gives_it_raises(resource):
    with pytest.raises(KeyError):
        specdoc.registry_tables({"resources": {"core.units": resource}})


MARKED = "above\n<!-- BEGIN GENERATED ORDERS -->\nstale\nrows\n<!-- END GENERATED ORDERS -->\nbelow\n"


def test_a_generated_region_takes_its_lines_between_markers_that_stay():
    assert specdoc.replace_generated_region(MARKED, "ORDERS", ["one", "two"]) == (
        "above\n<!-- BEGIN GENERATED ORDERS -->\none\ntwo\n<!-- END GENERATED ORDERS -->\nbelow\n"
    )


def test_a_generated_region_left_without_lines_keeps_only_its_markers():
    assert specdoc.replace_generated_region(MARKED, "ORDERS", []) == (
        "above\n<!-- BEGIN GENERATED ORDERS -->\n<!-- END GENERATED ORDERS -->\nbelow\n"
    )


@pytest.mark.parametrize("text", ["no markers", "<!-- BEGIN GENERATED ORDERS -->\nopened and never closed\n"])
def test_a_generated_region_missing_a_marker_raises(text):
    with pytest.raises(ValueError):
        specdoc.replace_generated_region(text, "ORDERS", ["one"])


NAMED = (
    "prose\n<!-- BEGIN facts: tables -->\nold\n<!-- END facts: tables -->\n"
    "between\n<!-- BEGIN facts: rules -->\n<!-- END facts: rules -->\n"
    "<!-- BEGIN generated: other -->\nnot a fact\n<!-- END generated: other -->\n"
)


def test_named_regions_of_one_kind_are_found_by_name():
    assert specdoc.region_names(specdoc.named_regions("facts"), NAMED) == {"tables", "rules"}
    assert specdoc.region_names(specdoc.named_regions("generated"), NAMED) == {"other"}


def test_a_region_closed_under_another_name_is_no_region():
    text = "<!-- BEGIN facts: tables -->\nold\n<!-- END facts: rules -->\n"

    assert specdoc.region_names(specdoc.named_regions("facts"), text) == set()


def test_each_named_region_is_filled_from_its_name_and_the_rest_is_kept():
    filled = specdoc.fill_regions(specdoc.named_regions("facts"), NAMED, lambda name: f"{name} now\n")

    assert filled == (
        "prose\n<!-- BEGIN facts: tables -->\ntables now\n<!-- END facts: tables -->\n"
        "between\n<!-- BEGIN facts: rules -->\nrules now\n<!-- END facts: rules -->\n"
        "<!-- BEGIN generated: other -->\nnot a fact\n<!-- END generated: other -->\n"
    )


def test_what_fills_a_region_may_refuse_a_name():
    with pytest.raises(KeyError):
        specdoc.fill_regions(specdoc.named_regions("facts"), NAMED, {"tables": "only\n"}.__getitem__)


def test_a_passing_check_prints_its_label_and_is_not_kept(capsys):
    report = specdoc.Reporter(shown=4)

    report("every part is numbered", [])

    assert capsys.readouterr().out == "ok    every part is numbered\n"
    assert report.failed == []


def test_a_failing_check_prints_its_count_and_no_more_items_than_are_shown(capsys):
    report = specdoc.Reporter(shown=2)

    report("every part is numbered", (name for name in ("a.md", "b.md", "c.md")))

    assert capsys.readouterr().out == ("FAIL  every part is numbered  (3)\n          a.md\n          b.md\n")
    assert report.failed == ["every part is numbered"]


def test_a_failing_check_formats_its_items_as_asked(capsys):
    report = specdoc.Reporter(shown=4)

    report("pairs agree", [("a", 1)], lambda pair: f"{pair[0]} is {pair[1]}")

    assert capsys.readouterr().out == "FAIL  pairs agree  (1)\n          a is 1\n"


def test_failed_labels_accumulate_in_the_order_reported():
    report = specdoc.Reporter(shown=0)
    for label, bad in (("first", [1]), ("second", []), ("third", [1])):
        report(label, bad)

    assert report.failed == ["first", "third"]

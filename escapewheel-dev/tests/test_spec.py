import re

import pytest

import escapewheel_dev as ew
from escapewheel_dev._root import spec_tool
from escapewheel_dev.spec import Citation, _citations


def test_sections_are_the_headings_the_record_tool_reads():
    by_part: dict[str, dict[str, str]] = {}
    for section in ew.sections():
        by_part.setdefault(section.part, {})[section.number] = section.title
    assert by_part == spec_tool("headings").current()


def test_lookup_by_part_number_and_anchor():
    index, _ = spec_tool("headings").anchors()
    anchor, entry = next(iter(index.items()))
    found = ew.section_by_anchor(anchor)
    assert (found.part, found.number) == (entry["part"], entry["section"])
    assert ew.section(int(entry["part"]), entry["section"]) == found
    with pytest.raises(KeyError):
        ew.section(2, "999")


def test_requirements_carry_their_keyword():
    must = ew.requirements(2, keyword="MUST")
    assert must
    assert all(requirement.section.part == "02" and "MUST" in requirement.keywords for requirement in must)
    # `MUST NOT` is one keyword, so a sentence holding no bare `MUST` is not a `MUST` sentence.
    only_not = [
        requirement
        for requirement in ew.requirements(2, keyword="MUST NOT")
        if not re.search(r"\bMUST\b(?! NOT)", requirement.sentence)
    ]
    assert only_not
    assert all(requirement.sentence not in {m.sentence for m in must} for requirement in only_not)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("see Part 03 §5.4.", [("03", "5.4")]),
        ("see `03` §5.4.", [("03", "5.4")]),
        ("per §6.", [("02", "6")]),
        ("Part 02 §§6, 10.1 and §11", [("02", "6"), ("02", "10.1"), ("02", "11")]),
        ("§5 and 6 rows", [("02", "5")]),
        ("R12 §4 and RFC 3339 §5.6", []),
    ],
)
def test_citations(text, expected):
    assert _citations("02", text) == tuple(Citation(part, section) for part, section in expected)


def test_cited_by_finds_a_citing_section():
    cited = next(citation for section in ew.sections() for citation in section.citations)
    assert any(cited in section.citations for section in ew.cited_by(cited.part, cited.section))

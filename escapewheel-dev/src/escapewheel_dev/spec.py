"""The current specification parts: sections, anchors, BCP 14 requirements and citations between parts."""

import re
from dataclasses import dataclass, field
from functools import cache

from ._root import ROOT, spec_tool

PARTS = ROOT / "spec" / "parts"

_specdoc = spec_tool("specdoc")
_HEADING: re.Pattern[str] = _specdoc.titled_heading(1)
_SECTION: str = _specdoc.SECTION
_ANCHOR: re.Pattern[str] = _specdoc.ANCHOR

#: BCP 14 keywords, longest first so `MUST NOT` is not read as `MUST`.
KEYWORDS = (
    "NOT RECOMMENDED",
    "MUST NOT",
    "SHALL NOT",
    "SHOULD NOT",
    "RECOMMENDED",
    "REQUIRED",
    "OPTIONAL",
    "SHOULD",
    "SHALL",
    "MUST",
    "MAY",
)
_KEYWORD = re.compile(r"\b(" + "|".join(KEYWORDS) + r")\b")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*(\[])")
# A citation: optionally a revision (`R12 `), a part (`Part 03 ` or `` `03` ``) or another document
# (`RFC 3339 `) before the section sign; `§§` admits a list such as `§§6, 10.1`.
_CITATION = re.compile(
    r"(?:\bR(?P<revision>\d+)\s+|(?:`(?P<quoted>\d\d)`|Part (?P<part>\d\d))\s+"
    r"|(?P<other>\b[A-Za-z][\w-]*\s+\d[\w.-]*\s+))?"
    rf"§(?P<list>§)?\s?(?P<sections>{_SECTION}(?(list)(?:(?:, | and | or |–)(?:§\s?)?{_SECTION})*))"
)


@dataclass(frozen=True)
class Citation:
    """A reference to section `section` of part `part`."""

    part: str
    section: str


@dataclass(frozen=True)
class Section:
    """One numbered section of a part, its text running to the next numbered heading at any depth."""

    part: str
    number: str
    title: str
    #: Position of the heading's line in the part's file, the first line being 1.
    line: int
    text: str = field(repr=False)
    anchor: str | None = None
    aliases: tuple[str, ...] = ()

    @property
    def citations(self) -> tuple[Citation, ...]:
        """Sections of any part this one cites, a bare `§x` read as this part's own."""
        return _citations(self.part, self.text)


@dataclass(frozen=True)
class Requirement:
    """One sentence carrying BCP 14 keywords."""

    section: Section
    keywords: tuple[str, ...]
    sentence: str


def _citations(part: str, text: str) -> tuple[Citation, ...]:
    found: list[Citation] = []
    for match in _CITATION.finditer(text):
        if match["revision"] or match["other"]:
            continue
        cited_part = match["part"] or match["quoted"] or part
        for number in re.findall(_SECTION, match["sections"]):
            citation = Citation(cited_part, number)
            if citation not in found:
                found.append(citation)
    return tuple(found)


def _part_sections(part: str, text: str, anchors: dict[tuple[str, str], tuple[str, list[str]]]) -> list[Section]:
    sections: list[Section] = []
    heading: tuple[str, str, int] | None = None
    body: list[str] = []
    fenced = False

    def close() -> None:
        if heading is not None:
            number, title, line = heading
            anchor, aliases = anchors.get((part, number), (None, []))
            text = "\n".join(body).strip("\n")
            sections.append(Section(part, number, title, line, text, anchor, tuple(aliases)))

    for position, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
        match = None if fenced else _HEADING.fullmatch(line)
        if match:
            close()
            heading, body = (match[1], match[2].strip(), position), []
        elif not _ANCHOR.fullmatch(line):
            body.append(line)
    close()
    return sections


@cache
def sections() -> tuple[Section, ...]:
    """Return every numbered section of every part, in document order."""
    index, _ = spec_tool("headings").anchors()
    anchors = {(entry["part"], entry["section"]): (anchor, entry["aliases"]) for anchor, entry in index.items()}
    return tuple(
        section
        for path in _specdoc.part_paths(PARTS)
        for section in _part_sections(path.name[:2], path.read_text(), anchors)
    )


def section(part: str | int, number: str) -> Section:
    """Return one section; `part` may be ``"02"`` or ``2``."""
    key = f"{int(part):02d}"
    for candidate in sections():
        if candidate.part == key and candidate.number == number:
            return candidate
    raise KeyError(f"Part {key} has no §{number}")


def section_by_anchor(anchor: str) -> Section:
    """Return the section a canonical or alias anchor names."""
    for candidate in sections():
        if anchor == candidate.anchor or anchor in candidate.aliases:
            return candidate
    raise KeyError(f"no section carries anchor #{anchor}")


def requirements(part: str | int | None = None, *, keyword: str | None = None) -> list[Requirement]:
    """Return BCP 14 sentences outside code blocks, optionally one part's or those carrying `keyword`.

    Sentences are split at a full stop followed by a capital, so one holding an abbreviation such as
    `e.g. X` is split there.
    """
    key = None if part is None else f"{int(part):02d}"
    found = []
    for candidate in sections():
        if key is not None and candidate.part != key:
            continue
        for paragraph in _paragraphs(candidate.text):
            for sentence in _SENTENCE_END.split(paragraph):
                keywords = tuple(dict.fromkeys(_KEYWORD.findall(sentence)))
                if keywords and (keyword is None or keyword in keywords):
                    found.append(Requirement(candidate, keywords, sentence))
    return found


def _paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        stripped = line.strip()
        starts_item = bool(re.match(r"([-*+]|\d+\.|\|)\s", stripped))
        if fenced or not stripped or starts_item:
            if current:
                paragraphs.append(" ".join(current))
            current = [] if fenced or not stripped else [stripped]
        else:
            current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def cited_by(part: str | int, number: str) -> list[Section]:
    """Return the sections, in any part, citing exactly `number` of `part`."""
    target = Citation(f"{int(part):02d}", number)
    return [candidate for candidate in sections() if target in candidate.citations]


__all__ = [
    "KEYWORDS",
    "PARTS",
    "Citation",
    "Requirement",
    "Section",
    "cited_by",
    "requirements",
    "section",
    "section_by_anchor",
    "sections",
]

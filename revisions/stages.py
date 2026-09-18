"""Check the structure of every open proposal and revision draft.

The semantic appraisal is still a review, but several prerequisites are mechanical: an open
document names its baseline, uses the right template sections, contains no template instructions,
and a proposal does not prescribe behavior with BCP 14 keywords. Drafts also enumerate the exact
Decision clauses that the acceptance ledger will require someone to place.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "revisions"

ROW = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|$", re.MULTILINE)
HEADING = re.compile(r"^## (\d+)\.\s+(.+?)\s*$", re.MULTILINE)
NUMBERED = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)\.?\s+", re.MULTILINE)
BCP14 = re.compile(
    r"\b(?:MUST|MUST NOT|SHOULD|SHOULD NOT|MAY|REQUIRED|SHALL|OPTIONAL)\b"
)
SHA = re.compile(r"[0-9a-f]{40}")
NON_STAGE_DOCUMENTS = {"README.md", "ROADMAP.md"}

PROPOSAL_HEADINGS = {
    "1": "Problem",
    "2": "Evidence",
    "3": "Desired outcome and constraints",
    "4": "Options and tradeoffs",
    "5": "Impact sketch",
    "7": "Promotion criteria",
}
DRAFT_HEADINGS = {
    "1": "Scope",
    "2": "Background",
    "3": "Decision",
    "5": "Consequence",
    "6": "Conformance and implementation evidence",
}


def fields(text: str) -> dict[str, str]:
    """Return the two-column metadata table at the head of a stage document."""
    return {name: value for name, value in ROW.findall(text[:2000])}


def baseline(path: Path, value: str | None) -> list[str]:
    """Return defects in a document's full baseline commit hash."""
    if value is None:
        return ["declares no `Based on` commit"]
    commit = value.strip("`")
    if not SHA.fullmatch(commit):
        return [f"`Based on` is not a full commit hash: {value!r}"]
    exists = (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    return (
        [] if exists else [f"`Based on` names no commit in this repository: {commit}"]
    )


def common(path: Path, text: str, expected_status: str) -> list[str]:
    """Return defects shared by proposals and drafts."""
    meta = fields(text)
    errors = baseline(path, meta.get("Based on"))
    if meta.get("Status") != f"**{expected_status}**":
        errors.append(
            f"status is {meta.get('Status')!r}, expected `**{expected_status}**`"
        )
    if "<!--" in text:
        errors.append("contains template instructions or another HTML comment")
    if path.name.startswith("R"):
        errors.append("an open proposal or draft carries an accepted-revision number")
    return errors


def headings(path: Path, text: str, required: dict[str, str]) -> list[str]:
    """Return missing or renamed required top-level sections."""
    found = dict(HEADING.findall(text))
    return [
        f"§{number} is {found.get(number)!r}, expected {title!r}"
        for number, title in required.items()
        if found.get(number) != title
    ]


def proposal(path: Path) -> list[str]:
    """Return structural defects in one proposal."""
    text = path.read_text()
    errors = common(path, text, "Proposal") + headings(path, text, PROPOSAL_HEADINGS)
    meta = fields(text)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta.get("Opened", "")):
        errors.append(f"`Opened` is not an ISO date: {meta.get('Opened')!r}")
    if not meta.get("Affects"):
        errors.append("declares no affected concepts or specification locations")
    if match := BCP14.search(text):
        line = text[: match.start()].count("\n") + 1
        errors.append(f"uses BCP 14 keyword {match.group()!r} on line {line}")
    return errors


def draft(path: Path) -> list[str]:
    """Return structural defects in one revision draft."""
    text = path.read_text()
    errors = common(path, text, "Draft") + headings(path, text, DRAFT_HEADINGS)
    meta = fields(text)
    for name in ("Amends", "Depends on", "Profile", "Decision clauses"):
        if not meta.get(name):
            errors.append(f"declares no `{name}` value")
    declared = re.findall(r"§(\d+(?:\.\d+)*)", meta.get("Decision clauses", ""))
    if not declared:
        errors.append("`Decision clauses` enumerates no section")
    known = set(NUMBERED.findall(text))
    expected = {section for section in known if section.startswith("3.")} or (
        {"3"} if "3" in known else set()
    )
    if len(declared) != len(set(declared)):
        errors.append("`Decision clauses` repeats a section")
    if set(declared) != expected:
        errors.append(
            f"`Decision clauses` enumerates {sorted(set(declared))}, expected {sorted(expected)}"
        )
    for section in declared:
        if section not in known:
            errors.append(f"`Decision clauses` names absent §{section}")
        if not (section == "3" or section.startswith("3.")):
            errors.append(f"`Decision clauses` names §{section}, outside §3 Decision")
    return errors


def main() -> int:
    """Check every open stage document and report all defects."""
    proposals = sorted(
        p
        for p in (HERE / "proposals").glob("*.md")
        if p.name not in NON_STAGE_DOCUMENTS
    )
    drafts = sorted(p for p in (HERE / "drafts").glob("*.md") if p.name != "README.md")
    failures = 0
    for path, check in [(p, proposal) for p in proposals] + [
        (p, draft) for p in drafts
    ]:
        for error in check(path):
            print(f"  {path.relative_to(ROOT)}: {error}")
            failures += 1
    if failures:
        print(f"{failures} open-stage defect(s)")
        return 1
    print(
        f"{len(proposals)} proposal(s) and {len(drafts)} draft(s) are structurally complete"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

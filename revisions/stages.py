"""Check the structure of every open change document and every prospective accepted record.

The appraisal of a change is a review, but what a document carries at each status is mechanical
(`revisions/CONTRIBUTING.md#ew-pre-acceptance-gates`): an Open document names its baseline, uses
the Open sections and no BCP 14 keyword; a Ready one has answered every question and enumerates the
exact Decision clauses that the acceptance ledger will require someone to place. Neither declares a
decision domain, carries a revision number, or keeps a template instruction, and nothing is left
under the retired `proposals/` and `drafts/` directories.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

try:
    from revisions.process_rules import canonical_anchors
except ModuleNotFoundError:  # Direct execution from revisions/.
    from process_rules import canonical_anchors

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "revisions"
CHANGES = HERE / "changes"
#: Directories a change document no longer lives in; any file left there fails.
RETIRED = (HERE / "proposals", HERE / "drafts")
sys.path.insert(0, str(ROOT / "spec" / "tools"))

import specdoc

HEADING = re.compile(r"^## (\d+)\.\s+(.+?)\s*$", re.MULTILINE)
NUMBERED = re.compile(r"^#{2,4} (\d+(?:\.\d+)*)\.?\s+", re.MULTILINE)
BCP14 = re.compile(r"\b(?:MUST|MUST NOT|SHOULD|SHOULD NOT|MAY|REQUIRED|SHALL|OPTIONAL)\b")
SHA = re.compile(r"[0-9a-f]{40}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
ACCEPTED_STATUS = re.compile(r"\*\*Accepted\*\* \d{4}-\d{2}-\d{2}")
PROCESS_AMENDS = re.compile(r"([^#;]+\.md)#([a-z0-9]+(?:-[a-z0-9]+)*)")
#: A question is one numbered item under `Questions`; its continuation lines are indented.
QUESTION = re.compile(r"^(\d+)\.\s.*?(?=^\d+\.\s|^\S|\Z)", re.MULTILINE | re.DOTALL)
ANSWERED = "**Answered"
NON_STAGE_DOCUMENTS = {"README.md"}
#: Accepted records from R120 declare their lifecycle metadata; from this one, a domain is optional.
METADATA_FROM = 120
DOMAIN_OPTIONAL_FROM = 167

OPEN_HEADINGS = {
    "1": "Problem",
    "2": "Evidence",
    "3": "Preferred direction",
    "4": "Questions",
    "5": "Consequence",
}
READY_HEADINGS = {
    "1": "Problem",
    "2": "Evidence",
    "3": "Decision",
    "4": "Questions",
    "5": "Consequence",
    "6": "Conformance and implementation evidence",
}
READY_FIELDS = ("Change form", "Amends", "Depends on", "Profile", "Decision clauses")


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
    return [] if exists else [f"`Based on` names no commit in this repository: {commit}"]


def lifecycle_metadata(path: Path, text: str, *, domain_required: bool = True) -> list[str]:
    """Validate an accepted record's decision-domain, change-form, and process-target metadata."""
    meta = specdoc.metadata(text)
    domain = meta.get("Decision domain")
    errors = []
    if domain is None and not domain_required:
        domain = "specification"
    if domain not in {"specification", "process"}:
        errors.append(f"`Decision domain` is {domain!r}, expected `specification` or `process`")
        return errors
    change = meta.get("Change form")
    if change not in {"ordinary", "structural"}:
        errors.append(f"`Change form` is {change!r}, expected `ordinary` or `structural`")
    if domain == "process":
        if change != "ordinary":
            errors.append("a process artifact must use `Change form: ordinary`")
        if meta.get("Profile") != "not applicable":
            errors.append("a process artifact must use `Profile: not applicable`")
        amendments = [value.strip(" `") for value in meta.get("Amends", "").split(";")]
        for amendment in filter(None, amendments):
            match = PROCESS_AMENDS.fullmatch(amendment)
            if match is None:
                errors.append(f"process `Amends` target is not an exact Markdown path#anchor: {amendment!r}")
                continue
            target = (ROOT / match.group(1)).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                errors.append(f"process `Amends` target escapes the repository: {amendment!r}")
                continue
            if not target.is_file() or match.group(2) not in canonical_anchors(target.read_text()):
                errors.append(f"process `Amends` target does not resolve: {amendment!r}")
    return errors


def headings(text: str, required: dict[str, str]) -> list[str]:
    """Return missing or renamed required top-level sections."""
    found = dict(HEADING.findall(text))
    return [
        f"§{number} is {found.get(number)!r}, expected {title!r}"
        for number, title in required.items()
        if found.get(number) != title
    ]


def section(text: str, number: str) -> str:
    """Return the body of top-level section `number`, up to the next top-level section."""
    match = re.search(rf"^## {number}\.\s.*$", text, re.MULTILINE)
    if match is None:
        return ""
    following = HEADING.search(text, match.end())
    return text[match.end() : following.start() if following else len(text)]


def unanswered(text: str) -> list[str]:
    """Return the positions of the questions under §4 that carry no recorded answer."""
    return [item.group(1) for item in QUESTION.finditer(section(text, "4")) if ANSWERED not in item.group(0)]


def clause_list(text: str) -> list[str]:
    """Return defects in `Decision clauses` against the subsections under §3."""
    meta = specdoc.metadata(text)
    declared = specdoc.SECTION_CITATION.findall(meta.get("Decision clauses", ""))
    known = set(NUMBERED.findall(text))
    expected = {s for s in known if s.startswith("3.")} or ({"3"} if "3" in known else set())
    errors = []
    if not declared:
        errors.append("`Decision clauses` enumerates no section")
    elif len(declared) != len(set(declared)):
        errors.append("`Decision clauses` repeats a section")
    if set(declared) != expected:
        errors.append(f"`Decision clauses` enumerates {sorted(set(declared))}, expected {sorted(expected)}")
    return errors


def change(path: Path) -> list[str]:
    """Return structural defects in one change document, read at the status it declares."""
    text = path.read_text()
    meta = specdoc.metadata(text)
    errors = baseline(path, meta.get("Based on"))
    status = meta.get("Status")
    if "<!--" in text:
        errors.append("contains template instructions or another HTML comment")
    if re.match(r"R\d+", path.name) or meta.get("Revision"):
        errors.append("a change document carries a revision number")
    if "Decision domain" in meta:
        errors.append("declares a `Decision domain`, which a change document does not carry")
    if not DATE.fullmatch(meta.get("Opened", "")):
        errors.append(f"`Opened` is not an ISO date: {meta.get('Opened')!r}")
    if status == "**Open**":
        errors += headings(text, OPEN_HEADINGS)
        if not meta.get("Affects"):
            errors.append("declares no affected concepts or specification locations")
        if match := BCP14.search(text):
            line = text[: match.start()].count("\n") + 1
            errors.append(f"an Open document uses BCP 14 keyword {match.group()!r} on line {line}")
    elif status == "**Ready**":
        errors += headings(text, READY_HEADINGS)
        for name in READY_FIELDS:
            if not meta.get(name):
                errors.append(f"declares no `{name}` value")
        if meta.get("Change form") not in {"ordinary", "structural"}:
            errors.append(f"`Change form` is {meta.get('Change form')!r}, expected `ordinary` or `structural`")
        errors += clause_list(text)
        errors += [f"question {number} has no recorded answer" for number in unanswered(text)]
    else:
        errors.append(f"status is {status!r}, expected `**Open**` or `**Ready**`")
    return errors


def accepted(path: Path) -> list[str]:
    """Validate metadata introduced prospectively at R120 without rewriting older history."""
    match = re.match(r"R(\d+)-", path.name)
    if match is None or int(match.group(1)) < METADATA_FROM:
        return []
    text = path.read_text()
    meta = specdoc.metadata(text)
    errors = baseline(path, meta.get("Based on"))
    if not ACCEPTED_STATUS.fullmatch(meta.get("Status", "")):
        errors.append(f"status is {meta.get('Status')!r}, expected accepted status and ISO date")
    errors += lifecycle_metadata(path, text, domain_required=int(match.group(1)) < DOMAIN_OPTIONAL_FROM)
    for name in ("Amends", "Depends on", "Profile", "Decision clauses"):
        if not meta.get(name):
            errors.append(f"declares no `{name}` value")
    errors += clause_list(text)
    if "<!--" in text:
        errors.append("contains template instructions or another HTML comment")
    return errors


def retired() -> list[Path]:
    """Every file left under a retired document directory."""
    return sorted(p for directory in RETIRED if directory.is_dir() for p in directory.rglob("*") if p.is_file())


def main() -> int:
    """Check every change document and prospective accepted record and report all defects."""
    changes = sorted(p for p in CHANGES.glob("[!.]*.md") if p.name not in NON_STAGE_DOCUMENTS)
    accepted_paths = sorted((HERE / "accepted").glob("R[0-9]*.md"))
    failures = 0
    for path in retired():
        print(f"  {path.relative_to(ROOT)}: a document under a retired directory belongs in `revisions/changes/`")
        failures += 1
    for path, check in [(p, change) for p in changes] + [(p, accepted) for p in accepted_paths]:
        for error in check(path):
            print(f"  {path.relative_to(ROOT)}: {error}")
            failures += 1
    if failures:
        print(f"{failures} open-stage defect(s)")
        return 1
    statuses = [specdoc.metadata(p.read_text()).get("Status", "").strip("*") for p in changes]
    print(
        f"{statuses.count('Open')} Open and {statuses.count('Ready')} Ready change document(s), "
        "and prospective accepted records are structurally complete"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

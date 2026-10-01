"""Require one exact disposition and a resolvable current owner for every accepted clause.

`applied.toml` is a one-way map from an accepted Decision clause through its disposition to the
current owner. An `applied` target may identify an untouched numbered section, an anchored numbered
section, or an anchored process section. A current owner need not cite the accepted revision back;
target existence is mechanically checkable, while semantic fidelity remains a review judgment.

Registry dispositions resolve through exact JSON locations in `registry-targets.toml`. Older
revisions retain their historical clause inference; current revisions enumerate `Decision clauses`.

    python revisions/ledger.py            # report
    python revisions/ledger.py --summary  # counts only
"""

from __future__ import annotations

import argparse
import functools
import json
import re
import sys
import tomllib
from pathlib import Path

try:
    from revisions.process_rules import canonical_anchors
except ModuleNotFoundError:  # Direct execution from revisions/.
    from process_rules import canonical_anchors

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARTS = ROOT / "spec" / "parts"
sys.path.insert(0, str(ROOT / "spec" / "tools"))

import specdoc

REVISIONS = HERE / "accepted"
LEDGER = HERE / "applied.toml"
REGISTRY_TARGETS = HERE / "registry-targets.toml"
#: Where a registry target may lie: the tree's artifacts and the extension registries outside it.
REGISTRY_ROOTS = ("spec/artifacts", "extensions", "escapewheel-aind/extensions")

DISPOSITIONS = {"applied", "registry", "superseded", "rationale"}


class LedgerError(Exception):
    """An accepted record or a ledger file no clause set can be read from; the message names it."""


HEADING = specdoc.HEADING
DECLARED_SECTION = specdoc.SECTION_CITATION


def targets(where: object) -> tuple[list[dict[str, str]], list[str]]:
    """Return well-formed applied targets and descriptions of malformed targets."""
    if not isinstance(where, list):
        return [], [f"{where!r}, which is not a list of targets"]
    found: list[dict[str, str]] = []
    malformed = []
    for target in where:
        if not isinstance(target, dict):
            malformed.append(f"{target!r}, which is not a target table")
            continue
        keys = set(target) - {"note"}
        if keys not in ({"part", "section"}, {"part", "anchor"}, {"path", "anchor"}):
            malformed.append(f"{target!r}, which has no recognized exact target shape")
            continue
        if not all(isinstance(target.get(key), str) and target[key] for key in keys):
            malformed.append(f"{target!r}, whose target fields are not nonempty strings")
            continue
        if "note" in target and not isinstance(target["note"], str):
            malformed.append(f"{target!r}, whose optional note is not a string")
            continue
        found.append(target)
    return found, malformed


@functools.cache
def sections(part: str) -> frozenset[str] | None:
    """Every section number a part declares, or None where no part carries that number."""
    found = specdoc.part_path(PARTS, part)
    return frozenset(HEADING.findall(found.read_text())) if found else None


def registry_target_defects(ledger: dict[str, dict]) -> list[str]:
    """Return missing, stale, malformed, or unresolved registry target declarations."""
    try:
        declared = tomllib.loads(REGISTRY_TARGETS.read_text()).get("target", {})
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"{REGISTRY_TARGETS.name}: {exc}"]
    expected = {key for key, entry in ledger.items() if entry.get("disposition") == "registry"}
    defects = [f"{key}: registry disposition has no exact target" for key in sorted(expected - set(declared))]
    defects += [f"{key}: target names no registry disposition" for key in sorted(set(declared) - expected)]
    defects += [
        f"{key}: registry disposition retains legacy `where`; use registry-targets.toml"
        for key in sorted(expected)
        if "where" in ledger[key]
    ]
    loaded: dict[Path, object] = {}
    for key in sorted(expected & set(declared)):
        locations = declared[key].get("locations")
        if not isinstance(locations, list) or not locations:
            defects.append(f"{key}: `locations` is not a nonempty list")
            continue
        seen: set[tuple[str, str]] = set()
        for location in locations:
            if not isinstance(location, dict):
                defects.append(f"{key}: target {location!r} is not a table")
                continue
            if set(location) - {"path", "pointer", "equals"}:
                defects.append(
                    f"{key}: target has unknown fields {sorted(set(location) - {'path', 'pointer', 'equals'})}"
                )
            path, at = location.get("path"), location.get("pointer")
            pair = (path, at) if isinstance(path, str) and isinstance(at, str) else None
            if pair is None:
                defects.append(f"{key}: target {location!r} needs string `path` and `pointer`")
                continue
            if pair in seen:
                defects.append(f"{key}: repeats {path}#{at}")
                continue
            seen.add(pair)
            artifact = (ROOT / path).resolve()
            if not any(artifact.is_relative_to((ROOT / root).resolve()) for root in REGISTRY_ROOTS):
                defects.append(f"{key}: {path!r} is outside {', '.join(REGISTRY_ROOTS)}")
                continue
            if artifact.suffix != ".json" or not artifact.is_file():
                defects.append(f"{key}: {path!r} is not an existing JSON artifact")
                continue
            try:
                document = loaded.setdefault(artifact, json.loads(artifact.read_text()))
                resolved = specdoc.resolve_pointer(document, at)
                if "equals" in location and resolved != location["equals"]:
                    defects.append(f"{key}: {path}#{at} is {resolved!r}, expected {location['equals']!r}")
                elif any(token.isdigit() for token in at.split("/")[1:]) and "equals" not in location:
                    defects.append(f"{key}: array target {path}#{at} needs an `equals` guard")
            except (
                json.JSONDecodeError,
                KeyError,
                IndexError,
                TypeError,
                ValueError,
            ) as exc:
                defects.append(f"{key}: {path}#{at} does not resolve ({exc})")
    return defects


def unresolved(  # noqa: C901
    ledger: dict[str, dict],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return every unresolved applied destination and every malformed target."""
    dangling, unparsed = [], []
    for key, entry in sorted(ledger.items(), key=lambda kv: int(kv[0][1:].split()[0])):
        if entry.get("disposition") != "applied":
            continue
        found, loose = targets(entry.get("where", []))
        unparsed += [(key, piece) for piece in loose]
        revision = int(key[1:].split()[0])
        revision_path = next(REVISIONS.glob(f"R{revision}-*.md"), None)
        domain = "specification"
        if revision_path is not None and revision >= 120:
            domain = specdoc.metadata_value(revision_path.read_text(), "Decision domain") or ""
        for target in found:
            if domain == "process" and "path" not in target:
                dangling.append((key, "process clause does not use a path-plus-anchor owner"))
                continue
            if "section" in target:
                part, section = target["part"], target["section"]
                declared = sections(part)
                if declared is None:
                    dangling.append((key, f"`{part}` — no part has that number"))
                elif section not in declared:
                    dangling.append(
                        (
                            key,
                            f"`{part}` §{section} — that part declares no such section",
                        )
                    )
            elif "part" in target:
                part = target["part"]
                file = specdoc.part_path(PARTS, part)
                if file is None:
                    dangling.append((key, f"`{part}` — no part has that number"))
                elif target["anchor"] not in canonical_anchors(file.read_text()):
                    dangling.append((key, f"`{part}` has no canonical #{target['anchor']}"))
            else:
                path = (ROOT / target["path"]).resolve()
                try:
                    path.relative_to(ROOT)
                except ValueError:
                    dangling.append((key, f"{target['path']!r} escapes the repository"))
                    continue
                if domain != "process":
                    dangling.append((key, "path-plus-anchor target is reserved for process clauses"))
                elif path != HERE / "CONTRIBUTING.md":
                    dangling.append((key, f"{target['path']!r} is not a recognized process owner"))
                elif not path.is_file() or target["anchor"] not in canonical_anchors(path.read_text()):
                    dangling.append((key, f"{target['path']} has no canonical #{target['anchor']}"))
    return dangling, unparsed


def clauses() -> dict[str, str]:
    """Every Decision clause of every accepted revision, as `R<n> §<sec>` to its title.

    Everything a revision decided, not only what carries an RFC 2119 keyword. `R68 §2.1` says
    `pts` *becomes* `int64` and binds a writer completely without one; filtering on MUST and
    SHOULD missed it, and missed `R6 §2` entirely because that revision states its decision at
    the section level with no subsections. A clause that turns out to be rationale is disposed
    as such, which is a judgement someone recorded rather than a heuristic that dropped it.
    """
    found = {}
    for path in sorted(
        REVISIONS.glob("R[0-9]*.md"),
        key=lambda p: int(re.match(r"R(\d+)", p.name).group(1)),
    ):
        number = re.match(r"R(\d+)", path.name).group(1)
        text = path.read_text()
        if "**Accepted**" not in text[:400]:
            continue
        # Current revisions state the exact normative set. This avoids inferring force from a
        # keyword: a declarative "becomes" binds without one, while Background can quote one.
        if (declared := specdoc.metadata_value(text, "Decision clauses")) is not None:
            titles = {
                m.group(1): m.group(2).strip()
                for m in re.finditer(r"^#{2,4} (\d+(?:\.\d+)*)\.?\s+(.+)$", text, re.MULTILINE)
            }
            named = DECLARED_SECTION.findall(declared)
            if not named:
                raise LedgerError(f"{path.name}: `Decision clauses` enumerates no section")
            for section in named:
                if section not in titles:
                    raise LedgerError(f"{path.name}: `Decision clauses` names absent §{section}")
                found[f"R{number} §{section}"] = titles[section]
            continue
        # Every section from 2 onward, at either depth. Section 1 is Motivation by convention;
        # after that the numbering is not consistent -- R32 states its rules in §2, §3 and §4,
        # R30's order is §3.2, R21's codec floor is §3 -- so position cannot say what binds.
        # A subsection supersedes its parent: `### 2.1` is disposed, `## 2.` then is not.
        matches = [
            m
            for m in re.finditer(r"^#{2,3} (\d+(?:\.[\d.]*\d)?)\.?\s+(.+)$", text, re.MULTILINE)
            if int(m.group(1).split(".")[0]) >= 2
        ]
        parents = {m.group(1).split(".")[0] for m in matches if "." in m.group(1)}
        for index, match in enumerate(matches):
            section = match.group(1)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end() : end]
            # A parent is enumerated only for its own body, the text before its first
            # subsection. R32 §4 states the manifest's carry-forward there and then subdivides;
            # skipping every parent lost it.
            if section in parents and not re.search(r"\b(MUST|SHOULD)\b", body):
                continue
            # A Decision subsection always counts: `R68 §2.1` says `pts` *becomes* `int64` and
            # binds completely without an RFC 2119 keyword. Anywhere else -- and the numbering
            # is not consistent, R32 decides in §2, §3 and §4 -- a keyword is what marks it.
            if section.startswith("2") or re.search(r"\b(MUST|SHOULD)\b", body):
                found[f"R{number} §{section}"] = match.group(2).strip()
    return found


def recorded() -> dict[str, dict[str, str]]:
    """What the ledger says, keyed the same way."""
    if not LEDGER.exists():
        return {}
    text = LEDGER.read_text()
    try:
        return tomllib.loads(text).get("clause", {})
    except tomllib.TOMLDecodeError as exc:
        # Appending an entry that already exists is the usual cause, and tomllib's traceback
        # says so only in its last line.
        raise LedgerError(f"{LEDGER.name}: {exc}") from None


def main() -> int:
    """Report every clause with no disposition, and every disposition naming no clause."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--summary", action="store_true", help="counts only")
    args = parser.parse_args()

    binding, ledger = clauses(), recorded()
    # The ratchet's high-water mark lives beside the data it describes, not as a number in
    # another file that someone has to remember to lower. Falling below it rewrites it, so
    # disposing a clause shows up as a diff and `verify.py`'s candidate-state comparison sees it.
    baseline = tomllib.loads(LEDGER.read_text()).get("baseline", {}).get("undisposed", 0) if LEDGER.exists() else 0
    undisposed = {k: v for k, v in binding.items() if k not in ledger}
    # A disposition for a clause that no longer exists is as wrong as a missing one: the revision
    # was edited, or the clause was renumbered, and the ledger now vouches for nothing.
    stale = sorted(set(ledger) - set(binding))
    bad = {k: d.get("disposition") for k, d in ledger.items() if d.get("disposition") not in DISPOSITIONS}
    # An `applied` entry naming no part says the clause was written down and not where, which is
    # the state the withdrawn `implementation` disposition made permanent for 23 clauses.
    placeless = sorted(k for k, d in ledger.items() if d.get("disposition") == "applied" and not d.get("where"))
    dangling, unparsed = unresolved(ledger)
    registry_defects = registry_target_defects(ledger)
    counts: dict[str, int] = {}
    for entry in ledger.values():
        counts[entry.get("disposition", "?")] = counts.get(entry.get("disposition", "?"), 0) + 1
    print(f"{len(binding)} decision clauses across the accepted revisions")
    for name in sorted(counts):
        print(f"  {counts[name]:>4}  {name}")
    print(f"  {len(undisposed):>4}  undisposed")

    # Undisposed clauses are a backlog and can run to hundreds, so `--summary` holds them back.
    # The rest are defects in what the ledger already claims, and there is nothing to read
    # instead of them.
    if not args.summary:
        for key, title in sorted(undisposed.items(), key=lambda kv: (int(kv[0][1:].split()[0]), kv[0])):
            print(f"    UNDISPOSED  {key:<12} {title[:62]}")
    for key in stale:
        print(f"    STALE       {key:<12} the ledger disposes a clause no revision states")
    for key, value in sorted(bad.items()):
        print(f"    BAD         {key:<12} disposition {value!r} is not one of {sorted(DISPOSITIONS)}")
    for key in placeless:
        print(f"    PLACELESS   {key:<12} applied, but `where` names no part")
    for key, target in dangling:
        print(f"    DANGLING    {key:<12} {target}")
    for key, piece in unparsed:
        print(f"    MALFORMED   {key:<12} `where` holds {piece}")
    for defect in registry_defects:
        print(f"    REGISTRY    {defect}")
    over = max(0, len(undisposed) - baseline)
    failures = over + len(stale) + len(bad) + len(placeless) + len(dangling) + len(unparsed) + len(registry_defects)
    if len(undisposed) < baseline:
        text = LEDGER.read_text()
        text = re.sub(r"(?m)^undisposed = \d+$", f"undisposed = {len(undisposed)}", text)
        print(f"ratchet lowered: undisposed {baseline} -> {len(undisposed)}")
        LEDGER.write_text(text)
        print("commit applied.toml")
        return 0
    if not failures:
        print(f"\nok — {len(undisposed)} undisposed, at the recorded high-water mark")
    elif over:
        print(f"\n{over} clause(s) need a disposition; the mark is {baseline}")
    else:
        print(f"\n{failures} disposition(s) vouch for something that is not there")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        status = main()
    except LedgerError as error:
        raise SystemExit(str(error)) from None
    raise SystemExit(status)

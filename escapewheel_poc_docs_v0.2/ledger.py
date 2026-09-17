"""Every accepted normative clause has a disposition, or the compilation fails.

Two independent audits of this specification found dropped clauses, and found different ones:
`R53 §2.4`'s escape to `int64` vanished, `R21`'s codec floor vanished, `R36 §2.2`'s prefix digest
was reversed into "undefined", `R52`'s SHOULD became a MUST. Each was invisible because the
revision is cited elsewhere in the spec, so a citation sweep sees it and a reader does not.

The fix is a ledger rather than another audit. Every clause of every accepted revision that
carries RFC 2119 force appears in `applied.toml` with one of four dispositions:

    applied         stated in the compiled spec; `where` lists the parts and sections
    registry        delegated to one or more exact JSON declarations in registry-targets.toml
    superseded      a later revision replaced it; `by` names which
    rationale       decided nothing, so there is nothing to place

A clause binding a writer, reader, validator or consumer is `applied` like any other: an actor
is bound by the spec's prose, so naming one does not excuse a clause from appearing in a part.
There was a fifth disposition, `implementation`, which said a clause "binds a writer, reader or
validator rather than the prose" and so let 23 of them be counted as disposed while living
nowhere in the durable document. 21 were in a part or the registry all along and the ledger had
simply never recorded where; 2 had reached no part, which is the class this script exists to
catch and which that disposition hid. `applied` now requires a `where`.

A clause with no entry is **undisposed**, and this script exits non-zero listing them. Adding a
revision therefore adds failures until someone says where each of its clauses went, which is the
property neither audit had. A `registry` disposition also has one or more path-plus-JSON-Pointer
locations in `registry-targets.toml`. Every path and pointer is resolved, so naming a registry file
without naming the declaration it carries is not a disposition.

New revisions enumerate their normative clauses in the `Decision clauses` metadata field. That is
the exact set this ledger reads. Older revisions predate the field and retain the historical
heading-and-keyword inference used to compile their existing entries.

An `applied` entry's `where` is a list of `{ part, section }` targets, each with an optional `note`
saying which piece of the clause landed there. Every one is resolved against that part's own
headings, so a clause cannot be recorded as placed in a section that does not exist -- the defect
one step along from no `where` at all, and the one that let R111 §3.5 name two sections of Part 01
that part has never carried.

The other dispositions omit `where`. A `registry` entry's machine location comes only from
`registry-targets.toml`; `superseded` names its replacement in `by`.

A section that exists is not a section that says the right thing, and `05` §8 held four clauses
belonging to §11 while resolving perfectly. So each `applied` target is also checked against what
the part states there: a part cites the revision that set each rule it carries (`00` §10.2), so a
target whose section names its revision is the part confirming the claim. It corroborates rather
than proves -- a later revision resetting the same rule replaces the citation. The reviewed legacy
cases for which that corroboration is absent are enumerated exactly in
`corroboration-exceptions.toml`. A new exception or an exception that is no longer needed fails;
one cannot hide behind an unchanged count.

    python ledger.py            # report
    python ledger.py --summary  # counts only
"""

from __future__ import annotations

import argparse
import functools
import json
import re
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REVISIONS = HERE.parent / "revisions"
LEDGER = HERE / "applied.toml"
REGISTRY_TARGETS = HERE / "registry-targets.toml"
CORROBORATION_EXCEPTIONS = HERE / "corroboration-exceptions.toml"

DISPOSITIONS = {"applied", "registry", "superseded", "rationale"}

#: `## 3.` and `### 3.1 ` alike, which is every section a part declares.
HEADING = re.compile(r"^#{1,4} (\d+(?:\.\d+)*)\.?(?:\s|$)", re.MULTILINE)
#: The same, keeping the depth, so a section's own text can be cut from its subsections'.
NUMBERED = re.compile(r"^(#{1,4}) (\d+(?:\.\d+)*)\.?(?:\s|$)")
DECLARED = re.compile(r"^\|\s*\*\*Decision clauses\*\*\s*\|\s*(.*?)\s*\|$", re.MULTILINE)
DECLARED_SECTION = re.compile(r"§(\d+(?:\.\d+)*)")


def targets(where: object) -> tuple[list[tuple[str, str]], list[str]]:
    """Each (part, section) an `applied` entry's `where` names, and every target that is malformed.

    A target is a table of `part` and `section`, with an optional `note` saying which piece of the
    clause landed there. The field was prose until the shape was pinned, and the cost was that
    every consumer parsed it differently and partially -- a field naming two parts read as naming
    none, and a pattern scanning one for two adjacent digits read `05 §10 §12` as part 05 and then
    part **10**, inventing a target in the same pass as it lost a real one.
    """
    if not isinstance(where, list):
        return [], [f"{where!r}, which is not a list of targets"]
    found, malformed = [], []
    for target in where:
        if (isinstance(target, dict) and isinstance(target.get("part"), str)
                and isinstance(target.get("section"), str)):
            found.append((target["part"], target["section"]))
        else:
            malformed.append(f"{target!r}, which is not a `part` and a `section`")
    return found, malformed


@functools.cache
def sections(part: str) -> frozenset[str] | None:
    """Every section number a part declares, or None where no part carries that number."""
    found = sorted(HERE.glob(f"{part}_*.md"))
    return frozenset(HEADING.findall(found[0].read_text())) if found else None


@functools.cache
def bodies(part: str) -> dict[str, str]:
    """Each section of a part, mapped to its own text and its subsections'.

    A section runs to the next heading at its depth or shallower, so `§9` carries `§9.1` and
    `§9.2` while `§9.2` carries neither its parent's preamble nor its siblings.
    """
    found = sorted(HERE.glob(f"{part}_*.md"))
    if not found:
        return {}
    lines = found[0].read_text().splitlines()
    marks = [(n, m.group(2)) for n, line in enumerate(lines) if (m := NUMBERED.match(line))]
    out = {}
    for index, (start, number) in enumerate(marks):
        depth = number.count(".")
        end = next((s for s, other in marks[index + 1:] if other.count(".") <= depth), len(lines))
        out[number] = "\n".join(lines[start:end])
    return out


def corroborated(revision: str, part: str, section: str) -> bool:
    """Whether the part confirms the ledger's claim by citing the revision where it says.

    A part cites the revision that set each rule it states, which `00` §10.2 permits as
    provenance and R112 §2.2 makes the reason citing a part loses nothing. So the ledger's claim
    that a clause landed somewhere is checkable against the section itself: `05` §8 named three
    R75 clauses and cites R75 nowhere, because those clauses are §11's.

    A parent counts for a subsection, since a rule stated once in a section's preamble covers the
    subsections that qualify it, and a later revision resetting the same rule replaces the
    citation -- which is why this corroborates rather than proves.
    """
    text = bodies(part)
    here = text.get(section, "")
    parent = text.get(section.rsplit(".", 1)[0], "") if "." in section else ""
    return any(re.search(rf"\b{revision}[ ,)§]", body) for body in (here, parent) if body)


def uncorroborated(ledger: dict[str, dict]) -> list[tuple[str, str, str]]:
    """Every `applied` target whose section does not cite the revision that claims to have landed there."""
    out = []
    for key, entry in sorted(ledger.items(), key=lambda kv: int(kv[0][1:].split()[0])):
        if entry.get("disposition") != "applied":
            continue
        revision = key.split()[0]
        for part, section in targets(entry.get("where", []))[0]:
            if not corroborated(revision, part, section):
                out.append((key, part, section))
    return out


def pointer(document: object, value: str) -> object:
    """Resolve one RFC 6901 JSON Pointer, raising a useful lookup error."""
    if not isinstance(value, str) or not value.startswith("/"):
        raise ValueError("pointer must be a nonempty RFC 6901 string beginning with `/`")
    current = document
    for raw in value[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise KeyError(token)
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise IndexError(token)
            current = current[int(token)]
        else:
            raise TypeError(f"{token!r} follows a scalar")
    return current


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
                defects.append(f"{key}: target has unknown fields {sorted(set(location) - {'path', 'pointer', 'equals'})}")
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
            try:
                artifact.relative_to((ROOT / "registry").resolve())
            except ValueError:
                defects.append(f"{key}: {path!r} is outside registry/")
                continue
            if artifact.suffix != ".json" or not artifact.is_file():
                defects.append(f"{key}: {path!r} is not an existing JSON artifact")
                continue
            try:
                document = loaded.setdefault(artifact, json.loads(artifact.read_text()))
                resolved = pointer(document, at)
                if "equals" in location and resolved != location["equals"]:
                    defects.append(
                        f"{key}: {path}#{at} is {resolved!r}, expected {location['equals']!r}"
                    )
                elif any(token.isdigit() for token in at.split("/")[1:]) and "equals" not in location:
                    defects.append(f"{key}: array target {path}#{at} needs an `equals` guard")
            except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
                defects.append(f"{key}: {path}#{at} does not resolve ({exc})")
    return defects


def corroboration_exception_defects(
    thin: list[tuple[str, str, str]],
) -> tuple[list[str], int]:
    """Compare absent provenance with the exact reviewed exception set."""
    try:
        rows = tomllib.loads(CORROBORATION_EXCEPTIONS.read_text()).get("exception", [])
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"{CORROBORATION_EXCEPTIONS.name}: {exc}"], 0
    allowed: dict[tuple[str, str, str], str] = {}
    defects = []
    for row in rows:
        if not isinstance(row, dict):
            defects.append(f"exception {row!r} is not a table")
            continue
        key = (row.get("clause"), row.get("part"), row.get("section"))
        if not all(isinstance(piece, str) and piece for piece in key):
            defects.append(f"exception {row!r} needs clause, part, and section")
            continue
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            defects.append(f"{key}: exception has no review reason")
        if key in allowed:
            defects.append(f"{key}: exception is repeated")
        allowed[key] = row.get("reason", "")
    current = set(thin)
    for key in sorted(current - set(allowed)):
        defects.append(f"{key[0]}: `{key[1]}` §{key[2]} lacks provenance and is not reviewed")
    for key in sorted(set(allowed) - current):
        defects.append(f"{key[0]}: `{key[1]}` §{key[2]} exception is no longer needed")
    return defects, len(allowed)


def unresolved(ledger: dict[str, dict]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Every `applied` target naming no section, and every one that is not a target at all."""
    dangling, unparsed = [], []
    for key, entry in sorted(ledger.items(), key=lambda kv: int(kv[0][1:].split()[0])):
        if entry.get("disposition") != "applied":
            continue
        found, loose = targets(entry.get("where", []))
        unparsed += [(key, piece) for piece in loose]
        for part, section in found:
            declared = sections(part)
            if declared is None:
                dangling.append((key, f"`{part}` — no part has that number"))
            elif section not in declared:
                dangling.append((key, f"`{part}` §{section} — that part declares no such section"))
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
    for path in sorted(REVISIONS.glob("R*.md"), key=lambda p: int(re.match(r"R(\d+)", p.name).group(1))):
        number = re.match(r"R(\d+)", path.name).group(1)
        text = path.read_text()
        if "**Accepted**" not in text[:400]:
            continue
        # Current revisions state the exact normative set. This avoids inferring force from a
        # keyword: a declarative "becomes" binds without one, while Background can quote one.
        if declared := DECLARED.search(text[:2000]):
            titles = {
                m.group(1): m.group(2).strip()
                for m in re.finditer(r"^#{2,4} (\d+(?:\.\d+)*)\.?\s+(.+)$", text, re.MULTILINE)
            }
            named = DECLARED_SECTION.findall(declared.group(1))
            if not named:
                raise SystemExit(f"{path.name}: `Decision clauses` enumerates no section")
            for section in named:
                if section not in titles:
                    raise SystemExit(f"{path.name}: `Decision clauses` names absent §{section}")
                found[f"R{number} §{section}"] = titles[section]
            continue
        # Every section from 2 onward, at either depth. Section 1 is Motivation by convention;
        # after that the numbering is not consistent -- R32 states its rules in §2, §3 and §4,
        # R30's order is §3.2, R21's codec floor is §3 -- so position cannot say what binds.
        # A subsection supersedes its parent: `### 2.1` is disposed, `## 2.` then is not.
        matches = [m for m in re.finditer(r"^#{2,3} (\d+(?:\.[\d.]*\d)?)\.?\s+(.+)$", text, re.MULTILINE)
                   if int(m.group(1).split(".")[0]) >= 2]
        parents = {m.group(1).split(".")[0] for m in matches if "." in m.group(1)}
        for index, match in enumerate(matches):
            section = match.group(1)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end():end]
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
        raise SystemExit(f"{LEDGER.name}: {exc}") from None


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
    bad = {k: d.get("disposition") for k, d in ledger.items()
           if d.get("disposition") not in DISPOSITIONS}
    # An `applied` entry naming no part says the clause was written down and not where, which is
    # the state the withdrawn `implementation` disposition made permanent for 23 clauses.
    placeless = sorted(k for k, d in ledger.items()
                       if d.get("disposition") == "applied" and not d.get("where"))
    dangling, unparsed = unresolved(ledger)
    registry_defects = registry_target_defects(ledger)
    # What the section itself says, as far as anything can check it: a part cites the revision
    # that set each rule it states, so a target citing it is the part confirming the claim.
    thin = uncorroborated(ledger)
    exception_defects, exception_count = corroboration_exception_defects(thin)

    counts: dict[str, int] = {}
    for entry in ledger.values():
        counts[entry.get("disposition", "?")] = counts.get(entry.get("disposition", "?"), 0) + 1
    print(f"{len(binding)} decision clauses across the accepted revisions")
    for name in sorted(counts):
        print(f"  {counts[name]:>4}  {name}")
    print(f"  {len(undisposed):>4}  undisposed")
    print(f"  {len(thin):>4}  applied, in a section that does not cite the revision")
    print(f"  {exception_count:>4}  exact reviewed corroboration exceptions")

    # Undisposed clauses are a backlog and can run to hundreds, so `--summary` holds them back.
    # The rest are defects in what the ledger already claims, and there is nothing to read
    # instead of them.
    if not args.summary:
        for key, title in sorted(undisposed.items(), key=lambda kv: (int(kv[0][1:].split()[0]), kv[0])):
            print(f"    UNDISPOSED  {key:<12} {title[:62]}")
        for key, part, section in thin:
            print(f"    UNCORROBORATED {key:<12} `{part}` §{section} states no such provenance")
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
    for defect in exception_defects:
        print(f"    EXCEPTION   {defect}")

    over = max(0, len(undisposed) - baseline)
    failures = (over + len(stale) + len(bad) + len(placeless) + len(dangling) + len(unparsed)
                + len(registry_defects) + len(exception_defects))
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
    raise SystemExit(main())

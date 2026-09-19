"""Check the built registry against the invariants R2-R9 establish."""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG = json.loads((HERE / "logical_schemas.json").read_text())
T = REG["tables"]
# Part 09 §2: an extension is a registry document in R2's format, so the invariants that hold of a
# registry hold of it. They are checked here for the same reason core's are -- a naming
# convention or an unparseable rule is a property of the document, which no packet's rows can
# show and no SQL can see (R12 §4).
EXT = {
    f.stem: json.loads(f.read_text())
    for f in sorted((HERE / "extensions").glob("*.json"))
}
EXT_T = {n: t for doc in EXT.values() for n, t in doc["tables"].items()}
ALL = T | EXT_T

fail = []


def check(label, bad, fmt=str):
    bad = list(bad)
    print(f"{'FAIL' if bad else 'ok  '}  {label}" + (f"  ({len(bad)})" if bad else ""))
    for b in bad[:4]:
        print(f"          {fmt(b)}")
    if bad:
        fail.append(label)


ledger = subprocess.run(
    [sys.executable, str(HERE.parent / "conformance/spec-sweep/tables.py")],
    capture_output=True,
    text=True,
    check=False,
).stdout
# Namespaces beyond core exist from Part 00 §3; match any <namespace>.<table> line.
expected = {
    l.strip()
    for l in ledger.splitlines()
    if re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", l.strip())
}
check("table set matches R9 §2 ledger", expected ^ set(T))
# R29 §6. A 02 table whose columns a revision amended carries `since` on those columns and
# not on itself, which is right -- so the checkable claims are the format and that every
# revision the build stamps is one the registry says it derived from.
# The inverse, and the one that was actually missing: a revision may be accepted, implemented,
# and left out of the list. R54, R65 and R66 all were, for several revisions each, because the
# list was hand-maintained and only the stamped direction was checked.
_accepted = set()
for _revision in (HERE.parent / "revisions/accepted").glob("R[0-9]*.md"):
    _head = _revision.read_text()[:2000]
    _number = int(re.match(r"R(\d+)", _revision.name).group(1))
    _domain = re.search(
        r"^\| \*\*Decision domain\*\* \| (.*?) \|$", _head, re.MULTILINE
    )
    if "**Accepted**" in _head and (
        _number < 120 or (_domain is not None and _domain.group(1) == "specification")
    ):
        _accepted.add(f"R{_number}")
_listed = set(REG.get("derived_from", {}).get("revisions", []))
check(
    "every accepted specification revision is declared in derived_from",
    sorted(_accepted - _listed, key=lambda r: int(r[1:])),
)
check(
    "derived_from declares no revision that is not an accepted specification decision",
    sorted(_listed - _accepted, key=lambda r: int(r[1:])),
)
check(
    "every stamped revision is declared in derived_from",
    sorted(
        {
            v.split(" ")[0]
            for n, t in T.items()
            for v in [t.get("since"), *(c.get("since") for c in t["columns"])]
            if v
        }
        - set(REG.get("derived_from", {}).get("revisions", []))
    ),
)
check(
    "a since names a revision",
    [
        (n, v)
        for n, t in T.items()
        for v in [t.get("since"), *(c.get("since") for c in t["columns"])]
        if v is not None and not re.fullmatch(r"R\d+(?: §[\d.\-]+)?", v)
    ],
)
# Part 09 §2's invariants live in `escapewheel_validator.registry_document`, because an author
# outside this repository has the same document and the same question and no way to ask it. Core
# is held to exactly what an extension is held to, which is only true while there is one
# implementation of them.
sys.path.insert(0, str(HERE))
from escapewheel_validator.registry_document import (
    declarations,
    structural,
)


def _structural(tables, universe, prefix="", *, is_core=False):
    """Run the shared invariants and report each finding through this script's own printer."""
    for finding in structural(tables, universe, is_core=is_core):
        check(f"{prefix}{finding.label}", finding.offenders)


_structural(T, T, is_core=True)
for _id, _doc in EXT.items():
    _structural(_doc["tables"], T | _doc["tables"], prefix=f"{_id}: ")

# Part 09 §2's MUST, stated rather than implied: core resolving against itself above cannot see a
# reference *into* an extension, because such a target would simply be absent from core.
check(
    "core references no extension",
    [
        (n, r["resource"])
        for n, t in T.items()
        for r in t["references"]
        if r["resource"] in EXT_T
    ],
)
# What an extension declares about itself, from the same module the command runs, so an author
# outside this repository is held to exactly this.
for _id, _doc in EXT.items():
    for _finding in declarations(_doc, _id):
        check(f"{_id}: {_finding.label}", _finding.offenders)
# R57 §4 for core's own document, which `declarations` covers only for an extension. A meta-schema
# URI resolves to nothing over the network, so what makes the declaration worth carrying is that it
# is verifiable offline against the schema in hand.
META_ID = json.loads((HERE / "registry.schema.json").read_text())["$id"]
check(
    "the core registry names this meta-schema",
    [f"logical_schemas: {REG.get('$schema', 'declares none')}"]
    if REG.get("$schema") != META_ID
    else [],
)

check(
    "withdrawn tables absent",
    [
        n
        for n in (
            "core.unit_spike_chunks",
            "core.provenance_entities",
            "core.provenance_activities",
            "core.provenance_edges",
        )
        if n in T
    ],
)

# rules.json is hand-authored and merged at build time, so it can drift from the
# structure it annotates. build.py rejects unknown tables; these catch the rest.
RULES = json.loads((HERE / "rules.json").read_text())["rules"]
check("every rules.json table exists in the registry", sorted(set(RULES) - set(T)))

# Template invocations carry no id until build.py expands them (R24 §3). Expand through the
# same function rather than a second copy, so this cannot drift from what the build does.
sys.path.insert(0, str(HERE))
from build import expand

authored_rules = []
for resource, rs in RULES.items():
    for r in rs:
        if template := r.get("use"):
            authored_rules += expand(template, resource, r, T[resource]["primary_key"])
        else:
            authored_rules.append(r)

merged = {r["id"] for t_ in T.values() for r in t_["rules"]}
authored = {r["id"] for r in authored_rules}
check("every authored rule reached the registry", sorted(authored - merged))
check(
    "the registry carries no rule rules.json does not author", sorted(merged - authored)
)
# Part 02 §10.2. `optional` lets a column be absent from the file, and a Tier 2 rule is SQL run against
# that file -- so a rule naming one does not miss a check, it fails to parse, and the run meant to
# find defects reports an error of its own. The match is on identifiers rather than text: string
# literals and comments are stripped, and a name matches only whole, so `some_metadata_key` and a
# quoted 'metadata' are not hits. Part 02 §10.2 records what this rests on -- every column bearing one of
# these names is optional -- and R94 §6 what would break it.
_OPTIONAL = {
    c["name"]
    for t_ in (*T.values(), *EXT_T.values())
    for c in t_["columns"]
    if c["presence"] == "optional"
}


def _identifiers(sql):
    """Every whole word in `sql`, with string literals and comments removed."""
    body = re.sub(r"'[^']*'", " ", sql)
    body = re.sub(r"--[^\n]*", " ", body)
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", body))


check(
    "no Tier 2 rule names an optional column (Part 02 §10.2)",
    sorted(
        {
            (r["id"], c)
            for t_ in (*T.values(), *EXT_T.values())
            for r in t_["rules"]
            for c in _OPTIONAL & _identifiers(r["sql"])
        }
    ),
    lambda b: f"{b[0]} names {b[1]}, which is optional and may be absent from the file",
)

ids = [r["id"] for r in authored_rules] + [
    r["id"] for t_ in EXT_T.values() for r in t_["rules"]
]
check(
    "rule ids are unique across core and every extension",
    sorted({i for i in ids if ids.count(i) > 1}),
)
check(
    "an extension's rule ids carry its table's name",
    [
        r["id"]
        for n, t_ in EXT_T.items()
        for r in t_["rules"]
        if not r["id"].startswith(f"{n}.")
    ],
)


# R50 §5: a naming convention is a property of the registry, not of any packet's rows, so no SQL
# rule can see it -- and one written anyway would pass silently (R12 §4). It is checked here.
#
# R48 is what makes this exact rather than heuristic. Before a column declared its `role`,
# "identifier-shaped" had to be guessed from name and type, which is why R50's three misnamed
# columns survived as long as they did. Seven of the nine tests below compare a name against a
# *declaration* and consequently flag nothing; the two that remain compare it against a type,
# and those are the two carrying every exception.

#: SQL reserved words a column name must not be, unless declared below. Not exhaustive: it is
#: the words that have actually collided, since the point is to notice a new one.
RESERVED = {
    "offset",
    "order",
    "group",
    "select",
    "from",
    "where",
    "table",
    "column",
    "index",
    "key",
    "all",
    "primary",
    "case",
    "when",
    "end",
    "values",
}
INTEGERS = {"int32", "int64"}

#: Names that break a convention on purpose, each with the reason. An exception is declared, never
#: inferred: a baseline absorbing whatever exists today would have absorbed `step_ticks` too.
#: Removing a column here without renaming it fails the run, which is the point.
NAMING_EXCEPTIONS = {
    "core.array_assets.offset": "NWB-standard name; the reserved word is handled by unconditional quoting (R50 §4)",
    "analysis.array_assets.offset": "as core.array_assets.offset",
    "core.array_channels.offset": "as core.array_assets.offset, per channel (R19 §2)",
    "core.units.n_spikes": "a count, not a plural duration -- the shape R50 §3 renamed step_ticks for",
    "core.source_files.size_bytes": "a quantity in bytes, not a plural of `size_byte`",
    "core.media_frames.pts": "the container's own initialism for one timestamp, not a plural (Part 01 §3.18)",
    # A metric's name is the vocabulary people search by, so renaming one makes the column match
    # nothing anyone's code expects. Unlike `sync_spike_8`, none of these is a parameter glued on.
    "aind_unit_qc.metrics.rp_violations": "the sorter's own metric name; a count of violations",
    "aind_unit_qc.waveform_metrics.num_negative_peaks": "the sorter's own metric name; a count of peaks",
    "aind_unit_qc.waveform_metrics.num_positive_peaks": "as num_negative_peaks",
    # Part 02 §8.3: each carries `core.intervals.interval_kind` as part of the shared key, so it holds
    # a discriminator's value without being one -- and the name must match the parent's column for
    # the composite reference to read.
    # R100 §2.1: `_kind` reads as a category and every column carrying it holds one -- an
    # interval's kind, a run's scope kind. This holds the table whose rows are the data, and R48
    # §3 measured that a role says what a name cannot, which is why R55 added the role.
    "core.array_dimensions.coordinate_resource": "names the table whose rows are the axis's positions, not a kind of thing (R100 §2.1)",
    "analysis.array_dimensions.coordinate_resource": "as core.array_dimensions.coordinate_resource",
    "dynamic_foraging.trials.interval_kind": "carries core.intervals.interval_kind as a shared-key column, not a discriminator (Part 02 §8.3)",
    "vr_foraging.sites.interval_kind": "as dynamic_foraging.trials.interval_kind",
}

NAMING = {
    "an identifier is named _id": lambda n, t, role: (
        not (role == "identifier" and not n.endswith(("_id", "_label", "_name")))
    ),
    "an _id column is an identifier": lambda n, t, role: (
        not (n.endswith("_id") and role != "identifier")
    ),
    # R53 §2.1 inverted this: an identifier is an integer, and a string one is the defect.
    "an _id column is an integer": lambda n, t, role: (
        not (n.endswith("_id") and t not in INTEGERS)
    ),
    "a _name column is a string": lambda n, t, role: (
        not (n.endswith("_name") and t != "string")
    ),
    "a _tick column is a coordinate": lambda n, t, role: (
        not (n.endswith("_tick") and role != "coordinate")
    ),
    "a coordinate is named _tick": lambda n, t, role: (
        not (role == "coordinate" and not n.endswith("_tick"))
    ),
    "an _index column is an index": lambda n, t, role: (
        not (
            n.endswith("_index")
            and role not in {"structural_index", "sequence_position"}
        )
    ),
    "a structural index is named _index": lambda n, t, role: (
        not (role == "structural_index" and not n.endswith("_index"))
    ),
    "no column is a reserved word": lambda n, t, role: n not in RESERVED,
    # R50 §3: `step_ticks` read as a coordinate and was a duration. A plural integer is the shape
    # that confusion takes, so it is flagged and a real count says so here.
    "no integer column is plural": lambda n, t, role: (
        not (n.endswith("s") and t in INTEGERS)
    ),
    # Part 02 §8.3. A discriminator holds a dotted resource ID, so it is a string by construction,
    # and the `_kind` suffix is what R49 chose for the first one.
    "a _kind column is a discriminator": lambda n, t, role: (
        not (n.endswith("_kind") and role != "discriminator")
    ),
    "a discriminator is named _kind": lambda n, t, role: (
        not (role == "discriminator" and not n.endswith("_kind"))
    ),
    "a discriminator is a string": lambda n, t, role: (
        not (role == "discriminator" and t != "string")
    ),
}

flagged = {}
for label, holds in NAMING.items():
    for tid, tbl in ALL.items():
        for c in tbl["columns"]:
            if not holds(c["name"], c["type"], c.get("role")):
                flagged.setdefault(f"{tid}.{c['name']}", []).append(label)
check(
    "column names follow the conventions, or say why not",
    sorted(
        f"{k}: {', '.join(v)}" for k, v in flagged.items() if k not in NAMING_EXCEPTIONS
    ),
)
check(
    "every declared naming exception still exists and still breaks a convention",
    sorted(k for k in NAMING_EXCEPTIONS if k not in flagged),
)
print(
    f"      {len(NAMING)} conventions over {sum(len(t['columns']) for t in ALL.values())} columns "
    f"in core and {len(EXT)} extensions, "
    f"{len(NAMING_EXCEPTIONS)} declared exceptions"
)


#: Part 02 §8.2. Name columns that name a **kind** of thing rather than one assigned identifier's
#: value, and are therefore expected to repeat. Declared rather than inferred, for the reason
#: NAMING_EXCEPTIONS is: a set absorbing whatever has no `*_id` sibling today would absorb the
#: next identifier whose name column was added without one.
NAMES_A_KIND = {
    "core.array_dimensions.dimension_name": "an axis's name, repeated across every array",
    "analysis.array_dimensions.dimension_name": "as core.array_dimensions.dimension_name",
    "core.probes.insertion_name": "the trajectory the probe was inserted along, not the probe",
    "core.processing_runs.software_name": "what ran, so every run of one tool repeats it",
    "core.sessions.task_name": "which task, so every session running it repeats the name",
    "core.sorting_runs.sorter_name": "as software_name, per sorting",
    "dynamic_foraging.sessions.auto_train_curriculum_name": "which curriculum, not which session",
    "vr_foraging.sessions.curriculum_name": "as auto_train_curriculum_name",
    "vr_foraging.sessions.curriculum_stage_name": "which stage of it",
    "core.coordinate_frame_axes.axis_name": "what the source called the field, repeated across "
    "every frame that read the same one (Part 01 §3.24)",
}

# Part 02 §8.2. Which `*_name` columns carry the uniqueness obligation: the ones naming an assigned
# identifier of their own table. No rule can enforce it -- a writer numbering per distinct name
# has already merged two things into one row, and that merge is what Part 01 §3.5 requires of four
# streams naming one serial -- so the registry says which columns it falls on and Part 02 §8.2 states
# the counts. Everything else must be declared above, so a new name column is a decision.
named = {}
for tid, tbl in ALL.items():
    owned = {c["name"]: c for c in tbl["columns"]}
    for c in tbl["columns"]:
        if c["name"].endswith("_name"):
            identifier = owned.get(f"{c['name'][: -len('_name')]}_id") or {}
            named[f"{tid}.{c['name']}"] = identifier.get("identity") == "assigned"
check(
    "a name column names an assigned identifier, or is declared to name a kind of thing",
    sorted(n for n, paired in named.items() if not paired and n not in NAMES_A_KIND),
)
check(
    "every column declared to name a kind of thing still exists and still names one",
    sorted(n for n in NAMES_A_KIND if named.get(n, True)),
)
core_unique = sum(
    1 for n, paired in named.items() if paired and not n.startswith(tuple(EXT))
)
print(
    f"      {sum(named.values())} name columns must be unique within a packet (Part 02 §8.2), "
    f"{core_unique} of them in core and analysis; {len(NAMES_A_KIND)} name a kind of thing"
)


# Part 00 §2.4. Which tables a reader must carry a session discriminator on: the ones reaching
# `core.sessions` through their declared references. A property of the registry, decided with no
# packet in hand, and the stricter of the two available tests -- every table carrying a
# `session_id` reaches the table, while eight reach it without carrying the column, so the graph
# subsumes the column and the column does not subsume the graph. R46 is what made it usable, by
# declaring the sixteen foreign keys that had never been written.
def session_scoped(tables):
    """Every table reaching `core.sessions`, `core.sessions` itself included."""
    edges = {n: {r["resource"] for r in t["references"]} for n, t in tables.items()}

    def reaches(name, seen):
        if name == "core.sessions":
            return True
        if name in seen:
            return (
                False  # a self-reference is well-founded (Part 01 §3.5) and not a route
            )
        seen.add(name)
        return any(reaches(m, seen) for m in edges.get(name, ()))

    return {n for n in tables if reaches(n, set())}


scoped = session_scoped(T)
carries = {
    n for n, t in T.items() if any(c["name"] == "session_id" for c in t["columns"])
}
check(
    "every table carrying session_id reaches core.sessions (Part 00 §2.4)",
    sorted(carries - scoped),
)
# Part 02 §7.1's two halves, neither of which anything checked. The column and the reference are
# separate obligations and the second is the one that bites: Tier 1 generates one anti-join per
# declared reference and nothing from a column's name, so a `session_id` in no reference is a
# foreign key no rule can see -- which is how 418,618,218 rows came to hold an unvalidated session
# key. `core.sessions` is the one exemption, having nothing to reference but itself.
#
# The second check runs over the extensions too, and is deliberately weaker there than Part 02 §7.1's
# letter: it asks that `session_id` be part of *some* declared reference rather than of a direct one
# to `core.sessions`. Four extension tables carry it inside a composite reference to another
# session-scoped table, which gives Tier 1 the anti-join Part 02 §7.1's reasoning asks for while not
# being the reference Part 02 §7.1 names. Whether the letter or the reasoning governs is a question for
# a revision; enforcing the letter here would mean adding a redundant reference to those four.
check(
    "every session-scoped table carries session_id (Part 02 §7.1)",
    sorted(scoped - carries),
)
_in_a_reference = {
    n for n, t in ALL.items() for r in t["references"] if "session_id" in r["columns"]
}
check(
    "every table carrying session_id declares it in a reference (Part 02 §7.1)",
    sorted(
        {
            n
            for n, t in ALL.items()
            if n != "core.sessions"
            and any(c["name"] == "session_id" for c in t["columns"])
        }
        - _in_a_reference
    ),
)
_direct = {
    n
    for n, t in ALL.items()
    for r in t["references"]
    if r["resource"] == "core.sessions" and r["columns"] == ["session_id"]
}
print(
    f"      {len(_direct)} tables reference core.sessions on session_id directly; "
    f"{len(_in_a_reference - _direct)} carry it inside a composite reference to another "
    f"session-scoped table ({', '.join(sorted(_in_a_reference - _direct))})"
)
print(
    f"      {len(scoped)} of {len(T)} core and analysis tables are session-scoped; "
    f"{len(set(T) - scoped)} are not ({', '.join(sorted(set(T) - scoped))}); "
    f"{len(scoped - carries)} reach core.sessions without carrying the column"
)

# Part 02 §8.3, §2.3.2. What a discriminator declares, checked where the meta-schema cannot: the
# enum constrains the value but not that a discriminator has one, and `resolves` on anything else
# is a declaration that decides nothing.
_disc = []
for _r, _t in ALL.items():
    _names = {_c["name"] for _c in _t["columns"]}
    for _c in _t["columns"]:
        _is = _c.get("role") == "discriminator"
        if _is and "resolves" not in _c:
            _disc.append(f"{_r}.{_c['name']}: a discriminator declares no resolves")
        for _field in ("resolves", "discriminates"):
            if _field in _c and not _is:
                _disc.append(
                    f"{_r}.{_c['name']}: {_field} on a {_c.get('role')}, not a discriminator"
                )
        # A paired value lives in the named table's key space, so it is an identifier here too.
        if (_paired := _c.get("discriminates")) is not None and _paired not in _names:
            _disc.append(
                f"{_r}.{_c['name']}: discriminates {_paired}, which is not a column here"
            )
check("a discriminator declares what it resolves to", sorted(_disc))

# Part 02 §8.3. Three resolution shapes and only one was declared: `discriminates` separates a paired
# value from the other two, leaving by-position and shared-key indistinguishable, so `generate`
# read every discriminator without a paired value as shared-key and emitted Part 02 §8.3's reverse
# check for it. `positions_in` is the declaration that was missing.
_position = []
for _r, _t in ALL.items():
    _names = {_c["name"] for _c in _t["columns"]}
    for _c in _t["columns"]:
        if (_in := _c.get("positions_in")) is None:
            continue
        if _c.get("role") != "discriminator":
            _position.append(
                f"{_r}.{_c['name']}: positions_in on a {_c.get('role')}, not a discriminator"
            )
        if _in not in _names:
            _position.append(
                f"{_r}.{_c['name']}: positions_in names {_in}, which is not a column here"
            )
        if "discriminates" in _c:
            _position.append(
                f"{_r}.{_c['name']}: declares both positions_in and discriminates, "
                "which are different resolution shapes"
            )
check(
    "a by-position discriminator names the column holding its position column (Part 02 §8.3)",
    sorted(_position),
)

# Part 02 §8.3: a discriminator may sit on the table whose rows it specialises, or one declared
# reference away. Where it is away, `discriminates_via` names the *referencing* column as
# `resource.column` -- a reference carries no identifier of its own, so there is nothing else to
# name, and naming the referencing side settles the direction by construction.
_via = []
for _r, _t in ALL.items():
    for _c in _t["columns"]:
        if (_path := _c.get("discriminates_via")) is None:
            continue
        if _c.get("role") != "discriminator":
            _via.append(
                f"{_r}.{_c['name']}: declares discriminates_via and is not a discriminator"
            )
            continue
        _parts = _path.split(".")
        if len(_parts) != 3:
            _via.append(
                f"{_r}.{_c['name']}: discriminates_via {_path} is not a resource.column"
            )
            continue
        _from, _col = f"{_parts[0]}.{_parts[1]}", _parts[2]
        if _from not in ALL:
            _via.append(
                f"{_r}.{_c['name']}: discriminates_via names no resource {_from}"
            )
        elif not any(
            _col in ref["columns"] and ref["resource"] == _r
            for ref in ALL[_from]["references"]
        ):
            _via.append(
                f"{_r}.{_c['name']}: {_from}.{_col} is no declared reference to {_r}"
            )
check("a discriminator away from its rows names the reference", sorted(_via))

# Part 02 §8.3. A paired value is a string, and not by accident: one column resolves against
# several kinds, and an assigned key is matched by its `*_name` where a carried one is matched by
# the number itself, so the union it joins mixes types by construction.
check(
    "a paired value is a string",
    sorted(
        f"{_r}.{_c['discriminates']} is declared "
        f"{next(x for x in _t['columns'] if x['name'] == _c['discriminates'])['type']}"
        for _r, _t in ALL.items()
        for _c in _t["columns"]
        if _c.get("discriminates")
        and any(
            x["name"] == _c["discriminates"] and x["type"] != "string"
            for x in _t["columns"]
        )
    ),
)

# Part 02 §8.3: a paired value holds one identifier, so it can only name a resource whose key is one
# column. Reported rather than enforced -- the kind vocabulary is open (Part 02 §8.3), so what this can
# say is which resources are namable at all, which is otherwise found by a check quietly matching
# no branch.
NAMABLE = {
    _r: _t["primary_key"][0]
    for _r, _t in ALL.items()
    if _t.get("primary_key") and len(_t["primary_key"]) == 1
}
# Part 02 §8.3: which column a paired value matches follows from the key's identity, so the split
# is a property of the registry and is reported rather than rediscovered per consumer.
_by_name = {
    _r
    for _r, _k in NAMABLE.items()
    if next(c for c in ALL[_r]["columns"] if c["name"] == _k).get("identity")
    == "assigned"
    and any(c["name"] == _k.removesuffix("_id") + "_name" for c in ALL[_r]["columns"])
}
_core = {_r for _r in NAMABLE if _r in T}
print(
    f"      {len(_core)} of {len(T)} core resources have a single-column key "
    f"({len(NAMABLE)} of {len(ALL)} with extensions); "
    f"{len(_by_name & _core)} of those resolve by name, {len(_core - _by_name)} by key"
)
# A single-column key is necessary and not sufficient. An assigned identifier a table does not
# *own* -- it is exported through a reference, so R53 §2.3.1 puts the name on the owner -- has no
# column a value written before the build could match, so the resource is simply not namable.
# vr_foraging.sessions is the instance: its session_id belongs to core.sessions.
_unnamable = sorted(
    _r
    for _r, _k in NAMABLE.items()
    if _r not in _by_name
    and next(c for c in ALL[_r]["columns"] if c["name"] == _k).get("identity")
    == "assigned"
)
for _r in _unnamable:
    print(
        f"      note  {_r} has a single-column key but no name to match, so a scope cannot name it"
    )


# Part 02 §8.4: a declared unit or clock source must resolve. Structural -- decidable from the
# registry with no packet in hand, which is where this format puts a check it can make without
# data. The point is that a wrong `clock_from` converts ticks on the wrong clock silently.
def _resolves(resource, spec, value):
    """Whether a same-table column name or a one-hop `resource.column` resolves. Returns why not."""
    parts = value.split(".")
    if len(parts) == 1:
        if value not in {c["name"] for c in spec["columns"]}:
            return f"{resource} has no column {value}"
        return None
    target, column = f"{parts[0]}.{parts[1]}", parts[2]
    if target not in ALL:
        return f"{value} names no resource"
    if not any(ref["resource"] == target for ref in spec["references"]):
        return f"{resource} declares no reference to {target}, so the hop is not one this table can make"
    if column not in {c["name"] for c in ALL[target]["columns"]}:
        return f"{target} has no column {column}"
    return None


bad_context = []
for _r, _t in ALL.items():
    for _c in _t["columns"]:
        for _field in ("unit_from", "clock_from"):
            if _field in _c and (_why := _resolves(_r, _t, _c[_field])):
                bad_context.append(f"{_r}.{_c['name']} {_field}: {_why}")
        if "clock_from" in _c and _c.get("role") != "coordinate":
            bad_context.append(
                f"{_r}.{_c['name']}: clock_from on a {_c.get('role')}, not a coordinate"
            )
        if "unit" in _c and "unit_from" in _c:
            bad_context.append(f"{_r}.{_c['name']}: declares both unit and unit_from")
check("a declared unit or clock source resolves", sorted(bad_context))

# A vendored schema is a build artifact (see `build.py`'s VENDORED), so a copy that disagrees
# means the build was not run. Checked here because this is what one runs after touching the
# registry, and because a stale copy has three times been reported as a hundred findings about
# the data rather than one about the copy.
from build import VENDORED

stale = []
for _schema, _consumer in VENDORED.items():
    if not _consumer.parent.is_dir():
        continue
    if not _consumer.exists():
        stale.append(f"{_consumer.relative_to(HERE.parent)} is absent; run build.py")
    elif _consumer.read_text() != (HERE / _schema).read_text():
        stale.append(
            f"{_consumer.relative_to(HERE.parent)} differs from {_schema}; run build.py"
        )
check("every vendored schema matches its source", stale)

# The same argument one level up: a count restated in prose goes stale, and this one did --
# 33 tables against 34, 51 rules against 61, and two rules revisions had removed.
import render

_readme = (HERE / "README.md").read_text()
check(
    "README's generated regions are current",
    []
    if render.fill(_readme, render.regions(REG)) == _readme
    else ["README.md is stale; run build.py"],
)

# Part 02 §9.2: the registry validates against its published meta-schema.
try:
    import jsonschema

    meta = json.loads((HERE / "registry.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(meta)
    errs = list(jsonschema.Draft202012Validator(meta).iter_errors(REG))
    check(
        "registry validates against its meta-schema",
        [f"{list(e.path)[:4]}: {e.message[:60]}" for e in errs],
    )
    validator = jsonschema.Draft202012Validator(meta)
    check(
        "every extension validates against the same meta-schema",
        [
            f"{_id}: {list(e.path)[:4]} {e.message[:50]}"
            for _id, _doc in EXT.items()
            for e in validator.iter_errors(_doc)
        ],
    )
    manifest = json.loads((HERE / "manifest.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(manifest)
    check("manifest schema is valid JSON Schema", [])
    # Part 04 §5.5's sidecar is specified the way the manifest is, so it is checked the way the
    # manifest is: valid JSON Schema here, vendored by build.py, compared by the loop above.
    _sources = json.loads((HERE / "sources.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(_sources)
    check("source resolution schema is valid JSON Schema", [])
    _example = HERE / "sources.example.json"
    check(
        "the example resolution document validates against it",
        [
            f"{list(e.path)[:4]} {e.message[:60]}"
            for e in jsonschema.Draft202012Validator(_sources).iter_errors(
                json.loads(_example.read_text())
            )
        ]
        if _example.exists()
        else [],
    )
    # Part 03 §11.5's declaration document, checked the way the two above are: valid JSON Schema
    # here, vendored by build.py, and an example that must still satisfy it.
    _adapter = json.loads((HERE / "adapter.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(_adapter)
    check("adapter declaration schema is valid JSON Schema", [])
    _declared = HERE / "adapter.example.json"
    check(
        "the example adapter declaration validates against it",
        [
            f"{list(e.path)[:4]} {e.message[:60]}"
            for e in jsonschema.Draft202012Validator(_adapter).iter_errors(
                json.loads(_declared.read_text())
            )
        ]
        if _declared.exists()
        else [],
    )
    # Part 03 §11.3's resource document, checked as the three above are.
    _resources = json.loads((HERE / "resources.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(_resources)
    check("resource document schema is valid JSON Schema", [])
    _referenced = HERE / "resources.example.json"
    check(
        "the example resource document validates against it",
        [
            f"{list(e.path)[:4]} {e.message[:60]}"
            for e in jsonschema.Draft202012Validator(_resources).iter_errors(
                json.loads(_referenced.read_text())
            )
        ]
        if _referenced.exists()
        else [],
    )
    # The prototype argues that the format drives the tooling, which is worth nothing if its
    # own input is a document the format rejects. It drifted 16 errors out of conformance
    # unnoticed -- 13 columns with no `role` after R48, two tables with no `rules`.
    _proto = HERE.parent / "prototype/registry-codegen/registry.json"
    check(
        "the registry-codegen prototype's document validates against the meta-schema",
        [
            f"{list(e.path)[:4]} {e.message[:60]}"
            for e in validator.iter_errors(json.loads(_proto.read_text()))
        ]
        if _proto.exists()
        else [],
    )
except ImportError:
    print("skip  schema validation (jsonschema not available)")

# Every rule must be valid SQL naming real columns. Empty tables built from the registry
# validate syntax and identifiers without needing a packet.
DDL = {
    "string": "VARCHAR",
    "int32": "INTEGER",
    "int64": "BIGINT",
    "float32": "FLOAT",
    "float64": "DOUBLE",
    "bool": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMPTZ",
    "json_string": "VARCHAR",
}
try:
    import duckdb

    con = duckdb.connect()
    for n, t_ in ALL.items():
        cols = ", ".join(f'"{c["name"]}" {DDL[c["type"]]}' for c in t_["columns"])
        con.sql(f"CREATE TABLE {n.replace('.', '_')} ({cols})")
    con.sql(
        "CREATE TABLE manifest_sessions (session_id VARCHAR)"
    )  # supplied by the shim
    broken = []
    for n, t_ in ALL.items():
        for r in t_["rules"]:
            try:
                con.sql(r["sql"]).fetchall()
            except duckdb.Error as e:
                broken.append((r["id"], str(e).splitlines()[0][:70]))
    check("every Tier 2 rule is executable SQL", broken)
    print(
        f"      {sum(len(t_['rules']) for t_ in ALL.values())} rules executed against "
        f"{len(ALL)} empty tables"
    )
except ImportError:
    print("skip  rule execution (duckdb not available)")

print(
    f"\n{len(T)} tables, {sum(len(t['columns']) for t in T.values())} columns, "
    f"{sum(len(t['references']) for t in T.values())} references"
)
print(
    f"{len(EXT)} extensions: {len(EXT_T)} tables, "
    f"{sum(len(t['columns']) for t in EXT_T.values())} columns, "
    f"{sum(len(t['references']) for t in EXT_T.values())} references"
)
raise SystemExit(1 if fail else 0)

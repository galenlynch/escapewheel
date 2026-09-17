"""Check a registry document against the invariants that hold of any of them.

Part 09 §2 makes an extension a registry document in the same format as core's, so what is true of
a registry is true of one: a reference relates columns of the same type, role and identity, a
namespace prefixes its own tables, a discriminator declares what it resolves to. None of it is
visible to a packet's rows, so no SQL can see it (R12 §4) and no validation run against a built
packet reports it.

This lives here rather than in the repository's own `registry/check.py` because an author outside
that repository has the same document and the same question, and had no way to ask it: a draft was
sound or not, and the answer arrived when a build refused it, or did not arrive. `check.py` imports
`structural` from here, so the invariants core is held to and the ones an extension is held to
cannot drift apart.

What is **not** here is the rest of `check.py`: the R9 §2 ledger, the `derived_from` bookkeeping,
the rule-expansion round trip and the vendored-schema comparison are all facts about this
repository's build rather than about a document, and an author has no use for them.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: R2 §4's type vocabulary. A spelling outside it is a column no reader can be asked to decode.
VOCAB = {"string", "int32", "int64", "float32", "float64", "bool", "date",
         "timestamp", "json_string"}

#: Part 02 §8.4. A UCUM code is printable ASCII without spaces; an annotation in curly braces is one
#: and is dimensionless. This rejects prose that was declared as a unit rather than parsing the
#: grammar.
_UCUM = re.compile(r"[!-~]+")

#: The meta-schema a registry document declares itself written in (Part 02 §9.2), vendored beside this
#: module by the registry build.
SCHEMA = Path(__file__).resolve().parent / "schemas" / "registry.schema.json"


@dataclass(frozen=True)
class Finding:
    """One invariant's result: what was checked, and what broke it.

    Every invariant returns one of these whether or not it held, so a caller can report which ran
    rather than only which failed. An invariant nothing exercised and one nothing broke are the
    same line in a report and different facts about a document.
    """

    label: str
    offenders: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        """Whether the document satisfies this invariant."""
        return not self.offenders

    def __str__(self) -> str:
        """Render the label, the count, and the first few offenders, as a person reads a report."""
        if self.passed:
            return self.label
        shown = ", ".join(self.offenders[:4])
        more = f", +{len(self.offenders) - 4} more" if len(self.offenders) > 4 else ""
        return f"{self.label} ({len(self.offenders)}): {shown}{more}"


def structural(
    tables: Mapping[str, Any], universe: Mapping[str, Any], *, is_core: bool = False,
) -> list[Finding]:
    """Return every invariant these tables break, as findings.

    `universe` is what a reference may resolve against: core's own tables for core, and core's
    plus the extension's own for an extension. Part 09 §2 makes the direction one-way and §4 declines
    dependency resolution, so an extension reaching another extension's table is not a reference
    a packet can be relied on to satisfy.
    """
    found: list[Finding] = []

    def c_(label: str, bad: Iterable[Any], fmt: Callable[[Any], str] = str) -> None:
        found.append(Finding(label, tuple(fmt(b) for b in bad)))

    cols = {n: {c["name"]: c for c in t["columns"]} for n, t in tables.items()}
    ucols = {n: {c["name"]: c for c in t["columns"]} for n, t in universe.items()}
    c_("every table declares a primary key", [n for n, t in tables.items() if t["primary_key"] is None])
    c_("every column type is in R2 §4's vocabulary",
       [(n, c["name"], c["type"]) for n, t in tables.items() for c in t["columns"]
        if c["type"] not in VOCAB])
    c_("no required column is json_string",
       [(n, c["name"]) for n, t in tables.items() for c in t["columns"]
        if c["type"] == "json_string" and c["presence"] != "optional"])
    c_("no nested type spellings survived",
       [(n, c["name"], c["type"]) for n, t in tables.items() for c in t["columns"]
        if any(k in c["type"] for k in ("list", "struct", "map"))])
    c_("primary key columns exist",
       [(n, k) for n, t in tables.items() for k in (t["primary_key"] or []) if k not in cols[n]])
    c_("primary key columns are required",
       [(n, k) for n, t in tables.items() for k in (t["primary_key"] or [])
        if k in cols[n] and cols[n][k]["presence"] != "required"])
    # Part 03 §5.3's override names columns, and a revision that narrows a key leaves them behind:
    # `aind_unit_qc` kept sorting by two columns R81 had removed, which no packet could satisfy
    # and no rule could see, because a sort is physical and SQL cannot read it (R12 §4).
    c_("sort columns exist",
       [(n, k) for n, t in tables.items() for k in (t.get("sort") or []) if k not in cols[n]])
    c_("reference targets exist",
       [(n, r["resource"]) for n, t in tables.items() for r in t["references"]
        if r["resource"] not in universe])
    c_("reference source columns exist",
       [(n, c) for n, t in tables.items() for r in t["references"] for c in r["columns"]
        if c not in cols[n]])
    c_("reference target columns exist",
       [(n, r["resource"], c) for n, t in tables.items() for r in t["references"]
        if r["resource"] in universe for c in r["resource_columns"] if c not in ucols[r["resource"]]])
    c_("reference arity matches",
       [(n, r["resource"]) for n, t in tables.items() for r in t["references"]
        if len(r["columns"]) != len(r["resource_columns"])])
    # Part 02 §7. A join is on values, so two columns of different types resolve to each other not
    # at all -- `string` "7" and `int32` 7 are not one value, and nothing else here compares them.
    # R53 §2.1 is the case: it made every identifier `int32` where all 110 had been `string`, and
    # an extension still declaring `string` matched on role, on identity and on target, which is
    # every other thing this file asks of a reference.
    types = {(n, c["name"]): c["type"] for n, t in universe.items() for c in t["columns"]}
    c_("a reference relates columns of the same type",
       [(n, a, types.get((n, a)), r["resource"], b, types.get((r["resource"], b)))
        for n, t in tables.items() for r in t["references"]
        for a, b in zip(r["columns"], r["resource_columns"])
        if types.get((n, a)) != types.get((r["resource"], b))])
    # Part 02 §7. A structural index may also be a foreign-key component, so a client converting one
    # side and not the other would break the join. Both sides sharing a role is what makes
    # converting every structural_index column join-preserving by construction.
    role = {(n, c["name"]): c["role"] for n, t in universe.items() for c in t["columns"]}
    # Part 02 §8.3 exempts one pair: a shared-key column carrying a discriminator's value is `data`
    # where the column it references is the `discriminator`. Nothing converts either side, so
    # Part 02 §7's reason does not reach it.
    c_("a reference relates columns of the same role",
       [(n, a, r["resource"], b) for n, t in tables.items() for r in t["references"]
        for a, b in zip(r["columns"], r["resource_columns"])
        if role.get((n, a)) != role.get((r["resource"], b))
        and (role.get((n, a)), role.get((r["resource"], b))) != ("data", "discriminator")])
    # R53 §2.3 with Part 02 §7's reasoning: `number` resolves an assigned identifier through its
    # target's map and coerces a carried one, so a reference across the two numbers each side
    # differently and resolves to nothing. Decidable here, and invisible until a packet is built.
    identity = {(n, c["name"]): c.get("identity") for n, t in universe.items() for c in t["columns"]}
    c_("a reference relates columns of the same identity",
       [(n, a, r["resource"], b) for n, t in tables.items() for r in t["references"]
        for a, b in zip(r["columns"], r["resource_columns"])
        if role.get((n, a)) == "identifier" and identity.get((n, a)) != identity.get((r["resource"], b))])
    # A convention of this registry rather than a conformance requirement, so no revision mandates
    # it and Part 02 states no column order at all (CONTRIBUTING.md §4). `build.py` emits it for core; an
    # extension is a registry document in the same format (Part 09 §2) and nothing regenerates one,
    # which is the case this check exists for.
    c_("a table carrying session_id leads with it",
       [n for n, t in tables.items()
        if "session_id" in cols[n] and t["columns"][0]["name"] != "session_id"])
    # Part 02 §8.4 resolves a `coordinate` against its own row's `clock_id`, so a reader who has found a
    # tick needs the clock next to it. Twelve of the thirteen tables carrying one already do that;
    # `core.units` did not, because R96 §3.2 added the column beside what R96 §3.1 had just added.
    # A `clock_id` in the primary key leads for that reason instead, and a table with no coordinate
    # has nothing to sit beside -- both fall out of the condition rather than needing a list.
    _clocked = []
    for n, t in tables.items():
        names = [c["name"] for c in t["columns"]]
        coords = {c["name"] for c in t["columns"] if c["role"] == "coordinate"}
        if "clock_id" not in names or not coords or "clock_id" in (t["primary_key"] or []):
            continue
        k = names.index("clock_id")
        if not ({names[k - 1] if k else None, names[k + 1] if k + 1 < len(names) else None} & coords):
            _clocked.append((n, sorted(coords)))
    c_("a clock_id outside the key sits beside a coordinate it interprets", _clocked,
       lambda b: f"{b[0]}: clock_id interprets {b[1]} and sits by neither")
    c_("source labels are strings",
       [(n, c["name"], c["type"]) for n, t in tables.items() for c in t["columns"]
        if c["name"].endswith("_label") and c["type"] != "string"])
    # Part 02 §8.6. Which tables declare `metadata` is bounded at both ends by the primary key, and
    # both bounds are decidable here with no packet in hand. A key holding an identifier of its
    # own -- one not part of a declared reference -- makes the row a thing, which may carry what
    # its source said about it; a key made entirely of other tables' identifiers makes the row a
    # relationship, and nothing can be said about one that is not a fact about an end. Between
    # them the declaration is a judgement and nothing is checked.
    #
    # `build.py` emits the column from the key for core, so this fails only on an extension, which
    # nothing regenerates -- which is the case it exists for.
    own_key = {n: [k for k in (t["primary_key"] or [])
                   if cols[n].get(k, {}).get("role") == "identifier"
                   and k not in {c for r in t["references"] for c in r["columns"]}]
               for n, t in tables.items()}
    # The band reads *declared references*, so a table that forgets one lands here rather than in
    # the check that would name the real defect: drop `core.unit_quality_labels`' session reference
    # and `session_id` stops counting as referenced, which reads as an identifier of the table's own
    # and reports a missing `metadata` column. Adding one satisfies this and leaves the foreign key
    # undeclared, so the message says which reading to check first.
    c_("a table keyed by an identifier of its own declares `metadata` (Part 02 §8.6)",
       [n for n, t in tables.items() if own_key[n] and "metadata" not in cols[n]],
       lambda n: f"{n} owes one, its key holding {own_key[n]}; where such a column should be part "
                 f"of a reference, the undeclared reference is the defect and not the column")
    c_("a table keyed only by other tables' identifiers declares no `metadata` (Part 02 §8.6)",
       [n for n, t in tables.items() if t["primary_key"] and not own_key[n] and "metadata" in cols[n]
        and all(k in {c for r in t["references"] for c in r["columns"]} for k in t["primary_key"])])
    # Part 02 §8.6 again: Part 02 §10.2's check matches a bare column name, which is sound only while every
    # column called `metadata` is optional.
    # Part 02 §8.3: Part 01 §3.17 makes this standard name no instruments, so a device's kind-specific
    # facts live in an extension's table and never in core. A core table keyed beginning
    # `device_id` would be that table, whatever it was called.
    if is_core:  # a detail table keyed on `device_id` is what an extension is for
        c_("no core table but `core.devices` is keyed beginning `device_id` (Part 02 §8.3)",
           [n for n, t in tables.items()
            if n != "core.devices" and t["primary_key"] and t["primary_key"][0] == "device_id"],
           lambda n: f"{n} is shaped like a device detail table, which an extension declares (Part 09 §2)")
    c_("every `metadata` column is optional (Part 02 §8.6)",
       [n for n, t in tables.items()
        if "metadata" in cols[n] and cols[n]["metadata"]["presence"] != "optional"])

    # ---- what a column says about its values (Part 02 §9.3) ---------------------------------------
    # Part 02 §9.3 made open the default, so nothing distinguished a column deliberately left open
    # from one nobody had classified, and the marker rode on a column rather than on the
    # vocabulary -- `coordinate_frame` open on one table and undeclared on the other.
    _strings = [(n, c) for n, t in tables.items() for c in t["columns"] if c["type"] == "string"]
    c_("every string column but a discriminator declares a vocabulary (Part 02 §9.3)",
       [(n, c["name"]) for n, c in _strings
        if c["role"] != "discriminator" and "vocabulary" not in c])
    c_("a discriminator declares no vocabulary (Part 02 §9.3)",
       [(n, c["name"]) for n, c in _strings
        if c["role"] == "discriminator" and "vocabulary" in c],
       lambda x: f"{x[0]}.{x[1]}: Part 02 §8.3 fixes the value space to the declared resource IDs")
    c_("no column of another type declares one (Part 02 §9.3)",
       [(n, c["name"]) for n, t in tables.items() for c in t["columns"]
        if c["type"] != "string" and "vocabulary" in c])
    c_("`closed` holds exactly where `enum` does (Part 02 §9.3)",
       [(n, c["name"]) for n, c in _strings
        if (c.get("vocabulary") == "closed") != ("enum" in c)])
    c_("`reserved_values` appears only under `open` (R101 §3.4)",
       [(n, c["name"]) for n, c in _strings
        if "reserved_values" in c and c.get("vocabulary") != "open"])
    c_("an authority declares a name and an absolute URI (Part 02 §9.3)",
       [(n, c["name"], a) for n, t in tables.items() for c in t["columns"]
        for a in c.get("authority", [])
        if not (a.get("name") and str(a.get("uri", "")).startswith(("http://", "https://")))])
    c_("a declared unit is a UCUM code (Part 02 §8.4)",
       [(n, c["name"], c["unit"]) for n, t in tables.items() for c in t["columns"]
        if c.get("unit") and not _UCUM.fullmatch(c["unit"])],
       lambda x: f"{x[0]}.{x[1]} declares {x[2]!r}; an annotation in curly braces is a UCUM unit "
                 f"and is dimensionless, which is what a packet-relative quantity is")
    c_("an open column carries a description (R101 §3.5)",
       [(n, c["name"]) for n, c in _strings
        if c.get("vocabulary") == "open" and not c.get("description")])
    # §3.6: the drift caught mechanically. A name declared two ways in two tables is what
    # §2.3 measured on `coordinate_frame`, `activity_type` and the eight unit columns.
    _by_name: dict[str, set] = {}
    for n, c in _strings:
        if "vocabulary" in c:
            _by_name.setdefault(c["name"], set()).add(
                (c["vocabulary"],
                 tuple((a["name"], a["uri"]) for a in c.get("authority", ()))))
    c_("one column name carries one vocabulary and one authority (Part 02 §9.3)",
       sorted(k for k, v in _by_name.items() if len(v) > 1))

    # R107 §3.6. A description restating a field is a second statement of the same fact that
    # nothing compared, and six had drifted from the declaration beside them. Reaches four of the
    # five fields exactly; an authority's name in prose is prose, so §3.1 binds the writer there.
    # Capitalised, because "Calibrated open time" and "onto the closed set" are the ordinary words.
    _CLAIM = re.compile(r"(?<![A-Za-z])(Open|Closed|Free)(?![A-Za-z])")
    _restated = []
    for n, t in tables.items():
        for c in t["columns"]:
            desc, said = c.get("description", ""), []
            if _CLAIM.search(desc):
                said.append("names a vocabulary")
            if c.get("resolves") and f"resolves: {c['resolves']}" in desc:
                said.append("quotes `resolves`")
            # A value repeated with no meaning beside it restates the field; `band` states what
            # each of its reserved values means, which is a fact no field carries (Part 02 §3).
            if c.get("enum") and all(f"`{v}`" in desc for v in c["enum"]):
                said.append("lists its `enum`")
            if said:
                _restated.append(f"{n}.{c['name']}: {', '.join(said)}")
    c_("a description restates no field the column declares (Part 02 §3)", sorted(_restated))
    return found


def against_schema(document: Any) -> list[Finding]:
    """Check the document against Part 02 §9.2's meta-schema, where `jsonschema` is installed.

    Reports nothing at all where it is not, rather than a passing invariant: the schema fixes the
    document's shape and `structural` checks what the shape cannot say, so an author without the
    optional dependency still gets the half that finds real defects, and is not told that a check
    which never ran held.
    """
    try:
        import jsonschema
    except ImportError:
        return []
    schema = json.loads(SCHEMA.read_text())
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(document), key=lambda e: list(e.path))
    return [Finding("the document satisfies its meta-schema (Part 02 §9.2)",
                    tuple(f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors))]


#: What `extends` must name: an extension is written against the logical standard, not a profile
#: and not a packet (R17 §5).
LOGICAL_STANDARD = "escapewheel-logical-v0.1"


def declarations(document: Any, name: str | None = None) -> list[Finding]:
    """Check what an extension declares about itself, which `structural` does not look at.

    These hold of an extension and not of core, so they sit apart from the invariants both are
    held to: its tables carry its namespace, it extends the logical standard, and it names the
    meta-schema it is written in, which R57 §4 makes worth carrying precisely because it is
    verifiable offline against the schema in hand.

    Parameters
    ----------
    document : Mapping
        The extension's registry document.
    name : str, optional
        What the document is filed as, without its suffix. Where given, `extension_id` must match
        it: two documents disagreeing about which is which is a collision nothing else catches.
    """
    declared = document.get("extension_id")
    meta = json.loads(SCHEMA.read_text()).get("$id")
    found = [
        Finding("an extension's tables carry its own namespace (Part 09 §2)",
                tuple(n for n in document.get("tables", {}) if not n.startswith(f"{declared}."))),
        Finding(f"the document extends {LOGICAL_STANDARD} (R17 §5)",
                () if document.get("extends") == LOGICAL_STANDARD else (f"extends {document.get('extends')!r}",)),
        Finding("the document names this meta-schema (R57 §4)",
                () if document.get("$schema") == meta else (f"declares {document.get('$schema', 'none')!r}",)),
    ]
    if name is not None:
        found.append(Finding("the document's name is its `extension_id`",
                             () if declared == name else (f"filed as {name!r}, declares {declared!r}",)))
    return found


def check_extension(document: Any, core: Any, *, name: str | None = None) -> list[Finding]:
    """Every invariant an extension document is held to, against the core registry it extends.

    A reference may resolve against core's tables or the extension's own and no further: Part 09 §2
    makes the direction one-way and §4 declines dependency resolution, so an extension reaching
    another extension's table is not a reference a packet can be relied on to satisfy.

    Parameters
    ----------
    document : Mapping
        The extension's registry document.
    core : Mapping
        The core registry it extends, which a packet embeds.
    name : str, optional
        What the document is filed as, without its suffix; passed through to :func:`declarations`.

    Returns
    -------
    list of Finding
        One per invariant checked, in the order they ran; `Finding.passed` says which held.
    """
    tables = document.get("tables", {})
    return (against_schema(document)
            + declarations(document, name)
            + structural(tables, dict(core.get("tables", {})) | dict(tables)))

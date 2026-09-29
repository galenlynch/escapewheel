"""Check the built registry and its extensions against the current contract."""

import json
import re
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REG_BYTES = (HERE / "logical_schemas.json").read_bytes()
REG = json.loads(REG_BYTES)


def tables(document):
    """Project table contracts from the authoritative resource declarations."""
    return {
        name: declaration["table"]
        for name, declaration in document["resources"].items()
        if declaration["kind"] == "table"
    }


T = tables(REG)
# Part 09 §2: an extension is a registry document in R2's format, so the invariants that hold of a
# registry hold of it. They are checked here for the same reason core's are -- a naming
# convention or an unparseable rule is a property of the document, which no packet's rows can
# show and no SQL can see (R12 §4).
EXT_PATHS = {f.stem: f for f in sorted((HERE / "extensions").glob("*.json"))}
EXT = {name: json.loads(path.read_bytes()) for name, path in EXT_PATHS.items()}
EXT_T = {n: t for doc in EXT.values() for n, t in tables(doc).items()}
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
# Namespaces beyond core exist from Part 00 §3.2; match any <namespace>.<table> line.
expected = {
    l.strip()
    for l in ledger.splitlines()
    if re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", l.strip())
}
check("table set matches the Part 02 ledger", expected ^ set(T))
# Part 02 §9.4 defines one complete result for core and extension registry documents. This
# repository check consumes that result rather than maintaining another invariant subset.
sys.path.insert(0, str(HERE))
from escapewheel_validator.registry_document import (
    CheckedRegistryContext,
    check_registry_context_bytes,
)


def _registry_result(name, data, core: CheckedRegistryContext | None = None):
    """Require one repository registry to complete the incorporated contract."""
    context = check_registry_context_bytes(data, core=core)
    result = context.result
    check(
        f"{name} registry document is valid",
        [
            f"{phase.phase}: {outcome.id} at {outcome.instance or '<root>'}: "
            f"{outcome.detail or outcome.reason or outcome.state}"
            for phase in result.phases
            for outcome in phase.outcomes
        ]
        if result.state != "valid"
        else [],
    )
    return context


_core_context = _registry_result("core", REG_BYTES)
for _id, _path in EXT_PATHS.items():
    _registry_result(_id, _path.read_bytes(), _core_context)

META_ID = json.loads((HERE / "registry.schema.json").read_text())["$id"]
check(
    "every shipped registry names the current meta-schema",
    [f"logical_schemas: {REG.get('$schema', 'declares none')}"]
    if REG.get("$schema") != META_ID
    else [
        f"{name}: {document.get('$schema', 'declares none')}"
        for name, document in EXT.items()
        if document.get("$schema") != META_ID
    ],
)
check(
    "registry meta-schema identity is 0.9.0",
    [] if META_ID == "https://escapewheel.org/schemas/registry/0.9.0" else [META_ID],
)
check(
    "core registry version is 0.11.0",
    [] if REG.get("registry_version") == "0.11.0" else [REG.get("registry_version")],
)
check(
    "every shipped registry selects the incorporated rule language",
    [
        name
        for name, document in {"core": REG, **EXT}.items()
        if document.get("rule_language") != "escapewheel-rule-sql-v0.2"
    ],
)

# Part 03 incorporates the physical-profile descriptor. Its reusable schema owns local shape;
# this generic checker owns cross-member, cross-artifact, and anchor invariants without embedding
# the current descriptor's assignments.
sys.path.insert(0, str(HERE.parent / "escapewheel-reader/src"))
from escapewheel_reader.profile import check_physical_profile

_profile_schema = json.loads((HERE / "physical_profile.schema.json").read_text())
_profile = json.loads(
    (HERE / "physical_profiles/escapewheel-portable-v0.1.json").read_text()
)
_registry_schema = json.loads((HERE / "registry.schema.json").read_text())
check(
    "physical profile satisfies its schema and generic invariants",
    check_physical_profile(
        _profile,
        _profile_schema,
        logical_kinds=_registry_schema["$defs"]["resource"]["properties"]["kind"][
            "enum"
        ],
        logical_standard=REG["logical_standard_version"],
        part_text=(
            HERE.parent / "escapewheel_poc_docs_v0.2/03_portable_physical_profile.md"
        ).read_text(),
    ),
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

# A committed document an edit bypassed its source to reach, or a source edited without
# rebuilding, is caught here as well as by `verify.py`'s regeneration.
sys.path.insert(0, str(HERE))
import assemble
from canonical import dumps

check(
    "every registry document is what its source assembles to",
    [
        str(out.relative_to(HERE))
        for directory, out in assemble.sources().items()
        if dumps(assemble.assemble(directory)) != out.read_text()
    ]
    + sorted(
        str(path.relative_to(HERE))
        for path in (HERE / "extensions").glob("*.json")
        if path not in assemble.sources().values()
    ),
)

_history_cleanup = subprocess.run(
    [
        sys.executable,
        str(HERE.parent / "conformance/history-cleanup/probe.py"),
    ],
    capture_output=True,
    text=True,
    check=False,
)
check(
    "history cleanup preserves declarations and rules",
    []
    if _history_cleanup.returncode == 0
    else (_history_cleanup.stdout + _history_cleanup.stderr).splitlines(),
)
# Column order is a convention of this repository's registries rather than a conformance
# requirement (CONTRIBUTING.md §4), so nothing but this holds it.
check(
    "a table carrying session_id leads with it",
    [
        n
        for n, t in ALL.items()
        if any(c["name"] == "session_id" for c in t["columns"])
        and t["columns"][0]["name"] != "session_id"
    ],
)
check(
    "a table carrying metadata ends with it",
    [
        n
        for n, t in ALL.items()
        if any(c["name"] == "metadata" for c in t["columns"])
        and t["columns"][-1]["name"] != "metadata"
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
    "core.array_assets.resource_id": "Part 02 §2.6: packet identity is a carried string before row numbering",
    "analysis.array_assets.resource_id": "as core.array_assets.resource_id",
    "core.media_assets.resource_id": "as core.array_assets.resource_id",
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
    # Part 03 §6.3: `_kind` reads as a category and every column carrying it holds one -- an
    # interval's kind, a run's scope kind. This holds the table whose rows an axis's positions stand
    # for, and R48 §3 measured that a role says what a name cannot, which is why R55 added the role.
    "core.array_dimensions.coordinate_resource": "names the table whose rows the axis's positions stand for, not a kind of thing (Part 03 §6.3)",
    "analysis.array_dimensions.coordinate_resource": "as core.array_dimensions.coordinate_resource",
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
# column a value written before the build could match, so no string paired value can name it.
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

# Part 04's field tables and Part 03's delivery schema are projections of the incorporated
# manifest schema, so a hand edit to either, or a schema change nobody rebuilt, is a defect.
from build import delivery_schema, fill_manifest_tables

_manifest_schema = json.loads((HERE / "manifest.schema.json").read_text())
_part04 = HERE.parent / "escapewheel_poc_docs_v0.2/04_packet_catalog.md"
check(
    "Part 04's field tables project the manifest schema",
    []
    if fill_manifest_tables(_part04.read_text(), _manifest_schema) == _part04.read_text()
    else ["04_packet_catalog.md is stale; run build.py"],
)
check(
    "the delivery schema is the manifest entry without build-supplied members",
    []
    if json.loads((HERE / "resources.schema.json").read_text())
    == delivery_schema(_manifest_schema)
    else ["resources.schema.json is stale; run build.py"],
)

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
    _format = jsonschema.FormatChecker()
    errs = list(
        jsonschema.Draft202012Validator(meta, format_checker=_format).iter_errors(REG)
    )
    check(
        "registry validates against its meta-schema",
        [f"{list(e.path)[:4]}: {e.message[:60]}" for e in errs],
    )
    validator = jsonschema.Draft202012Validator(meta, format_checker=_format)
    _history_cases = []
    for _label, _mutate in (
        (
            "root derived_from",
            lambda document: document.update(
                {"derived_from": {"specification": "02", "revisions": []}}
            ),
        ),
        (
            "table since",
            lambda document: next(iter(tables(document).values())).update(
                {"since": "R1"}
            ),
        ),
        (
            "column since",
            lambda document: next(iter(tables(document).values()))["columns"][0].update(
                {"since": "R1"}
            ),
        ),
    ):
        _case = json.loads(json.dumps(REG))
        _mutate(_case)
        if not list(validator.iter_errors(_case)):
            _history_cases.append(_label)
    check("removed registry history fields are rejected", _history_cases)
    check(
        "every extension validates against the same meta-schema",
        [
            f"{_id}: {list(e.path)[:4]} {e.message[:50]}"
            for _id, _doc in EXT.items()
            for e in validator.iter_errors(_doc)
        ],
    )
    _contract_schema = json.loads((HERE / "registry_contract.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(_contract_schema)
    _contract = json.loads(
        (
            HERE / "registry_contracts/escapewheel-registry-contract-v0.7.json"
        ).read_text()
    )
    _contract_errors = list(
        jsonschema.Draft202012Validator(
            _contract_schema, format_checker=_format
        ).iter_errors(_contract)
    )
    check(
        "the incorporated registry contract validates against its schema",
        [f"{list(e.path)[:4]} {e.message[:60]}" for e in _contract_errors],
    )
    _invariant_ids = [entry["id"] for entry in _contract["invariants"]]
    check(
        "registry contract invariant IDs are unique",
        [item for item, count in Counter(_invariant_ids).items() if count > 1],
    )
    _parts = "\n".join(
        path.read_text()
        for path in sorted(
            (HERE.parent / "escapewheel_poc_docs_v0.2").glob("[0-9][0-9]_*.md")
        )
    )
    check(
        "every registry contract anchor resolves uniquely in the numbered specification",
        [
            anchor
            for entry in _contract["invariants"]
            for anchor in entry["anchors"]
            if _parts.count(f'id="{anchor}"') != 1
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
    # Part 04 §5.5 lets a source name be any string an entry's `source` can hold.
    check(
        "a resolution document naming a source with a space validates",
        [
            e.message[:60]
            for e in jsonschema.Draft202012Validator(_sources).iter_errors(
                {
                    "sources_standard_version": "escapewheel-sources-v0.1",
                    "sources": {"lab archive 2026": {"uri": "s3://bucket/prefix"}},
                }
            )
        ],
    )
    # Part 12 §7's declaration document, checked the way the two above are: valid JSON Schema
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
    # Every member is required and `protocols` names at least one, so each variant must fail.
    _complete = json.loads(_declared.read_text())
    _variants = {f"without {member}": {k: v for k, v in _complete.items() if k != member}
                 for member in _adapter["required"]}
    _variants["with empty protocols"] = {**_complete, "protocols": []}
    _variants["with a repeated protocol"] = {**_complete, "protocols": ["stream-v0.1"] * 2}
    check(
        "an adapter declaration missing a member or naming no protocol fails",
        [
            name
            for name, variant in _variants.items()
            if jsonschema.Draft202012Validator(_adapter).is_valid(variant)
        ],
    )
    # Part 05 §3.1's recipe, checked as the three above are; the example is TOML, validated in
    # its decoded form as a build validates one.
    _recipe = json.loads((HERE / "recipe.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(_recipe)
    check("recipe schema is valid JSON Schema", [])
    _recipe_example = HERE / "recipe.example.toml"
    check(
        "the example recipe validates against it",
        [
            f"{list(e.path)[:4]} {e.message[:60]}"
            for e in jsonschema.Draft202012Validator(_recipe).iter_errors(
                tomllib.loads(_recipe_example.read_text())
            )
        ]
        if _recipe_example.exists()
        else [],
    )
    # Part 12 §5's resource document, checked as the three above are.
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
    _language_schema = json.loads((HERE / "rule_language.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(_language_schema)
    _language = json.loads(
        (HERE / "rule_languages/escapewheel-rule-sql-v0.2.json").read_text()
    )
    check(
        "the incorporated rule-language profile validates against its schema",
        [
            f"{list(e.path)[:4]} {e.message[:60]}"
            for e in jsonschema.Draft202012Validator(_language_schema).iter_errors(
                _language
            )
        ],
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
    from escapewheel_validator.rule_language import RuleProfileError, check_rule

    con = duckdb.connect()
    con.sql("SET TimeZone = 'UTC'")
    for namespace in sorted({name.split(".", 1)[0] for name in ALL}):
        con.sql(f"CREATE SCHEMA {namespace}")
    for n, t_ in ALL.items():
        cols = ", ".join(f'"{c["name"]}" {DDL[c["type"]]}' for c in t_["columns"])
        con.sql(f"CREATE TABLE {n} ({cols})")
    broken = []
    for document in [REG, *EXT.values()]:
        for t_ in tables(document).values():
            for r in t_["rules"]:
                try:
                    check_rule(r["sql"], document, core_resources=REG)
                    con.sql(r["sql"]).fetchall()
                except (RuleProfileError, duckdb.Error) as e:
                    broken.append((r["id"], str(e).splitlines()[0][:70]))
    check("every Tier 2 rule conforms and executes against empty tables", broken)
    print(
        f"      {sum(len(t_['rules']) for t_ in ALL.values())} rules checked against "
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

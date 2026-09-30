"""Check the core registry and the tree's other artifacts against the current contract.

Everything read here lies in the tree. The checks over extensions, over Git history and over the
frozen v0.1 documents, and executing the Tier 2 rules, lie outside it.
"""

import json
import tomllib
from collections import Counter
from pathlib import Path

import jsonschema

import assemble
import conventions
import render
from build import delivery_schema, fill_manifest_tables
from canonical import dumps
from checkers.descriptor import check_physical_profile, override_errors
from checkers.registry_document import check_registry_context_bytes
from checkers.rule_language import RuleProfileError, check_rule

HERE = Path(__file__).resolve().parent
TREE = HERE.parent
ARTIFACTS = TREE / "artifacts"
INFORMATIVE = TREE / "informative"
PARTS = TREE / "parts"
REG_BYTES = (ARTIFACTS / "logical_schemas.json").read_bytes()
REG = json.loads(REG_BYTES)


def tables(document):
    """Project table contracts from the authoritative resource declarations."""
    return {
        name: declaration["table"]
        for name, declaration in document["resources"].items()
        if declaration["kind"] == "table"
    }


T = tables(REG)
fail = []


def check(label, bad, fmt=str):
    bad = list(bad)
    print(f"{'FAIL' if bad else 'ok  '}  {label}" + (f"  ({len(bad)})" if bad else ""))
    for b in bad[:4]:
        print(f"          {fmt(b)}")
    if bad:
        fail.append(label)


# Part 02 §9.4 defines one complete result for a registry document, which this consumes rather
# than maintaining another invariant subset.
_result = check_registry_context_bytes(REG_BYTES).result
check(
    "core registry document is valid",
    [
        f"{phase.phase}: {outcome.id} at {outcome.instance or '<root>'}: "
        f"{outcome.detail or outcome.reason or outcome.state}"
        for phase in _result.phases
        for outcome in phase.outcomes
    ]
    if _result.state != "valid"
    else [],
)

META_ID = json.loads((ARTIFACTS / "registry.schema.json").read_text())["$id"]
check(
    "the core registry names the current meta-schema",
    [] if REG.get("$schema") == META_ID else [REG.get("$schema", "declares none")],
)
check(
    "registry meta-schema identity is 0.11.0",
    [] if META_ID == "https://escapewheel.org/schemas/registry/0.11.0" else [META_ID],
)
check(
    "core registry version is 0.14.0",
    [] if REG.get("registry_version") == "0.14.0" else [REG.get("registry_version")],
)
check(
    "the core registry selects the incorporated rule language",
    [] if REG.get("rule_language") == "escapewheel-rule-sql-v0.2" else [REG.get("rule_language")],
)

# Part 03 incorporates the physical-profile descriptor. Its reusable schema owns local shape;
# this generic checker owns cross-member, cross-artifact, and anchor invariants without embedding
# the current descriptor's assignments.
_profile_schema = json.loads((ARTIFACTS / "physical_profile.schema.json").read_text())
_profile = json.loads((ARTIFACTS / "physical_profiles/escapewheel-portable-v0.1.json").read_text())
_registry_schema = json.loads((ARTIFACTS / "registry.schema.json").read_text())
check(
    "physical profile satisfies its schema and generic invariants",
    check_physical_profile(
        _profile,
        _profile_schema,
        logical_kinds=_registry_schema["$defs"]["resource"]["properties"]["kind"][
            "enum"
        ],
        logical_standard=REG["logical_standard_version"],
        part_text=(PARTS / "03_portable_physical_profile.md").read_text(),
    ),
)

# Part 03 §5.4: each override settles its key by adjacency against the core registry, with no
# packet in hand. An extension table takes its key's order and is not checked here.
_table_interface = _profile["interfaces"][_profile["kind_interfaces"]["table"]]
check(
    "every overriding order is consistent with the core registry",
    [
        f"{resource}: {error}"
        for resource, order in _table_interface.get("overriding_orders", {}).items()
        for error in override_errors(order, T.get(resource))
    ],
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
check(
    "the core registry is what its source assembles to",
    [
        str(out.relative_to(TREE))
        for directory, out in assemble.sources().items()
        if dumps(assemble.assemble(directory)) != out.read_text()
    ],
)

for _label, _bad in conventions.convention_failures(
    T, conventions.NAMING_EXCEPTIONS, conventions.NAMES_A_KIND
).items():
    check(_label, _bad)
_named = conventions.name_columns(T)
print(
    f"      {len(conventions.NAMING)} conventions over {sum(len(t['columns']) for t in T.values())} columns, "
    f"{len(conventions.NAMING_EXCEPTIONS)} declared exceptions; "
    f"{sum(_named.values())} name columns must be unique within a packet (Part 02 §8.2), "
    f"{len(conventions.NAMES_A_KIND)} name a kind of thing"
)


# Part 02 §8.3: a paired value holds one identifier, so it can only name a resource whose key is one
# column. Reported rather than enforced -- the kind vocabulary is open (Part 02 §8.3), so what this can
# say is which resources are namable at all, which is otherwise found by a check quietly matching
# no branch.
NAMABLE = {
    _r: _t["primary_key"][0]
    for _r, _t in T.items()
    if _t.get("primary_key") and len(_t["primary_key"]) == 1
}
# Part 02 §8.3: which column a paired value matches follows from the key's identity, so the split
# is a property of the registry and is reported rather than rediscovered per consumer.
_by_name = {
    _r
    for _r, _k in NAMABLE.items()
    if next(c for c in T[_r]["columns"] if c["name"] == _k).get("identity")
    == "assigned"
    and any(c["name"] == _k.removesuffix("_id") + "_name" for c in T[_r]["columns"])
}
print(
    f"      {len(NAMABLE)} of {len(T)} core resources have a single-column key; "
    f"{len(_by_name)} of those resolve by name, {len(NAMABLE) - len(_by_name)} by key"
)
# A single-column key is necessary and not sufficient. An assigned identifier a table does not
# *own* -- it is exported through a reference, so R53 §2.3.1 puts the name on the owner -- has no
# column a value written before the build could match, so no string paired value can name it.
_unnamable = sorted(
    _r
    for _r, _k in NAMABLE.items()
    if _r not in _by_name
    and next(c for c in T[_r]["columns"] if c["name"] == _k).get("identity")
    == "assigned"
)
for _r in _unnamable:
    print(
        f"      note  {_r} has a single-column key but no name to match, so a scope cannot name it"
    )


# Part 04's field tables and Part 03's delivery schema are projections of the incorporated
# manifest schema, so a hand edit to either, or a schema change nobody rebuilt, is a defect.
_manifest_schema = json.loads((ARTIFACTS / "manifest.schema.json").read_text())
_part04 = PARTS / "04_packet_catalog.md"
check(
    "Part 04's field tables project the manifest schema",
    []
    if fill_manifest_tables(_part04.read_text(), _manifest_schema) == _part04.read_text()
    else ["04_packet_catalog.md is stale; run build.py"],
)
check(
    "the delivery schema is the manifest entry without build-supplied members",
    []
    if json.loads((ARTIFACTS / "resources.schema.json").read_text())
    == delivery_schema(_manifest_schema)
    else ["resources.schema.json is stale; run build.py"],
)

# The same argument one level up: a count restated in prose goes stale, and this one did --
# 33 tables against 34, 51 rules against 61, and two rules revisions had removed.
_readme = (TREE / "source/README.md").read_text()
check(
    "the source guide's generated regions are current",
    []
    if render.fill(_readme, render.regions(REG)) == _readme
    else ["source/README.md is stale; run build.py"],
)

# Part 02 §9.2: the registry validates against its published meta-schema.
meta = json.loads((ARTIFACTS / "registry.schema.json").read_text())
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
_contract_schema = json.loads((ARTIFACTS / "registry_contract.schema.json").read_text())
jsonschema.Draft202012Validator.check_schema(_contract_schema)
_contract = json.loads(
    (
        ARTIFACTS / "registry_contracts/escapewheel-registry-contract-v0.9.json"
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
_parts = "\n".join(path.read_text() for path in sorted(PARTS.glob("[0-9][0-9]_*.md")))
check(
    "every registry contract anchor resolves uniquely in the numbered specification",
    [
        anchor
        for entry in _contract["invariants"]
        for anchor in entry["anchors"]
        if _parts.count(f'id="{anchor}"') != 1
    ],
)
manifest = json.loads((ARTIFACTS / "manifest.schema.json").read_text())
jsonschema.Draft202012Validator.check_schema(manifest)
check("manifest schema is valid JSON Schema", [])
# Part 04 §5.5's sidecar is specified the way the manifest is, so it is checked the way the
# manifest is: valid JSON Schema here, compared by the loop above.
_sources = json.loads((ARTIFACTS / "sources.schema.json").read_text())
jsonschema.Draft202012Validator.check_schema(_sources)
check("source resolution schema is valid JSON Schema", [])
_example = INFORMATIVE / "sources.example.json"
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
# here, and an example that must still satisfy it.
_adapter = json.loads((ARTIFACTS / "adapter.schema.json").read_text())
jsonschema.Draft202012Validator.check_schema(_adapter)
check("adapter declaration schema is valid JSON Schema", [])
_declared = INFORMATIVE / "adapter.example.json"
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
_recipe = json.loads((ARTIFACTS / "recipe.schema.json").read_text())
jsonschema.Draft202012Validator.check_schema(_recipe)
check("recipe schema is valid JSON Schema", [])
_recipe_example = INFORMATIVE / "recipe.example.toml"
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
_resources = json.loads((ARTIFACTS / "resources.schema.json").read_text())
jsonschema.Draft202012Validator.check_schema(_resources)
check("resource document schema is valid JSON Schema", [])
_referenced = INFORMATIVE / "resources.example.json"
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
_language_schema = json.loads((ARTIFACTS / "rule_language.schema.json").read_text())
jsonschema.Draft202012Validator.check_schema(_language_schema)
_language = json.loads(
    (ARTIFACTS / "rule_languages/escapewheel-rule-sql-v0.2.json").read_text()
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

# Every core rule is in the portable profile. Executing the rules needs an engine, which the tree
# does not declare, so their execution is checked outside it.
_broken = []
for _table in T.values():
    for _rule in _table["rules"]:
        try:
            check_rule(_rule["sql"], REG)
        except RuleProfileError as e:
            _broken.append((_rule["id"], str(e).splitlines()[0][:70]))
check("every core Tier 2 rule is in the portable profile", _broken)

print(
    f"\n{len(T)} tables, {sum(len(t['columns']) for t in T.values())} columns, "
    f"{sum(len(t['references']) for t in T.values())} references, "
    f"{sum(len(t['rules']) for t in T.values())} rules"
)
raise SystemExit(1 if fail else 0)

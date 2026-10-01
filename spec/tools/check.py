"""Check the core registry and the tree's other artifacts against the current contract.

Everything read here lies in the tree. The checks over extensions, over Git history and over the
frozen v0.1 documents, and executing the Tier 2 rules, lie outside it.
"""

import json
import sys
import tomllib
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path

import jsonschema

import assemble
import conventions
import render
from build import delivery_schema, fill_manifest_tables, fill_physical_profile
from canonical import dumps
from checkers.descriptor import check_physical_profile, override_errors
from checkers.registry_document import check_registry_context_bytes
from checkers.rule_language import RuleProfileError, check_rule
from specdoc import GenerationError

HERE = Path(__file__).resolve().parent
TREE = HERE.parent
ARTIFACTS = TREE / "artifacts"
INFORMATIVE = TREE / "informative"
PARTS = TREE / "parts"


def tables(document):
    """Project table contracts from the authoritative resource declarations."""
    return {
        name: declaration["table"]
        for name, declaration in document["resources"].items()
        if declaration["kind"] == "table"
    }


class Checks:
    """Print each check's outcome and keep the labels of those that failed.

    An instance is called as `check(label, bad)`, the spelling `tools/facts.py` counts.
    """

    def __init__(self) -> None:
        self.failed: list[str] = []

    def __call__(self, label: str, bad: Iterable, fmt: Callable[[object], str] = str) -> None:
        """Report one check, which fails where `bad` yields anything."""
        bad = list(bad)
        print(f"{'FAIL' if bad else 'ok  '}  {label}" + (f"  ({len(bad)})" if bad else ""))
        for b in bad[:4]:
            print(f"          {fmt(b)}")
        if bad:
            self.failed.append(label)


def _json(path: Path):
    return json.loads(path.read_text())


def _schema_errors(schema: dict, instance, format_checker=None) -> list[str]:
    """Return each schema violation of `instance`, with where it lies."""
    validator = jsonschema.Draft202012Validator(schema, format_checker=format_checker)
    return [f"{list(e.path)[:4]} {e.message[:60]}" for e in validator.iter_errors(instance)]


def identity_checks(check: Checks, registry_bytes: bytes, registry: dict) -> None:
    """Check the registry's complete contract result and the identifiers it records."""
    # Part 02 §9.4 defines one complete result for a registry document, which this consumes rather
    # than maintaining another invariant subset. The schema its portable form is held to is
    # itself checked as a schema.
    jsonschema.Draft202012Validator.check_schema(_json(ARTIFACTS / "registry_result.schema.json"))
    result = check_registry_context_bytes(registry_bytes).result
    check(
        "core registry document is valid",
        [
            f"{phase.phase}: {outcome.id} at {outcome.instance or '<root>'}: "
            f"{outcome.detail or outcome.reason or outcome.state}"
            for phase in result.phases
            for outcome in phase.outcomes
        ]
        if result.state != "valid"
        else [],
    )

    meta_id = _json(ARTIFACTS / "registry.schema.json")["$id"]
    check(
        "the core registry names the current meta-schema",
        [] if registry.get("$schema") == meta_id else [registry.get("$schema", "declares none")],
    )
    check(
        "registry meta-schema identity is 0.11.0",
        [] if meta_id == "https://escapewheel.org/schemas/registry/0.11.0" else [meta_id],
    )
    check(
        "core registry version is 0.14.0",
        [] if registry.get("registry_version") == "0.14.0" else [registry.get("registry_version")],
    )
    check(
        "the core registry selects the incorporated rule language",
        [] if registry.get("rule_language") == "escapewheel-rule-sql-v0.2" else [registry.get("rule_language")],
    )


def profile_checks(check: Checks, registry: dict, core: dict) -> None:
    """Check the physical-profile descriptor and the orders it overrides."""
    # Part 03 incorporates the physical-profile descriptor. Its reusable schema owns local shape;
    # this generic checker owns cross-member, cross-artifact, and anchor invariants without
    # embedding the current descriptor's assignments.
    profile_schema = _json(ARTIFACTS / "physical_profile.schema.json")
    jsonschema.Draft202012Validator.check_schema(profile_schema)
    profile = _json(ARTIFACTS / "physical_profiles/escapewheel-portable-v0.1.json")
    registry_schema = _json(ARTIFACTS / "registry.schema.json")
    check(
        "physical profile satisfies its schema and generic invariants",
        check_physical_profile(
            profile,
            profile_schema,
            logical_kinds=registry_schema["$defs"]["resource"]["properties"]["kind"]["enum"],
            logical_standard=registry["logical_standard_version"],
            part_text=(PARTS / "03_portable_physical_profile.md").read_text(),
        ),
    )

    # Part 03 §5.4: each override settles its key by adjacency against the core registry, with no
    # packet in hand. An extension table takes its key's order and is not checked here.
    table_interface = profile["interfaces"][profile["kind_interfaces"]["table"]]
    check(
        "every overriding order is consistent with the core registry",
        [
            f"{resource}: {error}"
            for resource, order in table_interface.get("overriding_orders", {}).items()
            for error in override_errors(order, core.get(resource))
        ],
    )


def source_checks(check: Checks, core: dict) -> None:
    """Check the table set and that the registry is what its source assembles to."""
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
            if n in core
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


def convention_checks(check: Checks, core: dict) -> None:
    """Check the authoring conventions and report which resources a paired value can name."""
    for label, bad in conventions.convention_failures(
        core, conventions.NAMING_EXCEPTIONS, conventions.NAMES_A_KIND
    ).items():
        check(label, bad)
    named = conventions.name_columns(core)
    print(
        f"      {len(conventions.NAMING)} conventions over {sum(len(t['columns']) for t in core.values())} columns, "
        f"{len(conventions.NAMING_EXCEPTIONS)} declared exceptions; "
        f"{sum(named.values())} name columns must be unique within a packet (Part 02 §8.2), "
        f"{len(conventions.NAMES_A_KIND)} name a kind of thing"
    )

    # Part 02 §8.3: a paired value holds one identifier, so it can only name a resource whose key
    # is one column. Reported rather than enforced: the kind vocabulary is open, so what this can
    # say is which resources are namable at all, which is otherwise found by a check quietly
    # matching no branch.
    namable = {r: t["primary_key"][0] for r, t in core.items() if t.get("primary_key") and len(t["primary_key"]) == 1}

    def key_column(resource: str) -> dict:
        return next(c for c in core[resource]["columns"] if c["name"] == namable[resource])

    # Which column a paired value matches follows from the key's identity, so the split is a
    # property of the registry and is reported rather than rediscovered per consumer.
    by_name = {
        r
        for r, k in namable.items()
        if key_column(r).get("identity") == "assigned"
        and any(c["name"] == k.removesuffix("_id") + "_name" for c in core[r]["columns"])
    }
    print(
        f"      {len(namable)} of {len(core)} core resources have a single-column key; "
        f"{len(by_name)} of those resolve by name, {len(namable) - len(by_name)} by key"
    )
    # A single-column key is necessary and not sufficient. An assigned identifier a table does not
    # *own* -- it is exported through a reference, so the name lies on the owner -- has no column a
    # value written before the build could match, so no string paired value can name it.
    unnamable = sorted(r for r in namable if r not in by_name and key_column(r).get("identity") == "assigned")
    for r in unnamable:
        print(f"      note  {r} has a single-column key but no name to match, so a scope cannot name it")


def projection_checks(check: Checks, registry: dict) -> None:
    """Check the generated regions and schema that project another artifact."""
    # Part 04's field tables and Part 03's delivery schema are projections of the incorporated
    # manifest schema, so a hand edit to either, or a schema change nobody rebuilt, is a defect.
    manifest_schema = _json(ARTIFACTS / "manifest.schema.json")
    part04 = (PARTS / "04_packet_catalog.md").read_text()
    check(
        "Part 04's field tables project the manifest schema",
        []
        if fill_manifest_tables(part04, manifest_schema) == part04
        else ["04_packet_catalog.md is stale; run build.py"],
    )
    check(
        "the delivery schema is the manifest entry without build-supplied members",
        []
        if _json(ARTIFACTS / "resources.schema.json") == delivery_schema(manifest_schema)
        else ["resources.schema.json is stale; run build.py"],
    )

    # Part 03's two tables project the profile descriptor the same way.
    part03 = (PARTS / "03_portable_physical_profile.md").read_text()
    profile = _json(ARTIFACTS / "physical_profiles/escapewheel-portable-v0.1.json")
    check(
        "Part 03's generated regions project the physical profile",
        []
        if fill_physical_profile(part03, profile) == part03
        else ["03_portable_physical_profile.md is stale; run build.py"],
    )

    listing = INFORMATIVE / "tables.md"
    check(
        "the rendered listing is what the registry renders to",
        []
        if listing.is_file() and render.render(registry) == listing.read_text()
        else ["informative/tables.md is stale; run build.py"],
    )

    # A count restated in prose goes stale, so the source guide's are generated and compared.
    readme = (TREE / "source/README.md").read_text()
    check(
        "the source guide's generated regions are current",
        [] if render.fill(readme, render.regions(registry)) == readme else ["source/README.md is stale; run build.py"],
    )


def schema_checks(check: Checks, registry: dict) -> None:
    """Check each incorporated schema, and each document or example a schema governs."""
    # Part 02 §9.2: the registry validates against its published meta-schema.
    meta = _json(ARTIFACTS / "registry.schema.json")
    jsonschema.Draft202012Validator.check_schema(meta)
    formats = jsonschema.FormatChecker()
    validator = jsonschema.Draft202012Validator(meta, format_checker=formats)
    check(
        "registry validates against its meta-schema",
        [f"{list(e.path)[:4]}: {e.message[:60]}" for e in validator.iter_errors(registry)],
    )
    accepted_history = []
    for label, mutate in (
        (
            "root derived_from",
            lambda document: document.update({"derived_from": {"specification": "02", "revisions": []}}),
        ),
        (
            "table since",
            lambda document: next(iter(tables(document).values())).update({"since": "R1"}),
        ),
        (
            "column since",
            lambda document: next(iter(tables(document).values()))["columns"][0].update({"since": "R1"}),
        ),
    ):
        case = json.loads(json.dumps(registry))
        mutate(case)
        if not list(validator.iter_errors(case)):
            accepted_history.append(label)
    check("removed registry history fields are rejected", accepted_history)

    contract_schema = _json(ARTIFACTS / "registry_contract.schema.json")
    jsonschema.Draft202012Validator.check_schema(contract_schema)
    contract = _json(ARTIFACTS / "registry_contracts/escapewheel-registry-contract-v0.9.json")
    check(
        "the incorporated registry contract validates against its schema",
        _schema_errors(contract_schema, contract, formats),
    )
    invariant_ids = [entry["id"] for entry in contract["invariants"]]
    check(
        "registry contract invariant IDs are unique",
        [item for item, count in Counter(invariant_ids).items() if count > 1],
    )
    parts = "\n".join(path.read_text() for path in sorted(PARTS.glob("[0-9][0-9]_*.md")))
    check(
        "every registry contract anchor resolves uniquely in the numbered specification",
        [
            anchor
            for entry in contract["invariants"]
            for anchor in entry["anchors"]
            if parts.count(f'id="{anchor}"') != 1
        ],
    )

    manifest = _json(ARTIFACTS / "manifest.schema.json")
    jsonschema.Draft202012Validator.check_schema(manifest)
    check("manifest schema is valid JSON Schema", [])
    # Part 04 §5.5's sidecar is specified the way the manifest is, so it is checked the way the
    # manifest is.
    sources = _json(ARTIFACTS / "sources.schema.json")
    jsonschema.Draft202012Validator.check_schema(sources)
    check("source resolution schema is valid JSON Schema", [])
    example = INFORMATIVE / "sources.example.json"
    check(
        "the example resolution document validates against it",
        _schema_errors(sources, _json(example)) if example.exists() else [],
    )
    # Part 04 §5.5 lets a source name be any string an entry's `source` can hold.
    check(
        "a resolution document naming a source with a space validates",
        [
            e.message[:60]
            for e in jsonschema.Draft202012Validator(sources).iter_errors(
                {
                    "sources_standard_version": "escapewheel-sources-v0.1",
                    "sources": {"lab archive 2026": {"uri": "s3://bucket/prefix"}},
                }
            )
        ],
    )
    # Part 12 §7's declaration document: valid JSON Schema, and an example that must satisfy it.
    adapter = _json(ARTIFACTS / "adapter.schema.json")
    jsonschema.Draft202012Validator.check_schema(adapter)
    check("adapter declaration schema is valid JSON Schema", [])
    declared = INFORMATIVE / "adapter.example.json"
    check(
        "the example adapter declaration validates against it",
        _schema_errors(adapter, _json(declared)) if declared.exists() else [],
    )
    # Every member is required and `protocols` names at least one, so each variant must fail.
    complete = _json(declared)
    variants = {
        f"without {member}": {k: v for k, v in complete.items() if k != member} for member in adapter["required"]
    }
    variants["with empty protocols"] = {**complete, "protocols": []}
    variants["with a repeated protocol"] = {**complete, "protocols": ["stream-v0.1"] * 2}
    check(
        "an adapter declaration missing a member or naming no protocol fails",
        [name for name, variant in variants.items() if jsonschema.Draft202012Validator(adapter).is_valid(variant)],
    )
    # Part 05 §3.1's recipe; the example is TOML, validated in its decoded form as a build
    # validates one.
    recipe = _json(ARTIFACTS / "recipe.schema.json")
    jsonschema.Draft202012Validator.check_schema(recipe)
    check("recipe schema is valid JSON Schema", [])
    recipe_example = INFORMATIVE / "recipe.example.toml"
    check(
        "the example recipe validates against it",
        _schema_errors(recipe, tomllib.loads(recipe_example.read_text())) if recipe_example.exists() else [],
    )
    # Part 12 §5's resource document.
    resources = _json(ARTIFACTS / "resources.schema.json")
    jsonschema.Draft202012Validator.check_schema(resources)
    check("resource document schema is valid JSON Schema", [])
    referenced = INFORMATIVE / "resources.example.json"
    check(
        "the example resource document validates against it",
        _schema_errors(resources, _json(referenced)) if referenced.exists() else [],
    )
    language_schema = _json(ARTIFACTS / "rule_language.schema.json")
    jsonschema.Draft202012Validator.check_schema(language_schema)
    language = _json(ARTIFACTS / "rule_languages/escapewheel-rule-sql-v0.2.json")
    check(
        "the incorporated rule-language profile validates against its schema",
        _schema_errors(language_schema, language),
    )


def rule_checks(check: Checks, registry: dict, core: dict) -> None:
    """Check every core rule against the portable profile.

    Executing the rules needs an engine, which the tree does not declare, so their execution is
    checked outside it.
    """
    broken = []
    for table in core.values():
        for rule in table["rules"]:
            try:
                check_rule(rule["sql"], registry)
            except RuleProfileError as e:
                broken.append((rule["id"], str(e).splitlines()[0][:70]))
    check("every core Tier 2 rule is in the portable profile", broken)


def main() -> int:
    """Run every check of the tree in order; return non-zero where any fails."""
    registry_bytes = (ARTIFACTS / "logical_schemas.json").read_bytes()
    registry = json.loads(registry_bytes)
    core = tables(registry)
    check = Checks()

    try:
        identity_checks(check, registry_bytes, registry)
        profile_checks(check, registry, core)
        source_checks(check, core)
        convention_checks(check, core)
        projection_checks(check, registry)
        schema_checks(check, registry)
        rule_checks(check, registry, core)
    except GenerationError as error:
        print(error, file=sys.stderr)
        return 1

    print(
        f"\n{len(core)} tables, {sum(len(t['columns']) for t in core.values())} columns, "
        f"{sum(len(t['references']) for t in core.values())} references, "
        f"{sum(len(t['rules']) for t in core.values())} rules"
    )
    return 1 if check.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

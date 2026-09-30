"""Build every generated artifact in the registry.

`assemble.py` writes each registry document from its TOML source, `render.py` renders the core
registry as Markdown, and this script refreshes Part 03's and Part 04's projections and the
delivery schema, then vendors each hand-written schema into the package that reads it. Every
output is committed and none is edited by hand.
"""

import json
from pathlib import Path

import assemble

HERE = Path(__file__).resolve().parent
OUT = HERE / "logical_schemas.json"

#: Where each hand-written schema is vendored. A wheel cannot read a file from another
#: distribution, so each carries a copy -- which makes the copy an output of this build.
VENDORED = {
    "registry_result.schema.json": HERE.parent
    / "escapewheel-validator/src/escapewheel_validator/schemas/registry_result.schema.json",
    "registry.schema.json": HERE.parent
    / "escapewheel-validator/src/escapewheel_validator/schemas/registry.schema.json",
    "registry_contract.schema.json": HERE.parent
    / "escapewheel-validator/src/escapewheel_validator/schemas/registry_contract.schema.json",
    "registry_contracts/escapewheel-registry-contract-v0.9.json": HERE.parent
    / "escapewheel-validator/src/escapewheel_validator/schemas/registry_contracts/escapewheel-registry-contract-v0.9.json",
    "rule_language.schema.json": HERE.parent
    / "escapewheel-validator/src/escapewheel_validator/schemas/rule_language.schema.json",
    "rule_languages/escapewheel-rule-sql-v0.2.json": HERE.parent
    / "escapewheel-validator/src/escapewheel_validator/schemas/escapewheel-rule-sql-v0.2.json",
    # The validator and the writer's publication gate apply the manifest schema; a reader does not.
    "manifest.schema.json": HERE.parent
    / "escapewheel-validator/src/escapewheel_validator/schemas/manifest.schema.json",
    "physical_profile.schema.json": HERE.parent
    / "escapewheel-reader/src/escapewheel_reader/schemas/physical_profile.schema.json",
    "physical_profiles/escapewheel-portable-v0.1.json": HERE.parent
    / "escapewheel-reader/src/escapewheel_reader/schemas/physical_profiles/escapewheel-portable-v0.1.json",
    "sources.schema.json": HERE.parent
    / "escapewheel-reader/src/escapewheel_reader/schemas/sources.schema.json",
    # A *build* reads an adapter's declaration (Part 12 §7), so this one vendors into the
    # writer where the other three go to whichever package reads them.
    "adapter.schema.json": HERE.parent
    / "escapewheel-writer/src/escapewheel_writer/schemas/adapter.schema.json",
    "resources.schema.json": HERE.parent
    / "escapewheel-writer/src/escapewheel_writer/schemas/resources.schema.json",
    "recipe.schema.json": HERE.parent
    / "escapewheel-writer/src/escapewheel_writer/schemas/recipe.schema.json",
}


def render_physical_profile() -> Path:
    """Refresh Part 03's informative kind-to-interface projection."""
    descriptor = json.loads(
        (HERE / "physical_profiles/escapewheel-portable-v0.1.json").read_text()
    )
    path = HERE.parent / "escapewheel_poc_docs_v0.2/03_portable_physical_profile.md"
    text = path.read_text()
    begin = "<!-- BEGIN GENERATED PHYSICAL PROFILE -->"
    end = "<!-- END GENERATED PHYSICAL PROFILE -->"
    rows = [begin, "| logical kind | generic interface |", "|---|---|"]
    rows.extend(
        f"| `{kind}` | {f'`{interface}`' if interface is not None else 'none'} |"
        for kind, interface in descriptor["kind_interfaces"].items()
    )
    projection = "\n".join([*rows, end])
    before, remainder = text.split(begin, 1)
    _, after = remainder.split(end, 1)
    path.write_text(before + projection + after)
    return path


#: Part 04's informative field tables, by region name, and the schema object each projects.
MANIFEST_TABLES = {
    "manifest": "#",
    "resource": "#/$defs/resource",
    "registry": "#/$defs/registry",
    "validation": "#/$defs/validation",
}

#: How a table names a member whose value is another closed object of the schema.
_DEF_LABELS = {
    "resource": "resource entry (§4.1)",
    "registry": "registry descriptor (§8)",
    "validation": "validation block (§9)",
    "member": "member (§5.4)",
    "digest": "digest (§4.3)",
    "replaced_packet": "replaced packet (§3)",
}


def _resolve(schema: dict, pointer: str) -> dict:
    node = schema
    for part in pointer.removeprefix("#").strip("/").split("/"):
        if part:
            node = node[part]
    return node


def _scalar(schema: dict, node: dict) -> dict:
    """Follow a `$ref` to a scalar definition, so its type and constraint are tabulated."""
    ref = node.get("$ref")
    if ref is None or ref.rsplit("/", 1)[-1] in _DEF_LABELS:
        return node
    return {**_resolve(schema, ref), **{k: v for k, v in node.items() if k != "$ref"}}


def _json_type(schema: dict, node: dict) -> str:
    ref = node.get("$ref")
    if ref is not None and ref.rsplit("/", 1)[-1] in _DEF_LABELS:
        return _DEF_LABELS[ref.rsplit("/", 1)[-1]]
    node = _scalar(schema, node)
    kind = node.get("type")
    if kind == "array":
        return f"array of {_json_type(schema, node['items'])}"
    if (
        kind == "object"
        and "additionalProperties" in node
        and node["additionalProperties"]
    ):
        return f"object of {_json_type(schema, node['additionalProperties'])}"
    return str(kind)


def _constraint(schema: dict, node: dict) -> str:
    node = _scalar(schema, node)
    said = []
    if "const" in node:
        said.append(f"`{node['const']}`")
    if "enum" in node:
        said.append("one of " + ", ".join(f"`{value}`" for value in node["enum"]))
    if "pattern" in node:
        said.append(f"pattern `{node['pattern']}`")
    if "format" in node:
        said.append(f"format `{node['format']}`")
    if node.get("minLength") == 1 or node.get("minItems") == 1:
        said.append("nonempty")
    if node.get("minProperties") == 1:
        said.append("at least one member")
    if "propertyNames" in node:
        said.append(f"member names match `{node['propertyNames']['pattern']}`")
    if node.get("uniqueItems"):
        said.append("unique items")
    if "minimum" in node:
        said.append(f"at least {node['minimum']}")
    if "exclusiveMinimum" in node:
        said.append(f"greater than {node['exclusiveMinimum']}")
    if node.get("type") == "array":
        item = _constraint(schema, node["items"])
        if item != "—" and "$ref" in node["items"]:
            said.append(f"each item {item}")
    return "; ".join(said) or "—"


def manifest_table(schema: dict, pointer: str) -> str:
    """One Part 04 field table: every member the schema object declares, in declaration order."""
    target = _resolve(schema, pointer)
    required = set(target.get("required", []))
    rows = ["| member | JSON type | required | constraint |", "|---|---|:---:|---|"]
    rows.extend(
        f"| `{name}` | {_json_type(schema, node)} | {'yes' if name in required else 'no'} | "
        # GFM ends a table cell at any unescaped pipe, a code span included.
        f"{_constraint(schema, node).replace('|', r'\|')} |"
        for name, node in target["properties"].items()
    )
    return "\n".join(rows)


def fill_manifest_tables(text: str, schema: dict) -> str:
    """Replace each generated Part 04 region with its projection of the manifest schema."""
    for region, pointer in MANIFEST_TABLES.items():
        begin = f"<!-- BEGIN GENERATED MANIFEST FIELDS: {region} -->"
        end = f"<!-- END GENERATED MANIFEST FIELDS: {region} -->"
        before, remainder = text.split(begin, 1)
        _, after = remainder.split(end, 1)
        text = (
            before + begin + "\n" + manifest_table(schema, pointer) + "\n" + end + after
        )
    return text


#: Members a build supplies when it merges a delivered entry, so a delivery carries neither.
BUILD_SUPPLIED = ("validation_state", "derived_from")


def delivery_schema(manifest: dict) -> dict:
    """Part 12 §5's resource document: the manifest entry without its build-supplied members.

    Generated so the two cannot define a shared member differently; every definition an entry
    reaches is copied from the manifest schema rather than restated.
    """
    entry = json.loads(json.dumps(manifest["$defs"]["resource"]))
    for name in BUILD_SUPPLIED:
        del entry["properties"][name]
    entry["required"] = [
        name for name in entry["required"] if name not in BUILD_SUPPLIED
    ]
    defs: dict = {}
    pending = [entry]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            ref = node.get("$ref", "")
            name = ref.rsplit("/", 1)[-1]
            if ref.startswith("#/$defs/") and name not in defs:
                defs[name] = manifest["$defs"][name]
                pending.append(defs[name])
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return {
        "$schema": manifest["$schema"],
        "$id": "https://escapewheel.org/schemas/resources/0.5.0",
        "title": "Escapewheel resource document",
        "description": (
            "Shape of the document an adapter delivers alongside its rows to describe the "
            "resources it references rather than writes (Part 12 §5). Generated from the "
            "manifest schema by registry/build.py: each entry is a manifest resource entry "
            "without the members a build supplies."
        ),
        "type": "object",
        "required": ["resources"],
        "additionalProperties": False,
        "properties": {
            "$schema": {
                "description": "This document's schema, by $id. Identity rather than a fetch instruction.",
                "type": "string",
            },
            "resources": {"type": "array", "items": {"$ref": "#/$defs/entry"}},
        },
        "$defs": {"entry": entry, **dict(sorted(defs.items()))},
    }


def render_manifest() -> list[Path]:
    """Refresh Part 04's field tables and the delivery schema from the manifest schema."""
    manifest = json.loads((HERE / "manifest.schema.json").read_text())
    part = HERE.parent / "escapewheel_poc_docs_v0.2/04_packet_catalog.md"
    part.write_text(fill_manifest_tables(part.read_text(), manifest))
    delivery = HERE / "resources.schema.json"
    delivery.write_text(json.dumps(delivery_schema(manifest), indent=2) + "\n")
    return [part, delivery]


if __name__ == "__main__":
    for path in assemble.main():
        print(f"wrote {path.relative_to(HERE)}")

    # Rendered here rather than by hand, so the readable form cannot drift from the content.
    # The README's counts go the same way: it claimed 33 tables and 51 rules against a registry
    # holding 34 and 61, and `check.py` now fails on a stale one.
    import render

    print(f"wrote {', '.join(p.name for p in render.main())}")
    print(f"wrote {render_physical_profile().relative_to(HERE.parent)}")
    print(
        f"wrote {', '.join(str(p.relative_to(HERE.parent)) for p in render_manifest())}"
    )

    # The two hand-written schemas are consumed by sibling distributions, which vendor them
    # because a wheel cannot read a file from another repository. A vendored copy is therefore a
    # *build artifact* and not a file to maintain: a stale one has broken every packet three
    # times -- R48, R53 and R56 -- each time reported as a hundred findings about the data rather
    # than one about the copy. Written here so the class of bug cannot recur, and compared by
    # `check.py` so a build nobody ran is still caught.
    for schema, consumer in VENDORED.items():
        consumer.parent.mkdir(parents=True, exist_ok=True)
        source = HERE / schema
        if not consumer.parent.is_dir():
            if consumer.parent.parent.is_dir():
                consumer.parent.mkdir()
            else:
                print(f"skip  {schema} -> {consumer} (sibling not present)")
                continue
        if consumer.exists() and consumer.read_text() == source.read_text():
            continue
        consumer.write_text(source.read_text())
        print(f"wrote {consumer.relative_to(HERE.parent)}")

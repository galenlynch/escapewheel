"""Build every generated file and region of the specification's tree.

`assemble.py` writes the core registry from its TOML source, `render.py` renders it as Markdown,
and this script refreshes Part 03's and Part 04's projections and the delivery schema. Every output
is committed and none is edited by hand. A package copies what it uses from the tree itself, so
nothing here writes outside it.

    python build.py            # write every output
    python build.py --check    # write nothing, and fail where an output is stale
"""

import argparse
import json
import sys
from pathlib import Path

import assemble
import render
from canonical import dumps
from specdoc import GenerationError

HERE = Path(__file__).resolve().parent
TREE = HERE.parent
ARTIFACTS = TREE / "artifacts"
PARTS = TREE / "parts"
PROFILE = ARTIFACTS / "physical_profiles/escapewheel-portable-v0.1.json"
MANIFEST = ARTIFACTS / "manifest.schema.json"
DELIVERY = ARTIFACTS / "resources.schema.json"
PART_03 = PARTS / "03_portable_physical_profile.md"
PART_04 = PARTS / "04_packet_catalog.md"


def _replace_region(text: str, name: str, rows: list[str]) -> str:
    begin, end = f"<!-- BEGIN GENERATED {name} -->", f"<!-- END GENERATED {name} -->"
    before, remainder = text.split(begin, 1)
    _, after = remainder.split(end, 1)
    return before + "\n".join([begin, *rows, end]) + after


def fill_physical_profile(text: str, descriptor: dict) -> str:
    """Replace Part 03's generated regions with their projections of the profile descriptor."""
    text = _replace_region(
        text,
        "PHYSICAL PROFILE",
        [
            "| logical kind | generic interface |",
            "|---|---|",
            *(
                f"| `{kind}` | {f'`{interface}`' if interface is not None else 'none'} |"
                for kind, interface in descriptor["kind_interfaces"].items()
            ),
        ],
    )
    tables = descriptor["interfaces"][descriptor["kind_interfaces"]["table"]]
    return _replace_region(
        text,
        "OVERRIDING ORDERS",
        [
            "| resource | order |",
            "|---|---|",
            *(
                f"| `{resource}` | `{', '.join(order)}` |"
                for resource, order in tables.get("overriding_orders", {}).items()
            ),
        ],
    )


def render_physical_profile() -> Path:
    """Refresh Part 03's kind-to-interface and overriding-order projections."""
    PART_03.write_text(fill_physical_profile(PART_03.read_text(), json.loads(PROFILE.read_text())))
    return PART_03


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
    if kind == "object" and "additionalProperties" in node and node["additionalProperties"]:
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
        text = before + begin + "\n" + manifest_table(schema, pointer) + "\n" + end + after
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
    entry["required"] = [name for name in entry["required"] if name not in BUILD_SUPPLIED]
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
            "manifest schema: each entry is a manifest resource entry "
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


def _delivery_text(manifest: dict) -> str:
    return json.dumps(delivery_schema(manifest), indent=2) + "\n"


def render_manifest() -> list[Path]:
    """Refresh Part 04's field tables and the delivery schema from the manifest schema."""
    manifest = json.loads(MANIFEST.read_text())
    PART_04.write_text(fill_manifest_tables(PART_04.read_text(), manifest))
    DELIVERY.write_text(_delivery_text(manifest))
    return [PART_04, DELIVERY]


def stale() -> list[Path]:
    """Return each file the build writes whose content it would change.

    Each output is compared with what its source yields now, so the listing and the source guide
    are judged against the registry the source assembles to rather than the committed one.
    """
    manifest = json.loads(MANIFEST.read_text())
    registries = {out: assemble.assemble(directory) for directory, out in assemble.sources().items()}
    expected = {out: dumps(document) for out, document in registries.items()}
    expected |= render.outputs(registries[render.REGISTRY])
    expected[PART_03] = fill_physical_profile(PART_03.read_text(), json.loads(PROFILE.read_text()))
    expected[PART_04] = fill_manifest_tables(PART_04.read_text(), manifest)
    expected[DELIVERY] = _delivery_text(manifest)
    return [path for path, text in expected.items() if not path.is_file() or path.read_text() != text]


def main(argv: list[str] | None = None) -> int:
    """Write every output, or with `--check` report each stale one and write nothing."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="write nothing, and fail where an output is stale")
    try:
        if parser.parse_args(argv).check:
            paths = stale()
            for path in paths:
                print(f"{path.relative_to(TREE)} is stale; run `python build.py`")
            if not paths:
                print("every file build.py writes is current")
            return 1 if paths else 0

        for path in assemble.main():
            print(f"wrote {path.relative_to(TREE)}")
        # Rendered here rather than by hand, so the readable form cannot drift from the content.
        print(f"wrote {', '.join(p.name for p in render.main())}")
        print(f"wrote {render_physical_profile().relative_to(TREE)}")
        print(f"wrote {', '.join(str(p.relative_to(TREE)) for p in render_manifest())}")
    except GenerationError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

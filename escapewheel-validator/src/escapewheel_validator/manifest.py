"""Manifest conformance before any declaration is used (Part 04 §10).

The `json`, `shape`, and `entries` phases need only the manifest's bytes, and the
`registry_binding` phase acquires each bound registry through its descriptor. Each phase reports
findings under Part 04 §10's check IDs; a finding in any of the first three stops evaluation, so a
later phase never indexes into a document an earlier one rejected.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from typing import Any

import jsonschema
from escapewheel_reader import Location, RegistryBinding, RegistryUnavailable
from escapewheel_reader.registries import acquire
from escapewheel_reader.uri import in_one_form

from .registry_document import CheckedRegistryContext, check_registry_context_bytes
from .stores import listing_digest

MANIFEST_FILENAME = "packet.json"


@dataclass(frozen=True)
class Issue:
    """One manifest finding, at `error` as every Part 04 §10 finding is."""

    check: str
    message: str
    rows: tuple[tuple[Any, ...], ...] = ()
    #: The registry a binding finding concerns, or None for a packet finding (Part 05 §9.5).
    registry: str | None = None


@dataclass
class Bound:
    """What the `registry_binding` phase established about the packet's registries."""

    #: Every acquired registry's checked context, by registry ID, whether or not it passed binding.
    contexts: dict[str, CheckedRegistryContext] = field(default_factory=dict)
    #: Registry IDs with no binding finding.
    passed: set[str] = field(default_factory=set)
    core_id: str | None = None

    def directs(self, registry_id: str) -> bool:
        """Whether this registry may direct packet checks (Part 05 §14.5)."""
        context = self.contexts.get(registry_id)
        return registry_id in self.passed and context is not None and context.result.state == "valid"

    @property
    def core(self) -> CheckedRegistryContext | None:
        """The core registry's context, where it may direct packet checks."""
        return None if self.core_id is None or not self.directs(self.core_id) else self.contexts[self.core_id]

    @property
    def extensions(self) -> dict[str, CheckedRegistryContext]:
        """The extension registries that may direct packet checks."""
        return {name: context for name, context in self.contexts.items() if name != self.core_id and self.directs(name)}


def manifest_schema() -> dict[str, Any]:
    """Load Part 04's incorporated manifest schema, as this distribution vendors it.

    Returns
    -------
    dict
        The parsed schema.
    """
    text = importlib_resources.files(__package__).joinpath("schemas/manifest.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def format_checker() -> jsonschema.FormatChecker:
    """Build a format checker that asserts `date-time`, as Part 04 §10 requires of a shape check.

    `jsonschema` registers `date-time` only where `rfc3339-validator` is importable and otherwise
    passes every value, so its absence is refused rather than silently weakening the check.
    """
    checker = jsonschema.FormatChecker()
    if "date-time" not in checker.checkers:
        raise RuntimeError("jsonschema cannot assert date-time; install rfc3339-validator")
    return checker


class _Object(dict[str, Any]):
    """A decoded object that remembers which member names it saw twice."""

    def __init__(self, pairs: list[tuple[str, Any]]) -> None:
        super().__init__(pairs)
        counts = Counter(name for name, _ in pairs)
        self.repeated = tuple(sorted(name for name, count in counts.items() if count > 1))


def _pointer(parts: Sequence[Any]) -> str:
    return "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in parts)


def _repeated(value: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[str, str]]:
    if isinstance(value, _Object):
        for name in value.repeated:
            yield _pointer(path), name
        for name, child in value.items():
            yield from _repeated(child, (*path, name))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _repeated(child, (*path, index))


def check_json(raw: bytes, issues: list[Issue]) -> Any:
    """Run the `json` phase: UTF-8 JSON under RFC 8259 with no repeated member.

    Returns
    -------
    Any
        The decoded manifest, or None where the phase found anything.
    """
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_Object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        issues.append(Issue("packet.manifest.invalid_json", f"the manifest is not UTF-8 JSON: {exc}"))
        return None
    repeated = list(_repeated(document))
    for where, name in repeated:
        issues.append(
            Issue(
                "packet.manifest.duplicate_member",
                f"{where or '<root>'} repeats member {name!r}",
                ((where, name),),
            )
        )
    return None if repeated else document


def check_shape(document: Any, issues: list[Issue]) -> bool:
    """Run the `shape` phase: the incorporated schema, with `date-time` asserted.

    Returns
    -------
    bool
        Whether the manifest satisfies the schema.
    """
    validator = jsonschema.Draft202012Validator(manifest_schema(), format_checker=format_checker())
    errors = sorted(validator.iter_errors(document), key=lambda e: (list(map(str, e.absolute_path)), e.message))
    for error in errors:
        instance = _pointer(list(error.absolute_path))
        schema = "#" + _pointer(list(error.absolute_schema_path))
        issues.append(
            Issue("packet.manifest.schema", f"{instance or '<root>'}: {error.message}", ((instance, schema),))
        )
    return not errors


def prefix_digest(members: Sequence[Mapping[str, Any]]) -> str:
    """Part 04 §4.3's value of a member list: SHA-256 of its compact JSON listing, sorted by key bytes."""
    return listing_digest((str(m["key"]), m["size_bytes"], str(m["digest"])) for m in members)


def check_entries(document: Mapping[str, Any], issues: list[Issue]) -> bool:
    """Run the `entries` phase: what a shape-valid manifest establishes about itself alone.

    Returns
    -------
    bool
        Whether the phase found nothing.
    """
    before = len(issues)
    resources: list[Mapping[str, Any]] = document["resources"]
    counts = Counter(entry["resource_id"] for entry in resources)
    for resource_id in sorted(name for name, count in counts.items() if count > 1):
        issues.append(Issue("packet.resource.id_unique", f"{resource_id}: {counts[resource_id]} entries share this ID"))
    for entry in resources:
        if entry.get("external") is not True and "digest" not in entry:
            issues.append(
                Issue(
                    "packet.resource.digest_missing",
                    f"{entry['resource_id']}: the packet owns this resource and records no digest (Part 04 §4.3)",
                )
            )
        if not in_one_form(entry["uri"]):
            issues.append(
                Issue(
                    "packet.resource.uri_form",
                    f"{entry['resource_id']}: uri {entry['uri']!r} is neither absolute nor a relative reference "
                    "in Part 03 §4's one form",
                    ((entry["resource_id"], entry["uri"]),),
                )
            )
        members = entry.get("members")
        if members is None:
            continue
        keys = Counter(member["key"] for member in members)
        for key in sorted(name for name, count in keys.items() if count > 1):
            issues.append(
                Issue("packet.resource.member_unique", f"{entry['resource_id']}: member {key!r} is listed twice")
            )
        total = sum(member["size_bytes"] for member in members)
        if "size_bytes" in entry and entry["size_bytes"] != total:
            issues.append(
                Issue(
                    "packet.resource.member_size",
                    f"{entry['resource_id']}: size_bytes {entry['size_bytes']} differs from its members' {total}",
                )
            )
        # The schema requires every member's digest where the entry records one.
        if "digest" in entry and prefix_digest(members) != entry["digest"]["value"]:
            issues.append(
                Issue(
                    "packet.resource.member_digest",
                    f"{entry['resource_id']}: digest is not the Part 04 §4.3 value of its member list",
                )
            )
    registries: Mapping[str, Mapping[str, Any]] = document["registries"]
    cores = sorted(name for name, descriptor in registries.items() if descriptor["role"] == "core")
    if len(cores) != 1:
        issues.append(
            Issue(
                "packet.registry.core_count",
                f"the manifest binds {len(cores)} core registries; exactly one is required",
                tuple((name,) for name in cores),
            )
        )
    paths = Counter(descriptor["path"] for descriptor in registries.values())
    for path in sorted(name for name, count in paths.items() if count > 1):
        issues.append(
            Issue(
                "packet.registry.path_unique",
                f"{path}: {paths[path]} registry descriptors share this path",
                tuple((name,) for name, descriptor in sorted(registries.items()) if descriptor["path"] == path),
            )
        )
    return len(issues) == before


def named_registries(raw: bytes) -> tuple[str, ...]:
    """Return the registry IDs a manifest's bytes name, read leniently since the phases may reject it.

    A registry withheld by an early-phase finding still has a verdict (Part 05 §9.5), so a report
    names every registry it can find, including in a manifest that fails `shape`.
    """
    try:
        document = json.loads(raw)
    except ValueError:
        return ()
    registries = document.get("registries") if isinstance(document, dict) else None
    return tuple(str(name) for name in registries) if isinstance(registries, dict) else ()


def check_manifest(raw: bytes, issues: list[Issue]) -> Mapping[str, Any] | None:
    """Run the `json`, `shape`, and `entries` phases, stopping at the first that finds anything.

    Returns
    -------
    Mapping or None
        The decoded manifest where all three passed.
    """
    document = check_json(raw, issues)
    if document is None or not check_shape(document, issues):
        return None
    shaped: Mapping[str, Any] = document  # the schema requires an object
    return shaped if check_entries(shaped, issues) else None


def _shape_valid(context: CheckedRegistryContext) -> bool:
    return any(phase.phase == "shape" and phase.state == "passed" for phase in context.result.phases)


def bind_registries(root: Location, document: Mapping[str, Any], issues: list[Issue]) -> Bound:
    """Run the `registry_binding` phase: acquire, digest, check, and compare every bound registry.

    Acquisition findings come first; only digest-matching bytes obtain a registry result, core's
    before any extension's so each extension is checked in core's context.
    """
    bound = Bound()
    bindings = {
        name: RegistryBinding(name, d["role"], d["version"], d["path"], d["sha256"])
        for name, d in document["registries"].items()
    }
    acquired: dict[str, bytes] = {}
    for name, binding in bindings.items():
        try:
            acquired[name] = acquire(root, binding)
        except RegistryUnavailable as exc:
            issues.append(Issue(f"packet.registry.{exc.reason}", str(exc), ((name, binding.path),), name))
    bound.core_id = next((name for name, binding in bindings.items() if binding.role == "core"), None)
    core_context = None
    if bound.core_id is not None and bound.core_id in acquired:
        core_context = check_registry_context_bytes(acquired[bound.core_id])
        bound.contexts[bound.core_id] = core_context
    for name in bindings:
        if name != bound.core_id and name in acquired:
            bound.contexts[name] = check_registry_context_bytes(acquired[name], core=core_context)
    for name, context in bound.contexts.items():
        binding = bindings[name]
        failed = False
        if _shape_valid(context):
            failed = _compare(name, binding, context.document, document, issues)
        if not failed:
            bound.passed.add(name)
    return bound


def _compare(
    name: str,
    binding: RegistryBinding,
    registry: Mapping[str, Any],
    manifest: Mapping[str, Any],
    issues: list[Issue],
) -> bool:
    """Part 04 §8's four comparisons between a descriptor and the document it binds."""
    found: list[Issue] = []
    if registry["registry_id"] != name:
        found.append(
            Issue("packet.registry.identity", f"{name}: the document's registry_id is {registry['registry_id']!r}")
        )
    role = "extension" if "extension_id" in registry else "core"
    if role != binding.role:
        found.append(Issue("packet.registry.role", f"{name}: bound as {binding.role}, but the document is {role}"))
    if registry["registry_version"] != binding.version:
        found.append(
            Issue(
                "packet.registry.version",
                f"{name}: bound as {binding.version}, but the document is {registry['registry_version']}",
            )
        )
    standards = ["logical_standard_version"] + (["semantic_standard_version"] if role == "core" else [])
    for member in standards:
        if registry.get(member) != manifest[member]:
            found.append(
                Issue(
                    "packet.registry.standard",
                    f"{name}: {member} {registry.get(member)!r} differs from the manifest's {manifest[member]!r}",
                )
            )
    issues.extend(Issue(i.check, i.message, ((name,),), name) for i in found)
    return bool(found)


__all__ = [
    "Bound",
    "Issue",
    "bind_registries",
    "check_manifest",
    "format_checker",
    "manifest_schema",
    "named_registries",
    "prefix_digest",
]

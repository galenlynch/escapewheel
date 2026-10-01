"""Manifest conformance before any declaration is used (Part 04 §10).

- :func:`check_manifest` -- the `json`, `shape` and `entries` phases, stopping at the first that
  finds anything.
- :func:`check_json`, :func:`check_shape`, :func:`check_entries` -- each of those phases alone.
- :func:`bind_registries` -- the `registry_binding` phase, returning what it established as a
  :class:`Bound`.
- :class:`Issue` -- one manifest finding, under Part 04 §10's check ID.
- :func:`confirm_replaced` -- each difference between a supplied packet and the `replaces` item
  it is read as.
- :func:`named_registries` -- the registry IDs a manifest's bytes name, read leniently.
- :func:`manifest_schema`, :func:`format_checker` -- the incorporated schema, and a format checker
  that asserts `date-time`.
- :func:`prefix_digest`, :func:`major` -- a member list's digest value, and a `packet_version`'s
  major version.
- :data:`MANIFEST_FILENAME` -- the manifest's name under a packet root.

The first three phases need only the manifest's bytes, and a finding in any of them stops
evaluation, so a later phase never indexes into a document an earlier one rejected.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

import jsonschema
from escapewheel_reader import Location, RegistryBinding, RegistryFault, RegistryUnavailable
from escapewheel_reader.registries import acquire
from escapewheel_reader.uri import in_one_form

from .errors import FormatCheckUnavailable, ReplacedPacketUnreadable
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
    """Load Part 04's incorporated manifest schema, as this distribution copies it.

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
        raise FormatCheckUnavailable("jsonschema cannot assert date-time; install rfc3339-validator")
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
    own = major(document["packet_version"])
    for position, item in enumerate(document.get("replaces", ()), start=1):
        if item["packet_id"] == document["packet_id"] and major(item["packet_version"]) >= own:
            issues.append(
                Issue(
                    "packet.replaces.major_version",
                    f"replaces item {position} names this packet_id at {item['packet_version']}, whose major "
                    f"version is not below this packet's {document['packet_version']} (Part 04 §3)",
                    ((position, item["packet_id"], item["packet_version"]),),
                )
            )
    return len(issues) == before


def major(version: str) -> int:
    """Return a `packet_version`'s major version, the first of its three numbers (Part 04 §3)."""
    return int(version.split(".", 1)[0])


def _published(path: Path) -> list[tuple[str, Mapping[str, Any]]]:
    """Return each manifest at `path` as (SHA-256 of its bytes, decoded), the published one first.

    A packet root yields its `packet.json` and every manifest it retains, since an item naming a
    version later amended names a retained one (Part 05 §15.3); a file yields itself.
    """
    paths = [path] if path.is_file() else [path / "packet.json", *sorted((path / "manifests").glob("*.json"))]
    found = []
    for manifest in paths:
        if manifest.is_file():
            body = manifest.read_bytes()
            try:
                decoded = json.loads(body)
            except ValueError:
                continue
            if isinstance(decoded, dict):
                found.append((hashlib.sha256(body).hexdigest(), decoded))
    if not found or not (path.is_file() or (path / "packet.json").is_file()):
        raise ReplacedPacketUnreadable(f"no published manifest can be read at {path}", path=path)
    return found


def confirm_replaced(
    document: Mapping[str, Any], supplied: Sequence[str | Path]
) -> list[tuple[str, tuple[tuple[Any, ...], ...]]]:
    """Compare each supplied packet with the `replaces` item it is read as (Part 04 §3).

    A packet is read as the item one of its manifests' SHA-256 confirms, else the item naming one
    of their `packet_id` and `packet_version`, else the item naming its `packet_id`, else the only
    item. Each returned (message, rows) is a difference the caller reports at `warning`, preferring
    neither side, since the item or the packet supplied may be the one that is wrong.

    Raises
    ------
    ReplacedPacketUnreadable
        If no published manifest can be read where a supplied path points.
    """
    items = list(document.get("replaces", ()))
    differences: list[tuple[str, tuple[tuple[Any, ...], ...]]] = []
    if not items:
        return differences
    for path in (Path(p) for p in supplied):
        manifests = _published(path)
        if any(item["sha256"] == sha for item in items for sha, _ in manifests):
            continue
        named = {(m.get("packet_id"), m.get("packet_version")): (sha, m) for sha, m in manifests}
        paired = next(
            (
                (i, *named[key])
                for i, item in enumerate(items)
                if (key := (item["packet_id"], item["packet_version"])) in named
            ),
            None,
        )
        if paired is None:
            sha, published = manifests[0]
            candidates = [i for i, item in enumerate(items) if item["packet_id"] == published.get("packet_id")]
            if not candidates and len(items) == 1:
                candidates = [0]
            if not candidates:
                differences.append(
                    (
                        f"the packet at {path} is {published.get('packet_id')}, which no replaces item names",
                        ((None, "packet_id", None, published.get("packet_id")),),
                    )
                )
                continue
            paired = (candidates[0], sha, published)
        index, sha, manifest = paired
        item = items[index]
        rows = tuple(
            (index + 1, member, item[member], found)
            for member, found in (
                ("packet_id", manifest.get("packet_id")),
                ("packet_version", manifest.get("packet_version")),
                ("sha256", sha),
            )
            if item[member] != found
        )
        members = ", ".join(row[1] for row in rows)
        differences.append((f"replaces item {index + 1} differs in {members} from the packet at {path}", rows))
    return differences


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


@lru_cache(maxsize=32)
def _checked(data: bytes, core: bytes | None) -> CheckedRegistryContext:
    """Check a registry's bytes in the context of core's, once for each distinct pair.

    The result is a function of the two byte strings, and the packets of one dataset bind the
    same ones.
    """
    return check_registry_context_bytes(data, core=None if core is None else _checked(core, None))


#: The check Part 04 §10 names for each way acquiring a bound registry fails.
_ACQUISITION_CHECK = {
    RegistryFault.MISSING: "packet.registry.missing",
    RegistryFault.UNREADABLE: "packet.registry.unreadable",
    RegistryFault.DIGEST: "packet.registry.digest",
}


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
            issues.append(Issue(_ACQUISITION_CHECK[exc.reason], str(exc), ((name, binding.path),), name))
    bound.core_id = next((name for name, binding in bindings.items() if binding.role == "core"), None)
    core_bytes = None
    if bound.core_id is not None and bound.core_id in acquired:
        core_bytes = acquired[bound.core_id]
        bound.contexts[bound.core_id] = _checked(core_bytes, None)
    for name in bindings:
        if name != bound.core_id and name in acquired:
            bound.contexts[name] = _checked(acquired[name], core_bytes)
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

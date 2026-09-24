"""Parsing of ``packet.json``.

The manifest is the packet's entry point: it declares which resources exist, where they
live, which registries declare them, and which sessions the packet covers. A reader checks only
what reading needs (Part 04 §10); the incorporated schema is the validator's.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ManifestError
from .location import Location
from .profile import interface_for

MANIFEST_FILENAME = "packet.json"

#: The namespaces the core registry declares; every other namespace is its extension's own.
CORE_NAMESPACES = frozenset({"core", "analysis"})


def _unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    counts = Counter(name for name, _ in pairs)
    repeated = sorted(name for name, count in counts.items() if count > 1)
    if repeated:
        raise ManifestError(f"an object repeats member {repeated[0]!r}")
    return dict(pairs)


def decode_json(raw: bytes, what: str) -> Any:
    """Decode UTF-8 JSON, rejecting a repeated object member rather than keeping the last.

    Parameters
    ----------
    raw : bytes
        The document's bytes.
    what : str
        What to call the document in an error.

    Returns
    -------
    Any
        The decoded value.

    Raises
    ------
    ManifestError
        If the bytes are not UTF-8, not JSON, or repeat a member within one object.
    """
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_members)
    except ManifestError as exc:
        raise ManifestError(f"{what}: {exc}") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"{what} is not valid UTF-8 JSON: {exc}") from exc


def _typed(entry: Mapping[str, Any], name: str, kind: type | tuple[type, ...], where: str) -> Any:
    """Read one required member, failing by name where it is absent or of the wrong JSON type."""
    if name not in entry:
        raise ManifestError(f"{where} lacks required member {name!r}")
    return _optional(entry, name, kind, where)


def _optional(entry: Mapping[str, Any], name: str, kind: type | tuple[type, ...], where: str) -> Any:
    value = entry.get(name)
    # JSON has no boolean-integer overlap, but Python's bool subclasses int.
    if value is not None and (not isinstance(value, kind) or (kind is not bool and isinstance(value, bool))):
        raise ManifestError(f"{where} member {name!r} has the wrong JSON type")
    return value


@dataclass(frozen=True)
class RegistryBinding:
    """One registry descriptor from the manifest's `registries` map (Part 04 §8).

    Attributes
    ----------
    registry_id : str
        The member name, which the bound document's own `registry_id` must equal.
    role : str
        ``core`` or ``extension``.
    version : str
        The bound document's `registry_version`.
    path : str
        Where the stored copy is, relative to the packet root.
    sha256 : str
        Digest of the document's exact bytes, after the profile's storage decoding.
    """

    registry_id: str
    role: str
    version: str
    path: str
    sha256: str


@dataclass(frozen=True)
class Resource:
    """One resource entry from the manifest.

    Attributes
    ----------
    resource_id : str
        Dotted resource ID, e.g. ``core.intervals``.
    declaration_id : str
        Logical declaration this packet resource instantiates.
    uri : str
        Location, relative to the packet root unless absolute.
    entry : Mapping
        The complete manifest entry, including fields this class does not surface.
    resolve : callable, optional
        Looks a declaration ID up in the packet's bound registries. Called only when a property
        needs the declaration, so listing resources acquires no registry.
    """

    resource_id: str
    declaration_id: str
    uri: str
    entry: Mapping[str, Any]
    resolve: Callable[[str], Mapping[str, Any] | None] | None = field(default=None, compare=False, repr=False)

    @property
    def declaration(self) -> Mapping[str, Any] | None:
        """The declaration `declaration_id` names in a bound registry, or None if none does.

        Raises
        ------
        RegistryUnavailable
            If the registry that would declare it is missing, unreadable, or fails its digest.
        """
        return None if self.resolve is None else self.resolve(self.declaration_id)

    @property
    def content_class(self) -> str | None:
        """Content class resolved from the registry declaration, if available."""
        value = None if self.declaration is None else self.declaration.get("content_class")
        return str(value) if value is not None else None

    @property
    def layer(self) -> str | None:
        """Compatibility name for the declaration-resolved content class."""
        return self.content_class

    @property
    def kind(self) -> str | None:
        """Logical kind resolved from the registry declaration, if available."""
        value = None if self.declaration is None else self.declaration.get("kind")
        return str(value) if value is not None else None

    @property
    def canonical(self) -> bool | None:
        """Canonicality derived from content class, if the declaration resolved."""
        content_class = self.content_class
        return None if content_class is None else content_class in {"core", "extension"}

    @property
    def instances(self) -> Mapping[str, Any] | None:
        """The declaration's instance model, if available."""
        value = None if self.declaration is None else self.declaration.get("instances")
        return value if isinstance(value, Mapping) else None

    @property
    def lineage_policy(self) -> str | None:
        """The declaration-selected lineage policy, if available."""
        value = None if self.declaration is None else self.declaration.get("lineage")
        return str(value) if value is not None else None

    @property
    def is_table(self) -> bool:
        """Whether this resource is tabular."""
        return self.kind == "table"

    @property
    def interface(self) -> str | None:
        """Generic physical interface derived from the checked logical kind."""
        return None if self.kind is None else interface_for(self.kind)

    @property
    def source(self) -> str | None:
        """The body of data this resource belongs to, if it names one (Part 04 §5.5).

        Where present, `uri` is a path relative to wherever that source turns out to be, and a
        resolution document says where that is. Neither field is a location.
        """
        value: str | None = _optional(self.entry, "source", str, self.resource_id)
        return value

    @property
    def is_external(self) -> bool:
        """Whether the packet references these bytes rather than owning them."""
        return bool(_optional(self.entry, "external", bool, self.resource_id))

    @property
    def validation_state(self) -> str | None:
        """The validation state recorded for this resource, if declared."""
        value: str | None = _optional(self.entry, "validation_state", str, self.resource_id)
        return value


@dataclass(frozen=True)
class Manifest:
    """A parsed packet manifest.

    Attributes
    ----------
    packet_id : str
        Identifier for this packet.
    profile_id : str
        Physical profile the packet claims to conform to.
    sessions : tuple of str
        Every session the packet contains.
    registries : Mapping
        Every bound registry's descriptor, by registry ID (Part 04 §8).
    resources : tuple of Resource
        Every declared resource.
    entry : Mapping
        The complete parsed manifest.
    """

    packet_id: str
    profile_id: str
    sessions: tuple[str, ...]
    registries: Mapping[str, RegistryBinding]
    resources: tuple[Resource, ...]
    entry: Mapping[str, Any]

    @property
    def core(self) -> RegistryBinding | None:
        """The descriptor whose role is ``core``, or None where the manifest binds none."""
        return next((binding for binding in self.registries.values() if binding.role == "core"), None)

    @property
    def extensions(self) -> dict[str, RegistryBinding]:
        """The descriptors whose role is ``extension``, by registry ID."""
        return {name: binding for name, binding in self.registries.items() if binding.role == "extension"}

    def binding_for(self, declaration_id: str) -> RegistryBinding | None:
        """Find the bound registry that would declare `declaration_id`, by its namespace.

        Parameters
        ----------
        declaration_id : str
            A dotted declaration ID.

        Returns
        -------
        RegistryBinding or None
            The core descriptor for ``core`` and ``analysis``, the extension descriptor named by
            any other namespace, or None where nothing bound could declare it.
        """
        namespace = declaration_id.split(".", 1)[0]
        if namespace in CORE_NAMESPACES:
            return self.core
        binding = self.extensions.get(namespace)
        return binding

    @classmethod
    def load(cls, root: Location | Path | str) -> Manifest:
        """Read and parse the manifest at a packet root.

        Only what reading needs is checked: UTF-8 JSON with no repeated member, unique resource
        IDs, and the JSON type of each member read. The incorporated schema is not applied, so a
        manifest carrying an unknown member or a malformed timestamp still opens.

        Parameters
        ----------
        root : Location, Path, or str
            Packet root: a local directory or a store prefix such as ``s3://bucket/prefix``.

        Returns
        -------
        Manifest
            The parsed manifest.

        Raises
        ------
        ManifestError
            If the manifest is missing, is not UTF-8 JSON, repeats a member or a resource ID, or
            lacks or mistypes a member reading needs.
        """
        where = Location.of(root)
        document = where.join(MANIFEST_FILENAME)
        try:
            # One request, not an existence check and then a read: over a store the second
            # round trip buys only a different error message.
            raw = document.read_bytes()
        except Exception as exc:
            raise ManifestError(f"no {MANIFEST_FILENAME} at {where}: {exc}") from exc
        parsed = decode_json(raw, str(document))
        if not isinstance(parsed, Mapping):
            raise ManifestError(f"{document} is not a JSON object")
        return cls.from_dict(parsed)

    @classmethod
    def from_dict(cls, entry: Mapping[str, Any]) -> Manifest:
        """Build a manifest from an already-decoded mapping.

        Parameters
        ----------
        entry : Mapping
            The decoded manifest.

        Returns
        -------
        Manifest
            The parsed manifest.

        Raises
        ------
        ManifestError
            If a resource ID repeats, or a member reading needs is absent or mistyped.
        """
        raw_resources: Sequence[Any] = _typed(entry, "resources", list, "manifest")
        for index, resource in enumerate(raw_resources):
            if not isinstance(resource, Mapping):
                raise ManifestError(f"manifest member 'resources' item {index + 1} is not an object")
        # Before any lookup is built: a mapping keyed by resource ID would keep one silently.
        counts = Counter(r["resource_id"] for r in raw_resources if isinstance(r.get("resource_id"), str))
        repeated = sorted(str(name) for name, count in counts.items() if count > 1)
        if repeated:
            raise ManifestError(f"resource ID {repeated[0]!r} names more than one entry")
        raw_registries: Mapping[str, Any] = _typed(entry, "registries", dict, "manifest")
        registries = {}
        for name, descriptor in raw_registries.items():
            where = f"registry descriptor {name!r}"
            if not isinstance(descriptor, Mapping):
                raise ManifestError(f"{where} is not an object")
            registries[str(name)] = RegistryBinding(
                registry_id=str(name),
                role=_typed(descriptor, "role", str, where),
                version=_typed(descriptor, "version", str, where),
                path=_typed(descriptor, "path", str, where),
                sha256=_typed(descriptor, "sha256", str, where),
            )
        sessions = _typed(entry, "sessions", list, "manifest")
        if not all(isinstance(session, str) for session in sessions):
            raise ManifestError("manifest member 'sessions' has the wrong JSON type")
        return cls(
            packet_id=_typed(entry, "packet_id", str, "manifest"),
            profile_id=_typed(entry, "profile_id", str, "manifest"),
            sessions=tuple(sessions),
            registries=registries,
            resources=tuple(
                Resource(
                    resource_id=_typed(r, "resource_id", str, "resource entry"),
                    declaration_id=_typed(r, "declaration_id", str, f"resource {r['resource_id']!r}"),
                    uri=_typed(r, "uri", str, f"resource {r['resource_id']!r}"),
                    entry=r,
                )
                for r in raw_resources
            ),
            entry=entry,
        )

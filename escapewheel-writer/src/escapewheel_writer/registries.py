"""The registries one packet is written against, and the lookups a writer makes in them (Part 04 §8).

- :class:`Declarations` -- core and each extension, checked, with every declaration they hold.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from escapewheel_validator import CheckedRegistryContext, RegistryRejected, RegistryState, check_registry_context

from .errors import UsageError, UsageFault


class Declarations:
    """Core and the extensions a packet binds, each checked before anything is resolved in it.

    Parameters
    ----------
    registry : Mapping or CheckedRegistryContext
        The core registry.
    extensions : sequence of Mapping or CheckedRegistryContext, optional
        The extension registries, each checked against that core.

    Raises
    ------
    RegistryRejected
        If core or an extension is not a valid registry.
    UsageError
        If two registries are given for one extension, or an extension declares a resource outside
        its namespace or one core declares.
    """

    def __init__(
        self,
        registry: Mapping[str, Any] | CheckedRegistryContext,
        extensions: Sequence[Mapping[str, Any] | CheckedRegistryContext] = (),
    ) -> None:
        core_context = registry if isinstance(registry, CheckedRegistryContext) else check_registry_context(registry)
        if core_context.result.state != RegistryState.VALID:
            raise RegistryRejected("core", core_context)
        checked_registry = core_context.document
        assert isinstance(checked_registry, Mapping)
        self.core: Mapping[str, Any] = checked_registry
        #: Extension registries this packet carries (Part 09 §5.3), by `extension_id`. An extension is a
        #: registry document like core's, so everything below resolves a resource against core
        #: and then these -- there is no second code path for an extension's tables.
        self.extensions: dict[str, Mapping[str, Any]] = {}
        for supplied in extensions:
            extension_context = (
                supplied
                if isinstance(supplied, CheckedRegistryContext)
                else check_registry_context(supplied, core=core_context)
            )
            if extension_context.core is not core_context:
                extension_context = check_registry_context(extension_context.document, core=core_context)
            if extension_context.result.state != RegistryState.VALID:
                subject = str(extension_context.document.get("extension_id", "extension"))
                raise RegistryRejected(subject, extension_context)
            document = extension_context.document
            assert isinstance(document, Mapping)
            extension_id = str(document["extension_id"])
            if extension_id in self.extensions:
                versions = (self.extensions[extension_id]["registry_version"], document["registry_version"])
                raise UsageError(
                    f"two registries for extension {extension_id!r} (versions {versions[0]} and {versions[1]}); a "
                    "packet binds one per extension (Part 04 §8, Part 05 §3.1), so the writer keeps neither",
                    code=UsageFault.EXTENSION_TWICE,
                    where=extension_id,
                )
            for resource_id in document["resources"]:
                if not resource_id.startswith(f"{extension_id}."):
                    raise UsageError(
                        f"{resource_id} is not namespaced by {extension_id!r}; Part 09 §5.2 requires it, "
                        "and an extension MUST NOT define a table in core or analysis",
                        code=UsageFault.EXTENSION_NAMESPACE,
                        where=resource_id,
                    )
                if resource_id in checked_registry["resources"]:
                    raise UsageError(
                        f"{resource_id} redefines a core resource, which Part 09 forbids",
                        code=UsageFault.EXTENSION_REDEFINES_CORE,
                        where=resource_id,
                    )
            self.extensions[extension_id] = document

    @property
    def documents(self) -> tuple[Mapping[str, Any], ...]:
        """Core, then each extension in the order given."""
        return (self.core, *self.extensions.values())

    def unused(self, declaration_ids: Iterable[str]) -> list[str]:
        """Each extension declaring none of `declaration_ids`, by registry ID.

        Part 04 §8 requires binding every extension that declares a resource and permits binding
        others, so one a recipe lists needlessly validates while telling a consumer the packet uses it.
        """
        used = set(declaration_ids)
        return sorted(str(d["registry_id"]) for d in self.extensions.values() if used.isdisjoint(d["resources"]))

    def declaration(self, declaration_id: str) -> Mapping[str, Any] | None:
        """Return one logical declaration from core or the owning extension."""
        if declaration_id in self.core["resources"]:
            declaration: Mapping[str, Any] = self.core["resources"][declaration_id]
            return declaration
        for document in self.extensions.values():
            if declaration_id in document["resources"]:
                declaration = document["resources"][declaration_id]
                return declaration
        return None

    def spec(self, resource_id: str) -> Mapping[str, Any] | None:
        """Return the registry entry for one resource, core or extension, or None if undefined.

        One lookup for both, because an extension needs no second code path (Part 09 §5.6):
        it is a registry document like core's, so a table of one is a table of the other.
        """
        declaration = self.declaration(resource_id)
        if declaration is None or declaration.get("kind") != "table":
            return None
        spec: Mapping[str, Any] = declaration["table"]
        return spec

    def family(self, declaration_id: str, resource_id: str, kind: str) -> Mapping[str, Any]:
        """Resolve an explicit family declaration and check that it admits this instance."""
        declaration = self.declaration(declaration_id)
        if declaration is None:
            raise UsageError(
                f"{resource_id}: unknown declaration {declaration_id!r}",
                code=UsageFault.UNKNOWN_DECLARATION,
                where=resource_id,
            )
        if declaration["kind"] != kind:
            raise UsageError(
                f"{resource_id}: {declaration_id} has kind {declaration['kind']!r}, not {kind!r}",
                code=UsageFault.DECLARATION_KIND,
                where=resource_id,
            )
        if declaration["instances"]["mode"] not in {"catalog", "family"}:
            raise UsageError(
                f"{resource_id}: {declaration_id} does not admit family instances",
                code=UsageFault.NOT_A_FAMILY,
                where=resource_id,
            )
        owner = declaration_id.split(".", 1)[0]
        if not resource_id.startswith(f"{owner}."):
            raise UsageError(
                f"{resource_id}: namespace is not owned by declaration {declaration_id!r}",
                code=UsageFault.INSTANCE_NAMESPACE,
                where=resource_id,
            )
        return declaration

    def opaque(self) -> tuple[dict[str, tuple[str, str]], set[str]]:
        """Every loaded opaque catalog family, to its catalog and column, and every opaque singleton."""
        families: dict[str, tuple[str, str]] = {}
        singletons: set[str] = set()
        for document in (self.core, *self.extensions.values()):
            for declaration_id, declaration in document["resources"].items():
                if declaration["kind"] != "opaque":
                    continue
                instances = declaration["instances"]
                if instances["mode"] == "catalog":
                    catalog, column = str(instances["catalog_resource"]), str(instances["resource_id_column"])
                    families[declaration_id] = (catalog, column)
                elif instances["mode"] == "singleton":
                    singletons.add(declaration_id)
        return families, singletons


__all__ = ["Declarations"]

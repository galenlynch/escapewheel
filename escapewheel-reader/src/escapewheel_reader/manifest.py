"""Parsing and validation of ``packet.json``.

The manifest is the packet's entry point: it declares which resources exist, where they
live, and which sessions the packet covers.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any

import jsonschema

from .errors import ManifestError
from .location import Location
from .profile import interface_for

MANIFEST_FILENAME = "packet.json"


def manifest_schema() -> dict[str, Any]:
    """Load the bundled JSON Schema for the packet manifest.

    Returns
    -------
    dict
        The parsed schema.
    """
    text = importlib_resources.files(__package__).joinpath("schemas/manifest.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


def sources_schema() -> dict[str, Any]:
    """Load the bundled JSON Schema for a source resolution document (Part 04 §5.5).

    Vendored from `registry/` the way the manifest's is, because a wheel cannot read a file from
    another repository.

    Returns
    -------
    dict
        The parsed schema.
    """
    text = importlib_resources.files(__package__).joinpath("schemas/sources.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


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
    """

    resource_id: str
    declaration_id: str
    uri: str
    entry: Mapping[str, Any]
    declaration: Mapping[str, Any] | None = None

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
    def producing_run_policy(self) -> str | None:
        """The declaration-selected producing-run policy, if available."""
        value = None if self.declaration is None else self.declaration.get("producing_run")
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
        value = self.entry.get("source")
        return str(value) if value is not None else None

    @property
    def is_external(self) -> bool:
        """Whether the packet references these bytes rather than owning them."""
        return bool(self.entry.get("external", False))

    @property
    def validation_state(self) -> str | None:
        """The validation state recorded for this resource, if declared."""
        value = self.entry.get("validation_state")
        return str(value) if value is not None else None


@dataclass(frozen=True)
class Manifest:
    """A parsed packet manifest.

    Attributes
    ----------
    packet_id : str
        Identifier for this packet.
    profile_id : str
        Physical profile the packet claims to conform to.
    registry_version : str
        Version of the schema registry the packet was written against.
    sessions : tuple of str
        Every session the packet contains.
    extensions : Mapping
        Extension registries the packet declares (Part 09 §6, Part 09 §2), by `extension_id`. Empty is
        the common case and is conforming: core is interpretable without any.
    resources : tuple of Resource
        Every declared resource.
    entry : Mapping
        The complete parsed manifest.
    """

    packet_id: str
    profile_id: str
    registry_version: str
    sessions: tuple[str, ...]
    extensions: Mapping[str, Any]
    resources: tuple[Resource, ...]
    entry: Mapping[str, Any]

    @classmethod
    def load(cls, root: Location | Path | str, *, validate: bool = True) -> Manifest:
        """Read and parse the manifest at a packet root.

        Parameters
        ----------
        root : Location, Path, or str
            Packet root: a local directory or a store prefix such as ``s3://bucket/prefix``.
        validate : bool, default True
            Whether to check the manifest against its JSON Schema before parsing.

        Returns
        -------
        Manifest
            The parsed manifest.

        Raises
        ------
        ManifestError
            If the manifest is missing, unparsable, or does not conform to its schema.
        """
        where = Location.of(root)
        document = where.join(MANIFEST_FILENAME)
        try:
            # One request, not an existence check and then a read: over a store the second
            # round trip buys only a different error message.
            raw = document.read_bytes()
        except Exception as exc:
            raise ManifestError(f"no {MANIFEST_FILENAME} at {where}: {exc}") from exc
        try:
            parsed: dict[str, Any] = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ManifestError(f"{document} is not valid JSON: {exc}") from exc
        if validate:
            errors = sorted(
                jsonschema.Draft202012Validator(manifest_schema()).iter_errors(parsed),
                key=lambda e: list(e.path),
            )
            if errors:
                detail = "; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors[:5])
                raise ManifestError(f"{document} does not conform to the manifest schema: {detail}")
        return cls.from_dict(parsed)

    @classmethod
    def from_dict(cls, entry: Mapping[str, Any]) -> Manifest:
        """Build a manifest from an already-parsed mapping.

        Parameters
        ----------
        entry : Mapping
            The parsed manifest contents.

        Returns
        -------
        Manifest
            The parsed manifest.
        """
        raw_resources: Sequence[Mapping[str, Any]] = entry.get("resources", [])
        return cls(
            packet_id=str(entry["packet_id"]),
            profile_id=str(entry["profile_id"]),
            registry_version=str(entry.get("registry_version", "")),
            sessions=tuple(str(s) for s in entry.get("sessions", [])),
            extensions=dict(entry.get("extensions") or {}),
            resources=tuple(
                Resource(
                    resource_id=str(r["resource_id"]),
                    declaration_id=str(r["declaration_id"]),
                    uri=str(r["uri"]),
                    entry=r,
                )
                for r in raw_resources
            ),
            entry=entry,
        )

"""Every check ID this package declares, in one table.

- :class:`CheckEntry` -- one check: its ID, its default level, its scope, and whether the
  specification names it.
- :class:`Scope` -- what one finding of a check names.
- :data:`TABLE` -- every entry: each fixed ID, and one entry for each templated family.
- A constant for each fixed ID, named as the ID in capitals with its full stops as underscores,
  such as :data:`OWNED_DIGEST` for ``owned.digest``.
- A function for each templated family, which builds one ID from its parts, such as
  :func:`physical_order` for ``<resource_id>.physical_order``.
- :func:`rule`, :func:`registry_outcome` -- an ID declared outside this table: a Tier 2 rule's by
  the registry holding it, and a registry result's outcome's by the registry contract.

A finding is recorded with `Report.add`, which takes an entry and reports at the entry's level;
:meth:`CheckEntry.at` gives the entry at another level where what was found decides it. No other
module of this package writes a check ID as a string.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from escapewheel_reader import sql_name

from .vocabulary import Level


class Scope(StrEnum):
    """What one finding of a check names."""

    #: The manifest or the packet as a whole.
    PACKET = "packet"
    #: One registry the manifest binds.
    REGISTRY = "registry"
    #: One resource: its manifest entry, its stored bytes, or its rows taken together.
    RESOURCE = "resource"
    #: One column of one table, or the columns of one reference.
    COLUMN = "column"


_PLACEHOLDER = re.compile(r"<(\w+)>")


@dataclass(frozen=True)
class CheckEntry:
    """One check a finding is reported under.

    Attributes
    ----------
    id : str
        The check ID. A templated family's entry in :data:`TABLE` holds its template, each part
        written as ``<name>``; the family's function returns an entry holding one built ID.
    level : Level
        The level a finding takes unless :meth:`at` says otherwise.
    scope : Scope
        What one finding names.
    named : bool or None
        Whether a numbered part of the specification writes the ID standing alone, joined to no
        longer ID. A family is named where a part writes its template, whatever the part calls
        each ``<name>``, or one ID the template admits. None for an ID declared outside this
        table.
    """

    id: str
    level: Level
    scope: Scope
    named: bool | None

    @property
    def templated(self) -> bool:
        """Whether `id` is a family's template, which no finding is reported under."""
        return _PLACEHOLDER.search(self.id) is not None

    def of(self, **parts: str) -> CheckEntry:
        """Return the entry for one ID of this family, each ``<name>`` replaced by its part."""
        return replace(self, id=_PLACEHOLDER.sub(lambda match: parts[match[1]], self.id))

    def at(self, level: Level | str) -> CheckEntry:
        """Return this entry at another level."""
        return replace(self, level=Level(level))


_ENTRIES: list[CheckEntry] = []
_ERROR, _WARNING, _INFO = Level.ERROR, Level.WARNING, Level.INFO
_PACKET, _REGISTRY, _RESOURCE, _COLUMN = Scope.PACKET, Scope.REGISTRY, Scope.RESOURCE, Scope.COLUMN


def _named(check_id: str, level: Level, scope: Scope) -> CheckEntry:
    """Declare a check a part of the specification names."""
    _ENTRIES.append(CheckEntry(check_id, level, scope, named=True))
    return _ENTRIES[-1]


def _unnamed(check_id: str, level: Level, scope: Scope) -> CheckEntry:
    """Declare a check no part of the specification names."""
    _ENTRIES.append(CheckEntry(check_id, level, scope, named=False))
    return _ENTRIES[-1]


# The manifest's `json`, `shape` and `entries` phases.
PACKET_MANIFEST_INVALID_JSON = _named("packet.manifest.invalid_json", _ERROR, _PACKET)
PACKET_MANIFEST_DUPLICATE_MEMBER = _named("packet.manifest.duplicate_member", _ERROR, _PACKET)
PACKET_MANIFEST_SCHEMA = _named("packet.manifest.schema", _ERROR, _PACKET)
PACKET_RESOURCE_ID_UNIQUE = _named("packet.resource.id_unique", _ERROR, _RESOURCE)
PACKET_RESOURCE_DIGEST_MISSING = _named("packet.resource.digest_missing", _ERROR, _RESOURCE)
PACKET_RESOURCE_URI_FORM = _named("packet.resource.uri_form", _ERROR, _RESOURCE)
PACKET_RESOURCE_MEMBER_UNIQUE = _named("packet.resource.member_unique", _ERROR, _RESOURCE)
PACKET_RESOURCE_MEMBER_SIZE = _named("packet.resource.member_size", _ERROR, _RESOURCE)
PACKET_RESOURCE_MEMBER_DIGEST = _named("packet.resource.member_digest", _ERROR, _RESOURCE)
PACKET_REGISTRY_CORE_COUNT = _named("packet.registry.core_count", _ERROR, _PACKET)
PACKET_REGISTRY_PATH_UNIQUE = _named("packet.registry.path_unique", _ERROR, _PACKET)
PACKET_REPLACES_MAJOR_VERSION = _named("packet.replaces.major_version", _ERROR, _PACKET)

# The `registry_binding` phase: acquiring each bound registry, then comparing it with its descriptor.
PACKET_REGISTRY_MISSING = _named("packet.registry.missing", _ERROR, _REGISTRY)
PACKET_REGISTRY_UNREADABLE = _named("packet.registry.unreadable", _ERROR, _REGISTRY)
PACKET_REGISTRY_DIGEST = _named("packet.registry.digest", _ERROR, _REGISTRY)
PACKET_REGISTRY_IDENTITY = _named("packet.registry.identity", _ERROR, _REGISTRY)
PACKET_REGISTRY_ROLE = _named("packet.registry.role", _ERROR, _REGISTRY)
PACKET_REGISTRY_VERSION = _named("packet.registry.version", _ERROR, _REGISTRY)
PACKET_REGISTRY_STANDARD = _named("packet.registry.standard", _ERROR, _REGISTRY)

# A packet supplied as one the manifest's `replaces` names.
PACKET_REPLACES_MISMATCH = _named("packet.replaces.mismatch", _WARNING, _PACKET)

# The `declaration` phase: each entry against the declaration it names.
PACKET_RESOURCE_DECLARATION_UNKNOWN = _named("packet.resource.declaration_unknown", _ERROR, _RESOURCE)
PACKET_REGISTRY_UNUSED = _named("packet.registry.unused", _WARNING, _REGISTRY)
PACKET_RESOURCE_SINGLETON_IDENTITY = _named("packet.resource.singleton_identity", _ERROR, _RESOURCE)
PACKET_RESOURCE_FAMILY_NAMESPACE = _named("packet.resource.family_namespace", _ERROR, _RESOURCE)
PACKET_RESOURCE_DEPENDENCY_MISSING = _named("packet.resource.dependency_missing", _ERROR, _RESOURCE)
PACKET_RESOURCE_ARRAY_AXES_MISSING = _named("packet.resource.array_axes_missing", _ERROR, _RESOURCE)
PACKET_RESOURCE_DERIVED_FROM_REQUIRED = _named("packet.resource.derived_from_required", _ERROR, _RESOURCE)
PACKET_RESOURCE_DERIVED_FROM_FORBIDDEN = _named("packet.resource.derived_from_forbidden", _ERROR, _RESOURCE)
PACKET_RESOURCE_REQUIRED_MISSING = _named("packet.resource.required_missing", _ERROR, _RESOURCE)
PACKET_RESOURCE_REFERENCE_TARGET_MISSING = _named("packet.resource.reference_target_missing", _ERROR, _RESOURCE)
PACKET_RESOURCE_CATALOG_TABLE_UNREADABLE = _named("packet.resource.catalog_table_unreadable", _ERROR, _RESOURCE)
PACKET_RESOURCE_CATALOG_ROW_BINDING = _named("packet.resource.catalog_row_binding", _ERROR, _RESOURCE)
PACKET_RESOURCE_LINEAGE_UNRESOLVED = _named("packet.resource.lineage_unresolved", _ERROR, _RESOURCE)
PACKET_RESOURCE_LINEAGE_CLASS = _named("packet.resource.lineage_class", _ERROR, _RESOURCE)
PACKET_RESOURCE_LINEAGE_CYCLE = _named("packet.resource.lineage_cycle", _ERROR, _PACKET)

# Source declarations.
SOURCES_DECLARED = _unnamed("sources.declared", _ERROR, _RESOURCE)
SOURCES_ABSOLUTE_URI = _unnamed("sources.absolute_uri", _ERROR, _RESOURCE)
SOURCES_DECLARED_COUNT = _unnamed("sources.declared_count", _INFO, _PACKET)
SOURCES_UNRESOLVED = _unnamed("sources.unresolved", _INFO, _PACKET)

# A resource's bytes: whether they are there, and whether they hold their recorded size and digest.
RESOURCE_MISSING = _unnamed("resource.missing", _ERROR, _RESOURCE)
RESOURCE_UNREADABLE = _unnamed("resource.unreadable", _ERROR, _RESOURCE)
OWNED_DIGEST = _unnamed("owned.digest", _ERROR, _RESOURCE)
OWNED_SIZE_BYTES = _unnamed("owned.size_bytes", _ERROR, _RESOURCE)
OWNED_VERIFIED = _unnamed("owned.verified", _INFO, _PACKET)

# An external resource against what the manifest claims of it.
EXTERNAL_UNREACHABLE = _unnamed("external.unreachable", _WARNING, _RESOURCE)
EXTERNAL_SIZE_BYTES = _unnamed("external.size_bytes", _ERROR, _RESOURCE)
EXTERNAL_DIGEST = _unnamed("external.digest", _ERROR, _RESOURCE)
EXTERNAL_MEMBERS = _unnamed("external.members", _ERROR, _RESOURCE)
EXTERNAL_STORE_DIGEST = _unnamed("external.store_digest", _ERROR, _RESOURCE)
EXTERNAL_NO_STORE_DIGEST = _unnamed("external.no_store_digest", _WARNING, _RESOURCE)
EXTERNAL_NO_CHECKSUM = _unnamed("external.no_checksum", _WARNING, _PACKET)
EXTERNAL_VERIFIED = _unnamed("external.verified", _INFO, _PACKET)
EXTERNAL_LOCATED = _unnamed("external.located", _INFO, _PACKET)
EXTERNAL_MIRROR_UNUSABLE = _unnamed("external.mirror_unusable", _WARNING, _RESOURCE)

# A packet-owned array against its own Zarr metadata, and its axes against its shape.
ARRAY_NO_ARRAY_DIMENSIONS_TABLE = _unnamed("array.no_array_dimensions_table", _ERROR, _PACKET)
ARRAY_UNREADABLE = _unnamed("array.unreadable", _ERROR, _RESOURCE)
ARRAY_NOT_ZARR_V3 = _unnamed("array.not_zarr_v3", _ERROR, _RESOURCE)
ARRAY_TRANSPOSE_CODEC = _unnamed("array.transpose_codec", _ERROR, _RESOURCE)
ARRAY_IRREGULAR_CHUNK_GRID = _unnamed("array.irregular_chunk_grid", _ERROR, _RESOURCE)
ARRAY_NO_FILL_VALUE = _unnamed("array.no_fill_value", _ERROR, _RESOURCE)
ARRAY_RANK_DISAGREES_WITH_DIMENSIONS = _unnamed("array.rank_disagrees_with_dimensions", _ERROR, _RESOURCE)
ARRAY_DIMENSION_NAMES = _unnamed("array.dimension_names", _ERROR, _RESOURCE)
ARRAY_LABEL_POSITION_OUT_OF_RANGE = _unnamed("array.label_position_out_of_range", _ERROR, _RESOURCE)
ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE = _unnamed("array.depends_on_position_out_of_range", _ERROR, _RESOURCE)
ARRAY_LABEL_MISSING = _unnamed("array.label_missing", _ERROR, _RESOURCE)
ARRAY_CHANNEL_INDEX_OUT_OF_RANGE = _unnamed("array.channel_index_out_of_range", _ERROR, _RESOURCE)

# An external array's stored shape against its axes.
EXTERNAL_ARRAY_RANK = _unnamed("external.array_rank", _ERROR, _RESOURCE)
EXTERNAL_ARRAY_LABEL_POSITION_OUT_OF_RANGE = _unnamed("external.array_label_position_out_of_range", _ERROR, _RESOURCE)
EXTERNAL_ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE = _unnamed(
    "external.array_depends_on_position_out_of_range", _ERROR, _RESOURCE
)
EXTERNAL_ARRAY_LABEL_MISSING = _unnamed("external.array_label_missing", _ERROR, _RESOURCE)
EXTERNAL_ARRAY_CHANNEL_INDEX_OUT_OF_RANGE = _unnamed("external.array_channel_index_out_of_range", _ERROR, _RESOURCE)

# The reader floors, and names a copy would not keep.
PHYSICAL_OUTSIDE_READER_FLOOR = _named("physical.outside_reader_floor", _INFO, _RESOURCE)
PHYSICAL_PAGE_TYPES_UNASSESSED = _unnamed("physical.page_types_unassessed", _INFO, _PACKET)
EXTERNAL_PHYSICAL_UNASSESSED = _named("external.physical_unassessed", _INFO, _RESOURCE)
PHYSICAL_OPAQUE_NAME_PORTABILITY = _named("physical.opaque_name_portability", _WARNING, _RESOURCE)
PHYSICAL_OUTSIDE_TYPE_MAPPING = _named("physical.outside_type_mapping", _INFO, _COLUMN)

# A session's declared time origin.
TIME_ORIGIN_UNMAPPABLE = _named("time.origin_unmappable", _ERROR, _COLUMN)
TIME_ORIGIN_NOT_EARLIEST = _named("time.origin_not_earliest", _ERROR, _COLUMN)

# A table's file against its declared columns.
SCHEMA_COLUMN_ABSENT = _named("schema.column_absent", _ERROR, _COLUMN)
SCHEMA_COLUMN_TYPE = _named("schema.column_type", _ERROR, _COLUMN)
SCHEMA_COLUMN_UNDECLARED = _named("schema.column_undeclared", _ERROR, _COLUMN)

# The manifest's session inventory against `core.sessions`.
CORE_SESSIONS_MANIFEST_SESSIONS_MATCH = _named("core.sessions.manifest_sessions_match", _ERROR, _RESOURCE)

# What an extension registry's checks covered.
EXTENSION_TABLE_ABSENT = _unnamed("extension.table_absent", _INFO, _REGISTRY)
EXTENSION_VALIDATED = _unnamed("extension.validated", _INFO, _REGISTRY)

# An amendment against the version it supersedes.
AMENDMENT_IDENTITY_CHANGED = _named("amendment.identity_changed", _ERROR, _PACKET)
AMENDMENT_RESOURCE_CHANGED = _named("amendment.resource_changed", _ERROR, _RESOURCE)
AMENDMENT_DERIVED_RESOURCE_STALE = _named("amendment.derived_resource_stale", _ERROR, _RESOURCE)
AMENDMENT_ROW_CHANGED = _named("amendment.row_changed", _ERROR, _RESOURCE)
AMENDMENT_GROUP_GROWN = _named("amendment.group_grown", _ERROR, _RESOURCE)

# Families generated from a registry's structure. `<kind>` is a resource ID with each full stop
# written as an underscore, and `<columns>` a reference's columns joined by underscores.
_NOT_NULL = _unnamed("<declaration_id>.<column>.not_null", _ERROR, _COLUMN)
_FINITE = _named("<declaration_id>.<column>.finite", _ERROR, _COLUMN)
_NAME_UNIQUE = _named("<declaration_id>.<column>.unique", _ERROR, _COLUMN)
_IN_VOCABULARY = _unnamed("<declaration_id>.<column>.in_vocabulary", _ERROR, _COLUMN)
_IS_A_RESOURCE_ID = _unnamed("<declaration_id>.<column>.is_a_resource_id", _ERROR, _COLUMN)
_KIND_DECLARED = _unnamed("<declaration_id>.<column>.kind_declared", _ERROR, _COLUMN)
_IS_SPECIALISED = _unnamed("<declaration_id>.<column>.<kind>_is_specialised", _ERROR, _COLUMN)
_NAMES_A_ROW_OF_ITS_KIND = _unnamed("<declaration_id>.<columns>.names_a_row_of_its_kind", _ERROR, _COLUMN)
_KEY_FITS_PAIRED_VALUE = _unnamed("<declaration_id>.<column>.key_fits_paired_value", _ERROR, _COLUMN)
_PAIRED_VALUE_RESOLVES = _unnamed("<declaration_id>.<column>.<kind>_resolves", _ERROR, _COLUMN)
_SPECIALISED_ROW_HAS_KIND = _unnamed("<declaration_id>.<column>.specialised_row_has_kind", _ERROR, _COLUMN)
_PRIMARY_KEY_UNIQUE = _unnamed("<declaration_id>.primary_key_unique", _ERROR, _RESOURCE)
_REFERENCE_RESOLVES = _unnamed("<declaration_id>.<columns>_resolves", _ERROR, _COLUMN)

# Families the shim reports of a table's file.
_PHYSICAL_ORDER = _unnamed("<resource_id>.physical_order", _ERROR, _RESOURCE)
_DETERMINED_BY = _unnamed("<resource_id>.determined_by", _ERROR, _RESOURCE)
_COLUMNS_DUPLICATED = _named("<resource_id>.columns_duplicated", _INFO, _RESOURCE)
_METADATA_UNFILLED = _named("<resource_id>.metadata_unfilled", _INFO, _RESOURCE)
_OUTSIDE_RESERVED_SET = _unnamed("<resource_id>.<column>.outside_reserved_set", _INFO, _COLUMN)
_UCUM_CODE = _named("<declaration_id>.<column>.ucum_code", _ERROR, _COLUMN)

#: Every entry this package declares; a family's holds its template.
TABLE: tuple[CheckEntry, ...] = tuple(_ENTRIES)


def not_null(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.not_null``: a required column holds a null."""
    return _NOT_NULL.of(declaration_id=declaration_id, column=column)


def finite(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.finite``: a column declared finite holds NaN or an infinity."""
    return _FINITE.of(declaration_id=declaration_id, column=column)


def name_unique(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.unique``: two rows of one table carry one owned identifier's name."""
    return _NAME_UNIQUE.of(declaration_id=declaration_id, column=column)


def in_vocabulary(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.in_vocabulary``: a value outside the column's closed vocabulary."""
    return _IN_VOCABULARY.of(declaration_id=declaration_id, column=column)


def is_a_resource_id(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.is_a_resource_id``: a discriminator holds no dotted resource ID."""
    return _IS_A_RESOURCE_ID.of(declaration_id=declaration_id, column=column)


def kind_declared(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.kind_declared``: a discriminator names a resource the packet lacks.

    At `info` where the discriminator need not resolve.
    """
    return _KIND_DECLARED.of(declaration_id=declaration_id, column=column)


def is_specialised(declaration_id: str, column: str, kind: str) -> CheckEntry:
    """``<declaration_id>.<column>.<kind>_is_specialised``: a row names `kind` and has no counterpart there."""
    return _IS_SPECIALISED.of(declaration_id=declaration_id, column=column, kind=sql_name(kind))


def names_a_row_of_its_kind(declaration_id: str, columns: Sequence[str]) -> CheckEntry:
    """``<declaration_id>.<columns>.names_a_row_of_its_kind``: a detail row specialises a row of another kind."""
    return _NAMES_A_ROW_OF_ITS_KIND.of(declaration_id=declaration_id, columns="_".join(columns))


def key_fits_paired_value(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.key_fits_paired_value``: a named resource's key is not one the value can hold."""
    return _KEY_FITS_PAIRED_VALUE.of(declaration_id=declaration_id, column=column)


def paired_value_resolves(declaration_id: str, column: str, kind: str) -> CheckEntry:
    """``<declaration_id>.<column>.<kind>_resolves``: a paired value names no row of `kind`."""
    return _PAIRED_VALUE_RESOLVES.of(declaration_id=declaration_id, column=column, kind=sql_name(kind))


def specialised_row_has_kind(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.specialised_row_has_kind``: a paired value's row has a null kind."""
    return _SPECIALISED_ROW_HAS_KIND.of(declaration_id=declaration_id, column=column)


def primary_key_unique(declaration_id: str) -> CheckEntry:
    """``<declaration_id>.primary_key_unique``: two rows share a primary key."""
    return _PRIMARY_KEY_UNIQUE.of(declaration_id=declaration_id)


def reference_resolves(declaration_id: str, columns: Sequence[str]) -> CheckEntry:
    """``<declaration_id>.<columns>_resolves``: a reference's columns name no row of its target."""
    return _REFERENCE_RESOLVES.of(declaration_id=declaration_id, columns="_".join(columns))


def physical_order(resource_id: str) -> CheckEntry:
    """``<resource_id>.physical_order``: a table's rows are not in the order required of it."""
    return _PHYSICAL_ORDER.of(resource_id=resource_id)


def determined_by(resource_id: str) -> CheckEntry:
    """``<resource_id>.determined_by``: two rows sharing a key differ in a column declared determined by it."""
    return _DETERMINED_BY.of(resource_id=resource_id)


def columns_duplicated(resource_id: str) -> CheckEntry:
    """``<resource_id>.columns_duplicated``: two columns hold equal values in every row."""
    return _COLUMNS_DUPLICATED.of(resource_id=resource_id)


def metadata_unfilled(resource_id: str) -> CheckEntry:
    """``<resource_id>.metadata_unfilled``: a declared `metadata` column is omitted or wholly null."""
    return _METADATA_UNFILLED.of(resource_id=resource_id)


def outside_reserved_set(resource_id: str, column: str) -> CheckEntry:
    """``<resource_id>.<column>.outside_reserved_set``: a value outside the column's reserved set."""
    return _OUTSIDE_RESERVED_SET.of(resource_id=resource_id, column=column)


def ucum_code(declaration_id: str, column: str) -> CheckEntry:
    """``<declaration_id>.<column>.ucum_code``: a unit column holds a value that is no UCUM code."""
    return _UCUM_CODE.of(declaration_id=declaration_id, column=column)


def rule(rule_id: str, level: Level | str) -> CheckEntry:
    """Return the entry for a Tier 2 rule, under the ID and level its registry declares."""
    return CheckEntry(rule_id, Level(level), Scope.RESOURCE, named=None)


def registry_outcome(outcome_id: str) -> CheckEntry:
    """Return the entry for an invalid outcome of a registry document's result, under the outcome's own ID."""
    return CheckEntry(outcome_id, Level.ERROR, Scope.REGISTRY, named=None)


__all__ = [
    "AMENDMENT_DERIVED_RESOURCE_STALE",
    "AMENDMENT_GROUP_GROWN",
    "AMENDMENT_IDENTITY_CHANGED",
    "AMENDMENT_RESOURCE_CHANGED",
    "AMENDMENT_ROW_CHANGED",
    "ARRAY_CHANNEL_INDEX_OUT_OF_RANGE",
    "ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE",
    "ARRAY_DIMENSION_NAMES",
    "ARRAY_IRREGULAR_CHUNK_GRID",
    "ARRAY_LABEL_MISSING",
    "ARRAY_LABEL_POSITION_OUT_OF_RANGE",
    "ARRAY_NOT_ZARR_V3",
    "ARRAY_NO_ARRAY_DIMENSIONS_TABLE",
    "ARRAY_NO_FILL_VALUE",
    "ARRAY_RANK_DISAGREES_WITH_DIMENSIONS",
    "ARRAY_TRANSPOSE_CODEC",
    "ARRAY_UNREADABLE",
    "CORE_SESSIONS_MANIFEST_SESSIONS_MATCH",
    "EXTENSION_TABLE_ABSENT",
    "EXTENSION_VALIDATED",
    "EXTERNAL_ARRAY_CHANNEL_INDEX_OUT_OF_RANGE",
    "EXTERNAL_ARRAY_DEPENDS_ON_POSITION_OUT_OF_RANGE",
    "EXTERNAL_ARRAY_LABEL_MISSING",
    "EXTERNAL_ARRAY_LABEL_POSITION_OUT_OF_RANGE",
    "EXTERNAL_ARRAY_RANK",
    "EXTERNAL_DIGEST",
    "EXTERNAL_LOCATED",
    "EXTERNAL_MEMBERS",
    "EXTERNAL_MIRROR_UNUSABLE",
    "EXTERNAL_NO_CHECKSUM",
    "EXTERNAL_NO_STORE_DIGEST",
    "EXTERNAL_PHYSICAL_UNASSESSED",
    "EXTERNAL_SIZE_BYTES",
    "EXTERNAL_STORE_DIGEST",
    "EXTERNAL_UNREACHABLE",
    "EXTERNAL_VERIFIED",
    "OWNED_DIGEST",
    "OWNED_SIZE_BYTES",
    "OWNED_VERIFIED",
    "PACKET_MANIFEST_DUPLICATE_MEMBER",
    "PACKET_MANIFEST_INVALID_JSON",
    "PACKET_MANIFEST_SCHEMA",
    "PACKET_REGISTRY_CORE_COUNT",
    "PACKET_REGISTRY_DIGEST",
    "PACKET_REGISTRY_IDENTITY",
    "PACKET_REGISTRY_MISSING",
    "PACKET_REGISTRY_PATH_UNIQUE",
    "PACKET_REGISTRY_ROLE",
    "PACKET_REGISTRY_STANDARD",
    "PACKET_REGISTRY_UNREADABLE",
    "PACKET_REGISTRY_UNUSED",
    "PACKET_REGISTRY_VERSION",
    "PACKET_REPLACES_MAJOR_VERSION",
    "PACKET_REPLACES_MISMATCH",
    "PACKET_RESOURCE_ARRAY_AXES_MISSING",
    "PACKET_RESOURCE_CATALOG_ROW_BINDING",
    "PACKET_RESOURCE_CATALOG_TABLE_UNREADABLE",
    "PACKET_RESOURCE_DECLARATION_UNKNOWN",
    "PACKET_RESOURCE_DEPENDENCY_MISSING",
    "PACKET_RESOURCE_DERIVED_FROM_FORBIDDEN",
    "PACKET_RESOURCE_DERIVED_FROM_REQUIRED",
    "PACKET_RESOURCE_DIGEST_MISSING",
    "PACKET_RESOURCE_FAMILY_NAMESPACE",
    "PACKET_RESOURCE_ID_UNIQUE",
    "PACKET_RESOURCE_LINEAGE_CLASS",
    "PACKET_RESOURCE_LINEAGE_CYCLE",
    "PACKET_RESOURCE_LINEAGE_UNRESOLVED",
    "PACKET_RESOURCE_MEMBER_DIGEST",
    "PACKET_RESOURCE_MEMBER_SIZE",
    "PACKET_RESOURCE_MEMBER_UNIQUE",
    "PACKET_RESOURCE_REFERENCE_TARGET_MISSING",
    "PACKET_RESOURCE_REQUIRED_MISSING",
    "PACKET_RESOURCE_SINGLETON_IDENTITY",
    "PACKET_RESOURCE_URI_FORM",
    "PHYSICAL_OPAQUE_NAME_PORTABILITY",
    "PHYSICAL_OUTSIDE_READER_FLOOR",
    "PHYSICAL_OUTSIDE_TYPE_MAPPING",
    "PHYSICAL_PAGE_TYPES_UNASSESSED",
    "RESOURCE_MISSING",
    "RESOURCE_UNREADABLE",
    "SCHEMA_COLUMN_ABSENT",
    "SCHEMA_COLUMN_TYPE",
    "SCHEMA_COLUMN_UNDECLARED",
    "SOURCES_ABSOLUTE_URI",
    "SOURCES_DECLARED",
    "SOURCES_DECLARED_COUNT",
    "SOURCES_UNRESOLVED",
    "TABLE",
    "TIME_ORIGIN_NOT_EARLIEST",
    "TIME_ORIGIN_UNMAPPABLE",
    "CheckEntry",
    "Scope",
    "columns_duplicated",
    "determined_by",
    "finite",
    "in_vocabulary",
    "is_a_resource_id",
    "is_specialised",
    "key_fits_paired_value",
    "kind_declared",
    "metadata_unfilled",
    "name_unique",
    "names_a_row_of_its_kind",
    "not_null",
    "outside_reserved_set",
    "paired_value_resolves",
    "physical_order",
    "primary_key_unique",
    "reference_resolves",
    "registry_outcome",
    "rule",
    "specialised_row_has_kind",
    "ucum_code",
]

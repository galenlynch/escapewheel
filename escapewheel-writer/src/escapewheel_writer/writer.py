"""Stage, validate, and commit a packet (Part 05 §2).

- :class:`PacketWriter` -- collect records, arrays, references and payloads, then commit them as a
  validated packet or amend one.

A commit stages and validates everything under ``staging/``, promotes it, and renames the
manifest to ``packet.json`` last, so a reader finds a whole packet or none.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import time
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader import Manifest, Packet, check_sources, open_packet
from escapewheel_reader.location import SOURCES_FILENAME, SOURCES_VERSION
from escapewheel_reader.manifest import MANIFEST_FILENAME, MANIFESTS_DIRNAME
from escapewheel_reader.profile import PROFILE_ID
from escapewheel_reader.registries import declared_tables
from escapewheel_reader.registries import gunzip_member as gzip_member
from escapewheel_reader.resource_ids import CORE_INTERVALS, CORE_PREFERRED_RUNS, CORE_PROCESSING_RUNS, CORE_SESSIONS
from escapewheel_reader.uri import encode
from escapewheel_validator import (
    CheckedRegistryContext,
    Report,
    validate,
)
from escapewheel_validator.amendment import DERIVED, PROVENANCE, chain_reaches, semver
from escapewheel_validator.errors import OrderViolation

from . import opaque
from .amending import Held
from .arrow import build_table, number_batch, sort_key
from .bindings import ExternalArray, ExternalMedia, StagedArray, check_reference
from .documents import (
    VALIDATION_FAILED,
    VALIDATION_NOT_RUN,
    VALIDATION_PASSED,
    bump,
    first_version,
    sha256_of,
    writer_version,
)
from .encoding import inefficient
from .errors import (
    CommitRefused,
    NotCommitted,
    PayloadFault,
    PayloadProblem,
    PayloadRefused,
    UndeclaredResource,
    UsageError,
    UsageFault,
)
from .keys import Keys
from .layout import PROMOTED, REGISTRIES, STAGING, retained
from .promotion import act_on_promotion, claim, created, record_promotion, refuse_occupied
from .registries import Declarations
from .staging import check_parquet_floor, parquet_options, write_stream


class PacketWriter:
    """Collect records and commit them as a validated packet.

    Parameters
    ----------
    registry : Mapping
        The registry to write against. The packet binds and stores it (Part 04 §8, Part 03 §3.3), so the packet
        stays readable when the reference registry moves on.
    packet_id : str
        The packet's identifier.
    description : str, optional
        Human-readable description for the manifest.
    replaces : sequence of Mapping, optional
        The `replaces` items the manifest records, one per packet this one replaces (Part 04 §3). A
        packet naming one of its own `packet_id` is published at a major version above it.

    Examples
    --------
    >>> writer = PacketWriter(registry, packet_id="s001")  # doctest: +SKIP
    >>> writer.add("core.sessions", [{"session_id": "s001", ...}])  # doctest: +SKIP
    >>> report = writer.commit(Path("s001"))  # doctest: +SKIP
    """

    def __init__(
        self,
        registry: Mapping[str, Any] | CheckedRegistryContext,
        *,
        packet_id: str,
        description: str | None = None,
        extensions: Sequence[Mapping[str, Any] | CheckedRegistryContext] = (),
        session: str | None = None,
        encoding_exceptions: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
        workspace: str | Path | None = None,
        replaces: Sequence[Mapping[str, str]] = (),
    ) -> None:
        self._replaces = [dict(item) for item in replaces]
        #: Where delivered sources handed over their files, beside the packet rather than in it.
        #: Removed once a commit promotes, since every delivery has been read by then; kept on a
        #: refusal, with staging, as evidence of why.
        self._workspace = Path(workspace) if workspace is not None else None
        #: Encoding exceptions an extension supplies for its own tables, keyed list-name to
        #: resource to columns (`encoding.encodings`). Core names no extension table, so this is
        #: how one says what its measurements do without core being edited to know it exists.
        self._encoding_exceptions = dict(encoding_exceptions or {})
        #: What Part 03 §5.5's rules cost where they guessed wrong, reported at commit. A rule is a
        #: good guess and an exception is how it is corrected, so a column more than
        #: `encoding.TOLERANCE` off its best is said aloud rather than silently paid for.
        self._encoding_notes: list[str] = []
        #: The session every session-scoped table's rows belong to, which `_with_session` fills
        #: from (Part 02 §7.1). Given rather than read back out of `core.sessions`, because a build adds
        #: that table last, and reading it back would leave every table added before it unfilled.
        self._session = session
        self._declarations = Declarations(registry, extensions)
        #: Assigns the integer every identifier holds (Part 05 §4.3). One per packet, shared by every
        #: adapter, because two sources numbering the same probe differently is a defect no
        #: foreign key can see: both values resolve, to different rows.
        self.keys = Keys()
        self._packet_id = packet_id
        self._description = description
        self._tables: dict[str, list[Mapping[str, Any]]] = {}
        self._batches: dict[str, Iterable[pa.RecordBatch]] = {}
        #: Part 05 §15.5's retention policy, written into every manifest. One kept version and no age
        #: limit: a packet that is never amended retains nothing, and a packet is archival where
        #: a table is operational, so age alone never expires a manifest.
        self._retention: dict[str, Any] = {"keep_versions": 1}
        #: Part 04 §5.5: where each named source was read from, written to `sources.json` at commit.
        #: A record of where the writer looked, never a resolution rule binding a later reader --
        #: the same standing Part 03 §8 gives `digest` and `verified_at`.
        self._sources: dict[str, str] = {}
        #: Rows each resource was written with, filled as `_stage` writes them. A streamed
        #: table has no count until then, so anything reported earlier is the source's estimate.
        self.rows_written: dict[str, int] = {}
        #: Called with `say` once staging has run, for whatever only a written packet knows.
        self._after_stage: list[Callable[[Callable[[str], None]], None]] = []
        self._derived: dict[str, list[str]] = {}
        self._ordered: set[str] = set()
        self._staged_arrays: dict[str, StagedArray] = {}
        #: The staging area `stage_at` prepared, which `commit` keeps rather than clearing.
        self._prepared: Path | None = None
        self._referenced_arrays: dict[str, ExternalArray] = {}
        self._referenced_media: dict[str, ExternalMedia] = {}
        #: Packet-owned opaque resources as each source delivered them, bound at commit, once every
        #: source's catalog rows are in (Part 12 §5).
        self._payloads: list[opaque.StagedPayload] = []
        #: The packet version this writer amends, whose numbers seed `keys` and against whose rows
        #: every table settles (Part 05 §4.3), or None for a new packet.
        self._held: Held | None = None
        #: For an amendment, the packet root and the new version, which name a file that would
        #: otherwise overwrite one the packet holds (Part 03 §9).
        self._amending: tuple[Path, str] | None = None

    def amending(self, held: Held, *, prevail: bool = False) -> None:
        """Amend `held` rather than build a new packet (Part 05 §15).

        Its numbers are held before any is assigned, so a held name keeps its identifier and an
        added one is numbered after every held one, and each table is settled against its held rows
        when staged (Part 05 §4.3).

        Parameters
        ----------
        held : Held
            The packet version amended.
        prevail : bool, default False
            Keep the packet's session and subject rows whatever a source delivers, as an amending
            build does (Part 05 §3.6), rather than settling them like any other row.

        Raises
        ------
        AmendmentRefused
            If a held row owns an assigned identifier and gives it no name.
        """
        documents = self._declarations.documents
        declarations = {rid: decl for document in documents for rid, decl in document["resources"].items()}
        held.bind(
            {rid: table for document in documents for rid, table in declared_tables(document, strict=True).items()},
            {rid: str(decl.get("content_class")) for rid, decl in declarations.items()},
        )
        held.prevail = prevail
        held.seed(self.keys)
        self._held = held

    def name_apart(self, kind: str, name: str) -> str:
        """Return a name the packet this writer amends does not hold, `name` itself where it holds none."""
        return name if self._held is None else self._held.apart(kind, name)

    def declaration(self, declaration_id: str) -> Mapping[str, Any] | None:
        """Return one logical declaration from core or the owning extension."""
        return self._declarations.declaration(declaration_id)

    def spec(self, resource_id: str) -> Mapping[str, Any] | None:
        """Return the registry entry for one resource, core or extension, or None if undefined."""
        return self._declarations.spec(resource_id)

    def rows(self, resource_id: str) -> Sequence[Mapping[str, Any]]:
        """Return the records added for one table so far, in the order added.

        Empty for a table with none, and for one added as batches, whose rows no one holds.
        """
        return self._tables.get(resource_id, [])

    def _bind_catalog_row(
        self,
        declaration: Mapping[str, Any],
        resource_id: str,
        source_column: str,
        source_value: str,
    ) -> None:
        """Put packet identity on the one catalog row delivered for a payload."""
        instances = declaration["instances"]
        catalog = str(instances["catalog_resource"])
        resource_column = str(instances["resource_id_column"])
        rows = self._tables.get(catalog, [])
        matching = [row for row in rows if str(row.get(source_column)) == source_value]
        if len(matching) != 1:
            raise UsageError(
                f"{resource_id}: {catalog}.{source_column}={source_value!r} resolves {len(matching)} catalog rows",
                code=UsageFault.CATALOG_ROW_UNBOUND,
                where=resource_id,
            )
        current = matching[0].get(resource_column)
        if current is not None and current != resource_id:
            raise UsageError(
                f"{catalog}.{resource_column} is {current!r}, not delivered resource {resource_id!r}",
                code=UsageFault.CATALOG_ROW_TAKEN,
                where=resource_id,
            )
        matching[0][resource_column] = resource_id

    def add(self, resource_id: str, records: Sequence[Mapping[str, Any]]) -> None:
        """Add records for one table.

        Called more than once for the same resource, records accumulate; ordering is applied
        at commit, so an adapter may emit in whatever order is natural for its source.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID, e.g. ``core.trials``.
        records : sequence of Mapping
            Rows, whose keys the registry must declare.

        Raises
        ------
        UndeclaredResource
            If the registry does not define this resource.
        UsageError
            If a record carries a key no column declares, as `add_batches` refuses one, so the
            same adapter defect fails a build through either entry point.
        """
        spec = self.spec(resource_id)
        if spec is None:
            raise UndeclaredResource(
                f"no registry defines a table named {resource_id}; core and "
                f"{len(self._declarations.extensions)} extension(s) were consulted",
                resource_id=resource_id,
            )
        declared = {c["name"] for c in spec["columns"]}
        if undeclared := sorted({key for record in records for key in record} - declared):
            raise UsageError(
                f"{resource_id}: {undeclared} is declared by no registry this build loaded; "
                f"the column would be dropped silently",
                code=UsageFault.UNDECLARED_COLUMN,
                where=resource_id,
            )
        self._tables.setdefault(resource_id, []).extend(self._with_session(resource_id, records))

    def _with_session(self, resource_id: str, records: Sequence[Mapping[str, Any]]) -> Sequence[Mapping[str, Any]]:
        """Fill `session_id` on a session-scoped table's rows that omit it (Part 02 §7.1).

        Filled centrally rather than in each of the eight adapters, because the value is the
        session this build is for: Part 02 §7.1 puts it in the adapter the build constructed, and
        that is one value here. It is not inferred from a name, which Part 02 §7.1 forbids and
        Part 01 §3.5 forbids a consumer for the same reason.

        Only where the packet holds one session, so a multi-session build cannot be stamped with
        whichever session went first; there, an adapter states it and this does nothing. The
        session is the one the build was given; `core.sessions` is consulted first so a caller
        that stages it before anything else still governs.
        """
        spec = self.spec(resource_id) or {}
        wanted = any(c["name"] == "session_id" and c["presence"] == "required" for c in spec.get("columns", ()))
        if not wanted or resource_id == CORE_SESSIONS:
            return records
        declared = {r.get("session_id") for r in self._tables.get(CORE_SESSIONS, [])}
        declared.discard(None)
        if not declared and self._session is not None:
            declared = {self._session}
        if len(declared) != 1:
            return records
        session = next(iter(declared))
        return [r if r.get("session_id") is not None else {"session_id": session, **r} for r in records]

    def _session_batch(self, spec: Mapping[str, Any], batch: pa.RecordBatch) -> pa.RecordBatch:
        """Fill `session_id` on a streamed batch, as `_with_session` does for records (Part 02 §7.1).

        A table large enough to stream would otherwise reach validation with nulls in a required
        column. Filled as the session's *name*, so `number_batch` assigns it the same integer
        every other table's reference to `core.sessions` gets.
        """
        if self._session is None or "session_id" in batch.schema.names:
            return batch
        wanted = any(c["name"] == "session_id" and c["presence"] == "required" for c in spec.get("columns", ()))
        if not wanted:
            return batch
        return batch.append_column("session_id", pa.array([self._session] * batch.num_rows, type=pa.string()))

    def stamp(self, resource_id: str, match: str, values: Mapping[Any, Mapping[str, Any]]) -> int:
        """Set columns on rows already added, matched on one column's value.

        Named `stamp` rather than `amend` because :meth:`amend` is R32's packet amendment, which
        is a different operation on a different thing.

        R99 §3.2 is why this exists. The sync source learns which of a clock's terminal anchors
        it withheld only by reading that clock's pulses, and the sync adapter's `CONSUMES` runs the sorter
        first because the sync source needs the sorter's clocks to know which streams to anchor
        at all -- so the row the fact belongs on is already here when the fact becomes known.

        Adding a second row would collide on the primary key, and holding `core.clocks` back
        until every source has run would defer a table four adapters contribute to. Setting the
        columns is the narrow thing.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        match : str
            The column whose value identifies the row to change.
        values : Mapping
            Match value to the columns to set on the row carrying it.

        Returns
        -------
        int
            Rows changed, so a caller can tell a hit from a silent miss.

        Raises
        ------
        UndeclaredResource
            If the registry does not define this resource.
        """
        if self.spec(resource_id) is None:
            raise UndeclaredResource(f"no registry defines a table named {resource_id}", resource_id=resource_id)
        changed = 0
        for index, row in enumerate(self._tables.get(resource_id, [])):
            if (setting := values.get(row.get(match))) is not None:
                self._tables[resource_id][index] = {**row, **setting}
                changed += 1
        return changed

    def add_batches(self, resource_id: str, batches: Iterable[pa.RecordBatch]) -> None:
        """Add one table as a stream of Arrow record batches, written without buffering.

        The records path holds every row as a Python mapping until commit, which a spike
        table cannot survive: one AIND session is order 10^8 spikes, and a dict per row is
        two orders of magnitude more memory than the Parquet file it becomes. This path
        writes each batch straight through, so peak memory is one batch rather than one
        packet.

        The caller MUST yield batches already in the registry's declared sort order, since
        nothing here reorders them -- that is the point. Disorder is not silently accepted:
        the validator's physical-order check reads the staged file before the commit
        completes, which is where R12 §4 puts it.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        batches : iterable of pyarrow.RecordBatch
            Consumed once, at commit, before any table given to `add` is built. A generator is
            the expected shape, and keeps the source's rows out of memory until they are written.

        Raises
        ------
        UndeclaredResource
            If the registry does not define this resource.
        UsageError
            If this resource already has records, or already has batches. One table comes
            from one path; interleaving them would make the sort order unenforceable.
        """
        if self.spec(resource_id) is None:
            raise UndeclaredResource(
                f"no registry defines a table named {resource_id}; core and "
                f"{len(self._declarations.extensions)} extension(s) were consulted",
                resource_id=resource_id,
            )
        if resource_id in self._tables:
            raise UsageError(
                f"{resource_id} already has records; use one path per table",
                code=UsageFault.STAGED_TWICE,
                where=resource_id,
            )
        if resource_id in self._batches:
            raise UsageError(
                f"{resource_id} already has batches; concatenate before adding",
                code=UsageFault.STAGED_TWICE,
                where=resource_id,
            )
        spec = self.spec(resource_id)
        assert spec is not None
        self._batches[resource_id] = (number_batch(spec, self._session_batch(spec, b), self.keys) for b in batches)

    def after_staging(self, report: Callable[[Callable[[str], None]], None]) -> None:
        """Register something to be reported once the packet has been written.

        A streamed table's rows do not exist until `commit` consumes its generator, so anything
        a source learns while producing them -- how many there were, what it had to work around
        -- is not available at the point the source was run. Registering it here is what puts it
        in the build log and, for a compensation, in the packet's provenance.

        Parameters
        ----------
        report : callable
            Called with the commit's `say` after the first staging pass, before anything is
            derived. It may raise, which refuses the commit and leaves staging in place.
        """
        self._after_stage.append(report)

    def derives(self, resource_id: str, sources: Sequence[str]) -> None:
        """Record which resources one was derived from (Part 06).

        An analysis resource MUST declare lineage to core, and the manifest's `derived_from`
        is where it goes -- not a table, because the claim is about a resource and not about
        any row in it. Recording it here rather than inferring it keeps a derivation the
        writer cannot see, such as one made in another process, expressible.

        Any resource may be derived, a table or an array instance alike, so the resource need
        not exist yet; `commit` refuses lineage naming one the packet does not carry.

        Parameters
        ----------
        resource_id : str
            The derived resource.
        sources : sequence of str
            The resource IDs it came from.
        """
        self._derived.setdefault(resource_id, []).extend(sources)

    def _with_lineage(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Put each derived resource's `derived_from` on its manifest entry."""
        if missing := sorted(set(self._derived) - {e["resource_id"] for e in entries}):
            raise UsageError(
                f"lineage was recorded for {missing}, which this packet does not carry",
                code=UsageFault.LINEAGE_UNSTAGED,
                where=", ".join(missing),
            )
        for entry in entries:
            if lineage := self._derived.get(entry["resource_id"]):
                entry["derived_from"] = list(lineage)
        return entries

    def add_array(self, resource_id: str, array: StagedArray) -> None:
        """Add a dense array, to be written into the packet as Zarr v3.

        Packet-owned, so `zarr_v3` (Part 03 §6.1) -- v2 is permitted only for a resource the packet
        references rather than owns. Its own metadata states its codecs (Part 03 §6.4), so a reader
        checks this array's pipeline before opening it and must not refuse the packet over a codec
        used only by something it never touches.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID. Not a registry table: an array is described *by*
            `core.array_assets` and `core.array_dimensions`, which are added as records.
        array : StagedArray
            The values and the layout to write them in.

        Raises
        ------
        UsageError
            If this resource already has an array.
        """
        if resource_id in self._staged_arrays:
            raise UsageError(
                f"{resource_id} already has an array staged", code=UsageFault.STAGED_TWICE, where=resource_id
            )
        if array.resource_id != resource_id:
            raise UsageError(
                f"{resource_id}: staged array declares resource_id {array.resource_id!r}",
                code=UsageFault.RESOURCE_ID_DIFFERS,
                where=resource_id,
            )
        if not array.declaration_id:
            array = self._delivered_binding(resource_id, array)
        declaration = self._declarations.family(array.declaration_id, resource_id, "dense_array")
        self._bind_catalog_row(declaration, resource_id, "array_asset_id", array.array_asset_id)
        self._staged_arrays[resource_id] = array

    def _delivered_binding(self, resource_id: str, array: StagedArray) -> StagedArray:
        """Bind an array delivered by name to the one catalog row carrying that name (Part 12 §5).

        A delivery names an array's directory by the row's `resource_id` and says nothing else, so
        the row is found among every dense-array catalog, and the array takes that catalog's
        declaration and the row's own identifier.
        """
        matching = []
        for declaration_id in [d for document in self._declarations.documents for d in document["resources"]]:
            declaration = self.declaration(declaration_id)
            if declaration is None or declaration["kind"] != "dense_array":
                continue
            instances = declaration["instances"]
            if instances["mode"] != "catalog":
                continue
            column = str(instances["resource_id_column"])
            matching += [
                (declaration_id, row)
                for row in self._tables.get(str(instances["catalog_resource"]), [])
                if row.get(column) == resource_id
            ]
        if len(matching) != 1:
            raise UsageError(
                f"{resource_id}: a delivered array binds {len(matching)} catalog rows, not one",
                code=UsageFault.CATALOG_ROW_UNBOUND,
                where=resource_id,
            )
        declaration_id, row = matching[0]
        return replace(array, declaration_id=declaration_id, array_asset_id=str(row["array_asset_id"]))

    def reference_array(self, resource_id: str, array: ExternalArray) -> None:
        """Record a dense array the packet references rather than owns (Part 04 §5.1).

        No bytes are copied and none are read: structural validation must not reach the network
        (Part 04 §5.3), so what this records is a claim. A validator reports it as `info` in its
        default mode and checks it only when asked.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        array : ExternalArray
            The URI, its Zarr version, and whatever was verified.

        Raises
        ------
        UsageError
            If this resource already has an array, or if the URI does not match how it resolves:
            absolute where no `source` is named, relative where one is (Part 04 §5.5).
        """
        if resource_id in self._staged_arrays or resource_id in self._referenced_arrays:
            raise UsageError(f"{resource_id} already has an array", code=UsageFault.STAGED_TWICE, where=resource_id)
        array = replace(array, uri=check_reference(resource_id, array.uri, array.source))
        declaration = self._declarations.family(array.declaration_id, resource_id, "dense_array")
        self._bind_catalog_row(declaration, resource_id, "array_asset_id", array.array_asset_id)
        self._referenced_arrays[resource_id] = array

    def reference_media(self, resource_id: str, media: ExternalMedia) -> None:
        """Record a media asset the packet references rather than owns (Part 04 §5.1).

        No bytes are copied and none are read, exactly as `reference_array`: what this records is
        a claim about a URI, checked only in a mode that asks for it.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        media : ExternalMedia
            The URI, its container format, and whatever was verified.

        Raises
        ------
        UsageError
            If this resource already has media, or if the URI does not match how it resolves
            (Part 04 §5.5).
        """
        if resource_id in self._referenced_media:
            raise UsageError(f"{resource_id} already has media", code=UsageFault.STAGED_TWICE, where=resource_id)
        media = replace(media, uri=check_reference(resource_id, media.uri, media.source))
        declaration = self._declarations.family(media.declaration_id, resource_id, "opaque")
        self._bind_catalog_row(declaration, resource_id, "media_asset_id", media.media_asset_id)
        self._referenced_media[resource_id] = media

    def add_payloads(
        self, source: str, location: str | Path, *, owned: Collection[str] | None = None
    ) -> list[opaque.StagedPayload]:
        """Take every packet-owned opaque resource one source placed in its `opaque_location` (Part 12 §5).

        Bound at commit rather than here, since the catalog row a payload binds to may come from a
        source that runs later.

        Parameters
        ----------
        source : str
            The delivering source, which every refusal names.
        location : str or Path
            The `opaque_location` the build supplied that source.
        owned : collection of str, optional
            The resources the recipe leaves this source owning (Part 05 §3.4). Given, a payload for
            a singleton declaration outside it is refused at commit.

        Returns
        -------
        list of StagedPayload
            The payloads found, one per resource directory.

        Raises
        ------
        PayloadRefused
            If the location holds anything but resource directories each holding one payload of
            regular files and nonempty directories under representable names.
        """
        found = opaque.read(source, location, owned)
        self._payloads.extend(found)
        return found

    def _bind_payloads(self) -> list[tuple[opaque.StagedPayload, str]]:
        """Bind each payload by its resource directory's name, refusing before anything is validated.

        A name binds the catalog row of an opaque catalog family carrying it, or otherwise the opaque
        singleton declaration it names (Part 12 §5). Every opaque catalog row must be bound, and
        no resource ID twice, whether by two payloads or by a payload and a referenced resource.

        Returns
        -------
        list of tuple
            Each payload and the declaration ID it binds to.

        Raises
        ------
        PayloadRefused
            Naming each directory and resource ID that binds no resource, binds two, is bound twice,
            or is a singleton the recipe does not leave its source owning.
        """
        families, singletons = self._declarations.opaque()
        rows: dict[str, list[str]] = {}
        unbound: list[PayloadProblem] = []
        for declaration_id, (catalog, column) in sorted(families.items()):
            for row in self._tables.get(catalog, []):
                value = row.get(column)
                if value is None:
                    shown = {k: v for k, v in row.items() if k != "metadata"}
                    unbound.append(
                        PayloadProblem(
                            PayloadFault.ROW_UNNAMED,
                            f"a {catalog} row carries no {column}, so nothing binds it: {shown}",
                        )
                    )
                    continue
                rows.setdefault(str(value), []).append(declaration_id)
        referenced = {*self._referenced_media, *self._referenced_arrays}
        problems: list[PayloadProblem] = []
        bound: list[tuple[opaque.StagedPayload, str]] = []
        by_id: dict[str, list[opaque.StagedPayload]] = {}
        for payload in self._payloads:
            resource_id, where = payload.resource_id, opaque.shown(payload.path.parent)
            by_id.setdefault(resource_id, []).append(payload)
            matched, singleton = rows.get(resource_id, []), resource_id in singletons
            if matched and singleton:
                problems.append(
                    PayloadProblem(
                        PayloadFault.ROW_AND_SINGLETON,
                        f"{payload.source}: {where} names {resource_id}, which is both a catalog row's resource_id "
                        "and an opaque singleton declaration",
                    )
                )
            elif singleton:
                if payload.owned is not None and resource_id not in payload.owned:
                    problems.append(
                        PayloadProblem(
                            PayloadFault.SINGLETON_NOT_OWNED,
                            f"{payload.source}: delivers a payload for opaque singleton {resource_id}, which the "
                            f"recipe does not leave {payload.source} owning (Part 05 §3.4)",
                        )
                    )
                bound.append((payload, resource_id))
            elif len(matched) == 1:
                bound.append((payload, matched[0]))
            elif matched:
                problems.append(
                    PayloadProblem(
                        PayloadFault.SEVERAL_ROWS,
                        f"{payload.source}: {where} names {resource_id}, which {len(matched)} catalog rows carry",
                    )
                )
            else:
                problems.append(
                    PayloadProblem(
                        PayloadFault.BINDS_NOTHING,
                        f"{payload.source}: {where} names {resource_id}, which is the resource_id of no catalog row "
                        "of an opaque catalog family and the ID of no opaque singleton declaration",
                    )
                )
        for resource_id, payloads in sorted(by_id.items()):
            places = ", ".join(f"{p.source} at {opaque.shown(p.path.parent)}" for p in payloads)
            if len(payloads) > 1:
                problems.append(
                    PayloadProblem(
                        PayloadFault.DELIVERED_TWICE,
                        f"{resource_id} is delivered as a payload {len(payloads)} times: {places}",
                    )
                )
            if resource_id in referenced:
                problems.append(
                    PayloadProblem(
                        PayloadFault.DELIVERED_AND_REFERENCED,
                        f"{resource_id} is delivered both as a payload ({places}) and as a referenced resource",
                    )
                )
        delivered = set(by_id) | referenced
        unbound += [
            PayloadProblem(
                PayloadFault.ROW_UNBOUND,
                f"{families[declaration_id][0]} row with resource_id {resource_id} is bound by no payload or "
                "referenced resource",
            )
            for resource_id, declarations in sorted(rows.items())
            for declaration_id in declarations
            if resource_id not in delivered
        ]
        if refused := [*problems, *unbound]:
            raise PayloadRefused("; ".join(p.message for p in refused) + " (Part 12 §5)", problems=refused)
        return bound

    @property
    def resources(self) -> list[str]:
        """Resource IDs with at least one record, in insertion order."""
        return [*self._tables, *self._batches]

    def _stage_arrays(self, staging: Path) -> list[dict[str, Any]]:
        """Write every staged array under `staging` and return its manifest entries."""
        if not self._staged_arrays:
            return []
        from .arrays import write_zarr

        entries = []
        for resource_id, spec in self._staged_arrays.items():
            declaration_id = spec.declaration_id
            relative = self._relative("arrays", resource_id, "zarr")
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if spec.written is not None:
                # Delivered: the adapter wrote it, so staging moves it rather than writing it
                # again, and what the manifest says about it is read off the array (Part 12 §5).
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(spec.written), str(path))
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            else:
                if spec.dimension_names is None:
                    spec = replace(spec, dimension_names=self._dimension_names(spec))
                size = write_zarr(path, spec)
            entries.append(
                {
                    "resource_id": resource_id,
                    "declaration_id": declaration_id,
                    "uri": encode(relative.split("/")),
                    "validation_state": VALIDATION_NOT_RUN,
                    "size_bytes": size,
                    "digest": sha256_of(path),
                }
            )
        return entries

    def _dimension_names(self, spec: StagedArray) -> tuple[str, ...] | None:
        """Return a staged array's axis names from its axes records, or None where it has none."""
        declaration = self.declaration(spec.declaration_id) or {}
        axes = (declaration.get("array") or {}).get("axes_resource")
        rows = sorted(
            (r for r in self._tables.get(str(axes), []) if str(r.get("array_asset_id")) == spec.array_asset_id),
            key=lambda r: int(r["axis_index"]),
        )
        return tuple(str(r["dimension_name"]) for r in rows) or None

    def _stage_payloads(self, staging: Path, bound: Sequence[tuple[opaque.StagedPayload, str]]) -> list[dict[str, Any]]:
        """Move each bound payload's resource directory under `staging` and return its manifest entries.

        The directory holds its payload alone, so moving it whole publishes the payload under its own
        name in a directory holding nothing else (Part 03 §11), and promotion is then one rename.
        """
        entries = []
        for payload, declaration_id in bound:
            directory = staging / opaque.ROOT / payload.resource_id
            directory.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(payload.path.parent), str(directory))
            staged = directory / payload.path.name
            entries.append(
                {
                    "resource_id": payload.resource_id,
                    "declaration_id": declaration_id,
                    "uri": encode((opaque.ROOT, payload.resource_id, payload.path.name)),
                    "validation_state": VALIDATION_NOT_RUN,
                    "size_bytes": opaque.size(staged),
                    "digest": sha256_of(staged),
                }
            )
        return entries

    def _reference_media(self) -> list[dict[str, Any]]:
        """Return a manifest entry per referenced media asset. Copies nothing and reads nothing."""
        entries = []
        for resource_id, media in self._referenced_media.items():
            declaration_id = media.declaration_id
            entry = {
                "resource_id": resource_id,
                "declaration_id": declaration_id,
                "uri": media.uri,
                "validation_state": VALIDATION_NOT_RUN,
                "external": True,
            }
            for name in ("source", "digest", "size_bytes", "verified_at"):
                if (value := getattr(media, name)) is not None:
                    entry[name] = dict(value) if name == "digest" else value
            entries.append(entry)
        return entries

    def _reference_arrays(self) -> list[dict[str, Any]]:
        """Return a manifest entry per referenced array. Copies nothing and reads nothing."""
        entries = []
        for resource_id, array in self._referenced_arrays.items():
            declaration_id = array.declaration_id
            entry = {
                "resource_id": resource_id,
                "declaration_id": declaration_id,
                "uri": array.uri,
                "validation_state": VALIDATION_NOT_RUN,
                "external": True,
            }
            for name in ("source", "digest", "size_bytes", "verified_at"):
                if (value := getattr(array, name)) is not None:
                    entry[name] = dict(value) if name == "digest" else value
            if array.members is not None:
                entry["members"] = [dict(member) for member in array.members]
            entries.append(entry)
        return entries

    def _stage(self, staging: Path, only: Collection[str] | None = None) -> list[dict[str, Any]]:
        """Write every table under `staging` and return its manifest entries.

        Records in `_ordered` the resources whose physical order `write_stream` established as
        it wrote them, so the commit that follows need not read them back to learn it.
        """
        entries = []
        if only is None:
            self._ordered = set()
        self._preassign()
        # Streams first, so a held row may record what a stream only knows once consumed, such
        # as a materializer's count of the spikes it could not place.
        for resource_id in sorted(self.resources, key=lambda r: r not in self._batches):
            if only is not None and resource_id not in only:
                continue
            spec = self.spec(resource_id)
            assert spec is not None
            relative = self._relative("tables", resource_id, "parquet")
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if resource_id in self._batches:
                batches = self._batches[resource_id]
                # A restage writes afresh, and an amendment adding nothing must leave no file.
                path.unlink(missing_ok=True)
                if self._held is not None:
                    batches = self._held.settle_stream(resource_id, batches, derived=self._derived)
                try:
                    self.rows_written[resource_id] = write_stream(
                        spec,
                        batches,
                        path,
                        resource_id,
                        self._encoding_exceptions,
                        self._encoding_notes,
                    )
                except OrderViolation as exc:
                    # Naming the table, because the streaming path writes through untouched and
                    # the caller is what has to be fixed: a message about two rows says nothing
                    # about which of a packet's forty tables they came from.
                    exc.resource_id = resource_id
                    raise
                if sort_key(resource_id, spec):
                    self._ordered.add(resource_id)
                if not path.exists():
                    # Nothing the amendment adds, so the held entry stands (Part 05 §4.3).
                    continue
            else:
                built = build_table(
                    resource_id, spec, self._tables[resource_id], self.keys, self._paired_kinds(resource_id)
                )
                table = built if self._held is None else self._held.settle(resource_id, built, derived=self._derived)
                if table is None:
                    continue
                self.rows_written[resource_id] = table.num_rows
                # No `row_group_size`: pyarrow's default is min(rows, 2**20), which puts each
                # of these tables in one row group, and that is the right answer — they are
                # smaller than a single object-storage fetch and are read whole, so splitting
                # one only adds requests and duplicates its string dictionary.
                #
                # Sizing a row group for the fetch band is a mistake on both paths. See
                # `encoding.STREAMED_BATCH_ROWS` for the streaming case; here the trap is that estimating
                # from `Table.nbytes` is 320x out on a string-heavy table, because Arrow
                # materialises strings that Parquet stores as dictionary codes.
                options = parquet_options(resource_id, spec, table.schema, self._encoding_exceptions, table)
                pq.write_table(table, path, **options)
                delta = list(options.get("column_encoding", {}))
                kept = set(options.get("use_dictionary", table.schema.names))
                self._encoding_notes.extend(
                    inefficient(
                        resource_id,
                        table,
                        delta,
                        [n for n in table.schema.names if n not in kept and n not in delta],
                    )
                )
            check_parquet_floor(path)
            entry: dict[str, Any] = {
                "resource_id": resource_id,
                "declaration_id": resource_id,
                "uri": encode(relative.split("/")),
                "validation_state": VALIDATION_NOT_RUN,
            }
            entry["digest"] = sha256_of(path)
            entries.append(entry)
        return entries

    def _relative(self, folder: str, resource_id: str, suffix: str) -> str:
        """Return where a resource is written, apart from any file the amended packet holds (Part 03 §9)."""
        namespace, name = resource_id.split(".", 1)
        relative = f"{folder}/{namespace}/{name}.{suffix}"
        if self._amending is not None and (self._amending[0] / relative).exists():
            relative = f"{folder}/{namespace}/{name}.{self._amending[1]}.{suffix}"
        return relative

    def _prefer_added_runs(self) -> None:
        """Prefer each run an amendment adds to the scope of a run the packet holds (Part 05 §12).

        A run of an activity other than `import` sharing its session, activity, `scope_kind` and
        `scope` with a held run is an alternative to it, and the one added is preferred unless a
        preference of that key is already delivered, as a recipe declares one (Part 05 §3.1).
        """
        if self._held is None:
            return
        held = self._held
        scopes = {
            (run["session_id"], run["activity_type"], run["scope_kind"], run["scope"])
            for run in held.named_rows(CORE_PROCESSING_RUNS, self.keys)
            if run.get("scope") is not None and run["activity_type"] != "import"
        }
        held_runs = held.held_names.get("processing_run_id", set())
        preferred = {
            (row.get("session_id", self._session), row["activity_type"], row["scope_kind"], row["scope"])
            for row in self._tables.get(CORE_PREFERRED_RUNS, [])
        }
        adding = []
        for run in self._tables.get(CORE_PROCESSING_RUNS, []):
            name = str(run["processing_run_id"])
            if name in held_runs or run.get("activity_type") == "import":
                continue
            key = (run.get("session_id", self._session), run["activity_type"], run.get("scope_kind"), run.get("scope"))
            if key in scopes and key not in preferred:
                preferred.add(key)
                adding.append(
                    {
                        "session_id": key[0],
                        "activity_type": key[1],
                        "scope_kind": key[2],
                        "scope": key[3],
                        "processing_run_id": name,
                        "reason": "the amendment adds this run to the scope of a run the packet holds (Part 05 §12)",
                    }
                )
        if adding:
            self.add(CORE_PREFERRED_RUNS, adding)

    def _preassign(self) -> None:
        """Assign a number to every name this packet uses, before any table is built (Part 05 §4.3).

        Numbering as each table is staged would let the order tables happen to be written in
        decide the numbers: `core.sessions` names a `reference_clock_id` and is staged before
        `core.clocks`, so the clocks would be numbered by the session's mention of one of them.
        Two builds of the same sources must produce the same packet, which is what lets a rebuild
        be compared to what it replaced -- and that has to hold across tables, not only within one.
        """
        pending: dict[str, set[str]] = {}
        for resource_id, rows in sorted(self._tables.items()):
            spec = self.spec(resource_id)
            if spec is None:
                continue
            target = {
                column: referenced
                for ref in spec.get("references", [])
                for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
            }
            paired = self._paired_kinds(resource_id)
            for column in spec["columns"]:
                name = column["name"]
                if column.get("role") != "identifier" or column.get("identity") != "assigned":
                    continue
                for r in rows:
                    if r.get(name) is not None:
                        kind = (paired[name](r) if name in paired else None) or target.get(name, name)
                        pending.setdefault(kind, set()).add(str(r[name]))
        for kind in sorted(pending):
            if kind == "interval_id":
                continue
            for value in sorted(pending[kind]):
                self.keys.of(kind, value)
        # Part 02 §12.9 numbers intervals by session, kind, clock and bounds, which only their rows
        # hold, so the rows order the names; a name no interval row carries is an orphan and follows.
        for row in sorted(self._tables.get(CORE_INTERVALS, []), key=self._interval_order):
            self.keys.of("interval_id", str(row["interval_id"]))
        for value in sorted(pending.get("interval_id", ())):
            self.keys.of("interval_id", value)

    def _interval_order(self, row: Mapping[str, Any]) -> tuple[int, str, int, int, int, str]:
        """Return where one `core.intervals` row falls in Part 02 §12.9's numbering."""
        return (
            self.keys.of("session_id", str(row["session_id"])),
            str(row["interval_kind"]),
            self.keys.of("clock_id", str(row["clock_id"])),
            int(row["start_tick"]),
            int(row["stop_tick"]),
            str(row["interval_id"]),
        )

    def _paired_kinds(self, resource_id: str) -> dict[str, Callable[[Mapping[str, Any]], str | None]]:
        """Map each identifier paired value on a table to the numbering its row's kind names.

        Part 02 §8.3 lets an identifier hold the key of whichever resource its row's discriminator
        names, so its map is chosen per row: the named resource's one key column, which is the map
        that resource numbers its own key in. The kind is read off the records, which still hold
        names, so a value on a specialised table reaches its discriminator row by the names its
        reference carries.
        """
        found: dict[str, Callable[[Mapping[str, Any]], str | None]] = {}
        documents = self._declarations.documents
        for owner, table in ((n, t) for doc in documents for n, t in declared_tables(doc, strict=True).items()):
            for column in table["columns"]:
                if column.get("role") != "discriminator" or column.get("discriminates") is None:
                    continue
                via = column.get("discriminates_via")
                holder = owner if via is None else str(via).rsplit(".", 1)[0]
                if holder != resource_id:
                    continue
                found[column["discriminates"]] = self._kind_reader(owner, column["name"], resource_id)
        return found

    def _kind_reader(self, owner: str, discriminator: str, holder: str) -> Callable[[Mapping[str, Any]], str | None]:
        """Return a function from a `holder` row to the key column of the resource its kind names."""

        def key_of(resource: Any) -> str | None:
            spec = self.spec(str(resource)) if resource is not None else None
            key = list((spec or {}).get("primary_key") or [])
            return key[0] if len(key) == 1 else None

        if owner == holder:
            return lambda row: key_of(row.get(discriminator))
        spec = self.spec(holder) or {}
        reference = next((r for r in spec.get("references", []) if r["resource"] == owner), None)
        if reference is None:
            return lambda row: None
        ours, theirs = list(reference["columns"]), list(reference["resource_columns"])
        kinds = {tuple(str(r.get(c)) for c in theirs): r.get(discriminator) for r in self._tables.get(owner, [])}
        return lambda row: key_of(kinds.get(tuple(str(row.get(c)) for c in ours)))

    def _manifest(
        self,
        entries: Sequence[Mapping[str, Any]],
        registries: Mapping[str, Mapping[str, str]],
        report: Report | None,
    ) -> dict[str, Any]:
        """Build the manifest for these resources, binding the registries `_store_registries` wrote."""
        sessions = sorted({r["session_id"] for r in self._tables.get(CORE_SESSIONS, []) if "session_id" in r})
        now = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
        validation = {
            "status": VALIDATION_NOT_RUN
            if report is None
            else (VALIDATION_PASSED if report.passed else VALIDATION_FAILED),
            "validated_at": now,
            "validator_name": "escapewheel_validator",
            "validator_version": writer_version(),
        }
        manifest: dict[str, Any] = {
            "packet_id": self._packet_id,
            "packet_version": first_version(self._packet_id, self._replaces),
            "profile_id": PROFILE_ID,
            "semantic_standard_version": self._declarations.core["semantic_standard_version"],
            "logical_standard_version": self._declarations.core["logical_standard_version"],
            "registries": {name: dict(descriptor) for name, descriptor in registries.items()},
            "created_at": now,
            "sessions": sessions,
            "resources": [dict(e) for e in entries],
            # Part 05 §15.5: declared rather than left to a default, because `prune` reads it and a
            # packet that says nothing makes the operator's policy invisible to the operation.
            "retention": dict(self._retention),
            "validation": validation,
        }
        if self._description is not None:
            manifest["description"] = self._description
        if self._replaces:
            manifest["replaces"] = [dict(item) for item in self._replaces]
        return manifest

    def declare_source(self, name: str, uri: str) -> None:
        """Record where a named body of referenced data was read from (Part 04 §5.5).

        An adapter that references bytes belonging to a nameable asset calls this once and then
        gives each resource a `source` and a path relative to it. What the packet stores is the
        name; where it is goes to `sources.json`, which is not a packet resource and may be
        corrected when a mirror moves.

        Parameters
        ----------
        name : str
            The source's identifier, as resource entries will spell it.
        uri : str
            Where this writer read it.
        """
        self._sources[name] = uri

    def _sources_document(self) -> dict[str, Any] | None:
        """Return Part 04 §5.5's default resolution document, or None where no resource names a source.

        None rather than an empty document, since a document locating nothing is worse than
        none -- it would answer a lookup the caller meant to answer itself. Written before the
        manifest, because Part 05 §6 makes publishing the manifest what makes a commit visible.

        Raises
        ------
        UsageError
            If the document would not satisfy its schema, which a writer MUST NOT write (Part 04
            §5.5). Raised before anything is promoted.
        """
        located = {
            referenced.source: {"uri": self._sources[referenced.source]}
            for referenced in (*self._referenced_arrays.values(), *self._referenced_media.values())
            if referenced.source is not None and referenced.source in self._sources
        }
        if not located:
            return None
        document = {
            "$schema": "https://escapewheel.org/schemas/sources/0.1.0",
            "sources_standard_version": SOURCES_VERSION,
            "description": f"Where {self._packet_id} read its referenced data. Editable: not a packet resource.",
            "sources": dict(sorted(located.items())),
        }
        if problems := check_sources(document):
            raise UsageError(
                f"the source resolution document would not satisfy its schema: {'; '.join(problems)}",
                code=UsageFault.SOURCES_DOCUMENT,
            )
        return document

    def stage_at(self, root: str | Path) -> Path:
        """Prepare, empty, the staging area `commit` or `amend` will use at `root`, and return it.

        For a build pointing deliveries there before any source runs, so the commit moves what they
        wrote by rename (Part 12 §5) and keeps it rather than clearing it.

        Raises
        ------
        PacketOccupied
            If `root` already holds a committed manifest and this writer amends none.
        PromotionRecordUnreadable
            If the staging area holds a promotion record this writer cannot read.
        """
        root = Path(root)
        act_on_promotion(root)
        if self._held is None:
            refuse_occupied(root)
        self._prepared = None
        staging = self._staging(root)
        self._prepared = staging.resolve()
        return staging

    def _staging(self, root: Path) -> Path:
        """Return the staging area at `root`: the one `stage_at` prepared, or a new empty one."""
        staging = root / STAGING
        if staging.resolve() != self._prepared:
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir(parents=True)
        return staging

    def commit(
        self,
        root: str | Path,
        *,
        limits: Mapping[str, Any] | None = None,
        say: Callable[[str], None] = lambda _: None,
        materialize: Sequence[Callable[[Any, PacketWriter], None]] = (),
    ) -> Report:
        """Stage, derive, validate, and commit.

        Parameters
        ----------
        root : str or Path
            The packet root. Created if absent; an existing packet is refused rather than
            overwritten, because immutability covers packet-owned bytes (Part 03 §8.1).
        limits : Mapping, optional
            DuckDB settings bounding validation, passed through to the validator. The default
            of 4 GB is not enough for every packet: a uniqueness check over 10^8 rows can
            exhaust it even with somewhere to spill, and the finding then reports that the
            check could not run rather than that the data is wrong.
        say : callable, optional
            Progress reporter, called with the elapsed time of each stage. A commit is the
            long half of an import and the three stages cost very differently, so a caller
            deciding where to spend effort should not have to guess which one it is in.
        materialize : sequence of callable, optional
            Run after the core resources are staged and before anything is validated, each
            given the staged packet and this writer. Derived resources are staged alongside the
            rest and validated with them, so the packet is complete at its first version.

        Returns
        -------
        Report
            The validation report. Warnings do not prevent a commit; errors do.

        Raises
        ------
        PacketOccupied
            If `root` already holds a committed manifest.
        UsageError
            If no `core.sessions` records were added.
        CommitRefused
            If validation found errors. Nothing is committed, and staging and the delivery
            workspace are left in place.
        PromotionRecordUnreadable
            If the staging area holds a promotion record this writer cannot read.
        """
        root = Path(root)
        act_on_promotion(root)
        refuse_occupied(root)
        # R1 §6 makes the session inventory part of the manifest and the schema requires it
        # non-empty. Refusing here beats letting the staged manifest fail its own schema,
        # which surfaces as an unhelpful error from a directory the caller never named.
        if not self._tables.get(CORE_SESSIONS):
            raise UsageError(
                "a packet declares at least one session; core.sessions is empty (R1 §6)", code=UsageFault.NO_SESSION
            )

        # Before anything is written, since binding needs only the rows and refuses outright.
        payloads = self._bind_payloads()
        staging = self._staging(root)

        # 1. staged resources, plus the registry they were written against
        clock = time.perf_counter()
        entries = self._with_lineage(
            [
                *self._stage(staging),
                *self._stage_arrays(staging),
                *self._stage_payloads(staging, payloads),
                *self._reference_arrays(),
                *self._reference_media(),
            ]
        )
        say(f"staged {len(entries)} resources in {time.perf_counter() - clock:.1f} s")
        # Part 03 §5.5's rules are good guesses, and a column one guesses wrong
        # about is said aloud rather than silently paid for. A report, not a refusal: every
        # encoding is permitted (Part 03 §5.5), so the packet is conforming whichever it got.
        for note in sorted(set(self._encoding_notes)):
            say(f"  encoding: {note}")
        for report in self._after_stage:
            report(say)
        clock = time.perf_counter()
        registries, _ = self._store_registries(staging)

        # 2. derive whatever the caller asked for from the staged packet, before anything is
        #    validated or promoted. Part 05 §8 puts materialization inside the import
        #    pipeline, and a staged packet is already openable -- it needs a manifest, which is
        #    written here anyway. Doing it now costs one validation over the finished packet;
        #    doing it after the commit costs a second manifest, a version bump and a
        #    revalidation of resources validated seconds earlier, which is what `amend` is for
        #    and what a build the recipe fully describes should never pay.
        (staging / MANIFEST_FILENAME).write_text(json.dumps(self._manifest(entries, registries, None), indent=2) + "\n")
        if materialize:
            # Row counts, not just names: a materializer adds its own `core.processing_runs`
            # row (Part 06 §5), and that table was staged in the pass above. Restaging only what is
            # new would leave the run record in memory and the resource pointing at a run the
            # packet does not contain -- which is exactly what the validator then says.
            def counts() -> dict[str, int]:
                return {r: len(self._tables.get(r, ())) for r in self.resources}

            before = counts()
            for derive in materialize:
                derive(open_packet(staging), self)
                say(f"derived {', '.join(sorted(set(self.resources) - set(before)))}")
                before = {**before, **{r: n for r, n in counts().items() if r not in before}}
            touched = {r for r, n in counts().items() if n != before.get(r, -1) or r not in before}
            touched |= set(self.resources) - {e["resource_id"] for e in entries}
            restaged = self._stage(staging, only=touched)
            kept = [e for e in entries if e["resource_id"] not in touched]
            entries = self._with_lineage([*kept, *restaged])
            (staging / MANIFEST_FILENAME).write_text(
                json.dumps(self._manifest(entries, registries, None), indent=2) + "\n"
            )
            say(f"staged {len(restaged)} derived or updated resource(s) in {time.perf_counter() - clock:.1f} s")
            clock = time.perf_counter()
        # Scan the order of everything except what `write_stream` compared on the way in.
        # Not a shortcut around the check: the same comparison ran, over the same rows, from
        # the same code, one step earlier (R12 §4 still governs where it lives).
        staged = {e["resource_id"] for e in entries}
        report = validate(open_packet(staging), limits=limits, scan=staged - self._ordered)
        say(f"validated in {time.perf_counter() - clock:.1f} s")
        clock = time.perf_counter()
        if not report.passed:
            raise CommitRefused(report, staging)

        # 3. record every path promotion creates, then move into final paths, the resolution
        #    document first since it alone can still fail
        sources = self._sources_document()
        promoted = [name for name in PROMOTED if (staging / name).exists()]
        creates = [*promoted, *([SOURCES_FILENAME] if sources is not None else []), f"{MANIFEST_FILENAME}.candidate"]
        claim(root, creates)
        record_promotion(staging, str(self._manifest(entries, registries, None)["packet_version"]), creates)
        if sources is not None:
            # At the root so a copy carries it, and outside the manifest so a moved mirror is fixed by
            # editing it in place (Part 04 §5.5).
            (root / SOURCES_FILENAME).write_text(json.dumps(sources, indent=2) + "\n")
        for entry in entries:
            entry["validation_state"] = VALIDATION_PASSED
        for name in promoted:
            shutil.move(str(staging / name), str(root / name))

        # 4. rename the manifest last: until this line the root holds no manifest at all,
        #    so a reader finds nothing rather than a partial import claiming to be valid.
        candidate = root / f"{MANIFEST_FILENAME}.candidate"
        candidate.write_text(json.dumps(self._manifest(entries, registries, report), indent=2) + "\n")
        os.replace(candidate, root / MANIFEST_FILENAME)
        shutil.rmtree(staging)
        if self._workspace is not None and self._workspace.exists():
            shutil.rmtree(self._workspace)
        say(f"promoted in {time.perf_counter() - clock:.1f} s")
        return report

    def amend(
        self,
        root: str | Path,
        *,
        packet_version: str | None = None,
        limits: Mapping[str, Any] | None = None,
        say: Callable[[str], None] = lambda _: None,
        materialize: Sequence[Callable[[Any, PacketWriter], None]] = (),
    ) -> Report:
        """Publish what this writer holds as a new version of a committed packet (Part 05 §15).

        Each table settles against the packet's rows as it is staged (Part 05 §4.3), so what is
        written adds groups of rows the packet lacks and changes no row it holds, and a resource
        the packet names is written to a new file (Part 03 §9). Everything is staged and validated,
        against the superseded version too (Part 05 §15.6), before anything reaches a final path,
        and `packet.json` is replaced by an atomic rename last, so a reader sees the old version or
        the new one.

        Parameters
        ----------
        root : str or Path
            A packet root holding a committed manifest.
        packet_version : str, optional
            The new version. Defaults to bumping the patch component.
        limits : Mapping, optional
            DuckDB settings bounding validation, as for `commit`.
        say : callable, optional
            Progress reporter, as for `commit`.
        materialize : sequence of callable, optional
            As for `commit`, each given the staged amended packet, so a derived resource is derived
            from what the new version holds and replaces the one the packet names (Part 05 §8).

        Returns
        -------
        Report
            The validation report for the whole packet, not only what was added (Part 05 §15.4).

        Raises
        ------
        NotCommitted
            If `root` holds no committed manifest. Use `commit` to create a packet.
        AmendmentRefused
            If a delivered row would change or grow what the packet holds, which is a new packet
            rather than a new version of this one (Part 05 §15.2).
        UsageError
            If `packet_version` does not sort after the packet's, or has another major version.
        CommitRefused
            If validation found errors. The packet stays at its previous version, and nothing
            was written outside the staging area.
        PromotionRecordUnreadable
            If the staging area holds a promotion record this writer cannot read.
        """
        root = Path(root)
        act_on_promotion(root)
        if not (root / MANIFEST_FILENAME).is_file():
            raise NotCommitted(f"{root} holds no committed {MANIFEST_FILENAME}; use commit() to create a packet")
        if self._held is None:
            self.amending(Held.open(root))
        held = self._held
        assert held is not None
        superseded = dict(held.manifest)
        version = packet_version or bump(str(superseded["packet_version"]))
        if semver(version) <= semver(str(superseded["packet_version"])):
            raise UsageError(
                f"packet_version {version} does not sort after {superseded['packet_version']} (Part 05 §15.1)",
                code=UsageFault.VERSION_NOT_AFTER,
            )
        if semver(version)[0] != semver(str(superseded["packet_version"]))[0]:
            raise UsageError(
                f"packet_version {version} leaves the major version of {superseded['packet_version']}; "
                "a greater major version is a replacement, not an amendment (Part 05 §15.1)",
                code=UsageFault.VERSION_MAJOR_CHANGED,
            )
        self._amending = (root, version)
        try:
            return self._amend(root, held, superseded, version, limits, say, materialize)
        finally:
            held.close()
            self._amending = None

    def _amend(
        self,
        root: Path,
        held: Held,
        superseded: Mapping[str, Any],
        version: str,
        limits: Mapping[str, Any] | None,
        say: Callable[[str], None],
        materialize: Sequence[Callable[[Any, PacketWriter], None]],
    ) -> Report:
        """Stage, derive, validate and promote an amendment; `amend` without its preparation."""
        payloads = [
            (payload, declaration)
            for payload, declaration in self._bind_payloads()
            if not self._held_instance(payload.resource_id, declaration)
        ]
        for instances in (self._staged_arrays, self._referenced_arrays, self._referenced_media):
            for resource_id in [r for r, i in instances.items() if self._held_instance(r, i.declaration_id)]:
                del instances[resource_id]
        staging = self._staging(root)

        clock = time.perf_counter()
        self._prefer_added_runs()
        entries = self._with_lineage(
            [
                *self._stage(staging),
                *self._stage_arrays(staging),
                *self._stage_payloads(staging, payloads),
                *self._reference_arrays(),
                *self._reference_media(),
            ]
        )
        say(f"staged {len(entries)} resources in {time.perf_counter() - clock:.1f} s")
        for note in sorted(set(self._encoding_notes)):
            say(f"  encoding: {note}")
        for report in self._after_stage:
            report(say)
        clock = time.perf_counter()
        # Before validation, since the validator acquires each registry through the candidate's
        # descriptor (Part 04 §10); one the packet does not yet store is bound under staging/.
        registries, added_registries = self._store_registries(root, staging=staging)

        def candidate(staged: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
            """Return the amended manifest with every written resource still under staging/."""
            written = {e["resource_id"] for e in staged}
            amended = dict(superseded)
            amended["packet_version"] = version
            amended["registries"] = registries
            amended["resources"] = [
                *(e for e in superseded["resources"] if e["resource_id"] not in written),
                *(e if e.get("external") else dict(e, uri=f"{STAGING}/{e['uri']}") for e in staged),
            ]
            if self._description is not None:
                amended["description"] = self._description
            return amended

        if materialize:

            def counts() -> dict[str, int]:
                return {r: len(self._tables.get(r, ())) for r in self.resources}

            before = counts()
            for derive in materialize:
                derive(Packet(root, Manifest.from_dict(candidate(entries))), self)
                self._prefer_added_runs()
                say(f"derived {', '.join(sorted(set(self.resources) - set(before)))}")
                before = {**before, **{r: n for r, n in counts().items() if r not in before}}
            touched = {r for r, n in counts().items() if n != before.get(r, -1) or r not in before}
            touched |= set(self.resources) - {e["resource_id"] for e in entries}
            restaged = self._stage(staging, only=touched)
            entries = self._with_lineage([*(e for e in entries if e["resource_id"] not in touched), *restaged])
            say(f"staged {len(restaged)} derived or updated resource(s) in {time.perf_counter() - clock:.1f} s")
            clock = time.perf_counter()

        amended = candidate(entries)
        amended["resources"] = self._without_stale(amended["resources"], entries)
        written = {e["resource_id"] for e in entries}
        report = validate(
            Packet(root, Manifest.from_dict(amended)),
            limits=limits,
            scan=written - self._ordered,
            recheck=written,
            superseded=superseded,
        )
        say(f"validated in {time.perf_counter() - clock:.1f} s")
        clock = time.perf_counter()
        if not report.passed:
            raise CommitRefused(report, staging)

        moved = [e["uri"] for e in entries if not e.get("external")]
        copies = [
            f"{MANIFESTS_DIRNAME}/{retained(manifest)}"
            for manifest in (superseded, amended)
            if not (root / MANIFESTS_DIRNAME / retained(manifest)).exists()
        ]
        creates = {created(root, relative) for relative in (*moved, *added_registries, *copies)}
        creates |= {f"{MANIFEST_FILENAME}.candidate"}
        claim(root, creates)
        record_promotion(staging, version, creates)
        for relative in (*moved, *added_registries):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging / relative), str(destination))
        by_id = {e["resource_id"]: e for e in entries}
        amended["resources"] = [
            dict(by_id[e["resource_id"]], validation_state=VALIDATION_PASSED) if e["resource_id"] in by_id else e
            for e in amended["resources"]
        ]
        amended["registries"] = {
            name: dict(bound, path=str(bound["path"]).removeprefix(f"{STAGING}/")) for name, bound in registries.items()
        }
        amended["validation"] = {
            "status": VALIDATION_PASSED,
            "validated_at": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "validator_name": "escapewheel_validator",
            "validator_version": writer_version(),
        }

        body = (json.dumps(amended, indent=2) + "\n").encode()
        self._retain(root, superseded, amended, body)
        candidate_path = root / f"{MANIFEST_FILENAME}.candidate"
        candidate_path.write_bytes(body)
        os.replace(candidate_path, root / MANIFEST_FILENAME)
        shutil.rmtree(staging)
        if self._workspace is not None and self._workspace.exists():
            shutil.rmtree(self._workspace)
        say(f"promoted in {time.perf_counter() - clock:.1f} s")
        return report

    def _held_instance(self, resource_id: str, declaration_id: str) -> bool:
        """Whether a canonical catalog instance is one the amended packet already names.

        Its catalog row then equals the held one or is refused as it settles, so the held instance
        stands and the delivered copy is dropped with its row (Part 05 §4.3).
        """
        held = self._held
        return held is not None and resource_id in held.entries and held.canonical(declaration_id)

    def _without_stale(
        self, resources: Sequence[Mapping[str, Any]], written: Sequence[Mapping[str, Any]]
    ) -> list[Mapping[str, Any]]:
        """Drop each derived resource the amendment neither wrote nor left current (Part 05 §15.2).

        One whose `derived_from` chain reaches a canonical table the amendment wrote, other than a
        provenance table, was derived from rows that are no longer all the packet holds.
        """
        held = self._held
        assert held is not None
        rewritten = {e["resource_id"] for e in written}
        sources = {r for r in rewritten if held.canonical(r) and r not in PROVENANCE}
        chains = {e["resource_id"]: e for e in resources}
        stale = {
            e["resource_id"]
            for e in resources
            if e["resource_id"] not in rewritten
            and held.classes.get(str(e.get("declaration_id", e["resource_id"]))) in DERIVED
            and chain_reaches(chains, e["resource_id"], sources)
        }
        return [e for e in resources if e["resource_id"] not in stale]

    def _retain(
        self, root: Path, superseded: Mapping[str, Any], amended: Mapping[str, Any], amended_body: bytes
    ) -> None:
        """Keep the exact bytes of every manifest a packet has had (Part 05 §15.3).

        A superseded file is only interpretable if the manifest that named it still exists;
        without these, an orphan and a stray are indistinguishable and a recorded `digest` points
        at a state nothing can reconstruct. Exact, because a replacement names a version by the
        SHA-256 of its manifest (Part 04 §3).
        """
        versions = root / MANIFESTS_DIRNAME
        versions.mkdir(exist_ok=True)
        for manifest, body in ((superseded, (root / MANIFEST_FILENAME).read_bytes()), (amended, amended_body)):
            path = versions / retained(manifest)
            # An existing copy is the one an earlier amendment retained, and retained bytes are
            # not rewritten.
            if not path.exists():
                path.write_bytes(body)

    def _store_registries(
        self, root: Path, *, staging: Path | None = None
    ) -> tuple[dict[str, dict[str, str]], list[str]]:
        """Store core and every extension as Part 03 §3.3 requires, returning their descriptors.

        The digest covers the exact serialized bytes (Part 04 §10). A registry ID and version that
        the packet's current or a retained manifest already binds is reused where the digest
        matches and refused where it differs (Part 05 §15.3), so every manifest keeps naming bytes
        that exist.

        Parameters
        ----------
        root : Path
            Where the registries are bound: the staged packet for a commit, the packet for an
            amendment.
        staging : Path, optional
            For an amendment, where a registry the packet does not yet store is written instead,
            its descriptor pointing there until promotion moves it (Part 05 §6).

        Returns
        -------
        dict
            A descriptor per registry ID, for the manifest's `registries`.
        list of str
            The root-relative final path of each registry written under `staging`.
        """
        recorded: dict[tuple[str, str], Mapping[str, str]] = {}
        for manifest_path in [root / MANIFEST_FILENAME, *sorted((root / MANIFESTS_DIRNAME).glob("*.json"))]:
            if manifest_path.is_file():
                for name, bound in json.loads(manifest_path.read_text()).get("registries", {}).items():
                    recorded.setdefault((name, bound["version"]), bound)
        descriptors: dict[str, dict[str, str]] = {}
        added: list[str] = []
        for document in self._declarations.documents:
            registry_id = str(document["registry_id"])
            body = (json.dumps(document, indent=2) + "\n").encode()
            version = str(document["registry_version"])
            digest = hashlib.sha256(body).hexdigest()
            earlier = recorded.get((registry_id, version))
            relative = earlier["path"] if earlier else f"{REGISTRIES}/{registry_id}/{version}.json.gz"
            path = root / relative
            stored = hashlib.sha256(gzip_member(path.read_bytes())).hexdigest() if path.is_file() else None
            bound = relative
            if (earlier is not None and earlier["sha256"] != digest) or stored not in {None, digest}:
                raise UsageError(
                    f"this packet already binds a different {registry_id} {version} at {relative}; two digests "
                    "under one registry ID and version cannot both be retained (Part 05 §15.3). Bump registry_version.",
                    code=UsageFault.REGISTRY_DIGEST_DIFFERS,
                    where=relative,
                )
            if stored is None:
                if staging is not None:
                    path = staging / relative
                    bound = f"{staging.relative_to(root).as_posix()}/{relative}"
                    added.append(relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(gzip.compress(body, mtime=0))
            descriptors[registry_id] = {
                "role": "extension" if "extension_id" in document else "core",
                "version": version,
                "path": bound,
                "sha256": digest,
            }
        return descriptors, added


__all__ = ["PacketWriter"]

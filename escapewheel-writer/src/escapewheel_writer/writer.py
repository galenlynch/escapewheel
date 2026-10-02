"""Stage, validate, and commit a packet (Part 05 §2).

- :class:`PacketWriter` -- collect records, arrays, references and payloads, then commit them as a
  validated packet or amend one.

A commit stages and validates everything under ``staging/``, promotes it, and renames the
manifest to ``packet.json`` last, so a reader finds a whole packet or none.
"""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.manifest import MANIFEST_FILENAME
from escapewheel_reader.registries import declared_tables
from escapewheel_reader.resource_ids import CORE_PREFERRED_RUNS, CORE_PROCESSING_RUNS, CORE_SESSIONS
from escapewheel_reader.uri import encode
from escapewheel_validator import (
    CheckedRegistryContext,
    Report,
)
from escapewheel_validator.amendment import semver
from escapewheel_validator.errors import OrderViolation

from . import opaque
from .amending import Held
from .arrow import build_table, number_batch, sort_key
from .attachments import Attachments
from .bindings import ExternalArray, ExternalMedia, ExternalResource, StagedArray
from .documents import (
    bump,
    manifest,
    resource_entry,
    sources_document,
    with_lineage,
)
from .encoding import inefficient
from .errors import (
    CommitRefused,
    NotCommitted,
    UndeclaredResource,
    UsageError,
    UsageFault,
)
from .keys import Keys
from .layout import STAGING
from .numbering import paired_kinds, preassign
from .promotion import act_on_promotion, claim, record_promotion, refuse_occupied
from .publication import CANDIDATE, Amendment, NewPacket
from .registries import Declarations
from .secrets import without_userinfo
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
        self._attachments = Attachments(self._declarations, self.rows)
        #: The staging area `stage_at` prepared, which `commit` keeps rather than clearing.
        self._prepared: Path | None = None
        #: The packet version this writer amends, whose numbers seed `keys` and against whose rows
        #: every table settles, or None for a new packet.
        self._held: Held | None = None

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
        session this build is for: that section puts it in the adapter the build constructed, and
        that is one value here. It is not inferred from a name, which it forbids and
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

        Named `stamp` rather than `amend` because :meth:`amend` is Part 05 §15.1's packet amendment, which
        is a different operation on a different thing.

        Part 02 §12.6's terminal-anchor record is why this exists. The sync source learns which of a
        clock's terminal anchors it withheld only by reading that clock's pulses, and its `CONSUMES` runs the sorter
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
        completes (Part 05 §5.3).

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
        self._attachments.add_array(resource_id, array)

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
        self._attachments.reference_array(resource_id, array)

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
        self._attachments.reference_media(resource_id, media)

    def reference_resource(self, resource_id: str, resource: ExternalResource) -> None:
        """Record an opaque resource the packet references, of a catalog keyed on `resource_id`.

        No bytes are copied and none are read, exactly as `reference_media`. The catalog row whose
        `resource_id` is `resource_id` is the one it binds (Part 04 §5.1).

        Parameters
        ----------
        resource_id : str
            Dotted resource ID, which a catalog row of `resource.declaration_id`'s catalog carries.
        resource : ExternalResource
            The declaration it instantiates, the URI, and whatever was verified.

        Raises
        ------
        UsageError
            If this resource is already referenced, if no one catalog row carries its ID, or if the
            URI does not match how it resolves (Part 04 §5.5).
        """
        self._attachments.reference_resource(resource_id, resource)

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
        return self._attachments.add_payloads(source, location, owned=owned)

    @property
    def resources(self) -> list[str]:
        """Resource IDs with at least one record, in insertion order."""
        return [*self._tables, *self._batches]

    def _stage(
        self, staging: Path, place: Callable[[str, str, str], str], only: Collection[str] | None = None
    ) -> list[dict[str, Any]]:
        """Write every table under `staging` and return its manifest entries.

        `place` returns where a resource is written under the packet root, given its folder,
        its resource ID and its suffix; `only` limits the pass to those resources.

        Records in `_ordered` the resources whose physical order `write_stream` established as
        it wrote them, so the commit that follows need not read them back to learn it.
        """
        entries = []
        if only is None:
            self._ordered = set()
        preassign(self._tables, self._declarations, self.keys)
        # Streams first, so a held row may record what a stream only knows once consumed, such
        # as a materializer's count of the spikes it could not place.
        for resource_id in sorted(self.resources, key=lambda r: r not in self._batches):
            if only is not None and resource_id not in only:
                continue
            spec = self.spec(resource_id)
            assert spec is not None
            relative = place("tables", resource_id, "parquet")
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
                    resource_id,
                    spec,
                    self._tables[resource_id],
                    self.keys,
                    paired_kinds(self._tables, self._declarations, resource_id),
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
            entries.append(resource_entry(resource_id, resource_id, encode(relative.split("/")), owned=path))
        return entries

    def _prefer_added_runs(self, held: Held | None) -> None:
        """Prefer each run an amendment adds to the scope of a run `held` holds (Part 05 §12).

        A run of an activity other than `import` sharing its session, activity, `scope_kind` and
        `scope` with a held run is an alternative to it, and the one added is preferred unless a
        preference of that key is already delivered, as a recipe declares one (Part 05 §3.1).
        """
        if held is None:
            return
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

    def _manifest(
        self,
        entries: Sequence[Mapping[str, Any]],
        registries: Mapping[str, Mapping[str, str]],
        report: Report | None,
    ) -> dict[str, Any]:
        """Build this packet's manifest for these resources and the registries stored for them."""
        return manifest(
            entries,
            registries,
            report,
            packet_id=self._packet_id,
            core=self._declarations.core,
            sessions=self.rows(CORE_SESSIONS),
            retention=self._retention,
            description=self._description,
            replaces=self._replaces,
        )

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
            Where this writer read it. Its userinfo, where it states any, is not written (Part 05 §7).
        """
        self._sources[name] = without_userinfo(uri)

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
        # Part 04 §3 makes the session inventory part of the manifest and the schema requires it
        # non-empty. Refusing here beats letting the staged manifest fail its own schema,
        # which surfaces as an unhelpful error from a directory the caller never named.
        if not self._tables.get(CORE_SESSIONS):
            raise UsageError(
                "a packet declares at least one session; core.sessions is empty", code=UsageFault.NO_SESSION
            )

        return self._publish(
            NewPacket(root, manifest=self._manifest, sources=self._sources_document), limits, say, materialize
        )

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
        try:
            target = Amendment(root, held, superseded, version, description=self._description)
            return self._publish(target, limits, say, materialize)
        finally:
            held.close()

    def _sources_document(self) -> dict[str, Any] | None:
        """Return the resolution document for the sources this packet's references name, or None."""
        return sources_document(self._packet_id, self._sources, self._attachments.referenced)

    def _publish(
        self,
        target: NewPacket | Amendment,
        limits: Mapping[str, Any] | None,
        say: Callable[[str], None],
        materialize: Sequence[Callable[[Any, PacketWriter], None]],
    ) -> Report:
        """Stage, derive, validate and promote what this writer holds, as a new packet or an amendment."""
        root = target.root
        # Before anything is written, since binding needs only the rows and refuses outright.
        payloads = target.delivered(self._attachments)
        staging = self._staging(root)

        # 1. staged resources, plus the registries they were written against
        clock = time.perf_counter()
        self._prefer_added_runs(target.held)
        entries = with_lineage(
            [
                *self._stage(staging, target.place),
                *self._attachments.stage_arrays(staging, target.place),
                *self._attachments.stage_payloads(staging, payloads),
                *self._attachments.array_entries(),
                *self._attachments.media_entries(),
                *self._attachments.resource_entries(),
            ],
            self._derived,
        )
        say(f"staged {len(entries)} resources in {time.perf_counter() - clock:.1f} s")
        # Part 03 §5.5's rules are good guesses, and a column one guesses wrong
        # about is said aloud rather than silently paid for. A report, not a refusal: every
        # encoding is permitted, so the packet is conforming whichever it got.
        for note in sorted(set(self._encoding_notes)):
            say(f"  encoding: {note}")
        for report_staged in self._after_stage:
            report_staged(say)
        clock = time.perf_counter()
        registries = target.bind_registries(self._declarations.documents)

        # 2. derive whatever the caller asked for from the staged packet, before anything is
        #    validated or promoted. Part 05 §8 puts materialization inside the import
        #    pipeline. Doing it now costs one validation over the finished packet;
        #    doing it after the commit costs a second manifest, a version bump and a
        #    revalidation of resources validated seconds earlier, which is what `amend` is for
        #    and what a build the recipe fully describes should never pay.
        target.describe(entries, registries)
        if materialize:
            # Row counts, not just names: a materializer adds its own `core.processing_runs`
            # row (Part 06 §5), and that table was staged in the pass above. Restaging only what is
            # new would leave the run record in memory and the resource pointing at a run the
            # packet does not contain -- which is exactly what the validator then says.
            def counts() -> dict[str, int]:
                return {r: len(self._tables.get(r, ())) for r in self.resources}

            before = counts()
            for derive in materialize:
                derive(target.staged(), self)
                self._prefer_added_runs(target.held)
                say(f"derived {', '.join(sorted(set(self.resources) - set(before)))}")
                before = {**before, **{r: n for r, n in counts().items() if r not in before}}
            touched = {r for r, n in counts().items() if n != before.get(r, -1) or r not in before}
            touched |= set(self.resources) - {e["resource_id"] for e in entries}
            restaged = self._stage(staging, target.place, only=touched)
            kept = [e for e in entries if e["resource_id"] not in touched]
            entries = with_lineage([*kept, *restaged], self._derived)
            target.describe(entries, registries)
            say(f"staged {len(restaged)} derived or updated resource(s) in {time.perf_counter() - clock:.1f} s")
            clock = time.perf_counter()
        # Scan the order of everything except what `write_stream` compared on the way in.
        # Not a shortcut around the check: the same comparison ran, over the same rows, from
        # the same code, one step earlier.
        written = {e["resource_id"] for e in entries}
        report = target.validate(limits=limits, scan=written - self._ordered)
        say(f"validated in {time.perf_counter() - clock:.1f} s")
        clock = time.perf_counter()
        if not report.passed:
            raise CommitRefused(report, staging)

        # 3. record every path promotion creates, then move into final paths
        creates = target.creates()
        claim(root, creates)
        record_promotion(staging, target.version, creates)
        target.promote(report)

        # 4. rename the manifest last, so a reader sees the packet as it was or as it now is
        os.replace(root / CANDIDATE, root / MANIFEST_FILENAME)
        shutil.rmtree(staging)
        if self._workspace is not None and self._workspace.exists():
            shutil.rmtree(self._workspace)
        say(f"promoted in {time.perf_counter() - clock:.1f} s")
        return report


__all__ = ["PacketWriter"]

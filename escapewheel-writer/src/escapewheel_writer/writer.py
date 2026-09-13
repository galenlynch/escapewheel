"""Stage, validate, and commit a packet.

Part 05's core principle is that **validation is importation**: copying or converting bytes is
only staging, and a resource is not imported until it has passed the checks for its schema.
This module is the writer and committer halves of that pipeline. It knows nothing about NWB,
SpikeInterface, or any other source -- adapters hand it records, and it turns them into a
packet or refuses to.

The commit sequence is Part 05 Stage 5's, and its ordering is the whole guarantee:

1. write staged resources under ``staging/``;
2. validate them there;
3. move them into their final paths;
4. rename the manifest to ``packet.json`` **last**.

Until step 4 the packet root holds no manifest, so a reader finds nothing rather than
finding a partial import that claims to be valid.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader import Manifest, Packet, open_packet
from escapewheel_validator import Report, validate, verify_order
from escapewheel_validator.generate import adjacency_settles_uniqueness

from .arrow import build, number_batch, schema, sort_key
from .encoding import encodings, inefficient
from .keys import Keys


def _standard_version(registry: Mapping[str, Any]) -> str:
    """Return the logical standard version a schema ID carries, e.g. `0.1` in `core.trials.v0.1`.

    From `logical_standard_version`, not `registry_version`: a schema ID names the standard the
    table conforms to, and the registry may be revised -- a column added, an order overridden --
    without the logical standard moving.
    """
    return str(registry["logical_standard_version"]).rsplit("-v", 1)[-1]


def _version() -> str:
    """Read this package's version without importing it at module scope."""
    from . import __version__

    return __version__


#: Where a manifest lives once committed (Part 04).
MANIFEST = "packet.json"

#: Part 04 §5.5's default source resolution document. Written at the packet root and **not** a packet
#: resource: under the root so a copy carries it, outside the manifest so Part 04 §5.1's immutability
#: does not reach it and a moved mirror is fixed by editing it in place.
SOURCES = "sources.json"

#: The version of that document this writer emits (Part 04 §5.5).
SOURCES_VERSION = "escapewheel-sources-v0.1"

#: Where a packet embeds the registry it was written against (Part 02 §9.2).
REGISTRY_PATH = "schemas/logical_schemas.json"
#: Where an extension registry lives in a packet (Part 09 §2, Part 09 §6).
EXTENSIONS_PATH = "extensions"

#: Part 03's portable profile.
PROFILE = "escapewheel-portable-v0.1"


#: Columns whose resource must not dictionary-encode them, by resource ID. Deliberately not in
#: the registry: R30 §3.3 leaves encoding and row-group size non-normative, because the right
#: values follow from session length and unit count rather than from the schema.
#:
#: `analysis.spike_events` is 98.8% `t_tick`, and a dictionary over near-unique int64 ticks is
#: the worst option measured at every row-group size -- the writer builds a dictionary nearly as
#: large as the column, overflows the page limit, abandons it mid-column, and emits both.
#: Measured in `conformance/parquet-probe/real.py`.
#: Columns that store better as deltas than as anything pyarrow chooses by itself, beyond the
#: `_tick` rule below, because measurement says so and their names do not. `anchor_index`
#: ascends over thousands of anchors per clock; `n_spikes` is a large count with no repeats.
def _options(resource_id: str, spec: Mapping[str, Any], out: pa.Schema,
             extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Parquet settings for one resource.

    **No page index.** `ColumnIndex` and `OffsetIndex` would give per-page bounds and byte
    offsets, letting pages behave like the chunks inside a Zarr shard — but unlike a shard index,
    nothing obliges a reader to read one, and neither DuckDB nor pyarrow does. DuckDB says so
    outright (duckdb#2755, closed as "not supported… mostly improves point queries which is not
    what DuckDB is focused on") and measures identically with it and without; pyarrow prunes at
    row-group granularity too. arrow-rs, DataFusion and Spark would use it, and it costs only
    0.9 MB on a 682 MB table — but a packet rebuilds from its recipe in 90 seconds, so carrying
    an unexercised feature buys less than turning it on when a reader needs it. pyarrow defaults
    it off, which is where this leaves it. See `session.BATCH_ROWS` for the row-group half.

    `sorting_columns` is written for every table that declares an order. It costs nothing, and
    it is what lets a file state which of several possible orderings it is in rather than
    leaving a reader to infer it from statistics. It is only truthful because both write paths
    produce the declared order: the records path sorts in `arrow.build`, and the streaming path
    is checked by the validator's physical-order shim (R12 §4) before the commit completes.
    """
    options: dict[str, Any] = {"compression": "zstd"}
    # A caller may hand over a column as dictionary codes rather than decoding what Parquet is
    # about to re-encode. Parquet has no dictionary type -- the column is BYTE_ARRAY/String
    # either way -- so the only thing that would record the choice is the Arrow schema pyarrow
    # stores as metadata, and storing it would make the file advertise a type the registry does
    # not declare. Withhold it, and the file reads back as the registry says.
    if any(pa.types.is_dictionary(field.type) for field in out):
        options["store_schema"] = False
    delta, plain = encodings(resource_id, spec, out, extra)
    if delta or plain:
        options["use_dictionary"] = [n for n in out.names if n not in {*delta, *plain}]
        if delta:
            options["column_encoding"] = dict.fromkeys(delta, "DELTA_BINARY_PACKED")
    keys = sort_key(resource_id, spec) or []
    if columns := [pq.SortingColumn(out.names.index(k)) for k in keys if k in out.names]:
        options["sorting_columns"] = columns
    return options


#: Batches held ahead of the Parquet writer. Building a batch and encoding one cost about the
#: same — 2.5 s and 2.6 s for a 23 M-spike stream — so serially a stream pays both and one
#: worker ahead overlaps them. The depth is a memory budget, not a throughput knob, and one is
#: where the two part company. Measured staging 287 M spikes: serial 62.0 s at 2,365 MiB,
#: depth 1 50.1 s at 2,682 MiB, depth 2 49.1 s at 2,845 MiB, depth 3 47.9 s at 3,042 MiB.
#: Double-buffering takes 84% of the available time for half the memory of the alternatives;
#: output is byte-identical at every depth.
PREFETCH = 1


def _prefetch(batches: Iterable[pa.RecordBatch], depth: int = PREFETCH) -> Iterator[pa.RecordBatch]:
    """Yield batches while the next is built on a worker thread.

    The producer's exception is re-raised in the consumer rather than lost in the thread, so a
    source that fails mid-stream still refuses the commit instead of truncating it silently.
    """
    queue: Queue[Any] = Queue(maxsize=depth)
    done = object()

    def produce() -> None:
        try:
            for batch in batches:
                queue.put(batch)
        except BaseException as exc:  # noqa: BLE001 - handed to the consumer, not swallowed
            queue.put(exc)
        else:
            queue.put(done)

    worker = Thread(target=produce, daemon=True)
    worker.start()
    try:
        while (item := queue.get()) is not done:
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        worker.join(timeout=0)


def _as_held(out: pa.Schema, held: pa.Schema) -> pa.Schema:
    """Take the registry's schema, but keep a column the caller already holds as codes.

    Decoding a dictionary here would only hand Parquet strings it is about to dictionary-encode
    again. The value type must still match what the registry declares; only the encoding is the
    caller's to choose.
    """
    fields = []
    for field in out:
        carried = held.field(field.name).type if field.name in held.names else None
        if carried is not None and pa.types.is_dictionary(carried) and carried.value_type == field.type:
            field = field.with_type(carried)
        fields.append(field)
    return pa.schema(fields)


def _write_stream(spec: Mapping[str, Any], batches: Iterable[pa.RecordBatch], path: Path,
                  resource_id: str, extra: Mapping[str, Any] | None = None,
                  report: list[str] | None = None) -> int:
    """Write batches to Parquet one row group at a time, casting each to the registry schema.

    The first batch fixes the schema, exactly as the first record does on the records path:
    an optional column is emitted when something carries it. A later batch may omit a
    declared column -- it is written as nulls, like a record that lacks the key -- but may
    not introduce one the schema does not have, because that column would be dropped without
    a word.

    An empty stream writes nothing and leaves no file, matching the records path, where a
    resource with no rows is simply absent from the packet.

    Returns the rows written, which is the only count of a streamed table anything holds: a
    generator's length is not knowable before it has run.

    Each batch becomes exactly one row group, so the caller controls row-group boundaries as
    well as order. That is what lets `analysis.spike_events` keep every row group inside a
    single time bucket (Part 03 §5.4) — cutting at a fixed row count instead would let a group
    straddle two buckets and span twice the intended time range — and it is what lets a caller
    size row groups for the store the packet will live on.
    """
    writer: pq.ParquetWriter | None = None
    out: pa.Schema | None = None
    written = 0
    try:
        # Verified on the way in, not read back afterwards. The rows pass through here
        # already sorted by the source, so comparing them costs the comparison alone, where
        # establishing the same fact from the written file costs re-reading its sort columns --
        # 467 MB on a quarter of a billion spikes. It runs inside the producer thread, so the
        # comparison overlaps the Parquet encoding rather than adding to it. `commit` tells the
        # validator which resources this settled; a validator handed an unknown packet still
        # reads every one.
        keys = sort_key(resource_id, spec) or []
        unique = spec["primary_key"] if keys and adjacency_settles_uniqueness(resource_id, spec) else None
        # Three stages, not two: building a batch, comparing it and encoding it cost 2.5 s,
        # 2.2 s and 2.6 s on a 23 M-spike stream, so folding the comparison into the producer
        # made it the bottleneck and gave back exactly what skipping the re-read saved. A queue
        # either side of it lets all three run at once, and the slowest one sets the pace.
        for batch in _prefetch(_prefetch(verify_order(batches, keys, unique)) if keys else batches):
            if out is None:
                out = _as_held(schema(spec, set(batch.schema.names)), batch.schema)
                options = _options(resource_id, spec, out, extra)
                writer = pq.ParquetWriter(path, out, **options)
                if report is not None:
                    report.extend(inefficient(resource_id, pa.Table.from_batches([batch]),
                                              options.get("column_encoding", {}) and
                                              list(options["column_encoding"]) or [],
                                              [n for n in out.names
                                               if n not in options.get("use_dictionary", out.names)
                                               and n not in options.get("column_encoding", {})]))
            if extra := sorted(set(batch.schema.names) - set(out.names)):
                # Two causes reach here and they send an author to different files: a column the
                # registry never declared, and an optional one the first batch lacked so `schema`
                # left it out. The check fires on the first batch too, where only the first is
                # possible, so a message naming only the second described the rarer case.
                declared = {c["name"] for c in spec["columns"]}
                said = []
                if undeclared := [n for n in extra if n not in declared]:
                    said.append(f"{undeclared} is declared by no registry this build loaded")
                if late := [n for n in extra if n in declared]:
                    said.append(f"{late} is optional and absent from the first batch")
                raise ValueError(
                    f"{resource_id}: {'; '.join(said)}; the column would be dropped silently"
                )
            columns = [
                batch.column(name) if name in batch.schema.names else pa.nulls(batch.num_rows, field.type)
                for name, field in zip(out.names, out, strict=True)
            ]
            assert writer is not None
            # `row_group_size` is load-bearing, not decoration: left to pyarrow it defaults to
            # 2**20 rows and silently cuts a larger batch into several row groups, which would
            # break the boundary guarantee this docstring makes.
            writer.write_batch(pa.record_batch(columns, schema=out), row_group_size=batch.num_rows)
            written += batch.num_rows
    finally:
        if writer is not None:
            writer.close()
    return written


#: Core tables an amendment may extend (Part 03 §9.2). Append-only by nature: a row records that
#: something ran, and a later run does not change what an earlier one did.
PROVENANCE = ("core.processing_runs", "core.source_files", "core.processing_run_inputs")

#: Where superseded manifests are retained (Part 03 §9.3).
MANIFESTS = "manifests"


def _bump(version: str) -> str:
    """Return the next packet version.

    Patch level, so a packet under development stays inside one minor series while the
    structure moves. Part 03 §9.1 requires only that the new version sort strictly after the
    superseded one, and §8 leaves what it *means* open, so nothing here rests on the choice.
    """
    major, minor, patch, *_ = (*version.split("."), "0", "0", "0")
    return f"{int(major)}.{int(minor)}.{int(patch) + 1}"


class NotCommitted(Exception):
    """There is no committed packet at this root to amend."""


@dataclass(frozen=True)
class StagedArray:
    """A dense array to write into the packet, with the layout it should take.

    Measured on 6,781 unit waveforms (`conformance/zarr-probe/waveforms.py`): the chunk should
    be the unit of the question, the shard keeps that from becoming one file per chunk, and
    the compressor belongs *inside* the shard -- wrapping a shard in an outer codec disables
    the partial read it exists for, at a cost of 324x.
    """

    values: Any
    array_asset_id: str
    chunks: tuple[int, ...]
    shard: tuple[int, ...] | None = None
    codecs: tuple[str, ...] = ("blosc",)
    fill_value: Any = 0


@dataclass(frozen=True)
class ExternalArray:
    """A dense array the packet references rather than owns (Part 04 §5.1).

    Referencing is the expected form for a large one. Copying duplicates the bulk of a dataset
    for no gain, and transcoding to the portable floor throws away the acquisition's own
    compression -- 5.8 GB of LFP across twelve probes, against three integers per series once
    R20 replaces its timestamps.

    `sha256`, `size_bytes`, `members` and `verified_at` record what was true when someone
    looked, not a promise about now: immutability covers packet-owned bytes only (Part 03 §8),
    and an external array may change or vanish without the packet changing at all.

    `members` is Part 04 §5.4's record of what the prefix held, each entry carrying whatever the
    store said about itself. It is a record and not a resolution rule -- a reader hands the URI
    to Zarr, which addresses chunks by key and never enumerates.
    """

    array_asset_id: str
    uri: str
    #: Part 04 §5.5: the body of data these bytes belong to. Where set, `uri` is a path relative to
    #: wherever that source turns out to be rather than a location, and a resolution document
    #: says where that is.
    source: str | None = None
    physical_profile: str = "zarr_v3"
    codecs: tuple[str, ...] = ()
    sha256: str | None = None
    size_bytes: int | None = None
    verified_at: str | None = None
    members: tuple[dict[str, Any], ...] | None = None


@dataclass(frozen=True)
class ExternalMedia:
    """An image or video the packet references rather than owns (Part 04 §5.1).

    The same bargain `ExternalArray` makes, for the same reason: three behaviour cameras of one
    session are 10 GB as MP4 and 80 GB as the AVI they were encoded from, so a packet that copied
    them would be mostly video. What the packet owns instead is the timing -- one row per frame
    in `core.media_frames`, on a declared clock -- which is what makes the video addressable and
    is the part no player can supply.

    `sha256`, `size_bytes` and `verified_at` record what was true when someone looked (R14
    §2.3.1), not a promise about now.
    """

    media_asset_id: str
    uri: str
    format: str
    #: Part 04 §5.5, as on `ExternalArray`.
    source: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    verified_at: str | None = None


def _check_reference(resource_id: str, uri: str, source: str | None) -> None:
    """Refuse a referenced URI that does not match how it will be resolved (Part 04 §5.1, Part 04 §5.5).

    Absolute where the entry names no source, because a relative one would resolve against a
    packet the bytes do not live in. Relative where it names one, because the source supplies
    the part in front and an absolute URI there would ignore it.
    """
    if source is None:
        if "://" not in uri:
            raise ValueError(f"{resource_id}: {uri!r} is not absolute, so it cannot resolve without the packet")
    elif "://" in uri:
        raise ValueError(f"{resource_id}: {uri!r} is absolute, so naming source {source!r} would have no effect")


def _digest(path: Path) -> str:
    """Part 04 §5.4: what the packet says its own bytes are.

    Recorded for every packet-owned resource and not optional, because the promise it makes
    checkable is not optional either: Part 04 §5.1 declares these bytes immutable and Part 03 §9.4 spends
    that, bounding revalidation after an amendment to what the amendment wrote. Costs 0.5% of a
    build -- the bytes were just written, so they are in page cache and hash at ~2 GB/s.

    A prefix goes through Part 04 §5.4's canonical listing, a single file is its own bytes; `digest`
    already distinguishes them.
    """
    from escapewheel_validator.stores import digest

    return digest(str(path))


class CommitRefused(Exception):
    """Validation found errors, so nothing was committed.

    Attributes
    ----------
    report : Report
        The findings. The staging directory is left in place for inspection.
    """

    def __init__(self, report: Report, staging: Path) -> None:
        errors = report.errors
        super().__init__(f"{errors} error(s); staged resources left at {staging}")
        self.report = report
        self.staging = staging


class PacketWriter:
    """Collect records and commit them as a validated packet.

    Parameters
    ----------
    registry : Mapping
        The registry to write against. It is embedded in the packet (Part 02 §9.2), so the packet
        stays readable when the reference registry moves on.
    packet_id : str
        The packet's identifier.
    description : str, optional
        Human-readable description for the manifest.

    Examples
    --------
    >>> writer = PacketWriter(registry, packet_id="s001")  # doctest: +SKIP
    >>> writer.add("core.sessions", [{"session_id": "s001", ...}])  # doctest: +SKIP
    >>> report = writer.commit(Path("s001"))  # doctest: +SKIP
    """

    def __init__(
        self,
        registry: Mapping[str, Any],
        *,
        packet_id: str,
        description: str | None = None,
        extensions: Sequence[Mapping[str, Any]] = (),
        session: str | None = None,
        encoding_exceptions: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
    ) -> None:
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
        #: that table last: reading it back left every table added before it unfilled, and only the
        #: adapters that happened to emit the column themselves were saved by it.
        self._session = session
        self._registry = registry
        #: Extension registries this packet carries (Part 09 §2), by `extension_id`. An extension is a
        #: registry document in R2's format, so everything below resolves a resource against core
        #: and then these -- there is no second code path for an extension's tables.
        self._extensions: dict[str, Mapping[str, Any]] = {}
        for document in extensions:
            extension_id = str(document["extension_id"])
            for resource_id in document["tables"]:
                if not resource_id.startswith(f"{extension_id}."):
                    raise ValueError(
                        f"{resource_id} is not namespaced by {extension_id!r}; Part 09 §2 requires it, "
                        "and an extension MUST NOT define a table in core or analysis"
                    )
                if resource_id in registry["tables"]:
                    raise ValueError(f"{resource_id} redefines a core table, which Part 09 §2 forbids")
            self._extensions[extension_id] = document
        #: Assigns the integer every identifier holds (Part 05 §8). One per packet, shared by every
        #: adapter, because two sources numbering the same probe differently is a defect no
        #: foreign key can see: both values resolve, to different rows.
        self.keys = Keys()
        self._packet_id = packet_id
        self._description = description
        self._tables: dict[str, list[Mapping[str, Any]]] = {}
        self._batches: dict[str, Iterable[pa.RecordBatch]] = {}
        #: Part 03 §9.3's retention policy, written into every manifest. One kept version and no age
        #: limit: a packet that is never amended retains nothing, and a packet is archival where
        #: a table is operational, so age alone never expires a manifest.
        self._retention: dict[str, Any] = {"keep_versions": 1}
        #: Part 04 §5.5: where each named source was read from, written to `sources.json` at commit.
        #: A record of where the writer looked, never a resolution rule binding a later reader --
        #: the same standing Part 03 §8 gives `sha256` and `verified_at`.
        self._sources: dict[str, str] = {}
        #: Rows each resource was written with, filled as `_stage` writes them. A streamed
        #: table has no count until then, so anything reported earlier is the source's estimate.
        self.rows_written: dict[str, int] = {}
        #: Called with `say` once staging has run, for whatever only a written packet knows.
        self._after_stage: list[Callable[[Callable[[str], None]], None]] = []
        self._derived: dict[str, list[str]] = {}
        self._runs: dict[str, str] = {}
        self._ordered: set[str] = set()
        self._staged_arrays: dict[str, StagedArray] = {}
        self._referenced_arrays: dict[str, ExternalArray] = {}
        self._referenced_media: dict[str, ExternalMedia] = {}

    def spec(self, resource_id: str) -> Mapping[str, Any] | None:
        """Return the registry entry for one resource, core or extension, or None if undefined.

        One lookup for both, because R17 §3's claim is that an extension needs no second code
        path: it is a registry document in R2's format, so a table of one is a table of the other.
        """
        if resource_id in self._registry["tables"]:
            core: Mapping[str, Any] = self._registry["tables"][resource_id]
            return core
        for document in self._extensions.values():
            if resource_id in document["tables"]:
                spec: Mapping[str, Any] = document["tables"][resource_id]
                return spec
        return None

    def extension_of(self, resource_id: str) -> str | None:
        """Return which extension defines this resource, or None where core does."""
        for extension_id, document in self._extensions.items():
            if resource_id in document["tables"]:
                return extension_id
        return None

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
        KeyError
            If the registry does not define this resource.
        ValueError
            If a record carries a key no column declares. `add_batches` has always refused
            one, and this path ignored it, so the same adapter defect was a build failure
            through one entry point and a dropped column through the other.
        """
        spec = self.spec(resource_id)
        if spec is None:
            raise KeyError(
                f"no registry defines a table named {resource_id}; core and "
                f"{len(self._extensions)} extension(s) were consulted"
            )
        declared = {c["name"] for c in spec["columns"]}
        if undeclared := sorted({key for record in records for key in record} - declared):
            raise ValueError(
                f"{resource_id}: {undeclared} is declared by no registry this build loaded; "
                f"the column would be dropped silently"
            )
        self._tables.setdefault(resource_id, []).extend(self._with_session(resource_id, records))

    def _with_session(
        self, resource_id: str, records: Sequence[Mapping[str, Any]]
    ) -> Sequence[Mapping[str, Any]]:
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
        if not wanted or resource_id == "core.sessions":
            return records
        declared = {r.get("session_id") for r in self._tables.get("core.sessions", [])}
        declared.discard(None)
        if not declared and self._session is not None:
            declared = {self._session}
        if len(declared) != 1:
            return records
        session = next(iter(declared))
        return [r if r.get("session_id") is not None else {"session_id": session, **r} for r in records]

    def _session_batch(self, spec: Mapping[str, Any], batch: pa.RecordBatch) -> pa.RecordBatch:
        """Fill `session_id` on a streamed batch, as `_with_session` does for records (Part 02 §7.1).

        The records path filled it and this one did not, so a table large enough to stream reached
        validation with nulls in a required column: `core.media_frames` at 7,570,450 rows, on the
        one packet that carries video. Filled as the session's *name*, so `number_batch` assigns it
        the same integer every other table's reference to `core.sessions` gets.
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
        KeyError
            If the registry does not define this resource.
        """
        if self.spec(resource_id) is None:
            raise KeyError(f"no registry defines a table named {resource_id}")
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
            Consumed once, at commit. A generator is the expected shape, and keeps the
            source's rows out of memory until they are written.

        Raises
        ------
        KeyError
            If the registry does not define this resource.
        ValueError
            If this resource already has records, or already has batches. One table comes
            from one path; interleaving them would make the sort order unenforceable.
        """
        if self.spec(resource_id) is None:
            raise KeyError(
                f"no registry defines a table named {resource_id}; core and "
                f"{len(self._extensions)} extension(s) were consulted"
            )
        if resource_id in self._tables:
            raise ValueError(f"{resource_id} already has records; use one path per table")
        if resource_id in self._batches:
            raise ValueError(f"{resource_id} already has batches; concatenate before adding")
        spec = self.spec(resource_id)
        assert spec is not None
        self._batches[resource_id] = (
            number_batch(spec, self._session_batch(spec, b), self.keys) for b in batches
        )

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

        Parameters
        ----------
        resource_id : str
            The derived resource.
        sources : sequence of str
            The resource IDs it came from.

        Raises
        ------
        KeyError
            If the registry does not define this resource.
        """
        if self.spec(resource_id) is None:
            raise KeyError(
                f"no registry defines a table named {resource_id}; core and "
                f"{len(self._extensions)} extension(s) were consulted"
            )
        self._derived.setdefault(resource_id, []).extend(sources)

    def add_array(self, resource_id: str, array: StagedArray) -> None:
        """Add a dense array, to be written into the packet as Zarr v3.

        Packet-owned, so `zarr_v3` (Part 03 §6.1) -- v2 is permitted only for a resource the packet
        references rather than owns. The codecs it uses are declared per resource (Part 03 §6.4), so
        a reader checks this array's own list before opening it and must not refuse the packet
        over a codec used only by something it never touches.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID. Not a registry table: an array is described *by*
            `core.array_assets` and `core.array_dimensions`, which are added as records.
        array : StagedArray
            The values and the layout to write them in.

        Raises
        ------
        ValueError
            If this resource already has an array.
        """
        if resource_id in self._staged_arrays:
            raise ValueError(f"{resource_id} already has an array staged")
        self._staged_arrays[resource_id] = array

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
        ValueError
            If this resource already has an array, or if the URI does not match how it resolves:
            absolute where no `source` is named, relative where one is (Part 04 §5.5).
        """
        if resource_id in self._staged_arrays or resource_id in self._referenced_arrays:
            raise ValueError(f"{resource_id} already has an array")
        _check_reference(resource_id, array.uri, array.source)
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
        ValueError
            If this resource already has media, or if the URI does not match how it resolves
            (Part 04 §5.5).
        """
        if resource_id in self._referenced_media:
            raise ValueError(f"{resource_id} already has media")
        _check_reference(resource_id, media.uri, media.source)
        self._referenced_media[resource_id] = media

    def produced_by(self, resource_id: str, processing_run_id: str) -> None:
        """Name the run that produced a resource (Part 04 §3).

        Part 06 requires a derived resource to declare its transform parameters and software
        version, and R31 puts them in a `core.processing_runs` row that the manifest points at.
        The run itself is added like any other table; this records the link, which lives in the
        manifest because it is a fact about a resource rather than about any row.

        Parameters
        ----------
        resource_id : str
            The produced resource.
        processing_run_id : str
            A `core.processing_runs.processing_run_id`. The validator checks it resolves.

        Raises
        ------
        KeyError
            If the registry does not define this resource.
        """
        if self.spec(resource_id) is None:
            raise KeyError(
                f"no registry defines a table named {resource_id}; core and "
                f"{len(self._extensions)} extension(s) were consulted"
            )
        self._runs[resource_id] = processing_run_id

    @property
    def resources(self) -> list[str]:
        """Resource IDs with at least one record, in insertion order."""
        return [*self._tables, *self._batches]

    def _stage_arrays(self, staging: Path) -> list[dict[str, Any]]:
        """Write every staged array under `staging` and return its manifest entries."""
        if not self._staged_arrays:
            return []
        from .arrays import declared_codecs, write_zarr

        entries = []
        for resource_id, spec in self._staged_arrays.items():
            namespace, name = resource_id.split(".", 1)
            relative = f"arrays/{namespace}/{name}.zarr"
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            written = write_zarr(path, spec)
            entries.append(
                {
                    "resource_id": resource_id,
                    "layer": namespace,
                    "kind": "dense_array_asset",
                    "physical_profile": "zarr_v3",
                    "uri": relative,
                    "array_asset_id": spec.array_asset_id,
                    "canonical": True,
                    "validation_state": "not_run",
                    "codecs": list(declared_codecs(spec)),
                    "size_bytes": written,
                    "sha256": _digest(path),
                }
            )
        return entries

    def _reference_media(self) -> list[dict[str, Any]]:
        """Return a manifest entry per referenced media asset. Copies nothing and reads nothing."""
        entries = []
        for resource_id, media in self._referenced_media.items():
            entry = {
                "resource_id": resource_id,
                "layer": resource_id.split(".", 1)[0],
                "kind": "media_asset",
                "physical_profile": media.format,
                "uri": media.uri,
                "media_asset_id": media.media_asset_id,
                "canonical": True,
                "validation_state": "not_run",
                "external": True,
            }
            for name in ("source", "sha256", "size_bytes", "verified_at"):
                if (value := getattr(media, name)) is not None:
                    entry[name] = value
            entries.append(entry)
        return entries

    def _reference_arrays(self) -> list[dict[str, Any]]:
        """Return a manifest entry per referenced array. Copies nothing and reads nothing."""
        entries = []
        for resource_id, array in self._referenced_arrays.items():
            entry = {
                "resource_id": resource_id,
                "layer": resource_id.split(".", 1)[0],
                "kind": "dense_array_asset",
                "physical_profile": array.physical_profile,
                "uri": array.uri,
                "array_asset_id": array.array_asset_id,
                "canonical": True,
                "validation_state": "not_run",
                "external": True,
                "codecs": list(array.codecs),
            }
            for name in ("source", "sha256", "size_bytes", "verified_at"):
                if (value := getattr(array, name)) is not None:
                    entry[name] = value
            if array.members is not None:
                entry["members"] = [dict(member) for member in array.members]
            entries.append(entry)
        return entries

    def _stage(self, staging: Path, only: Collection[str] | None = None) -> list[dict[str, Any]]:
        """Write every table under `staging` and return its manifest entries.

        Records in `_ordered` the resources whose physical order `_write_stream` established as
        it wrote them, so the commit that follows need not read them back to learn it.
        """
        entries = []
        if only is None:
            self._ordered = set()
        self._preassign()
        for resource_id in self.resources:
            if only is not None and resource_id not in only:
                continue
            spec = self.spec(resource_id)
            assert spec is not None
            namespace, name = resource_id.split(".", 1)
            relative = f"tables/{namespace}/{name}.parquet"
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if resource_id in self._batches:
                self.rows_written[resource_id] = _write_stream(
                    spec, self._batches[resource_id], path, resource_id,
                    self._encoding_exceptions, self._encoding_notes,
                )
                if sort_key(resource_id, spec):
                    self._ordered.add(resource_id)
            else:
                table = build(resource_id, spec, self._tables[resource_id], self.keys)
                self.rows_written[resource_id] = table.num_rows
                # No `row_group_size`: pyarrow's default is min(rows, 2**20), which puts each
                # of these tables in one row group, and that is the right answer — they are
                # smaller than a single object-storage fetch and are read whole, so splitting
                # one only adds requests and duplicates its string dictionary.
                #
                # Sizing a row group for the fetch band is a mistake on both paths. See
                # `session.BATCH_ROWS` for the streaming case; here the trap is that estimating
                # from `Table.nbytes` is 320x out on a string-heavy table, because Arrow
                # materialises strings that Parquet stores as dictionary codes. It once split a
                # 101 KB table three ways.
                options = _options(resource_id, spec, table.schema, self._encoding_exceptions)
                pq.write_table(table, path, **options)
                delta = list(options.get("column_encoding", {}))
                kept = set(options.get("use_dictionary", table.schema.names))
                self._encoding_notes.extend(inefficient(
                    resource_id, table, delta,
                    [n for n in table.schema.names if n not in kept and n not in delta],
                ))
            extension_id = self.extension_of(resource_id)
            entry = {
                "resource_id": resource_id,
                # Part 05 §5.4: an extension table's entry says so and names its owner, so a reader
                # knows what it holds without parsing the extension's registry.
                "layer": "extension" if extension_id else namespace,
                **({"extension_id": extension_id} if extension_id else {}),
                "kind": "table",
                "schema_id": f"{resource_id}.v{_standard_version(self._registry)}",
                "physical_profile": "parquet",
                "uri": relative,
                "canonical": True,
                "validation_state": "not_run",
            }
            entry["sha256"] = _digest(path)
            if lineage := self._derived.get(resource_id):
                entry["derived_from"] = lineage
            if run := self._runs.get(resource_id):
                # The name, not the assigned number: a manifest identifies by name throughout
                # -- `packet_id`, `sessions`, every `resource_id` -- because it is read before
                # any table and a number resolves against nothing. Part 02 §5.3's `*_name` columns
                # are the bridge, and Part 05 §5.3's check crosses it.
                entry["processing_run_id"] = run
            entries.append(entry)
        return entries

    def _preassign(self) -> None:
        """Assign a number to every name this packet uses, before any table is built (Part 05 §8).

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
            for column in spec["columns"]:
                if column.get("role") != "identifier" or column.get("identity") != "assigned":
                    continue
                kind = target.get(column["name"], column["name"])
                pending.setdefault(kind, set()).update(
                    str(r[column["name"]]) for r in rows if r.get(column["name"]) is not None
                )
        for kind in sorted(pending):
            for value in sorted(pending[kind]):
                self.keys.of(kind, value)

    def _manifest(self, entries: Sequence[Mapping[str, Any]], report: Report | None) -> dict[str, Any]:
        """Build the manifest for these resources."""
        sessions = sorted({r["session_id"] for r in self._tables.get("core.sessions", []) if "session_id" in r})
        now = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
        validation = {
            "status": "not_run" if report is None else ("passed" if report.passed else "failed"),
            "validated_at": now,
            "validator_name": "escapewheel_validator",
            "validator_version": _version(),
        }
        manifest: dict[str, Any] = {
            "packet_id": self._packet_id,
            "packet_version": "0.1.0",
            "profile_id": PROFILE,
            "semantic_standard_version": self._registry["semantic_standard_version"],
            "logical_standard_version": self._registry["logical_standard_version"],
            "registry_version": self._registry["registry_version"],
            "created_at": now,
            "sessions": sessions,
            # Part 03 §6.4 declares codecs per resource; the top-level list is their union, so a
            # reader can answer "can I open this packet at all" without walking every entry.
            "required_codecs": sorted({c for e in entries for c in e.get("codecs", [])}),
            "resources": [dict(e) for e in entries],
            # Part 03 §9.3: declared rather than left to a default, because `prune` reads it and a
            # packet that says nothing makes the operator's policy invisible to the operation.
            "retention": dict(self._retention),
            "validation": validation,
        }
        if inventory := self._extension_inventory():
            manifest["extensions"] = inventory
        if self._description is not None:
            manifest["description"] = self._description
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

    def _write_sources(self, root: Path) -> None:
        """Write Part 04 §5.5's default resolution document, where any resource names a source.

        Before the manifest, because Part 05 §6 makes publishing the catalog what makes a commit
        visible: everything a reader may look for is in place first. Skipped entirely when no
        resource names a source, since a document locating nothing is worse than none -- it
        would answer a lookup the caller meant to answer itself.
        """
        located = {
            referenced.source: {"uri": self._sources[referenced.source]}
            for referenced in (*self._referenced_arrays.values(), *self._referenced_media.values())
            if referenced.source is not None and referenced.source in self._sources
        }
        if not located:
            return
        document = {
            "$schema": "https://escapewheel.org/schemas/sources/0.1.0",
            "sources_standard_version": SOURCES_VERSION,
            "description": f"Where {self._packet_id} read its referenced data. Editable: not a packet resource.",
            "sources": dict(sorted(located.items())),
        }
        (root / SOURCES).write_text(json.dumps(document, indent=2) + "\n")

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
            overwritten, because immutability covers packet-owned bytes (Part 04 §5.1).
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
        FileExistsError
            If `root` already holds a committed manifest.
        ValueError
            If no `core.sessions` records were added.
        CommitRefused
            If validation found errors. Nothing is committed and staging is left in place.
        """
        root = Path(root)
        if (root / MANIFEST).exists():
            raise FileExistsError(f"{root} already holds a committed {MANIFEST}")
        # R1 §6 makes the session inventory part of the manifest and the schema requires it
        # non-empty. Refusing here beats letting the staged manifest fail its own schema,
        # which surfaces as an unhelpful error from a directory the caller never named.
        if not self._tables.get("core.sessions"):
            raise ValueError("a packet declares at least one session; core.sessions is empty (R1 §6)")

        staging = root / "staging"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)

        # 1. staged resources, plus the registry they were written against
        clock = time.perf_counter()
        entries = [
            *self._stage(staging),
            *self._stage_arrays(staging),
            *self._reference_arrays(),
            *self._reference_media(),
        ]
        say(f"staged {len(entries)} resources in {time.perf_counter() - clock:.1f} s")
        # Part 03 §5.5's rules are good guesses, and a column one guesses wrong
        # about is said aloud rather than silently paid for. A report, not a refusal: every
        # encoding is permitted (Part 03 §5.5), so the packet is conforming whichever it got.
        for note in sorted(set(self._encoding_notes)):
            say(f"  encoding: {note}")
        for report in self._after_stage:
            report(say)
        clock = time.perf_counter()
        (staging / "schemas").mkdir(parents=True, exist_ok=True)
        (staging / REGISTRY_PATH).write_text(json.dumps(self._registry, indent=2) + "\n")
        self._install_extensions(staging)

        # 2. derive whatever the caller asked for from the staged packet, before anything is
        #    validated or promoted. Part 05 stages 8 and 9 put materialization inside the import
        #    pipeline, and a staged packet is already openable -- it needs a manifest, which is
        #    written here anyway. Doing it now costs one validation over the finished packet;
        #    doing it after the commit costs a second manifest, a version bump and a
        #    revalidation of resources validated seconds earlier, which is what `amend` is for
        #    and what a build the recipe fully describes should never pay.
        (staging / MANIFEST).write_text(json.dumps(self._manifest(entries, None), indent=2) + "\n")
        if materialize:
            # Row counts, not just names: a materializer adds its own `core.processing_runs`
            # row (Part 04 §3), and that table was staged in the pass above. Restaging only what is
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
            entries = [*kept, *restaged]
            (staging / MANIFEST).write_text(json.dumps(self._manifest(entries, None), indent=2) + "\n")
            say(f"staged {len(restaged)} derived or updated resource(s) in {time.perf_counter() - clock:.1f} s")
            clock = time.perf_counter()
        # Scan the order of everything except what `_write_stream` compared on the way in.
        # Not a shortcut around the check: the same comparison ran, over the same rows, from
        # the same code, one step earlier (R12 §4 still governs where it lives).
        staged = {e["resource_id"] for e in entries}
        report = validate(open_packet(staging), limits=limits, scan=staged - self._ordered)
        say(f"validated in {time.perf_counter() - clock:.1f} s")
        clock = time.perf_counter()
        if not report.passed:
            raise CommitRefused(report, staging)

        # 3. move into final paths
        for entry in entries:
            entry["validation_state"] = "passed"
        for name in ("tables", "arrays", "schemas", EXTENSIONS_PATH):
            source = staging / name
            if source.exists():
                shutil.move(str(source), str(root / name))

        # 4. rename the manifest last: until this line the root holds no manifest at all,
        #    so a reader finds nothing rather than a partial import claiming to be valid.
        self._write_sources(root)
        candidate = root / f"{MANIFEST}.candidate"
        candidate.write_text(json.dumps(self._manifest(entries, report), indent=2) + "\n")
        os.replace(candidate, root / MANIFEST)
        shutil.rmtree(staging)
        say(f"promoted in {time.perf_counter() - clock:.1f} s")
        return report

    def amend(
        self,
        root: str | Path,
        *,
        packet_version: str | None = None,
        limits: Mapping[str, Any] | None = None,
    ) -> Report:
        """Add resources to a committed packet, as a new packet version (R32).

        An amendment modifies no file the superseded manifest names. A table that gains rows is
        written as a **new file** and the amended manifest names that one, so Part 04 §5.1's
        immutability holds literally rather than by exception.

        The sequence is `commit`'s, with the swap at the end doing more work: the added
        resources are staged and validated before anything reaches a final path, the superseded
        manifest and registry are retained, and `packet.json` is replaced by an atomic
        rename last. A reader sees the old packet or the new one, never a blend.

        Parameters
        ----------
        root : str or Path
            A packet root holding a committed manifest.
        packet_version : str, optional
            The new version. Defaults to bumping the minor component.
        limits : Mapping, optional
            DuckDB settings bounding validation. Part 03 §9.4 narrows an amendment to the rules
            attached to a written resource or naming one, but every table is still registered
            alongside it, so a surviving rule may read anything the packet holds.

        Returns
        -------
        Report
            The validation report for the **whole** packet, not only what was added (Part 03 §9.4).

        Raises
        ------
        NotCommitted
            If `root` holds no committed manifest. Use `commit` to create a packet.
        ValueError
            If the amendment would replace a core resource other than a provenance table, which
            is a new packet rather than a new version of this one (Part 03 §9.2).
        CommitRefused
            If validation found errors. The packet stays at its previous version.
        """
        root = Path(root)
        if not (root / MANIFEST).is_file():
            raise NotCommitted(f"{root} holds no committed {MANIFEST}; use commit() to create a packet")
        superseded = json.loads((root / MANIFEST).read_text())

        added = set(self.resources)
        standing = {e["resource_id"] for e in superseded["resources"]}
        if clash := sorted(r for r in added & standing if not r.startswith("analysis.") and r not in PROVENANCE):
            raise ValueError(
                f"amending would replace {clash}; a packet whose core data changes is a new packet (Part 03 §9.2)"
            )

        self._absorb_provenance(root, superseded)

        staging = root / "staging"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        entries = self._stage(staging)

        # Validate with the added resources still under staging/, so nothing occupies a final
        # path until it has passed. The candidate is derived from the superseded manifest, not
        # rebuilt: every packet-level field this amendment does not change carries over, which
        # is what keeps the session inventory and description from silently vanishing (Part 03 §9.3).
        kept = [e for e in superseded["resources"] if e["resource_id"] not in added]
        candidate = dict(superseded)
        candidate["resources"] = kept + [dict(e, uri=f"staging/{e['uri']}") for e in entries]
        candidate["registry_version"] = self._registry["registry_version"]
        candidate["packet_version"] = packet_version or _bump(superseded["packet_version"])
        candidate["supersedes"] = superseded["packet_version"]

        # The registry goes in before validation, not after: the validator compares the
        # manifest's declared registry_version against the copy the packet carries (Part 02 §9.2), so
        # a candidate declaring the new version against the old embedded copy fails on a
        # mismatch that says nothing about the data. Rolled back if this does not pass, which
        # leaves the packet exactly as it was.
        restore = self._install_registry(root)
        try:
            # Both halves of the amendment are bounded by what it writes (R35). Physical order
            # is re-read only for those files, and only the rules attached to one or naming one
            # re-run. A file the amendment does not name is byte-identical to one already
            # verified -- Part 03 §9.2 forbids modifying it and Part 04 §5.1 declares it immutable -- so
            # its order cannot have changed and a rule reading only it is already answered.
            written = {e["resource_id"] for e in entries}
            report = validate(
                Packet(root, Manifest.from_dict(candidate)),
                registry=dict(self._registry),
                limits=limits,
                scan=written - self._ordered,
                recheck=written,
            )
            if not report.passed:
                raise CommitRefused(report, staging)
        except BaseException:
            restore()
            raise

        for entry in entries:
            destination = root / entry["uri"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging / entry["uri"]), str(destination))
            entry["validation_state"] = "passed"

        amended = dict(candidate)
        amended["resources"] = kept + [dict(e) for e in entries]
        amended["validation"] = {
            "status": "passed" if report.passed else "failed",
            "validated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "validator_name": "escapewheel_validator",
            "validator_version": _version(),
        }

        self._retain(root, superseded, amended)
        candidate_path = root / f"{MANIFEST}.candidate"
        candidate_path.write_text(json.dumps(amended, indent=2) + "\n")
        os.replace(candidate_path, root / MANIFEST)
        shutil.rmtree(staging)
        return report

    def _absorb_provenance(self, root: Path, superseded: Mapping[str, Any]) -> None:
        """Carry a provenance table's existing rows into the amendment (Part 03 §9.2).

        R32 permits *adding rows* to these tables, and a resource is staged from whatever this
        writer holds -- so amending with one new run and nothing else would rewrite the table
        as that single row and drop every earlier one. Reading them back in is what makes
        "add" mean add.
        """
        standing = {e["resource_id"]: e for e in superseded["resources"]}
        for resource_id in [r for r in self._tables if r in PROVENANCE and r in standing]:
            existing = pq.read_table(root / standing[resource_id]["uri"]).to_pylist()
            key = (self.spec(resource_id) or {}).get("primary_key") or []
            taken = {tuple(row.get(k) for k in key) for row in self._tables[resource_id]}
            collide = sorted(
                str(tuple(r.get(k) for k in key)) for r in existing if tuple(r.get(k) for k in key) in taken
            )
            if collide:
                raise ValueError(
                    f"amending {resource_id} would rewrite existing row(s) {collide[:3]}; an amendment adds "
                    "rows to a provenance table, it does not revise them (Part 03 §9.2)"
                )
            self._tables[resource_id] = [*existing, *self._tables[resource_id]]

    def _retain(self, root: Path, superseded: Mapping[str, Any], amended: Mapping[str, Any]) -> None:
        """Keep every manifest a packet has had (Part 03 §9.3).

        A superseded file is only interpretable if the manifest that named it still exists;
        without these, an orphan and a stray are indistinguishable and a `sha256` recorded
        under R14 points at a state nothing can reconstruct.
        """
        versions = root / MANIFESTS
        versions.mkdir(exist_ok=True)
        for manifest in (superseded, amended):
            path = versions / f"nwb.packet.{manifest['packet_version']}.json"
            path.write_text(json.dumps(manifest, indent=2) + "\n")

    def _install_extensions(self, root: Path) -> None:
        """Write each extension registry into the packet, beside the core one (R17 §5, Part 09 §6).

        A packet embeds the registry it was written against so it stays self-describing; an
        extension is a registry document, so it is embedded the same way and for the same reason.
        Each carries its own `registry_version`, independent of core's.
        """
        if not self._extensions:
            return
        (root / EXTENSIONS_PATH).mkdir(parents=True, exist_ok=True)
        for extension_id, document in self._extensions.items():
            path = root / EXTENSIONS_PATH / f"{extension_id}.json"
            path.write_text(json.dumps(document, indent=2) + "\n")

    def _extension_inventory(self) -> dict[str, dict[str, str]]:
        """Return what the manifest says about the extensions this packet carries."""
        return {
            extension_id: {
                "version": str(document["registry_version"]),
                "registry": f"{EXTENSIONS_PATH}/{extension_id}.json",
            }
            for extension_id, document in self._extensions.items()
        }

    def _install_registry(self, root: Path) -> Callable[[], None]:
        """Put this writer's registry in the packet, retaining the superseded copy (Part 03 §9.3).

        Returns a callable that undoes it, because this has to happen *before* validation --
        the validator checks the embedded copy against the manifest's declared version -- and a
        failed amendment must leave the packet exactly as it was.
        """
        installed = root / REGISTRY_PATH
        # A retained copy at this version settles it too, not just the current one: installing
        # different content under a version the packet has already retained makes that version
        # ambiguous *within one packet*, so its older manifests name a registry that no longer
        # identifies anything.
        already = installed.with_name(f"logical_schemas.{self._registry['registry_version']}.json")
        if already.is_file() and json.loads(already.read_text()) != self._registry:
            raise ValueError(
                f"{already.name} is retained with different content; installing this registry would leave "
                f"two different {self._registry['registry_version']} in one packet (Part 03 §9.3). Bump "
                "registry_version, or rebuild the packet so it retains only one."
            )

        previous = installed.read_bytes() if installed.is_file() else None
        if previous is not None:
            embedded = json.loads(previous)
            if embedded["registry_version"] == self._registry["registry_version"]:
                if embedded != self._registry:
                    raise ValueError(
                        f"registry {embedded['registry_version']} differs from the packet's copy at the same "
                        "version; two registries that cannot be told apart make Part 02 §9.2 vacuous (Part 03 §9.3)"
                    )
                return lambda: None
            keep = installed.with_name(f"logical_schemas.{embedded['registry_version']}.json")
            keep.write_text(json.dumps(embedded, indent=2) + "\n")
        else:
            keep = None

        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_text(json.dumps(self._registry, indent=2) + "\n")

        def restore() -> None:
            if previous is None:
                installed.unlink(missing_ok=True)
            else:
                installed.write_bytes(previous)
            if keep is not None:
                keep.unlink(missing_ok=True)

        return restore


__all__ = [
    "MANIFEST",
    "MANIFESTS",
    "PROFILE",
    "PROVENANCE",
    "REGISTRY_PATH",
    "CommitRefused",
    "ExternalMedia",
    "NotCommitted",
    "PacketWriter",
]

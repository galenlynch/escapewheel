"""Stage, validate, and commit a packet.

Part 05's core principle is that **validation is importation**: copying or converting bytes is
only staging, and a resource is not imported until it has passed the checks for its schema.
This module is the writer and committer halves of that pipeline. It knows nothing about NWB,
SpikeInterface, or any other source -- adapters hand it records, and it turns them into a
packet or refuses to.

A build follows Part 05 §2's order, and the part of it this module performs is its guarantee:

1. write the normalized resources and the import's provenance under ``staging/`` (Part 03 §3.4);
2. derive the analysis resources the caller asked for from the staged packet (Part 05 §8);
3. validate the whole staged packet there;
4. record every path promotion will create, then promote into the final paths (Part 05 §6);
5. rename the manifest to ``packet.json`` **last**.

Until step 5 the packet root holds no manifest, so a reader finds nothing rather than finding a
partial import that claims to be valid, and the promotion record makes whatever an interrupted
step 4 left the next build's to remove.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import time
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader import Manifest, Packet, check_sources, open_packet
from escapewheel_reader.profile import parquet_floor
from escapewheel_reader.registries import gunzip_member as gzip_member
from escapewheel_reader.uri import canonical, encode, is_absolute
from escapewheel_validator import (
    CheckedRegistryContext,
    RegistryRejected,
    Report,
    check_registry_context,
    validate,
    verify_order,
)
from escapewheel_validator.amendment import DERIVED, chain_reaches
from escapewheel_validator.generate import adjacency_settles_uniqueness
from escapewheel_validator.validator import OrderViolation

from . import opaque
from .amending import Held
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
#: resource: under the root so a copy carries it, outside the manifest so Part 03 §8.1's immutability
#: does not reach it and a moved mirror is fixed by editing it in place.
SOURCES = "sources.json"

#: The version of that document this writer emits (Part 04 §5.5).
SOURCES_VERSION = "escapewheel-sources-v0.1"

#: Where the portable profile stores each bound registry, as `<registry_id>/<version>.json.gz`
#: (Part 03 §3.3).
REGISTRIES = "registries"

#: The directories under the packet root a commit promotes from its staging area, which a root holding
#: any of them without a committed manifest cannot take another commit into.
PROMOTED = ("tables", "arrays", opaque.ROOT, REGISTRIES)

#: Part 03's portable profile.
PROFILE = "escapewheel-portable-v0.1"

#: The portable profile's staging area, directly under the packet root (Part 03 §3.4).
STAGING = "staging"

#: The promotion record inside the staging area (Part 05 §6). Its format is this writer's.
PROMOTION = "promotion.json"


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
def _options(
    resource_id: str,
    spec: Mapping[str, Any],
    out: pa.Schema,
    extra: Mapping[str, Any] | None = None,
    sample: pa.Table | pa.RecordBatch | None = None,
) -> dict[str, Any]:
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
    options: dict[str, Any] = {"compression": "zstd", "data_page_version": "1.0"}
    # A caller may hand over a column as dictionary codes rather than decoding what Parquet is
    # about to re-encode. Parquet has no dictionary type -- the column is BYTE_ARRAY/String
    # either way -- so the only thing that would record the choice is the Arrow schema pyarrow
    # stores as metadata, and storing it would make the file advertise a type the registry does
    # not declare. Withhold it, and the file reads back as the registry says.
    if any(pa.types.is_dictionary(field.type) for field in out):
        options["store_schema"] = False
    delta, plain = encodings(resource_id, spec, out, extra, sample)
    if delta or plain:
        options["use_dictionary"] = [n for n in out.names if n not in {*delta, *plain}]
        if delta:
            options["column_encoding"] = dict.fromkeys(delta, "DELTA_BINARY_PACKED")
    keys = sort_key(resource_id, spec) or []
    if columns := [pq.SortingColumn(out.names.index(k)) for k in keys if k in out.names]:
        options["sorting_columns"] = columns
    return options


def _check_parquet_floor(path: Path) -> None:
    """Refuse a packet-owned table whose footer exceeds the incorporated writer floor."""
    floor = parquet_floor()
    metadata = pq.ParquetFile(path).metadata
    compressions: set[str] = set()
    encodings: set[str] = set()
    for row_group in range(metadata.num_row_groups):
        group = metadata.row_group(row_group)
        for column in range(group.num_columns):
            chunk = group.column(column)
            compressions.add(str(chunk.compression).upper())
            encodings.update(str(value).upper() for value in chunk.encodings)
    outside_compression = sorted(compressions - set(floor["compressions"]))
    outside_encoding = sorted(encodings - set(floor["encodings"]))
    if outside_compression or outside_encoding:
        detail = []
        if outside_compression:
            detail.append(f"compression {outside_compression}")
        if outside_encoding:
            detail.append(f"encoding {outside_encoding}")
        raise ValueError(f"{path}: Parquet footer exceeds the portable writer floor: {', '.join(detail)}")


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


def _write_stream(
    spec: Mapping[str, Any],
    batches: Iterable[pa.RecordBatch],
    path: Path,
    resource_id: str,
    extra: Mapping[str, Any] | None = None,
    report: list[str] | None = None,
) -> int:
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
            first = out is None
            if out is None:
                out = _as_held(schema(spec, set(batch.schema.names)), batch.schema)
            if unexpected := sorted(set(batch.schema.names) - set(out.names)):
                # Two causes reach here and they send an author to different files: a column the
                # registry never declared, and an optional one the first batch lacked so `schema`
                # left it out. The check fires on the first batch too, where only the first is
                # possible, so a message naming only the second described the rarer case.
                declared = {c["name"] for c in spec["columns"]}
                said = []
                if undeclared := [n for n in unexpected if n not in declared]:
                    said.append(f"{undeclared} is declared by no registry this build loaded")
                if late := [n for n in unexpected if n in declared]:
                    said.append(f"{late} is optional and absent from the first batch")
                raise ValueError(f"{resource_id}: {'; '.join(said)}; the column would be dropped silently")
            columns = [
                batch.column(name) if name in batch.schema.names else pa.nulls(batch.num_rows, field.type)
                for name, field in zip(out.names, out, strict=True)
            ]
            held = pa.record_batch(columns, schema=out)
            if first:
                # Chosen from the batch as it will be written, not as it arrived: a column the source
                # omits is written as nulls and counts as none, and a column cast to the registry's
                # type is measured at that type, where the source's can cost 77x as much plain.
                options = _options(resource_id, spec, out, extra, held)
                writer = pq.ParquetWriter(path, out, **options)
                if report is not None:
                    report.extend(
                        inefficient(
                            resource_id,
                            pa.Table.from_batches([held]),
                            options.get("column_encoding", {}) and list(options["column_encoding"]) or [],
                            [
                                n
                                for n in out.names
                                if n not in options.get("use_dictionary", out.names)
                                and n not in options.get("column_encoding", {})
                            ],
                        )
                    )
            assert writer is not None
            # `row_group_size` is load-bearing, not decoration: left to pyarrow it defaults to
            # 2**20 rows and silently cuts a larger batch into several row groups, which would
            # break the boundary guarantee this docstring makes.
            writer.write_batch(held, row_group_size=batch.num_rows)
            written += batch.num_rows
    finally:
        if writer is not None:
            writer.close()
    return written


#: Core tables whose added rows leave every derived resource current (Part 05 §15.2), since a row
#: records what ran, not what was measured.
PROVENANCE = ("core.processing_runs", "core.source_files", "core.processing_run_inputs")

#: Where superseded manifests are retained (Part 03 §9).
MANIFESTS = "manifests"


def semver(text: str) -> tuple[int, ...]:
    """Order a packet_version. A part that is not a number sorts before one that is."""
    return tuple(int(part) if part.isdigit() else -1 for part in str(text).split("."))


class PromotionRecordUnreadable(Exception):
    """A staging area holds a promotion record this writer cannot read (Part 05 §6)."""


def _record_promotion(staging: Path, packet_version: str, paths: Iterable[str]) -> None:
    """Write the promotion record durably, before anything is written outside `staging` (Part 05 §6)."""
    body = json.dumps({"packet_version": packet_version, "paths": sorted(set(paths))}, indent=2) + "\n"
    pending = staging / f"{PROMOTION}.pending"
    with pending.open("w") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(pending, staging / PROMOTION)
    directory = os.open(staging, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def read_promotion(root: Path) -> tuple[str, list[str]] | None:
    """Return the version and paths of the promotion record at `root`, or None where there is none.

    Raises
    ------
    PromotionRecordUnreadable
        If the record cannot be parsed, or lists a path outside the packet root.
    """
    path = root / STAGING / PROMOTION
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text())
        version = str(record["packet_version"])
        paths = [str(p) for p in record["paths"]]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise PromotionRecordUnreadable(f"{path}: cannot read the promotion record ({error})") from None
    if escaping := [p for p in paths if Path(p).is_absolute() or ".." in Path(p).parts or not p]:
        raise PromotionRecordUnreadable(f"{path}: lists {escaping[0]!r}, which is not under the packet root")
    return version, paths


def _act_on_promotion(root: Path) -> None:
    """Undo what an unpublished promotion created, before anything else happens at `root` (Part 05 §6).

    Where the record's version is already published the record is stale and the listed paths are
    the packet's, so nothing is removed; the staging area is emptied afterwards either way.
    """
    record = read_promotion(root)
    if record is None:
        return
    version, paths = record
    manifest = root / MANIFEST
    if manifest.is_file() and semver(json.loads(manifest.read_text())["packet_version"]) >= semver(version):
        return
    for relative in paths:
        target = root / relative
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.exists() or target.is_symlink():
            target.unlink()


def _claim(root: Path, paths: Iterable[str]) -> None:
    """Refuse to promote onto a path that already exists, naming it (Part 05 §6)."""
    if taken := sorted(p for p in paths if (root / p).exists()):
        raise FileExistsError(f"{root / taken[0]} already exists, so promotion would overwrite it")


def _created(root: Path, relative: str) -> str:
    """Return the outermost path writing `relative` under `root` would create."""
    parts = Path(relative).parts
    for depth in range(1, len(parts) + 1):
        if not (root / Path(*parts[:depth])).exists():
            return Path(*parts[:depth]).as_posix()
    return relative


def _bump(version: str) -> str:
    """Return the next packet version.

    Patch level, so a packet under development stays inside one minor series while the
    structure moves. Part 05 §15.1 requires only that the new version sort strictly after the
    superseded one, and Part 03 §8 leaves what it *means* open, so nothing here rests on the choice.
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
    resource_id: str
    #: Empty for an array delivered by name alone, which `add_array` binds by its catalog row.
    declaration_id: str
    array_asset_id: str
    chunks: tuple[int, ...] = ()
    shard: tuple[int, ...] | None = None
    codecs: tuple[str, ...] = ("blosc",)
    fill_value: Any = 0
    #: Each axis's `dimension_name`, in stored order (Part 03 §6.5). Unset, staging takes them
    #: from the axes records this array's catalog row has.
    dimension_names: tuple[str, ...] | None = None
    #: Where an adapter already wrote this array, for one delivered out of process (Part 03
    #: §11.3). Set, the layout above is the array's own and is read back off it rather than
    #: applied: staging moves the directory where it would have written one.
    written: Path | None = None


@dataclass(frozen=True)
class ExternalArray:
    """A dense array the packet references rather than owns (Part 04 §5.1).

    Referencing is the expected form for a large one. Copying duplicates the bulk of a dataset
    for no gain, and transcoding to the portable floor throws away the acquisition's own
    compression -- 5.8 GB of LFP across twelve probes, against three integers per series once
    R20 replaces its timestamps.

    `digest`, `size_bytes`, `members` and `verified_at` record what was true when someone
    looked, not a promise about now: immutability covers packet-owned bytes only (Part 03 §8),
    and an external array may change or vanish without the packet changing at all. `digest` is
    Part 04 §4.3's `{"algorithm", "value"}` object.

    `members` is Part 04 §5.4's record of what the prefix held, each entry carrying its own digest
    where the resource records one and the store's entity tag where it offered one. It is a record
    and not a resolution rule -- a reader hands the URI to Zarr, which addresses chunks by key and
    never enumerates.
    """

    array_asset_id: str
    declaration_id: str
    uri: str
    #: Part 04 §5.5: the body of data these bytes belong to. Where set, `uri` is a path relative to
    #: wherever that source turns out to be rather than a location, and a resolution document
    #: says where that is.
    source: str | None = None
    physical_profile: str = "zarr_v3"
    codecs: tuple[str, ...] = ()
    digest: Mapping[str, str] | None = None
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

    `digest`, `size_bytes` and `verified_at` record what was true when someone looked, not a
    promise about now (Part 04 §5.2).
    """

    media_asset_id: str
    declaration_id: str
    uri: str
    format: str = ""
    #: Part 04 §5.5, as on `ExternalArray`.
    source: str | None = None
    digest: Mapping[str, str] | None = None
    size_bytes: int | None = None
    verified_at: str | None = None


def _check_reference(resource_id: str, uri: str, source: str | None) -> str:
    """Return a referenced URI as the manifest records it, refusing one no reader could resolve.

    Relative where the entry names a source, because the source supplies the part in front and an
    absolute URI there would ignore it (Part 04 §5.5). A relative one is a relative reference, which
    the manifest spells in one form (Part 03 §4); without a source it resolves under the packet root,
    which an external resource may (Part 04 §5.1).
    """
    if is_absolute(uri):
        if source is not None:
            raise ValueError(f"{resource_id}: {uri!r} is absolute, so naming source {source!r} would have no effect")
        return uri
    try:
        return canonical(uri)
    except ValueError as exc:
        raise ValueError(
            f"{resource_id}: uri is neither absolute nor a relative reference: {exc} (Part 03 §4)"
        ) from None


def _refuse_occupied(root: Path) -> None:
    """Refuse a root holding a committed manifest or a directory commit would promote into.

    Called after `_act_on_promotion`, so what remains is a promoted directory no promotion record
    claims: a stray a writer may not remove (Part 05 §15.5), and moving another into it would nest
    the new one inside.
    """
    if (root / MANIFEST).exists():
        raise FileExistsError(f"{root} already holds a committed {MANIFEST}")
    if occupied := [name for name in PROMOTED if (root / name).exists()]:
        raise FileExistsError(
            f"{root} holds {', '.join(occupied)} but no committed {MANIFEST}, as an interrupted promotion "
            "leaves it; remove them or commit elsewhere"
        )


def _digest(path: Path) -> dict[str, str]:
    """Part 04 §4.3: what the packet says its own bytes are, under SHA-256.

    Required of every packet-owned resource, because the promise it makes checkable is not optional
    either: Part 03 §8.1 declares these bytes immutable and Part 05 §15.4 spends that, bounding
    revalidation after an amendment to what the amendment wrote. Costs 0.5% of a build -- the bytes
    were just written, so they are in page cache and hash at ~2 GB/s.

    A prefix goes through Part 04 §4.3's listing, a single file is its own bytes; `digest` already
    distinguishes them.
    """
    from escapewheel_validator.stores import digest

    return {"algorithm": "sha256", "value": digest(str(path))}


class CommitRefused(Exception):
    """The packet's verdict was not ``passed``, so nothing was committed (Part 05 §9.2).

    Attributes
    ----------
    report : Report
        The findings. The staging directory is left in place for inspection.
    """

    def __init__(self, report: Report, staging: Path) -> None:
        super().__init__(f"packet {report.verdict()}, {report.errors} error(s); staged resources left at {staging}")
        self.report = report
        self.staging = staging


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
    ) -> None:
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
        #: that table last: reading it back left every table added before it unfilled, and only the
        #: adapters that happened to emit the column themselves were saved by it.
        self._session = session
        core_context = registry if isinstance(registry, CheckedRegistryContext) else check_registry_context(registry)
        if core_context.result.state != "valid":
            raise RegistryRejected("core", core_context)
        checked_registry = core_context.document
        assert isinstance(checked_registry, Mapping)
        self._registry = checked_registry
        #: Extension registries this packet carries (Part 09 §2), by `extension_id`. An extension is a
        #: registry document in R2's format, so everything below resolves a resource against core
        #: and then these -- there is no second code path for an extension's tables.
        self._extensions: dict[str, Mapping[str, Any]] = {}
        for supplied in extensions:
            extension_context = (
                supplied
                if isinstance(supplied, CheckedRegistryContext)
                else check_registry_context(supplied, core=core_context)
            )
            if extension_context.core is not core_context:
                extension_context = check_registry_context(extension_context.document, core=core_context)
            if extension_context.result.state != "valid":
                subject = str(extension_context.document.get("extension_id", "extension"))
                raise RegistryRejected(subject, extension_context)
            document = extension_context.document
            assert isinstance(document, Mapping)
            extension_id = str(document["extension_id"])
            if extension_id in self._extensions:
                versions = (self._extensions[extension_id]["registry_version"], document["registry_version"])
                raise ValueError(
                    f"two registries for extension {extension_id!r} (versions {versions[0]} and {versions[1]}); a "
                    "packet binds one per extension (Part 04 §8, Part 05 §3.1), so the writer keeps neither"
                )
            for resource_id in document["resources"]:
                if not resource_id.startswith(f"{extension_id}."):
                    raise ValueError(
                        f"{resource_id} is not namespaced by {extension_id!r}; Part 09 §2 requires it, "
                        "and an extension MUST NOT define a table in core or analysis"
                    )
                if resource_id in checked_registry["resources"]:
                    raise ValueError(f"{resource_id} redefines a core resource, which Part 09 forbids")
            self._extensions[extension_id] = document
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
            build does (Part 05 §3.5), rather than settling them like any other row.

        Raises
        ------
        AmendmentRefused
            If a held row owns an assigned identifier and gives it no name.
        """
        documents = (self._registry, *self._extensions.values())
        declarations = {rid: decl for document in documents for rid, decl in document["resources"].items()}
        held.bind(
            {rid: decl["table"] for rid, decl in declarations.items() if decl.get("kind") == "table"},
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
        if declaration_id in self._registry["resources"]:
            declaration: Mapping[str, Any] = self._registry["resources"][declaration_id]
            return declaration
        for document in self._extensions.values():
            if declaration_id in document["resources"]:
                declaration = document["resources"][declaration_id]
                return declaration
        return None

    def spec(self, resource_id: str) -> Mapping[str, Any] | None:
        """Return the registry entry for one resource, core or extension, or None if undefined.

        One lookup for both, because R17 §3's claim is that an extension needs no second code
        path: it is a registry document in R2's format, so a table of one is a table of the other.
        """
        declaration = self.declaration(resource_id)
        if declaration is None or declaration.get("kind") != "table":
            return None
        spec: Mapping[str, Any] = declaration["table"]
        return spec

    def extension_of(self, resource_id: str) -> str | None:
        """Return which extension defines this resource, or None where core does."""
        for extension_id, document in self._extensions.items():
            if resource_id in document["resources"]:
                return extension_id
        return None

    def _family_declaration(self, declaration_id: str, resource_id: str, kind: str) -> Mapping[str, Any]:
        """Resolve an explicit family declaration and check that it admits this instance."""
        declaration = self.declaration(declaration_id)
        if declaration is None:
            raise ValueError(f"{resource_id}: unknown declaration {declaration_id!r}")
        if declaration["kind"] != kind:
            raise ValueError(f"{resource_id}: {declaration_id} has kind {declaration['kind']!r}, not {kind!r}")
        if declaration["instances"]["mode"] not in {"catalog", "family"}:
            raise ValueError(f"{resource_id}: {declaration_id} does not admit family instances")
        owner = declaration_id.split(".", 1)[0]
        if not resource_id.startswith(f"{owner}."):
            raise ValueError(f"{resource_id}: namespace is not owned by declaration {declaration_id!r}")
        return declaration

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
            raise ValueError(
                f"{resource_id}: {catalog}.{source_column}={source_value!r} resolves {len(matching)} catalog rows"
            )
        current = matching[0].get(resource_column)
        if current is not None and current != resource_id:
            raise ValueError(f"{catalog}.{resource_column} is {current!r}, not delivered resource {resource_id!r}")
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
            Consumed once, at commit, before any table given to `add` is built. A generator is
            the expected shape, and keeps the source's rows out of memory until they are written.

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
            raise ValueError(f"lineage was recorded for {missing}, which this packet does not carry")
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
        ValueError
            If this resource already has an array.
        """
        if resource_id in self._staged_arrays:
            raise ValueError(f"{resource_id} already has an array staged")
        if array.resource_id != resource_id:
            raise ValueError(f"{resource_id}: staged array declares resource_id {array.resource_id!r}")
        if not array.declaration_id:
            array = self._delivered_binding(resource_id, array)
        declaration = self._family_declaration(array.declaration_id, resource_id, "dense_array")
        self._bind_catalog_row(declaration, resource_id, "array_asset_id", array.array_asset_id)
        self._staged_arrays[resource_id] = array

    def _delivered_binding(self, resource_id: str, array: StagedArray) -> StagedArray:
        """Bind an array delivered by name to the one catalog row carrying that name (Part 12 §5).

        A delivery names an array's directory by the row's `resource_id` and says nothing else, so
        the row is found among every dense-array catalog, and the array takes that catalog's
        declaration and the row's own identifier.
        """
        matching = []
        for declaration_id in (
            *self._registry["resources"],
            *(d for e in self._extensions.values() for d in e["resources"]),
        ):
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
            raise ValueError(f"{resource_id}: a delivered array binds {len(matching)} catalog rows, not one")
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
        ValueError
            If this resource already has an array, or if the URI does not match how it resolves:
            absolute where no `source` is named, relative where one is (Part 04 §5.5).
        """
        if resource_id in self._staged_arrays or resource_id in self._referenced_arrays:
            raise ValueError(f"{resource_id} already has an array")
        array = replace(array, uri=_check_reference(resource_id, array.uri, array.source))
        declaration = self._family_declaration(array.declaration_id, resource_id, "dense_array")
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
        ValueError
            If this resource already has media, or if the URI does not match how it resolves
            (Part 04 §5.5).
        """
        if resource_id in self._referenced_media:
            raise ValueError(f"{resource_id} already has media")
        media = replace(media, uri=_check_reference(resource_id, media.uri, media.source))
        declaration = self._family_declaration(media.declaration_id, resource_id, "opaque")
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

    def _opaque_declarations(self) -> tuple[dict[str, tuple[str, str]], set[str]]:
        """Every loaded opaque catalog family, to its catalog and column, and every opaque singleton."""
        families: dict[str, tuple[str, str]] = {}
        singletons: set[str] = set()
        for document in (self._registry, *self._extensions.values()):
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
        families, singletons = self._opaque_declarations()
        rows: dict[str, list[str]] = {}
        unbound: list[str] = []
        for declaration_id, (catalog, column) in sorted(families.items()):
            for row in self._tables.get(catalog, []):
                value = row.get(column)
                if value is None:
                    shown = {k: v for k, v in row.items() if k != "metadata"}
                    unbound.append(f"a {catalog} row carries no {column}, so nothing binds it: {shown}")
                    continue
                rows.setdefault(str(value), []).append(declaration_id)
        referenced = {*self._referenced_media, *self._referenced_arrays}
        problems: list[str] = []
        bound: list[tuple[opaque.StagedPayload, str]] = []
        by_id: dict[str, list[opaque.StagedPayload]] = {}
        for payload in self._payloads:
            resource_id, where = payload.resource_id, opaque.shown(payload.path.parent)
            by_id.setdefault(resource_id, []).append(payload)
            matched, singleton = rows.get(resource_id, []), resource_id in singletons
            if matched and singleton:
                problems.append(
                    f"{payload.source}: {where} names {resource_id}, which is both a catalog row's resource_id "
                    "and an opaque singleton declaration"
                )
            elif singleton:
                if payload.owned is not None and resource_id not in payload.owned:
                    problems.append(
                        f"{payload.source}: delivers a payload for opaque singleton {resource_id}, which the "
                        f"recipe does not leave {payload.source} owning (Part 05 §3.4)"
                    )
                bound.append((payload, resource_id))
            elif len(matched) == 1:
                bound.append((payload, matched[0]))
            elif matched:
                problems.append(
                    f"{payload.source}: {where} names {resource_id}, which {len(matched)} catalog rows carry"
                )
            else:
                problems.append(
                    f"{payload.source}: {where} names {resource_id}, which is the resource_id of no catalog row of "
                    "an opaque catalog family and the ID of no opaque singleton declaration"
                )
        for resource_id, payloads in sorted(by_id.items()):
            places = ", ".join(f"{p.source} at {opaque.shown(p.path.parent)}" for p in payloads)
            if len(payloads) > 1:
                problems.append(f"{resource_id} is delivered as a payload {len(payloads)} times: {places}")
            if resource_id in referenced:
                problems.append(f"{resource_id} is delivered both as a payload ({places}) and as a referenced resource")
        delivered = set(by_id) | referenced
        unbound += [
            f"{families[declaration_id][0]} row with resource_id {resource_id} is bound by no payload or "
            "referenced resource"
            for resource_id, declarations in sorted(rows.items())
            for declaration_id in declarations
            if resource_id not in delivered
        ]
        if problems or unbound:
            raise opaque.PayloadRefused("; ".join([*problems, *unbound]) + " (Part 12 §5)")
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
                    "validation_state": "not_run",
                    "size_bytes": size,
                    "digest": _digest(path),
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
                    "validation_state": "not_run",
                    "size_bytes": opaque.size(staged),
                    "digest": _digest(staged),
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
                "validation_state": "not_run",
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
                "validation_state": "not_run",
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

        Records in `_ordered` the resources whose physical order `_write_stream` established as
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
                    self.rows_written[resource_id] = _write_stream(
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
                    raise OrderViolation(f"{resource_id}: {exc}") from None
                if sort_key(resource_id, spec):
                    self._ordered.add(resource_id)
                if not path.exists():
                    # Nothing the amendment adds, so the held entry stands (Part 05 §4.3).
                    continue
            else:
                built = build(resource_id, spec, self._tables[resource_id], self.keys, self._paired_kinds(resource_id))
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
                # `session.BATCH_ROWS` for the streaming case; here the trap is that estimating
                # from `Table.nbytes` is 320x out on a string-heavy table, because Arrow
                # materialises strings that Parquet stores as dictionary codes. It once split a
                # 101 KB table three ways.
                options = _options(resource_id, spec, table.schema, self._encoding_exceptions, table)
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
            _check_parquet_floor(path)
            entry: dict[str, Any] = {
                "resource_id": resource_id,
                "declaration_id": resource_id,
                "uri": encode(relative.split("/")),
                "validation_state": "not_run",
            }
            entry["digest"] = _digest(path)
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
            for run in held.named_rows("core.processing_runs", self.keys)
            if run.get("scope") is not None and run["activity_type"] != "import"
        }
        held_runs = held.held_names.get("processing_run_id", set())
        preferred = {
            (row.get("session_id", self._session), row["activity_type"], row["scope_kind"], row["scope"])
            for row in self._tables.get("core.preferred_runs", [])
        }
        adding = []
        for run in self._tables.get("core.processing_runs", []):
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
            self.add("core.preferred_runs", adding)

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
        for row in sorted(self._tables.get("core.intervals", []), key=self._interval_order):
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
        documents = [self._registry, *self._extensions.values()]
        for owner, declaration in ((n, d) for doc in documents for n, d in doc["resources"].items()):
            if declaration.get("kind") != "table":
                continue
            for column in declaration["table"]["columns"]:
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
        ValueError
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
            raise ValueError(f"the source resolution document would not satisfy its schema: {'; '.join(problems)}")
        return document

    def stage_at(self, root: str | Path) -> Path:
        """Prepare, empty, the staging area `commit` or `amend` will use at `root`, and return it.

        For a build pointing deliveries there before any source runs, so the commit moves what they
        wrote by rename (Part 12 §5) and keeps it rather than clearing it.

        Raises
        ------
        FileExistsError
            If `root` already holds a committed manifest and this writer amends none.
        PromotionRecordUnreadable
            If the staging area holds a promotion record this writer cannot read.
        """
        root = Path(root)
        _act_on_promotion(root)
        if self._held is None:
            _refuse_occupied(root)
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
        FileExistsError
            If `root` already holds a committed manifest.
        ValueError
            If no `core.sessions` records were added.
        CommitRefused
            If validation found errors. Nothing is committed, and staging and the delivery
            workspace are left in place.
        PromotionRecordUnreadable
            If the staging area holds a promotion record this writer cannot read.
        """
        root = Path(root)
        _act_on_promotion(root)
        _refuse_occupied(root)
        # R1 §6 makes the session inventory part of the manifest and the schema requires it
        # non-empty. Refusing here beats letting the staged manifest fail its own schema,
        # which surfaces as an unhelpful error from a directory the caller never named.
        if not self._tables.get("core.sessions"):
            raise ValueError("a packet declares at least one session; core.sessions is empty (R1 §6)")

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
        (staging / MANIFEST).write_text(json.dumps(self._manifest(entries, registries, None), indent=2) + "\n")
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
            (staging / MANIFEST).write_text(json.dumps(self._manifest(entries, registries, None), indent=2) + "\n")
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

        # 3. record every path promotion creates, then move into final paths, the resolution
        #    document first since it alone can still fail
        sources = self._sources_document()
        promoted = [name for name in PROMOTED if (staging / name).exists()]
        creates = [*promoted, *([SOURCES] if sources is not None else []), f"{MANIFEST}.candidate"]
        _claim(root, creates)
        _record_promotion(staging, str(self._manifest(entries, registries, None)["packet_version"]), creates)
        if sources is not None:
            (root / SOURCES).write_text(json.dumps(sources, indent=2) + "\n")
        for entry in entries:
            entry["validation_state"] = "passed"
        for name in promoted:
            shutil.move(str(staging / name), str(root / name))

        # 4. rename the manifest last: until this line the root holds no manifest at all,
        #    so a reader finds nothing rather than a partial import claiming to be valid.
        candidate = root / f"{MANIFEST}.candidate"
        candidate.write_text(json.dumps(self._manifest(entries, registries, report), indent=2) + "\n")
        os.replace(candidate, root / MANIFEST)
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
        ValueError
            If `packet_version` does not sort after the packet's.
        CommitRefused
            If validation found errors. The packet stays at its previous version, and nothing
            was written outside the staging area.
        PromotionRecordUnreadable
            If the staging area holds a promotion record this writer cannot read.
        """
        root = Path(root)
        _act_on_promotion(root)
        if not (root / MANIFEST).is_file():
            raise NotCommitted(f"{root} holds no committed {MANIFEST}; use commit() to create a packet")
        if self._held is None:
            self.amending(Held.open(root))
        held = self._held
        assert held is not None
        superseded = dict(held.manifest)
        version = packet_version or _bump(str(superseded["packet_version"]))
        if semver(version) <= semver(str(superseded["packet_version"])):
            raise ValueError(
                f"packet_version {version} does not sort after {superseded['packet_version']} (Part 05 §15.1)"
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
        retained = [
            f"{MANIFESTS}/nwb.packet.{manifest['packet_version']}.json"
            for manifest in (superseded, amended)
            if not (root / MANIFESTS / f"nwb.packet.{manifest['packet_version']}.json").exists()
        ]
        creates = {_created(root, relative) for relative in (*moved, *added_registries, *retained)}
        creates |= {f"{MANIFEST}.candidate"}
        _claim(root, creates)
        _record_promotion(staging, version, creates)
        for relative in (*moved, *added_registries):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staging / relative), str(destination))
        by_id = {e["resource_id"]: e for e in entries}
        amended["resources"] = [
            dict(by_id[e["resource_id"]], validation_state="passed") if e["resource_id"] in by_id else e
            for e in amended["resources"]
        ]
        amended["registries"] = {
            name: dict(bound, path=str(bound["path"]).removeprefix(f"{STAGING}/")) for name, bound in registries.items()
        }
        amended["validation"] = {
            "status": "passed",
            "validated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "validator_name": "escapewheel_validator",
            "validator_version": _version(),
        }

        self._retain(root, superseded, amended)
        candidate_path = root / f"{MANIFEST}.candidate"
        candidate_path.write_text(json.dumps(amended, indent=2) + "\n")
        os.replace(candidate_path, root / MANIFEST)
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

    def _retain(self, root: Path, superseded: Mapping[str, Any], amended: Mapping[str, Any]) -> None:
        """Keep every manifest a packet has had (Part 05 §15.3).

        A superseded file is only interpretable if the manifest that named it still exists;
        without these, an orphan and a stray are indistinguishable and a recorded `digest` points
        at a state nothing can reconstruct.
        """
        versions = root / MANIFESTS
        versions.mkdir(exist_ok=True)
        for manifest in (superseded, amended):
            path = versions / f"nwb.packet.{manifest['packet_version']}.json"
            # An existing copy is the one an earlier amendment retained, and retained bytes are
            # not rewritten.
            if not path.exists():
                path.write_text(json.dumps(manifest, indent=2) + "\n")

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
        for manifest_path in [root / MANIFEST, *sorted((root / MANIFESTS).glob("*.json"))]:
            if manifest_path.is_file():
                for name, bound in json.loads(manifest_path.read_text()).get("registries", {}).items():
                    recorded.setdefault((name, bound["version"]), bound)
        descriptors: dict[str, dict[str, str]] = {}
        added: list[str] = []
        for document in (self._registry, *self._extensions.values()):
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
                raise ValueError(
                    f"this packet already binds a different {registry_id} {version} at {relative}; two digests "
                    "under one registry ID and version cannot both be retained (Part 05 §15.3). Bump registry_version."
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


__all__ = [
    "MANIFEST",
    "MANIFESTS",
    "PROFILE",
    "PROMOTION",
    "PROVENANCE",
    "REGISTRIES",
    "STAGING",
    "CommitRefused",
    "ExternalMedia",
    "NotCommitted",
    "PacketWriter",
    "PromotionRecordUnreadable",
    "read_promotion",
    "semver",
]

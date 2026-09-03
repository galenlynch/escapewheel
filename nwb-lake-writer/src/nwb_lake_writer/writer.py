"""Stage, validate, and commit a packet.

`05`'s core principle is that **validation is importation**: copying or converting bytes is
only staging, and a resource is not imported until it has passed the checks for its schema.
This module is the writer and committer halves of that pipeline. It knows nothing about NWB,
SpikeInterface, or any other source -- adapters hand it records, and it turns them into a
packet or refuses to.

The commit sequence is `05` Stage 5's, and its ordering is the whole guarantee:

1. write staged resources under ``staging/``;
2. validate them there;
3. move them into their final paths;
4. rename the manifest to ``nwb.packet.json`` **last**.

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
from nwb_lake_reader import Manifest, Packet, open_packet
from nwb_lake_validator import Report, validate, verify_order
from nwb_lake_validator.generate import adjacency_settles_uniqueness

from .arrow import build, number_batch, schema, sort_key
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


#: Where a manifest lives once committed (`04`).
MANIFEST = "nwb.packet.json"

#: Where a packet embeds the registry it was written against (R2 §8).
REGISTRY_PATH = "schemas/logical_schemas.json"
#: Where an extension registry lives in a packet (R17 §2, `09` §6).
EXTENSIONS_PATH = "extensions"

#: `03`'s portable profile.
PROFILE = "nwb-lake-portable-v0.1"


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
DELTA_COLUMNS: dict[str, tuple[str, ...]] = {
    "core.clock_anchors": ("anchor_index",),
    "core.units": ("n_spikes",),
}


def _delta_columns(resource_id: str, out: pa.Schema) -> list[str]:
    """Integer columns to store as `DELTA_BINARY_PACKED`, which pyarrow never picks itself.

    Every `*_tick` column qualifies by the naming convention alone: a tick is a large integer
    on a monotonic clock, so its residuals bit-pack far smaller than the eight bytes PLAIN
    spends, and a high-cardinality tick overflows the dictionary page and falls back to PLAIN
    anyway. Measured over a real session, delta takes `core.clock_anchors.t_tick` from 268.8 KB
    to 5.2 KB and `core.spike_events.t_tick` from 660.9 MB to 462.1 MB, and it is no worse than
    the default on the one tick column that is unordered (`core.units.first_spike_tick`, 0.77x).

    The rule is monotonicity, not integer-ness, which is why it is not simply "every integer
    column". `core.unit_electrodes.channel_index` cycles 0..25 once per unit, and RLE over a
    26-entry dictionary beats delta there by 1.38x.
    """
    named = set(DELTA_COLUMNS.get(resource_id, ()))
    return [f.name for f in out if (f.name.endswith("_tick") or f.name in named) and pa.types.is_integer(f.type)]


def _options(resource_id: str, spec: Mapping[str, Any], out: pa.Schema) -> dict[str, Any]:
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
    if delta := _delta_columns(resource_id, out):
        options["use_dictionary"] = [n for n in out.names if n not in delta]
        options["column_encoding"] = dict.fromkeys(delta, "DELTA_BINARY_PACKED")
    keys = sort_key(spec) or []
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


def _write_stream(spec: Mapping[str, Any], batches: Iterable[pa.RecordBatch], path: Path, resource_id: str) -> None:
    """Write batches to Parquet one row group at a time, casting each to the registry schema.

    The first batch fixes the schema, exactly as the first record does on the records path:
    an optional column is emitted when something carries it. A later batch may omit a
    declared column -- it is written as nulls, like a record that lacks the key -- but may
    not introduce one the schema does not have, because that column would be dropped without
    a word.

    An empty stream writes nothing and leaves no file, matching the records path, where a
    resource with no rows is simply absent from the packet.

    Each batch becomes exactly one row group, so the caller controls row-group boundaries as
    well as order. That is what lets `analysis.spike_events` keep every row group inside a
    single time bucket (R30 §3.2) — cutting at a fixed row count instead would let a group
    straddle two buckets and span twice the intended time range — and it is what lets a caller
    size row groups for the store the packet will live on.
    """
    writer: pq.ParquetWriter | None = None
    out: pa.Schema | None = None
    try:
        # Verified on the way in, not read back afterwards. The rows pass through here
        # already sorted by the source, so comparing them costs the comparison alone, where
        # establishing the same fact from the written file costs re-reading its sort columns --
        # 467 MB on a quarter of a billion spikes. It runs inside the producer thread, so the
        # comparison overlaps the Parquet encoding rather than adding to it. `commit` tells the
        # validator which resources this settled; a validator handed an unknown packet still
        # reads every one.
        keys = sort_key(spec) or []
        unique = spec["primary_key"] if keys and adjacency_settles_uniqueness(spec) else None
        # Three stages, not two: building a batch, comparing it and encoding it cost 2.5 s,
        # 2.2 s and 2.6 s on a 23 M-spike stream, so folding the comparison into the producer
        # made it the bottleneck and gave back exactly what skipping the re-read saved. A queue
        # either side of it lets all three run at once, and the slowest one sets the pace.
        for batch in _prefetch(_prefetch(verify_order(batches, keys, unique)) if keys else batches):
            if out is None:
                out = _as_held(schema(spec, set(batch.schema.names)), batch.schema)
                writer = pq.ParquetWriter(path, out, **_options(resource_id, spec, out))
            if extra := sorted(set(batch.schema.names) - set(out.names)):
                raise ValueError(
                    f"batch carries {extra}, which the first batch did not; the column would be dropped silently"
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
    finally:
        if writer is not None:
            writer.close()


#: Core tables an amendment may extend (R32 §3). Append-only by nature: a row records that
#: something ran, and a later run does not change what an earlier one did.
PROVENANCE = ("core.processing_runs", "core.source_files", "core.processing_run_inputs")

#: Where superseded manifests are retained (R32 §4).
MANIFESTS = "manifests"


def _bump(version: str) -> str:
    """Return the next packet version.

    Patch level, so a packet under development stays inside one minor series while the
    structure moves. R32 §2 requires only that the new version sort strictly after the
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
    """A dense array the packet references rather than owns (R14 §2.3).

    Referencing is the expected form for a large one. Copying duplicates the bulk of a dataset
    for no gain, and transcoding to the portable floor throws away the acquisition's own
    compression -- 5.8 GB of LFP across twelve probes, against three integers per series once
    R20 replaces its timestamps.

    `sha256`, `size_bytes`, `members` and `verified_at` record what was true when someone
    looked, not a promise about now: immutability covers packet-owned bytes only (R14 §2.3.1),
    and an external array may change or vanish without the packet changing at all.

    `members` is R51 §2.1's record of what the prefix held, each entry carrying whatever the
    store said about itself. It is a record and not a resolution rule -- a reader hands the URI
    to Zarr, which addresses chunks by key and never enumerates.
    """

    array_asset_id: str
    uri: str
    physical_profile: str = "zarr_v3"
    codecs: tuple[str, ...] = ()
    sha256: str | None = None
    size_bytes: int | None = None
    verified_at: str | None = None
    members: tuple[dict[str, Any], ...] | None = None


def _digest(path: Path) -> str:
    """R52 §2.1: what the packet says its own bytes are.

    Recorded for every packet-owned resource and not optional, because the promise it makes
    checkable is not optional either: R14 §2.3 declares these bytes immutable and R35 §2 spends
    that, bounding revalidation after an amendment to what the amendment wrote. Costs 0.5% of a
    build -- the bytes were just written, so they are in page cache and hash at ~2 GB/s.

    A prefix goes through R36 §2.2's canonical listing, a single file is its own bytes; `digest`
    already distinguishes them.
    """
    from nwb_lake_validator.stores import digest

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
        The registry to write against. It is embedded in the packet (R2 §8), so the packet
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
    ) -> None:
        self._registry = registry
        #: Extension registries this packet carries (R17 §2), by `extension_id`. An extension is a
        #: registry document in R2's format, so everything below resolves a resource against core
        #: and then these -- there is no second code path for an extension's tables.
        self._extensions: dict[str, Mapping[str, Any]] = {}
        for document in extensions:
            extension_id = str(document["extension_id"])
            for resource_id in document["tables"]:
                if not resource_id.startswith(f"{extension_id}."):
                    raise ValueError(
                        f"{resource_id} is not namespaced by {extension_id!r}; R17 §2 requires it, "
                        "and an extension MUST NOT define a table in core or analysis"
                    )
                if resource_id in registry["tables"]:
                    raise ValueError(f"{resource_id} redefines a core table, which R17 §2 forbids")
            self._extensions[extension_id] = document
        #: Assigns the integer every identifier holds (R53 §2.5). One per packet, shared by every
        #: adapter, because two sources numbering the same probe differently is a defect no
        #: foreign key can see: both values resolve, to different rows.
        self.keys = Keys()
        self._packet_id = packet_id
        self._description = description
        self._tables: dict[str, list[Mapping[str, Any]]] = {}
        self._batches: dict[str, Iterable[pa.RecordBatch]] = {}
        self._derived: dict[str, list[str]] = {}
        self._runs: dict[str, str] = {}
        self._ordered: set[str] = set()
        self._staged_arrays: dict[str, StagedArray] = {}
        self._referenced_arrays: dict[str, ExternalArray] = {}

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
            Rows. Keys absent from the registry's column list are ignored.

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
        self._tables.setdefault(resource_id, []).extend(records)

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
        self._batches[resource_id] = (number_batch(spec, b, self.keys) for b in batches)

    def derives(self, resource_id: str, sources: Sequence[str]) -> None:
        """Record which resources one was derived from (`06`).

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

        Packet-owned, so `zarr_v3` (R21 §3.1) -- v2 is permitted only for a resource the packet
        references rather than owns. The codecs it uses are declared per resource (R15 §2), so
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
        """Record a dense array the packet references rather than owns (R14 §2.3).

        No bytes are copied and none are read: structural validation must not reach the network
        (R14 §2.3.2), so what this records is a claim. A validator reports it as `info` in its
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
            If this resource already has an array, or if the URI is not absolute -- a relative
            one would resolve against a packet the bytes do not live in.
        """
        if resource_id in self._staged_arrays or resource_id in self._referenced_arrays:
            raise ValueError(f"{resource_id} already has an array")
        if "://" not in array.uri:
            raise ValueError(f"{resource_id}: {array.uri!r} is not absolute, so it cannot resolve without the packet")
        self._referenced_arrays[resource_id] = array

    def produced_by(self, resource_id: str, processing_run_id: str) -> None:
        """Name the run that produced a resource (R31 §2).

        `06` requires a derived resource to declare its transform parameters and software
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
            for name in ("sha256", "size_bytes", "verified_at"):
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
                _write_stream(spec, self._batches[resource_id], path, resource_id)
                if sort_key(spec):
                    self._ordered.add(resource_id)
            else:
                table = build(spec, self._tables[resource_id], self.keys)
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
                pq.write_table(table, path, **_options(resource_id, spec, table.schema))
            extension_id = self.extension_of(resource_id)
            entry = {
                "resource_id": resource_id,
                # R17 §4: an extension table's entry says so and names its owner, so a reader
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
                entry["processing_run_id"] = run
            entries.append(entry)
        return entries

    def _preassign(self) -> None:
        """Assign a number to every name this packet uses, before any table is built (R53 §2.5).

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
            "validator_name": "nwb_lake_validator",
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
            # R15 §2 declares codecs per resource; the top-level list is their union, so a
            # reader can answer "can I open this packet at all" without walking every entry.
            "required_codecs": sorted({c for e in entries for c in e.get("codecs", [])}),
            "resources": [dict(e) for e in entries],
            "validation": validation,
        }
        if inventory := self._extension_inventory():
            manifest["extensions"] = inventory
        if self._description is not None:
            manifest["description"] = self._description
        return manifest

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
            overwritten, because immutability covers packet-owned bytes (R14 §2.3).
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
        entries = [*self._stage(staging), *self._stage_arrays(staging), *self._reference_arrays()]
        say(f"staged {len(entries)} resources in {time.perf_counter() - clock:.1f} s")
        clock = time.perf_counter()
        (staging / "schemas").mkdir(parents=True, exist_ok=True)
        (staging / REGISTRY_PATH).write_text(json.dumps(self._registry, indent=2) + "\n")
        self._install_extensions(staging)

        # 2. derive whatever the caller asked for from the staged packet, before anything is
        #    validated or promoted. `05` stages 8 and 9 put materialization inside the import
        #    pipeline, and a staged packet is already openable -- it needs a manifest, which is
        #    written here anyway. Doing it now costs one validation over the finished packet;
        #    doing it after the commit costs a second manifest, a version bump and a
        #    revalidation of resources validated seconds earlier, which is what `amend` is for
        #    and what a build the recipe fully describes should never pay.
        (staging / MANIFEST).write_text(json.dumps(self._manifest(entries, None), indent=2) + "\n")
        if materialize:
            # Row counts, not just names: a materializer adds its own `core.processing_runs`
            # row (R31 §2), and that table was staged in the pass above. Restaging only what is
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
        written as a **new file** and the amended manifest names that one, so R14 §2.3's
        immutability holds literally rather than by exception.

        The sequence is `commit`'s, with the swap at the end doing more work: the added
        resources are staged and validated before anything reaches a final path, the superseded
        manifest and registry are retained, and `nwb.packet.json` is replaced by an atomic
        rename last. A reader sees the old packet or the new one, never a blend.

        Parameters
        ----------
        root : str or Path
            A packet root holding a committed manifest.
        packet_version : str, optional
            The new version. Defaults to bumping the minor component.
        limits : Mapping, optional
            DuckDB settings bounding validation. R35 §5 narrows an amendment to the rules
            attached to a written resource or naming one, but every table is still registered
            alongside it, so a surviving rule may read anything the packet holds.

        Returns
        -------
        Report
            The validation report for the **whole** packet, not only what was added (R32 §5).

        Raises
        ------
        NotCommitted
            If `root` holds no committed manifest. Use `commit` to create a packet.
        ValueError
            If the amendment would replace a core resource other than a provenance table, which
            is a new packet rather than a new version of this one (R32 §3).
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
                f"amending would replace {clash}; a packet whose core data changes is a new packet (R32 §3)"
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
        # is what keeps the session inventory and description from silently vanishing (R32 §4).
        kept = [e for e in superseded["resources"] if e["resource_id"] not in added]
        candidate = dict(superseded)
        candidate["resources"] = kept + [dict(e, uri=f"staging/{e['uri']}") for e in entries]
        candidate["registry_version"] = self._registry["registry_version"]
        candidate["packet_version"] = packet_version or _bump(superseded["packet_version"])
        candidate["supersedes"] = superseded["packet_version"]

        # The registry goes in before validation, not after: the validator compares the
        # manifest's declared registry_version against the copy the packet carries (R2 §9), so
        # a candidate declaring the new version against the old embedded copy fails on a
        # mismatch that says nothing about the data. Rolled back if this does not pass, which
        # leaves the packet exactly as it was.
        restore = self._install_registry(root)
        try:
            # Both halves of the amendment are bounded by what it writes (R35). Physical order
            # is re-read only for those files, and only the rules attached to one or naming one
            # re-run. A file the amendment does not name is byte-identical to one already
            # verified -- R32 §3 forbids modifying it and R14 §2.3 declares it immutable -- so
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
            "validator_name": "nwb_lake_validator",
            "validator_version": _version(),
        }

        self._retain(root, superseded, amended)
        candidate_path = root / f"{MANIFEST}.candidate"
        candidate_path.write_text(json.dumps(amended, indent=2) + "\n")
        os.replace(candidate_path, root / MANIFEST)
        shutil.rmtree(staging)
        return report

    def _absorb_provenance(self, root: Path, superseded: Mapping[str, Any]) -> None:
        """Carry a provenance table's existing rows into the amendment (R32 §3).

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
                    "rows to a provenance table, it does not revise them (R32 §3)"
                )
            self._tables[resource_id] = [*existing, *self._tables[resource_id]]

    def _retain(self, root: Path, superseded: Mapping[str, Any], amended: Mapping[str, Any]) -> None:
        """Keep every manifest a packet has had (R32 §4).

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
        """Write each extension registry into the packet, beside the core one (R17 §5, `09` §6).

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
        """Put this writer's registry in the packet, retaining the superseded copy (R32 §4.1).

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
                f"two different {self._registry['registry_version']} in one packet (R32 §4.1). Bump "
                "registry_version, or rebuild the packet so it retains only one."
            )

        previous = installed.read_bytes() if installed.is_file() else None
        if previous is not None:
            embedded = json.loads(previous)
            if embedded["registry_version"] == self._registry["registry_version"]:
                if embedded != self._registry:
                    raise ValueError(
                        f"registry {embedded['registry_version']} differs from the packet's copy at the same "
                        "version; two registries that cannot be told apart make R2 §8 vacuous (R32 §4.1)"
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
    "NotCommitted",
    "PacketWriter",
]

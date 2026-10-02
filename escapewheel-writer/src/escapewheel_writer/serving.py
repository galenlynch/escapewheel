"""An adapter's rows served across a process boundary, in the adapter's process (Part 12 §3).

- :func:`construct` -- an adapter built from the JSON object a build passed.
- :func:`infers` -- the protocol a build reached the adapter by, from the term that build supplied.
- :func:`serve` -- one adapter's rows delivered over that protocol.
- :func:`offered` -- everything one adapter has to deliver, per resource.
- :func:`written_arrays` -- the arrays a source stages, written into the location supplied.
- :func:`referenced` -- the resource document for the resources a source references rather than
  writes.
- :func:`report_of` -- an adapter's report on its run.
- :func:`as_table` -- records as a table with every column that any row carries.
- :data:`SENTINEL`, :data:`RESOURCES`, :data:`COMPENSATIONS` -- the three reserved `resource_id`
  values of a delivery.

Arrays and opaque payloads cross as bytes in a location a build supplies (Part 12 §5), not as rows.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from . import opaque
from .bindings import ExternalArray, ExternalMedia, ExternalResource
from .declaration import FILES, FLIGHT, REPORT_AS_FILE, SOURCE_CACHE, STREAM
from .errors import SourceDefect, SourceFault, UnknownSourceKind
from .kinds import required_adapter
from .protocols import (
    DeclaresCompensations,
    ReferencesArrays,
    ReferencesMedia,
    ReferencesResources,
    SourceAdapter,
    StagesArrays,
    StagesPayloads,
    Streams,
)
from .sources.compensations import describe

#: The reserved `resource_id` ending a `stream-v0.1` delivery (Part 12 §6). A resource
#: identifier is dotted, so no undotted token can collide with it.
SENTINEL = "end"

#: The second: what a delivery says about the resources it references rather than
#: writes (Part 12 §5). Carried as text in a single-row table where a protocol carries Arrow,
#: so the manifest's schema stays the one description of an entry.
RESOURCES = "resources"

#: The third: the table a delivery states its adapter's compensations in (Part 12 §5).
COMPENSATIONS = "compensations"

#: One resource of a delivery: a held table, or the batches of one too large to hold.
Rows = pa.Table | Iterator[pa.RecordBatch]


def as_table(rows: Sequence[Mapping[str, Any]]) -> pa.Table:
    """Return records as a table, taking the columns from every row rather than from the first.

    `pa.Table.from_pylist` infers the schema from the leading row and drops what later rows carry,
    which loses a column a source populates for some rows only -- and an absent column is a
    statement under Part 12 §5, so losing one says something untrue. Types are the build's to
    settle against the registry, so nothing here declares one.

    A mapping is the exception, and it is not a type decision: the standard stores one as JSON text
    in an optional column and forbids a nested type outright (Part 02 §5.2), so a value that
    arrived as a struct could not be cast to what the packet stores. Encoded here in the form the
    writer would have written, which is what makes the two routes produce one byte string.
    """
    columns = list(dict.fromkeys(name for row in rows for name in row))
    return pa.Table.from_pylist([{c: _flat(row.get(c)) for c in columns} for row in rows])


def _flat(value: Any) -> Any:
    """Return a value in a form Arrow can carry across a boundary without inventing a type."""
    from .arrow import canonical_json

    return canonical_json(value) if isinstance(value, (Mapping, list, tuple)) else value


def offered(source: SourceAdapter) -> dict[str, Iterator[pa.RecordBatch] | pa.Table]:
    """Everything one adapter has to deliver, per resource, without materializing a large one.

    A table that streams stays a stream: `core.spike_events` is 10^8 rows, and a delivery that
    holds it as host objects costs two orders of magnitude more than the bytes it becomes.
    """
    delivering: dict[str, Iterator[pa.RecordBatch] | pa.Table] = {}
    for resource, rows in source.records().items():
        delivering[resource] = as_table(rows)
    if isinstance(source, Streams):
        delivering.update(source.batches())
    return delivering


def written_arrays(source: SourceAdapter, location: str | None) -> int:
    """Write every array this source stages into the location a build supplied (Part 12 §5).

    The adapter writes, because an array does not cross as rows and a reference to one a build
    cannot open is no use to it. Each goes in a directory named by its catalog row's `resource_id`,
    which is all a build binds it by.
    """
    staged = list(source.staged_arrays()) if isinstance(source, StagesArrays) else []
    if not staged:
        return 0
    if not location:
        raise SourceDefect(
            "this source stages a dense array and no array_location was supplied; an array crosses "
            "as bytes under a location a build names (Part 12 §5)",
            code=SourceFault.NO_ARRAY_LOCATION,
        )
    from .arrays import write_zarr

    root = Path(location)
    root.mkdir(parents=True, exist_ok=True)
    for array in staged:
        write_zarr(root / f"{array.resource_id}.zarr", array)
    return len(staged)


def referenced(source: SourceAdapter) -> dict[str, Any] | None:
    """Return the resource document for what this source references rather than writes.

    One entry per resource, each a manifest resource entry (Part 04 §5), carrying what the
    producer established by opening the store — which is the half of a manifest no row holds and
    no build may go looking for.
    """
    from dataclasses import fields

    declared: dict[str, ExternalArray | ExternalMedia | ExternalResource] = {}
    if isinstance(source, ReferencesArrays):
        declared.update(source.external_arrays())
    if isinstance(source, ReferencesMedia):
        declared.update(source.external_media())
    if isinstance(source, ReferencesResources):
        declared.update(source.external_resources())
    entries = []
    for resource_id, resource in declared.items():
        entry = {"resource_id": resource_id, "external": True}
        for field in fields(resource):
            value = getattr(resource, field.name)
            if (
                value is not None
                and not field.name.endswith("_asset_id")
                and field.name not in {"physical_profile", "codecs", "format"}
            ):
                entry[field.name] = value
        entries.append(entry)
    return {"resources": entries} if entries else None


def construct(kind: str, supplied: Mapping[str, Any]) -> SourceAdapter:
    """Build one adapter from the JSON object a build passed, and from nothing else.

    The terms the adapter declared arrive at the top level and the recipe's options under
    `options`, so no option can collide with a term. A term the protocol required is not passed
    on: an adapter never declared it, and a build supplied it because of the protocol. The root is
    opened uncached, and an adapter accepting `source_cache` reads through it for itself.
    """
    from .sources.store import source_root

    try:
        adapter = required_adapter(kind)
    except UnknownSourceKind as exc:
        # A delivery fails as a source defect, which is what the command prints and exits on.
        raise SourceDefect(str(exc), code=SourceFault.UNKNOWN_KIND, where=kind) from None
    declared = getattr(adapter, "NEEDS", ("root", "session_id"))
    terms = {name: supplied[name] for name in declared if name in supplied and name != "root"}
    if SOURCE_CACHE in supplied and SOURCE_CACHE in getattr(adapter, "ACCEPTS", ()):
        terms[SOURCE_CACHE] = supplied[SOURCE_CACHE]
    if "root" not in supplied:
        raise SourceDefect(
            f"{kind}: nothing supplied a root, which every adapter needs", code=SourceFault.NO_ROOT, where=kind
        )
    options = dict(supplied.get("options", {}))
    # Opened here rather than by the adapter, because how a store is reached is the recipe's fact
    # and an adapter takes a root it can read. Absent, the default applies: a public bucket is
    # read anonymously, which is what a build handed a bare URI would otherwise sign for.
    root = source_root(supplied["root"], **dict(options.pop("storage_options", {})))
    return adapter(root, **terms, **options)


def infers(supplied: Mapping[str, Any]) -> str:
    """Which protocol a build reached this adapter by, from the term it supplied for it.

    A build supplies whichever terms its adapter's protocol requires (Part 12 §4), so the term
    that is there says which protocol this is without a second statement that could disagree with
    the first.
    """
    if "socket" in supplied:
        return FLIGHT
    if "delivery_root" in supplied:
        return FILES
    return STREAM


def serve(source: SourceAdapter, supplied: Mapping[str, Any], protocol: str, *, out: Any = None) -> None:
    """Deliver one adapter's rows over the protocol a build reached it by.

    Parameters
    ----------
    source : object
        The constructed adapter.
    supplied : Mapping
        The JSON object a build passed: the terms the adapter declared, plus whichever its
        protocol requires.
    protocol : str
        Which of Part 12 §3's protocols to deliver over.
    out : file-like, optional
        Where `stream-v0.1` writes. Standard output's binary handle by default, because a
        platform translating a line ending corrupts the stream (Part 12 §6).
    """
    written_arrays(source, supplied.get("array_location"))
    handed = source.staged_payloads() if isinstance(source, StagesPayloads) else ()
    opaque.write(handed, supplied.get("opaque_location"), type(source).__name__)
    delivering = offered(source)
    # A resource this source has nothing for arrives empty rather than not arriving, so a build
    # reads absence as the run having failed and never as the source having had nothing to say
    # (Part 12 §5). What it owns is what the recipe left it, where a build said so, and its
    # whole `produces` otherwise -- an adapter that is not told cannot narrow, and must not
    # deliver less than it declared either way.
    declares = sorted(getattr(type(source), "PRODUCES", ()) or ())
    wanted = list(supplied.get("wanted") or declares or delivering)
    tables = {name: delivering.get(name, as_table([])) for name in wanted}
    if (document := referenced(source)) is not None:
        tables[RESOURCES] = as_table([{"document": json.dumps(document, default=str)}])
    delivery = _with_compensations(tables, source)
    if protocol == STREAM:
        _serve_stream(delivery, out if out is not None else sys.stdout.buffer)
    elif protocol == FILES:
        _serve_files(delivery, Path(supplied["delivery_root"]))
    elif protocol == FLIGHT:
        _serve_flight(delivery, str(supplied["socket"]))
    else:
        raise SourceDefect(
            f"{protocol} is in no group this profile names", code=SourceFault.PROTOCOL_UNKNOWN, where=protocol
        )
    if (path := supplied.get("report_path")) and protocol in REPORT_AS_FILE:
        Path(path).write_text(json.dumps(report_of(source), indent=2, default=str) + "\n")


def _with_compensations(tables: Mapping[str, Rows], source: SourceAdapter) -> Iterator[tuple[str, Rows]]:
    """Each resource of a delivery, then the compensations its adapter applied (Part 12 §5).

    Stated last, since an adapter may apply one while a table before it streams. One that applied
    none delivers no such table.
    """
    yield from tables.items()
    applied = list(source.compensations) if isinstance(source, DeclaresCompensations) else []
    if stated := describe(applied):
        yield COMPENSATIONS, as_table(stated)


def report_of(source: SourceAdapter) -> dict[str, Any]:
    """Return the run's report (Part 12 §9): what a build cannot derive from the delivery.

    `stated` is the half no static document can carry -- a declared field's value needs the source
    read -- and the notes an adapter accumulated are the other: what it worked around, and why a
    table that is short is legitimately short.
    """
    stated = {field: getattr(source, attribute, None) for field, attribute in source.STATES.items()}
    problems = [{"level": "info", "message": note} for note in source.notes]
    return {"stated": {f: v for f, v in stated.items() if v is not None}, "problems": problems}


def _write(out: Any, resource: str, table: pa.Table | Iterator[pa.RecordBatch]) -> None:
    """One resource as a complete stream, ending with the format's own end-of-stream marker."""
    if isinstance(table, pa.Table):
        batches = table.to_batches() or [pa.RecordBatch.from_pylist([], schema=table.schema)]
    else:
        batches = list(table)
        if not batches:
            batches = [pa.RecordBatch.from_pylist([])]
    schema = batches[0].schema.with_metadata({"resource_id": resource})
    # Uncompressed bodies at metadata version V5, each dictionary whole (Part 12 §6).
    options = pa.ipc.IpcWriteOptions(compression=None, metadata_version=pa.ipc.MetadataVersion.V5)
    with pa.ipc.new_stream(out, schema, options=options) as writer:
        for batch in batches:
            writer.write_batch(batch.replace_schema_metadata({"resource_id": resource}))


def _serve_stream(tables: Iterable[tuple[str, Rows]], out: Any) -> None:
    """`stream-v0.1`: concatenated Arrow IPC streams, ended by the sentinel."""
    for resource, table in tables:
        _write(out, resource, table)
    _write(out, SENTINEL, pa.table({}))
    out.flush()


def _serve_files(tables: Iterable[tuple[str, Rows]], root: Path) -> None:
    """`files-v0.1`: one Parquet file per resource, under the root a build named."""
    root.mkdir(parents=True, exist_ok=True)
    for resource, table in tables:
        if resource == RESOURCES and isinstance(table, pa.Table):
            # A file is a file: the document goes down as JSON rather than as text in a table,
            # which is the envelope only a protocol carrying Arrow needs.
            (root / f"{RESOURCES}.json").write_text(table.column("document")[0].as_py())
            continue
        if isinstance(table, pa.Table):
            pq.write_table(table, root / f"{resource}.parquet")
            continue
        writer = None
        try:
            for batch in table:
                if writer is None:
                    writer = pq.ParquetWriter(root / f"{resource}.parquet", batch.schema)
                writer.write_batch(batch)
        finally:
            if writer is not None:
                writer.close()
        if writer is None:
            pq.write_table(as_table([]), root / f"{resource}.parquet")


def _serve_flight(tables: Iterable[tuple[str, Rows]], socket: str) -> None:
    """`flight-v0.1`: one descriptor per resource, served until the build terminates this process."""
    import pyarrow.flight as fl

    held = {name: t if isinstance(t, pa.Table) else pa.Table.from_batches(list(t)) for name, t in tables}

    class Served(fl.FlightServerBase):
        """One adapter's resources, each a Flight descriptor."""

        def list_flights(self, context: Any, criteria: Any) -> Iterator[Any]:
            """Part 05 §4.1's discovery, from Arrow's own vocabulary."""
            for name, table in held.items():
                descriptor = fl.FlightDescriptor.for_path(name)
                yield fl.FlightInfo(table.schema, descriptor, [], table.num_rows, table.nbytes)

        def do_get(self, context: Any, ticket: Any) -> Any:
            """One resource, by the descriptor a build asked for."""
            return fl.RecordBatchStream(held[ticket.ticket.decode()])

    # Bound last, and that is load-bearing: a build's first call arrives as soon as the socket
    # answers, so an adapter that binds before it can answer serves discovery half-built
    # (Part 12 §8).
    Served(fl.Location.for_grpc_unix(socket)).serve()


__all__ = [
    "COMPENSATIONS",
    "RESOURCES",
    "SENTINEL",
    "as_table",
    "construct",
    "infers",
    "offered",
    "referenced",
    "report_of",
    "serve",
    "written_arrays",
]

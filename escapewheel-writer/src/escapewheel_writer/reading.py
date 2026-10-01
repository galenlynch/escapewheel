"""What an adapter delivered across a process boundary, read in the build's process (Part 12 §3).

- :func:`fetch` -- run one adapter as a command and read what it delivered.
- :class:`Delivered` -- what a build received, shaped like an adapter.
- :func:`protocol_supplies` -- the terms one protocol adds to what a build supplies.

A build reads `files-v0.1` from disk a batch at a time, but holds each `stream-v0.1` or
`flight-v0.1` resource in memory as it arrives, so a large source should use `files-v0.1`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from io import IOBase
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader.resource_ids import CORE_ARRAY_ASSETS, CORE_MEDIA_ASSETS
from escapewheel_reader.uri import canonical, is_absolute

from .bindings import ExternalArray, ExternalMedia
from .declaration import FILES, FLIGHT, PROTOCOL_TERMS, REPORT_AS_FILE, STREAM
from .encoding import STREAMED_BATCH_ROWS
from .errors import DeliveryFailed, SourceDefect, SourceFault
from .notes import Note, NoteCode
from .serving import (
    RESOURCES,
    SENTINEL,
)

#: How long to wait between attempts on a `flight-v0.1` socket, in seconds. A build retries until
#: the address answers or the adapter's process exits (Part 12 §8), so this only decides how
#: soon an adapter that died before binding is noticed.
RETRY = 0.01

#: One protocol's reading half: what arrived per resource, and what was wrong with the run.
Reader = Callable[
    [str, Sequence[str], bytes, Mapping[str, Any], Sequence[str]], tuple[dict[str, Any], list[SourceDefect]]
]


class Delivered:
    """What a build received from a source it ran out of process, shaped like an adapter.

    Everything after the boundary is the same for a delivered source as for an imported one, so
    this offers what a build asks of any adapter: what it has per resource, and its rows as
    batches. Types, column order, numbering and the declared sort are settled afterwards against
    the registry, exactly as they are for rows handed over in process.
    """

    #: Nothing here stages an array; a source that does is refused before it is run.
    PRODUCES: frozenset[str] = frozenset()

    def __init__(
        self,
        kind: str,
        tables: Mapping[str, pa.Table | Path],
        *,
        notes: Sequence[str] = (),
        stated: Mapping[str, Any] = {},
        states: Sequence[str] = (),
        merged: Collection[str] = (),
        referenced: Sequence[Mapping[str, Any]] = (),
        arrays: Path | None = None,
    ) -> None:
        self.kind = kind
        self.tables = dict(tables)
        #: What the delivery said about the resources it references rather than writes, as
        #: manifest entries (Part 12 §5).
        self.referenced = list(referenced)
        #: Where this source wrote the arrays the packet will own, which a build reads back.
        self.arrays = arrays
        #: Resources this source shares with another, which come back as rows rather than as a
        #: stream: a writer takes one table from one path, since two streams cannot be put in the
        #: declared sort order across the seam between them.
        self.merged = frozenset(merged)
        self.notes = list(notes)
        #: Part 05 §3.6's comparison reads a declared field off the source, so a delivered one
        #: carries what its report stated under the same names an imported adapter would.
        self.STATES = {field: _attribute(field) for field in states}
        for field, attribute in self.STATES.items():
            setattr(self, attribute, stated.get(field))

    def offers(self) -> dict[str, int]:
        """Part 05 §4.1: how many rows of each resource arrived."""
        return {
            resource: (table.num_rows if isinstance(table, pa.Table) else pq.ParquetFile(table).metadata.num_rows)
            for resource, table in self.tables.items()
        }

    def held(self, resource: str) -> bool:
        """Whether this resource comes back as rows rather than as a stream.

        Two reasons to hold one. A resource this source **shares** must be merged with another's,
        and a writer takes one table from one path because two streams cannot be put in the
        declared sort order across the seam between them. And a resource small enough to hold is
        held so the writer *applies* that sort: the streaming path writes through untouched and
        requires its caller to have sorted already, where an adapter's rows arrive in whatever
        order it read them and the sort is the build's (Part 12 §5).

        What is left is a table too large to hold, which is what the streaming path exists for,
        and which reaches a build in the order the adapter streamed it.
        """
        return resource in self.merged or self.offers().get(resource, 0) <= STREAMED_BATCH_ROWS

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Return every resource this build holds, as rows for the writer to sort and merge."""
        return {resource: self.rows(resource) for resource in self.tables if self.held(resource)}

    def staged_arrays(self) -> list[Any]:
        """Every array this source wrote, as a reference to what is on disk (Part 12 §5).

        The bytes are written and their layout is the array's own, so nothing here carries values
        or a layout to apply: staging moves the directory and reads the manifest entry off it. The
        directory's name is the only binding, which the writer resolves against the catalog rows.
        """
        from .bindings import StagedArray

        if self.arrays is None or not self.arrays.is_dir():
            return []
        return [
            StagedArray(values=None, resource_id=path.stem, declaration_id="", array_asset_id="", written=path)
            for path in sorted(self.arrays.glob("*.zarr"))
            if path.is_dir()
        ]

    def external_arrays(self) -> dict[str, Any]:
        """Every referenced array the delivery described, as the build's own reference object."""
        return self._referenced(ExternalArray, "array_asset_id", CORE_ARRAY_ASSETS)

    def external_media(self) -> dict[str, Any]:
        """Every referenced media asset the delivery described."""
        return self._referenced(ExternalMedia, "media_asset_id", CORE_MEDIA_ASSETS)

    def unresolved(self) -> list[str]:
        """Return the referenced entries no delivered catalog row declares, which a build rejects."""
        declared = {
            str(row[identity])
            for identity, resource in (("array_asset_id", CORE_ARRAY_ASSETS), ("media_asset_id", CORE_MEDIA_ASSETS))
            for row in self.rows(resource)
            if row.get(identity)
        }
        return [
            str(entry["resource_id"])
            for entry in self.referenced
            if str(entry["resource_id"]).split(".", 1)[-1] not in declared
        ]

    def _referenced(self, kind: Any, identity: str, resource: str) -> dict[str, Any]:
        """Build one kind of reference from the entries whose asset the delivery's rows declare.

        Which kind an entry is comes from the rows rather than from the entry: an asset the source
        delivered a `core.array_assets` row for is an array and one it delivered a
        `core.media_assets` row for is a media asset, where guessing from the fields an entry
        happens to carry would read a container format as a codec the first time one looked alike.
        """
        from dataclasses import fields

        declared = {str(row[identity]) for row in self.rows(resource) if row.get(identity)}
        taken = {f.name for f in fields(kind)}
        built = {}
        for entry in self.referenced:
            asset = str(entry["resource_id"]).split(".", 1)[-1]
            if asset not in declared:
                continue
            # JSON has no tuple, and these dataclasses declare one for a codec list and for a
            # prefix's members, so what crossed as an array comes back as the type they name.
            values = {
                name: tuple(value) if isinstance(value, list) else value
                for name, value in entry.items()
                if name in taken
            }
            built[str(entry["resource_id"])] = kind(**{**values, identity: asset})
        return built

    def rows(self, resource: str) -> list[dict[str, Any]]:
        """Return one delivered resource as rows, without spending the stream a build will stage.

        What a build harvests it reads twice -- once for the sources that come after, once to
        stage -- so this reads the delivery again rather than consuming it: a held table yields
        fresh batches, and a delivered file is opened again.
        """
        table = self.tables.get(resource)
        return [] if table is None else [row for batch in _batches(table) for row in batch.to_pylist()]

    def batches(self) -> dict[str, Iterator[pa.RecordBatch]]:
        """Return every resource too large to hold, as the stream it arrived as."""
        return {resource: _batches(table) for resource, table in self.tables.items() if not self.held(resource)}

    def stream_rows(self) -> dict[str, int]:
        """Return the rows of every resource too large to hold."""
        return {resource: rows for resource, rows in self.offers().items() if not self.held(resource)}


def _attribute(field: str) -> str:
    """Return the attribute a stated field is read from, which Part 05 §3.6's comparison names."""
    return "stated_" + field.replace(".", "_")


def _batches(table: pa.Table | Path) -> Iterator[pa.RecordBatch]:
    """One delivered resource as batches, read from disk where it is still there."""
    if isinstance(table, pa.Table):
        return iter(table.to_batches())
    return pq.ParquetFile(table).iter_batches(batch_size=STREAMED_BATCH_ROWS)


def fetch(
    kind: str,
    command: Sequence[str],
    supplied: Mapping[str, Any],
    *,
    protocol: str,
    wanted: Sequence[str],
    states: Sequence[str] = (),
    merged: Collection[str] = (),
    report_path: Path | None = None,
    workspace: Path,
    say: Callable[[str], None] = lambda _: None,
) -> Delivered:
    """Run one adapter as a command and read what it delivered (Part 05 §4.4).

    Parameters
    ----------
    kind : str
        The source kind, for what is reported.
    command : sequence of str
        The argument list the recipe carries, run as it is written. A list rather than a string
        because a parse is a quoting convention no recipe declared (Part 05 §3.7).
    supplied : Mapping
        The terms the adapter declared, which cross as one JSON object on the command's standard
        input; the terms of the protocol a build reaches the adapter by are added here (Part 12
        §4).
    protocol : str
        Which of Part 12 §3's protocols to read.
    wanted : sequence of str
        The resources this source owns, which a delivery is complete when it carries.
    states : sequence of str
        The `block.field` names this adapter declares it states, read back from its report.
    merged : collection of str
        Resources this source contributes to alongside others, which come back as rows so the
        writer can merge and sort them; everything it owns outright streams.
    report_path : Path, optional
        Where a report is expected. Removed before the run, so last week's findings are not
        reported as this run's (Part 12 §9).
    workspace : Path
        A directory to put a delivery in, beside the packet; a successful commit removes it.

    Returns
    -------
    Delivered
        The rows, and whatever the report carried.
    """
    if isinstance(command, str):
        raise SourceDefect(
            f"{kind}: command must be an argument list, not {command!r}; write it as a TOML array",
            code=SourceFault.COMMAND_NOT_A_LIST,
            where=kind,
        )
    if not command:
        raise SourceDefect(
            f"{kind}: a delivered source declares no command to run", code=SourceFault.NO_COMMAND, where=kind
        )
    workspace.mkdir(parents=True, exist_ok=True)
    if report_path is not None:
        # A file at a path the recipe names is present after any run that ever wrote one.
        report_path.unlink(missing_ok=True)
    readers: dict[str, Reader] = {
        STREAM: _read_stream,
        FILES: _read_files,
        FLIGHT: _read_flight,
    }
    if protocol not in readers:
        raise SourceDefect(
            f"{kind}: {protocol} is in no group this profile names", code=SourceFault.PROTOCOL_UNKNOWN, where=protocol
        )
    # A Unix socket's address holds about a hundred bytes, fewer than a packet's path may take, so
    # the socket is named in a directory of its own and not in the workspace.
    with tempfile.TemporaryDirectory(prefix="ew-") as socket_home:
        locations = protocol_supplies(protocol, workspace, Path(socket_home), report_path)
        for term in PROTOCOL_TERMS[protocol]:
            # Supplied empty (Part 05 §2): a build reads a delivery by name, so a file an earlier
            # run left would pass for this one's.
            if (leftover := Path(locations[term])).is_dir():
                shutil.rmtree(leftover)
            else:
                leftover.unlink(missing_ok=True)
        supplied = {**supplied, **locations}
        # On standard input, not in the argument list: an argument has a size no profile can
        # raise, and one term carrying a record per unit can exceed it (Part 12 §4).
        crossing = json.dumps(supplied, default=str).encode()
        argv = list(command)
        started = time.perf_counter()
        tables, failures = readers[protocol](kind, argv, crossing, supplied, wanted)
    say(f"  delivered {len(tables)} resource(s) over {protocol} in {time.perf_counter() - started:.1f} s")

    document, malformed = _document(kind, tables.pop(RESOURCES, None))
    failures += malformed
    notes, stated = _from_report(kind, protocol, report_path, tables)
    missing = [resource for resource in wanted if resource not in tables]
    if missing:
        # Reported together rather than one at a time: what a person wants is which resources did
        # not arrive, not which one did not arrive first (Part 05 §4.4).
        failures.append(
            SourceDefect(
                f"{len(missing)} resource(s) never arrived: {', '.join(missing)}",
                code=SourceFault.NEVER_ARRIVED,
                where=", ".join(missing),
            )
        )
    if failures:
        raise DeliveryFailed(
            f"{kind}: " + "; ".join(str(failure) for failure in failures) + _tail(notes), failures=failures, where=kind
        )
    delivered = Delivered(
        kind,
        tables,
        notes=notes,
        stated=stated,
        states=states,
        merged=merged,
        referenced=document,
        arrays=Path(supplied["array_location"]) if supplied.get("array_location") else None,
    )
    if unresolved := delivered.unresolved():
        raise SourceDefect(
            f"{kind}: {len(unresolved)} referenced resource(s) bind no delivered catalog row "
            f"(Part 12 §5): {', '.join(unresolved)}" + _tail(notes),
            code=SourceFault.REFERENCE_UNBOUND,
            where=", ".join(unresolved),
        )
    return delivered


def _document(kind: str, delivered: Any) -> tuple[list[dict[str, Any]], list[SourceDefect]]:
    """Read the resource document a delivery carried, refusing one that does not satisfy its shape.

    Refused rather than reported, unlike a report: this is the manifest's own content arriving from
    elsewhere, and a malformed entry merged into a manifest is a packet that misdescribes its own
    resources (Part 12 §5).
    """
    if delivered is None:
        return [], []
    text = delivered.column("document")[0].as_py() if isinstance(delivered, pa.Table) else None
    if text is None:
        table = pq.read_table(delivered) if isinstance(delivered, Path) else None
        text = table.column("document")[0].as_py() if table is not None else None
    try:
        document = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        return [], [SourceDefect(f"the resource document is not JSON ({exc})", code=SourceFault.DOCUMENT_NOT_JSON)]
    # Before the shape, which also refuses `external: false` where an entry's uri is absolute or it
    # names a source, but without naming the entry.
    if problems := _entry_refusals(document):
        return [], problems
    if problem := _refuses(document):
        return [], [SourceDefect(f"the resource document {problem}", code=SourceFault.DOCUMENT_SHAPE)]
    return [_as_recorded(entry) for entry in document.get("resources", ())], []


def _entry_refusals(document: Any) -> list[SourceDefect]:
    """Each entry declaring itself packet-owned, or whose uri no reader could resolve, by its `resource_id`.

    A resource document describes only a referenced resource, and a packet-owned opaque resource
    crosses as a payload (Part 12 §5). A uri that is not absolute is a relative reference in any
    spelling RFC 3986 admits for its segments (Part 03 §4).
    """
    entries = document.get("resources") if isinstance(document, Mapping) else None
    found = []
    for entry in entries if isinstance(entries, list) else ():
        if not isinstance(entry, Mapping):
            continue
        resource_id = entry.get("resource_id")
        if entry.get("external") is False:
            found.append(
                SourceDefect(
                    f"{resource_id}: declares external: false; a resource document describes only a referenced "
                    "resource, and a packet-owned opaque resource crosses as a payload (Part 12 §5)",
                    code=SourceFault.ENTRY_NOT_EXTERNAL,
                    where=str(resource_id),
                )
            )
        uri = entry.get("uri")
        if isinstance(uri, str) and not is_absolute(uri):
            try:
                canonical(uri)
            except ValueError as exc:
                found.append(
                    SourceDefect(
                        f"{resource_id}: uri is neither absolute nor a relative reference: {exc} (Part 03 §4)",
                        code=SourceFault.ENTRY_URI,
                        where=str(resource_id),
                    )
                )
    return found


def _as_recorded(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Record an entry as external, with a relative uri in Part 03 §4's one form."""
    uri = str(entry["uri"])
    return {**entry, "external": True, "uri": uri if is_absolute(uri) else canonical(uri)}


def _refuses(document: Mapping[str, Any]) -> str | None:
    """Return why a resource document does not satisfy its published shape, or None."""
    from importlib import resources as bundled

    import jsonschema
    from escapewheel_validator.manifest import format_checker

    schema = json.loads(bundled.files(__package__).joinpath("schemas/resources.schema.json").read_text())
    validator = jsonschema.Draft202012Validator(schema, format_checker=format_checker())
    found = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if not found:
        return None
    where = "/".join(str(p) for p in found[0].path) or "document"
    return f"does not satisfy resources.schema.json at {where}: {found[0].message}"


def _tail(notes: Sequence[str]) -> str:
    """Return what the report said, for a failure: the run that went wrong is the one with something to say."""
    return "\n  " + "\n  ".join(notes) if notes else ""


def protocol_supplies(protocol: str, workspace: Path, socket_home: Path, report_path: Path | None) -> dict[str, str]:
    """Return the terms this protocol requires, which an adapter may not declare and a build supplies."""
    supplies = {}
    for term in PROTOCOL_TERMS[protocol]:
        supplies[term] = str(workspace / "delivery" if term == "delivery_root" else socket_home / "adapter.sock")
    if report_path is not None and protocol in REPORT_AS_FILE:
        supplies["report_path"] = str(report_path)
    return supplies


def _from_report(
    kind: str, protocol: str, report_path: Path | None, tables: Mapping[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    """Read a report where one is expected, as notes and the values a source stated.

    A build must not require one and must not fail on its contents (Part 12 §9), so an absent
    report and an unparseable one are both notes. What it carries that nothing else can is
    `stated`; rows per table and which tables exist are established without asking.
    """
    del tables  # what a report says about them is what a build already knows
    if report_path is None or protocol not in REPORT_AS_FILE:
        return [], {}
    if not report_path.is_file():
        return [], {}
    try:
        document = json.loads(report_path.read_text())
    except json.JSONDecodeError as exc:
        return [Note(f"{kind}: the report at {report_path} is not JSON ({exc})", NoteCode.REPORT_NOT_JSON)], {}
    notes: list[str] = []
    for problem in document.get("problems", ()):
        where = f" [{problem['resource']}]" if problem.get("resource") else ""
        notes.append(
            Note(
                f"{kind} reports {problem.get('level', 'info')}{where}: {problem.get('message', '')}", NoteCode.REPORTED
            )
        )
    if read := document.get("read"):
        notes.append(
            Note(f"{kind} read {len(read)} input(s): {', '.join(str(r) for r in read[:4])}", NoteCode.INPUTS_READ)
        )
    return notes, dict(document.get("stated", {}))


def _supply(child: subprocess.Popen[bytes], crossing: bytes) -> threading.Thread:
    """Write what a build supplies to the child and close the stream, on a thread of its own.

    Without waiting for the child to exit (Part 05 §3.7): a pipe holds tens of kilobytes and a
    supplied object may be far larger, so writing it whole before reading rows would leave each
    process waiting on the other.
    """

    def run() -> None:
        assert child.stdin is not None
        try:
            child.stdin.write(crossing)
        except BrokenPipeError:
            # An adapter that died before reading is a failure the exit code reports; writing into
            # its closed pipe must not raise here and hide it.
            pass
        finally:
            child.stdin.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def _drain(handle: Any, into: list[str]) -> threading.Thread:
    """Read a pipe to its end on a thread of its own.

    A pipe holds tens of kilobytes, so reading one to completion after the other deadlocks on any
    adapter whose diagnosis outruns that buffer (Part 05 §3.7).
    """

    def run() -> None:
        into.append(handle.read().decode(errors="replace"))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def _said(collected: Sequence[str]) -> str:
    """Return an adapter's standard error, trimmed to what a build reports (Part 05 §4.4)."""
    text = "".join(collected).strip()
    return f" said: {text[-2000:]}" if text else ""


def _read_files(
    kind: str, argv: Sequence[str], crossing: bytes, supplied: Mapping[str, Any], wanted: Sequence[str]
) -> tuple[dict[str, Any], list[SourceDefect]]:
    """`files-v0.1`: the adapter writes Parquet, and discovery reads the footers."""
    root = Path(supplied["delivery_root"])
    root.mkdir(parents=True, exist_ok=True)
    # `communicate` writes the input and drains both output streams together, which is what keeps
    # a build from waiting on an adapter that is waiting on it (Part 05 §3.7).
    done = subprocess.run(argv, input=crossing, capture_output=True, check=False)
    failures = []
    if done.returncode:
        # A non-zero exit is a failure whatever arrived: an adapter saying it failed is not
        # overruled by its own output (Part 05 §4.4).
        failures.append(
            SourceDefect(
                f"the command exited {done.returncode}{_said([done.stderr.decode(errors='replace')])}",
                code=SourceFault.COMMAND_EXITED,
            )
        )
    tables: dict[str, Any] = {}
    if (document := root / f"{RESOURCES}.json").is_file():
        # A file is a file: under this protocol the document went down as JSON, and it reaches the
        # same reader the other protocols' single-row table does.
        tables[RESOURCES] = pa.table({"document": [document.read_text()]})
    for path in sorted(root.glob("*.parquet")):
        try:
            # The footer, which is what says the file is a delivery rather than a partial write.
            _ = pq.ParquetFile(path).metadata.num_rows
        except pa.ArrowInvalid as exc:
            failures.append(
                SourceDefect(
                    f"{path.stem}: the delivered file cannot be read ({exc})",
                    code=SourceFault.DELIVERED_FILE_UNREADABLE,
                    where=path.stem,
                )
            )
            continue
        tables[path.stem] = path
    del kind, wanted
    return tables, failures


def _read_stream(
    kind: str, argv: Sequence[str], crossing: bytes, supplied: Mapping[str, Any], wanted: Sequence[str]
) -> tuple[dict[str, Any], list[SourceDefect]]:
    """`stream-v0.1`: concatenated IPC on standard output, ended by the sentinel."""
    del supplied, wanted
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    said: list[str] = []
    _supply(child, crossing)
    draining = _drain(child.stderr, said)
    rows = cast("IOBase", child.stdout)  # a pipe, opened by `Popen` and never None with stdout=PIPE
    tables: dict[str, Any] = {}
    ended, last = False, None
    try:
        while True:
            try:
                reader = pa.ipc.open_stream(rows)
            except (pa.ArrowInvalid, OSError):
                break
            name = reader.schema.metadata[b"resource_id"].decode()
            if name == SENTINEL:
                ended = True
                # The adapter is still writing the sentinel's batch and end-of-stream marker, and
                # closing the pipe first fails a conforming delivery with a broken pipe.
                reader.read_all()
                rows.read()
                break
            tables[name] = reader.read_all()
            last = name
    finally:
        rows.close()
        child.wait()
        draining.join(timeout=5)
    failures = []
    if child.returncode:
        failures.append(
            SourceDefect(f"the command exited {child.returncode}{_said(said)}", code=SourceFault.COMMAND_EXITED)
        )
    if not ended:
        # Naming the last resource read rather than the first that never arrived: a reader treats
        # end of file as end of stream, so a cut delivery parses clean (Part 12 §6).
        where = f" after {last}" if last else " before anything arrived"
        failures.append(
            SourceDefect(
                f"the delivery did not end with the sentinel; the adapter died{where}{_said(said)}",
                code=SourceFault.NO_SENTINEL,
            )
        )
    del kind
    return tables, failures


def _read_flight(
    kind: str, argv: Sequence[str], crossing: bytes, supplied: Mapping[str, Any], wanted: Sequence[str]
) -> tuple[dict[str, Any], list[SourceDefect]]:
    """`flight-v0.1`: retry the socket until it answers, then one DoGet per descriptor."""
    import pyarrow.flight as fl

    del wanted
    socket = str(supplied["socket"])
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    said: list[str] = []
    _supply(child, crossing)
    draining = _drain(child.stderr, said)
    tables: dict[str, Any] = {}
    failures: list[SourceDefect] = []
    client = None
    try:
        client = _rendezvous(socket, child)
    except SourceDefect as exc:
        failures.append(SourceDefect(str(exc) + _said(said), code=exc.code))
    if client is not None:
        try:
            for info in client.list_flights():
                name = info.descriptor.path[0].decode()
                tables[name] = client.do_get(fl.Ticket(name.encode())).read_all()
        except fl.FlightError as exc:
            # A failing adapter writes nothing to standard error here, because the diagnosis
            # travels on the connection it was asked over (Part 05 §4.4).
            failures.append(
                SourceDefect(f"{exc}; detail: {getattr(exc, 'extra_info', b'')!r}", code=SourceFault.FLIGHT_ERROR)
            )
        client.close()
    # A build that started a process owns it, and an adapter may not rely on running code after
    # its last response (Part 12 §8).
    child.terminate()
    child.wait()
    draining.join(timeout=5)
    del kind
    return tables, failures


def _rendezvous(socket: str, child: subprocess.Popen[bytes]) -> Any:
    """Wait for a `flight-v0.1` adapter by connecting, not by reading a readiness line.

    A line would work and would be a second thing to specify, and it cannot cover the case that
    matters: an adapter that dies before binding says nothing either way (Part 12 §8).
    """
    import pyarrow.flight as fl

    while True:
        try:
            client = fl.connect(fl.Location.for_grpc_unix(socket))
            client.wait_for_available(timeout=1)
            return client
        except (fl.FlightUnavailableError, fl.FlightTimedOutError):
            if child.poll() is not None:
                raise SourceDefect(
                    f"the adapter exited {child.returncode} before serving", code=SourceFault.EXITED_BEFORE_SERVING
                ) from None
            time.sleep(RETRY)


__all__ = ["RETRY", "Delivered", "Reader", "fetch", "protocol_supplies"]

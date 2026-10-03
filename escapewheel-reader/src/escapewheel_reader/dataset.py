"""Many packets presented as one relation (Part 05 §13.1).

- :func:`open_dataset` -- open several packets as a :class:`Dataset`.
- :class:`Dataset` -- each session-scoped table as the union of every packet's rows, by
  :meth:`~Dataset.table` or as DuckDB views from :meth:`~Dataset.duckdb`.
- :class:`Session` -- one packet's session, and the ``session_key`` the dataset gave it.
- :func:`session_scoped` -- the tables a registry scopes to a session.

An identifier is assigned within its packet, so rows from two packets are told apart by
``session_key``, never by their identifiers.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
import pyarrow.compute as pc

from . import duck
from .errors import MultiSessionUnresolved, ResourceNotFoundError
from .location import Location
from .optional import held
from .packet import Packet, open_packet
from .protocols import PacketLike
from .registries import declared_tables
from .resource_ids import CORE_SESSIONS
from .resources import TableResource
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover - typing only
    from duckdb import DuckDBPyConnection

#: The columns a dataset projects onto every session-scoped table. `session_key` is the
#: session discriminator; `session_name` is the label permitted beside one, and promises nothing
#: about what two packets' matching labels denote.
PROJECTED = ("session_key", "session_name")

#: What :func:`duck.connect` says of a dataset where DuckDB is absent.
READS_WITHOUT_SQL = "A dataset is readable without it through table(), which goes through PyArrow."


def session_scoped(registry: Mapping[str, Any]) -> frozenset[str]:
    """Return every table reaching `core.sessions` through its declared references (Part 02 §7.1).

    A property of the registry, decided with no packet in hand. The stricter of the two
    available tests: every table carrying a `session_id` reaches `core.sessions`, while eight
    reach it without carrying the column, so the graph subsumes the column and not the reverse.

    Parameters
    ----------
    registry : Mapping
        A parsed registry document.

    Returns
    -------
    frozenset of str
        Dotted resource IDs, `core.sessions` included.
    """
    tables = declared_tables(registry)
    edges = {n: {r["resource"] for r in t.get("references", [])} for n, t in tables.items()}

    def reaches(name: str, seen: set[str]) -> bool:
        if name == CORE_SESSIONS:
            return True
        if name in seen:
            # A table's reference to itself is not a route to anywhere.
            return False
        seen.add(name)
        return any(reaches(m, seen) for m in edges.get(name, ()))

    return frozenset(n for n in tables if reaches(n, set()))


@dataclass(frozen=True)
class Session:
    """One session of one packet, and the number a dataset gave it.

    Attributes
    ----------
    session_key : int
        The discriminator. Numbered by the dataset as it opened the packets, so it is stable
        for one dataset and means nothing outside it, as an assigned identifier means nothing
        outside its packet.
    packet_id : str
        The packet this session was read from.
    session_id : int
        What that packet calls it, which another packet may reuse for a different session.
    session_name : str or None
        The label `core.sessions` carries, for reading and grouping.
    """

    session_key: int
    packet_id: str
    session_id: int
    session_name: str | None


class Dataset:
    """Several packets, presented as one relation per resource.

    The discriminator is **the packet a row came from together with the row's `session_id`**.
    Both are known for certain -- the reader opened the file, and the identifier is unique
    within it -- so their pair is unique by construction and nothing has to be assumed
    about the world. A `*_name` is never used for it: measured across two packets sharing no
    session, no animal and no probe, 6 of 13 name columns hold a value appearing in both.

    Identity is **carried, not joined on**. Within one packet an assigned identifier is already
    unique, so a query over one session joins on it alone; a query spanning sessions joins on
    `(session_key, unit_id)`.
    """

    def __init__(self, packets: Sequence[Packet]) -> None:
        """Open a dataset over packets already opened, numbering every session they hold.

        Parameters
        ----------
        packets : sequence of Packet
            The packets to present. One is allowed and behaves the same as many.

        Raises
        ------
        ValueError
            If no packets were given.
        """
        if not packets:
            raise ValueError("a dataset needs at least one packet")
        self._packets = tuple(packets)
        self._sessions = tuple(self._number(self._packets))
        self._scoped = self._scope(self._packets)
        self._by_packet: dict[str, dict[int, Session]] = {}
        for session in self._sessions:
            self._by_packet.setdefault(session.packet_id, {})[session.session_id] = session

    @staticmethod
    def _number(packets: Sequence[Packet]) -> list[Session]:
        """Read each packet's `core.sessions` and assign the discriminators.

        A handful of rows per packet: the reader knows every session's key and label before the
        first query runs.
        """
        numbered, key = [], 0
        for packet in packets:
            rows = packet.table(CORE_SESSIONS).to_pylist()
            for row in sorted(rows, key=lambda r: r["session_id"]):
                numbered.append(
                    Session(
                        session_key=key,
                        packet_id=packet.manifest.packet_id,
                        session_id=row["session_id"],
                        session_name=row.get("session_name"),
                    )
                )
                key += 1
        return numbered

    @staticmethod
    def _scope(packets: Sequence[Packet]) -> frozenset[str]:
        """Return the union of what each packet's own registry says is session-scoped.

        Each packet binds the registry it was written against, so two packets built against
        different registry versions can disagree. The union is what keeps a table scoped once
        any packet says it is, which is the safe direction: an extra discriminator is harmless,
        while omitting one where it is needed can correlate unrelated rows.
        """
        scoped: set[str] = set()
        for packet in packets:
            scoped |= session_scoped(packet.registry)
        return frozenset(scoped)

    @property
    def packets(self) -> tuple[Packet, ...]:
        """The packets this dataset presents, in the order given."""
        return self._packets

    @property
    def sessions(self) -> tuple[Session, ...]:
        """Every session across every packet, numbered."""
        return self._sessions

    @property
    def scoped(self) -> frozenset[str]:
        """Which resources carry a session discriminator."""
        return self._scoped

    def __repr__(self) -> str:
        """Return a short representation naming the packet and session counts."""
        return f"<Dataset of {len(self._packets)} packet(s), {len(self._sessions)} session(s)>"

    # -- SQL ------------------------------------------------------------------------

    def duckdb(
        self,
        *,
        connection: DuckDBPyConnection | None = None,
        tables: Collection[str] | Literal["all"] | None = None,
        for_query: str | None = None,
    ) -> DuckDBPyConnection:
        """Register each resource as one view over every packet that holds it.

        A session-scoped view carries `session_key` and `session_name`, projected as scalar
        expressions over `session_id` rather than joined from `core.sessions`. A query planner
        can prune the projection when a query does not select it.

        Nothing is registered unless asked for, for the reason `Packet.duckdb` says: binding a
        Parquet view reads its footer, which is a round trip per table in an object store.

        Parameters
        ----------
        connection : duckdb.DuckDBPyConnection, optional
            An existing connection to register into; a new in-memory one otherwise.
        tables : collection of str or "all", optional
            Which resources to register, by dotted ID. ``"all"`` registers every resource any
            packet declares. The default registers none.
        for_query : str, optional
            SQL to read resource names out of, registering those.

        Returns
        -------
        duckdb.DuckDBPyConnection
            The connection, with the requested resources registered.

        Raises
        ------
        MultiSessionUnresolved
            If a packet holds several sessions and a scoped resource does not carry
            `session_id`.
        """
        con = connection if connection is not None else duck.connect(READS_WITHOUT_SQL)
        wanted = set(self._declared()) if tables == "all" else set(tables or ())
        if for_query is not None:
            wanted |= {r for r in self._declared() if sql_name(r) in for_query}
        for resource_id in sorted(wanted):
            statement = self._view(resource_id)
            if statement is not None:
                con.sql(statement)
        return con

    def _declared(self) -> frozenset[str]:
        """Every resource ID any packet declares as a table."""
        return frozenset(
            r.resource_id
            for packet in self._packets
            for r in packet.resources(kind="table") + packet.resources(kind="materialized_table")
        )

    def _view(self, resource_id: str) -> str | None:
        """Return the `CREATE VIEW` for one resource, or None where no packet holds it."""
        arms = [arm for packet in self._packets if (arm := self._arm(packet, resource_id))]
        if not arms:
            return None
        # BY NAME rather than positional: two packets built against different revisions may
        # order or extend their columns differently, and a positional union would silently
        # pair one column with another.
        body = "\nUNION ALL BY NAME\n".join(arms)
        return f"CREATE OR REPLACE VIEW {sql_name(resource_id)} AS\n{body}"

    def _arm(self, packet: Packet, resource_id: str) -> str | None:
        """One packet's contribution to a resource's view, with the identity projected."""
        declared = {r.resource_id: r for r in packet.resources()}
        resource = declared.get(resource_id)
        if resource is None or resource.kind not in {"table", "materialized_table"}:
            return None
        handle = TableResource(resource, packet.location)
        base = str(handle.path) if handle.is_local else handle.location.uri
        source = f"SELECT * FROM '{base}'"
        if resource_id not in self._scoped:
            # A table that is not session-scoped carries no discriminator.
            return source
        return f"SELECT *, {self._identity(packet, resource_id)} FROM '{base}'"

    def _identity(self, packet: Packet, resource_id: str) -> str:
        """Return the projected `session_key` and `session_name` for one packet's rows.

        A scalar expression over a column already being scanned, so a query not selecting it
        can have the expression pruned and read nothing extra.
        """
        held = self._by_packet[packet.manifest.packet_id]
        if "session_id" in _column_names(packet, resource_id):
            keys = " ".join(f"WHEN {s.session_id} THEN {s.session_key}" for s in held.values())
            labels = " ".join(
                f"WHEN {s.session_id} THEN {_literal(s.session_name)}"
                if s.session_name is not None
                else f"WHEN {s.session_id} THEN NULL"
                for s in held.values()
            )
            return f"CASE session_id {keys} END AS session_key, CASE session_id {labels} END AS session_name"
        if len(held) != 1:
            raise MultiSessionUnresolved(
                f"{resource_id} is session-scoped, carries no session_id, and "
                f"{packet.manifest.packet_id} holds {len(held)} sessions; its rows need "
                "a discriminator, and one may not be derived from a session name"
            )
        only = next(iter(held.values()))
        label = _literal(only.session_name)
        return f"{only.session_key} AS session_key, {label} AS session_name"

    # -- Arrow ----------------------------------------------------------------------

    def table(self, resource_id: str, *, columns: list[str] | None = None) -> pa.Table:
        """Read one resource across every packet that holds it, as one Arrow table.

        The identity is appended the same way the SQL view projects it, so the two agree. Goes
        through PyArrow, so a dataset stays readable with the ``sql`` extra absent.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        columns : list of str, optional
            Read only these columns. `session_key` and `session_name` are always added to a
            session-scoped resource, and asking for them alone still reads `session_id`.

        Returns
        -------
        pyarrow.Table
            Every packet's rows, in the order the packets were opened.

        Raises
        ------
        MultiSessionUnresolved
            If a packet holds several sessions and the resource does not carry `session_id`.
        ResourceNotFoundError
            If no packet of the dataset holds the resource.
        """
        parts = []
        for packet in self._packets:
            if resource_id not in held(packet):
                continue
            wanted = columns
            if columns is not None and resource_id in self._scoped:
                wanted = [c for c in columns if c not in PROJECTED]
                if "session_id" not in wanted and "session_id" in _column_names(packet, resource_id):
                    wanted = [*wanted, "session_id"]
            part = packet.table(resource_id, columns=wanted)
            if resource_id in self._scoped:
                part = self._stamp(packet, resource_id, part)
            parts.append(part)
        if not parts:
            raise ResourceNotFoundError(f"no packet in this dataset declares {resource_id}", resource_id=resource_id)
        return pa.concat_tables(parts, promote_options="permissive")

    def _stamp(self, packet: Packet, resource_id: str, table: pa.Table) -> pa.Table:
        """Append `session_key` and `session_name` to one packet's rows.

        Entirely in Arrow: a lookup over the packet's handful of sessions, then a take. This can
        run over the packet's largest fact tables, so it keeps the operation columnar.
        """
        held = list(self._by_packet[packet.manifest.packet_id].values())
        keys = pa.array([s.session_key for s in held], pa.int32())
        labels = pa.array([s.session_name for s in held], pa.string())
        if "session_id" in table.column_names:
            at = pc.index_in(table.column("session_id"), value_set=pa.array([s.session_id for s in held], pa.int32()))
            key_column, label_column = pc.take(keys, at), pc.take(labels, at)
        elif len(held) == 1:
            key_column = pa.repeat(keys[0], table.num_rows)
            label_column = pa.repeat(labels[0], table.num_rows)
        else:
            raise MultiSessionUnresolved(
                f"{resource_id} is session-scoped, carries no session_id, and "
                f"{packet.manifest.packet_id} holds {len(held)} sessions"
            )
        return table.append_column("session_key", key_column).append_column("session_name", label_column)


def _literal(value: str | None) -> str:
    """Quote a session name as a SQL string literal, doubling any embedded quote."""
    return "NULL" if value is None else "'" + value.replace("'", "''") + "'"


def _column_names(packet: PacketLike, resource_id: str) -> list[str]:
    """Return the columns a resource holds, from the packet's registry or its Parquet schema."""
    registry = packet.registry
    declaration = registry.get("resources", {}).get(resource_id, {})
    declared = declaration.get("table") if declaration.get("kind") == "table" else None
    if declared is not None:
        return [c["name"] for c in declared["columns"]]
    return list(packet.table_resource(resource_id).schema().names)


def open_dataset(
    paths: Iterable[str | Path | Location | Packet],
    **options: Any,
) -> Dataset:
    """Open several packets and present them as one relation.

    Parameters
    ----------
    paths : iterable
        Packet roots, or already-opened `Packet` objects. A root is a local directory or a
        store prefix such as ``s3://bucket/prefix``.
    **options
        Passed to :func:`open_packet` for each root that is not already open.

    Returns
    -------
    Dataset
        The opened dataset.

    Examples
    --------
    >>> data = open_dataset(["/data/ecephys_776259", "/data/ecephys_786867"])  # doctest: +SKIP
    >>> con = data.duckdb(tables=["core.units", "core.electrode_coordinates"])  # doctest: +SKIP
    """
    opened = [p if isinstance(p, Packet) else open_packet(p, **options) for p in paths]
    return Dataset(opened)


__all__ = ["Dataset", "Session", "open_dataset"]

"""Many packets presented as one relation (Part 05 §13.1).

- :func:`open_packets` -- open several packets as a :class:`PacketSet`.
- :class:`PacketSet` -- each session-scoped table as the union of every packet's rows: lazily by
  :meth:`~PacketSet.scan` and :meth:`~PacketSet.scanner`, eagerly by :meth:`~PacketSet.table`,
  or as DuckDB views from :meth:`~PacketSet.duckdb`.
- :class:`Session` -- one packet's session, and the ``session_key`` the packet set gave it.
- :func:`session_scoped` -- the tables a registry scopes to a session.

An identifier is assigned within its packet, so rows of a session-scoped table from two packets are
told apart by ``packet_key`` and ``session_id`` together, or by ``session_key``, the one number each
such pair is given; never by their identifiers.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pads

from . import duck
from .clocks import shared_clock
from .errors import MultiSessionUnresolved, ResourceNotFoundError
from .location import Location
from .optional import held
from .packet import Packet, open_packet
from .predicates import Predicate, both, expression
from .protocols import PacketLike
from .registries import declared_tables
from .resource_ids import CORE_SESSIONS
from .resources import TableResource, read_pool
from .sql import sql_name

if TYPE_CHECKING:  # pragma: no cover - typing only
    from duckdb import DuckDBPyConnection

#: The columns a packet set projects onto every session-scoped table. `packet_key` names the packet
#: a row came from, and with the stored `session_id` it identifies the session; `session_key`
#: numbers that pair; `session_name` is the label permitted beside them, and promises nothing about
#: what two packets' matching labels denote.
PROJECTED = ("packet_key", "session_key", "session_name")

#: What :func:`duck.connect` says of a packet set where DuckDB is absent.
READS_WITHOUT_SQL = "A packet set is readable without it through table(), which goes through PyArrow."


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
    """One session of one packet, and the number a packet set gave it.

    Attributes
    ----------
    session_key : int
        The discriminator. Numbered by the packet set as it opened the packets, so it is stable
        for one packet set and means nothing outside it, as an assigned identifier means nothing
        outside its packet.
    packet_key : int
        The position of the packet this session was read from, among the packets the set opened.
    packet_id : str
        The packet this session was read from.
    session_id : int
        What that packet calls it, which another packet may reuse for a different session.
    session_name : str or None
        The label `core.sessions` carries, for reading and grouping.
    """

    session_key: int
    packet_key: int
    packet_id: str
    session_id: int
    session_name: str | None


class PacketSet:
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
        """Open a packet set over packets already opened, numbering every session they hold.

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
            raise ValueError("a packet set needs at least one packet")
        self._packets = tuple(packets)
        self._sessions = tuple(self._number(self._packets))
        self._scoped = self._scope(self._packets)
        self._by_packet: dict[str, dict[int, Session]] = {}
        for session in self._sessions:
            self._by_packet.setdefault(session.packet_id, {})[session.session_id] = session
        # Kept so a labelled file's footer is read once however many scans include it.
        self._labelled: dict[tuple[int, str], pads.Fragment] = {}

    @staticmethod
    def _number(packets: Sequence[Packet]) -> list[Session]:
        """Read each packet's `core.sessions` and assign the discriminators.

        A handful of rows per packet: the reader knows every session's key and label before the
        first query runs.
        """
        numbered, key = [], 0
        for packet_key, packet in enumerate(packets):
            rows = packet.table(CORE_SESSIONS).to_pylist()
            for row in sorted(rows, key=lambda r: r["session_id"]):
                numbered.append(
                    Session(
                        session_key=key,
                        packet_key=packet_key,
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
        """The packets this packet set presents, in the order given."""
        return self._packets

    @property
    def sessions(self) -> tuple[Session, ...]:
        """Every session across every packet, numbered."""
        return self._sessions

    def session_table(self) -> pa.Table:
        """Return every session as a table, for joining `session_key` onto a :meth:`scan`.

        Returns
        -------
        pyarrow.Table
            `packet_key`, `session_id`, `session_key` and `session_name`, one row per session.
        """
        return pa.table(
            {
                "packet_key": pa.array([s.packet_key for s in self._sessions], pa.int32()),
                "session_id": pa.array([s.session_id for s in self._sessions], pa.int32()),
                "session_key": pa.array([s.session_key for s in self._sessions], pa.int32()),
                "session_name": pa.array([s.session_name for s in self._sessions], pa.string()),
            }
        )

    @property
    def scoped(self) -> frozenset[str]:
        """Which resources carry a session discriminator."""
        return self._scoped

    def __repr__(self) -> str:
        """Return a short representation naming the packet and session counts."""
        return f"<PacketSet of {len(self._packets)} packet(s), {len(self._sessions)} session(s)>"

    # -- SQL ------------------------------------------------------------------------

    def duckdb(
        self,
        *,
        connection: DuckDBPyConnection | None = None,
        tables: Collection[str] | Literal["all"] | None = None,
        for_query: str | None = None,
    ) -> DuckDBPyConnection:
        """Register each resource as one view over every packet that holds it.

        A session-scoped view carries `packet_key`, `session_key` and `session_name`, projected as
        scalar expressions over `session_id` rather than joined from `core.sessions`. A query planner
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
        """Return the projected `packet_key`, `session_key` and `session_name` for one packet's rows.

        A scalar expression over a column already being scanned, so a query not selecting it
        can have the expression pruned and read nothing extra.
        """
        held = self._by_packet[packet.manifest.packet_id]
        packet_key = f"{self._packet_key(packet)} AS packet_key"
        if "session_id" in _column_names(packet, resource_id):
            keys = " ".join(f"WHEN {s.session_id} THEN {s.session_key}" for s in held.values())
            labels = " ".join(
                f"WHEN {s.session_id} THEN {_literal(s.session_name)}"
                if s.session_name is not None
                else f"WHEN {s.session_id} THEN NULL"
                for s in held.values()
            )
            return (
                f"{packet_key}, CASE session_id {keys} END AS session_key, CASE session_id {labels} END AS session_name"
            )
        if len(held) != 1:
            raise MultiSessionUnresolved(
                f"{resource_id} is session-scoped, carries no session_id, and "
                f"{packet.manifest.packet_id} holds {len(held)} sessions; its rows need "
                "a discriminator, and one may not be derived from a session name"
            )
        only = next(iter(held.values()))
        label = _literal(only.session_name)
        return f"{packet_key}, {only.session_key} AS session_key, {label} AS session_name"

    # -- Arrow ----------------------------------------------------------------------

    def scan(self, resource_id: str) -> pads.Dataset:
        """Open one resource across every packet holding it as one lazy dataset.

        Each packet's files are fragments whose partition field is `packet_key`, so a filter on it
        skips other packets' files unopened. With the stored `session_id`, `packet_key` identifies
        a session-scoped row's session; :meth:`session_table` gives each pair's `session_key` and
        `session_name`, which :meth:`scanner` and :meth:`table` add per row.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        pyarrow.dataset.Dataset
            A union of each packet's files, with `packet_key` added to a session-scoped resource
            and nulls for a column only some packets hold.

        Raises
        ------
        MultiSessionUnresolved
            If the resource is session-scoped and lacks `session_id` in a packet holding several
            sessions, whose rows nothing then tells apart.
        ResourceNotFoundError
            If no packet of the packet set holds the resource.
        """
        scoped = resource_id in self._scoped
        holding = self._holding(resource_id)
        if scoped:
            for packet in holding:
                self._distinguishable(packet, resource_id)
        # A labelled fragment is what a scoped scan reads, so its footer also gives the schema.
        handles = [packet.table_resource(resource_id) for packet in holding]
        fragments = [
            [self._labelled_fragment(packet, handle, resource_id)]
            if scoped
            else list(cast(pads.FileSystemDataset, handle.dataset()).get_fragments())
            for packet, handle in zip(holding, handles, strict=True)
        ]
        schemas = [
            each[0].physical_schema if scoped else handle.schema()
            for each, handle in zip(fragments, handles, strict=True)
        ]
        schema = pa.unify_schemas(schemas, promote_options="permissive")
        if scoped:
            schema = schema.append(pa.field("packet_key", pa.int32()))
        children = [pads.FileSystemDataset(each, schema, each[0].format, each[0].filesystem) for each in fragments]
        return pads.dataset(children)  # type: ignore[arg-type]  # the stubs omit a list of datasets

    def _labelled_fragment(self, packet: Packet, handle: TableResource, resource_id: str) -> pads.Fragment:
        """Return the packet's file for `resource_id` carrying its `packet_key`, made once per packet set."""
        packet_key = self._packet_key(packet)
        if (packet_key, resource_id) not in self._labelled:
            label = pc.field("packet_key") == pa.scalar(packet_key, pa.int32())
            self._labelled[packet_key, resource_id] = handle.labelled(label)
        return self._labelled[packet_key, resource_id]

    def scanner(
        self,
        resource_id: str,
        *,
        columns: list[str] | None = None,
        filter: pads.Expression | None = None,
        **where: Predicate,
    ) -> pads.Scanner:
        """Scan one resource across every packet holding it, with constraints pushed down.

        Takes :meth:`Packet.scanner`'s arguments. A session-scoped resource gains `packet_key`,
        `session_key` and `session_name`, the last two computed per row from `packet_key` and
        `session_id`. A keyword constraint on any of the three becomes one on `packet_key` and
        `session_id` and prunes other packets' files; `filter` is tested before they are computed,
        so it may name `packet_key` but not `session_key` or `session_name`.

        Returns
        -------
        pyarrow.dataset.Scanner
            A scanner over every packet's matching rows.

        Raises
        ------
        MultiSessionUnresolved
            As :meth:`scan` raises it.
        """
        dataset = self.scan(resource_id)
        stored = [name for name in dataset.schema.names if name not in PROJECTED]
        wanted = stored if columns is None else [c for c in columns if c not in PROJECTED]
        projection: dict[str, pads.Expression] = {name: pc.field(name) for name in wanted}
        if resource_id in self._scoped:
            key, label = self._per_row(resource_id)
            projection |= {"packet_key": pc.field("packet_key"), "session_key": key, "session_name": label}
            if columns is not None:
                projection = {name: projection[name] for name in [*wanted, *(c for c in columns if c in PROJECTED)]}
        rest, selected = self._identity_constraints(resource_id, where)
        return dataset.scanner(
            columns=projection,  # type: ignore[arg-type]  # the stubs omit a projection mapping
            filter=both(both(expression(rest), selected), filter),
            memory_pool=read_pool(),
        )

    def table(
        self,
        resource_id: str,
        *,
        columns: list[str] | None = None,
        on_clock: bool | int = False,
        seconds: bool = False,
        **where: Predicate,
    ) -> pa.Table:
        """Read one resource across every packet that holds it, as one Arrow table.

        Takes :meth:`Packet.table`'s arguments, with `packet_key`, `session_key` and
        `session_name` as constraints like any column; `on_clock` maps onto each packet's
        reference clock. Without a clock, this is :meth:`scanner` read whole, so every packet is
        one scan. The identity matches the SQL view's projection. Goes through PyArrow, so a
        packet set stays readable with the ``sql`` extra absent.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.
        columns : list of str, optional
            Read only these columns, which a session-scoped resource's `packet_key`,
            `session_key` and `session_name` may be among. All of them by default; the session
            name costs a string per row, so name the columns where the rows are many.
        on_clock, seconds, **where
            As :meth:`Packet.table` takes them, except that a clock ID must be every packet's
            reference clock, since it names a different clock in each.

        Returns
        -------
        pyarrow.Table
            Every packet's matching rows, in the order the packets were opened.

        Raises
        ------
        MultiSessionUnresolved
            If a packet holds several sessions and the resource does not carry `session_id`.
        ResourceNotFoundError
            If no packet of the packet set holds the resource.
        """
        if on_clock is False and not seconds:
            return self.scanner(resource_id, columns=columns, filter=None, **where).to_table()
        rest, _ = self._identity_constraints(resource_id, where)
        identity = PROJECTED if columns is None else tuple(c for c in PROJECTED if c in columns)
        parts = []
        for packet, session_ids in self._reached(resource_id, where):
            wanted = columns
            if columns is not None and resource_id in self._scoped:
                wanted = [c for c in columns if c not in PROJECTED]
                if identity and "session_id" not in wanted and "session_id" in _column_names(packet, resource_id):
                    wanted = [*wanted, "session_id"]
            if not isinstance(on_clock, bool):
                shared_clock(packet, on_clock)
            constraints = rest if session_ids is None else {**rest, "session_id": session_ids}
            part = packet.table(resource_id, columns=wanted, on_clock=on_clock, seconds=seconds, **constraints)
            if resource_id in self._scoped:
                part = self._stamp(packet, resource_id, part, identity)
                if columns is not None and "session_id" not in columns and "session_id" in part.column_names:
                    part = part.drop_columns(["session_id"])
            parts.append(part)
        if not parts:
            return self.scanner(resource_id, columns=columns).projected_schema.empty_table()
        return pa.concat_tables(parts, promote_options="permissive")

    def _holding(self, resource_id: str) -> list[Packet]:
        """Return the packets holding a resource, refusing where none does."""
        holding = [packet for packet in self._packets if resource_id in held(packet)]
        if not holding:
            raise ResourceNotFoundError(f"no packet in this packet set declares {resource_id}", resource_id=resource_id)
        return holding

    def _packet_key(self, packet: Packet) -> int:
        return self._packets.index(packet)

    def _distinguishable(self, packet: Packet, resource_id: str) -> None:
        """Refuse a scoped resource whose rows cannot say which of the packet's sessions they are in."""
        count = len(self._by_packet[packet.manifest.packet_id])
        if count > 1 and "session_id" not in _column_names(packet, resource_id):
            raise MultiSessionUnresolved(
                f"{resource_id} is session-scoped, carries no session_id, and "
                f"{packet.manifest.packet_id} holds {count} sessions"
            )

    def _per_row(self, resource_id: str) -> tuple[pads.Expression, pads.Expression]:
        """Build `session_key` and `session_name` as expressions over `packet_key` and `session_id`."""
        conditions, keys, labels = [], [], []
        for packet in self._holding(resource_id):
            sessions = list(self._by_packet[packet.manifest.packet_id].values())
            in_packet = pc.field("packet_key") == pa.scalar(self._packet_key(packet), pa.int32())
            for session in sessions:
                on_session = pc.field("session_id") == pa.scalar(session.session_id, pa.int32())
                conditions.append(in_packet if len(sessions) == 1 else in_packet & on_session)
                keys.append(pa.scalar(session.session_key, pa.int32()))
                labels.append(pa.scalar(session.session_name, pa.string()))
        struct = pc.make_struct(*conditions)
        return pc.case_when(struct, *keys), pc.case_when(struct, *labels)

    def _identity_constraints(
        self, resource_id: str, where: Mapping[str, Predicate]
    ) -> tuple[dict[str, Predicate], pads.Expression | None]:
        """Split `where` into stored-column constraints and an expression for the identity ones.

        The expression is on `packet_key` and `session_id`, which the files hold, so it prunes.
        """
        rest = {name: value for name, value in where.items() if name not in PROJECTED}
        if not any(where.get(name) is not None for name in PROJECTED):
            return rest, None
        terms = [
            pc.field("packet_key") == pa.scalar(self._packet_key(packet), pa.int32())
            if session_ids is None
            else (pc.field("packet_key") == pa.scalar(self._packet_key(packet), pa.int32()))
            & pc.field("session_id").isin(session_ids)
            for packet, session_ids in self._reached(resource_id, where)
        ]
        if not terms:
            return rest, pc.scalar(False)
        selected = terms[0]
        for term in terms[1:]:
            selected = selected | term
        return rest, selected

    def _reached(self, resource_id: str, where: Mapping[str, Predicate]) -> list[tuple[Packet, list[int] | None]]:
        """Each packet a read reaches, with the `session_id` values its identity constraints keep.

        None keeps every session of the packet. A packet none of whose sessions match is left out.
        """
        identity = {name: where[name] for name in PROJECTED if where.get(name) is not None}
        if identity and resource_id not in self._scoped:
            raise ValueError(f"{resource_id} is not session-scoped, so it carries no {', '.join(identity)}")
        sessions = self.session_table()
        reached: list[tuple[Packet, list[int] | None]] = []
        for packet in self._holding(resource_id):
            if not identity:
                reached.append((packet, None))
                continue
            own = sessions.filter(pc.field("packet_key") == pa.scalar(self._packet_key(packet), pa.int32()))
            kept = own.filter(cast(pads.Expression, expression(identity))).column("session_id")
            matching = cast("list[int]", kept.to_pylist())
            if not matching:
                continue
            if len(matching) == own.num_rows:
                reached.append((packet, None))
            else:
                self._distinguishable(packet, resource_id)
                reached.append((packet, matching))
        return reached

    def _keyed(self, resource_id: str) -> list[tuple[Packet, int]]:
        """Return each packet holding a resource with its `packet_key`."""
        return [(packet, self._packet_key(packet)) for packet in self._holding(resource_id)]

    def _member(self, packet_key: int) -> Packet:
        """Return the packet a `packet_key` names."""
        if not 0 <= packet_key < len(self._packets):
            raise KeyError(f"this packet set has no packet {packet_key}")
        return self._packets[packet_key]

    def _session_ids(self, packet_key: int) -> list[int]:
        """Return the `session_id` of every session the packet a `packet_key` names holds."""
        return list(self._by_packet[self._packets[packet_key].manifest.packet_id])

    def _stamp(self, packet: Packet, resource_id: str, table: pa.Table, names: Sequence[str] = PROJECTED) -> pa.Table:
        """Append the identity columns among `names` to one packet's rows.

        Entirely in Arrow: a lookup over the packet's handful of sessions, then a take. This can
        run over the packet's largest fact tables, so it keeps the operation columnar and builds
        only the columns named, a string per row being the costliest.
        """
        held = list(self._by_packet[packet.manifest.packet_id].values())
        at = None
        if "session_id" in table.column_names:
            at = pc.index_in(table.column("session_id"), value_set=pa.array([s.session_id for s in held], pa.int32()))
        elif len(held) > 1 and set(names) - {"packet_key"}:
            raise MultiSessionUnresolved(
                f"{resource_id} is session-scoped, carries no session_id, and "
                f"{packet.manifest.packet_id} holds {len(held)} sessions"
            )

        def per_session(values: pa.Array[Any]) -> pa.Array[Any] | pa.ChunkedArray[Any]:
            return pa.repeat(values[0], table.num_rows) if at is None else pc.take(values, at)

        for name in names:
            column: pa.Array[Any] | pa.ChunkedArray[Any]
            if name == "packet_key":
                column = pa.repeat(pa.scalar(self._packet_key(packet), pa.int32()), table.num_rows)
            elif name == "session_key":
                column = per_session(pa.array([s.session_key for s in held], pa.int32()))
            else:
                column = per_session(pa.array([s.session_name for s in held], pa.string()))
            table = table.append_column(name, column)
        return table


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


def open_packets(
    paths: Iterable[str | Path | Location | Packet],
    **options: Any,
) -> PacketSet:
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
    PacketSet
        The opened packet set.

    Examples
    --------
    >>> data = open_packets(["/data/ecephys_776259", "/data/ecephys_786867"])  # doctest: +SKIP
    >>> con = data.duckdb(tables=["core.units", "core.electrode_coordinates"])  # doctest: +SKIP
    """
    opened = [p if isinstance(p, Packet) else open_packet(p, **options) for p in paths]
    return PacketSet(opened)


__all__ = ["PacketSet", "Session", "open_packets"]

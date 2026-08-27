"""The packet: a dataset bundle under a declared physical profile."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pc

from .errors import ResourceNotFoundError, ResourceUnreadableError, UnsupportedCodecError
from .manifest import Manifest, Resource
from .resources import TableResource

if TYPE_CHECKING:  # pragma: no cover
    import duckdb

REGISTRY_PATH = "schemas/logical_schemas.json"

#: Zarr codecs every conforming reader must support (R3 §7.2). Arrays arrive at Phase 5;
#: this is declared here so a packet requiring more can be rejected before it is opened.
BASELINE_CODECS = frozenset({"none", "gzip", "zstd"})


class Packet:
    """A packet opened for reading.

    Resolves resources through the manifest rather than by filename convention, so a
    packet that partitions a table or relocates a file stays readable without changes here.
    """

    def __init__(self, root: Path, manifest: Manifest) -> None:
        """Wrap an already-parsed manifest at a packet root.

        Parameters
        ----------
        root : Path
            Packet root directory.
        manifest : Manifest
            The parsed manifest.
        """
        self._root = root
        self._manifest = manifest
        self._by_id = {r.resource_id: r for r in manifest.resources}

    @property
    def root(self) -> Path:
        """The packet root directory."""
        return self._root

    @property
    def manifest(self) -> Manifest:
        """The parsed manifest."""
        return self._manifest

    @property
    def sessions(self) -> tuple[str, ...]:
        """Every session this packet contains."""
        return self._manifest.sessions

    def __repr__(self) -> str:
        """Return a short representation naming the packet and its resource count."""
        return f"<Packet {self._manifest.packet_id!r} at {self._root} with {len(self._by_id)} resources>"

    # -- resources ------------------------------------------------------------------

    def resources(self, *, layer: str | None = None, kind: str | None = None) -> tuple[Resource, ...]:
        """List declared resources, optionally filtered.

        Parameters
        ----------
        layer : str, optional
            Restrict to one layer, e.g. ``core``.
        kind : str, optional
            Restrict to one kind, e.g. ``table``.

        Returns
        -------
        tuple of Resource
            Matching resources, in manifest order.
        """
        return tuple(
            r
            for r in self._manifest.resources
            if (layer is None or r.layer == layer) and (kind is None or r.kind == kind)
        )

    def resource(self, resource_id: str) -> Resource:
        """Look up one resource by ID.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        Resource
            The declared resource.

        Raises
        ------
        ResourceNotFoundError
            If the manifest declares no such resource.
        """
        try:
            return self._by_id[resource_id]
        except KeyError:
            known = ", ".join(sorted(self._by_id)) or "none"
            raise ResourceNotFoundError(f"{resource_id!r} is not declared; the packet has: {known}") from None

    def path(self, resource_id: str) -> Path:
        """Resolve a resource's URI to a filesystem path.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        Path
            The resolved path.

        Raises
        ------
        ResourceUnreadableError
            If the resolved path does not exist.
        """
        return self.table_resource(resource_id).path

    def table_resource(self, resource_id: str) -> TableResource:
        """Get a readable handle for a resource.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        TableResource
            A handle that can read, open lazily, or register the resource.
        """
        return TableResource(self.resource(resource_id), self._root)

    # -- the registry the packet carries --------------------------------------------

    @property
    def registry(self) -> dict[str, Any] | None:
        """The schema registry embedded in the packet, if it carries one.

        A packet SHOULD embed its registry so that it stays self-describing as the
        reference registry moves on. Reading does not require it; validation does.

        Returns
        -------
        dict or None
            The parsed registry, or None if the packet does not embed one.
        """
        path = self._root / REGISTRY_PATH
        if not path.is_file():
            return None
        parsed: dict[str, Any] = json.loads(path.read_text())
        return parsed

    # -- codec capability -------------------------------------------------------------

    def check_codecs(self, supported: Iterable[str] = BASELINE_CODECS) -> None:
        """Check that this reader supports every codec the packet requires.

        A reader must make this check before opening any array, and fail naming the codec
        it lacks rather than attempting the read.

        Parameters
        ----------
        supported : iterable of str, optional
            Codecs this reader can decode. Defaults to the portable-profile baseline.

        Raises
        ------
        UnsupportedCodecError
            If the packet requires a codec that is not supported.
        """
        missing = sorted(set(self._manifest.required_codecs) - set(supported))
        if missing:
            raise UnsupportedCodecError(
                f"{self._manifest.packet_id} requires codecs this reader does not support: {', '.join(missing)}"
            )

    # -- tabular access ---------------------------------------------------------------

    def table(self, resource_id: str) -> pa.Table:
        """Read a table resource into memory.

        Parameters
        ----------
        resource_id : str
            Dotted resource ID.

        Returns
        -------
        pyarrow.Table
            The table, read in stored order.
        """
        return self.table_resource(resource_id).to_arrow()

    def duckdb(self, *, connection: duckdb.DuckDBPyConnection | None = None) -> duckdb.DuckDBPyConnection:
        """Register every table resource as a view and return the connection.

        Views are named by flattening the dotted resource ID, so ``core.trials`` is queried
        as ``core_trials``.

        Parameters
        ----------
        connection : duckdb.DuckDBPyConnection, optional
            An existing connection to register into. A new in-memory one is created if
            omitted.

        Returns
        -------
        duckdb.DuckDBPyConnection
            The connection, with every readable table resource registered.
        """
        if connection is not None:
            con = connection
        else:
            try:
                import duckdb as _duckdb
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise ImportError(
                    "SQL access requires duckdb; install the 'validate' extra. Reading a packet "
                    "does not require it: use table(), the accessors, or TableResource.dataset()."
                ) from exc
            con = _duckdb.connect()
        for resource in self.resources(kind="table") + self.resources(kind="materialized_table"):
            handle = TableResource(resource, self._root)
            try:
                handle.register(con)
            except ResourceUnreadableError:
                continue
        return con

    def sql(self, query: str) -> pa.Table:
        """Run a query against this packet's tables.

        Parameters
        ----------
        query : str
            SQL referring to resources by their flattened names.

        Returns
        -------
        pyarrow.Table
            The result.
        """
        return self.duckdb().sql(query).to_arrow_table()

    # -- convenience accessors --------------------------------------------------------

    def _filtered(self, resource_id: str, columns: list[str] | None = None, **equals: str | None) -> pa.Table:
        """Read a resource, keeping rows whose columns equal the given values.

        Filtering runs through PyArrow rather than DuckDB so that reading a packet never
        requires a SQL engine.
        """
        table = self.table(resource_id)
        for column, value in equals.items():
            if value is not None:
                table = table.filter(pc.equal(table[column], pa.scalar(value)))
        return table.select(columns) if columns else table

    def trials(self, *, session_id: str | None = None, condition_id: str | None = None) -> pa.Table:
        """Read ``core.trials``, optionally filtered.

        Parameters
        ----------
        session_id : str, optional
            Keep only this session.
        condition_id : str, optional
            Keep only this experimental condition.

        Returns
        -------
        pyarrow.Table
            Matching trials.
        """
        return self._filtered("core.trials", session_id=session_id, condition_id=condition_id)

    def units(self, *, session_id: str | None = None, quality_label: str | None = None) -> pa.Table:
        """Read ``core.units``, optionally filtered.

        Parameters
        ----------
        session_id : str, optional
            Keep only this session.
        quality_label : str, optional
            Keep only units with this curation label: ``sua``, ``mua``, or ``noise``.

        Returns
        -------
        pyarrow.Table
            Matching units.
        """
        return self._filtered("core.units", session_id=session_id, quality_label=quality_label)

    def events(self, *, event_type: str | None = None, session_id: str | None = None) -> pa.Table:
        """Read ``core.events``, optionally filtered.

        Parameters
        ----------
        event_type : str, optional
            Keep only events of this type. The vocabulary is open, so an unrecognized
            value is not an error, only empty.
        session_id : str, optional
            Keep only this session.

        Returns
        -------
        pyarrow.Table
            Matching events.
        """
        return self._filtered("core.events", event_type=event_type, session_id=session_id)

    def spike_times(
        self,
        unit_id: str,
        *,
        session_id: str | None = None,
        sorting_run_id: str | None = None,
        curation_id: str | None = None,
    ) -> pa.Table:
        """Read one unit's spike times.

        Returns ``clock_id`` alongside ``t_tick`` because a tick has no meaning without the
        clock it was counted on.

        A unit is identified by ``(session_id, unit_id, sorting_run_id, curation_id)``, so a
        packet holding more than one sorting or curation of the same unit needs those
        arguments to disambiguate.

        Parameters
        ----------
        unit_id : str
            The unit.
        session_id, sorting_run_id, curation_id : str, optional
            Narrow the unit's identifying context.

        Returns
        -------
        pyarrow.Table
            Columns ``t_tick`` and ``clock_id``, in stored order.
        """
        return self._filtered(
            "core.spike_events",
            ["t_tick", "clock_id"],
            unit_id=unit_id,
            session_id=session_id,
            sorting_run_id=sorting_run_id,
            curation_id=curation_id,
        )


def open_packet(path: str | Path, *, validate_manifest: bool = True) -> Packet:
    """Open a packet for reading.

    Parameters
    ----------
    path : str or Path
        Packet root directory.
    validate_manifest : bool, default True
        Whether to check the manifest against its JSON Schema before parsing.

    Returns
    -------
    Packet
        The opened packet.
    """
    root = Path(path)
    return Packet(root, Manifest.load(root, validate=validate_manifest))

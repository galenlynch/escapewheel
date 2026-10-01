"""The packet version an amendment amends, and how delivered rows settle against it (Part 05 §15).

- :class:`Held` -- a committed packet version: its rows, the numbers it assigned, and the
  settlement of each delivered table against them.
- :func:`owned` -- the assigned identifiers a table's rows own, each with its `*_name` column.
- :data:`PREVAILING` -- the tables whose held rows prevail over every source.

The writer uses the validator's test of whether a delivered row joins a held group
(`escapewheel_validator.amendment`), so it never builds an amended packet that a validator would
report.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from escapewheel_reader import Manifest, Packet
from escapewheel_reader.manifest import MANIFEST_FILENAME
from escapewheel_reader.resource_ids import CORE_CLOCKS, CORE_SESSIONS, CORE_SOURCE_FILES, CORE_SUBJECTS
from escapewheel_reader.sql import quote
from escapewheel_validator.amendment import PREFERENCES, Version, absent

from .arrow import sort_key
from .errors import AmendmentFault, AmendmentRefused

#: Tables the packet identifies itself by, whose held rows prevail over every source in an amending
#: build (Part 05 §3.5).
PREVAILING = frozenset({CORE_SESSIONS, CORE_SUBJECTS})

#: Rows a refusal shows, so a message names the offending rows without printing a table.
SHOWN = 3


def owned(spec: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Return each assigned identifier a table's rows own, with the `*_name` column naming it.

    Owned means in the primary key and exported through no reference, which is where `number`
    fills the name (R53 §2.3.1).
    """
    exported = {c for ref in spec.get("references", ()) for c in ref["columns"]}
    primary = set(spec.get("primary_key") or ())
    return [
        (c["name"], f"{c['name'].removesuffix('_id')}_name")
        for c in spec["columns"]
        if c.get("role") == "identifier"
        and c.get("identity") == "assigned"
        and c["name"] in primary
        and c["name"] not in exported
    ]


def _kinds(spec: Mapping[str, Any]) -> dict[str, str]:
    """Return each assigned identifier column's numbering kind, as `arrow.number` chooses it."""
    target = {
        column: referenced
        for ref in spec.get("references", ())
        for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
    }
    return {
        c["name"]: target.get(c["name"], c["name"])
        for c in spec["columns"]
        if c.get("role") == "identifier" and c.get("identity") == "assigned"
    }


class Held:
    """A committed packet version an amendment amends.

    Parameters
    ----------
    root : Path
        The packet root.
    manifest : Mapping
        Its current manifest.
    """

    def __init__(self, root: Path, manifest: Mapping[str, Any]) -> None:
        self.root = root
        self.manifest = manifest
        self.packet = Packet(root, Manifest.from_dict(manifest))
        self.entries = {e["resource_id"]: e for e in manifest["resources"]}
        #: Resource ID to table declaration, from the registries the amendment binds.
        self.tables: Mapping[str, Mapping[str, Any]] = {}
        #: Resource ID to content class, for every declaration those registries hold.
        self.classes: Mapping[str, str] = {}
        #: Whether held session and subject rows prevail over delivered ones whatever they hold, as
        #: in an amending build (Part 05 §3.5), rather than settling like any other row.
        self.prevail = False
        #: Kind to every name the packet numbered, so a run added can be named apart (Part 05 §12).
        self.held_names: dict[str, set[str]] = {}
        self._connection: Any = None
        self._spill: Path | None = None
        self._version: Version | None = None

    @classmethod
    def open(cls, root: str | Path) -> Held:
        """Read the packet at `root`, once any interrupted promotion there is finished (Part 05 §6).

        Raises
        ------
        AmendmentRefused
            If `root` holds no published manifest.
        """
        from .writer import _act_on_promotion

        root = Path(root)
        _act_on_promotion(root)
        path = root / MANIFEST_FILENAME
        if not path.is_file():
            raise AmendmentRefused(
                f"{root} holds no published {MANIFEST_FILENAME}, so there is no packet to amend",
                code=AmendmentFault.NO_PACKET,
            )
        return cls(root, json.loads(path.read_text()))

    @property
    def version(self) -> str:
        """The `packet_version` amended."""
        return str(self.manifest["packet_version"])

    def documents(self) -> dict[str, dict[str, Any]]:
        """Return each registry the manifest binds, by registry ID."""
        return {name: self.packet.registry_document(name) for name in self.manifest.get("registries", {})}

    def bind(self, tables: Mapping[str, Mapping[str, Any]], classes: Mapping[str, str]) -> None:
        """Take the declarations the amendment binds, which name every column compared (Part 05 §15.6)."""
        self.tables = tables
        self.classes = classes
        self._version = None

    def path(self, resource_id: str) -> Path | None:
        """Return the file this version names for a table, or None where it names none."""
        return self.packet.path(resource_id) if resource_id in self.entries else None

    def canonical(self, resource_id: str) -> bool:
        """Whether a resource's content class is canonical (Part 02 §2.2)."""
        return self.classes.get(resource_id) in {"core", "extension"}

    def tables_named(self) -> list[str]:
        """Return every table the manifest names, which an amending recipe counts as supplied."""
        return [rid for rid, entry in self.entries.items() if str(entry.get("uri", "")).endswith(".parquet")]

    def clock_names(self) -> list[str]:
        """Return the `clock_name` of every `core.clocks` row the packet holds (Part 05 §3.5)."""
        if CORE_CLOCKS not in self.entries:
            return []
        table = pq.read_table(self.packet.path(CORE_CLOCKS), columns=["clock_name"])
        return [str(name) for name in table.column("clock_name").to_pylist() if name is not None]

    def source_files(self, keys: Any) -> dict[str, str]:
        """Return each `uri` the packet's `core.source_files` rows record, to that row's name (Part 05 §7)."""
        return {str(row["uri"]): str(row["source_file_id"]) for row in self.named_rows(CORE_SOURCE_FILES, keys)}

    # -- numbering --------------------------------------------------------------------

    def seed(self, keys: Any) -> None:
        """Hold every number the packet assigned, by the name its owning row gives (Part 05 §4.3).

        Raises
        ------
        AmendmentRefused
            If a held row owns an assigned identifier and gives it no name, since the build could
            then not tell that identifier from one it assigns (Part 05 §3.5).
        """
        for resource_id in sorted(self.tables):
            if resource_id not in self.entries:
                continue
            for column, named in owned(self.tables[resource_id]):
                present = set(pq.read_schema(self.packet.path(resource_id)).names)
                if named not in present:
                    raise AmendmentRefused(
                        f"{resource_id} holds {column} with no {named}, so an amending build cannot tell a held "
                        "identifier from one it assigns (Part 05 §3.5)",
                        code=AmendmentFault.HELD_NAME_ABSENT,
                        resource_id=resource_id,
                    )
                table = pq.read_table(self.packet.path(resource_id), columns=[column, named])
                numbers, names = table.column(column).to_pylist(), table.column(named).to_pylist()
                if None in names:
                    raise AmendmentRefused(
                        f"{resource_id} holds a null {named} for {names.count(None)} row(s), so an amending build "
                        f"cannot tell a held {column} from one it assigns (Part 05 §3.5)",
                        code=AmendmentFault.HELD_NAME_ABSENT,
                        resource_id=resource_id,
                    )
                held = self.held_names.setdefault(column, set())
                for number, name in zip(numbers, names, strict=True):
                    try:
                        keys.hold(column, str(name), int(number))
                    except ValueError as exc:
                        raise AmendmentRefused(
                            f"{resource_id}: {exc}", code=AmendmentFault.HELD_KEY_TAKEN, resource_id=resource_id
                        ) from None
                    held.add(str(name))

    def apart(self, kind: str, name: str) -> str:
        """Return `name`, or the first `name.<n>` from 2 up, whichever the packet does not hold."""
        held = self.held_names.get(kind, set())
        if name not in held:
            return name
        n = 2
        while f"{name}.{n}" in held:
            n += 1
        return f"{name}.{n}"

    def named_rows(self, resource_id: str, keys: Any) -> list[dict[str, Any]]:
        """Return a held table's rows with each assigned identifier replaced by its name.

        Which is how a row arrives from a source, so the packet's rows can be handed to the sources
        after them as delivered before any runs (Part 05 §4.3).
        """
        if resource_id not in self.entries or resource_id not in self.tables:
            return []
        spec = self.tables[resource_id]
        kinds = _kinds(spec)
        # A value a discriminator on its own row pairs is numbered in the named resource's one key
        # column (Part 02 §8.3).
        paired = {
            c["discriminates"]: c["name"]
            for c in spec["columns"]
            if c.get("role") == "discriminator" and c.get("discriminates") and c.get("discriminates_via") is None
        }
        rows = pq.read_table(self.packet.path(resource_id)).to_pylist()
        for row in rows:
            for column, kind in kinds.items():
                if row.get(column) is not None:
                    row[column] = keys.name_of(kind, int(row[column])) or row[column]
            for column, discriminator in paired.items():
                key = list((self.tables.get(str(row.get(discriminator))) or {}).get("primary_key") or ())
                if isinstance(row.get(column), int) and len(key) == 1:
                    row[column] = keys.name_of(key[0], int(row[column])) or row[column]
        return rows

    # -- settlement -------------------------------------------------------------------

    def _duckdb(self) -> Any:
        """Return the connection settlement runs on, spilling beside the packet rather than in RAM."""
        if self._connection is None:
            import duckdb

            self._connection = duckdb.connect()
            self._connection.execute("SET TimeZone = 'UTC'")
            self._spill = Path(tempfile.mkdtemp(prefix=".amend-", dir=self.root.parent))
            self._connection.execute(f"SET temp_directory = '{self._spill}'")
            self._connection.execute("SET memory_limit = '4GB'")
        return self._connection

    def close(self) -> None:
        """Release the settlement connection and its spill directory."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._spill is not None:
            shutil.rmtree(self._spill, ignore_errors=True)
            self._spill = None
        self._version = None

    def _held_version(self) -> Version:
        if self._version is None:
            self._version = Version(self._duckdb(), "held", self.tables, self.path)
        return self._version

    def _replaces(self, resource_id: str, derived: Collection[str]) -> bool:
        """Whether a delivered table replaces the held resource whole (Part 05 §15.2)."""
        return not self.canonical(resource_id) and (resource_id not in self.entries or resource_id in derived)

    def _verdicts(self, resource_id: str, delivered: pa.Table) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return, per delivered row, whether it equals a held row, forms a new group, or replaces one.

        Equality is over every declared column but `metadata` (Part 05 §4.3); a group is new where,
        under at least one group list, the packet does not hold it (Part 02 §2.8).
        """
        spec = self.tables[resource_id]
        version = self._held_version()
        connection = version.connection
        columns = [c["name"] for c in spec["columns"]]
        present = set(delivered.schema.names)
        indexed = delivered.append_column("__row", pa.array(np.arange(delivered.num_rows), type=pa.int64()))
        connection.register("delivered_rows", indexed)
        select = ", ".join(quote(c["name"]) if c["name"] in present else absent(c) for c in spec["columns"])
        connection.execute(f"CREATE OR REPLACE TEMP VIEW delivered AS SELECT __row, {select} FROM delivered_rows")
        held = version.view(resource_id)
        compared = [c for c in columns if c != "metadata"]
        equal = " AND ".join(f"h.{quote(c)} IS NOT DISTINCT FROM d.{quote(c)}" for c in compared)
        key = list(spec.get("primary_key") or ())
        replaces = (
            "EXISTS (SELECT 1 FROM "
            + held
            + " AS h WHERE "
            + " AND ".join(f"h.{quote(k)} IS NOT DISTINCT FROM d.{quote(k)}" for k in key)
            + ")"
            if resource_id == PREFERENCES and key
            else "false"
        )
        result = connection.execute(
            f"SELECT EXISTS (SELECT 1 FROM {held} AS h WHERE {equal}) AS equal, NOT {version.grows(resource_id, 'd')} "
            f"AS fresh, {replaces} AS replaces FROM delivered AS d ORDER BY __row"
        ).to_arrow_table()
        connection.unregister("delivered_rows")
        equal_rows, fresh_rows, replacing = (
            np.asarray(result.column(name).to_numpy(zero_copy_only=False), dtype=bool)
            for name in ("equal", "fresh", "replaces")
        )
        return equal_rows, fresh_rows, replacing

    def _refuse(self, resource_id: str, delivered: pa.Table, refused: np.ndarray) -> None:
        """Refuse delivered rows that would change or grow a group the packet holds (Part 05 §4.3)."""
        rows = delivered.filter(pa.array(refused)).slice(0, SHOWN).to_pylist()
        raise AmendmentRefused(
            f"{resource_id}: {int(refused.sum()):,} delivered row(s) neither equal a row the packet holds nor form a "
            f"group it lacks, so amending would change or grow what it holds (Part 05 §15.2); a packet whose "
            f"canonical data changes is a new packet. First: {rows}",
            code=AmendmentFault.CHANGES_HELD,
            resource_id=resource_id,
        )

    def settle(self, resource_id: str, delivered: pa.Table, *, derived: Collection[str] = ()) -> pa.Table | None:
        """Return the table the amendment writes for delivered rows, or None to keep the held entry.

        A row equal to a held one is dropped, a row forming a group the packet lacks is added to the
        held rows, and a `core.preferred_runs` row replaces the held row of its key (Part 05 §15.2).

        Parameters
        ----------
        resource_id : str
            The table.
        delivered : pyarrow.Table
            Its delivered rows, numbered.
        derived : collection of str
            Resources this amendment derives, which replace the held resource whole.

        Raises
        ------
        AmendmentRefused
            Naming the table and its first offending rows, if any delivered row is neither.
        """
        if self._replaces(resource_id, derived):
            return delivered
        if resource_id in PREVAILING and self.prevail:
            return None
        if resource_id not in self.tables:
            return delivered
        equal, fresh, replaces = self._verdicts(resource_id, delivered)
        if (refused := ~equal & ~fresh & ~replaces).any():
            self._refuse(resource_id, delivered, refused)
        added = ~equal & (fresh | replaces)
        if not added.any():
            return None
        adding = delivered.filter(pa.array(added))
        spec = self.tables[resource_id]
        if resource_id not in self.entries:
            return adding
        held = pq.read_table(self.packet.path(resource_id))
        if (replaced := replaces & added).any():
            key = list(spec.get("primary_key") or ())
            gone = {tuple(row[k] for k in key) for row in delivered.filter(pa.array(replaced)).select(key).to_pylist()}
            keep = [tuple(row[k] for k in key) not in gone for row in held.select(key).to_pylist()]
            held = held.filter(pa.array(keep, type=pa.bool_()))
        return _ordered(resource_id, spec, [held, adding])

    def settle_stream(
        self, resource_id: str, batches: Iterable[pa.RecordBatch], *, derived: Collection[str] = ()
    ) -> Iterator[pa.RecordBatch]:
        """Yield the batches the amendment writes for a streamed table: the held rows, then those added.

        As `settle`, batch by batch, so a table too large to hold is compared without holding it. A
        delivered row in a group the packet holds is set aside and, once the stream ends, must equal
        a held row. Yields nothing where no row is added, which leaves the held entry in place.

        Held rows come first, so an added group must sort after every held one, which a group
        numbered after the packet's identifiers does (Part 05 §4.3); one that does not is refused by
        the order check the stream passes through.
        """
        if self._replaces(resource_id, derived) or resource_id not in self.tables:
            yield from batches
            return
        spec = self.tables[resource_id]
        connection = self._held_version().connection
        pending = quote(f"pending__{resource_id}")
        compared = [c for c in spec["columns"] if c["name"] != "metadata"]
        started = False
        for batch in batches:
            table = pa.Table.from_batches([batch])
            equal, fresh, _ = self._verdicts(resource_id, table)
            if (aside := ~fresh & ~equal).any():
                rows = table.filter(pa.array(aside))
                select = ", ".join(quote(c["name"]) if c["name"] in rows.schema.names else absent(c) for c in compared)
                connection.register("aside_rows", rows)
                connection.execute(
                    f"CREATE TEMP TABLE IF NOT EXISTS {pending} AS SELECT {select} FROM aside_rows WHERE false"
                )
                connection.execute(f"INSERT INTO {pending} SELECT {select} FROM aside_rows")
                connection.unregister("aside_rows")
            if not (fresh & ~equal).any():
                continue
            adding = table.filter(pa.array(fresh & ~equal))
            if not started:
                started = True
                yield from self._held_batches(resource_id, adding.schema)
            yield from adding.to_batches()
        self._check_pending(resource_id, pending, [c["name"] for c in compared])

    def _held_batches(self, resource_id: str, schema: pa.Schema) -> Iterator[pa.RecordBatch]:
        """Yield the held rows, one batch per row group, over the columns the added rows carry."""
        if resource_id not in self.entries:
            return
        source = pq.ParquetFile(self.packet.path(resource_id))
        for index in range(source.num_row_groups):
            group = source.read_row_group(index)
            columns = [
                group.column(field.name).cast(field.type)
                if field.name in group.schema.names
                else pa.nulls(group.num_rows, field.type)
                for field in schema
            ]
            yield from pa.table(columns, schema=schema).to_batches()

    def _check_pending(self, resource_id: str, pending: str, compared: Sequence[str]) -> None:
        """Refuse set-aside streamed rows that equal no held row (Part 05 §4.3)."""
        connection = self._held_version().connection
        exists = connection.execute(
            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{pending.strip(chr(34))}'"
        ).fetchone()[0]
        if not exists:
            return
        listed = ", ".join(quote(c) for c in compared)
        query = f"SELECT {listed} FROM {pending} EXCEPT SELECT {listed} FROM {self._held_version().view(resource_id)}"
        count = connection.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]
        shown = connection.execute(f"SELECT * FROM ({query}) LIMIT {SHOWN}").fetchall() if count else []
        connection.execute(f"DROP TABLE {pending}")
        if count:
            raise AmendmentRefused(
                f"{resource_id}: {count:,} delivered row(s) join groups the packet holds and equal none of its rows, "
                f"so amending would change or grow what it holds (Part 05 §15.2). First: {shown}",
                code=AmendmentFault.CHANGES_HELD,
                resource_id=resource_id,
            )


def _ordered(resource_id: str, spec: Mapping[str, Any], parts: Sequence[pa.Table]) -> pa.Table:
    """Concatenate tables over the union of their columns, in the table's stored order (Part 03 §5.3)."""
    combined = pa.concat_tables(parts, promote_options="permissive")
    declared = [c["name"] for c in spec["columns"] if c["name"] in combined.schema.names]
    combined = combined.select(declared)
    if order := sort_key(resource_id, spec):
        combined = combined.sort_by([(k, "ascending", "at_start") for k in order])
    return combined


__all__ = ["PREVAILING", "Held", "owned"]

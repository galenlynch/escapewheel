"""The number each of a packet's names takes, and its tables as Arrow."""

import pyarrow as pa
import pyarrow.compute as pc

from .registry import OVERRIDING_ORDERS

ARROW = {
    "string": pa.string(),
    "int32": pa.int32(),
    "int64": pa.int64(),
    "float32": pa.float32(),
    "float64": pa.float64(),
    "bool": pa.bool_(),
    "date": pa.date32(),
    "timestamp": pa.timestamp("us", tz="UTC"),
    "json_string": pa.string(),
}


class Numbering:
    """The number each name takes in one packet, among the tables its registries declare.

    R53 §2.1: an identifier is an integer. The fixture writes names and numbers them here, one
    map per column so every table agrees -- deliberately its own rather than the writer's, since
    a hand-built packet exercises the format without going through the writer at all.
    """

    def __init__(self, *registries: dict) -> None:
        #: Every table the packet may write, by resource ID.
        self.specs = {
            name: declaration["table"]
            for document in registries
            for name, declaration in document["resources"].items()
            if declaration["kind"] == "table"
        }
        #: Each identifier column's map from a name to its number.
        self.keys: dict[str, dict[str, int]] = {}

    def table(self, resource: str, rows: list[dict], readers=None) -> pa.Table:
        """Build an Arrow table for `resource` with exactly the registry's schema.

        Columns absent from `rows` are emitted as nulls unless the registry marks them
        optional, in which case they are omitted entirely — exercising all three presence
        states (Part 02 §6).
        """
        spec = self.specs[resource]
        declared = {c["name"] for c in spec["columns"]}
        if undeclared := sorted({key for row in rows for key in row} - declared):
            raise SystemExit(f"{resource}: no column declares {undeclared}, so it would be dropped")
        rows = self.number(spec, [dict(r) for r in rows], readers)
        arrays, fields = [], []
        for c in spec["columns"]:
            present = any(c["name"] in r for r in rows)
            if c["presence"] == "optional" and not present:
                continue
            typ = ARROW[c["type"]]
            arrays.append(pa.array([r.get(c["name"]) for r in rows], type=typ))
            fields.append(pa.field(c["name"], typ))
        return pa.table(arrays, schema=pa.schema(fields))

    def number(self, spec, rows, readers=None):
        """Replace an identifier's name with its number, and fill in the `*_name` that records it.

        `readers` maps an identifier paired value to a function from its row to the map it numbers in.
        """
        exported = {c for ref in spec.get("references", []) for c in ref["columns"]}
        primary = set(spec.get("primary_key") or [])
        declared = {c["name"] for c in spec["columns"]}
        # A foreign key numbers in the map of the column it points at. `parent_clock_id` and
        # `clock_id` are both clocks; numbering them apart makes the parent chain name a clock that
        # does not exist, which is what Part 01 §3.9 requires to be well-founded.
        target = {
            column: referenced
            for ref in spec.get("references", [])
            for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
        }
        identifiers = [c for c in spec["columns"] if c.get("role") == "identifier"]
        # Read before anything is numbered: a row reaches its kind through its own references.
        kinds = {name: [reader(r) for r in rows] for name, reader in (readers or {}).items()}

        def kind_of(name, index):
            return (kinds[name][index] if name in kinds else None) or target.get(name, name)

        # Collect every name before assigning any: `parent_clock_id` and `clock_id` share a map, and
        # whichever column the loop reached first would otherwise decide the numbering.
        pending = {}
        for column in identifiers:
            if column.get("identity") != "assigned":
                continue
            for index, r in enumerate(rows):
                if r.get(column["name"]) is not None:
                    pending.setdefault(kind_of(column["name"], index), set()).add(str(r[column["name"]]))
        for kind in sorted(pending):
            within = self.keys.setdefault(kind, {})
            for value in sorted(pending[kind]):
                within.setdefault(value, len(within))

        for column in identifiers:
            name = column["name"]
            assigned = column.get("identity") == "assigned"
            owns = assigned and name in primary and name not in exported
            named = f"{name.removesuffix('_id')}_name" if owns else None
            for index, row in enumerate(rows):
                if row.get(name) is None:
                    continue
                value = str(row[name])
                if named is not None and named in declared and row.get(named) is None:
                    row[named] = value
                if assigned:
                    row[name] = self.keys[kind_of(name, index)][value]
                elif column["type"] != "string":
                    row[name] = int(row[name])
        return rows

    def paired_readers(self, tables: dict[str, list[dict]], resource: str) -> dict:
        """Map each identifier paired value `resource` holds to a function from its row to its map.

        Part 02 §8.3 lets an identifier hold the key of whichever resource its row's kind names, so
        its map is that resource's one key column, chosen per row. A value on a specialised table
        reaches its kind through the reference back to the discriminator's table, by names.
        """

        def key_of(kind):
            key = (self.specs.get(kind) or {}).get("primary_key") or []
            return key[0] if len(key) == 1 else None

        readers = {}
        for owner, spec in self.specs.items():
            for column in spec["columns"]:
                if column.get("role") != "discriminator" or not column.get("discriminates"):
                    continue
                via = column.get("discriminates_via")
                if (owner if via is None else via.rsplit(".", 1)[0]) != resource:
                    continue
                name = column["name"]
                if via is None:
                    readers[column["discriminates"]] = lambda row, name=name: key_of(row.get(name))
                    continue
                back = next(r for r in self.specs[resource]["references"] if r["resource"] == owner)
                kinds = {
                    tuple(str(r.get(c)) for c in back["resource_columns"]): r.get(name) for r in tables.get(owner, [])
                }
                readers[column["discriminates"]] = lambda row, kinds=kinds, ours=back["columns"]: key_of(
                    kinds.get(tuple(str(row.get(c)) for c in ours))
                )
        return readers

    def preassign(self, tables: dict[str, list[dict]]) -> None:
        """Number every name the packet uses, before any table is built.

        Assigning as each table is built would let the order tables happen to be written in decide
        the numbers: `core.sessions` names a `reference_clock_id` and is written before
        `core.clocks`, so the clocks would be numbered by the session's mention of one of them.
        Part 05 §4.3 wants two builds of the same sources to produce the same packet, and this is what
        makes that hold across tables as well as within one.
        """
        pending: dict[str, set[str]] = {}
        for resource, rows in sorted(tables.items()):
            spec = self.specs.get(resource)
            if spec is None:
                continue
            target = {
                column: referenced
                for ref in spec.get("references", [])
                for column, referenced in zip(ref["columns"], ref["resource_columns"], strict=True)
            }
            readers = self.paired_readers(tables, resource)
            for column in spec["columns"]:
                name = column["name"]
                if column.get("role") != "identifier" or column.get("identity") != "assigned":
                    continue
                for r in rows:
                    if r.get(name) is not None:
                        kind = (readers[name](r) if name in readers else None) or target.get(name, name)
                        pending.setdefault(kind, set()).add(str(r[name]))
        for kind in sorted(pending):
            if kind == "interval_id":
                continue
            within = self.keys.setdefault(kind, {})
            for value in sorted(pending[kind]):
                within.setdefault(value, len(within))
        # Part 02 §12.9 numbers intervals by session, kind, clock and bounds, which only their rows
        # hold, so the rows order the names; a name no interval row carries is an orphan and follows.
        within = self.keys.setdefault("interval_id", {})
        for r in sorted(tables.get("core.intervals", []), key=self.interval_order):
            within.setdefault(str(r["interval_id"]), len(within))
        for value in sorted(pending.get("interval_id", ())):
            within.setdefault(value, len(within))

    def interval_order(self, row: dict) -> tuple:
        """Where one `core.intervals` row falls in Part 02 §12.9's numbering."""
        return (
            self.keys["session_id"][str(row["session_id"])],
            row["interval_kind"],
            self.keys["clock_id"][str(row["clock_id"])],
            row["start_tick"],
            row["stop_tick"],
            str(row["interval_id"]),
        )

    def sort_table(self, resource: str, t: pa.Table) -> pa.Table:
        """Apply the stored order (Part 03 §5.3), as a writer should: the key's, unless §5.4 overrides it.

        Sorted by number rather than by name, since Part 02 §12.9 numbers intervals by their bounds.
        """
        order = OVERRIDING_ORDERS.get(resource) or self.specs[resource].get("primary_key") or ()
        keys = [k for k in order if k in t.column_names]
        if not keys:
            return t
        return t.take(pc.sort_indices(t, sort_keys=[(k, "ascending") for k in keys], null_placement="at_end"))

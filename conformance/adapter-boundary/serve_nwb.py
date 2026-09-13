"""The NWB adapter behind a Flight server, built from what a build supplies and nothing else.

`argv[1]` is the whole of it: one JSON object carrying the terms the adapter declared in `NEEDS`
and the one `flight-v0.1` requires, `socket`. Nothing else crosses — no store, no clock object, no
`ZoneInfo`, no object of the writer's — and nothing else is positional.
"""

from __future__ import annotations

import json
import sys
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.flight as fl
from escapewheel_writer.sources.nwb import NWBSource

#: What this adapter declares it needs. Four resolve against the vocabulary a build can supply and
#: two against the recipe's options -- `zone` and `interval_kind` -- because an option an adapter
#: does not declare is one a build refuses the recipe for setting.
NEEDS = ("root", "reference_clock", "session_id", "wanted", "zone", "interval_kind")


def as_table(rows: list[dict]) -> pa.Table:
    """Records as a table, taking the columns from every row rather than from the first.

    `pa.Table.from_pylist` infers the schema from the leading row and drops what later rows carry,
    which loses a column a source populates for some rows only. Types are the build's to settle
    against the registry, so nothing here needs one.
    """
    columns = list(dict.fromkeys(name for row in rows for name in row))
    return pa.Table.from_pylist([{c: row.get(c) for c in columns} for row in rows])


def build(supplied: dict) -> NWBSource:
    """Construct the adapter from values, rebuilding the writer's classes on this side.

    Every value crossed as a string or a record of them, so the types are rebuilt here: the zone is
    an option the recipe set and a `ZoneInfo` is what this adapter wants of it. The reference clock
    needs no rebuilding -- it crossed as its `core.clocks` row and that is what the adapter takes.
    """
    options = dict(supplied.get("options", {}))
    return NWBSource(
        supplied["root"],
        reference_clock=supplied["reference_clock"],
        zone=ZoneInfo(options.pop("zone")),
        session_id=supplied.get("session_id"),
        **options,
    )


class Served(fl.FlightServerBase):
    """One adapter's resources, each a Flight descriptor."""

    def __init__(
        self, location: str, source: NWBSource, wanted: list[str] | None
    ) -> None:
        rows = source.records()
        asked = list(wanted) if wanted else list(rows)
        # A resource this source has nothing for arrives empty rather than not arriving, so a build
        # reads absence as the run having failed and never as the source having nothing to say.
        self.tables = {r: as_table(rows.get(r, [])) for r in asked}
        # Bound last, and that is load-bearing: the base class starts accepting inside its own
        # `__init__`, so a build that reaches the socket as soon as it answers can call a handler
        # before anything assigned after this line exists.
        super().__init__(fl.Location.for_grpc_unix(location))

    def list_flights(self, context, criteria):
        """Stage 1: what this source offers per resource, and how many rows (Part 05 §4.1)."""
        for name, table in self.tables.items():
            descriptor = fl.FlightDescriptor.for_path(name)
            yield fl.FlightInfo(
                table.schema, descriptor, [], table.num_rows, table.nbytes
            )

    def do_get(self, context, ticket):
        """One resource, by the descriptor a build asked for."""
        return fl.RecordBatchStream(self.tables[ticket.ticket.decode()])


if __name__ == "__main__":
    supplied = json.loads(sys.argv[1])
    # No readiness line: a build retries the socket until it answers or this process exits, so an
    # adapter that never binds is detected without it having to say anything.
    Served(supplied["socket"], build(supplied), supplied.get("wanted")).serve()

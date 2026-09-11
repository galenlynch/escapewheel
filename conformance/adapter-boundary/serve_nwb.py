"""The NWB adapter behind a Flight server, built from what a build supplies and nothing else.

`argv[1]` is the socket to serve on; `argv[2]` is the JSON a build sends for the adapter's declared
`NEEDS`. Nothing else crosses: no store, no `Clock`, no `ZoneInfo`, no object of the writer's.
"""

from __future__ import annotations

import json
import sys
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.flight as fl
from escapewheel_writer.clock import Clock
from escapewheel_writer.sources.nwb import NWBSource

#: What this adapter declares it needs, from the closed vocabulary a build can supply.
NEEDS = ("root", "reference_clock", "zone", "session_id", "wanted")


def build(supplied: dict) -> NWBSource:
    """Construct the adapter from values, rebuilding the writer's classes on this side."""
    clock = Clock(**supplied["reference_clock"])
    return NWBSource(
        supplied["root"],
        clock=clock,
        zone=ZoneInfo(supplied["zone"]),
        session_id=supplied.get("session_id"),
        **supplied.get("options", {}),
    )


class Served(fl.FlightServerBase):
    """One adapter's resources, each a Flight descriptor."""

    def __init__(
        self, location: str, source: NWBSource, wanted: list[str] | None
    ) -> None:
        super().__init__(fl.Location.for_grpc_unix(location))
        rows = source.records()
        asked = list(wanted) if wanted else list(rows)
        # A resource this source has nothing for arrives empty rather than not arriving, so a build
        # reads absence as the run having failed and never as the source having nothing to say.
        self.tables = {r: pa.Table.from_pylist(rows.get(r, [])) for r in asked}

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
    supplied = json.loads(sys.argv[2])
    server = Served(sys.argv[1], build(supplied), supplied.get("wanted"))
    print("ready", flush=True)
    server.serve()

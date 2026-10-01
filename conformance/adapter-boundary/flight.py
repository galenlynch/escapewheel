import sys

import pyarrow as pa
import pyarrow.flight as fl

TABLES = {
    "core.sessions": pa.table({"session_id": pa.array([0], "int32")}),
    "core.units": pa.table({"unit_id": pa.array([1, 2], "int32"), "quality": pa.array(["sua", "mua"])}),
    "core.intervals": pa.table({"start_tick": pa.array([10, 20], "int64")}),
}


class Adapter(fl.FlightServerBase):
    def list_flights(self, context, criteria):
        for name, t in TABLES.items():
            d = fl.FlightDescriptor.for_path(name)
            yield fl.FlightInfo(t.schema, d, [], t.num_rows, t.nbytes)

    def do_get(self, context, ticket):
        return fl.RecordBatchStream(TABLES[ticket.ticket.decode()])


if __name__ == "__main__":
    sock = sys.argv[1]
    server = Adapter(fl.Location.for_grpc_unix(sock))
    print("ready", flush=True)
    server.serve()

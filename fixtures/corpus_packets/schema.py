"""Packets that break a table's physical schema."""

import pyarrow as pa

from .record import Expected, Packet
from .registry import KIND
from .session import variant


def retyped(column: str, type_: pa.DataType):
    """Write `column` as `type_`, which its declaration does not give it."""

    def recast(t: pa.Table) -> pa.Table:
        return t.set_column(t.schema.get_field_index(column), column, t.column(column).cast(type_))

    return recast


def without_column(column: str):
    """Leave `column` out of the file."""

    def recast(t: pa.Table) -> pa.Table:
        return t.drop_columns([column])

    return recast


#: Three variants that break the physical schema, not the data.
SCHEMA_PACKETS = (
    Packet(
        "bad_type",
        variant(recast={"core.intervals": retyped("start_tick", pa.int32())}),
        Expected("error", "schema.column_type"),
    ),
    Packet(
        "extension_bad_type",
        # Part 05 §5.4: an extension's table is type-checked as core's are, and the finding is its own.
        variant(recast={KIND: retyped("trial_id", pa.float64())}),
        Expected("error", "schema.column_type", registry="dynamic_foraging"),
    ),
    Packet(
        "missing_column",
        variant(recast={"core.intervals": without_column("clock_id")}),
        Expected("error", "schema.column_absent"),
    ),
)

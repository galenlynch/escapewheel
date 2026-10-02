"""Packets with a resource outside a reader floor, or one a validator cannot assess."""

from pathlib import Path

import pyarrow.parquet as pq

from .arrays import array_entry, catalogue_arrays
from .record import Expected, Packet
from .session import content
from .writing import digest, edit_manifest, write_packet

#: One array per pipeline, by the name it is catalogued under.
FLOOR_ARRAYS = {
    "default_array": "default",
    "sharded_array": "sharded",
    "delta_array": "delta",
}


def outside_array_floor(out: Path) -> None:
    c = content()
    catalogue_arrays(c, list(FLOOR_ARRAYS))
    write_packet(out, c)
    edit_manifest(
        out,
        lambda m: m["resources"].extend(array_entry(out, name, pipeline) for name, pipeline in FLOOR_ARRAYS.items()),
    )


def outside_table_floor(out: Path) -> None:
    # Parquet format version 1.0 writes dictionary pages as PLAIN_DICTIONARY, valid upstream and
    # outside the writer floor (Part 03 §5.5).
    write_packet(out, content())
    entry_uri = "tables/core/intervals.parquet"
    pq.write_table(
        pq.read_table(out / entry_uri),
        out / entry_uri,
        compression="zstd",
        version="1.0",
    )

    def redigest(manifest):
        entry = next(e for e in manifest["resources"] if e["uri"] == entry_uri)
        entry["digest"]["value"] = digest("sha256", (out / entry_uri).read_bytes())

    edit_manifest(out, redigest)


def unresolved_externals(out: Path) -> None:
    names = ["lfp_probe_a", "lfp_probe_b"]
    c = content()
    catalogue_arrays(c, names)
    write_packet(out, c)
    edit_manifest(out, lambda m: m["resources"].extend(array_entry(None, name, "default") for name in names))


#: Part 05 §5.3's outside-floor and unassessed findings, one resource at a time.
FLOOR_PACKETS = (
    Packet("outside_array_floor", outside_array_floor, Expected("info", "physical.outside_reader_floor", count=1)),
    Packet(
        "outside_table_floor",
        outside_table_floor,
        Expected("warning", "physical.outside_reader_floor", conforming=True),
    ),
    Packet("unresolved_externals", unresolved_externals, Expected("info", "external.physical_unassessed", count=2)),
)

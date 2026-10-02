"""A resource's encoding against the reader floor, and what a validation did not assess.

- :func:`check_zarr_floor` -- an array's own metadata against its variant's floor.
- :func:`check_parquet_floor` -- a table's footer-reported compressions and encodings against the
  Parquet floor.
- :func:`report_unassessed` -- one finding for each external resource with a floor whose metadata
  was not read.
- :func:`report_page_types_unassessed` -- the statement that data-page types were not compared.

A resource outside the floor is still conforming; the finding says a reader held only to the floor
may not open it.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from typing import Any

from escapewheel_reader import Packet
from escapewheel_reader.profile import parquet_floor, physical_profile, zarr_floor_outside

from .. import check_table
from ..report import Report
from ..vocabulary import Level


def _floor_level(resource: Any) -> Level:
    """`warning` only where a packet-owned resource exceeds a floor its writer is also held to (Part 05 §5.3)."""
    role = physical_profile()["interfaces"][resource.interface]["floor_role"]
    return Level.WARNING if role == "reader_and_packet_writer" and not resource.is_external else Level.INFO


def check_zarr_floor(resource: Any, metadata: Mapping[str, Any], report: Report) -> None:
    """Report an array whose own metadata places it outside its variant's reader floor (Part 03 §6.4).

    One finding names every member that does so (Part 05 §5.3): the pipeline of a v3 array, and of a
    v2 array `filters` and `compressor`, `dtype`, or all three. An unrecognized codec is valid metadata
    outside the floor, so it draws this finding and nothing else; metadata too malformed to compare is
    upstream invalidity, not a floor observation.
    """
    variants = physical_profile()["interfaces"]["zarr"]["variants"]
    zarr_format = metadata.get("zarr_format")
    selected = next(((name, v) for name, v in variants.items() if v["format_version"] == zarr_format), None)
    if selected is None:
        return
    variant, entry = selected
    try:
        members = zarr_floor_outside(metadata, entry["reader_floor"])
    except (AttributeError, KeyError, TypeError):
        return
    if not members:
        return
    observed = [(member, json.dumps(metadata.get(member), separators=(",", ":"))) for member in members]
    report.add_about(
        resource.resource_id,
        check_table.PHYSICAL_OUTSIDE_READER_FLOOR.at(_floor_level(resource)),
        f"{resource.resource_id}: zarr {variant} "
        + "; ".join(f"{member} {value}" for member, value in observed)
        + " is outside the reader floor of Part 03 §6.4",
        observed,
    )


def check_parquet_floor(resource: Any, metadata: Any, report: Report) -> None:
    """Compare a table's footer-reported compressions and encodings with the Parquet floor (Part 03 §5.5)."""
    floor = parquet_floor()
    compressions: set[str] = set()
    encodings: set[str] = set()
    for index in range(metadata.num_row_groups):
        group = metadata.row_group(index)
        for column in range(group.num_columns):
            chunk = group.column(column)
            compressions.add(str(chunk.compression).upper())
            encodings.update(str(value).upper() for value in chunk.encodings)
    observed = [("compression", value) for value in sorted(compressions - set(floor["compressions"]))]
    observed += [("encoding", value) for value in sorted(encodings - set(floor["encodings"]))]
    if observed:
        report.add_about(
            resource.resource_id,
            check_table.PHYSICAL_OUTSIDE_READER_FLOOR.at(_floor_level(resource)),
            f"{resource.resource_id}: parquet "
            + ", ".join(f"{member} {value}" for member, value in observed)
            + " is outside the reader floor of Part 03 §5.5",
            observed,
        )


def report_unassessed(packet: Packet, assessed: Collection[str], report: Report) -> None:
    """One `info` finding per external resource with a reader floor whose own metadata was not read (Part 05 §5.3)."""
    for resource in packet.resources():
        if resource.is_external and resource.interface is not None and resource.resource_id not in assessed:
            report.add_about(
                resource.resource_id,
                check_table.EXTERNAL_PHYSICAL_UNASSESSED,
                f"{resource.resource_id}: its {resource.interface} metadata was not read, so its physical "
                "version, codecs, compression and encodings are unassessed",
                [(resource.resource_id,)],
            )


def report_page_types_unassessed(tables: int, report: Report) -> None:
    """Part 03 §5.5: a validator comparing only footers states that it did not assess data-page types."""
    if tables:
        report.add(
            check_table.PHYSICAL_PAGE_TYPES_UNASSESSED,
            f"{tables} Parquet footer(s) compared with the floor's compressions and encodings; data-page "
            "types were not assessed, since they are recorded in page headers",
            counts={"tables": tables},
        )


__all__: list[str] = []

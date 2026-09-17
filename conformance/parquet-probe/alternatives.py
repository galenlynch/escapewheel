"""What each column's encoding cost against every encoding Part 03 §5.5 permits.

`layout.py` reports which encoding a column got; this reports what the others would have cost, which
is the number that says whether a rule or an exception chose wrongly. Each row group is rewritten on
its own at its own size, so a dictionary is per group as the writer's is, with zstd on top as Part 03
§5.1 recommends, and only the column chunk's bytes are counted, never a footer. A rewrite under the
encoding the file already uses should reproduce the file's bytes, and the report prints that ratio
for every column over 1 MB so the method can be checked before the rest is trusted.

The ratio is over the column's own best, never over the packet: a small column is often the one a
consumer reads across many packets, and a denominator of 1 GB hides a column twice the size it
should be.

    uv run --with pyarrow python alternatives.py <packet root>

A table over `TARGET` rows is sampled by evenly spaced row groups, and a column's bytes are scaled by
the sampled share of its actual bytes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

#: Rows rewritten per table before sampling by row group.
TARGET = 4_000_000

#: A column is listed where its encoding is at least this many times its best.
RATIO = 1.15

#: Parquet's name for each encoding, where one has to be asked for by name.
BY_NAME = {
    "delta": "DELTA_BINARY_PACKED",
    "delta_length": "DELTA_LENGTH_BYTE_ARRAY",
    "delta_bytes": "DELTA_BYTE_ARRAY",
}


def chosen_of(encodings: set[str]) -> str:
    """The data encoding a column chunk used; PLAIN and RLE also appear under a dictionary."""
    for label in ("delta_bytes", "delta_length", "delta"):
        if BY_NAME[label] in encodings:
            return label
    return "dict" if any("DICTIONARY" in e for e in encodings) else "plain"


def candidates(kind: pa.DataType) -> tuple[str, ...]:
    """The encodings Part 03 §5.5 permits for a type: dictionary, plain, and whichever delta applies."""
    if (
        pa.types.is_integer(kind)
        or pa.types.is_timestamp(kind)
        or pa.types.is_date(kind)
    ):
        return ("dict", "plain", "delta")
    if pa.types.is_floating(kind):
        return ("dict", "plain")
    if (
        pa.types.is_string(kind)
        or pa.types.is_large_string(kind)
        or pa.types.is_binary(kind)
    ):
        return ("dict", "plain", "delta_length", "delta_bytes")
    return ()


def cost(table: pa.Table, name: str, how: str) -> int | None:
    """Compressed bytes of one column chunk under one encoding, or None where pyarrow cannot write it."""
    options: dict[str, Any] = {
        "compression": "zstd",
        "store_schema": False,
        "use_dictionary": [name] if how == "dict" else False,
    }
    if how in BY_NAME:
        options["column_encoding"] = {name: BY_NAME[how]}
    sink = pa.BufferOutputStream()
    try:
        pq.write_table(table, sink, row_group_size=max(table.num_rows, 1), **options)
    except (pa.ArrowInvalid, pa.ArrowNotImplementedError, OSError):
        return None
    metadata = pq.ParquetFile(pa.BufferReader(sink.getvalue())).metadata
    return sum(
        metadata.row_group(g).column(0).total_compressed_size
        for g in range(metadata.num_row_groups)
    )


def measure(path: Path, table_name: str) -> list[dict[str, Any]]:
    """One entry per column with a choice of encoding."""
    f = pq.ParquetFile(path)
    metadata = f.metadata
    every = range(metadata.num_row_groups)
    sampled = list(every)
    if metadata.num_rows > TARGET:
        k = max(1, round(TARGET / (metadata.num_rows / len(sampled))))
        sampled = sorted(
            {round(i * (len(sampled) - 1) / max(k - 1, 1)) for i in range(k)}
        )
    found = []
    for c in range(metadata.num_columns):
        field = f.schema_arrow.field(c)
        if not (options := candidates(field.type)):
            continue
        chunks = [metadata.row_group(g).column(c) for g in every]
        actual = sum(chunk.total_compressed_size for chunk in chunks)
        chosen = chosen_of(
            {str(e) for chunk in chunks for e in (chunk.encodings or ())}
        )
        actual_sampled = sum(
            metadata.row_group(g).column(c).total_compressed_size for g in sampled
        )
        got = dict.fromkeys(options, 0)
        for g in sampled:
            part = f.read_row_group(g, columns=[field.name])
            for how in list(got):
                if (n := cost(part, field.name, how)) is None:
                    got.pop(how)
                else:
                    got[how] += n
        if chosen not in got:
            continue
        best = min(got, key=got.__getitem__)
        scale = actual / actual_sampled if actual_sampled else 1.0
        found.append(
            {
                "column": f"{table_name}.{field.name}",
                "type": str(field.type),
                "rows": metadata.num_rows,
                "chosen": chosen,
                "best": best,
                "actual": actual,
                "reproduced": got[chosen] / actual_sampled if actual_sampled else None,
                "ratio": got[chosen] / got[best] if got[best] else 1.0,
                "costs": {how: round(n * scale) for how, n in got.items()},
            }
        )
    return found


def _is_string(entry: dict[str, Any]) -> bool:
    return "string" in entry["type"] or "binary" in entry["type"]


def report(root: Path) -> int:
    """Print every column over `RATIO`, the count by kind, and the method check."""
    tables = root / "tables"
    found = []
    for path in sorted(tables.rglob("*.parquet")):
        found.extend(
            measure(path, ".".join(path.relative_to(tables).with_suffix("").parts))
        )
    print(
        f"{'column':56s} {'type':>10s} {'rows':>11s} {'chosen':>12s} {'bytes':>9s} "
        f"{'best':>12s} {'bytes':>9s} {'ratio':>6s}"
    )
    for entry in sorted(found, key=lambda e: -e["ratio"]):
        if entry["ratio"] >= RATIO:
            print(
                f"{entry['column']:56s} {entry['type'][:10]:>10s} {entry['rows']:11,d} "
                f"{entry['chosen']:>12s} {entry['costs'][entry['chosen']]:9,d} "
                f"{entry['best']:>12s} {entry['costs'][entry['best']]:9,d} {entry['ratio']:6.2f}"
            )
    for kind, part in (
        ("string", [e for e in found if _is_string(e)]),
        ("numeric", [e for e in found if not _is_string(e)]),
    ):
        bands = [
            sum(1 for e in part if e["ratio"] >= edge) for edge in (RATIO, 1.5, 2.0)
        ]
        print(
            f"\n{kind}: {len(part)} columns; {bands[0]} at {RATIO}x their best or more, "
            f"{bands[1]} at 1.5x, {bands[2]} at 2x"
        )
    print(
        "\nthe chosen encoding rewritten, over the file's own bytes, for every column over 1 MB:"
    )
    for entry in (e for e in found if e["actual"] > 1_000_000):
        print(
            f"  {entry['column']:54s} {entry['chosen']:>6s} {entry['reproduced']:.3f}  {entry['costs']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(
        report(Path(sys.argv[1])) if len(sys.argv) > 1 else print(__doc__) or 2
    )

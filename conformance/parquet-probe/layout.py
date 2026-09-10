"""What Parquet actually did with a committed packet's tables, per column.

R68 §1.3 is why this exists and how to read it: `core.media_frames.pts` was **96.9%** of its table
because a column declaring nothing else gets dictionary encoding, and a monotonic ramp of 7.5 M
values is its worst case. The writer chose that, not the format, so the gap closed without a
revision. Nothing here proposes a rule; it reports what a rebuild produced so the next such gap is
seen rather than assumed.

    python layout.py <packet root> [--top N]

Reports per table: rows, row groups, file size, and the columns that cost the most, with the
encodings each one actually got and its bits per row. Flags three shapes worth a look:

- **dict on a wide column** — a dictionary that is most of the column's own bytes, which is R68's
  case: the values are too distinct for the dictionary to pay for itself.
- **no delta on a sorted integer** — `DELTA_BINARY_PACKED` is defined for INT32/INT64 alone
  (R68 §2.3), so an ascending tick column not using it is leaving the floor unclaimed.
- **a row group under 8 K rows** — its footer statistics start to cost more than they prune.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow.parquet as pq

SMALL_GROUP = 8192


def _columns(f: pq.ParquetFile) -> dict[str, dict[str, object]]:
    """Per column: compressed and uncompressed bytes, and every encoding any row group used."""
    found: dict[str, dict[str, object]] = {}
    for g in range(f.metadata.num_row_groups):
        group = f.metadata.row_group(g)
        for c in range(group.num_columns):
            column = group.column(c)
            entry = found.setdefault(
                column.path_in_schema,
                {"compressed": 0, "uncompressed": 0, "encodings": set(), "dictionary": 0},
            )
            entry["compressed"] += column.total_compressed_size
            entry["uncompressed"] += column.total_uncompressed_size
            entry["encodings"].update(column.encodings or ())
            if column.dictionary_page_offset is not None and column.data_page_offset is not None:
                entry["dictionary"] += max(column.data_page_offset - column.dictionary_page_offset, 0)
    return found


#: Below this a dictionary page is unavoidable overhead rather than a choice, so the share it takes
#: says nothing: `core.calibrations` has three rows and every column's dictionary is most of it.
ENOUGH_ROWS = 10_000


def _flags(name: str, entry: dict[str, object], rows: int, groups: list[int]) -> list[str]:
    said = []
    compressed = int(entry["compressed"])
    if rows >= ENOUGH_ROWS and compressed and int(entry["dictionary"]) > compressed * 0.5:
        # R68 §1.3's shape: the values are distinct enough that the dictionary is as big as the
        # data it indexes, which is what a column declaring nothing else gets by default.
        said.append(f"dict is {int(entry['dictionary']) / compressed:.0%} of {compressed / 1e6:.2f}M")
    encodings = {str(e) for e in entry["encodings"]}
    # A tick ascends within its partition, which is what DELTA_BINARY_PACKED is for (R68 §2.3).
    # An `_index` does not -- `axis_index` cycles 0,1,2 per coordinate and `channel_index` per run --
    # so delta would encode a sawtooth and RLE is the right answer there.
    if name.endswith("_tick") and rows >= ENOUGH_ROWS and not any("DELTA" in e for e in encodings):
        said.append("no delta on an ascending integer")
    if groups and max(groups) < SMALL_GROUP and rows > SMALL_GROUP:
        said.append(f"row groups of {max(groups):,}")
    return said


def report(root: Path, top: int) -> int:
    files = sorted(root.rglob("*.parquet"))
    if not files:
        print(f"{root}: no parquet files")
        return 1
    print(f"{'table':44s} {'rows':>12s} {'groups':>7s} {'size':>10s}")
    print("-" * 78)
    flagged: list[str] = []
    for path in files:
        f = pq.ParquetFile(path)
        rows, size = f.metadata.num_rows, path.stat().st_size
        groups = [f.metadata.row_group(g).num_rows for g in range(f.metadata.num_row_groups)]
        name = str(path.relative_to(root))
        print(f"{name:44s} {rows:12,d} {len(groups):7d} {size / 1e6:9.2f}M")
        columns = _columns(f)
        widest = sorted(columns.items(), key=lambda kv: -int(kv[1]["compressed"]))[:top]
        for column, entry in widest:
            compressed = int(entry["compressed"])
            share = compressed / size * 100 if size else 0
            bits = compressed * 8 / rows if rows else 0
            encodings = ",".join(sorted(str(e).replace("Encoding.", "") for e in entry["encodings"]))
            print(f"    {column:38s} {share:5.1f}% {bits:7.2f} bits/row  {encodings}")
            for flag in _flags(column, entry, rows, groups):
                flagged.append(f"{name}.{column}: {flag}")
    if flagged:
        print(f"\n{len(flagged)} worth a look:")
        for line in flagged:
            print(f"  {line}")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--top=")), 4)
    raise SystemExit(report(Path(args[0]), n) if args else print(__doc__ or "") or 2)

"""Which readers decode each encoding a packet's columns may take, and what a string costs to read under each.

Part 03 §5.5 permits dictionary, RLE and delta encodings and requires a reader to support them; this
checks that against readers a consumer actually has. It writes one file per encoding from a committed
packet's own columns -- the string columns of `core.electrodes` and `core.units`, the integer columns
of `core.intervals` -- and compares what each reader returns with its own read of the plain file.
`readers.jl` reads the same directory from Julia, so run this first.

    uv run --with pyarrow --with duckdb --with polars --with fastparquet --with pandas \
        python readers.py <packet root> <scratch directory>
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

import duckdb
import fastparquet
import polars as pl
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

STRINGS = {
    "electrodes": ["electrode_name", "local_electrode_label", "local_channel_label"],
    "units": ["unit_name", "local_unit_label"],
}

BY_NAME = {
    "delta": "DELTA_BINARY_PACKED",
    "delta_length": "DELTA_LENGTH_BYTE_ARRAY",
    "delta_bytes": "DELTA_BYTE_ARRAY",
}


def write(table: pa.Table, path: Path, how: str) -> None:
    """One file with every column under one encoding, zstd on top."""
    options: dict[str, Any] = {"compression": "zstd", "use_dictionary": how == "dict"}
    if how in BY_NAME:
        options["column_encoding"] = dict.fromkeys(table.column_names, BY_NAME[how])
    pq.write_table(table, path, **options)


def files(packet: Path, out: Path) -> list[Path]:
    """Write the test files, named `<kind>-<table>-<encoding>.parquet`."""
    core = packet / "tables" / "core"
    for name, columns in STRINGS.items():
        table = pq.read_table(core / f"{name}.parquet", columns=columns)
        for how in ("plain", "dict", "delta_length", "delta_bytes"):
            write(table, out / f"strings-{name}-{how}.parquet", how)
    table = pq.read_table(core / "intervals.parquet")
    table = table.select([f.name for f in table.schema if pa.types.is_integer(f.type)])
    for how in ("plain", "dict", "delta"):
        write(table, out / f"integers-intervals-{how}.parquet", how)
    return sorted(out.glob("*.parquet"))


def _coded(path: Path) -> dict[str, list[Any]] | None:
    strings = [f.name for f in pq.read_schema(path) if pa.types.is_string(f.type)]
    return pq.read_table(path, read_dictionary=strings).to_pydict() if strings else None


def _fastparquet(path: Path) -> dict[str, list[Any]]:
    frame = fastparquet.ParquetFile(str(path)).to_pandas()
    return {column: frame[column].tolist() for column in frame.columns}


READERS: dict[str, Callable[[Path], dict[str, list[Any]] | None]] = {
    f"pyarrow {pa.__version__}": lambda p: pq.read_table(p).to_pydict(),
    "pyarrow read_dictionary": _coded,
    f"duckdb {duckdb.__version__}": lambda p: (
        duckdb.sql(f"select * from read_parquet('{p}')").to_arrow_table().to_pydict()
    ),
    f"polars {pl.__version__}": lambda p: pl.read_parquet(p).to_arrow().to_pydict(),
    f"fastparquet {version('fastparquet')}": _fastparquet,
}


def decoding(paths: list[Path]) -> None:
    """Print, per file and reader, whether the values match that reader's read of the plain file."""
    for label, read in READERS.items():
        print(label)
        for path in paths:
            plain = path.with_name(path.name.rsplit("-", 1)[0] + "-plain.parquet")
            try:
                got, truth = read(path), read(plain)
                result = "n/a" if got is None else "ok" if got == truth else "WRONG"
            except Exception as exc:  # noqa: BLE001 -- a reader's failure is the finding
                result = f"FAIL {type(exc).__name__}: {str(exc)[:70]}"
            print(f"  {path.stem:32s} {result}")


def scale(packet: Path, out: Path, rows: int = 1_000_000) -> None:
    """Size and read time of a million unique ascending names, as an assigned `*_name` column holds."""
    names = (
        pq.read_table(packet / "tables/core/units.parquet", columns=["unit_name"])
        .column(0)
        .combine_chunks()
    )
    copies = [
        pc.binary_join_element_wise(names, pa.scalar(f"{i:04d}"), "|")
        for i in range(rows // len(names) + 1)
    ]
    table = (
        pa.table({"unit_name": pa.concat_arrays(copies)})
        .slice(0, rows)
        .sort_by("unit_name")
    )
    probe = table.column(0)[rows // 8].as_py()
    con = duckdb.connect()

    def best(fn: Callable[[], Any]) -> float:
        times = []
        for _ in range(5):
            start = time.perf_counter()
            fn()
            times.append(time.perf_counter() - start)
        return min(times) * 1000

    print(
        f"\n{'encoding':14s} {'bytes':>10s} {'pyarrow':>9s} {'polars':>9s} {'duckdb =':>9s}"
    )
    for how in ("dict", "plain", "delta_length", "delta_bytes"):
        path = out / f"scale-{how}.parquet"
        options: dict[str, Any] = {
            "compression": "zstd",
            "use_dictionary": how == "dict",
        }
        if how in BY_NAME:
            options["column_encoding"] = {"unit_name": BY_NAME[how]}
        pq.write_table(table, path, row_group_size=rows, **options)
        chunk = (
            pq.ParquetFile(path).metadata.row_group(0).column(0).total_compressed_size
        )
        query = (
            f"select count(*) from read_parquet('{path}') where unit_name = '{probe}'"
        )
        print(
            f"{how:14s} {chunk:10,d} {best(lambda: pq.read_table(path)):7.1f}ms "
            f"{best(lambda: pl.read_parquet(path)):7.1f}ms {best(lambda: con.sql(query).fetchone()):7.1f}ms"
        )
        path.unlink()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(print(__doc__) or 2)
    packet, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    decoding(files(packet, out))
    scale(packet, out)

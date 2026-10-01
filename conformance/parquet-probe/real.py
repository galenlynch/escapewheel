"""Physical settings for the spike table, measured on real spikes rather than synthetic ones.

`delta.py` answered the same question against 500 units firing uniformly. Real spiking is
bursty and real amplitudes are not noise, so the encodings that win are not obviously the
same ones. This reads a slice of a committed packet and rewrites it under each candidate.

Run it from a directory on real disk: writing several copies of a 20M-row slice into a
tmpfs scratch directory is how you fill RAM without noticing.
"""

import os
import sys
import time

import pyarrow.parquet as pq

SOURCE = (
    sys.argv[1]
    if len(sys.argv) > 1
    else ("/mnt/Data/escapewheel/packets/ecephys_837772_2026-06-27_experiment1/tables/core/spike_events.parquet")
)
ROWS = 20_000_000
STRINGS = ["session_id", "unit_id", "sorting_run_id", "curation_id", "clock_id"]

# A column cannot carry both a dictionary and an explicit encoding, so `use_dictionary` has
# to name every column that should keep one. Naming only the strings silently drops
# amplitude's dictionary, which is what made an early run look as though BYTE_STREAM_SPLIT
# tripled the column -- it was measuring the loss of the dictionary, not the new encoding.
KEEP_DICT = [*STRINGS, "amplitude"]

CONFIGS = {
    "as written (dictionary, zstd)": {"use_dictionary": True},
    "delta t_tick, dict amplitude": {
        "use_dictionary": KEEP_DICT,
        "column_encoding": {"t_tick": "DELTA_BINARY_PACKED"},
    },
    "delta t_tick, split amplitude": {
        "use_dictionary": STRINGS,
        "column_encoding": {
            "t_tick": "DELTA_BINARY_PACKED",
            "amplitude": "BYTE_STREAM_SPLIT",
        },
    },
    "delta t_tick, plain amplitude": {
        "use_dictionary": STRINGS,
        "column_encoding": {"t_tick": "DELTA_BINARY_PACKED"},
    },
    "delta + dict, zstd level 9": {
        "use_dictionary": KEEP_DICT,
        "column_encoding": {"t_tick": "DELTA_BINARY_PACKED"},
        "compression_level": 9,
    },
    "delta + dict, 4M row groups": {
        "use_dictionary": KEEP_DICT,
        "column_encoding": {"t_tick": "DELTA_BINARY_PACKED"},
        "row_group_size": 4_000_000,
    },
}


def main() -> None:
    source = pq.ParquetFile(SOURCE)
    batches = []
    seen = 0
    for batch in source.iter_batches(batch_size=1 << 20):
        batches.append(batch)
        seen += batch.num_rows
        if seen >= ROWS:
            break
    import pyarrow as pa

    slice_ = pa.Table.from_batches(batches)
    units = sorted({u for u in slice_.column("unit_id").slice(0, 200_000).to_pylist()})[:24]
    print(f"{slice_.num_rows:,d} rows from {os.path.basename(SOURCE)}")
    print(f"probing with {len(units)} units, as a region's would be\n")
    print(
        f"{'configuration':32s} {'MB':>8s} {'vs':>6s} {'t_tick':>8s} {'amp':>7s} "
        f"{'write':>7s} {'scan':>7s} {'filter':>7s}"
    )

    baseline = None
    for name, kw in CONFIGS.items():
        path = f"probe_{abs(hash(name))}.parquet"
        start = time.perf_counter()
        pq.write_table(slice_, path, compression="zstd", **kw)
        wrote = time.perf_counter() - start

        size = os.path.getsize(path)
        baseline = baseline or size
        meta = pq.ParquetFile(path).metadata
        names = [meta.row_group(0).column(i).path_in_schema for i in range(meta.num_columns)]
        per = {
            n: sum(meta.row_group(g).column(i).total_compressed_size for g in range(meta.num_row_groups))
            for i, n in enumerate(names)
        }

        start = time.perf_counter()
        pq.read_table(path, columns=["t_tick"])
        scan = time.perf_counter() - start

        import pyarrow.compute as pc
        import pyarrow.dataset as ds

        start = time.perf_counter()
        ds.dataset(path).to_table(filter=pc.field("unit_id").isin(units), columns=["unit_id", "t_tick"])
        filt = time.perf_counter() - start

        print(
            f"{name:32s} {size / 1e6:>8.1f} {size / baseline * 100:>5.0f}% "
            f"{per['t_tick'] / 1e6:>8.1f} {per.get('amplitude', 0) / 1e6:>7.1f} "
            f"{wrote:>6.1f}s {scan:>6.2f}s {filt:>6.2f}s"
        )
        os.remove(path)


if __name__ == "__main__":
    main()

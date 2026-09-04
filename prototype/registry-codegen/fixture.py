"""Write two packets: one conforming, one with deliberate defects.

The broken packet is the generator's test: each defect must be caught by exactly the
check that covers it, and nothing else must fail.
"""
import sys
from datetime import UTC, datetime
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

TS = pa.timestamp("us", tz="UTC")


def write(out: Path, name: str, table: pa.Table):
    out.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out / f"{name}.parquet", compression="zstd")


#: The kind these intervals are, as R54 §2.1 requires: a dotted resource ID naming the table
#: that specialises them. This packet does not carry it, which R54 §2.4a makes an error -- the
#: generator here does not implement the discriminator checks R55 §2.4 adds, and the limits
#: section says so rather than the fixture pretending otherwise.
KIND = "dynamic_foraging.trials"

I32 = pa.int32()


def sessions():
    return pa.table({"session_id": pa.array([1], I32), "subject_id": pa.array([1], I32),
                     "session_start_time": pa.array([datetime(2026, 1, 5, 9, 30, tzinfo=UTC)], type=TS),
                     "reference_clock_id": pa.array([1], I32)})


def clocks():
    """Two clocks, so the nullable self-reference has both a null and a value to guard."""
    return pa.table({"clock_id": pa.array([1, 2], I32), "session_id": pa.array([1, 1], I32),
                     "name": ["Neuropixels AP sample clock", "behaviour counter"],
                     "tick_rate_hz": [30000.0, 1000.0],
                     "origin": ["sample 0 at acquisition start", "first behaviour tick"],
                     "parent_clock_id": pa.array([None, 1], I32)})


def valid(out: Path):
    write(out, "core_sessions", sessions())
    write(out, "core_clocks", clocks())
    write(out, "core_intervals", pa.table({
        "session_id":    pa.array([1, 1, 1], I32),
        "interval_kind": [KIND] * 3,
        "interval_id":   pa.array([1, 2, 3], I32),
        "start_tick":    [1000, 6000, 11000],
        "stop_tick":     [5000, 10000, 15000],
        "clock_id":      pa.array([1, 1, 1], I32)}))


def broken(out: Path):
    """Three defects: a duplicate key, an unresolvable clock, an inverted interval."""
    write(out, "core_sessions", sessions())
    write(out, "core_clocks", clocks())
    write(out, "core_intervals", pa.table({
        "session_id":    pa.array([1, 1, 1, 1], I32),
        "interval_kind": [KIND] * 4,
        "interval_id":   pa.array([1, 1, 3, 4], I32),
        "start_tick":    [1000, 2000, 9000, 4000],
        "stop_tick":     [5000, 6000, 7000, 8000],
        "clock_id":      pa.array([1, 1, 1, 99], I32)}))


if __name__ == "__main__":
    here = Path(__file__).parent
    valid(here / "packets" / "valid")
    broken(here / "packets" / "broken")
    print("wrote packets/valid and packets/broken", file=sys.stderr)

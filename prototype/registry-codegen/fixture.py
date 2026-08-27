"""Write two packets: one conforming, one with deliberate defects.

The broken packet is the generator's test: each defect must be caught by exactly the
check that covers it, and nothing else must fail.
"""
import sys
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

TS = pa.timestamp("us", tz="UTC")


def write(out: Path, name: str, table: pa.Table):
    out.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out / f"{name}.parquet", compression="zstd")


def sessions():
    return pa.table({"session_id": ["s001"], "subject_id": ["m001"],
                     "session_start_time": pa.array([None], type=TS)})


def clocks():
    return pa.table({"clock_id": ["imec_s001"], "session_id": ["s001"],
                     "tick_rate_hz": [30000.0],
                     "origin": ["sample 0 at acquisition start"]})


def valid(out: Path):
    write(out, "core_sessions", sessions())
    write(out, "core_clocks", clocks())
    write(out, "core_trials", pa.table({
        "session_id": ["s001", "s001", "s001"],
        "trial_id":   ["t1", "t2", "t3"],
        "start_tick": [1000, 6000, 11000],
        "stop_tick":  [5000, 10000, 15000],
        "clock_id":   ["imec_s001"] * 3,
        "probe_id":   ["p0", None, None]}))


def broken(out: Path):
    """Three defects: a duplicate key, an unresolvable clock, an inverted interval."""
    write(out, "core_sessions", sessions())
    write(out, "core_clocks", clocks())
    write(out, "core_trials", pa.table({
        "session_id": ["s001", "s001", "s001", "s001"],
        "trial_id":   ["t1", "t1", "t3", "t4"],
        "start_tick": [1000, 2000, 9000, 4000],
        "stop_tick":  [5000, 6000, 7000, 8000],
        "clock_id":   ["imec_s001", "imec_s001", "imec_s001", "behavior_s001"],
        "probe_id":   ["p0", None, None, None]}))


if __name__ == "__main__":
    here = Path(__file__).parent
    valid(here / "packets" / "valid")
    broken(here / "packets" / "broken")
    print("wrote packets/valid and packets/broken", file=sys.stderr)

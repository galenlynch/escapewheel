"""Convert an NWB-Zarr directory to an NWB-HDF5 file, for the HDF5 arms of the comparison.

uv run python to_hdf5.py SOURCE.nwb DEST.nwb

pynwb exports the Zarr file's contents unchanged and uncompressed, since HDF5 cannot read Blosc,
and `h5repack` then compresses every dataset with shuffle and gzip, the filters a stock HDF5 build
carries and so the ones an NWB-HDF5 file a user is handed carries too.
"""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

#: gzip level for every dataset: the level h5py and pynwb examples use.
GZIP_LEVEL = 4


def export(source: Path, dest: Path) -> None:
    from hdmf_zarr.nwb_zarrv2 import NWBZarrV2IO
    from pynwb import NWBHDF5IO

    # An AIND NWB-Zarr stores its object-reference columns with the pickle codec.
    with NWBZarrV2IO(str(source), "r", allow_pickle=True) as read_io, NWBHDF5IO(str(dest), "w") as write_io:
        write_io.export(src_io=read_io, write_args={"link_data": False})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="the NWB-Zarr directory")
    parser.add_argument("dest", type=Path, help="the NWB-HDF5 file to write")
    args = parser.parse_args()
    raw = args.dest.with_suffix(".raw.nwb")
    start = time.perf_counter()
    export(args.source, raw)
    print(f"exported {raw.stat().st_size / 1e9:.2f} GB in {time.perf_counter() - start:.0f} s", flush=True)
    start = time.perf_counter()
    subprocess.run(["h5repack", "-f", "SHUF", "-f", f"GZIP={GZIP_LEVEL}", str(raw), str(args.dest)], check=True)
    print(f"repacked {args.dest.stat().st_size / 1e9:.2f} GB in {time.perf_counter() - start:.0f} s", flush=True)
    raw.unlink()


if __name__ == "__main__":
    main()

"""Build the Phase 0 fixture packets.

A conforming single-session packet per R1 §6, plus variants each violating exactly one
rule. Table schemas are taken from the registry rather than restated, so a fixture cannot
drift from the specification it is meant to exercise.

`corpus_packets` declares the packets, and this writes each of them under `packets/`.
"""

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# A caller that loads this file by path has not put its directory on the import path.
sys.path.insert(0, str(HERE))

from corpus_packets import PACKETS
from corpus_packets.session import VALID, content


def main():
    root = HERE / "packets"
    # A packet dropped from the table would otherwise leave its last build behind.
    if root.exists():
        shutil.rmtree(root)
    for packet in PACKETS:
        packet.build(root / packet.name)
        written = f"{sum(len(v) for v in content().values()):>5d} rows" if packet is VALID else "written"
        print(f"{packet.name:26s}{written}")


if __name__ == "__main__":
    main()

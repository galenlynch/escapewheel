# Escapewheel benchmarks

Scripts that measure what reading a packet costs, against the NWB it was built beside and
against other layouts of its own tables. They produce the readings Part 10 and the writer's
performance guide quote. Nothing here is a package or a test: `bench/` is not released, so it
depends on the reader by path, and no script runs in `verify.py`.

## Setup

```bash
cd bench
uv sync
```

Every script takes its paths as arguments, or from the environment variable its `--help`
names. None has a default path.

## Cold reads need a native filesystem

A cold cell evicts its stores from the page cache with `posix_fadvise`, which needs no
privilege, then checks with `mincore` that the eviction took. On a FUSE mount such as
ntfs-3g, the file's pages are dropped but the block device's buffer cache keeps the bytes, so
the read is still warm. `benchkit.cold_child` therefore refuses a FUSE mount. Copy the
packet and the NWB to the disk you mean to measure first:

```bash
cp -a /path/to/packet /nvme/bench/packet
cp -a /path/to/session.nwb /nvme/bench/session.nwb
```

Each cell runs in its own process. Peak RSS is that process's alone, and the reader's modules
are imported before the clock starts.

## Scripts

| script | question | inputs |
|---|---|---|
| `readers.py` | One session read cold four ways: the packet through PyArrow and through DuckDB, and the NWB through pynwb and through lazynwb. The operations are opening the store, unit metadata, trials, every spike, a ten-second window and one unit's train. | `--packet`, `--nwb` |
| `row_groups.py` | Cold reads of `analysis.spike_events` at several row-group sizes, for a one-second window and for one unit over the whole session. | `--packet`, `--scratch` |
| `containment.py` | Which block holds each trial: a range join, an ASOF join, a binary search, or a stored key, at four scales. | none; the data is synthetic |
| `benchkit.py` | Shared helpers: path resolution, eviction and its check, child processes, and the environment record. | |

Each script prints a table and, with `--json-out`, writes the same numbers with the date,
commit, CPU, disk model, filesystem and library versions. The packet's core version is recorded
too.

```bash
uv run python readers.py --packet /nvme/bench/packet --nwb /nvme/bench/session.nwb \
    --repeat 3 --json-out results/$(date +%F)-readers-<session>.json
uv run python row_groups.py --packet /nvme/bench/packet --scratch /nvme/bench/rowgroups \
    --json-out results/$(date +%F)-row-groups-<session>.json
uv run python containment.py --json-out results/$(date +%F)-containment.json
```

## Results

`results/` holds one JSON file per run, named by date, and
[`results/history.md`](results/history.md). The history table carries every reading quoted
anywhere in the repository, with what it was measured on and whether its script survives.
A reading taken against an older packet shape stays there, with its date, after the script
that produced it has gone.

## Adding a benchmark

- Take every path as an argument or from the environment, and refuse a missing one.
- Measure each cold cell in a fresh process through `benchkit.cold_child`.
- Give the readers the same question, and print what each returned, so that a disagreement
  shows up beside the timing.
- Write the result with `benchkit.environment`, and add its numbers to `results/history.md`.

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
are imported before the clock starts. An arm that loads every spike into pandas can need tens of
gigabytes, so `trials.py --memory-max` runs each cell in a systemd user scope that is killed, not
swapped, at that size; such a cell is reported as killed at the cap. Some of its NWB arms take
tens of minutes a run over S3, so `--once-above SECONDS` stops repeating a cell after a run that
long; each cell records how many runs its median is of.

## Scripts

| script | question | inputs |
|---|---|---|
| `readers.py` | One session read cold four ways: the packet through PyArrow and through DuckDB, and the NWB through pynwb and through lazynwb. The operations are opening the store, unit metadata, trials, every spike, a ten-second window, one unit's train, and the units in one region with their trains. | `--packet`, `--nwb`, either a path or an `s3://` URI |
| `trials.py` | Two trial analyses read cold every way each store's readers offer: per trial, the first lick after the go cue; and for every unit, the spikes within [-1, +2] s of each go cue. The arms load each needed table whole into pandas, work out of core through Polars or a PyArrow dataset, state it in SQL, or call a reader's own alignment helper. Each prints the counts it found, and the run groups the arms that disagree. | `--packet`, `--nwb`, either a path or an `s3://` URI; `--memory-max` |
| `row_groups.py` | Cold reads of `analysis.spike_events` at several row-group sizes, for a one-second window and for one unit over the whole session, from local disk or from a store. | `--packet`, `--scratch`; for a store, `--store-packet`, `--store-scratch` |
| `stores.py` | Listing a stored packet or NWB, and downloading it to local disk, in seconds and objects. | `--root NAME=URI`, `--stage-dir` |
| `build.py` | What importing one recipe costs at several source-worker counts: wall time, peak RSS, and when each source's turn and each later step began. Each cell writes a fresh packet; the writer stages beside it, so `--out-root` is the scratch disk measured. | `--recipe`, `--out-root` |
| `containment.py` | Which block holds each trial: a range join, an ASOF join, a binary search, or a stored key, at four scales. | none; the data is synthetic |
| `benchkit.py` | Shared helpers: path resolution, eviction and its check, child processes, and the environment record. | |

Each script prints a table and, with `--json-out`, writes the same numbers with the date,
commit, CPU, disk model, filesystem and library versions. The packet's core version is recorded
too.

```bash
uv run python readers.py --packet /nvme/bench/packet --nwb /nvme/bench/session.nwb \
    --repeat 3 --json-out results/$(date +%F)-readers-<session>.json
uv run python trials.py --packet /nvme/bench/packet --nwb /nvme/bench/session.nwb \
    --repeat 3 --memory-max 80G --json-out results/$(date +%F)-trials-<session>.json
uv run python row_groups.py --packet /nvme/bench/packet --scratch /nvme/bench/rowgroups \
    --json-out results/$(date +%F)-row-groups-<session>.json
uv run python containment.py --json-out results/$(date +%F)-containment.json
uv run python build.py --recipe /data/recipe.toml --out-root /nvme/bench/build --workers 1 4 \
    --json-out results/$(date +%F)-build-<session>.json
```

## Reading from a store

A store URI needs no eviction: each cell's process is fresh and holds no client cache. Such a
cell records the bytes the host received during it instead, so run it on a quiet machine. The
four clients each find credentials their own way, so export one set into the environment first:

```bash
eval "$(aws configure export-credentials --format env)"
uv run python readers.py --packet s3://bucket/prefix/packet --nwb s3://bucket/prefix/session.nwb \
    --repeat 3 --json-out results/$(date +%F)-readers-<session>-s3.json
```

lazynwb recognises a stored NWB-Zarr only by `.zarr` in its URI, so stage the NWB under a name
ending `.nwb.zarr`; without it every lazynwb cell fails with a 404 on the root. pynwb reads the
same copy, so `trials.py` takes that name for every arm. The result records
the store's region, the network interface and its link speed, but not where
the bucket sits relative to the machine; say so beside the numbers in `results/history.md`.

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

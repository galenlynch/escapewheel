"""What every benchmark here shares: paths from the caller, cold reads, child processes, a record.

A cold measurement runs in its own process, so its peak RSS is its own and no import or cache
from an earlier one is shared. The page cache is evicted with `posix_fadvise(DONTNEED)`, which
needs no privilege but is honoured only by a filesystem whose pages the kernel owns. On a FUSE
mount such as ntfs-3g the file's pages go and the block device's buffer cache keeps the bytes,
so `mincore` reports the file evicted and the read is still warm. `cold_child` therefore
refuses a FUSE mount outright, and elsewhere refuses a store `resident_fraction` finds resident.

A store named by an `s3://` URI is cold by construction, since a fresh process holds no client
cache. Its cell records the bytes the host received instead, which counts anything else the host
fetched meanwhile, so a remote run wants a quiet machine.
"""

from __future__ import annotations

import ctypes
import json
import mmap
import os
import platform
import resource
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

#: Share of a store's pages allowed to stay resident after eviction.
RESIDENT_LIMIT = 0.01

#: URI schemes read through an object store rather than the page cache.
REMOTE = ("s3://",)

#: Packages whose versions a result records.
VERSIONED = (
    "escapewheel-reader",
    "duckdb",
    "pyarrow",
    "polars",
    "numpy",
    "zarr",
    "pynwb",
    "hdmf-zarr",
    "h5py",
    "remfile",
    "lazynwb",
)

_libc = ctypes.CDLL(None, use_errno=True)
_libc.mmap.restype = ctypes.c_void_p
_libc.mmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long)
_libc.munmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
_libc.mincore.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_ubyte))
_MAP_FAILED = ctypes.c_void_p(-1).value


def is_remote(store: str | Path) -> bool:
    """Whether a store is an object-store URI."""
    return str(store).startswith(REMOTE)


def is_hdf5(store: str | Path) -> bool:
    """Whether an NWB is one HDF5 file rather than a Zarr directory."""
    if not is_remote(store):
        return Path(store).is_file()
    from pyarrow import fs

    filesystem, key = fs.FileSystem.from_uri(str(store))
    return filesystem.get_file_info(key).type == fs.FileType.File


def open_nwb(store: str | Path):
    """pynwb's NWBFile from an NWB-HDF5 file or an NWB-Zarr directory, local or on S3.

    Remote HDF5 streams through `remfile`, the reader pynwb's streaming guide recommends.
    """
    store = str(store)
    if is_hdf5(store):
        import h5py
        from pynwb import NWBHDF5IO

        if is_remote(store):
            import remfile

            bucket, _, key = store.removeprefix("s3://").partition("/")
            store = remfile.File(f"https://{bucket}.s3.amazonaws.com/{key}")
        return NWBHDF5IO(file=h5py.File(store, "r"), mode="r").read()
    from hdmf_zarr.nwb_zarrv2 import NWBZarrV2IO

    # An AIND NWB-Zarr stores its object-reference columns with the pickle codec.
    options = {"anon": anonymous()} if is_remote(store) else None
    return NWBZarrV2IO(store, "r", allow_pickle=True, storage_options=options).read()


def anonymous() -> bool:
    """Whether to read a store unsigned: no credentials are exported, so the bucket must be public."""
    return not os.environ.get("AWS_ACCESS_KEY_ID")


def duckdb_s3_secret(region: str) -> str:
    """DuckDB's S3 secret: the environment's credentials where exported, else unsigned, for a public bucket."""
    if not anonymous():
        return f"CREATE SECRET store (TYPE s3, PROVIDER credential_chain, CHAIN 'env', REGION '{region}')"
    return f"CREATE SECRET store (TYPE s3, REGION '{region}')"


def required_store(value: str | None, variable: str, what: str) -> str:
    """Resolve a local path or an object-store URI; a URI is checked by the first read of it."""
    raw = value or os.environ.get(variable)
    if raw and is_remote(raw):
        return raw.rstrip("/")
    return str(required_path(value, variable, what))


def interface() -> str | None:
    """The network interface of the default route, or `BENCH_INTERFACE`."""
    if os.environ.get("BENCH_INTERFACE"):
        return os.environ["BENCH_INTERFACE"]
    for line in Path("/proc/net/route").read_text().splitlines()[1:]:
        fields = line.split()
        if fields[1] == "00000000":
            return fields[0]
    return None


def received_bytes() -> int | None:
    """Bytes the host has received on its default interface."""
    name = interface()
    try:
        return int(Path(f"/sys/class/net/{name}/statistics/rx_bytes").read_text())
    except (OSError, TypeError, ValueError):
        return None


def required_path(value: str | None, variable: str, what: str) -> Path:
    """Resolve a path from an argument, else the environment, and refuse a missing one."""
    raw = value or os.environ.get(variable)
    if not raw:
        sys.exit(f"name {what} with an argument or {variable}")
    path = Path(raw).expanduser()
    if not path.exists():
        sys.exit(f"{what} {path} does not exist")
    return path


def files_under(root: Path) -> Iterable[Path]:
    """Every regular file in a tree, or the path itself when it is a file."""
    if root.is_file():
        yield root
        return
    for directory, _, names in os.walk(root):
        for name in names:
            path = Path(directory, name)
            if path.is_file() and not path.is_symlink():
                yield path


def store_objects(store: str) -> list[tuple[str, int]]:
    """Every object under one known store prefix, with its size, by one listing of that prefix."""
    from pyarrow import fs

    filesystem, prefix = fs.FileSystem.from_uri(store)
    one = filesystem.get_file_info(prefix)
    if one.type == fs.FileType.File:
        return [(one.path, one.size)]
    found = filesystem.get_file_info(fs.FileSelector(prefix, recursive=True))
    return [(info.path, info.size) for info in found if info.type == fs.FileType.File]


def tree_bytes(root: str | Path) -> int:
    """Bytes held by a tree's regular files, or by the objects under a store prefix."""
    if is_remote(root):
        return sum(size for _, size in store_objects(str(root)))
    return sum(path.stat().st_size for path in files_under(Path(root)))


def evict(root: Path) -> None:
    """Ask the kernel to drop a tree's cached pages."""
    for path in files_under(root):
        try:
            fd = os.open(path, os.O_RDONLY)
        except OSError:
            continue
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)


def _resident(path: Path) -> tuple[int, int]:
    """Resident and total pages of one file, by `mincore` over a shared read-only mapping."""
    size = path.stat().st_size
    if size == 0:
        return 0, 0
    pages = -(-size // mmap.PAGESIZE)
    fd = os.open(path, os.O_RDONLY)
    try:
        address = _libc.mmap(None, size, mmap.PROT_READ, mmap.MAP_SHARED, fd, 0)
        if address in (None, _MAP_FAILED):
            raise OSError(ctypes.get_errno(), f"mmap failed on {path}")
        try:
            vector = (ctypes.c_ubyte * pages)()
            if _libc.mincore(address, size, vector) != 0:
                raise OSError(ctypes.get_errno(), f"mincore failed on {path}")
            return sum(byte & 1 for byte in vector), pages
        finally:
            _libc.munmap(address, size)
    finally:
        os.close(fd)


def resident_fraction(root: Path) -> float:
    """Share of a tree's pages in the page cache."""
    resident = total = 0
    for path in files_under(root):
        here, pages = _resident(path)
        resident += here
        total += pages
    return resident / total if total else 0.0


def peak_mib() -> float:
    """This process's peak RSS; Linux reports `ru_maxrss` in KiB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def filesystem(path: Path) -> str:
    """The type of the filesystem holding a path, as `findmnt` names it."""
    found = subprocess.run(["findmnt", "-n", "-o", "FSTYPE", "--target", str(path)], capture_output=True, text=True)
    return found.stdout.strip() or "?"


def cold_child(
    stores: Iterable[str | Path], operation: Callable[[], object], summarise: Callable[[object], object] | None = None
) -> None:
    """Evict the local stores, confirm it, time one operation, and print the result as JSON.

    `summarise` reduces the operation's result to the value printed, after the clock stops.
    """
    stores = [Path(store) for store in stores if not is_remote(store)]
    for store in stores:
        if filesystem(store).startswith("fuse"):
            sys.exit(f"{store} is on a FUSE mount, where eviction leaves the bytes cached; copy it to a native one")
        evict(store)
    for store in stores:
        left = resident_fraction(store)
        if left > RESIDENT_LIMIT:
            sys.exit(f"{store} is still {left:.1%} resident after eviction; this filesystem ignores it")
    before = received_bytes()
    clock = time.perf_counter()
    value = operation()
    elapsed = time.perf_counter() - clock
    after = received_bytes()
    received = after - before if before is not None and after is not None else None
    value = summarise(value) if summarise is not None else value
    print(json.dumps({"seconds": elapsed, "peak_mib": peak_mib(), "received_bytes": received, "value": str(value)}))


def run_child(arguments: list[str], memory_max: str | None = None) -> dict:
    """Run this interpreter on a child invocation and parse the JSON line it printed last.

    `memory_max`, a systemd size such as `64G`, runs the child in a user scope that is killed
    rather than swapped at that size, so one cell cannot take the host's memory.
    """
    command = [sys.executable, *arguments]
    if memory_max:
        limit = ["-p", f"MemoryMax={memory_max}", "-p", "MemorySwapMax=0"]
        command = ["systemd-run", "--user", "--scope", "--quiet", *limit, "--", *command]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    if memory_max and done.returncode in (-9, 137):
        return {"error": f"killed at the {memory_max} memory cap"}
    lines = done.stdout.strip().splitlines()
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        reason = (done.stderr.strip().splitlines() or ["no output"])[-1]
        return {"error": reason[:200]}


def _git_commit() -> str:
    """The checkout's commit, with a mark when its tree differs from it."""
    here = Path(__file__).parent
    commit = subprocess.run(["git", "rev-parse", "--short=8", "HEAD"], cwd=here, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain", "--", ".."], cwd=here, capture_output=True, text=True)
    return commit.stdout.strip() + ("+dirty" if dirty.stdout.strip() else "")


def _cpu() -> str:
    """The CPU model, from `/proc/cpuinfo`."""
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor()


def _disk(path: Path) -> dict:
    """The filesystem holding a path, and the model and rotation of the disk under it."""
    found = subprocess.run(
        ["findmnt", "-n", "-o", "SOURCE,FSTYPE", "--target", str(path)], capture_output=True, text=True
    ).stdout.split()
    source, fstype = (found + ["?", "?"])[:2]
    device = source.split("[")[0]
    parent = subprocess.run(["lsblk", "-n", "-d", "-o", "PKNAME", device], capture_output=True, text=True)
    disk = "/dev/" + parent.stdout.strip() if parent.stdout.strip() else device
    described = subprocess.run(["lsblk", "-n", "-d", "-o", "MODEL,ROTA", disk], capture_output=True, text=True)
    words = described.stdout.split()
    return {
        "path": str(path),
        "filesystem": fstype,
        "device": device,
        "model": " ".join(words[:-1]) if words else "?",
        "rotational": words[-1] == "1" if words else None,
    }


def _remote(store: str) -> dict:
    """An object store's URI and region, and the interface and link speed it is read over."""
    import botocore.session

    name = interface()
    try:
        speed = int(Path(f"/sys/class/net/{name}/speed").read_text())
    except (OSError, TypeError, ValueError):
        speed = None
    return {
        "path": store,
        "region": os.environ.get("AWS_REGION") or botocore.session.Session().get_config_variable("region"),
        "interface": name,
        "link_mbps": speed,
    }


def environment(stores: Iterable[str | Path]) -> dict:
    """Date, commit, hardware and versions, for the head of a result."""
    versions = {}
    for name in VERSIONED:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "commit": _git_commit(),
        "cpu": _cpu(),
        "cores": os.cpu_count(),
        "memory_gib": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30),
        "kernel": platform.release(),
        # Other work on the host slows every cell, so a result records how busy it was.
        "load_average": [round(load, 2) for load in os.getloadavg()],
        "python": platform.python_version(),
        "disks": [_remote(str(store)) if is_remote(store) else _disk(Path(store)) for store in stores],
        "versions": versions,
    }


def core_version(packet: str | Path) -> str | None:
    """The core registry version a packet's manifest binds."""
    if is_remote(packet):
        from pyarrow import fs

        filesystem, key = fs.FileSystem.from_uri(f"{packet}/packet.json")
        with filesystem.open_input_stream(key) as handle:
            manifest = json.loads(handle.read())
    else:
        manifest = json.loads((Path(packet) / "packet.json").read_text())
    return manifest.get("registries", {}).get("core", {}).get("version")


def write_result(path: Path | None, result: dict) -> None:
    """Write a result as JSON where asked; the table on stdout is the same numbers."""
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n")

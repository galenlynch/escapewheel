"""What every benchmark here shares: paths from the caller, cold reads, child processes, a record.

A cold measurement runs in its own process, so its peak RSS is its own and no import or cache
from an earlier one is shared. The page cache is evicted with `posix_fadvise(DONTNEED)`, which
needs no privilege but is honoured only by a filesystem whose pages the kernel owns. On a FUSE
mount such as ntfs-3g the file's pages go and the block device's buffer cache keeps the bytes,
so `mincore` reports the file evicted and the read is still warm. `cold_child` therefore
refuses a FUSE mount outright, and elsewhere refuses a store `resident_fraction` finds resident.
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

#: Packages whose versions a result records.
VERSIONED = ("escapewheel-reader", "duckdb", "pyarrow", "polars", "numpy", "zarr", "pynwb", "hdmf-zarr", "lazynwb")

_libc = ctypes.CDLL(None, use_errno=True)
_libc.mmap.restype = ctypes.c_void_p
_libc.mmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long)
_libc.munmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
_libc.mincore.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_ubyte))
_MAP_FAILED = ctypes.c_void_p(-1).value


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


def tree_bytes(root: Path) -> int:
    """Bytes held by a tree's regular files."""
    return sum(path.stat().st_size for path in files_under(root))


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


def cold_child(stores: Iterable[Path], operation: Callable[[], object]) -> None:
    """Evict the stores, confirm it, time one operation, and print the result as JSON."""
    stores = list(stores)
    for store in stores:
        if filesystem(store).startswith("fuse"):
            sys.exit(f"{store} is on a FUSE mount, where eviction leaves the bytes cached; copy it to a native one")
        evict(store)
    for store in stores:
        left = resident_fraction(store)
        if left > RESIDENT_LIMIT:
            sys.exit(f"{store} is still {left:.1%} resident after eviction; this filesystem ignores it")
    clock = time.perf_counter()
    value = operation()
    elapsed = time.perf_counter() - clock
    print(json.dumps({"seconds": elapsed, "peak_mib": peak_mib(), "value": str(value)}))


def run_child(arguments: list[str]) -> dict:
    """Run this interpreter on a child invocation and parse the JSON line it printed last."""
    done = subprocess.run([sys.executable, *arguments], capture_output=True, text=True, check=False)
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


def environment(stores: Iterable[Path]) -> dict:
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
        "python": platform.python_version(),
        "disks": [_disk(store) for store in stores],
        "versions": versions,
    }


def core_version(packet: Path) -> str | None:
    """The core registry version a packet's manifest binds."""
    manifest = json.loads((packet / "packet.json").read_text())
    return manifest.get("registries", {}).get("core", {}).get("version")


def write_result(path: Path | None, result: dict) -> None:
    """Write a result as JSON where asked; the table on stdout is the same numbers."""
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n")

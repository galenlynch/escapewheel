"""A read-only Zarr store over a PyArrow filesystem, so an array is reached as its packet's tables are.

- :class:`ArrowStore` -- the store, rooted at one array's prefix.

Handing Zarr a URI makes it resolve the store through fsspec, with its own credential chain and a
backend this package does not depend on, so an array a table beside it reads fine could be
unreachable. Needs the ``arrays`` extra; nothing else imports this module without it.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import AsyncIterator, Iterable, Sequence
from typing import Any

from pyarrow import fs
from zarr.abc.store import ByteRequest, OffsetByteRequest, RangeByteRequest, Store, SuffixByteRequest
from zarr.core.buffer import Buffer, BufferPrototype

#: Open files kept per store. Opening costs an object store a HEAD request, and a sharded array
#: reads each shard's index and then its chunks from the same file.
OPEN_FILES = 64


class ArrowStore(Store):
    """An array's prefix on a PyArrow filesystem, read-only.

    Open files are kept and shared between reads: packet bytes are immutable (Part 03 §8.1), and a
    PyArrow random-access file reads at an offset safely from several threads.
    """

    supports_writes = False
    supports_deletes = False
    supports_partial_writes = False
    supports_listing = True

    def __init__(self, filesystem: fs.FileSystem, root: str) -> None:
        """Bind the store to `root`, a path on `filesystem` with no scheme.

        Parameters
        ----------
        filesystem : pyarrow.fs.FileSystem
            The filesystem reaching the packet, as :meth:`Location.store` returns it.
        root : str
            The array's directory on that filesystem.
        """
        super().__init__(read_only=True)
        self.filesystem = filesystem
        self.root = root.rstrip("/")
        self._file = functools.lru_cache(maxsize=OPEN_FILES)(self._open_file)

    def __eq__(self, other: object) -> bool:
        """Two stores are equal when they read the same prefix through equal filesystems."""
        return isinstance(other, ArrowStore) and (self.filesystem, self.root) == (other.filesystem, other.root)

    def __hash__(self) -> int:
        """Hash by prefix, consistently with equality."""
        return hash(self.root)

    def __repr__(self) -> str:
        """Name the filesystem and the prefix."""
        return f"ArrowStore({self.filesystem.type_name}://{self.root})"

    def __getstate__(self) -> dict[str, Any]:
        """Drop the open files, which do not pickle, so a store crosses to a worker process."""
        state = dict(self.__dict__)
        del state["_file"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore a pickled store with no files open."""
        self.__dict__.update(state)
        self._file = functools.lru_cache(maxsize=OPEN_FILES)(self._open_file)

    def _path(self, key: str) -> str:
        """Return the key's path on the filesystem."""
        return f"{self.root}/{key}" if key else self.root

    def _open_file(self, key: str) -> Any:
        """Open the key for reads at an offset; kept, through `_file`."""
        return self.filesystem.open_input_file(self._path(key))

    def _read(self, key: str, byte_range: ByteRequest | None) -> bytes | None:
        """Read the key or the range of it, blocking; None where it is absent.

        A whole read streams, which costs an object store one request; a range opens the file,
        which costs a HEAD the first time.
        """
        try:
            if byte_range is None:
                with self.filesystem.open_input_stream(self._path(key)) as stream:
                    whole: bytes = stream.read()
                return whole
            file = self._file(key)
        except FileNotFoundError:
            return None
        size = file.size()
        if isinstance(byte_range, RangeByteRequest):
            start, stop = byte_range.start, min(byte_range.end, size)
        elif isinstance(byte_range, OffsetByteRequest):
            start, stop = byte_range.offset, size
        elif isinstance(byte_range, SuffixByteRequest):
            start, stop = max(0, size - byte_range.suffix), size
        else:
            raise TypeError(f"unexpected byte range {byte_range!r}")
        part: bytes = file.read_at(max(0, stop - start), start)
        return part

    async def get(self, key: str, prototype: BufferPrototype, byte_range: ByteRequest | None = None) -> Buffer | None:
        """Read one key, or a range of it; None where the key is absent."""
        found = await asyncio.to_thread(self._read, key, byte_range)
        return None if found is None else prototype.buffer.from_bytes(found)

    async def get_partial_values(
        self, prototype: BufferPrototype, key_ranges: Iterable[tuple[str, ByteRequest | None]]
    ) -> list[Buffer | None]:
        """Read several keys or ranges concurrently."""
        return list(await asyncio.gather(*(self.get(key, prototype, request) for key, request in key_ranges)))

    async def exists(self, key: str) -> bool:
        """Whether the key is present."""
        info = await asyncio.to_thread(self.filesystem.get_file_info, self._path(key))
        return bool(info.type != fs.FileType.NotFound)

    async def set(self, key: str, value: Buffer) -> None:
        """Refuse: a packet is read-only."""
        raise PermissionError(f"{self!r} is read-only")

    async def delete(self, key: str) -> None:
        """Refuse: a packet is read-only."""
        raise PermissionError(f"{self!r} is read-only")

    async def list(self) -> AsyncIterator[str]:
        """Yield every key under the array's prefix."""
        for key in await asyncio.to_thread(self._keys, "", True):
            yield key

    async def list_prefix(self, prefix: str) -> AsyncIterator[str]:
        """Yield every key starting with `prefix`."""
        for key in await asyncio.to_thread(self._keys, "", True):
            if key.startswith(prefix):
                yield key

    async def list_dir(self, prefix: str) -> AsyncIterator[str]:
        """Yield the names directly under `prefix`, keys and directories alike."""
        for key in await asyncio.to_thread(self._keys, prefix.rstrip("/"), False):
            yield key.rpartition("/")[2]

    def _keys(self, prefix: str, recursive: bool) -> Sequence[str]:
        """Return the keys under the array's own prefix, relative to it; never wider than one array."""
        selector = fs.FileSelector(self._path(prefix), recursive=recursive, allow_not_found=True)
        infos = self.filesystem.get_file_info(selector)
        return [
            info.path.removeprefix(self.root).lstrip("/")
            for info in infos
            if recursive is False or info.type == fs.FileType.File
        ]


__all__ = ["OPEN_FILES", "ArrowStore"]

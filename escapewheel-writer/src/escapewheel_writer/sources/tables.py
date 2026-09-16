"""Resources that already exist as files, optionally produced by a command first.

The least coupled way to supply a resource, and the one an extension should reach for. An
extension needs no Python at all this way: a registry document names its tables, Parquet files
hold their rows, and neither imports anything of ours. Nothing to install and so nothing to rot,
which is the failure `ndx-` extensions demonstrate on the read path and which a registered source
adapter would reproduce on the write path.

Where the raw source needs converting, `command` runs first. It is a plain argument list run in
`root` -- **not** a shell, and carried as a list rather than split from a string (Part 05 §3.7),
with no opinion about how the environment is arranged. That is
deliberate: `uv run export.py` and `python -m package.export` and `/opt/venv/bin/python -m …` are
all just commands, so isolating an adapter's dependencies is the recipe author's choice rather
than a tool this package requires anyone to adopt.

Rows arrive as names, not numbers. Part 05 §8 assigns identifiers packet-wide before anything is
staged, so a process outside this one cannot know them and does not need to: it writes
`session_id` as `"ecephys_776259"` and the writer turns that into an `int32`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import pyarrow as pa
import pyarrow.parquet as pq

from .nwb import SourceDefect
from .store import source_root

#: Rows per batch. Matched to `session.BATCH_ROWS` rather than imported, so a source does not
#: depend on the driver that happens to run it.
BATCH_ROWS = 1_000_000


class TablesSource:
    """One or more resources, each read from a Parquet file.

    Parameters
    ----------
    root : str or Path
        Directory the paths are relative to, and the working directory `command` runs in.
    session_id : str
        Accepted for the shape every adapter has; the rows carry their own.
    tables : Mapping
        Resource ID to the Parquet file holding it, relative to `root`.
    command : sequence of str, optional
        Run once before reading, as an argument list rather than through a shell (Part 05 §3.7).
        A non-zero exit is a `SourceDefect`, because a half-written export is worse than none.
    batch_rows : int, optional
        Rows per batch. A file is streamed rather than read whole: an extension's table may be
        as large as a core one, and R2 §7's own reason for the streaming path applies here.
    """

    #: Part 05 §3.4's exception: empty, because what this source supplies is named by the recipe
    #: entry and is not a property of the adapter at all.
    PRODUCES: frozenset[str] = frozenset()

    #: Part 05 §3.4: recipe fields this adapter states, to the attribute holding each. Declared
    #: empty rather than omitted, because a build refuses a source it cannot ask.
    STATES: ClassVar[dict[str, str]] = {}

    #: Part 05 §3.4: what a build must supply, resolved against Part 03 §11.2's terms first and the
    #: recipe's options second. A name resolving to neither is refused before any source is opened.
    #:
    #: An option the adapter can run without is left out: a declared name a recipe does not set
    #: resolves to nothing, so declaring one makes it mandatory.
    NEEDS: ClassVar[tuple[str, ...]] = ("root", "session_id")

    #: Part 05 §3.4: options this adapter reads and can run without, which a recipe may leave
    #: unset (Part 03 §11.2). `tables` is among them rather than in `NEEDS` because a recipe
    #: naming no table is refused by this adapter with what is wrong, not by a missing name.
    ACCEPTS: ClassVar[tuple[str, ...]] = ("tables", "command", "batch_rows")

    #: Part 05 §3.4: the kinds whose output this adapter reads, which is what orders a build.
    CONSUMES: ClassVar[tuple[str, ...]] = ()

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str,
        tables: Mapping[str, str] | None = None,
        command: Sequence[str] | None = None,
        batch_rows: int = BATCH_ROWS,
    ) -> None:
        self.root = source_root(root)
        self.session_id = session_id
        if isinstance(command, str):
            # Part 05 §3.7 forbids deriving a list by splitting a string: a parse is a quoting
            # convention the recipe never declared, and POSIX rules eat a backslash on every host.
            raise SourceDefect(
                f"command must be an argument list, not {command!r}; write it as a TOML array"
            )
        self.command = list(command) if command is not None else None
        self.batch_rows = batch_rows
        self.notes: list[str] = []
        if not tables:
            raise SourceDefect("a tables source declares no tables; give it resource = path")
        self.tables = {resource: self.root / path for resource, path in tables.items()}
        self._ran = False

    def _prepare(self) -> None:
        """Run `command`, once, and check it produced what it claimed."""
        if self._ran:
            return
        self._ran = True
        if self.command is not None:
            try:
                subprocess.run(self.command, cwd=self.root, check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                raise SourceDefect(f"{self.command!r} failed: {exc}") from None
            self.notes.append(f"ran {self.command!r} in {self.root}")
        if missing := sorted(r for r, path in self.tables.items() if not path.is_file()):
            raise SourceDefect(
                f"{', '.join(missing)}: no file at the declared path"
                + (f" after running {self.command!r}" if self.command else "")
            )

    def offers(self) -> dict[str, int]:
        """Part 05 Stage 1: how many rows of each resource. Read from the footer, not the data."""
        self._prepare()
        return {resource: pq.ParquetFile(path).metadata.num_rows for resource, path in self.tables.items()}

    def records(self) -> dict[str, list[dict[str, Any]]]:
        """Nothing. Every table here streams through `batches`, which is why this is empty."""
        return {}

    def batches(self) -> dict[str, Iterator[pa.RecordBatch]]:
        """Each resource as a stream of Arrow batches, in the order the file holds them.

        Order is the file's own. Part 03 §5.3's sort is applied by the writer where a table comes
        through the records path, and checked by the validator's physical-order shim either way
        (R12 §4) -- so a file in the wrong order is a finding rather than a silent acceptance.
        """
        self._prepare()
        return {
            resource: pq.ParquetFile(path).iter_batches(batch_size=self.batch_rows)
            for resource, path in self.tables.items()
        }


__all__ = ["BATCH_ROWS", "TablesSource"]

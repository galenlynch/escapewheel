"""Where bytes are: a local directory or a prefix in an object store.

A packet's own resources travel because each is a **name** resolved against a root the reader
supplies when it opens the packet, and Part 00 §3.3 names three forms that root may take -- a local
directory, an object-store prefix, or a release manifest pointing at distributed assets.
Resolving it as a filesystem path admits only the first, which is what this exists to fix.

Two things are kept apart here that the manifest's `uri` field runs together. A **location** is
somewhere bytes can be fetched from. A declared URI is what the packet says, which is a location
only once a root and any caller-supplied substitution have been applied to it.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

from .errors import ManifestError, ResourceUnreadableError, UnresolvedSource

#: A substitution a caller supplies at open time: declared URI prefix to replacement.
#:
#: Part 04 §5.1 makes an external resource's reachability a property of the reader's situation, and
#: a packet already committed records one situation -- the writer's. Substituting a prefix is
#: how a reader reaches the same bytes from somewhere else without touching bytes Part 04 §5.1
#: makes immutable. `git config url.<base>.insteadOf` is the same mechanism.
Rewrite = Mapping[str, str]

#: A source resolution document's `sources` block, flattened to name -> URI (Part 04 §5.5).
Sources = Mapping[str, str]

#: Where a writer SHOULD leave a default resolution document (Part 04 §5.5). Not a packet resource,
#: so nothing in the manifest names it and Part 04 §5.1's immutability does not reach it.
SOURCES_FILENAME = "sources.json"

#: The one version of that document this reader knows how to read.
SOURCES_VERSION = "escapewheel-sources-v0.1"


def read_sources(where: Location) -> dict[str, str]:
    """Parse a source resolution document, returning its name-to-URI mapping.

    Parameters
    ----------
    where : Location
        The document itself, local or in a store.

    Returns
    -------
    dict
        Source name to URI.

    Raises
    ------
    ManifestError
        If the document is unparsable, or declares a version this reader does not know. R80
        §2.2 makes refusing an unknown version the rule: reading it as if it were this one is
        how a location silently becomes wrong.
    """
    try:
        parsed = json.loads(where.read_bytes())
    except Exception as exc:
        raise ManifestError(f"{where} is not a readable source resolution document: {exc}") from exc
    declared = parsed.get("sources_standard_version")
    if declared != SOURCES_VERSION:
        raise ManifestError(f"{where} declares {declared!r}, and this reader knows {SOURCES_VERSION!r}")
    return {name: str(entry["uri"]) for name, entry in (parsed.get("sources") or {}).items()}


def _scheme(uri: str) -> str:
    """Return the URI's scheme, reading a single letter as a Windows drive rather than one."""
    scheme = urlparse(uri).scheme
    return "" if len(scheme) <= 1 else scheme


@functools.lru_cache(maxsize=32)
def _filesystem(store: str) -> tuple[Any, str]:
    """Resolve a store URI to a pyarrow filesystem, once per store.

    Resolving costs a request -- pyarrow asks S3 which region a bucket is in -- so a packet
    with 28 tables in one bucket must not pay it 28 times.

    **Credentials are deliberately not set.** Part 04 §5.1 makes reachability the caller's
    situation, so this takes whatever the filesystem's own default chain finds.
    """
    from pyarrow.fs import FileSystem

    filesystem, path = FileSystem.from_uri(store)
    return filesystem, path


@dataclass(frozen=True)
class Location:
    """One place bytes can be read from, and the substitutions a caller asked for.

    The rewrite travels with the location so that resolving a declared URI needs nothing but
    the root, which is already threaded through every resource handle.
    """

    uri: str
    rewrite: tuple[tuple[str, str], ...] = field(default=())
    sources: tuple[tuple[str, str], ...] = field(default=())

    @classmethod
    def of(
        cls,
        where: str | Path | Location,
        rewrite: Rewrite | None = None,
        sources: Sources | None = None,
    ) -> Location:
        """Read a root as a location, whatever form the caller had it in.

        Parameters
        ----------
        where : str, Path, or Location
            A local directory, a `file:` URI, or a store prefix such as `s3://bucket/prefix`.
        rewrite : Mapping, optional
            Declared-URI prefix to replacement, applied by :meth:`resolve`. Longest prefix
            wins, so a specific mapping may sit inside a general one.

        Returns
        -------
        Location
            The root, with any substitutions attached.
        """
        found = tuple((sources or {}).items())
        if isinstance(where, Location):
            if rewrite is None and sources is None:
                return where
            return cls(where.uri, cls._order(rewrite) if rewrite else where.rewrite, found or where.sources)
        text = str(where)
        rules = cls._order(rewrite) if rewrite else ()
        if _scheme(text) == "file":
            return cls(str(Path(unquote(urlparse(text).path))), rules, found)
        return cls(text.rstrip("/") if _scheme(text) else text, rules, found)

    @staticmethod
    def _order(rewrite: Rewrite) -> tuple[tuple[str, str], ...]:
        """Longest prefix first, so the most specific rule is the one that fires."""
        return tuple(sorted(rewrite.items(), key=lambda pair: len(pair[0]), reverse=True))

    @property
    def scheme(self) -> str:
        """The store's scheme, empty for a local path."""
        return _scheme(self.uri)

    @property
    def is_local(self) -> bool:
        """Whether these bytes are reachable as a filesystem path."""
        return not self.scheme

    @property
    def path(self) -> Path:
        """The filesystem path, for a local location only.

        Raises
        ------
        ResourceUnreadableError
            If the location is in a store, which has no local path.
        """
        if not self.is_local:
            raise ResourceUnreadableError(
                f"{self.uri} is {self.scheme}:, which has no local path; read it through the store"
            )
        return Path(self.uri)

    def join(self, relative: str) -> Location:
        """Resolve a relative name under this location.

        Parameters
        ----------
        relative : str
            A path relative to this location.

        Returns
        -------
        Location
            The named place.
        """
        if self.is_local:
            return Location(str(Path(self.uri) / relative), self.rewrite, self.sources)
        return Location(f"{self.uri.rstrip('/')}/{relative.lstrip('/')}", self.rewrite, self.sources)

    def resolve(self, declared: str, source: str | None = None) -> Location:
        """Where a manifest's declared URI points from here.

        Substitution comes first, so a caller may redirect an absolute URI as well as a
        relative one. A resource naming a `source` (Part 04 §5.5) is then relative to wherever that
        source resolves; one that does not is relative to this root where it has no scheme,
        which is what makes a packet portable (Part 03 §4).

        Parameters
        ----------
        declared : str
            The `uri` field of a manifest resource entry.
        source : str, optional
            The entry's `source`, naming the body of data it belongs to.

        Returns
        -------
        Location
            Where to read it.

        Raises
        ------
        UnresolvedSource
            If `source` is named and no resolution document locates it (Part 04 §5.5).
        """
        if source is not None:
            located = dict(self.sources).get(source)
            if located is None:
                known = ", ".join(sorted(dict(self.sources))) or "none"
                raise UnresolvedSource(f"no resolution document locates source {source!r}; this reader has: {known}")
            return Location(located, self.rewrite, self.sources).resolve(declared)
        for prefix, replacement in self.rewrite:
            if declared.startswith(prefix):
                declared = replacement + declared[len(prefix) :]
                break
        scheme = _scheme(declared)
        if scheme == "file":
            return Location(str(Path(unquote(urlparse(declared).path))), self.rewrite, self.sources)
        if scheme:
            return Location(declared, self.rewrite, self.sources)
        if PurePosixPath(declared).is_absolute():
            # An absolute path is where it says, not somewhere under the root -- which matters
            # most for a packet in a store, where joining would produce `s3://bucket//mnt/...`.
            return Location(declared, self.rewrite, self.sources)
        return self.join(declared)

    def store(self) -> tuple[str, Any]:
        """Return what every PyArrow entry point takes: a path and the filesystem reaching it.

        A local location resolves to a path and no filesystem, which those entry points
        already accept.

        Returns
        -------
        tuple
            The path, and the filesystem or None.

        Raises
        ------
        ResourceUnreadableError
            If the URI names a scheme pyarrow cannot open.
        """
        if self.is_local:
            return self.uri, None
        head, _, _ = self.uri.partition("://")
        netloc = urlparse(self.uri).netloc
        try:
            filesystem, _ = _filesystem(f"{head}://{netloc}")
        except Exception as exc:
            raise ResourceUnreadableError(f"cannot reach {self.uri}: {exc}") from exc
        return f"{netloc}{urlparse(self.uri).path}", filesystem

    def exists(self) -> bool:
        """Whether anything is here.

        Returns
        -------
        bool
            True if a file or directory answers at this location.
        """
        if self.is_local:
            return Path(self.uri).exists()
        from pyarrow.fs import FileType

        path, filesystem = self.store()
        try:
            return bool(filesystem.get_file_info(path).type != FileType.NotFound)
        except Exception:  # noqa: BLE001 - what an unreachable store raises is its own business
            return False

    def read_bytes(self) -> bytes:
        """Read this location's contents.

        Returns
        -------
        bytes
            What is stored here.
        """
        if self.is_local:
            return Path(self.uri).read_bytes()
        path, filesystem = self.store()
        with filesystem.open_input_file(path) as handle:
            data: bytes = handle.readall()
        return data

    def __str__(self) -> str:
        """Return the URI, which is what a message about this location should show."""
        return self.uri


__all__ = ["SOURCES_FILENAME", "SOURCES_VERSION", "Location", "Rewrite", "Sources", "read_sources"]

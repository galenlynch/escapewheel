"""Where bytes are: a local directory or a prefix in an object store (Part 00 §3.3).

- :class:`Location` -- one place bytes can be read from, with any caller-supplied rewrite.
- :func:`read_sources`, :func:`check_sources`, :func:`sources_schema` -- read and check a source
  resolution document (Part 04 §5.5).

A declared `uri` is what the packet says; it becomes a location only once a root and any rewrite
are applied to it.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

import jsonschema

from .errors import ResourceUnreadableError, SourcesError, UnresolvedSource
from .uri import decode, is_absolute

#: A substitution a caller supplies at open time: declared URI prefix to replacement.
#:
#: Part 04 §5.1 makes an external resource's reachability a property of the reader's situation, and
#: a packet already committed records one situation -- the writer's. Substituting a prefix is
#: how a reader reaches the same bytes from somewhere else without touching bytes Part 03 §8.1
#: makes immutable. `git config url.<base>.insteadOf` is the same mechanism.
Rewrite = Mapping[str, str]

#: A source resolution document's `sources` block, flattened to name -> URI (Part 04 §5.5).
Sources = Mapping[str, str]

#: Where a writer SHOULD leave a default resolution document (Part 04 §5.5). Not a packet resource,
#: so nothing in the manifest names it and Part 03 §8.1's immutability does not reach it.
SOURCES_FILENAME = "sources.json"

#: The one version of that document this reader knows how to read.
SOURCES_VERSION = "escapewheel-sources-v0.1"


def sources_schema() -> dict[str, Any]:
    """Load the bundled JSON Schema for a source resolution document (Part 04 §5.5).

    Copied from the specification's tree, because a wheel cannot read a file outside its package.

    Returns
    -------
    dict
        The parsed schema.
    """
    text = importlib_resources.files(__package__).joinpath("schemas/sources.schema.json").read_text()
    parsed: dict[str, Any] = json.loads(text)
    return parsed


@functools.cache
def _sources_validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(sources_schema())


def check_sources(document: Any) -> tuple[str, ...]:
    """Return where and how a parsed source resolution document fails its schema (Part 04 §5.5).

    Parameters
    ----------
    document : Any
        The parsed document.

    Returns
    -------
    tuple of str
        One ``<JSON path>: <message>`` per failure, empty when the document satisfies the schema.
    """
    failures = sorted(_sources_validator().iter_errors(document), key=lambda error: list(map(str, error.path)))
    return tuple(f"{error.json_path}: {error.message}" for error in failures)


def read_sources(where: Location) -> dict[str, str]:
    """Parse and validate a source resolution document, returning its name-to-URI mapping.

    The version is checked before the schema: Part 04 §5.5 forbids resolving through an unknown
    version whether or not a reader validates, so that refusal must not depend on the schema's
    ``const``.

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
    SourcesError
        If the document is unparsable, declares a version this reader does not know, or fails
        the schema, naming each place it fails.
    """
    try:
        parsed = json.loads(where.read_bytes())
    except Exception as exc:
        raise SourcesError(f"{where} is not a readable source resolution document: {exc}") from exc
    declared = parsed.get("sources_standard_version") if isinstance(parsed, Mapping) else None
    if declared != SOURCES_VERSION:
        raise SourcesError(f"{where} declares {declared!r}, and this reader knows {SOURCES_VERSION!r}")
    failures = check_sources(parsed)
    if failures:
        raise SourcesError(f"{where} does not satisfy the source resolution schema: " + "; ".join(failures))
    return {name: str(entry["uri"]) for name, entry in parsed["sources"].items()}


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

    def append(self, names: Sequence[str]) -> Location:
        """Place names under this location, each as one path component or object-key segment.

        Parameters
        ----------
        names : sequence of str
            Decoded names, as :func:`escapewheel_reader.uri.decode` returns them.

        Returns
        -------
        Location
            The named place.
        """
        if self.is_local:
            return Location(str(Path(self.uri).joinpath(*names)), self.rewrite, self.sources)
        return Location("/".join((self.uri.rstrip("/"), *names)), self.rewrite, self.sources)

    def resolve(self, declared: str, source: str | None = None) -> Location:
        """Where a manifest's declared URI points from here.

        Substitution comes first, so a caller may redirect an absolute URI as well as a
        relative one, and what it substitutes is taken as written. A resource naming a `source`
        (Part 04 §5.5) is then relative to wherever that source resolves; one that does not is
        relative to this root unless absolute, which is what makes a packet portable. A relative
        reference is decoded and its names appended, never merged under RFC 3986, Section 5
        (Part 03 §4).

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
        ResourceUnreadableError
            If `declared` is neither absolute nor a relative reference, such as a path beginning
            with `/` or one with a `..` segment, so it names no place under the root.
        """
        if source is not None:
            located = dict(self.sources).get(source)
            if located is None:
                known = ", ".join(sorted(dict(self.sources))) or "none"
                raise UnresolvedSource(
                    f"no resolution document locates source {source!r}; this reader has: {known}", source=source
                )
            return Location(located, self.rewrite, self.sources).resolve(declared)
        for prefix, replacement in self.rewrite:
            if declared.startswith(prefix):
                return self._substituted(replacement + declared[len(prefix) :])
        if is_absolute(declared):
            return self._substituted(declared)
        try:
            names = decode(declared)
        except ValueError as exc:
            raise ResourceUnreadableError(f"{declared!r} is neither absolute nor a relative reference: {exc}") from exc
        return self.append(names)

    def _substituted(self, where: str) -> Location:
        """Resolve an absolute URI, or what a caller's substitution produced, as spelled."""
        scheme = _scheme(where)
        if scheme == "file":
            return Location(str(Path(unquote(urlparse(where).path))), self.rewrite, self.sources)
        if scheme:
            return Location(where, self.rewrite, self.sources)
        if PurePosixPath(where).is_absolute():
            # An absolute path is where it says, not somewhere under the root -- which matters
            # most for a packet in a store, where joining would produce `s3://bucket//mnt/...`.
            return Location(where, self.rewrite, self.sources)
        return self.join(where)

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
        # Everything after the scheme is the key, so a `?` or `#` a decoded name holds stays in it.
        head, _, key = self.uri.partition("://")
        netloc = key.partition("/")[0]
        try:
            filesystem, _ = _filesystem(f"{head}://{netloc}")
        except Exception as exc:
            raise ResourceUnreadableError(f"cannot reach {self.uri}: {exc}") from exc
        return key, filesystem

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


__all__ = [
    "SOURCES_FILENAME",
    "SOURCES_VERSION",
    "Location",
    "Rewrite",
    "Sources",
    "check_sources",
    "read_sources",
    "sources_schema",
]

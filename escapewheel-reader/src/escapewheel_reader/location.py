"""Where bytes are: a local directory or a prefix in an object store (Part 00 §3.3).

- :class:`Location` -- one place bytes can be read from, with the resolution documents it ranks.
- :class:`SourcesDocument`, :class:`Resolution`, :class:`Located` -- one resolution document, the
  ranked set of them, and where one resource was found and through what.
- :func:`read_document`, :func:`read_sources`, :func:`check_sources`, :func:`sources_schema` --
  read and check a source resolution document.
- :func:`resolve_sources` -- rank the documents Part 04 §5.5 names for one packet.

A declared `uri` is what the packet says; it becomes a location only once a root, a source and any
mirror are applied to it.
"""

from __future__ import annotations

import functools
import json
import os
import re
import threading
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import jsonschema

from .errors import ResourceUnreadableError, SourcesError, UnresolvedSource
from .uri import decode, is_absolute

#: A caller's mirrors given as a mapping: mirror prefix to the location standing for it.
#:
#: Read as a resolution document holding only `mirrors`, ranked before every other document, so a
#: caller redirects an absolute location without touching bytes Part 03 §8.1 makes immutable.
Rewrite = Mapping[str, str]

#: A caller's sources given as a mapping: source name to URI.
Sources = Mapping[str, str]

#: Where a writer SHOULD leave a default resolution document (Part 04 §5.5). Not a packet resource,
#: so nothing in the manifest names it and it may be corrected after the packet is committed.
SOURCES_FILENAME = "sources.json"

#: The version a writer writes (Part 04 §5.5).
SOURCES_VERSION = "escapewheel-sources-v0.2"

#: Every version this reader reads.
SOURCES_VERSIONS = frozenset({SOURCES_VERSION, "escapewheel-sources-v0.1"})

#: The reader's configuration (Part 04 §5.5's second rank): resolution document locations, separated
#: by `os.pathsep`, consulted in the order listed and before :func:`user_sources`.
SOURCES_ENVIRONMENT = "ESCAPEWHEEL_SOURCES"


def user_sources() -> Path:
    """Return the per-user resolution document, ranked after :data:`SOURCES_ENVIRONMENT`'s.

    `%APPDATA%/escapewheel/sources.json` on Windows, and `$XDG_CONFIG_HOME/escapewheel/sources.json`
    elsewhere, `$XDG_CONFIG_HOME` defaulting to `~/.config`.
    """
    if os.name == "nt" and (appdata := os.environ.get("APPDATA")):
        return Path(appdata) / "escapewheel" / SOURCES_FILENAME
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "escapewheel" / SOURCES_FILENAME


def configured_sources() -> list[str]:
    """Return the configuration's resolution document locations, in rank (Part 04 §5.5)."""
    listed = [where for where in os.environ.get(SOURCES_ENVIRONMENT, "").split(os.pathsep) if where]
    return [*listed, str(user_sources())]


def sources_schema() -> dict[str, Any]:
    """Load the bundled JSON Schema for a source resolution document.

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


def read_document(where: Location) -> SourcesDocument:
    """Parse and validate a source resolution document (Part 04 §5.5).

    The version is checked before the schema: Part 04 §5.5 forbids resolving through an unknown
    version whether or not a reader validates, so that refusal must not depend on the schema's enum.

    Parameters
    ----------
    where : Location
        The document itself, local or in a store.

    Returns
    -------
    SourcesDocument
        Its sources and mirrors, with the directory or prefix holding it.

    Raises
    ------
    FileNotFoundError
        If nothing is there.
    SourcesError
        If the document is unparsable, declares a version this reader does not know, fails the
        schema, or holds two equal mirror prefixes, naming each place it fails.
    """
    try:
        raw = where.read_bytes()
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise SourcesError(f"{where} is not a readable source resolution document: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise SourcesError(f"{where} is not a readable source resolution document: {exc}") from exc
    declared = parsed.get("sources_standard_version") if isinstance(parsed, Mapping) else None
    if declared not in SOURCES_VERSIONS:
        known = ", ".join(repr(v) for v in sorted(SOURCES_VERSIONS))
        raise SourcesError(f"{where} declares {declared!r}, and this reader knows {known}")
    failures = check_sources(parsed)
    if failures:
        raise SourcesError(f"{where} does not satisfy the source resolution schema: " + "; ".join(failures))
    return SourcesDocument.of(
        str(where),
        where.parent(),
        {name: str(entry["uri"]) for name, entry in parsed.get("sources", {}).items()},
        {prefix: str(entry["uri"]) for prefix, entry in parsed.get("mirrors", {}).items()},
    )


def read_sources(where: Location) -> dict[str, str]:
    """Parse and validate a source resolution document, returning its `sources` as name to URI.

    Raises
    ------
    SourcesError
        As :func:`read_document` does, and where nothing is there.
    """
    try:
        return dict(read_document(where).sources)
    except FileNotFoundError as exc:
        raise SourcesError(f"no source resolution document at {where}") from exc


def _scheme(uri: str) -> str:
    """Return the URI's scheme, reading a single letter as a Windows drive rather than one."""
    scheme = urlparse(uri).scheme
    return "" if len(scheme) <= 1 else scheme


@functools.lru_cache(maxsize=32)
def _filesystem(store: str) -> tuple[Any, str]:
    """Resolve a store URI to a pyarrow filesystem, once per store.

    Resolving costs a request -- pyarrow asks S3 which region a bucket is in -- so a packet
    with 28 tables in one bucket must not pay it 28 times.

    **Credentials are deliberately not set.** Reachability is the caller's situation, so this
    takes whatever the filesystem's own default chain finds.
    """
    from pyarrow.fs import FileSystem

    filesystem, path = FileSystem.from_uri(store)
    return filesystem, path


#: A location as Part 04 §5.5.1 compares it: its kind, the scheme's authority or the drive or UNC
#: server (already lowercased), and its decoded names.
_Key = tuple[str, str, tuple[str, ...]]

_DRIVE = re.compile(r"^([A-Za-z]):[\\/]")
_URI = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]+):(.*)$", re.DOTALL)
_DRIVE_NAME = re.compile(r"^[A-Za-z]:$")
_SEPARATORS = re.compile(r"[\\/]")


def _key(text: str) -> _Key | None:
    """Read an absolute URI or absolute path as Part 04 §5.5.1 compares it, or None where it is neither.

    A `file:` URI is the path it names (RFC 8089, Section 2 and Appendix E): with an empty or
    `localhost` authority, a Windows path where its first name is a drive letter and a POSIX path
    otherwise; with any other authority, a UNC path on that server. A device path names nothing.
    """
    if text.startswith(("\\\\?\\", "\\\\.\\")):
        return None
    if drive := _DRIVE.match(text):
        return ("windows", drive[1].lower() + ":", tuple(n for n in _SEPARATORS.split(text[3:]) if n))
    if text.startswith("\\\\"):
        server, *shared = _SEPARATORS.split(text[2:])
        return ("windows", "\\\\" + server.lower(), tuple(n for n in shared if n)) if server else None
    if text.startswith("/"):
        return ("posix", "", tuple(n for n in text.split("/") if n))
    uri = _URI.match(text)
    if uri is None:
        return None
    scheme, rest = uri[1].lower(), uri[2]
    authority, path = rest[2:].partition("/")[::2] if rest.startswith("//") else ("", rest)
    try:
        names = tuple(unquote(n, errors="strict") for n in path.split("/") if n)
    except UnicodeDecodeError:
        return None
    if scheme != "file":
        return (scheme, authority.lower(), names)
    if authority.lower() not in ("", "localhost"):
        return ("windows", "\\\\" + authority.lower(), names)
    if names and _DRIVE_NAME.match(names[0]):
        return ("windows", names[0].lower(), names[1:])
    return ("posix", "", names)


def _begins(prefix: _Key, location: _Key) -> bool:
    """Whether a mirror prefix begins a location (Part 04 §5.5.1)."""
    return prefix[:2] == location[:2] and location[2][: len(prefix[2])] == prefix[2]


#: Whether this reader runs on Windows, where a Windows path names a location and a POSIX path none.
_WINDOWS = os.name == "nt"


def _here(key: _Key) -> bool:
    """Whether a location of this kind names a place for this reader (Part 04 §5.5.2)."""
    return key[0] != ("posix" if _WINDOWS else "windows")


@dataclass(frozen=True)
class SourcesDocument:
    """One source resolution document (Part 04 §5.5), as a reader ranks it.

    Attributes
    ----------
    where : str
        Its location, or a label for one the caller supplied as a mapping.
    base : Location or None
        The directory or prefix holding it, against which a relative `uri` resolves; None for a
        document stored at no location, where a relative or empty `uri` names nothing.
    sources : tuple of (str, str)
        Source name to `uri`.
    mirrors : tuple of (str, str)
        Mirror prefix to `uri`.
    default : bool
        Whether it is the packet's default, at the packet root.
    """

    where: str
    base: Location | None = None
    sources: tuple[tuple[str, str], ...] = ()
    mirrors: tuple[tuple[str, str], ...] = ()
    default: bool = False

    @classmethod
    def of(
        cls,
        where: str,
        base: Location | None = None,
        sources: Mapping[str, str] | None = None,
        mirrors: Mapping[str, str] | None = None,
    ) -> SourcesDocument:
        """Build a document, refusing one holding two equal mirror prefixes (Part 04 §5.5.1).

        Raises
        ------
        SourcesError
            If two mirror prefixes each begin the other.
        """
        keys: dict[_Key, str] = {}
        for prefix in mirrors or {}:
            key = _key(prefix)
            if key is None:
                continue
            if key in keys:
                raise SourcesError(f"{where} holds equal mirror prefixes {keys[key]!r} and {prefix!r}")
            keys[key] = prefix
        return cls(where, base, tuple((sources or {}).items()), tuple((mirrors or {}).items()))

    def place(self, uri: str) -> tuple[_Key | None, Location | None]:
        """Where a `uri` this document states points: its comparison key, and its location for this reader.

        Either is None where there is none: a Windows path has a key and no location for a reader
        on Linux, and a relative `uri` in a document stored nowhere has neither (Part 04 §5.5.2).
        """
        if uri.startswith(("\\\\?\\", "\\\\.\\")):
            return None, None
        if (key := _key(uri)) is not None:
            return key, Location.of(uri) if _here(key) else None
        if self.base is None:
            return None, None
        try:
            names = decode(uri) if uri else ()
        except ValueError:
            return None, None
        base = _key(self.base.uri)
        return (None if base is None else (*base[:2], base[2] + names)), self.base.append(names)


@dataclass(frozen=True)
class Located:
    """Where one resource's bytes are, and what placed them there (Part 04 §5.5.1).

    Attributes
    ----------
    location : Location
        Where to read it.
    source_document : str or None
        The document through which its source resolved.
    mirror_document : str or None
        The document whose mirror was applied.
    redirected : bool
        Whether a mirror produced the location or the source resolved through a document other
        than the packet's default, so that recorded store digests do not describe it (Part 04 §5.4).
    unusable : tuple of (str, str)
        Each mirror, by document and prefix, whose prefix began the location and whose `uri` names
        no location for this reader.
    """

    location: Location
    source_document: str | None = None
    mirror_document: str | None = None
    redirected: bool = False
    unusable: tuple[tuple[str, str], ...] = ()


class Resolution:
    """The resolution documents one reader ranks for one packet, and those it did not use (Part 04 §5.5).

    Documents a reader looks for itself are read only when something first needs them, since a
    packet-owned resource never does and over a store each is a request.

    Attributes
    ----------
    documents : tuple of SourcesDocument
        In rank: the caller's, the configuration's, then the packet's default.
    unused : tuple of (str, str)
        Each document it did not use, and why.
    """

    def __init__(
        self,
        documents: Iterable[SourcesDocument] = (),
        unused: Iterable[tuple[str, str]] = (),
        later: Callable[[], tuple[tuple[SourcesDocument, ...], tuple[tuple[str, str], ...]]] | None = None,
    ) -> None:
        self._documents = tuple(documents)
        self._unused = tuple(unused)
        self._later = later
        self._lock = threading.Lock()

    def _settle(self) -> None:
        if self._later is None:
            return
        with self._lock:
            if self._later is not None:
                documents, unused = self._later()
                self._documents += documents
                self._unused += unused
                self._later = None

    @property
    def documents(self) -> tuple[SourcesDocument, ...]:
        """In rank: the caller's, the configuration's, then the packet's default."""
        self._settle()
        return self._documents

    @property
    def unused(self) -> tuple[tuple[str, str], ...]:
        """Each document it did not use, and why."""
        self._settle()
        return self._unused

    @classmethod
    def of(cls, rewrite: Rewrite | None = None, sources: Iterable[Sources] = ()) -> Resolution:
        """Rank documents a caller gave as mappings: `rewrite`'s mirrors, then each of `sources`."""
        documents = [SourcesDocument.of("caller mirrors", mirrors=rewrite)] if rewrite else []
        documents += [SourcesDocument.of(f"caller sources {n}", sources=s) for n, s in enumerate(sources, 1)]
        return cls(tuple(documents))

    def source(self, name: str) -> SourcesDocument | None:
        """Return the first ranked document whose `sources` names `name`."""
        return next((d for d in self.documents if name in dict(d.sources)), None)

    def mirror(self, key: _Key) -> tuple[SourcesDocument | None, Location | None, tuple[tuple[str, str], ...]]:
        """Apply the first ranked document holding a usable mirror whose prefix begins `key`.

        Returns that document and the location it produces, both None where no usable mirror's
        prefix begins it, and every mirror whose prefix began it and that was not usable.
        """
        unusable: list[tuple[str, str]] = []
        for document in self.documents:
            best: tuple[int, Location] | None = None
            for prefix, uri in document.mirrors:
                begun = _key(prefix)
                if begun is None or not _begins(begun, key):
                    continue
                _, place = document.place(uri)
                if place is None:
                    unusable.append((document.where, prefix))
                elif best is None or len(begun[2]) > best[0]:
                    best = (len(begun[2]), place)
            if best is not None:
                return document, best[1].append(key[2][best[0] :]), tuple(unusable)
        return None, None, tuple(unusable)


@dataclass(frozen=True)
class Location:
    """One place bytes can be read from, and the resolution documents ranked for its packet.

    The resolution travels with the location so that resolving a declared URI needs nothing but
    the root, which is already threaded through every resource handle.
    """

    uri: str
    resolution: Resolution = field(default=Resolution(), compare=False)

    @classmethod
    def of(cls, where: str | Path | Location, resolution: Resolution | None = None) -> Location:
        """Read a root as a location, whatever form the caller had it in.

        Parameters
        ----------
        where : str, Path, or Location
            A local directory, a `file:` URI, or a store prefix such as `s3://bucket/prefix`.
        resolution : Resolution, optional
            The documents :meth:`resolve` ranks, replacing any `where` carries.

        Returns
        -------
        Location
            The root, with its resolution attached.
        """
        if isinstance(where, Location):
            return where if resolution is None else cls(where.uri, resolution)
        text = str(where)
        resolution = resolution or Resolution()
        if _scheme(text) == "file":
            return cls(str(Path(unquote(urlparse(text).path))), resolution)
        return cls(text.rstrip("/") if _scheme(text) else text, resolution)

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

    def parent(self) -> Location:
        """Return the directory or prefix holding this location."""
        if self.is_local:
            return Location(str(Path(self.uri).absolute().parent), self.resolution)
        return Location(self.uri.rstrip("/").rpartition("/")[0], self.resolution)

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
            return Location(str(Path(self.uri) / relative), self.resolution)
        return Location(f"{self.uri.rstrip('/')}/{relative.lstrip('/')}", self.resolution)

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
            return Location(str(Path(self.uri).joinpath(*names)), self.resolution)
        return Location("/".join((self.uri.rstrip("/"), *names)), self.resolution)

    def resolve(self, declared: str, source: str | None = None) -> Location:
        """Where a manifest's declared URI points from here; :meth:`locate` says what placed it."""
        return self.locate(declared, source).location

    def locate(self, declared: str, source: str | None = None) -> Located:
        """Where a manifest's declared URI points from here, and through which documents (Part 04 §5.5).

        A resource naming a `source` is relative to wherever the first ranked document naming that
        source puts it; one that does not is relative to this root unless absolute, which is what
        makes a packet portable. An absolute location then takes the first ranked document's
        longest usable mirror, once; one relative to the root is never mirrored. A relative
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
        Located
            Where to read it, and what placed it there.

        Raises
        ------
        UnresolvedSource
            If `source` is named and no ranked document locates it for this reader.
        ResourceUnreadableError
            If `declared` is neither absolute nor a relative reference, such as a path beginning
            with `/` or one with a `..` segment, so it names no place under the root.
        """
        document = None
        if source is not None:
            document = self.resolution.source(source)
            if document is None:
                known = sorted({name for d in self.resolution.documents for name, _ in d.sources}) or ["none"]
                raise UnresolvedSource(
                    f"no resolution document locates source {source!r}; this reader has: {', '.join(known)}",
                    source=source,
                )
            key, place = document.place(dict(document.sources)[source])
            names = self._names(declared)
            key = None if key is None else (*key[:2], key[2] + names)
            place = None if place is None else place.append(names)
        elif is_absolute(declared):
            key, place = _key(declared), self._absolute(declared)
        else:
            return Located(self.append(self._names(declared)))
        mirrored, produced, unusable = self.resolution.mirror(key) if key is not None else (None, None, ())
        place = produced or place
        if place is None:
            stated = dict(document.sources)[source] if document is not None and source is not None else declared
            raise UnresolvedSource(
                f"source {source!r} is at {stated!r} in {document.where if document else 'the manifest'}, "
                "which names no location for this reader and no usable mirror redirects",
                source=source,
            )
        return Located(
            Location(place.uri, self.resolution),
            None if document is None else document.where,
            None if mirrored is None else mirrored.where,
            mirrored is not None or (document is not None and not document.default),
            unusable,
        )

    @staticmethod
    def _names(declared: str) -> tuple[str, ...]:
        try:
            return decode(declared)
        except ValueError as exc:
            raise ResourceUnreadableError(f"{declared!r} is neither absolute nor a relative reference: {exc}") from exc

    def _absolute(self, where: str) -> Location:
        """Resolve a manifest's absolute URI as spelled."""
        if _scheme(where) == "file":
            return Location(str(Path(unquote(urlparse(where).path))), self.resolution)
        return Location(where, self.resolution)

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


def resolve_sources(
    root: Location,
    supplied: Iterable[Sources | str | Path] | None = None,
    rewrite: Rewrite | None = None,
    configured: Sequence[str] | None = None,
) -> Resolution:
    """Rank the resolution documents for the packet at `root`, in the order Part 04 §5.5 fixes.

    The caller's come first: `rewrite` as a document of mirrors, then each of `supplied` in the
    order given. The configuration's follow, from :func:`configured_sources` unless `configured`
    lists them, then `sources.json` at the packet root. The configuration's and the default are read
    when the resolution is first consulted rather than here. One that is absent is skipped, and one
    that cannot be used is recorded as unused rather than raised, so a defective optional file
    cannot stop a packet opening.

    Parameters
    ----------
    root : Location
        Packet root, where the default document is looked for.
    supplied : iterable, optional
        Mappings of source name to URI, or locations of resolution documents.
    rewrite : Mapping, optional
        The caller's mirrors, mirror prefix to location.
    configured : sequence of str, optional
        The configuration's document locations, in place of the environment's.

    Returns
    -------
    Resolution
        The ranked documents and those not used.

    Raises
    ------
    SourcesError
        If a supplied document is absent, unreadable, of an unknown version, fails the schema, or
        holds equal mirror prefixes.
    """
    documents = list(Resolution.of(rewrite).documents)
    for n, one in enumerate(supplied or (), 1):
        if isinstance(one, Mapping):
            documents.append(SourcesDocument.of(f"caller sources {n}", sources=one))
            continue
        try:
            documents.append(read_document(Location.of(one)))
        except FileNotFoundError as exc:
            raise SourcesError(f"no source resolution document at {one}") from exc
    if configured is None:
        configured = configured_sources()
    optional = [(Location.of(where), False) for where in configured] + [(root.join(SOURCES_FILENAME), True)]

    def read_optional() -> tuple[tuple[SourcesDocument, ...], tuple[tuple[str, str], ...]]:
        found: list[SourcesDocument] = []
        unused: list[tuple[str, str]] = []
        for where, default in optional:
            try:
                document = read_document(where)
            except FileNotFoundError:
                continue
            except SourcesError as exc:
                unused.append((str(where), str(exc)))
                continue
            found.append(SourcesDocument(document.where, document.base, document.sources, document.mirrors, default))
        return tuple(found), tuple(unused)

    return Resolution(documents, later=read_optional)


__all__ = [
    "SOURCES_ENVIRONMENT",
    "SOURCES_FILENAME",
    "SOURCES_VERSION",
    "SOURCES_VERSIONS",
    "Located",
    "Location",
    "Resolution",
    "SourcesDocument",
    "check_sources",
    "configured_sources",
    "read_document",
    "read_sources",
    "resolve_sources",
    "user_sources",
]

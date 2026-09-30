"""The session recipe: what a packet is built from, declared as a file rather than a script.

Part 05 §4.3 requires normalization to be deterministic in declared parameters, and
`core.processing_runs` records the run that used them. A build script satisfies neither. Its
parameters are wherever its statements happen to put them, nothing can hash it, and the
`processing_run_id` a packet carries then names a run whose inputs are unrecoverable. A recipe
is that parameter set as one file, so the run record can carry the parameters themselves
(`core.processing_runs.parameters`) and a reader can see what produced the packet.

Nothing here opens a source or writes anything. Parsing and checking are separate from
building for the reason Part 05 gives -- *"do not combine source parsing, normalization,
validation, and writing into one opaque step"* -- and because a recipe that is wrong should
say so before a four-minute build, not after.

The checks worth having come from the registry. A source declares which resources it `owns`,
and the registry declares which resources reference which, so an owned table whose required
foreign key points at a table no source produces is a packet that cannot validate -- knowable
from two documents, with no data in hand.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tomllib
from upath import UPath

from .sources.store import source_root

#: Resources a recipe supplies from its own declarations rather than through a source: the
#: session and subject it names, and the record of the run that read the sources.
#: Source kinds that accept a `sample` cap, for the development flag that makes a round trip
#: seconds instead of minutes. Only the sorter: the spike table is 99.9% of a packet's rows.
SAMPLED = frozenset({"sorter"})

RECIPE_SUPPLIES = ("core.sessions", "core.processing_runs")

#: What Part 04 §4.1 admits after a resource ID's dot, which a prefix begins.
_PREFIX = re.compile(r"[a-z0-9_.-]*")

#: Part 12 §4's closed vocabulary: the names a build fills itself. A declared name outside this
#: set is an option, which the recipe has to carry. Held here because `check` has to tell the two
#: apart with nothing open, and a profile adding a term amends that section.
TERMS = frozenset(
    {
        "root",
        "session_id",
        "reference_clock",
        "clocks",
        "first_samples",
        "units",
        "wanted",
        "array_location",
        "opaque_location",
        "source_cache",
    }
)

#: Resources the recipe supplies only where no source owns them (Part 05 §3.1). `core.subjects` left
#: RECIPE_SUPPLIES because the NWB states every column of it and the row was built and discarded;
#: a `[subject]` block is now the fallback for a packet whose sources name no subject.
RECIPE_MAY_SUPPLY = ("core.subjects",)


def payloads(registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()) -> frozenset[str]:
    """Return the loaded registries' opaque singleton declarations, which a source owns as it owns a table.

    Each is one resource whose ID is its declaration's, so a recipe can name it and a source deliver
    it as a payload (Part 12 §5).
    """
    return frozenset(
        declaration_id
        for document in (registry, *extensions)
        for declaration_id, declaration in document["resources"].items()
        if declaration["kind"] == "opaque" and declaration["instances"]["mode"] == "singleton"
    )


def adapter_for(kind: str) -> Any:
    """Return the class this kind names, built-in or registered by another distribution.

    Imported here rather than at module load: `Recipe` is meant to be parseable without the
    adapters, and this is the one thing it needs from them. The adapters cost 0.16 s to import and
    open nothing, so a check that consults them still reports before any I/O. A registered kind is
    consulted too, because a build that read less of one than of a built-in would give an adapter
    from another distribution the worse deal (Part 05 §3.4).
    """
    from . import sources

    return sources.ADAPTERS.get(kind) or sources.discovered().get(kind)


def states(kind: str) -> Mapping[str, str]:
    """Return the recipe fields an adapter of this kind can state, to the attribute holding each.

    Part 05 §3.4 puts the obligation on the build rather than on the adapter, so a kind whose adapter
    declares nothing is reported by `check` rather than silently treated as stating nothing --
    which is the failure `produces` has, and which R63 §4 left open.
    """
    adapter = adapter_for(kind)
    stated = getattr(adapter, "STATES", None) if adapter is not None else None
    return dict(stated) if stated is not None else {}


def declares_states(kind: str) -> bool:
    """Whether this kind's adapter declares `STATES` at all, empty or not (Part 05 §3.4)."""
    adapter = adapter_for(kind)
    return adapter is not None and getattr(adapter, "STATES", None) is not None


def state_accessors(kind: str) -> Mapping[str, str]:
    """`STATES` entries whose named attribute the adapter class does not expose (Part 05 §3.4)."""
    adapter = adapter_for(kind)
    return {f: a for f, a in states(kind).items() if adapter is not None and not hasattr(adapter, a)}


def needs(kind: str) -> tuple[str, ...]:
    """Return the names a build must supply an adapter of this kind (Part 05 §3.4).

    Each resolves against Part 12 §4's terms first and the recipe's options second, so what a
    recipe has to carry is whatever is left: the declaration is where the options a source cannot
    be constructed without are recorded, rather than a table here keyed by kind.
    """
    # The floor is what every adapter needs and no declaration can omit: a root to open and the
    # session it is built for (Part 12 §4).
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "NEEDS", ("root", "session_id")) if adapter is not None else ())


#: Options a build reaches a source with rather than an adapter reading them, so no declaration
#: names them and none is refused. `storage_options` says how to open the root and is consumed
#: where the store is opened (Part 12 §4). A facility a build applies through an option the
#: *adapter* reads is not one of these: Part 12 §4 makes the adapter declare it, which is why
#: `sample` is `sorter`'s to accept and not a build's to inject silently.
_BUILD_OPTIONS = frozenset({"storage_options"})


def accepts(kind: str) -> tuple[str, ...]:
    """Return the options an adapter of this kind reads and can run without (Part 05 §3.4).

    Separate from `needs` because the two differ in what a recipe owes: a declared need a recipe
    does not set is refused, so an option holding a default is declarable only here (R119 §2.1).
    """
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "ACCEPTS", ()) if adapter is not None else ())


def consumes(kind: str) -> tuple[str, ...]:
    """Return the kinds whose output an adapter of this kind reads (Part 05 §3.4)."""
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "CONSUMES", ()) if adapter is not None else ())


def contributes(kind: str) -> frozenset[str]:
    """Return the resources an adapter of this kind supplies only part of (Part 05 §3.4).

    A source entry without `owns` contributes these rather than owning them, because every such
    adapter supplies its own streams' clocks or its own arrays and devices, and another source
    supplies the rest.
    """
    adapter = adapter_for(kind)
    return frozenset(getattr(adapter, "CONTRIBUTES", ()) if adapter is not None else ())


def protocols(kind: str) -> tuple[str, ...]:
    """Return the protocols an adapter of this kind declares, empty for one this build ships."""
    adapter = adapter_for(kind)
    return tuple(getattr(adapter, "PROTOCOLS", ()) if adapter is not None else ())


def produces(kind: str) -> frozenset[str]:
    """Return what an adapter of this kind can supply (Part 05 §3.4).

    Empty where no adapter of this kind can be imported, which `check` reports through the
    declaration a recipe must then name (Part 12 §7) rather than treating as a source that
    produces nothing.
    """
    adapter = adapter_for(kind)
    return frozenset(getattr(adapter, "PRODUCES", ()) if adapter is not None else ())


#: Storage options that carry a credential itself rather than a reference to one. Refused,
#: because a recipe is recorded inside the packet it builds -- `core.processing_runs.parameters`
#: carries the document verbatim -- so a key written here travels wherever the packet does, and
#: an environment that can be asked for one instead is available on every machine that has one.
#: The names are fsspec's and its backends': s3fs, gcsfs and adlfs each spell the pair their own
#: way, and `connection_string` carries both halves at once.
SECRETS = frozenset(
    {
        "account_key",
        "api_key",
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
        "client_secret",
        "connection_string",
        "credential",
        "credentials",
        "key",
        "passwd",
        "password",
        "private_key",
        "sas_token",
        "secret",
        "secret_key",
        "session_token",
        "token",
    }
)

#: What a `token` may say without being one. gcsfs takes a mode here as well as a credential, and
#: `token = "anon"` is how its own documentation reads a public bucket -- so the name alone does
#: not decide, and these are the values that name a way to authenticate rather than a secret.
TOKEN_MODES = frozenset({"anon", "browser", "cache", "cloud", "google_default"})

#: What a refused option is replaced by wherever a recipe is recorded.
REDACTED = "[redacted]"


def carries_a_secret(name: str, value: Any) -> bool:
    """Whether one storage option is a credential rather than a reference to one."""
    if name not in SECRETS:
        return False
    return not (name == "token" and isinstance(value, str) and value in TOKEN_MODES)


def redacted(document: Any) -> Any:
    """Return a recipe document with every credential replaced, for recording it.

    Applied wherever the recipe is written down rather than at parse time, so a build still opens
    what the author declared -- and applied to the whole document rather than to `storage_options`
    alone, because the next place a key gets written will not be the one this was built for.
    """
    if isinstance(document, Mapping):
        return {
            name: REDACTED if carries_a_secret(str(name), value) else redacted(value)
            for name, value in document.items()
        }
    if isinstance(document, list):
        return [redacted(item) for item in document]
    return document


#: Keys a `[[source]]` entry uses for itself; everything else is passed to the adapter.
_SOURCE_KEYS = frozenset({"kind", "root", "owns", "contributes", "storage_options", "in_process", "delivery"})

#: Keys a `[[materialize]]` entry uses for itself; the rest are the materializer's parameters.
_MATERIALIZE_KEYS = frozenset({"resource"})


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a recipe.

    Attributes
    ----------
    level : str
        ``error``, ``warning`` or ``info``. Only an error refuses the recipe; ``info`` records
        something the build will do, such as an override it will apply (Part 05 §3.5).
    message : str
        What is wrong, naming the recipe's own vocabulary rather than the registry's internals.
    """

    level: str
    message: str

    def __str__(self) -> str:
        """Render as ``level: message``."""
        return f"{self.level}: {self.message}"


@dataclass(frozen=True)
class ClockSpec:
    """A clock the recipe declares.

    The rate is a rational because `core.clocks` carries one: a nominal 30 kHz whose true rate
    is 30000/1.0001 is not the grid 30000/1, and the difference is what anchor alignment has to
    resolve. `origin` has no default because `core.clocks.origin` is required -- a clock whose
    tick 0 means nothing in particular cannot be aligned to another.
    """

    clock_id: str
    name: str
    tick_rate_num: int
    origin: str
    tick_rate_den: int = 1
    parent_clock_id: str | None = None

    def clock(self, session_id: str) -> Any:
        """Build the writer's :class:`~escapewheel_writer.clock.Clock` for a session.

        Parameters
        ----------
        session_id : str
            The session this clock belongs to.

        Returns
        -------
        Clock
            The clock, ready to hand to an adapter.
        """
        from .clock import Clock

        return Clock(
            self.clock_id,
            session_id=session_id,
            name=self.name,
            tick_rate_num=self.tick_rate_num,
            tick_rate_den=self.tick_rate_den,
            origin=self.origin,
            parent_clock_id=self.parent_clock_id,
        )


@dataclass(frozen=True)
class DeliverySpec:
    """How a build reaches a source it does not import (Part 12 §2).

    The recipe carries all of it, because every field is a fact about one machine: which command
    runs the adapter, where its declarations are, and where it should write its report. What the
    adapter itself declares is in the document, and a build reads that before it launches anything.

    Attributes
    ----------
    command : tuple of str
        The argument list to run, in the source's own root. A list rather than a string because a
        parse is a quoting convention no recipe declared (Part 05 §3.7).
    protocol : str
        The protocol the recipe names, empty where it names none; :func:`reached_by` settles the
        one a build uses (Part 12 §3).
    declaration : Mapping, optional
        The parsed declaration document, where the recipe names one. Absent for a kind this build
        can import, whose class declares the same facts.
    report_path : Path, optional
        Where the adapter writes its report (Part 12 §9). A build removes it before the run.
    """

    command: tuple[str, ...]
    protocol: str
    declaration: Mapping[str, Any] | None = None
    report_path: Path | None = None


@dataclass(frozen=True)
class SourceSpec:
    """One source, what it is built from, and which resources it is responsible for.

    `owns` is the recipe's answer to a problem every multi-source build has: four adapters can
    each produce `core.probes`, and whichever runs last wins silently. Declaring it makes the
    overlap visible, and makes a resource nobody claims an error rather than an absence noticed
    much later.

    Attributes
    ----------
    kind : str
        Adapter to use.
    root : path
        Local directory or store prefix; `storage_options` in the recipe reaches it here.
        What the adapter reads.
    owns : tuple of str
        Resource IDs this source is solely responsible for. Records it emits for anything it
        neither owns nor contributes to are discarded.
    contributes : tuple of str
        Resource IDs this source adds rows to alongside others. `core.clocks` is the case that
        forces the distinction: the sorter declares one clock per probe stream and the sync
        source declares the rig clock they are all anchored to, and neither is wrong. What
        must not happen is two sources producing the *same* rows, which is what `owns` refuses.
    options : Mapping
        Everything else in the entry, passed to the adapter as keyword arguments.
    """

    kind: str
    root: Any
    owns: tuple[str, ...]
    contributes: tuple[str, ...] = ()
    options: Mapping[str, Any] = field(default_factory=dict)
    #: Where the source is, as the URI an adapter opens for itself (Part 12 §4). Not `str(root)`:
    #: a root this build resolved carries the anonymity it was opened with, and `str()` drops it,
    #: which is how a public bucket comes back signed in a process that was handed the text.
    uri: str = ""
    #: How to open that URI, where the recipe says. A fact about one machine's credentials, so it
    #: travels with the source rather than being a property of any adapter.
    storage_options: Mapping[str, Any] = field(default_factory=dict)
    #: Part 05 §3.4: whether the recipe stated `owns`. Silence means the whole of `PRODUCES`, so it
    #: must be distinguishable from an explicit empty list, which narrows to nothing.
    narrowed: bool = True
    #: Part 12 §2: how a build reaches this source where it does not import it. A source with
    #: no delivery block is constructed in this process, which every adapter this build ships
    #: can be (Part 05 §3.9).
    delivery: DeliverySpec | None = None
    #: Part 05 §3.9: whether the recipe declares that this source runs in the writer's process.
    #: A build delivers every other source out of process, so this is the recipe author saying
    #: that this machine installs the adapter alongside the writer -- a fact about one machine on
    #: one day, which is why no adapter and no build may decide it.
    in_process: bool = False

    @property
    def claims(self) -> tuple[str, ...]:
        """Every resource this source supplies, however it claims it."""
        return (*self.owns, *self.contributes)


def _delivery(block: Mapping[str, Any] | None, resolve: Any) -> DeliverySpec | None:
    """Parse a `[source.delivery]` block, leaving what is wrong with it to `check`.

    A declaration that cannot be read is carried as the problem it is rather than raised here,
    because a caller that reports every problem at once is more useful than one that stops at the
    first -- which is what `Recipe.load` promises of everything else in the document.
    """
    if not block:
        return None
    from . import declaration as declared_document

    document: Mapping[str, Any] | None = None
    if (named := block.get("declaration")) is not None:
        try:
            document = declared_document.load(resolve(str(named)))
        except ValueError as exc:
            document = {"unreadable": str(exc)}
    protocol = str(block.get("protocol") or "")
    command = block.get("command", ())
    report = block.get("report_path")
    return DeliverySpec(
        command=(command,) if isinstance(command, str) else tuple(str(c) for c in command),
        protocol=protocol,
        declaration=document,
        report_path=resolve(str(report)) if report else None,
    )


def _builtin(kind: str) -> bool:
    """Whether this build ships the adapter for a kind, which is what makes in process its route."""
    from . import sources

    return kind in sources.ADAPTERS


def _importable(kind: str) -> bool:
    """Whether this build can read a kind's declarations by importing its adapter."""
    return adapter_for(kind) is not None


def reached_by(spec: SourceSpec) -> str | None:
    """Return the protocol a build reaches this source by, or None where it runs in process.

    The recipe's where it names one, else the adapter's first declared (Part 12 §3). An adapter
    this build ships declares none, and is served over `stream-v0.1`, which needs no term beyond
    what the adapter declares.
    """
    from .declaration import STREAM

    if spec.delivery is None or spec.in_process:
        return None
    return spec.delivery.protocol or next(iter(declared(spec)["protocols"]), STREAM)


def declared(spec: SourceSpec) -> dict[str, Any]:
    """Return one source's declarations, from the document the recipe names or the class.

    A document and an importable class declaring the same facts are one declaration, and a build
    prefers neither (Part 12 §7) -- so everything reading a declaration reads it through here,
    and nothing downstream has to know which form this source took.
    """
    document = spec.delivery.declaration if spec.delivery is not None else None
    if document is not None and "unreadable" not in document:
        return {
            "protocols": tuple(document.get("protocols", ())),
            "produces": frozenset(document.get("produces", ())),
            "contributes": frozenset(document.get("contributes", ())),
            "states": tuple(document.get("states", ())),
            "needs": tuple(document.get("needs", ())),
            "accepts": tuple(document.get("accepts", ())),
            "consumes": tuple(document.get("consumes", ())),
            "declares_states": "states" in document,
        }
    return {
        "protocols": protocols(spec.kind),
        "produces": produces(spec.kind),
        "contributes": contributes(spec.kind),
        "states": tuple(sorted(states(spec.kind))),
        "needs": needs(spec.kind),
        "accepts": accepts(spec.kind),
        "consumes": consumes(spec.kind),
        "declares_states": declares_states(spec.kind),
    }


def _resolve_ownership(sources: tuple[SourceSpec, ...], preferred: Mapping[str, str]) -> tuple[SourceSpec, ...]:
    """Fill in `owns` and `contributes` from the entries, the declarations and the preferences.

    A preferred source owns its resource whatever its entry declares (Part 05 §3.3). An entry that
    declared no `owns` takes, of what its adapter can supply, everything no narrowed entry owns and
    no preference gives to another source: the resources its adapter supplies in part as
    contributions, and the rest as its own (Part 05 §3.4). What the entry itself lists under
    `contributes` it contributes and does not own.

    Where two defaulted entries are left owning one resource, both keep it and `check` refuses the
    recipe naming both -- a silent winner is what `owns` was introduced to prevent.
    """
    narrowed = {resource for spec in sources if spec.narrowed for resource in spec.owns}
    supplies = frozenset(RECIPE_SUPPLIES)
    resolved = []
    for spec in sources:
        mine = {resource for resource, kind in preferred.items() if kind == spec.kind}
        contributed = [resource for resource in spec.contributes if resource not in mine]
        if spec.narrowed:
            owns = [*spec.owns, *sorted(mine - set(spec.owns))]
        else:
            asked = declared(spec)
            elsewhere = {resource for resource, kind in preferred.items() if kind != spec.kind}
            owns = []
            for resource in sorted(asked["produces"] - narrowed - supplies - elsewhere - set(spec.contributes)):
                if resource in asked["contributes"] and resource not in mine:
                    contributed.append(resource)
                else:
                    owns.append(resource)
            owns += sorted(mine - set(owns))
        resolved.append(replace(spec, owns=tuple(owns), contributes=tuple(contributed)))
    return tuple(resolved)


@dataclass(frozen=True)
class MaterializeSpec:
    """An analysis resource to derive once the core resources are staged.

    Part 05 §8 puts materialization inside the import pipeline rather than after it, so
    a recipe declares what to derive and the commit does it: core is staged, the staged packet
    is opened, the resource is derived from it, and everything is validated together before
    anything is promoted. Deriving into a *committed* packet is what `amend` is for, and paying
    for that on a build the recipe fully describes is work nobody asked for -- a second
    manifest, a version bump, a superseded copy to retain, and a revalidation of resources that
    were validated moments earlier.

    Attributes
    ----------
    resource : str
        The resource ID to derive.
    options : Mapping
        Parameters for the materializer, such as `bucket_seconds`. They reach
        `core.processing_runs.parameters` by way of the recipe document.
    """

    resource: str
    options: Mapping[str, Any] = field(default_factory=dict)


def schema() -> dict[str, Any]:
    """Load the bundled JSON Schema for a recipe (Part 05 §3.1), copied from the specification's tree."""
    from importlib import resources

    parsed: dict[str, Any] = json.loads(resources.files(__package__).joinpath("schemas/recipe.schema.json").read_text())
    return parsed


def shape_problems(document: Mapping[str, Any]) -> list[str]:
    """Where a decoded recipe fails `recipe.schema.json`, each as `path: message`.

    Every failure rather than the first, since an author fixing a recipe wants the whole list; an
    unknown top-level block is one of them, where it would otherwise be dropped unread.
    """
    import jsonschema

    return [
        f"{'/'.join(str(p) for p in error.absolute_path) or 'recipe'}: {error.message}"
        for error in sorted(
            jsonschema.Draft202012Validator(schema()).iter_errors(document),
            key=lambda e: [str(p) for p in e.absolute_path],
        )
    ]


@dataclass(frozen=True)
class Recipe:
    """A parsed session recipe.

    Attributes
    ----------
    path : Path
        Where it was read from.
    digest : str
        ``sha256`` of the file, so a run record can name exactly these parameters.
    extensions : tuple of str
        Extension registries this packet carries (Part 09 §2), each named either by a **path** to a
        document beside the recipe, or by the **id** an installed distribution registers under
        `escapewheel.extensions`. Kept as written rather than resolved here, because which one a
        value is cannot be decided without looking at the filesystem and the installed
        distributions -- see `extensions.load`.
    registry : Path or None
        The registry to write against. Declared here rather than defaulted, because Part 04 §8 has
        the packet bind the registry it was written against -- so which one that is belongs in
        the parameters, not in whichever copy the tool happened to find.
    document : Mapping
        The parsed file, carried whole so it can go into `core.processing_runs.parameters`.
    """

    path: Path
    digest: str
    document: Mapping[str, Any]
    packet_id: str
    out: Path
    registry: Path | None
    extensions: tuple[str, ...]
    description: str | None
    session: Mapping[str, Any]
    subject: Mapping[str, Any]
    #: Part 05 §3.6: `block.field` to the reason the recipe's value supersedes the source's.
    overrides: Mapping[str, str]
    #: Parquet encodings this build forces, `resource.column` to `{encoding, reason}`. Declared
    #: here because an extension reaches the writer across a file or a subprocess and cannot hand
    #: it a Python object, and because an encoding is a fact about *this packet's* values rather
    #: than about the schema: a column that repeats in one session may not in the next.
    encoding: Mapping[str, Mapping[str, str]]
    clocks: tuple[ClockSpec, ...]
    sources: tuple[SourceSpec, ...]
    materialize: tuple[MaterializeSpec, ...]
    limits: Mapping[str, Any]
    #: Part 05 §3.3: resource to `{source, reason}`, the source kind that owns a resource several
    #: listed sources produce. The only preferences a build applies.
    preferences: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    #: The `packet_version` this recipe amends, which makes its build an amending build (Part 05
    #: §15.1), or None for a new packet.
    amends: str | None = None
    #: Where the build reads each packet it replaces, as the recipe wrote it (Part 05 §9.3).
    replaces: tuple[str, ...] = ()
    #: Part 05 §12: each run the recipe prefers among runs sharing an activity and scope.
    preferred_runs: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def load(cls, path: str | Path, *, out: str | Path | None = None) -> Recipe:
        """Read and parse a recipe.

        Parameters
        ----------
        path : str or Path
            The ``.toml`` file. Relative paths inside it resolve against its directory, so a
            recipe travels with the tree it describes.
        out : str or Path, optional
            Where the packet goes, overriding ``[packet].out``.

        Returns
        -------
        Recipe
            The parsed recipe. Structural problems are reported by :meth:`check`, not raised
            here, so a caller sees every problem at once rather than the first.

        Raises
        ------
        ValueError
            If the file is not valid TOML, declares no packet ID, or fails the recipe schema.
        """
        path = Path(path)
        raw = path.read_bytes()
        try:
            document = tomllib.loads(raw.decode())
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"{path}: not valid TOML: {exc}") from exc

        packet = document.get("packet", {})
        if not packet.get("id"):
            raise ValueError(f"{path}: [packet] declares no id")
        if problems := shape_problems(document):
            raise ValueError(f"{path}: not a recipe (Part 05 §3.1):\n  " + "\n  ".join(problems))

        here = path.parent

        def resolve(value: str) -> Path:
            """Resolve one declared path against the recipe's own directory."""
            candidate = Path(value)
            return candidate if candidate.is_absolute() else here / candidate

        def resolve_root(value: str, storage: Mapping[str, Any]) -> Any:
            """Resolve a source root, which Part 05 §3.1 leaves free to name a store.

            An AIND session's sorted asset is a prefix on `aind-open-data`, and a build reads
            about 12% of one, so naming the prefix is both shorter and better provenance than
            naming a staged copy (Part 05 §3.2).

            **A store root is read anonymously unless the recipe says otherwise.** The data
            these packets are built from is public, and signing it is what fails: a stale
            profile makes the client refresh an SSO token and give up before it considers that
            the object needs no signing at all. A recipe that does need credentials declares
            `storage_options`, which replaces the default rather than adding to it, so
            `{anon = false}` is how one asks for the ambient profile back. The rule itself lives
            in `sources.store.source_root`, so an adapter built directly from a URI behaves as
            a recipe-built one does.
            """
            if getattr(UPath(value), "protocol", "") in ("", "file"):
                return resolve(value)
            return source_root(value, **storage)

        def locate(value: str, storage: Mapping[str, Any]) -> str:
            """Where the source is, for an adapter that opens it in another process.

            A local path is resolved, since the other process has its own working directory; a
            store URI is left exactly as the recipe wrote it, because the text of what
            `resolve_root` returns no longer says how to open it.
            """
            del storage
            resolved = resolve_root(value, {})
            return str(resolved) if isinstance(resolved, Path) else value

        destination = Path(out) if out else resolve(str(packet.get("out", packet["id"])))

        return cls(
            path=path,
            digest=hashlib.sha256(raw).hexdigest(),
            document=document,
            packet_id=str(packet["id"]),
            out=destination,
            registry=resolve(str(packet["registry"])) if packet.get("registry") else None,
            extensions=tuple(str(e) for e in packet.get("extensions", [])),
            description=packet.get("description"),
            session=document.get("session", {}),
            subject=document.get("subject", {}),
            overrides=document.get("overrides", {}),
            encoding=document.get("encoding", {}),
            clocks=tuple(ClockSpec(**c) for c in document.get("clock", [])),
            sources=_resolve_ownership(
                tuple(
                    SourceSpec(
                        kind=str(s["kind"]),
                        root=resolve_root(str(s.get("root", ".")), s.get("storage_options", {})),
                        uri=locate(str(s.get("root", ".")), s.get("storage_options", {})),
                        storage_options=dict(s.get("storage_options", {})),
                        delivery=_delivery(s.get("delivery"), resolve),
                        owns=tuple(s.get("owns", ())),
                        contributes=tuple(s.get("contributes", ())),
                        options={k: v for k, v in s.items() if k not in _SOURCE_KEYS},
                        narrowed="owns" in s,
                        # `[packet] in_process` declares it for every source, since whether a set
                        # of adapters installs together is a fact about the set; an entry may
                        # narrow that to itself.
                        in_process=bool(s.get("in_process", packet.get("in_process", False))),
                    )
                    for s in document.get("source", [])
                ),
                {resource: str(entry["source"]) for resource, entry in document.get("preference", {}).items()},
            ),
            materialize=tuple(
                MaterializeSpec(
                    resource=str(m["resource"]),
                    options={k: v for k, v in m.items() if k not in _MATERIALIZE_KEYS},
                )
                for m in document.get("materialize", [])
            ),
            limits=document.get("commit", {}),
            preferences=document.get("preference", {}),
            amends=packet.get("amends"),
            replaces=tuple(str(entry) for entry in packet.get("replaces", ())),
            preferred_runs=tuple(document.get("preferred_run", ())),
        )

    def with_sample(self, sample: int) -> Recipe:
        """Return a copy capping every source that can be sampled, recording the cap.

        The cap goes into the document as well as the sources, because the document is what
        `core.processing_runs.parameters` carries — so a sampled packet says it is one, and a
        reader cannot mistake it for a full import that lost most of its spikes. The digest is
        recomputed over the effective parameters, so the run this produces is distinguishable
        from the same recipe run whole.

        Parameters
        ----------
        sample : int
            Spikes kept per stream.

        Returns
        -------
        Recipe
            A copy. The original is unchanged, as its digest must stay the file's.
        """
        document = json.loads(json.dumps(self.document, default=str))
        for entry in document.get("source", []):
            if entry.get("kind") in SAMPLED:
                entry["sample"] = sample
        sources = tuple(
            replace(spec, options={**spec.options, "sample": sample}) if spec.kind in SAMPLED else spec
            for spec in self.sources
        )
        # The digest identifies the parameters, not the file, once the two differ: a sampled run
        # and a full one must not claim the same `processing_run_id`.
        canonical = json.dumps(document, default=str, sort_keys=True).encode()
        return replace(self, document=document, sources=sources, digest=hashlib.sha256(canonical).hexdigest())

    @property
    def memory_budget(self) -> int | str:
        """What `[commit].memory_budget` allows a build to hold before it spills.

        One budget for the whole build rather than one per stage, because the stages that want
        memory do not overlap: the partition is built, then released, then the rules run. The
        peak is the larger of the two, not their sum, so each may have all of it.
        """
        budget: int | str = self.limits.get("memory_budget", 0)
        return budget

    @property
    def preferred(self) -> dict[str, str]:
        """Resource ID to the source kind the recipe prefers for it (Part 05 §3.3)."""
        return {resource: str(entry["source"]) for resource, entry in self.preferences.items()}

    @property
    def owners(self) -> dict[str, list[str]]:
        """Resource ID to the source kinds claiming it exclusively."""
        return self._claims("owns")

    @property
    def claimants(self) -> dict[str, list[str]]:
        """Resource ID to every source kind supplying it, exclusively or not.

        Includes what the recipe supplies itself, so a foreign key into `core.sessions` is not
        reported as dangling when no `[[source]]` produces it and the recipe does.
        """
        claimed = self._claims("claims")
        for resource in RECIPE_SUPPLIES:
            claimed.setdefault(resource, []).append("recipe")
        # Part 05 §3.1: the recipe supplies these only where no source owns them, so a `[subject]`
        # block still satisfies a foreign key into `core.subjects` and stops satisfying it the
        # moment a source claims the table.
        for resource in RECIPE_MAY_SUPPLY:
            if self.subject and resource not in claimed:
                claimed.setdefault(resource, []).append("recipe")
        return claimed

    def _claims(self, attribute: str) -> dict[str, list[str]]:
        """Invert the sources' claims of one kind into resource -> kinds."""
        claimed: dict[str, list[str]] = {}
        for source in self.sources:
            for resource in getattr(source, attribute):
                claimed.setdefault(resource, []).append(source.kind)
        return claimed

    def check(
        self,
        registry: Mapping[str, Any],
        extensions: Sequence[Mapping[str, Any]] = (),
        *,
        held_tables: Collection[str] = (),
        held_clocks: Collection[str] = (),
    ) -> list[Problem]:
        """Everything wrong with the recipe that is knowable without reading a source.

        Parameters
        ----------
        registry : Mapping
            A parsed registry document, supplying the table names and their references.
        extensions : sequence of Mapping
            Extension registries, whose tables a source may also own. An extension's references
            resolve against core; core's never resolve against an extension, which Part 09 §2
            requires by forbidding core to reference one at all. Given in the order of the
            `[packet].extensions` entries they resolve from, so a refusal can name the entries.
        held_tables, held_clocks : collection of str
            For an amending build, the tables the packet names and the names of the clocks it
            holds, which count as supplied and declared (Part 05 §3.5).

        Returns
        -------
        list of Problem
            Empty when the recipe is sound. Errors first, then warnings, each sorted, so two
            runs of the same recipe report identically.
        """
        tables = {
            name: declaration["table"]
            for name, declaration in registry["resources"].items()
            if declaration["kind"] == "table"
        }
        for document in extensions or ():
            tables.update(
                {
                    name: declaration["table"]
                    for name, declaration in document["resources"].items()
                    if declaration["kind"] == "table"
                }
            )
        # A source may own an opaque singleton, whose payload it delivers under the declaration's ID
        # (Part 12 §5); catalog instances are bound by the rows of the table it owns instead.
        singletons = payloads(registry, extensions)
        owners, claimants = self.owners, self.claimants
        supplied = {**claimants, **{r: claimants.get(r, ["packet"]) for r in held_tables}}
        errors: list[str] = []
        warnings: list[str] = []

        for resource, kinds in sorted(claimants.items()):
            if resource not in tables and resource not in singletons:
                errors.append(f"{kinds[0]} supplies {resource}, which the registry does not define")
        for resource, kinds in sorted(owners.items()):
            if len(kinds) > 1:
                errors.append(
                    f"{resource} is owned by {len(kinds)} sources ({', '.join(sorted(kinds))}); declare a "
                    f"[preference] naming the one that knows more, or contributes where each holds part"
                )
            elif len(claimants.get(resource, ())) > 1:
                others = sorted(set(claimants[resource]) - set(kinds))
                errors.append(f"{resource} is owned by {kinds[0]} but also supplied by {', '.join(others)}")

        errors.extend(self._arbitration_problems())
        errors.extend(self._extension_problems(extensions or ()))
        warnings.extend(self._unclaimed())
        errors.extend(self._dangling_references(tables, claimants, warnings, supplied))
        errors.extend(self._clock_problems(held_clocks))
        errors.extend(self._preferred_run_problems())
        errors.extend(self._amending_problems())
        errors.extend(self._option_problems())
        errors.extend(self._materialize_problems())
        errors.extend(self._prefix_problems())
        errors.extend(self._storage_problems())
        errors.extend(self._delivery_problems())
        errors.extend(self._declaration_problems(tables, singletons))
        errors.extend(self._states_problems())
        errors.extend(self.encoding_problems(tables))
        fact_errors, fact_warnings, notes = self._declared_fact_problems()
        errors.extend(fact_errors)
        warnings.extend(fact_warnings)

        return (
            [Problem("error", m) for m in sorted(set(errors))]
            + [Problem("warning", m) for m in sorted(set(warnings))]
            + [Problem("info", m) for m in sorted(set(notes))]
        )

    def _arbitration_problems(self) -> list[str]:
        """Report a repeated kind, an unsound preference, and a class contributing what it cannot produce.

        A source is named by its kind throughout, so a kind listed twice leaves a preference and
        every report unable to say which entry they mean (Part 05 §3.1). A preference declares
        ownership (Part 05 §3.3), so one naming a source that is absent, cannot supply the resource,
        or contradicts another entry's own `owns` or `contributes` has no sound reading. A delivered
        adapter's `contributes` is refused with the rest of its document (Part 12 §7); an
        imported one's is refused here.
        """
        problems = []
        kinds = [spec.kind for spec in self.sources]
        problems += [
            f"source {kind} is listed {kinds.count(kind)} times; a recipe lists a kind once, since everything "
            "names a source by its kind (Part 05 §3.1)"
            for kind in sorted({k for k in kinds if kinds.count(k) > 1})
        ]
        by_kind = {spec.kind: spec for spec in self.sources}
        for resource, kind in sorted(self.preferred.items()):
            chosen = by_kind.get(kind)
            if chosen is None:
                problems.append(f"[preference] {resource} names {kind}, which this recipe does not list")
                continue
            if resource not in declared(chosen)["produces"]:
                problems.append(
                    f"[preference] {resource} names {kind}, whose adapter does not declare it can supply it"
                )
            for entry in self.document.get("source", []):
                other = str(entry.get("kind"))
                if other != kind and resource in (*entry.get("owns", ()), *entry.get("contributes", ())):
                    problems.append(
                        f"[preference] {resource} names {kind}, and source {other} declares it under owns or "
                        "contributes; a preference says one source knows more, so the other supplies none of it"
                    )
            producers = sorted({spec.kind for spec in self.sources if resource in declared(spec)["produces"]})
            if len(producers) < 2:
                problems.append(
                    f"[preference] {resource} arbitrates nothing: only {', '.join(producers) or 'no source'} in this "
                    "recipe produces it (Part 05 §3.3)"
                )
        for spec in self.sources:
            if spec.delivery is not None:
                continue
            asked = declared(spec)
            problems += [
                f"{spec.kind} contributes {resource}, which its produces does not name"
                for resource in sorted(asked["contributes"] - asked["produces"])
            ]
        return problems

    def _extension_problems(self, extensions: Sequence[Mapping[str, Any]]) -> list[str]:
        """Report one extension listed in more than one `extensions` entry (Part 05 §3.1).

        Compared by `extension_id`, which only a resolved document carries, so a path paired with
        an installed id, or paths to two versions, are caught as well as a repeated string. A
        packet binds one registry per extension, so otherwise the build keeps one silently.
        """
        entries = (
            self.extensions
            if len(self.extensions) == len(extensions)
            else tuple(f"document {position}" for position in range(1, len(extensions) + 1))
        )
        by_extension: dict[str, list[str]] = {}
        for entry, document in zip(entries, extensions, strict=True):
            by_extension.setdefault(str(document["extension_id"]), []).append(entry)
        return [
            f"extension {extension_id} is listed in {len(named)} entries ({', '.join(repr(e) for e in named)}); "
            "a recipe lists an extension once, since a packet binds one registry per extension (Part 05 §3.1)"
            for extension_id, named in sorted(by_extension.items())
            if len(named) > 1
        ]

    def _states_problems(self) -> list[str]:
        """Adapters a build cannot ask which recipe fields they state (Part 05 §3.4).

        Refused rather than defaulted: an adapter that declares nothing would otherwise read as
        one that states nothing, which is the failure R63 §4 records for `PRODUCES`.
        """
        problems = []
        for spec in sorted(self.sources, key=lambda s: s.kind):
            if not declared(spec)["declares_states"]:
                problems.append(f"source {spec.kind} declares no STATES, so a build cannot tell what facts it states")
            if spec.delivery is not None:
                # An adapter a build cannot import exposes its stated values in its report rather
                # than through an attribute, so there is nothing here to look for (Part 12 §9).
                continue
            for fact, attribute in sorted(state_accessors(spec.kind).items()):
                problems.append(
                    f"source {spec.kind} states {fact} through {attribute!r}, which its adapter does not expose"
                )
        return problems

    @property
    def declared_facts(self) -> dict[str, Any]:
        """`block.field` to the value the recipe declares for it (Part 05 §3.4)."""
        blocks = {"session": self.session, "subject": self.subject}
        return {f"{block}.{k}": v for block, fields in blocks.items() for k, v in fields.items()}

    def stated_by(self) -> dict[str, list[str]]:
        """`block.field` to the source kinds in this recipe that state it (Part 05 §3.4)."""
        by_field: dict[str, list[str]] = {}
        for spec in sorted(self.sources, key=lambda s: s.kind):
            for fact in declared(spec)["states"]:
                by_field.setdefault(fact, []).append(spec.kind)
        return by_field

    def encoding_problems(self, tables: Mapping[str, Any]) -> list[str]:
        """Every `[encoding]` entry naming no declared column, knowable with no source read.

        An extension reaches the writer across a file or a subprocess, so what it says about its
        own columns arrives here rather than as a Python object it hands over. The choice and its
        reason are the schema's to check on load; the columns need the registries.
        """
        found: list[str] = []
        for name in sorted(self.encoding):
            resource, _, column = name.rpartition(".")
            if name.count(".") < 2 or resource not in tables:
                found.append(f"[encoding] {name} names no declared table")
            elif not any(c["name"] == column for c in tables[resource]["columns"]):
                found.append(f"[encoding] {name} names no column of {resource}")
        return found

    def _declared_fact_problems(self) -> tuple[list[str], list[str], list[str]]:
        """Errors, warnings and notes about declared facts and their overrides (Part 05 §3.5, §2.5).

        An empty override reason never loads (Part 05 §3.1). A field a source states is a warning because
        agreement is the likely case and only the build can tell, and a stale override costs a
        line rather than a build because it leaves the packet correct.
        """
        declared, stated = self.declared_facts, self.stated_by()
        errors: list[str] = []
        warnings: list[str] = []
        notes: list[str] = []
        for fact, reason in sorted(self.overrides.items()):
            if fact not in stated:
                warnings.append(f"[overrides] {fact} overrides nothing; no source in this recipe states it")
            elif fact not in declared:
                warnings.append(f"[overrides] {fact} overrides nothing; the recipe declares no value for it")
        for fact, kinds in sorted(stated.items()):
            if fact not in declared:
                continue
            who = ", ".join(kinds)
            if fact in self.overrides:
                notes.append(f"{fact} is declared and overrides {who}")
            else:
                warnings.append(f"{fact} is declared and {who} states it; the build compares them")
        return errors, warnings, notes

    def _dangling_references(
        self,
        tables: Mapping[str, Any],
        claimed: Mapping[str, list[str]],
        warnings: list[str],
        supplied: Mapping[str, list[str]] | None = None,
    ) -> list[str]:
        """Foreign keys from an owned table into a table no source produces.

        Severity follows the column: a **required** foreign key into an absent table means
        every row dangles, so the packet cannot validate. A **nullable** one may be legitimately
        empty, so it is a warning -- and worth saying, because `generate(only=...)` silently
        skips a foreign-key check whose target is absent, which is the quiet version of the
        same problem. `supplied` adds, as targets only, the tables an amended packet holds.
        """
        supplied = claimed if supplied is None else supplied
        problems = []
        for resource in sorted(claimed):
            spec = tables.get(resource)
            if spec is None:
                continue
            presence = {c["name"]: c["presence"] for c in spec["columns"]}
            for reference in spec.get("references", []):
                target = reference["resource"]
                if target in supplied:
                    continue
                columns = ", ".join(reference["columns"])
                if any(presence.get(c) == "required" for c in reference["columns"]):
                    problems.append(f"{resource}.{columns} requires {target}, which no source owns")
                else:
                    warnings.append(f"{resource}.{columns} references {target}, which no source owns")
        return problems

    def _unclaimed(self) -> list[str]:
        """Resources a listed source can produce that nothing in this recipe claims (Part 05 §3.5).

        A warning and not an error: narrowing is legitimate, and only the recipe's author knows
        whether this one was meant. It is the first of the three ways a recipe loses a resource,
        moved from the middle of a build to before a byte is read.
        """
        claimed = {resource for spec in self.sources for resource in spec.claims}
        claimed.update(RECIPE_SUPPLIES)
        return [
            f"{spec.kind} can produce {resource}, which no source in this recipe claims"
            for spec in self.sources
            for resource in sorted(declared(spec)["produces"] - claimed)
        ]

    def _preferred_run_problems(self) -> list[str]:
        """Two `preferred_run` entries of one key, or a `chosen_at` naming no instant (Part 05 §3.5)."""
        problems = []
        keys = [(str(e["activity_type"]), str(e["scope_kind"]), str(e["scope"])) for e in self.preferred_runs]
        problems += [
            f"[[preferred_run]] {activity} of {kind} {scope} is declared {keys.count(key)} times; a recipe "
            "prefers one run per activity and scope (Part 05 §12)"
            for key in sorted(set(keys))
            if keys.count(key) > 1
            for activity, kind, scope in [key]
        ]
        problems += [
            f"[[preferred_run]] {entry['processing_run_name']} gives chosen_at {entry['chosen_at']!r}, which names "
            "no instant; give an offset date-time"
            for entry in self.preferred_runs
            if "chosen_at" in entry and normalized_chosen_at(entry["chosen_at"]) is None
        ]
        return problems

    def _amending_problems(self) -> list[str]:
        """Report each member an amending recipe declares where the packet's rows prevail (Part 05 §3.5)."""
        if self.amends is None:
            return []
        problems = []
        if self.replaces:
            problems.append("[packet] gives both replaces and amends, and a build replaces packets or amends one")
        problems += [
            f"[session] {name} is declared, and an amending recipe declares only session_id"
            for name in sorted(self.session)
            if name != "session_id"
        ]
        problems += [
            f"[subject] {name} is declared, and an amending recipe declares none" for name in sorted(self.subject)
        ]
        problems += [
            f"[overrides] {name} is declared, and an amending recipe declares none" for name in sorted(self.overrides)
        ]
        return problems

    def _storage_problems(self) -> list[str]:
        """Storage options that carry a credential, which a recipe must not (Part 05 §3.1).

        Refused rather than redacted on the way in, because the recipe file is the author's and
        the value is in it: replacing it here would leave the packet clean and the file leaking,
        and the author would not learn. What a build records is redacted as well, since a recipe
        written before this check ran is already inside a packet.
        """
        return [
            f"[[source]] {spec.kind} sets storage_options.{name}, which is a credential; name a "
            f"profile or leave it to the environment, because the recipe is recorded in the packet "
            f"it builds"
            for spec in self.sources
            for name, value in sorted(spec.storage_options.items())
            if carries_a_secret(str(name), value)
        ]

    def _delivery_problems(self) -> list[str]:
        """Report each source with no route to a build (Part 05 §3.9).

        There are three: a `[source.delivery]` block, which carries the command that runs the
        adapter out of process; `in_process`, which is the recipe author saying this machine
        installs the adapter beside the writer; and being an adapter this build ships, which runs
        in process unless its entry gives it a delivery, so a recipe need say nothing.

        What is left over is a kind another distribution registered and the recipe says nothing
        about. An adapter released independently of a build must declare a protocol (Part 12
        §3), and declaring one is not enough on its own: something still has to say what
        command runs it, and only the recipe knows.
        """
        problems = []
        for spec in self.sources:
            if spec.in_process or spec.delivery is not None or _builtin(spec.kind):
                continue
            problems.append(
                f"{spec.kind} is registered by another distribution and this recipe neither delivers it nor "
                f"runs it in process; give it a [source.delivery] command or set in_process"
            )
        return problems

    def _declaration_problems(self, tables: Mapping[str, Any], singletons: Collection[str] = ()) -> list[str]:
        """Everything wrong with a source's declaration, knowable with nothing opened.

        Part 12 §7's checks for every source, whichever route it takes, plus what the recipe has
        to get right for a build to reach the adapter at all. A class is checked as the document it
        would generate, so the two forms are refused for the same defects. Each check fires on its
        own and names what is wrong, and none needs the adapter imported.
        """
        from . import declaration as document

        problems = []
        for spec in self.sources:
            delivery = spec.delivery
            if delivery is not None:
                if spec.in_process:
                    problems.append(
                        f"{spec.kind} declares both a delivery and in_process; a source is reached one way or "
                        "the other (Part 05 §3.9)"
                    )
                if not delivery.command:
                    problems.append(f"{spec.kind} declares a delivery and no command to run it with")
                if delivery.declaration is not None and "unreadable" in delivery.declaration:
                    problems.append(f"{spec.kind}: {delivery.declaration['unreadable']}")
                    continue
            if (delivery is None or delivery.declaration is None) and not _importable(spec.kind):
                if delivery is not None:
                    problems.append(
                        f"{spec.kind} names no declaration and this build cannot import it, so nothing says "
                        "what it produces"
                    )
                continue
            asked = declared(spec)
            stated = {
                "kind": spec.kind,
                **({"protocols": list(asked["protocols"])} if asked["protocols"] else {}),
                "produces": sorted(asked["produces"]),
                "contributes": sorted(asked["contributes"]),
                "states": list(asked["states"]),
                "needs": list(asked["needs"]),
                "accepts": list(asked["accepts"]),
                "consumes": list(asked["consumes"]),
            }
            if delivery is None or delivery.declaration is None:
                # A document was shape-checked as it was read; a class is checked here, as one.
                shipped = _builtin(spec.kind)
                if not shipped and not asked["protocols"]:
                    problems.append(
                        f"{spec.kind} declares no protocol; an adapter released independently of a build "
                        f"declares at least one of {', '.join(document.PROTOCOLS)} (Part 12 §3)"
                    )
                problems += [
                    f"{spec.kind} declaration: {problem}" for problem in document.shape_problems(stated, shipped=True)
                ]
            problems += [
                f"{spec.kind} {refusal}"
                for refusal in document.refusals(
                    stated, tables=tables, options=spec.options, terms=TERMS, payloads=singletons
                )
            ]
            named = delivery.protocol if delivery is not None else ""
            if named and asked["protocols"] and named not in asked["protocols"]:
                problems.append(
                    f"{spec.kind} names protocol {named!r}, which its adapter does not declare "
                    f"({', '.join(asked['protocols'])})"
                )
            elif named and named not in document.PROTOCOLS:
                problems.append(f"{spec.kind} names protocol {named!r}, which is in no group this profile names")
        return problems

    def _option_problems(self) -> list[str]:
        """Options a source kind requires and the recipe does not set, terms it sets, and unread options.

        All are refused before any source is opened (Part 12 §4). A term the build fills is not
        a recipe's business, so only the names that fall through to the recipe's options are
        reported here. An option the adapter names nowhere is the converse: the recipe states
        something about the packet that never reaches the source, and its author's next evidence
        would be its absence from the output (Part 12 §4).
        """
        problems = [
            f"source {spec.kind} requires {name!r}, which this entry does not set"
            for spec in self.sources
            for name in declared(spec)["needs"]
            if name not in TERMS and name not in spec.options
        ]
        problems += [
            f"source {spec.kind} sets {name!r}, which is a term the build fills rather than an option"
            for spec in self.sources
            for name in sorted(spec.options)
            if name in TERMS
        ]
        for spec in self.sources:
            known = set(declared(spec)["needs"]) | set(declared(spec)["accepts"])
            problems += [
                f"source {spec.kind} sets {name!r}, which it declares neither as needed nor as accepted"
                for name in sorted(spec.options)
                if name not in known and name not in _BUILD_OPTIONS and name not in TERMS
            ]
        return problems

    def _materialize_problems(self) -> list[str]:
        """Refuse a `[[materialize]]` resource nothing derives, or a parameter its materializer lacks.

        Materialization runs at commit, after every source has been read, so either would
        otherwise surface only once the build's whole cost had been paid.
        """
        import inspect

        from . import materialize
        from .session import MATERIALIZERS

        taken = {
            name
            for name, parameter in inspect.signature(materialize.into).parameters.items()
            if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        }
        problems: list[str] = []
        for spec in self.materialize:
            if spec.resource not in MATERIALIZERS:
                known = ", ".join(sorted(MATERIALIZERS)) or "nothing"
                problems.append(f"no materializer for {spec.resource}; this writer derives {known}")
                continue
            problems += [
                f"[[materialize]] {spec.resource} sets {name!r}, which its materializer does not take"
                for name in sorted(spec.options)
                if name not in taken
            ]
        return problems

    def _prefix_problems(self) -> list[str]:
        """Refuse a prefix no resource ID admits, or sources that would spell one identifier two ways.

        A prefix begins the name an adapter mints a resource ID from, so it holds only what Part 04
        §4.1 admits after the ID's dot. Adapters that read `prefix` compose shared identifiers from
        it -- `nwb`, `lfp` and `waveforms` each name a contact through `nwb.contact_ids` -- and a
        writer numbers a name (Part 05 §4.3), so a prefix on one and not another mints a second row
        for one entity. An unset prefix counts as a value, since a delivered adapter's default is
        not declared.
        """
        problems = [
            f"source {spec.kind!r}: prefix {spec.options['prefix']!r} holds characters outside [a-z0-9_.-], which "
            "a resource ID does not admit (Part 04 §4.1)"
            for spec in self.sources
            if "prefix" in spec.options
            and not (isinstance(spec.options["prefix"], str) and _PREFIX.fullmatch(spec.options["prefix"]))
        ]
        taking = sorted(
            (spec for spec in self.sources if "prefix" in {*declared(spec)["needs"], *declared(spec)["accepts"]}),
            key=lambda spec: spec.kind,
        )
        values = {spec.kind: spec.options.get("prefix") for spec in taking}
        # By repr, since an option may be a TOML table, which is unhashable.
        if len({repr(value) for value in values.values()}) <= 1:
            return problems
        named = ", ".join(f"{kind} {'unset' if value is None else repr(value)}" for kind, value in values.items())
        return [
            *problems,
            (
                f"sources disagree on prefix ({named}); every source whose adapter accepts prefix sets the same "
                "one, or one entity gets two identifiers"
            ),
        ]

    def _clock_problems(self, held: Collection[str] = ()) -> list[str]:
        """Clock IDs that are declared twice, referenced but absent, or parented to nothing.

        A clock an amended packet holds counts as declared, and declaring it again is refused, since
        its held row would then meet a second (Part 05 §3.5).
        """
        declared = [c.clock_id for c in self.clocks]
        known = set(declared) | set(held)
        problems = [
            f"clock {c} is declared more than once" for c in sorted({c for c in declared if declared.count(c) > 1})
        ]
        problems += [
            f"clock {c} is declared, and the packet this recipe amends holds a clock of that name"
            for c in sorted(set(declared) & set(held))
        ]
        reference = self.session.get("reference_clock_id")
        if reference and reference not in known:
            problems.append(f"session.reference_clock_id is {reference!r}, which no [[clock]] declares")
        for clock in self.clocks:
            if clock.parent_clock_id and clock.parent_clock_id not in known:
                problems.append(f"clock {clock.clock_id} names parent {clock.parent_clock_id!r}, which is not declared")
        return problems


def normalized_chosen_at(value: Any) -> datetime | None:
    """Return a `preferred_run` entry's `chosen_at` as a UTC timestamp, or None where it cannot be one.

    A local date-time or a bare date names no instant, so it is not normalized (Part 05 §3.5).
    """
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)


__all__ = [
    "RECIPE_SUPPLIES",
    "REDACTED",
    "SECRETS",
    "TERMS",
    "ClockSpec",
    "MaterializeSpec",
    "Problem",
    "Recipe",
    "SourceSpec",
    "normalized_chosen_at",
    "redacted",
]

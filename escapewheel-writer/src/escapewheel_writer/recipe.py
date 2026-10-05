"""The session recipe: what a packet is built from, declared as a file rather than a script.

The recipe (Part 05 §3):

- :class:`Recipe` -- a parsed recipe; `Recipe.load` reads one and `Recipe.check` reports
  everything wrong with it that is knowable without reading a source.
- :class:`SourceSpec`, :class:`DeliverySpec` -- one source, and how a build reaches it out of
  process.
- :class:`ClockSpec`, :class:`MaterializeSpec` -- a declared clock, and a resource to derive.
- :class:`Problem` -- one thing wrong with a recipe.
- :func:`schema`, :func:`shape_problems` -- the bundled recipe schema, and where a decoded
  recipe fails it.
- :func:`normalized_chosen_at` -- a `preferred_run` entry's `chosen_at` as a UTC timestamp.
- :func:`refusal` -- the refusal of a recipe for the problems a build found in it.
- :data:`RECIPE_SUPPLIES`, :data:`TERMS` -- the resources a recipe supplies itself, and the names
  a build fills.

What a source declares:

- :func:`declared` -- one source's declarations, from its document or its class.
- :func:`reached_by` -- the protocol a build reaches a source by.
- :func:`payloads` -- the loaded registries' opaque singleton declarations.

`kinds` reads what an adapter class declares, `secrets` holds what a build recognizes as a
credential, and `recipe_check` holds what `Recipe.check` reports.

Nothing here opens a source or writes anything, so a wrong recipe is refused before a build
spends anything on it.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from escapewheel_reader.resource_ids import CORE_PROCESSING_RUNS, CORE_SESSIONS, CORE_SUBJECTS
from escapewheel_validator import Level
from upath import UPath

from .errors import DeclarationUnreadable, RecipeFault, RecipeUnreadable, RecipeUnsound
from .kinds import accepts, consumes, contributes, declares_states, needs, produces, protocols, states
from .secrets import redacted
from .sources.store import source_root

#: Source kinds that accept a `sample` cap, for the development flag that makes a round trip
#: seconds instead of minutes. Only the sorter: the spike table is 99.9% of a packet's rows.
SAMPLED = frozenset({"sorter"})

#: Resources a recipe supplies from its own declarations rather than through a source: the
#: session it names, and the record of the run that read the sources.
RECIPE_SUPPLIES = (CORE_SESSIONS, CORE_PROCESSING_RUNS)


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

#: Resources the recipe supplies only where no source owns them (Part 05 §3.1). A source may state
#: every column of `core.subjects`, so a `[subject]` block is the fallback for a packet whose
#: sources name no subject.
RECIPE_MAY_SUPPLY = (CORE_SUBJECTS,)


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


#: Keys a `[[source]]` entry uses for itself; everything else is passed to the adapter.
_SOURCE_KEYS = frozenset({"kind", "root", "owns", "contributes", "storage_options", "in_process", "delivery"})

#: Keys a `[[materialize]]` entry uses for itself; the rest are the materializer's parameters.
_MATERIALIZE_KEYS = frozenset({"resource"})


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a recipe.

    Attributes
    ----------
    level : Level
        Only an error refuses the recipe; ``info`` records something the build will do, such as
        an override it will apply (Part 05 §3.5).
    message : str
        What is wrong, naming the recipe's own vocabulary rather than the registry's internals.
    code : RecipeFault
        Which fault it is, whatever the names in the message.
    """

    level: Level
    message: str
    code: RecipeFault

    def __str__(self) -> str:
        """Render as ``level: message``."""
        return f"{self.level}: {self.message}"


def refusal(recipe: Recipe, lead: str, problems: Sequence[Problem], *, cites: str = "") -> RecipeUnsound:
    """Return the refusal of `recipe`: its path, `lead`, each problem, and the part `cites` names."""
    message = f"{recipe.path}: {lead}" + "; ".join(p.message for p in problems) + cites
    return RecipeUnsound(message, path=recipe.path, problems=problems)


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
        The argument list to run, in a directory Part 12 §4 leaves unspecified. A list rather than a
        string because a parse is a quoting convention no recipe declared (Part 05 §3.7).
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
        except DeclarationUnreadable as exc:
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
    recipe naming both -- a silent winner is what `owns` exists to prevent.
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
        Extension registries this packet carries (Part 09 §5.3), each named either by a **path** to a
        document beside the recipe, or by the **id** an installed distribution registers under
        `escapewheel.extensions`. Kept as written rather than resolved here, because which one a
        value is cannot be decided without looking at the filesystem and the installed
        distributions -- see `extensions.load`.
    registry : Path or None
        The registry to write against. Declared here rather than defaulted, because Part 04 §8 has
        the packet bind the registry it was written against -- so which one that is belongs in
        the parameters, not in whichever copy the tool happened to find.
    document : Mapping
        The parsed file as stated, carried whole so it can go into `core.processing_runs.parameters`.
    packet_id, description, session, subject, clocks, preferred_runs
        What a build writes into the manifest or a row itself, each less a credential the build
        recognizes (Part 05 §3.2).
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
    #: Every `[overrides]` entry, key to reason: field overrides (Part 05 §3.6) and column overrides
    #: (Part 05 §3.4), told apart by the key's segments.
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
    #: Part 05 §3.5: each `[drop]` entry, `resource.column` to why the recipe gives up its held values.
    drop: Mapping[str, str] = field(default_factory=dict)

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
        RecipeUnreadable
            If the file is not valid TOML, declares no packet ID, or fails the recipe schema.
        """
        path = Path(path)
        raw = path.read_bytes()
        try:
            document = tomllib.loads(raw.decode())
        except tomllib.TOMLDecodeError as exc:
            unreadable = [Problem(Level.ERROR, f"not valid TOML: {exc}", RecipeFault.NOT_TOML)]
            raise RecipeUnreadable(f"{path}: not valid TOML: {exc}", path=path, problems=unreadable) from exc

        packet = document.get("packet", {})
        if not packet.get("id"):
            unnamed = [Problem(Level.ERROR, "[packet] declares no id", RecipeFault.NO_PACKET_ID)]
            raise RecipeUnreadable(f"{path}: [packet] declares no id", path=path, problems=unnamed)
        if problems := shape_problems(document):
            raise RecipeUnreadable(
                f"{path}: not a recipe (Part 05 §3.1):\n  " + "\n  ".join(problems),
                path=path,
                problems=[Problem(Level.ERROR, problem, RecipeFault.RECIPE_SHAPE) for problem in problems],
            )

        # Absolute even where the recipe was named relative to the build's directory, because an
        # adapter is handed what this resolves and runs where Part 12 §4 leaves unspecified.
        here = path.absolute().parent
        # A member the build writes into a row or the manifest itself is read less a credential it
        # recognizes (Part 05 §3.2). What it opens or hands an adapter is read as stated.
        written = redacted(document)

        def resolve(value: str) -> Path:
            """Resolve one declared path against the recipe's own directory."""
            candidate = Path(value)
            return candidate if candidate.is_absolute() else here / candidate

        def resolve_root(value: str, storage: Mapping[str, Any]) -> Any:
            """Resolve a source root, which Part 05 §3.1 leaves free to name a store.

            A sorted asset may be a prefix on an object store, of which a build reads a small
            part, so naming the prefix is both shorter and better provenance than naming a
            staged copy (Part 05 §3.2).

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
            packet_id=str(written["packet"]["id"]),
            out=destination,
            registry=resolve(str(packet["registry"])) if packet.get("registry") else None,
            extensions=tuple(str(e) for e in packet.get("extensions", [])),
            description=written["packet"].get("description"),
            session=written.get("session", {}),
            subject=written.get("subject", {}),
            overrides=document.get("overrides", {}),
            encoding=document.get("encoding", {}),
            clocks=tuple(ClockSpec(**c) for c in written.get("clock", [])),
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
                        # of adapters installs together is a fact about the set; an entry narrows
                        # that to itself, and a `delivery` table opts it out (Part 05 §3.10).
                        in_process=bool(s.get("in_process", packet.get("in_process", False) and "delivery" not in s)),
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
            preferred_runs=tuple(written.get("preferred_run", ())),
            drop=document.get("drop", {}),
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
            resolve against core; core's never resolve against an extension, which Part 09 §6.1
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
        # Imported here because `recipe_check` imports this module.
        from .recipe_check import check

        return check(self, registry, extensions, held_tables=held_tables, held_clocks=held_clocks)

    @property
    def declared_facts(self) -> dict[str, Any]:
        """`block.field` to the value the recipe declares for it (Part 05 §3.4)."""
        blocks = {"session": self.session, "subject": self.subject}
        return {f"{block}.{k}": v for block, fields in blocks.items() for k, v in fields.items()}

    @property
    def field_overrides(self) -> dict[str, str]:
        """`block.field` to the reason the recipe's value for that field supersedes a source's (Part 05 §3.6)."""
        return {key: reason for key, reason in self.overrides.items() if key.count(".") == 1}

    @property
    def column_overrides(self) -> dict[str, str]:
        """`resource.column` to the reason the recipe gives up a passed-over source's value (Part 05 §3.4)."""
        return {key: reason for key, reason in self.overrides.items() if key.count(".") == 2}

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


def normalized_chosen_at(value: Any) -> datetime | None:
    """Return a `preferred_run` entry's `chosen_at` as a UTC timestamp, or None where it cannot be one.

    A local date-time or a bare date names no instant, so it is not normalized (Part 05 §3.5).
    """
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(UTC)


__all__ = [
    "RECIPE_SUPPLIES",
    "TERMS",
    "ClockSpec",
    "DeliverySpec",
    "MaterializeSpec",
    "Problem",
    "Recipe",
    "SourceSpec",
    "declared",
    "normalized_chosen_at",
    "payloads",
    "reached_by",
    "refusal",
    "schema",
    "shape_problems",
]

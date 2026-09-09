"""The session recipe: what a packet is built from, declared as a file rather than a script.

`05` Stage 3 requires normalization to be deterministic in declared parameters, and
`core.processing_runs` records the run that used them. A build script satisfies neither. Its
parameters are wherever its statements happen to put them, nothing can hash it, and the
`processing_run_id` a packet carries then names a run whose inputs are unrecoverable. A recipe
is that parameter set as one file, so the run record can carry the parameters themselves
(`core.processing_runs.parameters`) and a reader can see what produced the packet.

Nothing here opens a source or writes anything. Parsing and checking are separate from
building for the reason `05` gives -- *"do not combine source parsing, normalization,
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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
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

#: Resources the recipe supplies only where no source owns them (R87 §2.8). `core.subjects` left
#: RECIPE_SUPPLIES because the NWB states every column of it and the row was built and discarded;
#: a `[subject]` block is now the fallback for a packet whose sources name no subject.
RECIPE_MAY_SUPPLY = ("core.subjects",)

#: Where a resource goes when more than one adapter can produce it (R63 §2.2). The winner is the
#: source that knows most about it: the NWB knows a probe's type and manufacturer where the sorter
#: knows only the stream, and the waveform source is the only one that can see a unit's channel
#: support. Held here rather than in the scaffolder, so a draft and a build resolve alike.
PREFERRED = {
    "core.probes": "nwb",
    "core.unit_electrodes": "waveforms",
    "core.clocks": "sync",
    "core.array_assets": "nwb",
    "core.array_dimensions": "nwb",
}

#: Resources several sources each supply *part* of, which `owns` refuses and `contributes` is for.
#: A defaulted source contributes to these rather than owning them.
SHARED = frozenset({"core.clocks", "core.clock_anchors", "core.clock_observation_intervals",
                    "core.array_assets", "core.array_dimensions", "core.devices"})


def states(kind: str) -> Mapping[str, str]:
    """Return the recipe fields an adapter of this kind can state, to the attribute holding each.

    R87 §2.2 puts the obligation on the build rather than on the adapter, so a kind whose adapter
    declares nothing is reported by `check` rather than silently treated as stating nothing --
    which is the failure `produces` has, and which R63 §4 left open.
    """
    from . import sources

    adapter = sources.ADAPTERS.get(kind)
    declared = getattr(adapter, "STATES", None) if adapter is not None else None
    return dict(declared) if declared is not None else {}


def declares_states(kind: str) -> bool:
    """Whether this kind's adapter declares `STATES` at all, empty or not (R87 §2.2)."""
    from . import sources

    adapter = sources.ADAPTERS.get(kind)
    return adapter is not None and getattr(adapter, "STATES", None) is not None


def state_accessors(kind: str) -> Mapping[str, str]:
    """`STATES` entries whose named attribute the adapter class does not expose (R87 §2.2)."""
    from . import sources

    adapter = sources.ADAPTERS.get(kind)
    return {f: a for f, a in states(kind).items() if adapter is not None and not hasattr(adapter, a)}


def produces(kind: str) -> frozenset[str]:
    """Return what an adapter of this kind can supply (R63 §2.1).

    Imported here rather than at module load: `Recipe` is meant to be parseable without the
    adapters, and this is the one thing it needs from them. The adapters cost 0.16 s to import
    and open nothing, so a check that consults them still reports before any I/O.
    """
    from . import sources

    adapter = sources.ADAPTERS.get(kind)
    return frozenset(getattr(adapter, "PRODUCES", ()) if adapter is not None else ())


#: Options an adapter requires that a recipe must carry, because no inspection supplies them.
#: `session.py`'s `_build_source` pops these; a recipe missing one dies there on a KeyError
#: rather than being reported here, which is what `--check` exists to prevent.
REQUIRED_OPTIONS = {
    "nwb": ("zone",),
    "session": ("zone",),
}

#: Keys a `[[source]]` entry uses for itself; everything else is passed to the adapter.
_SOURCE_KEYS = frozenset({"kind", "root", "owns", "contributes", "storage_options"})

#: Keys a `[[materialize]]` entry uses for itself; the rest are the materializer's parameters.
_MATERIALIZE_KEYS = frozenset({"resource"})


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a recipe.

    Attributes
    ----------
    level : str
        ``error``, ``warning`` or ``info``. Only an error refuses the recipe; ``info`` records
        something the build will do, such as an override it will apply (R87 §2.3).
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
    #: R63 §2.2: whether the recipe stated `owns`. Silence means the whole of `PRODUCES`, so it
    #: must be distinguishable from an explicit empty list, which narrows to nothing.
    narrowed: bool = True

    @property
    def claims(self) -> tuple[str, ...]:
        """Every resource this source supplies, however it claims it."""
        return (*self.owns, *self.contributes)


def _resolve_ownership(sources: tuple[SourceSpec, ...]) -> tuple[SourceSpec, ...]:
    """Fill in `owns` for entries that declared none (R63 §2.2).

    Silence means the whole of that adapter's `PRODUCES`, less what an explicitly narrowed source
    already owns, less what the recipe itself writes, and less what a preference gives to another
    kind this recipe lists. A shared resource becomes a `contributes` rather than an `owns`,
    because several sources each supply part of it.

    Where two defaulted sources are left owning one resource, both keep it and `check` refuses the
    recipe naming both -- a silent winner is what `owns` was introduced to prevent.
    """
    narrowed = {resource for spec in sources if spec.narrowed for resource in spec.owns}
    supplies, kinds = frozenset(RECIPE_SUPPLIES), {spec.kind for spec in sources}
    resolved = []
    for spec in sources:
        if spec.narrowed:
            resolved.append(spec)
            continue
        owns, contributes = [], list(spec.contributes)
        for resource in sorted(produces(spec.kind) - narrowed - supplies):
            if resource in SHARED:
                if resource not in contributes:
                    contributes.append(resource)
                continue
            preferred = PREFERRED.get(resource)
            if preferred is not None and preferred != spec.kind and preferred in kinds:
                continue
            owns.append(resource)
        resolved.append(replace(spec, owns=tuple(owns), contributes=tuple(contributes)))
    return tuple(resolved)


@dataclass(frozen=True)
class MaterializeSpec:
    """An analysis resource to derive once the core resources are staged.

    `05` stages 8 and 9 put materialization inside the import pipeline rather than after it, so
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
        Extension registries this packet carries (R17 §2), each named either by a **path** to a
        document beside the recipe, or by the **id** an installed distribution registers under
        `escapewheel.extensions`. Kept as written rather than resolved here, because which one a
        value is cannot be decided without looking at the filesystem and the installed
        distributions -- see `extensions.load`.
    registry : Path or None
        The registry to write against. Declared here rather than defaulted, because R2 §8 has
        the packet embed the registry it was written against -- so which one that is belongs in
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
    #: R87 §2.5: `block.field` to the reason the recipe's value supersedes the source's.
    overrides: Mapping[str, str]
    clocks: tuple[ClockSpec, ...]
    sources: tuple[SourceSpec, ...]
    materialize: tuple[MaterializeSpec, ...]
    limits: Mapping[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> Recipe:
        """Read and parse a recipe.

        Parameters
        ----------
        path : str or Path
            The ``.toml`` file. Relative paths inside it resolve against its directory, so a
            recipe travels with the tree it describes.

        Returns
        -------
        Recipe
            The parsed recipe. Structural problems are reported by :meth:`check`, not raised
            here, so a caller sees every problem at once rather than the first.

        Raises
        ------
        ValueError
            If the file is not valid TOML, or declares no packet ID.
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

        here = path.parent

        def resolve(value: str) -> Path:
            """Resolve one declared path against the recipe's own directory."""
            candidate = Path(value)
            return candidate if candidate.is_absolute() else here / candidate

        def resolve_root(value: str, storage: Mapping[str, Any]) -> Any:
            """Resolve a source root, which `05` §3.1 leaves free to name a store.

            An AIND session's sorted asset is a prefix on `aind-open-data`, and a build reads
            about 12% of one, so naming the prefix is both shorter and better provenance than
            naming a staged copy (`05` §3.2).

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

        return cls(
            path=path,
            digest=hashlib.sha256(raw).hexdigest(),
            document=document,
            packet_id=str(packet["id"]),
            out=resolve(str(packet.get("out", packet["id"]))),
            registry=resolve(str(packet["registry"])) if packet.get("registry") else None,
            extensions=tuple(str(e) for e in packet.get("extensions", [])),
            description=packet.get("description"),
            session=document.get("session", {}),
            subject=document.get("subject", {}),
            overrides=document.get("overrides", {}),
            clocks=tuple(ClockSpec(**c) for c in document.get("clock", [])),
            sources=_resolve_ownership(
                tuple(
                    SourceSpec(
                        kind=str(s["kind"]),
                        root=resolve_root(str(s.get("root", ".")), s.get("storage_options", {})),
                        owns=tuple(s.get("owns", ())),
                        contributes=tuple(s.get("contributes", ())),
                        options={k: v for k, v in s.items() if k not in _SOURCE_KEYS},
                        narrowed="owns" in s,
                    )
                    for s in document.get("source", [])
                )
            ),
            materialize=tuple(
                MaterializeSpec(
                    resource=str(m["resource"]),
                    options={k: v for k, v in m.items() if k not in _MATERIALIZE_KEYS},
                )
                for m in document.get("materialize", [])
            ),
            limits=document.get("commit", {}),
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
        # R87 §2.8: the recipe supplies these only where no source owns them, so a `[subject]`
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

    def check(self, registry: Mapping[str, Any], extensions: Sequence[Mapping[str, Any]] = ()) -> list[Problem]:
        """Everything wrong with the recipe that is knowable without reading a source.

        Parameters
        ----------
        registry : Mapping
            A parsed registry document, supplying the table names and their references.
        extensions : sequence of Mapping
            Extension registries, whose tables a source may also own. An extension's references
            resolve against core; core's never resolve against an extension, which R17 §2
            requires by forbidding core to reference one at all.

        Returns
        -------
        list of Problem
            Empty when the recipe is sound. Errors first, then warnings, each sorted, so two
            runs of the same recipe report identically.
        """
        tables = dict(registry["tables"])
        for document in extensions or ():
            tables.update(document["tables"])
        owners, claimants = self.owners, self.claimants
        errors: list[str] = []
        warnings: list[str] = []

        for resource, kinds in sorted(claimants.items()):
            if resource not in tables:
                errors.append(f"{kinds[0]} supplies {resource}, which the registry does not define")
        for resource, kinds in sorted(owners.items()):
            if len(kinds) > 1:
                errors.append(
                    f"{resource} is owned by {len(kinds)} sources ({', '.join(sorted(kinds))}); use contributes"
                )
            elif len(claimants.get(resource, ())) > 1:
                others = sorted(set(claimants[resource]) - set(kinds))
                errors.append(f"{resource} is owned by {kinds[0]} but also supplied by {', '.join(others)}")

        warnings.extend(self._unclaimed())
        errors.extend(self._dangling_references(tables, claimants, warnings))
        errors.extend(self._clock_problems())
        errors.extend(self._option_problems())
        errors.extend(self._states_problems())
        fact_errors, fact_warnings, notes = self._declared_fact_problems()
        errors.extend(fact_errors)
        warnings.extend(fact_warnings)

        return (
            [Problem("error", m) for m in sorted(set(errors))]
            + [Problem("warning", m) for m in sorted(set(warnings))]
            + [Problem("info", m) for m in sorted(set(notes))]
        )

    def _states_problems(self) -> list[str]:
        """Adapters a build cannot ask which recipe fields they state (R87 §2.2).

        Refused rather than defaulted: an adapter that declares nothing would otherwise read as
        one that states nothing, which is the failure R63 §4 records for `PRODUCES`.
        """
        problems = []
        for kind in sorted({spec.kind for spec in self.sources}):
            if not declares_states(kind):
                problems.append(f"source {kind} declares no STATES, so a build cannot tell what facts it states")
            for fact, attribute in sorted(state_accessors(kind).items()):
                problems.append(
                    f"source {kind} states {fact} through {attribute!r}, which its adapter does not expose"
                )
        return problems

    @property
    def declared_facts(self) -> dict[str, Any]:
        """`block.field` to the value the recipe declares for it (R87 §2.2)."""
        blocks = {"session": self.session, "subject": self.subject}
        return {f"{block}.{k}": v for block, fields in blocks.items() for k, v in fields.items()}

    def stated_by(self) -> dict[str, list[str]]:
        """`block.field` to the source kinds in this recipe that state it (R87 §2.2)."""
        by_field: dict[str, list[str]] = {}
        for kind in sorted({spec.kind for spec in self.sources}):
            for fact in states(kind):
                by_field.setdefault(fact, []).append(kind)
        return by_field

    def _declared_fact_problems(self) -> tuple[list[str], list[str], list[str]]:
        """Errors, warnings and notes about declared facts and their overrides (R87 §2.3, §2.5).

        Only an empty override reason is an error. A field a source states is a warning because
        agreement is the likely case and only the build can tell, and a stale override costs a
        line rather than a build because it leaves the packet correct.
        """
        declared, stated = self.declared_facts, self.stated_by()
        errors: list[str] = []
        warnings: list[str] = []
        notes: list[str] = []
        for fact, reason in sorted(self.overrides.items()):
            if not str(reason).strip():
                errors.append(f"[overrides] {fact} carries no reason; an override must say why (R87 §2.5)")
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
        self, tables: Mapping[str, Any], supplied: Mapping[str, list[str]], warnings: list[str]
    ) -> list[str]:
        """Foreign keys from an owned table into a table no source produces.

        Severity follows the column: a **required** foreign key into an absent table means
        every row dangles, so the packet cannot validate. A **nullable** one may be legitimately
        empty, so it is a warning -- and worth saying, because `generate(only=...)` silently
        skips a foreign-key check whose target is absent, which is the quiet version of the
        same problem.
        """
        problems = []
        for resource in sorted(supplied):
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
        """Resources a listed source can produce that nothing in this recipe claims (R63 §2.3).

        A warning and not an error: narrowing is legitimate, and only the recipe's author knows
        whether this one was meant. It is the first of the three ways a recipe loses a resource,
        moved from the middle of a build to before a byte is read.
        """
        claimed = {resource for spec in self.sources for resource in spec.claims}
        claimed.update(RECIPE_SUPPLIES)
        return [
            f"{spec.kind} can produce {resource}, which no source in this recipe claims"
            for spec in self.sources
            for resource in sorted(produces(spec.kind) - claimed)
        ]

    def _option_problems(self) -> list[str]:
        """Options a source kind requires and this recipe does not carry."""
        return [
            f"source {spec.kind} requires {option!r}, which this entry does not set"
            for spec in self.sources
            for option in REQUIRED_OPTIONS.get(spec.kind, ())
            if option not in spec.options
        ]

    def _clock_problems(self) -> list[str]:
        """Clock IDs that are declared twice, referenced but absent, or parented to nothing."""
        declared = [c.clock_id for c in self.clocks]
        known = set(declared)
        problems = [
            f"clock {c} is declared more than once" for c in sorted({c for c in declared if declared.count(c) > 1})
        ]
        reference = self.session.get("reference_clock_id")
        if reference and reference not in known:
            problems.append(f"session.reference_clock_id is {reference!r}, which no [[clock]] declares")
        for clock in self.clocks:
            if clock.parent_clock_id and clock.parent_clock_id not in known:
                problems.append(f"clock {clock.clock_id} names parent {clock.parent_clock_id!r}, which is not declared")
        return problems


__all__ = ["RECIPE_SUPPLIES", "REQUIRED_OPTIONS", "ClockSpec", "MaterializeSpec", "Problem", "Recipe", "SourceSpec"]

"""Build a packet from a recipe.

This is Part 05 §2's build, delivery through publication, with the parameters supplied rather
than written into the code. The recipe says which sources exist and which resources each is
responsible for; this module orders them, runs them, keeps what each one owns, and commits.

**Ordering comes from the adapters, not from the registry.** A foreign key constrains
validity, not write order -- Parquet files are independent and `core.spike_events` can be
written before `core.units` with nothing the worse. What actually sequences a build is
data-flow between adapters: `NWBSource` needs the sorter's units to attach a unit to an
electrode, and no reference in the registry says so, because the dependency is between
adapters rather than between tables. So each adapter declares `CONSUMES` (Part 05 §3.4), and the
declarations are short because there is little of it.

**Ownership is what stops two sources fighting.** Four adapters can each produce
`core.probes`, and without a rule the last one to run wins silently -- which is how a
`probe_id` collapse matched 0 of 6,781 units, and how two sources emitting
`core.unit_electrodes` collided on its primary key. A source's records are filtered to what
the recipe says it owns, so the resolution is declared in one place a reader can see.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from functools import partial
from math import ceil
from pathlib import Path
from typing import Any

import numpy as np
from escapewheel_reader.clocks import BOUND, align
from escapewheel_validator import CheckedRegistryContext, RegistryRejected, check_registry_context
from numpy.typing import NDArray

from . import opaque
from .extensions import load_checked as load_extension_context
from .recipe import RECIPE_SUPPLIES, TERMS, Recipe, SourceSpec, declared, payloads, reached_by, redacted
from .sources import ADAPTERS, SourceDefect
from .sources.compensations import describe
from .sources.store import cache_directory
from .writer import PacketWriter

#: Analysis resources a recipe may ask for by name, and the function that derives each from a
#: staged packet. Part 06 §2 makes these disposable, so a recipe that names none is complete.
MATERIALIZERS: dict[str, str] = {"analysis.spike_events": "spike_events"}


#: Rows per batch when streaming a spike table into staging, and therefore the row-group size:
#: `_write_stream` makes one row group per batch, so the caller owns the boundaries.
#:
#: **Sized for pruning, not for the fetch band, and that is a measured choice.** Four million
#: rows would put a row group at 9.6 MB, inside the 8-16 MB band `writer.row_group_rows`
#: derives for object storage — but no reader we have prunes below a row group, so quadrupling
#: it quadruples what a predicate must read. A one-second window over 287 M spikes, cold:
#:
#: ..  1M rows, no page index   293 groups   681.6 MB   pyarrow 1.93 s   duckdb 0.35 s
#: ..  1M rows + page index     291 groups   682.4 MB   pyarrow 2.13 s
#: ..  4M rows + page index      77 groups   691.7 MB   pyarrow 4.42 s   duckdb 0.34 s
#:
#: The page index is written anyway, but on someone else's behalf: neither reader here consults
#: it. DuckDB says so outright (duckdb#2755, closed as "not supported… mostly improves point
#: queries which is not what DuckDB is focused on") and measures identically with it and without;
#: pyarrow's `filters=` prunes at row-group granularity too. arrow-rs and DataFusion do use it.
#: So the row group is both the fetch unit and the prune unit for us, and pruning is what costs.
BATCH_ROWS = 1_000_000

#: The most error a mapping may carry before Part 01 §3.9 calls it undefined, in **seconds**.
#:
#: A duration rather than a tick count, because it is a claim about time and not about one
#: clock's granularity. Three milliseconds is R40's default: above every measured p95 by a
#: factor of four or more -- the estimator costs 117 µs at the two anchor intervals this
#: session needs, and 805 µs at a hundred and twenty -- while staying far below anything that
#: moves an analysis, the finest PSTH bin measured against this format being 30 ms.
#:
#: R37 §3.3's original default of one parent tick is 32 µs, which is *below* the estimator's
#: own median at every distance, so it gated on measurement noise: this session passed it by
#: 4%, and failing would have stranded the first 1.7 s of every stream.
TOLERANCE = 3e-3


class RecipeError(Exception):
    """A recipe cannot be built: a source kind is unknown, or its dependencies do not order."""


@dataclass
class Context:
    """What earlier sources produced, for the sources that consume it.

    Attributes
    ----------
    session_id : str
        The session every adapter is scoped to.
    sources : dict
        Kind to the adapter instance, once built.
    units : list of dict
        One record per unit: the probe and the sorter's label for it, and the identifier
        assigned. The join key the NWB and the sorter meet on -- the sorter mints unit identity,
        the NWB places it in space -- carried as rows rather than as a mapping, because a
        compound key does not survive the crossing (Part 03 §11.2). One identity column, not
        three: `core.units` is keyed on `unit_id` alone (Part 02 §12.1), and the tables an
        adapter puts this on declare no other.
    clocks : dict
        Clock ID to that clock's `core.clocks` row, for a source placing an array axis on one.
        An axis advances in ticks (R20 §2), so a step cannot be derived without the rate, and
        the row is what carries it.
    stores : dict
        Resolved source root to its open store. Three adapters in a real recipe read the same
        `.nwb`; sharing the store means they cannot disagree about what is in it, and stops the
        electrode table being parsed once per adapter.
    stated : dict
        Resource to source kind to the rows that kind produced, for the resources the recipe
        declares a preference for. Held so Part 05 §3.4 can compare the winner's row against the
        one it displaced, and bounded to those resources.
    """

    session_id: str
    sources: dict[str, Any] = field(default_factory=dict)
    units: list[dict[str, Any]] = field(default_factory=list)
    clocks: dict[str, dict[str, Any]] = field(default_factory=dict)
    stores: dict[Path, Any] = field(default_factory=dict)
    stated: dict[str, dict[str, list[dict[str, Any]]]] = field(default_factory=dict)
    #: The reference clock, as the recipe declares it and the build locates it. `_reference`
    #: fills `tick_zero_utc` once a source carrying the stamps has run; an adapter uses the
    #: row it is handed and never rewrites it.
    reference: Any = None
    #: `core.event_streams` IDs the NWB declared, which the observation windows cover.
    event_streams: list[str] = field(default_factory=list)
    #: Per source, the window it declared on the reference clock, in that clock's ticks. One
    #: source states a window and another states the streams watched in it, so the rows pairing
    #: them are composed here rather than by either (Part 05 §3.4).
    windows: dict[str, tuple[int, int]] = field(default_factory=dict)
    #: `core.clock_anchors` rows, whatever source produced them, since the alignment every later
    #: conversion uses is fitted across all of them.
    anchors: list[dict[str, Any]] = field(default_factory=list)
    #: Session facts a source derived that the recipe does not state, merged into
    #: `core.sessions` after every source has run.
    session_extra: dict[str, Any] = field(default_factory=dict)
    #: `core.clock_observation_intervals` rows, whatever source produced them, since R39's
    #: origin is a minimum across all of them and no single adapter sees them all.
    observed: list[dict[str, Any]] = field(default_factory=list)
    #: What `_bound_for` measured, for the import run's parameters (Part 01 §3.9, §4).
    measured_bound: dict[str, Any] = field(default_factory=dict)
    #: The anchors and the bound, once `alignment` has settled them.
    _alignment: tuple[dict[str, Any], float] | None = None
    #: Where a source delivered out of process writes: one directory per kind, beside the packet
    #: rather than inside it, so a delivery lands on the filesystem the packet is going to and a
    #: failed build leaves it where it can be looked at.
    workspace: Path = Path()
    #: The packet's staging area, prepared before any source runs, so an array a source writes
    #: there moves into the packet by rename at commit (Part 03 §11.3).
    staging: Path = Path()
    #: The build's progress reporter, for the stages that happen inside one source rather than
    #: between them -- a delivery being the one that can take minutes on its own.
    say: Callable[[str], None] = lambda _: None
    #: What the build itself observed, reported beside the adapters' own notes.
    notes: list[str] = field(default_factory=list)
    #: Part 05 §3.6: `block.field` to the registry type the packet stores it as, so a declared
    #: value and a stated one are compared after both are normalized, not as they were written.
    fact_types: dict[str, str] = field(default_factory=dict)
    #: Source kind to the `opaque_location` supplied it, which the build reads back once it has run.
    opaque_locations: dict[str, Path] = field(default_factory=dict)
    #: The loaded registries' opaque singletons, which a source owns and delivers as a payload
    #: rather than as rows (Part 03 §11.3), so no table for one is asked for or staged.
    payloads: frozenset[str] = frozenset()

    def alignment(self) -> tuple[dict[str, Any], float]:
        """Return the anchors and the bound to map at, measured once and kept.

        Every mapping in a build has to use the same bound, or the packet says one thing about
        which ticks are convertible and its own origin says another.
        """
        if self._alignment is None:
            by_clock = _anchors(self)
            reach = {row["clock_id"]: (int(row["start_tick"]), int(row["stop_tick"])) for row in self.observed}
            rate = self.reference.tick_rate_num / (self.reference.tick_rate_den or 1) if self.reference else 1.0
            bound, self.measured_bound = _bound_for(by_clock, reach, TOLERANCE, rate)
            self._alignment = (dict(by_clock), bound)
        return self._alignment


def order(recipe: Recipe) -> list[SourceSpec]:
    """Order sources so every one runs after what it consumes.

    Parameters
    ----------
    recipe : Recipe
        The parsed recipe.

    Returns
    -------
    list of SourceSpec
        The sources, in an order that satisfies every adapter's `CONSUMES`.

    Raises
    ------
    RecipeError
        If a source consumes a kind the recipe does not declare, or the dependencies cycle.
    """
    remaining = list(recipe.sources)
    kinds = {s.kind for s in remaining}
    for spec in remaining:
        missing = [k for k in declared(spec)["consumes"] if k not in kinds]
        if missing:
            raise RecipeError(f"source {spec.kind} consumes {', '.join(missing)}, which the recipe does not declare")

    ordered: list[SourceSpec] = []
    done: set[str] = set()
    while remaining:
        ready = [s for s in remaining if set(declared(s)["consumes"]) <= done]
        if not ready:
            stuck = ", ".join(sorted(s.kind for s in remaining))
            raise RecipeError(f"sources {stuck} depend on each other and cannot be ordered")
        ordered.extend(ready)
        done.update(s.kind for s in ready)
        remaining = [s for s in remaining if s not in ready]
    return ordered


def _terms(spec: SourceSpec, recipe: Recipe, context: Context, needed: Collection[str]) -> dict[str, Any]:
    """Return what this build can fill of Part 03 §11.2's vocabulary, for this source.

    A term absent from the result is one this recipe cannot fill, which is a refusal rather than an
    omission: an adapter cannot tell a term nobody filled from one whose value is legitimately
    empty. Only what `needed` names is resolved, since resolving the reference clock can itself
    refuse and a source that asks for none should not be held to it.
    """
    terms: dict[str, Any] = {"root": spec.root, "session_id": context.session_id}
    if "reference_clock" in needed:
        # The row, not the object: everything a build supplies is data (Part 03 §11.2).
        terms["reference_clock"] = _reference(recipe, context).record()
    if "clocks" in needed and context.clocks:
        terms["clocks"] = [context.clocks[clock_id] for clock_id in sorted(context.clocks)]
    if "units" in needed and context.units:
        terms["units"] = context.units
    if "array_location" in needed:
        # One directory per source (Part 03 §11.3), since two sources may each deliver an asset of
        # one name, and supplied empty (Part 05 §2), since a build binds what it finds by name.
        location = context.staging / "deliveries" / spec.kind
        if location.exists():
            shutil.rmtree(location)
        terms["array_location"] = str(location)
    if "opaque_location" in needed:
        # One directory per source for the same reason, apart from `array_location`'s so neither
        # delivery can pass for the other (Part 03 §11.3).
        location = context.staging / opaque.DELIVERIES / spec.kind
        if location.exists():
            shutil.rmtree(location)
        context.opaque_locations[spec.kind] = location
        terms["opaque_location"] = str(location)
    if "wanted" in needed:
        # Settled before any source is opened (Part 05 §3.4), so a source told what is wanted may
        # extract no more -- and one that is not told produces everything and a build discards.
        # What the recipe claims plus what this build harvests: a resource the recipe leaves
        # unclaimed may still be the one a later source needs, and narrowing it away would lose
        # a fact rather than a table.
        terms["wanted"] = sorted(set(spec.claims) | (set(HARVESTED) & set(declared(spec)["produces"])))
    return terms


def _reference(recipe: Recipe, context: Context) -> Any:
    """Return the reference clock as it stands, located in wall clock where a build can.

    `tick_zero_utc` is not declared by any source; it is derived by the one holding the record
    nodes' stamps, which states it on its own `core.clocks` row. So it can only be filled once
    that source has run, and an adapter built before it is handed a clock without one -- which is
    what it would have had anyway. Kept on the context, so every later adapter and the packet's
    own row agree.
    """
    clock = context.reference or _reference_clock(recipe, context)
    if clock.tick_zero_utc is None:
        located = context.clocks.get(clock.clock_id, {}).get("tick_zero_utc")
        if located is not None:
            clock = replace(clock, tick_zero_utc=_stored(located, "timestamp"))
    context.reference = clock
    return clock


def _supplied(spec: SourceSpec, recipe: Recipe, context: Context) -> dict[str, Any]:
    """Return what a build supplies this source, resolved against what it declares (Part 05 §3.4).

    Each name in the declaration resolves against Part 03 §11.2's terms first and the recipe's
    options second, and a name resolving to neither is refused -- which `Recipe.check` reports
    before anything is opened, so reaching the refusal here means the recipe was not checked.

    The recipe's remaining options travel too, under `options`, so no option can collide with a
    term. They are the ones an adapter can run without, which Part 03 §11.2 gives no way to
    declare: a declared name a recipe does not set resolves to nothing, so declaring one would
    make it mandatory.
    """
    names = declared(spec)["needs"]
    terms = _terms(spec, recipe, context, names)
    supplied: dict[str, Any] = {}
    for name in names:
        if name in TERMS:
            if name not in terms:
                raise RecipeError(f"source {spec.kind} needs {name!r}, which this recipe cannot fill")
            supplied[name] = terms[name]
        elif name not in spec.options:
            raise RecipeError(f"source {spec.kind} needs {name!r}, which this entry does not set")
    return {**supplied, "options": dict(spec.options)}


def _build_source(spec: SourceSpec, recipe: Recipe, context: Context) -> Any:
    """Construct one adapter, or run it and read what it delivered (Part 05 §3.9).

    One construction for every kind, built-in or registered by another distribution, and one
    delivery for every source the recipe does not run in this process. What a source is handed is
    the same either way -- it is the same JSON object, written down for a command and passed as
    keywords for a class -- so which route a source took reaches nothing downstream.
    """
    import inspect

    from . import delivery
    from .sources import discovered
    from .sources.store import store_for

    supplied = _supplied(spec, recipe, context)
    options = supplied.pop("options")
    if (protocol := reached_by(spec)) is not None and spec.delivery is not None:
        # The URI rather than the root this build resolved, and the options that open it beside
        # it: the other process opens the source for itself (Part 03 §11.2), and what it is
        # handed has to be enough to.
        crossing = {**supplied, "root": spec.uri or str(spec.root)}
        if spec.storage_options:
            options = {**options, "storage_options": dict(spec.storage_options)}
        return delivery.fetch(
            spec.kind,
            spec.delivery.command,
            {**crossing, "options": options},
            protocol=protocol,
            wanted=[resource for resource in spec.claims if resource not in context.payloads],
            states=declared(spec)["states"],
            merged=spec.contributes,
            report_path=spec.delivery.report_path,
            workspace=context.workspace / spec.kind,
            say=context.say,
        )

    adapter = ADAPTERS.get(spec.kind) or discovered().get(spec.kind)
    if adapter is None:
        known = ", ".join(sorted({*ADAPTERS, *discovered()}))
        raise RecipeError(f"unknown source kind {spec.kind!r}; known kinds are {known}")
    # In process, adapters reading one Zarr root share an open store, so they cannot disagree about
    # what is in it and the electrode table is parsed once. A handle is not something an adapter may
    # declare (Part 03 §11.2), so it is supplied where the class accepts one rather than from a
    # table of kinds -- and an adapter out of process is handed none and opens its own.
    if "store" in inspect.signature(adapter).parameters:
        options.setdefault("store", store_for(spec.root, context.stores))
    return adapter(supplied.pop("root"), **supplied, **options)


def _reference_clock(recipe: Recipe, context: Context) -> Any:
    """Return the clock an adapter that needs one is given: the session's declared reference."""
    wanted = recipe.session.get("reference_clock_id")
    for spec in recipe.clocks:
        if spec.clock_id == wanted:
            return spec.clock(context.session_id)
    raise RecipeError(f"no [[clock]] declares {wanted!r}, which [session].reference_clock_id names")


#: Part 05 §3.6: facts whose difference refuses a build rather than being reported. A subject is not
#: scoped to a session (Part 02 §7.1), so a wrong one agrees with another packet's animal instead of
#: colliding with the true value, and nothing downstream can detect it.
REFUSES_ON_DIFFERENCE = frozenset({"subject.subject_id"})

#: Part 05 §3.6's third disposition: facts where the source's value is written and the recipe's is
#: reported. Both ends of a session are derived from the acquisition windows a source declares, so
#: a hand-typed one transcribes that derivation rather than competing with it -- where a subject is
#: a fact about the world that the recipe may legitimately correct.
SOURCE_WINS = frozenset({"session.session_start_time", "session.session_end_time"})

#: The recipe block each resource's fields are declared in, for Part 05 §3.6's comparison type.
FACT_BLOCKS = {"session": "core.sessions", "subject": "core.subjects"}


def _fact_types(registry: Mapping[str, Any]) -> dict[str, str]:
    """`block.field` to the registry type the packet stores it as (Part 05 §3.6)."""
    return {
        f"{block}.{column['name']}": column["type"]
        for block, resource in FACT_BLOCKS.items()
        for column in registry["resources"].get(resource, {}).get("table", {}).get("columns", ())
    }


def _stored(value: Any, declared_type: str | None) -> Any:
    """Return a stated value as the type the packet stores it as, not as the text it crossed as.

    `_normalized` reduces two spellings to one for comparison; this is the other direction, and
    it is needed because a value that crossed a process boundary is a string whatever it means.
    """
    if value is None or declared_type not in {"timestamp", "date"}:
        return value
    if isinstance(value, datetime):
        return value.date() if declared_type == "date" else value
    if isinstance(value, date):
        return value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.date() if declared_type == "date" else parsed


def _normalized(value: Any, declared_type: str | None) -> Any:
    """Reduce a value to the type the packet stores it as, so two spellings compare equal.

    `session.json` states a subject as the number 776259 where a recipe declares the string
    `"776259"`, and an NWB states a date of birth as a timestamp where R4 §3.3 makes the column a
    calendar date. Comparing what was written would refuse both. A wall clock is the same problem
    with more spellings -- `Z` against `+00:00`, and a `T` against the space `str` puts there -- so
    it is compared as the instant it names rather than as the text either side wrote.
    """
    if value is None:
        return None
    if declared_type == "timestamp":
        return _stored(value, "timestamp")
    if declared_type == "date":
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    return str(value)


def _compare_declared_facts(spec: SourceSpec, source: Any, context: Context, recipe: Recipe) -> None:
    """Compare what the recipe declares against what this source states (Part 05 §3.6).

    Three dispositions, and which one applies is the fact's rather than the source's. A fact that
    identifies something a reader resolves across packets refuses the build, since nothing
    downstream can detect a wrong one. A fact the source derives and the recipe transcribes is
    written from the source. Everything else is the ordinary case, where a recipe correcting a
    source is legitimate and the difference is reported.

    A source that states a fact the recipe does not declare is not comparing anything, and its
    value is taken: which is how `core.sessions` gets both its ends from the windows a session
    source declares, whether that source ran here or delivered them from elsewhere.
    """
    declared, notes = recipe.declared_facts, getattr(source, "notes", context.notes)
    for fact, attribute in sorted(getattr(source, "STATES", {}).items()):
        stated = getattr(source, attribute, None)
        block, _, field = fact.partition(".")
        if stated is not None and fact in SOURCE_WINS and block == "session":
            context.session_extra[field] = _stored(stated, context.fact_types.get(fact))
        if fact not in declared:
            continue
        want = declared[fact]
        reason = recipe.overrides.get(fact)
        if stated is None:
            # Part 05 §3.6: silence is a fact about the source, not a disagreement -- but it is
            # reported, so a build log tells a verified fact from an asserted one.
            notes.append(f"{fact} {want!r} went unchecked; {spec.kind} states none")
            continue
        column = context.fact_types.get(fact)
        if _normalized(stated, column) == _normalized(want, column):
            if reason is not None:
                notes.append(f"{fact} declares an override and {spec.kind} states the same value")
            continue
        if reason is not None:
            notes.append(f"{fact} is {want!r} over {spec.kind}'s {stated!r}: {reason}")
        elif fact in REFUSES_ON_DIFFERENCE:
            raise SourceDefect(
                f"{fact} is {want!r} and {getattr(source, 'path', spec.kind)} states {stated!r}; "
                "a declared fact differs from the source that states it, with no override (Part 05 §3.6)"
            )
        elif fact in SOURCE_WINS:
            notes.append(f"{fact} is {want!r} and {spec.kind} derives {stated!r}; the source's value is used")
        else:
            notes.append(f"{fact} is {want!r} and {spec.kind} states {stated!r}; the recipe's value is used")


#: What a build takes from a source for the sources after it, beyond what the recipe claims. Each
#: is read from the rows a source produced rather than by asking the source, so a source delivered
#: out of process -- a process that has exited by the time this runs -- is harvested the same way.
HARVESTED = (
    "core.units",
    "core.clocks",
    "core.event_streams",
    "core.clock_anchors",
    "core.clock_observation_intervals",
)


def _rows(source: Any, records: Mapping[str, list[dict[str, Any]]]) -> Callable[[str], list[dict[str, Any]]]:
    """Return a reader for one source's rows, whichever way they reached this process.

    An adapter in this process hands over records; one delivered out of process hands over a
    table or a file, which `Delivered.rows` reads again for each caller. Either way the harvest
    asks the same question of the same rows.
    """

    def rows(resource: str) -> list[dict[str, Any]]:
        if resource in records:
            return records[resource]
        reader = getattr(source, "rows", None)
        return list(reader(resource)) if reader is not None else []

    return rows


def _harvest(
    spec: SourceSpec,
    source: Any,
    context: Context,
    recipe: Recipe,
    rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Take from what a source produced whatever the sources after it consume.

    Keyed on the resource rather than on the kind, for the reason `_composed` is: which adapter
    declared a clock is not what makes it a clock, and a build that dispatched on the kind could
    only harvest from the kinds it was written against.
    """
    if units := rows("core.units"):
        # The NWB names a quad-base probe's shanks separately and the sorting run ID ends in
        # exactly that name, while probe_id collapses to the physical probe.
        context.units += [
            {
                "device_name": row["sorting_run_id"].rsplit(".", 1)[-1],
                "local_unit_label": row["local_unit_label"],
                "unit_id": row["unit_id"],
            }
            for row in units
        ]
    for row in rows("core.clocks"):
        # Merged rather than replaced: `core.clocks` is shared, so two sources may each state
        # part of one clock -- a rate here, a located tick 0 there -- and the last to run must
        # not erase what the first knew.
        known = context.clocks.setdefault(str(row["clock_id"]), {})
        known.update({column: value for column, value in row.items() if value is not None})
    context.anchors += rows("core.clock_anchors")
    context.event_streams += [row["event_stream_id"] for row in rows("core.event_streams")]
    if (reference := context.reference) is not None:
        # The window this source watched the reference clock over, which the build pairs with the
        # streams another source declared. Kept per source: two sources may each declare a window
        # on one clock -- a sync train and an acquisition are both true -- and only the one that
        # comes with the resource being composed says when those streams were watched.
        for row in rows("core.clock_observation_intervals"):
            if row["clock_id"] == reference.clock_id:
                context.windows[spec.kind] = (int(row["start_tick"]), int(row["stop_tick"]))
    _compare_declared_facts(spec, source, context, recipe)


def _declared_start(recipe: Recipe) -> datetime | None:
    """Return the recipe's own `session_start_time`, parsed, or None where it declares none."""
    raw = recipe.session.get("session_start_time")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))


def _anchors(context: Context) -> dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Return every anchor a source produced as arrays per clock, in the shape `align` wants."""
    collected: dict[str, tuple[list[int], list[int]]] = {}
    for row in context.anchors:
        at, parent = collected.setdefault(row["clock_id"], ([], []))
        at.append(row["t_tick"])
        parent.append(row["parent_tick"])
    return {
        clock: (np.array(at, dtype=np.int64), np.array(parent, dtype=np.int64))
        for clock, (at, parent) in collected.items()
    }


def _bound_for(
    by_clock: Mapping[str, tuple[NDArray[np.int64], NDArray[np.int64]]],
    reach: Mapping[str, tuple[int, int]],
    tolerance: float,
    rate: float,
) -> tuple[float, dict[str, Any]]:
    """Choose the bound to map at, measuring it as Part 01 §3.9 requires.

    A packet whose earliest data sits inside one median anchor interval of its first anchor
    needs nothing; Part 01 §3.9's default covers it and this returns it unmeasured. Where it does
    not -- and withholding a displaced first anchor (Part 02 §12.6) is what usually makes it not --
    the writer may go further only by measuring the estimator at the distance it intends to
    use and finding its **95th percentile** within `tolerance` (Part 01 §3.9). The median is not a
    statement about what a consumer may rely on.

    Parameters
    ----------
    by_clock : Mapping
        Anchor pairs per clock.
    reach : Mapping
        Clock ID to the span that must map, which is the clock's own observation window. Both
        ends count: a session whose sync train stops well before its recording does needs the
        bound at the far end, and only the window says so.
    tolerance : float
        The most error the mapping may carry, in seconds (Part 01 §3.9).
    rate : float
        The parent clock's rate in hertz, which turns that duration into the parent ticks the
        measurement is in.

    Returns
    -------
    tuple
        The bound in median anchor intervals, and the measurement, for the run's parameters.
    """
    from escapewheel_reader.clocks import extrapolation_error

    needed = 0.0
    for clock, (at, _) in by_clock.items():
        if (window := reach.get(clock)) is None:
            continue
        interval = float(np.median(np.diff(at)))
        needed = max(needed, (at[0] - window[0]) / interval, (window[1] - at[-1]) / interval)
    if needed <= BOUND:
        return BOUND, {}

    distance = ceil(needed)
    allowed = tolerance * rate
    measured = {clock: extrapolation_error(at, parent, distance) for clock, (at, parent) in by_clock.items()}
    worst = max((m["p95"] for m in measured.values() if m), default=float("inf"))
    report: dict[str, Any] = {
        "distance": distance,
        "tolerance_seconds": tolerance,
        # Every statistic, so a reader may judge the packet by a stricter rule than the
        # writer applied (Part 01 §3.9).
        "p95_error_seconds": round(worst / rate, 9),
        "median_error_seconds": round(max((m["median"] for m in measured.values() if m), default=0.0) / rate, 9),
        "max_error_seconds": round(max((m["max"] for m in measured.values() if m), default=0.0) / rate, 9),
        "per_clock": {clock: {k: round(v, 2) for k, v in m.items()} for clock, m in measured.items() if m},
    }
    report["used"] = BOUND if worst > allowed else float(distance)
    return report["used"], report


def _time_origin(
    context: Context,
    intervals: list[dict[str, Any]],
    by_clock: Mapping[str, tuple[NDArray[np.int64], NDArray[np.int64]]],
    bound: float,
) -> int | None:
    """Part 01 §2.2: the earliest observation start among the session's clocks, on the reference.

    Returns None where any clock's window start cannot be mapped, since a minimum taken over
    some of the clocks is not the minimum Part 01 §2.2 requires a writer to declare -- and R39
    §2.4 says an origin the writer cannot compute is one it must not state.
    """
    reference = context.reference.clock_id if context.reference else None
    starts: list[int] = []
    for row in intervals:
        clock, start = row["clock_id"], int(row["start_tick"])
        if clock == reference:
            starts.append(start)
            continue
        if clock not in by_clock:
            return None
        converted, defined = align(np.array([start], dtype=np.int64), *by_clock[clock], bound=bound)
        if not defined[0]:
            return None
        starts.append(int(converted[0]))
    return min(starts) if starts else None


def _add_batches(
    writer: PacketWriter, spec: SourceSpec, source: Any, counts: dict[str, int], staged: Collection[str] = ()
) -> dict[str, int]:
    """Stream whatever a source streams, rather than holding it as Python mappings.

    `core.spike_events` is the case that forced the streaming path -- 10^8 rows, and a dict per
    row is two orders of magnitude more memory than the Parquet file it becomes. Any source may
    use it for any resource it claims, because an extension's table may be as large as a core
    one and nothing about the reason was ever specific to spikes.

    Returns
    -------
    dict
        Rows the source produced per resource, whether or not this spec claimed them, for
        `_unclaimed` to compare against the recipe.
    """
    produced: dict[str, int] = {}
    if hasattr(source, "spike_batches"):
        # Counted from the arrays' headers, so an unclaimed spike table still reports its size.
        produced["core.spike_events"] = source.spike_count
        if "core.spike_events" in spec.claims:
            writer.add_batches("core.spike_events", source.spike_batches(batch_rows=BATCH_ROWS))
            counts["core.spike_events"] = produced["core.spike_events"]
    streamed = getattr(source, "batches", None)
    if streamed is None:
        return produced
    offered = source.offers()
    for resource_id, batches in streamed().items():
        if resource_id in staged:
            # One table comes from one path, which is what keeps the declared sort enforceable:
            # a resource this build composed is already written, and what the source delivered
            # for it is the empty table it delivers for anything it has nothing to say about.
            continue
        produced[resource_id] = offered.get(resource_id, 0)
        if resource_id in spec.claims:
            writer.add_batches(resource_id, batches)
            counts[resource_id] = produced[resource_id]
    return produced


def _composed(spec: SourceSpec, context: Context) -> dict[str, list[dict[str, Any]]]:
    """Return the rows this build composes rather than any one source producing them.

    `core.event_stream_observation_intervals` is the case: one source declares the window it
    watched the reference clock over and another declares the streams watched in it, and
    Part 05 §3.3 leaves a row to a single source, so pairing them is the build's act. Keyed on
    what the spec claims rather than on its kind, since which source declared the window is not
    what decides the composition -- and paired with that source's own window, since two sources
    may each declare one on the reference clock and only one of them is these streams'.
    """
    resource = "core.event_stream_observation_intervals"
    window = context.windows.get(spec.kind)
    if resource not in spec.claims or window is None or not context.event_streams:
        return {}
    start, stop = window
    if stop < start:
        raise SourceDefect(f"{resource}: the acquisition window ends at {stop} and starts at {start}")
    # One window for every stream, because they come from a single acquisition: a stream with
    # 46 rewards was watched exactly as long as one with 2,641 licks, and giving each the extent
    # of its own events would make a rare event look frequent.
    return {
        resource: [
            {"event_stream_id": event_stream_id, "start_tick": start, "stop_tick": stop}
            for event_stream_id in context.event_streams
        ]
    }


def _derive(options: Mapping[str, Any], packet: Any, writer: Any) -> None:
    """Add one derived resource to a writer, reading its inputs from the staged packet."""
    from . import materialize

    materialize.into(packet, writer, **options)


def materializers(recipe: Recipe, memory_budget: int | str = 0) -> list[Callable[[Any, Any], None]]:
    """Turn a recipe's `[[materialize]]` entries into callables `commit` can run.

    Each is handed the staged packet and the writer, which is the pair `materialize.into` wants:
    it reads the core resources from the one and adds the derived rows, the run record and the
    lineage to the other.

    Parameters
    ----------
    recipe : Recipe
        The parsed recipe.
    memory_budget : int or str, optional
        Passed to any materializer that does not set its own. Bucketing a spike table is a
        transpose, so the partition either fits in memory or goes to disk, and which of those
        is sensible belongs to the machine rather than to the data.

    Returns
    -------
    list of callable
        In the order declared, since one derived resource may feed another.

    Raises
    ------
    RecipeError
        If a resource is named that nothing knows how to derive.
    """
    built: list[Callable[[Any, Any], None]] = []
    for spec in recipe.materialize:
        if spec.resource not in MATERIALIZERS:
            known = ", ".join(sorted(MATERIALIZERS)) or "nothing"
            raise RecipeError(f"no materializer for {spec.resource}; this writer derives {known}")
        options = dict(spec.options)
        if memory_budget and "memory_budget" not in options:
            options["memory_budget"] = memory_budget
        built.append(partial(_derive, options))
    return built


def build(  # noqa: C901
    recipe: Recipe,
    registry: Mapping[str, Any] | CheckedRegistryContext,
    *,
    extension_contexts: Collection[CheckedRegistryContext] | None = None,
    say: Callable[[str], None] = lambda _: None,
    strict: bool = False,
) -> PacketWriter:
    """Run every source and return a writer holding the packet, uncommitted.

    Parameters
    ----------
    recipe : Recipe
        The parsed recipe. Checked here as well as by a caller that reports every problem, since
        a build MUST refuse an unsound recipe before it opens any source (Part 05 §3.5).
    registry : Mapping
        The registry to write against.
    say : callable, optional
        Progress reporter.
    strict : bool, default False
        Refuse the build on any adapter note. A note is something the importer worked around --
        an absent column, a dropped timestamp, an offset that disagreed -- and every one is a
        place the packet says less than the source could have. Off by default because working
        around them is the point of an adapter; on in CI, where a new one is news.

    Returns
    -------
    PacketWriter
        Loaded with every record, ready to commit.
    """
    registry_context = registry if isinstance(registry, CheckedRegistryContext) else check_registry_context(registry)
    if registry_context.result.state != "valid":
        raise RegistryRejected("core", registry_context)
    checked_registry = registry_context.document
    assert isinstance(checked_registry, Mapping)
    if extension_contexts is None:
        extension_contexts = tuple(
            load_extension_context(named, registry_context, base=recipe.path.parent) for named in recipe.extensions
        )
    for extension_context in extension_contexts:
        if extension_context.result.state != "valid":
            document = extension_context.document
            subject = str(document.get("extension_id", "extension")) if isinstance(document, Mapping) else "extension"
            raise RegistryRejected(subject, extension_context)
    extension_documents = [extension.document for extension in extension_contexts]
    if errors := [p.message for p in recipe.check(checked_registry, extension_documents) if p.level == "error"]:
        raise RecipeError(f"{recipe.path}: refused, {len(errors)} error(s): " + "; ".join(errors))
    session_id = str(recipe.session["session_id"])
    # Reported rather than chosen here: `Recipe.load` places it, because a store root is opened
    # through a chained path that carries the location and is built as the recipe parses.
    say(f"source cache {cache_directory()}")
    context = Context(
        session_id=session_id,
        fact_types=_fact_types(checked_registry),
        workspace=Path(f"{recipe.out}.deliveries"),
        say=say,
        payloads=payloads(checked_registry, extension_documents),
    )
    if recipe.session.get("reference_clock_id"):
        context.reference = _reference_clock(recipe, context)
    writer = PacketWriter(
        registry_context,
        packet_id=recipe.packet_id,
        description=recipe.description,
        # Part 09 §2: the recipe names them, so a source may own an extension's table exactly as it
        # owns a core one. Which is what keeps declaring an extension from being harder than
        # adding a column to core -- the gradient that leaves NWB's own mechanism unused.
        extensions=tuple(extension_contexts),
        # Part 02 §7.1's fill needs the session before any source runs, and `core.sessions` is staged
        # last: three tables reached validation with a null `session_id` because of the order.
        session=session_id,
        # An extension reaches the writer across a file or a subprocess, so what it says about its
        # own columns arrives as recipe data rather than as a Python object it hands over.
        encoding_exceptions=_encoding_exceptions(recipe),
        workspace=context.workspace,
    )
    context.staging = writer.stage_at(recipe.out)

    # Part 05 §3.1: the recipe supplies `core.subjects` only where no source owns it, so a packet
    # whose NWB claims the table gets the row that file states rather than a hand-typed one.
    if recipe.subject and "core.subjects" not in recipe.owners:
        writer.add("core.subjects", [dict(recipe.subject)])

    counts: dict[str, int] = {}
    applied: list[str] = []
    #: Notes each source had said by the time it was run, so a later one can be told apart.
    drained: dict[str, int] = {}
    for spec in order(recipe):
        say(f"{spec.kind} -> {', '.join(spec.owns) or 'nothing it owns'}")
        source = _build_source(spec, recipe, context)
        context.sources[spec.kind] = source
        # Once, and used twice: an adapter's records are expensive to build, and the harvest and
        # the staging are two readings of one set of rows.
        records = source.records()
        _harvest(spec, source, context, recipe, _rows(source, records))

        produced = _add_records(writer, spec, records, context, counts, arbitrated=frozenset(recipe.preferred))
        produced.update(_add_batches(writer, spec, source, counts, staged=set(produced)))
        _note_unclaimed(spec, source, produced, frozenset(recipe.preferred))
        # Any adapter may stage arrays, not only the waveform one. A source that has them says
        # so by defining `staged_arrays`; the kind it happens to be is not the question.
        for staged in getattr(source, "staged_arrays", lambda: ())():
            # A delivered array is bytes an adapter already wrote (Part 03 §11.3), so what there
            # is to say about it is what is on disk; one staged in process is values, and its
            # shape is what a reader of the log wants before it costs anything to write.
            if staged.values is None:
                written = sum(f.stat().st_size for f in staged.written.rglob("*") if f.is_file())
                say(f"  array {staged.resource_id} delivered, {written / 1e6:.1f} MB written")
            else:
                say(
                    f"  array {staged.array_asset_id} {staged.values.shape} {staged.values.dtype}, "
                    f"{staged.values.nbytes / 1e6:.1f} MB raw"
                )
            writer.add_array(staged.resource_id, staged)
        # Any adapter may reference an array, not only the LFP one: a source says so by defining
        # `external_arrays`, and what kind it happens to be is not the question (Part 04 §5.1).
        for resource_id, array in getattr(source, "external_arrays", dict)().items():
            writer.reference_array(resource_id, array)
            say(f"  referenced {resource_id}")
        # Any adapter may reference media, not only this kind: a source says so by defining
        # `external_media`, and what kind it happens to be is not the question (Part 04 §5.1).
        for resource_id, media in getattr(source, "external_media", dict)().items():
            writer.reference_media(resource_id, media)
            size = f", {media.size_bytes / 1e9:.2f} GB" if media.size_bytes else ""
            say(f"  referenced {resource_id}{size}")
        # An adapter in this process may hand its payloads over as bytes, which the build writes where
        # a protocol adapter would have, so both are read back and refused the same way (Part 03 §11.3).
        location = context.opaque_locations.get(spec.kind)
        opaque.write(getattr(source, "staged_payloads", lambda: ())(), location, spec.kind)
        if location is not None:
            for payload in writer.add_payloads(spec.kind, location, owned=spec.owns):
                say(f"  payload {payload.resource_id}: {opaque.shown(Path(payload.path.name))}")

        drained[spec.kind] = _say_notes(spec.kind, source, 0, say, strict)
        applied.extend(getattr(source, "compensations", []))

    _refuse_a_discarded_fact(writer, context, recipe)
    _declare_withheld(context, writer, say)
    _declare_origin(context, say)
    for note in context.notes:
        say(f"  note: {note}")
    writer.add(
        "core.sessions",
        [
            {
                "session_id": session_id,
                **{k: v for k, v in recipe.session.items() if k != "session_id"},
                **context.session_extra,
            }
        ],
    )
    run = _import_run(recipe, applied, context)
    writer.add("core.processing_runs", [run])
    if roots := _source_roots(recipe):
        writer.add("core.source_files", [{"source_file_id": root, "uri": root} for root in roots])
        writer.add(
            "core.processing_run_inputs",
            [
                {"session_id": session_id, "processing_run_id": run["processing_run_id"], "source_file_id": root}
                for root in roots
            ],
        )
    for entry in describe(applied):
        say(f"  compensated: {entry['id']}")

    def written(say: Callable[[str], None]) -> None:
        """Report what the packet holds, once holding it is what the counts describe.

        A streamed table's rows are produced during the commit, so a source that streams learns
        both its own count and whatever it had to work around only after `build` has returned.
        Reporting here is what keeps the log a record of the packet rather than of the estimate.
        """
        for kind, source in context.sources.items():
            drained[kind] = _say_notes(kind, source, drained.get(kind, 0), say, strict)
        for resource in sorted(counts):
            say(f"  {resource:44s} {writer.rows_written.get(resource, counts[resource]):>12,}")

    writer.after_staging(written)
    return writer


def _say_notes(kind: str, source: Any, seen: int, say: Callable[[str], None], strict: bool) -> int:
    """Report a source's notes past the `seen` already reported, and return the new total."""
    notes = list(getattr(source, "notes", []))
    for note in notes[seen:]:
        say(f"  note: {note}")
    if strict and len(notes) > seen:
        raise RecipeError(f"{kind}: {len(notes) - seen} note(s) under --strict; first is {notes[seen]}")
    return len(notes)


def _source_roots(recipe: Recipe) -> list[str]:
    """Return each distinct `root` the recipe's sources state, as written (Part 05 §7).

    As written rather than as this build resolved it: a relative root resolves against wherever
    the recipe sits, and recording that would make two builds of one recipe over the same bytes
    differ (Part 05 §11). A source stating no root states none to record.
    """
    stated = (entry.get("root") for entry in recipe.document.get("source", []))
    return list(dict.fromkeys(str(root) for root in stated if root is not None))


def _import_run(
    recipe: Recipe, compensations: list[str] | None = None, context: Context | None = None
) -> dict[str, Any]:
    """Build the `core.processing_runs` row for this import, carrying the recipe as its parameters.

    Part 05 §4.3 wants normalization deterministic in declared parameters. Putting the recipe
    itself in `parameters` is what makes the run record answerable rather than merely present:
    a reader can see what produced the packet, and `code_uri` names the file it came from.

    The compensations go in beside it because a recipe alone does not determine the output: two
    runs of the same recipe against the same bytes differ if the importer's assumptions about
    those bytes changed. A packet that names them can be found again when a defect is fixed
    upstream.
    """
    from . import __version__

    return {
        "processing_run_id": f"import.{recipe.digest[:12]}",
        "session_id": recipe.session.get("session_id"),
        "activity_type": "import",
        # R44 §2.1: an import is session-wide, and a session-wide run names the session.
        "scope_kind": "core.sessions",
        "scope": recipe.session.get("session_id"),
        "software_name": "escapewheel-writer",
        "software_version": __version__,
        "code_uri": f"sha256:{recipe.digest}",
        "parameters": json.dumps(
            {
                # Redacted, because this lands in the packet: a recipe written before the
                # refusal existed carries a credential into every copy of it otherwise.
                "recipe": redacted(recipe.document),
                "compensations": describe(compensations or []),
                # Part 02 §12.6 and §4: what the terminal-anchor test withheld, and the measurement
                # that justifies mapping further than Part 01 §3.9's default.
                **_alignment_parameters(context),
            },
            default=str,
            sort_keys=True,
        ),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
    }


def _add_records(
    writer: PacketWriter,
    spec: SourceSpec,
    records: Mapping[str, list[dict[str, Any]]],
    context: Context,
    counts: dict[str, int],
    *,
    arbitrated: frozenset[str] = frozenset(),
) -> dict[str, int]:
    """Add every table a source owns to the writer, counting the rows.

    `arbitrated` is the resources the recipe declares a preference for, whose rows every source
    produced are kept so Part 05 §3.4 can compare them.

    Returns
    -------
    dict
        Rows the source produced per resource, claimed or not, for `_unclaimed` to report.
    """
    produced: dict[str, int] = {}
    for resource, rows in {**records, **_composed(spec, context)}.items():
        produced[resource] = len(rows)
        if resource in arbitrated:
            # Kept rather than counted, so Part 05 §3.4 can compare what the winner staged against
            # what the source it displaced stated. Only where a preference arbitrates, which is
            # what keeps this bounded.
            context.stated.setdefault(resource, {})[spec.kind] = rows
        if resource not in spec.claims or resource in context.payloads:
            continue
        if resource == "core.clock_observation_intervals":
            # R39's origin is a minimum across every clock, and no adapter sees them all.
            context.observed.extend(rows)
        writer.add(resource, rows)
        counts[resource] = counts.get(resource, 0) + len(rows)
    return produced


def _encoding_exceptions(recipe: Recipe) -> dict[str, dict[str, tuple[str, ...]]]:
    """Group the recipe's `[encoding]` block the way `encoding.encodings` reads it.

    `resource.column` splits at the last dot, since a resource ID is itself dotted.
    """
    grouped: dict[str, dict[str, list[str]]] = {"delta": {}, "plain": {}, "dictionary": {}}
    for name, chosen_for in recipe.encoding.items():
        chosen = str(chosen_for.get("encoding", "")).strip()
        if chosen not in grouped or name.count(".") < 2:
            continue
        resource, _, column = name.rpartition(".")
        grouped[chosen].setdefault(resource, []).append(column)
    return {how: {r: tuple(c) for r, c in tables.items()} for how, tables in grouped.items()}


def _refuse_a_discarded_fact(writer: PacketWriter, context: Context, recipe: Recipe) -> None:
    """Refuse where preferring a source discarded a value another source stated (Part 05 §3.4).

    Part 05 §3.4 spends a preference to buy silence about a discarded row, on the premise that the
    loser's copy is redundant. A preference is declared before either source is opened, so nothing
    checked the premise: one naming a source that turns out to state less, or nothing at all, buys
    the same silence and loses the difference. A preferred source producing no rows while another
    does is the limiting case, every value being discarded.

    Compared over declared columns. `metadata` is schemaless by design (Part 02 §8.6), so two sources
    filling it differently is not a difference this can weigh, and Part 02 §8.6 already binds it.

    A build refuses rather than composing the row from both, which would be a fact no source stated
    (Part 05 §3.4). The recipe resolves it: name the fact in `[overrides]` with its reason (Part 05 §3.6),
    prefer the other source, or fix the one that states less.
    """
    kinds = {spec.kind for spec in recipe.sources}
    lost: list[str] = []
    preferred = recipe.preferred
    for resource, by_kind in sorted(context.stated.items()):
        table = writer.spec(resource)
        if table is None or len(by_kind) < 2:
            continue
        # The preference names the winner. Reading it off whoever claims the resource is wrong for
        # a contributed one, where every claimant is a legitimate supplier of different rows.
        winner = preferred.get(resource)
        if winner not in kinds:
            continue
        kept = by_kind.get(winner, [])
        key = list(table.get("primary_key") or [])
        columns = [c["name"] for c in table["columns"] if c["name"] != "metadata"]
        for kind, rows in sorted(by_kind.items()):
            if kind == winner or not rows:
                continue
            if not kept:
                lost.append(f"{resource}: {kind} stated {len(rows):,} row(s) and {winner or 'no source'} staged none")
                continue
            held = {tuple(r.get(k) for k in key): r for r in kept} if key else {}
            for row in rows:
                match = held.get(tuple(row.get(k) for k in key)) if key else None
                if match is None:
                    lost.append(f"{resource}: {kind} stated a row {winner} did not")
                    continue
                lost.extend(
                    f"{resource}.{column}: {kind} stated {row[column]!r} and {winner} left it null"
                    for column in columns
                    if row.get(column) is not None and match.get(column) is None
                )
    if lost:
        raise SourceDefect(
            "preferring a source discarded a fact another stated (Part 05 §3.4). Declare it in "
            "[overrides] with a reason, prefer the other source, or fix the one that states less:"
            "\n  " + "\n  ".join(sorted(set(lost)))
        )


def _note_unclaimed(
    spec: SourceSpec, source: Any, produced: Mapping[str, int], preferred: frozenset[str] = frozenset()
) -> None:
    """Note what a source produced that nothing in the recipe claims.

    `owns` is exclusive and discards in silence, so rows every source produces and none claims
    leave the packet with no record of the omission. The symptom surfaces layers later and
    against the wrong table -- a Tier 2 rule left-joining one that was never staged reports its
    finding on the table that *was*. Every other recipe defect is refused before a byte is read
    (`Recipe.check`); this one needs the source to say what it holds, so it is a note, and
    `--strict` refuses on it.

    A resource some *other* source claims is reported unless it is in `preferred`, the resources
    the recipe names a winner for (Part 05 §3.4). A preference says two sources offer the same rows
    and the one that knows more wins, which makes the loser's copy discarded by design; without one
    they are producing *different* rows.

    A resource an adapter supplies in part needs no exemption of its own. Where this source
    contributes one it is in `claims` already, and where a narrowed source produced one it does not
    claim, the rows really are discarded.
    """
    # Discarded by design: the recipe writes these itself, or a preference names the winner.
    # Everything else this source produced and does not claim is discarded by omission.
    by_design = set(RECIPE_SUPPLIES) | {r for r in produced if r in preferred}
    dropped = {
        resource: rows
        for resource, rows in produced.items()
        if rows and resource not in spec.claims and resource not in by_design
    }
    notes = getattr(source, "notes", None)
    if not dropped or notes is None:
        return
    listed = ", ".join(f"{resource} ({rows:,} rows)" for resource, rows in sorted(dropped.items()))
    notes.append(f"{spec.kind} produced {listed}, which no source in this recipe claims; discarded")


def _declare_withheld(context: Context, writer: Any, say: Callable[[str], None]) -> None:
    """Put Part 02 §12.6's terminal-anchor test on each clock it examined (R99 §3.2).

    The sync source computes this and emits only the reference clock's row; the probe clock rows
    are the sorter's, and the sorter's `CONSUMES` runs it first, so they are already staged. Three
    states are the point: a clock the test never reached keeps both columns null, where one it
    reached and kept records `false` (Part 06 §4).
    """
    withheld = getattr(context.sources.get("sync"), "withheld", None)
    if not withheld:
        if any(getattr(source, "kind", None) for source in context.sources.values()):
            # A delivered source states what it produced and nothing about another source's rows,
            # and this is a fact about the sorter's clock rows. No resource carries it, so it does
            # not cross -- and a packet missing it says nothing, which is why this says it here.
            context.notes.append(
                "the terminal-anchor test's result is not recorded: the source that runs it was "
                "delivered, and no resource carries a fact about another source's rows (R99 §3.2)"
            )
        return
    stamped = writer.stamp(
        "core.clocks",
        "clock_id",
        {
            clock: {
                "withheld_first_anchor": "first" in entry["anchors"],
                "withheld_last_anchor": "last" in entry["anchors"],
            }
            for clock, entry in withheld.items()
        },
    )
    dropped = sum(entry["n_withheld"] for entry in withheld.values())
    say(
        f"  terminal-anchor test recorded on {stamped} of {len(withheld)} clocks, "
        f"{dropped} anchor(s) withheld (R99 §3.2)"
    )
    if stamped != len(withheld):
        context.notes.append(
            f"the terminal-anchor test examined {len(withheld)} clocks and {stamped} of them are "
            "staged, so the rest carry no record of it"
        )


def _declare_origin(context: Context, say: Callable[[str], None]) -> None:
    """Put R39's time origin on the session, or say why the packet gets none."""
    if not (context.observed and context.reference):
        return
    by_clock, bound = context.alignment()
    # R99 §3.1: a null column is a writer that stayed within Part 01 §3.9's default, so only a
    # measured widening is recorded. Set before the origin, which may decline to be stated.
    if bound != BOUND:
        context.session_extra["alignment_bound"] = bound
        say(f"  alignment_bound {bound:g} median anchor intervals (R99 §3.1)")
    origin = _time_origin(context, context.observed, by_clock, bound)
    if origin is None:
        say("  no t_zero_tick: a clock's observation start does not map to the reference (Part 01 §2.2)")
        return
    context.session_extra["t_zero_tick"] = origin
    say(f"  t_zero_tick {origin:,} on {context.reference.clock_id} (Part 01 §2.2)")


def _alignment_parameters(context: Context | None) -> dict[str, Any]:
    """Return the measurement behind the run's alignment decisions, or nothing.

    Part 02 §12.6 draws the line: the three facts a consumer needs to place a tick are columns, and
    what justified them stays here. So this holds the error distribution and the distance it was
    measured at, and no longer the bound, the withheld anchors or the phase steps.
    """
    if context is None or not context.measured_bound:
        return {}
    # `used` is `core.sessions.alignment_bound`; the rest is why the writer chose it.
    return {"alignment_bound": {k: v for k, v in context.measured_bound.items() if k != "used"}}


__all__ = [
    "BATCH_ROWS",
    "MATERIALIZERS",
    "TOLERANCE",
    "Context",
    "RecipeError",
    "build",
    "materializers",
    "order",
]

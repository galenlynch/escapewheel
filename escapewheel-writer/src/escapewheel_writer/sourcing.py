"""Open a recipe's sources and pass each what earlier ones produced (Part 05 §3.4).

- :func:`order` -- the recipe's sources, each after the sources it consumes.
- :func:`build_source`, :func:`supplied_to`, :func:`filled_terms` -- one source opened or
  delivered, what the build supplies it, and the terms the build can fill for it.
- :func:`resolved_source_cache` -- the source cache a build supplies.
- :func:`reference_clock` -- the clock a recipe names as its reference.
- :func:`harvest`, :func:`rows_reader` -- what later sources consume of one source's rows, and
  a reader of those rows.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Collection, Mapping
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from escapewheel_reader.resource_ids import (
    CORE_CLOCK_ANCHORS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_EVENT_STREAMS,
    CORE_UNITS,
)

from . import opaque
from .declaration import SOURCE_CACHE
from .errors import RecipeFault, RecipeUnsound, SourcesNotOrdered, TermUnfilled
from .facts import as_stored, compare_declared_facts
from .kinds import required_adapter
from .notes import Note, NoteCode
from .protocols import SourceAdapter
from .reading import Delivered
from .recipe import TERMS, Problem, Recipe, SourceSpec, declared, reached_by

if TYPE_CHECKING:
    from .session import Context


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
    SourcesNotOrdered
        If a source consumes a kind the recipe does not declare, or the dependencies cycle.
    """
    remaining = list(recipe.sources)
    kinds = {s.kind for s in remaining}
    for spec in remaining:
        missing = [k for k in declared(spec)["consumes"] if k not in kinds]
        if missing:
            raise SourcesNotOrdered(
                f"source {spec.kind} consumes {', '.join(missing)}, which the recipe does not declare",
                kinds=[spec.kind],
                missing=missing,
            )

    ordered: list[SourceSpec] = []
    done: set[str] = set()
    while remaining:
        ready = [s for s in remaining if set(declared(s)["consumes"]) <= done]
        if not ready:
            stuck = sorted(s.kind for s in remaining)
            raise SourcesNotOrdered(
                f"sources {', '.join(stuck)} depend on each other and cannot be ordered", kinds=stuck
            )
        ordered.extend(ready)
        done.update(s.kind for s in ready)
        remaining = [s for s in remaining if s not in ready]
    return ordered


def filled_terms(spec: SourceSpec, recipe: Recipe, context: Context, needed: Collection[str]) -> dict[str, Any]:
    """Return what this build can fill of Part 12 §4's vocabulary, for this source.

    A term absent from the result is one this recipe cannot fill, which is a refusal rather than an
    omission: an adapter cannot tell a term nobody filled from one whose value is legitimately
    empty. Only what `needed` names is resolved, since resolving the reference clock can itself
    refuse and a source that asks for none should not be held to it.
    """
    terms: dict[str, Any] = {"root": spec.root, "session_id": context.session_id}
    if "reference_clock" in needed:
        # The row, not the object: everything a build supplies is data.
        terms["reference_clock"] = _reference(recipe, context).record()
    if "clocks" in needed and context.clocks:
        terms["clocks"] = [context.clocks[clock_id] for clock_id in sorted(context.clocks)]
    if "units" in needed and context.units:
        terms["units"] = context.units
    if "array_location" in needed:
        # One directory per source (Part 12 §5), since two sources may each deliver an asset of
        # one name, and supplied empty (Part 05 §2), since a build binds what it finds by name.
        location = context.staging / "deliveries" / spec.kind
        if location.exists():
            shutil.rmtree(location)
        terms["array_location"] = str(location)
    if "opaque_location" in needed:
        # One directory per source for the same reason, apart from `array_location`'s so neither
        # delivery can pass for the other.
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
    clock = context.reference or reference_clock(recipe, context)
    if clock.tick_zero_utc is None:
        located = context.clocks.get(clock.clock_id, {}).get("tick_zero_utc")
        if located is not None:
            clock = replace(clock, tick_zero_utc=as_stored(located, "timestamp"))
    context.reference = clock
    return clock


def supplied_to(spec: SourceSpec, recipe: Recipe, context: Context) -> dict[str, Any]:
    """Return what a build supplies this source, resolved against what it declares (Part 05 §3.4).

    Each name in the declaration resolves against Part 12 §4's terms first and the recipe's
    options second, and a name resolving to neither is refused -- which `Recipe.check` reports
    before anything is opened, so reaching the refusal here means the recipe was not checked.

    The recipe's remaining options travel too, under `options`, so no option can collide with a
    term. They are the ones an adapter can run without, which that section gives no way to
    declare: a declared name a recipe does not set resolves to nothing, so declaring one would
    make it mandatory.
    """
    names = declared(spec)["needs"]
    terms = filled_terms(spec, recipe, context, names)
    supplied: dict[str, Any] = {}
    for name in names:
        if name in TERMS:
            if name not in terms:
                raise TermUnfilled(
                    f"source {spec.kind} needs {name!r}, which this recipe cannot fill", kind=spec.kind, name=name
                )
            supplied[name] = terms[name]
        elif name not in spec.options:
            raise TermUnfilled(
                f"source {spec.kind} needs {name!r}, which this entry does not set", kind=spec.kind, name=name
            )
    if SOURCE_CACHE in declared(spec)["accepts"] and context.source_cache is not None:
        supplied[SOURCE_CACHE] = str(context.source_cache)
    return {**supplied, "options": dict(spec.options)}


def build_source(spec: SourceSpec, recipe: Recipe, context: Context) -> SourceAdapter:
    """Construct one adapter, or run it and read what it delivered (Part 05 §3.9).

    One construction for every kind, built-in or registered by another distribution, and one
    delivery for every source the recipe does not run in this process. What a source is handed is
    the same either way -- it is the same JSON object, written down for a command and passed as
    keywords for a class -- so which route a source took reaches nothing downstream.
    """
    import inspect

    from . import reading
    from .sources.store import store_for

    supplied = supplied_to(spec, recipe, context)
    options = supplied.pop("options")
    if (protocol := reached_by(spec)) is not None and spec.delivery is not None:
        # The URI rather than the root this build resolved, and the options that open it beside
        # it: the other process opens the source for itself (Part 12 §4), and what it is
        # handed has to be enough to.
        crossing = {**supplied, "root": spec.uri or str(spec.root)}
        if spec.storage_options:
            options = {**options, "storage_options": dict(spec.storage_options)}
        return reading.fetch(
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

    adapter = required_adapter(spec.kind)
    # In process, adapters reading one Zarr root share an open store, so they cannot disagree about
    # what is in it and the electrode table is parsed once. A handle is not something an adapter may
    # declare, so it is supplied where the class accepts one rather than from a
    # table of kinds -- and an adapter out of process is handed none and opens its own.
    if "store" in inspect.signature(adapter).parameters:
        options.setdefault("store", store_for(spec.root, context.stores, cache=supplied.get(SOURCE_CACHE)))
    return adapter(supplied.pop("root"), **supplied, **options)


def reference_clock(recipe: Recipe, context: Context) -> Any:
    """Return the clock an adapter that needs one is given: the session's declared reference."""
    wanted = recipe.session.get("reference_clock_id")
    for spec in recipe.clocks:
        if spec.clock_id == wanted:
            return spec.clock(context.session_id)
    message = f"no [[clock]] declares {wanted!r}, which [session].reference_clock_id names"
    raise RecipeUnsound(
        message, path=recipe.path, problems=[Problem("error", message, RecipeFault.REFERENCE_CLOCK_UNDECLARED)]
    )


#: What a build takes from a source for the sources after it, beyond what the recipe claims. Each
#: is read from the rows a source produced rather than by asking the source, so a source delivered
#: out of process -- a process that has exited by the time this runs -- is harvested the same way.
HARVESTED = (
    CORE_UNITS,
    CORE_CLOCKS,
    CORE_EVENT_STREAMS,
    CORE_CLOCK_ANCHORS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
)


def rows_reader(
    source: SourceAdapter, records: Mapping[str, list[dict[str, Any]]]
) -> Callable[[str], list[dict[str, Any]]]:
    """Return a reader for one source's rows, whichever way they reached this process.

    An adapter in this process hands over records; one delivered out of process hands over a
    table or a file, which `Delivered.rows` reads again for each caller. Either way the harvest
    asks the same question of the same rows.
    """

    def rows(resource: str) -> list[dict[str, Any]]:
        if resource in records:
            return records[resource]
        return source.rows(resource) if isinstance(source, Delivered) else []

    return rows


def harvest(
    spec: SourceSpec,
    source: SourceAdapter,
    context: Context,
    recipe: Recipe,
    rows: Callable[[str], list[dict[str, Any]]],
) -> None:
    """Take from what a source produced whatever the sources after it consume.

    Keyed on the resource rather than on the kind, for the reason `composed` is: which adapter
    declared a clock is not what makes it a clock, and a build that dispatched on the kind could
    only harvest from the kinds it was written against.
    """
    if units := rows(CORE_UNITS):
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
    for row in rows(CORE_CLOCKS):
        # Merged rather than replaced: `core.clocks` is shared, so two sources may each state
        # part of one clock -- a rate here, a located tick 0 there -- and the last to run must
        # not erase what the first knew.
        known = context.clocks.setdefault(str(row["clock_id"]), {})
        known.update({column: value for column, value in row.items() if value is not None})
    context.anchors += rows(CORE_CLOCK_ANCHORS)
    context.event_streams += [row["event_stream_id"] for row in rows(CORE_EVENT_STREAMS)]
    if (reference := context.reference) is not None:
        # The window this source watched the reference clock over, which the build pairs with the
        # streams another source declared. Kept per source: two sources may each declare a window
        # on one clock -- a sync train and an acquisition are both true -- and only the one that
        # comes with the resource being composed says when those streams were watched.
        for row in rows(CORE_CLOCK_OBSERVATION_INTERVALS):
            if row["clock_id"] == reference.clock_id:
                context.windows[spec.kind] = (int(row["start_tick"]), int(row["stop_tick"]))
    compare_declared_facts(spec, source, context, recipe)


def resolved_source_cache(configured: str | Path | None, out: Path, context: Context) -> Path | None:
    """Return the location this build supplies as `source_cache`, creating it, or None (Part 12 §10).

    Refused inside the packet root or the delivery workspace, where a build replaces what it finds,
    and wherever it cannot be written; either way the build proceeds as one with no location.
    """
    if configured is None:
        return None
    where = Path(configured).resolve()
    for inside in (out.resolve(), context.workspace.resolve()):
        if where == inside or inside in where.parents:
            context.notes.append(
                Note(
                    f"source cache {where} lies inside {inside}, so no adapter is supplied one",
                    NoteCode.NO_SOURCE_CACHE,
                )
            )
            return None
    try:
        where.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        context.notes.append(
            Note(
                f"source cache {where} cannot be created ({exc}), so no adapter is supplied one",
                NoteCode.NO_SOURCE_CACHE,
            )
        )
        return None
    if not os.access(where, os.W_OK | os.X_OK):
        context.notes.append(
            Note(f"source cache {where} is not writable, so no adapter is supplied one", NoteCode.NO_SOURCE_CACHE)
        )
        return None
    context.say(f"source cache {where}")
    return where


__all__ = [
    "build_source",
    "filled_terms",
    "harvest",
    "order",
    "reference_clock",
    "resolved_source_cache",
    "rows_reader",
    "supplied_to",
]

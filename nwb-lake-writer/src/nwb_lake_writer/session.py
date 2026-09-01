"""Build a packet from a recipe.

This is `05` Stages 2-6 with the parameters supplied rather than written into the code. The
recipe says which sources exist and which resources each is responsible for; this module
orders them, runs them, keeps what each one owns, and commits.

**Ordering comes from the adapters, not from the registry.** A foreign key constrains
validity, not write order -- Parquet files are independent and `core.spike_events` can be
written before `core.units` with nothing the worse. What actually sequences a build is
data-flow between adapters: `NWBSource` needs the sorter's units to attach a unit to an
electrode, and no reference in the registry says so, because the dependency is between
adapters rather than between tables. So :data:`CONSUMES` states it, and it is short because
there is little of it.

**Ownership is what stops two sources fighting.** Four adapters can each produce
`core.probes`, and without a rule the last one to run wins silently -- which is how a
`probe_id` collapse matched 0 of 6,781 units, and how two sources emitting
`core.unit_electrodes` collided on its primary key. A source's records are filtered to what
the recipe says it owns, so the resolution is declared in one place a reader can see.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from .recipe import Recipe, SourceSpec
from .sources.compensations import describe
from .writer import PacketWriter, StagedArray

#: Which sources a kind consumes the output of. Data-flow between adapters, which the
#: registry cannot express; see the module docstring.
#: Kinds that read a Zarr source through :class:`~nwb_lake_writer.sources.store.SourceStore`,
#: and so share one open store per root.
_SHARED_SOURCES = frozenset({"nwb", "waveforms", "lfp"})

CONSUMES: dict[str, tuple[str, ...]] = {
    "nwb": ("sorter",),
    "waveforms": ("sorter", "nwb"),
    # The probe clock an LFP axis advances on comes from the sorter; the electrode behind each
    # channel comes from the NWB.
    "lfp": ("sorter", "nwb"),
    # Locating tick 0 takes a tick observed at the ephys stream's declared start: the first
    # spike, from the sorter, mapped onto the reference clock through the sync anchors. The
    # observation windows it writes cover the event streams the NWB declares.
    "session": ("sorter", "sync", "nwb"),
}

#: Analysis resources a recipe may ask for by name, and the function that derives each from a
#: staged packet. `05` stage 8 calls these optional, so a recipe that names none is complete.
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
    units : dict
        `(device_name, local_unit_label)` to the identifying triple. The join key the NWB and
        the sorter meet on: the sorter mints unit identity, the NWB places it in space.
    electrodes : dict
        Global electrode row index to `electrode_id`, for a source that reads an array indexed
        by row rather than by ID.
    clocks : dict
        Clock ID to declared tick rate, for a source placing an array axis on one. An axis
        advances in ticks (R20 §2), so a step cannot be derived without the rate.
    stores : dict
        Resolved source root to its open store. Three adapters in a real recipe read the same
        `.nwb`; sharing the store means they cannot disagree about what is in it, and stops the
        electrode table being parsed once per adapter.
    """

    session_id: str
    sources: dict[str, Any] = field(default_factory=dict)
    units: dict[tuple[str, str], dict[str, str]] = field(default_factory=dict)
    electrodes: dict[int, str] = field(default_factory=dict)
    clocks: dict[str, float] = field(default_factory=dict)
    stores: dict[Path, Any] = field(default_factory=dict)
    #: The reference clock, as the recipe declares it. A `session` source rewrites its row
    #: with a `tick_zero_utc`; every other adapter uses it as given.
    reference: Any = None
    #: `core.event_streams` IDs the NWB declared, which the observation windows cover.
    event_streams: list[str] = field(default_factory=list)


def order(recipe: Recipe) -> list[SourceSpec]:
    """Order sources so every one runs after what it consumes.

    Parameters
    ----------
    recipe : Recipe
        The parsed recipe.

    Returns
    -------
    list of SourceSpec
        The sources, in an order that satisfies :data:`CONSUMES`.

    Raises
    ------
    RecipeError
        If a source consumes a kind the recipe does not declare, or the dependencies cycle.
    """
    remaining = list(recipe.sources)
    declared = {s.kind for s in remaining}
    for spec in remaining:
        missing = [k for k in CONSUMES.get(spec.kind, ()) if k not in declared]
        if missing:
            raise RecipeError(f"source {spec.kind} consumes {', '.join(missing)}, which the recipe does not declare")

    ordered: list[SourceSpec] = []
    done: set[str] = set()
    while remaining:
        ready = [s for s in remaining if set(CONSUMES.get(s.kind, ())) <= done]
        if not ready:
            stuck = ", ".join(sorted(s.kind for s in remaining))
            raise RecipeError(f"sources {stuck} depend on each other and cannot be ordered")
        ordered.extend(ready)
        done.update(s.kind for s in ready)
        remaining = [s for s in remaining if s not in ready]
    return ordered


def _build_source(spec: SourceSpec, recipe: Recipe, context: Context) -> Any:
    """Construct one adapter, supplying whatever earlier sources produced for it."""
    from .sources import LFPSource, NWBSource, SorterSource, SyncSource, WaveformSource
    from .sources.store import store_for

    options = dict(spec.options)
    if spec.kind in _SHARED_SOURCES:
        options["store"] = store_for(spec.root, context.stores)
    if spec.kind == "sorter":
        return SorterSource(spec.root, session_id=context.session_id, **options)
    if spec.kind == "sync":
        first = options.pop("first_samples", None)
        samples = json.loads(Path(first).read_text()) if first else None
        return SyncSource(spec.root, session_id=context.session_id, first_samples=samples, **options)
    if spec.kind == "nwb":
        zone = ZoneInfo(str(options.pop("zone")))
        clock = context.reference or _reference_clock(recipe, context)
        return NWBSource(
            spec.root, clock=clock, zone=zone, session_id=context.session_id, units=context.units, **options
        )
    if spec.kind == "lfp":
        return LFPSource(
            spec.root,
            session_id=context.session_id,
            clocks=sorted(context.clocks),
            electrodes=context.electrodes,
            **options,
        )
    if spec.kind == "session":
        from .sources import SessionSource

        return SessionSource(spec.root, zone=ZoneInfo(str(options.pop("zone"))), session_id=context.session_id)
    if spec.kind == "waveforms":
        return WaveformSource(
            spec.root, session_id=context.session_id, units=context.units, electrodes=context.electrodes, **options
        )
    raise RecipeError(f"unknown source kind {spec.kind!r}")


def _reference_clock(recipe: Recipe, context: Context) -> Any:
    """Return the clock an adapter that needs one is given: the session's declared reference."""
    wanted = recipe.session.get("reference_clock_id")
    for spec in recipe.clocks:
        if spec.clock_id == wanted:
            return spec.clock(context.session_id)
    raise RecipeError(f"no [[clock]] declares {wanted!r}, which [session].reference_clock_id names")


def _harvest(spec: SourceSpec, source: Any, context: Context) -> None:
    """Take from a built source whatever the sources after it consume."""
    if spec.kind == "sorter":
        # The NWB names a quad-base probe's shanks separately and the sorting run ID ends in
        # exactly that name, while probe_id collapses to the physical probe.
        context.units = {
            (row["sorting_run_id"].rsplit(".", 1)[-1], row["local_unit_label"]): {
                key: row[key] for key in ("unit_id", "sorting_run_id", "curation_id")
            }
            for row in source.units()
        }
        context.clocks.update({c["clock_id"]: float(c["tick_rate_hz"]) for c in source.clocks()})
    if spec.kind == "nwb":
        context.electrodes = dict(enumerate(row["electrode_id"] for row in source.electrodes()))
        context.event_streams = [row["event_stream_id"] for row in source.event_streams()]


def _first_spike_tick(context: Context) -> int:
    """Return the earliest spike in the session, on the reference clock.

    `core.units` carries `first_spike_tick` per unit on its own probe's clock, so the earliest
    is a minimum per clock mapped through that clock's anchors, not a minimum of raw ticks:
    ticks from two probes are not comparable, which is the whole reason the anchors exist.
    """
    from nwb_lake_reader.clocks import align

    sorter, sync = context.sources["sorter"], context.sources["sync"]
    anchors: dict[str, tuple[list[int], list[int]]] = {}
    for row in sync.anchors():
        at, parent = anchors.setdefault(row["clock_id"], ([], []))
        at.append(row["t_tick"])
        parent.append(row["parent_tick"])

    earliest: list[int] = []
    for row in sorter.units():
        # A unit names no clock; its sorting run does, by the convention the two adapters
        # already meet on -- the same one `SyncSource.anchors` defaults to.
        tick, clock_id = row.get("first_spike_tick"), f"{row.get('sorting_run_id')}.samples"
        if tick is None or clock_id not in anchors:
            continue
        at, parent = anchors[clock_id]
        mapped, defined = align(np.array([tick], dtype=np.int64), np.array(at), np.array(parent))
        if defined[0]:
            earliest.append(int(mapped[0]))
    if not earliest:
        raise RecipeError("no unit carries a first_spike_tick on an anchored clock, so tick 0 cannot be located")
    return min(earliest)


def _records(spec: SourceSpec, source: Any, context: Context) -> dict[str, list[dict[str, Any]]]:
    """Return a source's records, with the arguments its kind needs to produce them."""
    got: dict[str, list[dict[str, Any]]]
    if spec.kind == "lfp":
        lfp: dict[str, list[dict[str, Any]]] = source.records(rates=context.clocks)
        return lfp
    if spec.kind == "session":
        clock = context.reference
        return source.records(
            at_tick=_first_spike_tick(context),
            clock_id=clock.clock_id,
            tick_rate_num=clock.tick_rate_num,
            tick_rate_den=clock.tick_rate_den,
            name=clock.name,
            origin=clock.origin,
            event_stream_ids=context.event_streams,
        )
    sorter = context.sources.get("sorter") if spec.kind == "sync" else None
    if sorter is not None:
        # Anchor only the streams the sorting made a clock for. The rig aligns more than it
        # sorts, and an anchor on a clock that does not exist is a dangling reference.
        known = {c["clock_id"] for c in sorter.clocks()}
        got = source.records(clock_id_for=lambda st: c if (c := f"{st.key}.samples") in known else None)
    else:
        got = source.records()
    return got


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


def build(
    recipe: Recipe,
    registry: Mapping[str, Any],
    *,
    say: Callable[[str], None] = lambda _: None,
    strict: bool = False,
) -> PacketWriter:
    """Run every source and return a writer holding the packet, uncommitted.

    Parameters
    ----------
    recipe : Recipe
        The parsed recipe. Assumed already checked; :meth:`Recipe.check` is the caller's job,
        because a caller that reports problems is more useful than one that raises on the first.
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
    session_id = str(recipe.session["session_id"])
    context = Context(session_id=session_id)
    if recipe.session.get("reference_clock_id"):
        context.reference = _reference_clock(recipe, context)
    writer = PacketWriter(registry, packet_id=recipe.packet_id, description=recipe.description)

    writer.add(
        "core.sessions", [{"session_id": session_id, **{k: v for k, v in recipe.session.items() if k != "session_id"}}]
    )
    if recipe.subject:
        writer.add("core.subjects", [dict(recipe.subject)])

    counts: dict[str, int] = {}
    applied: list[str] = []
    for spec in order(recipe):
        say(f"{spec.kind} -> {', '.join(spec.owns) or 'nothing it owns'}")
        source = _build_source(spec, recipe, context)
        context.sources[spec.kind] = source
        _harvest(spec, source, context)

        for resource, rows in _records(spec, source, context).items():
            if resource not in spec.claims:
                continue
            writer.add(resource, rows)
            counts[resource] = counts.get(resource, 0) + len(rows)

        if "core.spike_events" in spec.claims:
            writer.add_batches("core.spike_events", source.spike_batches(batch_rows=BATCH_ROWS))
            counts["core.spike_events"] = source.spike_count
        if spec.kind == "waveforms" and spec.options.get("array_asset_id", "waveform_mean"):
            _stage_array(writer, spec, source, say)
        if spec.kind == "lfp":
            for resource_id, array in source.external_arrays().items():
                writer.reference_array(resource_id, array)
                say(f"  referenced {resource_id} ({array.physical_profile}, {', '.join(array.codecs) or 'no codec'})")

        for note in getattr(source, "notes", []):
            say(f"  note: {note}")
        applied.extend(getattr(source, "compensations", []))
        if strict and (refused := list(getattr(source, "notes", []))):
            raise RecipeError(f"{spec.kind}: {len(refused)} note(s) under --strict; first is {refused[0]}")

    writer.add("core.processing_runs", [_import_run(recipe, applied)])
    for entry in describe(applied):
        say(f"  compensated: {entry['id']}")
    for resource, total in sorted(counts.items()):
        say(f"  {resource:44s} {total:>12,}")
    return writer


def _stage_array(writer: PacketWriter, spec: SourceSpec, source: Any, say: Callable[[str], None]) -> None:
    """Stage a waveform source's dense array, sizing the shard for the store it will live in."""
    from .arrays import shard_for

    values = source.values
    chunks = (1, *values.shape[1:])
    shard = shard_for(values.shape, chunks, float(spec.options.get("compressed_per_chunk", 3850.0)))
    say(f"  array {values.shape} {values.dtype}, {values.nbytes / 1e6:.0f} MB raw, shard {shard}")
    writer.add_array(
        f"core.{source.array_asset_id}",
        StagedArray(values=values, array_asset_id=source.array_asset_id, chunks=chunks, shard=shard),
    )


def _import_run(recipe: Recipe, compensations: list[str] | None = None) -> dict[str, Any]:
    """Build the `core.processing_runs` row for this import, carrying the recipe as its parameters.

    `05` Stage 3 wants normalization deterministic in declared parameters. Putting the recipe
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
        "software_name": "nwb-lake-writer",
        "software_version": __version__,
        "code_uri": f"sha256:{recipe.digest}",
        "parameters": json.dumps(
            {"recipe": recipe.document, "compensations": describe(compensations or [])},
            default=str,
            sort_keys=True,
        ),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
    }


__all__ = ["BATCH_ROWS", "CONSUMES", "MATERIALIZERS", "Context", "RecipeError", "build", "materializers", "order"]

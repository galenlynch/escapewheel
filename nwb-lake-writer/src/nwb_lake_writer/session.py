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
from datetime import UTC, datetime, timedelta
from functools import partial
from math import ceil
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from numpy.typing import NDArray
from nwb_lake_reader.clocks import BOUND, align

from .extensions import load as load_extension
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
    # `_clock_namer` reads the sorter's clocks to know which streams already have one, so the
    # sorter must have run first. Without this the namer is None and `anchors` falls back to
    # naming every aligned stream, including ones no source declared a clock for.
    "sync": ("sorter",),
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

#: The most error a mapping may carry before R40 §2.1 calls it undefined, in **seconds**.
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
    #: Session facts a source derived that the recipe does not state, merged into
    #: `core.sessions` after every source has run.
    session_extra: dict[str, Any] = field(default_factory=dict)
    #: `core.clock_observation_intervals` rows, whatever source produced them, since R39's
    #: origin is a minimum across all of them and no single adapter sees them all.
    observed: list[dict[str, Any]] = field(default_factory=list)
    #: What `_bound_for` measured, for the import run's parameters (R37 §3.3, §4).
    measured_bound: dict[str, Any] = field(default_factory=dict)
    #: The anchors and the bound, once `alignment` has settled them.
    _alignment: tuple[dict[str, Any], float] | None = None
    #: What the build itself observed, reported beside the adapters' own notes.
    notes: list[str] = field(default_factory=list)

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


#: Source kinds this package implements. A distribution may register others under
#: `nwb_lake_writer.sources.SOURCE_GROUP`; these are consulted first, so a plugin cannot shadow
#: one and a recipe naming `sorter` always means this one.
_KINDS = ("sorter", "sync", "nwb", "session", "waveforms", "lfp", "tables")


def _build_source(spec: SourceSpec, recipe: Recipe, context: Context) -> Any:
    """Construct one adapter, supplying whatever earlier sources produced for it."""
    from .sources import LFPSource, NWBSource, SorterSource, SyncSource, TablesSource, WaveformSource
    from .sources.store import store_for

    options = dict(spec.options)
    if spec.kind in _SHARED_SOURCES:
        options["store"] = store_for(spec.root, context.stores)
    if spec.kind == "tables":
        # The least coupled source: files that already exist, optionally produced by a command
        # first. An extension supplied this way needs no Python of ours at all.
        return TablesSource(spec.root, session_id=context.session_id, **options)
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
    # A kind this package does not know may be registered by another distribution (R17's problem
    # one layer down: an extension's table needs an adapter that knows a raw format core never
    # will). Consulted after the built-ins, so a plugin cannot shadow one.
    from .sources import discovered

    if (build := discovered().get(spec.kind)) is not None:
        return build(spec.root, session_id=context.session_id, **options)
    known = ", ".join(sorted({*_KINDS, *discovered()}))
    raise RecipeError(f"unknown source kind {spec.kind!r}; known kinds are {known}")


def _reference_clock(recipe: Recipe, context: Context) -> Any:
    """Return the clock an adapter that needs one is given: the session's declared reference."""
    wanted = recipe.session.get("reference_clock_id")
    for spec in recipe.clocks:
        if spec.clock_id == wanted:
            return spec.clock(context.session_id)
    raise RecipeError(f"no [[clock]] declares {wanted!r}, which [session].reference_clock_id names")


def _harvest(spec: SourceSpec, source: Any, context: Context, recipe: Recipe) -> None:
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
    if spec.kind == "session":
        # Both ends come from the declared stream windows rather than from the recipe: a
        # hand-entered start is a transcription of the same fact, and the two disagreeing
        # silently is worse than either being wrong loudly.
        began, ended = source.extent()
        context.session_extra["session_start_time"] = began
        context.session_extra["session_end_time"] = ended
        if (declared := _declared_start(recipe)) is not None and abs((declared - began).total_seconds()) > 1:
            source.notes.append(
                f"[session].session_start_time {declared.isoformat()} disagrees with the earliest "
                f"declared stream window {began.isoformat()}; the window is used"
            )
    if spec.kind == "nwb":
        context.electrodes = dict(enumerate(row["electrode_id"] for row in source.electrodes()))
        context.event_streams = [row["event_stream_id"] for row in source.event_streams()]


def _declared_start(recipe: Recipe) -> datetime | None:
    """Return the recipe's own `session_start_time`, parsed, or None where it declares none."""
    raw = recipe.session.get("session_start_time")
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))


def _anchors(context: Context) -> dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Return the sync source's anchors as arrays per clock, in the shape `align` wants."""
    collected: dict[str, tuple[list[int], list[int]]] = {}
    for row in context.sources["sync"].anchors(clock_id_for=_clock_namer(context)):
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
    """Choose the bound to map at, measuring it as R37 §3.3 and R40 §2 require.

    A packet whose earliest data sits inside one median anchor interval of its first anchor
    needs nothing; R27 §5.3's default covers it and this returns it unmeasured. Where it does
    not -- and withholding a displaced first anchor (R37 §3.2) is what usually makes it not --
    the writer may go further only by measuring the estimator at the distance it intends to
    use and finding its **95th percentile** within `tolerance` (R40 §2.2). The median is not a
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
        The most error the mapping may carry, in seconds (R40 §2.1).
    rate : float
        The parent clock's rate in hertz, which turns that duration into the parent ticks the
        measurement is in.

    Returns
    -------
    tuple
        The bound in median anchor intervals, and the measurement, for the run's parameters.
    """
    from nwb_lake_reader.clocks import extrapolation_error

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
        # writer applied (R40 §2.2).
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
    """R39 §2.1: the earliest observation start among the session's clocks, on the reference.

    Returns None where any clock's window start cannot be mapped, since a minimum taken over
    some of the clocks is not the minimum R39 §2.2 requires a writer to declare -- and R39
    §2.4 says an origin the writer cannot compute is one it must not state.
    """
    from nwb_lake_reader.clocks import align

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


def _recorded_epoch(context: Context, by_clock: Mapping[str, Any], bound: float) -> datetime | None:
    """Locate the reference clock's tick 0 in wall clock, from the record nodes' own stamps.

    Each node writes `sync_messages.txt` when it starts: a UTC instant to the millisecond, and
    the counter value of every stream at that moment. A stream's tick 0 *is* that counter
    value, so mapping tick 0 onto the reference gives a (reference tick, UTC) pair -- which is
    what `tick_zero_utc` is, and the only route to it that pairs a wall clock with an
    instrument event rather than with a datum. Every other route pairs it with the first spike,
    and the first spike is the thing being placed.

    A node's streams do not all reach their first sample at the same moment: the node opens the
    file and writes each stream's first available sample, so a stream is at or after the stamp,
    never before. The earliest is therefore the closest, and the spread over the rest bounds
    the error. Two nodes give two independent estimates; their disagreement is reported.
    """
    sync = context.sources.get("sync")
    reference = context.reference
    if sync is None or reference is None:
        return None
    rate = reference.tick_rate_num / (reference.tick_rate_den or 1)
    namer = _clock_namer(context)
    per_node: dict[str, list[int]] = {}
    stamps: dict[str, datetime] = {}
    for stream in sync.aligned():
        clock = namer(stream) if namer else None
        started = sync.started(stream)
        if clock is None or started is None or clock not in by_clock:
            continue
        converted, defined = align(np.array([0], dtype=np.int64), *by_clock[clock], bound=bound)
        if defined[0]:
            per_node.setdefault(stream.node, []).append(int(converted[0]))
            stamps[stream.node] = started.started

    estimates = [stamps[node] - timedelta(seconds=min(ticks) / rate) for node, ticks in per_node.items()]
    if not estimates:
        return None
    earliest, latest = min(estimates), max(estimates)
    if len(estimates) > 1:
        context.notes.append(
            f"tick_zero_utc: {len(estimates)} record nodes agree to {(latest - earliest).total_seconds() * 1e3:.0f} ms"
        )
    for node, ticks in sorted(per_node.items()):
        if len(ticks) > 1:
            context.notes.append(
                f"{node}: its streams reach sample 0 over "
                f"{(max(ticks) - min(ticks)) / rate * 1e3:.0f} ms, which bounds the estimate"
            )
    # The mean of the nodes' estimates; each is independently derived and neither is better.
    return earliest + (latest - earliest) / 2


def _first_spike_tick(context: Context, by_clock: Mapping[str, Any], bound: float) -> int:
    """Return the earliest spike in the session, on the reference clock.

    `core.units` carries `first_spike_tick` per unit on its own probe's clock, so the earliest
    is a minimum per clock mapped through that clock's anchors, not a minimum of raw ticks:
    ticks from two probes are not comparable, which is the whole reason the anchors exist.
    """
    from nwb_lake_reader.clocks import align

    earliest: list[int] = []
    for row in context.sources["sorter"].units():
        # A unit names no clock; its sorting run does, by the convention the two adapters
        # already meet on -- the same one `SyncSource.anchors` defaults to.
        tick, clock_id = row.get("first_spike_tick"), f"{row.get('sorting_run_id')}.samples"
        if tick is None or clock_id not in by_clock:
            continue
        converted, defined = align(np.array([tick], dtype=np.int64), *by_clock[clock_id], bound=bound)
        if defined[0]:
            earliest.append(int(converted[0]))
    if not earliest:
        raise RecipeError("no unit carries a first_spike_tick on an anchored clock, so tick 0 cannot be located")
    return min(earliest)


def _add_batches(writer: PacketWriter, spec: SourceSpec, source: Any, counts: dict[str, int]) -> None:
    """Stream whatever a source streams, rather than holding it as Python mappings.

    `core.spike_events` is the case that forced the streaming path -- 10^8 rows, and a dict per
    row is two orders of magnitude more memory than the Parquet file it becomes. Any source may
    use it for any resource it claims, because an extension's table may be as large as a core
    one and nothing about the reason was ever specific to spikes.
    """
    if "core.spike_events" in spec.claims and hasattr(source, "spike_batches"):
        writer.add_batches("core.spike_events", source.spike_batches(batch_rows=BATCH_ROWS))
        counts["core.spike_events"] = source.spike_count
    streamed = getattr(source, "batches", None)
    if streamed is None:
        return
    offered = source.offers()
    for resource_id, batches in streamed().items():
        if resource_id in spec.claims:
            writer.add_batches(resource_id, batches)
            counts[resource_id] = offered.get(resource_id, 0)


def _records(spec: SourceSpec, source: Any, context: Context) -> dict[str, list[dict[str, Any]]]:
    """Return a source's records, with the arguments its kind needs to produce them."""
    got: dict[str, list[dict[str, Any]]]
    if spec.kind == "lfp":
        lfp: dict[str, list[dict[str, Any]]] = source.records(rates=context.clocks)
        return lfp
    if spec.kind == "session":
        clock = context.reference
        session: dict[str, list[dict[str, Any]]] = source.records(
            at_tick=_first_spike_tick(context, *context.alignment()),
            epoch=_recorded_epoch(context, *context.alignment()),
            clock_id=clock.clock_id,
            tick_rate_num=clock.tick_rate_num,
            tick_rate_den=clock.tick_rate_den,
            name=clock.name,
            origin=clock.origin,
            event_stream_ids=context.event_streams,
        )
        return session
    if spec.kind == "sync":
        return dict(source.records(clock_id_for=_clock_namer(context)))
    got = source.records()
    return got


def _clock_namer(context: Context) -> Any:
    """Return the map from a sync stream to the clock its ticks are on, or None for neither.

    Anchor only the streams some source declared a clock for, because an anchor naming a clock
    the packet does not carry is a dangling reference. The rig aligns more than it sorts: the
    NI-DAQ has its own clock, running at its own rate, which `structure.oebin` records and no
    adapter yet emits -- so its anchors are dropped here rather than dangling, and the alignment
    for the stream carrying the sync pulse is lost with them. Every caller that asks the sync
    source for anchors uses this, so the packet and the alignment behind it see the same set.
    """
    sorter = context.sources.get("sorter")
    if sorter is None:
        return None
    known = {c["clock_id"] for c in sorter.clocks()}
    return lambda stream: name if (name := f"{stream.key}.samples") in known else None


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
    writer = PacketWriter(
        registry,
        packet_id=recipe.packet_id,
        description=recipe.description,
        # R17 §2: the recipe names them, so a source may own an extension's table exactly as it
        # owns a core one. Which is what keeps declaring an extension from being harder than
        # adding a column to core -- the gradient that leaves NWB's own mechanism unused.
        extensions=[load_extension(named, base=recipe.path.parent) for named in recipe.extensions],
    )

    if recipe.subject:
        writer.add("core.subjects", [dict(recipe.subject)])

    counts: dict[str, int] = {}
    applied: list[str] = []
    for spec in order(recipe):
        say(f"{spec.kind} -> {', '.join(spec.owns) or 'nothing it owns'}")
        source = _build_source(spec, recipe, context)
        context.sources[spec.kind] = source
        _harvest(spec, source, context, recipe)

        _add_records(writer, spec, source, context, counts)

        _add_batches(writer, spec, source, counts)
        if spec.kind == "waveforms" and spec.options.get("array_asset_id", "waveform_mean"):
            _stage_array(writer, spec, source, say)
        # Any adapter may stage arrays, not only the waveform one. A source that has them says
        # so by defining `staged_arrays`; the kind it happens to be is not the question.
        for staged in getattr(source, "staged_arrays", lambda: ())():
            say(
                f"  array {staged.array_asset_id} {staged.values.shape} {staged.values.dtype}, "
                f"{staged.values.nbytes / 1e6:.1f} MB raw"
            )
            writer.add_array(f"core.{staged.array_asset_id}", staged)
        if spec.kind == "lfp":
            for resource_id, array in source.external_arrays().items():
                writer.reference_array(resource_id, array)
                say(f"  referenced {resource_id} ({array.physical_profile}, {', '.join(array.codecs) or 'no codec'})")

        for note in getattr(source, "notes", []):
            say(f"  note: {note}")
        applied.extend(getattr(source, "compensations", []))
        if strict and (refused := list(getattr(source, "notes", []))):
            raise RecipeError(f"{spec.kind}: {len(refused)} note(s) under --strict; first is {refused[0]}")

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
    writer.add("core.processing_runs", [_import_run(recipe, applied, context)])
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


def _import_run(
    recipe: Recipe, compensations: list[str] | None = None, context: Context | None = None
) -> dict[str, Any]:
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
        # R44 §2.1: an import is session-wide, and a session-wide run names the session.
        "scope_kind": "core.sessions",
        "scope": recipe.session.get("session_id"),
        "software_name": "nwb-lake-writer",
        "software_version": __version__,
        "code_uri": f"sha256:{recipe.digest}",
        "parameters": json.dumps(
            {
                "recipe": recipe.document,
                "compensations": describe(compensations or []),
                # R37 §3.2 and §4: what the terminal-anchor test withheld, and the measurement
                # that justifies mapping further than R27 §5.3's default.
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
    source: Any,
    context: Context,
    counts: dict[str, int],
) -> None:
    """Add every table a source owns to the writer, counting the rows."""
    for resource, rows in _records(spec, source, context).items():
        if resource not in spec.claims:
            continue
        if resource == "core.clock_observation_intervals":
            # R39's origin is a minimum across every clock, and no adapter sees them all.
            context.observed.extend(rows)
        writer.add(resource, rows)
        counts[resource] = counts.get(resource, 0) + len(rows)


def _declare_origin(context: Context, say: Callable[[str], None]) -> None:
    """Put R39's time origin on the session, or say why the packet gets none."""
    if not (context.observed and context.reference):
        return
    by_clock, bound = context.alignment()
    origin = _time_origin(context, context.observed, by_clock, bound)
    if origin is None:
        say("  no t_zero_tick: a clock's observation start does not map to the reference (R39 §2.4)")
        return
    context.session_extra["t_zero_tick"] = origin
    say(f"  t_zero_tick {origin:,} on {context.reference.clock_id} (R39 §2.1)")


def _alignment_parameters(context: Context | None) -> dict[str, Any]:
    """Return what a run should record about how it aligned clocks, or nothing."""
    if context is None:
        return {}
    sync = context.sources.get("sync")
    withheld = getattr(sync, "withheld", {})
    recorded = {}
    if withheld:
        recorded["withheld_anchors"] = withheld
    if stepped := getattr(sync, "discontinuities", {}):
        # Reported so a consumer can see them, never corrected -- see SyncSource.discontinuities.
        recorded["phase_discontinuities"] = stepped
    if context.measured_bound:
        recorded["alignment_bound"] = context.measured_bound
    return recorded


__all__ = [
    "BATCH_ROWS",
    "CONSUMES",
    "MATERIALIZERS",
    "TOLERANCE",
    "Context",
    "RecipeError",
    "build",
    "materializers",
    "order",
]

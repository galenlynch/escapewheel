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

from .recipe import Recipe, SourceSpec
from .writer import PacketWriter, StagedArray

#: Which sources a kind consumes the output of. Data-flow between adapters, which the
#: registry cannot express; see the module docstring.
CONSUMES: dict[str, tuple[str, ...]] = {
    "nwb": ("sorter",),
    "waveforms": ("sorter", "nwb"),
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
    """

    session_id: str
    sources: dict[str, Any] = field(default_factory=dict)
    units: dict[tuple[str, str], dict[str, str]] = field(default_factory=dict)
    electrodes: dict[int, str] = field(default_factory=dict)


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
    from .sources import NWBSource, SorterSource, SyncSource, WaveformSource

    options = dict(spec.options)
    if spec.kind == "sorter":
        return SorterSource(spec.root, session_id=context.session_id, **options)
    if spec.kind == "sync":
        first = options.pop("first_samples", None)
        samples = json.loads(Path(first).read_text()) if first else None
        return SyncSource(spec.root, session_id=context.session_id, first_samples=samples, **options)
    if spec.kind == "nwb":
        zone = ZoneInfo(str(options.pop("zone")))
        clock = _reference_clock(recipe, context)
        return NWBSource(
            spec.root, clock=clock, zone=zone, session_id=context.session_id, units=context.units, **options
        )
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
    if spec.kind == "nwb":
        context.electrodes = dict(enumerate(row["electrode_id"] for row in source.electrodes()))


def _records(spec: SourceSpec, source: Any, context: Context) -> dict[str, list[dict[str, Any]]]:
    """Return a source's records, with the arguments its kind needs to produce them."""
    got: dict[str, list[dict[str, Any]]]
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


def build(recipe: Recipe, registry: Mapping[str, Any], *, say: Callable[[str], None] = lambda _: None) -> PacketWriter:
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

    Returns
    -------
    PacketWriter
        Loaded with every record, ready to commit.
    """
    session_id = str(recipe.session["session_id"])
    context = Context(session_id=session_id)
    writer = PacketWriter(registry, packet_id=recipe.packet_id, description=recipe.description)

    writer.add(
        "core.sessions", [{"session_id": session_id, **{k: v for k, v in recipe.session.items() if k != "session_id"}}]
    )
    if recipe.subject:
        writer.add("core.subjects", [dict(recipe.subject)])

    counts: dict[str, int] = {}
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

        for note in getattr(source, "notes", []):
            say(f"  note: {note}")

    writer.add("core.processing_runs", [_import_run(recipe)])
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


def _import_run(recipe: Recipe) -> dict[str, Any]:
    """Build the `core.processing_runs` row for this import, carrying the recipe as its parameters.

    `05` Stage 3 wants normalization deterministic in declared parameters. Putting the recipe
    itself in `parameters` is what makes the run record answerable rather than merely present:
    a reader can see what produced the packet, and `code_uri` names the file it came from.
    """
    from . import __version__

    return {
        "processing_run_id": f"import.{recipe.digest[:12]}",
        "session_id": recipe.session.get("session_id"),
        "activity_type": "import",
        "software_name": "nwb-lake-writer",
        "software_version": __version__,
        "code_uri": f"sha256:{recipe.digest}",
        "parameters": json.dumps(recipe.document, default=str, sort_keys=True),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "succeeded",
    }


__all__ = ["BATCH_ROWS", "CONSUMES", "MATERIALIZERS", "Context", "RecipeError", "build", "materializers", "order"]

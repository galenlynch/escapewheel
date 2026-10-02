"""Build a packet from a recipe (Part 05 §2).

- :func:`build` -- run every source and return a writer holding the packet, uncommitted.
- :func:`import_packet` -- build the packet a recipe describes and commit it.
- :func:`prepare`, :class:`Prepared` -- what a build settles before it opens a source.
- :func:`commit_arguments` -- the limits and materializers a recipe passes a commit.
- :func:`materializers` -- the recipe's `[[materialize]]` entries as callables `commit` runs.
- :class:`Context` -- what earlier sources produced, for the sources that consume it.
- :data:`MATERIALIZERS` -- the analysis resources a recipe may ask for by name.

The steps of a build that its tests run alone:

- :func:`composed`, :func:`note_unclaimed` -- the rows a build composes, and a note of rows
  nothing claims.
- :func:`grouped_encoding_exceptions` -- the recipe's `[encoding]` block by resource and column.

`sourcing` opens the sources, `facts` compares what they state, `alignment` maps their clocks and
`provenance` writes the rows the build records about itself.

A build orders sources by what each adapter declares it consumes, not by the registry's
references, and filters a source's rows to the resources the recipe leaves it owning.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

from escapewheel_reader.resource_ids import (
    ANALYSIS_SPIKE_EVENTS,
    CORE_CLOCK_ANCHORS,
    CORE_CLOCK_OBSERVATION_INTERVALS,
    CORE_CLOCKS,
    CORE_EVENT_STREAM_OBSERVATION_INTERVALS,
    CORE_EVENT_STREAMS,
    CORE_PREFERRED_RUNS,
    CORE_PROCESSING_RUN_INPUTS,
    CORE_PROCESSING_RUNS,
    CORE_SESSIONS,
    CORE_SOURCE_FILES,
    CORE_SUBJECTS,
    CORE_UNITS,
)
from escapewheel_validator import (
    CheckedRegistryContext,
    Level,
    RegistryRejected,
    RegistryState,
    Report,
    check_registry_context,
)

from . import opaque
from .alignment import TOLERANCE, anchors_by_clock, bound_for, declare_origin, declare_withheld
from .amending import Held
from .errors import (
    AmendmentRefused,
    MaterializerNotFound,
    NotesUnderStrict,
    RecipeFault,
    ReplacementRefused,
    SourceDefect,
    SourceFault,
)
from .extensions import load_checked as load_extension_context
from .facts import as_stored, refuse_a_discarded_fact, stored_types
from .notes import Note, NoteCode
from .protocols import (
    DeclaresCompensations,
    ReferencesArrays,
    ReferencesMedia,
    SourceAdapter,
    StagesArrays,
    StagesPayloads,
    Streams,
)
from .provenance import import_run, preferred_runs, source_roots
from .reading import Delivered
from .recipe import RECIPE_SUPPLIES, Problem, Recipe, SourceSpec, payloads, refusal
from .replacing import Replaced, read_replaced
from .sources.compensations import describe, recordable
from .sourcing import build_source, harvest, order, reference_clock, resolved_source_cache, rows_reader
from .writer import PacketWriter

#: Analysis resources a recipe may ask for by name, and the function that derives each from a
#: staged packet. Part 06 §2 makes these disposable, so a recipe that names none is complete.
MATERIALIZERS: dict[str, str] = {ANALYSIS_SPIKE_EVENTS: "spike_events"}


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
        compound key does not survive the crossing (Part 12 §4). One identity column, not
        three: `core.units` is keyed on `unit_id` alone (Part 02 §12.1), and the tables an
        adapter puts this on declare no other.
    clocks : dict
        Clock ID to that clock's `core.clocks` row, for a source placing an array axis on one.
        An axis advances in ticks (Part 03 §6.3), so a step cannot be derived without the rate, and
        the row is what carries it.
    stores : dict
        Resolved source root and source-cache location to the open store. Three adapters in a
        real recipe read the same `.nwb`; sharing the store means they cannot disagree about what
        is in it, and stops the electrode table being parsed once per adapter.
    stated : dict
        Resource to source kind to the rows that kind produced, for the resources the recipe
        declares a preference for. Held so Part 05 §3.4 can compare the winner's row against the
        one it displaced, and bounded to those resources.
    """

    session_id: str
    sources: dict[str, SourceAdapter] = field(default_factory=dict)
    units: list[dict[str, Any]] = field(default_factory=list)
    clocks: dict[str, dict[str, Any]] = field(default_factory=dict)
    stores: dict[Any, Any] = field(default_factory=dict)
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
    #: `core.clock_observation_intervals` rows, whatever source produced them, since the time
    #: origin is a minimum across all of them and no single adapter sees them all.
    observed: list[dict[str, Any]] = field(default_factory=list)
    #: What `bound_for` measured, for the import run's parameters (Part 02 §12.6).
    measured_bound: dict[str, Any] = field(default_factory=dict)
    #: The anchors and the bound, once `alignment` has settled them.
    _alignment: tuple[dict[str, Any], float] | None = None
    #: Where a source delivered out of process writes: one directory per kind, beside the packet
    #: rather than inside it, so a delivery lands on the filesystem the packet is going to and a
    #: failed build leaves it where it can be looked at.
    workspace: Path = Path()
    #: The packet's staging area, prepared before any source runs, so an array a source writes
    #: there moves into the packet by rename at commit (Part 12 §5).
    staging: Path = Path()
    #: The build's progress reporter, for the stages that happen inside one source rather than
    #: between them -- a delivery being the one that can take minutes on its own.
    say: Callable[[str], None] = lambda _: None
    #: The source-cache location supplied to every adapter accepting `source_cache`, or None where
    #: the build has none (Part 12 §10).
    source_cache: Path | None = None
    #: What the build itself observed, reported beside the adapters' own notes.
    notes: list[str] = field(default_factory=list)
    #: Part 05 §3.6: `block.field` to the registry type the packet stores it as, so a declared
    #: value and a stated one are compared after both are normalized, not as they were written.
    fact_types: dict[str, str] = field(default_factory=dict)
    #: For an amending build, `block.field` to the value the packet's `core.sessions` or
    #: `core.subjects` row holds, which prevails over every source (Part 05 §3.6); None otherwise.
    held_facts: dict[str, Any] | None = None
    #: Source kind to the `opaque_location` supplied it, which the build reads back once it has run.
    opaque_locations: dict[str, Path] = field(default_factory=dict)
    #: The loaded registries' opaque singletons, which a source owns and delivers as a payload
    #: rather than as rows (Part 12 §5), so no table for one is asked for or staged.
    payloads: frozenset[str] = frozenset()

    def alignment(self) -> tuple[dict[str, Any], float]:
        """Return the anchors and the bound to map at, measured once and kept.

        Every mapping in a build has to use the same bound, or the packet says one thing about
        which ticks are convertible and its own origin says another.
        """
        if self._alignment is None:
            by_clock = anchors_by_clock(self)
            reach = {row["clock_id"]: (int(row["start_tick"]), int(row["stop_tick"])) for row in self.observed}
            rate = self.reference.tick_rate_num / (self.reference.tick_rate_den or 1) if self.reference else 1.0
            bound, self.measured_bound = bound_for(by_clock, reach, TOLERANCE, rate)
            self._alignment = (dict(by_clock), bound)
        return self._alignment


def _add_batches(
    writer: PacketWriter, spec: SourceSpec, source: SourceAdapter, counts: dict[str, int], staged: Collection[str] = ()
) -> dict[str, int]:
    """Stream whatever a source streams, rather than holding it as Python mappings.

    `core.spike_events` is the case the streaming path exists for -- 10^8 rows, and a dict per
    row is two orders of magnitude more memory than the Parquet file it becomes. Any source may
    use it for any resource it claims, because an extension's table may be as large as a core
    one and nothing about the reason is specific to spikes.

    Returns
    -------
    dict
        Rows the source produced per resource, whether or not this spec claimed them, for
        `_unclaimed` to compare against the recipe.
    """
    produced: dict[str, int] = {}
    if not isinstance(source, Streams):
        return produced
    # Counted without reading, so an unclaimed table still reports its size.
    offered = source.stream_rows()
    for resource_id, batches in source.batches().items():
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


def composed(spec: SourceSpec, context: Context) -> dict[str, list[dict[str, Any]]]:
    """Return the rows this build composes rather than any one source producing them.

    `core.event_stream_observation_intervals` is the case: one source declares the window it
    watched the reference clock over and another declares the streams watched in it, and
    Part 05 §3.4 leaves a row to a single source, so pairing them is the build's act. Keyed on
    what the spec claims rather than on its kind, since which source declared the window is not
    what decides the composition -- and paired with that source's own window, since two sources
    may each declare one on the reference clock and only one of them is these streams'.
    """
    resource = CORE_EVENT_STREAM_OBSERVATION_INTERVALS
    window = context.windows.get(spec.kind)
    if resource not in spec.claims or window is None or not context.event_streams:
        return {}
    start, stop = window
    if stop < start:
        raise SourceDefect(
            f"{resource}: the acquisition window ends at {stop} and starts at {start}",
            code=SourceFault.WINDOW_REVERSED,
            where=resource,
        )
    # One window for every stream, because they come from a single acquisition: a stream of
    # rare events was watched exactly as long as one of frequent ones, and giving each the
    # extent of its own events would make a rare event look frequent.
    return {
        resource: [
            {"event_stream_id": event_stream_id, "start_tick": start, "stop_tick": stop}
            for event_stream_id in context.event_streams
        ]
    }


def _derive(options: Mapping[str, Any], packet: Any, writer: Any) -> None:
    """Add one derived resource to a writer, reading its inputs from the staged packet."""
    from . import materialize

    materialize.materialize_spike_events(packet, writer, **options)


def materializers(recipe: Recipe, memory_budget: int | str = 0) -> list[Callable[[Any, Any], None]]:
    """Turn a recipe's `[[materialize]]` entries into callables `commit` can run.

    Each is handed the staged packet and the writer, which is the pair `materialize_spike_events` takes:
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
    MaterializerNotFound
        If a resource is named that nothing knows how to derive.
    """
    built: list[Callable[[Any, Any], None]] = []
    for spec in recipe.materialize:
        if spec.resource not in MATERIALIZERS:
            known = sorted(MATERIALIZERS)
            raise MaterializerNotFound(
                f"no materializer for {spec.resource}; this writer derives {', '.join(known) or 'nothing'}",
                resource=spec.resource,
                known=known,
            )
        options = dict(spec.options)
        if memory_budget and "memory_budget" not in options:
            options["memory_budget"] = memory_budget
        built.append(partial(_derive, options))
    return built


@dataclass(frozen=True)
class Prepared:
    """What a build settles before it opens a source (Part 05 §3.5).

    Attributes
    ----------
    registry : CheckedRegistryContext
        The core registry, valid.
    extensions : tuple of CheckedRegistryContext
        The extension registries the build binds, each valid.
    held : Held or None
        The packet an amending recipe amends, opened; None where the recipe amends none.
    problems : tuple of Problem
        Everything the recipe's check reports, warnings included.
    """

    registry: CheckedRegistryContext
    extensions: tuple[CheckedRegistryContext, ...]
    held: Held | None
    problems: tuple[Problem, ...]

    @property
    def errors(self) -> list[Problem]:
        """The problems that refuse the recipe."""
        return [problem for problem in self.problems if problem.level == Level.ERROR]


def prepare(
    recipe: Recipe,
    registry: Mapping[str, Any] | CheckedRegistryContext,
    *,
    extension_contexts: Collection[CheckedRegistryContext] | None = None,
) -> Prepared:
    """Check the registries and the recipe, and open the packet an amending recipe amends.

    The recipe's problems are returned and not raised, so a caller can report every one before it
    refuses.

    Parameters
    ----------
    recipe : Recipe
        The parsed recipe.
    registry : Mapping or CheckedRegistryContext
        The core registry to write against.
    extension_contexts : collection of CheckedRegistryContext, optional
        The extension registries to bind. Those the recipe names are loaded where absent.

    Raises
    ------
    RegistryRejected
        If the core registry, or an extension's, is not valid.
    AmendmentRefused
        If the recipe amends a packet no build can amend.
    """
    registry_context = registry if isinstance(registry, CheckedRegistryContext) else check_registry_context(registry)
    if registry_context.result.state != RegistryState.VALID:
        raise RegistryRejected("core", registry_context)
    checked_registry = registry_context.document
    assert isinstance(checked_registry, Mapping)
    if extension_contexts is None:
        extension_contexts = tuple(
            load_extension_context(named, registry_context, base=recipe.path.parent) for named in recipe.extensions
        )
    for extension_context in extension_contexts:
        if extension_context.result.state != RegistryState.VALID:
            document = extension_context.document
            subject = str(document.get("extension_id", "extension")) if isinstance(document, Mapping) else "extension"
            raise RegistryRejected(subject, extension_context)
    held = Held.open(recipe.out) if recipe.amends is not None else None
    problems = recipe.check(
        checked_registry,
        [extension.document for extension in extension_contexts],
        held_tables=() if held is None else held.tables_named(),
        held_clocks=() if held is None else held.clock_names(),
    )
    return Prepared(registry_context, tuple(extension_contexts), held, tuple(problems))


def build(  # noqa: C901
    recipe: Recipe,
    registry: Mapping[str, Any] | CheckedRegistryContext,
    *,
    extension_contexts: Collection[CheckedRegistryContext] | None = None,
    say: Callable[[str], None] = lambda _: None,
    strict: bool = False,
    source_cache: str | Path | None = None,
    replaced: Sequence[Replaced] | None = None,
    prepared: Prepared | None = None,
) -> PacketWriter:
    """Run every source and return a writer holding the packet, uncommitted.

    Parameters
    ----------
    recipe : Recipe
        The parsed recipe. A build MUST refuse an unsound one before it opens any source
        (Part 05 §3.5).
    registry : Mapping or CheckedRegistryContext
        The registry to write against.
    say : callable, optional
        Progress reporter.
    strict : bool, default False
        Refuse the build on any adapter note. A note is something the importer worked around --
        an absent column, a dropped timestamp, an offset that disagreed -- and every one is a
        place the packet says less than the source could have. Off by default because working
        around them is the point of an adapter; on in CI, where a new one is news.
    source_cache : str or Path, optional
        The source-cache location, supplied as `source_cache` to each adapter accepting it
        (Part 12 §10). Created where absent and never emptied. One inside the packet root or the
        delivery workspace is supplied to no adapter, and the build notes that and proceeds.
    replaced : sequence of Replaced, optional
        The packets `[packet].replaces` names, already read by a caller that compares against them.
        Read here where absent, before any source opens.
    prepared : Prepared, optional
        What :func:`prepare` returned for this recipe, from a caller that reported its problems.
        Its registries are the ones written against. Prepared here where absent.

    Returns
    -------
    PacketWriter
        Loaded with every record, ready to commit.
    """
    if prepared is None:
        try:
            prepared = prepare(recipe, registry, extension_contexts=extension_contexts)
        except AmendmentRefused as exc:
            raise refusal(recipe, "refused: ", [_amendment_refused(exc)], cites=" (Part 05 §3.5)") from exc
    registry_context = prepared.registry
    checked_registry = registry_context.document
    assert isinstance(checked_registry, Mapping)
    extension_contexts = prepared.extensions
    extension_documents = [extension.document for extension in extension_contexts]
    held = prepared.held
    if held is not None:
        _refuse_another_packet(recipe, held, checked_registry, extension_documents)
    if replaced is None:
        try:
            replaced = read_replaced(recipe.replaces, recipe.path.parent)
        except ReplacementRefused as exc:
            raise refusal(recipe, "refused, [packet].replaces (Part 05 §3.5): ", exc.problems) from exc
    if errors := prepared.errors:
        raise refusal(recipe, f"refused, {len(errors)} error(s): ", errors)
    session_id = str(recipe.session["session_id"])
    context = Context(
        session_id=session_id,
        fact_types=stored_types(checked_registry),
        workspace=Path(f"{recipe.out}.deliveries"),
        say=say,
        payloads=payloads(checked_registry, extension_documents),
    )
    context.source_cache = resolved_source_cache(source_cache, recipe.out, context)
    if recipe.session.get("reference_clock_id"):
        context.reference = reference_clock(recipe, context)
    writer = PacketWriter(
        registry_context,
        packet_id=recipe.packet_id,
        description=recipe.description,
        # Part 05 §3.1: the recipe names them, so a source may own an extension's table exactly as it
        # owns a core one. Which is what keeps declaring an extension from being harder than
        # adding a column to core -- the gradient that leaves NWB's own mechanism unused.
        extensions=tuple(extension_contexts),
        # Part 02 §7.1's fill needs the session before any source runs, and `core.sessions` is staged
        # last, so it is given here rather than read back.
        session=session_id,
        # An extension reaches the writer across a file or a subprocess, so what it says about its
        # own columns arrives as recipe data rather than as a Python object it hands over.
        encoding_exceptions=grouped_encoding_exceptions(recipe),
        workspace=context.workspace,
        replaces=[r.item() for r in replaced],
    )
    if held is not None:
        try:
            writer.amending(held, prevail=True)
        except AmendmentRefused as exc:
            raise refusal(recipe, "refused: ", [_amendment_refused(exc)]) from exc
        _from_packet(context, held, writer, session_id)
    context.staging = writer.stage_at(recipe.out)

    # The recipe supplies `core.subjects` only where no source owns it, so a packet
    # whose NWB claims the table gets the row that file states rather than a hand-typed one.
    if recipe.subject and CORE_SUBJECTS not in recipe.owners:
        writer.add(CORE_SUBJECTS, [dict(recipe.subject)])

    counts: dict[str, int] = {}
    #: Every compensation a source stated, in full (Part 05 §4.3).
    compensated: list[Mapping[str, str | None]] = []
    #: Notes each source had said by the time it was run, so a later one can be told apart.
    drained: dict[str, int] = {}
    for spec in order(recipe):
        say(f"{spec.kind} -> {', '.join(spec.owns) or 'nothing it owns'}")
        source = build_source(spec, recipe, context)
        context.sources[spec.kind] = source
        # Once, and used twice: an adapter's records are expensive to build, and the harvest and
        # the staging are two readings of one set of rows.
        records = source.records()
        harvest(spec, source, context, recipe, rows_reader(source, records))

        produced = _add_records(writer, spec, records, context, counts, arbitrated=frozenset(recipe.preferred))
        produced.update(_add_batches(writer, spec, source, counts, staged=set(produced)))
        note_unclaimed(spec, source, produced, frozenset(recipe.preferred))
        for staged in source.staged_arrays() if isinstance(source, StagesArrays) else ():
            # A delivered array is bytes an adapter already wrote (Part 12 §5), so what there
            # is to say about it is what is on disk; one staged in process is values, and its
            # shape is what a reader of the log wants before it costs anything to write.
            if staged.values is None and staged.written is not None:
                stored = sum(f.stat().st_size for f in staged.written.rglob("*") if f.is_file())
                say(f"  array {staged.resource_id} delivered, {stored / 1e6:.1f} MB written")
            else:
                say(
                    f"  array {staged.array_asset_id} {staged.values.shape} {staged.values.dtype}, "
                    f"{staged.values.nbytes / 1e6:.1f} MB raw"
                )
            writer.add_array(staged.resource_id, staged)
        for resource_id, array in (source.external_arrays() if isinstance(source, ReferencesArrays) else {}).items():
            writer.reference_array(resource_id, array)
            say(f"  referenced {resource_id}")
        for resource_id, media in (source.external_media() if isinstance(source, ReferencesMedia) else {}).items():
            writer.reference_media(resource_id, media)
            size = f", {media.size_bytes / 1e9:.2f} GB" if media.size_bytes else ""
            say(f"  referenced {resource_id}{size}")
        # An adapter in this process may hand its payloads over as bytes, which the build writes where
        # a protocol adapter would have, so both are read back and refused the same way.
        location = context.opaque_locations.get(spec.kind)
        opaque.write(source.staged_payloads() if isinstance(source, StagesPayloads) else (), location, spec.kind)
        if location is not None:
            for payload in writer.add_payloads(spec.kind, location, owned=spec.owns):
                say(f"  payload {payload.resource_id}: {opaque.shown(Path(payload.path.name))}")

        drained[spec.kind] = _say_notes(spec.kind, source, 0, say, strict)
        if isinstance(source, Delivered):
            compensated.extend(source.compensated)
        elif isinstance(source, DeclaresCompensations):
            compensated.extend(describe(source.compensations))

    refuse_a_discarded_fact(writer, context, recipe)
    declare_withheld(context, writer, say)
    if held is None:
        # An amendment keeps the packet's session row, derived facts included (Part 05 §3.6).
        declare_origin(context, say)
    for note in context.notes:
        say(f"  note: {note}")
    if held is None:
        writer.add(
            CORE_SESSIONS,
            [
                {
                    "session_id": session_id,
                    **{k: v for k, v in recipe.session.items() if k != "session_id"},
                    **context.session_extra,
                }
            ],
        )
    run = import_run(recipe, compensated, context)
    run["processing_run_id"] = writer.name_apart("processing_run_id", run["processing_run_id"])
    writer.add(CORE_PROCESSING_RUNS, [run])
    if roots := source_roots(recipe):
        # A root the packet already records keeps its row, and the import still names it (Part 05 §7).
        recorded = {} if held is None else held.source_files(writer.keys)
        if added := [root for root in roots if root not in recorded]:
            writer.add(CORE_SOURCE_FILES, [{"source_file_id": root, "uri": root} for root in added])
        writer.add(
            CORE_PROCESSING_RUN_INPUTS,
            [
                {
                    "session_id": session_id,
                    "processing_run_id": run["processing_run_id"],
                    "source_file_id": recorded.get(root, root),
                }
                for root in roots
            ],
        )
    if recipe.preferred_runs:
        writer.add(CORE_PREFERRED_RUNS, preferred_runs(recipe, writer, held, session_id))
    for entry in recordable(compensated):
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


def commit_arguments(recipe: Recipe, memory_budget: int | str = 0) -> dict[str, Any]:
    """Return what a recipe passes a commit: its limits and its materializers, under one budget.

    A budget given here wins over the recipe's, since the recipe travels with the data and the
    machine building it does not.
    """
    budget = memory_budget or recipe.memory_budget
    limits = {name: value for name, value in recipe.limits.items() if name != "memory_budget"}
    if budget and "memory_limit" not in limits:
        limits["memory_limit"] = budget
    return {"limits": limits or None, "materialize": materializers(recipe, memory_budget=budget)}


def import_packet(
    recipe: Recipe,
    registry: Mapping[str, Any] | CheckedRegistryContext,
    *,
    extension_contexts: Collection[CheckedRegistryContext] | None = None,
    say: Callable[[str], None] = lambda _: None,
    strict: bool = False,
    source_cache: str | Path | None = None,
    replaced: Sequence[Replaced] | None = None,
    prepared: Prepared | None = None,
    memory_budget: int | str = 0,
) -> Report:
    """Build the packet a recipe describes and commit it at `recipe.out` (Part 05 §2).

    The packet is amended where the recipe amends one (Part 05 §15). `memory_budget` is
    :func:`commit_arguments`'s, and every other parameter is :func:`build`'s.

    Returns
    -------
    Report
        The validation the commit passed.

    Raises
    ------
    CommitRefused
        If the staged packet fails validation, in which case nothing is published.
    """
    writer = build(
        recipe,
        registry,
        extension_contexts=extension_contexts,
        say=say,
        strict=strict,
        source_cache=source_cache,
        replaced=replaced,
        prepared=prepared,
    )
    publish = writer.amend if recipe.amends is not None else writer.commit
    return publish(recipe.out, say=say, **commit_arguments(recipe, memory_budget))


def _refuse_another_packet(
    recipe: Recipe, held: Held, registry: Mapping[str, Any], extensions: Collection[Mapping[str, Any]]
) -> None:
    """Refuse an amending recipe the packet it amends does not answer to (Part 05 §3.5)."""
    manifest = held.manifest
    problems = []
    if manifest["packet_id"] != recipe.packet_id:
        problems.append(
            Problem(
                Level.ERROR,
                f"the packet at {recipe.out} is {manifest['packet_id']}, and [packet].id is {recipe.packet_id}",
                RecipeFault.AMENDS_OTHER_PACKET,
            )
        )
    if manifest["packet_version"] != recipe.amends:
        problems.append(
            Problem(
                Level.ERROR,
                f"the packet at {recipe.out} is at version {manifest['packet_version']}, and [packet].amends is "
                f"{recipe.amends}",
                RecipeFault.AMENDS_OTHER_VERSION,
            )
        )
    if str(recipe.session.get("session_id")) not in manifest.get("sessions", ()):
        problems.append(
            Problem(
                Level.ERROR,
                f"the packet does not list session {recipe.session.get('session_id')}",
                RecipeFault.AMENDS_OTHER_SESSION,
            )
        )
    for document in (registry, *extensions):
        name = str(document.get("extension_id", "core"))
        standards = ("logical_standard_version",) + (("semantic_standard_version",) if name == "core" else ())
        problems += [
            Problem(
                Level.ERROR,
                f"registry {name} has {standard} {document.get(standard)}, and the packet {manifest.get(standard)}",
                RecipeFault.AMENDS_OTHER_STANDARD,
            )
            for standard in standards
            if document.get(standard) != manifest.get(standard)
        ]
    if problems:
        raise refusal(recipe, "refused, an amending recipe (Part 05 §3.5): ", problems)


def _amendment_refused(refusal: AmendmentRefused) -> Problem:
    """Return an amendment's refusal as the problem a recipe's refusal carries."""
    return Problem(Level.ERROR, str(refusal), RecipeFault.AMENDMENT_REFUSED)


def _from_packet(context: Context, held: Held, writer: PacketWriter, session_id: str) -> None:
    """Take the packet's rows as delivered before any source runs (Part 05 §4.3).

    So a source that consumes clocks, units or the reference clock is handed the packet's, named as
    a source names them, and the facts the packet's session and subject rows hold prevail.
    """
    from .clock import Clock

    keys = writer.keys
    for row in held.named_rows(CORE_CLOCKS, keys):
        context.clocks[str(row["clock_id"])] = {k: v for k, v in row.items() if v is not None}
    context.units += [
        {
            "device_name": str(row["sorting_run_id"]).rsplit(".", 1)[-1],
            "local_unit_label": row["local_unit_label"],
            "unit_id": row["unit_id"],
        }
        for row in held.named_rows(CORE_UNITS, keys)
    ]
    context.anchors += held.named_rows(CORE_CLOCK_ANCHORS, keys)
    context.event_streams += [row["event_stream_id"] for row in held.named_rows(CORE_EVENT_STREAMS, keys)]
    sessions = [r for r in held.named_rows(CORE_SESSIONS, keys) if str(r["session_id"]) == session_id]
    subjects = {str(r["subject_id"]): r for r in held.named_rows(CORE_SUBJECTS, keys)}
    session = sessions[0] if sessions else {}
    subject = subjects.get(str(session.get("subject_id")), {})
    context.held_facts = {
        **{f"session.{k}": v for k, v in session.items()},
        **{f"subject.{k}": v for k, v in subject.items()},
    }
    reference = context.clocks.get(str(session.get("reference_clock_id")))
    if reference is not None and reference.get("tick_rate_num") is not None:
        context.reference = Clock(
            str(reference["clock_id"]),
            session_id=session_id,
            name=str(reference.get("clock_name", reference["clock_id"])),
            tick_rate_num=int(reference["tick_rate_num"]),
            tick_rate_den=int(reference.get("tick_rate_den", 1)),
            origin=str(reference["origin"]),
            tick_zero_utc=as_stored(reference.get("tick_zero_utc"), "timestamp"),
            parent_clock_id=reference.get("parent_clock_id"),
        )


def _say_notes(kind: str, source: SourceAdapter, seen: int, say: Callable[[str], None], strict: bool) -> int:
    """Report a source's notes past the `seen` already reported, and return the new total."""
    notes = list(source.notes)
    for note in notes[seen:]:
        say(f"  note: {note}")
    if strict and len(notes) > seen:
        raise NotesUnderStrict(
            f"{kind}: {len(notes) - seen} note(s) under --strict; first is {notes[seen]}", kind=kind, notes=notes[seen:]
        )
    return len(notes)


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
    for resource, rows in {**records, **composed(spec, context)}.items():
        produced[resource] = len(rows)
        if resource in arbitrated:
            # Kept rather than counted, so the build can compare what the winner staged against
            # what the source it displaced stated. Only where a preference arbitrates, which is
            # what keeps this bounded.
            context.stated.setdefault(resource, {})[spec.kind] = rows
        if resource not in spec.claims or resource in context.payloads:
            continue
        if resource == CORE_CLOCK_OBSERVATION_INTERVALS:
            # The time origin is a minimum across every clock, and no adapter sees them all.
            context.observed.extend(rows)
        writer.add(resource, rows)
        counts[resource] = counts.get(resource, 0) + len(rows)
    return produced


def grouped_encoding_exceptions(recipe: Recipe) -> dict[str, dict[str, tuple[str, ...]]]:
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


def note_unclaimed(
    spec: SourceSpec, source: SourceAdapter, produced: Mapping[str, int], preferred: frozenset[str] = frozenset()
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
    if not dropped:
        return
    listed = ", ".join(f"{resource} ({rows:,} rows)" for resource, rows in sorted(dropped.items()))
    source.notes.append(
        Note(
            f"{spec.kind} produced {listed}, which no source in this recipe claims; discarded",
            NoteCode.UNCLAIMED_DISCARDED,
        )
    )


__all__ = [
    "MATERIALIZERS",
    "Context",
    "Prepared",
    "build",
    "commit_arguments",
    "composed",
    "grouped_encoding_exceptions",
    "import_packet",
    "materializers",
    "note_unclaimed",
    "prepare",
]

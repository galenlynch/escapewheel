"""The writer's ``escapewheel`` subcommands, found through the ``escapewheel.commands`` group.

- :func:`register` -- add ``inspect``, ``init``, ``import``, ``extension``, ``verify``, ``prune``,
  ``prune-cache``, ``declare`` and ``deliver`` to ``escapewheel``.
- :func:`declaration_protocols` -- Part 12 §3's protocol group, imported only when called.
- :data:`KINDS` -- the source kinds ``init`` and ``inspect`` can open with nothing but a root.

``deliver`` reads the terms a build supplies from standard input and takes no argument beyond the
kind, so running it by hand is `escapewheel deliver nwb < supplied.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from escapewheel_reader.errors import EscapewheelError
from escapewheel_reader.registries import gunzip_member
from escapewheel_validator import (
    EvaluationStatus,
    Level,
    RegistryRejected,
    RegistryState,
    check_registry_context_bytes,
)

from .. import compare
from ..amending import Held
from ..errors import AmendmentRefused, CommitRefused, ReplacementRefused, SourceDefect
from ..extensions import load_checked as load_extension_context
from ..recipe import RECIPE_SUPPLIES, Recipe, contributes, produces
from ..replacing import read_replaced
from ..session import build, materializers


def declaration_protocols() -> tuple[str, ...]:
    """Part 12 §3's group, read where the CLI is built rather than imported at module load."""
    from ..declaration import PROTOCOLS

    return PROTOCOLS


#: What the recipe declares rather than reading from a source, spelled for a draft's comment.
SUPPLIES_NOTE = "the recipe supplies core.sessions, core.subjects and core.processing_runs"

#: Kinds `_open` can construct with nothing but a root, which is what `init` and `inspect`
#: need. Narrower than the kinds a build accepts: `video` needs a clock, `session` a zone,
#: and `waveforms` the sorting it describes, so none can be opened on its own.
#: `test_arbitration.py` refuses a kind here that `_open` would turn away, and one that
#: `sources.ADAPTERS` does not know.
KINDS = ("lfp", "nwb", "sorter", "sync")

#: Options an adapter requires that no inspection can supply, drafted so the recipe builds.
#: `_build_source` pops these; without them a build dies on a KeyError rather than a finding.
REQUIRED = {
    "nwb": (("zone", '"America/Los_Angeles"', "the rig's zone, which resolves a naive stamp"),),
}

#: Values a draft guesses because nothing it read says. Marked, the way a contested resource
#: is: a draft that guesses silently is worse than one that says where to look.
GUESSED = "  # GUESS: nothing inspected says this; check it"


def _open(kind: str, root: Path, session_id: str) -> Any:
    """Construct a source for inspection, with the least configuration that will open it."""
    from ..sources import NWBSource, SorterSource, SyncSource

    if kind == "sorter":
        return SorterSource(root, session_id=session_id)
    if kind == "sync":
        return SyncSource(root, session_id=session_id)
    if kind == "lfp":
        from ..sources import LFPSource

        # Inspecting reads what the series declare; the clocks a build passes in change what the
        # rows say, not how many there are.
        return LFPSource(root, session_id=session_id)
    if kind == "nwb":
        # A stand-in row: counting what the file offers needs a grid to convert against, and any
        # rate answers that. Which clock it really is decides tick values, which discovery does not
        # report.
        row = {"clock_id": "harp", "session_id": session_id, "origin": "HARP epoch", "tick_rate_num": 31250}
        return NWBSource(root, reference_clock=row, zone="UTC", session_id=session_id)
    raise SystemExit(f"error: {kind} cannot be inspected on its own; it consumes another source")


def _inspect(args: argparse.Namespace) -> int:
    """Report what one source offers (Part 05 §4.1)."""
    source = _open(args.kind, args.root, args.session_id)
    offered = source.offers()
    print(f"{args.kind}  {args.root}")
    for resource, rows in sorted(offered.items()):
        print(f"  {resource:44s} {rows:>12,}")
    for note in getattr(source, "notes", []):
        print(f"  note: {note}")
    if not offered:
        print("  offers nothing")
    return 0


def _init(args: argparse.Namespace) -> int:
    """Draft a recipe from what several sources report they hold."""
    offers: dict[str, dict[str, int]] = {}
    for pair in args.source:
        kind, _, root = pair.partition("=")
        if kind not in KINDS or not root:
            raise SystemExit(f"error: --source takes kind=path, with kind one of {', '.join(KINDS)}")
        offers[kind] = _open(kind, Path(root), args.session_id).offers()

    lines = [
        "# Drafted by `escapewheel init` from what each source reported holding.",
        "# Each source owns by default what its adapter can supply. A resource two of them can own is",
        "# refused until a [preference] at the end names one, and every line marked GUESS is one",
        "# nothing inspected could settle.",
        "",
        "[packet]",
        f'id = "{args.session_id}"',
        f'out = "{args.session_id}"{GUESSED}',
        'registry = "spec/artifacts/logical_schemas.json"',
        "",
        "[session]",
        f'session_id = "{args.session_id}"',
        f'reference_clock_id = "harp"{GUESSED}',
        f"# session_start_time, session_end_time and subject_id belong here too: {SUPPLIES_NOTE}",
        "# session.json carries them, and stamps a Pacific wall clock as UTC -- localize first.",
        "",
        "[subject]",
        f'subject_id = "{args.session_id.split("_")[1] if "_" in args.session_id else args.session_id}"' + GUESSED,
        "# date_of_birth, sex and genotype belong here, from subject.json",
        "",
        "# Every clock a source names must be declared, including the reference above.",
        "[[clock]]",
        f'clock_id = "harp"{GUESSED}',
        f'name = "harp"{GUESSED}',
        f"tick_rate_num = 31250{GUESSED}",
        f'origin = "harp_counter"{GUESSED}',
        "",
    ]
    listed = [p.split("=", 1) for p in args.source]
    # The recipe supplies these itself, so handing one to a source is a conflict the checker then
    # reports (recipe.RECIPE_SUPPLIES).
    supplies = frozenset(RECIPE_SUPPLIES)
    # What each entry without `owns` would own (Part 05 §3.4), which is where a build finds a
    # contest. Read from the declarations rather than the offers, since those are what it reads.
    defaults = {kind: produces(kind) - contributes(kind) - supplies for kind, _ in listed}
    contested = {
        resource: kinds
        for resource in sorted(set().union(*defaults.values()))
        if len(kinds := sorted(k for k in defaults if resource in defaults[k])) > 1
    }
    for kind, root in listed:
        lines += ["[[source]]", f'kind = "{kind}"', f'root = "{root}"']
        for option, value, why in REQUIRED.get(kind, ()):
            lines += [f"# {why}", f"{option} = {value}{GUESSED}"]
        lines += [
            f"# can own {r}, as can {', '.join(k for k in contested[r] if k != kind)}"
            for r in sorted(defaults[kind])
            if r in contested
        ]
        lines += [f"# supplies {r}, which the recipe declares itself" for r in sorted(set(offers[kind]) & supplies)]
        lines += [*HINTS.get(kind, ()), ""]
    if contested:
        # A candidate and not a choice: which source knows more is the author's to say (Part 05
        # §3.3), so the draft is refused until they uncomment one.
        lines += ["# Uncomment one preference per resource, naming the source that knows more and why."]
        for resource, kinds in contested.items():
            lines += [
                f'# [preference."{resource}"]',
                f'# source = "{kinds[0]}"  # or {", ".join(kinds[1:])}',
                '# reason = ""',
                "",
            ]

    text = "\n".join(lines)
    if args.out is None:
        print(text)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"drafted {args.out}")
    return 0


#: Options a drafted `[[source]]` mentions but does not set, commented out. They change what a
#: packet claims rather than what it contains, so a default standing in for the decision is worse
#: than an absence someone has to look at.
HINTS = {
    "lfp": (
        '# uri_base = "s3://bucket/prefix"   # where the referenced arrays actually live',
        '# verify = "members"                # record R51 members and store digests, at list cost',
        '# verify = "sha256"                 # digest every byte too: 75 s here, 88 s from S3',
    ),
}


def _import(args: argparse.Namespace) -> int:
    """Build and commit a packet from a recipe (Part 05 §2, delivery through publication).

    A refusal is printed, never raised. The status is 2 where the recipe, a registry, a source or
    the build refuses before the commit begins, and 1 where the commit is refused.
    """
    try:
        return _build_and_commit(args)
    except EscapewheelError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _build_and_commit(args: argparse.Namespace) -> int:  # noqa: C901
    """Run an import, raising what refuses it before the commit and returning 1 for a refused commit."""
    # The override goes into the load rather than onto the result: a build derives where a
    # delivery lands from where the packet is going.
    recipe = Recipe.load(args.recipe, out=args.out)
    registry_path = args.registry or recipe.registry
    # Part 05 §15.1: an amending build binds, under an ID its recipe names nothing for, the
    # registry the packet binds.
    bound = _bound_registries(recipe.out) if recipe.amends is not None else {}
    if registry_path is None and "core" not in bound:
        print("error: no registry; declare [packet].registry or pass --registry", file=sys.stderr)
        return 2
    core_context = check_registry_context_bytes(
        Path(registry_path).read_bytes() if registry_path is not None else bound["core"]
    )
    if args.registry_result is not None:
        args.registry_result.write_text(json.dumps(core_context.result.to_dict(), indent=2) + "\n")
    if core_context.result.state != RegistryState.VALID:
        print(f"error: core registry is {core_context.result.state}", file=sys.stderr)
        return 2
    registry = core_context.document
    extension_contexts = [
        load_extension_context(named, core_context, base=recipe.path.parent) for named in recipe.extensions
    ]
    named_ids = {
        str(context.document.get("registry_id")) for context in extension_contexts if isinstance(context.document, dict)
    }
    extension_contexts += [
        check_registry_context_bytes(body, core=core_context)
        for registry_id, body in sorted(bound.items())
        if registry_id != "core" and registry_id not in named_ids
    ]
    rejected = [context for context in extension_contexts if context.result.state != RegistryState.VALID]
    if rejected:
        print(f"error: extension registry is {rejected[0].result.state}", file=sys.stderr)
        return 2
    extensions = [context.document for context in extension_contexts]
    if args.sample:
        recipe = recipe.with_sample(args.sample)

    held = {}
    if recipe.amends is not None:
        try:
            amended = Held.open(recipe.out)
        except AmendmentRefused as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        held = {"held_tables": amended.tables_named(), "held_clocks": amended.clock_names()}
    problems = recipe.check(registry, extensions, **held)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    if any(p.level == "error" for p in problems):
        print(f"{recipe.path}: refused, {sum(p.level == 'error' for p in problems)} error(s)", file=sys.stderr)
        return 2
    try:
        replaced = read_replaced(recipe.replaces, recipe.path.parent)
    except ReplacementRefused as exc:
        print(f"{recipe.path}: refused, [packet].replaces (Part 05 §3.5): {exc}", file=sys.stderr)
        return 2
    if args.check:
        print(f"{recipe.path}: sound")
        return 0

    for source in recipe.sources:
        if not source.root.exists():
            print(f"error: {source.kind} root {source.root} does not exist", file=sys.stderr)
            return 2

    # Stamped and flushed. An import is minutes long and its stages cost very differently, so
    # the log has to say where the time went; print block-buffers when stdout is not a terminal.
    start = time.perf_counter()

    def say(line: str) -> None:
        print(f"[{time.perf_counter() - start:6.1f}s] {line}", flush=True)

    # One budget for the build. The CLI wins over the recipe, because the recipe travels with
    # the data and the machine packaging it does not.
    budget = args.memory_budget or recipe.memory_budget
    try:
        writer = build(
            recipe,
            core_context,
            extension_contexts=extension_contexts,
            say=say,
            strict=args.strict,
            source_cache=_source_cache(args, recipe.out),
            replaced=replaced,
        )
    except RegistryRejected as exc:
        print(json.dumps(exc.result.to_dict(), indent=2), file=sys.stderr)
        return 2
    derive = materializers(recipe, memory_budget=budget)
    limits = {k: v for k, v in recipe.limits.items() if k != "memory_budget"}
    if budget and "memory_limit" not in limits:
        limits["memory_limit"] = budget
    out = recipe.out
    # Read before the commit writes over it: after `commit` there is nothing left to compare
    # against. A packet the recipe names is each its own reference (Part 05 §9.3).
    if args.compare or not replaced:
        where = str(args.compare) if args.compare else "the packet it overwrites"
        references = [(where, compare.resources(args.compare or out))]
    else:
        references = [(named.entry, named.resources) for named in replaced]
    try:
        if recipe.amends is not None:
            report = writer.amend(out, limits=limits or None, say=say, materialize=derive)
        else:
            report = writer.commit(out, limits=limits or None, say=say, materialize=derive)
    except CommitRefused as exc:
        _say_refusal(exc)
        return 1
    except EscapewheelError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    built = compare.resources(out)
    for where, reference in references:
        if dropped := compare.lost(reference, built):
            print(f"warning: {len(dropped)} resource(s) in {where} are not in this build:", file=sys.stderr)
            for resource_id in dropped:
                print(f"  lost  {resource_id}", file=sys.stderr)
    print(f"committed {out} — {report.warnings} warning(s)")
    return 0


def _bound_registries(root: Path) -> dict[str, bytes]:
    """Return the exact bytes of each registry the packet at `root` binds, by registry ID."""
    manifest = root / "packet.json"
    if not manifest.is_file():
        return {}
    registries = json.loads(manifest.read_text()).get("registries", {})
    return {name: gunzip_member((root / bound["path"]).read_bytes()) for name, bound in registries.items()}


def _source_cache(args: argparse.Namespace, out: Path) -> Path | None:
    """Return the location `import` supplies as `source_cache`: the one named, else beside the packet.

    Beside rather than under `TMPDIR`, which is RAM wherever `/tmp` is a tmpfs, so a cgroup cap
    would not bound what a build fetches; and in the packet's parent, so a rebuild into a new
    directory reads what the last one kept.
    """
    if args.no_source_cache:
        return None
    return args.source_cache or out.parent / ".escapewheel-source-cache"


def _prune_cache(args: argparse.Namespace) -> int:
    """Report, or remove, what this writer keeps in a source-cache location (Part 12 §10)."""
    from ..sources.store import STORAGE_FORMAT, prune_kept

    found = prune_kept(args.location, older_than=args.older_than, apply=args.apply)
    total = sum(size for _, size in found)
    verb = "removed" if args.apply else "would remove"
    print(f"{args.location / STORAGE_FORMAT}: {verb} {len(found)} file(s), {total:,} bytes")
    return 0


def _say_refusal(exc: CommitRefused) -> None:
    """Name each registry's verdict, so a refusal says whether core or an extension failed (Part 05 §9.5)."""
    report = exc.report
    for finding in [f for f in report.findings if f.level == Level.ERROR][:20]:
        where = f"[{finding.registry}] " if finding.registry else ""
        print(f"  {finding.level:8s} {where}{finding.check}: {finding.message}", file=sys.stderr)
    for evaluation in report.evaluations:
        if evaluation.status != EvaluationStatus.COMPLETE:
            print(f"  {evaluation.status:8s} [{evaluation.registry}] {evaluation.rule or ''}", file=sys.stderr)
    verdicts = ", ".join(f"{name} {report.verdict(name)}" for name in report.bound)
    print(
        f"refused: packet {report.verdict()} ({verdicts}), {report.errors} error(s); staging left at {exc.staging}",
        file=sys.stderr,
    )


def _verify(args: argparse.Namespace) -> int:
    """Record what is true about a committed packet's external resources (Part 04 §5.2)."""
    from ..verify import verify

    report, manifest = verify(args.packet, level=args.level)
    for finding in report.findings:
        print(f"  {finding.level:8s} {finding.check}: {finding.message}")
    if not report.passed:
        print(f"\nnothing recorded — {report.errors} error(s); the packet stays at its version")
        return 1
    print(f"\n{manifest['packet_id']}: recorded at version {manifest['packet_version']}")
    return 0


def _prune(args: argparse.Namespace) -> int:
    """Remove what a committed packet no longer names (Part 05 §15.5)."""
    from ..prune import prune

    plan = prune(
        args.packet,
        keep_versions=args.keep_versions,
        keep_days=args.keep_days,
        apply=args.apply,
    )
    mark = "removed" if plan.applied else "to remove"
    for path in plan.orphans:
        print(f"  orphan    {mark:9s} {path.relative_to(args.packet)}")
    for path in plan.expired:
        print(f"  manifest  {mark:9s} {path.relative_to(args.packet)}")
    for path in plan.strays:
        print(f"  stray     kept      {path.relative_to(args.packet)}")
    # A build's own files, which the next build or amendment removes (Part 05 §§2 and 6).
    for path in plan.staged:
        print(f"  staged    kept      {path.relative_to(args.packet)}")
    for path in plan.promoting:
        print(f"  promoting kept      {path.relative_to(args.packet)}")
    for note in plan.notes:
        print(f"  note      {note}")
    verb = "removed" if plan.applied else "would remove"
    kept = f", {len(plan.retained)} superseded manifest(s) retained" if plan.retained else ""
    print(f"\n{verb} {len(plan)} file(s); {len(plan.strays)} stray kept{kept}")
    if not plan.applied and len(plan):
        print("nothing was removed; pass --apply")
    return 0


def _extension(args: argparse.Namespace) -> int:
    """Draft an extension registry from tables that already exist (Part 09 §5.1)."""
    from ..scaffold import draft

    tables = {}
    for pair in args.table:
        if "=" not in pair:
            print(f"error: --table takes name=path, not {pair!r}", file=sys.stderr)
            return 2
        name, path = pair.split("=", 1)
        if not Path(path).is_file():
            print(f"error: {path} does not exist", file=sys.stderr)
            return 2
        tables[name] = Path(path)

    drafted = draft(args.extension_id, tables)
    written = drafted.write(args.out or Path(f"{args.extension_id}.json"))
    print(f"drafted {written} — {len(drafted.document['resources'])} table resource(s)")
    print(f"\n{len(drafted.decisions)} decision(s) this cannot make for you:")
    for decision in drafted.decisions:
        print(f"  {decision}")
    print(
        "\nThe draft does not validate until every role is chosen, which is deliberate: R48 §2.2 "
        "\nrefuses a default because a forgotten classification would look like a decision."
    )
    return 0


def _extension_check(args: argparse.Namespace) -> int:
    """Check an extension's registry document against the invariants any registry is held to.

    `draft` writes a document and this says whether it is sound, so an author learns before a
    build refuses it. Core is checked by exactly this function, which is what keeps the two from
    drifting.
    """
    if not args.document.is_file():
        print(f"error: {args.document} does not exist", file=sys.stderr)
        return 2
    if args.packet is not None:
        from escapewheel_reader import RegistryUnavailable, open_packet

        packet = open_packet(args.packet)
        core = packet.manifest.core
        if core is None:
            print(f"error: {args.packet} binds no core registry to check against", file=sys.stderr)
            return 2
        try:
            core_context = check_registry_context_bytes(packet.registry_bytes(core.registry_id))
        except RegistryUnavailable as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        if not args.registry.is_file():
            print(f"error: {args.registry} does not exist", file=sys.stderr)
            return 2
        core_context = check_registry_context_bytes(args.registry.read_bytes())

    context = check_registry_context_bytes(args.document.read_bytes(), core=core_context)
    if args.result is not None:
        args.result.write_text(json.dumps(context.result.to_dict(), indent=2) + "\n")
    for phase in context.result.phases:
        for outcome in phase.outcomes:
            print(f"{outcome.state.upper():11s} {phase.phase}: {outcome.id} at {outcome.instance or '<root>'}")
    document = context.document
    tables = (
        sum(1 for declaration in document.get("resources", {}).values() if declaration.get("kind") == "table")
        if isinstance(document, dict)
        else 0
    )
    if context.result.state != RegistryState.VALID:
        print(f"\n{args.document}: {context.result.state} over {tables} table(s)", file=sys.stderr)
        return 1
    print(f"\n{args.document}: sound — complete result over {tables} table(s)")
    return 0


def _declare(args: argparse.Namespace) -> int:
    """Write one adapter's declarations as the document Part 12 §7 publishes the shape of."""
    from .. import declaration
    from ..sources import ADAPTERS, discovered

    adapter = ADAPTERS.get(args.kind) or discovered().get(args.kind)
    if adapter is None:
        known = ", ".join(sorted({*ADAPTERS, *discovered()}))
        print(f"unknown source kind {args.kind!r}; this build ships {known}", file=sys.stderr)
        return 2
    if args.protocol and getattr(adapter, "PROTOCOLS", ()):
        print(f"{args.kind} declares its own protocols; --protocol is for an adapter that states none", file=sys.stderr)
        return 2
    document = declaration.of(adapter, args.kind, args.protocol or [declaration.STREAM])
    if problems := declaration.shape_problems(document):
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(f"{args.kind}: its declaration does not satisfy the schema (Part 12 §7)", file=sys.stderr)
        return 2
    text = json.dumps(document, indent=2) + "\n"
    if args.out is None:
        print(text, end="")
    else:
        args.out.write_text(text)
        print(f"wrote {args.out} ({len(text)} bytes)")
    return 0


def _deliver(args: argparse.Namespace) -> int:
    """Run one adapter and deliver its rows over the protocol the build reached it by."""
    from .. import delivery

    # Read to end of file before anything is written, which is what a build supplies and all it
    # supplies on this stream (Part 12 §4).
    try:
        supplied = json.loads(sys.stdin.buffer.read() or b"{}")
    except json.JSONDecodeError as exc:
        print(f"standard input must carry one JSON object of supplied terms: {exc}", file=sys.stderr)
        return 2
    protocol = args.protocol or delivery.infers(supplied)
    try:
        source = delivery.construct(args.kind, supplied)
        delivery.serve(source, supplied, protocol)
    except SourceDefect as exc:
        # Standard error is what `files-v0.1` and `stream-v0.1` carry a failure on, and rows have
        # taken standard output (Part 05 §4.4).
        print(f"{args.kind}: {exc}", file=sys.stderr)
        return 1
    return 0


def register(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``import``, ``inspect``, ``init``, ``declare`` and ``deliver`` to ``escapewheel``.

    Parameters
    ----------
    subcommands : argparse._SubParsersAction
        The subparser action to register against.
    """
    inspect = subcommands.add_parser("inspect", help="report what one source offers (Part 05 §4.1)")
    inspect.add_argument("kind", choices=KINDS)
    inspect.add_argument("root", type=Path)
    inspect.add_argument("--session-id", default="session", help="session the records are scoped to")
    inspect.set_defaults(func=_inspect)

    init = subcommands.add_parser("init", help="draft a recipe from what several sources hold")
    init.add_argument("--source", action="append", required=True, metavar="KIND=PATH")
    init.add_argument("--session-id", required=True)
    init.add_argument("--out", type=Path, help="write here rather than to stdout")
    init.set_defaults(func=_init)

    extension = subcommands.add_parser("extension", help="draft an extension registry, or check one")
    # Two verbs rather than two commands: drafting and checking are the two halves of authoring one
    # document, and a verb is where a third would go.
    authoring = extension.add_subparsers(dest="verb", required=True, metavar="{draft,check}")

    drafting = authoring.add_parser("draft", help="draft a registry document from tables that already exist")
    drafting.add_argument("extension_id", help="namespace every table is prefixed by (Part 09 §5.2)")
    drafting.add_argument(
        "--table",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="a table and the parquet file whose schema it takes; repeatable",
    )
    drafting.add_argument("--out", type=Path, default=None, help="where to write (default: <id>.json)")
    drafting.set_defaults(func=_extension)

    checking = authoring.add_parser("check", help="check a registry document against Part 02 §9.4's invariants")
    checking.add_argument("document", type=Path, help="the extension's registry document")
    source = checking.add_mutually_exclusive_group(required=True)
    source.add_argument("--registry", type=Path, help="the core registry it extends, as logical_schemas.json")
    source.add_argument("--packet", type=Path, help="a packet root, whose embedded registry is read instead")
    checking.add_argument(
        "--all", action="store_true", help="list every invariant checked, not only the ones that failed"
    )
    checking.add_argument("--result", type=Path, help="write the complete portable registry result as JSON")
    checking.set_defaults(func=_extension_check)

    verifier = subcommands.add_parser(
        "verify", help="record what is true about a committed packet's external resources"
    )
    verifier.add_argument("packet", type=Path, help="packet root holding a committed manifest")
    verifier.add_argument(
        "--level",
        choices=("size", "members", "sha256"),
        default="members",
        help="how much to establish; sha256 reads every byte, which is the cost Part 04 §5.2 puts "
        "at publication rather than in a build (default: members)",
    )
    verifier.set_defaults(func=_verify)

    pruner = subcommands.add_parser(
        "prune", help="remove what a committed packet no longer names, reporting by default"
    )
    pruner.add_argument("packet", type=Path, help="packet root holding a committed manifest")
    pruner.add_argument(
        "--keep-versions",
        type=int,
        default=None,
        metavar="N",
        help="superseded manifests to retain, overriding the packet's declared retention "
        "(default: what it declares, else 1)",
    )
    pruner.add_argument(
        "--keep-days",
        type=float,
        default=None,
        metavar="D",
        help="also retain a superseded manifest younger than this; both floors must permit an "
        "expiry (default: what the packet declares, else no age limit)",
    )
    pruner.add_argument("--apply", action="store_true", help="remove, rather than report what would be removed")
    pruner.set_defaults(func=_prune)

    importer = subcommands.add_parser("import", help="build and commit a packet from a recipe")
    importer.add_argument("recipe", type=Path)
    importer.add_argument("--out", type=Path, help="packet root, overriding [packet].out")
    importer.add_argument(
        "--compare",
        type=Path,
        default=None,
        help=(
            "a packet to compare the result against; defaults to each one [packet].replaces names, "
            "else the one at the packet root"
        ),
    )
    importer.add_argument("--registry", type=Path, help="registry, overriding [packet].registry")
    importer.add_argument("--registry-result", type=Path, help="write the complete core-registry result as JSON")
    importer.add_argument("--check", action="store_true", help="check the recipe and stop")
    importer.add_argument(
        "--strict",
        action="store_true",
        help="refuse the build on any adapter note, each of which is something worked around",
    )
    importer.add_argument(
        "--memory-budget",
        metavar="N",
        help="what the build may hold before spilling, as bytes or '20GB'; overrides "
        "[commit].memory_budget, and bounds validation too. Bucketing a spike table is a "
        "transpose, so its partition either fits in memory or goes to disk",
    )
    importer.add_argument(
        "--sample",
        type=int,
        metavar="N",
        help="keep only the first N spikes per stream, for a fast development cycle; "
        "recorded in the run's parameters so the packet says it is a sample",
    )
    kept = importer.add_mutually_exclusive_group()
    kept.add_argument(
        "--source-cache",
        type=Path,
        metavar="DIR",
        help="where adapters keep what they read from a store for later builds (default: "
        ".escapewheel-source-cache beside the packet; Part 12 §10)",
    )
    kept.add_argument("--no-source-cache", action="store_true", help="supply no source-cache location")
    importer.set_defaults(func=_import)

    cache_pruner = subcommands.add_parser(
        "prune-cache", help="remove what this writer keeps in a source-cache location, reporting by default"
    )
    cache_pruner.add_argument("location", type=Path, help="the location `import` was given as --source-cache")
    cache_pruner.add_argument(
        "--older-than",
        type=float,
        default=None,
        metavar="D",
        help="only what no build has read for D days (default: everything)",
    )
    cache_pruner.add_argument("--apply", action="store_true", help="remove, rather than report what would be removed")
    cache_pruner.set_defaults(func=_prune_cache)

    declare = subcommands.add_parser("declare", help="write an adapter's declarations as a document")
    declare.add_argument("kind", help="the source kind, as a recipe entry names it")
    declare.add_argument(
        "--protocol",
        action="append",
        choices=declaration_protocols(),
        help="a protocol to declare for an adapter stating none, repeatable (default: stream-v0.1; Part 12 §3)",
    )
    declare.add_argument("--out", type=Path, help="write here rather than to stdout")
    declare.set_defaults(func=_declare)

    deliver = subcommands.add_parser("deliver", help="run one adapter and hand over its rows")
    deliver.add_argument("kind", help="the source kind to run")
    deliver.add_argument(
        "--protocol",
        default=None,
        choices=declaration_protocols(),
        help="override the protocol, which is otherwise read from the terms supplied",
    )
    deliver.set_defaults(func=_deliver)


__all__ = ["KINDS", "register"]

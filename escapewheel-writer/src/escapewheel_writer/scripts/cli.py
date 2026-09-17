"""The ``escapewheel import``, ``inspect``, ``init``, ``declare`` and ``deliver`` subcommands.

`escapewheel_reader` owns the ``escapewheel`` entry point and discovers this through the
``escapewheel.commands`` group, so installing this package makes the subcommands appear rather
than competing for the command name.

The three follow Part 05's stages. ``inspect`` is Stage 1 -- what a source offers, before anything
is staged. ``init`` turns several inspections into a recipe draft, so the ownership decisions a
build depends on are made from what the sources actually hold rather than from memory.
``import`` is Stages 2-6.

``declare`` and ``deliver`` are the two halves of Part 03 §11's boundary. ``declare`` writes an
adapter's declarations as the document a build reads where it cannot import one, generated from the
class rather than maintained. ``deliver`` runs one adapter and hands its rows over a protocol, which
is how an adapter this package ships becomes reachable out of process without declaring anything --
and is the command a recipe names to have a source delivered rather than imported. It takes what a
build supplies on standard input and no arguments of its own beyond the kind, so running one by
hand is `escapewheel deliver nwb < supplied.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from .. import compare
from ..extensions import load as load_extension
from ..recipe import RECIPE_SUPPLIES, SHARED, Recipe, preferences
from ..session import build, materializers
from ..writer import CommitRefused


def declaration_protocols() -> tuple[str, ...]:
    """Part 03 §11.1's group, read where the CLI is built rather than imported at module load."""
    from ..declaration import PROTOCOLS

    return PROTOCOLS


#: What the recipe declares rather than reading from a source, spelled for a draft's comment.
SUPPLIES_NOTE = "the recipe supplies core.sessions, core.subjects and core.processing_runs"

#: Source kinds ``init`` can inspect, and the adapter each names.
#: Kinds `_open` can construct with nothing but a root, which is what `init` and `inspect`
#: need. Narrower than the kinds a build accepts: `video` needs a clock, `tables` a table
#: map, `session` a zone, and `waveforms` the sorting it describes, so none can be opened
#: on its own. `test_arbitration.py` refuses a kind here that `_open` would turn away, and
#: one that `session._KINDS` does not know.
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
        # rate answers that. Which clock it really is decides tick values, which Stage 1 does not
        # report.
        row = {"clock_id": "harp", "session_id": session_id, "origin": "HARP epoch", "tick_rate_num": 31250}
        return NWBSource(root, reference_clock=row, zone="UTC", session_id=session_id)
    raise SystemExit(f"error: {kind} cannot be inspected on its own; it consumes another source")


def _inspect(args: argparse.Namespace) -> int:
    """Report what one source offers (Part 05 Stage 1)."""
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

    contested = {r: sorted(k for k in offers if r in offers[k]) for r in {r for o in offers.values() for r in o}}
    lines = [
        "# Drafted by `escapewheel init` from what each source reported holding.",
        "# Review the ownership below: a contested resource is noted where it was passed over,",
        "# and every line marked GUESS is one nothing inspected could settle.",
        "",
        "[packet]",
        f'id = "{args.session_id}"',
        f'out = "{args.session_id}"{GUESSED}',
        'registry = "registry/logical_schemas.json"',
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
    for kind, root in (p.split("=", 1) for p in args.source):
        # The recipe supplies these itself, so handing one to a source is a conflict the
        # checker then reports (recipe.RECIPE_SUPPLIES).
        # SHARED wins over RECIPE_SUPPLIES: the recipe writes one core.processing_runs row for
        # its own import and the sorter writes one per sorting, so both belong and neither owns.
        supplies = frozenset(RECIPE_SUPPLIES) - SHARED
        mine = {r for r in offers[kind] if r not in supplies}
        owned = [r for r, kinds in sorted(contested.items()) if r in mine and r not in SHARED and _wins(kind, kinds)]
        shared = [r for r in sorted(mine & SHARED)]
        passed = [
            r for r, kinds in sorted(contested.items()) if r in mine and r not in SHARED and not _wins(kind, kinds)
        ]
        lines += ["[[source]]", f'kind = "{kind}"', f'root = "{root}"']
        lines += [f"contributes = [{', '.join(chr(34) + r + chr(34) for r in shared)}]"] if shared else []
        lines += ["owns = ["]
        lines += [f'  "{r}",' for r in owned]
        lines += ["]"]
        for option, value, why in REQUIRED.get(kind, ()):
            lines += [f"# {why}", f"{option} = {value}{GUESSED}"]
        lines += [f"# also offers {r}, owned here by {preferences().get(r, 'another source')}" for r in passed]
        lines += [f"# supplies {r}, which the recipe declares itself" for r in sorted(set(offers[kind]) & supplies)]
        lines += [*HINTS.get(kind, ()), ""]

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


def _wins(kind: str, offering: list[str]) -> bool:
    """Whether this kind owns a resource several sources offer.

    Uncontested resources go to their only source. A contested one goes to :data:`PREFERRED`,
    and where that says nothing, to the first kind alphabetically -- which is arbitrary, and
    meant to be: the draft notes the choice so a human overrules it rather than a default
    quietly standing in for a decision.
    """
    if len(offering) == 1:
        return True
    preferred = preferences()
    resource_owner = next((r for r, k in preferred.items() if k == kind and kind in offering), None)
    return kind == preferred.get(resource_owner or "", offering[0]) if resource_owner else kind == offering[0]


def _import(args: argparse.Namespace) -> int:
    """Build and commit a packet from a recipe (Part 05 Stages 2-6)."""
    # The override goes into the load rather than onto the result: a build derives where a
    # delivery lands and where the source cache sits from where the packet is going, and the
    # second of those is fixed when the first source root resolves.
    recipe = Recipe.load(args.recipe, out=args.out)
    registry_path = args.registry or recipe.registry
    if registry_path is None:
        print("error: no registry; declare [packet].registry or pass --registry", file=sys.stderr)
        return 2
    registry = json.loads(Path(registry_path).read_text())
    extensions = [load_extension(named, base=recipe.path.parent) for named in recipe.extensions]
    if args.sample:
        recipe = recipe.with_sample(args.sample)

    problems = recipe.check(registry, extensions)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    if any(p.level == "error" for p in problems):
        print(f"{recipe.path}: refused, {sum(p.level == 'error' for p in problems)} error(s)", file=sys.stderr)
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
    writer = build(recipe, registry, say=say, strict=args.strict)
    derive = materializers(recipe, memory_budget=budget)
    limits = {k: v for k, v in recipe.limits.items() if k != "memory_budget"}
    if budget and "memory_limit" not in limits:
        limits["memory_limit"] = budget
    out = recipe.out
    # Read before the commit writes over it: a rebuild's reference is the packet it replaces,
    # and after `commit` there is nothing left to compare against.
    reference = compare.resources(args.compare or out)
    try:
        report = writer.commit(out, limits=limits or None, say=say, materialize=derive)
    except CommitRefused as exc:
        for finding in exc.report.findings[:20]:
            print(f"  {finding.level:8s} {finding.check}: {finding.message}", file=sys.stderr)
        print(f"refused: {exc.report.errors} error(s); staging left at {exc.staging}", file=sys.stderr)
        return 1
    if dropped := compare.lost(reference, compare.resources(out)):
        where = "the packet it replaces" if not args.compare else str(args.compare)
        print(f"warning: {len(dropped)} resource(s) in {where} are not in this build:", file=sys.stderr)
        for resource_id in dropped:
            print(f"  lost  {resource_id}", file=sys.stderr)
    _say_verdict(out, report)
    return 0


def _say_verdict(out: Path, report: Any) -> None:
    """Report core's verdict and the extensions' apart, as Part 05 §5.4 keeps them.

    A packet stays core-conformant carrying an extension whose rules a validator cannot run, so
    one total conflates two verdicts and reads as a packet that committed despite an error.
    """
    failed = [f for f in report.findings if f.level == "error" and f.extension is not None]
    line = f"committed {out} — {report.errors - len(failed)} core error(s), {report.warnings} warning(s)"
    if failed:
        line += f"; {len(failed)} extension error(s), which do not change the core verdict"
    print(line)
    for finding in failed:
        print(f"  {finding.extension}: {finding.check}: {finding.message}", file=sys.stderr)


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
    """Remove what a committed packet no longer names (Part 03 §9.5)."""
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
    for note in plan.notes:
        print(f"  note      {note}")
    verb = "removed" if plan.applied else "would remove"
    kept = f", {len(plan.retained)} superseded manifest(s) retained" if plan.retained else ""
    print(f"\n{verb} {len(plan)} file(s); {len(plan.strays)} stray kept{kept}")
    if not plan.applied and len(plan):
        print("nothing was removed; pass --apply")
    return 0


def _extension(args: argparse.Namespace) -> int:
    """Draft an extension registry from tables that already exist (Part 09 §2)."""
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
    print(f"drafted {written} — {len(drafted.document['tables'])} table(s)")
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

    The half of extension authoring that never shipped: `draft` writes a document and nothing told
    an author whether it was sound, so the answer arrived when a build refused it, or did not
    arrive. Core is checked by exactly this function, which is what keeps the two from drifting.
    """
    from escapewheel_validator.registry_document import check_extension

    if not args.document.is_file():
        print(f"error: {args.document} does not exist", file=sys.stderr)
        return 2
    if args.packet is not None:
        from escapewheel_reader import open_packet

        core = open_packet(args.packet).registry
        if core is None:
            print(f"error: {args.packet} embeds no registry to check against", file=sys.stderr)
            return 2
    else:
        if not args.registry.is_file():
            print(f"error: {args.registry} does not exist", file=sys.stderr)
            return 2
        core = json.loads(args.registry.read_text())

    try:
        document = json.loads(args.document.read_text())
    except json.JSONDecodeError as exc:
        print(f"error: {args.document} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    # The stem is what the document is filed as, which its `extension_id` must match.
    findings = check_extension(document, core, name=args.document.stem)
    broken = [f for f in findings if not f.passed]
    for finding in findings if args.all else broken:
        print(f"{'FAIL' if not finding.passed else 'ok  '}  {finding}")
    tables = len(document.get("tables", {}))
    if broken:
        print(
            f"\n{args.document}: {len(broken)} of {len(findings)} invariant(s) broken over {tables} table(s)",
            file=sys.stderr,
        )
        return 1
    print(f"\n{args.document}: sound — {len(findings)} invariant(s) over {tables} table(s)")
    return 0


def _declare(args: argparse.Namespace) -> int:
    """Write one adapter's declarations as the document Part 03 §11.5 publishes the shape of."""
    from .. import declaration
    from ..sources import ADAPTERS, discovered

    adapter = ADAPTERS.get(args.kind) or discovered().get(args.kind)
    if adapter is None:
        known = ", ".join(sorted({*ADAPTERS, *discovered()}))
        print(f"unknown source kind {args.kind!r}; this build ships {known}", file=sys.stderr)
        return 2
    document = declaration.of(adapter, args.kind, args.protocol)
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
    from ..sources import SourceDefect

    # Read to end of file before anything is written, which is what a build supplies and all it
    # supplies on this stream (Part 03 §11.2).
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
    inspect = subcommands.add_parser("inspect", help="report what one source offers (05 Stage 1)")
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
    drafting.add_argument("extension_id", help="namespace every table is prefixed by (Part 09 §2)")
    drafting.add_argument(
        "--table",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="a table and the parquet file whose schema it takes; repeatable",
    )
    drafting.add_argument("--out", type=Path, default=None, help="where to write (default: <id>.json)")
    drafting.set_defaults(func=_extension)

    checking = authoring.add_parser("check", help="check a registry document against Part 09 §2's invariants")
    checking.add_argument("document", type=Path, help="the extension's registry document")
    source = checking.add_mutually_exclusive_group(required=True)
    source.add_argument("--registry", type=Path, help="the core registry it extends, as logical_schemas.json")
    source.add_argument("--packet", type=Path, help="a packet root, whose embedded registry is read instead")
    checking.add_argument(
        "--all", action="store_true", help="list every invariant checked, not only the ones that failed"
    )
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
        help="a packet to compare the result against; defaults to the one being replaced",
    )
    importer.add_argument("--registry", type=Path, help="registry, overriding [packet].registry")
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
    importer.set_defaults(func=_import)

    declare = subcommands.add_parser("declare", help="write an adapter's declarations as a document")
    declare.add_argument("kind", help="the source kind, as a recipe entry names it")
    declare.add_argument(
        "--protocol",
        default="stream-v0.1",
        choices=declaration_protocols(),
        help="the protocol this adapter's rows cross by (Part 03 §11.1)",
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

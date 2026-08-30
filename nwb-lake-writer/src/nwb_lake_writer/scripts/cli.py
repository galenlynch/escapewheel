"""The ``nwb-lake import``, ``inspect`` and ``init`` subcommands.

`nwb_lake_reader` owns the ``nwb-lake`` entry point and discovers this through the
``nwb_lake.commands`` group, so installing this package makes the subcommands appear rather
than competing for the command name.

The three follow `05`'s stages. ``inspect`` is Stage 1 -- what a source offers, before anything
is staged. ``init`` turns several inspections into a recipe draft, so the ownership decisions a
build depends on are made from what the sources actually hold rather than from memory.
``import`` is Stages 2-6.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from ..recipe import Recipe
from ..session import build, materializers
from ..writer import CommitRefused

#: Source kinds ``init`` can inspect, and the adapter each names.
KINDS = ("sorter", "sync", "nwb", "waveforms")

#: Where a resource goes when more than one source offers it. The winner is the source that
#: knows most about it: the NWB knows a probe's type and manufacturer where the sorter knows
#: only the stream, and the waveform source is the only one that can see a unit's channel
#: support. A draft says what it chose and what it passed over, rather than choosing silently.
PREFERRED = {
    "core.probes": "nwb",
    "core.clocks": "sync",
    "core.unit_electrodes": "waveforms",
}


def _open(kind: str, root: Path, session_id: str) -> Any:
    """Construct a source for inspection, with the least configuration that will open it."""
    from ..sources import NWBSource, SorterSource, SyncSource

    if kind == "sorter":
        return SorterSource(root, session_id=session_id)
    if kind == "sync":
        return SyncSource(root, session_id=session_id)
    if kind == "nwb":
        from zoneinfo import ZoneInfo

        from ..clock import Clock

        clock = Clock("harp", session_id=session_id, name="HARP", tick_rate_num=31250, origin="HARP epoch")
        return NWBSource(root, clock=clock, zone=ZoneInfo("UTC"), session_id=session_id)
    raise SystemExit(f"error: {kind} cannot be inspected on its own; it consumes another source")


def _inspect(args: argparse.Namespace) -> int:
    """Report what one source offers (`05` Stage 1)."""
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
        "# Drafted by `nwb-lake init` from what each source reported holding.",
        "# Review the ownership below: a contested resource is noted where it was passed over.",
        "",
        "[packet]",
        f'id = "{args.session_id}"',
        f'out = "{args.session_id}"',
        'registry = "registry/logical_schemas.json"',
        "",
        "[session]",
        f'session_id = "{args.session_id}"',
        'reference_clock_id = "harp"',
        "",
    ]
    for kind, root in (p.split("=", 1) for p in args.source):
        owned = [r for r, kinds in sorted(contested.items()) if r in offers[kind] and _wins(kind, kinds)]
        passed = [r for r, kinds in sorted(contested.items()) if r in offers[kind] and not _wins(kind, kinds)]
        lines += ["[[source]]", f'kind = "{kind}"', f'root = "{root}"', "owns = ["]
        lines += [f'  "{r}",' for r in owned]
        lines += ["]"]
        lines += [f"# also offers {r}, owned here by {PREFERRED.get(r, 'another source')}" for r in passed]
        lines += [""]

    text = "\n".join(lines)
    if args.out is None:
        print(text)
    else:
        args.out.write_text(text)
        print(f"drafted {args.out}")
    return 0


def _wins(kind: str, offering: list[str]) -> bool:
    """Whether this kind owns a resource several sources offer.

    Uncontested resources go to their only source. A contested one goes to :data:`PREFERRED`,
    and where that says nothing, to the first kind alphabetically -- which is arbitrary, and
    meant to be: the draft notes the choice so a human overrules it rather than a default
    quietly standing in for a decision.
    """
    if len(offering) == 1:
        return True
    resource_owner = next((r for r, k in PREFERRED.items() if k == kind and kind in offering), None)
    return kind == PREFERRED.get(resource_owner or "", offering[0]) if resource_owner else kind == offering[0]


def _import(args: argparse.Namespace) -> int:
    """Build and commit a packet from a recipe (`05` Stages 2-6)."""
    recipe = Recipe.load(args.recipe)
    registry_path = args.registry or recipe.registry
    if registry_path is None:
        print("error: no registry; declare [packet].registry or pass --registry", file=sys.stderr)
        return 2
    registry = json.loads(Path(registry_path).read_text())
    if args.sample:
        recipe = recipe.with_sample(args.sample)

    problems = recipe.check(registry)
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

    writer = build(recipe, registry, say=say)
    derive = materializers(recipe)
    out = args.out or recipe.out
    try:
        report = writer.commit(out, limits=recipe.limits or None, say=say, materialize=derive)
    except CommitRefused as exc:
        for finding in exc.report.findings[:20]:
            print(f"  {finding.level:8s} {finding.check}: {finding.message}", file=sys.stderr)
        print(f"refused: {exc.report.errors} error(s); staging left at {exc.staging}", file=sys.stderr)
        return 1
    print(f"committed {out} — {report.errors} error(s), {report.warnings} warning(s)")
    return 0


def register(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``import``, ``inspect`` and ``init`` to the ``nwb-lake`` command.

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

    importer = subcommands.add_parser("import", help="build and commit a packet from a recipe")
    importer.add_argument("recipe", type=Path)
    importer.add_argument("--out", type=Path, help="packet root, overriding [packet].out")
    importer.add_argument("--registry", type=Path, help="registry, overriding [packet].registry")
    importer.add_argument("--check", action="store_true", help="check the recipe and stop")
    importer.add_argument(
        "--sample",
        type=int,
        metavar="N",
        help="keep only the first N spikes per stream, for a fast development cycle; "
        "recorded in the run's parameters so the packet says it is a sample",
    )
    importer.set_defaults(func=_import)


__all__ = ["KINDS", "PREFERRED", "register"]

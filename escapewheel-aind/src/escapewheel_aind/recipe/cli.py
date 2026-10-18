"""`escapewheel-aind-recipe`: draft one session's recipe from DocDB, Code Ocean and S3."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from zoneinfo import ZoneInfo

from ..errors import DraftRefused
from . import assets, catalog, draft, facts


def _extensions(paths: Sequence[Path]) -> dict[str, str]:
    """Each extension registry given, by the ID its document declares."""
    return {str(json.loads(path.read_text())["registry_id"]): str(path.resolve()) for path in paths}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="escapewheel-aind-recipe",
        description="Draft a recipe for one AIND ecephys session from its public assets.",
    )
    parser.add_argument("raw", help="the raw asset's name, as ecephys_786867_2025-09-25_12-43-56")
    parser.add_argument("--sorted", dest="sorted_name", help="read this sorted asset rather than the newest")
    parser.add_argument("--nwb", dest="nwb_name", help="read this NWB asset rather than the newest of the sorting")
    parser.add_argument("--registry", type=Path, required=True, help="the core registry to write against")
    parser.add_argument(
        "--extension", type=Path, action="append", default=[], help="an extension registry a source may fill"
    )
    parser.add_argument("--packet-out", default=None, help="where the build writes the packet (default: the raw name)")
    parser.add_argument("--videos", type=Path, help="a local copy of behavior-videos, read instead of S3")
    parser.add_argument(
        "--mirror", type=Path, help="a CSV of asset_name and destination: a readable copy of each private asset"
    )
    parser.add_argument("--no-codeocean", action="store_true", help="find assets in DocDB alone")
    parser.add_argument("--out", type=Path, help="write the recipe here rather than to standard output")
    return parser


def _choose(args: argparse.Namespace) -> tuple[dict[str, object], assets.Choice]:
    """Find the session's assets in both catalogues, and choose the ones the recipe reads."""
    record, derived = catalog.docdb_records(args.raw)
    found = [a for r in [record, *derived] if (a := assets.from_docdb(r, args.raw)) is not None]
    subject_id = str((record.get("subject") or {}).get("subject_id") or args.raw.split("_")[1])
    if not args.no_codeocean:
        found += [a for co in catalog.codeocean_assets(subject_id) if (a := assets.from_codeocean(co, args.raw))]
    mirrors = {}
    if args.mirror:
        with args.mirror.open(newline="") as rows:
            mirrors = {row["asset_name"]: row["destination"] for row in csv.DictReader(rows)}
    held, copies = assets.mirrored(assets.merged(found), mirrors)
    choice = assets.choose(held, args.raw, sorted_name=args.sorted_name, nwb_name=args.nwb_name)
    return record, replace(choice, notes=(*copies, *choice.notes))


def main(argv: Sequence[str] | None = None) -> int:
    """Draft the recipe and report the assets it passed over."""
    args = _parser().parse_args(argv)
    try:
        record, choice = _choose(args)
    except DraftRefused as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    zone = ZoneInfo(draft.ZONE)
    session, session_notes = facts.session_facts(record, args.raw, zone)
    subject, subject_notes = facts.subject_facts(record)
    extensions = _extensions(args.extension)
    text, missing = draft.render(
        choice,
        catalog.layout(choice, catalog.s3_lister()),
        session=session,
        subject=subject,
        notes=[*session_notes, *subject_notes],
        packet_id=args.raw,
        out=args.packet_out or args.raw,
        registry=str(args.registry.resolve()),
        extensions=extensions,
        local_videos=args.videos.resolve() if args.videos else None,
    )
    if missing:
        print(f"error: the sources fill {', '.join(missing)}; pass each registry with --extension", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(text)
    else:
        sys.stdout.write(text)
    for note in choice.notes:
        print(f"note: {note}", file=sys.stderr)
    return 0


__all__ = ["main"]

"""The ``escapewheel validate`` subcommand.

- :func:`register` -- add ``validate`` to the ``escapewheel`` command's subcommands.

`escapewheel_reader` owns the ``escapewheel`` entry point and discovers this through the
``escapewheel.commands`` group, so installing this package makes the subcommand appear rather
than competing for the command name.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from escapewheel_reader import ManifestError, open_packet

from ..validator import check_packet_manifest, validate


def _validate(args: argparse.Namespace) -> int:
    """Validate a packet against the registries it binds."""
    try:
        packet = open_packet(args.packet)
    except ManifestError:
        # A manifest the reader refuses still gets Part 04 §10's findings, from its bytes alone.
        report, _ = check_packet_manifest(args.packet, advisory=args.advisory)
        packet_id = str(args.packet)
    else:
        packet_id = packet.manifest.packet_id
        # A digest is pointless without resolving, so asking for one asks for the level under it.
        replaced = [path for path in args.replaced if not (path.is_file() or (path / "packet.json").is_file())]
        if replaced:
            print(f"error: no published manifest at {replaced[0]}")
            return 2
        report = validate(
            packet,
            advisory=args.advisory,
            external=args.external or args.checksums or args.store_digests,
            checksums=args.checksums,
            store_digests=args.store_digests,
            store_checksums=args.store_checksums,
            replaced=args.replaced,
        )
    for finding in report.findings:
        where = f"[{finding.registry}] " if finding.registry else ""
        print(f"  {finding.level:8s} {where}{finding.check}: {finding.message}")
        for row in finding.rows:
            print(f"           {tuple(row)}")
    for evaluation in report.evaluations:
        if evaluation.status == "complete":
            continue
        rule = f" {evaluation.rule}" if evaluation.rule else ""
        detail = f": {evaluation.detail}" if evaluation.detail else ""
        print(f"  {evaluation.status:11s} [{evaluation.registry}]{rule}{detail}")
    # Part 05 §9.5: the packet's verdict first, then each bound registry's, so a failing extension is
    # visible as the reason a packet whose core passed did not.
    print(f"\n{packet_id}: {report.verdict()} — {report.errors} error(s), {report.warnings} warning(s)")
    for registry in report.bound:
        errors = sum(f.level == "error" and f.registry == registry for f in report.findings)
        print(f"{' ' * len(packet_id)}  {registry}: {report.verdict(registry)} — {errors} error(s)")

    if args.report is not None:
        args.report.write_text(json.dumps(report.to_dict(packet_id), indent=2) + "\n")
        print(f"report written to {args.report}")
    return 0 if report.passed else 1


def register(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``validate`` to the ``escapewheel`` command.

    Parameters
    ----------
    subcommands : argparse._SubParsersAction
        The subparser action `escapewheel_reader` passes to every registered extension.
    """
    parser = subcommands.add_parser("validate", help="validate a packet against the registries it binds")
    parser.add_argument("packet", type=Path, help="packet root directory")
    parser.add_argument("--report", type=Path, default=None, help="write a JSON report here")
    parser.add_argument(
        "--advisory",
        action="store_true",
        help="also run advisory rules; they are never errors, so the verdict cannot change",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        help="reach external resources and check their size and codecs (Part 04 §5.3 level 3a); "
        "off by default because reachability is your situation, not the packet's",
    )
    parser.add_argument(
        "--store-digests",
        action="store_true",
        help="also compare each declared member's store digest with what the store reports now "
        "(Part 04 §5.4); implies --external and costs only the listing it already does",
    )
    parser.add_argument(
        "--checksums",
        action="store_true",
        help="also establish every recorded digest: external resources at Part 04 §5.3 level 3c "
        "and packet-owned ones at level 2, from a store's full-object checksums where it reports "
        "them and otherwise by reading every byte; implies --external, and the report names each "
        "digest's route",
    )
    parser.add_argument(
        "--no-store-checksums",
        dest="store_checksums",
        action="store_false",
        help="with --checksums, read every byte rather than take a store's full-object checksums",
    )
    parser.add_argument(
        "--replaced",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help="a packet root or manifest to read as a packet this one's replaces names, reporting each "
        "difference from its item (Part 04 §3); repeatable",
    )
    parser.set_defaults(func=_validate)

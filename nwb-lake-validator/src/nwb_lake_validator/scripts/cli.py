"""The ``nwb-lake validate`` subcommand.

`nwb_lake_reader` owns the ``nwb-lake`` entry point and discovers this through the
``nwb_lake.commands`` group, so installing this package makes the subcommand appear rather
than competing for the command name.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nwb_lake_reader import open_packet

from ..validator import validate


def _validate(args: argparse.Namespace) -> int:
    """Validate a packet against the registry it embeds."""
    packet = open_packet(args.packet)
    # A digest is pointless without resolving, so asking for one asks for the level under it.
    report = validate(
        packet,
        advisory=args.advisory,
        external=args.external or args.checksums,
        checksums=args.checksums,
    )
    for finding in report.findings:
        print(f"  {finding.level:8s} {finding.check}: {finding.message}")
        for row in finding.rows:
            print(f"           {tuple(row)}")
    status = "passed" if report.passed else "failed"
    print(f"\n{packet.manifest.packet_id}: {status} — {report.errors} error(s), {report.warnings} warning(s)")

    if args.report is not None:
        args.report.write_text(json.dumps(report.to_dict(packet.manifest.packet_id), indent=2) + "\n")
        print(f"report written to {args.report}")
    return 0 if report.passed else 1


def register(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``validate`` to the ``nwb-lake`` command.

    Parameters
    ----------
    subcommands : argparse._SubParsersAction
        The subparser action `nwb_lake_reader` passes to every registered extension.
    """
    parser = subcommands.add_parser("validate", help="validate a packet against its registry")
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
        help="reach external resources and check their size and codecs (R15 §4 level 3a); "
        "off by default because reachability is your situation, not the packet's",
    )
    parser.add_argument(
        "--checksums",
        action="store_true",
        help="also recompute each external sha256, reading every byte (level 3b); implies "
        "--external, and reports the resources that recorded no digest to compare",
    )
    parser.set_defaults(func=_validate)

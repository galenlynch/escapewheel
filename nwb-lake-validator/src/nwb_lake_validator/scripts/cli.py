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
    report = validate(packet)
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
    parser.set_defaults(func=_validate)

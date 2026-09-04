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
        external=args.external or args.checksums or args.store_digests,
        checksums=args.checksums,
        store_digests=args.store_digests,
    )
    for finding in report.findings:
        where = f"[{finding.extension}] " if finding.extension else ""
        print(f"  {finding.level:8s} {where}{finding.check}: {finding.message}")
        for row in finding.rows:
            print(f"           {tuple(row)}")
    # R17 §4: the two verdicts are separate, so printing one total would say a packet failed when
    # its core is conformant and an extension nobody is required to hold is not.
    core_errors = sum(f.level == "error" and f.extension is None for f in report.findings)
    status = "passed" if report.passed else "failed"
    print(f"\n{packet.manifest.packet_id}: core {status} — {core_errors} error(s), {report.warnings} warning(s)")
    for extension in report.extensions:
        errors = sum(f.level == "error" and f.extension == extension for f in report.findings)
        verdict = "passed" if report.extension_passed(extension) else "failed"
        print(f"{' ' * len(packet.manifest.packet_id)}  {extension}: {verdict} — {errors} error(s)")

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
        "--store-digests",
        action="store_true",
        help="also compare each declared member's store digest with what the store reports now "
        "(R51 §2.3); implies --external and costs only the listing it already does",
    )
    parser.add_argument(
        "--checksums",
        action="store_true",
        help="also recompute each external sha256, reading every byte (level 3b); implies "
        "--external, and reports the resources that recorded no digest to compare",
    )
    parser.set_defaults(func=_validate)

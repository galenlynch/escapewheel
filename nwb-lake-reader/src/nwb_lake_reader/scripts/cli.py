"""Command-line access to a packet.

``07`` names the CLI ``nwb-lake`` with subcommands spanning several phases. This package
provides the reader's share of them; importing, validating, and materializing belong to
later phases and to their own packages, which extend this command rather than replacing it.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from ..errors import PacketError
from ..packet import open_packet


def _ls(args: argparse.Namespace) -> int:
    """List the resources a packet declares."""
    packet = open_packet(args.packet)
    manifest = packet.manifest
    print(f"{manifest.packet_id}  profile={manifest.profile_id}  registry={manifest.registry_version}")
    print(f"sessions: {', '.join(packet.sessions) or 'none'}")
    if packet.manifest.required_codecs:
        print(f"required codecs: {', '.join(packet.manifest.required_codecs)}")
    print()
    width = max((len(r.resource_id) for r in packet.resources()), default=0)
    for resource in packet.resources():
        handle = packet.table_resource(resource.resource_id)
        try:
            rows: str = f"{handle.to_arrow().num_rows:>9,}" if resource.is_table else "        -"
        except PacketError:
            rows = "  missing"
        print(f"  {resource.resource_id:<{width}}  {resource.kind:<18} {rows}  {resource.uri}")
    return 0


def _sql(args: argparse.Namespace) -> int:
    """Run a query against a packet's tables."""
    packet = open_packet(args.packet)
    result = packet.duckdb().sql(args.query)
    if result is not None:
        result.show()
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns
    -------
    argparse.ArgumentParser
        The parser, with one subcommand per reader operation.
    """
    parser = argparse.ArgumentParser(prog="nwb-lake", description="Read NWB-Lake packets.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ls = subcommands.add_parser("ls", help="list the resources a packet declares")
    ls.add_argument("packet", type=Path, help="packet root directory")
    ls.set_defaults(func=_ls)

    sql = subcommands.add_parser("sql", help="run a query against a packet's tables")
    sql.add_argument("packet", type=Path, help="packet root directory")
    sql.add_argument("query", help="SQL, referring to resources by their flattened names")
    sql.set_defaults(func=_sql)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Parameters
    ----------
    argv : sequence of str, optional
        Arguments to parse. Defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        Process exit status.
    """
    args = build_parser().parse_args(argv)
    try:
        status: int = args.func(args)
    except PacketError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return status


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

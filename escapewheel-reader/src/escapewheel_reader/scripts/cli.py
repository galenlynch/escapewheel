"""Command-line access to a packet.

Part 07 names the CLI ``escapewheel`` with subcommands spanning several phases. This package
provides the reader's share -- ``ls`` and ``sql`` -- and discovers the rest through the
``escapewheel.commands`` entry-point group, so validating and importing arrive with their own
packages rather than being vendored here.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from importlib.metadata import entry_points
from pathlib import Path

from ..errors import PacketError
from ..packet import open_packet

#: Entry-point group later packages register their subcommands under.
COMMAND_GROUP = "escapewheel.commands"

#: Subcommands provided by packages that may not be installed, so an absent one can say so.
EXTENSIONS = {
    "validate": "escapewheel-validator",
    "import": "escapewheel-writer",
}


def _ls(args: argparse.Namespace) -> int:
    """List the resources a packet declares."""
    packet = open_packet(args.packet)
    manifest = packet.manifest
    core = manifest.core
    print(f"{manifest.packet_id}  profile={manifest.profile_id}  registry={core.version if core else 'unbound'}")
    print(f"sessions: {', '.join(packet.sessions) or 'none'}")
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
    # `for_query` so only the tables the query names are registered -- over an object store
    # the others would each cost a round trip to bind a view nothing reads.
    result = packet.duckdb(for_query=args.query).sql(args.query)
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
    parser = argparse.ArgumentParser(prog="escapewheel", description="Read Escapewheel packets.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ls = subcommands.add_parser("ls", help="list the resources a packet declares")
    ls.add_argument("packet", type=Path, help="packet root directory")
    ls.set_defaults(func=_ls)

    sql = subcommands.add_parser("sql", help="run a query against a packet's tables")
    sql.add_argument("packet", type=Path, help="packet root directory")
    sql.add_argument("query", help="SQL, referring to resources by their flattened names")
    sql.set_defaults(func=_sql)

    _extend(subcommands)
    return parser


def _extend(subcommands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Let installed packages contribute their own subcommands.

    Part 07 names a single CLI, ``escapewheel``. Two distributions cannot both claim it under
    ``[project.scripts]`` -- the last one installed wins silently, and the other's
    subcommands vanish -- so later packages register a callable here instead, and this
    command grows as they are installed.

    Parameters
    ----------
    subcommands : argparse._SubParsersAction
        The subparser action to register against.
    """
    provided = set()
    for entry in entry_points(group=COMMAND_GROUP):
        try:
            entry.load()(subcommands)
        except Exception as exc:  # noqa: BLE001 - see _broken
            _broken(subcommands, entry.name, exc)
        provided.add(entry.name)

    for name, distribution in EXTENSIONS.items():
        if name not in provided:
            absent = subcommands.add_parser(name, help=f"requires {distribution}")
            # Swallow whatever would have followed, so the message is about the missing
            # package rather than an argument the real subcommand would have accepted.
            absent.add_argument("args", nargs=argparse.REMAINDER)
            absent.set_defaults(func=_absent(name, distribution))


def _broken(subcommands: argparse._SubParsersAction[argparse.ArgumentParser], name: str, exc: Exception) -> None:
    """Register a subcommand that reports why it could not load.

    A package registering a callable that raises would otherwise take down the whole command:
    the exception propagates out of `build_parser`, so `escapewheel validate` stops working
    because something unrelated is broken. Discovery is open by design, so one bad entry point
    is a thing that will happen, and the failure belongs to the subcommand that caused it.

    Parameters
    ----------
    subcommands : argparse._SubParsersAction
        The subparser action to register against.
    name : str
        Subcommand name.
    exc : Exception
        What loading raised.
    """
    parser = subcommands.add_parser(name, help="failed to load")
    parser.add_argument("args", nargs=argparse.REMAINDER)

    def run(args: argparse.Namespace) -> int:
        print(f"error: `escapewheel {name}` failed to load: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    parser.set_defaults(func=run)


def _absent(name: str, distribution: str) -> Callable[[argparse.Namespace], int]:
    """Build a handler explaining which package provides a subcommand.

    Without this, an uninstalled subcommand fails as an argparse "invalid choice", which
    says nothing about what to install.

    Parameters
    ----------
    name : str
        Subcommand name.
    distribution : str
        Distribution that provides it.

    Returns
    -------
    callable
        Handler printing the hint and returning exit status 2.
    """

    def run(args: argparse.Namespace) -> int:
        print(f"error: `escapewheel {name}` is provided by {distribution} (uv add {distribution})", file=sys.stderr)
        return 2

    return run


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

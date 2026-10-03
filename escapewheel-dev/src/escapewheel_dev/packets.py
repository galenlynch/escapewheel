"""Packets through the reader, and what their stored tables hold beyond their declarations."""

from collections.abc import Mapping
from pathlib import Path

from escapewheel_reader import Packet

from ._root import ROOT

#: Where `fixtures/build.py` writes the conformance corpus; gitignored, so empty until it runs.
CORPUS = ROOT / "fixtures" / "packets"


def corpus_packets() -> Mapping[str, Path]:
    """Return each built corpus packet's directory by name, or nothing where none is built."""
    if not CORPUS.is_dir():
        return {}
    return {path.name: path for path in sorted(CORPUS.iterdir()) if (path / "packet.json").is_file()}


def stored_columns(packet: Packet, resource_id: str) -> tuple[str, ...]:
    """Return the column names a table resource stores, read from its schema without reading rows.

    Parameters
    ----------
    packet : Packet
        An open packet.
    resource_id : str
        A table resource the packet holds, such as ``core.units``.
    """
    return tuple(packet.scan(resource_id).schema.names)


def undeclared_columns(packet: Packet) -> Mapping[str, tuple[str, ...]]:
    """Return, per table resource, the stored columns its bound declaration does not name.

    A resource whose declaration the packet's registries lack is left out; the validator reports it.
    """
    found = {}
    for resource in packet.resources(kind="table"):
        declaration = resource.declaration
        if declaration is None:
            continue
        declared = {column["name"] for column in declaration["table"]["columns"]}
        extra = tuple(name for name in stored_columns(packet, resource.resource_id) if name not in declared)
        if extra:
            found[resource.resource_id] = extra
    return found


__all__ = ["CORPUS", "corpus_packets", "stored_columns", "undeclared_columns"]

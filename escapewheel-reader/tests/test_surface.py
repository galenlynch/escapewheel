"""The package's surface: what is exported, and what `Packet` does not repeat."""

import inspect

import escapewheel_reader
from escapewheel_reader import Packet


def test_no_packet_method_mirrors_an_exported_function():
    """A read has one spelling: the free function taking the packet."""
    functions = {name for name in escapewheel_reader.__all__ if inspect.isfunction(getattr(escapewheel_reader, name))}
    members = {name for name in vars(Packet) if not name.startswith("_")}
    assert not functions & members

"""An exception these adapters define is one a build already catches."""

import importlib
import inspect
import pkgutil

from escapewheel_writer.errors import WriterError

import escapewheel_aind


def _defined():
    """Every exception class a module of the package defines."""
    for info in pkgutil.walk_packages(escapewheel_aind.__path__, "escapewheel_aind."):
        module = importlib.import_module(info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseException) and cls.__module__ == module.__name__:
                yield cls


def test_every_exception_derives_from_the_writer_base():
    """The build and the command line catch `WriterError`, so nothing an adapter raises on purpose escapes them."""
    for cls in _defined():
        assert issubclass(cls, WriterError), cls

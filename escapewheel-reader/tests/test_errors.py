"""The package's exceptions are one taxonomy, defined in one module."""

import importlib
import inspect
import pkgutil

import escapewheel_reader
from escapewheel_reader import errors


def _defined():
    """Every exception class a module of the package defines."""
    for info in pkgutil.walk_packages(escapewheel_reader.__path__, "escapewheel_reader."):
        module = importlib.import_module(info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseException) and cls.__module__ == module.__name__:
                yield cls


def test_every_exception_is_defined_in_the_error_module_under_the_package_base():
    """A caller catching `PacketError` catches every deliberate refusal, wherever it is raised."""
    classes = list(_defined())
    assert errors.PacketError in classes
    for cls in classes:
        assert cls.__module__ == errors.__name__, cls
        assert issubclass(cls, errors.EscapewheelError), cls
        assert cls is errors.EscapewheelError or issubclass(cls, errors.PacketError), cls


def test_an_error_a_caller_catches_as_a_value_error_stays_one():
    """Downstream code catches these four as `ValueError`."""
    for cls in (errors.NotAligned, errors.Unanchored, errors.ClockMismatch, errors.StaleSupport):
        assert issubclass(cls, ValueError)
        assert issubclass(cls, errors.Refused)
    assert issubclass(errors.PhysicalProfileError, ValueError)


def test_every_exported_exception_is_documented_in_the_module_docstring():
    """The module docstring is the taxonomy a reader of the page sees."""
    for name, cls in inspect.getmembers(errors, inspect.isclass):
        if issubclass(cls, BaseException) and cls.__module__ == errors.__name__:
            assert f":class:`{name}`" in errors.__doc__, name

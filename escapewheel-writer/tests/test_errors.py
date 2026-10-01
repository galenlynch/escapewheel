"""The package's exceptions are one taxonomy, defined in one module."""

import importlib
import inspect
import pkgutil

from escapewheel_reader.errors import EscapewheelError

import escapewheel_writer
from escapewheel_writer import errors


def _defined():
    """Every exception class a module of the package defines."""
    for info in pkgutil.walk_packages(escapewheel_writer.__path__, "escapewheel_writer."):
        module = importlib.import_module(info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, BaseException) and cls.__module__ == module.__name__:
                yield cls


def test_every_exception_is_defined_in_the_error_module_under_the_package_base():
    """A caller catching `WriterError` catches every deliberate refusal, wherever it is raised."""
    classes = list(_defined())
    assert errors.WriterError in classes
    assert issubclass(errors.WriterError, EscapewheelError)
    for cls in classes:
        assert cls.__module__ == errors.__name__, cls
        assert issubclass(cls, errors.WriterError), cls


def test_an_error_a_caller_catches_as_a_built_in_stays_one():
    """Each of these was a `ValueError` before the package had a base class."""
    for cls in (
        errors.RecipeUnreadable,
        errors.AmendmentRefused,
        errors.SourceDefect,
        errors.UnsupportedEncoding,
        errors.PayloadRefused,
        errors.OffGrid,
        errors.NonFinite,
        errors.NaiveTimestamp,
        errors.CarriedNotAnInteger,
        errors.Collided,
    ):
        assert issubclass(cls, ValueError), cls


def test_every_exception_is_documented_in_the_module_docstring():
    """The module docstring is the taxonomy a reader of the page sees."""
    for name, cls in inspect.getmembers(errors, inspect.isclass):
        if issubclass(cls, BaseException) and cls.__module__ == errors.__name__:
            assert f":exc:`{name}`" in errors.__doc__, name

"""The package's exceptions are one taxonomy, defined in one module."""

import ast
import importlib
import inspect
import pkgutil
from enum import StrEnum
from pathlib import Path

from escapewheel_reader.errors import EscapewheelError

import escapewheel_writer
from escapewheel_writer import errors

#: The classes an adapter raises with a code.
DEFECTS = {"SourceDefect", "UnsupportedEncoding"}


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


def test_a_code_is_its_name_in_lower_case():
    """A code is compared and logged, so its two spellings differ in case alone."""
    for _, codes in inspect.getmembers(errors, inspect.isclass):
        if issubclass(codes, StrEnum) and codes.__module__ == errors.__name__:
            for member in codes:
                assert member.value == member.name.lower(), member


def test_every_defect_this_package_raises_carries_a_code():
    """A caller tells defects apart by code, so one raised without a code is one it cannot tell."""
    for path in sorted(Path(escapewheel_writer.__file__).parent.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) in DEFECTS:
                assert any(keyword.arg == "code" for keyword in node.keywords), f"{path.name}:{node.lineno}"

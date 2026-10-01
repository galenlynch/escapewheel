"""The package's exceptions are one taxonomy, defined in one module."""

import ast
import builtins
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


#: The built-in a caller may catch each class as.
BUILT_IN = {
    errors.RecipeUnreadable: ValueError,
    errors.AmendmentRefused: ValueError,
    errors.DeclarationUnreadable: ValueError,
    errors.SourceDefect: ValueError,
    errors.UnsupportedEncoding: ValueError,
    errors.PayloadRefused: ValueError,
    errors.UsageError: ValueError,
    errors.UndeclaredResource: KeyError,
    errors.UnknownCompensation: KeyError,
    errors.CompensationsInvalid: ValueError,
    errors.FixedOffsetZone: TypeError,
    errors.OffGrid: ValueError,
    errors.NonFinite: ValueError,
    errors.NaiveTimestamp: ValueError,
    errors.CarriedNotAnInteger: ValueError,
    errors.OutOfRange: ValueError,
    errors.TickOverflow: OverflowError,
    errors.Collided: ValueError,
    errors.PacketOccupied: FileExistsError,
}


def test_an_error_a_caller_catches_as_a_built_in_stays_one():
    for cls, built_in in BUILT_IN.items():
        assert issubclass(cls, built_in), cls


def test_an_error_that_is_a_key_error_prints_its_message_bare():
    """A `KeyError` quotes its argument, which a refusal printed to a person should not be."""
    assert str(errors.UndeclaredResource("no table named x", resource_id="x")) == "no table named x"
    assert str(errors.UnknownCompensation("x is not registered", identifier="x")) == "x is not registered"


def test_an_occupied_root_carries_what_is_in_the_way(tmp_path):
    refused = errors.PacketOccupied("occupied", root=tmp_path, occupied=("tables",))
    assert (str(refused), refused.root, refused.occupied) == ("occupied", tmp_path, ["tables"])


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


def test_no_module_raises_a_built_in_exception():
    """A caller catching the package base catches every deliberate refusal, so none is a bare built-in."""
    built_in = {name for name, cls in vars(builtins).items() if isinstance(cls, type) and issubclass(cls, Exception)}
    for path in sorted(Path(escapewheel_writer.__file__).parent.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Raise) and node.exc is not None:
                raised = getattr(node.exc, "func", node.exc)
                assert getattr(raised, "id", None) not in built_in, f"{path.name}:{node.lineno}"

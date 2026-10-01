"""An exception these adapters define is one a build already catches."""

import ast
import builtins
import importlib
import inspect
import pkgutil
from enum import StrEnum
from pathlib import Path

from escapewheel_writer import WriterError

import escapewheel_aind
from escapewheel_aind import errors

#: The classes an adapter raises with a code.
DEFECTS = {"SourceDefect", "UnsupportedEncoding"}


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


def test_a_code_is_its_name_in_lower_case():
    """A code is compared and logged, so its two spellings differ in case alone."""
    for _, codes in inspect.getmembers(errors, inspect.isclass):
        if issubclass(codes, StrEnum) and codes.__module__ == errors.__name__:
            for member in codes:
                assert member.value == member.name.lower(), member


def test_every_defect_this_package_raises_carries_a_code():
    """A caller tells defects apart by code, so one raised without a code is one it cannot tell."""
    for path in sorted(Path(escapewheel_aind.__file__).parent.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) in DEFECTS:
                assert any(keyword.arg == "code" for keyword in node.keywords), f"{path.name}:{node.lineno}"


def test_no_module_raises_a_built_in_exception():
    """A caller catching the package base catches every deliberate refusal, so none is a bare built-in."""
    built_in = {name for name, cls in vars(builtins).items() if isinstance(cls, type) and issubclass(cls, Exception)}
    for path in sorted(Path(escapewheel_aind.__file__).parent.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Raise) and node.exc is not None:
                raised = getattr(node.exc, "func", node.exc)
                assert getattr(raised, "id", None) not in built_in, f"{path.name}:{node.lineno}"
